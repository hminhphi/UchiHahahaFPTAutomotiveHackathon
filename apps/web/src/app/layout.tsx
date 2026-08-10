import type { Metadata } from "next";
import type { ReactNode } from "react";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import NavLink from "@/components/nav-link";
import "./styles.css";

export const metadata: Metadata = {
  title: "FleetIQ Guardian",
  description: "Remote driver intelligence and collision risk operations console",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" className={`dark ${GeistSans.variable} ${GeistMono.variable}`}>
      <body>
        <div className="app-shell">
          <aside className="side-nav">
            <NavLink className="brand" href="/">
              <span className="brand-mark">FQ</span>
              <span><strong>FleetIQ</strong><small>Guardian</small></span>
            </NavLink>
            <nav aria-label="Primary navigation">
              <NavLink href="/" icon="overview">Overview</NavLink>
              <NavLink href="/trips/T01d" icon="trip">Trip review</NavLink>
              <NavLink href="/drivers" icon="drivers">Drivers</NavLink>
              <NavLink href="/vehicles" icon="vehicles">Vehicles</NavLink>
              <NavLink href="/risk-insights" icon="insights">Risk insights</NavLink>
              <NavLink href="/reports" icon="reports">Reports</NavLink>
            </nav>
          </aside>
          <div className="app-content">
            <header className="site-header">
              <strong>Fleet safety operations</strong>
            </header>
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
