"""Trusted controller Docker transport; only this experiment's objects mutate.

No Docker socket/host paths/management keys are exposed to victim tool servers
or business environments. TaskExecutor owns scheduling; this is its isolated
environment backend, not another evaluation runner.
"""

from urllib.parse import quote

import httpx


class SandboxError(RuntimeError):
    pass


class DockerSandbox:
    def __init__(self, experiment, *, socket="/var/run/docker.sock"):
        self.experiment = experiment
        self.client = httpx.Client(
            transport=httpx.HTTPTransport(uds=socket),
            base_url="http://docker/v1.47",
            timeout=120,
            trust_env=False,
        )

    def request(self, method, path, **kwargs):
        response = self.client.request(method, path, **kwargs)
        if response.status_code >= 400:
            # Docker errors may contain environment configuration. Keep public
            # diagnostics stable, retain only status/operation here.
            raise SandboxError(
                "DOCKER_" + str(response.status_code) + "_" + method + "_" + path.split("?")[0]
            )
        return response.json() if response.content else None

    def owned(self, identity, kind="containers"):
        value = (
            self.request("GET", "/" + kind + "/" + quote(identity, safe="") + "/json")
            if kind == "containers"
            else self.request("GET", "/networks/" + quote(identity, safe=""))
        )
        labels = (
            value.get("Config", {}).get("Labels", {})
            if kind == "containers"
            else value.get("Labels", {})
        )
        if labels.get("with-human.dtap.experiment") != self.experiment:
            raise SandboxError("FOREIGN_DOCKER_OBJECT_PRESERVED")
        return value

    def network(self, name, subnet):
        found = self.client.get("/networks/" + name)
        if found.status_code == 200:
            value = found.json()
            if value.get("Labels", {}).get("with-human.dtap.experiment") != self.experiment:
                raise SandboxError("FOREIGN_NETWORK_NAME_COLLISION")
            if value.get("IPAM", {}).get("Config") != [
                {"Subnet": subnet, "Gateway": subnet.rsplit(".", 1)[0] + ".1"}
            ]:
                existing = [row.get("Subnet") for row in value.get("IPAM", {}).get("Config", [])]
                if existing != [subnet]:
                    raise SandboxError("NETWORK_SUBNET_DRIFT")
            return value["Id"]
        if found.status_code != 404:
            raise SandboxError("NETWORK_INSPECTION_FAILED")
        # Never prune/delete another network to make room.
        all_networks = self.request("GET", "/networks")
        import ipaddress

        target = ipaddress.ip_network(subnet)
        for network in all_networks:
            for row in network.get("IPAM", {}).get("Config") or []:
                if row.get("Subnet") and target.overlaps(ipaddress.ip_network(row["Subnet"])):
                    raise SandboxError("NETWORK_SUBNET_COLLISION_PRESERVE_EXISTING")
        return self.request(
            "POST",
            "/networks/create",
            json={
                "Name": name,
                "Internal": True,
                "Labels": {"with-human.dtap.experiment": self.experiment},
                "IPAM": {"Config": [{"Subnet": subnet}]},
            },
        )["Id"]

    def inspect(self, identity):
        return self.request("GET", "/containers/" + quote(identity, safe="") + "/json")

    def create(
        self,
        name,
        image,
        command,
        *,
        network=None,
        aliases=(),
        namespace=None,
        env=None,
        mounts=(),
        kind="runtime",
        ports=None,
        memory=536870912,
        cap_add=(),
        user="10001:10001",
        readonly=True,
    ):
        existing = self.client.get("/containers/" + name + "/json")
        if existing.status_code == 200:
            self.owned(name)
            raise SandboxError("EXISTING_CONTAINER_PRESERVED_NO_REPLACEMENT")
        host = {
            "ReadonlyRootfs": readonly,
            "CapDrop": ["ALL"],
            "CapAdd": list(cap_add),
            "SecurityOpt": ["no-new-privileges:true"],
            "PidsLimit": 128,
            "Memory": memory,
            "NanoCpus": 1000000000,
            "Tmpfs": {"/tmp": "rw,size=134217728,mode=1777"},
            "Mounts": list(mounts),
            "NetworkMode": "container:" + namespace if namespace else network or "none",
        }
        config = {
            "Image": image,
            "Cmd": list(command),
            "User": user,
            "Env": [str(k) + "=" + str(v) for k, v in (env or {}).items()],
            "Labels": {"with-human.dtap.experiment": self.experiment, "with-human.dtap.kind": kind},
            "HostConfig": host,
        }
        if network and not namespace:
            config["NetworkingConfig"] = {"EndpointsConfig": {network: {"Aliases": list(aliases)}}}
        if ports:
            config["ExposedPorts"] = {str(port) + "/tcp": {} for port in ports}
            host["PortBindings"] = {
                str(port) + "/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(hostport)}]
                for port, hostport in ports.items()
            }
        value = self.request("POST", "/containers/create?name=" + quote(name, safe=""), json=config)
        self.request("POST", "/containers/" + value["Id"] + "/start")
        return value["Id"]

    def create_broker(self, name, image, command, *, off_network, on_network, live, **kwargs):
        # create() starts the process immediately. LIVE startup can already need
        # public DNS/OAuth, so its external network must exist at creation time.
        cid = self.create(
            name,
            image,
            command,
            network="bridge" if live else off_network,
            aliases=() if live else ("broker",),
            kind="provider-broker",
            **kwargs,
        )
        if live:
            self.connect(cid, off_network, ("broker",))
        if on_network != off_network:
            self.connect(cid, on_network, ("broker",))
        return cid

    def connect(self, container, network, aliases=()):
        self.owned(container)
        self.owned(network, "networks")
        self.request(
            "POST",
            "/networks/" + network + "/connect",
            json={"Container": container, "EndpointConfig": {"Aliases": list(aliases)}},
        )

    def exec(self, container, command, *, timeout=120):
        self.owned(container)
        eid = self.request(
            "POST",
            "/containers/" + container + "/exec",
            json={"AttachStdout": True, "AttachStderr": True, "Cmd": list(command)},
        )["Id"]
        response = self.client.post(
            "/exec/" + eid + "/start", json={"Detach": False, "Tty": False}, timeout=timeout
        )
        response.raise_for_status()
        raw = response.content
        # Docker multiplexed stdout/stderr stream (8-byte header per frame).
        out = bytearray()
        position = 0
        while position + 8 <= len(raw):
            length = int.from_bytes(raw[position + 4 : position + 8], "big")
            position += 8
            out.extend(raw[position : position + length])
            position += length
        state = self.request("GET", "/exec/" + eid + "/json")
        return state["ExitCode"], out.decode("utf-8", errors="replace")

    def wait(self, container, *, timeout):
        self.owned(container)
        result = self.request(
            "POST",
            "/containers/" + container + "/wait",
            params={"condition": "not-running"},
            timeout=timeout,
        )
        return result["StatusCode"]

    def stop(self, container):
        value = self.owned(container)
        if value["State"]["Running"]:
            self.request("POST", "/containers/" + container + "/stop?t=10")

    def remove(self, container):
        self.owned(container)
        self.stop(container)
        self.request("DELETE", "/containers/" + container, params={"v": "true"})

    def snapshot(self, container, tag, *, reserve=None):
        value = self.owned(container)
        if value["Config"]["Labels"].get("with-human.dtap.kind") != "environment":
            raise SandboxError("NEVER_SNAPSHOT_KEYS_OR_TRUSTED_WORKERS")
        if value.get("Mounts"):
            raise SandboxError("VOLUME_SNAPSHOT_ADAPTER_REQUIRED")
        self.stop(container)
        size = self.request(
            "GET", "/containers/" + container + "/json", params={"size": "true"}
        ).get("SizeRw")
        if type(size) is not int or size < 0:
            raise SandboxError("SNAPSHOT_SIZE_UNKNOWN_PRESERVE_CONTAINER")
        if reserve:
            reserve(tag, size)
        # Stopped environment image includes the COMPLETE writable root layer,
        # not four selected files. Kernel/clock are not image state.
        image = self.request(
            "POST",
            "/commit",
            params={
                "container": container,
                "repo": "with-human-dtap-state",
                "tag": tag,
                "pause": "true",
            },
        )["Id"]
        return {
            "image": image,
            "initial_source_image": value["Image"],
            "scope": "COMPLETE_STOPPED_CONTAINER_WRITABLE_FILESYSTEM_NO_VOLUMES",
            "memory_restoration": "ORIGINAL_ENTRYPOINT_FRESH_PROCESS",
            "clock_random": "NOT_FROZEN; persisted task data frozen in image",
            "writable_bytes": size,
        }

    def logs(self, container):
        self.owned(container)
        response = self.client.get(
            "/containers/" + container + "/logs", params={"stdout": 1, "stderr": 1}
        )
        response.raise_for_status()
        return response.content


def bind(source, target, readonly=True):
    return {"Type": "bind", "Source": str(source), "Target": target, "ReadOnly": readonly}
