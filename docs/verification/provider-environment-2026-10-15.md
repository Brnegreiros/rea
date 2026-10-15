# REA-1.1: provider environment inheritance — 2026-10-15

## Outcome and revision

**F03 is partially mitigated on the evaluation branch. Production remains NO-GO.**
The old owned-process boundary forwarded unrelated synthetic credentials and
Node runtime injection options. The revised boundary selects known runtime
variables and preserves explicit adapter inputs.

- Repository: Brnegreiros/rea; branch: fix/bcode-rea-1-1-containment.
- Parent revision: `10c4c1cdef9d414008300adae754360088a39c16`.
- Main checked before publication: `6060de329de9f3636f63e24a2419847fd9d3f889`.
- No upstream, main, dependencies, package identity, license or deployment changes.
- [Machine-readable evidence](provider-environment-2026-10-15.json) retains logs,
  exit codes, tested-source SHA-256 values, commands, worker metrics and disposal.
- [Policy and compatibility contract](../provider-process-environment.md).

## Investigation and evidence

Static inspection followed the shared launcher and its provider consumers, plus
direct child-process, PTY, SDK and browser launch boundaries. The keyword
inventory is a navigation aid, not proof of complete dynamic coverage.

At the parent revision, two real owned-Node-child regressions failed as expected.
The child reported these synthetic variable names present:
OPENAI_API_KEY, AWS_SECRET_ACCESS_KEY, DATABASE_URL,
SUPABASE_SERVICE_ROLE_KEY, GITHUB_TOKEN, VERCEL_TOKEN and ORDINARY_SETTING.
It also reported the supplied NODE_OPTIONS preload setting. Thus exposure depends
on inheritance, not on recognizable credential names. No real credential values
were inspected or collected. The baseline assertion failed before checking the
preload marker; baseline execution of that preload is not separately claimed.

The fixed real-child tests report no listed ambient names, no NODE_OPTIONS,
preserved PATH and the owned run ID, and absence of the benign preload marker.
A separate test verifies the default process.env fallback and another preserves
an explicitly supplied synthetic adapter value while rejecting a forged run ID.
Retained output is names/booleans rather than secret values.

| Finding | Severity / impact | Evidence boundary | Disposition |
| --- | --- | --- | --- |
| E01: full base inheritance | HIGH: any credential or runtime option in the base can reach a provider | ProviderProcess.ts, former spread of hostEnvironment/process.env; two baseline failures | Mitigated in common launcher |
| E02: parallel launch boundaries | HIGH: a common-launcher-only fix would miss separate paths | IDA stdio, ProcessCaptureEnvironment, GhidraInstallation, JadxConfiguration, NativeModuleResolver | Same producer policy applied; verification scope below |
| E03: explicit override authority | HIGH when untrusted: caller can deliberately supply credentials/options | options.env, IDA config.env, scenario.environment | Preserved caller contract; upstream authorization remains required |
| E04: remaining direct execution | HIGH before operation: other routes can still forward broad environments | ExecFileOutput/ExecFileBoundedOutput consumers, ownership/native helpers, updater and external runtimes | OPEN; individual provenance review required |
| E05: compatibility and resource assurance | MEDIUM operational risk: omitted custom settings may break a provider; heavy checks approach VM memory bound | Exact allowlist and worker observations | Native-provider/OS matrix and clean larger-worker baseline pending |

## Minimal correction

One shared producer owns an exact runtime-name allowlist. The owned launcher
filters only its implicit/base layer, then applies explicit trusted overrides and
the owned run ID. Windows key normalization occurs per layer before merging.
Empty selected bases remain empty. Undefined and empty explicit values retain
their existing meaning. No regex guesses whether a value is a secret.

The same producer is used for the named parallel boundaries. IDA still explicitly
blanks SDK ambient defaults before selected coordinates and config.env are
applied. Ghidra retains its explicit empty JVM option controls. The existing
Android Termux loader exception is derived, rather than inheriting arbitrary
LD_PRELOAD. Browser-scenario and Electron policies are unchanged.

Retained groups include PATH/home/temp, locale/terminal, desktop/XDG, selected
toolchain/library locations and existing resource/Pwndbg controls. These are
compatibility candidates; not every variable has demonstrated real-provider
necessity. The complete list and risks are documented in the policy.

This is a **breaking environment compatibility change**. Arbitrary variables in
a selected base are now dropped for covered children. Reviewed adapters must
explicitly authorize additional values. No modernizations or dependency changes
were introduced.

## Isolated validation

Disposable Firecracker worker `sbx_F8TQYYj9PPXjM93ayb1zE0TGbcIq`, pinned image
digest in JSON, 2 vCPU, 4096 MiB, 512 PIDs, 30-minute maximum, no persistent
snapshot. A dedicated UID/GID 1001 ran project commands with cleared groups,
no effective capabilities and no_new_privs. Operator home access and sudo
elevation were denied; cgroup controls were not writable by the test user.

A bounded acquisition window allowed GitHub, npm and Node downloads. Node 24.18.0
was verified against its published checksum and npm 11.16.0 was pinned.
Locked dependencies were acquired with lifecycle scripts disabled. The unchanged
lockfile SHA-256 is
`0482085372c563c99b32519f51339eb280adc2bd83efdba6a8efd7cd4a49e9f0`.
Egress was deny-all for validation. Only benign fixtures and synthetic values
were used. No provider installation, native injection, deploy or package
publication was performed.

| Control / executed check | Status | Result and scope |
| --- | --- | --- |
| Exposure reproduction at parent | PASS (reproduction) | Two regressions fail against old code, showing seven synthetic names and NODE_OPTIONS |
| Final selected Vitest run | PASS | 144 passed, 1 macOS-only skip, 13 files; 13.99 s |
| Real owned-child suppression/explicit authority | PASS | Three tests; canaries absent, explicit value preserved, run ID protected |
| IDA SDK stdio seam | PASS | Real Node fixture through SDK; no native IDA execution |
| Ghidra/JADX environment tests | PASS | Producer/inspection and benign executable fixtures; no native Ghidra/JADX application certification |
| Process capture / Windows / Android policy | PASS for producer semantics | Pure boundary cases; actual PTY and native OS runtimes NOT_TESTED here |
| Browser module launch environment | PASS for requested options | Mock launcher; real Chromium compatibility NOT_TESTED in this round |
| CLI and MCP environment seams | PASS for selected fixtures | Provider selection preserved; does not establish every real provider |
| TypeScript | PASS | npm run typecheck, exit 0 |
| Runtime/skill build | PASS | npm run build:cached, exit 0; 3 successful tasks, 1 cached; 55.516 s |
| Formatting, 13 changed TS files | PASS | oxfmt --check, exit 0 |
| Selected-file ordinary lint | PASS with warnings | 0 errors, 14 warnings in legacy-sized/complex functions; exit 0 |
| Module boundaries | PASS | 1888 source files checked |
| Additional type-aware lint | NOT_TESTED | Invocation failed because oxlint-tsgolint executable is unavailable; no package added |
| Full suite/native providers/macOS/Windows | NOT_TESTED | No broader certification claimed |
| Cleanup/disposal | PASS | No remaining rea-user processes before stop; worker stopped, persistent false, deny-all retained |

The initial edited-code run had one invalid fixture (reserved scenario run ID)
and a TypeScript predicate error, both corrected. A later compatibility test
still expected an arbitrary Ghidra base variable and was aligned with the new
contract. Intermediate checks were interrupted and rerun; only the final logs
are acceptance evidence. Baseline and first failure logs remain in JSON.
A baseline lint sample has a different test-override scope; its 21 warnings
must not be interpreted as a comparable improvement over the final 14.

## Cost and resource observations

Whole-worker API duration was 1333.199 s and active CPU duration 630.037 s,
including setup, acquisition, failed/interrupted attempts, checks and evidence
collection. Cgroup CPU at evidence capture was 544.028381 s and whole-worker
memory peak 4,210,216,960 bytes (about 3.92 GiB). These counters have different
collection scopes and are not per-test performance measurements. Agent token
usage and peak process-family RSS were not measured separately.

The worker lifetime counter reported **two oom_kill events**. Their responsible
processes were not established. The final typecheck/build/tests completed, but
this is not a clean resource-health baseline. Repeat heavy validation in a
larger disposable worker before a broader readiness claim. The 434 ms baseline
run and 13.99 s final suite have different scopes and are not a speed comparison.

## Residual risks and roadmap

F03 stays OPEN/PARTIALLY_MITIGATED. Raw execution routes, explicit override
authority, real-provider compatibility and credential-bearing file access remain.
Even an allowlisted HOME, PATH, desktop bus or library path can expose local
resources or load code. A retained value may itself contain a secret.
The selection policy is not a security sandbox, redaction engine, DLP control
or production credential boundary.

REA-0 and REA-1 remain complete. REA-1.1 is partial; REA-2 through REA-4 have not
started. GO only for continued isolated evaluation. NO-GO for production
integration, unrestricted agent operation or secret-bearing operator hosts.
Main remains unchanged; no merge, PR, publication or deploy was performed.

**Next operational prompt:** Continue REA-1.1 by auditing the remaining direct
subprocess routes and the authority of explicit environment overrides. Trace
each environment producer, reduce inheritance only with a verified compatibility
contract, and validate synthetic secrets through real boundaries in a larger
disposable worker. Preserve main and report PASS/FAIL/NOT_TESTED, residual risks
and the real-provider matrix.
