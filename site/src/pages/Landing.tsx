import { SiteButton, SiteHero, SiteRich } from "@viglet/viglet-design-system/site";
import { Footer, Nav } from "../components/Chrome";
import { HeroFigure } from "../components/sections/HeroFigure";
import { Icon } from "../components/ui/Icon";
import { hero, repoUrl } from "../lib/site-content";
import { Different } from "../components/sections/Different";
import { Gains } from "../components/sections/Gains";
import { Steps } from "../components/sections/Steps";
import { Makes } from "../components/sections/Makes";
import { Showcase } from "../components/sections/Showcase";
import { Demo } from "../components/sections/Demo";
import { Middle } from "../components/sections/Middle";
import { Review } from "../components/sections/Review";
import { Trust } from "../components/sections/Trust";
import { Install } from "../components/sections/Install";
import { Explore } from "../components/sections/Explore";

// The landing page, and the section order is the pitch:
//
//   hero (what it is, in one picture) → where it sits (what the other tools leave to you)
//   → what Claude Code gains (the reason to install it) → how it works → what it makes → the games made with it → see it run → the models it sits in front of
//   → the review page (where the person decides) → why it is safe → install → go deeper.
//
// Claude Code comes first because it is the operator: every section answers what it can
// now do, or what the person approving its work now sees.
export function Landing() {
  return (
    <>
      <Nav />
      <SiteHero
        badge={hero.badge}
        title={hero.titleLead}
        titleAccent={hero.titleAccent}
        sub={<SiteRich runs={hero.sub} />}
        actions={
          <>
            <SiteButton href="#install">{hero.cta}</SiteButton>
            <SiteButton variant="ghost" href={repoUrl}>
              ★ View on GitHub
            </SiteButton>
          </>
        }
        meta={hero.meta.map((item) => (
          <>
            <Icon name="check" /> {item}
          </>
        ))}
      >
        <HeroFigure />
      </SiteHero>
      <Different />
      <Gains />
      <Steps />
      <Makes />
      <Showcase />
      <Demo />
      <Middle />
      <Review />
      <Trust />
      <Install />
      <Explore />
      <Footer />
    </>
  );
}
