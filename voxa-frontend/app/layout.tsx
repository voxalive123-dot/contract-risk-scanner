import type { Metadata } from "next";
import GoogleAnalytics from "./GoogleAnalytics";

import "./globals.css";

export const metadata: Metadata = {
  title: "VoxaRisk | Contract Risk Decision Intelligence",
  description:
    "VoxaRisk helps commercial teams identify hidden contract exposure, compare findings against organisational tolerance, preserve decision history, and create audit-ready contract risk review records.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body><GoogleAnalytics />
        {children}</body>
    </html>
  );
}
