import { session } from "../lib/site-content";
import { sessionTerminal } from "../lib/diagrams";
import { Rich } from "./ui/Rich";

/**
 * The transcript. A dark island in both themes, like every other figure here, and static:
 * there is no autoplay, because the thing being shown is four calls and their answers, not
 * a performance of them. The markdown twin picks this up as a fenced block, which is the
 * form an agent reading the twin actually wants.
 */
export function Session() {
  return (
    <>
      <div className="session-eyebrow">{session.eyebrow}</div>
      <div className="term session-term">
        <div className="bar">
          <i />
          <i />
          <i />
          <span>a Claude Code session</span>
        </div>
        <pre dangerouslySetInnerHTML={{ __html: sessionTerminal }} />
      </div>
      <p className="session-note">
        <Rich runs={session.note} />
      </p>
    </>
  );
}
