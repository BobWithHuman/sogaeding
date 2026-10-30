"""POSIX descriptor-relative reads for runtime credentials."""
from contextlib import contextmanager
import os
import stat
from pathlib import Path


def read_private(path, limit=65536):
    path = Path(path).absolute()
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
            info = os.fstat(directory)
            if info.st_uid not in (0, os.getuid()) or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX and not os.fstatvfs(directory).f_flag & os.ST_RDONLY):
                raise OSError('UNSAFE_CREDENTIAL_ANCESTOR')
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit or (info.st_mode & 0o077 and not os.fstatvfs(stream.fileno()).f_flag & os.ST_RDONLY) or info.st_uid not in (0, os.getuid()):
                raise OSError('PRIVATE_FILE_REQUIRED')
            value = stream.read(limit + 1)
            if len(value) > limit:
                raise OSError('PRIVATE_FILE_TOO_LARGE')
            return value
    finally:
        os.close(directory)


def open_private_database(path, *, read_only=False, **kwargs):
    """SQLite requires a pathname: protect its namespace before connecting.

    The current OS user is trusted. Never chmod existing operator data here.
    SQLite creates sidecars using the database's permissions.
    """
    import sqlite3
    path = Path(path).absolute()
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            if not read_only:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=directory)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
            info = os.fstat(directory)
            if info.st_uid not in (0, os.getuid()) or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                raise OSError('UNSAFE_DATABASE_ANCESTOR')
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise OSError('PRIVATE_DATABASE_DIRECTORY_REQUIRED')
        for name in (path.name, *(path.name + suffix for suffix in ('-journal', '-wal', '-shm'))):
            try:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            except FileNotFoundError:
                continue
            try:
                info = os.fstat(fd)
                # SQLite may unlink a journal after this descriptor was opened.
                # It no longer names a file in the protected directory.
                if name != path.name and info.st_nlink == 0:
                    continue
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
                    raise OSError('PRIVATE_DATABASE_FILE_REQUIRED')
            finally:
                os.close(fd)
        if read_only:
            os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        try:
            if read_only:
                raise FileExistsError()
            fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, **kwargs) if read_only else sqlite3.connect(str(path), **kwargs)
    finally:
        os.close(directory)


@contextmanager
def private_connect(path, **kwargs):
    connection = open_private_database(path, **kwargs)
    try:
        with connection:
            yield connection
    finally:
        connection.close()
