import { access, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import { expect, it, vi } from "vitest";
import { runOwnedCommand } from "../../../src/process/OwnedCommand.js";
import { createTestTempDirectory } from "../../fixtures/temporaryDirectory.js";

const credentialNames = [
  "OPENAI_API_KEY",
  "AWS_SECRET_ACCESS_KEY",
  "DATABASE_URL",
  "SUPABASE_SERVICE_ROLE_KEY",
  "GITHUB_TOKEN",
  "VERCEL_TOKEN",
  "ORDINARY_SETTING",
];
const syntheticHost = () => ({
  ...Object.fromEntries(
    credentialNames.map((name) => [name, "SYNTHETIC_REA_ENV_CANARY"]),
  ),
  PATH: process.env.PATH,
  HOME: process.env.HOME,
  SystemRoot: process.env.SystemRoot,
});

it("also filters the default process.env base", async () => {
  vi.stubEnv("REA_OPAQUE_PARENT_VALUE", "SYNTHETIC_DEFAULT_CANARY");
  try {
    const result = await runOwnedCommand(
      {
        command: process.execPath,
        arguments: [
          "-e",
          "process.stdout.write(JSON.stringify({hasParent:process.env.REA_OPAQUE_PARENT_VALUE!==undefined,hasNodeOptions:process.env.NODE_OPTIONS!==undefined}))",
        ],
        runId: `rea-default-env-${randomUUID()}`,
      },
      { timeoutMs: 5000, diagnosticBytes: 4096 },
    );
    expect(JSON.parse(result.stdout.text)).toEqual({
      hasParent: false,
      hasNodeOptions: false,
    });
  } finally {
    vi.unstubAllEnvs();
  }
});

it("blocks synthetic ambient credentials and Node preloading in a real owned child", async () => {
  const root = await createTestTempDirectory("rea-provider-env-");
  const marker = join(root, "preload-ran");
  const preload = join(root, "preload.cjs");
  await writeFile(
    preload,
    `require('node:fs').writeFileSync(${JSON.stringify(marker)}, 'synthetic preload');`,
  );
  const code = `process.stdout.write(JSON.stringify({seen:${JSON.stringify(credentialNames)}.filter(k=>process.env[k]!==undefined),nodeOptions:process.env.NODE_OPTIONS??null,path:process.env.PATH??null,runId:process.env.REA_PROCESS_RUN_ID}));`;
  const runId = `rea-env-${randomUUID()}`;
  const result = await runOwnedCommand(
    {
      command: process.execPath,
      arguments: ["-e", code],
      runId,
      hostEnvironment: {
        ...syntheticHost(),
        NODE_OPTIONS: `--require=${preload}`,
      },
    },
    { timeoutMs: 5000, diagnosticBytes: 4096 },
  );
  const observed = JSON.parse(result.stdout.text);
  expect(observed).toEqual({
    seen: [],
    nodeOptions: null,
    path: process.env.PATH ?? null,
    runId,
  });
  await expect(access(marker)).rejects.toMatchObject({ code: "ENOENT" });
  expect(result.stdout.text).not.toContain("SYNTHETIC_REA_ENV_CANARY");
});

it("preserves explicitly authorized adapter values without accepting a forged run ID", async () => {
  const runId = `rea-env-explicit-${randomUUID()}`;
  const result = await runOwnedCommand(
    {
      command: process.execPath,
      arguments: [
        "-e",
        "process.stdout.write(JSON.stringify({hasExplicit:process.env.PROVIDER_ACCESS==='SYNTHETIC_EXPLICIT_VALUE',hasAmbient:process.env.GITHUB_TOKEN!==undefined,runId:process.env.REA_PROCESS_RUN_ID}))",
      ],
      runId,
      hostEnvironment: syntheticHost(),
      env: {
        PROVIDER_ACCESS: "SYNTHETIC_EXPLICIT_VALUE",
        REA_PROCESS_RUN_ID: "forged",
      },
    },
    { timeoutMs: 5000, diagnosticBytes: 4096 },
  );
  expect(JSON.parse(result.stdout.text)).toEqual({
    hasExplicit: true,
    hasAmbient: false,
    runId,
  });
  expect(result.stdout.text).not.toContain("SYNTHETIC_EXPLICIT_VALUE");
});
