"""Versioned source-bound semantic annotation contract. No model inference."""
from __future__ import annotations

from collections import defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re

try:
    from .semantic_review_io import HEADERS, snapshot
    from .clean_excel_comments import normalize_confirmed_technical_terms, contains_confirmed_technical_term
except ImportError:
    from semantic_review_io import HEADERS, snapshot
    from clean_excel_comments import normalize_confirmed_technical_terms, contains_confirmed_technical_term

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / 'config/semantic-review.json'
PROMPT_PATH = (ROOT / 'assets/ai-semantic-review/annotation-prompt.md' if (ROOT / 'SKILL.md').exists()
               else ROOT / 'skills/product-user-comment-data-merge-cleaning/assets/ai-semantic-review/annotation-prompt.md')


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    def unique(pairs):
        d = {}
        for k, v in pairs:
            require(k not in d, 'Duplicate JSON object key')
            d[k] = v
        return d
    def invalid(_):
        raise ValueError('Non-finite JSON constant')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique, parse_constant=invalid)


def fields(obj, names):
    require(type(obj) is dict and set(obj) == set(names), 'Invalid object fields')


def nonblank(value, limit=4000):
    require(type(value) is str and bool(value.strip()) and len(value) <= limit,
            'Expected nonempty bounded text')
    require(re.search(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', value) is None, 'Illegal control character')


def build_manifest(source, project, platform, technical_terms, kol_terms, batch_size=None):
    nonblank(project, 200)
    nonblank(platform, 100)
    for terms in (technical_terms, kol_terms):
        require(type(terms) is list, 'Terms must be a list')
        for term in terms:
            nonblank(term, 200)
    technical = list(normalize_confirmed_technical_terms(tuple(technical_terms)))
    kol = list(normalize_confirmed_technical_terms(tuple(kol_terms)))
    sha = file_digest(source)
    sheets, rows = snapshot(Path(source))
    require(file_digest(source) == sha, 'Source changed while reading')
    prefix, identities = defaultdict(list), defaultdict(list)
    for row in rows:
        comment = str(row['values'][1] or '')
        row['technical_hits'] = [t for t in technical if contains_confirmed_technical_term(comment, t)]
        row['kol_hits'] = [t for t in kol if contains_confirmed_technical_term(comment, t)]
        normalized = re.sub(r'\s+', '', comment)
        if len(normalized) >= 10:
            prefix[normalized[:10]].append(row['id'])
        if row['values'][5]:
            identities[row['values'][5]].append(row['id'])
    policy = load_json(POLICY_PATH)
    size = policy['batch_size'] if batch_size is None else batch_size
    require(type(size) is int and 1 <= size <= 60, 'Invalid fixed batch size')
    data = {'version': policy['version'], 'source_sha256': sha, 'batch_size': size,
            'policy_sha256': file_digest(POLICY_PATH), 'prompt_sha256': file_digest(PROMPT_PATH),
            'project': project, 'platform': platform, 'technical_terms': technical, 'kol_terms': kol,
            'sheets': sheets, 'rows': rows,
            'candidates': {'same_prefix': [ids for ids in prefix.values() if len(ids) >= 3],
                           'same_key': [ids for ids in identities.values() if len(ids) >= 2]},
            'batches': [{'id': f'b{i // size + 1:04}', 'row_ids': [r['id'] for r in rows[i:i + size]]}
                        for i in range(0, len(rows), size)]}
    data['run_id'] = digest(data)
    return data


def check_manifest(source, manifest):
    require(type(manifest) is dict, 'Invalid manifest')
    try:
        expected = build_manifest(source, manifest['project'], manifest['platform'],
                                  manifest['technical_terms'], manifest['kol_terms'], manifest['batch_size'])
    except KeyError as exc:
        raise ValueError('Incomplete manifest') from exc
    require(expected == manifest, 'Source, policy, prompt or manifest changed; prepare a new run')


def quote(q, row, policy, extra=()):
    fields(q, ['field', 'quote', *extra])
    require(q['field'] in policy['evidence_fields'], 'Evidence must reference a comment field')
    nonblank(q['quote'], 2000)
    value = row['values'][HEADERS.index(q['field'])]
    require(type(value) is str and q['quote'] in value, 'Evidence quote is not in source row')


def validate_k(ks, row, policy):
    require(type(ks) is list, 'K must be an array')
    seen = set()
    for k in ks:
        quote(k, row, policy, ('code',))
        require(k['code'] in policy['k_codes'] and k['code'] not in seen, 'Invalid/duplicate K code')
        seen.add(k['code'])


def validate_r1(pairs, row, policy):
    require(type(pairs) is list, 'R1 must be an array')
    if not pairs:
        return
    require(len(pairs) >= policy['r1_min_pairs'], 'R1 needs consecutive function/effect evidence pairs')
    cursor = 0
    body = str(row['values'][1] or '')
    for pair in pairs:
        fields(pair, ['function', 'effect'])
        for part in ('function', 'effect'):
            q = pair[part]
            quote(q, row, policy)
            require(q['field'] == '评论内容', 'R1 must use main comment, not inferred reply context')
            start = body.find(q['quote'], cursor)
            require(start >= cursor, 'R1 quotes must be nonoverlapping in source order')
            cursor = start + len(q['quote'])


def validate_r3(group, key, rows, policy):
    if group is None:
        return None
    fields(group, ['members', 'quotes'])
    members = group['members']
    require(type(members) is list and all(type(x) is str for x in members), 'Invalid R3 members')
    require(len(set(members)) == len(members) and key in members and all(k in rows for k in members),
            'R3 members must uniquely reference this run and include the annotated row')
    keys = {rows[k]['values'][5] for k in members if rows[k]['values'][5]}
    require(len(keys) >= policy['r3_distinct_nonempty_keys'], 'R3 requires three distinct nonempty full keys')
    qs = group['quotes']
    require(type(qs) is list and len(qs) == len(members), 'R3 evidence coverage mismatch')
    require(all(type(q) is dict and type(q.get('id')) is str for q in qs), 'Invalid R3 quote')
    require([q['id'] for q in qs] == members, 'R3 evidence member order mismatch')
    for q in qs:
        quote(q, rows[q['id']], policy, ('id',))
    return {'members': members, 'quotes': qs, 'distinct_hashes': len(keys)}


def validate_annotations(manifest, documents, review=None, require_reviews=False):
    policy = load_json(POLICY_PATH)
    rows = {r['id']: r for r in manifest['rows']}
    require(type(documents) is list and len(documents) == len(manifest['batches']), 'Missing/extra annotation batches')
    decisions, group_map = {}, {}
    for doc, batch in zip(documents, manifest['batches']):
        fields(doc, ['run_id', 'batch_id', 'model', 'prompt_sha256', 'annotations'])
        require(doc['run_id'] == manifest['run_id'] and doc['batch_id'] == batch['id'], 'Annotation batch/run mismatch')
        require(doc['prompt_sha256'] == manifest['prompt_sha256'], 'Annotation prompt version mismatch')
        nonblank(doc['model'], 200)
        annotations = doc['annotations']
        require(type(annotations) is list and len(annotations) == len(batch['row_ids']), 'Annotation row coverage mismatch')
        for a, key in zip(annotations, batch['row_ids']):
            fields(a, ['id', 'label', 'k', 'family', 'evidence', 'r1', 'r3', 'note'])
            require(type(a['id']) is str and a['id'] == key and key not in decisions, 'Duplicate/wrong row key')
            require(a['label'] in policy['labels'], 'Invalid label')
            nonblank(a['note'])
            require(type(a['family']) is str and a['family'] in ['', *policy['a_families'], *policy['b_families']], 'Invalid family')
            row = rows[key]
            validate_k(a['k'], row, policy)
            require(type(a['evidence']) is list, 'Evidence must be an array')
            for q in a['evidence']:
                quote(q, row, policy)
            validate_r1(a['r1'], row, policy)
            group = validate_r3(a['r3'], key, rows, policy)
            if group:
                group_map[digest(sorted(group['members']))] = group
            if a['label'] == 'A':
                require(not a['k'] and a['family'] in policy['a_families'] and a['evidence'], 'A requires a supported family, evidence and no K')
                if a['family'] == 'R3pair':
                    require(group is not None, 'Same-account pair alone cannot authorize A')
                if a['family'] == 'G1a':
                    require(bool(a['r1']), 'G1a requires function/effect chain evidence')
                if a['family'] == 'G3':
                    require(len(row['technical_hits']) >= policy['r2_distinct_terms'], 'G3 requires computed R2')
            d = copy.deepcopy(a)
            d.update(final_label=a['label'], final_note=a['note'])
            decisions[key] = d
    aset = [k for k, d in decisions.items() if d['label'] == 'A']
    if review is None:
        require(not require_reviews or not aset, 'A candidates require bound full-text second-pass reviews')
    else:
        fields(review, ['run_id', 'annotations_sha256', 'reviewer', 'reviews'])
        require(review['run_id'] == manifest['run_id'] and review['annotations_sha256'] == digest(documents), 'Stale review/annotation binding')
        nonblank(review['reviewer'], 200)
        require(type(review['reviews']) is list and len(review['reviews']) == len(aset), 'Review coverage mismatch')
        for r, key in zip(review['reviews'], aset):
            fields(r, ['id', 'decision', 'full_text_reviewed', 'k', 'evidence', 'note'])
            require(type(r['id']) is str and r['id'] == key, 'Review row/order mismatch')
            require(r['decision'] in ['delete', 'keep', 'uncertain'] and r['full_text_reviewed'] is True, 'Invalid/incomplete full-text review')
            nonblank(r['note'])
            validate_k(r['k'], rows[key], policy)
            require(type(r['evidence']) is list and bool(r['evidence']), 'Review evidence required')
            for q in r['evidence']:
                quote(q, rows[key], policy)
            require(r['decision'] != 'delete' or not r['k'], 'K protection forbids deletion')
            d = decisions[key]
            d.update(final_label='A' if r['decision'] == 'delete' else 'B', final_note=r['note'],
                     review_decision=r['decision'], review_note=r['note'])
            if r['k']:
                d['k'] = r['k']
    return decisions, list(group_map.values())
