// The illustrative SVGs. These are figures — a mechanism drawn, and terminal output kept
// as it prints — so they hold their own fixed dark palette rather than following the page
// theme; the themed .shot-frame around them is what places them on a light or dark page.
// Kept as verbatim markup (not converted to JSX) so the drawing stays pixel-identical to
// the hand-written original, and rendered with dangerouslySetInnerHTML because it is
// static, author-controlled content with no interpolation.
//
// Every number that appears inside one of these figures is either a measurement the
// roadmap records against Cottony or a name from docs/specs/. Nothing here is a benchmark
// of polyweave, because there is nothing yet to benchmark, and a figure that implied
// otherwise would be the exact failure the product exists to remove.

export const loopDiagram = `
<svg viewBox="0 0 900 310" role="img" aria-label="An acceptance spec feeds a search; the search proposes parameters, bakes at a preview rung, measures the render and scores the margin, looping; what comes back is the winning parameters, a contact sheet and a trace of every sample. A cache keyed on the inputs and the renderer version means a state already rendered is never rendered twice.">
  <rect width="900" height="310" rx="12" fill="#0c0a18"/>

  <text x="30" y="32" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5" font-weight="700" letter-spacing="1.4">WHAT YOU DECLARE</text>
  <rect x="24" y="48" width="188" height="150" rx="10" fill="#181433" stroke="#2f2760"/>
  <text x="40" y="74" fill="#a996ff" font-family="JetBrains Mono,monospace" font-size="12.5">mascot.accept.toml</text>
  <line x1="40" y1="86" x2="196" y2="86" stroke="#2f2760"/>
  <text x="40" y="108" fill="#ece9fb" font-family="JetBrains Mono,monospace" font-size="11">silhouette_iou</text>
  <text x="40" y="124" fill="#21c1a6" font-family="JetBrains Mono,monospace" font-size="11">  min = 0.97</text>
  <text x="40" y="146" fill="#ece9fb" font-family="JetBrains Mono,monospace" font-size="11">delta_e</text>
  <text x="40" y="162" fill="#21c1a6" font-family="JetBrains Mono,monospace" font-size="11">  max = 2.0</text>
  <text x="40" y="184" fill="#9b93c4" font-family="JetBrains Mono,monospace" font-size="11">[search.light] 0.5-4.0</text>

  <path d="M218 123 H262" stroke="#a996ff" stroke-width="1.6" fill="none" marker-end="url(#pw-arrow)"/>

  <defs>
    <marker id="pw-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="#a996ff"/>
    </marker>
    <marker id="pw-arrow-dim" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="#6f679a"/>
    </marker>
  </defs>

  <rect x="268" y="48" width="336" height="150" rx="12" fill="#120f26" stroke="#7a5af8" stroke-width="1.5"/>
  <text x="436" y="70" text-anchor="middle" fill="#a996ff" font-family="Inter,sans-serif" font-size="12" font-weight="700" letter-spacing="1.2">THE SEARCH</text>

  <rect x="288" y="84" width="128" height="40" rx="8" fill="#211b44" stroke="#2f2760"/>
  <text x="352" y="108" text-anchor="middle" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">propose values</text>
  <rect x="456" y="84" width="128" height="40" rx="8" fill="#211b44" stroke="#2f2760"/>
  <text x="520" y="103" text-anchor="middle" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">bake</text>
  <text x="520" y="117" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="10.5">at the cheapest rung</text>
  <rect x="456" y="140" width="128" height="40" rx="8" fill="#211b44" stroke="#2f2760"/>
  <text x="520" y="164" text-anchor="middle" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">measure</text>
  <rect x="288" y="140" width="128" height="40" rx="8" fill="#211b44" stroke="#2f2760"/>
  <text x="352" y="159" text-anchor="middle" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">score the margin</text>
  <text x="352" y="173" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="10.5">per predicate, 0 to 1</text>

  <path d="M420 104 H452" stroke="#a996ff" stroke-width="1.5" fill="none" marker-end="url(#pw-arrow)"/>
  <path d="M520 128 V136" stroke="#a996ff" stroke-width="1.5" fill="none" marker-end="url(#pw-arrow)"/>
  <path d="M452 160 H420" stroke="#a996ff" stroke-width="1.5" fill="none" marker-end="url(#pw-arrow)"/>
  <path d="M352 136 V128" stroke="#a996ff" stroke-width="1.5" fill="none" marker-end="url(#pw-arrow)"/>

  <path d="M610 123 H654" stroke="#a996ff" stroke-width="1.6" fill="none" marker-end="url(#pw-arrow)"/>

  <text x="660" y="32" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5" font-weight="700" letter-spacing="1.4">WHAT COMES BACK</text>
  <rect x="660" y="48" width="216" height="150" rx="10" fill="#181433" stroke="#2f2760"/>
  <circle cx="678" cy="76" r="4" fill="#21c1a6"/>
  <text x="692" y="80" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">the winning values</text>
  <circle cx="678" cy="106" r="4" fill="#21c1a6"/>
  <text x="692" y="110" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">a contact sheet</text>
  <text x="692" y="124" fill="#9b93c4" font-family="Inter,sans-serif" font-size="10.5">the best handful, side by side</text>
  <circle cx="678" cy="150" r="4" fill="#21c1a6"/>
  <text x="692" y="154" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">a trace</text>
  <text x="692" y="168" fill="#9b93c4" font-family="Inter,sans-serif" font-size="10.5">every sample it rejected,</text>
  <text x="692" y="182" fill="#9b93c4" font-family="Inter,sans-serif" font-size="10.5">and the predicate that rejected it</text>

  <rect x="24" y="222" width="852" height="62" rx="10" fill="#141127" stroke="#2f2760" stroke-dasharray="5 4"/>
  <text x="44" y="248" fill="#e0a33c" font-family="JetBrains Mono,monospace" font-size="11.5">cache key</text>
  <text x="44" y="268" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5">the inputs, the renderer and its version, the seed — a sweep revisits neighbourhoods, and a state already rendered is not paid for twice.</text>
  <path d="M436 218 V204" stroke="#6f679a" stroke-width="1.4" fill="none" marker-end="url(#pw-arrow-dim)"/>
</svg>`;

export const rungsDiagram = `
<svg viewBox="0 0 900 250" role="img" aria-label="Three preview rungs: a sphere answers whether the surface reads, a preview mesh answers whether the silhouette lands, and the final bake is the only rung a verdict may be taken at. Every measurement reports the rung it came from.">
  <rect width="900" height="250" rx="12" fill="#0c0a18"/>

  <rect x="24" y="30" width="268" height="152" rx="10" fill="#181433" stroke="#2f2760"/>
  <circle cx="86" cy="94" r="34" fill="#2b2455"/>
  <circle cx="76" cy="84" r="12" fill="#5c4bb0" opacity="0.9"/>
  <text x="136" y="72" fill="#a996ff" font-family="JetBrains Mono,monospace" font-size="12.5">rung: sphere</text>
  <text x="136" y="94" fill="#21c1a6" font-family="JetBrains Mono,monospace" font-size="17" font-weight="600">3 s</text>
  <text x="44" y="152" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">Does the surface read?</text>
  <text x="44" y="170" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">Roughness, glaze, colour. No mesh needed.</text>

  <rect x="316" y="30" width="268" height="152" rx="10" fill="#181433" stroke="#2f2760"/>
  <path d="M352 122 L378 62 L412 100 L440 70 L446 122 Z" fill="#2b2455" stroke="#5c4bb0" stroke-width="1.4"/>
  <text x="472" y="72" fill="#a996ff" font-family="JetBrains Mono,monospace" font-size="12.5">rung: preview</text>
  <text x="472" y="94" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5">low samples, real mesh</text>
  <text x="336" y="152" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">Does the silhouette land?</text>
  <text x="336" y="170" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">Mass, proportion, where the shape sits.</text>

  <rect x="608" y="30" width="268" height="152" rx="10" fill="#181433" stroke="#7a5af8" stroke-width="1.5"/>
  <path d="M644 122 L670 62 L704 100 L732 70 L738 122 Z" fill="#3b3170" stroke="#a996ff" stroke-width="1.4"/>
  <path d="M652 122 L676 78 L700 108" fill="none" stroke="#e0a33c" stroke-width="1.2" opacity="0.7"/>
  <text x="764" y="72" fill="#a996ff" font-family="JetBrains Mono,monospace" font-size="12.5">rung: final</text>
  <text x="764" y="94" fill="#e0a33c" font-family="JetBrains Mono,monospace" font-size="17" font-weight="600">2 min</text>
  <text x="628" y="152" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">The verdict rung.</text>
  <text x="628" y="170" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">What a spec may be accepted at, and nothing below.</text>

  <text x="450" y="216" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5">The rung comes back with every measurement, reported and never inferred, so a verdict taken on a sphere is never mistaken for one</text>
  <text x="450" y="232" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5">taken on the final mesh. The three seconds and the two minutes are Cottony's, measured before any of this existed.</text>
</svg>`;

export const sheetDiagram = `
<svg viewBox="0 0 900 290" role="img" aria-label="A contact sheet of five candidate renders with their scores: the winner at 0.94, and four rejected samples each labelled with the predicate that rejected it.">
  <rect width="900" height="290" rx="12" fill="#0c0a18"/>
  <text x="30" y="34" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5" font-weight="700" letter-spacing="1.4">THE BEST FIVE, SIDE BY SIDE</text>

  <rect x="24" y="52" width="156" height="150" rx="10" fill="#181433" stroke="#21c1a6" stroke-width="1.8"/>
  <rect x="38" y="66" width="128" height="86" rx="6" fill="#4a3f8f"/>
  <circle cx="102" cy="112" r="28" fill="#cbb79a"/>
  <text x="46" y="176" fill="#21c1a6" font-family="JetBrains Mono,monospace" font-size="14" font-weight="600">0.94</text>
  <text x="96" y="176" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">kept</text>
  <text x="46" y="192" fill="#9b93c4" font-family="JetBrains Mono,monospace" font-size="10">light 2.8 · form 1.9</text>

  <rect x="196" y="52" width="156" height="150" rx="10" fill="#181433" stroke="#2f2760"/>
  <rect x="210" y="66" width="128" height="86" rx="6" fill="#4a3f8f"/>
  <circle cx="274" cy="112" r="28" fill="#e6dccb"/>
  <text x="218" y="176" fill="#9b93c4" font-family="JetBrains Mono,monospace" font-size="14">0.71</text>
  <text x="218" y="192" fill="#f2607a" font-family="JetBrains Mono,monospace" font-size="10">delta_e 4.6 &gt; 2.0</text>

  <rect x="368" y="52" width="156" height="150" rx="10" fill="#181433" stroke="#2f2760"/>
  <rect x="382" y="66" width="128" height="86" rx="6" fill="#4a3f8f"/>
  <ellipse cx="446" cy="116" rx="18" ry="30" fill="#cbb79a"/>
  <text x="390" y="176" fill="#9b93c4" font-family="JetBrains Mono,monospace" font-size="14">0.63</text>
  <text x="390" y="192" fill="#f2607a" font-family="JetBrains Mono,monospace" font-size="10">silhouette_iou 0.88</text>

  <rect x="540" y="52" width="156" height="150" rx="10" fill="#181433" stroke="#2f2760"/>
  <rect x="554" y="66" width="128" height="86" rx="6" fill="#2c2555"/>
  <circle cx="618" cy="112" r="28" fill="#8e7f68"/>
  <text x="562" y="176" fill="#9b93c4" font-family="JetBrains Mono,monospace" font-size="14">0.52</text>
  <text x="562" y="192" fill="#f2607a" font-family="JetBrains Mono,monospace" font-size="10">saturation_p99 0.61</text>

  <rect x="712" y="52" width="156" height="150" rx="10" fill="#181433" stroke="#2f2760"/>
  <rect x="726" y="66" width="128" height="86" rx="6" fill="#6a5cb8"/>
  <circle cx="790" cy="112" r="28" fill="#d8c6ad"/>
  <text x="734" y="176" fill="#9b93c4" font-family="JetBrains Mono,monospace" font-size="14">0.49</text>
  <text x="734" y="192" fill="#f2607a" font-family="JetBrains Mono,monospace" font-size="10">delta_e 7.1 &gt; 2.0</text>

  <line x1="24" y1="226" x2="876" y2="226" stroke="#2f2760"/>
  <text x="30" y="252" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5">A search that reports only its winner cannot be overruled. If the one a person would have chosen is not the one that scored highest,</text>
  <text x="30" y="270" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5">the spec is what is wrong — and finding that out is the fastest thing this loop does.</text>
</svg>`;

export const fetchDiagram = `
<svg viewBox="0 0 900 300" role="img" aria-label="A paid fetch: the request is checked against the reference silhouette before any credit is spent, a refusal costs nothing, the ceiling in polyweave.toml is what authorises the spend rather than a question per fetch, and what comes back is copied locally with its sha256 and a provenance sidecar because the service deletes the asset after seventy-two hours.">
  <rect width="900" height="300" rx="12" fill="#0c0a18"/>
  <defs>
    <marker id="pw-arrow-2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="#a996ff"/>
    </marker>
    <marker id="pw-arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="#f2607a"/>
    </marker>
  </defs>

  <rect x="24" y="52" width="156" height="92" rx="10" fill="#181433" stroke="#2f2760"/>
  <text x="102" y="82" text-anchor="middle" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12.5">the request</text>
  <text x="102" y="104" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">a prompt, and the</text>
  <text x="102" y="120" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">drawing it must match</text>

  <path d="M186 98 H228" stroke="#a996ff" stroke-width="1.6" fill="none" marker-end="url(#pw-arrow-2)"/>

  <rect x="234" y="40" width="186" height="116" rx="10" fill="#120f26" stroke="#e0a33c" stroke-width="1.5"/>
  <text x="327" y="66" text-anchor="middle" fill="#e0a33c" font-family="Inter,sans-serif" font-size="12" font-weight="700" letter-spacing="1">THE GATE</text>
  <text x="327" y="90" text-anchor="middle" fill="#ece9fb" font-family="JetBrains Mono,monospace" font-size="11.5">silhouette_iou</text>
  <text x="327" y="108" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">against the reference,</text>
  <text x="327" y="124" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">before a credit moves</text>
  <text x="327" y="144" text-anchor="middle" fill="#21c1a6" font-family="Inter,sans-serif" font-size="11" font-weight="600">a refusal costs nothing</text>

  <path d="M327 162 V206" stroke="#f2607a" stroke-width="1.5" fill="none" marker-end="url(#pw-arrow-red)"/>
  <rect x="234" y="212" width="186" height="52" rx="10" fill="#1d1226" stroke="#f2607a"/>
  <text x="327" y="234" text-anchor="middle" fill="#f2607a" font-family="JetBrains Mono,monospace" font-size="11.5">fetch.silhouette-mismatch</text>
  <text x="327" y="252" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">a tall dome for a wide low cap</text>

  <path d="M426 98 H468" stroke="#a996ff" stroke-width="1.6" fill="none" marker-end="url(#pw-arrow-2)"/>

  <rect x="474" y="40" width="168" height="116" rx="10" fill="#181433" stroke="#2f2760"/>
  <text x="558" y="66" text-anchor="middle" fill="#a996ff" font-family="JetBrains Mono,monospace" font-size="11.5">[budget]</text>
  <text x="558" y="90" text-anchor="middle" fill="#ece9fb" font-family="Inter,sans-serif" font-size="12">a ceiling, agreed once</text>
  <text x="558" y="112" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">not a question per fetch,</text>
  <text x="558" y="128" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">and never the agent's call</text>
  <text x="558" y="148" text-anchor="middle" fill="#e0a33c" font-family="JetBrains Mono,monospace" font-size="11">spent 18 / 200</text>

  <path d="M648 98 H690" stroke="#a996ff" stroke-width="1.6" fill="none" marker-end="url(#pw-arrow-2)"/>

  <rect x="696" y="40" width="180" height="116" rx="10" fill="#181433" stroke="#21c1a6" stroke-width="1.4"/>
  <text x="786" y="66" text-anchor="middle" fill="#21c1a6" font-family="Inter,sans-serif" font-size="12" font-weight="700" letter-spacing="1">KEPT</text>
  <text x="786" y="90" text-anchor="middle" fill="#ece9fb" font-family="Inter,sans-serif" font-size="11.5">the mesh, on your disk</text>
  <text x="786" y="110" text-anchor="middle" fill="#9b93c4" font-family="JetBrains Mono,monospace" font-size="10.5">sha256 · prompt · seed</text>
  <text x="786" y="126" text-anchor="middle" fill="#9b93c4" font-family="JetBrains Mono,monospace" font-size="10.5">service · version · cost</text>
  <text x="786" y="146" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">the receipt and the thing</text>

  <line x1="450" y1="280" x2="876" y2="280" stroke="#2f2760" stroke-dasharray="4 4"/>
  <text x="663" y="212" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5">The service deletes what it made seventy-two hours later.</text>
  <text x="663" y="230" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5">One Cottony run recorded the settings it proved and not the mesh,</text>
  <text x="663" y="248" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5">so the receipt outlived the thing that was bought.</text>
</svg>`;

export const geometryDiagram = `
<svg viewBox="0 0 900 260" role="img" aria-label="A shape as a TOML declaration on the left, the built mesh on the right, and between them the two things a declaration gives that a script does not: numbers a search can reach, and a review before anything is built.">
  <rect width="900" height="260" rx="12" fill="#0c0a18"/>

  <rect x="24" y="30" width="330" height="200" rx="10" fill="#181433" stroke="#2f2760"/>
  <text x="44" y="56" fill="#a996ff" font-family="JetBrains Mono,monospace" font-size="12">tray.geom.toml</text>
  <line x1="44" y1="68" x2="334" y2="68" stroke="#2f2760"/>
  <text x="44" y="92" fill="#9b93c4" font-family="JetBrains Mono,monospace" font-size="11">[[part]]</text>
  <text x="44" y="110" fill="#ece9fb" font-family="JetBrains Mono,monospace" font-size="11">op      = "extrude_outline"</text>
  <text x="44" y="128" fill="#ece9fb" font-family="JetBrains Mono,monospace" font-size="11">outline = "rounded_rect"</text>
  <text x="44" y="146" fill="#ece9fb" font-family="JetBrains Mono,monospace" font-size="11">radius  = 0.06</text>
  <text x="44" y="164" fill="#ece9fb" font-family="JetBrains Mono,monospace" font-size="11">height  = 0.018</text>
  <text x="44" y="188" fill="#9b93c4" font-family="JetBrains Mono,monospace" font-size="11">[[part]]</text>
  <text x="44" y="206" fill="#ece9fb" font-family="JetBrains Mono,monospace" font-size="11">op    = "radial_array"</text>
  <text x="44" y="224" fill="#ece9fb" font-family="JetBrains Mono,monospace" font-size="11">count = 6</text>

  <path d="M368 130 H424" stroke="#a996ff" stroke-width="1.6" fill="none" marker-end="url(#pw-arrow-g)"/>
  <defs>
    <marker id="pw-arrow-g" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="#a996ff"/>
    </marker>
  </defs>

  <rect x="430" y="30" width="232" height="200" rx="10" fill="#120f26" stroke="#2f2760"/>
  <text x="546" y="56" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11.5" font-weight="700" letter-spacing="1.2">BUILT</text>
  <ellipse cx="546" cy="150" rx="88" ry="42" fill="#2b2455" stroke="#5c4bb0"/>
  <ellipse cx="546" cy="138" rx="88" ry="42" fill="#3b3170" stroke="#a996ff"/>
  <g fill="#0c0a18" opacity="0.55">
    <ellipse cx="546" cy="116" rx="16" ry="8"/>
    <ellipse cx="596" cy="134" rx="16" ry="8"/>
    <ellipse cx="596" cy="160" rx="16" ry="8"/>
    <ellipse cx="546" cy="176" rx="16" ry="8"/>
    <ellipse cx="496" cy="160" rx="16" ry="8"/>
    <ellipse cx="496" cy="134" rx="16" ry="8"/>
  </g>
  <text x="546" y="214" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">six seats, one radial array</text>

  <rect x="678" y="30" width="198" height="94" rx="10" fill="#181433" stroke="#21c1a6" stroke-width="1.3"/>
  <text x="777" y="56" text-anchor="middle" fill="#21c1a6" font-family="Inter,sans-serif" font-size="12" font-weight="600">reachable by the search</text>
  <text x="777" y="80" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">radius and height are numbers</text>
  <text x="777" y="96" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">in a file, not constants inside</text>
  <text x="777" y="112" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">a module nothing can reach</text>

  <rect x="678" y="136" width="198" height="94" rx="10" fill="#181433" stroke="#e0a33c" stroke-width="1.3"/>
  <text x="777" y="162" text-anchor="middle" fill="#e0a33c" font-family="Inter,sans-serif" font-size="12" font-weight="600">reviewable before it is built</text>
  <text x="777" y="186" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">two wrong constructions of one</text>
  <text x="777" y="202" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">tray each looked reasonable</text>
  <text x="777" y="218" text-anchor="middle" fill="#9b93c4" font-family="Inter,sans-serif" font-size="11">while being written</text>
</svg>`;

// The session transcript — a formatted figure like the SVGs, kept verbatim so the column
// alignment and the per-line colours render exactly as written. Rendered inside a .term
// <pre>. Every command is the surface docs/specs/tool-surface.md fixes; the values are
// illustrative, and the two costs in it are Cottony's own.
export const sessionTerminal = `<span class="c"># the agent has a drawing and a name, and no numbers at all</span>

<span class="pr">&gt;</span> polyweave accept mascot --from docs/design/art/ui/mascot.png
  <span class="ok">wrote</span> assets/mascot.accept.toml    3 predicates, 2 parameters to search

<span class="pr">&gt;</span> polyweave search mascot
  <span class="hl">job</span> j_7f3a  stage=queued
  <span class="hl">job</span> j_7f3a  stage=rendering  rung=sphere   18/64  elapsed_s=54
  <span class="hl">job</span> j_7f3a  stage=rendering  rung=preview  61/64  elapsed_s=212
  <span class="ok">done</span>  score 0.94   light=2.8  form=1.9
        sheet  .polyweave/sheets/mascot-7f3a.png   <span class="c">(5 candidates)</span>
        trace  .polyweave/traces/mascot-7f3a.json  <span class="c">(64 samples, 41 cached)</span>

<span class="pr">&gt;</span> polyweave bake mascot --rung final
  <span class="ok">done</span>  1024x1024  saturation_p99=0.87  delta_e=1.4  silhouette_iou=0.981
        <span class="ok">accept: 3/3 predicates pass</span>   rung=final

<span class="pr">&gt;</span> polyweave bake shelf --rung final
  <span class="fail">post.render-uniform</span>  the render is a single colour, so nothing was lit
  <span class="rem">-&gt; the model 'shelf' carries no material. Set \`material\` on it, or pass
     \`glaze: {roughness: 0.22}\` to apply the default.</span>`;

// The conventions, as the fixed strip they are. Not a figure — the section renders these
// as a grid — but they live beside the drawings because they are the same kind of thing:
// a decision taken once so nothing downstream has to guess.
export const conventions = [
  { name: "Axes", value: "Y up, −Z forward, right-handed", note: "the engine's convention, because the engine draws the result" },
  { name: "Scale", value: "one unit is one metre", note: "unless the asset declares pixels_per_unit" },
  { name: "Origin", value: "centre of the footprint, on the ground", note: "the base of the silhouette, not the middle of the box" },
  { name: "Colour", value: "sRGB, everywhere a caller can see", note: "linear values live inside a renderer and never in an interface" },
  { name: "Angles", value: "degrees in authored documents", note: "radians nowhere a caller can see" },
  { name: "State", value: ".polyweave/, inside the project", note: "a cache in a home directory is state a colleague cannot reproduce" },
];
