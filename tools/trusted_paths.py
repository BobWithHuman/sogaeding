"""Local launch helpers; repository write access is code execution authority."""
import importlib.util
import os
import shutil
import stat
from pathlib import Path

HELPERS = frozenset({'hookgw_hook', 'hookgw_launch', 'hookgw_preflight'})
PUBLIC_CERTIFICATES = frozenset({'ca.pem', 'control.pem', 'gateway.pem', 'gateway-client.pem', 'upstream.pem'})


def load_helper(name):
    if name not in HELPERS:
        raise ValueError('UNTRUSTED_HELPER')
    path = Path(__file__).absolute().with_name(name + '.py')
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('HELPER_LINK_REJECTED')
        if os.name == 'posix' and (info.st_uid not in (0, os.getuid()) or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX and not os.statvfs(part).f_flag & os.ST_RDONLY)):
            raise ValueError('HELPER_WRITABLE_PARENT_REJECTED')
    if not path.is_file():
        raise ValueError('HELPER_UNAVAILABLE')
    spec = importlib.util.spec_from_file_location('with_human_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def executable_path(value):
    value = os.fspath(value)
    explicit = Path(value).is_absolute() or '/' in value or '\\' in value
    found = value if explicit else shutil.which(value)
    if not found:
        raise ValueError('EXECUTABLE_UNAVAILABLE')
    path = Path(found).resolve(strict=True)
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError('EXECUTABLE_UNAVAILABLE')
    return path


def write_new_private(path, value):
    """Create new secrets with restrictive permissions before the first byte."""
    data = value.encode('utf-8') if isinstance(value, str) else value
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)


def read_local_file(path, *, public=False, limit=65536):
    """Read POSIX credentials by descriptor; Windows relies on prepared ACLs."""
    path = Path(path).absolute()
    directory = None
    try:
        if os.name == 'posix':
            directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
            for part in path.parts[1:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                os.close(directory)
                directory = child
                info = os.fstat(directory)
                if info.st_uid not in (0, os.getuid()) or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                    raise ValueError('UNSAFE_CREDENTIAL_PARENT')
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        else:
            for part in (path, *path.parents):
                info = part.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                    raise ValueError('CREDENTIAL_LINK_REJECTED')
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
                raise ValueError('PRIVATE_FILE_REQUIRED')
            if os.name == 'posix' and (info.st_uid not in (0, os.getuid()) or info.st_mode & (0o022 if public else 0o077)):
                raise ValueError('PRIVATE_FILE_PERMISSIONS_REQUIRED')
            value = stream.read(limit + 1)
            if len(value) > limit:
                raise ValueError('PRIVATE_FILE_TOO_LARGE')
            return value
    finally:
        if directory is not None:
            os.close(directory)
