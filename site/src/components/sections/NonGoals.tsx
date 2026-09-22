import { nonGoals as copy } from "../../lib/site-content";
import { nonGoals } from "../../lib/roadmap";
import { Rich } from "../ui/Rich";

/**
 * The five non-goals, and their reasons, straight out of the governed roadmap. Nothing
 * here is typed into the site: this list binds a proposal before it becomes a line, and a
 * copy of it that had drifted would be worse than no copy at all.
 */
export function NonGoals() {
  return (
    <section id="non-goals">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{copy.eyebrow}</div>
          <h2>{copy.heading}</h2>
          <p>
            <Rich runs={copy.intro} />
          </p>
        </div>
        <div className="nots reveal">
          {nonGoals.map((item) => (
            <div className="not" key={item.lead}>
              <h4>
                <em>✗</em> {item.lead}
              </h4>
              <p>{item.why}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
