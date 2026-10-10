import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque, DM_Mono, Figtree } from "next/font/google";

import { SessionProvider } from "@/lib/session";

import "./globals.css";

const bricolage = Bricolage_Grotesque({ subsets: ["latin"], weight: ["500", "700", "800"], variable: "--font-bricolage" });
const figtree = Figtree({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-figtree" });
const dmMono = DM_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-dm-mono" });

export const metadata: Metadata = {
  title: { default: "UnboxEd", template: "%s · UnboxEd" },
  description: "Any knowledge in. Real learning out.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { themeColor: "#1B164B", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-IN" className={`${bricolage.variable} ${figtree.variable} ${dmMono.variable}`}>
      <body className="min-h-dvh font-sans text-[16px] leading-relaxed antialiased">
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
