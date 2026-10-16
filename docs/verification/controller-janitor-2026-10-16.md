# REA-1.1: janitor readiness and storage-owner loss

**Date:** 2026-10-16 UTC. **Decision:** PARTIAL / **NO-GO**.
Repository: `Brnegreiros/rea`, branch `fix/bcode-rea-1-1-containment`.
Parent: `0140bc2882db8a86639a366faa10dd969ce1a4ef`.
Main remains `6060de329de9f3636f63e24a2419847fd9d3f889`.

## Investigated and changed

The previous prototype exposed its request socket before the storage janitor
confirmed readiness. The janitor opened a parent PID after its own startup,
leaving an untested early-death interval. The controller now opens its own pidfd
before spawning the janitor and passes that stable reference plus a private
notification pipe. The janitor validates private storage ownership/modes and the
SQLite schema before acknowledging. A missing, malformed or absent acknowledgement
within two seconds fails closed, blocks the profile and reaps the child before
socket creation. This addresses the prior source-derived CP-R01 finding.

Detected janitor death denies proposal, approval and execution. During an active
capture, the controller detects that loss, stops its owned cgroup, closes/removes
raw handles and returns an incomplete outcome. These are measured interleavings,
not proof of every possible race or of a continuously healthy janitor.

A real acceptance run exposed an empty launch-counter read while its producer
truncated and rewrote the file. The producer now uses atomic replacement rather
than retrying or repairing reads. The counter remains an observer metric;
transactional approval consumption, not this metric, owns execution authority.
A concurrent reader stress test measures the actual private metric producer.

The janitor now takes an explicit immediate SQLite transaction before reading
and disposing its owned rows. Approval preflight runs before taking the decision
write transaction. This makes transaction ownership explicit and shortens that
write lock; it does not establish resilience to storage exhaustion. Private
janitor diagnostics retain only error types/SQLite error names for caught
retention failures; operator diagnostic handles are inventoried at disposal.

The acceptance producer also labels partial and declaration-only cases separately.
It no longer describes EA-23/EA-28 status declarations as real kernel-boundary
execution. No public REA source, dependency, workflow, package or license changes
were made in this stage. The experiment remains outside the published runtime.

## Validation and provenance

**Final catalogue: 20 PASS, 0 FAIL, 8 NOT_TESTED; exit 0.**

The incomplete cases remain EA-14, EA-16, EA-17, EA-18, EA-23, EA-25, EA-26 and EA-28. Their partial observations and remaining oracles are recorded per case in JSON.

**Additional regressions: 9 PASS, 1 FAIL, 0 NOT_TESTED; exit 1.**

| Case | Status | Measured boundary |
| --- | --- | --- |
| JR-01 | PASS | Janitor exits without acknowledgement; no socket or REA launch |
| JR-02 | PASS | Live child without acknowledgement; bounded startup timeout |
| JR-03 | PASS | Malformed acknowledgement rejected |
| JR-04 | PASS | Stopped child timed out and reaped |
| JR-05 | PASS | Parent SIGKILL before real janitor exec; inherited pidfd and injected-row expiry |
| JR-06 | PASS | Parent SIGKILL after readiness, before first request |
| JR-07 | PASS | Janitor SIGKILL after approval; next execution/approval/proposal denied |
| JR-08 | PASS | Janitor SIGKILL during real capture; owned family and raw run handle removed |
| JR-09 | FAIL | Raw intent/audit remain past deadlines after storage-owner loss |
| JR-10 | PASS | 1,000 atomic publications; concurrent whole-integer reads |

The metric reader observed 3,865 valid snapshots during 1,000 publications. Four Python files compiled; both unchanged MJS fixtures passed formatting and lint (zero warnings/errors). The parent REA build passed inside the VM. Full REA regression, native providers and complete SCA were not rerun.

Final catalogue timing: 139.19 s wall, 88.26 s user, 12.38 s system. Additional regressions: 45.42 s wall, 10.21 s user, 0.99 s system. These include their stated synthetic workloads and waits, not a controlled performance comparison. Model token usage was not measured.

The 28-case catalogue and the new regression suite are different result sets;
their denominators must not be merged or counted as a full security audit.
The historical definition catalogue and earlier runtime records remain unchanged.
The [machine-readable evidence](controller-janitor-2026-10-16.json) contains
case observations, tested file hashes, commands, exits, timings and disposal.

JR-01..JR-04 use privileged fault substitution of the child startup at the test
boundary, with real processes and file descriptors. They are not proof of a
malicious agent changing the launcher. JR-05 freezes the real janitor before
exec and kills its parent; a private row is injected by the operator to test
expiry despite that death. No request was admitted before readiness. JR-06..08
use the unchanged controller and Unix peers; JR-08 launches the real REA CLI and
synthetic target under Linux cgroups/namespaces. PID reuse itself was not forced.
The operator is automated UID-0 test orchestration, not human approval or IAM.

After verifying admission blocking/active-family cleanup, JR-07 and JR-08 terminate
their controllers in test cleanup. JR-09 then waits past the original deadlines.
It therefore measures janitor loss followed by controller termination; it does
not measure a controller kept alive throughout the expiry interval or simultaneous
loss. Those variants remain pending. The absence of a surviving expiry owner is
a failed control for the observed sequence, not evidence about every failure mode.

## Findings and proposed corrections

| Finding | Severity / status | Evidence and minimal next action |
| --- | --- | --- |
| CP-R01: admission before janitor readiness | High / corrected for tested startup cases | Private acknowledgement and inherited pidfd; JR-01..06. Preserve fail-closed startup. |
| CP-R03: expiry lost when the storage janitor dies | High / **FAIL**, open | JR-09 finds pending raw intent beyond 20 s and audit beyond 30 s. Blocking admission does not delete data. Establish an independent storage owner/deadline mechanism, bounded failure receipts and restart-safe ownership before another enablement decision. |
| CP-R04: observer counter publication race | Corrected for tested boundary | First full run failed EA-16 on an empty integer; atomic replacement plus JR-10 and a fresh real-workflow run. No durability claim is made for this observer metric. |
| CP-R05: unexpected blocked-profile development trial | Open diagnostic uncertainty | One trial had 14 FAIL after CONTROL_UNVERIFIED. The exact trigger was not recorded by that revision; later success does not establish its root cause. Transaction ownership and private failure-code diagnostics improve the boundary; controlled contention/fault tests are still required. |
| CP-R02: client read/rate limits | NOT_TESTED, open | Socket read deadlines, connection/concurrency budgets and flooding resistance are not certified. |
| Resource and sink-failure closure | NOT_TESTED, open | Memory/PID exhaustion, complete output/evidence quotas, missing enforcers, midrun full/disconnected sinks and forced cleanup failure remain pending. |

CP-R03 is not an expected successful negative test. It is a **failed required
retention assertion**, and the regression process exits 1. Conversely, an
intentionally disallowed operator registry must generate a FAIL/exit 1 with zero
REA launches; that separate negative-driver check is expected behavior and does
not cancel or hide CP-R03.

## Isolation, retention and disposal

Disposable Firecracker VM `sbx_pNcTTf5e9ZVrpPmgFGvr4od59SP1`: 4 vCPUs, 8 GiB, 512 outer PIDs, finite 45-minute timeout, persistent=false and no exposed ports/routes. Source/toolchain were root-owned and read-only to workers. Workers used UID/GID 1001, no effective capabilities, no_new_privs, mount/PID/network namespaces and per-family cgroups. Agent peer UID 1002 could not read private control/evidence files. The VM marker is an accident guard, not isolation proof.

Each admitted synthetic capture retained the existing one-CPU quota, 512 MiB family memory, 64 PIDs, 16 MiB writable tmpfs, 2 MiB file limit and ten-second external deadline. These bounds were configured and probed; this stage does not certify full resource-exhaustion behavior. Dependencies were acquired inside the VM with a narrow allowlist and npm lifecycle scripts disabled. The official Node archive checksum matched; Node 24.18.0/npm 11.16.0 and the unchanged lockfile were used. Outer network policy was deny-all for all project tests and remained deny-all at stop.

Whole-VM memory peak: 4,488,134,656 bytes (about 4.18 GiB), zero OOM/oom_kill events, peak 84 PIDs. Cgroup CPU at collection: 646.995901 s. API duration: 1176.800 s; active CPU: 697.907 s. These aggregate figures include provisioning, development trials, build and final tests.

Before stop, the collector found zero controller/worker/janitor processes, zero UID-1001 processes and zero owned capture cgroups. Thirty-seven private test stores were inventoried. Eight still had retained rows after failed expiry across the fault/development rounds; the final pending-loss store had one expired raw intent and five audit rows, while the active-loss store had no raw intent but ten expired audit rows. The normal final catalogue and negative-driver stores were empty after expiry. All stores, private diagnostics, marker and 13 socket handles were removed by the evaluation operator; this is recorded as operator disposal, not automatic-expiry success.

The transferred collected gzip matched SHA-256 `4baf7439a6946d5f6872b9172408bae3917cf6434a14c0c9ec5b501ddb5fb008`; all ten recorded experiment/package/lock/license hashes matched the local files. Lifecycle and command metadata were appended after transfer verification. API status is **stopped**, at 2026-10-16T01:37:44.513000+00:00; no persistent snapshot was requested.

Normal completed/error/cancelled captures remove raw run directories and clear
intent/hash/decision state on settlement. The normal controller-SIGKILL test
still tests a surviving janitor, with raw deadline 20 seconds and audit deadline
30 seconds. JR-09 separately disproves automatic expiry after janitor loss.

The evaluation operator inspected only synthetic captures and retained selected
facts, hashes and resource metadata. Raw databases, private logs, temporary
diagnostics, input copies and socket handles were inventoried and removed before
outer VM shutdown. Operator removal is a separate receipt and **does not turn
failed automatic expiry into PASS**. Neither logical removal nor VM shutdown
proves physical erasure or deletion of unobserved provider backups.

## Roadmap and next action

REA-0 and REA-1 remain complete; REA-1.1 remains PARTIAL. REA-2..4 have not started.
Production, unrestricted agents and platform integration remain NO-GO. No native
provider, real credential, main/upstream change, merge, package publication or
deploy occurred. Human ownership/readiness is not attested on the user's behalf.

Next correct CP-R03 at the storage-ownership boundary and reproduce JR-09 until
its real expiry assertion passes. Do not silently extend retention, auto-approve
new work, rewrite canonical Evidence or remove a failed test to obtain green
results. Then close cleanup-failure, resource and midrun storage-failure cases,
and investigate CP-R05 with controlled contention and bounded diagnostics.

**Next operational prompt:** Continue REA-1.1 by correcting independent raw/audit
expiry after janitor loss (CP-R03/JR-09), including pending intent, active capture,
controller restart and failed disposal. Validate actual deadlines and ownership
with synthetic data in a disposable VM; retain PASS/FAIL/NOT_TESTED and diagnostic
uncertainty. Preserve main; no platform integration, real credentials, native
providers, merge, publication or deploy.
