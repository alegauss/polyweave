import { gains } from "../../lib/site-content";
import { SiteRich as Rich, SiteSectionHead } from "@viglet/viglet-design-system/site";
import { Icon } from "../ui/Icon";

/** What Claude Code can do with the plugin that it cannot do without it — the page's core. */
export function Gains() {
  return (
    <section id="gains" className="band">
      <div className="vg-site-wrap">
        <div className="reveal">
          <SiteSectionHead eyebrow={gains.eyebrow} title={gains.heading}>
            <Rich runs={gains.intro} />
          </SiteSectionHead>
        </div>
        <div className="tiles reveal">
          {gains.items.map((g) => (
            <div className="tile" key={g.title}>
              <div className="tile-ico">
                <Icon name={g.icon} />
              </div>
              <h3>{g.title}</h3>
              <p>{g.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
