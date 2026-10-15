// Operator-only provisioning. Uses REA's owning parser, not duplicated defaults.
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { processScenarioSchema } from "../../dist/domain/process/processScenario.js";
import { providerHostEnvironment } from "../../dist/process/providerProcessEnvironment.js";

const base = providerHostEnvironment({
  PATH: "/runtime/bin:/usr/bin:/bin",
  HOME: "/work",
  TMPDIR: "/work",
  LANG: "C.UTF-8",
  TERM: "xterm",
});
const profiles = {};
for (const name of ["basic", "echo", "wait", "probe", "disk", "cpu", "error"]) {
  profiles[name] = processScenarioSchema.parse({
    executable: "/runtime/bin/node",
    arguments: ["/app/experiments/execution-controller/fixture.mjs", name],
    working_directory: "/work",
    environment: { SYNTHETIC_VALUE: "SYNTHETIC_EXPLICIT_CANARY", EMPTY: "" },
    events:
      name === "echo"
        ? [
            {
              type: "input",
              at_ms: 600,
              data: "SYNTHETIC_MARKED_INPUT\n",
              sensitive: true,
            },
          ]
        : [],
    timeout_ms: name === "wait" ? 15000 : 5000,
    idle_timeout_ms: 15000,
    limits: {
      output_bytes: 12000,
      processes: 64,
      files: 32,
      file_bytes: 65536,
      filesystem_depth: 4,
    },
  });
}
const fixture = await readFile(new URL("./fixture.mjs", import.meta.url));
await writeFile(
  process.argv[2],
  JSON.stringify(
    {
      version: "rea-evaluation-authorization/1",
      base,
      profiles,
      fixtureSha256: createHash("sha256").update(fixture).digest("hex"),
    },
    null,
    2,
  ) + "\n",
);
