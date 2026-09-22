import { roadmapUrl, specsUrl, stage } from "../../lib/site-content";
import { Rich } from "../ui/Rich";

/**
 * The status band, placed immediately under the hero rather than in a footnote.
 *
 * The rest of this page describes polyweave in the present tense, which is the right way
 * to write about a design that is settled enough to build against — and it is only
 * honest if the reader is told, before anything else, that none of it is built. A site
 * that lets somebody discover that on GitHub is a site making a claim it cannot support,
 * which is the exact failure the product on it exists to remove.
 */
export function Stage() {
  return (
    <section className="stage-band" id="stage">
      <div className="wrap">
        <div className="stage reveal">
          <div className="eyebrow">{stage.eyebrow}</div>
          <h2>{stage.heading}</h2>
          <p>
            <Rich runs={stage.body} />
          </p>
          <p>
            <Rich runs={stage.body2} />
          </p>
          <div className="stage-links" data-twin="omit">
            <a className="btn btn-ghost" href={roadmapUrl}>
              docs/ROADMAP.md
            </a>
            <a className="btn btn-ghost" href={specsUrl}>
              docs/specs/
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
