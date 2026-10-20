"""Bounded interactive process tree; terminal streams inherited, no transcript.

Windows: CreateProcessW suspended -> Job assignment -> ResumeThread. The job
uses KILL_ON_JOB_CLOSE with no breakaway permission. API basis: Microsoft Learn
/windows/win32/procthread/job-objects and CreateProcessW/SetInformationJobObject.
This controls direct OS child trees, not broker/service-created remote work.
"""
import os
import signal
import subprocess
import time
from contextlib import contextmanager
from datetime import UTC, datetime


def utc():
    return datetime.now(UTC).isoformat()


def run(argv, *, cwd, env, wall_seconds, event_sink, cancel_event=None, before_stop=None):
    if type(wall_seconds) is not int or not 1 <= wall_seconds <= 3600 or not argv:
        raise ValueError("DEMO_LIFECYCLE_LIMIT_INVALID")
    start = utc()
    tick = time.monotonic()
    event_sink({"event": "STARTING", "started_utc": start, "wall_seconds": wall_seconds,
                "wait_accounting": "HUMAN_AND_EXECUTION_COMBINED_NOT_SEPARABLE"})
    try:
        if os.name == "nt":
            result = windows_run(argv, cwd, env, wall_seconds, cancel_event, before_stop)
        else:
            result = posix_run(argv, cwd, env, wall_seconds, cancel_event, before_stop)
    except OSError:
        result = {"outcome": "LAUNCH_FAILED", "exit_code": None, "started": False, "tree_cleanup": "NOT_CREATED"}
    result.update(event="FINISHED", started_utc=start, ended_utc=utc(), elapsed_seconds=round(time.monotonic()-tick, 3), wall_seconds=wall_seconds)
    event_sink(result)
    return result


def stop_control(callback):
    if callback is None:
        return "NOT_APPLICABLE"
    try:
        return "VERIFIED" if callback() is True else "UNVERIFIED"
    except KeyboardInterrupt:
        return "INTERRUPTED"
    except BaseException:
        # No callback termination may bypass process-tree teardown.
        return "UNVERIFIED"


@contextmanager
def cleanup_shield():
    previous = None
    try:
        previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    except (ValueError, OSError):
        pass  # Non-main-thread callers cannot install handlers.
    try:
        yield
    finally:
        if previous is not None:
            signal.signal(signal.SIGINT, previous)


def posix_run(argv, cwd, env, wall_seconds, cancel_event, before_stop=None):
    child = subprocess.Popen(argv, cwd=cwd, env=env, start_new_session=True)
    outcome, exit_code, cleanup = "EXITED", None, "UNVERIFIED"
    deadline = time.monotonic() + wall_seconds
    try:
        while child.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                raise KeyboardInterrupt
            if time.monotonic() >= deadline:
                outcome = "TIMEOUT"
                break
            time.sleep(0.05)
        exit_code = child.poll()
        if outcome == "EXITED" and exit_code:
            outcome = "INTERRUPTED" if exit_code == -signal.SIGINT else "EXITED_NONZERO"
    except KeyboardInterrupt:
        outcome = "INTERRUPTED"
    finally:
        with cleanup_shield():
            closed = stop_control(before_stop)
            if closed == "INTERRUPTED":
                outcome, closed = "INTERRUPTED", "UNVERIFIED"
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=3)
                try:
                    os.killpg(child.pid, 0)
                    cleanup = "UNVERIFIED"
                except ProcessLookupError:
                    cleanup = "VERIFIED"
            except (OSError, subprocess.TimeoutExpired):
                cleanup = "UNVERIFIED"
    return {"outcome": outcome, "exit_code": exit_code, "started": True, "tree_cleanup": cleanup, "connection_closed": closed}


def windows_run(argv, cwd, env, wall_seconds, cancel_event, before_stop=None):
    import ctypes as c
    from ctypes import wintypes as w

    api = c.WinDLL("kernel32", use_last_error=True)
    size = c.c_size_t
    class BasicLimit(c.Structure):
        _fields_ = [("ProcessTime", c.c_longlong), ("JobTime", c.c_longlong), ("Flags", w.DWORD),
                    ("MinWorkingSet", size), ("MaxWorkingSet", size), ("ActiveLimit", w.DWORD),
                    ("Affinity", size), ("Priority", w.DWORD), ("Scheduling", w.DWORD)]
    class Io(c.Structure):
        _fields_ = [(name, c.c_ulonglong) for name in ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]
    class Extended(c.Structure):
        _fields_ = [("Basic", BasicLimit), ("Io", Io), ("ProcessMemory", size), ("JobMemory", size), ("PeakProcess", size), ("PeakJob", size)]
    class Accounting(c.Structure):
        _fields_ = [("UserTime", c.c_longlong), ("KernelTime", c.c_longlong), ("PeriodUser", c.c_longlong), ("PeriodKernel", c.c_longlong),
                    ("PageFaults", w.DWORD), ("TotalProcesses", w.DWORD), ("ActiveProcesses", w.DWORD), ("TerminatedProcesses", w.DWORD)]
    class Startup(c.Structure):
        _fields_ = [("cb", w.DWORD), ("Reserved", w.LPWSTR), ("Desktop", w.LPWSTR), ("Title", w.LPWSTR),
                    ("X", w.DWORD), ("Y", w.DWORD), ("XSize", w.DWORD), ("YSize", w.DWORD), ("XChars", w.DWORD),
                    ("YChars", w.DWORD), ("Fill", w.DWORD), ("Flags", w.DWORD), ("Show", w.WORD),
                    ("ReservedSize", w.WORD), ("Reserved2", c.POINTER(c.c_byte)), ("Input", w.HANDLE), ("Output", w.HANDLE), ("Error", w.HANDLE)]
    class Process(c.Structure):
        _fields_ = [("process", w.HANDLE), ("thread", w.HANDLE), ("pid", w.DWORD), ("tid", w.DWORD)]

    signatures = {
        "CreateJobObjectW": ([c.c_void_p, w.LPCWSTR], w.HANDLE),
        "SetInformationJobObject": ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD], w.BOOL),
        "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
        "QueryInformationJobObject": ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p], w.BOOL),
        "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL), "TerminateProcess": ([w.HANDLE, w.UINT], w.BOOL),
        "GetExitCodeProcess": ([w.HANDLE, c.POINTER(w.DWORD)], w.BOOL), "WaitForSingleObject": ([w.HANDLE, w.DWORD], w.DWORD),
        "ResumeThread": ([w.HANDLE], w.DWORD), "CloseHandle": ([w.HANDLE], w.BOOL),
        "GetStdHandle": ([w.DWORD], w.HANDLE), "GetHandleInformation": ([w.HANDLE, c.POINTER(w.DWORD)], w.BOOL),
        "SetHandleInformation": ([w.HANDLE, w.DWORD, w.DWORD], w.BOOL),
        "CreateProcessW": ([w.LPCWSTR, w.LPWSTR, c.c_void_p, c.c_void_p, w.BOOL, w.DWORD, c.c_void_p, w.LPCWSTR, c.POINTER(Startup), c.POINTER(Process)], w.BOOL),
    }
    for name, (args, returns) in signatures.items():
        fn = getattr(api, name)
        fn.argtypes, fn.restype = args, returns
    job, process, assigned = None, Process(), False
    outcome, exit_code, started, cleanup = "LAUNCH_FAILED", None, False, "NOT_CREATED"
    try:
        job = api.CreateJobObjectW(None, None)
        if not job:
            raise OSError("JOB_CREATE_FAILED")
        limit = Extended()
        limit.Basic.Flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway flags.
        if not api.SetInformationJobObject(job, 9, c.byref(limit), c.sizeof(limit)):
            raise OSError("JOB_LIMIT_FAILED")
        startup = Startup()
        startup.cb, startup.Flags = c.sizeof(startup), 0x100  # STARTF_USESTDHANDLES.
        handles = []
        for code, field in ((-10, "Input"), (-11, "Output"), (-12, "Error")):
            handle = api.GetStdHandle(code & 0xFFFFFFFF)
            previous = w.DWORD()
            if not handle or not api.GetHandleInformation(handle, c.byref(previous)):
                raise OSError("CONSOLE_HANDLES_UNAVAILABLE")
            handles.append((handle, previous.value))
            setattr(startup, field, handle)
        environment = c.create_unicode_buffer("\0".join(f"{k}={v}" for k, v in sorted(env.items(), key=lambda pair: pair[0].upper())) + "\0\0")
        line = c.create_unicode_buffer(subprocess.list2cmdline([str(x) for x in argv]))
        try:
            for handle, _ in handles:
                if not api.SetHandleInformation(handle, 1, 1):
                    raise OSError("CONSOLE_INHERITANCE_FAILED")
            if not api.CreateProcessW(str(argv[0]), line, None, None, True, 0x4 | 0x400, environment, str(cwd), c.byref(startup), c.byref(process)):
                raise OSError("PROCESS_CREATE_FAILED")
        finally:
            for handle, flags in handles:
                api.SetHandleInformation(handle, 1, flags & 1)
        # No child instruction runs before the job owns the process tree.
        if not api.AssignProcessToJobObject(job, process.process):
            api.TerminateProcess(process.process, 125)
            raise OSError("JOB_ASSIGN_FAILED")
        assigned = True
        if api.ResumeThread(process.thread) == 0xFFFFFFFF:
            raise OSError("PROCESS_RESUME_FAILED")
        started, outcome = True, "EXITED"
        deadline = time.monotonic() + wall_seconds
        try:
            while api.WaitForSingleObject(process.process, 50) == 0x102:
                if cancel_event is not None and cancel_event.is_set():
                    raise KeyboardInterrupt
                if time.monotonic() >= deadline:
                    outcome = "TIMEOUT"
                    break
            if outcome == "EXITED":
                code = w.DWORD()
                if not api.GetExitCodeProcess(process.process, c.byref(code)) or code.value == 259:
                    outcome = "EXIT_STATUS_UNKNOWN"
                else:
                    exit_code = code.value
                    if exit_code:
                        outcome = "INTERRUPTED" if exit_code == 0xC000013A else "EXITED_NONZERO"
        except KeyboardInterrupt:
            outcome = "INTERRUPTED"
    except (OSError, KeyboardInterrupt) as error:
        outcome = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "LAUNCH_FAILED" if not started else "EXIT_STATUS_UNKNOWN"
    finally:
        with cleanup_shield():
            try:
                closed = stop_control(before_stop)
                if closed == "INTERRUPTED":
                    outcome, closed = "INTERRUPTED", "UNVERIFIED"
            finally:
                try:
                    if assigned:
                        cleanup = "UNVERIFIED"
                        api.TerminateJobObject(job, 124 if outcome == "TIMEOUT" else 130 if outcome == "INTERRUPTED" else 125)
                        deadline = time.monotonic() + 3
                        while time.monotonic() < deadline:
                            accounting = Accounting()
                            if api.QueryInformationJobObject(job, 1, c.byref(accounting), c.sizeof(accounting), None) and accounting.ActiveProcesses == 0:
                                cleanup = "VERIFIED"
                                break
                            time.sleep(0.05)
                    elif process.process:
                        api.TerminateProcess(process.process, 125)
                        cleanup = "VERIFIED" if api.WaitForSingleObject(process.process, 3000) == 0 else "UNVERIFIED"
                finally:
                    for handle in (process.thread, process.process, job):
                        if handle:
                            api.CloseHandle(handle)
    return {"outcome": outcome, "exit_code": exit_code, "started": started, "tree_cleanup": cleanup, "connection_closed": closed}
