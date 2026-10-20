"""Initialize NEW role volumes from new app PKI as root, then run services as10001.

Windows private ACLs map to root-only bind modes; do not grant Everyone key access.
Existing volume files are verified, never replaced. No old runtime paths accepted.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path


def product_manifest(folder):
    if folder.is_symlink() or any(p.is_symlink() for p in folder.rglob("*")):
        raise SystemExit("Product symlink rejected")
    rows = json.loads((folder / "manifest.json").read_text())
    paths = set()
    if not isinstance(rows, list) or not 1 <= len(rows) <= 256:
        raise SystemExit("Invalid product manifest")
    for row in rows:
        name = row["path"]
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or name in paths or not ((name.startswith("src/app/") and path.suffix == ".py") or (name.startswith("contracts/") and path.suffix == ".json")):
            raise SystemExit("Product path rejected")
        paths.add(name)
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != row["sha256"]:
            raise SystemExit("Product bytes differ; no upgrade performed")
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    if actual != {"manifest.json", *paths} or any(p.is_symlink() for p in folder.rglob("*")):
        raise SystemExit("Unexpected product contents")
    return rows


def upgrade_product(source, target, previous_manifest):
    """Caller stops services first. Validate old bytes before code-only publication."""
    if not previous_manifest.resolve().is_relative_to((source / "bundle-history").resolve()):
        raise SystemExit("Archived previous product manifest required")
    previous = product_manifest(previous_manifest.parent)
    current = product_manifest(target)
    if previous != current:
        raise SystemExit("Existing product differs from archived baseline")
    fresh = product_manifest(source / "bundle")
    if not {r["path"] for r in previous}.issubset({r["path"] for r in fresh}):
        raise SystemExit("Product removals require separate review")
    for name in [*(row["path"] for row in fresh), "manifest.json"]:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        pending = destination.with_name(destination.name + ".pending-upgrade")
        # Never overwrite an interrupted staging file silently.
        with pending.open("xb") as stream:
            stream.write((source / "bundle" / name).read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(pending, 0o644)
        os.replace(pending, destination)
    if product_manifest(target) != fresh:
        raise SystemExit("Published product verification failed")
    print(json.dumps({"product_files_verified": len(fresh), "previous_manifest_sha256": hashlib.sha256(previous_manifest.read_bytes()).hexdigest(),
                      "manifest_sha256": hashlib.sha256((target / "manifest.json").read_bytes()).hexdigest(), "role_or_budget_files_changed": False}))


def install(source=Path("/new-runtime"), destination=Path("/installed")):
    sets = {
        "control": ["ca.pem", "control.pem", "control.key", "storage.key", "human.token", "machine.token", "machine.id", "forward.key", "grant.json"],
        "gateway": ["ca.pem", "gateway.pem", "gateway.key", "gateway-client.pem", "gateway-client.key"],
        "upstream": ["ca.pem", "upstream.pem", "upstream.key", "forward.key"],
        "product": [(p.relative_to(source / "bundle")).as_posix() for p in (source / "bundle").rglob("*") if p.is_file()],
    }
    count = 0
    for role, names in sets.items():
        target = destination / role
        parent = source / ("bundle" if role == "product" else role)
        expected = set(names)
        existing = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        # LIVE prep may add only an empty regular mountpoint, never a key copy.
        placeholder = target / "judge.api-key"
        if role == "control" and placeholder.exists() and not placeholder.is_symlink() and placeholder.is_file() and placeholder.stat().st_size == 0 and placeholder.stat().st_nlink == 1:
            existing.discard("judge.api-key")
        if not existing.issubset(expected):
            raise SystemExit("Existing new role volume differs; no replacement performed")
        for name in names:
            src, dst = parent / name, target / name
            if src.is_symlink() or dst.is_symlink():
                raise SystemExit("Role volume symlink rejected")
            if dst.exists():
                if hashlib.sha256(dst.read_bytes()).digest() != hashlib.sha256(src.read_bytes()).digest():
                    raise SystemExit("Existing new role volume binding mismatch; no replacement performed")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            os.chown(dst, 10001, 10001)
            os.chmod(dst, 0o644 if role == "product" or dst.suffix == ".pem" else 0o600)
            count += 1
        for path in [target, *(p for p in target.rglob("*") if p.is_dir())]:
            os.chown(path, 10001, 10001)
            os.chmod(path, 0o755 if role == "product" else 0o700)
    print(f"Verified/initialized {count} NEW role files; uid10001, no legacy keys/DB involved.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--upgrade-product", type=Path)
    args = parser.parse_args()
    if args.upgrade_product:
        upgrade_product(Path("/new-runtime"), Path("/installed/product"), args.upgrade_product)
    else:
        install()
