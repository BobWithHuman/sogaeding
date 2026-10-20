"""Stage three local IPI inputs without running an actor, service or payload."""

import argparse
import hashlib
import json
import re
import shutil
import stat
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "ipi_scenarios"
RUNTIME = ROOT / "artifacts" / "runtime-ipi-scenarios"
FILES = {
    "supply_chain": "pr-184.diff",
    "log_forging": "error.log",
    "cross_channel": "tickets.md",
}


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(path: Path) -> None:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError as error:
        raise ValueError("Path outside project") from error
    cursor = ROOT
    for part in (None, *parts):
        if part is not None:
            cursor = cursor / part
        if cursor.is_symlink() or getattr(cursor, "is_junction", lambda: False)():
            raise ValueError(f"Symlink or junction in path: {cursor}")


def regular_file(path: Path) -> bool:
    safe_path(path)
    return path.is_file() and stat.S_ISREG(path.stat().st_mode) and path.stat().st_nlink == 1


def layout() -> dict[str, Path]:
    return {
        f"workspaces/{scenario}/{name}": FIXTURES / scenario / "attack" / name
        for scenario, name in FILES.items()
    } | {
        f"controls/{scenario}/{name}": FIXTURES / scenario / "clean" / name
        for scenario, name in FILES.items()
    }


def expected_manifest() -> dict:
    sources = layout()
    if any(not regular_file(source) for source in sources.values()):
        raise ValueError("Fixture missing or not a regular file")
    metadata_path = FIXTURES / "scenarios.json"
    if not regular_file(metadata_path):
        raise ValueError("Scenario metadata missing or not a regular file")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if {row["id"] for row in metadata["scenarios"]} != set(FILES):
        raise ValueError("Scenario metadata differs from fixture layout")
    for scenario, name in FILES.items():
        control = sources[f"controls/{scenario}/{name}"].read_text(encoding="utf-8")
        attack = sources[f"workspaces/{scenario}/{name}"].read_text(encoding="utf-8")
        if control == attack:
            raise ValueError(f"Missing case variation: {scenario}")
        urls = re.findall(r"https?://[^\s\"'<>]+", attack)
        if scenario != "log_forging" and not urls:
            raise ValueError(f"Missing reserved destination in case: {scenario}")
        if any(not (urlsplit(url).hostname or "").endswith(".invalid") for url in urls):
            raise ValueError(f"Non-reserved destination in case: {scenario}")
    return {
        "schema_version": 1,
        "purpose": "synthetic local scenario inputs; no actor or service started",
        "scenarios_sha256": hash_file(metadata_path),
        "files": {relative: hash_file(source) for relative, source in sorted(sources.items())},
    }


def check(manifest: dict) -> None:
    safe_path(RUNTIME)
    manifest_path = RUNTIME / "manifest.json"
    if not regular_file(manifest_path):
        raise ValueError("Runtime manifest missing or not a regular file")
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    if stored != manifest:
        raise ValueError("Runtime manifest differs from current fixtures")
    found = set()
    for path in RUNTIME.rglob("*"):
        safe_path(path)
        if path.is_file():
            found.add(path.relative_to(RUNTIME).as_posix())
    if found != set(manifest["files"]) | {"manifest.json"}:
        raise ValueError("Runtime file set differs from manifest")
    for relative, expected in manifest["files"].items():
        path = RUNTIME / relative
        if not regular_file(path) or hash_file(path) != expected:
            raise ValueError(f"Runtime file changed: {relative}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "check"))
    args = parser.parse_args()
    manifest = expected_manifest()
    safe_path(RUNTIME)
    if args.mode == "prepare" and not RUNTIME.exists():
        RUNTIME.mkdir(parents=True)
        for relative, source in layout().items():
            target = RUNTIME / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        (RUNTIME / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    check(manifest)
    print(f"READY: {len(FILES)} scenarios, {len(manifest['files'])} local input files; actor=0, provider=0")
    print(f"Runtime: {RUNTIME}")


if __name__ == "__main__":
    main()
