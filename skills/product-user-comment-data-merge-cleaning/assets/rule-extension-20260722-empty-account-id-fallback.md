# Rule Change Record: Empty Account-ID Fallback

- Change type: display-name fallback selection.
- User-confirmed rule: when every registered stable account-ID column is entirely blank, continue to the platform's registered display-name fallback for worksheet-wide hash generation.
- Confirmed example: YouTube `author_channel_id` is entirely blank while `author` contains display names.
- Identity type and priority: select the first registered account-ID column with at least one nonblank value; otherwise select the first registered display-name fallback.
- Rules kept unchanged: no row-by-row identity-source mixing; raw identities are never output; HMAC-SHA256 project/platform isolation remains unchanged; merge, cleaning, naming, confirmation, and retention behavior remains unchanged.
- Script files: `scripts/standardize_excel_headers.py` and project source `tools/standardize_excel_headers.py`.
- Reference files: `references/workflow.md`, `references/data-contract.md`, `references/header-standardization.md`, `references/tool-reference.md`, `references/extension-policy.md`, and `references/known-issues.md`.
- Regression tests: entirely blank account-ID fallback plus partially populated account-ID no-row-fallback coverage in `tests/test_standardize_excel_headers.py`.
- Validation: full test suite, bundle synchronization check, bytecode compilation, diff check, and isolated Skill package tests must pass before release.
