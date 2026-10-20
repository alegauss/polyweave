import { Footer, Nav } from "../components/Chrome";
import { Session } from "../components/Session";
import { SiteRich as Rich, SiteSectionHead } from "@viglet/viglet-design-system/site";
import { claudeCode, nonGoals as nonGoalCopy } from "../lib/site-content";
import { nonGoals } from "../lib/roadmap";

export function ClaudeCode() {
  return (
    <>
      <Nav />
      <header className="page-head">
        <div className="vg-site-wrap">
          <div className="eyebrow">{claudeCode.eyebrow}</div>
          <h1>{claudeCode.heading}</h1>
          <p className="sub">
            <Rich runs={claudeCode.lead} />
          </p>
        </div>
      </header>

      <section>
        <div className="vg-site-wrap">
          <Session />
        </div>
      </section>

      <section>
        <div className="vg-site-wrap">
          <div className="prose reveal">
            {claudeCode.sections.map((s) => (
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

      <section id="non-goals">
        <div className="vg-site-wrap">
          <div className="reveal">
            <SiteSectionHead eyebrow={nonGoalCopy.eyebrow} title={nonGoalCopy.heading}>
              <Rich runs={nonGoalCopy.intro} />
            </SiteSectionHead>
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

      <Footer />
    </>
  );
}
