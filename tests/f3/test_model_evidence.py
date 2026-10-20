import asyncio

import pytest
from test_decisions import FakeJudge, call, read, session


@pytest.mark.asyncio
async def test_summary_cannot_allow_without_same_issue_quote(repo):
    s = session(repo)
    read(repo, s)

    class NoSourceJudge(FakeJudge):
        async def analyze(self, snapshot):
            a, b = await super().analyze(snapshot)
            b["external_use"] = "NONE"
            b["evidence_refs"] = a["evidence_refs"]
            return a, b

    result = await repo.check_async(call(s), NoSourceJudge())
    assert result["decision"] == "DENY" and result["reason_codes"] == ["ANALYSIS_UNAVAILABLE"]
    assert result["approval_id"] is None


@pytest.mark.asyncio
async def test_mutated_model_snapshot_and_caller_args_are_not_authority(repo):
    s = session(repo)
    read(repo, s)
    value = call(s)
    judge = FakeJudge(delay=0.1)
    task = asyncio.create_task(repo.check_async(value, judge))
    await judge.entered.wait()
    value["args"]["body"] = "caller-mutated-while-waiting"
    result = await task
    # Original immutable call is still bound; caller mutation cannot authorize new args.
    assert result["decision"] == "ALLOW"
    with repo.tx() as db:
        stored = repo.decrypt(repo.call(db, result["call_id"])["canonical_cipher"])
        assert "caller-mutated" not in stored
    s2 = session(repo)
    read(repo, s2)

    class MutatingJudge(FakeJudge):
        async def analyze(self, snapshot):
            a, b = await super().analyze(snapshot)
            snapshot["server_grant"]["issue_id"] = 43
            return a, b

    denied = await repo.check_async(call(s2), MutatingJudge())
    assert denied["reason_codes"] == ["ANALYSIS_STALE"] and denied["approval_id"] is None
