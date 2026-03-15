import CTAForm from "../CTAForm";
export const metadata = { title: "新增 CTA — NorthForge Admin" };
export default function NewCTAPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增 CTA</h1>
      <CTAForm />
    </div>
  );
}
