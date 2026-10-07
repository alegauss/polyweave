import { gains } from "../../lib/site-content";
import { Rich } from "../ui/Rich";
import { Icon } from "../ui/Icon";

/** What Claude Code can do with the plugin that it cannot do without it — the page's core. */
export function Gains() {
  return (
    <section id="gains" className="band">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{gains.eyebrow}</div>
          <h2>{gains.heading}</h2>
          <p>
            <Rich runs={gains.intro} />
          </p>
        </div>
        <div className="tiles reveal">
          {gains.items.map((g) => (
            <div className="tile" key={g.title}>
              <div className="tile-ico">
                <Icon name={g.icon} />
              </div>
              <h3>{g.title}</h3>
              <p>{g.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
