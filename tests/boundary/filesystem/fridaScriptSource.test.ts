import { execFile } from "node:child_process";
import {
  appendFile,
  mkdir,
  open,
  rename,
  symlink,
  writeFile,
} from "node:fs/promises";
import { join } from "node:path";
import { promisify } from "node:util";
import { expect, it, onTestFinished, vi } from "vitest";

import { ArtifactResourceScope } from "../../../src/artifacts/ArtifactResourceScope.js";
import { AnalysisInputError } from "../../../src/domain/analysisErrorCore.js";
import { RegularFileCleanupFailure } from "../../../src/application/RegularFileRead.js";
import { OwnedFileHandle } from "../../../src/filesystem/OwnedFileHandle.js";
import {
  MAX_FRIDA_SCRIPT_BYTES,
  readFridaScriptSource,
} from "../../../src/frida/FridaScriptSource.js";
import { createTestTempDirectory } from "../../fixtures/temporaryDirectory.js";
import { holdFirstFileRead } from "../../support/holdFirstFileRead.js";

const run = promisify(execFile);
const fixture = async () => {
  const root = await createTestTempDirectory("rea-frida-source-");
  const scope = new ArtifactResourceScope();
  onTestFinished(async () => {
    await scope.close();
  });
  return { root, scope, path: join(root, "script.js") };
};

it.each([0, MAX_FRIDA_SCRIPT_BYTES])(
  "accepts exactly %i file bytes",
  async (size) => {
    const { path, scope } = await fixture();
    const source = "a".repeat(size);
    await writeFile(path, source);
    expect(
      await readFridaScriptSource({ sourceKind: "file", path }, scope),
    ).toBe(source);
  },
);

it("preserves UTF-8 text, BOM and selected regular-file symlinks", async () => {
  const { root, path, scope } = await fixture();
  const source = "\uFEFFsend('ação');\n";
  await writeFile(path, source);
  expect(await readFridaScriptSource({ sourceKind: "file", path }, scope)).toBe(
    source,
  );
  if (process.platform !== "win32") {
    const link = join(root, "selected-link.js");
    await symlink(path, link);
    expect(
      await readFridaScriptSource({ sourceKind: "file", path: link }, scope),
    ).toBe(source);
  }
});

it("rejects an oversized sparse file before reading content", async () => {
  const { path, scope } = await fixture();
  const handle = await open(path, "w");
  await handle.truncate(MAX_FRIDA_SCRIPT_BYTES + 1);
  await handle.close();
  const gate = await holdFirstFileRead(path);
  try {
    await expect(
      readFridaScriptSource({ sourceKind: "file", path }, scope),
    ).rejects.toBeInstanceOf(AnalysisInputError);
    expect(gate.readCount).toBe(0);
  } finally {
    gate.release();
    vi.restoreAllMocks();
  }
});

it("uses UTF-8 bytes for the same inline limit", async () => {
  const { scope } = await fixture();
  const source = "é".repeat(MAX_FRIDA_SCRIPT_BYTES / 2);
  expect(
    await readFridaScriptSource({ sourceKind: "inline", source }, scope),
  ).toBe(source);
  await expect(
    readFridaScriptSource(
      { sourceKind: "inline", source: source + "é" },
      scope,
    ),
  ).rejects.toMatchObject({ issues: [{ path: ["source"] }] });
});

it("rejects replacement-character expansion past the native source budget", async () => {
  const { path, scope } = await fixture();
  await writeFile(path, Buffer.alloc(MAX_FRIDA_SCRIPT_BYTES / 2, 0xff));
  await expect(
    readFridaScriptSource({ sourceKind: "file", path }, scope),
  ).rejects.toBeInstanceOf(AnalysisInputError);
});

it("rejects a directory", async () => {
  const { root, scope } = await fixture();
  const path = join(root, "directory");
  await mkdir(path);
  await expect(
    readFridaScriptSource({ sourceKind: "file", path }, scope),
  ).rejects.toMatchObject({ code: "EISDIR" });
});

it.skipIf(process.platform === "win32")(
  "rejects a FIFO and its symlink without waiting for a writer",
  async () => {
    const { root, path, scope } = await fixture();
    await run("mkfifo", [path]);
    const link = join(root, "fifo-link");
    await symlink(path, link);
    for (const selected of [path, link])
      await expect(
        readFridaScriptSource({ sourceKind: "file", path: selected }, scope),
      ).rejects.toMatchObject({ code: "ENOTFILE" });
  },
  2000,
);

it.skipIf(process.platform === "win32")(
  "rejects an unbounded character device",
  async () => {
    const { scope } = await fixture();
    await expect(
      readFridaScriptSource({ sourceKind: "file", path: "/dev/zero" }, scope),
    ).rejects.toMatchObject({ code: "ENOTFILE" });
  },
  2000,
);

it("honors cancellation before acquisition", async () => {
  const { path, scope } = await fixture();
  const controller = new AbortController();
  const reason = new Error("cancel before source acquisition");
  controller.abort(reason);
  await expect(
    readFridaScriptSource(
      { sourceKind: "file", path },
      scope,
      controller.signal,
    ),
  ).rejects.toBe(reason);
});

it("cancels between real read chunks and closes its handle", async () => {
  const { path, scope } = await fixture();
  await writeFile(path, Buffer.alloc(128 * 1024, 0x61));
  const gate = await holdFirstFileRead(path);
  const close = vi.spyOn(OwnedFileHandle.prototype, "close");
  const controller = new AbortController();
  const reason = new Error("cancel during file read");
  const reading = readFridaScriptSource(
    { sourceKind: "file", path },
    scope,
    controller.signal,
  );
  try {
    await gate.firstRead;
    controller.abort(reason);
    gate.release();
    await expect(reading).rejects.toBe(reason);
    expect(gate.readCount).toBe(1);
    expect(close).toHaveBeenCalled();
    expect(scope.hasPending).toBe(false);
  } finally {
    gate.release();
    vi.restoreAllMocks();
  }
});

it("bounds reads even when the file grows past the limit after admission", async () => {
  const { path, scope } = await fixture();
  await writeFile(path, Buffer.alloc(64 * 1024, 0x61));
  const gate = await holdFirstFileRead(path);
  const reading = readFridaScriptSource({ sourceKind: "file", path }, scope);
  try {
    await gate.firstRead;
    await appendFile(path, Buffer.alloc(MAX_FRIDA_SCRIPT_BYTES, 0x62));
    gate.release();
    await expect(reading).rejects.toBeInstanceOf(AnalysisInputError);
    expect(gate.totalReadBytes).toBe(MAX_FRIDA_SCRIPT_BYTES + 1);
  } finally {
    gate.release();
    vi.restoreAllMocks();
  }
});

it("rejects path replacement while reading the admitted descriptor", async () => {
  const { root, path, scope } = await fixture();
  await writeFile(path, "send('original');");
  const gate = await holdFirstFileRead(path);
  const reading = readFridaScriptSource({ sourceKind: "file", path }, scope);
  try {
    await gate.firstRead;
    await rename(path, join(root, "original.js"));
    await writeFile(path, "send('replacement');");
    gate.release();
    await expect(reading).rejects.toMatchObject({ code: "ESTALE" });
  } finally {
    gate.release();
    vi.restoreAllMocks();
  }
});

it("retains failed close ownership and blocks subsequent inline acquisition until cleanup", async () => {
  const { path, scope } = await fixture();
  await writeFile(path, "send('fixture');");
  let denied = true;
  let handle: OwnedFileHandle["handle"] | undefined;
  const original = OwnedFileHandle.prototype.close;
  vi.spyOn(OwnedFileHandle.prototype, "close").mockImplementation(
    async function (this: OwnedFileHandle) {
      handle = this.handle;
      if (denied) throw new Error("fixture descriptor close denied");
      await original.call(this);
    },
  );
  try {
    await expect(
      readFridaScriptSource({ sourceKind: "file", path }, scope),
    ).rejects.toBeInstanceOf(RegularFileCleanupFailure);
    expect(handle?.fd).toBeGreaterThanOrEqual(0);
    expect(scope.hasPending).toBe(true);
    await expect(
      readFridaScriptSource(
        { sourceKind: "inline", source: "send('next');" },
        scope,
      ),
    ).rejects.toMatchObject({ cleanup: { resources: [path] } });
    await expect(scope.close()).rejects.toThrow("cleanup remains incomplete");
    denied = false;
    await scope.close();
    expect(handle?.fd).toBe(-1);
  } finally {
    denied = false;
    await scope.close();
    vi.restoreAllMocks();
  }
});
