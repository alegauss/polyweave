import { showcase } from "../../lib/site-content";
import { Rich } from "../ui/Rich";

/**
 * The games made with polyweave, each its logo and a link to its own site. The link sits
 * on the name, so the twin reads a heading and a URL rather than one run-on line; CSS
 * stretches it over the card so the whole card is still the target.
 */
export function Showcase() {
  return (
    <section id="showcase">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{showcase.eyebrow}</div>
          <h2>{showcase.heading}</h2>
          <p>
            <Rich runs={showcase.intro} />
          </p>
        </div>
        <div className="games reveal">
          {showcase.games.map((g) => (
            <div className="game" key={g.name}>
              {/* A fixed dark stage in both themes: both logos are drawn for a dark ground. */}
              <div className="game-stage">
                <img src={g.logo} alt={`${g.name} logo`} loading="lazy" decoding="async" />
              </div>
              <div className="game-body">
                <p className="game-kind">{g.kind}</p>
                <h3>
                  <a href={g.url} target="_blank" rel="noopener">
                    {g.name}
                  </a>
                </h3>
                <p>{g.body}</p>
                <p className="game-link">{g.site} ↗</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
