import { different } from "../../lib/site-content";
import { SiteRich as Rich, SiteSectionHead } from "@viglet/viglet-design-system/site";
import { Icon } from "../ui/Icon";

/**
 * Where polyweave sits among the tools a reader already knows: each kind of tool, what it
 * gives and what it leaves to you, with polyweave's own row last and held to the same two
 * columns. The pillars under it are the three things no other row has.
 */
export function Different() {
  const { columns, rows, ours } = different;
  return (
    <section id="different" className="band">
      <div className="vg-site-wrap">
        <div className="reveal">
          <SiteSectionHead eyebrow={different.eyebrow} title={different.heading}>
            <Rich runs={different.intro} />
          </SiteSectionHead>
        </div>
        <div className="table-wrap reveal">
          <table className="matrix compare">
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.kind}>
                  <td>{r.kind}</td>
                  <td data-label={columns[1]}>{r.gives}</td>
                  <td data-label={columns[2]}>{r.leaves}</td>
                </tr>
              ))}
              <tr className="ours">
                <td>
                  <span className="ours-name">
                    <img src="/polyweave/logo.svg" alt="" /> {ours.kind}
                  </span>
                </td>
                <td data-label={columns[1]}>{ours.gives}</td>
                <td data-label={columns[2]}>{ours.leaves}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="trio reveal">
          {different.pillars.map((p) => (
            <div className="tile" key={p.title}>
              <div className="tile-ico">
                <Icon name={p.icon} />
              </div>
              <h3>{p.title}</h3>
              <p>
                <Rich runs={p.body} />
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
