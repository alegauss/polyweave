# Roadmap (active backlog)

## Block A — What a tool call costs the turn

- 📋 **PW37** (deps: —) **a renderer outlives the worker that started it, and a sweep on Windows cannot find it to end it** — taskkill walks a tree from the living parent, so a worker that died takes its handle to its children with it, and the render goes on spending a core nobody is watching. → §PW37
- 📋 **PW38** (deps: —) **a height field survives an eight-bit round trip as a staircase, and every assertion says it is fine** — The third silent failure behind the post-conditions is a blur that quantises a gradient, invisible in a shadow and ruinous under a specular, and no colour or coverage check sees it. → §PW38
- 📋 **PW39** (deps: —) **a job checks only that an argument exists while a direct call checks its range, so one call has two contracts** — The worker reads a target's signature and describe reads its registration, so a value the surface would refuse still costs a spawn and a failed job to discover. → §PW39
- 📋 **PW40** (deps: —) **a tolerance has one default in the project config and a different one in the function that uses it** — A check falls back to an alpha floor of zero while the config declares 0.02, so an operation that forgets to pass it measures the background as part of the subject. → §PW40
- 📋 **PW41** (deps: —) **an artefact that was produced without a record is invisible, because verify starts from the records** — A paid mesh with no sidecar reads as a sound project, and re-buying it is the only way to find out what it was made from. → §PW41
- 📋 **PW42** (deps: —) **a render that is black to any observer passes the check for a blank render, on one bit of edge noise** — The assertion asks whether every visible pixel is exactly one colour, and an unlit Cycles render came back with two: black, and 1/255 at the antialiased edge. → §PW42

## Block B — Seeing the result cheaply

- 📋 **PW43** (deps: —) **a colour measured off a render is not the colour that was authored, and nothing says so** — An emission that should land on sRGB 128 came back at 161, and at 172 after asking for the standard view transform, because this Blender ships without the colour configuration. → §PW43
- 📋 **PW44** (deps: —) **one configured noise floor calls every preview-sized render a change, because the floor moves with the rung** — Two seeds of one scene measured 0.046 apart at four samples and 0.014 at sixty-four, against a configured default of 0.004 calibrated for a final render. → §PW44

## Block C — The asset compiler

- 📋 **PW45** (deps: —) **a search renders its samples one after another, so a budget of twenty-four costs twenty-four waits** — The job handles exist so four samples can run at once, and the search calls its evaluator once per sample and waits for each render before proposing the next. → §PW45

## Block D — Fetching from a paid service without surprise

- 📋 **PW19** (deps: —) **an unknown field is dropped in silence, so a payload that validates proves nothing** — Learning the schema takes a series of deliberately invalid values, each carrying a made-up field as its control, and none of that knowledge is kept anywhere. → §PW19
- 📋 **PW20** (deps: —) **a fetched mesh arrives at an arbitrary orientation, scale and origin** — The service returned a hammer standing upright where the drawing leans it, and the correction was two angles found by re-rendering until it looked right. → §PW20
- 📋 **PW21** (deps: —) **a reference photograph brings whatever stood behind the subject back as geometry** — A picture of a plush toy returned the logo the toy was sitting on, fused into the mesh, and no camera move takes it back out again. → §PW21

## Block E — One world with the engine

- 📋 **PW22** (deps: —) **the engine's exit code is not the verdict, so each project writes its own output parser** — Godot exits zero on a script error and non-zero on a clean quit, so the only honest signal is a line the script printed and no error in the log. → §PW22
- 📋 **PW23** (deps: PW22) **a real renderer needs a window, so a capture cannot run where there is no screen** — Headless mode draws nothing at all, which makes every screenshot a manual step on a developer's desk and keeps it out of any gate. → §PW23
- 📋 **PW24** (deps: —) **the baked sprite and the running game agree on scale only because a constant was tuned** — One unit is one pixel because somebody set the render rectangle to match a cell size the game holds separately, and nothing fails if either moves. → §PW24
- 📋 **PW25** (deps: PW22) **a capture takes its picture in whatever language and settings the runner happens to have** — The same script on two machines produces two different images, and the difference is a locale nobody declared rather than a change anybody made. → §PW25

## Block F — Motion

- 📋 **PW26** (deps: —) **a fetched mesh has no skeleton, so it cannot be posed at all** — Every generative mesh arrives as a static surface, and rigging one by hand is the step that keeps character animation out of reach entirely. → §PW26
- 📋 **PW27** (deps: PW26) **motion is expressed as a second static render, so nothing longer than two frames exists** — A settle is a squashed re-render of the same mesh, which is right for one beat and has no way to say what a walk or a reaction would be. → §PW27
- 📋 **PW28** (deps: PW27) **an animation lives in a binary track, so a curve cannot be reviewed or edited as text** — A timing change inside a mesh file is invisible in a diff and unreachable by an edit, which makes every adjustment a re-export from a tool nobody scripted. → §PW28
- 📋 **PW29** (deps: PW27) **a 2D screen needs frames and a 3D scene needs a clip, so the motion is authored twice** — The same settle exists as a sprite the interface crossfades to and as something a 3D scene would play, and keeping the two in step is manual. → §PW29

## Block G — Geometry as a declaration

- 📋 **PW30** (deps: —) **a shape is a Python script, so stating one means writing and debugging a program** — Cottony's tray, star, ball and props are four modules of imperative geometry code, and the shape each describes is not readable without running it. → §PW30
- 📋 **PW31** (deps: PW30) **a format covering only primitives would leave every real asset in code** — The existing models use extruded outlines, crowned plates, radial arrays, annuli and boolean pockets, so the vocabulary has to be read off what they already do. → §PW31
- 📋 **PW32** (deps: PW13 ✅, PW30) **a shape's own numbers are unreachable from the search that tunes everything else** — Geometry constants live inside a module while the rig's live in a dataclass, so a search can reach the lighting and never the shape it is lighting. → §PW32
- 📋 **PW33** (deps: PW30) **a shape cannot be reviewed without building it, so a wrong construction is found in the render** — Two wrong constructions of one tray's seats each looked reasonable while being written and were only visible once rendered, which is the expensive place. → §PW33
- 📋 **PW34** (deps: PW30) **a declaration that cannot express a shape leaves no way back to code** — Any format will meet a shape it cannot state, and forcing that shape into the format produces worse geometry than the script it replaced. → §PW34

## Block H — Proof on a real game

- 📋 **PW35** (deps: PW13 ✅) **the plugin's value is asserted and never measured against what it replaced** — Nothing records how long a correct asset took before or after, so there is no way to tell a real improvement from a rearrangement of the same work. → §PW35
- 📋 **PW36** (deps: PW5 ✅) **a real project cannot adopt the plugin without carrying its own paths and palette into it** — Cottony is the first consumer and the test of whether the configuration boundary holds, and an adoption that needs a fork proves that it does not. → §PW36

## Non-goals

- **A graphical editor** The caller here is an agent in a terminal, so a surface that
  needs a person at a screen to operate is one the agent cannot use at all.
- **Replacing Blender, Godot or the generative service** Those three already do the
  work; what is missing is the loop around them, so this orchestrates and measures and
  never re-implements a renderer, an engine or a mesh generator.
- **Spending money on the agent's own judgement** A fetch draws on a real balance, so
  the ceiling is a person's to set and the plugin's job is to make a spend bounded and
  visible, never to decide one is worth it.
- **One project's palette, rig or paths compiled in** Cottony is the first consumer and
  not the specification, so anything it needs that a second project would not is
  configuration, and a default that cannot be overridden is a defect.
- **A hosted service or an account to sign into** Everything runs on the developer's
  machine against files in their own repository, because a plugin that needs an account
  is one that fails on the day the account does.
