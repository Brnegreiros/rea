# Provider subprocess environment boundary

The evaluation branch limits **implicit/base environment inheritance** for owned
provider subprocesses. Unknown names are omitted regardless of their spelling or
value. This is runtime selection, not secret classification or output redaction.

## Ownership and precedence

`providerHostEnvironment` owns the exact runtime-name policy in
`src/process/providerProcessEnvironment.ts`. The common launcher selects the base
from `hostEnvironment ?? process.env`, filters it, then applies explicit adapter
`env` overrides. The owned `REA_PROCESS_RUN_ID` is always applied last. An empty
selected host stays empty; no ambient fallback is introduced. Each Windows layer
is normalized separately before merging, so casing cannot evade precedence.

Explicit adapter overrides, IDA registration `config.env`, and process-scenario
`environment` are trusted caller inputs and remain available. They may deliberately
contain credentials or runtime injection options. Authorization must govern who
can supply them. A scenario cannot select the reserved process run ID.

This is a compatibility change: arbitrary values supplied only through the base
environment no longer reach covered children. A reviewed adapter that needs an
additional variable must pass that value explicitly, without copying the entire
ambient environment into the override layer.

## Selected runtime variables

The source constant is the complete, exact list. These groups explain why the
initial compatibility policy retains them; real-provider necessity has not been
demonstrated for every variable.

| Group | Retained coordinates | Reason and limit |
| --- | --- | --- |
| Executable and home | PATH, HOME, USER, LOGNAME, SHELL | Discovery and local runtime configuration; paths and user profiles remain trusted |
| Temporary storage | TMP, TEMP, TMPDIR | Runtime scratch space |
| Locale and terminal | LANG, LANGUAGE, explicit LC_* names, TZ, TERM, COLORTERM, NO_COLOR, FORCE_COLOR | Encoding, locale and terminal behavior; no wildcard selection |
| Desktop and XDG | DISPLAY, WAYLAND_DISPLAY, XAUTHORITY, DBUS_SESSION_BUS_ADDRESS, explicit XDG_* directories | Existing desktop/runtime compatibility; these can grant access to a user's session |
| Toolchain | JAVA_HOME, JDK_HOME, VIRTUAL_ENV, PREFIX | Provider runtime discovery |
| Libraries | LD_LIBRARY_PATH, DYLD_LIBRARY_PATH, DYLD_FALLBACK_LIBRARY_PATH | Native runtime compatibility; these affect code loading and require trusted paths |
| Resource/runtime controls | UV_THREADPOOL_SIZE, OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, GOMAXPROCS, GOMEMLIMIT | Existing worker and native-library limits |
| Python/debugger setup | PYTHONNOUSERSITE, PWNLIB_NOTERM, PWNDBG_NO_AUTOUPDATE, PWNDBG_VENV_PATH | Existing Pwntools/Pwndbg producer configuration |
| Windows only | SYSTEMROOT, WINDIR, COMSPEC, PATHEXT, USERPROFILE, APPDATA, LOCALAPPDATA, PROGRAMDATA, ALLUSERSPROFILE, USERNAME, SYSTEMDRIVE, HOMEDRIVE, HOMEPATH, PROCESSOR_ARCHITECTURE, OS | Runtime and interpreter discovery; normalized to uppercase |

Android derives only the existing Termux compatibility loader from the selected
PREFIX and process executable. Arbitrary ambient LD_PRELOAD is dropped. This
exception and all retained code-loading paths require external isolation.

Ambient NODE_OPTIONS, PYTHONPATH, JVM option injection, proxy settings and unknown
application settings are not selected. Ghidra additionally preserves its existing
explicit blank JVM injection controls. No secret-name regex or credential scan
is used, and no operator credential values are collected.

## Covered routes and remaining work

The policy is applied at the common owned-process launcher, process-capture PTY
environment producer, IDA stdio transport, Ghidra Java environment producer,
JADX Java inspection, and the native-module Playwright launcher. Existing browser
scenario and Electron allowlists are separate and unchanged. Provider-selection
variables are still read by the parent; they need not all be forwarded to a child.

This is **not a universal subprocess firewall**. Direct execution routes still
need individual review, including updater/setup commands, adb/apktool version
probes, Apple asset/disk helpers, Hopper utilities, ownership/sampling probes,
native UI helpers and the Android workspace guardian. Ghidra LaunchSupport
also deserves verification of every caller's environment provenance. Frida
target creation and remote/device runtimes require a separate environment
authority assessment.

Neither name selection nor an empty environment prevents a process from reading
files accessible to its OS identity, contacting a network, loading configuration,
or receiving a credential through arguments, stdin, files or explicit overrides.
A retained variable can itself contain sensitive data. The worker must remain
isolated and credential-free, with trusted PATH/library/display values.

See [the isolated verification report](verification/provider-environment-2026-10-15.md)
for reproduced exposure, exact tested scope and remaining gates.

