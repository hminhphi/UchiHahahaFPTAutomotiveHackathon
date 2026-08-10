"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentProps } from "react";

export default function NavLink({ href, className, children, ...props }: ComponentProps<typeof Link>) {
  const pathname = usePathname();
  const hrefStr = href.toString();
  const isActive = hrefStr === "/" ? pathname === "/" : pathname.startsWith(hrefStr);
  return (
    <Link
      href={href}
      className={[className, isActive ? "nav-active" : ""].filter(Boolean).join(" ")}
      aria-current={isActive ? "page" : undefined}
      {...props}
    >
      {children}
    </Link>
  );
}
