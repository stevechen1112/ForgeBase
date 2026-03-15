import CertificationForm from "../CertificationForm";
export const metadata = { title: "新增認證 — NorthForge Admin" };
export default function NewCertificationPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增認證</h1>
      <CertificationForm />
    </div>
  );
}
