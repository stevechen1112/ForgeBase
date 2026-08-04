import BriefForm from "../BriefForm";
export const metadata = { title: "新增寫作大綱 — NorthForge Admin" };
export default function NewBriefPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-foreground">新增寫作大綱</h1>
      <BriefForm />
    </div>
  );
}
