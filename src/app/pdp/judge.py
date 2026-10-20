"""Official Responses adapter, bounded attempts, no tools/proxy/retry/storage."""

import asyncio
import json
import os
import sqlite3
import time
from pathlib import Path

import httpx
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.common import SafeError, canonical, secret_file, strict_json
from app.pdp.diagnostics import AnalysisFailure
from app.pdp.semantic import INSTRUCTIONS, JUDGE_SCHEMA, inputs


class OpenAIJudge:
    model = os.getenv("WITH_HUMAN_JUDGE_MODEL", "gpt-5.6-luna")
    instructions = INSTRUCTIONS
    observation_schema = JUDGE_SCHEMA
    observation_name = "f3_observation"
    request_inputs = staticmethod(inputs)

    def __init__(self, budget_path=None):
        self.path = str(
            budget_path or os.getenv("JUDGE_BUDGET_DB_PATH", "/data/judge-budget.sqlite3")
        )
        self.usage = []

    def claim(self, analysis_id, view):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=1) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS attempts (analysis_id TEXT, view TEXT, started REAL, usage TEXT, status TEXT, PRIMARY KEY(analysis_id,view))"
            )
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM attempts").fetchone()[0] >= 24:
                raise AnalysisFailure("REQUEST_BUDGET_EXHAUSTED", view)
            db.execute(
                "INSERT INTO attempts VALUES (?,?,?,NULL,?)",
                (analysis_id, view, time.time(), "STARTED"),
            )

    def budget_summary(self):
        if not Path(self.path).exists():
            return {"requests_attempted": 0, "remaining": 24, "limit": 24}
        with sqlite3.connect(self.path, timeout=1) as db:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='attempts'").fetchone()
            rows = db.execute("SELECT status,usage FROM attempts").fetchall() if exists else []
        totals = {"input_tokens": 0, "output_tokens": 0}
        for _, usage in rows:
            value = json.loads(usage) if usage else {}
            for name in totals:
                totals[name] += value.get(name) or 0
        return {"requests_attempted": len(rows), "remaining": max(0, 24-len(rows)),
                "limit": 24, "recorded_usage": totals}

    def record(self, analysis_id, view, status, usage, elapsed):
        safe = {
            "input_tokens": usage.input_tokens if usage else None,
            "output_tokens": usage.output_tokens if usage else None,
            "elapsed_ms": round(elapsed * 1000),
        }
        with sqlite3.connect(self.path, timeout=1) as db:
            db.execute(
                "UPDATE attempts SET usage=?,status=? WHERE analysis_id=? AND view=?",
                (canonical(safe), status, analysis_id, view),
            )
        self.usage.append({"analysis_id": analysis_id, "view": view, "status": status, **safe})

    async def observe(self, snapshot, view):
        self.claim(snapshot["analysis_id"], view)  # Before starting any outbound request.
        started, usage, status = time.monotonic(), None, "FAILED"
        try:
            try:
                key = secret_file("judge.api-key")
                if not key:
                    raise OSError()
            except OSError:
                raise AnalysisFailure("MISSING_API_KEY", view) from None
            async with httpx.AsyncClient(
                trust_env=False, follow_redirects=False, timeout=15
            ) as http:
                async with AsyncOpenAI(
                    api_key=key,
                    base_url="https://api.openai.com/v1",
                    max_retries=0,
                    timeout=15,
                    http_client=http,
                ) as client:
                    response = await asyncio.wait_for(
                        client.responses.create(
                            model=self.model,
                            instructions=self.instructions,
                            input=[{"role": "user", "content": canonical(self.request_inputs(snapshot, view))}],
                            tools=[],
                            store=False,
                            max_output_tokens=2048,
                            reasoning={"effort": "none"},
                            text={
                                "format": {
                                    "type": "json_schema",
                                    "name": self.observation_name,
                                    "strict": True,
                                    "schema": self.observation_schema,
                                }
                            },
                        ),
                        15,
                    )
            usage = response.usage
            if response.status != "completed":
                raise AnalysisFailure("RESPONSE_INCOMPLETE", view)
            for item in response.output:
                if item.type == "reasoning":
                    continue
                if item.type == "message" and any(c.type == "refusal" for c in item.content):
                    raise AnalysisFailure("MODEL_REFUSAL", view)
                if item.type != "message" or any(c.type != "output_text" for c in item.content):
                    raise AnalysisFailure("UNEXPECTED_OUTPUT", view)
            if not response.output_text:
                raise AnalysisFailure("RESPONSE_INCOMPLETE", view)
            try:
                result = strict_json(response.output_text)
            except (SafeError, ValueError):
                raise AnalysisFailure("INVALID_JSON", view) from None
            status = "COMPLETED"
            return result
        except (Exception, asyncio.CancelledError) as exc:
            if isinstance(exc, asyncio.CancelledError):
                status = "CANCELLED"
                raise
            if isinstance(exc, AnalysisFailure):
                raise
            code = ("API_TIMEOUT" if isinstance(exc, (TimeoutError, APITimeoutError)) else
                    "API_AUTHENTICATION" if isinstance(exc, AuthenticationError) else
                    "API_RATE_LIMIT" if isinstance(exc, RateLimitError) else
                    "API_CONNECTION" if isinstance(exc, APIConnectionError) else
                    "API_ERROR" if isinstance(exc, APIError) else "ADAPTER_ERROR")
            raise AnalysisFailure(code, view) from None
        finally:
            self.record(snapshot["analysis_id"], view, status, usage, time.monotonic() - started)

    async def analyze(self, snapshot):
        tasks = [asyncio.create_task(self.observe(snapshot, view)) for view in ("A", "B")]
        try:
            return await asyncio.wait_for(asyncio.gather(*tasks), 20)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
