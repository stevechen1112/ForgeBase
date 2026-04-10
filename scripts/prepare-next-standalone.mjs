import { existsSync, mkdirSync, rmSync, symlinkSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

const appDir = resolve(process.argv[2] ?? ".");
const standaloneDir = join(appDir, ".next", "standalone");
const standaloneNextDir = join(standaloneDir, ".next");

if (!existsSync(standaloneDir)) {
  console.error(`Standalone build output not found: ${standaloneDir}`);
  process.exit(1);
}

const linkIfExists = (source, destination) => {
  if (!existsSync(source)) {
    return;
  }

  rmSync(destination, { recursive: true, force: true });
  mkdirSync(dirname(destination), { recursive: true });
  symlinkSync(source, destination, process.platform === "win32" ? "junction" : "dir");
};

linkIfExists(join(appDir, "public"), join(standaloneDir, "public"));
linkIfExists(join(appDir, ".next", "static"), join(standaloneNextDir, "static"));