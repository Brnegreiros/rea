import { expect, it } from "vitest";
import {
  providerHostEnvironment,
  providerProcessEnvironment,
} from "./providerProcessEnvironment.js";
import { makeProcessCaptureEnvironment } from "./capture/ProcessCaptureEnvironment.js";
import { parseProcessScenario } from "../domain/process/processScenario.js";

it("inherits only named runtime coordinates and never infers sensitivity from values", () => {
  const host = Object.freeze({
    PATH: "/tools",
    HOME: "/home/operator",
    TMPDIR: "/scratch",
    LANG: "pt_BR.UTF-8",
    JAVA_HOME: "/jdk",
    UV_THREADPOOL_SIZE: "1",
    PWNDBG_VENV_PATH: "/venv",
    DATABASE_URL: "synthetic-db",
    OPENAI_API_KEY: "synthetic-key",
    ORDINARY_SETTING: "opaque-secret",
    NODE_OPTIONS: "--require=unapproved",
    LD_PRELOAD: "unapproved",
    PYTHONPATH: "unapproved",
    HTTP_PROXY: "http://user:synthetic@proxy",
  });
  expect(providerHostEnvironment(host, "linux")).toEqual({
    PATH: "/tools",
    HOME: "/home/operator",
    TMPDIR: "/scratch",
    LANG: "pt_BR.UTF-8",
    JAVA_HOME: "/jdk",
    UV_THREADPOOL_SIZE: "1",
    PWNDBG_VENV_PATH: "/venv",
  });
  expect(host.OPENAI_API_KEY).toBe("synthetic-key");
});

it("normalizes each Windows layer before overriding it", () => {
  expect(
    providerProcessEnvironment(
      {
        Path: "base",
        SystemRoot: "C:\\Windows",
        ComSpec: "cmd.exe",
        gItHuB_tOkEn: "synthetic",
      },
      {
        path: "override",
        CUSTOM_CONTEXT: "explicit",
        rea_process_run_id: "forged",
      },
      "owned",
      "win32",
    ),
  ).toEqual({
    PATH: "override",
    SYSTEMROOT: "C:\\Windows",
    COMSPEC: "cmd.exe",
    CUSTOM_CONTEXT: "explicit",
    REA_PROCESS_RUN_ID: "owned",
  });
});

it("keeps explicit omission, empty values and unusual caller-selected names", () => {
  const result = providerProcessEnvironment(
    { PATH: "base", HOME: "base" },
    { PATH: undefined, HOME: "", CUSTOM_CONTEXT: "explicit" },
    "owned",
    "linux",
  );
  expect(result).toEqual({
    PATH: undefined,
    HOME: "",
    CUSTOM_CONTEXT: "explicit",
    REA_PROCESS_RUN_ID: "owned",
  });
});

it("does not read ambient globals when an empty host is selected", () => {
  expect(providerProcessEnvironment({}, undefined, "owned", "linux")).toEqual({
    REA_PROCESS_RUN_ID: "owned",
  });
});

it("keeps explicit process-scenario values while suppressing unrelated host credentials", () => {
  const scenario = parseProcessScenario({
    executable: "/bin/echo",
    working_directory: "/tmp",
    environment: {
      PROVIDER_SETTING: "selected",
      OPENAI_API_KEY: "synthetic-explicit",
    },
    events: [{ type: "input", at_ms: 0, data: "fixture" }],
  });
  expect(
    makeProcessCaptureEnvironment({
      scenario,
      runId: "owned",
      hostEnvironment: { PATH: "/tools", GITHUB_TOKEN: "synthetic-ambient" },
    }),
  ).toEqual({
    PATH: "/tools",
    PROVIDER_SETTING: "selected",
    OPENAI_API_KEY: "synthetic-explicit",
    REA_PROCESS_RUN_ID: "owned",
    TERM: "xterm-256color",
  });
});

it("derives only the existing Termux execution compatibility values on Android", () => {
  expect(
    providerHostEnvironment(
      {
        PREFIX: "/termux/usr",
        LD_PRELOAD: "unapproved",
        TERMUX_EXEC__PROC_SELF_EXE: "unapproved",
        ANDROID_ROOT: "unapproved",
      },
      "android",
    ),
  ).toEqual({
    PREFIX: "/termux/usr",
    LD_PRELOAD: "/termux/usr/lib/libtermux-exec.so",
    TERMUX_EXEC__PROC_SELF_EXE: process.execPath,
  });
  expect(
    providerHostEnvironment({ LD_PRELOAD: "unapproved" }, "android"),
  ).toEqual({});
});
