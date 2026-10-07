import { Nav } from "../components/Nav";
import { Footer } from "../components/Footer";
import { Hero } from "../components/sections/Hero";
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
//   hero (what it is, in one picture) → what Claude Code gains (the reason to install it)
//   → how it works → what it makes → the games made with it → see it run → the models it sits in front of
//   → the review page (where the person decides) → why it is safe → install → go deeper.
//
// Claude Code comes first because it is the operator: every section answers what it can
// now do, or what the person approving its work now sees.
export function Landing() {
  return (
    <>
      <Nav />
      <Hero />
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
