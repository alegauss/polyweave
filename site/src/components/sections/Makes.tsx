import { makes } from "../../lib/site-content";
import { SiteRich as Rich, SiteSectionHead } from "@viglet/viglet-design-system/site";
import { Icon } from "../ui/Icon";

export function Makes() {
  return (
    <section id="makes">
      <div className="vg-site-wrap">
        <div className="reveal">
          <SiteSectionHead eyebrow={makes.eyebrow} title={makes.heading}>
            <Rich runs={makes.intro} />
          </SiteSectionHead>
        </div>
        <div className="makes reveal">
          {makes.items.map((m) => (
            <div className="make" key={m.title}>
              <div className="make-ico">
                <Icon name={m.icon} />
              </div>
              <div>
                <h3>{m.title}</h3>
                <p>{m.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
