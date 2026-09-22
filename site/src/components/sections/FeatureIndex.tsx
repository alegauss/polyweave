import { featureIndex } from "../../lib/site-content";
import { features } from "../../lib/features";
import { tasksIn } from "../../lib/roadmap";
import { Rich } from "../ui/Rich";

export function FeatureIndex() {
  return (
    <section id="blocks">
      <div className="wrap">
        <div className="sec-head reveal">
          <div className="eyebrow">{featureIndex.eyebrow}</div>
          <h2>{featureIndex.heading}</h2>
          <p>
            <Rich runs={featureIndex.intro} />
          </p>
        </div>
        <div className="grid reveal">
          {features.map((f) => (
            <a className="card block-card" key={f.slug} href={`/polyweave/features/${f.slug}/`}>
              <div className="block-letter">{f.block}</div>
              <h3>{f.heading}</h3>
              <p>{f.description}</p>
              <span className="block-count">{tasksIn(f.block).length} lines</span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
