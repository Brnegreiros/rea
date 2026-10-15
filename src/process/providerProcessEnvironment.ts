import { snapshotEnvironment } from "./snapshotEnvironment.js";

// Runtime coordinates, not an inventory of secrets. Unknown ambient names are
// omitted regardless of spelling; adapters must explicitly supply extra values.
const RUNTIME_KEYS = [
  "PATH",
  "HOME",
  "USER",
  "LOGNAME",
  "SHELL",
  "TMP",
  "TEMP",
  "TMPDIR",
  "LANG",
  "LANGUAGE",
  "LC_ALL",
  "LC_CTYPE",
  "LC_NUMERIC",
  "LC_TIME",
  "LC_COLLATE",
  "LC_MONETARY",
  "LC_MESSAGES",
  "LC_PAPER",
  "LC_NAME",
  "LC_ADDRESS",
  "LC_TELEPHONE",
  "LC_MEASUREMENT",
  "LC_IDENTIFICATION",
  "TZ",
  "TERM",
  "COLORTERM",
  "NO_COLOR",
  "FORCE_COLOR",
  "DISPLAY",
  "WAYLAND_DISPLAY",
  "XAUTHORITY",
  "DBUS_SESSION_BUS_ADDRESS",
  "XDG_RUNTIME_DIR",
  "XDG_CONFIG_HOME",
  "XDG_CACHE_HOME",
  "XDG_DATA_HOME",
  "XDG_STATE_HOME",
  "JAVA_HOME",
  "JDK_HOME",
  "VIRTUAL_ENV",
  "PREFIX",
  "LD_LIBRARY_PATH",
  "DYLD_LIBRARY_PATH",
  "DYLD_FALLBACK_LIBRARY_PATH",
  // Existing JS/Python producer limits and Pwndbg's controlled runtime setup.
  "UV_THREADPOOL_SIZE",
  "OMP_NUM_THREADS",
  "OPENBLAS_NUM_THREADS",
  "GOMAXPROCS",
  "GOMEMLIMIT",
  "PYTHONNOUSERSITE",
  "PWNLIB_NOTERM",
  "PWNDBG_NO_AUTOUPDATE",
  "PWNDBG_VENV_PATH",
] as const;

const WINDOWS_KEYS = [
  "SYSTEMROOT",
  "WINDIR",
  "COMSPEC",
  "PATHEXT",
  "USERPROFILE",
  "APPDATA",
  "LOCALAPPDATA",
  "PROGRAMDATA",
  "ALLUSERSPROFILE",
  "USERNAME",
  "SYSTEMDRIVE",
  "HOMEDRIVE",
  "HOMEPATH",
  "PROCESSOR_ARCHITECTURE",
  "OS",
] as const;

/** Select only runtime variables from a provider's ambient/base environment. */
export const providerHostEnvironment = (
  environment: Readonly<NodeJS.ProcessEnv>,
  platform: NodeJS.Platform = process.platform,
): Record<string, string> => {
  const snapshot = snapshotEnvironment(environment, platform);
  const selected: Record<string, string> = {};
  for (const name of [
    ...RUNTIME_KEYS,
    ...(platform === "win32" ? WINDOWS_KEYS : []),
  ]) {
    const value = snapshot[name];
    if (value !== undefined) selected[name] = value;
  }
  // Match the existing Android browser exception without inheriting arbitrary
  // loader injection values. This is compatibility, not a sandbox guarantee.
  if (platform === "android" && snapshot.PREFIX !== undefined) {
    selected.LD_PRELOAD = `${snapshot.PREFIX}/lib/libtermux-exec.so`;
    selected.TERMUX_EXEC__PROC_SELF_EXE = process.execPath;
  }
  return selected;
};

/** Explicit overrides require authority at their caller; this merge grants none. */
export const providerCommandEnvironment = (
  host: Readonly<NodeJS.ProcessEnv>,
  overrides: Readonly<NodeJS.ProcessEnv> | undefined = undefined,
  platform: NodeJS.Platform = process.platform,
): NodeJS.ProcessEnv => ({
  ...providerHostEnvironment(host, platform),
  ...snapshotEnvironment(overrides ?? {}, platform),
});

/** Preserve the owned run ID after explicitly selected adapter overrides. */
export const providerProcessEnvironment = (
  host: Readonly<NodeJS.ProcessEnv>,
  overrides: Readonly<NodeJS.ProcessEnv> | undefined,
  runId: string,
  platform: NodeJS.Platform = process.platform,
): NodeJS.ProcessEnv => ({
  ...providerCommandEnvironment(host, overrides, platform),
  REA_PROCESS_RUN_ID: runId,
});
