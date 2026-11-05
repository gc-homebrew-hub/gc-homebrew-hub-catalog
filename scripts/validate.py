#!/usr/bin/env python3
"""Checks sources.json and index.json against the rules GC Homebrew Hub Browser
applies when it reads them (source/catalog.c), so an entry the program would
silently drop fails here instead.

usage: validate.py [--download] [REPO_DIR]
  --download  also fetch every app and check zip_size, sha256 and, for
              archives, that the binary is inside the root folder
"""
import hashlib
import io
import json
import lzma
import os
import re
import sys
import tarfile
import urllib.request
import zipfile

CATEGORIES = {"games", "emulators", "media", "utilities", "demos"}
MAX_APPS = 256
INDEX_MAX_BYTES = 256 * 1024
XZ_MEMLIMIT = 16 << 20                      # XZ_MEMLIMIT in the program's tarxz.c
MAX_SOURCES = 16
LONG_SHOWN = 240                            # about what fits in the six lines the app's page shows
LONG_SHOWN_TO_ROOT = 210                    # five lines: copy_to_root adds a line of its own
# longest string each field may be (the program's buffer size minus one)
LIMITS = {"slug": 31, "name": 47, "author": 39, "version": 23, "category": 15, "short": 95,
          "long": 1023, "homepage": 159, "zip": 255, "archive": 255, "dol": 255, "sha256": 64, "root": 63,
          "binary": 47, "folder": 47}

errors = []


def fail(where, msg):
    errors.append(f"{where}: {msg}")


def url_ok(u):
    return (isinstance(u, str) and 10 <= len(u) < 256 and u.startswith(("http://", "https://"))
            and all(32 < ord(c) < 127 for c in u))


def safe_relative(p):
    if not isinstance(p, str) or not p or p[0] in "/\\" or ":" in p or "\\" in p:
        return False
    if any(ord(c) < 32 for c in p):
        return False
    return all(seg not in ("", ".", "..") for seg in p.split("/"))


def check_sources(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("format") != 1:
        fail("sources.json", "format must be 1")
    srcs = data.get("sources")
    if not isinstance(srcs, list) or not srcs:
        fail("sources.json", "needs a non-empty sources list")
        return
    if len(srcs) > MAX_SOURCES:
        fail("sources.json", f"more than {MAX_SOURCES} sources")
    for i, s in enumerate(srcs):
        if not url_ok(s.get("url")):
            fail(f"sources.json [{i}]", "url must be an http:// or https:// address under 256 characters")
        if len(s.get("name", "")) > 47:
            fail(f"sources.json [{i}]", "name longer than 47 characters")


def check_index(path):
    raw = open(path, "rb").read()
    if len(raw) > INDEX_MAX_BYTES:
        fail("index.json", f"{len(raw)} bytes; the program reads at most {INDEX_MAX_BYTES}")
    data = json.loads(raw)
    if data.get("format") != 1:
        fail("index.json", "format must be 1")
    apps = data.get("apps")
    if not isinstance(apps, list):
        fail("index.json", "needs an apps list")
        return []
    if len(apps) > MAX_APPS:
        fail("index.json", f"more than {MAX_APPS} apps")
    seen = set()
    for i, a in enumerate(apps):
        w = f"index.json app {a.get('slug') or i}"
        if not isinstance(a, dict):
            fail(w, "not an object")
            continue
        for k, n in LIMITS.items():
            if k in a and (not isinstance(a[k], str) or len(a[k]) > n):
                fail(w, f"{k} must be a string of at most {n} characters")
        shown = LONG_SHOWN_TO_ROOT if a.get("copy_to_root") else LONG_SHOWN
        if len(a.get("long", "")) > shown:
            fail(w, f"long is {len(a['long'])} characters; the app's page has room for about {shown}")
        slug = a.get("slug", "")
        if not re.fullmatch(r"[a-z0-9-]{1,31}", slug):
            fail(w, "slug must be 1-31 of a-z, 0-9 and -")
        if slug in seen:
            fail(w, "slug used twice")
        seen.add(slug)
        if a.get("category") not in CATEGORIES:
            fail(w, f"category must be one of {', '.join(sorted(CATEGORIES))}")
        for k in ("name", "author", "version", "short"):
            if not a.get(k):
                fail(w, f"{k} is missing")
        if sum(k in a for k in ("zip", "archive", "dol")) != 1:
            fail(w, "give exactly one of zip, archive or dol")
        url = a.get("zip") or a.get("archive") or a.get("dol")
        if not url_ok(url):
            fail(w, "download address must be http:// or https:// with no spaces")
        folder = a.get("folder", slug)
        # the browser's own folder is for its own entry only, which brings nothing else
        own = slug == "gc-homebrew-hub-browser"
        if not re.fullmatch(r"[A-Za-z0-9._\- ]{1,40}", folder) or (folder.lower() == "gc-homebrew-hub-browser") != own:
            fail(w, "folder must be 1-40 letters, digits, . _ - or space; gc-homebrew-hub-browser is the browser's own entry and folder")
        if own and any(k in a for k in ("keep", "copy_to_root", "replace_at_root")):
            fail(w, "the browser's own entry cannot have keep, copy_to_root or replace_at_root")
        binary = a.get("binary", "boot.dol")
        if not safe_relative(binary):
            fail(w, "binary must be a relative path inside the app folder")
        if "dol" in a and ("/" in binary or not binary.lower().endswith(".dol")):
            fail(w, "for a bare .dol, binary must be a file name ending in .dol")
        if "root" in a and not safe_relative(a["root"]):
            fail(w, "root must be a relative path inside the zip")
        if "sha256" in a and not re.fullmatch(r"[0-9a-f]{64}", a["sha256"]):
            fail(w, "sha256 must be 64 lowercase hex digits")
        if not isinstance(a.get("zip_size", 0), int):
            fail(w, "zip_size must be a whole number of bytes")
        if not isinstance(a.get("updated", 0), int):
            fail(w, "updated must be a Unix time in seconds")
        keep = a.get("keep", [])
        if not isinstance(keep, list) or len(keep) > 4 or not all(safe_relative(k) and len(k) < 64 for k in keep):
            fail(w, "keep must list at most 4 relative paths")
        root = a.get("copy_to_root", [])
        if (not isinstance(root, list) or len(root) > 4 or
                not all(safe_relative(r) and "/" not in r and r.lower() != "apps" and len(r) < 48 for r in root)):
            fail(w, "copy_to_root must list at most 4 top-level names (not apps)")
        reps = a.get("replace_at_root", [])
        if not isinstance(reps, list) or len(reps) > 2:
            fail(w, "replace_at_root must list at most 2 files")
            reps = []
        for r in reps:
            to = r.get("to", "") if isinstance(r, dict) else ""
            src = r.get("file", "") if isinstance(r, dict) else ""
            if not (isinstance(src, str) and all(safe_relative(p) for p in src.split("!", 1)) and len(src) < 112 and
                    safe_relative(to) and len(to) < 48 and to.lower() != "apps" and not to.lower().startswith("apps/")):
                fail(w, "replace_at_root: each needs file (a path in the download, or outer.zip!path) "
                        "and to (at the card root, not in apps)")
            arch = r.get("archive", f"{slug}_archive") if isinstance(r, dict) else ""
            if not re.fullmatch(r"[A-Za-z0-9._\- ]{1,40}", arch) or arch.lower() == "apps":
                fail(w, "replace_at_root: archive must be a folder name of 1-40 letters, digits, . _ - or space")
    return apps


def check_download(a):
    w = f"download {a['slug']}"
    url = a.get("zip") or a.get("archive") or a.get("dol")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "gc-homebrew-hub-catalog validate"})
        data = urllib.request.urlopen(req, timeout=60).read()
    except Exception as e:
        fail(w, f"could not fetch {url}: {e}")
        return
    if a.get("zip_size") and len(data) != a["zip_size"]:
        fail(w, f"size is {len(data)}, zip_size says {a['zip_size']}")
    digest = hashlib.sha256(data).hexdigest()
    if a.get("sha256") and digest != a["sha256"]:
        fail(w, f"sha256 is {digest}")
    if "zip" in a or "archive" in a:
        # told apart by their first bytes, as the program does
        if data[:4] == b"PK\3\4":
            zf = zipfile.ZipFile(io.BytesIO(data))
            names = set(zf.namelist())
            read = zf.read
        elif data[:6] == b"\xfd7zXZ\0" and "archive" in a:
            try:
                lzma.LZMADecompressor(lzma.FORMAT_XZ, memlimit=XZ_MEMLIMIT).decompress(data)
                tar = tarfile.open(fileobj=io.BytesIO(data), mode="r:xz")
                members = {m.name.removeprefix("./"): m for m in tar.getmembers() if m.isfile()}
                names = set(members)
                read = lambda n: tar.extractfile(members[n]).read()
            except lzma.LZMAError as e:
                fail(w, f"cannot unpack within {XZ_MEMLIMIT >> 20} MB of memory: {e}")
                return
        else:
            fail(w, "zip must be a zip file; archive a zip or .tar.xz")
            return
        prefix = a["root"].rstrip("/") + "/" if a.get("root") else ""
        if prefix + a.get("binary", "boot.dol") not in names:
            fail(w, f"{prefix}{a.get('binary', 'boot.dol')} is not in the zip")
        for r in a.get("replace_at_root", []):
            outer, _, member = r["file"].partition("!")
            if outer not in names:
                fail(w, f"replace_at_root file {outer} is not in the archive")
            elif member:
                try:
                    if member not in zipfile.ZipFile(io.BytesIO(read(outer))).namelist():
                        fail(w, f"replace_at_root: {member} is not in {outer}")
                except zipfile.BadZipFile:
                    fail(w, f"replace_at_root: {outer} is not a zip")
    elif a.get("replace_at_root") and any(r["file"] != a.get("binary") for r in a["replace_at_root"]):
        fail(w, "a bare .dol can only put its own binary at the root")
    print(f"ok  {a['slug']}: {len(data)} bytes, sha256 {digest}")


def main():
    args = sys.argv[1:]
    download = "--download" in args
    args = [a for a in args if a != "--download"]
    repo = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    check_sources(os.path.join(repo, "sources.json"))
    apps = check_index(os.path.join(repo, "index.json"))
    if download and not errors:
        for a in apps:
            check_download(a)
    for e in errors:
        print("error", e)
    if errors:
        sys.exit(1)
    print(f"{len(apps)} apps, all valid")


if __name__ == "__main__":
    main()
