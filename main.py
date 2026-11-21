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
poster designed for this bounty. This program copies it, byte
for byte, to the harness output directory, deterministically:
two runs write identical bytes. Pure Python standard library;
no network, no third-party dependencies.

Usage: python3 main.py
Output: $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png)
"""

import os
import shutil
import sys

SOURCE_NAME = "entry.png"
OUTPUT_NAME = "entry.png"


def repo_dir():
    """Directory holding this program (and entry.png)."""
    return os.path.dirname(os.path.abspath(__file__))


def output_dir():
    """Harness output directory (MAKEFUN_OUTPUT_DIR, else /output)."""
    return os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")


def main():
    source = os.path.join(repo_dir(), SOURCE_NAME)
    if not os.path.isfile(source):
        print("missing %s next to main.py" % SOURCE_NAME, file=sys.stderr)
        return 1
    out_dir = output_dir()
    os.makedirs(out_dir, exist_ok=True)
    destination = os.path.join(out_dir, OUTPUT_NAME)
    shutil.copyfile(source, destination)
    # make.fun collects outputs as another user: world-readable.
    os.chmod(destination, 0o644)
    return 0


if __name__ == "__main__":
    sys.exit(main())
