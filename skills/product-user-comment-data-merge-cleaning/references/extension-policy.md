# Safe Extension Policy

## Locked Base Rules

All confirmed merge, standardization, cleaning, naming, confirmation, output, and retention rules are locked. Do not change a base rule while adding another feature. A base rule may change only when the user explicitly identifies the exact rule to modify.

Examples of locked behavior include:

- deterministic processing without AI data judgment;
- the nine-column standard output order including `哈希ID`;
- Chinese main-comment threshold of 7 or fewer characters;
- non-Chinese threshold of 4 or fewer words and unspaced fallback of 4 or fewer characters;
- pure numeric legacy threshold;
- fixed-word append-only behavior preserving `链接`;
- same-worksheet duplicate policy that keeps the last occurrence;
- subcomment duplicate/short rules that clear cells instead of deleting rows;
- confirmation gates between merge, standardization, and cleaning;
- default retention of only cleaned `.xlsx` and `.csv`.

## Adding A Header Alias

1. Obtain an explicit mapping from the user.
2. Update only the relevant `aliases` list in `config/header-standardizer.json`.
3. Do not change output order, required status, or another alias list unless explicitly requested.
4. Add a representative test proving the new alias maps to the intended standard column with its data intact.
5. Update `references/header-standardization.md`.
6. Synchronize the bundled configuration.

## Adding A Fixed Delete Word

1. Append the confirmed term; never replace or remove existing terms.
2. Add confirmed equivalents for Chinese, English, Japanese, Korean, Spanish, Thai, and Hindi where applicable.
3. Use the case-insensitive list when case variants must match.
4. Do not use AI-generated translations as live cleaning decisions.
5. Add tests for matching and a nearby negative case.
6. Update `references/cleaning-rules.md` and synchronize the bundled configuration.

## Adding Automation

- Put deterministic executable behavior in `scripts/`.
- Put executable configuration in `config/`.
- Put detailed requirements and content standards in `references/`.
- Put reusable templates, forms, and output scaffolds in `assets/`.
- Keep `SKILL.md` concise and link to the relevant reference instead of duplicating long rule lists.
- Preserve standalone operation: bundled scripts must resolve companion modules and configuration relative to the Skill folder.

## Required Change Record

Use `assets/rule-extension-template.md` to record:

- the exact user-confirmed change;
- the rules explicitly kept unchanged;
- affected config, script, reference, and tests;
- isolated Skill verification.

## Validation For Every Extension

- Update or add a test before changing behavior.
- Confirm the test fails for the missing behavior.
- Make the minimal deterministic implementation.
- Run the entire suite, not only the new test.
- Run the Skill bundle consistency check.
- Run the isolated-copy smoke test.
- Do not claim completion while any validation fails.

## Adding A Verified User-ID Header

1. Accept only an explicit platform account-ID field confirmed from the exporter schema; do not infer from values.
2. Add it to the matching platform in `config/hash-id.json`.
3. Never register comment IDs, parent IDs, usernames, nicknames, profile URLs, or ambiguous identity fields.
4. Add positive, blank-fallback, cross-platform, and raw-ID non-disclosure tests.
5. Synchronize the bundled scripts/config and update the header reference.