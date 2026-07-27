from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr

from tools.audit_standardized_comments import parse_args as parse_audit_args
from tools.clean_excel_comments import parse_args as parse_clean_args
from tools.filter_comments_by_keywords import parse_args as parse_filter_args
from tools.merge_excel_workbooks import parse_args as parse_merge_args
from tools.preprocess_platform_comments import parse_args as parse_preprocess_args
from tools.standardize_excel_headers import parse_args as parse_standardize_args
from tools.strip_bilibili_reply_prefixes import parse_args as parse_strip_args


class CliOutputRequirementsTest(unittest.TestCase):
    def assert_requires_output(self, parser, argv: list[str]) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                parser(argv)
        self.assertEqual(2, raised.exception.code)

    def test_each_transform_cli_requires_a_confirmed_output_path(self) -> None:
        cases = (
            (parse_merge_args, ["source.xlsx"]),
            (parse_strip_args, ["source.xlsx"]),
            (parse_preprocess_args, ["source.xlsx"]),
            (parse_standardize_args, ["source.xlsx"]),
            (parse_audit_args, ["standardized.xlsx"]),
            (parse_filter_args, ["standardized.xlsx", "--keep-keyword", "screenbar"]),
            (parse_clean_args, ["standardized.xlsx"]),
        )

        for parser, argv in cases:
            with self.subTest(argv=argv):
                self.assert_requires_output(parser, argv)
