# AI Semantic Extension Change Record

Change type: optional post-cleaning AI workflow; no traditional rule changes.

Exact user-confirmed change: on 2026-09-14 user selected “传统规则保持不变，AI 扩展接在传统清洗结果之后”, then authorized “先修复，后推送” after reviewing the supplied package's defects and repair plan.

Locked base rules kept unchanged: every existing merge, platform route, standardization, hash identity/key, length/word, duplicate, technical-term/KOL, confirmation, naming, overwrite and default cleanup rule; all preexisting executable base configurations and scripts.

Affected platform/language: no new platform/header/identity mapping. Input is a confirmed traditional eleven-column XLSX. AI performance across languages/platforms is not asserted.

Identity evidence: no new source fields; existing pseudonymous keys copied only. Raw identity values and real user comments must never be committed.

New configuration: `config/semantic-review.json`, synchronized into the Skill; no product word lists or model credentials.

New scripts: `semantic_review.py`, `semantic_review_contract.py`, `semantic_review_io.py`, synchronized into `scripts/`. Reuses existing read-only technical-term matcher and output-path guards without changing them.

References: `ai-semantic-review.md`, this record; scoped routing added to `extension-policy.md` and `SKILL.md`. AI prompt and confirmation templates are in `assets/ai-semantic-review/`.

Verification: `tests/test_semantic_review.py` contains synthetic source, annotation corruption, A review, R1/R3, typed XLSX, all-field output and isolated full-Skill copy tests. Release verification results are recorded in the repository release report; no accuracy claim follows from these tests.

Audit repair (2026-09-17): fixed literal formula-text preservation after deterministic URL removal while preserving genuine formulas, and Taobao product splitting; raw header exactness during merge; manifest/output type-sensitive comparison; case-insensitive final sidecar protection; manifest-defined batch ordering; direct-product precedence over the Taobao combined field; portable `tzdata` declaration; and the related workflow/template/reference contradictions. These repairs do not change traditional selection rules, user gates, identity mappings, or retention.

Intentional changes from the supplied Markdown: omit its conflicting stage one; replace fixed row/date/file paths and historical conclusions with source-bound computation; preserve existing empty/display-name hashes; never truncate comments; make failures block output; preserve cell types and formula provenance; require source-bound structural evidence and full-text A review. R1 uses at least two ordered function/effect pairs as a descriptive chain, not a fraud confidence threshold. The UI/Agent must state uncertainty rather than manufacture account or product authenticity facts.
