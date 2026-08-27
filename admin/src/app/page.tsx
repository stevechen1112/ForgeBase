import { redirect } from "next/navigation";

export default function AdminRootPage() {
  // next.config.ts already applies basePath=/backend.
  redirect("/login");
}
