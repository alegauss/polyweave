import type { IconName } from "../../lib/site-content";

// Line icons drawn on a 24-unit grid in the current text colour, so they follow the theme
// with no palette of their own. Decorative: the title beside each one carries the meaning,
// so they are hidden from the accessibility tree and never reach a Markdown twin.
const PATHS: Record<IconName, string[]> = {
  hand: ["M18 11V6a2 2 0 0 0-4 0v1", "M14 10V4a2 2 0 0 0-4 0v2", "M10 10.5V6a2 2 0 0 0-4 0v8", "M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"],
  eye: ["M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z", "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"],
  ear: ["M6 8.5a6.5 6.5 0 1 1 13 0c0 6-6 6-6 10a3.5 3.5 0 1 1-7 0", "M15 8.5a2.5 2.5 0 0 0-5 0v1a2 2 0 1 1 0 4"],
  target: ["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z", "M12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12Z", "M12 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"],
  gamepad: ["M6 11h4", "M8 9v4", "M15 12h.01", "M18 10h.01", "M17.32 5H6.68a4 4 0 0 0-3.98 3.59l-.69 6.07A2.5 2.5 0 0 0 4.5 17.5c.9 0 1.7-.5 2.1-1.3L8 14h8l1.4 2.2c.4.8 1.2 1.3 2.1 1.3a2.5 2.5 0 0 0 2.49-2.84l-.69-6.07A4 4 0 0 0 17.32 5Z"],
  verdict: ["M9 11l3 3L22 4", "M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"],
  wrench: ["M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z"],
  memory: ["M12 8v4l3 2", "M3.05 11a9 9 0 1 1 .5 4", "M3 4v5h5"],
  book: ["M4 19.5V5a2 2 0 0 1 2-2h14v16H6.5a2.5 2.5 0 0 0 0 5H20", "M8 7h8", "M8 11h6"],
  wallet: ["M19 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2", "M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"],
  record: ["M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z", "M14 2v6h6", "M8 13h8", "M8 17h5"],
  box: ["M21 8 12 3 3 8v8l9 5 9-5Z", "M3 8l9 5 9-5", "M12 13v8"],
  cube: ["M12 2 3 7v10l9 5 9-5V7Z", "M3 7l9 5 9-5", "M12 12v10", "M7.5 4.5l9 5"],
  image: ["M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z", "M9 7a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z", "M21 15l-5-5L5 21"],
  wave: ["M2 12h2", "M6 8v8", "M10 4v16", "M14 7v10", "M18 10v4", "M22 12h-2"],
  music: ["M9 18V5l12-2v13", "M6 15a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z", "M18 13a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"],
  mic: ["M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z", "M19 10v2a7 7 0 0 1-14 0v-2", "M12 19v3"],
  text: ["M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z", "M8 9h8", "M8 13h5"],
  map: ["M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3Z", "M9 3v15", "M15 6v15"],
  motion: ["M13 4a2 2 0 1 0 0-.01", "M7 21l3-6 3 2v4", "M6 12l3-4h4l3 4 3 1", "M10 15l-1-3"],
  kit: ["M3 9h18v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z", "M8 9V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v4", "M3 14h18", "M10 14v2h4v-2"],
  laptop: ["M4 5h16v10H4Z", "M2 19h20"],
  file: ["M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z", "M14 2v6h6", "M10 13l-2 2 2 2", "M14 13l2 2-2 2"],
  shield: ["M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z", "M9 12l2 2 4-4"],
  chat: ["M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z"],
  check: ["M20 6 9 17l-5-5"],
  spark: ["M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.4Z", "M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8Z", "M5 3l.6 1.4L7 5l-1.4.6L5 7l-.6-1.4L3 5l1.4-.6Z"],
};

export function Icon({ name, className }: { name: IconName; className?: string }) {
  return (
    <svg
      className={className ? `icon ${className}` : "icon"}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name].map((d) => (
        <path d={d} key={d} />
      ))}
    </svg>
  );
}
