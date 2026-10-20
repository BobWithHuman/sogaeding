"""A finite shell grammar mapped to reviewed OS operations, never shell evaluation.

The original command and arguments are forwarded unchanged. This mapping only
describes effects for authorization; unsupported syntax cannot obtain a grant.
"""

import re
import shlex
from pathlib import PurePosixPath

from app.common import canonical, digest

REVISION = "dtap-functional-scope-3"
PROFILE = "dtap-functional-routing-1"
PROGRAMS = {
    "ls": "53a9c0557a948069d56f964cf21c7c0854bb2677d9985080369ed1e172161625",
    "stat": "3b87d297111f11d30b3c51fd2663f131a161e09d8e130e1842adaefb74307efe",
    "find": "ac1ea1c5391de921aca1572f1bf25d03707beb3887b27c16a5b4948fd553941b",
    "cat": "a63158e6e5bce20616425f5d61e5bd7374bb5bccf15bbb93ae2e40238248f179",
    "head": "bba6734ebc053fef547ec4a0bcd824011e80c81f8a67f5b83b0fccf7617ce959",
    "tail": "871571a28ad9483140d92027915a263311462f4ca96e0451e38d6ebcce370c0b",
    "cp": "6187dab32cd7b6291d96c54425a22915a6eeb39add6d95ee9008e1dbba427131",
    "bash": "bc5945feb8bd26203ebfafea5ce1878bb2e32cb8fb50ab7ae395cfb1e1aaaef1",
}


class UnsupportedShell(ValueError):
    pass


def path(value):
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"/[A-Za-z0-9_./-]*", value)
        or str(PurePosixPath(value)) != value
        or ".." in PurePosixPath(value).parts
    ):
        raise UnsupportedShell("SHELL_RESOURCE_NOT_LITERAL")
    return value


def operation(tool, **args):
    return {"route": "mcp", "tool": "OS-filesystem::" + tool, "args": args}


def describe(candidate):
    args = candidate["args"]
    if args.get("user", "root") != "alice":
        raise UnsupportedShell("UNAUTHORIZED_IDENTITY_OVERRIDE")
    command = args.get("command")
    if (
        not isinstance(command, str)
        or not 1 <= len(command.encode()) <= 4096
        or any(c in command for c in "\x00\r\n\\$`(){}<>|&!#")
    ):
        raise UnsupportedShell("UNSUPPORTED_SHELL_SYNTAX")
    quote = None
    for char in command:
        if quote is not None:
            if char == ";":
                raise UnsupportedShell("UNSUPPORTED_SHELL_SYNTAX")
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char in "*?[":
            raise UnsupportedShell("UNSUPPORTED_SHELL_SYNTAX")
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";")
    lexer.whitespace_split, lexer.commenters = True, ""
    try:
        tokens = list(lexer)
    except ValueError as error:
        raise UnsupportedShell("UNSUPPORTED_SHELL_SYNTAX") from error
    groups, current = [], []
    for token in tokens:
        if token == ";":
            if not current:
                raise UnsupportedShell("UNSUPPORTED_SHELL_SYNTAX")
            groups.append(current)
            current = []
        elif token.startswith(";"):
            raise UnsupportedShell("UNSUPPORTED_SHELL_SYNTAX")
        else:
            current.append(token)
    if current:
        groups.append(current)
    if not 1 <= len(groups) <= 4:
        raise UnsupportedShell("UNSUPPORTED_SHELL_SYNTAX")
    workdir = path(args.get("workdir", "/"))
    operations = [operation("list_directory", dirpath=workdir)] if workdir != "/" else []
    programs = set()
    metadata_only = True
    for words in groups:
        name = words[0]
        program = PurePosixPath(name).name
        if (
            name not in (program, "/usr/bin/" + program)
            or program not in PROGRAMS
            or program == "bash"
        ):
            raise UnsupportedShell("UNSUPPORTED_SHELL_OPERATION")
        programs.add(program)
        values = words[1:]
        if program == "ls":
            while values and values[0].startswith("-"):
                flag, values = values[0], values[1:]
                if flag == "--":
                    break
                if not re.fullmatch(r"-[alhnSrtd]+", flag) or "d" in flag:
                    raise UnsupportedShell("UNSUPPORTED_SHELL_OPTION")
            values = values or [args.get("workdir", "/")]
            operations.extend(operation("list_directory", dirpath=path(p)) for p in values)
        elif program == "stat":
            if values and values[0] == "--":
                values = values[1:]
            if not values:
                raise UnsupportedShell("SHELL_RESOURCE_REQUIRED")
            operations.extend(operation("get_file_info", filepath=path(p)) for p in values)
        elif program in ("cat", "head", "tail"):
            metadata_only = False
            limit = None
            if program in ("head", "tail") and values[:1] == ["-n"]:
                if len(values) < 3 or not values[1].isdigit() or not 1 <= int(values[1]) <= 4096:
                    raise UnsupportedShell("UNSUPPORTED_SHELL_OPTION")
                limit, values = int(values[1]), values[2:]
            if values[:1] == ["--"]:
                values = values[1:]
            if not values:
                raise UnsupportedShell("SHELL_RESOURCE_REQUIRED")
            for value in values:
                extra = {program: limit or 10} if program in ("head", "tail") else {}
                operations.append(operation("read_file", filepath=path(value), **extra))
        elif program == "cp":
            metadata_only = False
            if values[:1] in (["--"], ["-T"]):
                values = values[1:]
            if len(values) != 2:
                raise UnsupportedShell("UNSUPPORTED_SHELL_OPTION")
            source, destination = map(path, values)
            if source == destination:
                raise UnsupportedShell("UNSUPPORTED_SHELL_OPERATION")
            operations.extend(
                (
                    operation("read_file", filepath=source),
                    operation("write_file", filepath=destination, content=""),
                )
            )
        elif program == "find":
            if not values:
                raise UnsupportedShell("SHELL_RESOURCE_REQUIRED")
            target, values = path(values[0]), values[1:]
            depth, pattern = None, "*"
            if values[:1] == ["-maxdepth"]:
                if len(values) < 2 or values[1] not in ("1", "2", "3", "4"):
                    raise UnsupportedShell("UNSUPPORTED_SHELL_OPTION")
                depth, values = int(values[1]), values[2:]
            if values[:1] == ["-name"]:
                if len(values) < 2 or not re.fullmatch(r"[A-Za-z0-9_.*?-]{1,128}", values[1]):
                    raise UnsupportedShell("UNSUPPORTED_SHELL_OPTION")
                pattern, values = values[1], values[2:]
            if values not in ([], ["-print"]):
                raise UnsupportedShell("UNSUPPORTED_SHELL_OPTION")
            operations.append(operation("search_files", search_path=target, pattern=pattern))
            # A bounded metadata probe may inspect more than this command,
            # never less. The original find arguments remain untouched.
            if depth is not None:
                operations[-1]["shell_max_depth"] = depth
        else:
            raise UnsupportedShell("UNSUPPORTED_SHELL_OPERATION")
    if not operations or len(operations) > 4:
        raise UnsupportedShell("SHELL_RESOURCE_LIMIT")
    return {
        "version": REVISION,
        "command_sha256": digest(command),
        "candidate_sha256": digest(canonical(candidate)),
        "operations": operations,
        "programs": sorted(programs),
        "metadata_only": metadata_only,
    }


def verify_programs(metadata, programs):
    attestation = metadata.get("program_attestation")
    if not isinstance(attestation, dict) or attestation.get("startup_overrides") is not False:
        return False
    for name in set(programs) | {"bash"}:
        item = attestation.get("programs", {}).get(name, {})
        if item.get("path") != "/usr/bin/" + name or item.get("sha256") != PROGRAMS[name]:
            return False
    return True
