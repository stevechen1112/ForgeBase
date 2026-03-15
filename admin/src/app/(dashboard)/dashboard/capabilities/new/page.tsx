import CapabilityForm from "../CapabilityForm";
export const metadata = { title: "新增廠能 — NorthForge Admin" };
export default function NewCapabilityPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增廠能介紹</h1>
      <CapabilityForm />
    </div>
  );
}
