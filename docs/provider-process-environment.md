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

Explicit adapter overrides, IDA registration `config.env`, process-scenario
`environment`, and native-call environment overrides remain available. Being
explicit does not establish authorization: process/native-call fields can come
from CLI/MCP callers, while IDA registration comes from a selected local file.
They may deliberately contain credentials or runtime injection options. The
current schemas do not verify an independent operator approval. A scenario
cannot select the reserved process run ID.

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

The policy is applied at the common owned-process launcher, captured-command
executors, updater, process-capture PTY environment producer, IDA stdio transport,
Ghidra Java environment producer, JADX Java inspection, the native-module
Playwright launcher, and MCP self-diagnostics. Existing browser
scenario and Electron allowlists are separate and unchanged. Provider-selection
variables are still read by the parent; they need not all be forwarded to a child.

The captured-command producer treats `options.env` as a base and filters it.
`envOverrides` is a separate internal adapter input. Its production consumer
selects only SDKROOT, DEVELOPER_DIR, TOOLCHAINS and CLANG_MODULE_CACHE_PATH for
Darwin helper compilation. The selected host snapshot now reaches that compiler
even when a custom startup timeout is supplied. The adb version probe likewise
uses its selected environment rather than an unrelated global PATH.

MCP self-diagnostics retain runtime names plus exact configuration names derived
from `config/environment.ts`. The SDK's ambient defaults are explicitly blanked
before selected values are applied, and target selection remains removed.
Recognized configuration values, including declared reference-secret patterns,
are intentional REA inputs; they are not classified as safe or authorized merely
because the parser recognizes their names. Unknown custom launcher variables
and ambient NODE_OPTIONS no longer reach that diagnostic child.

This is **not a universal subprocess firewall**. Shared executors now cover the
mapped adb/apktool, Apple asset/disk, Hopper utility, ownership/sampling and native
UI command routes. Mac Hopper and taskkill calls use the same producer. Native
providers were not all executed. The Windows Android guardian and PTY capability
probe already select small explicit maps. Browser/Electron policies are unchanged.
Ghidra LaunchSupport can produce additional environment entries as provider code;
its installation must be trusted. Frida native spawning and remote/device
runtimes remain outside dynamic coverage. LLDB's caller-selected target overrides
also retain their separate execution authority.

Neither name selection nor an empty environment prevents a process from reading
files accessible to its OS identity, contacting a network, loading configuration,
or receiving a credential through arguments, stdin, files or explicit overrides.
A retained variable can itself contain sensitive data. The worker must remain
isolated and credential-free, with trusted PATH/library/display values.

See [the isolated verification report](verification/provider-environment-2026-10-15.md)
for reproduced exposure, exact tested scope and remaining gates.

## Explicit authority and retained data

A real isolated PTY fixture demonstrated that a process scenario accepted by the
public tool schema can supply a synthetic value and execute an explicitly chosen
Node preload. Capture Evidence retains the explicit value in its scenario
commitment. This is preserved caller data, not a redaction guarantee. Native-call
observations similarly include explicit target environment fields; their macOS
execution was not tested here.

For B•Code evaluation, use a credential-free worker and synthetic inputs. An
approval must cover the selected executable, arguments, target and explicit
variable names/values; approving an investigation generally is insufficient.
Automated operation requires an authorization decision outside model-generated
input. No IAM integration or per-key authorization service is introduced by this
patch. A checkbox or model-supplied approval flag would not supply that authority.

See the [direct-route and authority verification](verification/direct-environment-2026-10-15.md)
for the route matrix, observed limitations and readiness decision.

The [external execution authorization contract](external-execution-authorization.md)
defines a narrow synthetic-evaluation profile, independent operator decisions,
exact intent/environment binding and private evidence retention. Its
[acceptance catalogue](verification/execution-authorization-acceptance-2026-10-15.json)
stores definition-time NOT_TESTED values. The separate
[controller prototype record](verification/controller-prototype-2026-10-15.md)
reports later case-specific execution observations. Neither documentation nor
the experimental fixed-fixture controller enables authorization for direct REA
CLI/MCP users, enables a native provider or changes canonical Evidence.

The [janitor follow-up](verification/controller-janitor-2026-10-16.md) separates
verified startup/interruption behavior from failed raw/audit expiry after the
storage owner is killed. Synthetic explicit values remaining in pending intent
are still controlled evidence; an admission block is not a deletion receipt.
