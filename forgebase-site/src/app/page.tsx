/* eslint-disable @next/next/no-img-element */
import Link from "next/link";
import "./homepage-v2.css";

const problems = [
  ["01", "產品很多，買主不知道怎麼選", "用途、規格與認證分散，只能等待業務解釋。"],
  ["02", "收到詢問，資料仍不夠報價", "業務還要重新追問產品、數量、應用與時程。"],
  ["03", "詢價進來，後續卻散在個人信箱", "負責人、回覆與處理結果沒有共同紀錄。"],
];

const journey = [
  ["01", "先被看見", "展會、搜尋、轉介紹或推廣。", true],
  ["02", "看懂產品", "了解用途、能力與適用方向。", false],
  ["03", "找到品項", "查看規格、證書與常見問題。", false],
  ["04", "提出需求", "填寫數量、用途、時程與附件。", false],
  ["05", "業務接手", "分派負責人並設定下一步。", false],
  ["06", "留下結果", "記錄報價、成交或失單。", false],
];

const features = [
  ["01", "產品、分類與規格管理", "管理產品圖片、規格、下載文件、分類與多層產品資料。", "目前可用"],
  ["02", "用途、能力與證書內容", "讓買主從應用情境、製造能力與品質資料了解公司。", "目前可用"],
  ["03", "多語網站與內容維護", "依語系管理已確認的網站內容，交付後由公司自行更新。", "目前可用"],
  ["04", "結構化 RFQ 詢價", "收集產品、數量、用途、時程、客製需求與附件。", "目前可用"],
  ["05", "詢價工作台", "指派負責人、建立待辦、留下備註並追蹤處理進度。", "目前可用"],
  ["06", "訪客行為與關注意圖", "整理瀏覽、下載、互動與詢價前行為，協助判斷關注程度。", "進階測試"],
  ["07", "AI 產品顧問", "依已確認資料回答問題、協助找產品並引導完成詢價。", "目前可用"],
  ["08", "商機與結果追蹤", "連結來源、詢價、報價、洽談、成交與失單結果。", "進階測試"],
];

const templates = [
  ["01", "精密加工", "AxisForm", "能力與零件案例導向", "/templates/precision-machining/hero-cnc-facility.png", "/templates/precision-machining/"],
  ["02", "工業機械", "Vantera", "設備系列與服務導向", "/templates/industrial-machinery/hero-servo-forming-line.png", "/templates/industrial-machinery/"],
  ["03", "電子零組件", "Veltrix", "料號與規格查找導向", "/templates/electronic-components/component-family-hero.png", "/templates/electronic-components/"],
  ["04", "工業自動化", "Kinetra", "產線與解決方案導向", "/templates/industrial-automation/connected-robotic-line.png", "/templates/industrial-automation/"],
  ["05", "工程材料", "Matera", "材料與性能資料導向", "/templates/engineering-materials/material-archive-hero.png", "/templates/engineering-materials/"],
  ["06", "客製包裝", "Tuckform", "包裝形式與需求導向", "/templates/custom-packaging/packaging-system-hero.png", "/templates/custom-packaging/"],
];

function Brand() {
  return (
    <span className="v2-brand">
      <span className="v2-brand-mark" aria-hidden="true">FB</span>
      <span className="v2-brand-copy"><strong>ForgeBase</strong><small>EXPORT CUSTOMER &amp; RFQ SYSTEM</small></span>
    </span>
  );
}

export default function HomePage() {
  return (
    <main className="forge-v2" id="top">
      <header className="v2-header">
        <div className="v2-shell v2-nav">
          <Link href="#top" aria-label="ForgeBase 首頁"><Brand /></Link>
          <nav className="v2-desktop-nav" aria-label="主要導覽">
            <a href="#why">為什麼需要</a>
            <a href="#journey">如何接住需求</a>
            <a href="#features">產品功能</a>
            <a href="#templates">版型範本</a>
            <a href="#demo">測試案例</a>
          </nav>
          <div className="v2-nav-actions">
            <Link className="v2-login" href="/backend/login">後台登入</Link>
            <Link className="v2-button v2-button-primary" href="/apply">申請導入評估</Link>
          </div>
          <details className="v2-mobile-menu">
            <summary>選單</summary>
            <nav aria-label="行動版導覽">
              <a href="#why">為什麼需要</a><a href="#journey">如何接住需求</a><a href="#features">產品功能</a><a href="#templates">版型範本</a><a href="#demo">測試案例</a><Link href="/backend/login">後台登入</Link>
            </nav>
          </details>
        </div>
      </header>

      <section className="v2-hero">
        <div className="v2-shell v2-hero-inner">
          <p className="v2-eyebrow">Your always-on export sales desk</p>
          <h1>24 小時<span className="v2-mobile-break"><br /></span>全年無休的<br /><em>線上全能業務。</em></h1>
          <p className="v2-lead">從介紹產品、協助查找、回答基本問題，到收集詢價條件；ForgeBase 先完成前置接待，再把較完整的需求交給真人業務。</p>
          <div className="v2-actions"><a className="v2-button v2-button-primary" href="#journey">看看完整接待流程</a><a className="v2-button v2-button-ghost" href="#demo">查看實際測試案例</a></div>
          <ul className="v2-hero-notes"><li>團隊協助導入</li><li>交付後自行維護內容</li><li>目前開放產品測試</li></ul>
        </div>
      </section>

      <div className="v2-role-wrap">
        <div className="v2-shell v2-role-grid">
          <div className="v2-role-main"><small>FORGEBASE 的角色</small><strong>網站是入口，目標是把較完整的詢價交給業務。</strong></div>
          <div className="v2-role-item"><b>01</b><strong>讓買主看懂</strong><span>找到產品與必要資料</span></div>
          <div className="v2-role-item"><b>02</b><strong>協助填清需求</strong><span>產品、數量、用途、時程</span></div>
          <div className="v2-role-item"><b>03</b><strong>交給業務處理</strong><span>分派、追蹤、留下紀錄</span></div>
        </div>
      </div>

      <section className="v2-section" id="why">
        <div className="v2-shell">
          <div className="v2-section-head"><div><p className="v2-eyebrow">The missing middle</p><h2>買主有興趣，卻還沒走到詢價。</h2></div><p>當產品不好找、資料不完整、表單問得太少，機會常在業務收到消息前就中斷。</p></div>
          <div className="v2-problem-grid">
            <div className="v2-problem-photo"><img src="/northforge-tools/demo/handtool-company/assets/generated/capability-quality-inspection.png" alt="製造業人員檢視品質與產品資料" /><div><strong>「網站有人看，不代表需求有被接回來。」</strong><span>ForgeBase 接住業務介入前的前置過程。</span></div></div>
            <div className="v2-problem-list">{problems.map(([number, title, text]) => <article key={number}><span>{number}</span><div><h3>{title}</h3><p>{text}</p></div></article>)}</div>
          </div>
        </div>
      </section>

      <section className="v2-section v2-journey" id="journey">
        <div className="v2-shell">
          <div className="v2-section-head"><div><p className="v2-eyebrow">One connected journey</p><h2>從進站到接手，不要斷在半路。</h2></div><p>ForgeBase 不取代業務，而是協助買主完成產品查找與需求填寫。</p></div>
          <div className="v2-journey-grid">{journey.map(([number, title, text, outside]) => <article className={outside ? "v2-outside" : ""} key={String(number)}><b>{String(number)}</b><strong>{String(title)}</strong><p>{String(text)}</p></article>)}</div>
          <div className="v2-range"><span><strong>ForgeBase：</strong>接起買主進站後，到業務接手前的流程。</span><span>曝光與流量另行規劃</span></div>
        </div>
      </section>

      <section className="v2-section v2-features" id="features">
        <div className="v2-shell">
          <div className="v2-section-head"><div><p className="v2-eyebrow">What ForgeBase does</p><h2>不只介紹公司，也把產品、詢價與業務處理接起來。</h2></div><p>從買主進站、查找產品、提出需求，到公司接手處理，ForgeBase 提供一套完整功能。</p></div>
          <div className="v2-feature-grid">{features.map(([number, title, text, status]) => <article key={number}><div className="v2-feature-top"><span>{number}</span><small className={status === "進階測試" ? "v2-test" : ""}>{status}</small></div><h3>{title}</h3><p>{text}</p></article>)}</div>
        </div>
      </section>

      <section className="v2-section v2-templates" id="templates">
        <div className="v2-shell">
          <div className="v2-section-head"><div><p className="v2-eyebrow">Six industry directions</p><h2>不同產業、不同產品，都有適合的網站表達方式。</h2></div><p>六套範本不只是更換照片與顏色，版面、產品查找與詢價動線也各自不同。先選接近的方向，再換成公司的內容並接上 ForgeBase。</p></div>
          <div className="v2-template-grid">{templates.map(([number, industry, name, direction, image, href]) => <a href={href} className="v2-template-card" key={number}><span className="v2-template-no">{number}</span><img src={image} alt={`${industry}網站範本 ${name}`} /><div><small>{industry}</small><strong>{name}</strong><span>{direction}</span></div></a>)}</div>
          <div className="v2-template-note"><b>範本說明</b><span>範本中的公司、設備、規格、證書與產能皆為示意資料，不代表真實公司或製造能力。實際導入時會依公司產品與需求調整內容。</span></div>
        </div>
      </section>

      <section className="v2-section v2-demo" id="demo">
        <div className="v2-shell">
          <div className="v2-section-head"><div><p className="v2-eyebrow">See how it works</p><h2>看完整流程，不只看首頁。</h2></div><p>從找產品、送詢價，一路測試到後台接手。</p></div>
          <div className="v2-demo-card"><div className="v2-demo-image"><img src="/northforge-tools/demo/handtool-company/assets/generated/about-factory-hero-northforge.png" alt="NorthForge Tools 測試網站工廠情境" /></div><div className="v2-demo-copy"><p className="v2-eyebrow">完整功能測試 / NorthForge Tools</p><h3>從找產品，到業務收到詢價。</h3><p>一個實際串起前台、詢價與後台的測試情境。</p><ul><li>產品與應用查找</li><li>AI 接待與結構化詢價</li><li>後台分派與處理紀錄</li></ul><small>NorthForge Tools 為功能測試情境，不代表真實製造商、供貨能力或成交案例。</small><a className="v2-button v2-button-primary" href="/northforge-tools/">查看完整測試網站</a></div></div>
        </div>
      </section>

      <section className="v2-final" id="contact"><div className="v2-shell v2-final-grid"><div><p className="v2-eyebrow">ForgeBase product test</p><h2>先走一次完整流程，再判斷是否適合你的產品與詢價方式。</h2><p>目前開放產品測試與導入評估。我們會先了解產品資料、現有網站與詢價流程，再確認適合的導入範圍。</p></div><div className="v2-final-actions"><Link className="v2-button v2-button-dark" href="/apply">申請導入評估</Link><a className="v2-button v2-button-outline" href="#demo">先看完整測試案例</a><small>送出評估不代表受理、報價或交付承諾</small></div></div></section>

      <footer className="v2-footer"><div className="v2-shell"><div className="v2-footer-top"><div><Link href="#top"><Brand /></Link><p>製造業的海外客戶接待與詢價管理平台</p></div><nav aria-label="頁尾導覽"><a href="#why">為什麼需要</a><a href="#journey">接待流程</a><a href="#features">產品功能</a><a href="#templates">版型範本</a><a href="#demo">測試案例</a><Link href="/privacy">資料使用</Link><Link href="/terms">產品測試說明</Link></nav></div><div className="v2-footer-bottom"><span>© 2026 ForgeBase. Controlled product test.</span><span>對外資料與承諾仍由公司人員確認。</span></div></div></footer>
    </main>
  );
}
