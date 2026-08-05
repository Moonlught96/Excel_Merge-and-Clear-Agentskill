from __future__ import annotations

import atexit
import shutil
import tempfile
from pathlib import Path


# Each test process owns a fresh root so output-path safety checks do not
# inherit artifacts from an earlier test run in the same working tree. Keep
# the visible child name stable because filename-discovery tests intentionally
# inspect their parent paths.
_TEST_SESSION_ROOT = Path(tempfile.mkdtemp(prefix="product-user-comment-skill-tests-"))
TEST_TEMP_ROOT = _TEST_SESSION_ROOT / ".tmp-tests"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


@atexit.register
def _remove_test_temp_root() -> None:
    shutil.rmtree(_TEST_SESSION_ROOT, ignore_errors=True)
