import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./styles.css";

export const metadata: Metadata = {
  title: "FleetIQ Guardian",
  description: "Remote driver intelligence and collision risk operations console",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <aside className="side-nav">
            <Link className="brand" href="/">
              <span className="brand-mark">FQ</span>
              <span><strong>FleetIQ</strong><small>Guardian</small></span>
            </Link>
            <nav aria-label="Primary navigation">
              <Link href="/">Overview</Link>
              <Link className="nav-active" href="/trips/T01-Sample">Trip review</Link>
              <Link href="/">Drivers</Link>
              <Link href="/">Vehicles</Link>
              <Link href="/">Risk insights</Link>
              <Link href="/">Reports</Link>
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
