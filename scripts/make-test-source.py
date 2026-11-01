#!/usr/bin/env python3
"""Builds test/, a source for trying the fields no real app in index.json
uses yet: copy_to_root, together with keep. scripts/serve.sh runs it; test/ is
not committed.

usage: make-test-source.py ADDRESS PORT [VERSION]

The app, "copytest", installs to sd:/apps/copytest and brings:
  settings.ini    kept on update (keep)
  copytest-data/  copied to sd:/copytest-data on first install, never
                  overwritten, left in place on removal (copy_to_root)
VERSION (default 1) goes into every file, so a second run with VERSION 2 shows
an update and which files it replaced. Its boot.dol only loops: starting it
gives a black screen until Reset.
"""
import hashlib
import io
import json
import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate  # noqa: E402

LOAD_AT = 0x80003100


def tiny_dol():
    """A DOL whose one text section is `b .` (a branch to itself)."""
    code = struct.pack(">I", 0x48000000).ljust(32, b"\0")
    text_off = [0x100] + [0] * 6
    text_addr = [LOAD_AT] + [0] * 6
    text_size = [len(code)] + [0] * 6
    header = struct.pack(">7I11I7I11I7I11I3I", *text_off, *[0] * 11, *text_addr, *[0] * 11,
                         *text_size, *[0] * 11, 0, 0, LOAD_AT)
    return header.ljust(0x100, b"\0") + code


def build_zip(version):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("copytest/boot.dol", tiny_dol())
        z.writestr("copytest/settings.ini", f"# from copytest {version}; edit it to see that updates keep it\n")
        z.writestr("copytest/copytest-data/readme.txt",
                   f"Copied to the card root by copytest {version}.\n"
                   "An update must leave this file as it is; removing copytest must leave this folder.\n")
        z.writestr("copytest/copytest-data/sub/version.txt", f"{version}\n")
    return buf.getvalue()


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    addr, port = sys.argv[1], sys.argv[2]
    version = sys.argv[3] if len(sys.argv) == 4 else "1"
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test")
    os.makedirs(root, exist_ok=True)
    data = build_zip(version)
    name = f"copytest-{version}.zip"
    with open(os.path.join(root, name), "wb") as f:
        f.write(data)
    index = {
        "format": 1,
        "name": "Test apps",
        "apps": [{
            "slug": "copytest",
            "name": "copy_to_root test",
            "author": "gc-homebrew-hub",
            "version": version,
            "category": "utilities",
            "short": "Test app for copy_to_root and keep; starting it shows a black screen",
            "long": "Installs to sd:/apps/copytest. settings.ini there is kept on update. copytest-data is "
                    "copied to sd:/copytest-data on first install, never overwritten, and left on removal.",
            "zip": f"http://{addr}:{port}/test/{name}",
            "zip_size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "root": "copytest",
            "binary": "boot.dol",
            "folder": "copytest",
            "keep": ["settings.ini"],
            "copy_to_root": ["copytest-data"],
        }],
    }
    path = os.path.join(root, "index.json")
    with open(path, "w") as f:
        json.dump(index, f, indent=2)
        f.write("\n")
    validate.check_index(path)
    if validate.errors:
        sys.exit("\n".join(validate.errors))


if __name__ == "__main__":
    main()
