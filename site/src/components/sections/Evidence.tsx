import { evidence } from "../../lib/site-content";
import { Rich } from "../ui/Rich";

export function Evidence() {
  return (
    <section id="evidence">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{evidence.eyebrow}</div>
          <h2>{evidence.heading}</h2>
          <p>
            <Rich runs={evidence.body} />
          </p>
        </div>
        <div className="stats reveal">
          {evidence.stats.map((s) => (
            <div className="stat" key={s.label}>
              <div className="stat-value">{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
