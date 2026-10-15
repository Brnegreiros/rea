import { writeFile } from "node:fs/promises";

const pidPath = process.argv[2];
if (pidPath !== undefined) await writeFile(pidPath, String(process.pid));
setInterval(() => undefined, 1_000);
