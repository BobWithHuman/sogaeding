"""macOS/POSIX product launcher. Host needs only Python's standard library."""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

IMAGE = "with-human-engine:local"
ROLES = ("ca.pem", "machine.id", "machine.token", "human.token")
MODES = ("build", "prepare", "up", "check", "start", "dashboard",
         "dashboard-stop", "history", "security", "status", "down")


def no_links(path):
    path = path.absolute()
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("SYMLINK_PATH_REJECTED")
    return path


def private_directory(path, *, new=False):
    no_links(path)
    if new:
        path.mkdir(mode=0o700)  # Exclusive: never replace another runtime.
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("PRIVATE_DIRECTORY_REQUIRED")


def private_parents(path):
    no_links(path)
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for item in (current, *current.parents):
        info = item.stat()
        if not stat.S_ISDIR(info.st_mode) or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
            raise ValueError("UNSAFE_PARENT_DIRECTORY")
    for item in reversed(missing):
        item.mkdir(mode=0o700)


def write_private(path, value):
    no_links(path)
    data = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def read_private(path):
    no_links(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 65536):
            raise ValueError("PRIVATE_FILE_REQUIRED_CHMOD_600")
        return stream.read(65537)


def port(value):
    value = int(value)
    if not 1024 <= value <= 65535:
        raise argparse.ArgumentTypeError("port must be 1024..65535")
    return value


def install_provider(runtime):
    """Container-side stdin import; only Control mounts this private directory."""
    payload = json.load(sys.stdin)
    if set(payload) != {"key", "policy"}:
        raise ValueError("INVALID_PROVIDER_BUNDLE")
    destination = runtime / "control-provider"
    private_directory(destination, new=True)
    write_private(destination / "jev.api-key", base64.b64decode(payload["key"], validate=True))
    write_private(destination / "policy.json", payload["policy"])


def provider_mounts(config, runtime_name):
    """Adapt two mounts in resolved Compose JSON; no new YAML or host secrets."""
    replaced = set()
    for index, mount in enumerate(config["services"]["control"]["volumes"]):
        if mount["target"] in ("/jev-key/jev.api-key", "/jev-config/policy.json"):
            target = "/jev-key" if mount["target"].startswith("/jev-key/") else "/jev-config"
            config["services"]["control"]["volumes"][index] = {
                "type": "volume", "source": "team-runtime", "target": target,
                "read_only": True, "volume": {"subpath": f"artifacts/team-dev/{runtime_name}/control-provider"}}
            replaced.add(target)
    if replaced != {"/jev-key", "/jev-config"}:
        raise ValueError("COMPOSE_PROVIDER_MOUNT_CONTRACT_CHANGED")
    return config


class Product:
    def __init__(self, root, name, *, home=None):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", name):
            raise ValueError("INVALID_RUNTIME_NAME")
        self.root = root.resolve()
        self.name = name
        self.root_id = hashlib.sha256(str(self.root).lower().encode()).hexdigest()[:8]
        self.project = f"sogaeding-team-{self.root_id}-{name}"
        self.volume = self.project + "-runtime"
        home = (home or Path.home()).resolve()
        base = home / ("Library/Application Support" if sys.platform == "darwin" else ".local/share")
        self.client = base / "WithHuman/Codex" / self.root_id / name
        self.host = self.client / "host"
        self.runtime = self.root / "artifacts/team-dev" / name
        self.settings = self.client / "connection.json"

    def run(self, args, *, capture=False, input_text=None, env=None):
        # No shell, no credential output/traceback on subprocess failure.
        result = subprocess.run([str(arg) for arg in args], cwd=self.root, env=env,
                                text=True, input=input_text, capture_output=capture, check=False)
        if result.returncode:
            raise ValueError("LOCAL_COMMAND_FAILED_NO_AUTOMATIC_RETRY")
        return result.stdout if capture else ""

    def docker(self, *args, **kwargs):
        return self.run(["docker", *args], **kwargs)

    def mount(self, source, target, *, volume=False, readonly=False):
        if any(c in str(source) for c in (",", "\n", "\r", "\x00")):
            raise ValueError("UNSUPPORTED_MOUNT_PATH")
        return f"type={'volume' if volume else 'bind'},source={source},target={target}" + (",readonly" if readonly else "")

    def container(self, command, *, volume=True, capture=False, input_text=None, owner=False):
        args = ["run", "--rm", "--log-driver", "none", "--pull", "never", "--network", "none",
                "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--tmpfs", "/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1"]
        if input_text is not None:
            args += ["-i"]
        if owner:
            args += ["--user", "0:0", "--cap-add", "CHOWN"]
        args += ["--mount", self.mount(self.root / "tools", "/tools", readonly=True)]
        if volume:
            args += ["--mount", self.mount(self.volume, "/team", volume=True, readonly=capture)]
        return self.docker(*args, IMAGE, "python", *command, capture=capture, input_text=input_text)

    def build(self):
        if self.docker("info", "--format", "{{.OSType}}", capture=True).strip() != "linux":
            raise ValueError("DOCKER_DESKTOP_LINUX_CONTAINERS_REQUIRED")
        self.docker("build", "--target", "runtime", "-f", "Dockerfile", "-t", IMAGE, ".")

    def prepare(self, key, control, gateway, dashboard):
        if len({control, gateway, dashboard}) != 3:
            raise ValueError("DISTINCT_PORTS_REQUIRED")
        if key is None:
            raise ValueError("EXTERNAL_JEV_KEY_FILE_REQUIRED")
        key = no_links(key.expanduser().absolute())
        if key.resolve().is_relative_to(self.root):
            raise ValueError("KEEP_JEV_KEY_OUTSIDE_REPOSITORY")
        key_data = read_private(key)
        if not key_data.strip():
            raise ValueError("EMPTY_JEV_KEY_FILE")
        no_links(self.runtime)
        no_links(self.client)
        if self.runtime.exists() or self.client.exists():
            raise ValueError("EXISTING_RUNTIME_PRESERVED_CHOOSE_NEW_NAME")
        # Confirm volume absence before building/creating anything.
        if self.volume in self.docker("volume", "ls", "--format", "{{.Name}}", capture=True).splitlines():
            raise ValueError("EXISTING_VOLUME_PRESERVED_CHOOSE_NEW_NAME")
        self.build()
        private_parents(self.runtime.parent)
        private_directory(self.runtime, new=True)
        private_parents(self.client.parent)
        private_directory(self.client, new=True)
        self.docker("volume", "create", "--label", "sogaeding.team=" + self.project, self.volume)
        self.container(["-c", "import os; os.chown('/team',10001,10001)"], owner=True)
        self.container(["/tools/team_runtime.py", "prepare", "/team", "--name", self.name])
        write_private(self.runtime / "prepared.json", {"volume": self.volume, "root_id": self.root_id})
        policy = {"enabled": True, "model": "jev-1.13.0", "request_limit": None,
                  "input_token_limit": None, "unlimited": True, "policy_id": "codex-gate6-" + self.name}
        write_private(self.runtime / "jev-policy.json", policy)
        # POSIX 0600 host files are not readable by container uid 10001. Import
        # once over stdin into a role-scoped volume; never relax the host file.
        self.container(["-c", "import sys; from pathlib import Path; sys.path.insert(0,'/tools'); "
                        "from product_local import install_provider; install_provider(Path(sys.argv[1]))",
                        "/team/artifacts/team-dev/" + self.name],
                       input_text=json.dumps({"key": base64.b64encode(key_data).decode(), "policy": policy}))
        bundle = json.loads(self.container(["/tools/product_codex.py", "export-bundle", "--runtime",
                                           "/team/artifacts/team-dev/" + self.name], capture=True))
        if set(bundle) != set(ROLES):
            raise ValueError("INVALID_CREDENTIAL_BUNDLE")
        private_directory(self.host, new=True)
        for name in ROLES:
            data = base64.b64decode(bundle[name], validate=True)
            if not 1 <= len(data) <= 8192:
                raise ValueError("INVALID_CREDENTIAL_BUNDLE")
            write_private(self.host / name, data)
        write_private(self.host / "profile.json", {"format": "product-codex-1", "workspace": str(self.root),
                      "engine_workspace": "/files", "mcp_only": True,
                      "control_url": f"https://127.0.0.1:{control}", "gateway_url": f"https://127.0.0.1:{gateway}/mcp"})
        write_private(self.settings, {"format": "product-local-1", "workspace": str(self.root),
                      "key_file": str(key), "key_sha256": hashlib.sha256(key_data).hexdigest(),
                      "control_port": control, "gateway_port": gateway,
                      "dashboard_port": dashboard})
        print("Prepared local engine and Codex client; model requests 0. Next: up, check, dashboard, start.")

    def configuration(self):
        private_directory(self.client)
        private_directory(self.host)
        for name in (*ROLES, "profile.json"):
            read_private(self.host / name)
        data = json.loads(read_private(self.settings))
        if data.get("format") != "product-local-1" or data.get("workspace") != str(self.root):
            raise ValueError("RUNTIME_WORKSPACE_MISMATCH")
        ports = [data[k] for k in ("control_port", "gateway_port", "dashboard_port")]
        if any(type(p) is not int or not 1024 <= p <= 65535 for p in ports) or len(set(ports)) != 3:
            raise ValueError("INVALID_SAVED_PORTS")
        prepared = json.loads(read_private(self.runtime / "prepared.json"))
        if prepared != {"volume": self.volume, "root_id": self.root_id}:
            raise ValueError("RUNTIME_VOLUME_MISMATCH")
        return data

    def environment(self, data, *, need_key=True):
        key = no_links(Path(data["key_file"]))
        if need_key:
            if hashlib.sha256(read_private(key)).hexdigest() != data["key_sha256"]:
                raise ValueError("EXTERNAL_KEY_CHANGED_PREPARE_NEW_RUNTIME")
        networks_path = self.runtime / "networks.json"
        if not networks_path.exists():
            ids = self.docker("network", "ls", "-q", capture=True).splitlines()
            inventory = self.docker("network", "inspect", *ids, capture=True) if ids else "[]"
            selected = self.container(["/tools/team_runtime.py", "networks"], volume=False,
                                      capture=True, input_text=inventory)
            write_private(networks_path, json.loads(selected))
        networks = json.loads(read_private(networks_path))
        return {**os.environ, "SOGAEDING_TEAM_IMAGE": IMAGE, "SOGAEDING_TEAM_VOLUME": self.volume,
                "SOGAEDING_RUNTIME_NAME": self.name, "SOGAEDING_JEV_KEY_FILE": str(key),
                "SOGAEDING_JEV_POLICY_FILE": str(self.runtime / "jev-policy.json"),
                "SOGAEDING_CONTROL_PORT": str(data["control_port"]),
                "SOGAEDING_GATEWAY_PORT": str(data["gateway_port"]),
                "SOGAEDING_DASHBOARD_PORT": str(data["dashboard_port"]),
                "SOGAEDING_PROTECTED_SUBNET": networks["protected"], "SOGAEDING_INGRESS_SUBNET": networks["ingress"]}

    def compose(self, mode):
        data = self.configuration()
        env = self.environment(data, need_key=mode not in ("down", "dashboard-stop", "status"))
        commands = {"up": ["up", "-d", "control", "upstream", "gateway"],
                    "dashboard": ["up", "-d", "--no-deps", "dashboard"],
                    "dashboard-stop": ["stop", "dashboard"], "status": ["ps"],
                    "down": ["--profile", "dashboard", "down"]}
        config = json.loads(self.docker("compose", "-p", self.project, "-f", "compose.yaml",
                                        "--profile", "dashboard", "--profile", "verification",
                                        "config", "--format", "json", capture=True, env=env))
        config = provider_mounts(config, self.name)
        self.docker("compose", "--project-directory", self.root, "-p", self.project, "-f", "-",
                    *commands[mode], input_text=json.dumps(config), env=env)
        if mode == "dashboard":
            print("Local dashboard: http://127.0.0.1:" + str(data["dashboard_port"]))

    def connect(self, mode, executable=None, *, engine_only=False):
        self.configuration()
        helper = [sys.executable, "-I", str(self.root / "tools/product_codex.py")]
        args = ["--host", str(self.host)]
        if mode in ("check", "start") and not engine_only:
            executable = Path(executable).expanduser() if executable else Path(shutil.which("codex") or "")
            if not executable.is_file() or not os.access(executable, os.X_OK):
                raise ValueError("INSTALLED_CODEX_REQUIRED_OR_USE_CHECK_ENGINE_ONLY")
            executable = executable.resolve()
            if mode == "check":
                self.run([*helper, "cli-check", *args, "--exe", executable])
            else:
                self.run([*helper, "start", *args, "--exe", executable])
                return
        self.run([*helper, mode, *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("--runtime", default="local")
    parser.add_argument("--jev-key-file", type=Path)
    parser.add_argument("--codex-path")
    parser.add_argument("--engine-only", action="store_true", help="check without Codex, for dashboard developers")
    parser.add_argument("--control-port", type=port, default=8130)
    parser.add_argument("--gateway-port", type=port, default=8140)
    parser.add_argument("--dashboard-port", type=port, default=8150)
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("Use scripts/product_codex.ps1 on Windows. This launcher requires macOS/POSIX permissions.")
    if sys.version_info < (3, 12):
        parser.error("Python 3.12 or newer required")
    if args.engine_only and args.mode != "check":
        parser.error("--engine-only is valid for check only")
    previous = os.umask(0o077)
    try:
        product = Product(Path(__file__).resolve().parents[1], args.runtime)
        if args.mode == "build":
            product.build()
        elif args.mode == "prepare":
            product.prepare(args.jev_key_file, args.control_port, args.gateway_port, args.dashboard_port)
        elif args.mode in ("check", "start", "history", "security"):
            product.connect(args.mode, args.codex_path, engine_only=args.engine_only)
        else:
            product.compose(args.mode)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        # Never echo subprocess output, credentials or arbitrary exception text.
        code = str(error) if isinstance(error, ValueError) and re.fullmatch(r"[A-Z0-9_]+", str(error)) else type(error).__name__
        print("LOCAL_PRODUCT_FAILED: " + code + ". Existing state preserved; no automatic retry.", file=sys.stderr)
        return 2
    finally:
        os.umask(previous)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
