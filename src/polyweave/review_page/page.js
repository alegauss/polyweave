// The page reads what is on disk and has one write, verdict.judge (§PW172).
"use strict";

const element = (tag, attributes = {}, ...children) => {
  const made = document.createElement(tag);
  for (const [key, value] of Object.entries(attributes)) made.setAttribute(key, value);
  for (const child of children) made.append(child);
  return made;
};

async function state() {
  const answer = await fetch("/api/state", { cache: "no-store" });
  return answer.json();
}

// What was said of this family on the page, and what came of it since (§PW173): an
// answer followed by a newer candidate for a member shows the two together.
function history(sitting, name, laid, answers, assets) {
  const said = answers.filter((one) => one.sitting === sitting && one.family === name);
  const block = element("div", { class: "answer" });
  for (const one of said) {
    block.append(element("p", {}, "Answered " + one.choice + " at " + one.at + ": " + one.why));
  }
  if (said.length) {
    for (const member of laid.members || []) {
      const row = assets.find((asset) => asset.asset === member.name);
      if (row && row.candidate && row.waiting) {
        block.append(element("p", {}, member.name + " has a newer candidate since: " + row.candidate));
      }
    }
  }
  return block;
}

// Where it is wrong, drawn over the member's own picture (§PW174). A drag draws a box,
// in the picture's own pixels, whatever size it is shown at; the server turns the boxes
// into a mask the picture's size and keeps it with the answer.
function marker(member, marks) {
  const shapes = [];
  marks.push({ member: member.name, shapes });
  const holder = element("div", { class: "mark" });
  const picture = element("img", {
    src: "/file?path=" + encodeURIComponent(member.new),
    alt: member.name + ", to mark where it is wrong",
  });
  const canvas = element("canvas", { "aria-label": "drag to mark where " + member.name + " is wrong" });
  const clear = element("button", { type: "button" }, "Clear marks");
  const frame = element("div", { class: "frame" }, picture, canvas);
  holder.append(element("p", {}, "Mark " + member.name + " (optional)"), frame, clear);
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
  canvas.addEventListener("pointermove", (event) => {
    if (start) paint([...start, ...at(event)]);
  });
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

function family(sitting, name, laid, choices, answers, assets) {
  const box = element("article", { class: "family" }, element("h2", {}, name));
  box.append(element("img", {
    src: "/file?path=" + encodeURIComponent(laid.sheet),
    alt: "the " + name + " family laid out to be judged",
  }));
  for (const member of laid.said || []) {
    const line = element("p", { class: "member" });
    line.append(element("strong", {}, member.name + ": "));
    line.append(element("span", { class: member.passed ? "passes" : "fails" },
      member.passed ? "passes" : "fails"));
    for (const failed of member.failed || []) line.append(element("br"), failed);
    box.append(line);
  }
  const form = element("form");
  const marks = [];
  for (const member of laid.members || []) {
    if (member.old) form.append(compare(member.old, member.new, "slider", null));
    form.append(marker(member, marks));
  }
  const options = element("div", { class: "choices", role: "radiogroup" });
  for (const [word, meaning] of Object.entries(choices)) {
    const input = element("input", { type: "radio", name: "choice", value: word });
    options.append(element("label", { title: meaning }, input, word + ": " + meaning));
  }
  const why = element("textarea", {
    name: "why", placeholder: "Your own sentence: what you saw.", "aria-label": "why",
  });
  const send = element("button", { type: "submit" }, "Record this verdict");
  const said = element("p", { class: "answer", "aria-live": "polite" });
  form.append(options, why, send, said);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const choice = new FormData(form).get("choice");
    if (!choice || !why.value.trim()) {
      said.textContent = "Pick one choice and write a sentence first.";
      return;
    }
    send.disabled = true;
    const answer = await fetch("/api/judge", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Polyweave": "1" },
      body: JSON.stringify({
        sitting, family: name, choice, why: why.value,
        marks: marks.filter((mark) => mark.shapes.length),
      }),
    });
    const body = await answer.json();
    said.textContent = answer.ok
      ? "Recorded: " + body.choice + ". " + (body.ledger || "")
      : body.code + ": " + body.message + "\n" + (body.remedy || "");
    send.disabled = answer.ok;
    if (answer.ok) {  // said once; the next read shows it under the family
      form.reset();
      for (const mark of marks) mark.shapes.length = 0;
    }
  });
  box.append(history(sitting, name, laid, answers, assets), form);
  return box;
}

// Two versions in one place (§PW176): side by side, a slider across one picture, an
// onion skin at an opacity the person sets, and a difference map lit only above the
// noise floor. It opens in the mode that suits what is compared; the person can switch.
const file = (path) => "/file?path=" + encodeURIComponent(path);

function compare(oldPath, newPath, mode, maskPath) {
  const box = element("div", { class: "compare" });
  const tabs = element("div", { class: "tabs", role: "tablist" });
  const stage = element("div", { class: "stage" });
  const modes = {
    side: () => {
      const both = element("div", { class: "side" });
      both.append(element("img", { src: file(oldPath), alt: "before: " + oldPath }),
        element("img", { src: file(newPath), alt: "after: " + newPath }));
      return both;
    },
    slider: () => {
      const frame = element("div", { class: "layers" });
      const top = element("img", { src: file(newPath), alt: "after, over before" });
      frame.append(element("img", { src: file(oldPath), alt: "before" }), top);
      if (maskPath) {
        frame.append(element("img", { src: file(maskPath), alt: "the edit's mask", class: "mask" }));
      }
      const range = element("input", { type: "range", min: "0", max: "100", value: "50",
        "aria-label": "how much of the new picture shows" });
      const set = () => { top.style.clipPath = "inset(0 " + (100 - range.value) + "% 0 0)"; };
      range.addEventListener("input", set);
      set();
      const holder = element("div");
      holder.append(frame, range);
      return holder;
    },
    onion: () => {
      const frame = element("div", { class: "layers" });
      const top = element("img", { src: file(newPath), alt: "after, over before" });
      frame.append(element("img", { src: file(oldPath), alt: "before" }), top);
      const range = element("input", { type: "range", min: "0", max: "100", value: "50",
        "aria-label": "the new picture's opacity" });
      const set = () => { top.style.opacity = range.value / 100; };
      range.addEventListener("input", set);
      set();
      const holder = element("div");
      holder.append(frame, range);
      return holder;
    },
    difference: () => {
      const holder = element("div", {}, "Measuring the difference.");
      fetch("/api/compare?old=" + encodeURIComponent(oldPath) + "&new=" + encodeURIComponent(newPath))
        .then((answer) => answer.json())
        .then((found) => {
          holder.replaceChildren();
          if (!found.map) { holder.textContent = found.message || "No map could be made."; return; }
          holder.append(element("img", { src: file(found.map), alt: "where the two differ above noise" }),
            element("p", { class: "says" }, found.changed_patches + " of " + found.patches +
              " patches past a floor of " + found.tolerance + " (" + (found.tolerance_from || "") + ")"));
        });
      return holder;
    },
  };
  const show = (name) => {
    for (const tab of tabs.children) tab.setAttribute("aria-selected", String(tab.dataset.mode === name));
    stage.replaceChildren(modes[name]());
  };
  for (const name of Object.keys(modes)) {
    const tab = element("button", { type: "button", role: "tab" }, name);
    tab.dataset.mode = name;
    tab.addEventListener("click", () => show(name));
    tabs.append(tab);
  }
  box.append(tabs, stage);
  show(modes[mode] ? mode : "side");
  return box;
}

// The refused beside the kept (§PW175): each gate run's candidates in two lanes, every
// one with the numbers it was judged on, and a refused one can be promoted by a person.
function candidate(run, one) {
  const card = element("div", { class: "candidate" });
  card.append(element("img", {
    src: "/file?path=" + encodeURIComponent(one.picture), alt: one.picture,
  }));
  const facts = element("ul");
  facts.append(element("li", {}, one.picture + ": silhouette IoU " + one.silhouette_iou));
  for (const failed of one.failed) facts.append(element("li", { class: "fails" }, failed));
  for (const [measure, number] of Object.entries(one.drift || {})) {
    facts.append(element("li", {}, measure + " " + number.value + " against " +
      number.canon + " ± " + number.floor + (number.which_way ? ", " + number.which_way : "")));
  }
  for (const gap of one.unchecked || []) facts.append(element("li", {}, "unchecked: " + gap));
  if (one.bought) {
    const left = one.ceiling ? ", " + one.ceiling.left + " " + one.ceiling.unit + " left" : "";
    facts.append(element("li", {}, "cost " + one.bought.credits + " on " + one.bought.service + left));
  }
  card.append(facts);
  if (one.compare) card.append(compare(one.compare.old, one.picture, one.compare.mode, one.compare.mask));
  if (!one.passed) {
    const form = element("form");
    const why = element("textarea", {
      placeholder: "Why this one is right after all.", "aria-label": "why",
    });
    const send = element("button", { type: "submit" }, "Promote: the bar was wrong for this one");
    const said = element("p", { class: "answer", "aria-live": "polite" });
    form.append(why, send, said);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!why.value.trim()) { said.textContent = "Write a sentence first."; return; }
      send.disabled = true;
      const answer = await fetch("/api/judge", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Polyweave": "1" },
        body: JSON.stringify({ gate: run.id, picture: one.picture, choice: "accept", why: why.value }),
      });
      const body = await answer.json();
      said.textContent = answer.ok ? "Recorded: promoted." : body.code + ": " + body.message;
      if (answer.ok) form.reset();
    });
    card.append(form);
  }
  return card;
}

function gateRun(run) {
  const box = element("article", { class: "family" });
  box.append(element("h2", {}, "Gate of " + run.at + (run.family ? " (" + run.family + ")" : "")));
  box.append(element("p", { class: "says" }, "chosen: " + (run.chosen || "none") + " — " + run.why));
  const kept = run.candidates.filter((one) => one.passed);
  const refused = run.candidates.filter((one) => !one.passed);
  const keptLane = element("div", { class: "lane" }, element("h3", {}, "Kept (" + kept.length + ")"));
  for (const one of kept) keptLane.append(candidate(run, one));
  const refusedLane = element("details", { class: "lane" },
    element("summary", {}, "Refused (" + refused.length + ")"));
  for (const one of refused) refusedLane.append(candidate(run, one));
  box.append(keptLane, refusedLane);
  return box;
}

async function draw() {
  const found = await state();
  document.getElementById("says").textContent = found.pending.says;
  const sittings = document.getElementById("sittings");
  sittings.replaceChildren();
  for (const sitting of found.sittings.slice().reverse()) {
    sittings.append(element("h2", {}, "Sitting of " + sitting.at));
    for (const [name, laid] of Object.entries(sitting.families)) {
      sittings.append(family(
        sitting.manifest, name, laid, sitting.choices, found.answers, found.pending.assets));
    }
  }
  const gates = document.getElementById("gates");
  gates.replaceChildren();
  for (const run of (found.gates || []).slice().reverse()) gates.append(gateRun(run));
  const rows = document.querySelector("#pending tbody");
  rows.replaceChildren();
  for (const asset of found.pending.assets) {
    rows.append(element("tr", {},
      element("td", {}, asset.asset),
      element("td", {}, asset.waiting ? "yes" : "no"),
      element("td", {}, asset.candidate || ""),
      element("td", {}, asset.judged || "")));
  }
}

draw();
// The page reads the files again every few seconds, so an answer, or the agent's next
// candidate, shows without a reload. It keeps nothing of its own between reads.
// A redraw never runs over an answer being written: anything typed or chosen holds it.
let marking = false;
document.addEventListener("pointerdown", (event) => { marking = event.target.tagName === "CANVAS" || marking; });
const writing = () =>
  marking ||
  [...document.querySelectorAll("textarea")].some((box) => box.value.trim()) ||
  document.querySelector("input[type=radio]:checked") !== null;
setInterval(() => { if (!writing()) draw(); }, 5000);
