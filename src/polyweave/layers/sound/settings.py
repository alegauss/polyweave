"""The sound layer's tables in polyweave.toml, declared as data (§PW508).

The kernel resolves and refuses; this says which tables the layer reads, every
key each holds and its default, and how the kernel should treat them.
"""

from __future__ import annotations

from typing import Any

#: Every table this layer reads, each key with the value used where the project
#: declares none. A key absent from here is refused rather than ignored.
TABLES: dict[str, Any] = {
    "sound": {
        # What a game needs to hear, declared by the game (§PW185): each family is a
        # list of cues sharing a kind, a format and a folder, so polyweave can say which
        # file is missing without reading the consumer's scripts. A bare [sound] is one
        # family, `default`, as a bare [style] is.
        # `loop` has a seam; a `stinger` plays once over the music; an `effect` is a
        # one-shot. The kind decides which measures mean anything for its files.
        "kind": "effect",
        "format": "wav",
        # Under [paths] audio; empty is that folder itself.
        "folder": "",
        # What the cue is made to: seconds and RMS dBFS, where zero states none. Bounds
        # a file is held to stay in its *.accept.toml; these are the targets.
        "duration": 0.0,
        "loudness": 0.0,
        # The cue names, each landing at <folder>/<name>.<format>.
        "cues": [],
    },
    # What each instrument library a render plays through permits and owes (§PW191),
    # keyed by the library's file name: `[licence."GeneralUser-GS.sf2"]` with `terms`,
    # the `credit` it requires (empty owes none), a `note` and a `url`. The project's to
    # declare, because the project chose the library; a render through an undeclared
    # one is refused.
    "licence": {},
    "voice": {
        # What a spoken take is held to before a person hears it (§PW323). The game's
        # numbers, so nothing here invents one: zero, or an empty band, bounds nothing.
        # Seconds of silence before the first word and after the last.
        "lead_silence": 0.0,
        "tail_silence": 0.0,
        # [low, high] characters of the line per second spoken: a skipped phrase reads
        # fast, a repeated one slow.
        "rate": [],
        # [low, high] dBFS, so dialogue sits where the project's effects do.
        "loudness": [],
        # Cut a bought take's silence down to the two bounds above as it lands, the
        # service's own bytes kept on its record by their digest.
        "trim": False,
        # The game's interjections ("uhuu", "vamo"): a transcription spells them its own
        # way ("woohoo", "vamos"), so a take is never failed for how one was heard.
        "interjections": [],
        # The free rung a line is drafted on before a character is billed (§PW324):
        # "piper" with `draft_model` (a downloaded .onnx), or "espeak-ng" with
        # `draft_voice` (such as "pt-br"). Empty takes the first one installed.
        "draft_engine": "",
        "draft_model": "",
        "draft_voice": "",
    },
}

#: Tables a project may add its own keys to.
FREE = ("licence",)

#: Tables that hold one thing, or several named ones.
NAMED = ("sound",)

#: Settings whose value is one of a few words.
CHOICES = {
    "kind": ('loop', 'stinger', 'effect'),
    "format": ('wav', 'ogg', 'flac', 'mp3', 'opus'),
}
