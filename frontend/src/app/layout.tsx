import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FlarePoint — Geospatial Wildfire Intelligence",
  description: "Operational satellite fire detection clustering, tracking, and prioritization",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased select-none">{children}</body>
    </html>
  );
}
