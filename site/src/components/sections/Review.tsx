import { review } from "../../lib/site-content";
import { Rich } from "../ui/Rich";
import { Icon } from "../ui/Icon";

export function Review() {
  return (
    <section id="review">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{review.eyebrow}</div>
          <h2>{review.heading}</h2>
          <p>
            <Rich runs={review.intro} />
          </p>
        </div>
        <div className="review-split reveal">
          <ReviewMock />
          <ul className="ticks">
            {review.points.map((runs, i) => (
              <li key={i}>
                <Icon name="check" />
                <span>
                  <Rich runs={runs} />
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

/** A drawing of the review page: three candidates, their checks, and the three answers. */
function ReviewMock() {
  const m = review.mock;
  return (
    <div className="mock" data-twin="omit" aria-hidden="true">
      <div className="mock-bar">
        <i />
        <i />
        <i />
        <span>{m.window}</span>
      </div>
      <div className="mock-grid">
        {m.candidates.map((c, i) => {
          const pass = c.checks.every(([, , ok]) => ok);
          return (
            <div className={`cand${i === 0 ? " picked" : ""}${pass ? "" : " miss"}`} key={c.label}>
              <Critter hue={c.hue} />
              <div className="cand-label">{c.label}</div>
              {c.checks.map(([name, value, ok]) => (
                <div className={`chip ${ok ? "ok" : "no"}`} key={name}>
                  {ok ? "✓" : "✗"} {name} <b>{value}</b>
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <div className="mock-actions">
        <span className="act act-yes">{m.approve}</span>
        <span className="act">{m.reject}</span>
        <span className="act act-change">{m.change}</span>
      </div>
      <div className="mock-ask">
        <span className="ask-bubble">{m.ask}</span>
        <span className="ask-status">
          <i /> {m.status}
        </span>
      </div>
    </div>
  );
}

/** A little round mascot, tinted per candidate — the thing being judged. */
function Critter({ hue }: { hue: number }) {
  const body = `hsl(${hue} 70% 82%)`;
  const shade = `hsl(${hue} 55% 66%)`;
  return (
    <svg viewBox="0 0 100 90" className="critter">
      <ellipse cx="50" cy="84" rx="28" ry="4" fill="rgba(0,0,0,0.18)" />
      <circle cx="30" cy="26" r="12" fill={shade} />
      <circle cx="70" cy="26" r="12" fill={shade} />
      <ellipse cx="50" cy="52" rx="34" ry="30" fill={body} />
      <circle cx="39" cy="50" r="4" fill="#1b1533" />
      <circle cx="61" cy="50" r="4" fill="#1b1533" />
      <path d="M44 62 Q50 67 56 62" stroke="#1b1533" strokeWidth="2.5" fill="none" strokeLinecap="round" />
    </svg>
  );
}
