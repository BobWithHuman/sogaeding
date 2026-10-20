"""Read pinned official task/environment configuration; never execute vendor code."""

import argparse
import collections
import hashlib
import json
import tarfile
from pathlib import Path

import yaml


def audit(vendor, inventory, output):
    vendor, output = Path(vendor), Path(output)
    if output.exists():
        raise ValueError("PRESERVE_EXISTING_AUDIT")
    tasks = json.loads(Path(inventory).read_text())
    with tarfile.open(vendor.parents[1] / "source.tar.gz", "r:gz") as archive:
        files = {
            "/".join(Path(member.name).parts[1:]): archive.extractfile(member).read()
            for member in archive
            if member.isfile()
        }
    config = yaml.safe_load(files["dt_arena/config/env.yaml"])["environments"]
    envs = {}
    for name, definition in config.items():
        path = vendor / definition["docker_compose"]
        raw = files.get(definition["docker_compose"])
        if raw is None:
            envs[name] = {
                "compose": str(path.relative_to(vendor)),
                "status": "OFFICIAL_COMPOSE_FILE_MISSING",
                "services": [],
            }
            continue
        body = yaml.safe_load(raw)
        services = []
        for service, spec in body.get("services", {}).items():
            services.append(
                {
                    "name": service,
                    "image": spec.get("image"),
                    "build": spec.get("build"),
                    "privileged": spec.get("privileged", False),
                    "devices": spec.get("devices", []),
                    "network_mode": spec.get("network_mode"),
                    "volumes": spec.get("volumes", []),
                    "environment_keys": list(spec.get("environment", {}))
                    if isinstance(spec.get("environment", {}), dict)
                    else [v.split("=", 1)[0] for v in spec.get("environment", [])],
                    "healthcheck": spec.get("healthcheck"),
                }
            )
        envs[name] = {
            "compose": str(path.relative_to(vendor)),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "services": services,
        }
    attacks = collections.Counter()
    details = []
    for task in tasks:
        config = yaml.safe_load(files[task["config_path"]])
        kinds = []
        attack = config.get("Attack", {}) or {}
        for turn in attack.get("attack_turns", []) or []:
            for step in turn.get("attack_steps", []) or []:
                kind = step.get("type", "UNKNOWN")
                kinds.append(kind)
                attacks[kind] += 1
        details.append(
            {
                "task_key": task["task_key"],
                "injection_types": sorted(set(kinds)),
                "subagents": bool((config.get("Agent", {}) or {}).get("sub_agents")),
                "skills": bool((config.get("Agent", {}) or {}).get("skill_directories")),
            }
        )
    output.mkdir(parents=True)
    (output / "environments.json").write_text(json.dumps(envs, indent=2))
    (output / "tasks.json").write_text(json.dumps(details, indent=2))
    return {"environments": len(envs), "tasks": len(details), "injection_steps": dict(attacks)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.vendor, args.inventory, args.output)))
