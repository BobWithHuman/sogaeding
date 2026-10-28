"""Enrolled tool schemas and lexical identity. Upstream still opens with NOFOLLOW."""
import re
from pathlib import PurePosixPath, PureWindowsPath

from jsonschema import Draft202012Validator

FILE_TOOLS = [
    {"name": "read_file", "description": "Read a UTF-8 file inside the enrolled workspace.",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
    {"name": "write_file", "description": "Write a UTF-8 file inside the enrolled workspace.",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string", "maxLength": 16384}}, "required": ["path", "content"], "additionalProperties": False}},
]


def file_path(name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("PATH_SCOPE")
    path = PurePosixPath(name)
    parts = name.split("/")
    if path.is_absolute() or any(x in ("", ".", "..") or x.startswith(".") or x.casefold() in ("artifacts", "references") for x in parts):
        raise ValueError("PATH_SCOPE")
    devices = {"con", "prn", "aux", "nul", *("com" + str(i) for i in range(1, 10)), *("lpt" + str(i) for i in range(1, 10))}
    if any(x.rstrip(". ") != x or x.casefold().split(".")[0] in devices or any(ord(c) < 32 for c in x) for x in parts):
        raise ValueError("SPECIAL_PATH_UNSUPPORTED")
    lowered = name.casefold()
    if path.suffix.casefold() in (".key", ".p12", ".pfx", ".api-key") or any(x.casefold() in ("credentials.json", "secrets.json", "id_rsa", "id_ed25519", "service.token", "human.token", "machine.token", "jev.api-key", "judge.api-key") for x in parts):
        raise ValueError("SENSITIVE_RESOURCE")
    if lowered in ("agents.md", "harness/build_tasks.json") or lowered.startswith(("docs/plans/", "docs/handoffs/", "src/app/", "agentgateway/", "tools/hookgw", "scripts/hookgw", "compose.hookgw", "tools/mvp_", "scripts/mvp_", "compose.mvp-demo")):
        raise ValueError("TRUSTED_PRODUCT_OR_EVIDENCE")
    return path


def native_path(name, workspace):
    # Resolve only lexical identity here. Native hook/OS sandbox still owns actual
    # symlink/hardlink checks. A string origin never establishes file authority.
    if "\\" in name or PureWindowsPath(name).is_absolute():
        path, root = PureWindowsPath(name), PureWindowsPath(workspace)
        if ".." in path.parts:
            raise ValueError("PATH_SCOPE")
        if path.is_absolute():
            name = path.relative_to(root).as_posix()
        else:
            name = path.as_posix()
    elif PurePosixPath(name).is_absolute():
        name = PurePosixPath(name).relative_to(PurePosixPath(workspace)).as_posix()
    return file_path(name).as_posix()


def parse(candidate, workspace):
    """No guessed shell slots. All returned values came from a supported grammar."""
    tool, args, route = candidate["tool"], candidate["args"], candidate["route"]
    if route == "mcp":
        from app.transparent.npm_lab import NPM_TOOLS, parse_npm
        if tool in {t['name'] for t in NPM_TOOLS}:
            return parse_npm(tool, args)
        schema = next((t["inputSchema"] for t in FILE_TOOLS if t["name"] == tool), None)
        if schema is None or not Draft202012Validator(schema).is_valid(args):
            raise ValueError("INVALID_TOOL_SCHEMA")
        path = file_path(args["path"]).as_posix()
        if tool == "write_file" and len(args["content"].encode()) > 16384:
            raise ValueError("CONTENT_LIMIT")
        return {"action": "READ" if tool == "read_file" else "WRITE", "targets": [path], "options": None, "payload": args.get("content"), "parser": "enrolled-files-1"}
    if route != "native" or not isinstance(args, dict) or set(args) != {"command"} or not isinstance(args["command"], str):
        raise ValueError("UNPARSED_TOOL")
    command = args["command"]
    if tool == "Bash":
        if any(c in command for c in (";", "|", "&", "`", "$", ">", "<", "\n", "\r")):
            raise ValueError("UNPARSED_COMPOUND_COMMAND")
        if re.fullmatch(r"Get-Location\s*", command, re.I):
            return {"action": "METADATA", "targets": [], "options": None, "payload": None, "parser": "native-powershell-subset-1"}
        read = re.fullmatch(r"(Get-Content|Get-ChildItem)\s+-LiteralPath\s+'([^']+)'", command, re.I)
        write = re.fullmatch(r"Set-Content\s+-LiteralPath\s+'([^']+)'\s+-Value\s+'([^']*)'", command, re.I)
        if not read and not write:
            raise ValueError("UNPARSED_TOOL")
        name = read[2] if read else write[1]
        if not (PureWindowsPath(name).is_absolute() or PurePosixPath(name).is_absolute()):
            raise ValueError("ABSOLUTE_SHELL_PATH_REQUIRED")
        return {"action": "READ" if read else "WRITE", "targets": [native_path(name, workspace)], "options": ["LiteralPath"], "payload": None if read else write[2], "parser": "native-powershell-subset-1"}
    if tool == "apply_patch":
        lines = command.splitlines()
        if not lines or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
            raise ValueError("UNPARSED_PATCH")
        paths, section = [], None
        for line in lines[1:-1]:
            header = re.fullmatch(r"\*\*\* (Add File|Update File|Delete File|Move to): (.+)", line)
            if header:
                if header[1] == "Move to" and section != "Update File":
                    raise ValueError("UNPARSED_PATCH")
                paths.append(native_path(header[2], workspace))
                if header[1] != "Move to":
                    section = header[1]
            elif section is None or line.startswith("***") and line != "*** End of File" or section == "Delete File" or section == "Add File" and not line.startswith("+") or not (line.startswith(("+", "-", " ", "@@")) or line == "*** End of File"):
                raise ValueError("UNPARSED_PATCH")
        if not paths:
            raise ValueError("UNPARSED_PATCH")
        return {"action": "WRITE", "targets": paths, "options": None, "payload": command, "parser": "native-patch-subset-1"}
    raise ValueError("UNPARSED_TOOL")
