import { makes } from "../../lib/site-content";
import { Rich } from "../ui/Rich";
import { Icon } from "../ui/Icon";

export function Makes() {
  return (
    <section id="makes">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{makes.eyebrow}</div>
          <h2>{makes.heading}</h2>
          <p>
            <Rich runs={makes.intro} />
          </p>
        </div>
        <div className="makes reveal">
          {makes.items.map((m) => (
            <div className="make" key={m.title}>
              <div className="make-ico">
                <Icon name={m.icon} />
              </div>
              <div>
                <h3>{m.title}</h3>
                <p>{m.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
