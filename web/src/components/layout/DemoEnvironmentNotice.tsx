type Props = {
  locale: string;
};

export function DemoEnvironmentNotice({ locale }: Props) {
  const isTraditionalChinese = locale.toLowerCase() === "zh-tw";

  return (
    <aside
      role="note"
      aria-label={isTraditionalChinese ? "測試網站說明" : "Test site notice"}
      className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-center text-xs font-medium leading-5 text-amber-950"
    >
      {isTraditionalChinese
        ? "ForgeBase 功能測試網站：公司、產品、證書與成效數字皆為測試情境，不代表真實製造商或供貨能力。"
        : "ForgeBase functional test site: the company, products, credentials, and performance figures are fictional and do not represent a real manufacturer or supply capability."}
    </aside>
  );
}
