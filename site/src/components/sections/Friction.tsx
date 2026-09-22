import { friction } from "../../lib/site-content";
import { Rich } from "../ui/Rich";

export function Friction() {
  return (
    <section id="why">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{friction.eyebrow}</div>
          <h2>{friction.heading}</h2>
          <p>
            <Rich runs={friction.intro} />
          </p>
        </div>
        <div className="grid reveal">
          {friction.cards.map((card) => (
            <div className="card" key={card.title}>
              <div className="ico">{card.ico}</div>
              <h3>{card.title}</h3>
              <p>
                <Rich runs={card.body} />
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
