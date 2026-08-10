import type { NextConfig } from "next";
import { withNextVideo } from "next-video/process";

const nextConfig: NextConfig = {
  // Windows developer shells often lack symlink privileges; ECS builds on Linux.
  output: process.platform === "win32" ? undefined : "standalone",
};

export default withNextVideo(nextConfig);
