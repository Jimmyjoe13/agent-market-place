import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Sidebar } from "@/components/sidebar";
import { SectionErrorBoundary } from "@/components/ui/error-boundary";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RAG Agent IA",
  description: "Assistant IA personnalisé avec RAG - Retrieval Augmented Generation",
  keywords: ["RAG", "IA", "Assistant", "Mistral", "AI"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-zinc-950 text-zinc-100`}
      >
        <Providers>
          <div className="flex h-screen">
            {/* Sidebar */}
            <SectionErrorBoundary name="Sidebar">
              <Sidebar />
            </SectionErrorBoundary>
            
            {/* Main Content */}
            <main className="flex-1 overflow-hidden">
              <SectionErrorBoundary name="Content">
                {children}
              </SectionErrorBoundary>
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}

