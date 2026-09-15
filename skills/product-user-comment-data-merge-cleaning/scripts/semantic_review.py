"""Optional post-traditional AI review: deterministic packaging and validation CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from .semantic_review_contract import (build_manifest, check_manifest, load_json, validate_annotations,
                                         digest, PROMPT_PATH)
    from .semantic_review_io import export_outputs, verify_outputs
    from .output_path_safety import ensure_output_paths_safe, atomic_output_path, add_confirmed_overwrite_arguments
except ImportError:
    from semantic_review_contract import (build_manifest, check_manifest, load_json, validate_annotations,
                                        digest, PROMPT_PATH)
    from semantic_review_io import export_outputs, verify_outputs
    from output_path_safety import ensure_output_paths_safe, atomic_output_path, add_confirmed_overwrite_arguments


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare', help='Package full source-bound batches; does not call a model')
    prep.add_argument('--input', type=Path, required=True)
    prep.add_argument('--output', type=Path, required=True)
    prep.add_argument('--project', required=True)
    prep.add_argument('--platform', required=True)
    prep.add_argument('--confirm-traditional-output', action='store_true', required=True)
    prep.add_argument('--technical-term', action='append', default=[])
    prep.add_argument('--kol-term', action='append', default=[])
    prep.add_argument('--confirm-terms-complete', action='store_true')
    prep.add_argument('--batch-size', type=int, default=60, help='1..60; reduce for long comments, never truncate')
    add_confirmed_overwrite_arguments(prep)
    for command in ('show-batch', 'validate', 'export', 'verify'):
        sp = sub.add_parser(command)
        sp.add_argument('--input', type=Path, required=True)
        sp.add_argument('--manifest', type=Path, required=True)
        if command == 'show-batch':
            sp.add_argument('--batch-id', required=True)
        else:
            sp.add_argument('--annotation', type=Path, action='append', default=[])
            sp.add_argument('--reviews', type=Path)
        if command in ('export', 'verify'):
            sp.add_argument('--review-output', type=Path, required=True)
            sp.add_argument('--output', type=Path, required=True)
            sp.add_argument('--csv-output', type=Path, required=True)
        if command == 'export':
            add_confirmed_overwrite_arguments(sp)
    return p


def run(args):
    if args.command == 'prepare':
        if (args.technical_term or args.kol_term) and not args.confirm_terms_complete:
            raise ValueError('Runtime term lists require current-conversation completion confirmation')
        if args.output.suffix.lower() != '.json':
            raise ValueError('Manifest output must be .json')
        if args.output.name.endswith('.summary.json'):
            raise ValueError('AI manifest must not recreate a finalized traditional summary')
        ensure_output_paths_safe([args.input], [args.output], overwrite=args.overwrite,
                                 overwrite_confirmations=args.confirm_overwrite)
        manifest = build_manifest(args.input, args.project, args.platform, args.technical_term, args.kol_term, args.batch_size)
        with atomic_output_path(args.output) as staged:
            staged.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        return {'run_id': manifest['run_id'], 'batches': len(manifest['batches']), 'manifest': str(args.output)}
    manifest = load_json(args.manifest)
    check_manifest(args.input, manifest)
    if args.command == 'show-batch':
        batch = next((b for b in manifest['batches'] if b['id'] == args.batch_id), None)
        if batch is None:
            raise ValueError('Unknown batch ID')
        ids = set(batch['row_ids'])
        return {'run_id': manifest['run_id'], 'prompt_sha256': manifest['prompt_sha256'],
                'batch_id': batch['id'], 'instructions': PROMPT_PATH.read_text(encoding='utf-8'),
                'untrusted_comment_rows': [r for r in manifest['rows'] if r['id'] in ids]}
    annotation_paths = [p.resolve() for p in args.annotation]
    if len(set(annotation_paths)) != len(annotation_paths):
        raise ValueError('Duplicate annotation file paths')
    docs = [load_json(p) for p in annotation_paths]
    # Order-independent explicit paths, but duplicates/wrong batch IDs still fail.
    if not all(type(d) is dict and type(d.get('batch_id')) is str for d in docs):
        raise ValueError('Invalid annotation envelope')
    docs.sort(key=lambda d: d['batch_id'])
    review = load_json(args.reviews) if args.reviews else None
    decisions, groups = validate_annotations(manifest, docs, review, require_reviews=args.command in ('export', 'verify'))
    if args.command == 'validate':
        return {'valid': True, 'annotations_sha256': digest(docs),
                'A_reviews_required': sum(d['label'] == 'A' for d in decisions.values())}
    outputs = [args.review_output, args.output, args.csv_output]
    if args.command == 'export':
        protected = [args.input, args.manifest, *args.annotation, *([args.reviews] if args.reviews else [])]
        export_outputs(manifest, decisions, groups, outputs, protected, args.overwrite, args.confirm_overwrite)
    else:
        verify_outputs(manifest, decisions, groups, outputs)
    return {'verified': True, 'outputs': [str(p) for p in outputs]}


def main():
    args = parser().parse_args()
    try:
        result = run(args)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        # Avoid printing untrusted raw values or Python tracebacks in summaries.
        print(f'ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
