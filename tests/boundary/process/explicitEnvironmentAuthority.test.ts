import { access, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { expect } from "vitest";
import { toolContract } from "../../../src/contracts/toolContracts.js";
import { captureProcessScenario } from "../../../src/process/capture/ProcessHarness.js";
import { createProcessCaptureEvidence } from "../../../src/application/process/ProcessEvidence.js";
import { createTestTempDirectory } from "../../fixtures/temporaryDirectory.js";
import { itWithCaptureCapability } from "./processCaptureCapability.js";

itWithCaptureCapability(
  "shows that explicit scenario variables are caller authority and are retained in evidence",
  async () => {
    const root = await createTestTempDirectory("rea-explicit-env-");
    const marker = join(root, "explicit-preload-ran");
    const preload = join(root, "preload.cjs");
    await writeFile(
      preload,
      `require('node:fs').writeFileSync(${JSON.stringify(marker)}, 'synthetic');`,
    );
    // The public MCP schema accepts these values without a separate approval field.
    const scenario = toolContract("capture_process_scenario").inputSchema.parse(
      {
        executable: process.execPath,
        arguments: [
          "-e",
          "process.stdout.write(JSON.stringify({explicit:process.env.EXPLICIT_CONTEXT==='SYNTHETIC_SCENARIO_CANARY',ambient:process.env.ORDINARY_SETTING!==undefined})+'\\n');",
        ],
        working_directory: root,
        environment: {
          EXPLICIT_CONTEXT: "SYNTHETIC_SCENARIO_CANARY",
          NODE_OPTIONS: `--require=${preload}`,
        },
      },
    );
    const result = await captureProcessScenario(
      scenario,
      undefined,
      process.platform,
      {
        PATH: process.env.PATH,
        HOME: root,
        ORDINARY_SETTING: "SYNTHETIC_AMBIENT_CANARY",
      },
    );
    if (!result.ok) throw result.error;
    const terminal = result.value.frames.map(({ data }) => data).join("");
    expect(terminal).toContain('"explicit":true');
    expect(terminal).toContain('"ambient":false');
    await expect(access(marker)).resolves.toBeUndefined();
    const evidence = JSON.stringify(
      createProcessCaptureEvidence(scenario, result.value),
    );
    expect(evidence).toContain("SYNTHETIC_SCENARIO_CANARY");
    expect(evidence).not.toContain("SYNTHETIC_AMBIENT_CANARY");
    expect(result.value.cleanup).toMatchObject({
      owned_process_group: "verified",
      temporary_root: "removed",
    });
  },
  20000,
);
