"""polyweave — a game's parts declared rather than dialled in.

Nothing is imported here on purpose. The caller is an agent whose turn is the budget,
and a package that pulls in its whole surface to answer one call spends that budget
before the call happens.

The one function here keeps that rule: `readable()` imports `sys` inside itself, and a
caller that never calls it pays nothing for it.

The package is laid out by which way its dependencies are meant to run (§PW499):

- `kernel/`: errors and doors, the operation registry, config, jobs, files, the cache,
  the post-checks and the provenance record. It knows no medium.
- `loop/`: accept, measure, search, calibrate, verdict, review, brief, revision and the
  loop's own ledger: what every medium is declared, measured, searched and judged by.
- `layers/<medium>/`: geometry (with render), picture, sound, words, vfx, motion,
  engine, reference, store and kits. A measure reading one medium lives with it.
- `services/`: what was bought from a paid service, and what the service accepts.
- `surface/`: the server, the command line, the census, capabilities and the calls
  that adopt a project whole.

A module that fits no layer cleanly sits with the layer that owns its data.
"""

__version__ = "0.1.0"


def readable() -> list[str]:
    """Write this process's output as UTF-8, and say which streams moved (§PW73).

    Nothing in this package prints its prose. A refusal's message and remedy, and every
    line a run reports, are returned for the caller to print — so the encoding of the
    stream they land on is the caller's process to set, not this one's.

    Left unset on a Windows desk it is the locale's. An em dash then goes out as the
    single byte 0x97, which is correct cp1252 and nothing is lost writing it; what reads
    the pipe decodes UTF-8, where that byte is not a character, and shows a lozenge. The
    loss is at the far end, which is the worse end: the process that wrote the line saw
    nothing wrong and has nothing to report.

    A library must not reconfigure a process it does not own, so this is a call and not
    something that happens on import. One line at the top of a runner, before it prints:

        polyweave.readable()

    It returns the streams it changed, which is empty where they were already UTF-8, and
    it is safe to call twice. `sys` is the only import, so it costs nothing to the turn
    of a caller that never uses it.
    """
    import sys

    moved = []
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        if (getattr(stream, "encoding", "") or "").lower().replace("-", "") == "utf8":
            continue
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            # A stream that cannot be reconfigured is one somebody else already wrapped,
            # and taking it over would be the reach this call exists to avoid.
            continue
        moved.append(name)
    return moved
