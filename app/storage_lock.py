"""Serialize shared history updates across web and startup worker processes."""
import os
import threading
from contextlib import contextmanager

_locks = {}
_guard = threading.Lock()


@contextmanager
def storage_lock(path):
    with _guard:
        lock = _locks.setdefault(os.path.abspath(path), threading.RLock())
    with lock:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path + ".lock", "a+b") as stream:
            if os.name == "nt":
                import msvcrt
                if os.path.getsize(path + ".lock") == 0:
                    stream.write(b"0")
                    stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)

