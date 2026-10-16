# REA-1.1: resource limits and active-storage failures

**Date:** 2026-10-16 UTC. **State:** experimental scope only; REA-1.1 PARTIAL,
production and unrestricted agents **NO-GO**.
Repository: `Brnegreiros/rea`; branch `fix/bcode-rea-1-1-containment`.
Parent: `ecea596a7ccb8a822f7b3483737e6c34205d04e4`.
Main: `6060de329de9f3636f63e24a2419847fd9d3f889`, unchanged.

## Findings and minimal corrections

| Finding | Operational priority / impact | Owning files and change |
| --- | --- | --- |
| RS-R01: output was redirected directly to files; the aggregate budget was checked after writes | HIGH: approved bytes could be exceeded before detection | `controller.py`, `CaptureSink` and `execute`: external pipe collector caps each write before storage; aggregate stdout/stderr budget is 1 MiB. Regular-file device/inode/link count/size must remain consistent |
| RS-R02: a terminal kernel limit event could occur between polls and worker exit | HIGH: an interrupted capture could lose the true resource-limit classification | `controller.py`, `kernel_snapshot`, `kernel_limit_hit`, `execute`: reconcile final memory/PID events; configure/read back whole-family OOM behavior, memory, swap, PIDs and CPU |
| RS-R03: SQLite transaction context did not close its file descriptor | MEDIUM: descriptor ownership depended on Python garbage collection, obstructing deterministic resource/storage recovery | `controller.py`, `connect_db`: explicit close in finally, including setup/commit errors; related observer DB helpers in `acceptance.py` and `janitor_acceptance.py` close the same way |
| RS-R04: setup and storage failures required one cleanup boundary | HIGH: failure before normal capture could leave an owned run without normal settlement | `controller.py`, `execute`: publish lease before setup, include setup in try/finally, stop/reap the worker and attempt disposal; unavailable audit/evidence blocks the profile; failed settlement is never VERIFIED |
| RS-R06: repeated execute preflight hashed the runtime while holding the SQLite writer transaction | HIGH: the short audit deadline hit SQLITE_BUSY and blocked valid concurrent capture | `controller.py`, `dispatch`: integrity preflight before writer lock; fresh approval checks and consume-before-launch remain atomic inside it; typed private SQLite error metadata preserves diagnosis |
| RS-R05: busy evidence deletion prevented removing an already empty cgroup | MEDIUM: an unrelated filesystem failure retained a stale empty process-family handle | `controller.py`, `dispose_unlocked`: stop/verify and release empty cgroup before raw deletion. Failed raw disposal still retains the run and lease and blocks admission |

These are prototype findings, not newly established vulnerabilities in every REA
provider. Public REA source, tests, workflows, dependencies, package/lockfile and
license are unchanged. No new dependency or production entry point was added.
The minimal alternative to post-write size sampling is a bounded external pipe
collector; increasing the old budget would not enforce it. Kernel events are
owned facts, not an inference from a target exit code. The per-run 2 MiB file
limit and 16 MiB writable work filesystem remain in place independently.

The fixtures in `fixture.mjs`/`prepare.mjs` are fixed, finite synthetic memory,
nonrecursive process and output loads. No request accepts commands, fault flags,
mount coordinates or arbitrary destinations. REA's owning scenario parser still
produces their contracts. The real compiled capture CLI executes each admitted
fixture. A privileged test provisioning hook mounts only the fixed owned raw
directory on a small tmpfs; storage errors come from Linux/SQLite, not mocked
return values. This is operator fault injection, not an agent capability.

## Executed cases

| Final suite | PASS | FAIL | NOT_TESTED | Exit |
| --- | ---: | ---: | ---: | ---: |
| Resources/storage (RS-01..05, SF-01..07) | 12 | 0 | 0 | 0 |
| Startup/loss regressions (JR-01..12) | 12 | 0 | 0 | 0 |
| Retention recovery (RR-01..04) | 4 | 0 | 0 | 0 |
| Original 28-case catalogue | 20 | 0 | 8 | 0 |

| New case | Oracle actually exercised | Result |
| --- | --- | --- |
| RS-01 | Finite memory allocation; actual cgroup OOM event, whole-family limit classification and verified family/raw disposal | PASS |
| RS-02 | Finite nonrecursive sleep children; actual denied PID creation, peak no greater than 64 and verified family/raw disposal | PASS |
| RS-03 | Actual REA capture with canonical `truncated=true`; workflow completion does not assert complete trace coverage | PASS |
| RS-04 | Actual capture exceeds external stream budget; exactly 1 MiB retained, incomplete/LIMIT_REACHED and verified disposal | PASS |
| RS-05 | Waiting fixture stopped by external deadline, bounded response and verified family/raw disposal | PASS |
| SF-01 | Audit DB disconnected before execution; zero CLI launches, no run ID and blocked profile | PASS |
| SF-02 | Audit DB disconnected after actual CLI launch; incomplete result, stopped family, blocked profile and post-recovery removal | PASS |
| SF-03 | Actual SQLite FULL under its 2,048-page quota during capture; fail closed and post-recovery removal | PASS |
| SF-04 | Output path replaced by privileged symlink; identity loss interrupts capture; external sentinel unchanged | PASS |
| SF-05 | Actual ENOSPC on 256 KiB evidence tmpfs; incomplete/cleanup FAILED, stopped family, retained run lease, verified retry after operator unmount | PASS |
| SF-06 | Actual read-only bind mount on audit DB during capture; incomplete/cleanup FAILED; operator restores writability and removes mount; no automatic unblock | PASS |
| SF-07 | Original deadlines unchanged; original request/decision/audit rows, raw runs, metrics and leases absent after expiry/recovery | PASS |

Measured memory peak was **536,870,912 bytes**, with
`oom=2`, `oom_kill=4` and `oom_group_kill=1`.
PID/task peak was **64**, with 51 limit-denial events;
the Linux PID controller counts threads as well as processes.
The output broker retained **1,048,576 bytes total**, including
stderr, and reported the cap reached. The truncation case privately observed
27,068 bytes of canonical JSON and preserved REA's truncation
metadata; no raw JSON was returned to the requesting client. ENOSPC was errno
**28** in the **EVIDENCE** stage, with
259,705 stream bytes retained before failure.
Final private audit errors were explicitly verified as SQLITE_CANTOPEN,
SQLITE_FULL and SQLITE_READONLY for SF-02/03/06.

The [machine-readable record](controller-resource-storage-2026-10-16.json) owns
case observations, timing, hashes, commands and disposal receipts. The original
28-case catalogue remains a definition artifact, and previous reports are
preserved. EA-14/16/17/18/23/25/26/28 remain NOT_TESTED for their complete criteria.
Narrow resource/storage PASS cases do not complete those broader oracles.

**Failure reporting is part of the oracle.** Audit loss/FULL/read-only failure
can prevent a truthful successful settlement even after the process family was
stopped. The response then remains cleanup FAILED and the profile blocked.
A busy raw mount retains ownership until operator recovery and an owner retry;
it does not become VERIFIED through a response rewrite or TTL renewal. RR-04
still demonstrates **FAIL for timely deletion under its persistent forced EBUSY
fault**, followed by verified late recovery. SF-05 does not certify deletion
while its busy mount remains in place. Provider backups and physical erasure are
not covered.

Development trials are retained separately. Initial resource/storage results
were 10 PASS / 2 FAIL. A focused repeat retained both failures. Explicit SQLite
closure and correct read-only fault restoration resolved SF-06; SF-05's next
trace identified the retained empty cgroup. Reordering owned cleanup resolved
that failure without abandoning failed raw ownership.

The next full catalogue run was 15 PASS / 8 FAIL / 5 NOT_TESTED: EA-15's real
concurrent execution first returned AUDIT_UNAVAILABLE, then the latched profile
caused dependent cases to fail. Three focused repeats with typed private SQLite
metadata reproduced SQLITE_BUSY/AUDIT_UNAVAILABLE three times. The second
execute performed expensive runtime/policy hashing inside BEGIN IMMEDIATE while
the active capture required a short audit-write deadline. Preflight now runs
before the writer transaction; the stored approval and consume remain checked
atomically inside it. This reduces the lock's work rather than weakening the
audit failure policy, extending retention or increasing its timeout. The typed
SQLite name is private metadata without query values, raw bytes or credentials.
After this correction, three equivalent focused repeats each produced exactly
one COMPLETED capture and one DENIED duplicate, with no SQLite error; the
complete suites were then rerun on the final source.
This diagnoses the current reproduced regression; it is not retroactive proof of
the unrelated earlier CP-R05 observation's root cause.

Two development read-only
mounts required explicit operator restoration/identified-controller termination
before normal unmount; that recovery is recorded separately from automatic
expiry. Final passes do not erase the failed observations.

Six Python sources compiled inside the VM; the two MJS files passed format and
lint. The parent runtime built with the pinned toolchain and unchanged lockfile.
No host execution of project code was used. Historical Frida/environment suites
were not rerun or counted as new results; their production sources were untouched.
No full SCA, native provider validation or human-readiness attestation occurred.

## Isolation, retention and disposal

Disposable Firecracker VM `sbx_MsaojsGxBbM6YWociRY44GuRLlH1`: 4 vCPUs, 8 GiB,
512 outer PIDs, 45-minute deadline, persistent=false and no exposed routes/ports.
Pinned image digest: `sha256:6ad1291a9fe7d243ee9f23626e6b08614a596431801c55e14cc5ee9d525f28d1`.
Dependencies were acquired only inside the VM with an acquisition allowlist and
npm lifecycle scripts disabled. Tests ran under outer deny-all egress; no
credential was injected. Node 24.18.0/npm 11.16.0/Python 3.14 were used.

Each worker had mount/PID/network namespaces, root-owned immutable inputs,
UID/GID 1001, zero effective capabilities, no_new_privs, one CPU quota,
512 MiB whole-family memory with swap disabled, 64 PIDs, 16 MiB writable work
storage, a 2 MiB per-file limit, 1 MiB private aggregate streams and ten-second
external execution deadline. The request peer was UID 1002; operator/control
state and both independent expiry owners remained outside worker namespaces.
This shares the VM kernel; it is not a separate microVM per capture or proof
against kernel exploits. The VM marker prevents accidental host invocation and
is not independent isolation evidence.

Raw intent expires 20 seconds after proposal; audit/metrics/leases expire at the
original 30-second audit deadline. No retry or operator fault restoration renews
those dates. Controlled raw FD closure, family termination, raw handle removal,
audit expiry and operator removal of empty control containers are distinct
observations. Failed-disposal ownership may outlive a deadline until verified
recovery; it is an open failed-deletion receipt, never permission to execute.
The derived report retains only selected synthetic observations and metadata.
Raw captures, databases and private diagnostics are not committed.

All **73 inventoried private stores** had zero requests/decisions/audit rows after
automatic expiry or recovery, and zero raw run handles, leases or per-run metrics.
There were no controller/worker/guard processes, UID-1001 processes, owned
cgroups or owned mounts. The operator then removed empty control containers,
private diagnostics, the VM marker and 58 socket handles. No expired data
rows required manual deletion in this final inspection. Privileged fault
restoration is separately recorded and was necessary before some owner retries.

The compressed export transferred with verified SHA-256
`857a07c090cfd5fa7741c612ebac6b827a54e9925f7a03e68e91e7633b3a78a2`.
All **12 recorded source hashes** matched the local copy, including the unchanged
package, lockfile and license. Lifecycle/commands were appended afterward.
API status is **stopped**, at **2026-10-16T12:59:07.549000+00:00**; persistent=false,
no persistent snapshot requested, deny-all retained. Logical handle removal and
shutdown do not certify physical media erasure or unknown provider backups.

| Final suite | Wall seconds | User CPU seconds | System CPU seconds |
| --- | ---: | ---: | ---: |
| Resources/storage | 88.56 | 23.34 | 2.92 |
| JR | 45.73 | 6.85 | 0.68 |
| RR | 124.24 | 6.90 | 0.57 |
| Catalogue | 122.75 | 75.43 | 8.58 |

These timings include child work and expiry waits. Aggregate guest peak memory
was 4,528,816,128 bytes (4.22 GiB), and peak PIDs/tasks 91.
The hierarchical memory events were oom=4, oom_kill=10,
oom_group_kill=3; these include the deliberate child-cgroup OOM tests.
Root-local events were not collected separately; these are not a count of
VM-wide failures. Guest cgroup CPU was 493.966903 s at collection.
API duration was 1854.196 s, active CPU 575.509 s.
Aggregate metrics include provisioning, build, development trials, final tests
and export. Model tokens were not measured; no controlled before/after
benchmark or arbitrary-target sizing claim is made.

## Residual risk and next stage

REA-0 and REA-1 remain complete. This bounded REA-1.1 resource/storage task is
complete for its listed oracles; REA-1.1 overall remains PARTIAL / NO-GO.
REA-2/3/4 are not started. Main/upstream are unchanged; there is no platform
integration, PR, merge, package publication, service installation or deployment.

Still NOT_TESTED: loss of both guards, a live hung guard, clock changes, VM/kernel
failure, whole control-filesystem exhaustion/unavailability (including inability
to persist a block/ownership record), persistent storage I/O hangs, abrupt-power
crash durability, uncontrolled artifact/backup copies, complete EA-18/26 coverage,
full SCA and native providers. The older CP-R05 contention diagnosis is unresolved;
a successful current regression is not proof of its root cause. A finite set of
synthetic filesystem faults cannot certify every storage failure.

Next: test loss/hang of expiry owners and whole-control-storage failure with
bounded, credential-free VM faults, preserving original deadlines and failure
ownership. Do not broaden execution authority or integrate into the platform.

Operational prompt: “Continue a REA-1.1 pelas falhas simultâneas ou travamento dos
guardiões e pela indisponibilidade do armazenamento de controle, com prazos
originais, posse de descarte e dados sintéticos em VM isolada. Preserve as
regressões e a main, sem integração, merge ou deploy.”
