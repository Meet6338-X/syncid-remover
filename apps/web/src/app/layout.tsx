import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DeSynth Pro — Universal AI Watermark & SynthID Neutralization Engine",
  description: "Next-Generation cryptographic and frequency-domain platform for neutralizing invisible AI watermarks (SynthID, Tree-Ring) and scrubbing C2PA provenance credentials.",
  icons: {
    icon: "/brand-icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light">
      <body className={`${inter.variable} ${jetbrainsMono.variable} antialiased min-h-screen bg-[#FAFAFA] text-slate-900 selection:bg-indigo-600 selection:text-white`}>
        {children}
      </body>
    </html>
  );
}
