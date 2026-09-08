//// Neoffice — added file (no upstream equivalent): the Studio's type-check, run by CI.
// vue-tsc walks into frappe-ui's shipped TypeScript sources (a workspace package), whose
// import.meta.env and .ts-extension imports fail under this tsconfig; those errors are the
// library's, not ours. Only errors in frontend/src count.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const run = spawnSync("npx", ["vue-tsc", "--noEmit", "--pretty", "false", "-p", "tsconfig.json"], {
	cwd: path.join(here, ".."),
	encoding: "utf8",
	shell: process.platform === "win32",
});
const output = `${run.stdout || ""}${run.stderr || ""}`;
const errors = output.split("\n").filter((line) => /error TS\d+/.test(line));
const ours = errors.filter((line) => !line.includes("node_modules/"));
const library = errors.length - ours.length;
if (ours.length) {
	console.error(ours.join("\n"));
	console.error(`\n${ours.length} type error(s) in frontend/src (${library} more inside node_modules ignored)`);
	process.exit(1);
}
console.log(`type-check: frontend/src is clean (${library} error(s) inside node_modules ignored)`);
