import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { join, resolve } from "node:path";

const appDir = resolve(process.cwd(), process.argv[2] ?? ".");
const requireFromApp = createRequire(join(appDir, "package.json"));
const nextCli = requireFromApp.resolve("next/dist/bin/next");

const child = spawn(process.execPath, [nextCli, "build"], {
  cwd: appDir,
  stdio: "inherit",
  env: {
    ...process.env,
    // Static generation must not depend on the previous production API being
    // reachable. CI validates the API contract separately and ISR refreshes
    // content once the new stack is healthy.
    FORGEBASE_STRICT_BUILD_API: process.env.FORGEBASE_STRICT_BUILD_API ?? "0",
  },
});

child.on("error", (error) => {
  console.error("Failed to start Next.js build", error);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
