import { hero, heroParts, repoUrl } from "../../lib/site-content";
import { Rich } from "../ui/Rich";
import { Icon } from "../ui/Icon";
import { Lattice } from "../ui/Lattice";
import { Brand } from "../ui/Brand";

export function Hero() {
  return (
    <header className="hero" id="top">
      <div className="wrap">
        <div className="badge">
          <img src="/polyweave/logo.svg" alt="" className="badge-mark" /> {hero.badge}
        </div>
        <h1>
          {hero.titleLead}
          <br />
          <span className="grad">{hero.titleAccent}</span>
        </h1>
        <p className="sub">
          <Rich runs={hero.sub} />
        </p>

        <div className="part-chips">
          {heroParts.map((p) => (
            <a className="part-chip" href="#makes" key={p.label}>
              <Icon name={p.icon} />
              {p.label}
            </a>
          ))}
        </div>

        {/* The call to action is dropped from the Markdown twin by this attribute — it
            converts a reader and costs an agent the same words on every page. */}
        <div className="hero-cta" data-twin="omit">
          <a className="btn btn-primary btn-lg" href="#install">
            {hero.cta}
          </a>
          <a className="btn btn-ghost btn-lg" href={repoUrl}>
            ★ View on GitHub
          </a>
        </div>

        <Hub />

        <div className="hero-meta">
          {hero.meta.map((item) => (
            <span key={item}>
              <Icon name="check" /> {item}
            </span>
          ))}
        </div>
      </div>
      <Lattice />
    </header>
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
