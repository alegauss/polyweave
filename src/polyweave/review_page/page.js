// The page reads what is on disk and has one write, verdict.judge (§PW172). It is laid
// out for the person deciding, not for the tool (§PW287): each family is a card with
// the picture, what it is, and the choices as buttons that say what each one leads to.
// Every word the person reads comes from review_page/locales/<language>.json.
"use strict";

let words = {};
// Each kind of sitting's words, which read an older sitting too (§PW293).
let kinds = {};
const t = (key, fields = {}) =>
  (words[key] || key).replace(/\{(\w+)\}/g, (_, name) => (name in fields ? fields[name] : ""));

async function speak(language) {
  if (words.__language === language) return;
  const answer = await fetch("/locales/" + encodeURIComponent(language) + ".json");
  const catalog = await answer.json();
  words = { ...catalog.page, __language: language };
  kinds = catalog.kinds || {};
  document.documentElement.lang = language;
  for (const [id, key] of Object.entries({
    heading: "heading", "advanced-title": "advanced", "canons-title": "canons_title",
    "show-canons": "show_canons", "pending-title": "pending_title", "th-asset": "th_asset",
    "th-waiting": "th_waiting", "th-candidate": "th_candidate", "th-judged": "th_judged",
  })) document.getElementById(id).textContent = t(key);
  document.title = t("heading") + " · polyweave";
  document.getElementById("zoom-close").setAttribute("aria-label", t("close"));
}

const element = (tag, attributes = {}, ...children) => {
  const made = document.createElement(tag);
  for (const [key, value] of Object.entries(attributes)) made.setAttribute(key, value);
  for (const child of children) if (child !== null && child !== undefined) made.append(child);
  return made;
};
const file = (path) => "/file?path=" + encodeURIComponent(path);
const when = (at) => {
  const date = new Date(at);
  return isNaN(date) ? at : date.toLocaleString(words.__language, { dateStyle: "medium", timeStyle: "short" });
};

async function state() {
  const answer = await fetch("/api/state", { cache: "no-store" });
  return answer.json();
}

// A picture shown whole on a click, since a sheet of six stills is small in a card.
function zoomable(path, alt) {
  const figure = element("figure", { class: "picture", title: t("zoom") },
    element("img", { src: file(path), alt }), element("figcaption", {}, t("zoom")));
  figure.addEventListener("click", () => {
    const dialog = document.getElementById("zoom");
    dialog.querySelector("img").src = file(path);
    dialog.querySelector("img").alt = alt;
    dialog.showModal();
  });
  return figure;
}

// Where it is wrong, drawn over the member's own picture (§PW174). A drag draws a box,
// in the picture's own pixels, whatever size it is shown at; the server turns the boxes
// into a mask the picture's size and keeps it with the answer.
function marker(member, marks) {
  const shapes = [];
  marks.push({ member: member.name, shapes });
  const holder = element("div", { class: "mark" });
  const picture = element("img", { src: file(member.new), alt: t("mark_alt", { name: member.name }) });
  const canvas = element("canvas", { "aria-label": t("mark_alt", { name: member.name }) });
  const clear = element("button", { type: "button", class: "secondary" }, t("clear_marks"));
  holder.append(element("p", { class: "facts" }, t("mark_help")),
    element("div", { class: "frame" }, picture, canvas), clear);
  const scale = () => picture.naturalWidth / picture.clientWidth;
  const paint = (extra) => {
    canvas.width = picture.clientWidth;
    canvas.height = picture.clientHeight;
    const pen = canvas.getContext("2d");
    pen.strokeStyle = "#ff3b30";
    pen.lineWidth = 2;
    for (const box of extra ? [...shapes.map((s) => s.box), extra] : shapes.map((s) => s.box)) {
      const k = scale();
      pen.strokeRect(box[0] / k, box[1] / k, (box[2] - box[0]) / k, (box[3] - box[1]) / k);
    }
  };
  picture.addEventListener("load", () => paint());
  let start = null;
  const at = (event) => {
    const frame = canvas.getBoundingClientRect();
    const k = scale();
    return [(event.clientX - frame.left) * k, (event.clientY - frame.top) * k];
  };
  canvas.addEventListener("pointerdown", (event) => { start = at(event); });
  canvas.addEventListener("pointermove", (event) => { if (start) paint([...start, ...at(event)]); });
  canvas.addEventListener("pointerup", (event) => {
    if (!start) return;
    const end = at(event);
    const box = [Math.min(start[0], end[0]), Math.min(start[1], end[1]),
      Math.max(start[0], end[0]), Math.max(start[1], end[1])].map(Math.round);
    if (box[2] - box[0] > 1 && box[3] - box[1] > 1) shapes.push({ box });
    start = null;
    paint();
  });
  clear.addEventListener("click", () => { shapes.length = 0; paint(); });
  return holder;
}

// A sound beside the one it replaces (§PW256): each plays on its own player, a loop
// looped so its seam is heard, with what sound.measure says of it.
function listen(member) {
  const holder = element("div", { class: "listen" });
  for (const key of ["old", "new"]) {
    if (!member[key]) continue;
    const player = element("audio", {
      controls: "", preload: "auto", src: file(member[key]), "aria-label": t(key === "old" ? "before" : "after"),
    });
    if (member.loop) player.setAttribute("loop", "");
    const measured = (member.measured || {})[key] || {};
    const said = Object.entries(measured)
      .filter(([, value]) => typeof value === "number")
      .map(([name, value]) => name + " " + value).join(", ");
    holder.append(element("p", {}, element("strong", {}, t(key === "old" ? "before" : "after"))),
      player, element("p", { class: "measured" }, said));
  }
  return holder;
}

// A choice from a sitting written before choices said what they lead to (§PW287).
const asChoice = (word, choice, kind = "look") => {
  if (typeof choice !== "string") return choice;
  // A sitting laid out before choices said what they lead to keeps them as English
  // strings; the catalog knows them by their key (§PW293).
  const known = ((kinds[kind] || {}).choices || {})[word];
  return known || { label: word, means: choice, then: "" };
};

function legend(entries) {
  const list = element("dl", { class: "legend" });
  for (const [name, meaning] of Object.entries(entries)) {
    list.append(element("dt", {}, name), element("dd", {}, meaning));
  }
  return list;
}

// A card's id, one per family of one sitting: two sittings may name the same family.
const cardId = (manifest, name) => "family-" + manifest + "#" + name;

// What a card shows, the first of these a family has (§PW287, §PW291): a line as words,
// large, with who says it; films playing side by side; the pictures themselves, the
// old beside the new; else the sheet the tool drew. A sheet behind the first three is
// one click away.
function visual(laid, name) {
  const members = laid.members || [];
  const spoken = members.filter((member) => member.text);
  const films = members.flatMap((member) => member.films || []);
  const shown = members.filter((member) => member.new && !member.sound);
  const figure = (label, path) => element("figure", {}, element("figcaption", {}, label),
    element("img", { src: file(path), alt: label }));
  if (spoken.length) {
    return spoken.map((member) => {
      const who = member.who || member.speaker || "";
      const quote = element("div", { class: "line" },
        element("p", { class: "who" }, t("says", { who })),
        ...Object.entries(member.text).map(([locale, text]) =>
          element("blockquote", { lang: locale }, text)),
        element("p", { class: "key" }, member.line));
      if ((member.examples || []).length) {
        quote.append(element("p", { class: "facts" }, t("examples", { who })),
          element("ul", { class: "examples" }, ...member.examples.map((one) => element("li", {}, one))));
      }
      return quote;
    });
  }
  if (films.length) {
    return [element("div", { class: "films" }, ...films.map((film) => figure(film.label, film.path))),
      element("details", { class: "frames" }, element("summary", {}, t("frames")), zoomable(laid.sheet, name))];
  }
  if (shown.length) {
    return [element("div", { class: "films" }, ...shown.flatMap((member) => member.old
      ? [figure(t("before"), member.old), figure(t("after"), member.new)]
      : [figure(member.name, member.new)])),
      element("details", { class: "frames" }, element("summary", {}, t("sheet")), zoomable(laid.sheet, name))];
  }
  return [zoomable(laid.sheet, name)];
}

// One family as a card: what it is, the picture, and the decision (§PW287).
function card(sitting, name, laid, answers, assets) {
  const choices = sitting.choices || {};
  const said = answers.filter((one) => one.sitting === sitting.manifest && one.family === name);
  const last = said[said.length - 1];
  const status = !last ? ["wait", t("status_wait")]
    : last.choice === "accept" ? ["yes", t("status_accept")]
      : last.choice === "look" ? ["no", t("status_look")] : ["yes", t("status_other")];
  const box = element("article", { class: "card" + (last ? " done" : ""),
    id: cardId(sitting.manifest, name) });
  // A line is named by who says it, its key shown small under it; anything else by name.
  const speaking = (laid.members || []).find((member) => member.text);
  const title = speaking ? (speaking.who || speaking.speaker || name) : name;
  box.append(element("header", {}, element("h3", {}, title),
    element("span", { class: "badge " + status[0] }, status[1])));
  if (laid.about) box.append(element("p", { class: "about" }, laid.about));
  box.append(...visual(laid, name));

  const decide = element("div", { class: "decide" });
  const form = element("form");
  const marks = [];
  let picked = null;
  const options = element("div", { class: "options", role: "group", "aria-label": t("question") });
  const note = element("div", { class: "note" });
  const noteLabel = element("label", { for: "why-" + name });
  const why = element("textarea", { id: "why-" + name, name: "why" });
  note.append(noteLabel, why);
  const failed = (laid.said || []).some((member) => (member.failed || []).length);
  for (const [word, raw] of Object.entries(choices)) {
    if (word === "number" && !failed) continue;
    const choice = asChoice(word, raw, sitting.kind);
    const button = element("button", {
      type: "button", class: "option " + (["accept", "look"].includes(word) ? word : "other"),
      "aria-pressed": "false",
    }, element("b", {}, choice.label), element("small", {}, choice.means),
    choice.then ? element("small", {}, "→ " + choice.then) : null);
    button.addEventListener("click", () => {
      picked = word;
      for (const other of options.children) other.setAttribute("aria-pressed", String(other === button));
      note.classList.add("open");
      noteLabel.textContent = word === "accept" ? t("note_accept") : t("note_look");
      why.placeholder = word === "accept" ? t("placeholder_accept")
        : word === "look" ? t("placeholder_look") : t("placeholder_other");
      if (word !== "accept") why.focus();
    });
    options.append(button);
  }
  const send = element("button", { type: "submit", class: "primary" }, t("record"));
  const message = element("span", { class: "message", "aria-live": "polite" });
  form.append(element("p", { class: "question" }, t("question")), options, note,
    element("div", { class: "actions" }, send, message));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.classList.remove("bad");
    if (!picked) { message.textContent = t("need_choice"); message.classList.add("bad"); return; }
    // A redo needs to say what is wrong; an accept may say nothing more.
    if (picked !== "accept" && !why.value.trim()) {
      message.textContent = t("need_note"); message.classList.add("bad"); why.focus(); return;
    }
    send.disabled = true;
    message.textContent = t("recording");
    const answer = await fetch("/api/judge", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Polyweave": "1" },
      body: JSON.stringify({
        sitting: sitting.manifest, family: name, choice: picked, why: why.value.trim(),
        marks: marks.filter((mark) => mark.shapes.length),
      }),
    });
    const body = await answer.json();
    if (answer.ok) {
      message.textContent = t("recorded");
      redrawCard(sitting.manifest, name);
    } else {
      send.disabled = false;
      message.classList.add("bad");
      message.textContent = body.code + ": " + body.message + "\n" + (body.remedy || "");
    }
  });
  decide.append(form);

  if (last) {
    // Answered: say so plainly, and keep the form one click away for a second thought.
    const choice = asChoice(last.choice, choices[last.choice] || last.choice, sitting.kind);
    const done = element("div", { class: "answered" },
      element("p", {}, t("answered", { choice: choice.label, at: when(last.at) })),
      element("p", {}, element("q", {}, last.why || t("no_comment"))));
    for (const member of laid.members || []) {
      const row = assets.find((asset) => asset.asset === member.name);
      if (row && row.candidate && row.waiting) {
        done.append(element("p", { class: "facts" },
          t("newer_candidate", { name: member.name, candidate: row.candidate })));
      }
    }
    const again = element("button", { type: "button", class: "link" }, t("answer_again"));
    decide.hidden = true;
    again.addEventListener("click", () => { decide.hidden = false; again.remove(); });
    done.append(again);
    box.append(done);
  }
  box.append(decide);

  // What a person may want and should never have to wade through: marks and numbers.
  const tools = element("div", { class: "tools" });
  // Marks are drawn on a picture, so a sound or a line has none to draw on.
  const drawable = (laid.members || []).filter((member) => !member.sound && !member.text);
  for (const member of laid.members || []) if (member.sound) form.insertBefore(listen(member), form.firstChild);
  if (drawable.length) {
    const marking = element("details", {}, element("summary", {}, t("mark")));
    for (const member of drawable) {
      if (member.old) marking.append(compare(member.old, member.new, "slider", null));
      marking.append(marker(member, marks));
    }
    tools.append(marking);
  }
  const facts = element("details", {}, element("summary", {}, t("details")));
  for (const member of laid.said || []) {
    const line = element("p", { class: "facts" }, element("strong", {}, member.name + ": "),
      element("span", { class: member.passed ? "passes" : "fails" }, member.passed ? t("passes") : t("fails")));
    for (const failed of member.failed || []) line.append(element("br"), failed);
    facts.append(line);
  }
  for (const member of laid.members || []) {
    if (typeof member.measured === "string") {
      facts.append(element("p", { class: "facts" }, t("measured") + ": " + member.measured));
    }
  }
  if (sitting.legend) facts.append(legend(sitting.legend));
  tools.append(facts);
  box.append(tools);
  return box;
}

// A sitting: its title and what it is for, how to decide, then one card per family.
function sittingView(sitting, found) {
  // Each sitting is a section of its own, parted from the next, its count under its
  // title so a person knows which cards they are in and how far along (§PW295).
  const section = element("section", { class: "sitting" });
  const intro = element("div", { class: "intro" });
  const kind = kinds[sitting.kind || "look"] || {};
  const total = Object.keys(sitting.families).length;
  intro.append(element("h2", {}, sitting.title || kind.title || t("heading")),
    element("p", { class: "when" }, t(total === 1 ? "sitting_count_one" : "sitting_count", {
      total, done: answered(sitting, found.answers) }) + " · " +
      t("laid_out", { at: when(sitting.at) })));
  const about = sitting.about || kind.about;
  if (about) intro.append(element("p", {}, about));
  // What each choice means, as a legend and never as something to press (§PW295).
  const how = element("ul", { class: "how" });
  const failed = Object.values(sitting.families).some((laid) =>
    (laid.said || []).some((member) => (member.failed || []).length));
  for (const [word, raw] of Object.entries(sitting.choices || {})) {
    if (word === "number" && !failed) continue;
    const choice = asChoice(word, raw, sitting.kind);
    how.append(element("li", {}, element("strong", {}, choice.label + ": "),
      choice.means + (choice.then ? " " + choice.then : "")));
  }
  intro.append(element("p", { class: "how-title" }, t("how")), how);
  if ((sitting.tone || []).length) {
    intro.append(element("details", { class: "more", open: "" }, element("summary", {}, t("tone")),
      element("ul", { class: "examples" }, ...sitting.tone.map((rule) => element("li", {}, rule)))));
  }
  if (sitting.legend) {
    intro.append(element("details", { class: "more" }, element("summary", {}, t("legend")),
      legend(sitting.legend)));
  }
  section.append(intro);
  for (const [name, laid] of Object.entries(sitting.families)) {
    section.append(card(sitting, name, laid, found.answers, found.pending.assets));
  }
  return section;
}

const answered = (sitting, answers) => Object.keys(sitting.families)
  .filter((name) => answers.some((one) => one.sitting === sitting.manifest && one.family === name)).length;

// Two versions in one place (§PW176): side by side, a slider across one picture, an
// onion skin at an opacity the person sets, and a difference map lit only above the
// noise floor. It opens in the mode that suits what is compared; the person can switch.
function compare(oldPath, newPath, mode, maskPath) {
  const box = element("div", { class: "compare" });
  const tabs = element("div", { class: "tabs", role: "tablist" });
  const stage = element("div", { class: "stage" });
  const layered = (setter, label) => {
    const frame = element("div", { class: "layers" });
    const top = element("img", { src: file(newPath), alt: t("after") });
    frame.append(element("img", { src: file(oldPath), alt: t("before") }), top);
    if (maskPath && setter === "clip") {
      frame.append(element("img", { src: file(maskPath), alt: "", class: "mask" }));
    }
    const range = element("input", { type: "range", min: "0", max: "100", value: "50", "aria-label": label });
    const set = () => {
      if (setter === "clip") top.style.clipPath = "inset(0 " + (100 - range.value) + "% 0 0)";
      else top.style.opacity = range.value / 100;
    };
    range.addEventListener("input", set);
    set();
    return element("div", {}, frame, range);
  };
  const modes = {
    side: () => element("div", { class: "side" },
      element("img", { src: file(oldPath), alt: t("before") }),
      element("img", { src: file(newPath), alt: t("after") })),
    slider: () => layered("clip", t("mode_slider")),
    onion: () => layered("opacity", t("mode_onion")),
    difference: () => {
      const holder = element("div", {}, t("measuring_difference"));
      fetch("/api/compare?old=" + encodeURIComponent(oldPath) + "&new=" + encodeURIComponent(newPath))
        .then((answer) => answer.json())
        .then((found) => {
          holder.replaceChildren();
          if (!found.map) { holder.textContent = found.message || t("no_map"); return; }
          holder.append(element("img", { src: file(found.map), alt: t("mode_difference") }),
            element("p", { class: "says" }, t("difference_says", {
              changed: found.changed_patches, patches: found.patches,
              tolerance: found.tolerance, from: found.tolerance_from || "",
            })));
        });
      return holder;
    },
  };
  const show = (name) => {
    for (const tab of tabs.children) tab.setAttribute("aria-selected", String(tab.dataset.mode === name));
    stage.replaceChildren(modes[name]());
  };
  for (const name of Object.keys(modes)) {
    const tab = element("button", { type: "button", role: "tab" }, t("mode_" + name));
    tab.dataset.mode = name;
    tab.addEventListener("click", () => show(name));
    tabs.append(tab);
  }
  box.append(tabs, stage);
  show(modes[mode] ? mode : "side");
  return box;
}

const post = (body) => fetch("/api/judge", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-Polyweave": "1" },
  body: JSON.stringify(body),
}).then(async (answer) => ({ ok: answer.ok, body: await answer.json() }));

// A form of one sentence and one button, as the canon and the gates use.
function sentence(placeholder, label, done, send) {
  const form = element("form");
  const why = element("textarea", { placeholder, "aria-label": placeholder });
  const button = element("button", { type: "submit", class: "primary" }, label);
  const said = element("p", { class: "message", "aria-live": "polite" });
  form.append(why, element("div", { class: "actions" }, button), said);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!why.value.trim()) { said.textContent = t("write_first"); return; }
    button.disabled = true;
    const { ok, body } = await send(why.value);
    said.textContent = ok ? done : body.code + ": " + body.message;
    button.disabled = ok;
    if (ok) form.reset();
  });
  return form;
}

// The refused beside the kept (§PW175): each gate run's candidates in two lanes, every
// one with the numbers it was judged on, and a refused one can be promoted by a person.
function candidate(run, one) {
  const item = element("div", { class: "candidate" });
  item.append(element("img", { src: file(one.picture), alt: one.picture }));
  const facts = element("ul");
  facts.append(element("li", {}, one.picture + ": silhouette IoU " + one.silhouette_iou));
  for (const failed of one.failed) facts.append(element("li", { class: "fails" }, failed));
  for (const [measure, number] of Object.entries(one.drift || {})) {
    facts.append(element("li", {}, measure + " " + number.value + " / " + number.canon +
      " ± " + number.floor + (number.which_way ? ", " + number.which_way : "")));
  }
  for (const gap of one.unchecked || []) facts.append(element("li", {}, t("unchecked", { gap })));
  if (one.bought) {
    const left = one.ceiling ? t("left", { left: one.ceiling.left, unit: one.ceiling.unit }) : "";
    facts.append(element("li", {}, t("cost", { credits: one.bought.credits, service: one.bought.service }) + left));
  }
  item.append(facts);
  if (one.compare) item.append(compare(one.compare.old, one.picture, one.compare.mode, one.compare.mask));
  item.append(sentence(t("why_canon"), t("add_to_canon"), t("added"), (why) =>
    post({ gate: run.id, picture: one.picture, choice: "accept", why, canon: run.family || "default" })));
  if (!one.passed) {
    item.append(sentence(t("why_promote"), t("promote"), t("promoted"), (why) =>
      post({ gate: run.id, picture: one.picture, choice: "accept", why })));
  }
  return item;
}

function gateRun(run) {
  const box = element("article", { class: "family" });
  box.append(element("h2", {}, t("gate_of", { at: when(run.at) }) + (run.family ? " (" + run.family + ")" : "")));
  box.append(element("p", { class: "says" }, t("chosen", { chosen: run.chosen || t("none"), why: run.why })));
  const kept = run.candidates.filter((one) => one.passed);
  const refused = run.candidates.filter((one) => !one.passed);
  const keptLane = element("div", { class: "lane" }, element("h3", {}, t("kept", { n: kept.length })));
  for (const one of kept) keptLane.append(candidate(run, one));
  const refusedLane = element("details", { class: "lane" }, element("summary", {}, t("refused", { n: refused.length })));
  for (const one of refused) refusedLane.append(candidate(run, one));
  box.append(keptLane, refusedLane);
  return box;
}

// A mesh turned at the rig's own camera, never a viewer's (§PW176).
function meshes(turntables) {
  const byAsset = {};
  for (const one of turntables) (byAsset[one.asset] = byAsset[one.asset] || []).push(one);
  const section = element("section");
  for (const [asset, turned] of Object.entries(byAsset)) {
    const box = element("article", { class: "family" }, element("h2", {}, t("turned", { asset })));
    const newest = turned[turned.length - 1];
    const before = turned.length > 1 ? turned[turned.length - 2] : null;
    const pick = element("input", { type: "range", min: "0", max: String(newest.frames.length - 1),
      value: "0", "aria-label": t("which_frame") });
    const said = element("p", { class: "says" });
    const stage = element("div");
    const show = () => {
      const at = Number(pick.value);
      const frame = newest.frames[at];
      said.textContent = t("azimuth", { azimuth: frame.azimuth, elevation: newest.elevation }) +
        (before ? t("turned_against", { before: before.at, newest: newest.at }) : t("one_turntable"));
      stage.replaceChildren(before && before.frames[at]
        ? compare(before.frames[at].picture, frame.picture, "slider", null)
        : element("img", { src: file(frame.picture), alt: asset + " " + frame.azimuth + "°" }));
    };
    pick.addEventListener("input", show);
    show();
    box.append(pick, said, stage);
    if (newest.against) {
      box.append(element("h3", {}, t("front_against")), compare(newest.against, newest.front, "onion", null));
    }
    section.append(box);
  }
  return section;
}

// The canon on one board per family (§PW177), loaded when asked.
function canonBoard(one) {
  const box = element("article", { class: "family" }, element("h2", {}, t("canon_of", { family: one.family })));
  const swatches = element("div", { class: "swatches" });
  for (const colour of one.palette) {
    const chip = element("span", { class: "swatch", title: colour }, colour);
    chip.style.setProperty("--chip", colour);
    swatches.append(chip);
  }
  box.append(swatches, element("pre", {}, JSON.stringify(one.skeleton, null, 2)));
  box.append(element("p", { class: "says" }, t("floors", { floors: Object.entries(one.floors)
    .map(([k, v]) => k + " " + (v === null ? t("floor_none") : v)).join(", ") })));
  const grid = element("div", { class: "canon" });
  for (const picture of one.pictures) {
    const item = element("div", { class: "candidate" });
    item.append(element("img", { src: file(picture.path), alt: picture.picture }));
    const facts = element("ul");
    facts.append(element("li", {}, picture.picture + ": " + picture.verdict.choice + ", " +
      picture.verdict.when + ", “" + picture.verdict.why + "”"));
    const without = one.without[picture.picture] || {};
    const narrower = Object.entries(without).filter(([k, v]) => v !== null && one.floors[k] !== null
      && v < one.floors[k]).map(([k, v]) => k + " " + one.floors[k] + " → " + v);
    facts.append(element("li", {}, narrower.length ? t("narrow", { which: narrower.join(", ") }) : t("no_narrow")));
    item.append(facts, sentence(t("why_withdraw"), t("withdraw"), t("withdrawn"), (why) =>
      post({ canon: one.family, withdraw: picture.picture, why })));
    grid.append(item);
  }
  box.append(grid);
  if (one.says) box.append(element("p", { class: "says" }, one.says));
  // Pictures the project pointed at that no gate ever saw (§PW266).
  if ((one.candidates || []).length) {
    box.append(element("h3", {}, t("candidates")));
    const offered = element("div", { class: "canon" });
    for (const offer of one.candidates) {
      const item = element("div", { class: "candidate" });
      item.append(element("img", { src: file(offer.path), alt: offer.path }), element("p", {}, offer.path),
        sentence(t("why_canon"), t("add_to_canon"), t("added"), (why) =>
          post({ canon: one.family, admit: offer.path, why })));
      offered.append(item);
    }
    box.append(offered);
  }
  return box;
}

async function drawCanons() {
  const boards = document.getElementById("canons");
  boards.replaceChildren(t("measuring_canons"));
  const answer = await fetch("/api/canon", { cache: "no-store" });
  const found = await answer.json();
  boards.replaceChildren(...(Array.isArray(found) ? found.map(canonBoard)
    : [element("p", {}, found.code + ": " + found.message)]));
}

// What was last drawn, so a read that found nothing new changes nothing on the page: a
// redraw replaces every button, and one landing between a person's clicks lost the
// click (§PW289).
let drawn = "";
const seen = (found) => JSON.stringify([found.language, found.sittings, found.answers,
  found.pending, found.gates, found.turntables]);

// Progress over every sitting still open, so two sittings read as one amount of work.
function progressOf(found) {
  const open = found.sittings.filter((one) =>
    answered(one, found.answers) < Object.keys(one.families).length);
  const progress = document.getElementById("progress");
  if (!open.length) { progress.hidden = true; return; }
  const total = open.reduce((sum, one) => sum + Object.keys(one.families).length, 0);
  const done = open.reduce((sum, one) => sum + answered(one, found.answers), 0);
  progress.hidden = false;
  document.getElementById("bar").style.width = (total ? (100 * done) / total : 0) + "%";
  document.getElementById("counted").textContent = t("progress", { done, total });
}

// After an answer, only the card answered is drawn again, in its place; the rest of the
// page, and whatever the person is already doing further down it, is left alone.
async function redrawCard(manifest, name) {
  const found = await state();
  drawn = seen(found);
  const sitting = found.sittings.find((one) => one.manifest === manifest);
  const old = document.getElementById(cardId(manifest, name));
  if (sitting && old && sitting.families[name]) {
    old.replaceWith(card(sitting, name, sitting.families[name], found.answers, found.pending.assets));
  }
  progressOf(found);
}

async function draw() {
  const found = await state();
  if (seen(found) === drawn) return;
  drawn = seen(found);
  await speak(found.language || "en");
  document.getElementById("project").textContent = found.project || "";
  const sittings = document.getElementById("sittings");
  const older = document.getElementById("older");
  const newest = found.sittings.slice().reverse();
  sittings.replaceChildren();
  older.replaceChildren();
  progressOf(found);
  // Every sitting with something still to answer is in full, newest first; the ones a
  // person has finished fold under them (§PW291).
  const open = newest.filter((one) => answered(one, found.answers) < Object.keys(one.families).length);
  const done = newest.filter((one) => !open.includes(one));
  if (!open.length) sittings.append(element("p", { class: "empty" }, t("empty")));
  for (const one of open) sittings.append(sittingView(one, found));
  if (done.length) {
    const fold = element("details", { class: "older" }, element("summary", {}, t("older", { n: done.length })));
    for (const earlier of done) fold.append(sittingView(earlier, found));
    older.append(fold);
  }
  document.getElementById("meshes").replaceChildren(meshes(found.turntables || []));
  const gates = document.getElementById("gates");
  gates.replaceChildren();
  for (const run of (found.gates || []).slice().reverse()) gates.append(gateRun(run));
  const rows = document.querySelector("#pending tbody");
  rows.replaceChildren();
  for (const asset of found.pending.assets) {
    rows.append(element("tr", {},
      element("td", {}, asset.asset),
      element("td", {}, asset.waiting ? t("yes") : t("no")),
      element("td", {}, asset.candidate || ""),
      element("td", {}, asset.judged || "")));
  }
}

document.getElementById("zoom-close").addEventListener("click", () => document.getElementById("zoom").close());
document.getElementById("zoom").addEventListener("click", (event) => {
  if (event.target.id === "zoom") event.target.close();
});
draw();
// The page reads the files again every few seconds, so an answer, or the agent's next
// candidate, shows without a reload. It keeps nothing of its own between reads.
// A redraw never runs over a decision being made: a choice picked or a word typed holds it.
let marking = false;
document.addEventListener("pointerdown", (event) => { marking = event.target.tagName === "CANVAS" || marking; });
const writing = () =>
  marking || document.getElementById("zoom").open ||
  [...document.querySelectorAll("textarea")].some((box) => box.value.trim()) ||
  document.querySelector('.option[aria-pressed="true"]') !== null ||
  [...document.querySelectorAll("details")].some((one) => one.open && one.closest(".card"));
setInterval(() => { if (!writing()) draw(); }, 5000);
