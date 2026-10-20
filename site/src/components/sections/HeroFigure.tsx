import { hero, heroParts } from "../../lib/site-content";
import { Icon } from "../ui/Icon";
import { Lattice } from "../ui/Lattice";
import { Brand } from "../ui/Brand";

// The product's half of the landing hero (PW572): the design system's SiteHero draws the
// badge, the headline, the lead, the call to action and the meta line, and this is what it
// renders after them — the parts polyweave makes, the picture of who talks to whom, and the
// weave behind it all.
export function HeroFigure() {
  return (
    <>
      <div className="vg-site-wrap hero-figure">
        <div className="part-chips">
          {heroParts.map((p) => (
            <a className="part-chip" href="#makes" key={p.label}>
              <Icon name={p.icon} />
              {p.label}
            </a>
          ))}
        </div>
        <Hub />
      </div>
      <Lattice />
    </>
  );
}

/**
 * The product in one picture: you and Claude Code on the left, polyweave in the middle,
 * the tools on the right, and the review page underneath where the verdict comes back.
 * Drawn in HTML rather than SVG so it reflows to a column on a phone and follows the theme.
 * The sentence above it already says this, so the twin drops the figure.
 */
function Hub() {
  const { you, core, tools, review } = hero.hub;
  return (
    <div className="hub" data-twin="omit" aria-hidden="true">
      <div className="hub-node hub-you">
        <div className="hub-title">
          <Icon name="chat" /> {you.title}
        </div>
        {you.lines.map((l) => (
          <div className="hub-bubble" key={l}>
            {l}
          </div>
        ))}
      </div>

      <div className="hub-link" />

      <div className="hub-node hub-core">
        <img src="/polyweave/logo.svg" alt="" />
        <div className="hub-core-title">{core.title}</div>
        <div className="hub-verbs">
          {core.lines.map((l) => (
            <span key={l}>{l}</span>
          ))}
        </div>
      </div>

      <div className="hub-link" />

      <div className="hub-node hub-tools">
        <div className="hub-title">
          <Icon name="hand" /> Your tools and models
        </div>
        <div className="hub-tool-list">
          {tools.map((t) => (
            <Brand className="hub-tool" name={t} key={t} />
          ))}
        </div>
      </div>

      <div className="hub-down" />

      <div className="hub-node hub-review">
        <Icon name="verdict" />
        <b>{review.title}</b>
        <span>{review.line}</span>
      </div>
    </div>
  );
}
