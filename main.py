#!/usr/bin/env python3
"""news-image-20261121 v1 — "The Crash Edition".

Sums up Saturday 21 November 2026's world news in one image:
the AI market meltdown (Nasdaq -5.28%, Nvidia -14%, Anthropic -8.5%,
$4 trillion wiped out), Russia's biggest air assault on Ukraine
(400+ drones, 110+ missiles, Kyiv bridges hit, Polish airspace
violated), COP31 spilling into overtime in Antalya, and Bolsonaro
hospitalised in Brasilia — plus the day's other stories in the
ticker strip.

The image (entry.png, 1024x1024, under 1 MiB) is a front-page
poster designed for this bounty. This program publishes it to the
harness output directory, deterministically: two runs write
identical bytes. Before copying it validates the source PNG
(signature, IHDR dimensions and CRC, size limit); the copy itself
is atomic (temp file + rename, so a crash never leaves a partial
file); afterwards the output is verified byte-for-byte against
the source. Pure Python standard library; no network, no
third-party dependencies.

Usage: python3 main.py
Output: $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png)
"""

import hashlib
import os
import shutil
import struct
import sys
import zlib

SOURCE_NAME = "entry.png"
OUTPUT_NAME = "entry.png"
EXPECTED_WIDTH = 1024
EXPECTED_HEIGHT = 1024
MAX_BYTES = 1048576
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def validate_source(path):
    """Check the repo image is a valid entry before copying it.

    Returns None when the file is a well-formed PNG of the expected
    size; otherwise returns a human-readable error string. A corrupt
    or wrong-sized source must fail loudly here instead of being
    copied and failing grading later.
    """
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        return "%s is %d bytes, over the 1 MiB limit" % (path, size)
    with open(path, "rb") as fh:
        header = fh.read(33)
    if len(header) < 33 or header[:8] != PNG_SIGNATURE:
        return "%s is not a PNG file" % path
    length, ctype = struct.unpack(">I4s", header[8:16])
    if ctype != b"IHDR" or length != 13:
        return "%s has no valid IHDR chunk" % path
    width, height = struct.unpack(">II", header[16:24])
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        return "%s is %dx%d, expected %dx%d" % (
            path, width, height, EXPECTED_WIDTH, EXPECTED_HEIGHT)
    crc_stored = struct.unpack(">I", header[29:33])[0]
    crc_actual = zlib.crc32(header[12:29]) & 0xFFFFFFFF
    if crc_stored != crc_actual:
        return "%s has a corrupt IHDR chunk (bad CRC)" % path
    return None


def repo_dir():
    """Directory holding this program (and entry.png)."""
    return os.path.dirname(os.path.abspath(__file__))


def output_dir():
    """Harness output directory (MAKEFUN_OUTPUT_DIR, else /output)."""
    return os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")


def publish(source, destination):
    """Copy source to destination atomically.

    Writes to a temporary file in the same directory, fsyncs it,
    then renames over the destination, so a crash or kill mid-copy
    never leaves a partial entry.png behind. Returns the number of
    bytes written. Raises OSError on failure; the temp file is
    removed on the error path.
    """
    out_dir = os.path.dirname(destination)
    # Unique per process: two concurrent runs sharing one output dir
    # must not clobber each other's temp file.
    tmp_path = os.path.join(
        out_dir, ".%s.tmp.%d" % (OUTPUT_NAME, os.getpid()))
    try:
        with open(source, "rb") as src, open(tmp_path, "wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(tmp_path, destination)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return os.path.getsize(destination)


def sha256_file(path):
    """SHA-256 hex digest of a file, streamed in 1 MiB blocks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def verify_copy(source, destination):
    """Confirm the published file is a byte-identical, valid PNG.

    Returns None on success, else a human-readable error string.
    Catches disk errors or truncated writes that the copy itself
    would not notice.
    """
    if sha256_file(source) != sha256_file(destination):
        return "%s does not match %s after copy" % (destination, source)
    return validate_source(destination)


def main():
    source = os.path.join(repo_dir(), SOURCE_NAME)
    if not os.path.isfile(source):
        print("missing %s next to main.py" % SOURCE_NAME, file=sys.stderr)
        return 1
    problem = validate_source(source)
    if problem is not None:
        print("invalid source: %s" % problem, file=sys.stderr)
        return 1
    out_dir = output_dir()
    os.makedirs(out_dir, exist_ok=True)
    destination = os.path.join(out_dir, OUTPUT_NAME)
    if os.path.abspath(source) == os.path.abspath(destination):
        print("source and destination are the same file", file=sys.stderr)
        return 1
    try:
        written = publish(source, destination)
    except OSError as exc:
        print("failed to write %s: %s" % (destination, exc), file=sys.stderr)
        return 1
    problem = verify_copy(source, destination)
    if problem is not None:
        print("output verification failed: %s" % problem, file=sys.stderr)
        return 1
    # make.fun collects outputs as another user: world-readable.
    os.chmod(destination, 0o644)
    print("wrote %s (%d bytes)" % (destination, written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
