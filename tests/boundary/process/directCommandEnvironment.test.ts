import { access, chmod, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { afterEach, expect, it, vi } from "vitest";
import { execFileOutput } from "../../../src/process/ExecFileOutput.js";
import { execFileBoundedOutput } from "../../../src/process/ExecFileBoundedOutput.js";
import { runUpdateCommand } from "../../../src/application/UpdateRuntime.js";
import { inspectAdbClient } from "../../../src/adb/AdbConfiguration.js";
import { createSystemProcessOwnershipHost } from "../../../src/process/ProcessOwnershipObservation.js";
import { createTestTempDirectory } from "../../fixtures/temporaryDirectory.js";

const names = [
  "GITHUB_TOKEN",
  "OPENAI_API_KEY",
  "DATABASE_URL",
  "ORDINARY_SETTING",
];
const host = () => ({
  PATH: process.env.PATH,
  HOME: process.env.HOME,
  SystemRoot: process.env.SystemRoot,
  ...Object.fromEntries(names.map((name) => [name, "SYNTHETIC_DIRECT_CANARY"])),
});
const probe = `process.stdout.write(JSON.stringify({seen:${JSON.stringify(names)}.filter(k=>process.env[k]!==undefined),nodeOptions:process.env.NODE_OPTIONS??null}));`;
afterEach(() => vi.unstubAllEnvs());

it.skipIf(process.platform === "win32")(
  "authorizes only selected compiler coordinates even with an explicit startup timeout",
  async () => {
    const root = await createTestTempDirectory("rea-compiler-env-");
    const compiler = join(root, "xcrun-fixture");
    const output = join(root, "compiler-state.json");
    await writeFile(
      compiler,
      `#!${process.execPath}\nconst fs=require('node:fs');fs.writeFileSync(${JSON.stringify(output)},JSON.stringify({sdk:process.env.SDKROOT,developer:process.env.DEVELOPER_DIR,ambient:process.env.GITHUB_TOKEN!==undefined}));const out=process.argv[process.argv.indexOf('-o')+1];fs.writeFileSync(out,'#!/bin/sh\\nexit 0\\n');fs.chmodSync(out,0o700);`,
    );
    await chmod(compiler, 0o700);
    vi.stubEnv("DEVELOPER_DIR", "/unselected-developer");
    const host = createSystemProcessOwnershipHost(
      "darwin",
      {
        PATH: process.env.PATH,
        HOME: root,
        SDKROOT: "/selected-sdk",
        DEVELOPER_DIR: "/selected-developer",
        GITHUB_TOKEN: "SYNTHETIC_COMPILER_CANARY",
      },
      {
        darwinCompiler: { kind: "xcrun", executable: compiler },
        compileTimeoutMs: 5000,
      },
    );
    try {
      await host.prepare?.();
      expect(JSON.parse(await readFile(output, "utf8"))).toEqual({
        sdk: "/selected-sdk",
        developer: "/selected-developer",
        ambient: false,
      });
    } finally {
      await host.close?.();
    }
  },
);

it("filters an execFile base and suppresses ambient Node preloading", async () => {
  const root = await createTestTempDirectory("rea-direct-env-");
  const marker = join(root, "preload-ran");
  const preload = join(root, "preload.cjs");
  await writeFile(
    preload,
    `require('node:fs').writeFileSync(${JSON.stringify(marker)}, 'synthetic');`,
  );
  const result = await execFileOutput(process.execPath, ["-e", probe], {
    env: { ...host(), NODE_OPTIONS: `--require=${preload}` },
    timeout: 5000,
    maxBuffer: 4096,
  });
  expect(JSON.parse(result.stdout)).toEqual({ seen: [], nodeOptions: null });
  await expect(access(marker)).rejects.toMatchObject({ code: "ENOENT" });
});

it("filters the implicit execFile process.env fallback", async () => {
  vi.stubEnv("ORDINARY_SETTING", "SYNTHETIC_IMPLICIT_CANARY");
  const result = await execFileOutput(process.execPath, ["-e", probe], {
    timeout: 5000,
    maxBuffer: 4096,
  });
  expect(JSON.parse(result.stdout)).toEqual({ seen: [], nodeOptions: null });
});

it("filters a bounded-output command's selected base", async () => {
  const result = await execFileBoundedOutput(process.execPath, ["-e", probe], {
    env: host(),
    limit: 4096,
  });
  expect(result.exitCode).toBe(0);
  expect(JSON.parse(result.stdout)).toEqual({ seen: [], nodeOptions: null });
});

it("filters the updater boundary without invoking a package manager", async () => {
  const result = await runUpdateCommand(
    [process.execPath, "-e", probe],
    host(),
  );
  if (!result.ok) throw new Error(result.error);
  expect(JSON.parse(result.value)).toEqual({ seen: [], nodeOptions: null });
});

it("keeps explicit adapter values separate from the filtered execFile base", async () => {
  const result = await execFileOutput(
    process.execPath,
    [
      "-e",
      "process.stdout.write(JSON.stringify({selected:process.env.EXPLICIT_CONTEXT==='SYNTHETIC_EXPLICIT_CANARY',ambient:process.env.GITHUB_TOKEN!==undefined}))",
    ],
    {
      env: host(),
      envOverrides: { EXPLICIT_CONTEXT: "SYNTHETIC_EXPLICIT_CANARY" },
      timeout: 5000,
      maxBuffer: 4096,
    },
  );
  expect(JSON.parse(result.stdout)).toEqual({ selected: true, ambient: false });
  expect(result.stdout).not.toContain("SYNTHETIC_EXPLICIT_CANARY");
});

it.skipIf(process.platform === "win32")(
  "uses the selected adb PATH for its real version probe",
  async () => {
    const root = await createTestTempDirectory("rea-adb-env-");
    const output = join(root, "observed.json");
    const binary = join(root, "adb");
    await writeFile(
      binary,
      `#!${process.execPath}\nrequire('node:fs').writeFileSync(${JSON.stringify(output)},JSON.stringify({ambient:process.env.ORDINARY_SETTING!==undefined,path:process.env.PATH}));process.stdout.write('Android Debug Bridge version 1.0.41\\nVersion 36.0.0-fixture\\n');`,
    );
    await chmod(binary, 0o700);
    vi.stubEnv("PATH", "/missing-global-path");
    const identity = await inspectAdbClient(
      { binary: "adb", pathSource: "path" },
      undefined,
      { PATH: root, ORDINARY_SETTING: "SYNTHETIC_ADB_CANARY" },
    );
    expect(identity.version).toBe("36.0.0-fixture");
    expect(JSON.parse(await readFile(output, "utf8"))).toEqual({
      ambient: false,
      path: root,
    });
  },
);
