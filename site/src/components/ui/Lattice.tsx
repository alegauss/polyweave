// The weave the mark is made of. The logo is three ribbons crossing inside a polygon, so
// the page it introduces closes the hero into a lattice and opens the footer out of one:
// bands of triangulated strip, drawn in the mark's own violet and its teal.
//
// Each band is two zigzags of opposite phase — one filled down to the floor, one stroked
// over it — because two crossing zigzags read as a woven lattice where a single one reads
// as a saw. The nearest band carries the vertices as nodes, which is the "poly" half of
// the name doing the same job the threads do for the other half.
//
// Seamlessness here is arithmetic, not luck. Every band is drawn twice across a 2880-unit
// viewBox laid out at 200% of the element, so 1440 units is exactly one width; the drift
// translates by 50% — one whole repeat — which means the frame after the last is the
// first. Each period below divides 1440 for the same reason: a band that does not close on
// 1440 shows a seam once per cycle, and once per cycle is every few seconds.
//
// The drift and the sway sit on two elements on purpose. Both are transforms, and two
// animations on one element are one property overwriting the other — so the outer div
// rises and falls, and the inner svg travels sideways.
//
// Decorative only: it carries no copy, so it is hidden from the accessibility tree and
// dropped from the Markdown twin, and it stops moving under prefers-reduced-motion.

const SPAN = 2880; // two identical repeats of 1440
const FLOOR = 200; // the viewBox floor the bands are filled down to

/**
 * One zigzag across the span. `phase` 0 starts at the baseline and rises; phase 1 starts
 * raised and falls, so the two cross at every quarter period and the crossings are what
 * the eye reads as a weave.
 */
function zigzag(baseline: number, amplitude: number, period: number, phase: 0 | 1): string {
  const half = period / 2;
  const hi = baseline - amplitude;
  let d = `M0 ${phase === 1 ? hi : baseline}`;
  for (let x = 0; x < SPAN; x += period) {
    d += ` L${x + half} ${phase === 1 ? baseline : hi}`;
    d += ` L${x + period} ${phase === 1 ? hi : baseline}`;
  }
  return d;
}

/** The same zigzag, closed down to the floor: the body of the band under the line. */
const body = (baseline: number, amplitude: number, period: number): string =>
  `${zigzag(baseline, amplitude, period, 0)} V${FLOOR} H0 Z`;

/** The peaks of the phase-0 zigzag, where the front band puts its vertices. */
function peaks(baseline: number, amplitude: number, period: number): { x: number; y: number }[] {
  const out = [];
  for (let x = period / 2; x < SPAN; x += period) {
    out.push({ x, y: baseline - amplitude });
  }
  return out;
}

// Back to front. Nearer bands are drawn lower, shorter and tighter, which is what reads as
// depth; the speeds that go with it are in the stylesheet, next to the colours.
//
// The periods are the second set. The first — 720, 480, 360 — divided the repeat correctly
// and still drew the wrong thing: at a 1440-wide viewport one period of 720 units is 720
// pixels of a single rise and fall, which is a swell. A weave has to show its triangles,
// so each band now carries three to eight of them across the page. All three still divide
// 1440, which is what the lint test checks and what keeps the loop seamless.
const LAYERS = [
  { key: "back", baseline: 72, amplitude: 46, period: 360 },
  { key: "mid", baseline: 104, amplitude: 32, period: 240 },
  { key: "front", baseline: 130, amplitude: 22, period: 180 },
] as const;

export function Lattice({ className }: { className?: string }) {
  return (
    <div
      className={className ? `lattice ${className}` : "lattice"}
      aria-hidden="true"
      data-twin="omit"
    >
      {LAYERS.map((layer) => (
        <div className={`lat-sway lat-${layer.key}`} key={layer.key}>
          <svg
            className="lat-drift"
            viewBox={`0 0 ${SPAN} ${FLOOR}`}
            preserveAspectRatio="none"
            focusable="false"
          >
            <path
              className="lat-body"
              d={body(layer.baseline, layer.amplitude, layer.period)}
            />
            <path
              className="lat-thread"
              d={zigzag(layer.baseline, layer.amplitude, layer.period, 1)}
            />
            {/* The nodes ride the nearest band, and are drawn in that layer's own svg so
                they cannot drift out of step with the lattice they sit on. */}
            {layer.key === "front" &&
              peaks(layer.baseline, layer.amplitude, layer.period).map((p) => (
                <circle className="lat-node" key={p.x} cx={p.x} cy={p.y} r={4} />
              ))}
          </svg>
        </div>
      ))}
    </div>
  );
}
