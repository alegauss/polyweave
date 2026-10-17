"""The sound layer's error codes, declared beside the code that raises them (§PW507).

The kernel reads them through `Layer.codes`, so a code here is one `explain`
answers and `PolyweaveError` accepts.
"""

from __future__ import annotations

from polyweave.kernel.codes import Code

#: What each of this layer's areas is about.
AREAS: dict[str, str] = {
    "sound": "the audio a game declares it needs, and where each file lands",
    "music": "a score written as a source, compiled to notes and checked",
}

CODES: dict[str, Code] = {
    "sound.no-speech-engine": Code(
        means="a line was asked to be drafted and no local speech engine is installed",
        when="sound.speak rung=draft with neither piper (and a model) nor espeak-ng "
        "on PATH (§PW324); it is refused rather than moved to the paid rung",
        doors=("install espeak-ng, or piper with a model in [voice] draft_model",),
    ),
    # -- sound: the audio a game declares it needs -----------------------------
    "sound.family-unnamed": Code(
        means="the project declares several sound families and the call named none",
        when="a read of the declared audio with [sound.<family>] tables and no family",
        doors=("pass the family", "leave family out to read every one"),
    ),
    "sound.unknown-family": Code(
        means="no sound family of that name is declared",
        when="a misspelled family, or one whose [sound.<family>] was never written",
        doors=("name a declared family", "declare [sound.<family>]"),
    ),
    "sound.cue-twice": Code(
        means="two cues land on one file, so making one would overwrite the other",
        when="one cue name in two families that share a folder and a format",
        doors=("rename one cue", "give one family its own folder"),
    ),
    "sound.no-ffmpeg": Code(
        means="cutting a loop needs ffmpeg to decode the track and encode the loop",
        when="sound.loop on a machine with no ffmpeg on PATH",
        doors=("put ffmpeg on PATH, with libvorbis for an Ogg loop",),
    ),
    "sound.no-loop-point": Code(
        means="no bar in the track's second half comes back to its opening's level",
        when="sound.loop on a track cut short, or one that never returns to its intro",
        doors=("give the whole track, intro to outro",),
    ),
    "sound.loop-gap": Code(
        means="the loop came back from its encoder a different length than it was cut",
        when="an encoder that pads or trims, which is a gap or an overlap at the seam",
        doors=("write the loop as .wav", "use an encoder that keeps the length"),
    ),
    "sound.unknown-cue": Code(
        means="no [sound] family declares a cue of that name",
        when="a sound bought for a cue that was never added to a family's cues",
        doors=("add the cue to a family", "pass out, a path, instead"),
    ),
    "sound.no-source": Code(
        means="the effects file is missing, not TOML, or holds no [effect.<name>]",
        when="a path to no file, or a *.sfx.toml with a stray table",
        doors=("name a *.sfx.toml under the project", "write [effect.<name>] tables"),
    ),
    "sound.bad-effect": Code(
        means="an effect names a key, generator or value sfxr does not have",
        when="generator = \"coin\" for pickup, base_freq = 2, or a misspelled key",
        doors=("use the name the remedy offers", "keep a parameter within its range"),
    ),
    "sound.no-draw": Code(
        means="no seed within the tries gave a length inside the effect's bounds",
        when="a min_duration longer than the generator ever draws",
        doors=("widen the bounds", "pin env_sustain and env_decay"),
    ),
    "sound.no-encoder": Code(
        means="the effect's cue is declared in a format that needs ffmpeg, and there "
        "is none",
        when="an effect for a cue whose family declares ogg, on a machine without "
        "ffmpeg",
        doors=("put ffmpeg on PATH", "declare the family's format as wav"),
    ),
    # -- music: a score as a source, compiled and checked ----------------------
    "music.unreadable": Code(
        means="the score is missing or is not TOML",
        when="a path to no file, or a source with a syntax error on the line named",
        doors=("name a *.music.toml under the project", "fix the syntax on that line"),
    ),
    "music.no-reference": Code(
        means="a score names a reference track that is not a file under the project",
        when="[music] reference points at a path with nothing there",
        doors=("name a file under the project",
               "bring another project's in with provenance.borrow first"),
    ),
    "music.invalid": Code(
        means="the score has problems, so it compiles to nothing a render may play",
        when="music.to_midi on a source music.validate would not pass",
        doors=("call music.validate and fix every problem it names",),
    ),
    "music.bad-format": Code(
        means="a render asked for a format it does not write",
        when="formats naming mp3 or flac, or an empty list",
        doors=("ask for wav, ogg or both",),
    ),
    "music.unknown-key": Code(
        means="a table or key the score format does not have",
        when="a misspelled key such as tempo for bpm, or a stray table",
        doors=("use the key the remedy names",),
    ),
    "music.missing": Code(
        means="a key the score must state is absent",
        when="a score with no title, bpm or form, or a track with no instrument",
        doors=("write the key the problem names",),
    ),
    "music.bad-value": Code(
        means="a value of the wrong type or outside its range",
        when="bpm as a string, a meter of [4, 3], a velocity of 200, a track name "
        "used twice",
        doors=("write the value the remedy describes",),
    ),
    "music.unknown-section": Code(
        means="the form, loop_from or a track's play names a section never declared",
        when="form = [\"A\", \"B\"] with only [section.A], or a typo in play",
        doors=("declare [section.<name>] with its bars", "name a declared section"),
    ),
    "music.unknown-pattern": Code(
        means="a track plays a pattern [pattern] does not hold",
        when="play = { A = \"lead_a\" } with no lead_a under [pattern]",
        doors=("add the pattern", "name one [pattern] holds"),
    ),
    "music.bad-pattern": Code(
        means="a pattern does not parse as mini-notation, or plays drums on a pitched "
        "track",
        when="an unclosed bracket, a note with no octave such as c instead of c4, or "
        "bd in a lead's pattern",
        doors=("fix the step at the character named", "set drums = true on the track"),
    ),
    "music.unknown-instrument": Code(
        means="a track names an instrument no engine plays, or a patch never declared",
        when="piano instead of gm:0, surge:lead with no [patch.lead], or a drum kit "
        "on a track that is not drums",
        doors=("write surge:<patch>, gm:<program> or drums:<kit>",
               "declare [patch.<name>]"),
    ),
    "music.no-engine": Code(
        means="an engine or library the score renders through is not here",
        when="Pedalboard not installed, no FluidSynth on PATH, [paths] soundfont "
        "unset, or Surge XT not in its usual plug-in folder",
        doors=("install the engine the message names",
               "set its [paths] entry to where it is"),
    ),
    "music.bad-kit": Code(
        means="a chip kit's file is missing or unreadable, or lacks a hit it is played",
        when="[kit.chip] naming a file that is not there, or a pattern playing oh "
        "where the kit has only bd, sd and hh",
        doors=("write the kit's *.sfx.toml", "add the missing [effect.<drum>]"),
    ),
    "music.licence-undeclared": Code(
        means="the render plays through a library the project declared no licence for",
        when="a SoundFont in [paths] soundfont with no [licence.\"<its file name>\"]",
        doors=('declare [licence."<file>"] with its terms and any credit it requires',),
    ),
    "music.unknown-parameter": Code(
        means="a patch sets a parameter Surge XT does not have",
        when="a misspelled name, or one that exists only under another oscillator type "
        "than the patch set first",
        doors=("use the name the remedy offers", "set the _type it depends on first"),
    ),
    "music.out-of-range": Code(
        means="a note falls outside MIDI's 0 to 127",
        when="a pattern written an octave or two too high or low",
        doors=("move the note into range",),
    ),
    "music.overlap": Code(
        means="one track strikes the same pitch twice at one tick",
        when="a stack such as [c4, c4], which MIDI cannot hold as two notes",
        doors=("remove the duplicate from the stack",),
    ),
}
