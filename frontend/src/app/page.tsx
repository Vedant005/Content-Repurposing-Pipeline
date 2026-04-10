import Link from "next/link";
import {
  FileText,
  Twitter,
  Linkedin,
  ArrowRight,
  Zap,
  Shield,
  Clock,
} from "lucide-react";
import FeatureCard from "@/components/FeatureCard";

const Index = () => {
  return (
    <div>
      <section className="border-b border-foreground">
        <div className="container py-10 md:py-20">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-0">
            <div className="lg:col-span-8 lg:border-r lg:border-foreground lg:pr-12">
              <h2 className="font-serif text-5xl sm:text-6xl lg:text-8xl font-black tracking-tighter leading-[0.9] mt-4 mb-6">
                One Video.
                <br />
                Three Formats.
                <br />
                Zero Effort.
              </h2>
              <p className="font-body text-lg text-muted-foreground leading-relaxed max-w-xl text-justify">
                Paste a YouTube URL and instantly generate an SEO-optimized blog
                post, a compelling Twitter thread, and a polished LinkedIn
                summary. Content repurposing, automated.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 mt-8">
                <Link
                  href="/pipeline"
                  className="inline-flex items-center justify-center gap-2 min-h-[44px] px-8 py-3 bg-foreground text-primary-foreground font-sans text-xs uppercase tracking-widest font-semibold hover:bg-background hover:text-foreground border border-foreground transition-all duration-200"
                >
                  Start Repurposing
                  <ArrowRight className="h-4 w-4" />
                </Link>
                {/* <Link
                  href="/about"
                  className="inline-flex items-center justify-center gap-2 min-h-[44px] px-8 py-3 bg-transparent text-foreground font-sans text-xs uppercase tracking-widest font-semibold border border-foreground hover:bg-foreground hover:text-primary-foreground transition-all duration-200"
                >
                  Learn More
                </Link> */}
              </div>
            </div>

            <div className="lg:col-span-4 lg:pl-12 flex flex-col justify-center">
              <div className="space-y-6">
                {[
                  {
                    icon: <FileText className="h-5 w-5" />,
                    label: "Blog Post",
                    desc: "SEO-optimized, long-form",
                  },
                  {
                    icon: <Twitter className="h-5 w-5" />,
                    label: "Twitter Thread",
                    desc: "Engaging, viral-ready",
                  },
                  {
                    icon: <Linkedin className="h-5 w-5" />,
                    label: "LinkedIn Summary",
                    desc: "Professional, concise",
                  },
                ].map((item, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-4 border-b border-secondary pb-4 last:border-b-0"
                  >
                    <div className="border border-foreground h-10 w-10 flex items-center justify-center shrink-0">
                      {item.icon}
                    </div>
                    <div>
                      <h4 className="font-sans text-sm font-semibold uppercase tracking-wide">
                        {item.label}
                      </h4>
                      <p className="font-mono text-xs text-muted-foreground">
                        {item.desc}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-foreground text-primary-foreground border-b border-foreground overflow-hidden">
        <div className="flex animate-marquee whitespace-nowrap py-3">
          {Array(2)
            .fill(null)
            .map((_, i) => (
              <div key={i} className="flex items-center gap-8 mr-8">
                {[
                  "YouTube → Blog",
                  "YouTube → Tweets",
                  "YouTube → LinkedIn",
                  "SEO Optimized",
                  "One Click",
                  "AI Powered",
                ].map((text, j) => (
                  <span
                    key={j}
                    className="font-mono text-xs uppercase tracking-widest flex items-center gap-3"
                  >
                    <span className="text-accent">✦</span> {text}
                  </span>
                ))}
              </div>
            ))}
        </div>
      </section>

      <section className="bg-foreground text-primary-foreground border-b border-foreground newsprint-texture">
        <div className="container py-16 md:py-20">
          <div className="text-center mb-12">
            <span className="font-mono text-xs uppercase tracking-widest text-accent">
              How It Works
            </span>
            <h2 className="font-serif text-4xl lg:text-5xl font-black mt-2">
              Three Simple Steps
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0">
            {[
              {
                step: "01",
                title: "Paste URL",
                desc: "Drop any YouTube video link into the pipeline input.",
              },
              {
                step: "02",
                title: "AI Processes",
                desc: "Our engine extracts transcripts and generates optimized content.",
              },
              {
                step: "03",
                title: "Copy & Publish",
                desc: "Get your blog post, tweets, and LinkedIn summary instantly.",
              },
            ].map((item, i) => (
              <div
                key={i}
                className={`p-8 ${i < 2 ? "md:border-r md:border-primary-foreground/20" : ""}`}
              >
                <span className="font-serif text-6xl font-black text-accent leading-none">
                  {item.step}
                </span>
                <h3 className="font-serif text-2xl font-bold mt-4 mb-2">
                  {item.title}
                </h3>
                <p className="font-body text-sm opacity-70 leading-relaxed">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-foreground">
        <div className="container py-16 md:py-20">
          <div className="text-center mb-12">
            <span className="font-mono text-xs uppercase tracking-widest text-accent">
              Features
            </span>
            <h2 className="font-serif text-4xl lg:text-5xl font-black mt-2">
              Built for Creators
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0">
            <FeatureCard
              icon={<Zap className="h-5 w-5" strokeWidth={1.5} />}
              title="Lightning Fast"
              description="Generate all three content formats in under 30 seconds. No waiting, no queues."
              figure="Fig. 1.1"
            />
            <FeatureCard
              icon={<Shield className="h-5 w-5" strokeWidth={1.5} />}
              title="SEO Optimized"
              description="Blog posts include meta descriptions, headers, and keyword optimization out of the box."
              figure="Fig. 1.2"
            />
            <FeatureCard
              icon={<Clock className="h-5 w-5" strokeWidth={1.5} />}
              title="Save Hours"
              description="What used to take 2+ hours of writing now takes a single click. Focus on creating."
              figure="Fig. 1.3"
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-b border-foreground">
        <div className="container py-16 md:py-20 text-center">
          <div className="max-w-2xl mx-auto">
            <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
              ✧ ✧ ✧
            </span>
            <h2 className="font-serif text-4xl lg:text-5xl font-black mt-4 mb-4">
              Ready to Repurpose?
            </h2>
            <p className="font-body text-muted-foreground mb-8">
              Stop letting great video content go to waste. Transform it into
              written gold.
            </p>
            <Link
              href="/pipeline"
              className="inline-flex items-center justify-center gap-2 min-h-[44px] px-10 py-4 bg-foreground text-primary-foreground font-sans text-xs uppercase tracking-widest font-semibold hover:bg-background hover:text-foreground border border-foreground transition-all duration-200"
            >
              Launch Pipeline
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Index;
