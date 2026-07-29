import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Windows developer shells often lack symlink privileges; ECS builds on Linux.
  output: process.platform === "win32" ? undefined : "standalone",
};

export default nextConfig;
