import "./globals.css";

import type { Metadata } from "next";

import Footer from "@/components/Footer";
import Header from "@/components/Header";
import { Analytics } from "@vercel/analytics/next";

export const metadata: Metadata = {
  title: "The Content Times | Video Repurposing Pipeline",
  description: "Generate content from videos",

  openGraph: {
    title: "The Content Times | Video Repurposing Pipeline",
    description: "Generate content from videos",
    url: "https://content-repurposing-pipeline.vercel.app",
    siteName: "The Content Times | Video Repurposing Pipeline",
    images: [
      {
        url: "/Content_home.png",
        width: 1200,
        height: 630,
        alt: "The Content Times | Video Repurposing Pipeline Preview",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "The Content Times | Video Repurposing Pipeline",
    description: "Generate content from videos",
    images: ["/Content_home.png"],
    creator: "@VedantKane56217",
  },

  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon-16x16.png",
    apple: "/apple-touch-icon.png",
  },

  authors: [{ name: "Vedant" }],
  creator: "Vedant",
  publisher: "Vedant",

  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
    },
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex flex-col min-h-screen">
        <Header />

        <main className="flex-grow max-w-screen-xl w-full mx-auto px-4 lg:px-8 border-x border-black bg-white/50">
          <Analytics />
          {children}
        </main>

        <Footer />
      </body>
    </html>
  );
}
