from __future__ import annotations

import unittest
from pathlib import Path


class WorkflowDocsTest(unittest.TestCase):
    def test_skill_records_validated_multi_file_workflow(self) -> None:
        skill = Path("skills/bazhuayu-excel-cleaning/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("## Validated Multi-File Workflow", skill)
        self.assertIn("Confirm product name and data source once before merging.", skill)
        self.assertIn("Use `YYYYMMDD_产品名_数据来源_步骤名` for all main workbook filenames.", skill)
        self.assertIn("Step names are `合并总表`, `标准化总表`, and `清洗后总表`.", skill)
        self.assertIn("After product name and data source are confirmed once, do not ask again for later step filenames.", skill)
        self.assertIn(
            "Ask `请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。` before running merge.",
            skill,
        )
        self.assertIn(
            "If only one workbook is provided, ask `当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。`",
            skill,
        )
        self.assertIn("Do not skip merge on a single workbook until the user confirms it is the only intended file.", skill)
        self.assertIn("Do not standardize individual source workbooks before merging same-platform batches.", skill)
        self.assertIn("Merge the original provided workbook files into a raw merged workbook.", skill)
        self.assertIn("Ask `是否已经提供并合并完所有需要合并的表格？你确认后我再进行标准化。`", skill)
        self.assertIn("Standardize the reply-prefix-stripped merged workbook into a separate standardized merged workbook.", skill)
        self.assertIn("Return the standardized merged workbook and wait for the user to confirm it before cleaning.", skill)
        self.assertIn("Clean only after standardized-workbook confirmation and KOL clean-word completion confirmation.", skill)
        self.assertIn("`评论日期`: `评论日期`, `评论时间`, `评论日期与产品`, `timestamp`", skill)
        self.assertIn("`评论内容`: `评论内容`, `content`", skill)
        self.assertIn("`产品名`: `产品名`, `购买产品`, `商品名称`, `商品`, `评论日期与产品`", skill)
        self.assertIn("`点赞数`: `点赞数`, `点赞量`", skill)
        self.assertIn("`点赞数`: `点赞数`, `点赞量`, `like_count`", skill)
        self.assertIn(
            "`子评论数/追评数`: `子评论数/追评数`, `子评论数`, `子评论数（追评数）`, `追评数`, `评论数`",
            skill,
        )
        self.assertIn("`一级评论`: `一级评论`, `一级评论内容`, `追评`", skill)
        self.assertIn("`rpid`, `parent_rpid`, `username`, `ip_location`", skill)
        self.assertIn("`parent_rpid` is a parent-comment ID, not a subcomment count.", skill)
        self.assertIn("`子评论数/追评数` is a required standard output column, but the source header may be missing.", skill)
        self.assertIn("Missing source headers for `子评论数/追评数` keep that standard output column blank instead of failing.", skill)
        self.assertIn(
            "When the source header is `timestamp`, `createTime`, `create_time`, `createdAt`, `created_at`, `publishedAt`, `published_at`, `publishedTime`, `published_time`, `date`, `Date`, `time`, `Time`, or another configured English platform time alias",
            skill,
        )
        self.assertIn("Keep only year, month, and day; do not output hours, minutes, or seconds.", skill)
        self.assertIn("TikTok aliases such as `createTime`, `text`, `diggCount`, and `replyCommentTotal`", skill)
        self.assertIn("YouTube aliases such as `publishedAt`, `commentText`, `likeCount`, `replyCount`, and `replyText`", skill)
        self.assertIn("Relative platform time values such as `1年前`, `9个月前`, `1 year ago`, and `9 months ago` are converted deterministically from the current Beijing date.", skill)
        self.assertIn("Relative year values output only `YYYY`; relative month values output only `YYYY-MM`.", skill)
        self.assertIn("The leading `YYYY年M月D日`, `YYYY/M/D`, or `YYYY-M-D` text becomes `评论日期`.", skill)
        self.assertIn("Headers can be reordered into the approved eight-column schema.", skill)
        self.assertIn("clear only the earlier duplicate subcomment cell", skill)
        self.assertIn("Clear `一级评论`, `二级评论`, and `三级评论` cells whose trimmed length is less than or equal to 5 characters.", skill)
        self.assertIn("must not delete the row and must not modify the main `评论内容` column", skill)
        self.assertIn("uses exact text matching only", skill)
        self.assertIn("Fixed delete words are appended to the original `链接` rule; do not replace or remove `链接`.", skill)
        self.assertIn("`为了金币`", skill)
        self.assertIn("`暂无评价`", skill)
        self.assertIn("`蹲一个`", skill)
        self.assertIn("`交朋友`", skill)
        self.assertIn("`加v` is matched case-insensitively", skill)
        self.assertIn("Delete no-Chinese random alphanumeric heap comments only by deterministic regex and thresholds", skill)
        self.assertIn("Supported inputs: `.xlsx`, `.xlsm`, and `.csv`.", skill)
        self.assertIn("Supported merge inputs: `.xlsx`, `.xlsm`, and `.csv`.", skill)
        self.assertIn("CSV inputs are loaded through the deterministic compatibility layer", skill)
        self.assertIn("CSV values are preserved as text", skill)
        self.assertIn("For B站 exports, strip fixed `回复@xxx：` or `回复 @xxx:` prefixes on the raw merged workbook before standardization.", skill)
        self.assertIn("Do not move reply rows or infer parent-child hierarchy during this prefix-stripping step.", skill)
        self.assertIn("tools/strip_bilibili_reply_prefixes.py", skill)
        self.assertIn(
            "After cleaned outputs are generated and verified, immediately delete intermediate workflow files",
            skill,
        )
        self.assertIn("Do not ask for a separate cleanup confirmation after cleaning.", skill)
        self.assertIn("Delete cleaning logs and summary files by default unless the user explicitly asks to keep them for audit.", skill)
        self.assertIn("Keep only the final cleaned `.xlsx` and `.csv` as the default retained outputs.", skill)
        self.assertIn("tools/cleanup_intermediate_outputs.py", skill)

        merge_command = (
            'python tools\\merge_excel_workbooks.py "<file1.xlsx-or.csv>" "<file2.xlsx-or.csv>" '
            '"<file3.xlsx-or.csv>" --output "<raw-merged.xlsx>"'
        )
        strip_command = (
            'python tools\\strip_bilibili_reply_prefixes.py "<raw-merged.xlsx>" '
            '--output "<reply-prefix-stripped-merged.xlsx>"'
        )
        standardize_command = (
            'python tools\\standardize_excel_headers.py "<reply-prefix-stripped-merged.xlsx>" '
            '--output "<confirmed-standardized.xlsx>"'
        )
        clean_command = (
            'python tools\\clean_excel_comments.py "<standardized-merged.xlsx>" '
            '--target-header "评论内容" --clean-word "<word1>" --output "<confirmed-cleaned.xlsx>"'
        )
        cleanup_command = (
            'python tools\\cleanup_intermediate_outputs.py --intermediate "<raw-merged.xlsx>" '
            '--intermediate "<reply-prefix-stripped-merged.xlsx>" --intermediate "<confirmed-standardized.xlsx>" '
            '--intermediate "<confirmed-cleaned.deletions.csv>" --intermediate "<confirmed-cleaned.summary.json>" '
            '--protect "<confirmed-cleaned.xlsx>" --protect "<confirmed-cleaned.csv>" --summary "<cleanup-summary.json>"'
        )

        self.assertIn(merge_command, skill)
        self.assertIn(strip_command, skill)
        self.assertIn(standardize_command, skill)
        self.assertIn(clean_command, skill)
        self.assertIn(cleanup_command, skill)
        self.assertLess(skill.index(merge_command), skill.index(strip_command))
        self.assertLess(skill.index(strip_command), skill.index(standardize_command))
        self.assertLess(skill.index(standardize_command), skill.index(clean_command))
        self.assertLess(skill.index(clean_command), skill.index(cleanup_command))
        self.assertLess(
            skill.index("Ask `是否已经提供并合并完所有需要合并的表格？你确认后我再进行标准化。`"),
            skill.index(standardize_command),
        )
        self.assertLess(
            skill.index("Return the standardized merged workbook and wait for the user to confirm it before cleaning."),
            skill.index(clean_command),
        )

    def test_agents_records_non_destructive_merge_then_standardize_flow(self) -> None:
        agents = Path("AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("多文件流程必须先合并原始输入文件", agents)
        self.assertIn("合并之前必须先确认产品名和数据来源", agents)
        self.assertIn("文件名格式固定为 `YYYYMMDD_产品名_数据来源_步骤名`", agents)
        self.assertIn("同一流程只确认一次产品名和数据来源", agents)
        self.assertIn("请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。", agents)
        self.assertIn("当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。", agents)
        self.assertIn("只有在用户确认确实只有一个文件后，才允许跳过合并步骤", agents)
        self.assertIn("单文件流程也必须先确认产品名、数据来源和输出命名", agents)
        self.assertIn("用户确认确实只有一个文件后，才允许跳过合并并执行表头标准化", agents)
        self.assertIn("标准化后的表格返回给用户确认后，才允许询问 KOL 清理词", agents)
        self.assertIn("`.xlsx`、`.xlsm` 或 `.csv` 文件路径", agents)
        self.assertIn("CSV 输入必须先通过确定性兼容层读取", agents)
        self.assertIn("CSV 单元格值按文本保留", agents)
        self.assertIn("`子评论数/追评数` 是标准输出必保留列，但源文件没有对应表头时允许保留空列", agents)
        self.assertNotIn("只询问一个问题：是否有 KOL 清理词", agents)
        self.assertIn("用户确认所有需要合并的表格都已合并后", agents)
        self.assertIn("才允许对该原始合并总表执行表头标准化", agents)
        self.assertIn("标准化完成后必须把标准化后的表格返回给用户确认", agents)
        self.assertIn("原始输入文件和原始合并总表都不得被标准化步骤改写", agents)
        self.assertIn("表头标准化必须不只改表头文字", agents)
        self.assertIn("`评论日期`、`评论内容`、`产品名`、`点赞数`", agents)
        self.assertIn("`点赞量` -> `点赞数`", agents)
        self.assertIn("`评论数` -> `子评论数/追评数`", agents)
        self.assertIn("`追评` -> `一级评论`", agents)
        self.assertIn("`timestamp` -> `评论日期`", agents)
        self.assertIn("`timestamp` 必须按北京时间（UTC+8）转换为 `YYYY-MM-DD` 日期，只保留年月日，不输出时分秒", agents)
        self.assertIn("`content` -> `评论内容`", agents)
        self.assertIn("`like_count` -> `点赞数`", agents)
        self.assertIn("`rpid`、`parent_rpid`、`username`、`ip_location` 必须作为 ID、昵称或 IP 相关列丢弃", agents)
        self.assertIn("`parent_rpid` 是父评论 ID，不得映射为 `子评论数/追评数`", agents)
        self.assertIn("B站数据在标准化前必须先在原始合并总表中按固定规则去掉 `回复@xxx：` 或 `回复 @xxx:` 前缀", agents)
        self.assertIn("不得在该步骤中移动回复行或推断父子层级", agents)
        self.assertIn("清洗工具成功生成并核对清洗后的 `.xlsx` 和 `.csv` 后，必须立即删除本次流程生成的合并总表、回复前缀清理表、标准化总表及其摘要文件", agents)
        self.assertIn("默认同时删除清洗日志和清洗摘要，不再额外询问用户是否清理", agents)
        self.assertIn("除非用户在清洗前明确要求保留日志或摘要用于核对", agents)
        self.assertIn("最终默认只保留清洗后的 `.xlsx` 和 `.csv`", agents)
        self.assertIn("固定清理词只能追加，不能覆盖或移除原有固定词“链接”", agents)
        self.assertIn("“为了金币”", agents)
        self.assertIn("“暂无评价”", agents)
        self.assertIn("“蹲一个”", agents)
        self.assertIn("“交朋友”", agents)
        self.assertIn("“加v”以及英文固定清理词必须按大小写不敏感方式匹配", agents)
        self.assertIn("“link in bio”", agents)
        self.assertIn("“内容なし”", agents)
        self.assertIn("完全不含中文字符且命中随机英文/数字堆砌阈值的评论必须整行删除", agents)
        self.assertIn("TikTok/YouTube 英文表头映射", agents)
        self.assertIn("`createTime`、`publishedAt`", agents)
        self.assertIn("Relative platform time values such as `1年前`, `9个月前`, `1 year ago`, and `9 months ago` are converted deterministically from the current Beijing date.", agents)
        self.assertIn("Relative year values output only `YYYY`; relative month values output only `YYYY-MM`.", agents)
        self.assertIn("不得使用 AI 或语义判断拆分产品名", agents)
        self.assertIn("不得删除整行，不得修改主评论列 `评论内容`", agents)
        self.assertIn("对子评论列删除首尾空白后长度小于等于 5 的内容只清空对应单元格", agents)


if __name__ == "__main__":
    unittest.main()
