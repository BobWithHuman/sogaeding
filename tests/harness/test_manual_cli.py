import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("manual_cli", Path(__file__).parents[2] / "tools/manual_cli.py")
manual = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manual)


def test_actor_environment_drops_parent_privileged_credentials(tmp_path, monkeypatch):
    for name in ("HUMAN_USER_TOKEN", "GATEWAY_SERVICE_TOKEN", "JUDGE_API_KEY", "OPENAI_BASE_URL", "CODEX_HOME"):
        monkeypatch.setenv(name, "private-parent-value")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-api-key")
    env = manual.actor_environment(tmp_path, {}, "fake-agent-token")
    assert env["OPENAI_API_KEY"] == "fake-api-key" and env["WITH_HUMAN_AGENT_SESSION_TOKEN"] == "fake-agent-token"
    assert "private-parent-value" not in env.values()
    assert env["CODEX_HOME"] == str(tmp_path / "codex-home")


def test_connect_prepares_without_starting_cli_or_creating_session(tmp_path, monkeypatch):
    paths = []
    monkeypatch.setenv("OPENAI_API_KEY", "fake-api-key")
    monkeypatch.setattr(manual, "EVIDENCE", tmp_path / "evidence")
    monkeypatch.setattr(manual, "programs", lambda: {"pwsh": "fake-pwsh", "python": "fake-python"})
    monkeypatch.setattr(manual, "trial_config", lambda p: tmp_path / "isolated-trial")

    def control(path, payload=None):
        paths.append((path, payload))
        if path.endswith("cli-binding"):
            return {"task_kind": "POST_COMMENT", "comment_mode": "ISSUE_SUMMARY", "issue_id": 42,
                    "request_sha256": manual.sha(manual.REQUEST)}
        return {"remaining": 12}

    monkeypatch.setattr(manual, "control", control)
    monkeypatch.setattr(manual.subprocess, "run", lambda *a, **kw: pytest.fail("No shell or model may start in prepare-only connect"))
    sid = "11111111-1111-4111-8111-111111111111"
    context, env = manual.connect(sid, "fake-agent-token-" * 4, enter=False)
    assert context["models_started"] == 0 and context["initial_input_observation"] == "NOT_OBSERVED"
    assert all(path != "/v1/sessions" for path, _ in paths)
    saved = (manual.EVIDENCE / (context["connection_id"] + ".json")).read_text()
    assert "fake-agent-token" not in saved and "fake-api-key" not in saved
    assert env["WITH_HUMAN_AGENT_SESSION_TOKEN"].startswith("fake-agent-token")


def test_actor_attempts_are_persistent_finite_and_not_refunded(tmp_path):
    dbpath = tmp_path / "episodes.sqlite3"
    manual.claim_episode("first", dbpath)
    with pytest.raises(sqlite3.IntegrityError):
        manual.claim_episode("first", dbpath)
    manual.claim_episode("second", dbpath)
    with pytest.raises(ValueError, match="ACTOR_BUDGET_EXHAUSTED"):
        manual.claim_episode("third", dbpath)
    with sqlite3.connect(dbpath) as db:
        assert db.execute("SELECT count(*) FROM episodes").fetchone()[0] == 2


def test_initial_input_is_only_claimed_when_observed_in_rollout(tmp_path):
    expected = manual.sha(manual.REQUEST)
    assert manual.input_observation(tmp_path, expected)["status"] == "NOT_OBSERVED"
    path = tmp_path / "codex-home/sessions/rollout.jsonl"
    path.parent.mkdir(parents=True)
    row = {"type": "event_msg", "payload": {"type": "user_message", "message": manual.REQUEST}}
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    observed = manual.input_observation(tmp_path, expected)
    assert observed["matches_dashboard"] is True and "message" not in observed
    row["payload"]["message"] = "different request"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert manual.input_observation(tmp_path, expected)["matches_dashboard"] is False


def test_user_invoked_start_has_no_prefilled_prompt_and_charges_episode_before_process(tmp_path, monkeypatch):
    cid = "11111111-1111-4111-8111-111111111111"
    context = {"session_id": cid, "trial_root": str(tmp_path), "programs": {"codex": "fake-codex"}, "models_started": 0}
    monkeypatch.setattr(manual, "EVIDENCE", tmp_path / "evidence")
    monkeypatch.setattr(manual, "context_for", lambda cid: context)
    monkeypatch.setattr(manual, "bind", lambda *args: None)
    monkeypatch.setattr(manual, "control", lambda *args: {"remaining": 12})
    monkeypatch.setenv("OPENAI_API_KEY", "fake-api-key")
    monkeypatch.setenv("WITH_HUMAN_AGENT_SESSION_TOKEN", "fake-agent-token")
    dbpath = tmp_path / "actor.sqlite3"
    real_claim = manual.claim_episode
    monkeypatch.setattr(manual, "claim_episode", lambda value: real_claim(value, dbpath))
    captured = {}

    class FakeProcess:
        pid = 12345
        def wait(self, timeout):
            captured["timeout"] = timeout
            return 0

    def popen(args, **kwargs):
        with sqlite3.connect(dbpath) as db:
            assert db.execute("SELECT count(*) FROM episodes").fetchone()[0] == 1
        captured.update({"args": args, **kwargs})
        return FakeProcess()

    monkeypatch.setattr(manual.subprocess, "Popen", popen)
    assert manual.start(cid) == 0
    assert captured["args"] == ["fake-codex", "--strict-config", "--no-alt-screen", "-C", str(tmp_path / "workspace")]
    assert captured["timeout"] == 180 and "stdin" not in captured
    assert captured["env"]["OPENAI_API_KEY"] == "fake-api-key"
    assert context["actor_attempt_recorded"] is True
    # FakeProcess alone was run; no actual Codex or paid API was started.


def test_actor_usage_is_observed_as_numbers_only(tmp_path):
    assert manual.rollout_usage(tmp_path)["status"] == "NOT_OBSERVED"
    path = tmp_path / "codex-home/sessions/rollout.jsonl"
    path.parent.mkdir(parents=True)
    row = {"type": "event_msg", "payload": {"type": "token_count", "info": {
        "total_token_usage": {"input_tokens": 100, "output_tokens": 12, "raw_secret": "not-persisted"}}}}
    path.write_text(json.dumps(row), encoding="utf-8")
    assert manual.rollout_usage(tmp_path) == {"status": "OBSERVED_ROLLOUT", "usage": {"input_tokens": 100, "output_tokens": 12}}


def test_windows_watchdog_stuck_taskkill_still_runs_direct_kill(monkeypatch):
    monkeypatch.setattr(manual.os, "name", "nt")
    def taskkill(*args, **kwargs):
        raise manual.subprocess.TimeoutExpired("taskkill", 5)
    monkeypatch.setattr(manual.subprocess, "run", taskkill)

    class FakeProcess:
        pid = 12345
        killed = False
        def poll(self):
            return 1 if self.killed else None
        def kill(self):
            self.killed = True
        def wait(self, timeout):
            assert timeout == 5 and self.killed
            return 1

    process = FakeProcess()
    assert manual.stop_process(process) == {"process_stop_confirmed": True, "tree_stop_status": "COMMAND_FAILED"}


def test_failed_direct_kill_is_reported_unconfirmed(monkeypatch):
    monkeypatch.setattr(manual.os, "name", "posix")

    class FakeProcess:
        def poll(self):
            return None
        def kill(self):
            raise OSError("private-kill-error")

    assert manual.stop_process(FakeProcess()) == {"process_stop_confirmed": False, "tree_stop_status": "NOT_APPLICABLE"}
