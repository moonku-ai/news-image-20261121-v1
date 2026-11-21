#!/usr/bin/env python3
"""Tests for news-image-20261121 v1 — 'The Crash Edition'.

Pure stdlib (unittest). Run: python3 -m unittest test_main -v
"""
import hashlib
import os
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

REPO = os.path.dirname(os.path.abspath(__file__))


def read_png_chunks(path):
    """Yield (type, data) for each PNG chunk, verifying CRCs."""
    with open(path, "rb") as fh:
        data = fh.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG signature"
    pos = 8
    chunks = []
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        cdata = data[pos + 8:pos + 8 + length]
        crc_stored = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])[0]
        crc_actual = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
        assert crc_stored == crc_actual, "bad CRC in %r chunk" % ctype
        chunks.append((ctype, cdata))
        pos += 12 + length
        if ctype == b"IEND":
            break
    assert pos == len(data), "trailing bytes after IEND"
    return chunks


class TestMain(unittest.TestCase):
    def run_main(self, out_dir):
        env = dict(os.environ)
        env["MAKEFUN_OUTPUT_DIR"] = out_dir
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "main.py")],
            env=env, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, "main.py failed: %s" % proc.stderr)
        return os.path.join(out_dir, "entry.png")

    def test_main_writes_entry_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_main(tmp)
            self.assertTrue(os.path.isfile(out), "entry.png not written")

    def test_png_valid_and_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_main(tmp)
            chunks = read_png_chunks(out)
            types = [c for c, _ in chunks]
            self.assertIn(b"IHDR", types)
            self.assertIn(b"IDAT", types)
            self.assertEqual(types[-1], b"IEND")
            ihdr = dict(chunks)[b"IHDR"]
            width, height = struct.unpack(">II", ihdr[:8])
            self.assertEqual((width, height), (1024, 1024))

    def test_size_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_main(tmp)
            self.assertLessEqual(os.path.getsize(out), 1048576,
                                "entry.png over 1 MiB")

    def test_deterministic_two_runs(self):
        with tempfile.TemporaryDirectory() as d1, \
                tempfile.TemporaryDirectory() as d2:
            out1 = self.run_main(d1)
            out2 = self.run_main(d2)
            with open(out1, "rb") as fh:
                b1 = fh.read()
            with open(out2, "rb") as fh:
                b2 = fh.read()
            self.assertEqual(b1, b2, "two runs differ")
            self.assertEqual(hashlib.sha256(b1).hexdigest(),
                             hashlib.sha256(b2).hexdigest())

    def test_output_matches_repo_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_main(tmp)
            with open(out, "rb") as fh:
                produced = fh.read()
            with open(os.path.join(REPO, "entry.png"), "rb") as fh:
                source = fh.read()
            self.assertEqual(produced, source)

    def test_output_readable_by_all(self):
        # make.fun collects outputs as another user: mode must be 0644.
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_main(tmp)
            mode = stat.S_IMODE(os.stat(out).st_mode)
            self.assertEqual(mode, 0o644, "entry.png mode is %o" % mode)

    def test_env_var_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "nested", "out")
            out = self.run_main(sub)
            self.assertTrue(os.path.isfile(out))


if __name__ == "__main__":
    unittest.main()
