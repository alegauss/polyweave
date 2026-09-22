import type { Rich as RichRuns } from "../../lib/site-content";
import { Rich } from "../ui/Rich";
import { RawSvg } from "../ui/RawSvg";

/**
 * Six of the landing sections have the same shape — an eyebrow, a heading, a lead, a
 * figure where there is one, and a list of points that each open with a bolded claim — so
 * they are one component that takes them rather than six that repeat them.
 *
 * The composition still lives in the JSX; this *is* the JSX for that shape. What the
 * content module owns is the words, and the six call sites in Landing.tsx are where the
 * order of the argument lives.
 */
export function Pillar({
  id,
  eyebrow,
  heading,
  lead,
  figure,
  figureCaption,
  points,
  children,
}: {
  id: string;
  eyebrow: string;
  heading: string;
  lead: RichRuns;
  figure?: string;
  figureCaption?: RichRuns;
  points: RichRuns[];
  children?: React.ReactNode;
}) {
  return (
    <section id={id}>
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{eyebrow}</div>
          <h2>{heading}</h2>
          <p>
            <Rich runs={lead} />
          </p>
        </div>

        {figure && (
          <figure className="shot-frame reveal">
            <RawSvg markup={figure} />
            {figureCaption && (
              <figcaption>
                <Rich runs={figureCaption} />
              </figcaption>
            )}
          </figure>
        )}

        <ul className="feat-list two reveal">
          {points.map((runs, i) => (
            <li key={i}>
              <span className="chk">◆</span>
              <span>
                <Rich runs={runs} />
              </span>
            </li>
          ))}
        </ul>

        {children}
      </div>
    </section>
  );
}
