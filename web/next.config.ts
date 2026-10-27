import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  serverExternalPackages: ["@electric-sql/pglite", "pg"],
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    // Local development only: the Python functions are served by scripts/dev_api.py. On Vercel they are native.
    if (process.env.NODE_ENV !== "development") return [];
    return [
      { source: "/api/estate", destination: "http://127.0.0.1:8000/api/estate" },
      { source: "/api/scan", destination: "http://127.0.0.1:8000/api/scan" },
      { source: "/api/remediate", destination: "http://127.0.0.1:8000/api/remediate" },
      { source: "/api/policy", destination: "http://127.0.0.1:8000/api/policy" },
    ];
  },
};

export default nextConfig;
