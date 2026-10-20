import asyncio
import sqlite3
from uuid import uuid4

import pytest

from app.common import POLICY, SafeError, digest
from app.executor.demo import DemoExecutor
from app.pdp.semantic import inputs, material

REQUEST = "이슈42를 읽고 요약 댓글을 한 번 작성해줘"


def session(repo, mode="ISSUE_SUMMARY", request=REQUEST):
    value = {
        "task_kind": "POST_COMMENT",
        "comment_mode": mode,
        "user_request": request,
        "issue_id": 42,
    }
    if mode == "EXACT":
        value["allowed_comment_body"] = "검토 완료"
    return repo.create_session(value)


def call(s, body="배포가 완료되어 문서를 확인해야 합니다.", tool="post_issue_comment", key=None):
    args = {"issue_id": 42, "body": body} if tool == "post_issue_comment" else {"issue_id": 42}
    return {
        "session_id": s["session_id"],
        "client_request_id": key or str(uuid4()),
        "tool_name": tool,
        "backend_id": "demo.v1",
        "args": args,
    }


def read(repo, s, text="배포 완료. 문서를 확인해야 합니다.", complete=True):
    value = call(s, tool="get_issue")
    checked = repo.check(value)
    reserved = repo.reserve(
        checked["call_id"], {k: value[k] for k in ("tool_name", "backend_id", "args")}
    )
    source = repo.source(
        {
            "call_id": checked["call_id"],
            "kind": "EXTERNAL",
            "origin_ref": "demo:42",
            "content_sha256": digest(text),
            "masked_excerpt": text[:512],
            "match_values": [],
            **material(text),
            "analysis_complete": complete,
        }
    )
    repo.report(
        checked["call_id"],
        {
            "reservation_id": reserved["reservation_id"],
            "state": "SUCCEEDED",
            "receipt": {
                "call_id": checked["call_id"],
                "session_id": s["session_id"],
                "tool_name": "get_issue",
                "write_count_for_call": 0,
                "executor_invocations": 1,
                "effect_digest": digest(text),
                "comment_id": None,
            },
        },
    )
    return source


class FakeJudge:
    model = "fake-only"

    def __init__(
        self, relation="DATA_DEPENDENT", use="TASK_DATA", delay=0, invalid=False, failed=False
    ):
        self.relation, self.use, self.delay, self.invalid, self.failed = (
            relation,
            use,
            delay,
            invalid,
            failed,
        )
        self.calls = 0
        self.entered = asyncio.Event()

    async def analyze(self, snapshot):
        self.calls += 2
        a_input, b_input = inputs(snapshot, "A"), inputs(snapshot, "B")
        assert "sources" not in a_input and "sources" in b_input
        assert "expected_decision" not in str(a_input) + str(b_input)
        self.entered.set()
        await asyncio.sleep(self.delay)
        if self.failed:
            raise TimeoutError()
        a = {
            "task_relation": self.relation,
            "external_use": "NONE",
            "reason": "USER_INTENT_SUPPORTED",
            "evidence_refs": [
                {
                    "source_id": "user_request",
                    "start": 0,
                    "end": 3,
                    "quote": snapshot["user_request"][:3],
                }
            ],
        }
        source = snapshot["sources"][0]
        b = {
            "task_relation": self.relation,
            "external_use": self.use,
            "reason": "TASK_DATA_SUPPORTED",
            "evidence_refs": [
                {
                    "source_id": source["source_id"],
                    "start": 0,
                    "end": 3,
                    "quote": source["analysis_text"][:3],
                }
            ],
        }
        if self.invalid:
            b["evidence_refs"][0]["source_id"] = "forged-source"
        return a, b


def execute(repo, s, value, checked):
    reserved = repo.reserve(
        checked["call_id"], {k: value[k] for k in ("tool_name", "backend_id", "args")}
    )
    if reserved["execute"]:
        executor = DemoExecutor(repo.path + ".effects")
        _, receipt = executor.execute(
            checked["call_id"], s["session_id"], value["tool_name"], value["args"]
        )
        repo.report(
            checked["call_id"],
            {
                "reservation_id": reserved["reservation_id"],
                "state": "SUCCEEDED",
                "receipt": receipt,
            },
        )
    with sqlite3.connect(repo.path + ".effects") as db:
        return db.execute(
            "SELECT count(*) FROM comments WHERE session_id=?", (s["session_id"],)
        ).fetchone()[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "use,decision", [("TASK_DATA", "ALLOW"), ("NEW_INSTRUCTION", "DENY"), ("UNCERTAIN", "CONFIRM")]
)
async def test_f3_03_04_08_fake_observations_and_real_atomic_effect(repo, use, decision):
    s = session(repo)
    read(repo, s)
    value = call(s)
    judge = FakeJudge(use=use)
    result = await repo.check_async(value, judge)
    assert (
        result["decision"] == decision
        and result["analysis_id"]
        and result["decision_stage"] == "SEMANTIC"
    )
    assert judge.calls == 2 and await repo.check_async(value, judge) == result and judge.calls == 2
    if decision == "DENY":
        assert result["approval_id"] is None
        with pytest.raises(SafeError):
            repo.reserve(
                result["call_id"], {k: value[k] for k in ("tool_name", "backend_id", "args")}
            )
    else:
        if decision == "CONFIRM":
            with pytest.raises(SafeError):
                repo.reserve(
                    result["call_id"], {k: value[k] for k in ("tool_name", "backend_id", "args")}
                )
            repo.approve(result["approval_id"], result["args_sha256"])
        assert execute(repo, s, value, result) == 1
        assert execute(repo, s, value, result) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", ["missing", "incomplete", "bad_ref", "timeout", "refusal", "cancel"]
)
async def test_f3_07_09_fail_closed_no_approval(repo, failure):
    s = session(repo)
    if failure != "missing":
        read(repo, s, complete=failure != "incomplete")
    judge = FakeJudge(
        delay=10 if failure == "cancel" else 0,
        invalid=failure == "bad_ref",
        failed=failure in ("timeout", "refusal"),
    )
    value = call(s)
    if failure == "cancel":
        task = asyncio.create_task(repo.check_async(value, judge))
        await judge.entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        result = await repo.check_async(value, judge)
    else:
        result = await repo.check_async(value, judge)
    assert result["decision"] == "DENY" and result["approval_id"] is None
    with pytest.raises(SafeError):
        repo.reserve(result["call_id"], {k: value[k] for k in ("tool_name", "backend_id", "args")})
    assert not __import__("pathlib").Path(repo.path + ".effects").exists()
    assert judge.calls == (0 if failure in ("missing", "incomplete") else 2)


@pytest.mark.asyncio
async def test_f3_10_single_flight_no_long_db_lock_stale_and_conflict(repo):
    s = session(repo)
    read(repo, s)
    value = call(s)
    judge = FakeJudge(delay=0.1)
    task = asyncio.create_task(repo.check_async(value, judge))
    await judge.entered.wait()
    pending = await repo.check_async(value, judge)
    assert pending["reason_codes"] == ["ANALYSIS_IN_PROGRESS"] and judge.calls == 2
    conflict = {**value, "args": {"issue_id": 42, "body": "다른값"}}
    with pytest.raises(SafeError, match="REQUEST_KEY_CONFLICT"):
        await repo.check_async(conflict, judge)
    # Actual second connection writes while model work is waiting.
    with repo.tx() as db:
        db.execute("UPDATE sessions SET status='CLOSED' WHERE id=?", (s["session_id"],))
    result = await task
    assert result["reason_codes"] == ["ANALYSIS_STALE"] and result["approval_id"] is None


@pytest.mark.asyncio
async def test_f3_10_reserve_snapshot_mutation_and_policy_migration(repo):
    s = session(repo)
    source = read(repo, s)
    value = call(s)
    result = await repo.check_async(value, FakeJudge())
    with repo.tx() as db:
        db.execute(
            "UPDATE source_analysis SET text_sha256=? WHERE source_id=?",
            ("0" * 64, source["source_id"]),
        )
    with pytest.raises(SafeError, match="ANALYSIS_STALE"):
        execute(repo, s, value, result)
    with repo.tx() as db:
        db.execute(
            "UPDATE sessions SET policy_version='mvp-2026-10-13-v1' WHERE id=?", (s["session_id"],)
        )
    with pytest.raises(SafeError, match="POLICY_CHANGED"):
        repo.check(call(s))
    assert repo.timeline(s["session_id"])["policy_version"] != POLICY


@pytest.mark.asyncio
async def test_f3_09_10_lease_expiry_and_semantic_session_budget(repo):
    now = [1000000.0]
    repo.clock = lambda: now[0]
    s = session(repo)
    read(repo, s)
    value = call(s)
    pending, snapshot = repo.prepare_check(value, "fake-only")
    now[0] += 21
    expired = await repo.check_async(value,FakeJudge())
    assert (
        expired["reason_codes"] == ["ANALYSIS_UNAVAILABLE"]
        and expired["call_id"] == pending["call_id"]
    )
    assert repo.finish_analysis(snapshot, FakeJudge()) == expired
    await repo.check_async(call(s, body="두 번째 후보"), FakeJudge())
    judge = FakeJudge()
    third = await repo.check_async(call(s, body="세 번째 후보"), judge)
    assert third["decision"] == "DENY" and judge.calls == 0


@pytest.mark.asyncio
async def test_f3_01_02_hard_policy_has_zero_judge_calls_and_no_agent_grants(repo):
    s = session(repo, "EXACT")
    judge = FakeJudge()
    exact = call(s, body="검토 완료")
    checked = await repo.check_async(exact, judge)
    assert (
        checked["decision"] == "ALLOW"
        and checked["decision_stage"] == "POLICY"
        and checked["analysis_id"] is None
    )
    assert execute(repo, s, exact, checked) == 1 and judge.calls == 0
    summary = repo.create_session(
        {"task_kind": "SUMMARIZE_ISSUE", "issue_id": 42, "user_request": "요약만"}
    )
    denied = await repo.check_async(call(summary), judge)
    assert denied["decision"] == "DENY" and judge.calls == 0
    with pytest.raises(SafeError):
        repo.create_session(
            {
                "task_kind": "POST_COMMENT",
                "comment_mode": "ISSUE_SUMMARY",
                "issue_id": 42,
                "user_request": REQUEST,
                "allowed_comment_body": "agent-created grant",
            }
        )


def test_f3_07_analysis_material_unicode_secret_and_encrypted_storage(repo):
    text = "한글" * 5000
    analysis = material(text)
    assert (
        len(analysis["analysis_text"]) <= 8192 and len(analysis["analysis_text"].encode()) <= 16384
    )
    assert (
        not analysis["analysis_complete"]
        and not material("DEMO_SECRET_DO_NOT_SEND")["analysis_complete"]
    )
    s = session(repo)
    read(repo, s, text="public-snapshot-canary")
    assert b"public-snapshot-canary" not in __import__("pathlib").Path(repo.path).read_bytes()
