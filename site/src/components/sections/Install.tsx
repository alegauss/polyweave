import { install } from "../../lib/site-content";
import { SiteCopyButton, SiteRich as Rich } from "@viglet/viglet-design-system/site";

export function Install() {
  return (
    <section id="install">
      <div className="vg-site-wrap">
        <div className="banner reveal">
          <div className="eyebrow">{install.eyebrow}</div>
          <h2>{install.heading}</h2>
          <p>
            <Rich runs={install.intro} />
          </p>
          {/* The <pre> carries the class itself: the twin parser keeps a <pre>'s content as
              raw text, so a block found by its inner <code> would never be found at all. */}
          <div className="install-code">
            <SiteCopyButton
              text={install.commands}
              label="Copy the install commands"
              copyLabel="Copy"
              copiedLabel="Copied!"
            />
            <pre className="codeblock">
              <code>{install.commands}</code>
            </pre>
          </div>
          <div className="try">
            <span className="try-label">{install.tryHeading}</span>
            <span className="try-prompt">
              <code>&gt;</code> {install.prompt}
            </span>
          </div>
          <p className="banner-note">
            <Rich runs={install.needs} />
          </p>
        </div>
      </div>
    </section>
  );
}
