import { ArrowRight } from "lucide-react";
import Link from "next/link";

const About = () => {
  return (
    <div>
      <section className="border-b border-foreground">
        <div className="container py-12 md:py-20">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-7">
              <span className="font-mono text-xs uppercase tracking-widest text-accent font-semibold">
                ● About
              </span>
              <h2 className="font-serif text-4xl sm:text-5xl lg:text-7xl font-black tracking-tighter leading-[0.9] mt-3 mb-6">
                Why We Built
                <br />
                The Repurposer
              </h2>
            </div>
            <div className="lg:col-span-5 lg:border-l lg:border-foreground lg:pl-12 flex items-end">
              <p className="font-body text-lg text-muted-foreground leading-relaxed text-justify drop-cap">
                Content creators spend hours filming, editing, and publishing
                videos. But the content lifecycle shouldn't end there. Every
                video holds the potential for blog posts, social threads, and
                professional summaries—yet most creators lack the time to
                repurpose manually.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-foreground text-primary-foreground border-b border-foreground newsprint-texture">
        <div className="container py-16 md:py-20">
          <div className="max-w-3xl mx-auto text-center">
            <span className="font-mono text-xs uppercase tracking-widest text-accent">
              Our Mission
            </span>
            <blockquote className="font-serif text-3xl md:text-4xl font-bold italic mt-6 leading-snug">
              "To ensure no great idea stays trapped in a single format."
            </blockquote>
            <p className="font-body text-sm opacity-70 mt-6 max-w-lg mx-auto leading-relaxed">
              We believe content should flow freely across platforms. The
              Repurposer bridges the gap between video and written content,
              powered by AI that understands context, tone, and audience.
            </p>
          </div>
        </div>
      </section>

      <section className="border-b border-foreground">
        <div className="container py-16 md:py-20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0">
            {[
              {
                label: "The Problem",
                title: "Wasted Potential",
                text: "93% of video content is never repurposed. Creators leave enormous value on the table by not adapting their message for different platforms and audiences.",
              },
              {
                label: "The Solution",
                title: "Automated Pipeline",
                text: "Our AI engine extracts transcripts, identifies key themes, and generates platform-specific content that maintains your voice while optimizing for each medium.",
              },
              {
                label: "The Result",
                title: "3x Your Reach",
                text: "One YouTube video becomes a blog post ranking on Google, a Twitter thread driving engagement, and a LinkedIn summary building your professional brand.",
              },
            ].map((item, i) => (
              <div
                key={i}
                className={`p-8 ${i < 2 ? "md:border-r md:border-foreground" : ""}`}
              >
                <span className="font-mono text-[10px] uppercase tracking-widest text-accent">
                  {item.label}
                </span>
                <h3 className="font-serif text-2xl font-bold mt-2 mb-3">
                  {item.title}
                </h3>
                <p className="font-body text-sm text-muted-foreground leading-relaxed text-justify">
                  {item.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section>
        <div className="container py-16 text-center">
          <h2 className="font-serif text-3xl font-black mb-4">Try It Now</h2>
          <Link
            href="/pipeline"
            className="inline-flex items-center justify-center gap-2 min-h-[44px] px-10 py-4 bg-foreground text-primary-foreground font-sans text-xs uppercase tracking-widest font-semibold hover:bg-background hover:text-foreground border border-foreground transition-all duration-200"
          >
            Open Pipeline
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
};

export default About;
