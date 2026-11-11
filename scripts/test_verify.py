"""验证内核缺失时 FAIL/SKIP 的退出状态，防止跳过被计为通过。"""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import verify


class MissingKernelTests(unittest.TestCase):
    def test_missing_kernel_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(verify, "CORE_EXE", Path(tmp) / "missing"):
                ok, log = verify.test_kernel_config(Path(tmp) / "sandbox", {}, "mock")
        self.assertFalse(ok)
        self.assertIn("未通过", log)

    def check_cli(self, args, expected_code, expected_status):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(verify, "CORE_EXE", Path(tmp) / "missing"), \
                    patch("sys.argv", ["verify.py", *args]), \
                    patch.object(verify, "verify_tier") as run, \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(verify.main(), expected_code)
                run.assert_not_called()
        self.assertIn(expected_status, out.getvalue())
        self.assertNotIn("PASS", out.getvalue())
        self.assertNotIn("100%", out.getvalue())

    def test_cli_requires_kernel(self):
        self.check_cli([], 1, "[FAIL]")

    def test_explicit_skip_is_not_pass(self):
        self.check_cli(["--allow-missing-core"], 0, "[SKIP]")


if __name__ == "__main__":
    unittest.main()
