import type { Metadata } from "next";
import "./globals.css";
import Footer from "@/components/Footer";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "The Content Times | Video Repurposing Pipeline",
  description: "All the news that is fit to print, generated from your videos.",
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
          {children}
        </main>

        <Footer />
      </body>
    </html>
  );
}
