from __future__ import annotations

import unittest
from pathlib import Path


SKILL_ROOT = Path("skills/bazhuayu-excel-cleaning")
REFERENCE_FILES = (
    "workflow.md",
    "data-contract.md",
    "header-standardization.md",
    "cleaning-rules.md",
    "naming-and-retention.md",
    "tool-reference.md",
    "extension-policy.md",
)


class WorkflowDocsTest(unittest.TestCase):
    def test_skill_and_references_record_validated_workflow(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        references = "\n".join(
            (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")
            for name in REFERENCE_FILES
        )
        documented_contract = skill + "\n" + references

        self.assertRegex(
            skill,
            r"\A---\nname: bazhuayu-excel-cleaning\ndescription: Use when ",
        )

        required_contract = (
            "## Multi-File Workflow",
            "请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。",
            "当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。",
            "是否已经提供并合并完所有需要合并的表格？你确认后我再进行标准化。",
            "标准化后的表格已生成，请确认是否可以进入清洗流程？你确认后我再询问 KOL 清理词并清洗。",
            "是否已经提供完成所有 KOL 清理词？你确认后我再进行清洗。",
            "scripts/merge_excel_workbooks.py",
            "scripts/strip_bilibili_reply_prefixes.py",
            "scripts/standardize_excel_headers.py",
            "scripts/clean_excel_comments.py",
            "scripts/cleanup_intermediate_outputs.py",
            "`评论日期`、`评论内容`、`产品名`、`哈希ID`、`点赞数`、`子评论数/追评数`、`一级评论`、`二级评论`、`三级评论`",
            "`评论日期与产品`",
            "`timestamp`",
            "`parent_rpid` is a parent-comment ID, not a subcomment count.",
            "Beijing date (`UTC+8`)",
            "Relative year values output only `YYYY`; relative month values output only `YYYY-MM`.",
            "Chinese comments whose trimmed length is less than or equal to 7 characters are deleted.",
            "Non-Chinese comments with four or fewer words are deleted.",
            "Pure numeric comments keep the legacy seven-character threshold",
            "Fixed delete words are appended to the original `链接` rule",
            "Chinese, English, Japanese, Korean, Spanish, Thai, and Hindi",
            "`一级评论`, `二级评论`, and `三级评论` cells whose trimmed length is less than or equal to 5 characters",
            "data_only=False",
            "Do not use AI",
            "Keep only the final cleaned `.xlsx` and `.csv`",
        )
        for item in required_contract:
            self.assertIn(item, documented_contract)

        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertNotIn("你确认清洗结果成功后", readme)
        self.assertNotIn("你确认清洗成功后", readme)
        self.assertIn("清洗后的 `.xlsx` 和 `.csv` 生成并核对成功后立即", readme)

        gitignore = Path(".gitignore").read_text(encoding="utf-8")
        self.assertIn("outputs/", gitignore)

    def test_agents_records_non_destructive_merge_then_standardize_flow(self) -> None:
        agents = Path("AGENTS.md").read_text(encoding="utf-8")

        required_instructions = (
            "多文件流程必须先合并原始输入文件",
            "合并之前必须先确认研究项目名、产品名和数据来源",
            "文件名格式固定为 `YYYYMMDD_产品名_数据来源_步骤名`",
            "同一流程只确认一次产品名和数据来源",
            "请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。",
            "当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。",
            "标准化后的表格返回给用户确认后，才允许询问 KOL 清理词",
            "CSV 输入必须先通过确定性兼容层读取",
            "CSV 单元格值按文本保留",
            "`子评论数/追评数` 是标准输出必保留列，但源文件没有对应表头时允许保留空列",
            "表头标准化必须不只改表头文字",
            "`点赞量` -> `点赞数`",
            "`timestamp` -> `评论日期`",
            "`content` -> `评论内容`",
            "`parent_rpid` 是父评论 ID，不得映射为 `子评论数/追评数`",
            "B站数据在标准化前必须先在原始合并总表中按固定规则去掉 `回复@xxx：` 或 `回复 @xxx:` 前缀",
            "默认同时删除清洗日志和清洗摘要，不再额外询问用户是否清理",
            "最终默认只保留清洗后的 `.xlsx` 和 `.csv`",
            "固定清理词只能追加，不能覆盖或移除原有固定词“链接”",
            "删除首尾空白后长度小于等于 7 的中文主评论",
            "Non-Chinese comments with four or fewer words are deleted.",
            "Pure numeric comments keep the legacy seven-character threshold for backward compatibility.",
            "完整固定清理词清单以 `config/comment-cleaner.json` 为准",
            "缺少必需标准列的已登记别名时必须停止",
            "不得猜测为标准列",
            "完全不含中文字符且命中随机英文/数字堆砌阈值的评论必须整行删除",
            "TikTok/YouTube 平台表头映射",
            "不得使用 AI 或语义判断拆分产品名",
            "不得删除整行，不得修改主评论列 `评论内容`",
            "对子评论列删除首尾空白后长度小于等于 5 的内容只清空对应单元格",
            "## Agent Skill Packaging Standard",
            "Skill 职责、触发场景、执行步骤、输出标准",
            "`references/`",
            "`scripts/`",
            "`assets/`",
            "单独复制",
            "独立运行",
        )
        for instruction in required_instructions:
            self.assertIn(instruction, agents)

        self.assertNotIn("未知表头必须停止", agents)


if __name__ == "__main__":
    unittest.main()
