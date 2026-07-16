# Display Name Hash Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic username/nickname fallback that produces stable project-scoped `哈希ID` values when a platform has no configured stable account-ID column, while preserving every existing account-ID hash.

**Architecture:** Extend the versioned platform identity configuration with ordered `display_name_headers`, then select one identity source for the entire worksheet using account IDs first and display names second. Keep `hash_user_id()` byte-for-byte compatible and add a separate display-name HMAC message containing a fixed `display_name` type segment. The standardizer records only aggregate identity metadata and the portable Skill receives byte-identical scripts and configuration.

**Tech Stack:** Python 3 standard library (`dataclasses`, `hashlib`, `hmac`, `json`, `struct`, `unittest`), openpyxl, Windows DPAPI project store, JSON configuration.

---

## File Map

- Modify `config/hash-id.json`: add ordered display-name aliases for YouTube, 小红书, B站, TikTok, 淘宝, and 京东.
- Modify `tools/hash_id_pseudonymizer.py`: validate the new configuration, represent identity type, select a worksheet identity source, and hash display names in a separate message space.
- Modify `tools/standardize_excel_headers.py`: use the typed identity selection, hash the chosen source, redact raw values, and report `identity_type`.
- Modify `tests/test_hash_id_pseudonymizer.py`: cover alias priority, deterministic equality, platform/project isolation, type isolation, configuration rejection, and the historical account-ID vector.
- Modify `tests/test_standardize_excel_headers.py`: cover all platform fallbacks, whole-sheet priority, summaries, and missing-context failures.
- Modify `tests/test_end_to_end_workflow.py`: run the B站 workflow with a fixed project context and verify hashes survive cleaning.
- Modify `AGENTS.md` and `README.md`: replace the obsolete prohibition on username/nickname hashing with the approved fallback boundary.
- Modify `skills/product-user-comment-data-merge-cleaning/SKILL.md`, `references/`, and `assets/`: document source priority, privacy strength, platform mappings, and extension rules.
- Synchronize `tools/hash_id_pseudonymizer.py`, `tools/standardize_excel_headers.py`, and `config/hash-id.json` into `skills/product-user-comment-data-merge-cleaning/` through `tools/sync_skill_bundle.py`.
- Modify package/documentation tests only where they assert the previous “never hash display names” policy.

### Task 1: Configuration Model and Typed Identity Selection

**Files:**
- Modify: `config/hash-id.json`
- Modify: `tools/hash_id_pseudonymizer.py:61-194`
- Modify: `tests/test_hash_id_pseudonymizer.py:188-300`

- [ ] **Step 1: Write failing configuration and source-selection tests**

Add imports for `select_identity_header` and assert the selected identity type and priority:

```python
def test_bilibili_selects_username_as_display_name(self) -> None:
    selected = select_identity_header(
        ["rpid", "parent_rpid", "username", "content"],
        "B站",
        self.config,
    )
    self.assertIsNotNone(selected)
    assert selected is not None
    self.assertEqual("username", selected.source_header)
    self.assertEqual(3, selected.source_column)
    self.assertEqual("display_name", selected.identity_type)

def test_stable_id_wins_over_display_name_for_whole_sheet(self) -> None:
    selected = select_identity_header(
        ["author", "author_channel_id"],
        "YouTube",
        self.config,
    )
    self.assertIsNotNone(selected)
    assert selected is not None
    self.assertEqual("author_channel_id", selected.source_header)
    self.assertEqual("account_id", selected.identity_type)

def test_tiktok_display_name_priority_is_username_then_nickname(self) -> None:
    selected = select_identity_header(
        ["昵称", "用户名", "用户身份"],
        "TikTok",
        self.config,
    )
    self.assertIsNotNone(selected)
    assert selected is not None
    self.assertEqual("用户名", selected.source_header)
    self.assertEqual("display_name", selected.identity_type)

def test_ambiguous_identity_and_comment_ids_are_not_selected(self) -> None:
    for platform in ("B站", "TikTok", "淘宝", "京东"):
        with self.subTest(platform=platform):
            self.assertIsNone(
                select_identity_header(
                    ["用户身份", "评论ID", "rpid", "parent_rpid", "url"],
                    platform,
                    self.config,
                )
            )
```

Create temporary invalid configs and assert `HashIdConfigError` for duplicate, blank, or non-list `display_name_headers`.

- [ ] **Step 2: Run the selection tests and verify RED**

Run: `python -m unittest tests.test_hash_id_pseudonymizer -v`

Expected: FAIL because `PlatformIdentityConfig` has no `display_name_headers`, `SelectedIdentityHeader` has no `identity_type`, and `select_identity_header` does not exist.

- [ ] **Step 3: Add the configuration model and selector**

Extend the immutable models without removing `select_user_id_header`:

```python
@dataclass(frozen=True)
class PlatformIdentityConfig:
    namespace: str
    aliases: tuple[str, ...]
    user_id_headers: tuple[str, ...]
    display_name_headers: tuple[str, ...]

@dataclass(frozen=True)
class SelectedIdentityHeader:
    source_header: str
    source_column: int
    identity_type: str

def select_identity_header(
    headers: list[Any],
    platform: str,
    config: HashIdConfig,
) -> SelectedIdentityHeader | None:
    namespace = normalize_platform(platform, config)
    platform_config = next(
        item for item in config.platforms if item.namespace == namespace
    )
    for identity_type, configured_headers in (
        ("account_id", platform_config.user_id_headers),
        ("display_name", platform_config.display_name_headers),
    ):
        for configured_header in configured_headers:
            for source_column, header in enumerate(headers, start=1):
                if isinstance(header, str) and header == configured_header:
                    return SelectedIdentityHeader(
                        source_header=header,
                        source_column=source_column,
                        identity_type=identity_type,
                    )
    return None
```

Keep `select_user_id_header()` as a compatibility API that checks only `user_id_headers` and returns `identity_type="account_id"`. Validate that each header list contains only non-empty unique strings and that the same header is not present in both lists for one platform.

Update `config/hash-id.json` with this exact mapping:

```json
{
  "namespace": "youtube",
  "aliases": ["YouTube", "YouTube Shorts", "youtube", "yt-comments"],
  "user_id_headers": ["author_channel_id", "authorChannelId", "Author Channel ID"],
  "display_name_headers": ["author"]
}
```

Use `用户ID` then `用户名称` for 小红书; `username` for B站; `用户名`, `昵称` for TikTok; `用户名称`, `用户名` for 淘宝; and `用户名` for 京东. Preserve the existing platform order and algorithm version.

- [ ] **Step 4: Run the selection tests and verify GREEN**

Run: `python -m unittest tests.test_hash_id_pseudonymizer -v`

Expected: all configuration and selector tests PASS; legacy `select_user_id_header()` tests continue to pass.

- [ ] **Step 5: Commit typed identity selection**

```bash
git add config/hash-id.json tools/hash_id_pseudonymizer.py tests/test_hash_id_pseudonymizer.py
git commit -m "增加平台显示名身份源配置"
```

### Task 2: Display-Name HMAC with Historical Account-ID Compatibility

**Files:**
- Modify: `tools/hash_id_pseudonymizer.py:197-240`
- Modify: `tests/test_hash_id_pseudonymizer.py:30-187`

- [ ] **Step 1: Write failing hash-isolation and equality tests**

Add a public `hash_display_name()` API and lock the existing account-ID output:

```python
def test_existing_account_id_hash_vector_is_unchanged(self) -> None:
    self.assertEqual(
        "72bd4fc68258026ac244e1cfbb758e603455defca92af91c577ed9f9b23082c9",
        hash_user_id("UC-secret-user", "YouTube", self.context, self.config),
    )

def test_same_display_name_is_stable_across_source_header_names(self) -> None:
    username_hash = hash_display_name("same-user", "TikTok", self.context, self.config)
    nickname_hash = hash_display_name("same-user", "TikTok", self.context, self.config)
    self.assertEqual(username_hash, nickname_hash)

def test_display_name_is_isolated_from_account_id_and_platform(self) -> None:
    display_hash = hash_display_name("same-user", "YouTube", self.context, self.config)
    account_hash = hash_user_id("same-user", "YouTube", self.context, self.config)
    other_platform = hash_display_name("same-user", "B站", self.context, self.config)
    self.assertNotEqual(display_hash, account_hash)
    self.assertNotEqual(display_hash, other_platform)

def test_display_name_only_trims_outer_whitespace(self) -> None:
    self.assertEqual(
        hash_display_name("  Same User  ", "B站", self.context, self.config),
        hash_display_name("Same User", "B站", self.context, self.config),
    )
    self.assertNotEqual(
        hash_display_name("Same User", "B站", self.context, self.config),
        hash_display_name("same user", "B站", self.context, self.config),
    )
```

Also assert the same display name differs under a second `project_id`.

- [ ] **Step 2: Run pseudonymizer tests and verify RED**

Run: `python -m unittest tests.test_hash_id_pseudonymizer -v`

Expected: FAIL because `hash_display_name` is not defined.

- [ ] **Step 3: Implement display-name hashing without changing `hash_user_id`**

Use the existing normalization and validation, but add the fixed type segment only to display-name messages:

```python
def hash_display_name(
    value: Any,
    platform: str,
    context: HashProjectContext,
    config: HashIdConfig,
) -> str | None:
    _validate_project_context(context)
    namespace = normalize_platform(platform, config)
    normalized_display_name = normalize_raw_user_id(value)
    if normalized_display_name is None:
        return None
    message = _encode_length_prefixed(
        (
            config.algorithm_version,
            context.project_id,
            str(context.key_version),
            namespace,
            "display_name",
            normalized_display_name,
        )
    )
    return hmac.new(context.secret_key, message, hashlib.sha256).hexdigest()

def hash_selected_identity(
    value: Any,
    selected: SelectedIdentityHeader,
    platform: str,
    context: HashProjectContext,
    config: HashIdConfig,
) -> str | None:
    if selected.identity_type == "account_id":
        return hash_user_id(value, platform, context, config)
    if selected.identity_type == "display_name":
        return hash_display_name(value, platform, context, config)
    raise HashIdConfigError("Unsupported identity type")
```

Do not refactor the tuple inside `hash_user_id()`; the fixed-vector test must prove its bytes remain unchanged.

- [ ] **Step 4: Run pseudonymizer tests and verify GREEN**

Run: `python -m unittest tests.test_hash_id_pseudonymizer -v`

Expected: all tests PASS, including the historical 64-character vector.

- [ ] **Step 5: Commit the display-name hash path**

```bash
git add tools/hash_id_pseudonymizer.py tests/test_hash_id_pseudonymizer.py
git commit -m "实现显示名独立哈希空间"
```

### Task 3: Standardizer Integration and Redacted Identity Summaries

**Files:**
- Modify: `tools/standardize_excel_headers.py:21-42, 132-150, 492-655, 726-772`
- Modify: `tests/test_standardize_excel_headers.py:10-47, 320-433`

- [ ] **Step 1: Write failing standardizer tests for fallback, priority, and summaries**

Replace the previous blank B站/TikTok expectation with platform-specific tests:

```python
def test_hashes_bilibili_username_stably_and_redacts_summary(self) -> None:
    sheet.append(["rpid", "username", "content", "like_count", "timestamp"])
    sheet.append(["1001", "same-user", "评论内容足够完整", "4", "1678870952"])
    sheet.append(["1002", "same-user", "另一条评论内容足够完整", "2", "1678870953"])
    result = self.standardize_with_hash(input_path, tmp / "out", "B站")
    rows = list(load_workbook(result.output_xlsx, read_only=True, data_only=True).active.values)
    self.assertEqual(rows[1][3], rows[2][3])
    self.assertRegex(rows[1][3], r"^[0-9a-f]{64}$")
    summary_text = result.summary_json.read_text(encoding="utf-8")
    self.assertNotIn("same-user", summary_text)
    summary = json.loads(summary_text)
    self.assertEqual("display_name", summary["sheets"][0]["hash_id"]["identity_type"])
    self.assertEqual("username", summary["sheets"][0]["hash_id"]["source_header"])

def test_youtube_uses_account_id_for_every_row_when_id_column_exists(self) -> None:
    sheet.append(["author_channel_id", "author", "text", "published_at", "likes"])
    sheet.append(["UC-1", "same-user", "First useful review", "2026-07-08", 1])
    sheet.append([None, "same-user", "Second useful review", "2026-07-08", 2])
    result = self.standardize_with_hash(input_path, tmp / "out", "YouTube")
    rows = list(load_workbook(result.output_xlsx, read_only=True, data_only=True).active.values)
    self.assertRegex(rows[1][3], r"^[0-9a-f]{64}$")
    self.assertIsNone(rows[2][3])
```

Add cases for YouTube `author` fallback, 小红书 `用户名称` fallback, TikTok `用户名` priority with `昵称` fallback only when the username column is absent, 淘宝 `用户名称`, and 京东 `用户名`. Add a missing-context test using B站 `username` and assert the error contains the header name but not the raw username.

- [ ] **Step 2: Run standardizer tests and verify RED**

Run: `python -m unittest tests.test_standardize_excel_headers -v`

Expected: FAIL because the standardizer still selects only account-ID headers and omits `identity_type` from summaries.

- [ ] **Step 3: Use the typed selector and typed hash function**

Change `_all_registered_identity_headers()` to include both configured lists, call `select_identity_header()` from `resolve_identity_selection()`, and call `hash_selected_identity()` inside the row loop. Extend the summary model:

```python
@dataclass(frozen=True)
class HashIdSheetSummary:
    source_header: str | None
    source_column: int | None
    identity_type: str | None
    hashed_count: int
    blank_count: int
```

Serialize `identity_type` beside `source_header`. Change unsafe-value wording from “user ID” to “identity value” while retaining sheet, row, header, and identity type and never including the raw value. The selector remains worksheet-scoped, so a blank stable ID cell produces a blank hash rather than a nickname fallback.

- [ ] **Step 4: Run standardizer and hash suites and verify GREEN**

Run: `python -m unittest tests.test_hash_id_pseudonymizer tests.test_standardize_excel_headers -v`

Expected: all tests PASS; summary JSON contains aggregate type and counts only.

- [ ] **Step 5: Commit standardizer integration**

```bash
git add tools/standardize_excel_headers.py tests/test_standardize_excel_headers.py
git commit -m "在标准化流程接入显示名哈希兜底"
```

### Task 4: End-to-End Workflow and Hash Preservation

**Files:**
- Modify: `tests/test_end_to_end_workflow.py:1-120`
- Verify: `tests/test_clean_excel_comments.py`

- [ ] **Step 1: Write the failing B站 end-to-end assertions**

Create one fixed context in the test and pass `platform="B站"`, `hash_context`, and `load_hash_id_config()` to `standardize_workbook()`:

```python
hash_context = HashProjectContext(
    project_id="project-screenbar-e2e",
    project_name="ScreenBar十周年专案",
    key_version=1,
    key_fingerprint="test-fingerprint",
    secret_key=b"e" * 32,
)
standardize_result = standardize_workbook(
    stripped,
    load_config(),
    output_path=standardized,
    platform="B站",
    hash_context=hash_context,
    hash_config=load_hash_id_config(),
)
```

Use `user1` in both source files and assert both cleaned rows contain the same 64-character value in column D, while neither output row contains raw `user1` or IP data. Keep the source-byte equality and intermediate cleanup assertions.

- [ ] **Step 2: Run the end-to-end test and verify RED**

Run: `python -m unittest tests.test_end_to_end_workflow -v`

Expected: FAIL until the typed display-name path is integrated and the fixture passes project/platform context.

- [ ] **Step 3: Complete the fixture imports and assertions**

Import `HashProjectContext` and `load_hash_id_config`, update the two source rows to share `username="user1"`, and assert:

```python
self.assertRegex(cleaned_rows[1][3], r"^[0-9a-f]{64}$")
self.assertEqual(cleaned_rows[1][3], cleaned_rows[2][3])
self.assertNotIn("user1", cleaned_rows[1])
self.assertNotIn("user1", cleaned_rows[2])
```

No production cleaning rule changes are required because the cleaner already preserves standard columns.

- [ ] **Step 4: Run workflow and cleaner suites and verify GREEN**

Run: `python -m unittest tests.test_end_to_end_workflow tests.test_clean_excel_comments -v`

Expected: all tests PASS; cleaned `.xlsx` and `.csv` retain equal hash values and original inputs remain byte-identical.

- [ ] **Step 5: Commit workflow coverage**

```bash
git add tests/test_end_to_end_workflow.py
git commit -m "验证显示名哈希贯穿清洗流程"
```

### Task 5: Policy Documentation and Portable Skill Synchronization

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `skills/product-user-comment-data-merge-cleaning/SKILL.md`
- Modify: `skills/product-user-comment-data-merge-cleaning/references/data-contract.md`
- Modify: `skills/product-user-comment-data-merge-cleaning/references/header-standardization.md`
- Modify: `skills/product-user-comment-data-merge-cleaning/references/tool-reference.md`
- Modify: `skills/product-user-comment-data-merge-cleaning/references/extension-policy.md`
- Modify: `skills/product-user-comment-data-merge-cleaning/references/workflow.md`
- Modify: `skills/product-user-comment-data-merge-cleaning/assets/rule-extension-template.md`
- Modify: `tests/test_skill_package.py`
- Modify: `tests/test_skill_reference_coverage.py`
- Modify: `tests/test_workflow_docs.py`
- Synchronize: `skills/product-user-comment-data-merge-cleaning/scripts/hash_id_pseudonymizer.py`
- Synchronize: `skills/product-user-comment-data-merge-cleaning/scripts/standardize_excel_headers.py`
- Synchronize: `skills/product-user-comment-data-merge-cleaning/config/hash-id.json`

- [ ] **Step 1: Write failing policy and package assertions**

Require the references to contain these approved rules:

```python
required_display_name_hash_rules = (
    "stable account ID first",
    "display_name_headers",
    "display_name",
    "same project and platform",
    "weak linkage",
    "not legal anonymization",
    "用户名",
    "昵称",
)
```

Require the platform mapping text to name YouTube `author`, 小红书 `用户名称`, B站 `username`, TikTok `用户名` then `昵称`, 淘宝 `用户名称` then `用户名`, and 京东 `用户名`. Require the extension template to forbid unconfirmed aliases and ambiguous `用户身份`, comment IDs, parent IDs, URLs, and IP fields.

- [ ] **Step 2: Run documentation/package tests and verify RED**

Run: `python -m unittest tests.test_skill_package tests.test_skill_reference_coverage tests.test_workflow_docs -v`

Expected: FAIL because current documents still state that usernames and nicknames can never be hashed.

- [ ] **Step 3: Replace the obsolete policy and synchronize bundled files**

Update all listed documents with these exact boundaries:

- account ID is selected first for the whole worksheet;
- display name is selected only when no registered account-ID column exists;
- normalized equal names in the same project/platform produce equal hashes regardless of source header;
- cross-platform, cross-project, and account-ID/display-name hashes differ;
- nickname linkage is weaker and may split renamed users or merge different same-name users;
- raw IDs and raw names remain omitted from standardized and cleaned outputs;
- the process is deterministic and does not call AI.

Run: `python tools/sync_skill_bundle.py`

Expected: prints `Synchronized 13 files into skills\product-user-comment-data-merge-cleaning` and updates only configured bundle files.

- [ ] **Step 4: Run synchronization and package verification**

Run: `python tools/sync_skill_bundle.py --check`

Expected: `Skill bundle scripts and configs are synchronized.`

Run: `python -m unittest tests.test_skill_package tests.test_skill_reference_coverage tests.test_workflow_docs -v`

Expected: all package, reference, metadata, and independent-copy checks PASS.

- [ ] **Step 5: Commit policy and portable Skill updates**

```bash
git add AGENTS.md README.md skills/product-user-comment-data-merge-cleaning tests/test_skill_package.py tests/test_skill_reference_coverage.py tests/test_workflow_docs.py
git commit -m "固化多平台显示名哈希兜底规则"
```

### Task 6: Full Regression and Current B站 Batch Verification

**Files:**
- Verify all tracked implementation files.
- Regenerate: `outputs/2017_ScreenBar/20260716_2017_ScreenBar_B站评论数据_标准化总表.xlsx`
- Regenerate: its `.standardized.summary.json` process summary for user review only.

- [ ] **Step 1: Run syntax, bundle, and complete regression checks**

Run: `python -m compileall -q tools skills/product-user-comment-data-merge-cleaning/scripts`

Expected: exit code 0.

Run: `python tools/sync_skill_bundle.py --check`

Expected: synchronized message and exit code 0.

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS with no tracebacks; the baseline 111 tests plus the new fallback cases all pass.

- [ ] **Step 2: Verify tracked files and privacy exclusions**

Run:

```bash
git diff --check
git status --short
git grep -n "same-user\|UC-secret-user"
```

Expected: no whitespace errors; only intentional files are tracked; any sample identity strings occur only in tests or design/plan documents, never output, configuration secrets, or production logs. `analysis/` remains untracked and unstaged.

- [ ] **Step 3: Initialize the confirmed ScreenBar project key and regenerate the current standardization**

Run the standardizer against the already generated prefix-cleaned B站 workbook:

```powershell
python tools/standardize_excel_headers.py `
  "outputs/2017_ScreenBar/20260716_2017_ScreenBar_B站评论数据_合并总表_回复前缀已清理.xlsx" `
  --platform "B站" `
  --project-name "ScreenBar十周年专案" `
  --initialize-project `
  --output "outputs/2017_ScreenBar/20260716_2017_ScreenBar_B站评论数据_标准化总表.xlsx"
```

If the project already exists, rerun the same command without `--initialize-project`. Expected: 123 data rows are written, the standard output has nine columns, and the project key stays in the DPAPI-protected local project store rather than the repository or output directory.

- [ ] **Step 4: Verify aggregates without printing usernames or hashes**

Use a local verification command that reports only:

- data row count;
- non-empty `哈希ID` count;
- count of distinct non-empty hashes;
- number of raw distinct usernames in the prefix-cleaned source;
- whether every repeated normalized username maps to exactly one hash;
- whether the original 11 CSV files and merged workbook remain unchanged.

Expected: 123 rows remain; every non-empty normalized username has a 64-character lowercase hash; repeated identical usernames never map to multiple hashes; no raw username appears in the standardized workbook or summary.

- [ ] **Step 5: Commit implementation completion and publish the feature branch**

```bash
git status --short
git push -u origin codex/display-name-hash-fallback
```

Expected: the branch pushes successfully with implementation and Skill updates; `analysis/` and generated output files remain outside the commit. Return the regenerated standardized workbook to the user for confirmation before any KOL-word cleaning step.

## Self-Review

- Spec coverage: Tasks 1-3 implement ordered platform mappings, whole-sheet account-ID priority, exact-name determinism, source-header independence, type/project/platform isolation, summary redaction, and explicit failures. Task 4 proves cleaning preservation. Task 5 removes conflicting policy text and synchronizes the portable Skill. Task 6 covers DPAPI-backed real-batch verification and Git publication.
- Placeholder scan: the plan contains no unresolved implementation markers or unspecified error-handling steps.
- Type consistency: `display_name_headers`, `identity_type`, `select_identity_header`, `hash_display_name`, and `hash_selected_identity` use the same names in configuration, production code, tests, summaries, and documentation.
- Compatibility: `hash_user_id()` retains its five-part historical message, protected by the fixed expected vector `72bd4fc68258026ac244e1cfbb758e603455defca92af91c577ed9f9b23082c9`.
- Privacy: no step stores raw names, raw IDs, project keys, or row-level mappings outside source inputs; all verification reports aggregates only.
- Scope control: the plan does not add AI classification, infer cross-platform identity, alter comment cleaning rules, or stage the local `analysis/` directory.
