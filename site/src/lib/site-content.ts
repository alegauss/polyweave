// The copy lives here and nowhere else. Every section component imports a value from this
// module and only renders it — so a claim is an array element a reviewer can check against
// the roadmap, not a string welded into the markup that displays it. The composition
// (which section, in which order, and the illustrative SVGs) lives in the JSX; this file
// is the words.
//
// Fragments carrying inline code or emphasis are modelled as a small tagged run list
// (`Rich`) rather than raw HTML, so a section renders them without dangerouslySetInnerHTML
// and the twin generator has a structure to convert rather than markup to parse.
//
// Two rules this file is held to, and they are the reason the project exists:
//
//   1. Every count comes from `roadmap.ts`, which reads the governed roadmap through
//      roadkeep. None of them is typed here.
//   2. Every measurement quoted is one the roadmap records against Cottony, and it is
//      named as such. There is no measurement of polyweave on this site, because there is
//      no polyweave yet to measure. A page for a product that searches for evidence does
//      not get to assert its own.
import { Spelled, blockCount, finishedCount, spelled, taskCount } from "./roadmap";
import { conventions as conventionRows, sessionTerminal } from "./diagrams";

/** How many commands the transcript actually runs, so the sentence under it can say. */
const sessionCalls = (sessionTerminal.match(/&gt;<\/span> polyweave /g) ?? []).length;

export type Run =
  | string
  | { code: string }
  | { b: string }
  | { i: string };

export type Rich = Run[];

/* ------------------------------------------------------------------ meta + chrome */

export const meta = {
  title: "polyweave — declare what a 3D asset has to be, and let it search",
  description:
    "A Claude Code plugin that makes 3D assets by declaring what they have to satisfy and searching for the parameters that satisfy it, on top of Blender, Godot and a generative mesh service. Runs on your machine, against files in your own repository.",
  og: {
    title: "polyweave",
    description:
      "State what an asset has to satisfy; let a search find the parameters that satisfy it. Measured against your own reference, not against an opinion.",
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
// resolve the same from every route. The brand and footer link home the same way.
export const navLinks = [
  { href: "#loop", label: "The loop" },
  { href: "#contract", label: "The contract" },
  { href: "/polyweave/claude-code/", label: "Claude Code" },
  { href: "/polyweave/specs/", label: "Specs" },
] as const;

export const footer = {
  links: [
    { href: "/polyweave/claude-code/", label: "Claude Code" },
    { href: "/polyweave/specs/", label: "Specs" },
    { href: repoUrl, label: "GitHub" },
    { href: roadmapUrl, label: "Roadmap" },
    { href: specsUrl, label: "Contracts" },
  ],
  disclaimer:
    "polyweave is an independent open-source project. It orchestrates Blender, Godot and a generative mesh service and re-implements none of them; it is not affiliated with, endorsed by or sponsored by any of their authors, and every mark named on this page belongs to its owner. Nothing here is installable yet — the plan, and the evidence behind each line of it, is in docs/ROADMAP.md. © 2026 Alexandre Oliveira.",
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
  badge: `${Spelled(finishedCount())} of ${spelled(blockCount())} blocks built · ${taskCount()} lines open`,
  titleLead: "Say what the asset has to be.",
  titleAccent: "Let it find the numbers.",
  sub: [
    "polyweave is a Claude Code plugin for making 3D assets — geometry, surface and motion. You state what an asset has to ",
    { b: "satisfy" },
    "; it searches for the parameters that satisfy it, measuring against ",
    { b: "your own reference" },
    " rather than against an opinion. On top of Blender, Godot and a generative mesh service, on your machine, against files in your own repository.",
  ] as Rich,
  // No emoji on these three, and that is a writing rule rather than a taste: an emoji glued
  // to the front of a feature line is the most recognisable mannerism of a generated landing
  // page, and these strings are also bullets in the Markdown twin an agent reads.
  meta: [
    "No GUI and no account",
    "Nothing leaves your machine",
    "It never spends money on its own judgement",
  ],
  pills: [
    ["Blender for the ", { b: "bake" }] as Rich,
    ["Godot for the ", { b: "world" }] as Rich,
    ["A generative service for the ", { b: "mesh" }] as Rich,
    [{ b: "TOML" }, " for what a person writes, ", { b: "JSON" }, " for what a machine does"] as Rich,
  ],
  cta: "Read the plan",
  ctaShort: "The plan",
};

/* ------------------------------------------------------------------ the stage band */
// The first thing after the transcript, and deliberately not in a footnote. Its status
// is derived from the roadmap, never typed (§PW137): the typed version said there was no
// code a hundred shipped lines after it stopped being true, and a test defended it.

export const stage = {
  eyebrow: "Read this first",
  heading: `${Spelled(finishedCount())} of ${spelled(blockCount())} blocks are built.`,
  body: [
    "polyweave is Python under ",
    { code: "src/polyweave" },
    ", served as a Claude Code plugin. What this page describes is the product ",
    { code: "docs/ROADMAP.md" },
    " and ",
    { code: "docs/specs/" },
    " specify, and ",
    { b: `${taskCount()} lines are still open across ${spelled(blockCount() - finishedCount())} blocks` },
    ". ",
  ] as Rich,
  body2: [
    "Every measurement quoted here was taken in ",
    { b: "Cottony" },
    ", the game the backlog was drawn from, and describes the cost polyweave exists to remove. ",
    { b: "None of it is a benchmark of polyweave" },
    ": the loop ledger that would measure the plugin against the hand-tuned way has only begun to record runs, and a claim this page cannot cite a run for is one it does not make.",
  ] as Rich,
};

/* ------------------------------------------------------------------ session */

export const session = {
  eyebrow: "What driving it looks like",
  note: [
    `${Spelled(sessionCalls)} calls: turn a drawing into a spec, search for the parameters that satisfy it, take the verdict at the final rung, and — on the last one — get a failure that names the door instead of a traceback. The commands are the surface `,
    { code: "docs/specs/tool-surface.md" },
    " fixes; the values are illustrative.",
  ] as Rich,
};

/* ------------------------------------------------------------------ friction */

// The cards first, so the sentence that counts them can count them. This one sentence is
// why: it said "four" for as long as there were four cards and stayed saying it when two
// more were added, which is the drift this whole module is arranged to make impossible.
const frictionCards = [
  {
    ico: "⏱",
    title: "Fourteen constants, at two minutes a sample",
    body: [
      "Cottony's render rig has fourteen tuned fields, and every one of them was found by rendering, looking, and changing it by hand. It is the single largest cost in making an asset, and it is the cost this plugin exists to remove.",
    ] as Rich,
  },
  {
    ico: "📉",
    title: "0.31 against 0.32, and plainly wrong",
    body: [
      "A board matched the concept art's mean saturation to within 0.01 and still looked washed out. The whole difference sat at the ",
      { b: "99th percentile" },
      ", which is why a measurement here is a distribution and never a single number.",
    ] as Rich,
  },
  {
    ico: "💳",
    title: "Thirty credits for a silhouette",
    body: [
      "A wide low cap was sent to the generative service and a tall dome on a long stem came back. A silhouette check against the drawing would have said so before a credit moved.",
    ] as Rich,
  },
  {
    ico: "🎲",
    title: "29,696 pixels, none by more than 1/255",
    body: [
      "Two runs of one unchanged scene. A path-traced bake is not byte-reproducible, so equality is the wrong question and a tolerance is the right one — and any usable distance metric has to sit above that noise floor.",
    ] as Rich,
  },
  {
    ico: "🔇",
    title: "A success returned over an empty mesh",
    body: [
      "Blender's ",
      { code: "EXACT" },
      " boolean returns an empty mesh with no error when its target was bevelled. The silence cost a full render to locate, which is why every operation here asserts its own output before returning.",
    ] as Rich,
  },
{
  ico: "📖",
  title: "Fourteen fields, documented as comments",
  body: [
    "The rig's parameters live in a thousand-line module, so every caller pays a file read to find out what it may set. A surface an agent has to read the implementation to use is one it will get wrong on the first call.",
  ] as Rich,
},
];

export const friction = {
  eyebrow: "The cost today",
  heading: "Generating a mesh is the cheap part.",
  intro: [
    "What is expensive is everything between ",
    { i: "having a mesh" },
    " and ",
    { i: "knowing it is right" },
    ` — and today that is a person changing one number at a time and looking at a two-minute render. ${Spelled(frictionCards.length)} measurements from Cottony, each of which put a line on the backlog.`,
  ] as Rich,
  cards: frictionCards,
};

/* ------------------------------------------------------------------ the loop */

export const loop = {
  eyebrow: "The mechanism",
  heading: "Declare it, then search for it.",
  lead: [
    "One file beside the asset says what makes a render of it correct. A search reads it, proposes values for the parameters the file permits, bakes at the cheapest rung that can answer, measures the result and scores how comfortably each predicate passed. What comes back is the winning values, a contact sheet and a trace of everything it rejected.",
  ] as Rich,
  points: [
    [
      { b: "A bound, not an expression." },
      " ",
      { code: "min" },
      ", ",
      { code: "max" },
      " and ",
      { code: "target" },
      " are the only comparisons a predicate has. Anything needing more is a measure that does not exist yet, and the honest response is to add the measure rather than widen the grammar.",
    ] as Rich,
    [
      { b: "A margin, not a verdict." },
      " Each predicate yields pass/fail ",
      { i: "and" },
      " a value in [0, 1] for how comfortably it passed. A pure boolean gives a search a cliff and nothing to climb; the margin is what makes it converge on something rather than wander.",
    ] as Rich,
    [
      { b: "The spec is the whole permission." },
      " A parameter ",
      { code: "[search.<param>]" },
      " does not name is not searched, whatever the optimiser would like. It can tune the exposure; it cannot decide the asset should be twice as large.",
    ] as Rich,
    [
      { b: "Every predicate has a name." },
      " The trace addresses them by ",
      { code: "id" },
      ", so a result can be argued with. An anonymous predicate is one nobody can discuss.",
    ] as Rich,
    [
      { b: "Cancelling is not advisory." },
      " A search that has found its answer stops paying for the renders it no longer needs, which is what makes running one affordable at all.",
    ] as Rich,
    [
      { b: "Nothing is rendered twice." },
      " The cache is keyed on the inputs, the renderer and its version, and the seed — a sweep revisits neighbourhoods, and without that key the same picture is paid for as many times as the search returns to it.",
    ] as Rich,
  ],
  sheetCaption: [
    "The contact sheet, and why it is not a nicety: the expected case is a search that satisfies the spec and returns a render a person rejects. That is the moment you find out the ",
    { b: "spec" },
    " is incomplete rather than the renderer — and it is the fastest way this loop earns its keep.",
  ] as Rich,
};

/* ------------------------------------------------------------------ seeing cheaply */

export const seeing = {
  eyebrow: "Before you pay for a render",
  heading: "Three seconds, not two minutes.",
  lead: [
    "A surface is read on a sphere, and a sphere renders in three seconds. Nothing in the old pipeline made the cheap look the default, so the expensive one is what got run — every time, for every judgement, including the ones a sphere could have settled.",
  ] as Rich,
  measures: {
    heading: "A closed vocabulary, so a spec is checkable",
    intro: [
      "A measure named in an acceptance spec has to be one of these. An unknown name is a refusal — ",
      { code: "spec.unknown-measure" },
      " — never a warning, because a spec that accepts any string is a spec that silently checks nothing.",
    ] as Rich,
    rows: [
      {
        name: "saturation_{p1,p50,p99,mean,std}",
        range: "0–1",
        what: "HSL saturation over the region, returned as a set and never as one number",
      },
      {
        name: "luma_{p1,p50,p99,mean,std}",
        range: "0–1",
        what: "Relative luminance, sRGB-weighted",
      },
      { name: "hue_spread", range: "0–1", what: "Circular standard deviation of hue, weighted by saturation" },
      { name: "alpha_coverage", range: "0–1", what: "Fraction of the region above the alpha floor" },
      {
        name: "silhouette_iou",
        range: "0–1",
        what: "Intersection over union of the alpha mask against a reference drawing",
      },
      { name: "silhouette_centroid_offset", range: "px", what: "Distance between the two mask centroids" },
      { name: "silhouette_bbox_delta", range: "px", what: "Largest per-edge difference between the bounding boxes" },
      { name: "region_colour", range: "Lab", what: "Mean CIELAB colour over the region" },
      { name: "delta_e", range: "0–100", what: "CIEDE2000 distance to a target: under 2 is a difference you have to look for" },
      { name: "distance", range: "0–1", what: "Perceptual distance between two renders, above the sampler's own noise" },
      { name: "changed_fraction", range: "0–1", what: "Fraction of pixels differing by more than a stated amount" },
      { name: "luma_bands", range: "count", what: "Distinct luminance bands surviving a downscale to the size it will be seen at" },
    ],
  },
  points: [
    [
      { b: "The picture and its numbers are one answer." },
      " A render returns the image alongside its measurements, so a verdict costs one turn rather than three.",
    ] as Rich,
    [
      { b: "The region is masked, and named." },
      " ",
      { code: "subject" },
      " means the pixels where alpha clears the floor, so a prop is measured over its own pixels and not diluted by whatever background it happens to sit on.",
    ] as Rich,
    [
      { b: "At the size it will be seen." },
      " Cottony's fluff read at 1.2 and vanished at 1.0, at a third of the sprite's authored size. ",
      { code: "luma_bands" },
      " takes the display size and downscales before counting, which is the only honest way to ask that question.",
    ] as Rich,
    [
      { b: "Beside its siblings, not alone." },
      " A prop that reads correctly on its own can be the one thing on a sheet with no shadow and no specular window, which no solo render shows.",
    ] as Rich,
  ],
};

/* ------------------------------------------------------------------ the contract */

export const contract = {
  eyebrow: "What a call costs the turn",
  heading: "One call, right the first time.",
  lead: [
    "One measure governs the whole surface: ",
    { b: "a caller gets a call right on the first attempt, and answers a failure, without opening an implementation file." },
    " Where a rule does not serve that, the rule is wrong.",
  ] as Rich,
  points: [
    [
      { b: "Anything over a couple of seconds returns a handle." },
      " A bake, a fetch, a capture and a search all do; a measurement and a config read do not. ",
      { code: "stage" },
      " is a short vocabulary, so a caller branches on a word rather than parsing a message.",
    ] as Rich,
    [
      { b: "The handle survives the session." },
      " Job state is a file in ",
      { code: ".polyweave/jobs/" },
      ", so a session that ends mid-render can be told what happened by the next one.",
    ] as Rich,
    [
      { b: "A dead worker is a failure, not a hang." },
      " The record carries the OS process id; a poll that finds no live process and no result returns ",
      { code: "job.worker-gone" },
      ".",
    ] as Rich,
    [
      { b: "An unknown field is refused, never dropped." },
      " A silent drop makes a typo indistinguishable from a working call, which is how a payload that validates comes to prove nothing.",
    ] as Rich,
    [
      { b: "The surface describes itself." },
      " ",
      { code: "describe()" },
      " returns each parameter's type, range, default and one sentence, read from the implementation, so the documentation and the code cannot drift.",
    ] as Rich,
    [
      { b: "And it describes this machine." },
      " ",
      { code: "capabilities()" },
      " says which renderer and version are here, whether an engine is reachable, which offscreen route works, whether a service key is present and what budget is left — so a caller plans against it rather than discovering a missing binary three calls later.",
    ] as Rich,
  ],
  post: {
    heading: "Every operation asserts its own output",
    intro: [
      "A success returned over a result nobody checked is a failure this plugin exists partly to remove. Before returning, each operation checks what must be true of what it produced. A failed assertion is an ",
      { b: "error" },
      ", never a warning, and its code names the assertion.",
    ] as Rich,
    rows: [
      { produces: "A mesh", asserted: "at least one face; finite bounds; no NaN in any vertex" },
      { produces: "A boolean result", asserted: "face count is not zero where both operands had faces" },
      { produces: "A render", asserted: "not a single uniform colour; not fully transparent; dimensions as requested" },
      { produces: "A texture", asserted: "not fully transparent; not a single uniform colour" },
      { produces: "A download", asserted: "byte length matches the declared length; sha256 recorded" },
      { produces: "A capture", asserted: "the named artefact exists on disk and is a readable image" },
    ],
  },
  error: {
    heading: "An error names the door",
    intro: [
      "A traceback says where the code gave up, not what the caller should do instead — which is the one thing needed to retry without another round trip.",
    ] as Rich,
    sample: `{
  "code": "render.no-material",
  "message": "the model 'mascot' carries no material, so the rig has nothing to light",
  "remedy": "set \`material\` on the model, or pass \`glaze: {roughness: 0.22}\` to apply the default",
  "detail": "…traceback, for a human…"
}`,
    after: [
      { code: "code" },
      " is stable and namespaced by area, and does not change once published. ",
      { code: "remedy" },
      " is the call that closes it, with the arguments filled in wherever they are derivable; where the choice is a judgement the tool cannot make, it names both doors and what separates them. ",
      { code: "message" },
      " never contains a traceback. ",
      { code: "detail" },
      " may.",
    ] as Rich,
  },
};

/* ------------------------------------------------------------------ the paid service */

export const service = {
  eyebrow: "Someone else's balance",
  heading: "Bounded, visible, and never the agent's call.",
  lead: [
    "A fetch draws on a real balance. The ceiling is a person's to set; the plugin's job is to make a spend bounded and visible, and never to decide one is worth it. That is a constraint on this project, not a feature of it.",
  ] as Rich,
  points: [
    [
      { b: "The silhouette is checked before the credit moves." },
      " The request carries the drawing it has to match, and a mismatch is a refusal that costs nothing.",
    ] as Rich,
    [
      { b: "A ceiling agreed once, not a question each time." },
      " The rule that an agent may not spend on its own judgement is right; enforcing it by asking every time is what stops work between approvals. The budget and the ledger are files in the project.",
    ] as Rich,
    [
      { b: "What was bought is kept." },
      " The service deletes what it made seventy-two hours later. The mesh is copied locally with its sha256 and a provenance sidecar — prompt, seed, service, version, cost — so the receipt never outlives the thing.",
    ] as Rich,
    [
      { b: "The schema is learned once and written down." },
      " Finding out what a service accepts takes a series of deliberately invalid payloads, each with a made-up field as its control. That knowledge is recorded rather than rediscovered.",
    ] as Rich,
    [
      { b: "It arrives in this project's axes." },
      " A fetched mesh comes at an arbitrary orientation, scale and origin — a hammer standing upright where the drawing leans it. Normalising it is one conversion on the boundary, not two angles found by re-rendering until it looks right.",
    ] as Rich,
    [
      { b: "The background does not become geometry." },
      " A photograph of a plush toy returned the logo the toy was sitting on, fused into the mesh, and no camera move takes that back out.",
    ] as Rich,
  ],
};

/* ------------------------------------------------------------------ the engine */

export const engine = {
  eyebrow: "One world",
  heading: "The engine's exit code is not the verdict.",
  lead: [
    "Godot exits zero on a script error and non-zero on a clean quit. The only honest signal is a line the script printed and no error in the log — and every project that has driven it headless has written that parser again.",
  ] as Rich,
  points: [
    [
      { b: "A capture runs where there is no screen." },
      " Headless mode draws nothing at all, which makes every screenshot a manual step on a developer's desk and keeps it out of any gate. ",
      { code: "capabilities()" },
      " names the offscreen route that works on this machine.",
    ] as Rich,
    [
      { b: "Scale is derived, not tuned." },
      " One unit is one pixel today because somebody set a render rectangle to match a cell size the game holds separately, and nothing fails if either moves. Here the grid is declared once and both sides read it.",
    ] as Rich,
    [
      { b: "The runner is pinned." },
      " Language, locale and settings are declared, so the same script on two machines produces the same image — and a difference is a change somebody made rather than an environment nobody stated.",
    ] as Rich,
  ],
};

/* ------------------------------------------------------------------ motion */

export const motion = {
  eyebrow: "Motion",
  heading: "A pose needs a skeleton.",
  lead: [
    "Every generative mesh arrives as a static surface, and rigging one by hand is the step that keeps character animation out of reach entirely. Everything below follows from fixing that one thing.",
  ] as Rich,
  points: [
    [
      { b: "A clip, not a second static render." },
      " A settle expressed as a squashed re-render of the same mesh is right for one beat and has no way to say what a walk or a reaction would be.",
    ] as Rich,
    [
      { b: "Curves as text." },
      " A timing change inside a binary track is invisible in a diff and unreachable by an edit, which makes every adjustment a re-export from a tool nobody scripted.",
    ] as Rich,
    [
      { b: "One source, two outputs." },
      " The same settle is frames a 2D interface crossfades to and a clip a 3D scene plays. Authoring it twice and keeping the two in step by hand is the work being removed.",
    ] as Rich,
  ],
};

/* ------------------------------------------------------------------ geometry */

export const geometry = {
  eyebrow: "Geometry",
  heading: "A shape is data, not a program.",
  lead: [
    "Cottony's tray, star, ball and props are four modules of imperative geometry code, and the shape each one describes is not readable without running it. A declaration is the same shape in a file a person can read, a search can reach and a reviewer can argue with.",
  ] as Rich,
  points: [
    [
      { b: "The vocabulary is read off real assets." },
      " Extruded outlines, crowned plates, radial arrays, annuli and boolean pockets — because a format covering only primitives would leave every real asset back in code.",
    ] as Rich,
    [
      { b: "Its numbers are reachable." },
      " Geometry constants sit inside a module while the rig's sit in a dataclass, so a search can reach the lighting and never the shape it is lighting. In a declaration both are fields.",
    ] as Rich,
    [
      { b: "It can be reviewed before it is built." },
      " Two wrong constructions of one tray's seats each looked reasonable while being written and were only visible once rendered, which is the expensive place to find out.",
    ] as Rich,
    [
      { b: "And there is a way back to code." },
      " Any format will meet a shape it cannot state, and forcing that shape into the format produces worse geometry than the script it replaced. The escape hatch is part of the design, not an admission.",
    ] as Rich,
  ],
};

/* ------------------------------------------------------------------ conventions */

export const conventions = {
  eyebrow: "Fixed once",
  heading: `${Spelled(conventionRows.length)} decisions nothing downstream has to guess.`,
  intro: [
    "Stated in ",
    { code: "docs/specs/tool-surface.md" },
    " so that no other spec has to repeat them and no ingest has to invent one.",
  ] as Rich,
};

/* ------------------------------------------------------------------ feature index */

export const featureIndex = {
  eyebrow: "In depth",
  heading: "The seven blocks, one page each.",
  intro: [
    "Each block on the roadmap is a group of lines that share a failure. These pages carry the lines themselves — the symptom in the roadmap's own words, and the measurement behind it.",
  ] as Rich,
};

/* ------------------------------------------------------------------ non-goals */

export const nonGoals = {
  eyebrow: "Deliberately not",
  heading: "What this will not be.",
  intro: [
    "Five constraints bind the project, and they are governed alongside the backlog: a proposal is read against them before it becomes a line. The sharpest is the third.",
  ] as Rich,
};

/* ------------------------------------------------------------------ proof */

export const proof = {
  eyebrow: "The last block",
  heading: "Measured against what it replaced.",
  body: [
    "Cottony is the first consumer and the test of whether the configuration boundary holds — an adoption that needs a fork proves that it does not. It is also where the claim gets settled: nothing today records how long a correct asset took before and after, so there is no way to tell a real improvement from a rearrangement of the same work.",
  ] as Rich,
  body2: [
    "Until that line ships, every number on this page is Cottony's cost and not polyweave's saving. That is the honest state of it, and it is why the benchmark is on the roadmap rather than in the pitch.",
  ] as Rich,
};

/* ------------------------------------------------------------------ the close */

export const close = {
  eyebrow: "Where it stands",
  heading: "Nothing to install yet.",
  body: [
    "The plan is the artefact. ",
    { code: "docs/ROADMAP.md" },
    " holds ",
    { b: `${taskCount()} lines` },
    ", each one a failure measured in a real project rather than a feature somebody wanted, and ",
    { code: "docs/specs/" },
    " holds the contracts that more than one of them depends on. Both are worth reading before the code exists, because that is when they are still cheap to argue with.",
  ] as Rich,
  ctaPrimary: "Read the roadmap",
  ctaGhost: "★ View on GitHub",
  // Split around the link rather than carrying one in the run list: a `Rich` run is text,
  // code, bold or italic, and adding a fifth kind for the one anchor on the page would put
  // href handling into the twin generator for no other caller.
  noteLead: ["The roadmap, the changelog and the rationale file are governed by "] as Rich,
  noteLink: "roadkeep",
  noteTail: [
    ", which refuses a hand edit — so a line shipped is a line removed from the backlog and written into the ledger by a tool, and the counts on this page are generated from it rather than typed.",
  ] as Rich,
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

/* ------------------------------------------------------------------ shared bits */

export const evidence = {
  eyebrow: "Where the evidence comes from",
  // The count is derived; the sentence is a sentence. That split is the rule this whole
  // module follows, and it is the one that survives somebody reworking the copy.
  heading: `Every one of the ${taskCount()} lines is a failure somebody measured.`,
  body: [
    { b: "Cottony" },
    " is a real game, and it is where nearly every symptom in this backlog was measured: a fourteen-field render rig found by hand at two minutes a sample, a silhouette bought for thirty credits, a percentile that disagreed with a mean, and two runs of one unchanged scene that differed in 29,696 pixels. The backlog was not imagined and then justified — it was read off a project that already hurt.",
  ] as Rich,
  stats: [
    { value: String(taskCount()), label: "lines, each with its measurement" },
    { value: Spelled(blockCount()), label: "blocks, grouped by the failure they share" },
    { value: "0", label: "shipped, because this is a plan and not a product" },
  ],
};
