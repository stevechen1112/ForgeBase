import { NextResponse } from "next/server";
import { getMissingAssets, readDemoAsset } from "@/lib/demoAssetRoute";
import { getAllPublishedProducts, getPublishedCategories } from "@/lib/api";
import { getProductImage } from "@/lib/demoAssets";
import { getRuntimeSiteConfig } from "@/lib/runtimeSiteConfig";

export const dynamic = "force-dynamic";

/**
 * 前台自檢：圖片能不能正常顯示，取決於兩件事同時成立
 *   1. demo 素材目錄有掛進容器（否則所有圖退化成佔位圖）
 *   2. 前台的租戶設定與內容歸屬一致（否則查不到內容，連圖都不會被引用）
 *
 * 這兩者過去都是靜默失敗，只能靠人用眼睛發現。這個端點把它們變成可監控的訊號，
 * web 容器的 healthcheck 會打這裡，不健康時 `docker compose ps` 就會顯示 unhealthy。
 */
export async function GET() {
  const problems: string[] = [];

  const runtimeSiteConfig = await getRuntimeSiteConfig();

  // 1. 素材目錄探針：manifest 指定的首頁主視覺一定要讀得到實體檔
  const heroPath = runtimeSiteConfig.assetManifest?.homeHero;
  const heroSegments = heroPath
    ? heroPath.split("/assets/")[1]?.split("/").filter(Boolean)
    : undefined;
  let assetsMounted = false;
  if (heroSegments?.length) {
    assetsMounted = Boolean(await readDemoAsset(heroSegments, runtimeSiteConfig.demoCompanyFolder));
    if (!assetsMounted) {
      problems.push(
        `找不到素材實體檔 ${heroSegments.join("/")}，` +
          `請確認 demo/${runtimeSiteConfig.demoCompanyFolder}/assets 已掛進 web 容器`,
      );
    }
  } else {
    problems.push("assetManifest.homeHero 未設定，無法驗證素材目錄");
  }

  // 2. 內容探針：查不到任何分類，多半是 NEXT_PUBLIC_TENANT_SLUG 與內容歸屬不符
  const categories = await getPublishedCategories("en");
  if (categories.length === 0) {
    problems.push(
      "API 回傳 0 筆已發布分類；若後台確實有內容，請檢查 NEXT_PUBLIC_TENANT_SLUG 是否與內容的 tenant 一致",
    );
  }

  // 3. 執行期間實際發生過的缺檔
  const missingAssets = getMissingAssets();
  if (missingAssets.length > 0) {
    problems.push(`執行期間有 ${missingAssets.length} 個素材找不到實體檔`);
  }

  // 4. 產品圖仍靠 assetManifest.productByKey 以型號對照，新增或改型號的產品會沒有圖。
  //    這屬於內容缺口而非系統故障，列為 warning，不讓容器變 unhealthy。
  const warnings: string[] = [];
  const products = await getAllPublishedProducts("en");
  const productsWithoutImage = products.data
    .filter((product) => !getProductImage(product, undefined, runtimeSiteConfig))
    .map((product) => product.model_number);
  if (productsWithoutImage.length > 0) {
    warnings.push(
      `${productsWithoutImage.length} 個已發布產品沒有對應圖片（CMS 未設 image_url，型號也不在 assetManifest.productByKey）`,
    );
  }

  const healthy = problems.length === 0;
  return NextResponse.json(
    {
      status: healthy ? (warnings.length ? "ok-with-warnings" : "ok") : "degraded",
      assetsMounted,
      publishedCategories: categories.length,
      publishedProducts: products.data.length,
      missingAssets,
      productsWithoutImage,
      problems,
      warnings,
    },
    { status: healthy ? 200 : 503, headers: { "Cache-Control": "no-store" } },
  );
}
