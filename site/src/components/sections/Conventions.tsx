import { conventions } from "../../lib/site-content";
import { conventions as rows } from "../../lib/diagrams";
import { Rich } from "../ui/Rich";

export function Conventions() {
  return (
    <section id="conventions">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{conventions.eyebrow}</div>
          <h2>{conventions.heading}</h2>
          <p>
            <Rich runs={conventions.intro} />
          </p>
        </div>
        <div className="convs reveal">
          {rows.map((row) => (
            <div className="conv" key={row.name}>
              <div className="conv-name">{row.name}</div>
              <div className="conv-value">{row.value}</div>
              <p>{row.note}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
