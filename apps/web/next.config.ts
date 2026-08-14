import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  devIndicators: { position: "bottom-right" },
  allowedDevOrigins: process.env.NEXT_DEV_ALLOWED_ORIGINS
    ? process.env.NEXT_DEV_ALLOWED_ORIGINS.split(",").map((origin) => origin.trim())
    : [],
};

export default nextConfig;
