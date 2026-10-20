"""Opt-in prep of an EMPTY mountpoint in the NEW role volume, never a key copy.

Run with the existing dev image, network none, UID10001 and only that volume.
Preflight does not run this mutating preparation.
"""
import argparse
import hashlib
import os
import stat
from pathlib import Path


def prepare(root):
    root = root.resolve(strict=True)
    names = ("ca.pem", "control.pem", "control.key", "storage.key", "human.token", "machine.token", "machine.id", "forward.key", "grant.json")
    before = {}
    for name in names:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Prepared NEW control role required")
        before[name] = hashlib.sha256(path.read_bytes()).digest()
    path = root / "judge.api-key"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
    except FileExistsError:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size or info.st_nlink != 1:
            raise ValueError("Existing mountpoint differs; no replacement performed") from None
    if any(hashlib.sha256((root / name).read_bytes()).digest() != value for name, value in before.items()):
        raise ValueError("Role file changed during preparation")
    return {"empty_mountpoint_prepared": True, "existing_role_files_unchanged": len(names), "legacy_key_copied": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    import json
    print(json.dumps(prepare(args.root)))
