import { Nav } from "../components/Nav";
import { Footer } from "../components/Footer";
import { Rich } from "../components/ui/Rich";
import { RawSvg } from "../components/ui/RawSvg";
import type { FeatureRecord } from "../lib/features";
import { features } from "../lib/features";
import { blockTitle } from "../lib/roadmap";
import {
  fetchDiagram,
  geometryDiagram,
  loopDiagram,
  rungsDiagram,
  sheetDiagram,
} from "../lib/diagrams";

const FIGURES: Record<NonNullable<FeatureRecord["figure"]>, string> = {
  loop: loopDiagram,
  rungs: rungsDiagram,
  sheet: sheetDiagram,
  fetch: fetchDiagram,
  geometry: geometryDiagram,
};

/**
 * One depth page per roadmap block: the prose is the record, the figure the mechanism, and
 * the cards at the bottom the blocks it sits next to. The title is read from the roadmap,
 * so a page cannot outlive the block it describes.
 */
export function FeaturePage({ record }: { record: FeatureRecord }) {
  const others = features.filter((f) => f.slug !== record.slug);

  return (
    <>
      <Nav />
      <header className="page-head">
        <div className="wrap">
          <div className="eyebrow">
            {record.eyebrow} · {blockTitle(record.block)}
          </div>
          <h1>{record.heading}</h1>
          <p className="sub">
            <Rich runs={record.lead} />
          </p>
        </div>
      </header>

      <section>
        <div className="wrap">
          {record.figure && (
            <figure className="shot-frame reveal">
              <RawSvg markup={FIGURES[record.figure]} />
            </figure>
          )}

          <div className="prose reveal">
            {record.sections.map((s) => (
              <div className="prose-block" key={s.heading}>
                <h2>{s.heading}</h2>
                {s.body && (
                  <p>
                    <Rich runs={s.body} />
                  </p>
                )}
                {s.list && (
                  <ul className="feat-list">
                    {s.list.map((runs, i) => (
                      <li key={i}>
                        <span className="chk">◆</span>
                        <span>
                          <Rich runs={runs} />
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="more">
        <div className="wrap">
          <div className="sec-head reveal">
            <div className="eyebrow">The other blocks</div>
            <h2>What this one sits next to</h2>
          </div>
          <div className="grid reveal">
            {others.map((f) => (
              <a className="card block-card" key={f.slug} href={`/polyweave/features/${f.slug}/`}>
                <div className="block-letter">{f.block}</div>
                <h3>{f.heading}</h3>
                <p>{f.description}</p>
              </a>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
