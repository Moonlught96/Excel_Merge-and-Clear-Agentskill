# Reddit Reconstruction Module Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Make the Reddit JSON-plus-page-text reconstruction tool a self-contained top-level module with no dependency on the generic comment-cleaning Skill, then push its source-only branch to the existing GitHub remote.

**Architecture:** reddit_reconstruction/ becomes the primary runtime package. It owns its parser, merger, CLI, output-safety helper, tests, requirements, and README. Existing tools/reddit_*.py paths become thin compatibility wrappers, so current callers still work while the package itself imports neither tools.* nor skills.*.

**Tech Stack:** Python 3.11+, standard library, openpyxl>=3.1,<4, unittest, Git.

## Global Constraints

- JSON governs comment rows, order, authors, dates, content, IDs, hierarchy, and all-descendant reply counts.
- Page text supplements only post time/score/reported count and uniquely matched comment scores.
- Unknown, unavailable, ambiguous, and unmatched comment scores remain blank, never 0.
- The output contract remains 11 columns and a post-first data row.
- The package must not import tools.*, skills.*, cleaner configuration, hash-ID code, AI libraries, web clients, or browser automation.
- Do not stage raw JSON/TXT, generated XLSX/CSV, previews, scratch files, generic Skill files, or unrelated changes.
- Push only codex/reddit-data-reconstruction to origin; do not open a PR while gh is unavailable.

---

### Task 1: Build the package-local runtime and compatibility wrappers

**Files:**
- Create: reddit_reconstruction/__init__.py
- Create: reddit_reconstruction/__main__.py
- Create: reddit_reconstruction/cli.py
- Create: reddit_reconstruction/json_export.py
- Create: reddit_reconstruction/page_text.py
- Create: reddit_reconstruction/merge.py
- Create: reddit_reconstruction/output_safety.py
- Create: reddit_reconstruction/tests/test_isolation.py
- Modify: tools/reconstruct_reddit_comments.py
- Modify: tools/reddit_json_export.py
- Modify: tools/reddit_page_text.py
- Modify: tools/reddit_json_text_merge.py

**Interfaces:**
- Consumes: current Reddit-only source files and tools/output_path_safety.py.
- Produces: python -m reddit_reconstruction and package-local parse_reddit_json, parse_reddit_page_metrics, match_json_primary_page_scores, reconstruct_json_primary_page_rows, and main.

- [ ] **Step 1: Write the failing isolation test**

~~~python
class RedditPackageIsolationTests(unittest.TestCase):
    def test_primary_package_has_no_tools_or_skills_imports(self) -> None:
        source_root = Path(reddit_reconstruction.__file__).parent
        source = "\n".join(
            item.read_text(encoding="utf-8")
            for item in source_root.glob("*.py")
        )
        self.assertNotIn("from tools.", source)
        self.assertNotIn("import tools.", source)
        self.assertNotIn("from skills.", source)
        self.assertNotIn("import skills.", source)
~~~

- [ ] **Step 2: Verify RED**

Run:

~~~powershell
& '<bundled-python>' -m unittest reddit_reconstruction.tests.test_isolation.RedditPackageIsolationTests.test_primary_package_has_no_tools_or_skills_imports -v
~~~

Expected: import failure because reddit_reconstruction does not yet exist.

- [ ] **Step 3: Copy production logic into package-local files**

Use only these relative imports:

~~~python
# page_text.py
from .json_export import RedditJsonComment, RedditJsonExport

# merge.py
from .json_export import RedditJsonComment, RedditJsonExport
from .page_text import PageMetricCandidate, RedditPageMetricSnapshot

# cli.py
from .json_export import RedditJsonError, parse_reddit_json
from .merge import JSON_TEXT_OUTPUT_HEADERS, match_json_primary_page_scores
from .merge import reconstruct_json_primary_page_rows, reconstruct_json_text_rows
from .output_safety import ensure_output_paths_safe
from .page_text import RedditPageTextError, parse_reddit_page_metrics, parse_reddit_page_text
~~~

Copy tools/output_path_safety.py into reddit_reconstruction/output_safety.py. In __main__.py write:

~~~python
from .cli import main

raise SystemExit(main())
~~~

- [ ] **Step 4: Convert old tool files to compatibility wrappers**

~~~python
# tools/reddit_json_export.py
from reddit_reconstruction.json_export import *  # noqa: F401,F403

# tools/reconstruct_reddit_comments.py
from reddit_reconstruction.cli import *  # noqa: F401,F403

if __name__ == "__main__":
    raise SystemExit(main())
~~~

Create equivalent import-only wrappers for reddit_page_text.py and reddit_json_text_merge.py.

- [ ] **Step 5: Verify GREEN and compatibility**

Run:

~~~powershell
& '<bundled-python>' -m unittest reddit_reconstruction.tests.test_isolation tests.test_reddit_json_export tests.test_reddit_page_text tests.test_reddit_json_text_merge -v
~~~

Expected: all pass, package source contains no generic-flow imports, and old tools.* paths remain compatible.

- [ ] **Step 6: Commit the runtime scope**

~~~powershell
git add -- reddit_reconstruction tools/reconstruct_reddit_comments.py tools/reddit_json_export.py tools/reddit_page_text.py tools/reddit_json_text_merge.py
git commit -m "feat: isolate Reddit reconstruction module"
~~~

### Task 2: Add portable tests and no-AI documentation

**Files:**
- Create: reddit_reconstruction/tests/__init__.py
- Create: reddit_reconstruction/tests/test_json_export.py
- Create: reddit_reconstruction/tests/test_page_text.py
- Create: reddit_reconstruction/tests/test_merge.py
- Create: reddit_reconstruction/tests/test_cli.py
- Create: reddit_reconstruction/requirements.txt
- Create: reddit_reconstruction/README.md
- Create: reddit_reconstruction/.gitignore

**Interfaces:**
- Consumes: the Task 1 package.
- Produces: a runnable test suite and instructions with no reference to the generic cleaning workflow.

- [ ] **Step 1: Write the failing package CLI test**

~~~python
completed = subprocess.run(
    [
        sys.executable, "-m", "reddit_reconstruction",
        "--json", str(json_path),
        "--page-text", str(page_text_path),
        "--output-xlsx", str(output_xlsx),
        "--output-csv", str(output_csv),
        "--json-primary-page-metrics",
    ],
    cwd=repo_root,
    capture_output=True,
    text=True,
    check=False,
)
self.assertEqual(0, completed.returncode, completed.stderr)
~~~

Assert the paired files exist, one post row precedes every JSON comment, and an unmatched comment score is the empty string.

- [ ] **Step 2: Verify RED**

Run:

~~~powershell
& '<bundled-python>' -m unittest reddit_reconstruction.tests.test_cli -v
~~~

Expected: test-file import failure before it is created.

- [ ] **Step 3: Port deterministic coverage only**

Create package-local tests for the exact behaviors below:

~~~python
self.assertEqual("", parse_reddit_json(media_post_path).post.content)
self.assertEqual("", row_for_unmatched_comment["点赞数"])
self.assertEqual(expected_descendant_count, row_for_parent["评论/回复数"])
self.assertEqual(expected_comment_ids, [row["评论ID"] for row in comment_rows])
~~~

Do not port Free-CSV or saved-HTML test helpers because they are outside this module.

- [ ] **Step 4: Add package-local instructions and ignores**

requirements.txt contains exactly:

~~~text
openpyxl>=3.1,<4
~~~

README.md must state the 11 columns, JSON-primary source-of-truth rule, unique-body-only score mapping, blank-not-zero rule, no-AI rule, reported-versus-collected count gap, and this test command:

~~~powershell
& '<bundled-python>' -m unittest discover -s reddit_reconstruction/tests -p 'test_*.py' -v
~~~

.gitignore contains:

~~~text
__pycache__/
.tmp-tests/
outputs/
*.xlsx
*.csv
~~~

- [ ] **Step 5: Verify package portability**

Run:

~~~powershell
& '<bundled-python>' -m unittest discover -s reddit_reconstruction/tests -p 'test_*.py' -v
~~~

Copy only reddit_reconstruction/ to a temporary directory, run the controlled CLI fixture with that copy on PYTHONPATH, and confirm it imports no root tools/ or skills/ files.

- [ ] **Step 6: Commit tests and documentation**

~~~powershell
git add -- reddit_reconstruction
git commit -m "test: document isolated Reddit module"
~~~

### Task 3: Verify boundaries, commit remaining Reddit work, and push source only

**Files:**
- Modify: README.md only if one discovery link is useful.
- Modify: existing Reddit test files only when wrapper compatibility requires it.
- Exclude: all outputs/, user JSON/TXT, previews, and generic Skill files.

**Interfaces:**
- Consumes: green package and compatibility suites.
- Produces: a reviewed source-only commit and a pushed branch at origin/codex/reddit-data-reconstruction.

- [ ] **Step 1: Add and verify a boundary test**

~~~python
for source_path in Path(reddit_reconstruction.__file__).parent.glob("*.py"):
    source = source_path.read_text(encoding="utf-8")
    self.assertNotIn("product-user-comment-data-merge-cleaning", source)
    self.assertNotIn("clean_excel_comments", source)
    self.assertNotIn("standardize_excel_headers", source)
~~~

Run:

~~~powershell
& '<bundled-python>' -m unittest reddit_reconstruction.tests.test_isolation -v
~~~

- [ ] **Step 2: Run a new ignored JSON-primary sample output**

~~~powershell
& '<bundled-python>' -m reddit_reconstruction --json '<user-json>' --page-text '<page-text>' --output-xlsx 'outputs/reddit-verification/result.xlsx' --output-csv 'outputs/reddit-verification/result.csv' --json-primary-page-metrics
~~~

Verify:

~~~python
assert workbook_rows[0] == JSON_TEXT_OUTPUT_HEADERS
assert workbook_rows[1][0] == "主帖"
assert len(workbook_rows) == 2 + len(source_json["comments"])
assert xlsx_cells == csv_cells
~~~

- [ ] **Step 3: Run full repository tests**

~~~powershell
& '<bundled-python>' -m unittest discover -s tests -p 'test_*.py' -v
~~~

Expected: generic cleaning workflow tests stay green and Git status contains no user data.

- [ ] **Step 4: Review and stage only approved Reddit files**

~~~powershell
git status --short
git diff --check
git diff --stat
git add -- reddit_reconstruction tools/reconstruct_reddit_comments.py tools/reddit_json_export.py tools/reddit_page_text.py tools/reddit_json_text_merge.py tests/test_reconstruct_reddit_comments.py tests/test_reddit_json_export.py tests/test_reddit_json_text_merge.py tests/test_reddit_page_text.py docs/superpowers/specs/2026-07-28-reddit-module-isolation-design.md docs/superpowers/plans/2026-07-28-reddit-module-isolation-implementation.md
git diff --cached --check
git diff --cached --stat
~~~

Do not use git add -A. Keep the already committed design document separate and do not amend it.

- [ ] **Step 5: Commit and push**

~~~powershell
git commit -m "feat: isolate Reddit reconstruction module"
git push -u origin codex/reddit-data-reconstruction
~~~

If GitHub credentials or remote write access fail, stop and report the exact Git error. Do not change the remote URL or retry with guessed credentials. A draft PR is intentionally skipped because gh is unavailable.
