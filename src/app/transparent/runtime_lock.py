"""Linux local-runtime lease shared by servers and offline maintenance."""
import os
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def lease(database):
    import fcntl
    path = Path(str(database) + '.service-lock')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(fd).st_nlink != 1:
            raise ValueError('UNSAFE_RUNTIME_LOCK')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('RUNTIME_IS_RUNNING') from None
        yield
    finally:
        os.close(fd)
