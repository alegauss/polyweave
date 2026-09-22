import { close, repoUrl, roadkeepUrl, roadmapUrl } from "../../lib/site-content";
import { Rich } from "../ui/Rich";

export function Close() {
  return (
    <section id="plan">
      <div className="wrap">
        <div className="banner reveal">
          <div className="eyebrow">{close.eyebrow}</div>
          <h2>{close.heading}</h2>
          <p>
            <Rich runs={close.body} />
          </p>
          <div className="hero-cta" data-twin="omit">
            <a className="btn btn-primary" href={roadmapUrl}>
              {close.ctaPrimary}
            </a>
            <a className="btn btn-ghost" href={repoUrl}>
              {close.ctaGhost}
            </a>
          </div>
          <p className="banner-note">
            <Rich runs={close.noteLead} />
            <a href={roadkeepUrl}>
              <b>{close.noteLink}</b>
            </a>
            <Rich runs={close.noteTail} />
          </p>
        </div>
      </div>
    </section>
  );
}
