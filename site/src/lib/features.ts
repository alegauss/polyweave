import type { Rich } from "./site-content";
import { blockTitle, tasksIn } from "./roadmap";

// The seven depth pages, one record each, one per roadmap block. The route, the title and
// the description are all read off the same record (in routes.tsx), so a new pillar cannot
// ship half-declared or untitled: add a record here and its route, its <head> and its page
// all appear together, or none of them do.
//
// `block` is the letter the roadmap files those lines under. The page renders the block's
// own lines from the generated module, so a depth page carries the backlog rather than a
// second description of it — and `blockTitle` throws at import time if the letter is gone,
// which fails the build rather than publishing a page about a block that no longer exists.

export interface FeatureSection {
  heading: string;
  body?: Rich;
  list?: Rich[];
}

export interface FeatureRecord {
  slug: string;
  /** the roadmap block this page is the long form of */
  block: string;
  title: string;
  description: string;
  ogTitle: string;
  ogDescription: string;
  eyebrow: string;
  heading: string;
  lead: Rich;
  /** a diagram key resolved to markup in the page component */
  figure?: "loop" | "rungs" | "sheet" | "fetch" | "geometry";
  sections: FeatureSection[];
}

export const features: FeatureRecord[] = [
  {
    slug: "tool-surface",
    block: "A",
    title: "The tool surface: what a call costs the turn",
    description:
      "Handles for anything slow, a post-condition on every operation, typed errors that name the remedy, a surface that describes itself and this machine, and configuration resolved per call.",
    ogTitle: "polyweave: the tool surface",
    ogDescription: "One call, right the first time, without reading the implementation.",
    eyebrow: "Block A",
    heading: "What a call costs the turn",
    lead: [
      "The caller is an agent in a terminal, and the measure for everything in this block is that it ",
      { b: "gets a call right on the first attempt, and answers a failure, without opening an implementation file" },
      ". Where a rule does not serve that, the rule is wrong.",
    ],
    sections: [
      {
        heading: "Slow calls return a handle",
        body: [
          "Anything expected to exceed roughly two seconds is asynchronous: a bake, a fetch, a capture and a search. ",
          { code: "start" },
          " gives a job, ",
          { code: "poll" },
          " gives a stage from a short fixed vocabulary, ",
          { code: "result" },
          " blocks only if asked to, and ",
          { code: "cancel" },
          " actually stops paying. State is a file under ",
          { code: ".polyweave/jobs/" },
          ", so a handle outlives the session that made it, and a poll that finds no live process and no result returns ",
          { code: "job.worker-gone" },
          " rather than hanging.",
        ],
      },
      {
        heading: "Concurrency belongs to the caller",
        body: [
          "Four handles is four parallel samples, bounded by one number in the project config. Nothing in the plugin decides how much of your machine a search may use.",
        ],
      },
      {
        heading: "Every operation asserts its own output",
        list: [
          ["A mesh: at least one face, finite bounds, and no NaN in any vertex."],
          ["A boolean: a face count that is not zero where both operands had faces."],
          ["A render: not a single uniform colour, not fully transparent, and the dimensions that were asked for."],
          ["A download: a byte length matching the declared one, with the sha256 recorded."],
          [
            "Expensive assertions — a manifold check on a dense mesh — are opt-in and off by default. The cheap ones above always run, because the alternative is what cost the render that put this block on the roadmap.",
          ],
        ],
      },
      {
        heading: "Nothing outside the project tree",
        body: [
          "Working state goes in ",
          { code: ".polyweave/" },
          ", which belongs in ",
          { code: ".gitignore" },
          ". A cache in a home directory is state a repository cannot review and a colleague cannot reproduce.",
        ],
      },
    ],
  },
  {
    slug: "preview",
    block: "B",
    title: "Seeing the result cheaply: rungs, and a closed vocabulary",
    description:
      "A surface is read on a sphere in three seconds, a render returns its measurements in the same answer, a distribution is reported as a set rather than a mean, and a sheet shows an asset beside its siblings.",
    ogTitle: "polyweave: seeing the result cheaply",
    ogDescription: "Three seconds, not two minutes — and a percentile, not a mean.",
    eyebrow: "Block B",
    heading: "Seeing the result cheaply",
    lead: [
      "A surface is read on a sphere, and a sphere renders in three seconds. Nothing made the cheap look the default, so the expensive one is what got run — and the verdict it produced was no better.",
    ],
    figure: "rungs",
    sections: [
      {
        heading: "The rung is reported, never inferred",
        body: [
          "Every measurement comes back with the preview level it was taken at, so a verdict taken on a sphere is never mistaken for one taken on the final mesh. An acceptance spec names the lowest rung it will accept a verdict from.",
        ],
      },
      {
        heading: "A distribution, not a number",
        body: [
          "Cottony's board matched the concept art's mean saturation to within 0.01 and looked plainly wrong, because the entire difference sat at the 99th percentile. So a call asking for ",
          { code: "saturation" },
          " returns ",
          { code: "p1" },
          ", ",
          { code: "p50" },
          ", ",
          { code: "p99" },
          ", the mean and the standard deviation, and a predicate names the one it means.",
        ],
      },
      {
        heading: "Measured over its own pixels",
        body: [
          { code: "subject" },
          " means the pixels where alpha clears the floor, and it is the default wherever an image has an alpha channel. Half the value of the whole vocabulary is in that masking: a prop measured over only its own pixels is not diluted by whatever background it happens to sit on.",
        ],
      },
      {
        heading: "Equality is the wrong question",
        body: [
          "Two runs of one unchanged Cottony scene differed in 29,696 pixels, none of them by more than 1/255. That is the noise floor any usable distance metric has to sit above, and the first implementation has to demonstrate the separation on that case rather than assert it.",
        ],
      },
    ],
  },
  {
    slug: "compiler",
    block: "C",
    title: "The asset compiler: a spec, a search, and a trace",
    description:
      "What counts as a correct render, written as a file a search can aim at; a search that finds the rig numbers instead of a person finding them by hand; a cache so nothing renders twice; and a trace of everything the search rejected.",
    ogTitle: "polyweave: the asset compiler",
    ogDescription: "Declare it, search for it, and keep the argument the search had.",
    eyebrow: "Block C",
    heading: "The asset compiler",
    lead: [
      "This is the block the rest of the plugin exists to make possible. Fourteen tuned constants found by hand at two minutes a sample is the single largest cost in making an asset — and the only reason it is paid by a person is that nothing anywhere states what the right answer would look like.",
    ],
    figure: "loop",
    sections: [
      {
        heading: "The margin is what makes it converge",
        body: [
          "Each predicate yields pass/fail ",
          { i: "and" },
          " a value in [0, 1] for how comfortably it passed, normalised against its own bound. A pure boolean gives a search a cliff and nothing to climb. The overall score is the weighted mean of the margins.",
        ],
      },
      {
        heading: "The spec is the whole permission",
        body: [
          "A parameter not named in a ",
          { code: "[search.<param>]" },
          " block is not searched, whatever the optimiser would like. That is what stops a search reaching a value that is wrong for reasons the spec does not capture: it can tune the exposure, and it cannot decide the asset should be twice as large.",
        ],
      },
      {
        heading: "And the spec is the thing being debugged",
        body: [
          "The expected case is a search that satisfies every predicate and returns a render a person rejects. The contact sheet is what makes that visible — the best handful side by side, so you see that the winner is not the one you would have chosen and now know the ",
          { b: "spec" },
          " is incomplete rather than the renderer. Finding that out fast is the point.",
        ],
      },
    ],
  },
  {
    slug: "fetch",
    block: "D",
    title: "Buying a mesh without surprise",
    description:
      "A silhouette gate before the credit moves, a ceiling agreed once instead of a question per fetch, the mesh kept because the service deletes it at seventy-two hours, and a fetched asset normalised into this project's axes.",
    ogTitle: "polyweave: the paid service",
    ogDescription: "Bounded, visible, and never the agent's call.",
    eyebrow: "Block D",
    heading: "Fetching without surprise",
    lead: [
      "A fetch draws on a real balance, so the ceiling is a person's to set and the plugin's job is to make a spend bounded and visible — never to decide one is worth it. Every line in this block is a way of spending less, or of keeping what was bought.",
    ],
    figure: "fetch",
    sections: [
      {
        heading: "The cheapest credit is the one not spent",
        body: [
          "A wide low cap was sent and a tall dome on a long stem came back: thirty credits to learn something a silhouette check against the drawing would have shown for nothing. The check runs before the request, and a mismatch is a refusal.",
        ],
      },
      {
        heading: "A ceiling, not a question each time",
        body: [
          "The rule that an agent may not spend on its own judgement is right, and enforcing it by asking every time is what stops work between approvals. A ceiling set once by a person, with a ledger of what has gone against it, is the same rule enforced in a way an agent can work inside.",
        ],
      },
      {
        heading: "The receipt must not outlive the thing",
        body: [
          "The service deletes what it made seventy-two hours later. One Cottony run recorded the settings it proved and not the mesh, and the mesh is now gone — so what comes back is copied locally with its sha256 and a provenance sidecar naming the prompt, the seed, the service, its version and the cost.",
        ],
      },
      {
        heading: "It arrives usable",
        body: [
          "A fetched mesh comes at an arbitrary orientation, scale and origin, and a photograph brings whatever stood behind the subject back as geometry. Both are fixed on the boundary: the axes and the origin are this project's conventions, and the background is removed before it can be fused into a mesh no camera move takes it out of.",
        ],
      },
    ],
  },
  {
    slug: "engine",
    block: "E",
    title: "One world with the engine",
    description:
      "A Godot run judged by what the script printed rather than by an exit code that means nothing, a capture that works where there is no screen, a scale derived instead of tuned, and a runner pinned so two machines agree.",
    ogTitle: "polyweave: one world with the engine",
    ogDescription: "The exit code is not the verdict, and headless draws nothing.",
    eyebrow: "Block E",
    heading: "One world with the engine",
    lead: [
      "Godot exits zero on a script error and non-zero on a clean quit. The only honest signal is a line the script printed and no error in the log — and every project that has driven it from a script has written that parser again, slightly differently.",
    ],
    sections: [
      {
        heading: "Headless draws nothing at all",
        body: [
          "A real renderer needs a window, which makes every screenshot a manual step on a developer's desk and keeps it out of any gate. Which offscreen route works on a given machine is something ",
          { code: "capabilities()" },
          " answers before a capture is attempted, rather than something a caller discovers from a blank image.",
        ],
      },
      {
        heading: "The sprite grid is declared once",
        body: [
          "A baked sprite and the running game agree on scale today because somebody set a render rectangle to match a cell size the game holds separately, and nothing fails if either moves. One declaration both sides read is the difference between an agreement and a coincidence.",
        ],
      },
      {
        heading: "Two machines, one image",
        body: [
          "The same capture script on two machines produces two different images, and the difference is a locale nobody declared rather than a change anybody made. Language and settings are pinned by the runner, so a difference in the output is a difference in the work.",
        ],
      },
    ],
  },
  {
    slug: "motion",
    block: "F",
    title: "Motion: a skeleton, a clip, and a curve you can read",
    description:
      "A fetched mesh rigged so it can be posed at all, motion as a clip rather than a second static render, curves as text a diff can show, and one source for both a 2D sprite and a 3D scene.",
    ogTitle: "polyweave: motion",
    ogDescription: "A pose needs a skeleton, and a timing change needs to be visible in a diff.",
    eyebrow: "Block F",
    heading: "Motion",
    lead: [
      "Every generative mesh arrives as a static surface, and rigging one by hand is the step that keeps character animation out of reach entirely. This block is the shortest on the roadmap and the most dependent: each line waits on the one before it.",
    ],
    sections: [
      {
        heading: "Two frames is not motion",
        body: [
          "A settle expressed as a squashed re-render of the same mesh is right for exactly one beat, and has no way to say what a walk or a reaction would be. A clip does.",
        ],
      },
      {
        heading: "A curve is text or it is unreachable",
        body: [
          "A timing change inside a binary track is invisible in a diff and unreachable by an edit, which makes every adjustment a re-export from a tool nobody scripted. The format is deliberately unwritten until the skeleton decisions are made, because a format written before them would be guessing.",
        ],
      },
      {
        heading: "One settle, two outputs",
        body: [
          "The same motion exists as frames a 2D interface crossfades to and as something a 3D scene plays. Authoring it twice and keeping the two in step by hand is the work this removes.",
        ],
      },
    ],
  },
  {
    slug: "geometry",
    block: "G",
    title: "Geometry as a declaration",
    description:
      "A shape stated as data rather than written as a program: a vocabulary read off real assets, numbers a search can reach, a review before anything is built, and a way back to code for the shape no format can state.",
    ogTitle: "polyweave: geometry as a declaration",
    ogDescription: "A shape a reviewer can read without running it.",
    eyebrow: "Block G",
    heading: "Geometry as a declaration",
    lead: [
      "Cottony's tray, star, ball and props are four modules of imperative geometry code, and the shape each one describes is not readable without running it. Stating a shape should not mean writing and debugging a program.",
    ],
    figure: "geometry",
    sections: [
      {
        heading: "Read off what the assets already do",
        body: [
          "A format covering only primitives would leave every real asset back in code. The vocabulary comes from the existing models: extruded outlines, crowned plates, radial arrays, annuli and boolean pockets — not from a list of shapes that seemed reasonable.",
        ],
      },
      {
        heading: "Numbers the search can reach",
        body: [
          "Geometry constants live inside a module while the rig's live in a dataclass, so a search can reach the lighting and never the shape it is lighting. A declaration puts both in the same place, which is the whole reason this block is worth doing at all.",
        ],
      },
      {
        heading: "The escape hatch is part of the design",
        body: [
          "Any format will meet a shape it cannot state, and forcing that shape into the format produces worse geometry than the script it replaced. A declaration that cannot express a shape has to leave a way back to code, and saying so now is cheaper than discovering it later.",
        ],
      },
    ],
  },
];

// Import-time, in both directions: a record naming a block the roadmap has lost would
// otherwise publish a page with an empty backlog under a heading that promises one.
(function assertBlocksExist(): void {
  for (const f of features) {
    blockTitle(f.block);
    if (tasksIn(f.block).length === 0) {
      throw new Error(
        `features: block ${f.block} ("${f.slug}") has no open lines — the page would be empty`,
      );
    }
  }
})();
