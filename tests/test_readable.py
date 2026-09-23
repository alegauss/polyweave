"""The prose this package returns, reaching the process that prints it intact.

§PW73. Nothing here prints: a refusal's message and remedy are returned, and the stream
they land on belongs to the caller. Left at the locale's encoding on a Windows desk, an
em dash goes out as one correct cp1252 byte and comes back to a UTF-8 reader as a
lozenge — nothing lost writing it, everything lost reading it.

The tests below drive real `TextIOWrapper`s rather than `sys.stdout`, because the
question is what the bytes are, and a captured stream would answer a different one.
"""

from __future__ import annotations

import io
import sys

import polyweave


def stream(encoding="cp1252"):
    """A text stream over bytes we can read back, as a console pipe is."""
    raw = io.BytesIO()
    return raw, io.TextIOWrapper(raw, encoding=encoding, line_buffering=True)


def test_the_locale_s_encoding_is_what_loses_it(tmp_path):
    """The premise this task started from, kept as the thing being fixed."""
    raw, text = stream()
    print("a — b", file=text)
    text.flush()
    assert b"\x97" in raw.getvalue()
    assert raw.getvalue().decode("utf-8", "replace").count("�") == 1


def test_a_stream_this_moved_writes_utf_8(monkeypatch):
    raw, text = stream()
    monkeypatch.setattr(sys, "stdout", text)
    assert polyweave.readable() == ["stdout"]
    print("a — b", file=sys.stdout)
    sys.stdout.flush()
    assert raw.getvalue().decode("utf-8").strip() == "a — b"


def test_it_says_which_streams_it_moved(monkeypatch):
    _, out = stream()
    _, err = stream()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    assert polyweave.readable() == ["stdout", "stderr"]


def test_a_stream_already_utf_8_is_left_alone(monkeypatch):
    """Nothing to report is reported as nothing, so a caller can assert on it."""
    _, text = stream(encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", text)
    monkeypatch.setattr(sys, "stderr", text)
    assert polyweave.readable() == []


def test_calling_it_twice_moves_nothing_the_second_time(monkeypatch):
    _, text = stream()
    monkeypatch.setattr(sys, "stdout", text)
    monkeypatch.setattr(sys, "stderr", text)
    assert polyweave.readable() == ["stdout"]
    assert polyweave.readable() == []


def test_a_stream_somebody_else_wrapped_is_not_taken_over(monkeypatch):
    """Which is the reach this call exists to avoid; it declines rather than raises."""

    class Captured(io.StringIO):
        encoding = "cp1252"

    monkeypatch.setattr(sys, "stdout", Captured())
    monkeypatch.setattr(sys, "stderr", Captured())
    assert polyweave.readable() == []


def test_importing_the_package_reconfigures_nothing(monkeypatch):
    """A library must not set the encoding of a process it does not own."""
    _, text = stream()
    monkeypatch.setattr(sys, "stdout", text)
    import importlib

    importlib.reload(polyweave)
    assert sys.stdout.encoding == "cp1252"
