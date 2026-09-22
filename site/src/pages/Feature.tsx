import { Nav } from "../components/Nav";
import { Footer } from "../components/Footer";
import { Rich } from "../components/ui/Rich";
import { RawSvg } from "../components/ui/RawSvg";
import type { FeatureRecord } from "../lib/features";
import { features } from "../lib/features";
import { blockTitle, Spelled, tasksIn } from "../lib/roadmap";
import { changelogUrl, roadmapUrl } from "../lib/site-content";
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
 * One depth page per roadmap block. The prose is the record; the backlog at the bottom is
 * the block's own lines, generated from the governed roadmap — so this page carries the
 * work rather than a second description of it, and a line that ships disappears from here
 * the next time the site is generated.
 */
export function FeaturePage({ record }: { record: FeatureRecord }) {
  const lines = tasksIn(record.block);
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

      <section id="lines">
        <div className="wrap">
          <div className="sec-head reveal">
            <div className="eyebrow">The block itself</div>
            <h2>
              {lines.length === 0 ? (
                <>This block is finished</>
              ) : (
                <>
                  {Spelled(lines.length)} open {lines.length === 1 ? "line" : "lines"}, in
                  the roadmap's own words
                </>
              )}
            </h2>
            <p>
              {lines.length === 0 ? (
                <>
                  Every line it held has shipped, so the roadmap no longer carries any —
                  which is why there are none below. What each one turned out to be is in{" "}
                  <a href={changelogUrl}>
                    <code>docs/CHANGELOG.md</code>
                  </a>
                  .
                </>
              ) : (
                <>
                  Each line names the failure it exists to remove and the measurement
                  behind it. None of them has shipped. This list is generated from{" "}
                  <a href={roadmapUrl}>
                    <code>docs/ROADMAP.md</code>
                  </a>
                  , so it cannot describe a backlog the file does not have.
                </>
              )}
            </p>
          </div>
          <div className="rows reveal">
            {lines.map((t) => (
              <div className="row" key={t.id}>
                <span className="mark">📋</span>
                <span className="id">{t.id}</span>
                <span className="what">
                  <b>{t.symptom}</b>
                  <span>{t.why}</span>
                  {t.deps.length > 0 && (
                    <span className="deps">waits on {t.deps.join(", ")}</span>
                  )}
                </span>
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
                <span className="block-count">{tasksIn(f.block).length} lines</span>
              </a>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
