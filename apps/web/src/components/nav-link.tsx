"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentProps } from "react";

export type NavIconName = "overview" | "trip" | "drivers" | "vehicles" | "insights" | "reports";

type NavLinkProps = ComponentProps<typeof Link> & {
  icon?: NavIconName;
};

export default function NavLink({ href, className, children, icon, ...props }: NavLinkProps) {
  const pathname = usePathname();
  const hrefStr = href.toString();
  const isActive = hrefStr === "/" ? pathname === "/" : pathname.startsWith(hrefStr);
  const label = typeof children === "string" ? children : undefined;
  return (
    <Link
      href={href}
      className={[className, isActive ? "nav-active" : ""].filter(Boolean).join(" ")}
      aria-current={isActive ? "page" : undefined}
      aria-label={icon ? label : undefined}
      {...props}
    >
      {icon ? <><NavIcon name={icon} /><span className="nav-label">{children}</span></> : children}
    </Link>
  );
}

function NavIcon({ name }: { name: NavIconName }) {
  const paths: Record<NavIconName, React.ReactNode> = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    trip: <><path d="M4 6.5h16" /><path d="M7 3.5v6" /><path d="M17 3.5v6" /><path d="M5 12h14v8H5z" /><path d="m8 16 2 2 4-4" /></>,
    drivers: <><circle cx="12" cy="8" r="3.2" /><path d="M5 21c.6-3.9 3-6 7-6s6.4 2.1 7 6" /></>,
    vehicles: <><path d="M4 14h16l-1.4-5H5.4z" /><path d="M3 14v4h2" /><path d="M21 14v4h-2" /><circle cx="7" cy="18" r="1.7" /><circle cx="17" cy="18" r="1.7" /></>,
    insights: <><path d="M4 19V9" /><path d="M10 19V5" /><path d="M16 19v-8" /><path d="M22 19V3" /></>,
    reports: <><path d="M7 3h8l3 3v15H7z" /><path d="M15 3v4h4" /><path d="M10 12h5" /><path d="M10 16h5" /></>,
  };

  return (
    <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {paths[name]}
    </svg>
  );
}
