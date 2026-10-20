import { session } from "../../lib/site-content";
import { SiteRich as Rich, SiteSectionHead } from "@viglet/viglet-design-system/site";
import { Session } from "../Session";

export function Demo() {
  return (
    <section id="demo">
      <div className="vg-site-wrap">
        <div className="reveal">
          <SiteSectionHead eyebrow={session.eyebrow} title={session.heading}>
            <Rich runs={session.intro} />
          </SiteSectionHead>
        </div>
        <div className="demo reveal">
          <Session />
          <p className="demo-more">
            <a href="/polyweave/claude-code/">{session.more} →</a>
          </p>
        </div>
      </div>
    </section>
  );
}
