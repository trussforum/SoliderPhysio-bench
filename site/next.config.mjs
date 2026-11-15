import { dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  outputFileTracingRoot: __dirname,
  // Next 15.5's segment explorer corrupts the webpack dev cache
  // (missing chunks such as ./611.js, then a client-manifest crash).
  experimental: { devtoolSegmentExplorer: false },
};

export default nextConfig;
