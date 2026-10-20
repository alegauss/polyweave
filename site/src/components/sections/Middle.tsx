import { middle } from "../../lib/site-content";
import { SiteRich as Rich, SiteSectionHead } from "@viglet/viglet-design-system/site";
import { Icon } from "../ui/Icon";
import { Brand } from "../ui/Brand";

export function Middle() {
  return (
    <section id="models" className="band">
      <div className="vg-site-wrap">
        <div className="reveal">
          <SiteSectionHead eyebrow={middle.eyebrow} title={middle.heading}>
            <Rich runs={middle.intro} />
          </SiteSectionHead>
        </div>
        <div className="models reveal">
          {middle.groups.map((g) => (
            <div className="model-group" key={g.label}>
              <div className="model-label">{g.label}</div>
              <div className="model-names">
                {g.names.map((n) => (
                  <Brand className="model" name={n} key={n} />
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="trio reveal">
          {middle.points.map((p) => (
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
