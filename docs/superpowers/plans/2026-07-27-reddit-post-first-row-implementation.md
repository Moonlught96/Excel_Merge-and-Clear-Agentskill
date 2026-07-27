# Reddit 主帖首行导出 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 JSON + 页面全文 Reddit 重建结果以一条主帖记录开头，随后输出不重复主帖字段的评论记录，并包含页面点赞数和全部后代回复数。

**Architecture:** `tools/reddit_json_text_merge.py` 保持 JSON/页面严格匹配与折叠 AutoModerator 排除，在保留评论集合上计算每条评论的全部后代数，并构造一条主帖行加 N 条评论行。通用 XLSX/CSV 写入器保持不变，只接收新的 JSON 路径表头；测试覆盖行契约、后代统计、折叠排除以及两种文件输出。

**Tech Stack:** Python 3、dataclasses、unittest、openpyxl、csv、现有确定性 Reddit JSON/页面文本解析器。

## Global Constraints

- 仅修改 JSON + 页面全文重建路径；`OUTPUT_HEADERS` 和免费 CSV + HTML 路径不改动。
- 所有数据处理必须是确定性的；不得使用 AI、网络访问、模糊匹配或推断。
- 主帖时间与点赞数、评论点赞数只能从已严格解析的页面全文获取；不得使用 `upvote_ratio` 代替点赞数。
- 主帖评论数必须是实际保留并导出的评论行数；页面原始评论数仍必须与 JSON 的 `post.num_comments` 精确相等。
- 评论“评论/回复数”必须是保留 JSON 父子图中全部后代数量，不包括自身。
- 页面没有数值点赞时保持空字符串，绝不改写成 `0`。
- 保留现有的输出路径安全、原子写入、公式文本保护、严格整数范围和 CLI 隐私行为。

---

## File structure

- Modify: `tools/reddit_json_text_merge.py` — JSON + 页面行表头、主帖首行构造、全部后代回复统计。
- Modify: `tests/test_reddit_json_text_merge.py` — 新行数据契约、深层后代、折叠排除和空评论的单元测试。
- Modify: `tests/test_reconstruct_reddit_comments.py` — XLSX/CSV 的 JSON 路径表头、数值列、主帖首行和端到端 CLI 断言。
- Add: `docs/superpowers/specs/2026-07-27-reddit-post-first-row-design.md` — 已提交的用户批准规格；实现时只按它执行。

### Task 1: 构造主帖首行并计算全部后代回复数

**Files:**

- Modify: `tools/reddit_json_text_merge.py`
- Test: `tests/test_reddit_json_text_merge.py`

**Interfaces:**

- Consumes: `RedditJsonExport`、`RedditPageText`、`_retained_comments(export, page)` 和每条 `PageCommentMetric.score`。
- Produces: `JSON_TEXT_OUTPUT_HEADERS: tuple[str, ...]`，顺序固定为 `记录类型`、`标题`、`作者`、`时间`、`内容`、`点赞数`、`评论/回复数`、`层级`、`是否回复`、`评论ID`、`父ID`。
- Produces: `_all_descendant_counts(comments: tuple[RedditJsonComment, ...]) -> dict[str, int]`，只统计传入的保留评论图。
- Produces: `reconstruct_json_text_rows(...) -> list[dict[str, str | int]]`，其第一行总是主帖，后续行按保留 JSON 评论顺序。

- [ ] **Step 1: 写入失败的行契约和后代统计测试**

在 `tests/test_reddit_json_text_merge.py` 中把基础 fixture 改为元数据与评论数一致的值，并新增一个有根评论、子评论、孙评论和第二个根评论的 fixture。先断言目标数据契约：

```python
def test_emits_post_first_then_comments_without_repeating_post_fields(self) -> None:
    export, page = self.fixture()

    rows = reconstruct_json_text_rows(export, page)

    self.assertEqual(
        (
            "记录类型", "标题", "作者", "时间", "内容", "点赞数",
            "评论/回复数", "层级", "是否回复", "评论ID", "父ID",
        ),
        JSON_TEXT_OUTPUT_HEADERS,
    )
    self.assertEqual(["主帖", "评论", "评论"], [row["记录类型"] for row in rows])
    self.assertEqual("Title", rows[0]["标题"])
    self.assertEqual("", rows[1]["标题"])
    self.assertEqual(2, rows[0]["评论/回复数"])
    self.assertEqual("p1", rows[0]["评论ID"])
    self.assertEqual("", rows[0]["父ID"])


def test_counts_all_descendants_for_each_retained_comment(self) -> None:
    export, page = self.nested_fixture()

    rows = reconstruct_json_text_rows(export, page)

    comments = rows[1:]
    self.assertEqual([2, 1, 0, 0], [row["评论/回复数"] for row in comments])
```

同时增加空评论 JSON 路径测试，断言结果仍只有一条主帖行且其 `评论/回复数` 为数值 `0`；增加折叠 AutoModerator 测试，断言主帖评论数和被保留根评论的全部后代数都不计入被排除项。

- [ ] **Step 2: 运行测试确认 RED**

运行：

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_json_text_merge -v
```

预期：失败，原因是现有表头仍是旧英文宽表、没有主帖首行，并且没有全部后代回复数。

- [ ] **Step 3: 实现固定表头、后代统计和主帖首行**

在 `tools/reddit_json_text_merge.py` 中把 JSON 路径表头替换为规格中的 11 列。保留现有的页面原始评论数校验、`_retained_comments` 防御性验证和页面指标长度校验。

实现只基于保留评论构建的后代统计。例如先建 `by_id`，再从每个保留评论向上遍历其父评论，给每一个保留祖先加一：

```python
def _all_descendant_counts(
    comments: tuple[RedditJsonComment, ...],
) -> dict[str, int]:
    by_id = {comment.id: comment for comment in comments}
    counts = {comment.id: 0 for comment in comments}
    for descendant in comments:
        parent_id = descendant.parent_id
        while parent_id in by_id:
            counts[parent_id] += 1
            parent_id = by_id[parent_id].parent_id
    return counts
```

在 `reconstruct_json_text_rows` 中先追加主帖行：

```python
rows = [{
    "记录类型": "主帖",
    "标题": export.post.title,
    "作者": export.post.author,
    "时间": page.post_time,
    "内容": export.post.content,
    "点赞数": page.post_score,
    "评论/回复数": len(retained_comments),
    "层级": 0,
    "是否回复": "否",
    "评论ID": export.post.id,
    "父ID": "",
}]
```

随后为每一条 `zip(retained_comments, page.comments, strict=True)` 的评论追加一行：`记录类型` 为 `评论`、`标题` 为空、`点赞数` 为页面评分（无数字时空字符串）、`评论/回复数` 为统计值、`是否回复` 沿用深度为 0 时 `否` 的严格规则。

- [ ] **Step 4: 运行合并器测试确认 GREEN**

运行：

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_json_text_merge -v
```

预期：全部通过；新测试证明首行是主帖、评论顺序不变、所有后代回复数正确、折叠系统横幅不参与统计。

- [ ] **Step 5: 提交 Task 1**

```powershell
git add -- tools/reddit_json_text_merge.py tests/test_reddit_json_text_merge.py
git commit -m "feat: emit Reddit post as first row"
```

### Task 2: 验证 JSON 路径的 XLSX、CSV 和 CLI 输出

**Files:**

- Modify: `tests/test_reconstruct_reddit_comments.py`
- Test: `tests/test_reconstruct_reddit_comments.py`

**Interfaces:**

- Consumes: `JSON_TEXT_OUTPUT_HEADERS` 和 `reconstruct_json_text_rows` 返回的统一行。
- Produces: 对 `write_outputs(..., headers=JSON_TEXT_OUTPUT_HEADERS)` 和 JSON + `--page-text` CLI 路径的回归覆盖。
- Does not modify: 通用 `write_outputs`、免费 CSV + HTML 路径的 `OUTPUT_HEADERS` 或 CLI 参数表面。

- [ ] **Step 1: 写入失败的文件与 CLI 回归测试**

更新 JSON 路径样例行以使用新表头。新增一个端到端 JSON + 页面文本 fixture，包含一条根评论、一条子评论和一条孙评论，断言 XLSX 和 CSV 都满足：

```python
self.assertEqual(list(JSON_TEXT_OUTPUT_HEADERS), xlsx_rows[0])
self.assertEqual(list(JSON_TEXT_OUTPUT_HEADERS), csv_rows[0])
self.assertEqual("主帖", xlsx_rows[1][0])
self.assertEqual("评论", xlsx_rows[2][0])
self.assertEqual([3, 2, 1, 0], [
    row[JSON_TEXT_OUTPUT_HEADERS.index("评论/回复数")]
    for row in xlsx_rows[1:]
])
```

断言主帖正文以字符串类型写入、评论点赞数为整数、无数值点赞的评论单元格为空，并且 CSV 的行值与 XLSX 行值完全一致。保持已有 CLI stdout/stderr 隐私断言，不在诊断中加入帖子或评论文本、作者或 ID。

- [ ] **Step 2: 运行测试确认 RED**

运行：

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reconstruct_reddit_comments -v
```

预期：失败，原因是旧 JSON 路径表头和列索引仍被测试样例使用。

- [ ] **Step 3: 仅调整受新契约影响的测试和写入断言**

确认 `write_outputs` 已按传入的 `headers` 顺序通用写入后，不修改其生产逻辑。更新 JSON 路径相关的测试行字典、整数边界列列表、公式文本列断言和空点赞列断言，以新中文表头和列位置为准。不得改变 `OUTPUT_HEADERS` 的现有免费 CSV + HTML 测试。

- [ ] **Step 4: 运行 JSON 路径与全套测试确认 GREEN**

运行：

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reconstruct_reddit_comments -v
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -v
```

预期：两条命令全部通过，且免费 CSV + HTML 路径未回归。

- [ ] **Step 5: 提交 Task 2**

```powershell
git add -- tests/test_reconstruct_reddit_comments.py
git commit -m "test: cover Reddit post-first file output"
```

### Task 3: 使用真实输入重新生成并核对交付文件

**Files:**

- Input (read-only): `C:\Users\Eddie.J.Lu\Downloads\Reddit-desksetup-1v3t6z2 (1).json`
- Input (read-only): 当前会话已提供的页面全文文本文件
- Output: 新的、未覆盖的 `.xlsx` 和 `.csv` 文件

**Interfaces:**

- Consumes: 已验证通过的 `tools/reconstruct_reddit_comments.py` JSON + `--page-text` 路径。
- Produces: 表头、主帖首行、评论行数和所有后代回复数均已验证的用户交付文件。

- [ ] **Step 1: 先验证输入与目标输出路径**

计算输入文件 SHA-256，确认原始 JSON 和页面全文未变化。选择一个与旧结果不同的显式 `.xlsx` 和 `.csv` 目标路径；若目标已存在，不传 `--overwrite`，而是先停止并请求用户确认新的路径。

- [ ] **Step 2: 运行重建 CLI**

以用户的 JSON、页面全文和明确的新输出路径调用 CLI。不得向 stdout、stderr 或最终摘要复制帖子、评论、作者或 ID 的原始内容。

- [ ] **Step 3: 使用表格工具核对产物**

用已配置的表格工具读取 XLSX 和 CSV，核对：

1. 两者表头均为 `JSON_TEXT_OUTPUT_HEADERS`；
2. 两者第一条数据行均为 `主帖`；
3. 两者评论行数相同，且主帖 `评论/回复数` 等于该评论行数；
4. 每条评论的 `评论/回复数` 是非负整数；
5. XLSX 与 CSV 的所有行顺序一致。

只在最终报告中提供输出文件路径、行数和核对结果，不暴露评论或作者内容。

- [ ] **Step 4: 提交 Task 3 代码相关变更（如有）并记录验证**

Task 3 不应产生生产代码变更。若仅生成本地交付文件和忽略的测试产物，不提交它们；在最终交付中报告验证命令和实际行数。

## Plan self-review

- 规格覆盖：Task 1 覆盖统一 11 列、主帖首行、页面评分和全部后代统计；Task 2 覆盖 XLSX/CSV/CLI 行契约与安全回归；Task 3 覆盖真实输入交付验证。
- 占位符扫描：没有未完成标记、含糊的处理要求或跨任务省略指令。
- 类型一致性：所有任务使用 `list[dict[str, str | int]]`、`JSON_TEXT_OUTPUT_HEADERS` 和 `_all_descendant_counts` 的同一字段名与顺序。
