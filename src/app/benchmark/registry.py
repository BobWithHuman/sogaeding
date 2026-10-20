"""Pinned MCP schema enrollment, exact server identity and explicit slot mapping."""

import copy
import re
from pathlib import PurePosixPath

from jsonschema import Draft202012Validator

from app.common import canonical, digest


class UnsupportedTool(ValueError):
    pass


class Registry:
    def __init__(self, entries):
        self.entries = copy.deepcopy(entries)
        self.digest = digest(canonical(entries))
        if len({(e["server"], e["name"]) for e in entries}) != len(entries):
            raise ValueError("DUPLICATE_TOOL_IDENTITY")
        for entry in self.entries:
            Draft202012Validator.check_schema(entry["schema"])
            if digest(canonical(entry["schema"])) != entry["schema_sha256"]:
                raise ValueError("SCHEMA_HASH_MISMATCH")
            properties = set(entry["schema"].get("properties", {}))
            slots = entry["slots"]
            assigned = [key for role in ("targets", "options", "payload") for key in slots[role]]
            if len(assigned) != len(set(assigned)) or set(assigned) != properties:
                raise ValueError("EXPLICIT_SLOT_COVERAGE_REQUIRED")
            if entry["effect"] not in ("QUERY", "MUTATE") or not slots["targets"]:
                raise ValueError("EXPLICIT_EFFECT_AND_RESOURCE_REQUIRED")

    def name(self, server, tool):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", server) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+", tool
        ):
            raise UnsupportedTool("TOOL_IDENTITY_INVALID")
        return server + "::" + tool

    def resolve(self, server, tool, args):
        match = [e for e in self.entries if (e["server"], e["name"]) == (server, tool)]
        if len(match) != 1:
            raise UnsupportedTool("UNENROLLED_TOOL_NOT_SEMANTIC_DENY")
        entry = match[0]
        if (
            not isinstance(args, dict)
            or set(args) - set(entry["schema"].get("properties", {}))
            or not Draft202012Validator(entry["schema"]).is_valid(args)
        ):
            raise UnsupportedTool("ACTUAL_SCHEMA_ARGUMENT_MISMATCH")
        # This selected official filesystem implementation interpolates paths
        # into shell commands. Reject nonliteral paths equally in BOTH arms.
        if entry["resource_kind"] == "DTAP_POSIX_PATH":
            for field in entry["slots"]["targets"]:
                value = args.get(field)
                if (
                    not isinstance(value, str)
                    or not re.fullmatch(r"/[A-Za-z0-9_./-]+", value)
                    or ".." in PurePosixPath(value).parts
                    or str(PurePosixPath(value)) != value
                ):
                    raise UnsupportedTool("OFFICIAL_SHELL_PATH_NOT_LITERAL")
        if args.get("access_token") is not None:
            raise UnsupportedTool("ACTOR_SUPPLIED_CREDENTIAL_OVERRIDE")
        if args.get("ask_for_permission"):
            raise UnsupportedTool("ENVIRONMENT_PERMISSION_LLM_NOT_ENABLED")
        return entry

    def parse(self, candidate):
        if candidate.get("route") != "mcp" or candidate["tool"].count("::") != 1:
            raise UnsupportedTool("NO_ENROLLED_SERVER_IDENTITY")
        server, tool = candidate["tool"].split("::")
        args = candidate["args"]
        entry = self.resolve(server, tool, args)
        slots = entry["slots"]
        return {
            "parser": "dtap-schema-1",
            "action": entry["effect"],
            "targets": [
                canonical(
                    {
                        "server": server,
                        "kind": entry["resource_kind"],
                        "field": field,
                        "value": args[field],
                    }
                )
                for field in slots["targets"]
            ],
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
