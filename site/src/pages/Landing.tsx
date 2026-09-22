import { Nav } from "../components/Nav";
import { Footer } from "../components/Footer";
import { Hero } from "../components/sections/Hero";
import { Stage } from "../components/sections/Stage";
import { Evidence } from "../components/sections/Evidence";
import { Friction } from "../components/sections/Friction";
import { Loop } from "../components/sections/Loop";
import { Seeing } from "../components/sections/Seeing";
import { Contract } from "../components/sections/Contract";
import { Pillar } from "../components/sections/Pillar";
import { Conventions } from "../components/sections/Conventions";
import { FeatureIndex } from "../components/sections/FeatureIndex";
import { NonGoals } from "../components/sections/NonGoals";
import { Proof } from "../components/sections/Proof";
import { Close } from "../components/sections/Close";
import { engine, geometry, motion, service } from "../lib/site-content";
import { fetchDiagram, geometryDiagram } from "../lib/diagrams";

// The landing page. The section order is the argument, not a feature list:
//
//   hero → there is no code yet → where the evidence came from → what it costs today
//   → the loop (the mechanism the whole thing exists for) → seeing cheaply (what makes
//   the loop affordable) → the call contract (what makes it usable by an agent) → the
//   four remaining blocks → the conventions → the depth pages → what this refuses →
//   the benchmark that has to ship → the plan.
//
// Two placements are deliberate. `Stage` is second, not last: a page that describes an
// unbuilt product in the present tense has to say so before it says anything else. And
// `Proof` is last before the close, because the line that measures whether any of this
// helped is the one that turns the rest of the page from a claim into a result — putting
// it near the top would read as modesty, and putting it after the argument reads as the
// condition it is.
export function Landing() {
  return (
    <>
      <Nav />
      <Hero />
      <Stage />
      <Evidence />
      <Friction />
      <Loop />
      <Seeing />
      <Contract />
      <Pillar
        id="service"
        eyebrow={service.eyebrow}
        heading={service.heading}
        lead={service.lead}
        figure={fetchDiagram}
        points={service.points}
      />
      <Pillar
        id="engine"
        eyebrow={engine.eyebrow}
        heading={engine.heading}
        lead={engine.lead}
        points={engine.points}
      />
      <Pillar
        id="motion"
        eyebrow={motion.eyebrow}
        heading={motion.heading}
        lead={motion.lead}
        points={motion.points}
      />
      <Pillar
        id="geometry"
        eyebrow={geometry.eyebrow}
        heading={geometry.heading}
        lead={geometry.lead}
        figure={geometryDiagram}
        points={geometry.points}
      />
      <Conventions />
      <FeatureIndex />
      <NonGoals />
      <Proof />
      <Close />
      <Footer />
    </>
  );
}
