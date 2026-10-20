import { steps } from "../../lib/site-content";
import { SiteRich as Rich, SiteSectionHead } from "@viglet/viglet-design-system/site";

export function Steps() {
  return (
    <section id="how">
      <div className="vg-site-wrap">
        <div className="reveal">
          <SiteSectionHead eyebrow={steps.eyebrow} title={steps.heading} />
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
