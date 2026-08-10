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
              <NavLink href="/">Overview</NavLink>
              <NavLink href="/trips/T01d">Trip review</NavLink>
              <NavLink href="/drivers">Drivers</NavLink>
              <NavLink href="/vehicles">Vehicles</NavLink>
              <NavLink href="/risk-insights">Risk insights</NavLink>
              <NavLink href="/reports">Reports</NavLink>
            </nav>
            <div className="nav-footer"><span className="status-dot" /> Demo control plane</div>
          </aside>
          <div className="app-content">
            <header className="site-header">
              <div><span className="header-kicker">Fleet safety operations</span><strong>Historical trip intelligence</strong></div>
              <div className="system-status"><span className="status-dot" /> Systems ready</div>
            </header>
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
