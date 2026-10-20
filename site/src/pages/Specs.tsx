import { Footer, Nav } from "../components/Chrome";
import { SiteCopyButton, SiteRich as Rich } from "@viglet/viglet-design-system/site";
import { specs, specsUrl } from "../lib/site-content";

export function Specs() {
  return (
    <>
      <Nav />
      <header className="page-head">
        <div className="vg-site-wrap">
          <div className="eyebrow">{specs.eyebrow}</div>
          <h1>{specs.heading}</h1>
          <p className="sub">
            <Rich runs={specs.lead} />
          </p>
          <p className="status-line">
            <Rich runs={specs.status} />
          </p>
        </div>
      </header>

      <section>
        <div className="vg-site-wrap">
          <div className="table-wrap reveal">
            <table className="matrix">
              <thead>
                <tr>
                  <th>Spec</th>
                  <th>What it fixes</th>
                  <th>Lines it binds</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {specs.table.map((row) => (
                  <tr key={row.name}>
                    <td>
                      <code>{row.name}</code>
                    </td>
                    <td>{row.fixes}</td>
                    <td className="num">{row.binds}</td>
                    <td className={row.written ? "state-yes" : "state-no"}>
                      {row.written ? "written" : "to come"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="table-note">
            The four written ones live in{" "}
            <a href={specsUrl}>
              <code>docs/specs/</code>
            </a>
            . They are ordinary documents — nothing governs them, and they are edited
            directly, unlike the roadmap.
          </p>
        </div>
      </section>

      <section>
        <div className="vg-site-wrap">
          <div className="prose reveal">
            <div className="prose-block">
              <h2>{specs.formats.heading}</h2>
              <p>
                <Rich runs={specs.formats.body} />
              </p>
            </div>
            <div className="prose-block">
              <h2>{specs.sample.heading}</h2>
              <p>
                <Rich runs={specs.sample.body} />
              </p>
            </div>
          </div>

          <div className="codeblock file reveal">
            <div className="file-bar">
              <span>mascot.accept.toml</span>
              <SiteCopyButton
                text={specs.sample.code}
                label="Copy the acceptance spec"
                copyLabel="Copy"
                copiedLabel="Copied!"
              />
            </div>
            <pre>
              <code>{specs.sample.code}</code>
            </pre>
          </div>

          <div className="prose reveal">
            <div className="prose-block">
              <h2>{specs.cannot.heading}</h2>
              <p>
                <Rich runs={specs.cannot.body} />
              </p>
            </div>
            <div className="prose-block">
              <h2>{specs.notYet.heading}</h2>
              <ul className="feat-list">
                {specs.notYet.list.map((runs, i) => (
                  <li key={i}>
                    <span className="chk">◆</span>
                    <span>
                      <Rich runs={runs} />
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
