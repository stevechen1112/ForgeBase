import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  basePath: "/backend",
  assetPrefix: "/backend",

  async redirects() {
    return [
      {
        source: "/",
        destination: "/backend",
        permanent: false,
        basePath: false,
      },
      // Capture 定案：移除半套內容工廠／舊站匯入／假多語產品
      { source: "/dashboard/briefs", destination: "/dashboard", permanent: false },
      { source: "/dashboard/briefs/:path*", destination: "/dashboard", permanent: false },
      { source: "/dashboard/strategies", destination: "/dashboard", permanent: false },
      { source: "/dashboard/strategies/:path*", destination: "/dashboard", permanent: false },
      { source: "/dashboard/content-optimizer", destination: "/dashboard", permanent: false },
      { source: "/dashboard/content-optimizer/:path*", destination: "/dashboard", permanent: false },
      { source: "/dashboard/intake", destination: "/dashboard", permanent: false },
      { source: "/dashboard/intake/:path*", destination: "/dashboard", permanent: false },
      { source: "/dashboard/multilingual", destination: "/dashboard", permanent: false },
      { source: "/dashboard/multilingual/:path*", destination: "/dashboard", permanent: false },
      { source: "/dashboard/relations", destination: "/dashboard/products", permanent: false },
    ];
  },

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
