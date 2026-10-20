"""A provider using public DNS during process startup must already have egress."""

import pytest

from app.benchmark.docker_sandbox import DockerSandbox


class BootProbe:
    create_broker = DockerSandbox.create_broker

    def __init__(self, public_dns=False, reject_attach=False):
        self.public_dns, self.reject_attach = public_dns, reject_attach
        self.events = []

    def create(self, name, image, command, **kwargs):
        self.events.append(("boot", kwargs))
        if self.public_dns and kwargs["network"] != "bridge":
            raise OSError("STARTUP_DNS_UNAVAILABLE")
        return "synthetic-broker"

    def connect(self, container, network, aliases):
        if self.reject_attach:
            raise OSError("ATTACH_FAILED")
        self.events.append(("connect", network, aliases))


def test_live_boot_can_resolve_before_internal_networks_are_attached():
    box = BootProbe(public_dns=True)
    assert (
        box.create_broker("b", "image", ["broker"], off_network="off", on_network="on", live=True)
        == "synthetic-broker"
    )
    boot = box.events[0][1]
    assert boot["network"] == "bridge" and boot["kind"] == "provider-broker"
    assert box.events[1:] == [("connect", "off", ("broker",)), ("connect", "on", ("broker",))]


@pytest.mark.parametrize("on", ["off", "on"])
def test_offline_broker_has_no_external_network(on):
    box = BootProbe()
    box.create_broker("b", "image", [], off_network="off", on_network=on, live=False)
    assert box.events[0][1]["network"] == "off"
    assert all(event[1] != "bridge" for event in box.events[1:])
    assert len(box.events) == (1 if on == "off" else 2)


def test_attach_failure_never_returns_a_ready_broker():
    box = BootProbe(reject_attach=True)
    with pytest.raises(OSError, match="ATTACH_FAILED"):
        box.create_broker("b", "image", [], off_network="off", on_network="on", live=True)
