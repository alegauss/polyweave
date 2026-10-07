import { session } from "../../lib/site-content";
import { Rich } from "../ui/Rich";
import { Session } from "../Session";

export function Demo() {
  return (
    <section id="demo">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{session.eyebrow}</div>
          <h2>{session.heading}</h2>
          <p>
            <Rich runs={session.intro} />
          </p>
        </div>
        <div className="demo reveal">
          <Session />
          <p className="demo-more">
            <a href="/polyweave/claude-code/">{session.more} →</a>
          </p>
        </div>
      </div>
    </section>
  );
}
