import { seeing } from "../../lib/site-content";
import { rungsDiagram } from "../../lib/diagrams";
import { Pillar } from "./Pillar";
import { Rich } from "../ui/Rich";

export function Seeing() {
  return (
    <Pillar
      id="seeing"
      eyebrow={seeing.eyebrow}
      heading={seeing.heading}
      lead={seeing.lead}
      figure={rungsDiagram}
      points={seeing.points}
    >
      <div className="sub-head reveal">
        <h3>{seeing.measures.heading}</h3>
        <p>
          <Rich runs={seeing.measures.intro} />
        </p>
      </div>
      <div className="table-wrap reveal">
        <table className="matrix">
          <thead>
            <tr>
              <th>Measure</th>
              <th>Range</th>
              <th>What it is</th>
            </tr>
          </thead>
          <tbody>
            {seeing.measures.rows.map((row) => (
              <tr key={row.name}>
                <td>
                  <code>{row.name}</code>
                </td>
                <td className="num">{row.range}</td>
                <td>{row.what}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Pillar>
  );
}
