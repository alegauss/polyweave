import { steps } from "../../lib/site-content";
import { Rich } from "../ui/Rich";

export function Steps() {
  return (
    <section id="how">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{steps.eyebrow}</div>
          <h2>{steps.heading}</h2>
        </div>
        <ol className="steps reveal">
          {steps.items.map((s) => (
            <li className="step" key={s.n}>
              <span className="step-n" aria-hidden="true">
                {s.n}
              </span>
              <h3>{s.title}</h3>
              <p>
                <Rich runs={s.body} />
              </p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
