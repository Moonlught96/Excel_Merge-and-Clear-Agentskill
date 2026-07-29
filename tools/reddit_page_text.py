from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reddit_reconstruction.page_text import *  # noqa: F401,F403
from reddit_reconstruction.page_text import _visible_markdown_links
