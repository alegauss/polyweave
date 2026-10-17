"""The words layer's error codes, declared beside the code that raises them (§PW507).

The kernel reads them through `Layer.codes`, so a code here is one `explain`
answers and `PolyweaveError` accepts.
"""

from __future__ import annotations

from polyweave.kernel.codes import Code

#: What each of this layer's areas is about.
AREAS: dict[str, str] = {
    "world": "a game's names, factions and characters, declared beside its prose",
    "words": "the text a player reads, held to the world it is set in",
}

CODES: dict[str, Code] = {
    "world.no-voice": Code(
        means="a line was asked of an entity the world gives no voice id",
        when="sound.speak with entity= where [entity.<id>.voice] has no id (§PW321); "
        "it is refused rather than spoken in a voice nobody chose for it",
        doors=("have a person choose the voice and write its id in the world",),
    ),
    "world.voice-unchosen": Code(
        means="a voice was to be kept that no person accepted",
        when="voice.choose on a file that is not a voice.design preview, or one with "
        "no person's accept on its bytes (§PW321); an agent never picks a voice",
        doors=("let a person accept one on the review page voice.design lays out",),
    ),
    "words.no-fonts": Code(
        means="the project names no font, or one that cannot be read, to hold lines to",
        when="words.glyphs with no [words] fonts, a path with nothing there, or a "
        "file whose character map is not one this reads (§PW335)",
        doors=('set [words] fonts = [{ path = "fonts/Game.ttf" }]',),
    ),
    "words.no-voiced": Code(
        means="the project says nowhere for a spoken line to land",
        when="voice.lines with no [words] voiced, the path each take is written to "
        "(§PW322)",
        doors=('set [words] voiced = "audio/voice/{locale}/{key}.ogg"',),
    ),
    "world.voice-mismatch": Code(
        means="a call named a voice other than the one the world gives its entity",
        when="sound.speak with both entity= and a voice= that is not the entity's",
        doors=("leave voice unset to speak in the entity's own",),
    ),
    # -- world: a game's names, factions and characters -----------------------
    "world.none": Code(
        means="no *.world.toml was found where the call looked",
        when="a project that has not declared its world yet, or a world path "
        "misspelled",
        doors=("write a *.world.toml beside the world's prose", "name the file"),
    ),
    "world.several": Code(
        means="the project holds several world files and the call named none",
        when="a world read or validated without world= in a project with more than "
        "one *.world.toml",
        doors=("pass world",),
    ),
    "world.malformed": Code(
        means="the world file is not readable as TOML",
        when="a syntax error, or one entity's table written twice",
        doors=("fix the syntax the detail points at",),
    ),
    "world.unknown-key": Code(
        means="the world file declares a table, entity field or rule a world does "
        "not have",
        when="a misspelled field, or a table other than [entity.<id>] and [rules]",
        doors=("use a key the message lists",),
    ),
    "world.missing-field": Code(
        means="an entity lacks a field every entity carries",
        when="an entity with no name or no kind",
        doors=("write the field under the entity's table",),
    ),
    "world.bad-value": Code(
        means="a field of the world file holds a value of the wrong type",
        when="a number where a name belongs, an empty name, or a rule that is not "
        "a whole number or a list of ids",
        doors=("write the value in the shape the message gives",),
    ),
    "world.bad-kind": Code(
        means="an entity's kind is not one a world knows",
        when="a kind other than place, faction, character, enemy or item",
        doors=("make it one of the five kinds",),
    ),
    "world.duplicate-name": Code(
        means="two entities share the name a player reads or the code the scripts use",
        when="a character and a place both called the same thing, or a copied entity "
        "whose name was never changed",
        doors=("give one of them another name",),
    ),
    "world.unknown-faction": Code(
        means="an entity belongs to a faction no entity of kind faction declares",
        when="a misspelled faction, or one never written as an entity",
        doors=("declare the faction as an entity", "name a declared faction"),
    ),
    "world.unknown-family": Code(
        means="an entity is held to a style family polyweave.toml does not declare",
        when="a family misspelled in the world file, or one whose [style.<family>] "
        "was never written",
        doors=("declare [style.<family>]", "name a declared family"),
    ),
    "world.unknown-entity": Code(
        means="an id names no entity the world declares",
        when="world.read asked for an entity that is not there, or a rule naming one",
        doors=("name a declared entity", "declare [entity.<id>]"),
    ),
    "world.family-mismatch": Code(
        means="a purchase drawn from an entity named a style family other than the one "
        "the world holds the entity to",
        when="picture.buy with entity and a family the entity's style is not",
        doors=("leave family unset", "pass the entity's own family"),
    ),
    # -- words: the text a player reads ---------------------------------------
    "words.no-table": Code(
        means="polyweave.toml names no string table, so there is no text to check",
        when="words.check in a project whose text is still literals in its scripts",
        doors=("move the text into Godot's translation CSV and set [words] table",),
    ),
    "words.no-canon": Code(
        means="polyweave.toml names no lines canon, so a verdict on a line has nowhere "
        "to be kept",
        when="words.sheet, or a verdict on a line, before [words] canon is set",
        doors=("set [words] canon to a JSON file under the project",),
    ),
    "words.unreadable-table": Code(
        means="the string table is missing, or has no header naming keys and a locale",
        when="a moved or misspelled [words] table, or a CSV with no header row",
        doors=("write the CSV there", "correct [words] table"),
    ),
    "words.unreadable-copy": Code(
        means="a file [words] copy names cannot be read as copy",
        when="no file at the path, a suffix other than .md, .markdown, .html, .htm or "
        ".txt, or no locale named for it",
        doors=("correct the path or its locale in [words] copy",),
    ),
    "words.unknown-name": Code(
        means="a line names something with a capitalised word the world shows as no "
        "name",
        when="an old name left on screen after a rename, or a word written in capitals "
        "that is not a name at all",
        doors=(
            "use the world's name",
            "add the word to [words] ordinary",
            "declare it in the world",
        ),
    ),
    "words.code-name": Code(
        means="a line shows an entity's code name, which the scripts use and a player "
        "never should",
        when="a key's text copied from the code rather than the world's name",
        doors=("write the name the world declares",),
    ),
    "words.too-long": Code(
        means="a line is longer than the world's [rules] longest_line",
        when="a long sentence, often in the locale whose words are longest",
        doors=("shorten it", "break it with \\n"),
    ),
    "words.unknown-speaker": Code(
        means="a line's speaker is no entity the world declares",
        when="a misspelled speaker id, or a character not yet in the world",
        doors=("name a declared entity", "declare [entity.<id>]"),
    ),
    "words.silent-speaks": Code(
        means="a line is given to an entity the world says never speaks",
        when="dialogue written for a character the world keeps silent",
        doors=("give the line to another speaker", "take it out of [rules] silent"),
    ),
    "words.hidden-name": Code(
        means="a line shows a name the world keeps unshown",
        when="an unnamed character named on screen",
        doors=("refer to it without its name", "take it out of [rules] unshown"),
    ),
}
