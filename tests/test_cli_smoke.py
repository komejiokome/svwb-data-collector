from __future__ import annotations

import subprocess
import unittest


class CLISmokeTest(unittest.TestCase):
    def test_console_help(self) -> None:
        proc = subprocess.run(["svwb-collect", "--help"], capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("SVWB data collector", proc.stdout)


if __name__ == "__main__":
    unittest.main()
