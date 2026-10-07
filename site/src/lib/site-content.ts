// The copy lives here and nowhere else. Every section component imports a value from this
// module and only renders it — so a claim is an array element a reviewer can check against
// the roadmap, not a string welded into the markup that displays it. The composition
// (which section, in which order, and the figures) lives in the JSX; this file is the words.
//
// Fragments carrying inline code or emphasis are modelled as a small tagged run list
// (`Rich`) rather than raw HTML, so a section renders them without dangerouslySetInnerHTML
// and the twin generator has a structure to convert rather than markup to parse.
//
// The landing page describes polyweave as the roadmap leaves it: every block built. It
// states no status — what is still open lives in docs/ROADMAP.md, which the depth pages
// link to — and it still claims no measured result for polyweave, which
// scripts/lint.test.mjs enforces.
import { sessionTerminal } from "./diagrams";

/** How many commands the transcript actually runs, so the sentence under it can say. */
const sessionCalls = (sessionTerminal.match(/&gt;<\/span> polyweave /g) ?? []).length;
const SPELLED_SMALL = ["zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight"];

export type Run =
  | string
  | { code: string }
  | { b: string }
  | { i: string };

export type Rich = Run[];

/** The name of an inline icon, drawn by components/ui/Icon.tsx. */
export type IconName =
  | "hand" | "eye" | "ear" | "target" | "gamepad" | "verdict" | "wrench" | "memory"
  | "book" | "wallet" | "record" | "box" | "cube" | "image" | "wave" | "music" | "mic"
  | "text" | "map" | "motion" | "kit" | "laptop" | "file" | "shield" | "chat" | "check"
  | "spark";

/* ------------------------------------------------------------------ meta + chrome */

export const meta = {
  title: "polyweave — a Claude Code plugin that makes your game's parts",
  description:
    "polyweave gives Claude Code the hands to drive Blender, Godot and AI generators, the eyes and ears to check every result against the bar you set, and a review page where you approve what ships: 3D models, pictures, sound, music, voices, words, levels and game kits.",
  og: {
    title: "polyweave",
    description:
      "Claude Code can write your game. Now it can make the rest of it — and you approve every part.",
    url: "https://alegauss.github.io/polyweave/",
  },
} as const;

export const repoUrl = "https://github.com/alegauss/polyweave";
export const parentUrl = "https://alegauss.github.io/";
export const roadmapUrl = `${repoUrl}/blob/main/docs/ROADMAP.md`;
export const changelogUrl = `${repoUrl}/blob/main/docs/CHANGELOG.md`;
export const specsUrl = `${repoUrl}/tree/main/docs/specs`;
export const roadkeepUrl = "https://github.com/alegauss/roadkeep";

// Section anchors (#x) act on the landing page; the page links are base-absolute so they
// resolve the same from every route. There is no "Claude Code" item: the whole page is.
export const navLinks = [
  { href: "/polyweave/#gains", label: "Why Claude Code" },
  { href: "/polyweave/#how", label: "How it works" },
  { href: "/polyweave/#makes", label: "What it makes" },
  { href: "/polyweave/#review", label: "Review" },
] as const;

export const footer = {
  links: [
    { href: "/polyweave/claude-code/", label: "For agents" },
    { href: "/polyweave/specs/", label: "Specs" },
    { href: repoUrl, label: "GitHub" },
    { href: roadmapUrl, label: "Roadmap" },
    { href: changelogUrl, label: "Changelog" },
  ],
  disclaimer:
    "polyweave is an independent open-source project. It orchestrates Blender, Godot and the generative services named on this page and re-implements none of them; it is not affiliated with, endorsed by or sponsored by any of their authors, and every mark named here belongs to its owner. © 2026 Alexandre Oliveira.",
} as const;

/* --------------------------------------------------------------- sponsor */

// Mirrors alegauss.github.io/sponsor.json — the canonical sponsor declaration for these
// projects. Transcribed here rather than fetched at runtime: this site is prerendered, and
// the whole point of naming a sponsor is that crawlers and LLMs read it in the served HTML.
export const sponsor = {
  label: "Sponsored by",
  name: "Viglet",
  url: "https://www.viglet.org",
  siteLabel: "viglet.org",
  logo: "/polyweave/viglet/viglet-logo.png",
  summary:
    "Open source search and content tools for organisations with a lot to publish. Run on your own servers, with no per-user licence.",
  products: [
    {
      name: "Viglet Turing ES",
      url: "https://turing.viglet.org",
      logo: "/polyweave/viglet/turing-logo.png",
      inline:
        "so visitors find what they came for, with AI answers drawn only from your own content",
    },
    {
      name: "Viglet Shio CMS",
      url: "https://shio.viglet.org",
      logo: "/polyweave/viglet/shio-logo.png",
      inline:
        "so a new page goes live the same day, reviewed and approved by your own team",
    },
  ],
} as const;

/* ------------------------------------------------------------------ hero */

export const hero = {
  badge: "A plugin for Claude Code",
  titleLead: "Claude Code can write your game.",
  titleAccent: "Now it can make the rest of it.",
  sub: [
    "polyweave sits ",
    { b: "between Claude Code and the tools that make game content" },
    ". It drives Blender, Godot and AI generators, checks every result against the bar you set, and puts the best candidates on one page where ",
    { b: "you approve what ships" },
    ".",
  ] as Rich,
  cta: "Install in Claude Code",
  ctaShort: "Install",
  // The middle figure, in words: who talks to whom.
  hub: {
    you: { title: "You + Claude Code", lines: ["“Make the mascot from my sketch.”", "“Level 3, a little harder.”"] },
    core: { title: "polyweave", lines: ["makes", "checks", "tunes", "records"] },
    tools: ["Blender", "Godot", "Meshy", "FLUX", "Ideogram", "ElevenLabs", "sfxr"],
    review: { title: "Your review page", line: "approve · reject · ask for a change" },
  },
  meta: ["Runs on your machine", "Works with the models you pick", "Spends only what you allow"],
};

/* ------------------------------------------------------------------ what Claude Code gains */

export const gains = {
  eyebrow: "Claude Code first",
  heading: "Everything Claude Code gains with polyweave.",
  intro: [
    "On its own, Claude Code writes code and reads text. It cannot see a render, hear a sound or play a level, and it has no way to know when a part is good enough. polyweave gives it all of that through ",
    { b: "one MCP server" },
    ", installed with the plugin.",
  ] as Rich,
  items: [
    {
      icon: "hand",
      title: "Hands on every tool",
      body: "Drives Blender, Godot and the 3D, picture, sound and voice generators through one set of calls, each tool in its own language.",
    },
    {
      icon: "eye",
      title: "Eyes",
      body: "Every render comes back with its numbers: silhouette, colour, contrast, and how it reads at the size a player sees it.",
    },
    {
      icon: "ear",
      title: "Ears",
      body: "Loudness, clipping, loop seams and spoken takes are measured, so a sound is checked before a person hears it.",
    },
    {
      icon: "target",
      title: "A bar to aim at",
      body: "Each part has a short file saying what correct means. A search tunes the settings until every check passes.",
    },
    {
      icon: "gamepad",
      title: "Hands on the game",
      body: "Opens your game, presses buttons, waits for a state, takes screenshots and replays a run, all without a screen.",
    },
    {
      icon: "verdict",
      title: "Your verdict, on tap",
      body: "Sends the candidates to your review page and waits for your answer, so it never has to guess your taste.",
    },
    {
      icon: "wrench",
      title: "Errors that carry the fix",
      body: "Every failure has a stable code and the exact call that resolves it. No traceback to decode, no second round trip.",
    },
    {
      icon: "memory",
      title: "Memory across sessions",
      body: "Long jobs return a handle, and jobs, traces and records are files in the repo, so the next session picks up where this one stopped.",
    },
    {
      icon: "book",
      title: "Tools that explain themselves",
      body: "Each operation lists its parameters, ranges and defaults, and the plugin says which tools this machine has.",
    },
    {
      icon: "wallet",
      title: "A budget it can work inside",
      body: "You set a spending ceiling once. Claude Code works freely under it and can never raise it.",
    },
    {
      icon: "record",
      title: "The history of every file",
      body: "Which model, prompt, seed, cost and licence made each part. Credits and licence checks are written from it.",
    },
    {
      icon: "box",
      title: "Game parts already proven",
      body: "Menus, settings, saves, controls, co-op and accessibility arrive as kits, installed and tested in your project.",
    },
  ] as { icon: IconName; title: string; body: string }[],
};

/* ------------------------------------------------------------------ how it works */

export const steps = {
  eyebrow: "How it works",
  heading: "From a request to a part you approved, in four steps.",
  items: [
    {
      n: "1",
      title: "Ask",
      body: [
        "Tell Claude Code what you need, in plain words: ",
        { i: "“a mascot like this sketch”" },
        ", ",
        { i: "“a coin sound in C”" },
        ", ",
        { i: "“make level 3 a bit harder”" },
        ".",
      ] as Rich,
    },
    {
      n: "2",
      title: "Make",
      body: [
        "polyweave picks up the right tool and drives it: Blender, Godot, a 3D or picture generator, a synth or a voice.",
      ] as Rich,
    },
    {
      n: "3",
      title: "Check",
      body: [
        "Every result is measured against the bar you set. A miss is tuned and tried again before you ever see it.",
      ] as Rich,
    },
    {
      n: "4",
      title: "Approve",
      body: [
        "The best candidates land on your review page. Approve, reject, or ask for a change, and Claude Code takes it from there.",
      ] as Rich,
    },
  ],
};

/* ------------------------------------------------------------------ what it makes */

export const makes = {
  eyebrow: "What it makes",
  heading: "One plugin for every part of a game.",
  intro: [
    "Each layer works the same way: say what the part should be, let it be made and checked, approve the result. All of them share one project config, one record and one review page.",
  ] as Rich,
  items: [
    { icon: "cube", title: "3D models", body: "Built in Blender from a declaration, or bought from a generator and fitted to your drawing." },
    { icon: "image", title: "Images", body: "Concept art, icons, sprite sheets and store capsules, held to your style." },
    { icon: "music", title: "Music", body: "Loops that close without a seam, rendered from MIDI and heard mixed." },
    { icon: "wave", title: "Sound", body: "Effects synthesised or bought, put in a key, checked for loudness and clicks." },
    { icon: "spark", title: "Effects", body: "Particles, glows and hits declared as data and previewed before they ship." },
    { icon: "kit", title: "Game kits", body: "Menus, saves, settings, controls, co-op and accessibility, installed already tested." },
    { icon: "mic", title: "Voices", body: "Lines read in each character's own voice, priced before anything is spent." },
    { icon: "text", title: "Words", body: "Names, dialogue and string tables checked against your world and your fonts." },
    { icon: "map", title: "Levels", body: "Declared as data, built into the engine, measured for difficulty before anyone plays." },
    { icon: "motion", title: "Animation", body: "Skeletons and clips kept as text, so a timing change is one edit you can diff." },
  ] as { icon: IconName; title: string; body: string }[],
};

/** The six the hero names first, as chips. Each one links to its card below. */
export const heroParts: { icon: IconName; label: string }[] = [
  { icon: "cube", label: "3D" },
  { icon: "image", label: "Images" },
  { icon: "music", label: "Music" },
  { icon: "wave", label: "Sound" },
  { icon: "spark", label: "Effects" },
  { icon: "kit", label: "Kits" },
];

/* ------------------------------------------------------------------ session */

export const session = {
  eyebrow: "See it in action",
  heading: "What Claude Code actually does.",
  intro: [
    `${SPELLED_SMALL[sessionCalls] ?? sessionCalls} calls: turn a sketch into a bar, search until it passes, take the final render, and get a failure that says how to fix it.`,
  ] as Rich,
  note: [
    "The commands are the surface ",
    { code: "docs/specs/tool-surface.md" },
    " fixes; the values are illustrative.",
  ] as Rich,
  more: "How polyweave is built for an agent",
};

/* ------------------------------------------------------------------ the middle */

export const middle = {
  eyebrow: "The middle layer",
  heading: "Many models. One way to use them.",
  intro: [
    "Claude Code talks to polyweave, and polyweave talks to each tool in its own language. Pick the models you like; the rules stay the same.",
  ] as Rich,
  groups: [
    { label: "3D", names: ["Blender", "Meshy"] },
    { label: "Pictures", names: ["FLUX", "Ideogram"] },
    { label: "Sound and music", names: ["sfxr", "MIDI"] },
    { label: "Voice", names: ["ElevenLabs"] },
    { label: "Game engine", names: ["Godot"] },
  ],
  points: [
    {
      icon: "file",
      title: "Chosen in one config",
      body: [
        "Models, budgets and paths live in ",
        { code: "polyweave.toml" },
        ", in your repo. Switching is a config change, not a rewrite.",
      ] as Rich,
    },
    {
      icon: "check",
      title: "Checked before you pay",
      body: [
        "A request is checked against your drawing before a credit moves, and every price is quoted before it is spent.",
      ] as Rich,
    },
    {
      icon: "record",
      title: "Kept, with its receipt",
      body: [
        "What a service made is copied into your project with its prompt, seed, cost and licence, so nothing expires out from under you.",
      ] as Rich,
    },
  ] as { icon: IconName; title: string; body: Rich }[],
};

/* ------------------------------------------------------------------ review */

export const review = {
  eyebrow: "Review",
  heading: "You judge the result. Never the file.",
  intro: [
    "Only a person can say a look is right, a line sounds true or a level feels fair. polyweave makes that the quick part.",
  ] as Rich,
  mock: {
    window: "polyweave · mascot",
    candidates: [
      { label: "A", hue: 32, checks: [["silhouette", "0.98", true], ["colour", "ΔE 1.4", true]] },
      { label: "B", hue: 14, checks: [["silhouette", "0.97", true], ["colour", "ΔE 1.9", true]] },
      { label: "C", hue: 300, checks: [["silhouette", "0.91", false], ["colour", "ΔE 4.2", false]] },
    ] as { label: string; hue: number; checks: [string, string, boolean][] }[],
    approve: "Approve",
    reject: "Reject",
    change: "Ask for a change",
    ask: "“Make the ears rounder.”",
    status: "Claude Code is on it",
  },
  points: [
    [
      { b: "Every candidate side by side," },
      " with the checks behind it, so you compare instead of opening files.",
    ] as Rich,
    [
      { b: "Ask for a change in your own words." },
      " Claude Code makes it, runs the checks again, and comes back to you.",
    ] as Rich,
    [
      { b: "A desktop window for every project" },
      " on your machine: each item with its bar, its history and its next step.",
    ] as Rich,
    [
      { b: "Sounds heard mixed, words seen in place." },
      " You judge a part the way the player will meet it.",
    ] as Rich,
    [
      { b: "Claude Code cannot approve its own work." },
      " The verdict is always yours.",
    ] as Rich,
  ],
};

/* ------------------------------------------------------------------ trust */

export const trust = {
  eyebrow: "Safe by design",
  heading: "Your project. Your money. Your call.",
  items: [
    {
      icon: "laptop",
      title: "Runs on your machine",
      body: "No account and no hosted service. polyweave works on files in your own repository.",
    },
    {
      icon: "wallet",
      title: "You set the budget",
      body: "A ceiling you agree once. Every spend is bounded, quoted and written in a ledger.",
    },
    {
      icon: "shield",
      title: "You approve every look",
      body: "An agent can measure a part. Only you can accept it.",
    },
    {
      icon: "file",
      title: "Everything is a file",
      body: "Specs, records and jobs live in your repo, so a colleague can review and repeat any of it.",
    },
  ] as { icon: IconName; title: string; body: string }[],
};

/* ------------------------------------------------------------------ non-goals */

export const nonGoals = {
  eyebrow: "Deliberately not",
  heading: "What polyweave will never be.",
  intro: [
    "These constraints bind the project, and every new idea is read against them first.",
  ] as Rich,
};

/* ------------------------------------------------------------------ install */

export const install = {
  eyebrow: "Get started",
  heading: "Three lines, then just ask.",
  intro: [
    "Add the plugin from inside Claude Code. It brings the MCP server, the skill that teaches Claude Code to drive it, and the hooks that keep it safe.",
  ] as Rich,
  commands: `pip install git+https://github.com/alegauss/polyweave
/plugin marketplace add alegauss/polyweave
/plugin install polyweave@polyweave`,
  tryHeading: "Then try",
  prompt: "Set up polyweave in this project, and make me a mascot from docs/sketch.png.",
  needs: [
    "Python 3.11 or newer. Blender and Godot are optional: polyweave says which tools it found, and what each missing one would unlock.",
  ] as Rich,
};

/* ------------------------------------------------------------------ explore */

export const explore = {
  eyebrow: "Go deeper",
  heading: "How each piece works.",
};

/* ------------------------------------------------------------------ claude code page */

export const claudeCode = {
  meta: {
    title: "polyweave for Claude Code — the agent is the operator",
    description:
      "How a coding agent drives polyweave: handles for anything slow, a closed measurement vocabulary, errors that name the remedy, a per-call config resolution, and a spend ceiling the agent cannot raise.",
    ogTitle: "polyweave for Claude Code",
    ogDescription:
      "One call, right the first time — the design rules that follow from the caller being an agent in a terminal.",
  },
  eyebrow: "For an agent",
  heading: "The operator is an agent in a terminal.",
  lead: [
    "That is not a use case here, it is the premise. Every design decision in this project is judged by whether an agent gets it right on the first call without reading the implementation — and a feature that needs a GUI, a second round trip or a source read to use is a feature that has not landed.",
  ] as Rich,
  sections: [
    {
      heading: "What follows from it",
      list: [
        [
          { b: "No GUI, ever." },
          " A surface that needs a person at a screen to operate is one the agent cannot use at all. That is the first non-goal, and it is the reason for most of the others.",
        ] as Rich,
        [
          { b: "A file beats a stream." },
          " Job state, traces, contact sheets, the budget ledger and every provenance record are files under ",
          { code: ".polyweave/" },
          " in the project, so a session that ends can be picked up by the next one and a colleague can reproduce what happened.",
        ] as Rich,
        [
          { b: "Names are the address." },
          " An asset, a predicate, a rung and a job all have names, and the trace addresses them by name. An anonymous thing cannot be discussed across a turn boundary.",
        ] as Rich,
        [
          { b: "Errors are instructions." },
          " A typed code, a message with no traceback in it, and a ",
          { code: "remedy" },
          " that is the call which closes it.",
        ] as Rich,
        [
          { b: "Refusal over silence." },
          " An unknown field is refused, an unknown measure is refused, and a post-condition that fails is an error. Every one of those could have been a warning, and every one of them was a warning somewhere that cost a render.",
        ] as Rich,
      ],
    },
    {
      heading: "The one thing it may not decide",
      body: [
        "A fetch from the generative service spends real money, and the plugin will not let an agent authorise that on its own judgement. What it does instead is make the spend bounded and visible: a ceiling in ",
        { code: "polyweave.toml" },
        " that a person sets, a ledger of what has been spent against it, and a silhouette gate that refuses a request which plainly will not match the reference — because the cheapest credit is the one not spent. An agent can work continuously inside that ceiling without asking, and cannot move it.",
      ] as Rich,
    },
    {
      heading: "Configuration, resolved per call",
      body: [
        "Explicit argument, then ",
        { code: "polyweave.toml" },
        ", then the plugin default — in that order, evaluated on every call rather than cached at startup, so correcting a config file does not need a session restart. And nothing is written outside the project tree: a cache in a home directory is state a repository cannot review.",
      ] as Rich,
    },
    {
      heading: "What it will not do for you",
      body: [
        "It will not tell you a render is good. It measures what it was given a measure for, and reports the margin. Where the criterion is real and no measure can compute it — “reads as cloth rather than paper” — the answer is the contact sheet: the search returns its best handful, you see that the winner is not the one you would have chosen, and you now know the ",
        { b: "spec" },
        " is incomplete. Inventing a proxy for that criterion is how a spec ends up satisfied by a render a person rejects.",
      ] as Rich,
    },
  ],
};

/* ------------------------------------------------------------------ specs page */

export const specs = {
  meta: {
    title: "polyweave specs — the contracts more than one line depends on",
    description:
      "The tool surface, the closed measurement vocabulary, the acceptance spec and the format rules: what polyweave fixes as a contract, and what it deliberately has not specced yet.",
    ogTitle: "polyweave: the contracts",
    ogDescription:
      "A file format, a vocabulary, and a behaviour every call obeys — settled enough to build against.",
  },
  eyebrow: "The contracts",
  heading: "What is settled before the code is.",
  lead: [
    "A spec here is a contract more than one roadmap line depends on — a file format, a vocabulary, or a behaviour every tool obeys. It exists because a rationale section says ",
    { i: "why" },
    " in 250 words, and a format needs to say ",
    { i: "what" },
    ", at whatever length that takes.",
  ] as Rich,
  status: [
    { b: "Status: the contract the code is held to." },
    " Each spec is written ahead of, or beside, the lines that implement it, and a shipped line records its design in one. Where the code and a spec disagree, that is evidence about the spec, not only about the code.",
  ] as Rich,
  table: [
    {
      name: "tool-surface.md",
      fixes: "How every call behaves: handles, post-conditions, errors, self-description, conventions",
      binds: "PW1–PW6",
      written: true,
    },
    {
      name: "project-config.md",
      fixes: "What a project declares, and how a value is resolved",
      binds: "PW5",
      written: false,
    },
    {
      name: "measurements.md",
      fixes: "The closed vocabulary a comparison may return",
      binds: "PW8–PW11",
      written: true,
    },
    {
      name: "acceptance-spec.md",
      fixes: "What “correct” means, as a file a search can aim at",
      binds: "PW12, PW13, PW15",
      written: true,
    },
    {
      name: "geometry.md",
      fixes: "A shape as data rather than as a program",
      binds: "PW30–PW34",
      written: false,
    },
    {
      name: "provenance.md",
      fixes: "What is recorded beside an artefact, and the cache key",
      binds: "PW6, PW14, PW17",
      written: false,
    },
  ],
  formats: {
    heading: "Two format rules, so nobody has to decide twice",
    body: [
      { b: "TOML for documents a person authors or reads" },
      " — the project config, an acceptance spec, a geometry declaration. ",
      { b: "JSON for records a machine writes" },
      " — provenance sidecars, job state, ledgers, cache entries. The split is about who edits the file, not about what is in it. A document may also arrive as JSON where a caller emits it programmatically; a record never arrives as TOML.",
    ] as Rich,
  },
  sample: {
    heading: "An acceptance spec, in full",
    body: [
      "One file per asset, beside it or under a directory the project config names. This is the whole grammar: a list of named predicates, each naming a measure from the closed vocabulary and stating one bound, and a block per parameter the search is permitted to move.",
    ] as Rich,
    code: `asset = "mascot"
rung  = "final"          # the lowest preview rung a verdict may be taken at

[[predicate]]
id      = "face-reads-cream"
measure = "delta_e"
region  = [120, 80, 180, 140]
target  = "#E8D5C4"
max     = 2.0

[[predicate]]
id      = "silhouette-holds"
measure = "silhouette_iou"
against = "docs/design/art/ui/mascot.png"
min     = 0.97

[[predicate]]
id      = "has-a-saturated-tail"
measure = "saturation_p99"
region  = "subject"
min     = 0.85
weight  = 0.5

[search.light]
min = 0.5
max = 4.0

[search.form]
min  = 1.0
max  = 4.0
step = 0.1`,
  },
  notYet: {
    heading: "Deliberately not specced yet",
    list: [
      [
        { b: "The clip and curve format." },
        " It depends on decisions the skeleton line makes, and a format written before them would be guessing. Its own roadmap section holds the requirements until then.",
      ] as Rich,
      [
        { b: "The paid-service lock and ledger." },
        " One file written by one task, whose fields are already pinned on that line. It becomes a spec here if a second consumer appears.",
      ] as Rich,
      [
        { b: "The tool list." },
        " Which calls exist is implementation, and it follows from the tool surface rather than needing a document of its own.",
      ] as Rich,
    ],
  },
  cannot: {
    heading: "What an acceptance spec deliberately cannot say",
    body: [
      "Anything no measure can compute. ",
      { i: "“Reads as cloth rather than paper”" },
      " is a real criterion and not a predicate, and pretending otherwise by inventing a proxy for it is how a spec ends up satisfied by a render a person rejects. That case is expected rather than designed away — it is exactly what the contact sheet is for.",
    ] as Rich,
  },
};
