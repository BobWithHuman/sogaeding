"""Freeze reviewed product code outside the MCP-editable workspace import path."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def source_files(root):
    files = {}
    for parent, suffix, prefix in [(root / "src/app", ".py", "src/app"), (root / "docs/mvp/contracts", ".json", "contracts")]:
        for source in sorted(parent.rglob("*" + suffix)):
            if source.is_symlink():
                raise SystemExit("Product bundle source symlink rejected")
            files[(Path(prefix) / source.relative_to(parent)).as_posix()] = source
    return files


def bundle(root, verify=False, current=False, update=False):
    root = root.resolve()
    target = root / "artifacts/runtime-hookgw/bundle"
    if verify:
        rows = json.loads((target / "manifest.json").read_text())
        actual = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        if actual != {"manifest.json", *(row["path"] for row in rows)} or any(p.is_symlink() for p in target.rglob("*")):
            raise SystemExit("Unexpected frozen product bundle contents")
        for row in rows:
            path = target / row["path"]
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                raise SystemExit("Frozen product bundle integrity failure")
        if current:
            sources = source_files(root)
            if set(sources) != {row["path"] for row in rows} or any(hashlib.sha256(sources[row["path"]].read_bytes()).hexdigest() != row["sha256"] for row in rows):
                raise SystemExit("Frozen product differs from current reviewed source")
        print("Frozen product bundle verified (no workspace imports).")
        return
    if update:
        # Explicit developer code-only update; keep previous bytes, never PKI/DB.
        bundle(root, verify=True)
        previous_hash = hashlib.sha256((target / "manifest.json").read_bytes()).hexdigest()
        archive = target.parent / "bundle-history" / previous_hash
        stage = target.parent / "bundle-stage"
        for path in (target, archive, stage):
            if path.is_symlink() or not path.resolve().is_relative_to((root / "artifacts/runtime-hookgw").resolve()):
                raise SystemExit("Bundle update path rejected")
        if archive.exists() or stage.exists():
            raise SystemExit("Previous archive/staging exists; preserve it for reviewed recovery")
        stage.mkdir()
        rows = []
        for name, source in source_files(root).items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, path)
            rows.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        (stage / "manifest.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        archive.parent.mkdir(exist_ok=True)
        target.rename(archive)
        stage.rename(target)
        bundle(root, verify=True, current=True)
        print(json.dumps({"previous_manifest_sha256": previous_hash, "previous_bundle": archive.relative_to(root).as_posix(),
                          "manifest_sha256": hashlib.sha256((target / "manifest.json").read_bytes()).hexdigest()}))
        return
    target.mkdir(parents=True, exist_ok=False)
    rows = []
    for parent, suffix, prefix in [(root / "src/app", ".py", "src/app"), (root / "docs/mvp/contracts", ".json", "contracts")]:
        for source in sorted(parent.rglob("*" + suffix)):
            if source.is_symlink():
                raise SystemExit("Product bundle source symlink rejected")
            name = (Path(prefix) / source.relative_to(parent)).as_posix()
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            rows.append({"path": name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    (target / "manifest.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps({"bundle_files": len(rows), "manifest_sha256": hashlib.sha256((target / "manifest.json").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--current", action="store_true")
    p.add_argument("--update", action="store_true")
    args = p.parse_args()
    if args.verify and args.update or args.current and not args.verify:
        p.error("Use --verify [--current] or explicit --update")
    bundle(args.root, args.verify, args.current, args.update)
