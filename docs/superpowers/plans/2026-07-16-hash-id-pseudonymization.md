# Hash ID Pseudonymization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, project-scoped, platform-isolated `哈希ID` column to the Excel/CSV standardization pipeline without exposing raw user IDs or secrets.

**Architecture:** Keep cryptographic transformation and project-key storage outside the existing header standardizer. A pure `hash_id_pseudonymizer` module owns platform mapping, ID normalization, message encoding, and HMAC-SHA256; a `hash_id_project_store` module owns project metadata and Windows DPAPI key storage. The standardizer receives an explicit project context and platform, selects only configured real user-ID columns, and writes a derived `哈希ID` column while omitting the raw source column.

**Tech Stack:** Python 3 standard library (`hashlib`, `hmac`, `secrets`, `uuid`, `ctypes`, `json`), openpyxl, unittest, Windows DPAPI.

---

## File Map

- Create `tools/hash_id_pseudonymizer.py`: pure configuration models, platform normalization, ID normalization, HMAC message encoding, and hashing.
- Create `tools/hash_id_project_store.py`: project registry, DPAPI protect/unprotect, secure project initialization, and context loading.
- Create `config/hash-id.json`: fixed platform aliases and confirmed real user-ID headers.
- Modify `tools/standardize_excel_headers.py`: add derived-column selection, hashing, safe summary metadata, and CLI arguments.
- Create `tests/test_hash_id_pseudonymizer.py`: deterministic cryptographic and normalization tests.
- Create `tests/test_hash_id_project_store.py`: isolated temporary registry and secret-provider tests.
- Modify `tests/test_standardize_excel_headers.py`: nine-column contract and workbook/CSV integration tests.
- Modify `tests/test_clean_excel_comments.py`: verify `哈希ID` survives row cleaning and CSV export.
- Modify `tests/test_skill_package.py`: require new scripts/config/reference coverage and independent-copy execution.
- Mirror executable files under `skills/bazhuayu-excel-cleaning/scripts/` and `skills/bazhuayu-excel-cleaning/config/`.
- Modify `skills/bazhuayu-excel-cleaning/SKILL.md`, references, assets, `README.md`, and `AGENTS.md`: document project confirmation, privacy boundary, field mappings, and invocation.

### Task 1: Pure Hash ID Transformation

**Files:**
- Create: `tests/test_hash_id_pseudonymizer.py`
- Create: `tools/hash_id_pseudonymizer.py`
- Create: `config/hash-id.json`

- [ ] **Step 1: Write failing tests for platform mapping, ID normalization, and HMAC stability**

```python
class HashIdPseudonymizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_hash_id_config(PROJECT_ROOT / "config" / "hash-id.json")
        self.context = HashProjectContext(
            project_id="11111111-1111-1111-1111-111111111111",
            project_name="ScreenBar十周年专案",
            key_version=1,
            key_fingerprint="test-fingerprint",
            secret_key=bytes.fromhex("11" * 32),
        )

    def test_same_project_platform_and_id_produce_same_hash(self) -> None:
        first = hash_user_id("UC001", "YouTube", self.context, self.config)
        second = hash_user_id("UC001", "youtube", self.context, self.config)
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_platform_and_project_isolation(self) -> None:
        youtube = hash_user_id("00123", "YouTube", self.context, self.config)
        xhs = hash_user_id("00123", "小红书", self.context, self.config)
        other_project = replace(self.context, project_id="22222222-2222-2222-2222-222222222222")
        other = hash_user_id("00123", "YouTube", other_project, self.config)
        self.assertNotEqual(youtube, xhs)
        self.assertNotEqual(youtube, other)

    def test_string_normalization_preserves_leading_zero_and_case(self) -> None:
        self.assertEqual("001AbC", normalize_raw_user_id(" 001AbC "))
        self.assertNotEqual(
            hash_user_id("001AbC", "YouTube", self.context, self.config),
            hash_user_id("001abc", "YouTube", self.context, self.config),
        )

    def test_integer_and_integral_float_share_canonical_form(self) -> None:
        self.assertEqual("123", normalize_raw_user_id(123))
        self.assertEqual("123", normalize_raw_user_id(123.0))

    def test_invalid_id_types_fail_without_echoing_value(self) -> None:
        for value in (True, 12.5, "=A1", "#REF!"):
            with self.assertRaises(InvalidUserIdError) as caught:
                normalize_raw_user_id(value)
            self.assertNotIn(str(value), str(caught.exception))
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_hash_id_pseudonymizer -v`

Expected: FAIL because `tools.hash_id_pseudonymizer` does not exist.

- [ ] **Step 3: Implement the pure API and fixed configuration**

The module must expose these stable interfaces:

```python
@dataclass(frozen=True)
class HashProjectContext:
    project_id: str
    project_name: str
    key_version: int
    key_fingerprint: str
    secret_key: bytes

@dataclass(frozen=True)
class PlatformIdentityConfig:
    namespace: str
    aliases: tuple[str, ...]
    user_id_headers: tuple[str, ...]

def normalize_raw_user_id(value: Any) -> str | None: ...
def normalize_platform(value: str, config: HashIdConfig) -> str: ...
def select_user_id_header(headers: list[Any], platform: str, config: HashIdConfig) -> SelectedIdentityHeader | None: ...
def hash_user_id(value: Any, platform: str, context: HashProjectContext, config: HashIdConfig) -> str | None: ...
```

Use length-prefixed UTF-8 encoding for `bazhuayu-hash-id-v1`, `project_id`, canonical platform namespace, and normalized user ID. Produce `hmac.new(secret_key, message, hashlib.sha256).hexdigest()` without truncation.

`config/hash-id.json` must initially register only verified source fields:

```json
{
  "schema_version": 1,
  "algorithm_version": "bazhuayu-hash-id-v1",
  "platforms": [
    {
      "namespace": "youtube",
      "aliases": ["YouTube", "YouTube Shorts", "youtube", "yt-comments"],
      "user_id_headers": ["author_channel_id", "authorChannelId", "Author Channel ID"]
    },
    {
      "namespace": "xiaohongshu",
      "aliases": ["小红书"],
      "user_id_headers": ["用户ID"]
    },
    {
      "namespace": "bilibili",
      "aliases": ["B站", "哔哩哔哩", "bilibili"],
      "user_id_headers": []
    },
    {
      "namespace": "tiktok",
      "aliases": ["TikTok", "TTCommentExporter"],
      "user_id_headers": []
    },
    {"namespace": "taobao", "aliases": ["淘宝"], "user_id_headers": []},
    {"namespace": "jd", "aliases": ["京东"], "user_id_headers": []}
  ]
}
```

Do not map `用户身份`, `用户名`, `昵称`, `id`, `评论ID`, `rpid`, `parent_rpid`, `reply_to`, or `youtube_comment_id`.

- [ ] **Step 4: Run the unit tests and verify GREEN**

Run: `python -m unittest tests.test_hash_id_pseudonymizer -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit the pure transformation**

```bash
git add config/hash-id.json tools/hash_id_pseudonymizer.py tests/test_hash_id_pseudonymizer.py
git commit -m "实现项目隔离的哈希ID转换"
```

### Task 2: Secure Project Registry and Key Storage

**Files:**
- Create: `tests/test_hash_id_project_store.py`
- Create: `tools/hash_id_project_store.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing tests for initialization, reuse, duplicate protection, and secret redaction**

```python
class HashIdProjectStoreTest(unittest.TestCase):
    def test_initializes_and_reloads_same_project_context(self) -> None:
        store = ProjectStore(self.tmp / "registry", protector=TestProtector())
        created = store.initialize_project("ScreenBar十周年专案")
        loaded = store.load_project(project_name="ScreenBar十周年专案")
        self.assertEqual(created.project_id, loaded.project_id)
        self.assertEqual(created.secret_key, loaded.secret_key)
        self.assertNotIn(created.secret_key.hex(), (self.tmp / "registry").read_text(errors="ignore"))

    def test_new_project_uses_new_key_and_project_id(self) -> None:
        store = ProjectStore(self.tmp / "registry", protector=TestProtector())
        first = store.initialize_project("Project A")
        second = store.initialize_project("Project B")
        self.assertNotEqual(first.project_id, second.project_id)
        self.assertNotEqual(first.secret_key, second.secret_key)

    def test_duplicate_project_name_is_rejected(self) -> None:
        store = ProjectStore(self.tmp / "registry", protector=TestProtector())
        store.initialize_project("Project A")
        with self.assertRaises(ProjectAlreadyExistsError):
            store.initialize_project("Project A")
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_hash_id_project_store -v`

Expected: FAIL because the project store does not exist.

- [ ] **Step 3: Implement project metadata, DPAPI, and explicit non-Windows provider**

Implement:

```python
class SecretProtector(Protocol):
    def protect(self, secret: bytes) -> bytes: ...
    def unprotect(self, protected: bytes) -> bytes: ...

class WindowsDpapiProtector:
    def protect(self, secret: bytes) -> bytes: ...
    def unprotect(self, protected: bytes) -> bytes: ...

class EnvironmentSecretProtector:
    def __init__(self, variable_name: str = "BAZHUAYU_HASH_ID_MASTER_KEY"): ...

class ProjectStore:
    def initialize_project(self, project_name: str) -> HashProjectContext: ...
    def load_project(self, *, project_name: str | None = None, project_id: str | None = None) -> HashProjectContext: ...
```

The default registry root is `%LOCALAPPDATA%/BazhuayuExcelCleaning/hash-id-projects`. Metadata is JSON; the 32-byte project key is stored only as a protected binary blob. Project names must be non-empty after trimming. Errors may name the project and metadata path but never include raw or protected key bytes.

Add local secret patterns to `.gitignore` as defense in depth:

```gitignore
.hash-id-projects/
*.hash-id.key
*.dpapi
```

- [ ] **Step 4: Run project-store tests and verify GREEN**

Run: `python -m unittest tests.test_hash_id_project_store -v`

Expected: all tests PASS, including a Windows-only DPAPI round trip guarded by `@unittest.skipUnless(sys.platform == "win32", ...)`.

- [ ] **Step 5: Commit secure project storage**

```bash
git add .gitignore tools/hash_id_project_store.py tests/test_hash_id_project_store.py
git commit -m "增加哈希ID项目密钥安全存储"
```

### Task 3: Integrate the Derived Column into Standardization

**Files:**
- Modify: `tests/test_standardize_excel_headers.py`
- Modify: `tools/standardize_excel_headers.py`
- Modify: `config/header-standardizer.json`

- [ ] **Step 1: Update the expected schema and write failing YouTube/Xiaohongshu integration tests**

Change the shared expected header to:

```python
EXPECTED_HEADER = [
    "评论日期", "评论内容", "产品名", "哈希ID", "点赞数",
    "子评论数/追评数", "一级评论", "二级评论", "三级评论",
]
```

Add tests that pass a fixed `HashProjectContext` and platform:

```python
def test_hashes_verified_youtube_user_id_without_writing_raw_id(self) -> None:
    sheet.append(["published_at", "text", "author_channel_id", "likes"])
    sheet.append(["2026-07-08T00:00:00Z", "Useful review", "UC001", 4])
    result = standardize_workbook(
        input_path, load_config(), output_dir=output_dir,
        platform="YouTube", hash_context=self.hash_context,
        hash_config=self.hash_config,
    )
    rows = list(load_workbook(result.output_xlsx, read_only=True, data_only=True).active.values)
    self.assertEqual(64, len(rows[1][3]))
    self.assertNotIn("UC001", json.dumps(json.loads(result.summary_json.read_text("utf-8"))))

def test_hashes_verified_xiaohongshu_user_id(self) -> None:
    sheet.append(["评论时间", "评论内容", "用户ID", "点赞数"])
    sheet.append(["2026-07-08", "真实评论内容", "00123", 4])
    # Assert a 64-character hash at index 3 and no raw value in output/summary.

def test_unverified_identity_like_tiktok_user_identity_stays_blank(self) -> None:
    # `用户身份`, username, and profile URL must not be selected.

def test_registered_user_id_requires_project_context_and_platform(self) -> None:
    # A detected `author_channel_id` without context must raise MissingHashContextError.
```

Update every existing row assertion by inserting `None` at index 3; retained data shifts one position right.

- [ ] **Step 2: Run standardizer tests and verify RED**

Run: `python -m unittest tests.test_standardize_excel_headers -v`

Expected: FAIL because the standardizer still emits eight columns and has no hashing parameters.

- [ ] **Step 3: Implement derived-column selection and safe summaries**

Add `哈希ID` after `产品名` in `config/header-standardizer.json` with `required: false` and no direct aliases. Extend the standardizer API:

```python
def standardize_workbook(
    input_path: Path,
    config: HeaderStandardizerConfig,
    output_dir: Path | None = None,
    output_path: Path | None = None,
    today: date | None = None,
    *,
    platform: str | None = None,
    hash_context: HashProjectContext | None = None,
    hash_config: HashIdConfig | None = None,
) -> StandardizeResult:
    ...
```

The sheet processor selects the verified identity header separately from normal header aliases. For each row it hashes only that source cell. The raw identity column remains an omitted source column and never enters the output. Summary fields are limited to project ID/name, key fingerprint, canonical platform, selected source-header name, hash count, blank count, and algorithm version.

- [ ] **Step 4: Run standardizer tests and verify GREEN**

Run: `python -m unittest tests.test_standardize_excel_headers -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit standardizer integration**

```bash
git add config/header-standardizer.json tools/standardize_excel_headers.py tests/test_standardize_excel_headers.py
git commit -m "在标准化表格中生成哈希ID"
```

### Task 4: Add Project Initialization and CLI Wiring

**Files:**
- Modify: `tests/test_standardize_excel_headers.py`
- Modify: `tools/standardize_excel_headers.py`

- [ ] **Step 1: Write failing CLI tests**

Use patched argument arrays and a temporary `ProjectStore` to verify:

```python
def test_cli_initializes_confirmed_project_and_standardizes(self) -> None:
    exit_code = main([
        str(input_path), "--platform", "YouTube",
        "--project-name", "ScreenBar十周年专案", "--initialize-project",
        "--project-store", str(project_store_path), "--output", str(output_path),
    ])
    self.assertEqual(0, exit_code)
    self.assertTrue(output_path.exists())

def test_cli_reuses_existing_project_without_initialize_flag(self) -> None:
    # Initialize once, then invoke again and assert identical hash IDs.
```

- [ ] **Step 2: Run CLI tests and verify RED**

Run: `python -m unittest tests.test_standardize_excel_headers.StandardizeExcelHeadersCliTest -v`

Expected: FAIL because the CLI does not accept project or platform arguments.

- [ ] **Step 3: Add explicit CLI arguments and safe output**

Add:

```text
--platform <confirmed-source>
--project-name <confirmed-project>
--project-id <uuid>
--initialize-project
--project-store <optional-local-registry-for-testing-or-admin>
--hash-config <path>
```

`--project-name` and `--project-id` are mutually exclusive. `--initialize-project` requires `--project-name`. CLI output may print project name, project ID, key fingerprint, platform namespace, and file paths, but never raw IDs or key data.

- [ ] **Step 4: Run CLI and standardizer suites**

Run: `python -m unittest tests.test_hash_id_pseudonymizer tests.test_hash_id_project_store tests.test_standardize_excel_headers -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit CLI integration**

```bash
git add tools/standardize_excel_headers.py tests/test_standardize_excel_headers.py
git commit -m "接入哈希ID项目确认与命令入口"
```

### Task 5: Preserve Hash IDs Through Cleaning and Portable Skill Copy

**Files:**
- Modify: `tests/test_clean_excel_comments.py`
- Modify: `tests/test_skill_package.py`
- Create: `skills/bazhuayu-excel-cleaning/scripts/hash_id_pseudonymizer.py`
- Create: `skills/bazhuayu-excel-cleaning/scripts/hash_id_project_store.py`
- Create: `skills/bazhuayu-excel-cleaning/config/hash-id.json`
- Modify: `skills/bazhuayu-excel-cleaning/scripts/standardize_excel_headers.py`
- Modify: `skills/bazhuayu-excel-cleaning/config/header-standardizer.json`

- [ ] **Step 1: Write failing cleaning and package tests**

```python
def test_cleaning_preserves_hash_id_in_xlsx_and_csv(self) -> None:
    sheet.append(EXPECTED_HEADER)
    sheet.append(["2026-07-08", "这是一条足够长的有效评论", None, "a" * 64, 2, 0, None, None, None])
    result = clean_workbook(...)
    self.assertEqual("a" * 64, load_workbook(result.output_xlsx).active["D2"].value)
    self.assertIn("a" * 64, result.output_csv.read_text(encoding="utf-8-sig"))
```

Extend package requirements with both new scripts and `hash-id.json`. The copied Skill test must initialize a temporary project, standardize a YouTube workbook containing `author_channel_id`, and assert a 64-character hash without importing any project-root module.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_clean_excel_comments tests.test_skill_package -v`

Expected: FAIL because the portable Skill is missing the new files and schema.

- [ ] **Step 3: Mirror production files into the Skill package**

Copy the finalized modules and configs byte-for-byte into the Skill package. Update relative imports so `scripts/standardize_excel_headers.py` can import sibling scripts both when copied independently and when run from the repository.

- [ ] **Step 4: Run cleaning and package tests and verify GREEN**

Run: `python -m unittest tests.test_clean_excel_comments tests.test_skill_package -v`

Expected: all tests PASS, including independent-copy execution.

- [ ] **Step 5: Commit portable package behavior**

```bash
git add tests/test_clean_excel_comments.py tests/test_skill_package.py skills/bazhuayu-excel-cleaning
git commit -m "同步可移植哈希ID标准化工具"
```

### Task 6: Update Workflow, Privacy References, and Confirmation Assets

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `skills/bazhuayu-excel-cleaning/SKILL.md`
- Modify: `skills/bazhuayu-excel-cleaning/references/workflow.md`
- Modify: `skills/bazhuayu-excel-cleaning/references/data-contract.md`
- Modify: `skills/bazhuayu-excel-cleaning/references/header-standardization.md`
- Modify: `skills/bazhuayu-excel-cleaning/references/tool-reference.md`
- Modify: `skills/bazhuayu-excel-cleaning/references/extension-policy.md`
- Modify: `skills/bazhuayu-excel-cleaning/assets/workflow-confirmation-template.md`
- Modify: `skills/bazhuayu-excel-cleaning/assets/rule-extension-template.md`
- Modify: `tests/test_skill_package.py`

- [ ] **Step 1: Add failing documentation coverage assertions**

Require the package references to contain:

```python
required_hash_rules = (
    "`哈希ID`",
    "HMAC-SHA256",
    "same project and platform",
    "project-specific key",
    "raw user ID",
    "用户名、昵称、评论 ID",
    "Windows DPAPI",
    "新项目",
)
```

Also require the confirmation template to include `项目名称：{{PROJECT_NAME}}` and a statement that a new project must be declared explicitly.

- [ ] **Step 2: Run package tests and verify RED**

Run: `python -m unittest tests.test_skill_package -v`

Expected: FAIL because the references do not yet contain the new contract.

- [ ] **Step 3: Update all project and Skill documentation**

Document the nine-column schema, one-time project confirmation, new-project declaration, platform isolation, verified initial mappings, empty-column behavior, DPAPI storage, no raw-ID logging, and deterministic-tool-only boundary. Replace old statements that all IDs are unconditionally dropped with the precise rule: verified user IDs are transformed to `哈希ID`; comment IDs, parent IDs, usernames, nicknames, IPs, and unverified identity fields are dropped.

The workflow confirmation template must show project, product, source, and output names in one confirmation. The extension template must require evidence that a new alias is a true platform user ID before adding it.

- [ ] **Step 4: Run package tests and verify GREEN**

Run: `python -m unittest tests.test_skill_package -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit documentation and policy updates**

```bash
git add AGENTS.md README.md skills/bazhuayu-excel-cleaning tests/test_skill_package.py
git commit -m "固化哈希ID隐私与项目确认规则"
```

### Task 7: Full Verification, Secret Scan, and GitHub Publication

**Files:**
- Verify all changed files; no new production behavior is introduced in this task.

- [ ] **Step 1: Run the complete test suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS with no unexpected warnings or tracebacks.

- [ ] **Step 2: Run syntax compilation for project and Skill scripts**

Run: `python -m compileall -q tools skills/bazhuayu-excel-cleaning/scripts`

Expected: exit code 0.

- [ ] **Step 3: Verify source samples without exposing values**

Run the standardizer against temporary copies of representative YouTube and Xiaohongshu inputs with a temporary test project. Verify only aggregate properties:

- output has nine columns in the fixed order;
- non-empty source user IDs produce 64-character lowercase hashes;
- raw user IDs do not occur in output or summary bytes;
- B站, TikTok, 淘宝, 京东, and YouTube Shorts samples without confirmed user IDs contain a blank `哈希ID` column;
- source-file hashes before and after are identical.

Delete the temporary outputs and temporary test project registry after verification.

- [ ] **Step 4: Scan tracked content for secret leakage and excluded commits**

Run:

```bash
git grep -n "BAZHUAYU_HASH_ID_MASTER_KEY="
git branch --contains 0f778c9
git branch --contains 61d73e2
git status --short
```

Expected: no committed secret value, neither excluded ScreenBar design/plan commit is reachable from a local branch, and the worktree is clean.

- [ ] **Step 5: Push the feature branch to GitHub**

Run: `git push -u origin codex/hash-id-pseudonymization`

Expected: push succeeds. The branch contains the hash-ID design and implementation but not the two excluded ScreenBar dashboard design/plan commits.

## Self-Review

- Spec coverage: tasks cover project identity, secure key storage, platform isolation, verified ID mapping, nine-column output, summary redaction, CLI workflow, cleaning preservation, portable Skill packaging, documentation, sample verification, and Git publication.
- Placeholder scan: no TBD/TODO or unspecified “appropriate handling” steps remain.
- Type consistency: `HashProjectContext`, `HashIdConfig`, `ProjectStore`, `hash_user_id`, `platform`, and `hash_context` use the same names across tasks.
- Scope control: the plan does not modify ScreenBar dashboard analysis or its local artifact files.
