import { loop } from "../../lib/site-content";
import { loopDiagram, sheetDiagram } from "../../lib/diagrams";
import { Pillar } from "./Pillar";
import { RawSvg } from "../ui/RawSvg";
import { Rich } from "../ui/Rich";

export function Loop() {
  return (
    <Pillar
      id="loop"
      eyebrow={loop.eyebrow}
      heading={loop.heading}
      lead={loop.lead}
      figure={loopDiagram}
      points={loop.points}
    >
      {/* The sheet comes after the points rather than beside the loop: it is what the loop
          returns, and a reader who has not yet been told the search reports a margin has
          no way to read a row of scores. */}
      <figure className="shot-frame reveal sheet">
        <RawSvg markup={sheetDiagram} />
        <figcaption>
          <Rich runs={loop.sheetCaption} />
        </figcaption>
      </figure>
    </Pillar>
  );
}
