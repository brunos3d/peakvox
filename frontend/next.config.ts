import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  typescript: { ignoreBuildErrors: true },
  allowedDevOrigins: ["192.168.1.150"],
};

export default nextConfig;
