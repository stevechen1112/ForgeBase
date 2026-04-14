import type { MetadataRoute } from "next";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

export default async function robots(): Promise<MetadataRoute.Robots> {
  const { siteUrl: SITE_URL } = await getRuntimeSiteContext();

  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/dashboard/", "/api/"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
