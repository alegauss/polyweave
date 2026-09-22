import { proof } from "../../lib/site-content";
import { tasksIn } from "../../lib/roadmap";
import { Rich } from "../ui/Rich";

/**
 * Block H, and the two lines in it, quoted from the roadmap. It closes the argument rather
 * than opening it: everything above is a design, and this is the line that decides whether
 * the design was worth anything.
 */
export function Proof() {
  return (
    <section id="proof">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{proof.eyebrow}</div>
          <h2>{proof.heading}</h2>
          <p>
            <Rich runs={proof.body} />
          </p>
          <p>
            <Rich runs={proof.body2} />
          </p>
        </div>
        <div className="rows reveal">
          {tasksIn("H").map((t) => (
            <div className="row" key={t.id}>
              <span className="mark">📋</span>
              <span className="id">{t.id}</span>
              <span className="what">
                <b>{t.symptom}</b>
                <span>{t.why}</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
