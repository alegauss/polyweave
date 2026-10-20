import {
  SiteButton,
  SiteFooter,
  SiteNav,
  SiteSponsor,
  SiteThemeToggle,
} from "@viglet/viglet-design-system/site";
import { footer, hero, navLinks, parentUrl, repoUrl, sponsor, THEME_KEY } from "../lib/site-content";
import { ConsentSettings } from "./Consent";
import { Lattice } from "./ui/Lattice";

// The chrome every route shares, drawn by the design system's site layer (PW572). What is
// left here is this product's half of it: which links, which words, and the weave the footer
// stands on.

const brand = { href: "/polyweave/", name: "polyweave", logo: "/polyweave/logo.svg" };

const themeLabel = (next: string) => `Switch to ${next} theme`;

export function Nav() {
  return (
    <SiteNav
      brand={brand}
      parent={{ href: parentUrl, name: "alegauss", pre: "part of", title: "alegauss: small developer tools" }}
      links={navLinks}
      actions={
        <>
          {/* The primary button is the install, from every route. */}
          <SiteButton href="/polyweave/#install">{hero.ctaShort}</SiteButton>
          <SiteButton variant="ghost" href={repoUrl}>
            ★ View on GitHub
          </SiteButton>
          <SiteThemeToggle storageKey={THEME_KEY} label={themeLabel} />
        </>
      }
    />
  );
}

export function Footer() {
  return (
    <SiteFooter
      brand={brand}
      links={footer.links}
      sponsor={
        <SiteSponsor
          declaration={sponsor}
          moreLabel="More at"
          note="Both Apache 2.0 and self-hostable."
        />
      }
      disclaimer={
        <>
          {footer.disclaimer} <ConsentSettings />
        </>
      }
    >
      <Lattice className="lattice--footer" />
    </SiteFooter>
  );
}
