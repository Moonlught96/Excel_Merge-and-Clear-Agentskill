# 2026-07-22 Deterministic Safety Hardening

## Confirmed Scope

- Reject duplicate merge inputs.
- Parse valid eight-digit `YYYYMMDD` dates before Unix timestamps.
- Reject input/output collisions and unconfirmed existing outputs.
- Write generated artifacts through same-directory temporary files and atomic replacement.
- Require explicit cleanup protection paths.
- Preserve formulas and duplicate-row multiplicity in audit comparison.
- Close workbooks opened during naming and reporting.
- Accept BOM-marked UTF-16 CSV in addition to UTF-8 and GB18030.

## Rules Kept Unchanged

- No AI data judgment.
- Fixed standard schema, hash-ID policy, cleaning rules, confirmation gates, naming convention, and final retention policy.
- Original inputs remain unchanged.

## Verification

- Add failing regression tests before each behavior change.
- Synchronize project tools into the standalone Skill.
- Run the complete test suite, compile check, bundle consistency check, isolated-copy test, and `git diff --check`.
