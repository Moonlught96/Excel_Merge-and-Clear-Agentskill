# Rule Change Record: YouTube Shorts Author Name

- Change type: YouTube display-name fallback alias.
- User-confirmed rule: YouTube long-video and Shorts exports belong to the same platform and must reuse hash IDs for the same available user identity.
- Platform evidence: the Shorts export uses `author_name`; the long-video export uses `author`.
- Configuration: append `author_name` after `author` in YouTube `display_name_headers`; retain the shared `youtube` namespace and existing `YouTube Shorts` platform alias.
- Hash behavior: the same project, `youtube` namespace, display-name identity type, and trimmed value produce the same HMAC-SHA256 hash regardless of whether the source header is `author` or `author_name`.
- Safety: raw names remain omitted; no fuzzy matching, semantic inference, or AI data decision is introduced.
- Unchanged rules: account-ID priority, entirely blank account-ID fallback, no row-by-row source mixing, merge, cleaning, naming, confirmation, and retention behavior.
