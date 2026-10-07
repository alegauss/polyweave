import { brandMarks } from "../../lib/brands";
import { Icon } from "./Icon";

/**
 * A tool's mark beside its name. The name stays as text, so the twin and a screen reader
 * read "Blender" and the mark is decoration; a tool with no mark of its own (sfxr) gets the
 * generic sound icon rather than an invented logo.
 */
export function Brand({ name, className }: { name: string; className?: string }) {
  const mark = brandMarks[name];
  return (
    <span className={className}>
      {mark ? (
        <svg
          className="brand-mark"
          viewBox={mark.viewBox}
          fill="currentColor"
          fillRule={mark.evenOdd ? "evenodd" : undefined}
          style={mark.color ? { color: mark.color } : undefined}
          aria-hidden="true"
          focusable="false"
          dangerouslySetInnerHTML={{ __html: mark.markup }}
        />
      ) : (
        <Icon name="wave" className="brand-mark" />
      )}
      {name}
    </span>
  );
}
