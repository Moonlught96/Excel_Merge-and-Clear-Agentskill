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

## YouTube Export Variants Use Different Display-Name Headers

### Symptom

YouTube long-video exports may provide display names in `author`, while YouTube Shorts exports may provide the same kind of display name in `author_name`. Treating Shorts as a separate platform or leaving `author_name` unregistered produces blank or incompatible hash IDs.

### Fixed Rule

- Register both `author` and `author_name` as ordered YouTube display-name fallbacks.
- Normalize `YouTube` and `YouTube Shorts` to the same `youtube` platform namespace.
- Use the same research-project key and the same display-name identity domain for both headers.
- Therefore, the same trimmed display name in `author` and `author_name` produces the same hash ID within the same research project.
- Keep raw `author` and `author_name` values out of standardized and cleaned outputs, logs, and summaries.

This is exact configured header mapping, not AI inference or fuzzy identity matching.

## Output Collision And Partial-Write Risks

Earlier tools could replace an existing output without an explicit CLI choice, and a CSV input could collide with the cleaner's derived `.csv` sidecar. All workflow writers now reject input/output collisions, reject existing CLI destinations unless `--overwrite` was explicitly confirmed, and stage files beside the destination before atomic replacement. Cleanup also refuses to run without at least one protected path.

## Compact Dates Mistaken For Unix Timestamps

An eight-digit date such as `20260709` is numerically plausible as a Unix timestamp. The standardizer now parses valid `YYYYMMDD` calendar values before Unix timestamp detection, so the result is `2026-07-09` rather than a 1970 date.

## Audit Comparison Lost Formula And Duplicate Detail

Comparison previously read cached formula results and indexed rows as a set, which could hide formula differences and duplicate-count differences. Comparison now reads with `data_only=False`, preserves formula text, and uses row counters so duplicate-row multiplicity remains visible.

## YouTube Shorts Paths Fell Through To Generic YouTube Naming

A path under an exact `Shorts` directory used to match the generic `youtube` keyword first and produced `YouTube评论数据`. Naming now gives the exact `Shorts` path segment precedence and emits `YouTube Shorts评论数据`; long-video paths remain `YouTube评论数据`. Both display labels still resolve to the shared `youtube` hash namespace.

## Emoji Filenames Failed On Windows GBK Consoles

The naming CLI previously printed unescaped Unicode through the inherited console encoding. A filename containing an emoji could raise `UnicodeEncodeError` before any workbook processing. JSON output is now written through a UTF-8 reconfigured stream when supported, with ASCII-escaped JSON as a deterministic fallback.
