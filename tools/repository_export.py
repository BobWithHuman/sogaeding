"""Export reviewable source; exclude local credentials, runtime and Git history."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

DIRECTORIES = (
    "src",
    "scripts",
    "tools",
    "tests",
    "fixtures",
    "agentgateway",
    "docs",
    "harness",
    ".agents",
)
ROOT_FILES = {
    "README.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    ".gitignore",
    ".gitattributes",
    ".dockerignore",
    ".env.example",
    "Dockerfile.dev",
    "pyproject.toml",
    "requirements-dev.in",
    "requirements-dev.lock",
    "LICENSE",
}
SKIP_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "runtime",
}
PRIVATE_SUFFIXES = (
    ".pem",
    ".key",
    ".token",
    ".api-key",
    ".pfx",
    ".p12",
    ".sqlite3",
    ".sqlite3-shm",
    ".sqlite3-wal",
    ".db",
    ".log",
    ".zip",
    ".tar",
    ".tar.gz",
    ".pyc",
)
PRIVATE_NAMES = {"auth.json", "credentials.json", "tokens.json", ".npmrc", ".netrc"}
PATTERNS = {
    "OPENAI_KEY": re.compile(rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}\b"),
    "GITHUB_KEY": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "JWT": re.compile(rb"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{16,}\b"),
    "PRIVATE_KEY": re.compile(
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{80,}"
    ),
}


def private_path(relative):
    name = relative.name.lower()
    return (
        any(part in SKIP_PARTS for part in relative.parts)
        or name in PRIVATE_NAMES
        or name.endswith(PRIVATE_SUFFIXES)
        or name.startswith(".env")
        and name != ".env.example"
    )


def inventory(root):
    """Explicit allowlist works before the first commit, without reading artifacts."""
    root = root.resolve()
    candidates = [root / name for name in ROOT_FILES if (root / name).exists()]
    candidates += list(root.glob("compose*.yaml"))
    for name in DIRECTORIES:
        directory = root / name
        if directory.is_symlink():
            raise ValueError("SOURCE_SYMLINK:" + name)
        if directory.exists():
            candidates.extend(directory.rglob("*"))
    rows, rejected, excluded = [], [], []
    for path in sorted(set(candidates)):
        relative = path.relative_to(root)
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("SOURCE_SYMLINK:" + relative.as_posix())
        if not path.is_file():
            continue
        if private_path(relative):
            excluded.append(relative.as_posix())
            continue
        data = path.read_bytes()
        for label, pattern in PATTERNS.items():
            if pattern.search(data):
                rejected.append({"path": relative.as_posix(), "kind": label})
        rows.append(
            {
                "path": relative.as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    if rejected:
        raise ValueError("CREDENTIAL_PATTERNS:" + json.dumps(rejected))
    return rows, excluded


def export(root, output):
    root = root.resolve()
    output = output.absolute()
    if output.exists() or not output.resolve().is_relative_to(root / "artifacts"):
        raise ValueError("NEW_EXPORT_INSIDE_ARTIFACTS_REQUIRED")
    rows, excluded = inventory(root)
    output.mkdir(parents=True, exist_ok=False)
    for row in rows:
        destination = output / row["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / row["path"], destination)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("EXPORT_HASH_MISMATCH")
    manifest = {
        "files": rows,
        "excluded_paths": excluded,
        "scan": "PATTERN_SCAN_NOT_A_GENERAL_SECRET_ABSENCE_PROOF",
    }
    (output.parent / (output.name + "-manifest.json")).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "state": "EXPORTED",
        "files": len(rows),
        "bytes": sum(row["bytes"] for row in rows),
        "excluded_files": len(excluded),
        "remote_upload": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.output:
            report = export(args.root, args.output)
        else:
            rows, excluded = inventory(args.root)
            report = {"state": "CHECKED", "files": len(rows), "excluded_files": len(excluded)}
        print(json.dumps(report))
    except ValueError as exc:
        print(str(exc))
        raise SystemExit(1) from None
