from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from reddit_reconstruction.json_export import parse_reddit_json


class RedditJsonExportTests(unittest.TestCase):
    def test_preserves_an_empty_post_body(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            media_post_path = Path(temporary_directory) / "media-post.json"
            media_post_path.write_text(
                json.dumps(
                    {
                        "meta": {
                            "completeness": "complete",
                            "collectedCommentCount": 0,
                            "reportedByApi": 0,
                            "discrepancy": 0,
                            "failedMore": 0,
                            "failedNodes": [],
                            "failedReasons": [],
                            "failedDetails": [],
                        },
                        "post": {
                            "id": "mediapost",
                            "subreddit": "python",
                            "title": "Media post",
                            "content": "",
                            "author": "poster",
                            "num_comments": 0,
                        },
                        "comments": [],
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual("", parse_reddit_json(media_post_path).post.content)
