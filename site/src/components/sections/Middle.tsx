import { middle } from "../../lib/site-content";
import { Rich } from "../ui/Rich";
import { Icon } from "../ui/Icon";
import { Brand } from "../ui/Brand";

export function Middle() {
  return (
    <section id="models" className="band">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{middle.eyebrow}</div>
          <h2>{middle.heading}</h2>
          <p>
            <Rich runs={middle.intro} />
          </p>
        </div>
        <div className="models reveal">
          {middle.groups.map((g) => (
            <div className="model-group" key={g.label}>
              <div className="model-label">{g.label}</div>
              <div className="model-names">
                {g.names.map((n) => (
                  <Brand className="model" name={n} key={n} />
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="trio reveal">
          {middle.points.map((p) => (
            <div className="tile" key={p.title}>
              <div className="tile-ico">
                <Icon name={p.icon} />
              </div>
              <h3>{p.title}</h3>
              <p>
                <Rich runs={p.body} />
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
