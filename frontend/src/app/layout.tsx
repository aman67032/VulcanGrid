import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VulcanGrid | AI Satellite Thermal Hotspot Spatial Intelligence",
  description: "Smart India Hackathon 2026 PS 26162 - Dual-Tier AI Thermal Hotspot Classifier & Spatial Intelligence System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
      </head>
      <body className="bg-slate-950 text-slate-100 antialiased overflow-hidden">
        {children}
      </body>
    </html>
  );
}
