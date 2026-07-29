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
        <header className="site-header">
          <Link className="brand" href="/">
            <span className="brand-mark">FQ</span>
            <span>
              <strong>FleetIQ Guardian</strong>
              <small>Remote safety operations</small>
            </span>
          </Link>
          <div className="system-status">
            <span className="status-dot" />
            Control plane online
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
