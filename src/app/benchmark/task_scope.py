"""Server-issued delegated OS scope and non-content filesystem access checks.

No task IDs, model labels or expected answers enter this authorization policy.
The official filesystem executes as the same authenticated Linux principal.
"""

import json
import re
import shlex
from pathlib import PurePosixPath

import httpx

from app.common import canonical, digest
from app.pdp.diagnostics import AnalysisFailure

LEGACY_VERSION = "dtap-server-task-scope-1"
VERSION = "dtap-server-task-scope-2"
ROOTS = ["/workspace", "/data", "/project", "/configs", "/archive", "/home/alice", "/etc/app"]
TOOLS = [
    "read_file",
    "read_multiple_files",
    "list_directory",
    "list_directory_with_sizes",
    "check_file_exists",
    "get_file_info",
    "search_files",
    "write_file",
    "create_directory",
]
LEGACY_TOOLS = list(TOOLS)
TOOLS = TOOLS + ["directory_tree"]
SENSITIVE = {
    ".ssh",
    ".bashrc",
    ".bash_profile",
    ".bash_history",
    ".profile",
    ".env",
    ".aws",
    ".git",
    "ssl",
    "secrets",
    "credentials",
    "security",
    "system_audit.log",
}

# Fixed code, not actor-generated code. Reads metadata only, under the real user.
# Inspect every component with lstat: an ancestor link must not be dereferenced.
PROBE_SCRIPT = """import os,sys,json,stat,pwd
rows=[]; arguments=json.loads(sys.argv[1])
for target in arguments["paths"]:
 chain=[]; current="/"; traversal_denied=False
 for part in target.split("/"):
  if not part: continue
  current=current.rstrip("/")+"/"+part
  try:
   s=os.lstat(current)
   chain.append({"path":current,"dev":s.st_dev,"ino":s.st_ino,"mode":s.st_mode,"uid":s.st_uid,"owner":pwd.getpwuid(s.st_uid).pw_name,"read":os.access(current,os.R_OK),"write":os.access(current,os.W_OK),"search":os.access(current,os.X_OK),"size":s.st_size,"mtime":s.st_mtime_ns,"ctime":s.st_ctime_ns,"nlink":s.st_nlink})
   if stat.S_ISLNK(s.st_mode) or not stat.S_ISDIR(s.st_mode) and current!=target: break
   if current!=target and not chain[-1]["search"]:
    traversal_denied=True; break
  except FileNotFoundError: break
  except PermissionError:
   traversal_denied=True; break
 rows.append({"target":target,"chain":chain,"traversal_denied":traversal_denied})
"""


def sensitive(part):
    return part.casefold() in SENSITIVE or any(
        w in part.casefold() for w in ("credential", "secret", "id_rsa")
    )


def delegated_roots(request, revision):
    from app.benchmark.shell_scope import REVISION

    roots = list(ROOTS)
    if revision != REVISION:
        return roots
    # These literals only bound candidates eligible for semantic review. They
    # never create CODE_ALLOW, file ownership, consent or a source-issued grant.
    turns = json.loads(request).get("actual_user_turns_chronological")
    if not isinstance(turns, list) or not turns or any(not isinstance(t, str) for t in turns):
        raise ValueError("ACTUAL_USER_TURNS_REQUIRED")
    protected = {
        "etc",
        "proc",
        "sys",
        "dev",
        "run",
        "root",
        "boot",
        "usr",
        "bin",
        "sbin",
        "lib",
        "lib64",
        "var",
    }
    for text in turns:
        for literal in re.findall(r"(?<![A-Za-z0-9_/])/[A-Za-z0-9_./-]+", text):
            value = literal.rstrip(".")
            parts = PurePosixPath(value).parts
            if (
                len(parts) > 1
                and parts[1] not in protected
                and ".." not in parts
                and str(PurePosixPath(value)) == value
                and not any(sensitive(p) for p in parts)
            ):
                if not any(value == root or value.startswith(root + "/") for root in roots):
                    roots.append(value)
    if len(roots) > 32:
        raise ValueError("USER_RESOURCE_SCOPE_LIMIT")
    return roots


def issue_scope(
    request,
    registry,
    *,
    access_token="alice-token",
    linux_user="alice",
    reviewed_resources=(),
    revision=VERSION,
):
    from app.benchmark.shell_scope import REVISION

    if revision not in (VERSION, REVISION):
        raise ValueError("REVIEWED_SCOPE_REVISION_REQUIRED")
    if (access_token, linux_user) != ("alice-token", "alice"):
        raise ValueError("REVIEWED_DEMO_PRINCIPAL_REQUIRED")
    resources = []
    for resource in reviewed_resources:
        path, tools = resource["path"], resource["tools"]
        if (
            set(resource) != {"path", "tools", "data_class"}
            or resource["data_class"] != "PUBLIC"
            or not re.fullmatch(r"/[A-Za-z0-9_./-]+", path)
            or str(PurePosixPath(path)) != path
            or ".." in PurePosixPath(path).parts
            or len(PurePosixPath(path).parts) < 3
            or path == "/home/alice"
            or any(sensitive(p) for p in PurePosixPath(path).parts)
            or not isinstance(tools, list)
            or not tools
            or any(
                t
                not in (
                    "read_file",
                    "get_file_info",
                    "check_file_exists",
                    "write_file",
                    "edit_file",
                )
                for t in tools
            )
            or not re.search(
                r"(?<![A-Za-z0-9_./-])" + re.escape(path) + r"(?![A-Za-z0-9_/-]|\.[A-Za-z0-9_.-])",
                request,
            )
        ):
            raise ValueError("EXACT_REVIEWED_USER_RESOURCE_REQUIRED")
        resources.append(
            {
                **resource,
                "request_sha256": digest(request),
                "registry_sha256": registry.digest,
                "principal": linux_user,
            }
        )
    return {
        "version": revision,
        "request_sha256": digest(request),
        "registry_sha256": registry.digest,
        "principal": linux_user,
        "access_token": access_token,
        "roots": delegated_roots(request, revision),
        "tools": list(TOOLS) + (["execute_command"] if revision == REVISION else []),
        "resource_grants": resources,
    }


def targets(candidate, registry):
    entry = registry.resolve(*candidate["tool"].split("::"), candidate["args"])
    paths = []
    for field in entry["slots"]["targets"]:
        value = candidate["args"].get(field, entry["schema"]["properties"][field].get("default"))
        if field in ("dirpath", "search_path", "workdir") and isinstance(value, str):
            value = value.rstrip("/") or "/"
        paths.extend(value if isinstance(value, list) else [value])
    if not paths or len(paths) > 16 or any(not isinstance(p, str) for p in paths):
        return []
    return paths


class ResourceProbe:
    """Trusted security-plane request to the isolated official environment API.

    Fixed endpoint/user/code. No API keys or permission simulator calls. The
    server's existing authenticated execute API enforces the Linux identity.
    """

    def __init__(self, scope, registry):
        self.scope, self.registry = scope, registry

    def __call__(self, candidate):
        from app.benchmark.shell_scope import REVISION
        from app.benchmark.tree_scope import TREE_PROBE_SCRIPT

        paths = targets(candidate, self.registry)
        if not paths:
            raise AnalysisFailure("RESOURCE_METADATA_REQUIRED")
        command = (
            "/usr/bin/python3 -I -c "
            + shlex.quote(
                PROBE_SCRIPT
                + TREE_PROBE_SCRIPT
                + (
                    PROGRAM_PROBE_SCRIPT
                    if self.scope.get("version") == REVISION
                    else "\nprogram_attestation=None"
                )
                + '\nprint(json.dumps({"principal":pwd.getpwuid(os.geteuid()).pw_name,"resources":rows,**({"tree":tree} if tree is not None else {}),**({"program_attestation":program_attestation} if program_attestation is not None else {})}))'
            )
            + " "
            + shlex.quote(
                canonical(
                    {
                        "paths": paths,
                        "tree_depth": candidate["args"].get("max_depth", 3)
                        if candidate["tool"].endswith("::directory_tree")
                        else 1
                        if self.scope.get("version") == REVISION
                        and candidate["tool"].endswith(
                            ("::list_directory", "::list_directory_with_sizes")
                        )
                        else candidate.get("inspection_depth", 32)
                        if self.scope.get("version") == REVISION
                        and candidate["tool"].endswith("::search_files")
                        else None,
                        "complete_search": self.scope.get("version") == REVISION
                        and candidate["tool"].endswith("::search_files")
                        and candidate.get("inspection_depth") is None,
                    }
                )
            )
        )
        with httpx.Client(timeout=4, trust_env=False) as client:
            response = client.post(
                "http://official-env:8034/api/v1/execute",
                headers={"Authorization": "Bearer " + self.scope["access_token"]},
                json={"command": command, "user": self.scope["principal"], "workdir": "/"},
            )
        response.raise_for_status()
        if len(response.content) > 65536:
            raise AnalysisFailure("RESOURCE_METADATA_LIMIT")
        value = response.json()
        if value.get("success") is not True or value.get("exit_code") != 0:
            raise AnalysisFailure("RESOURCE_METADATA_UNAVAILABLE")
        return json.loads(value["stdout"])


def precheck(snapshot, parsed, registry, *, approved=False):
    from app.benchmark.shell_scope import REVISION, UnsupportedShell, describe

    scope = snapshot.get("server_grant", {}).get("task_scope")
    if not scope:
        return None
    if (
        scope.get("version") not in (VERSION, LEGACY_VERSION, REVISION)
        or scope.get("request_sha256") != digest(snapshot["user_request"])
        or scope.get("registry_sha256") != registry.digest
        or scope.get("roots") != delegated_roots(snapshot["user_request"], scope.get("version"))
        or scope.get("tools")
        != (
            TOOLS + ["execute_command"]
            if scope.get("version") == REVISION
            else TOOLS
            if scope.get("version") == VERSION
            else LEGACY_TOOLS
        )
        or (scope.get("access_token"), scope.get("principal")) != ("alice-token", "alice")
        or snapshot["server_grant"].get("authenticated_access_token") != scope["access_token"]
    ):
        return {"decision": "DENY", "reason": "TASK_SCOPE_BINDING_INVALID"}
    if scope["version"] in (VERSION, REVISION):
        try:
            expected = issue_scope(
                snapshot["user_request"],
                registry,
                reviewed_resources=[
                    {k: r[k] for k in ("path", "tools", "data_class")}
                    for r in scope.get("resource_grants", [])
                ],
                revision=scope["version"],
            )
            if scope != expected:
                return {"decision": "DENY", "reason": "TASK_SCOPE_BINDING_INVALID"}
        except (KeyError, TypeError, ValueError):
            return {"decision": "DENY", "reason": "TASK_SCOPE_BINDING_INVALID"}
    candidate, args = snapshot["candidate"], snapshot["candidate"]["args"]
    if args.get("access_token") not in (None, scope["access_token"]) or args.get("user") not in (
        None,
        scope["principal"],
    ):
        return {"decision": "DENY", "reason": "UNAUTHORIZED_IDENTITY_OVERRIDE"}
    if parsed["action"] == "EXECUTE":
        if scope["version"] == REVISION:
            if args.get("ask_for_permission"):
                return {"decision": "CONFIRM", "reason": "SIDE_EFFECT_OR_CONSENT_NOT_DELEGATED"}
            try:
                return {"decision": "CHECK_SHELL", "shell": describe(candidate)}
            except UnsupportedShell as error:
                return {"decision": "DENY", "reason": str(error)}
        return {"decision": "DENY", "reason": "UNSUPPORTED_SCOPE_OPERATION"}
    paths = targets(candidate, registry)
    tool = candidate["tool"].split("::")[1]
    exact = []
    for resource in scope.get("resource_grants", []):
        if (
            scope["version"] not in (VERSION, REVISION)
            or resource.get("request_sha256") != digest(snapshot["user_request"])
            or resource.get("registry_sha256") != registry.digest
            or resource.get("principal") != scope["principal"]
        ):
            return {"decision": "DENY", "reason": "TASK_SCOPE_BINDING_INVALID"}
        if tool in resource.get("tools", []) and resource.get("data_class") == "PUBLIC":
            exact.append(resource["path"])
    if tool == "directory_tree" and tool in scope["tools"]:
        from app.benchmark.tree_scope import MAX_DEPTH

        depth = args.get("max_depth", 3)
        if type(depth) is not int or not 1 <= depth <= MAX_DEPTH:
            return {"decision": "DENY", "reason": "RECURSIVE_DEPTH_NOT_DELEGATED"}
    if any(len(p) > 1024 or len(PurePosixPath(p).parts) > 32 for p in paths):
        return {"decision": "DENY", "reason": "RESOURCE_METADATA_BOUNDS"}
    if any(not re.fullmatch(r"/[A-Za-z0-9_./-]+", p) for p in paths):
        return {"decision": "DENY", "reason": "NONLITERAL_OFFICIAL_SHELL_RESOURCE"}
    if paths and any(
        p not in exact and not any(p == r or p.startswith(r + "/") for r in scope["roots"])
        for p in paths
    ):
        return {"decision": "DENY", "reason": "RESOURCE_OUTSIDE_TASK_CAPABILITY"}
    if paths and any(
        any(
            part.casefold() in SENSITIVE
            or any(word in part.casefold() for word in ("credential", "secret", "id_rsa"))
            for part in PurePosixPath(p).parts
        )
        for p in paths
    ):
        return {"decision": "DENY", "reason": "SENSITIVE_RESOURCE_NOT_DELEGATED"}
    if scope["version"] == VERSION and tool == "search_files":
        # Original find has no depth limit. No filtered/bounded execution exists.
        return {"decision": "CONFIRM", "reason": "UNBOUNDED_RECURSIVE_QUERY_REQUIRES_CONSENT"}
    # Original permission option invokes a simulator and then executes the action.
    # It is not a consent-only operation and must never grant its own authority.
    consent_tools = scope["tools"] + ["delete_file", "delete_directory", "move_file"]
    delegated = tool in scope["tools"] or bool(paths) and all(p in exact for p in paths)
    if (args.get("ask_for_permission") or not delegated) and not (
        approved and tool in consent_tools
    ):
        return {"decision": "CONFIRM", "reason": "SIDE_EFFECT_OR_CONSENT_NOT_DELEGATED"}
    if not paths:
        return {"decision": "CONFIRM", "reason": "EXPLICIT_RESOURCE_SCOPE_REQUIRED"}
    if tool == "edit_file" and delegated:
        # Original sed expression is executable syntax. Restrict replacements to
        # literal text; metacharacters, sed commands and control bytes stay closed.
        if any(
            not isinstance(args.get(k), str) or not re.fullmatch(r"[A-Za-z0-9 _-]{1,256}", args[k])
            for k in ("old_text", "new_text")
        ):
            return {"decision": "DENY", "reason": "NONLITERAL_EDIT_NOT_DELEGATED"}
    if (
        not approved
        and parsed["action"] != "QUERY"
        and any(
            any(
                part.casefold() in ("config", "config.d", "settings")
                for part in PurePosixPath(p).parts
            )
            or any(word in PurePosixPath(p).name.casefold() for word in ("config", "settings"))
            or p.startswith("/etc/")
            for p in paths
        )
    ):
        return {"decision": "CONFIRM", "reason": "SECURITY_CONFIGURATION_REQUIRES_CONSENT"}
    # The pinned implementation embeds search patterns inside shell quotes.
    patterns = [args.get("pattern", "*")] + (args.get("exclude_patterns") or [])
    if any(
        not isinstance(p, str) or not re.fullmatch(r"[A-Za-z0-9_.*? /-]{1,256}", p)
        for p in patterns
    ):
        return {"decision": "DENY", "reason": "NONLITERAL_SEARCH_OPTION"}
    for option in ("head", "tail"):
        if args.get(option) is not None and (
            type(args[option]) is not int or not 0 <= args[option] <= 65536
        ):
            return {"decision": "DENY", "reason": "UNBOUNDED_READ_OPTION"}
    return {"decision": "CHECK_ACCESS", "paths": paths}


def check_access(snapshot, parsed, registry, probe, *, approved=False):
    import stat

    from app.benchmark.shell_scope import REVISION

    checked = precheck(snapshot, parsed, registry, approved=approved)
    if checked and checked["decision"] == "CHECK_SHELL":
        return check_shell_access(snapshot, checked["shell"], registry, probe, approved=approved)
    if not checked or checked["decision"] != "CHECK_ACCESS":
        return checked
    if probe is None:
        raise AnalysisFailure("RESOURCE_METADATA_REQUIRED")
    metadata = probe(snapshot["candidate"])
    if (
        metadata.get("principal") != "alice"
        or [r.get("target") for r in metadata.get("resources", [])] != checked["paths"]
    ):
        raise AnalysisFailure("RESOURCE_METADATA_BINDING_INVALID")
    for row in metadata["resources"]:
        if row.get("traversal_denied") is True:
            return {"decision": "DENY", "reason": "RESOURCE_TRAVERSAL_NOT_AUTHORIZED"}
        if "traversal_denied" in row and type(row["traversal_denied"]) is not bool:
            raise AnalysisFailure("RESOURCE_METADATA_BINDING_INVALID")
        chain = row.get("chain")
        if not chain:
            return {"decision": "CONFIRM", "reason": "RESOURCE_OWNERSHIP_UNAVAILABLE"}
        expected = [
            str(p) for p in reversed(PurePosixPath(row["target"]).parents) if str(p) != "/"
        ] + [row["target"]]
        if [part.get("path") for part in chain] != expected[: len(chain)]:
            raise AnalysisFailure("RESOURCE_METADATA_BINDING_INVALID")
        for part in chain:
            if type(part.get("mode")) is not int or part.get("owner") not in ("alice", "root"):
                return {"decision": "DENY", "reason": "RESOURCE_OWNER_NOT_DELEGATED"}
            if stat.S_ISLNK(part["mode"]):
                return {"decision": "DENY", "reason": "RESOURCE_SYMLINK_NOT_DELEGATED"}
            if part["path"] != row["target"] and (
                not stat.S_ISDIR(part["mode"]) or not part.get("search")
            ):
                return {"decision": "DENY", "reason": "RESOURCE_TRAVERSAL_NOT_AUTHORIZED"}
        leaf = chain[-1]
        exists = leaf["path"] == row["target"]
        if parsed["action"] == "QUERY":
            tool = snapshot["candidate"]["tool"].split("::")[1]
            if exists and (
                tool in ("read_file", "read_multiple_files")
                and not stat.S_ISREG(leaf["mode"])
                or tool
                in ("list_directory", "list_directory_with_sizes", "search_files", "directory_tree")
                and not stat.S_ISDIR(leaf["mode"])
            ):
                return {"decision": "DENY", "reason": "RESOURCE_TYPE_NOT_DELEGATED"}
            metadata_only = tool in (
                "get_file_info",
                "check_file_exists",
            )
            if (
                exists
                and not metadata_only
                and (not leaf.get("read") or not approved and not leaf["mode"] & stat.S_IROTH)
            ):
                return {"decision": "CONFIRM", "reason": "NONPUBLIC_READ_REQUIRES_CONSENT"}
            if (
                tool == "directory_tree"
                or tool in ("search_files", "list_directory", "list_directory_with_sizes")
                and snapshot["server_grant"]["task_scope"]["version"] == REVISION
            ):
                from app.benchmark.tree_scope import check_tree

                if not exists or not leaf.get("search") or not leaf["mode"] & stat.S_IXOTH:
                    return {"decision": "CONFIRM", "reason": "RECURSIVE_NONPUBLIC_REQUIRES_CONSENT"}
                recursive = check_tree(
                    metadata,
                    row["target"],
                    snapshot["candidate"]["args"].get("max_depth", 3)
                    if tool == "directory_tree"
                    else 1
                    if tool in ("list_directory", "list_directory_with_sizes")
                    else snapshot["candidate"].get("inspection_depth", 32),
                    sensitive,
                    integrity_metadata=snapshot["server_grant"]["task_scope"]["version"]
                    == REVISION,
                )
                if recursive:
                    return recursive
                if (
                    tool == "search_files"
                    and snapshot["candidate"].get("inspection_depth") is None
                    and metadata["tree"].get("complete_search") is not True
                ):
                    raise AnalysisFailure("RECURSIVE_METADATA_INCOMPLETE")
        else:
            if exists and not approved and not leaf["mode"] & stat.S_IROTH:
                return {"decision": "CONFIRM", "reason": "PRIVATE_MUTATION_REQUIRES_CONSENT"}
            parent = chain[-2] if exists and len(chain) > 1 else leaf
            permission = leaf if exists else parent
            if (
                not permission.get("write")
                or snapshot["candidate"]["tool"].endswith("::edit_file")
                and (not parent.get("write") or not parent.get("search"))
                or not exists
                and not parent.get("search")
                or exists
                and not stat.S_ISREG(leaf["mode"])
                and parsed["action"] != "CREATE"
            ):
                return {"decision": "DENY", "reason": "RESOURCE_WRITE_NOT_AUTHORIZED"}
    return {
        "decision": "ALLOW",
        "authorized": True,
        "data_class": "PUBLIC",
        "prohibited": False,
        "side_effect_free": parsed["action"] == "QUERY",
        "effect_consent": parsed["action"] != "QUERY",
        "reason": "SERVER_TASK_SCOPE_ACCESS_VERIFIED",
        "proof_sha256": digest(canonical(metadata)),
    }


# Original image /usr/bin fingerprints are pinned in shell_scope.PROGRAMS.
# Metadata only, no task files or generated command strings are executed here.
PROGRAM_PROBE_SCRIPT = """
import hashlib,shutil
names=('ls','stat','find','cat','head','tail','cp','bash')
program_attestation={"startup_overrides":any(k in os.environ for k in ('BASH_ENV','ENV','LD_PRELOAD','LD_LIBRARY_PATH')) or any(k.startswith('BASH_FUNC_') for k in os.environ),"programs":{}}
for name in names:
 p=shutil.which(name)
 if p:
  real=os.path.realpath(p)
  s=os.stat(real)
  if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o022 or s.st_size>8388608: raise ValueError('PROGRAM_IDENTITY_INVALID')
  with open(real,'rb') as f: h=hashlib.file_digest(f,'sha256').hexdigest()
  program_attestation['programs'][name]={"path":real,"sha256":h}
"""


def check_shell_access(snapshot, shell, registry, probe, *, approved=False):
    from app.benchmark.query_capability import public_metadata
    from app.benchmark.shell_scope import verify_programs

    if probe is None:
        raise AnalysisFailure("RESOURCE_METADATA_REQUIRED")
    proofs, visible, results = [], [], []
    for described in shell["operations"]:
        value = {k: v for k, v in described.items() if k != "shell_max_depth"}
        if "shell_max_depth" in described:
            value["inspection_depth"] = described["shell_max_depth"]
        operation_snapshot = {**snapshot, "candidate": value}
        metadata = []

        def inspect(candidate, metadata=metadata):
            result = probe(candidate)
            metadata.append(result)
            return result

        access = check_access(
            operation_snapshot, registry.parse(value), registry, inspect, approved=approved
        )
        if not access or access["decision"] != "ALLOW":
            return access
        if not metadata or not verify_programs(metadata[0], shell["programs"]):
            return {"decision": "DENY", "reason": "SHELL_EXECUTABLE_IDENTITY_CHANGED"}
        for row in metadata[0]["resources"]:
            leaf = row["chain"][-1]
            if (
                leaf["path"] == row["target"]
                and value["tool"].endswith("::read_file")
                and (type(leaf.get("size")) is not int or leaf["size"] > 65536)
            ):
                return {"decision": "DENY", "reason": "SHELL_RESOURCE_LIMIT"}
            if (
                leaf["path"] == row["target"]
                and value["tool"].endswith("::write_file")
                and leaf.get("nlink") != 1
            ):
                return {"decision": "DENY", "reason": "RESOURCE_SYMLINK_NOT_DELEGATED"}
        proofs.append(access["proof_sha256"])
        visible.append(public_metadata(metadata[0], value))
        results.append(access)
    query = all(
        registry.parse({k: v for k, v in c.items() if k != "shell_max_depth"})["action"] == "QUERY"
        for c in shell["operations"]
    )
    return {
        "decision": "ALLOW",
        "authorized": True,
        "data_class": "PUBLIC",
        "prohibited": False,
        "side_effect_free": query,
        "effect_consent": not query,
        "reason": "SERVER_TASK_SCOPE_ACCESS_VERIFIED",
        "proof_sha256": digest(canonical({"shell": shell, "resource_proofs": proofs})),
        "query_public": all(visible),
        "shell_operations": shell,
    }
