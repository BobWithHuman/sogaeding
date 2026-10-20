"""Trusted official worker entry, invoked by the isolated TaskExecutor adapter."""

import argparse
import asyncio
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["seed", "run", "discover", "inject-seed"])
    parser.add_argument("--task")
    args = parser.parse_args()
    if args.mode == "inject-seed":
        import sys

        from dt_arena.src.types.task import AttackConfig
        from utils.injection_helpers import (
            apply_environment_injections_async,
            get_env_injections_from_attack,
        )

        from app.benchmark.injection_outcome import inspect_results
        from app.benchmark.mcp_compat import Client, module
        from app.common import canonical, digest

        attack = AttackConfig.from_yaml(str(Path("/vendor/dataset") / args.task / "config.yaml"))
        injections = get_env_injections_from_attack(attack, turn_id=1)

        async def inject():
            for attempt in range(60):
                try:
                    async with Client("http://127.0.0.1:8873/mcp"):
                        break
                except Exception:
                    if attempt == 59:
                        raise
                    await asyncio.sleep(0.2)
            sys.modules["fastmcp"] = module()
            results = await apply_environment_injections_async(
                injections, {"os-filesystem-injection": "http://127.0.0.1:8873/mcp"}
            )
            outcome = inspect_results(injections, results)
            state = (
                "READY"
                if outcome["verified"]
                else "SETUP_FAILED"
                if outcome["domain_failure"]
                else "UNKNOWN"
            )
            Path("/data/injection-seed-result.json").write_text(
                canonical(
                    {
                        "state": state,
                        "injections_sha256": digest(canonical(injections)),
                        "results": results,
                        "outcome": outcome,
                    }
                )
            )
            print(
                canonical(
                    {"stage": "ORIGINAL_INJECTION_SEED", "state": state, "steps": len(injections)}
                )
            )

        asyncio.run(inject())
        return
    if args.mode == "seed":
        import shutil

        if not shutil.which("curl"):
            raise RuntimeError("OFFICIAL_SETUP_REQUIRES_CURL")
        from utils.env_helpers import task_setup

        task_setup(Path("/vendor/dataset") / args.task)
        print("OFFICIAL_SETUP_COMPLETED")
        return
    if args.mode == "discover":
        import httpx

        from app.benchmark.proxy import rpc

        async def discover():
            async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
                _, session = await rpc(
                    client,
                    "http://127.0.0.1:8033/mcp",
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": "dtap-runtime-discovery", "version": "1"},
                        },
                    },
                )
                headers = {"mcp-session-id": session} if session else {}
                await rpc(
                    client,
                    "http://127.0.0.1:8033/mcp",
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    headers,
                )
                result, _ = await rpc(
                    client,
                    "http://127.0.0.1:8033/mcp",
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                    headers,
                )
                Path("/data/actual-tools.json").write_text(json.dumps(result["result"]["tools"]))

        asyncio.run(discover())
        return
    from app.benchmark.official_adapter import run_official_task
    from app.benchmark.runtime_registry import RuntimeRegistry

    config = json.loads(Path("/config/runtime.json").read_text())
    config["registry"] = RuntimeRegistry(config["registry"])
    config["machine_token"] = Path("/runtime/machine.token").read_text().strip()
    config["ca_file"] = "/runtime/ca.pem"
    os.environ["EVAL_RESULTS_ROOT"] = "/data/results"
    os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
    from app.benchmark.auxiliary import judge_clients

    with judge_clients(config):
        result = asyncio.run(
            run_official_task(Path("/vendor/dataset") / config["task_key"], config)
        )
    Path("/data/official-runtime-result.json").write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            {
                "official_exit_code": result["official_exit_code"],
                "judge_error": result["judge"].get("error"),
                "product_model_transport": config["provider_mode"],
            }
        )
    )


if __name__ == "__main__":
    main()
