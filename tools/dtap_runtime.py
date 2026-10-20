"""Explicit benchmark bootstrap; execute in the trusted controller image."""

import argparse
import asyncio
import hashlib
import json
import secrets
import shutil
from pathlib import Path

from app.benchmark.runtime_budget import RuntimeBudget
from app.benchmark.runtime_controller import (
    ENV_IMAGE,
    GATEWAY,
    SERVER,
    WORKER,
    Controller,
    DockerSandbox,
    atomic,
    bind,
    private_tree,
)
from app.benchmark.runtime_plan import experiment
from app.common import canonical, digest

OS100_SELECTION = Path("/project/artifacts/management-dtap-100-20261018/selection.json")
OS100_SELECTION_SHA256 = "05370679e22dc0f1eef328908a3ab1f819b168f336165c3312aa19734196250b"


def selected_os100(inventory, details):
    if hashlib.sha256(OS100_SELECTION.read_bytes()).hexdigest() != OS100_SELECTION_SHA256:
        raise ValueError("PINNED_OS100_SELECTION_CHANGED")
    selection = json.loads(OS100_SELECTION.read_text(encoding="utf-8"))
    inventory_path = Path("/project/artifacts/20261017-dtap-prepare/inventory-final/inventory.json")
    detail_path = Path("/project/artifacts/20261017-dtap-runtime/audit-fast/tasks.json")
    if (
        selection["inventory_sha256"] != hashlib.sha256(inventory_path.read_bytes()).hexdigest()
        or selection["detail_audit_sha256"] != hashlib.sha256(detail_path.read_bytes()).hexdigest()
    ):
        raise ValueError("OS100_SELECTION_INPUT_BINDING_CHANGED")
    expected = sorted(
        (
            t
            for t in inventory
            if t["domain"] == "os-filesystem"
            and t["threat_model"] == "indirect"
            and t["servers"] == ["OS-filesystem"]
            and t["environments"] == ["os-filesystem"]
        ),
        key=lambda t: t["task_key"],
    )
    keys = [t["task_key"] for t in expected]
    if (
        len(keys) != 100
        or len(set(keys)) != 100
        or selection["task_keys"] != keys
        or selection["selected_tasks"] != 100
    ):
        raise ValueError("OS100_EXACT_MEMBERSHIP_CHANGED")
    selected = {t["task_key"]: t for t in selection["tasks"]}
    if len(selected) != 100 or set(selected) != set(keys):
        raise ValueError("OS100_SELECTION_TASK_ROWS_CHANGED")
    detail = {d["task_key"]: d for d in details}
    vendor = Path("/vendor/dataset")
    for row in expected:
        key = row["task_key"]
        for field in ("config_sha256", "judge_sha256", "setup_sha256", "servers", "environments"):
            if selected[key][field] != row[field]:
                raise ValueError("OS100_SOURCE_ROW_CHANGED:" + key)
        if (
            detail[key]["subagents"]
            or detail[key]["skills"]
            or sorted(detail[key]["injection_types"]) != sorted(selected[key]["injection_types"])
        ):
            raise ValueError("OS100_REQUIREMENT_ROW_CHANGED:" + key)
        for file, field in (
            ("config.yaml", "config_sha256"),
            ("judge.py", "judge_sha256"),
            ("setup.sh", "setup_sha256"),
        ):
            if hashlib.sha256((vendor / key / file).read_bytes()).hexdigest() != row[field]:
                raise ValueError("OS100_OFFICIAL_FILE_CHANGED:" + key + ":" + file)
    return expected


def source_map(root):
    root = Path(root)
    return {
        str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }


def freeze_source(root):
    source = root / "source"
    source.mkdir()
    for directory in ("src", "docs/mvp/contracts", "agentgateway"):
        shutil.copytree(
            Path("/project") / directory,
            source / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    (source / "tools").mkdir()
    for name in (
        "dtap_runtime.py",
        "dtap_runtime_task.py",
        "dtap_runtime_injection.py",
        "prepare_tls.py",
    ):
        shutil.copyfile(Path("/project/tools") / name, source / "tools" / name)
    prefix = "artifacts/20261017-dtap-prepare/vendor/e0323a521ba4ef88f8e14c1eccf68d0a3d19a458/"
    for suffix in (
        "dt_arena/mcp_server/os-filesystem/main.py",
        "dt_arena/injection_mcp_server/os-filesystem/env_injection.py",
    ):
        dest = source / prefix / suffix
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path("/project") / prefix / suffix, dest)
    files = source_map(source)
    atomic(root / "source-manifest.json", files)
    return digest(canonical(files))


def verify_frozen(root, plan):
    files = json.loads((root / "source-manifest.json").read_text())
    if (
        source_map(root / "source") != files
        or digest(canonical(files)) != plan["manifest"]["runtime_source_sha256"]
    ):
        raise ValueError("FROZEN_RUNTIME_SOURCE_CHANGED")
    if digest(canonical(plan["coverage"])) != plan["manifest"]["coverage_sha256"]:
        raise ValueError("TASK_COVERAGE_MANIFEST_CHANGED")
    if plan["manifest"].get("selection_profile") == "PINNED_OS_FILESYSTEM_INDIRECT_100":
        if (
            hashlib.sha256((root / "selection.json").read_bytes()).hexdigest()
            != plan["manifest"]["selection_sha256"]
        ):
            raise ValueError("FROZEN_OS100_SELECTION_CHANGED")
        keys = json.loads((root / "selection.json").read_text(encoding="utf-8"))["task_keys"]
        if (
            keys != plan["manifest"]["task_keys"]
            or digest(canonical(keys)) != plan["manifest"]["selection_task_keys_sha256"]
        ):
            raise ValueError("FROZEN_OS100_TASK_KEYS_CHANGED")


def initialize(args):
    if getattr(args, "functional_metadata_fix", False):
        from app.benchmark.runtime_functional_continuation import prepare_metadata_successor

        return prepare_metadata_successor(args)
    if getattr(args, "functional_continuation", False):
        from app.benchmark.runtime_functional_continuation import prepare

        return prepare(args)
    if getattr(args, "functional_routing", False):
        from app.benchmark.runtime_functional import prepare

        return prepare(args)
    if getattr(args, "login_pair", False):
        from app.benchmark.runtime_login_pair import prepare

        return prepare(args)
    if getattr(args, "chatgpt_plan", False):
        from app.benchmark.runtime_login import prepare

        return prepare(args)
    if getattr(args, "utility_acceptance", False):
        from app.benchmark.runtime_utility_acceptance import prepare

        return prepare(args)
    if getattr(args, "deny_followup", False):
        from app.benchmark.runtime_deny_followup import prepare

        return prepare(args)
    if getattr(args, "demo", False):
        from app.benchmark.runtime_demo import prepare

        return prepare(args)
    if args.continue_parent:
        from app.benchmark.runtime_continuation import prepare

        return prepare(args)
    from prepare_tls import generate

    root = Path("/experiment")
    if (root / "plan.json").exists():
        raise ValueError("FROZEN_EXPERIMENT_ALREADY_EXISTS")
    source = Path("/project/artifacts/20261017-dtap-prepare/inventory-final/inventory.json")
    legacy = Path("/project/artifacts/20261017-dtap-prepare/prepared/manifest.json")
    if (
        hashlib.sha256(legacy.read_bytes()).hexdigest()
        != "343bac491c239b5ead01cf0df9ab2951a2af18718a1dc0a9243dd5af8c780306"
    ):
        raise ValueError("PRESERVED_ORIGINAL_MANIFEST_CHANGED")
    if (
        hashlib.sha256(source.read_bytes()).hexdigest()
        != json.loads(legacy.read_text())["inventory_sha256"]
    ):
        raise ValueError("ORIGINAL_FULL_TASK_INVENTORY_CHANGED")
    tasks = json.loads(source.read_text())
    details = json.loads(
        Path("/project/artifacts/20261017-dtap-runtime/audit-fast/tasks.json").read_text()
    )
    if args.offline:
        keys = [
            "os-filesystem/benign/1",
            "os-filesystem/malicious/indirect/consent-violations/1",
            *args.offline_case,
        ]
        tasks = [t for t in tasks if t["task_key"] in keys]
    elif args.profile == "os100":
        if args.offline_case:
            raise ValueError("OS100_NO_AD_HOC_CASES")
        tasks = selected_os100(tasks, details)
    elif args.offline_case:
        raise ValueError("USER_RUN_SUBSET_FORBIDDEN")
    # These are candidate capabilities for the integration test. Live init
    # requires a reviewed proof file bound to the production source digest.
    proof = (
        Path("/project/artifacts/20261018-dtap-os100/verified-capabilities.json")
        if args.profile == "os100"
        else Path("/project/artifacts/20261017-dtap-runtime/verified-capabilities.json")
    )
    if not args.offline and not proof.exists():
        raise ValueError("VERIFIED_RUNTIME_CAPABILITIES_REQUIRED")
    capabilities = (
        json.loads(proof.read_text())
        if proof.exists()
        else {
            "servers": {
                "OS-filesystem": {
                    "actual_schema_verified": True,
                    "complete_slots": True,
                    "gateway_integration_verified": True,
                }
            },
            "environments": {
                "os-filesystem": {
                    "image_digest": "sha256:7dc11a71388793b859cf7332f0d474784164d5e15bae751b28dab85a92b10732",
                    "paired_snapshot_verified": True,
                }
            },
            "injections": ["prompt", "tool", "environment"],
            "judge_domains": ["os-filesystem"],
        }
    )
    vendor = Path("/project/artifacts/20261017-dtap-prepare/vendor-manifest.json")
    vendor_files = json.loads(vendor.read_text())["files"]
    for suffix in (
        "dt_arena/mcp_server/os-filesystem/main.py",
        "dt_arena/injection_mcp_server/os-filesystem/env_injection.py",
    ):
        actual = (
            Path(
                "/project/artifacts/20261017-dtap-prepare/vendor/e0323a521ba4ef88f8e14c1eccf68d0a3d19a458"
            )
            / suffix
        )
        if hashlib.sha256(actual.read_bytes()).hexdigest() != vendor_files[suffix]["sha256"]:
            raise ValueError("PINNED_OFFICIAL_TOOL_SOURCE_CHANGED")
    if not args.offline:
        for name, expected in capabilities["verified_runtime_files"].items():
            if hashlib.sha256((Path("/project") / name).read_bytes()).hexdigest() != expected:
                raise ValueError("REVIEWED_RUNTIME_CANDIDATE_CHANGED")
    manifest, coverage = experiment(
        tasks,
        details,
        capabilities,
        cost_usd=args.max_usd,
        mode="OFFLINE" if args.offline else "LIVE",
    )
    if args.profile == "os100" and not args.offline:
        manifest["selection_profile"] = "PINNED_OS_FILESYSTEM_INDIRECT_100"
        manifest["selection_sha256"] = OS100_SELECTION_SHA256
        manifest["selection_task_keys_sha256"] = digest(canonical([t["task_key"] for t in tasks]))
    name = "dtap-" + secrets.token_hex(5)
    root.mkdir(parents=True, exist_ok=True)
    if args.profile == "os100" and not args.offline:
        shutil.copyfile(OS100_SELECTION, root / "selection.json")
    manifest["runtime_source_sha256"] = freeze_source(root)
    manifest["images"] = {
        "worker": WORKER,
        "server": SERVER,
        "environment": ENV_IMAGE,
        "gateway": GATEWAY,
    }
    plan = {
        "experiment": name,
        "manifest": manifest,
        "coverage": coverage,
        "host_root": args.host_root,
        "project_root": args.project_root,
        "networks": {
            "engine-off": {"name": name + "-off", "subnet": args.subnet_off},
            "engine-on": {"name": name + "-on", "subnet": args.subnet_on},
        },
    }
    plan["project_root"] = args.host_root.rstrip("/") + "/source"
    pki = root / "pki"
    generate(pki, [("upstream", ["upstream"]), ("broker", ["broker", "localhost", "127.0.0.1"])])
    runtime = root / "task-runtime"
    runtime.mkdir()
    for file in pki.iterdir():
        shutil.copyfile(file, runtime / file.name)
    for file in ("machine.id", "machine.token", "forward.key"):
        (runtime / file).write_text(secrets.token_urlsafe(48))
    broker_runtime = root / "broker-runtime"
    broker_runtime.mkdir()
    for file in ("ca.pem", "broker.pem", "broker.key"):
        shutil.copyfile(pki / file, broker_runtime / file)
    for file in ("admin.token", "broker.secret"):
        (broker_runtime / file).write_text(secrets.token_urlsafe(48))
    broker_config = root / "broker-config"
    broker_config.mkdir()
    atomic(broker_config / "runtime.json", {"manifest": manifest})
    (root / "broker-data").mkdir()
    atomic(root / "plan.json", plan)
    (root / "manifest.sha256").write_text(digest(canonical(manifest)) + "\n")
    import csv

    with (root / "COVERAGE.csv").open("w", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["task_key", "domain", "threat_model", "coverage", "readiness_reasons"]
        )
        writer.writeheader()
        for row in coverage:
            writer.writerow(
                {
                    k: canonical(row[k]) if isinstance(row[k], list) else row[k]
                    for k in writer.fieldnames
                }
            )
    private_tree(root)
    print(
        canonical(
            {
                "manifest_sha256": digest(canonical(manifest)),
                "target_tasks": len(tasks),
                "runtime_ready": manifest["runtime_ready"],
                "mode": manifest["mode"],
                "combined_usd_hard_cap": args.max_usd,
            }
        )
    )


def broker_start(args):
    root = Path("/experiment")
    plan = json.loads((root / "plan.json").read_text())
    if (
        args.expected_manifest_sha256
        and digest(canonical(plan["manifest"])) != args.expected_manifest_sha256
    ):
        raise ValueError("USER_FROZEN_MANIFEST_MISMATCH")
    sandbox = DockerSandbox(plan["experiment"])
    verify_frozen(root, plan)
    for data in plan["networks"].values():
        sandbox.network(data["name"], data["subnet"])
    off = plan["networks"].get("engine-off", plan["networks"]["engine-on"])["name"]
    mounts = [
        bind(plan["project_root"] + "/src", "/product/src"),
        bind(plan["project_root"] + "/docs/mvp/contracts", "/product/contracts"),
        bind(args.host_root + "/broker-runtime", "/runtime"),
        bind(args.host_root + "/broker-config", "/config"),
        bind(args.host_root + "/broker-data", "/data", False),
    ]
    command = ["python", "-m", "app.benchmark.runtime_services", "broker"]
    if plan["manifest"].get("chatgpt_plan"):
        from app.benchmark.runtime_login import verify

        verify(root, plan)
        mounts.append(bind(plan["manifest"]["chatgpt_plan"]["parent_host_root"], "/parent"))
        if plan["manifest"]["mode"] == "LIVE":
            if not args.credentials_host_root:
                raise ValueError("SIWC_PROTECTED_CREDENTIAL_MOUNT_REQUIRED")
            mounts.append(bind(args.credentials_host_root, "/credentials", False))
    if plan["manifest"].get("demo"):
        from app.benchmark.runtime_demo import verify_parent_ledger

        verify_parent_ledger(plan["manifest"])
        mounts.append(bind(plan["manifest"]["demo"]["parent_host_root"], "/parent"))
    if plan["manifest"]["mode"] == "OFFLINE":
        command += ["--offline"]
    else:
        opt = Path("/experiment/broker-data/paid-opt-in.json")
        if not opt.exists():
            raise ValueError("USER_PAID_OPT_IN_REQUIRED")
        mounts.extend([bind(args.host_root + "/keys", "/keys")])
    cid = sandbox.create_broker(
        plan["experiment"] + "-broker",
        WORKER,
        command,
        off_network=off,
        on_network=plan["networks"]["engine-on"]["name"],
        live=plan["manifest"]["mode"] == "LIVE",
        mounts=mounts,
        ports={8500: args.broker_port},
        env={
            "PYTHONPATH": "/product/src:/benchdeps:/vendor",
            "CONTRACT_DIR": "/product/contracts",
            "PYTHONDONTWRITEBYTECODE": "1",
            "DTAP_WINDOWS_HOST_ACL": "1",
        },
    )
    atomic(root / "broker-container.json", {"id": cid, "local_port": args.broker_port})
    print("PROVIDER_BROKER_STARTED_" + plan["manifest"]["mode"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "mode",
        choices=[
            "init",
            "probe",
            "verify",
            "broker",
            "run",
            "status",
            "collect",
            "stop",
            "recover",
            "resume",
        ],
    )
    p.add_argument("--host-root", required=True)
    p.add_argument("--project-root", default="C:/sogaeding")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--profile", choices=["full", "os100"], default="full")
    p.add_argument("--max-usd", default="250")
    p.add_argument("--arm", choices=["engine-off", "engine-on"])
    p.add_argument("--broker-port", type=int, default=18650)
    p.add_argument("--subnet-off", default="10.233.90.0/24")
    p.add_argument("--subnet-on", default="10.233.91.0/24")
    p.add_argument("--offline-case", action="append", default=[])
    p.add_argument("--continue-parent", action="store_true")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--deny-followup", action="store_true")
    p.add_argument("--utility-acceptance", action="store_true")
    p.add_argument("--query-routing", action="store_true")
    p.add_argument("--chatgpt-plan", action="store_true")
    p.add_argument("--login-pair", action="store_true")
    p.add_argument("--functional-routing", action="store_true")
    p.add_argument("--functional-continuation", action="store_true")
    p.add_argument("--functional-metadata-fix", action="store_true")
    p.add_argument("--credentials-host-root")
    p.add_argument("--require-fresh", action="store_true")
    p.add_argument("--continue-parent-sha256")
    p.add_argument("--parent-host-root")
    p.add_argument("--expected-manifest-sha256")
    a = p.parse_args()
    if a.mode == "init":
        return initialize(a)
    if a.mode == "broker":
        return broker_start(a)
    root = Path("/experiment")
    plan = json.loads((root / "plan.json").read_text())
    if (
        a.expected_manifest_sha256
        and digest(canonical(plan["manifest"])) != a.expected_manifest_sha256
    ):
        raise ValueError("USER_FROZEN_MANIFEST_MISMATCH")
    if a.mode == "verify":
        verify_frozen(root, plan)
        if plan["manifest"].get("chatgpt_plan"):
            from app.benchmark.runtime_login import verify

            verify(root, plan)
        if plan["manifest"].get("demo"):
            from app.benchmark.runtime_demo import verify_demo

            verify_demo(root, plan)
        if a.require_fresh:
            from app.benchmark.runtime_utility_acceptance import verify_fresh

            verify_fresh(root, plan)
        if plan["manifest"].get("continuation"):
            from app.benchmark.runtime_continuation import verify_parent

            if a.host_root != plan["host_root"]:
                raise ValueError("CONTINUATION_HOST_PATH_CHANGED")
            verify_parent(root, plan, Path("/parent"))
        print(
            canonical(
                {
                    "manifest_sha256": digest(canonical(plan["manifest"])),
                    "runtime_ready": plan["manifest"]["runtime_ready"],
                    "target_total": plan["manifest"]["target_total"],
                    "mode": plan["manifest"]["mode"],
                    "readiness": plan["manifest"]["readiness"],
                    "cost_cap_micro_usd": plan["manifest"]["limits"]["total"]["micro_usd"],
                }
            )
        )
        return
    if a.mode == "probe":
        from app.benchmark.runtime_utility_acceptance import run_probe

        return run_probe(a, root, plan)
    if a.mode == "run":
        if not a.arm:
            raise ValueError("ARM_REQUIRED")
        verify_frozen(root, plan)
        if plan["manifest"]["mode"] == "LIVE":
            if a.host_root != plan["host_root"]:
                raise ValueError("CONTINUATION_HOST_PATH_CHANGED")
            if plan["manifest"].get("chatgpt_plan"):
                from app.benchmark.runtime_login import verify

                verify(root, plan)
            elif plan["manifest"].get("demo"):
                from app.benchmark.runtime_demo import verify_demo

                if a.arm != "engine-on":
                    raise ValueError("DEMO_FRESH_ON_ONLY")
                verify_demo(root, plan)
            else:
                from app.benchmark.runtime_continuation import verify_parent

                verify_parent(root, plan, Path("/parent"))
        controller = Controller(root, a.host_root, plan["project_root"], a.arm)
        asyncio.run(controller.run(plan["manifest"]["task_keys"]))
        status = controller.admin_call("status")
        atomic(root / ("status-" + a.arm + ".json"), status)
        print(canonical(status))
        if status["stop"]:
            raise SystemExit(3)
        return
    budget = RuntimeBudget(root / "broker-data/provider.sqlite3", plan["manifest"])
    if a.mode == "stop":
        budget.stop("OPERATOR_STOP")
    elif a.mode == "resume":
        budget.resume_operator_stop()
    elif a.mode == "recover":
        if not a.arm:
            raise ValueError("ARM_REQUIRED")
        budget.reconcile_interrupted(a.arm)
    status = budget.status()
    atomic(root / "status.json", status)
    if a.mode == "collect":
        with budget.db() as db:
            jobs = [
                {"task_key": k, "arm": arm, "state": s, "result": json.loads(r) if r else None}
                for k, arm, s, r in db.execute("SELECT task,arm,state,result FROM jobs")
            ]
        atomic(
            root / "collected-results.json",
            {
                "status": status,
                "jobs": jobs,
                "coverage": plan["coverage"],
                "actual_model_accuracy": "NOT_RUN"
                if plan["manifest"]["mode"] == "OFFLINE"
                else "SEE_OFFICIAL_JUDGES_AND_INCOMPLETE_DENOMINATORS",
            },
        )
        from app.benchmark.runtime_report import summarize

        report = summarize(plan, jobs, status)
        atomic(root / "summary.json", report)
        lines = [
            "Official DTAP runtime collection",
            f"Mode: {report['mode']}; full target: {report['target_tasks']}; runtime ready: {report['runtime_ready_tasks']}; valid completed pairs: {report['valid_completed_pairs']}",
            "",
            "arm | group | full target | states | task success | attack success",
            "--- | --- | ---: | --- | ---: | ---:",
        ]
        lines.extend(
            f"{r['arm']} | {r['threat_model']} | {r['full_target_tasks']} | {canonical(r['states'])} | {r['completed_task_success']} | {r['completed_attack_success']}"
            for r in report["groups"]
        )
        lines.extend(
            [
                "",
                (
                    "One-pair functional acceptance: "
                    if plan["manifest"].get("chatgpt_plan", {}).get("paired_acceptance")
                    else "Utility acceptance: "
                    if plan["manifest"].get("utility_acceptance")
                    else "Official indirect attack comparison: "
                )
                + canonical(report["comparison"]),
                "",
                report["unavailable_unknown_incomplete"],
                report["clock_memory_limit"],
                "Actual model accuracy: " + report["actual_model_accuracy"],
            ]
        )
        (root / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    print(canonical(status))


if __name__ == "__main__":
    main()
