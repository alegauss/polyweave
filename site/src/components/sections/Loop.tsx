import { useEffect, useRef } from "react";
import { loop } from "../../lib/site-content";
import { SiteRich as Rich, SiteSectionHead } from "@viglet/viglet-design-system/site";

/**
 * One real part going from refused to accepted, right under the hero (§PW663): the
 * promise is visual, and prose had never shown it. The poster is the loop's last frame,
 * so a reader who never plays it still sees all three attempts, and the caption says
 * them in words.
 */
export function Loop() {
  const video = useRef<HTMLVideoElement>(null);
  // A reader who asked for less motion sees the poster, which holds all three attempts.
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      video.current?.pause();
    }
  }, []);
  return (
    <section id="loop">
      <div className="vg-site-wrap">
        <div className="reveal">
          <SiteSectionHead eyebrow={loop.eyebrow} title={loop.heading}>
            <Rich runs={loop.intro} />
          </SiteSectionHead>
        </div>
        <figure className="loop reveal">
          <video
            ref={video}
            src={loop.video}
            poster={loop.poster}
            autoPlay
            loop
            muted
            playsInline
            preload="none"
            width={1280}
            height={720}
            aria-label={loop.caption}
          />
          <figcaption>{loop.caption}</figcaption>
        </figure>
      </div>
    </section>
  );
}
