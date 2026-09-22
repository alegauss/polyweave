import { contract } from "../../lib/site-content";
import { Rich } from "../ui/Rich";

export function Contract() {
  return (
    <section id="contract">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{contract.eyebrow}</div>
          <h2>{contract.heading}</h2>
          <p>
            <Rich runs={contract.lead} />
          </p>
        </div>

        <ul className="feat-list two reveal">
          {contract.points.map((runs, i) => (
            <li key={i}>
              <span className="chk">◆</span>
              <span>
                <Rich runs={runs} />
              </span>
            </li>
          ))}
        </ul>

        {/* The table beside its own argument, because the two are the same height; the
            error sample below at full width, because those JSON lines are long and a
            half-column would wrap `remedy` into something nobody would copy. Putting both
            in one two-column row left half a screen of nothing under the shorter one. */}
        <div className="split post-split reveal">
          <div className="split-txt">
            <h3>{contract.post.heading}</h3>
            <p>
              <Rich runs={contract.post.intro} />
            </p>
          </div>
          <div className="table-wrap">
            <table className="matrix">
              <thead>
                <tr>
                  <th>Produces</th>
                  <th>Asserted before it returns</th>
                </tr>
              </thead>
              <tbody>
                {contract.post.rows.map((row) => (
                  <tr key={row.produces}>
                    <td>{row.produces}</td>
                    <td>{row.asserted}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="error-block reveal">
          <div className="split-txt">
            <h3>{contract.error.heading}</h3>
            <p>
              <Rich runs={contract.error.intro} />
            </p>
          </div>
          <pre className="codeblock">
            <code>{contract.error.sample}</code>
          </pre>
          <p className="after">
            <Rich runs={contract.error.after} />
          </p>
        </div>
      </div>
    </section>
  );
}
