"""The child process that does the work and reports where it got to.

Run as `python -m polyweave.jobs.worker <record.json>`. It is the only writer of the
record once a job is running, so nothing here has to merge with a concurrent write.

A target is named `module:function` or `path/to/file.py:function`, the second form
resolved against the project root — a project's own generator lives in its own tree
(`docs/specs/geometry.md`), not in this package.
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.util
import inspect
import sys
import threading
import traceback
from pathlib import Path
from typing import Any

from ..errors import PolyweaveError
from . import record as rec
from .report import Report


def _heartbeat(beat_path: Path, interval: float, stop: threading.Event) -> None:
    """Prove the worker is still this process.

    A pid is reused, so liveness alone would report a stranger's process as this job's
    worker. A beat that has stopped moving is the other half of that answer.
    """
    while not stop.wait(interval):
        # A full or vanished work directory is not worth ending the render over.
        with contextlib.suppress(OSError):
            rec.write_beat(beat_path)


def resolve_target(target: str, root: Path) -> Any:
    """Import `module:function` or `file.py:function` and return the callable."""
    if ":" not in target:
        raise PolyweaveError(
            "job.bad-target",
            f"{target!r} does not name a function",
            "write it as 'module:function' or 'path/to/file.py:function'",
        )
    where, name = target.rsplit(":", 1)
    a_file = where.endswith(".py") or "/" in where or "\\" in where
    module = _import_file(where, root) if a_file else _import_module(where, target)
    try:
        return getattr(module, name)
    except AttributeError:
        raise PolyweaveError(
            "job.target-not-found",
            f"{where} has no {name!r}",
            f"name one of {', '.join(n for n in dir(module) if not n.startswith('_'))}",
        ) from None


def _import_module(where: str, target: str) -> Any:
    try:
        return importlib.import_module(where)
    except ImportError as exc:
        raise PolyweaveError(
            "job.target-not-found",
            f"no module {where!r} on this worker's path",
            f"check the spelling of {target!r}, or pass its directory as `path`",
            detail=traceback.format_exc(),
        ) from exc


def _import_file(where: str, root: Path) -> Any:
    path = Path(where)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        raise PolyweaveError(
            "job.target-not-found",
            f"no file at {path}",
            f"write the path relative to the project root, {root}",
        )
    spec = importlib.util.spec_from_file_location(f"polyweave_target_{path.stem}", path)
    if spec is None or spec.loader is None:  # pragma: no cover - unimportable suffix
        raise PolyweaveError(
            "job.target-not-found",
            f"{path} is not importable as Python",
            "point the target at a .py file",
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_args(fn: Any, args: dict) -> None:
    """Refuse an argument the target does not take, rather than dropping it.

    §3 of the tool surface: a silently dropped field makes a typo indistinguishable from
    a working call, which is the whole of §PW19.
    """
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):  # pragma: no cover - a builtin target
        return
    if any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()
    ):
        return
    accepted = [
        name
        for name, p in signature.parameters.items()
        if p.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    ]
    unknown = sorted(set(args) - set(accepted[1:]))
    if unknown:
        raise PolyweaveError(
            "job.unknown-arg",
            f"{', '.join(unknown)} is not an argument of this target"
            if len(unknown) == 1
            else f"{', '.join(unknown)} are not arguments of this target",
            f"it takes {', '.join(accepted[1:]) or 'no arguments'}",
        )


def run(record_path: Path) -> int:
    state = rec.read_record(record_path)
    if state is None:
        print(f"polyweave: no job record at {record_path}", file=sys.stderr)
        return 2
    if state.get("schema") != rec.SCHEMA:
        print(f"polyweave: job record schema {state.get('schema')!r}", file=sys.stderr)
        return 2

    paths = rec.JobPaths(Path(state["work"]))
    stop = threading.Event()
    beat = threading.Thread(
        target=_heartbeat,
        args=(paths.beat(state["job"]), state["heartbeat_s"], stop),
        daemon=True,
    )
    beat.start()

    report = Report(record_path, state)
    try:
        root = Path(state["root"])
        fn = resolve_target(state["target"], root)
        check_args(fn, state["args"])
        result = fn(report, **state["args"])
        report.finish("done", result=result, error=None)
        return 0
    except PolyweaveError as exc:
        report.finish("failed", result=None, error=exc.as_dict())
        return 1
    except BaseException as exc:  # noqa: BLE001 - every failure becomes a record
        report.finish(
            "failed",
            result=None,
            error={
                "code": "job.target-failed",
                "message": f"{type(exc).__name__}: {exc}",
                "remedy": (
                    f"read {paths.log(state['job'])} for the output, and the detail "
                    f"below for where it raised"
                ),
                "detail": traceback.format_exc(),
            },
        )
        return 1
    finally:
        stop.set()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m polyweave.jobs.worker <record.json>", file=sys.stderr)
        return 2
    return run(Path(args[0]))


if __name__ == "__main__":  # pragma: no cover - the process entry point
    raise SystemExit(main())
