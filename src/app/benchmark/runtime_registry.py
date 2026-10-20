"""Runtime enrollment from actual schemas and reviewed operation mappings."""

import copy
import re
from pathlib import PurePosixPath

from jsonschema import Draft202012Validator

from app.benchmark.registry import UnsupportedTool
from app.common import canonical, digest

# Arguments are from the pinned original 18-tool OS schema, not name aliases
# for the product parser. Every remaining property is explicitly an option.
OS_OPERATIONS = {
    "read_file": ("QUERY", ["filepath"], []),
    "read_multiple_files": ("QUERY", ["filepaths"], []),
    "write_file": ("MUTATE", ["filepath"], ["content"]),
    "edit_file": ("MUTATE", ["filepath"], ["old_text", "new_text"]),
    "create_directory": ("CREATE", ["dirpath"], []),
    "move_file": ("MOVE", ["source", "destination"], []),
    "list_directory": ("QUERY", ["dirpath"], []),
    "list_directory_with_sizes": ("QUERY", ["dirpath"], []),
    "directory_tree": ("QUERY", ["dirpath"], []),
    "search_files": ("QUERY", ["search_path"], ["pattern"]),
    "execute_command": ("EXECUTE", ["workdir"], ["command"]),
    "check_file_exists": ("QUERY", ["filepath"], []),
    "get_file_info": ("QUERY", ["filepath"], []),
    "delete_file": ("DELETE", ["filepath"], []),
    "delete_directory": ("DELETE", ["dirpath"], []),
    "log_action": ("APPEND", [], ["action", "details", "status", "result"]),
    "get_logs": ("QUERY", [], []),
    "clear_logs": ("DELETE", [], []),
}


def enroll_os(tools):
    if {t["name"] for t in tools} != set(OS_OPERATIONS):
        raise UnsupportedTool("OFFICIAL_OS_TOOL_SET_CHANGED")
    entries = []
    for tool in tools:
        effect, targets, payload = OS_OPERATIONS[tool["name"]]
        schema = copy.deepcopy(tool["inputSchema"])
        fields = set(schema.get("properties", {}))
        if not set(targets + payload) <= fields:
            raise UnsupportedTool("OFFICIAL_OS_SCHEMA_CHANGED")
        entries.append(
            {
                "server": "OS-filesystem",
                "name": tool["name"],
                "schema": schema,
                "schema_sha256": digest(canonical(schema)),
                "description": tool.get("description", ""),
                "effect": effect,
                "resource_kind": "DTAP_POSIX_PATH",
                "fixed_resources": ["OS_FILESYSTEM_SESSION_LOG"]
                if not targets
                else ["OS_FILESYSTEM_WORKSPACE"]
                if tool["name"] == "execute_command"
                else [],
                "slots": {
                    "targets": targets,
                    "payload": payload,
                    "options": sorted(fields - set(targets + payload)),
                },
            }
        )
    return entries


class RuntimeRegistry:
    def __init__(self, entries):
        self.entries = copy.deepcopy(entries)
        self.digest = digest(canonical(entries))
        self.by_name = {self.name(e["server"], e["name"]): e for e in self.entries}
        if len(self.by_name) != len(entries):
            raise UnsupportedTool("DUPLICATE_RUNTIME_TOOL")
        for entry in self.entries:
            schema = entry["schema"]
            Draft202012Validator.check_schema(schema)
            if digest(canonical(schema)) != entry["schema_sha256"]:
                raise UnsupportedTool("RUNTIME_SCHEMA_HASH_CHANGED")
            assigned = [
                k for role in ("targets", "options", "payload") for k in entry["slots"][role]
            ]
            if len(assigned) != len(set(assigned)) or set(assigned) != set(
                schema.get("properties", {})
            ):
                raise UnsupportedTool("COMPLETE_RUNTIME_SLOT_MAP_REQUIRED")
            if not entry["slots"]["targets"] and not entry.get("fixed_resources"):
                raise UnsupportedTool("EXPLICIT_RESOURCE_ID_REQUIRED")
            if entry["effect"] not in (
                "QUERY",
                "MUTATE",
                "CREATE",
                "MOVE",
                "DELETE",
                "APPEND",
                "EXECUTE",
                "SEND",
                "SQL_QUERY",
                "SQL_MUTATE",
                "API_QUERY",
                "API_MUTATE",
            ):
                raise UnsupportedTool("EXPLICIT_OPERATION_EFFECT_REQUIRED")

    def name(self, server, tool):
        if not all(
            isinstance(s, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", s) for s in (server, tool)
        ):
            raise UnsupportedTool("INVALID_SERVER_TOOL_ID")
        return server + "::" + tool

    def resolve(self, server, tool, args):
        entry = self.by_name.get(self.name(server, tool))
        if not entry:
            raise UnsupportedTool("UNENROLLED_RUNTIME_TOOL")
        if (
            not isinstance(args, dict)
            or set(args) - set(entry["schema"].get("properties", {}))
            or not Draft202012Validator(entry["schema"]).is_valid(args)
        ):
            raise UnsupportedTool("RUNTIME_ARGUMENT_SCHEMA_MISMATCH")
        if entry["resource_kind"] == "DTAP_POSIX_PATH":
            for field in entry["slots"]["targets"]:
                value = args.get(field, entry["schema"]["properties"][field].get("default"))
                if value is None and entry.get("fixed_resources"):
                    continue
                values = value if isinstance(value, list) else [value]
                for path in values:
                    normalized = (
                        path.rstrip("/") or "/"
                        if isinstance(path, str) and field in ("dirpath", "search_path", "workdir")
                        else path
                    )
                    if (
                        not isinstance(path, str)
                        or not re.fullmatch(r"/[A-Za-z0-9_./ -]*", path)
                        or ".." in PurePosixPath(path).parts
                        or str(PurePosixPath(path)) != normalized
                    ):
                        raise UnsupportedTool("NONLITERAL_OFFICIAL_SHELL_RESOURCE_INCOMPLETE")
        # Synthetic OS credentials are part of the ORIGINAL benchmark API;
        # do not silently remove privilege-escalation attacks in either arm.
        if server == "OS-filesystem" and args.get("access_token") not in (
            None,
            "alice-token",
            "bob-token",
            "admin-token-for-setup",
        ):
            raise UnsupportedTool("UNKNOWN_CREDENTIAL_VALUE_INCOMPLETE")
        return entry

    def parse(self, candidate):
        if candidate.get("route") != "mcp" or candidate.get("tool", "").count("::") != 1:
            raise UnsupportedTool("NO_RUNTIME_SERVER_IDENTITY")
        server, tool = candidate["tool"].split("::")
        args = candidate["args"]
        entry = self.resolve(server, tool, args)
        slots = entry["slots"]
        targets = [
            canonical(
                {
                    "server": server,
                    "kind": entry["resource_kind"],
                    "field": field,
                    "value": args.get(field, entry["schema"]["properties"][field].get("default")),
                }
            )
            for field in slots["targets"]
        ]
        targets.extend(
            canonical({"server": server, "kind": "TRUSTED_ENV_RESOURCE", "identity": value})
            for value in entry.get("fixed_resources", [])
        )
        return {
            "parser": "dtap-runtime-schema-1",
            "action": entry["effect"],
            "targets": targets,
            "options": canonical({f: args[f] for f in slots["options"] if f in args}),
            "payload": canonical({f: args[f] for f in slots["payload"] if f in args})
            if slots["payload"]
            else None,
            "tool_identity": {
                "server": server,
                "name": tool,
                "schema_sha256": entry["schema_sha256"],
                "registry_sha256": self.digest,
            },
        }
