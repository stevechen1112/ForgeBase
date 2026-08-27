import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: "https://pcbrm.tw/", changeFrequency: "monthly", priority: 1 },
    { url: "https://pcbrm.tw/apply", changeFrequency: "monthly", priority: 0.8 },
    { url: "https://pcbrm.tw/privacy", changeFrequency: "yearly", priority: 0.3 },
    { url: "https://pcbrm.tw/terms", changeFrequency: "yearly", priority: 0.3 },
  ];
}
