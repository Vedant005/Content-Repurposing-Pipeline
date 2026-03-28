import { CiLinkedin } from "react-icons/ci";
import { FaGithub } from "react-icons/fa";
import { FaXTwitter } from "react-icons/fa6";
import { TbWorld } from "react-icons/tb";

const Footer = () => {
  return (
    <footer className="w-full border-t-4 border-black py-5 bg-[#F9F9F7]">
      <div className="container py-8">
        <div className="max-w-screen-xl mx-auto px-4 lg:px-8 grid grid-cols-1 md:grid-cols-12 gap-8">
          <div className="md:col-span-5 md:border-r md:border-foreground md:pr-8">
            <h3 className="font-serif text-2xl font-black uppercase mb-4">
              The Repurposer
            </h3>
            <p className="font-body text-sm  leading-relaxed text-justify">
              Transform your YouTube content into SEO-optimized blog posts,
              engaging Twitter threads, and professional LinkedIn summaries. One
              URL, three formats, zero effort.
            </p>
          </div>
          <div className="md:col-span-3 md:border-r md:border-foreground md:pr-8 md:pl-8">
            <h4 className="font-sans text-xs uppercase tracking-widest font-semibold mb-3">
              Navigation
            </h4>
            <ul className="space-y-2 font-body text-sm">
              <li>
                <a
                  href="/"
                  className="hover:underline decoration-accent decoration-2 underline-offset-4"
                >
                  Home
                </a>
              </li>
              <li>
                <a
                  href="/pipeline"
                  className="hover:underline decoration-accent decoration-2 underline-offset-4"
                >
                  Pipeline
                </a>
              </li>
            </ul>
          </div>
          <div className="md:col-span-4 md:pl-8">
            <h4 className="font-sans text-xs uppercase tracking-widest font-semibold mb-3">
              Details
            </h4>
            <p className="font-mono text-md ">
              Made by Vedant
              <br />
              <FaGithub /> <TbWorld /> <CiLinkedin /> <FaXTwitter />
              <br />© {new Date().getFullYear()} The Repurposer
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
