# The polyweave window

A desktop window onto the polyweave projects on a machine (§PW303). It finds them under
a folder a person names, opens one, and shows what it governs, by kind, with the state of
each item's record and whether it waits on a person.

```
npm ci            # once
npm start         # build and open the window
npm run build     # ui/dist and shell/dist
npm test          # every package's tests, the live window included
```

`python tools/gate.py`, at the repository root, runs the typecheck, the build and these
tests after pytest, so one gate covers both halves.

## Three packages

The layout is roadkeep's window's, whose choices were paid for once already.

- **`core`** has no Node, no DOM, no Electron and no React in scope. It holds the MCP
  client over a transport it is handed, project discovery over a lister it is handed,
  which polyweave serves a project, the inventory reader, and the bridge contract the
  other two meet on.
- **`shell`** is the Electron main process and the only place a path or a process
  appears. It holds one `python -m polyweave serve` per open project, answers each bridge
  channel with what that server says, and bundles a CommonJS preload.
- **`ui`** is React over Tailwind and the viglet design system. It draws what the bridge
  hands it, and every word it shows comes from `src/locales/en.json` or `pt-BR.json`.

## What the window holds to

**Nothing is scanned until a person names a root and a depth.** A project is a folder
holding `polyweave.toml`; hidden folders and `node_modules` are passed over, and a project's
own subfolders are not searched.

**Every fact on screen is an operation's payload.** The window never parses a TOML, a
sidecar or a JSONL itself, so a kind added in Python appears without a change here.

**The engine is named.** A project's own environment (`.venv` or `venv`) is asked first
and the PATH last, and the screen says which served it, with the server's name and
version.

**The renderer is a web page and nothing more.** It runs sandboxed and context-isolated,
with no Node, under a content security policy. It never navigates away from itself, and
the only thing it holds is one frozen bridge object the preload builds from `core`'s
interface: no `ipcRenderer`, no module, no path.

**It is local.** No account and no remote store.

## One item, beside what it was held to

The project screen filters its list to what waits on a person or what needs attention
(a record changed, missing, outdated, or never written). Choosing an item opens it beside
its `asset.brief`: each predicate with its bound and where the bound came from, its chain
back to a purchase (`provenance.generated`), and what was made from it. The window draws
a picture at its real size, plays a sound, and shows a line in each locale with its
speaker and its verdict. Any other kind is offered as the call that would draw it, such
as `shape.turntable` for a mesh or `vfx.preview` for an effect, for the agent session to
run. The window never runs one, because it is a reader and not an editor. A file reaches
the page only through `shell/src/files.ts`, which refuses any path outside the open
project and any file that is not a picture or a sound.

## The live test

`shell/src/window-live.test.ts` starts Electron in smoke mode (`POLYWEAVE_GUI_SMOKE`).
The renderer finds and opens a project under the root it is given, draws its inventory
in the language it is given, and main prints what the page drew, read back off the page.
Smoke mode can also save a picture of the window (`shot`), which is how a change to a
screen is looked at before it is handed over.
