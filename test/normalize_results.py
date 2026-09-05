#!/usr/bin/env python3
"""Make clean cocotb JUnit XML compatible with TinyTapeout's grep check."""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: normalize_results.py <results.xml>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    tree = ET.parse(path)
    root = tree.getroot()

    for element in root.iter():
        if element.tag == "failure":
            print("cocotb reported a failed testcase", file=sys.stderr)
            return 1
        count = element.attrib.get("failures")
        if count is not None and int(count) != 0:
            print(f"cocotb reported failures={count}", file=sys.stderr)
            return 1

    text = path.read_text()
    text = text.replace("failures=", "failed_count=")
    path.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
