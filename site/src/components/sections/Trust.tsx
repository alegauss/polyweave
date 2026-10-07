import { nonGoals as copy, trust } from "../../lib/site-content";
import { nonGoals } from "../../lib/roadmap";
import { Rich } from "../ui/Rich";
import { Icon } from "../ui/Icon";

/**
 * The promises, then the non-goals they come from. The non-goals are read straight out of
 * the governed roadmap, never typed here; the landing shows each one's lead, and the reason
 * sits behind it for whoever opens it.
 */
export function Trust() {
  return (
    <section id="trust" className="band">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{trust.eyebrow}</div>
          <h2>{trust.heading}</h2>
        </div>
        <div className="tiles four reveal">
          {trust.items.map((t) => (
            <div className="tile" key={t.title}>
              <div className="tile-ico">
                <Icon name={t.icon} />
              </div>
              <h3>{t.title}</h3>
              <p>{t.body}</p>
            </div>
          ))}
        </div>

        <div className="sub-head reveal">
          <h3>{copy.heading}</h3>
          <p>
            <Rich runs={copy.intro} />
          </p>
        </div>
        <ul className="nevers reveal">
          {nonGoals.map((item) => (
            <li key={item.lead}>
              <details>
                <summary>
                  <em>✗</em> {item.lead}
                </summary>
                <p>{item.why}</p>
              </details>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
