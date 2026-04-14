import http from "node:http";

const port = Number(process.env.MOCK_SITE_PROFILE_PORT || 4010);

const tenantProfiles = {
  "tenant-a.localhost:3000": {
    brand_name: "Atlas Forge",
    logo_mark: "AF",
    logo_url: "",
    favicon_url: "",
    theme_key: "industrial",
    layout_key: "industrial",
    contact_email: "hello@atlasforge.test",
    contact_phone: "+1-555-0101",
    site_url: "https://atlasforge.example.com",
    default_locale: "en",
    asset_base: "/demo-assets",
    demo_company_folder: "handtool-company",
  },
  "tenant-b.localhost:3000": {
    brand_name: "Beacon Industrial",
    logo_mark: "BI",
    logo_url: "",
    favicon_url: "",
    theme_key: "classic",
    layout_key: "classic",
    contact_email: "sales@beaconindustrial.test",
    contact_phone: "+1-555-0202",
    site_url: "https://beaconindustrial.example.com",
    default_locale: "en",
    asset_base: "/demo-assets",
    demo_company_folder: "handtool-company",
  },
};

const defaultProfile = {
  brand_name: "ForgeBase Default",
  logo_mark: "FB",
  logo_url: "",
  favicon_url: "",
  theme_key: "classic",
  layout_key: "classic",
  contact_email: "hello@forgebase.test",
  contact_phone: "+1-555-0000",
  site_url: "https://forgebase.example.com",
  default_locale: "en",
  asset_base: "/demo-assets",
  demo_company_folder: "handtool-company",
};

const server = http.createServer((req, res) => {
  const tenantHost = req.headers["x-tenant-host"] || req.headers.host;
  const profile = tenantProfiles[tenantHost] || defaultProfile;

  console.log(`[mock-site-profile] ${req.method} ${req.url} host=${tenantHost} brand=${profile.brand_name}`);

  if (req.url === "/api/v1/site-profile") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(profile));
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ detail: "not found" }));
});

server.listen(port, "127.0.0.1", () => {
  console.log(`[mock-site-profile] listening on http://127.0.0.1:${port}`);
});