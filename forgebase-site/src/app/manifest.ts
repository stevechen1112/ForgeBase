import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "ForgeBase",
    short_name: "ForgeBase",
    description: "外銷製造業網站與詢價管理工具",
    start_url: "/",
    display: "standalone",
    background_color: "#f2f0ea",
    theme_color: "#18242c",
  };
}
