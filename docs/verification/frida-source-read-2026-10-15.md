# REA-1.1 — Frida script-source acquisition

Date: 2026-10-15. Repository: [Brnegreiros/rea](https://github.com/Brnegreiros/rea).
Branch: `fix/bcode-rea-1-1-containment`.
Parent baseline: `2b7d59c0f1c4e291d177b4e3d29792e02ecbe247`.
Main baseline: `6060de329de9f3636f63e24a2419847fd9d3f889`.

**Finding F08: corrected and tested on the evaluation branch. REA-1.1 remains PARTIAL; production integration remains NO-GO.** No merge, publication, deployment, or integration is included.

## Problem, cause and change

The manager previously used `readFile(path, "utf8")` without file-type admission, a source-byte ceiling or cancellation during acquisition. A writer-less FIFO reproducer in the isolated VM did not return before a 1-second safety timeout (exit 124). This demonstrates a local availability failure, not arbitrary code execution or a sandbox escape.

`src/frida/FridaScriptSource.ts` now owns source acquisition and its error projection. The manager calls it before hashing, native `createScript` or message registration. It reuses existing `withRegularFile`, `readBoundedFileBytes`, `OwnedFileHandle` and `ArtifactResourceScope` mechanisms.

- File and inline inputs share a **4 MiB (4,194,304 byte)** source budget. Files are checked by descriptor metadata before content acquisition. This is an operational resource policy, not a Frida format maximum.
- The reader checks the byte ceiling through EOF instead of trusting the initial size. At most one overflow byte is read. Growth, observed identity replacement and metadata changes fail admission.
- Pipes, directories and devices are rejected without waiting for a FIFO writer. Caller-selected symlinks resolving to regular files remain supported.
- Existing Node UTF-8 replacement and BOM semantics are preserved. A second byte check after decoding prevents malformed UTF-8 expansion from bypassing the native-source budget.
- Cancellation is checked before acquisition, between real reads and before native effects. An in-flight OS read is awaited; cancellation does not abandon its descriptor.
- Failed descriptor cleanup is retained in the manager-owned scope. Subsequent source acquisition fails until cleanup succeeds. Shutdown retries retained handles, and errors retain cleanup attribution, including on cancellation.
- Source path and hash semantics remain intact. Script source is not added to Evidence.

The source-acquisition error projection was moved out of the already large load method rather than extending its branching. Unrelated legacy methods were left unchanged.

## Compatibility and alternatives

This deliberately changes admission: scripts above the source budget and non-regular inputs now fail. Larger scripts require a future reviewed budget change; no automatic override was added. The commit marks this compatibility change explicitly.

Using only `stat` followed by `readFile` would retain a path race and would not bound growth after admission. Adding a signal to `readFile` alone would not enforce file type or size. A promise race would return before owned I/O and cleanup completed. The chosen change reuses the existing descriptor and resource owners and does not introduce a new execution service.

## Executed verification

The final source hashes and retained logs are in [the evidence record](frida-source-read-2026-10-15.json). All five modified source/test/document hashes matched the local files after transfer from the worker. Documentation and this record were added afterwards; successful checks are not attributed to hypothetical later source edits.

| Check | Result | Actual scope |
| --- | --- | --- |
| Service tests | PASS: 54 | Instrumentation manager and service, 4.17 s |
| Filesystem boundary tests | PASS: 17 | New 14-case source reader suite plus existing 3 bounded-read cases, 0.536 s |
| CLI/MCP boundary tests | PASS: 28 | CLI, MCP schemas/redaction and lifecycle, 12.05 s |
| Total | **99 PASS, 0 skipped** | 7 test files, selected coverage |
| Typecheck | PASS, exit 0 | `npm run typecheck` |
| Build | PASS, exit 0 | `npm run build:cached`; 52.933 s; 2 executed tasks and 1 metadata cache hit |
| Formatter | PASS, exit 0 | Five changed source/test/document files |
| Lint | PASS with warnings, exit 0 | Four TypeScript files; 9 warnings, no errors |
| Baseline lint comparison | 12 warnings, no errors | Original manager and manager test from parent commit, same configuration |
| Whitespace | PASS | `git diff --check` |
| FIFO baseline reproducer | Reproduced | Original Node file reader blocked until external timeout |
| Native Frida instrumentation | NOT_TESTED | Bindings were simulated; no target attach, injection or script execution |
| Windows/macOS filesystems | NOT_TESTED | Linux VM only |
| Complete suite / full PR gate | NOT_TESTED | Selected gates only |

The new cases cover exact limits (including empty files), UTF-8 byte counting, decoding expansion, a sparse oversized file rejected with zero content reads, directory, FIFO, symlink-to-FIFO, character device, a regular-file symlink, pre-read and mid-read cancellation, growth bounded at limit + 1 byte, identity replacement, retained close failure, blocked subsequent acquisition, and manager shutdown retry. The manager test also verifies that a cancelled read does not call `createScript` and that a later valid load can proceed after clean cancellation.

The first added cancellation assertion incorrectly expected a projected `code` field on the internal tagged error; it was corrected to the actual `AnalysisCancelledError` contract. A transient syntax error during extraction of the error projection was corrected before final validation. These unsuccessful iterations are not counted as passing checks. The final gates above were rerun on the retained source hashes.

The build retains two existing `INEFFECTIVE_DYNAMIC_IMPORT` warnings. Lint warnings in large/complex legacy methods remain; the scoped extraction reduced the compared warning count from 12 to 9.

## Isolated worker and observations

A nonpersistent microVM in the separate `rea-readiness-lab` project ran with 2 vCPUs, 4 GiB memory, a 512-PID root-owned cgroup ceiling, bounded virtual disk and a 30-minute final lifetime ceiling. The host received no software installation. The image digest was:

`vercel/sandbox/node@sha256:6ad1291a9fe7d243ee9f23626e6b08614a596431801c55e14cc5ee9d525f28d1`.

Code ran as the exclusive UID/GID 1001 user with cleared supplementary groups, no effective capabilities and `no_new_privs=1`. Sudo escalation and outbound fetch probes were denied. Acquisition temporarily allowed only GitHub, nodejs.org and registry.npmjs.org; network returned to deny-all before project tests. No production credentials were supplied. npm dependency lifecycle scripts remained disabled, including optional Frida setup.

Node 24.18.0 and npm 11.16.0 matched the pins. The Node archive checksum matched the official HTTPS release listing (not an independent signature verification). Package manifest, lockfile and MIT license were unchanged. Lockfile SHA-256:

`0482085372c563c99b32519f51339eb280adc2bd83efdba6a8efd7cd4a49e9f0`.

At the evidence capture, cgroup peak memory was 4,163,096,576 bytes (about 3.88 GiB); CPU usage was 452.395 seconds. These are whole-worker observations across setup and all iterations, not per-test measurements or production sizing. There were no OOM events. Token usage was not measured. Deterministic byte-read assertions establish zero content bytes read for an initially oversized sparse file and at most 4,194,305 content bytes when a file grows beyond the limit.

Final process inspection found no evaluation-user processes. The worker `sbx_RCrkNZpARV2uqzdcqRlAhTtmmTpa` was stopped with persistence disabled, after 1,510.589 seconds; the control plane reported 478.799 active CPU seconds at shutdown. No exposed application route, deployment, snapshot, package publication or service installation was created.

The evidence JSON retains successful test/build/typecheck/format logs, FIFO reproducer result, diagnostic summaries for both lint runs, exact source hashes, command script, worker preflight, resource observations and shutdown metadata. Full verbose lint code excerpts were reduced to diagnostic headings and summaries, with hashes retained for the complete stripped logs.

## Residual risks and acceptance

**PASS for this source-admission correction on the branch.** Merge has not occurred, so main does not contain it.

The 4 MiB check does not limit transport allocation of an already-arrived inline string. Cancellation is cooperative and cannot forcibly interrupt every filesystem or native Frida call. Metadata checks detect observed change; they are not a filesystem snapshot or an adversarial concurrency proof. Native-provider behavior and cross-platform compatibility remain unverified.

Executing an accepted Frida script still grants the target process's capabilities. Authorization, host isolation, generic subprocess environment inheritance, external-provider SCA and evidence classification/retention remain separate open controls. No claim of complete security or production readiness is made.

REA-0 and REA-1 remain complete. REA-1.1 remains in progress; REA-2 through REA-4 are not started. The next recommended step is a scoped review of provider environment inheritance, preserving required runtime variables while excluding unapproved ambient credentials, with synthetic-secret boundary tests.

Next operational prompt:

> Continue REA-1.1 in Brnegreiros/rea. Recheck the branch and remote HEAD, preserve main, and audit provider subprocess environment inheritance. Identify required variables and credential exposure paths before proposing a minimal policy. Implement only evidence-backed safeguards with synthetic-secret tests in an isolated worker. Do not merge, publish, deploy or integrate. Report actual results, residual risks, roadmap and the next prompt.
