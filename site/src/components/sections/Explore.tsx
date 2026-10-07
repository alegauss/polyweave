import { explore } from "../../lib/site-content";
import { features } from "../../lib/features";

/** The depth pages, one link each, for whoever wants the mechanism behind the promise. */
export function Explore() {
  return (
    <section id="explore">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{explore.eyebrow}</div>
          <h2>{explore.heading}</h2>
        </div>
        <div className="links-grid reveal">
          <a className="link-card" href="/polyweave/claude-code/">
            <b>Built for an agent</b>
            <span>The rules that let Claude Code get every call right the first time.</span>
          </a>
          {features.map((f) => (
            <a className="link-card" key={f.slug} href={`/polyweave/features/${f.slug}/`}>
              <b>{f.heading}</b>
              <span>{f.ogDescription}</span>
            </a>
          ))}
          <a className="link-card" href="/polyweave/specs/">
            <b>The specs</b>
            <span>The file formats and contracts every call obeys.</span>
          </a>
        </div>
      </div>
    </section>
  );
}
