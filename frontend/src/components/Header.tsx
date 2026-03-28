"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const Header = () => {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = [
    { label: "Home", path: "/" },
    { label: "Pipeline", path: "/pipeline" },
    // { label: "About", path: "/about" },
  ];

  return (
    <header className="w-full border-b-2 border-black bg-[#F9F9F7] z-20 sticky top-0">
      {/* Main header */}
      <div className="container flex justify-between  px-4 lg:px-16  py-4 md:py-6">
        <Link href="/" className="flex items-center gap-3">
          <div>
            <h1 className="font-serif text-2xl md:text-3xl font-black tracking-tight leading-none">
              The Repurposer
            </h1>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
              YouTube → Blog → Tweets → LinkedIn
            </p>
          </div>
        </Link>
        <nav className="hidden md:flex align-middle gap-0 py-0 border border-foreground">
          {navItems.map((item) => (
            <Link
              key={item.path}
              href={item.path}
              className={`px-6 py-2 font-sans text-xs uppercase tracking-widest transition-colors duration-200 border-r border-foreground last:border-r-0 ${
                pathname === item.path
                  ? "bg-foreground text-primary-foreground"
                  : "hover:bg-foreground hover:text-primary-foreground"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden min-h-[44px] min-w-[44px] flex items-center justify-center border border-foreground hover:bg-foreground hover:text-primary-foreground transition-colors"
          aria-label="Toggle menu"
        >
          {mobileOpen ? (
            <X className="h-5 w-5" />
          ) : (
            <Menu className="h-5 w-5" />
          )}
        </button>
      </div>

      {mobileOpen && (
        <nav className="md:hidden border-t border-foreground">
          {navItems.map((item) => (
            <Link
              key={item.path}
              href={item.path}
              onClick={() => setMobileOpen(false)}
              className={`block px-4 py-3 font-sans text-sm uppercase tracking-widest border-b border-foreground transition-colors ${
                pathname === item.path
                  ? "bg-foreground text-primary-foreground"
                  : "hover:bg-secondary"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
};

export default Header;
