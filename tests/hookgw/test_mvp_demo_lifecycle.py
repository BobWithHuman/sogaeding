"""Real subprocess lifecycle; temporary synthetic effects, provider zero."""
import importlib.util
import os
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("lifecycle_tests", ROOT / "tools/mvp_demo_lifecycle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("code,outcome", [(0, "EXITED"), (7, "EXITED_NONZERO")])
def test_actual_exit_and_os_stdio_not_captured(tmp_path, code, outcome):
    module, events, order = load(), [], []
    value = module.run([sys.executable, "-I", "-c", f"raise SystemExit({code})"], cwd=tmp_path, env=os.environ.copy(),
                       wall_seconds=2, event_sink=events.append, before_stop=lambda: order.append("revoke") or True)
    assert value["outcome"] == outcome and value["exit_code"] == code
    assert value["connection_closed"] == "VERIFIED" and order == ["revoke"]
    assert events[0]["event"] == "STARTING" and events[1]["event"] == "FINISHED"
    assert 0 <= value["elapsed_seconds"] <= 5 and value["ended_utc"] >= value["started_utc"]


@pytest.mark.parametrize("cancel", [False, True])
def test_actual_timeout_or_cancel_kills_child_delayed_effect(tmp_path, cancel):
    module, events = load(), []
    effect = tmp_path / "late.txt"
    child = tmp_path / "child.py"
    child.write_text("import time;from pathlib import Path;time.sleep(4);Path('late.txt').write_text('PUBLIC')", encoding="utf-8")
    event = threading.Event()
    if cancel:
        timer = threading.Timer(0.2, event.set)
        timer.start()
    value = module.run([sys.executable, "-I", str(child)], cwd=tmp_path, env=os.environ.copy(), wall_seconds=1,
                       event_sink=events.append, cancel_event=event, before_stop=lambda: True)
    assert value["outcome"] == ("INTERRUPTED" if cancel else "TIMEOUT")
    assert value["tree_cleanup"] == "VERIFIED" and value["exit_code"] is None
    time.sleep(0.1)
    assert not effect.exists()
    assert len(events) == 2


def test_launch_failure_and_failed_control_revoke(tmp_path):
    module, events = load(), []
    value = module.run([str(tmp_path / "absent-executable")], cwd=tmp_path, env=os.environ.copy(), wall_seconds=1, event_sink=events.append)
    assert value["outcome"] == "LAUNCH_FAILED" and value["started"] is False
    value = module.run([sys.executable, "-I", "-c", "pass"], cwd=tmp_path, env=os.environ.copy(), wall_seconds=2,
                       event_sink=lambda _: None, before_stop=lambda: False)
    assert value["connection_closed"] == "UNVERIFIED" and value["tree_cleanup"] == "VERIFIED"


def test_interrupt_inside_shutdown_cannot_skip_tree_cleanup(tmp_path):
    module, events = load(), []
    def interrupted():
        raise KeyboardInterrupt
    value = module.run([sys.executable, "-I", "-c", "import time;time.sleep(10)"], cwd=tmp_path, env=os.environ.copy(),
                       wall_seconds=1, event_sink=events.append, before_stop=interrupted)
    assert value["outcome"] == "INTERRUPTED" and value["connection_closed"] == "UNVERIFIED"
    assert value["tree_cleanup"] == "VERIFIED" and events[-1]["event"] == "FINISHED"
