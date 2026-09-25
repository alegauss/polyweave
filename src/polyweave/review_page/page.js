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

function family(sitting, name, laid, choices) {
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
  });
  box.append(form);
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
      sittings.append(family(sitting.manifest, name, laid, sitting.choices));
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
