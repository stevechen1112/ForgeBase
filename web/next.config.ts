import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");
const configuredBasePath = process.env.NEXT_PUBLIC_BASE_PATH?.trim();
const basePath = configuredBasePath && configuredBasePath !== "/"
  ? `/${configuredBasePath.replace(/^\/+|\/+$/g, "")}`
  : "";

const nextConfig: NextConfig = {
  // 前台部署在 Vercel，使用 standalone output
  output: "standalone",
  turbopack: { root: process.cwd() },
  basePath,

  async redirects() {
    const legacyPaths = [
      ["/technical-docs", "/docs"],
      ["/dealer-locator", "/dealers"],
      ["/cookie-policy", "/cookies"],
      ["/custom-solutions", "/oem-odm"],
    ] as const;
    return legacyPaths.flatMap(([from, to]) => [
      { source: from, destination: to, permanent: true },
      { source: `/zh-TW${from}`, destination: `/zh-TW${to}`, permanent: true },
    ]);
  },

  async rewrites() {
    const apiBase =
      process.env.INTERNAL_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiBase}/api/v1/:path*`,
      },
    ];
  },

  images: {
    remotePatterns: [
      {
        protocol: "https",
        // Cloudflare R2 public URL（部署時替換為實際 domain）
        hostname: process.env.R2_PUBLIC_HOSTNAME || "assets.example.com",
      },
    ],
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

export default withNextIntl(nextConfig);
