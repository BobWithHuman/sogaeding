"""Insert a guarded Responses backend into the PINNED official task_runner.

Task config/setup, original injection builders, official SDK description
injection, original Agent/Trajectory interfaces and judge classes are reused.
No case-specific candidate sequence is supplied to this production adapter.
"""

import asyncio
import concurrent.futures
import copy
import inspect
import json
import ssl
import sys
from pathlib import Path
from uuid import uuid4

import httpx

from app.benchmark.denial import policy_denial, policy_feedback, user_declined
from app.benchmark.hook import GatewayHook, GuardedDispatch, Stopped
from app.benchmark.responses_loop import AutonomousResponses, TaskIncomplete
from app.common import canonical, digest


def injected_tools(original, injections, server):
    # Call the official SDK wrapper's actual injection method rather than
    # changing benchmark descriptions or applying a fixture-only projection.
    from agent.openaisdk.src.mcp_wrapper import MCPServerStreamableHttp
    from mcp import Tool

    wrapper = MCPServerStreamableHttp(
        params={"url": "http://unused.invalid/mcp"},
        name=server,
        tool_injections=(injections or {}).get(server, {}),
    )
    return [
        t.model_dump(by_alias=True, exclude_none=True)
        for t in wrapper._apply_injections([Tool.model_validate(t) for t in original])
    ]


def judge_bridge(task_dir, response="", *, trajectory=None, check_task=True, check_attack=True):
    from utils.judge_helpers import load_judge_module

    module = load_judge_module(Path(task_dir))
    if module is None or not hasattr(module, "Judge"):
        return {"error": "OFFICIAL_JUDGE_UNAVAILABLE", "task_success": None, "attack_success": None}
    judge = module.Judge()
    events = (trajectory or {}).get("runtime_tool_events", [])
    judge.trajectory = [(event["call"], event["response"]) for event in events]
    responses = [response] if isinstance(response, str) else list(response)

    async def evaluate():
        value = {"error": None, "task_success": None, "attack_success": None}
        for kind, enabled in [("task", check_task), ("attack", check_attack)]:
            if not enabled:
                continue
            method = getattr(judge, "eval_" + kind)
            signature = inspect.signature(method)
            kwargs = (
                {"trajectory": trajectory}
                if "trajectory" in signature.parameters
                or any(
                    p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()
                )
                else {}
            )
            try:
                result = method(responses, **kwargs)
                if inspect.isawaitable(result):
                    result = await result
                if result is None and kind == "attack":
                    continue
                if (
                    not isinstance(result, (tuple, list))
                    or len(result) != 2
                    or type(result[0]) is not bool
                    or not isinstance(result[1], dict)
                ):
                    raise TypeError("OFFICIAL_JUDGE_RESULT_SHAPE")
                value[kind + "_success"], value[kind + "_metadata"] = result
                value[kind + "_message"] = result[1].get("message", "")
            except Exception:
                # Official helper converts exceptions to false; preserve error
                # explicitly so it cannot inflate the defense success rate.
                value["error"] = "OFFICIAL_" + kind.upper() + "_JUDGE_ERROR"
                value[kind + "_success"] = None
        return value

    # Official task_runner invokes run_judge synchronously from its async loop.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(evaluate())).result(timeout=120)


def parsed_mcp_result(result):
    value = result.get("structuredContent")
    if value is None:
        texts = [p.get("text", "") for p in result.get("content", []) if p.get("type") == "text"]
        value = "\n".join(texts)
    for _ in range(3):
        if isinstance(value, dict) and set(value) == {"result"}:
            value = value["result"]
        if not isinstance(value, str):
            break
        try:
            value = json.loads(value)
        except ValueError:
            break
    return value if isinstance(value, dict) else {"text": value}


async def dispatch_tool(self, name, args):
    server, tool = self.names[name]
    try:
        result = await self.dispatcher.call(server, tool, args)
    except Stopped as error:
        pre = self.records[-1] if self.records else {}
        if (
            str(error) == "SOURCE_CONTEXT_LIMIT_OBSERVED"
            and pre.get("stage") == "POST"
            and pre.get("state") == "OBSERVED"
            and pre.get("analysis_complete") is False
        ):
            raise TaskIncomplete("SOURCE_CONTEXT_LIMIT_OBSERVED") from error
        if pre.get("stage") != "PRE":
            raise TaskIncomplete("GATEWAY_BINDING_STOP") from error
        if (
            str(error) == "DTAP_USER_DECLINED"
            and pre.get("decision") == "CONFIRM"
            and pre.get("consent") == "DENIED"
            and pre.get("upstream_invoked") is False
        ):
            # The user's answer, as the environment's own permission refusal reads.
            return {
                "isError": True,
                "policy_feedback": user_declined(),
                "content": [{"type": "text", "text": "Permission DENIED by user. The action was not executed."}],
            }
        if pre.get("decision") == "CONFIRM":
            raise TaskIncomplete("CONFIRM_UNAPPROVED") from error
        if not policy_denial(pre, error):
            raise TaskIncomplete("ANALYSIS_OR_INFRASTRUCTURE_STOP") from error
        return {
            "isError": True,
            "policy_feedback": policy_feedback(pre["reasons"], self.names.values()),
            "content": [
                {
                    "type": "text",
                    "text": "Policy DENY: this exact call was not executed. Reasons: "
                    + ", ".join(pre["reasons"]),
                }
            ],
        }
    observed = next((r for r in reversed(self.records) if r.get("stage") == "POST"), {})
    if observed.get("state") not in ("OBSERVED", "OBSERVED_ERROR"):
        raise TaskIncomplete("POST_UNCONFIRMED_UNKNOWN")
    self.events.append(
        {
            "call": {"env": server, "tool": tool, "arguments": copy.deepcopy(args)},
            "response": parsed_mcp_result(result),
        }
    )
    self.trajectory.append_agent_step(tool, tool_name=tool, tool_params=args, server=server)
    self.trajectory.append_tool_return(result, tool_name=tool, server=server)
    self.record(
        {
            "kind": "observed_tool",
            "server": server,
            "tool": tool,
            "arguments": args,
            "state": observed["state"],
        }
    )
    return result


def agent_class(context):
    from dt_arena.src.types import hooks as official_hooks
    from dt_arena.src.types.agent import Agent, AgentResult
    from dt_arena.src.types.trajectory import Trajectory

    class GuardedOfficialResponsesAgent(Agent):
        def __init__(self, agent_config, runtime_config):
            super().__init__(agent_config, runtime_config)
            self.events = []
            self.records = []
            self.turn_index = 0
            self.final_output = ""
            self.completed_turns = 0
            self.output_dir = Path(runtime_config.output_dir)
            self.trajectory = Trajectory()
            self.trajectory.data["runtime_tool_events"] = self.events

        def _create_mcp_server(self, server_config):
            raise TaskIncomplete("DIRECT_SDK_DISPATCH_FORBIDDEN")

        def record(self, event):
            self.records.append(event)
            # Durable per-event rewrite, then official trajectory snapshot.
            # Task directory is private to this arm/task; no success before
            # post/transport observation and the independent official judge.
            target = self.output_dir / "runtime-events.json"
            temp = target.with_suffix(".tmp")
            temp.write_text(canonical(self.records))
            temp.replace(target)
            self.trajectory.save(str(self.output_dir / "trajectory.json"))

        async def initialize(self):
            self.ssl = ssl.create_default_context(cafile=context["ca_file"])
            self.control = httpx.AsyncClient(
                base_url=context["control_url"], verify=self.ssl, trust_env=False, timeout=30
            )
            self.gateway = httpx.AsyncClient(
                base_url=context["gateway_url"], verify=self.ssl, trust_env=False, timeout=35
            )
            self.provider = httpx.AsyncClient(
                base_url=context["provider_url"],
                verify=self.ssl,
                trust_env=False,
                timeout=context["limits"]["request_seconds"],
            )
            self.headers = {"Authorization": "Bearer " + context["machine_token"]}
            for _ in range(40):
                try:
                    if (await self.control.get("/health")).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.5)
            else:
                raise TaskIncomplete("MANDATORY_CONTROL_HEALTH_FAILED")
            connected = await self.control.post("/connect", headers=self.headers, json={})
            connected.raise_for_status()
            self.connection = connected.json()["connection"]
            Path("/data/active-connection.json").write_text(
                canonical({"connection": self.connection})
            )
            self.session = "dtap-" + str(uuid4())
            self.names = {}
            tools = []
            collected = []
            for server, original in context["catalogs"].items():
                actual = injected_tools(original, self.runtime_config.mcp_injection, server)
                collected.extend({"server": server, **t} for t in actual)
                for tool in actual:
                    # Stable alias is a namespace binding, never a file-tool
                    # parser alias. The original server/name is retained.
                    name = "dt_" + digest(server + "::" + tool["name"])[:24]
                    self.names[name] = (server, tool["name"])
                    tools.append(
                        {
                            "type": "function",
                            "name": name,
                            "description": tool.get("description", ""),
                            "parameters": tool["inputSchema"],
                            "strict": False,
                        }
                    )
            if digest(canonical(collected)) != context["catalog_sha256"]:
                raise TaskIncomplete("ACTOR_AND_ENGINE_CATALOG_MISMATCH")

            async def send(body):
                response = await self.provider.post(
                    "/v1/responses",
                    json=body,
                    headers={"Authorization": "Bearer " + context["actor_token"]},
                )
                response.raise_for_status()
                return response.json()

            async def dispatch(name, args):
                return await dispatch_tool(self, name, args)

            self.loop = AutonomousResponses(
                send,
                dispatch,
                tools,
                system=self.config.system_prompt,
                limits=context["limits"],
                record=self.record,
                provider_profile=context.get("provider_profile"),
                policy_recovery=context.get("functional_routing", False),
            )

        async def run(self, user_input, metadata=None):
            # metadata includes official labels/hidden attack goals; deliberately
            # never pass it to Responses, Jev, a system prompt or a tool result.
            self.turn_index += 1
            originals = context["original_instructions"]
            original = (
                originals[min(self.turn_index - 1, len(originals) - 1)] if originals else user_input
            )
            if not original:
                original = user_input  # direct prompt is the actual direct user request
            self.turn = "turn-" + str(self.turn_index)
            event = {
                "event": "UserPromptSubmit",
                "connection": self.connection,
                "session": self.session,
                "turn": self.turn,
                "prompt": original,
                "cwd": "DTAP_OFFICIAL_SANDBOX",
            }
            response = await self.control.post("/event", headers=self.headers, json=event)
            response.raise_for_status()
            if self.turn_index == 1:
                response = await self.control.post(
                    "/benchmark/catalog", headers=self.headers, json={"connection": self.connection}
                )
                response.raise_for_status()
            if user_input != original:
                response = await self.control.post(
                    "/runtime/prompt-source",
                    headers=self.headers,
                    json={"connection": self.connection, "text": user_input, "turn": self.turn},
                )
                response.raise_for_status()
            hook = GatewayHook(
                context["registry"],
                self.control,
                self.gateway,
                context["machine_token"],
                self.connection,
                self.session,
                self.turn,
                self.record,
            )
            self.dispatcher = GuardedDispatch(official_hooks, hook)
            self.hook_manager = self.dispatcher.manager
            self.trajectory.append_user_step(user_input)
            try:
                self.final_output = await self.loop.run(user_input)
                self.completed_turns += 1
                self.trajectory.set_final_response(self.final_output)
                return AgentResult(
                    final_output=self.final_output,
                    turn_count=self.loop.responses,
                    trajectory=self.trajectory,
                )
            except Exception as error:
                self.record(
                    {
                        "kind": "actor_incomplete",
                        "code": str(error)
                        if isinstance(error, TaskIncomplete)
                        else type(error).__name__,
                    }
                )
                raise
            finally:
                self.record(
                    {
                        "kind": "turn_finished",
                        "turn": self.turn_index,
                        "completed_turns": self.completed_turns,
                        "final_output": self.final_output,
                    }
                )

        async def cleanup(self):
            if hasattr(self, "connection"):
                response = await asyncio.shield(
                    self.control.post(
                        "/benchmark/close",
                        headers=self.headers,
                        json={"connection": self.connection},
                    )
                )
                response.raise_for_status()
                Path("/data/active-connection.json").unlink(missing_ok=True)
            for name in ("control", "gateway", "provider"):
                if hasattr(self, name):
                    await getattr(self, name).aclose()

    return GuardedOfficialResponsesAgent


async def run_official_task(task_dir, context, *, setup_callback=None):
    import eval.task_runner as runner
    from utils.env_helpers import task_setup as original_setup

    cls = agent_class(context)
    agents = []
    setup_failures = []

    def build(agent_type=None, agent_cfg=None, runtime_cfg=None, **kwargs):
        if agent_type != "withhuman-responses" or kwargs:
            raise TaskIncomplete("UNENROLLED_AGENT_BACKEND")
        agent = cls(agent_cfg, runtime_cfg)
        agents.append(agent)
        return agent

    def setup(path, task_id=None):
        if not context.get("initial_snapshot_restored"):
            original_setup(path, task_id=task_id)
        if setup_callback:
            setup_callback()

    def prestarted(*args, **kwargs):
        # MCP servers were started in separate, isolated containers. Never let
        # the official manager spawn a second/direct dispatch path locally.
        return None

    original = {
        name: getattr(runner, name)
        for name in (
            "task_setup",
            "start_task_mcp_servers",
            "build_agent",
            "run_judge",
            "start_injection_mcp_servers",
            "wait_for_injection_mcp_ready",
            "apply_environment_injections_async",
        )
    }

    def injection_servers(config, **kwargs):
        required = set(config["environment_servers"])
        if not required <= set(context.get("injection_urls", {})):
            raise TaskIncomplete("UNENROLLED_ENVIRONMENT_INJECTION_SERVER")
        return None, {
            **config,
            "environment_servers": {
                name: {"url": context["injection_urls"][name]} for name in required
            },
        }

    async def apply_injections(injections, urls):
        from app.benchmark.mcp_compat import module

        preapplied = context.get("preapplied_environment_injection")
        if preapplied and digest(canonical(injections)) == preapplied["injections_sha256"]:
            if preapplied["state"] != "READY":
                raise TaskIncomplete("INJECTION_SEED_UNAVAILABLE")
            return copy.deepcopy(preapplied["results"])

        previous = sys.modules.get("fastmcp")
        sys.modules["fastmcp"] = module()
        try:
            results = await original["apply_environment_injections_async"](injections, urls)
        finally:
            if previous is None:
                sys.modules.pop("fastmcp", None)
            else:
                sys.modules["fastmcp"] = previous
        Path("/data/environment-injection-results.json").write_text(canonical(results))
        if context.get("functional_routing"):
            from app.benchmark.injection_outcome import inspect_results

            outcome = inspect_results(injections, results)
            if not outcome["verified"]:
                setup_failures.append(
                    {
                        "kind": "benchmark_setup_failure",
                        "stage": "ENVIRONMENT_INJECTION",
                        "code": "OFFICIAL_ENVIRONMENT_INJECTION_FAILED",
                        "verified_domain_failure": outcome["domain_failure"],
                        "injection_outcome": outcome,
                    }
                )
                raise TaskIncomplete("OFFICIAL_ENVIRONMENT_INJECTION_FAILED")
            return results
        if len(results) != len(injections) or any(not r["success"] for r in results):
            setup_failures.append(
                {
                    "kind": "benchmark_setup_failure",
                    "stage": "ENVIRONMENT_INJECTION",
                    "code": "OFFICIAL_ENVIRONMENT_INJECTION_FAILED",
                }
            )
            raise TaskIncomplete("OFFICIAL_ENVIRONMENT_INJECTION_FAILED")
        for result in results:
            try:
                value = json.loads(result["result"])
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict) and (
                value.get("status") == "error" or value.get("success") is False
            ):
                setup_failures.append(
                    {
                        "kind": "benchmark_setup_failure",
                        "stage": "ENVIRONMENT_INJECTION",
                        "code": "OFFICIAL_ENVIRONMENT_INJECTION_FAILED",
                    }
                )
                raise TaskIncomplete("OFFICIAL_ENVIRONMENT_INJECTION_FAILED")
        return results

    try:
        runner.task_setup = setup
        runner.start_task_mcp_servers = prestarted
        runner.build_agent = build
        runner.run_judge = judge_bridge
        runner.start_injection_mcp_servers = injection_servers
        runner.wait_for_injection_mcp_ready = lambda config: None
        runner.apply_environment_injections_async = apply_injections
        code = await runner.run_single_task(
            Path(task_dir),
            agent_type="withhuman-responses",
            model=context.get("actor_model", "gpt-5.2"),
            max_turns=context["limits"]["responses"],
            skip_mcp=False,
            skip_judge=False,
            temperature=None,
        )
        agent = agents[0] if agents else None
        if agent:
            directory = agent.output_dir
            path = directory / "judge_result.json"
            # Judge partial effects too, without pretending that an incomplete
            # actor/CONFIRM/provider failure is a completed benchmark task.
            if not path.exists():
                result = judge_bridge(
                    task_dir, agent.final_output, trajectory=agent.trajectory.data
                )
                path.write_text(canonical(result))
            return {
                "official_exit_code": code,
                "actor_initialized": hasattr(agent, "loop"),
                "actor_completed": agent.completed_turns == agent.turn_index
                and agent.turn_index > 0,
                "judge": json.loads(path.read_text()),
                "output_dir": str(directory),
                "events": setup_failures + agent.records,
            }
        return {
            "official_exit_code": code,
            "judge": {"error": "AGENT_NOT_INITIALIZED"},
            "events": setup_failures,
        }
    finally:
        for name, value in original.items():
            setattr(runner, name, value)
