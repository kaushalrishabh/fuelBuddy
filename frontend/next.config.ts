import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cache Components / PPR target apps with cacheable static content.
  // FuelBuddy is entirely per-user, auth-gated client data (TanStack Query
  // over cookie-authenticated API calls) -- nothing here is prerenderable,
  // so the feature only adds dev-time "instant navigation" friction with no
  // benefit. Left off.
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
