"""Apply original turn-1 injection once; restore the same attacked filesystem."""

import json
import os
import time
from pathlib import Path

from app.benchmark.docker_sandbox import bind
from app.common import canonical, digest


def shared_attack_seed(controller, key, initial):
    from dt_arena.src.types.task import AttackConfig
    from utils.injection_helpers import get_env_injections_from_attack

    from app.benchmark.runtime_controller import SERVER, WORKER, atomic, private_tree

    folder_task = Path("/vendor/dataset") / key
    attack = AttackConfig.from_yaml(str(folder_task / "config.yaml"))
    injections = get_env_injections_from_attack(attack, turn_id=1)
    if not injections:
        return initial, None
    wanted = digest(canonical(injections))
    folder = controller.root / "injection-seeds" / digest(key)
    folder.mkdir(parents=True, exist_ok=True)
    ready = folder / "ready.json"
    lock = folder / "seed.lock"

    def read():
        value = json.loads(ready.read_text())
        if value["base_image"] != initial["image"] or value["injections_sha256"] != wanted:
            raise RuntimeError("INJECTION_SEED_BINDING_CHANGED")
        if value["state"] == "UNKNOWN":
            raise RuntimeError("INJECTION_SEED_UNKNOWN_NO_REPLAY")
        if (
            controller.sandbox.request(
                "GET", "/images/" + value["snapshot"]["image"] + "/json"
            ).get("Id")
            != value["snapshot"]["image"]
        ):
            raise RuntimeError("INJECTION_SEED_IMAGE_UNAVAILABLE")
        return value["snapshot"], value

    if ready.exists():
        return read()
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        for _ in range(600):
            if ready.exists():
                return read()
            time.sleep(1)
        raise RuntimeError("INJECTION_SEED_UNKNOWN_NO_REPLAY") from None
    os.close(fd)
    private_tree(folder)
    label = controller.plan["experiment"] + "-attack-seed-" + digest(key)[:12]
    created = []

    def create(*args, **kwargs):
        cid = controller.create(*args, **kwargs)
        created.append(cid)
        return cid

    env = create(
        label + "-env",
        initial["image"],
        [],
        network=controller.network,
        kind="environment",
        user="0:0",
        readonly=False,
        cap_add=("SETUID", "SETGID", "CHOWN", "DAC_OVERRIDE"),
    )
    receipt = None
    preserve_env = False
    try:
        controller.wait_api(env)
        source = (
            controller.project
            + "/artifacts/20261017-dtap-prepare/vendor/"
            + controller.plan["manifest"]["source_commit"]
            + "/dt_arena/injection_mcp_server/os-filesystem/env_injection.py"
        )
        create(
            label + "-server",
            SERVER,
            ["python", "/product/tools/dtap_runtime_injection.py"],
            namespace=env,
            mounts=[
                bind(controller.project + "/src", "/product/src"),
                bind(
                    controller.project + "/tools/dtap_runtime_injection.py",
                    "/product/tools/dtap_runtime_injection.py",
                ),
                bind(source, "/official-injection.py"),
            ],
            env={
                "PYTHONPATH": "/product/src:/benchdeps",
                "FILESYSTEM_API_URL": "http://127.0.0.1:8034",
            },
        )
        worker = create(
            label + "-worker",
            WORKER,
            ["python", "/product/tools/dtap_runtime_task.py", "inject-seed", "--task", key],
            namespace=env,
            mounts=controller.common(folder),
            env={
                "PYTHONPATH": "/product/src:/benchdeps:/vendor",
                "PYTHONDONTWRITEBYTECODE": "1",
                "CONTRACT_DIR": "/product/contracts",
            },
        )
        code = controller.sandbox.wait(worker, timeout=300)
        (folder / "worker.log").write_bytes(controller.sandbox.logs(worker))
        result_path = folder / "injection-seed-result.json"
        if code or not result_path.exists():
            raise RuntimeError("INJECTION_SEED_RESULT_UNKNOWN")
        result = json.loads(result_path.read_text())
        if result["injections_sha256"] != wanted:
            raise RuntimeError("INJECTION_SEED_RESULT_CHANGED")
        snapshot = controller.sandbox.snapshot(
            env, digest(label)[:24], reserve=controller.reserve_snapshot
        )
        snapshot.update(
            task_key=key,
            original_setup_sha256=initial["original_setup_sha256"],
            pre_attack_initial_image=initial["image"],
            environment_injection_sha256=wanted,
        )
        receipt = {
            "state": result["state"],
            "base_image": initial["image"],
            "injections_sha256": wanted,
            "results": result["results"],
            "outcome": result["outcome"],
            "snapshot": snapshot,
        }
    except BaseException:
        try:
            partial = controller.sandbox.snapshot(
                env, digest(label + "-unknown")[:24], reserve=controller.reserve_snapshot
            )
            atomic(folder / "unknown-final-snapshot.json", partial)
        except Exception:
            controller.sandbox.stop(env)
            preserve_env = True
            atomic(folder / "preserved-container.json", {"id": env, "state": "UNKNOWN_NO_REPLAY"})
        raise
    finally:
        for cid in reversed(created):
            if cid == env and preserve_env:
                controller.created.remove(cid)
                continue
            controller.sandbox.remove(cid)
            controller.created.remove(cid)
    if receipt is None:
        raise RuntimeError("INJECTION_SEED_RESULT_UNKNOWN")
    atomic(ready, receipt)
    return read()
