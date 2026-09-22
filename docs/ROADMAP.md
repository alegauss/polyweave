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

- 📋 **PW46** (deps: —) **a normalised mesh sits beside the paid one with nothing recording what it derives from** — Ingest writes a second file and returns the transform to its caller, so the mesh the project loads is one `verify` reads as an artefact nothing recorded. → §PW46

## Block E — One world with the engine

- 📋 **PW47** (deps: PW24 ✅) **a bake renders square at the rung's size, so a declared world rectangle can be refused but never met** — PW24's contract names the size a sprite must be, and nothing renders at it: the size is the rung's, and it is not in the cache key either. → §PW47

## Block F — Motion

## Block G — Geometry as a declaration

## Block H — Proof on a real game

- 📋 **PW36** (deps: PW5 ✅) **a real project cannot adopt the plugin without carrying its own paths and palette into it** — Cottony is the first consumer and the test of whether the configuration boundary holds, and an adoption that needs a fork proves that it does not. → §PW36
- 📋 **PW48** (deps: —) **every test input is synthetic, so nothing is ever checked against an artefact somebody made** — The suite has no real mesh, photograph or capture in it, and those are where every symptom in this backlog was measured in the first place. → §PW48

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
