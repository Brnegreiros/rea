import { access, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { expect, it } from "vitest";
import { runProductionMcpDoctor } from "../../../src/mcpDoctor.js";
import { createTestTempDirectory } from "../../fixtures/temporaryDirectory.js";

it("starts the SDK doctor with selected runtime/configuration names and no ambient canaries", async () => {
  const root = await createTestTempDirectory("rea-doctor-env-");
  const output = join(root, "observed.json");
  const marker = join(root, "preload-ran");
  const preload = join(root, "preload.cjs");
  await writeFile(
    preload,
    `require('node:fs').writeFileSync(${JSON.stringify(marker)},'synthetic');`,
  );
  const code = `require('node:fs').writeFileSync(${JSON.stringify(output)},JSON.stringify({ambient:process.env.GITHUB_TOKEN!==undefined,opaque:process.env.ORDINARY_SETTING!==undefined,nodeOptions:process.env.NODE_OPTIONS??null,home:process.env.HOME,profile:process.env.REA_MCP_INPUT_SCHEMA_PROFILE,target:process.env.HOPPER_TARGET_PATH??null}));`;
  const result = await runProductionMcpDoctor({
    command: process.execPath,
    args: ["-e", code],
    cwd: root,
    environment: {
      HOME: root,
      REA_MCP_INPUT_SCHEMA_PROFILE: "compact",
      HOPPER_TARGET_PATH: "/must-not-launch",
      GITHUB_TOKEN: "SYNTHETIC_DOCTOR_CANARY",
      ORDINARY_SETTING: "SYNTHETIC_DOCTOR_CANARY",
      NODE_OPTIONS: `--require=${preload}`,
    },
    deadlineMs: 5000,
  });
  // This fixture records startup only, so it deliberately does not implement MCP.
  expect(result.healthy).toBe(false);
  expect(JSON.parse(await readFile(output, "utf8"))).toEqual({
    ambient: false,
    opaque: false,
    nodeOptions: null,
    home: root,
    profile: "compact",
    target: null,
  });
  await expect(access(marker)).rejects.toMatchObject({ code: "ENOENT" });
});
