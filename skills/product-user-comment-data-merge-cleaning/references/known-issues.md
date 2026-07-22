# Known Issues And Deterministic Resolutions

## Blank Stable Account-ID Column Blocks Display-Name Hashing

### Symptom

A source worksheet contains both a registered stable account-ID header and a registered display-name header, but the stable account-ID column is entirely blank. Earlier versions selected the account-ID header solely because it existed, so every standardized `哈希ID` cell was blank even though display names were available.

Confirmed YouTube example:

- `author_channel_id` exists but every data cell is blank;
- `author` contains the available display name;
- the standardized workbook previously produced no hash IDs.

### Root Cause

Identity selection checked header presence but did not check whether the registered account-ID column contained a usable value. The worksheet-wide no-row-fallback rule then correctly preserved blank hashes, but the initial worksheet-level source selection was wrong for an entirely empty ID column.

### Fixed Rule

Use this deterministic worksheet-level selection order:

1. Inspect registered account-ID headers in configured priority order.
2. Select the first account-ID column containing at least one nonblank value.
3. If every registered account-ID column is absent or entirely blank, select the first present display-name fallback in configured priority order.
4. Apply the selected source to the entire worksheet.
5. If a selected account-ID column has at least one value but is blank on individual rows, keep those rows' `哈希ID` blank. Never mix account IDs and display names row-by-row.

For YouTube, an entirely blank `author_channel_id`/`authorChannelId`/`Author Channel ID` set therefore falls back to `author`. The same rule applies to every platform using its registered mappings in `config/hash-id.json`.

### Safety And Consistency

- Selection and hashing remain deterministic tools only; AI does not inspect or choose identity values.
- Raw account IDs and display names remain omitted from standardized output, cleaned output, logs, and summaries.
- Display-name hashing remains weak pseudonymization, not legal anonymization.
- The same project, platform, identity type, and trimmed display name produce the same hash.
- No cleaning, merging, naming, confirmation, or retention rule changes as part of this fix.

### Regression Coverage

Tests must prove both cases:

- an entirely blank account-ID column falls back to the registered display name and repeated names receive the same hash;
- an account-ID column containing at least one value remains selected for the worksheet, and individual blank rows do not fall back to display names.
