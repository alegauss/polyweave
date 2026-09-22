import { hero, navLinks, parentUrl, repoUrl, roadmapUrl } from "../lib/site-content";
import { ThemeToggle } from "./ui/ThemeToggle";

export function Nav() {
  return (
    <nav>
      <div className="wrap">
        <div className="nav-left">
          <a className="brand" href="/polyweave/">
            <img src="/polyweave/logo.svg" alt="" />
            polyweave
          </a>
          <a className="parent" href={parentUrl} title="alegauss: small developer tools">
            <span className="pre">part of</span>
            <b>alegauss</b>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M7 17 17 7" />
              <path d="M9 7h8v8" />
            </svg>
          </a>
        </div>
        <div className="nav-links">
          {navLinks.map((link) => (
            <a key={link.href} href={link.href}>
              {link.label}
            </a>
          ))}
          {/* The primary button is the roadmap, because the roadmap is what exists. A
              download button on a project with no code is the one thing this page must
              not have. */}
          <a className="btn btn-primary" href={roadmapUrl}>
            {hero.ctaShort}
          </a>
          <a className="btn btn-ghost" href={repoUrl}>
            ★ View on GitHub
          </a>
          <ThemeToggle />
        </div>
      </div>
    </nav>
  );
}
