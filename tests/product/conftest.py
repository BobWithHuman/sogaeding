"""Product-only fixtures; no DTAP modules, API keys or model requests."""
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from app.transparent.engine import Engine
from app.transparent.jev import MODEL, validate_response
from app.transparent.jev_config import make_policy


class Observer:
    is_fixture = True

    def __init__(self, *, a="WITHIN_TASK", b="LEGITIMATE", a_confidence=1., b_confidence=.8):
        self.a, self.b = a, b
        self.a_confidence, self.b_confidence = a_confidence, b_confidence
        self.calls = []
        self.settings = SimpleNamespace(authorized=lambda:False)

    async def observe(self, view, state, questions, analysis_id):
        self.calls.append((view, state))
        answers = {}
        for name, question in questions.items():
            choices = question["criteria"]
            behavior = name in ("behavior", "current_behavior", "benchmark_behavior")
            scope = name == "task_relation"
            selected = self.b if behavior else self.a if scope else "UNCERTAIN"
            confidence = self.b_confidence if behavior else self.a_confidence if scope else 1.
            # Keep computed confidence above the supplied provider value so exact
            # .50 provider boundaries do not depend on a repeating binary fraction.
            probability = min(1., (confidence * (len(choices)-1)+1)/len(choices)+1e-12)
            answers[name] = {"type": "choice", "choice": selected, "confidence": confidence,
                             "probabilities": {c: probability if c == selected else
                                               (1-probability)/(len(choices)-1) for c in choices}}
        return validate_response({"model": MODEL, "answers": answers,
                                  "usage": {"input_tokens": None, "output_tokens": None}}, questions)[0]


@pytest.fixture
def observer():
    return Observer()


@pytest.fixture
def engine_factory(tmp_path, observer):
    created=[]
    def create(resource_rules=None):
        path=tmp_path/str(len(created))/"control.sqlite3"
        grant={"workspace":"/files","tools":{"mcp":["read_file","write_file"],"native":[]}}
        if resource_rules is not None:
            grant["gate6_resource_rules"]=resource_rules
        value=Engine(path,Fernet.generate_key(),grant,policy_router=make_policy(observer))
        created.append(value)
        return value
    return create


@pytest.fixture
def engine(engine_factory):
    return engine_factory()
