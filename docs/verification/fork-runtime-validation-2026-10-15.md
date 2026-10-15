# REA-1.1 — isolated runtime validation

Observed on 2026-10-15 UTC / 2026-10-14 America/Manaus.
Repository: https://github.com/Brnegreiros/rea
Tested revision: `930643577fa5f4c19d350a5c11eddad3e6c1ce0d`.
Main baseline, rechecked before the work: `6060de329de9f3636f63e24a2419847fd9d3f889`.
Branch: `fix/bcode-rea-1-1-containment`.

## Decision

**GO for continued bounded evaluation with synthetic fixtures in the observed isolated worker. NO-GO for production integration or unrestricted/untrusted target execution. REA-1.1 remains PARTIAL.**

This is scoped execution evidence for the prepared containment change. It is not a full security audit, the complete test suite, cross-platform certification, or permission to merge or publish.

## What ran

| Control / command | Result | Evidence and limit |
| --- | --- | --- |
| Locked source and dependency acquisition | PASS | Public clone matched the tested SHA; unchanged lockfile; npm lifecycle scripts disabled |
| Pinned toolchain | PASS | Node 24.18.0; npm 11.16.0 |
| Launch-boundary / release metadata source tests | PASS | 27 tests in 3 files, 1.22 s |
| `npm run typecheck` | PASS in 4 GiB worker | Exit 0; first attempt in 2 GiB worker was killed with an OOM event |
| `npm run build:cached` | PASS | Exit 0, 3 tasks executed without prior cache, 53.103 s; remote cache disabled |
| Focused security and workflow tests | PASS with platform skip | 179 passed, 1 skipped, 7 files, 9.57 s |
| Changed-file formatting | PASS after formatting | 14 files checked; two formatting-only corrections |
| `git diff --check` | PASS | No whitespace errors |
| Real browser startup and DOM fixture | PASS, compatibility probe | Chromium Headless Shell 145.0.7632.6 / revision 1208; one launch; sandbox requested; expected title rendered |
| Renderer kernel observations | PASS for this process | UID 1001, NoNewPrivs=1, Seccomp=2; renderer user namespace differed from harness namespace; no `--no-sandbox` observed |
| Internal `chrome://sandbox` diagnostic | NOT_TESTED | Headless Shell rejected that internal URL |
| Synthetic redaction sink | PASS for selected projection | Explicit synthetic value and transport credentials absent from serialized selected sink |
| Owned process and browser profile cleanup | PASS | Selected process tests passed; final worker scan found no processes for the evaluation user and no scenario profiles |
| Full test suite, MCP end-to-end smoke, all providers | NOT_TESTED | No claim of coverage beyond the selected files |
| Native module resolver with a real browser | NOT_TESTED | Its 10 mock-based tests passed; no real module-resolution scenario was run |
| macOS/Windows/Android runtime | NOT_TESTED | Platform-option mocks are not native OS evidence |

Total: **206 passed, 1 skipped**, across 10 distinct test files. The skipped case is macOS-specific native ownership preparation in `tests/boundary/process/providerProcess.test.ts`; it was not applicable to this Linux worker.

Source tests:

- `src/browser/PlaywrightScenarioBrowser.test.ts`: 12 passed.
- `src/browser/modules/NativeModuleResolver.test.ts`: 10 passed.
- `tests/conformance/releaseConfiguration.test.ts`: 5 passed.

Focused security tests, run with `npm run test:focused --` and the exact paths:

- `src/browser/history/CaptureRedaction.test.ts`: 22 passed.
- `src/process/LinuxResourceLimits.test.ts`: 5 passed.
- `src/process/ProviderProcessOutput.test.ts`: 6 passed.
- `tests/boundary/filesystem/releaseRecovery.test.ts`: 9 passed.
- `tests/boundary/filesystem/releaseWorkflow.test.ts`: 31 passed.
- `tests/boundary/browser/webSourceMapFetcher.test.ts`: 81 passed.
- `tests/boundary/process/providerProcess.test.ts`: 25 passed, 1 skipped.

The build reported two `INEFFECTIVE_DYNAMIC_IMPORT` warnings concerning `composition/binary` and `dotnet/ManagedStaticProvider`. They did not fail the build and were not changed in this scope.

## Worker observations and acquisition

A separate Vercel project, `rea-readiness-lab`, was created solely to associate temporary sandboxes. It has no Git connection, deployment, domain, or supplied production variables. No existing B•Code project was used or changed. Project creation is not an application deployment. The empty project remains available for later evaluations; running compute was stopped.

Both workers were Firecracker-based, nonpersistent microVMs, with no exposed application ports or shared host mounts. Image digest:

`vercel/sandbox/node@sha256:6ad1291a9fe7d243ee9f23626e6b08614a596431801c55e14cc5ee9d525f28d1`

The default worker account had passwordless sudo. It was not used to execute the project. An exclusive `rea` user (UID/GID 1001), with cleared supplementary groups, empty supplied environment, no effective capabilities and `setpriv --no-new-privs`, ran project commands. The operator home was inaccessible to that user. Sudo elevation was probed and denied. No host Docker socket was exposed.

The VM memory boundary, complete process namespace and bounded virtual disk contain descendants. The first worker had 1 vCPU / 2 GiB; the validation worker had 2 vCPUs / 4 GiB. The root-owned cgroup PID ceiling was set to 512 and was not writable by the evaluation user. The disk was approximately 64 GiB, and the validation session had an external 20-minute lifetime ceiling. Individual execution commands also had deadlines. These values describe this audit worker; they are not production sizing recommendations.

The initial typecheck in 2 GiB printed `Killed`; `memory.events` recorded `oom_kill=1`. Its orchestration status did not supply a reliable final exit code. It is recorded as a resource-limited failed attempt, not a TypeScript diagnostic. The 4 GiB worker completed typecheck and build with exit 0 and ended with zero OOM events.

Network was denied at creation and during project tests. Bounded acquisition windows allowed only GitHub, the npm registry and nodejs.org, then Ubuntu archives and the browser distribution endpoints. A redirect from the Playwright CDN to storage.googleapis.com was initially blocked; that explicit destination was added for browser acquisition. Network was returned to `deny-all` before browser execution. Benign outbound fetch probes failed under the deny policy. No application target was executed during acquisition.

The Node archive SHA-256 matched the official HTTPS SHASUMS256 listing:
`783130984963db7ba9cbd01089eaf2c2efb055c7c1693c943174b967b3050cb8`
(`node-v24.18.0-linux-x64.tar.gz`). This was a checksum comparison, not an independently verified release signature.

Lockfile SHA-256 remained:
`0482085372c563c99b32519f51339eb280adc2bd83efdba6a8efd7cd4a49e9f0`.

Ubuntu's signed distribution repositories supplied browser runtime libraries inside the disposable VM. npm lifecycle scripts remained disabled. No Frida/native-provider installation script or upstream installer was executed.

## Browser compatibility limitation

The image contains Ubuntu 26.04, which pinned Playwright 1.58.2 does not officially recognize for this browser download. The normal download failed. A separately recorded compatibility probe used `PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64` **only during acquisition** to select the pinned Linux browser binary. This override did not disable Chromium sandboxing or change repository dependencies.

The actual REA launcher opened a blank owned profile with `chromiumSandbox: true`; a synthetic in-memory DOM was rendered. Linux procfs observations found the renderer in user namespace `user:[4026532180]`, distinct from harness `user:[4026531837]`, with Seccomp=2 and NoNewPrivs=1. These are process observations, not proof against every sandbox escape or certification of Ubuntu 26.04 support. Repeat the smoke on an officially supported, pinned operating system before homologation.

The probe originally combined browser startup with the unsupported internal `chrome://sandbox` page. Its diagnostic was separated from startup, and the corrected probe was rerun. The final retained JSON distinguishes startup PASS from internal-diagnostic NOT_TESTED.

## Evidence retention and disposal

Retained evidence includes the full typecheck, build, focused-test and formatter logs; browser smoke JSON; OS package inventory; source-test output; the final probe source; and a manifest with worker IDs and observations. The standalone evidence archive accompanies this report.

Runtime evidence bundle SHA-256:
`3026c9dc5ce8f9693deecf9c06e9ed885f447158203f12b8194854b2cc29f544`.

Runtime browser JSON SHA-256:
`256beb56dffebb2f8dfc1b09c49c9ce87d33d9f9746acf63c2cf375ed73e644d`.

Worker sessions:

- `sbx_UTPIU0DCzg3jabSHKHc2E1VZHHm1`: stopped; 339.677 s; 1 vCPU / 2 GiB.
- `sbx_GGoodOq3WhMvAbJIV9bsKqs3uPZH`: stopped; 925.331 s; 2 vCPUs / 4 GiB; persistence disabled.
- The validation worker ended with no evaluation-user processes, no owned scenario profiles and no OOM events.

Changes following the tested commit are formatting-only in the existing test, formatting and evidence-status updates in the readiness document, plus this evidence report. Production source and dependencies are unchanged in this follow-up commit. Successful observations on the tested ancestor do not imply that unexecuted later source changes are covered.

## Remaining risks and roadmap

| Item | State after this round | Next requirement |
| --- | --- | --- |
| Fork release/publication guards | Prepared and structural regressions PASS | Review before any authorized merge; main still lacks these changes |
| Browser defaults | Mock regressions and selected Linux runtime observations PASS | Supported OS smoke; retain explicit Android/opt-out exclusions |
| Generic provider environment inheritance | OPEN | Explicit policy and synthetic-secret process-boundary tests |
| Tool authority / Frida and debugger operations | OPEN | Enforce allowed capabilities outside model-generated context |
| Frida source-file read admission and bounds | OPEN | Focused fix for regular files, size bounds, cancellation and cleanup |
| External-provider SCA | PARTIAL | Inventory and audit applicable language/native dependency graphs; no blanket CVE clearance |
| Data classification, retention and authorization | OPEN | Operational policy and selected sink / MCP validation |
| Cross-platform and all-provider execution | NOT_TESTED | Separate isolated, applicable OS/provider lanes |
| Supported evaluation OS | OPEN | Pinned supported image and repeatable acquisition |
| Production readiness | NO-GO | Resolve blocking risks and obtain later specific authorization |

REA-0 and REA-1 remain complete. REA-1.1 remains in progress, with isolated validation of the containment change now recorded. REA-2, REA-3 and REA-4 have not started.

Recommended next action: address Frida source admission and bounded reads in a focused branch change, with filesystem boundary and cancellation tests in an isolated supported worker. Continue external-provider SCA and authority-policy work before considering integration.

Operational prompt:

> Continue REA-1.1 in Brnegreiros/rea. Recheck branch, remote HEAD and main without changing main. Use this runtime report as scoped evidence. Inspect the Frida source-file admission boundary and implement the smallest justified regular-file, size and cancellation safeguards with relevant tests in a verified isolated worker. Preserve upstream, license and source semantics; do not merge, publish, deploy or integrate into B•Code. Report actual tests, residual risks, roadmap and the next prompt.
