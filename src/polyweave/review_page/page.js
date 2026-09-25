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
      body: JSON.stringify({ sitting, family: name, choice, why: why.value }),
    });
    const body = await answer.json();
    said.textContent = answer.ok
      ? "Recorded: " + body.choice + ". " + (body.ledger || "")
      : body.code + ": " + body.message + "\n" + (body.remedy || "");
    send.disabled = answer.ok;
    if (answer.ok) form.reset();  // said once; the next read shows it under the family
  });
  box.append(history(sitting, name, laid, answers, assets), form);
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
const writing = () =>
  [...document.querySelectorAll("textarea")].some((box) => box.value.trim()) ||
  document.querySelector("input[type=radio]:checked") !== null;
setInterval(() => { if (!writing()) draw(); }, 5000);
