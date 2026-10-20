"""Run the real SDK adapter with a local fake client, never an HTTP request."""
import json
from types import SimpleNamespace

import pytest
from test_span_repair import snapshot

from app.pdp.judge import OpenAIJudge
from app.pdp.semantic import SPAN_JUDGE_SCHEMA, validated_spans
from app.transparent.judge import DevelopmentJudge


@pytest.mark.asyncio
async def test_sdk_adapter_sends_span_catalog_schema_and_retains_budget_no_retries(tmp_path, monkeypatch):
    from app.pdp import judge as module
    captured = []
    class Client:
        def __init__(self, **kwargs):
            captured.append({"constructor": kwargs})
            self.responses = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def create(self, **kwargs):
            captured.append({"request": kwargs})
            value = json.loads(kwargs["input"][0]["content"])
            assert "evidence_texts" not in value
            assert value["evidence_catalog"]["coverage_complete"]
            result = {"task_relation": "DIRECT", "external_use": "NONE", "reason": "USER_INTENT_SUPPORTED",
                      "evidence_span_ids": [value["evidence_catalog"]["spans"][0]["span_id"]]}
            return SimpleNamespace(status="completed", usage=None, output_text=json.dumps(result),
                                   output=[SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text")])])
    monkeypatch.setattr(module, "AsyncOpenAI", Client)
    monkeypatch.setattr(module, "secret_file", lambda _: "fake-offline-key")
    path = tmp_path / "local-only-budget.db"
    seed = OpenAIJudge(path)
    for i in range(18):
        seed.claim(str(i), "A")
    adapter = DevelopmentJudge(path)
    snap = snapshot()
    pair = await adapter.analyze(snap)
    for view, value in zip(("A", "B"), pair, strict=True):
        assert validated_spans(value, snap, view)
    assert adapter.budget_summary()["requests_attempted"] == 20
    assert adapter.model == OpenAIJudge.model  # no model switch or new budget
    for entry in captured:
        if "constructor" in entry:
            assert entry["constructor"]["base_url"] == "https://api.openai.com/v1"
            assert entry["constructor"]["max_retries"] == 0
        else:
            value = entry["request"]
            assert value["text"]["format"]["schema"] == SPAN_JUDGE_SCHEMA
            assert value["text"]["format"]["name"] == "hookgw_span_observation"
            assert value["tools"] == [] and value["store"] is False
