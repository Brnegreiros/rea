# REA-1.1: independent retention recovery

**Date:** 2026-10-16 UTC. **State:** experimental scope only; REA-1.1 PARTIAL,
production and unrestricted agents **NO-GO**.
Repository: `Brnegreiros/rea`; branch `fix/bcode-rea-1-1-containment`.
Parent: `9ddc190e470f503741a70334e5574cb76dece583`.
Main: `6060de329de9f3636f63e24a2419847fd9d3f889`, unchanged.

## Problem, cause and correction

The [previous record](controller-janitor-2026-10-16.md) measured JR-09 FAIL:
pending raw intent and audit survived their deadlines when the single janitor
was killed and the controller subsequently terminated. Admission blocking
prevented another run but supplied no surviving expiry owner.

The minimal prototype correction adds one independent standby process. Both
guards inherit the controller's stable pidfd and must confirm private storage
readiness before the request socket is exposed. Separate private pipes identify
the lifetime of the exact peer; the controller closes every parent copy before
admission. EOF or controller death retires and blocks that boot. The standby
promotes on failure; it never admits work or renews an approval.

A per-boot lifetime flock assigns one guard cleanup ownership. Both use the same
expiry implementation, rather than maintaining competing cleanup policies.
The active owner disposes controlled raw copies on retirement and removes audit
at its existing deadline. The standby derives remaining time from the stored
original deadline when taking over; the stable-clock interleavings are tested,
not clock rollback or VM resumption. Denials tied to an existing request use its
original audit deadline instead of granting a fresh 30 seconds.

A separate bounded flock serializes guard/controller removal of the same owned
run handles. Run leases are published atomically, so recovery does not read a
partly written JSON lease. If disposal fails, the profile stays blocked, raw
intent/hash and executable approval are cleared, and the opaque run/owner receipt
and lease remain. The active owner retries. Audit expiry does not silently drop
failed ownership. That minimal incident receipt is intentionally retained while
deletion is unverified; it is a failed-retention outcome, not an extension of
permission to execute or a claim that remaining raw copies were erased.

A repeated real capture also found a settlement race: the surviving owner could
stop the worker between the controller's liveness check and worker.poll(). The
controller could then return FAILED/NONE despite observed guard loss. Settlement
now rechecks both guards before classifying the response and marks the result
INCOMPLETE/CONTROL_UNVERIFIED. JR-08 exercises that real producer boundary.
The dependent expiry test records its stores at setup, so a response assertion
cannot silently remove its retention scenario. Failed development observations
are retained separately from the final run.

The alternative of restarting the only janitor from the controller was rejected:
it does not cover the already measured sequence in which both are gone.
No installed service, IAM integration, platform gateway, arbitrary-command API or provider integration
was added. The processes live only inside the disposable evaluation VM. Public
REA source, workflows, dependencies, package/lockfile and license are untouched.
The experiment remains outside the published package/runtime.

## Results and verification boundaries

| Final suite | PASS | FAIL | NOT_TESTED | Exit |
| --- | ---: | ---: | ---: | ---: |
| Original 28-case catalogue | 20 | 0 | 8 | 0 |
| Startup/loss regressions (JR-01..12) | 12 | 0 | 0 | 0 |
| Retention recovery (RR-01..04) | 4 | 0 | 0 | 0 |

**JR-09 changed from FAIL to PASS for its tested fault sequence.** The catalogue
and extra suites have different oracles; do not merge denominators into a claimed
full security audit. EA-14, EA-16, EA-17, EA-18, EA-23, EA-25, EA-26 and EA-28
remain NOT_TESTED for their complete criteria, despite partial observations.
Their remaining requirements are retained in the per-case JSON. The narrower
RR-04 deletion-failure result does not by itself complete all EA-16/EA-25 paths.

Five Python files compiled. Both unchanged MJS fixtures passed formatting and
lint (zero warnings/errors). The baseline REA runtime built inside the VM.
An intentionally disallowed operator registry produced the expected negative
smoke FAIL/exit 1 with zero REA launches; it is not an acceptance failure.

The first repeated run exposed JR-08's settlement race and a dependent JR-09
setup failure (10 PASS / 2 FAIL). Those observations remain in the JSON. After
the producer classification/setup correction, the complete final run passed as
above. Earlier successful tests were not used to overwrite the failed trial.

The [machine-readable record](controller-retention-2026-10-16.json) owns the
case observations, exits, hashes, timing and disposal receipts. The historical
28-case definition catalogue and previous failed runtime records remain intact.
An acceptance PASS means its stated oracle, not general security certification.
Partial cases remain NOT_TESTED; declaration-only cases are not Linux tests.

| Test | Boundary actually exercised |
| --- | --- |
| JR-01..04 | Real children/FDs with privileged primary-startup fault substitution; no socket or REA launch |
| JR-05..06 | Early and post-readiness controller death; private operator-injected row is explicitly distinguished from an admitted request |
| JR-07..09 | Primary SIGKILL, admission block, active CLI interruption and original-deadline expiry with surviving standby |
| JR-10 | Actual private counter producer and concurrent reader; observer metric only |
| JR-11..12 | Real standby child without acknowledgement / malformed acknowledgement; startup denies and reaps both children |
| RR-01 | Primary loss with controller alive throughout original raw/audit expiry; zero REA launches |
| RR-02 | Standby loss then controller termination; primary retains expiry ownership; zero REA launches |
| RR-03 | Real active REA CLI; primary and controller SIGKILL, surviving standby cleanup, restart before audit expiry, blocked replay and unchanged deadlines |
| RR-04 | Real EBUSY from an operator-created bind mount, failure receipt/lease and block retained past deadline, operator unmount and owner retry/recovery |

JR startup substitutions are privileged test orchestration, not a claim that the
agent can replace the launcher. Other listed process/namespace/CLI interactions
use the real prototype, kernel peer credentials and fixed synthetic fixtures.
All operator approvals are automated UID-0 orchestration, not human review or
production authority. Stable pidfds and private pipe identities are structural;
PID reuse itself was not forced.

**RR-04 distinction:** timely deletion under the forced EBUSY fault is **FAIL**.
Its test PASS requires truthful failure reporting, continued ownership, blocking
and verified recovery. Raw files may remain in the busy owned directory until
operator recovery. The test does not pretend every filesystem failure can be
made to meet a deadline. Minimal failed-deletion ownership is retained and later
removed after successful retry. Unknown backups and physical media remain
outside the proof.

## Isolation, performance and final disposal

Disposable Firecracker VM `sbx_LD66CKUaZLgTlGnW4LuHZdLvtM0Y` had 4 vCPUs, 8 GiB, 512 outer
PIDs, a finite 45-minute timeout, persistent=false and no exposed ports/routes.
Dependencies were acquired inside the VM using an acquisition allowlist; npm
lifecycle scripts were disabled. The official Node archive checksum matched;
Node 24.18.0/npm 11.16.0 and the unchanged lockfile were used. Project tests ran
under outer deny-all egress. No credential was injected into the VM.

The existing capture profile used root-owned immutable input/runtime mounts,
UID/GID 1001, zero effective capabilities, no_new_privs, mount/PID/network
namespaces and a bounded cgroup. The request peer used UID 1002. Guards/control
state remained outside the worker namespaces. This is a shared-kernel prototype
inside an outer VM, not a separate microVM per capture or kernel-exploit proof.
The VM marker is only an accidental-host-execution guard.

Configured capture limits remain one CPU, 512 MiB whole-family memory, 64 PIDs,
16 MiB writable tmpfs, 2 MiB per file and a ten-second external deadline. Complete
exhaustion coverage is still pending. Raw intent has a 20-second deadline and
audit a 30-second deadline; loss-triggered cleanup occurred before raw expiry
in the covered successful-removal cases. RR-01..03 checked the original audit
deadline without renewal. RR-04 preserves an explicit failed-deletion receipt
past the deadline, followed by operator recovery and verified late removal.

Final timings (bash time, includes waits/child work): catalogue 87.78 s wall,
38.58 s user, 6.79 s system; JR suite 41.61 / 2.77 / 0.64 s; RR suite
122.49 / 2.58 / 0.59 s. The counter producer had 1,000 publications and 3,672
concurrent valid reads. Model token usage was not measured. These are not a
controlled before/after benchmark or arbitrary-target sizing evidence.

Whole-VM peak memory was 4,708,794,368 bytes (about 4.39 GiB); OOM and oom_kill
were zero. Peak PIDs: 86. Cgroup CPU at collection: 187.172825 s. API duration:
1246.922 s; active CPU: 227.703 s.
Aggregate metrics include provisioning, build, development and final runs.

All 46 inventoried stores had zero requests, decisions and audit rows after
automatic expiry/recovery, and zero raw run handles, leases or per-run metrics.
No controller/worker/guard process, UID-1001 process, owned cgroup or busy mount
remained. The operator then removed empty control containers, private diagnostic
copies, VM marker and 22 socket handles. Recovery unmounting is distinguished
from the owner performing its later data cleanup. No expired data rows required
manual deletion in this final inspection.

The collected gzip transferred with verified SHA-256
`8fef786da43d16f48c57cc55bd68a43c0937e603024f00423482912e0e2872f9`; all eleven recorded file hashes matched the
local copy. Lifecycle/commands were appended after that verification. API status
is **stopped**, at 2026-10-16T02:38:34.515000+00:00; persistent=false, deny-all retained and no persistent
snapshot requested. Logical removal/shutdown is not physical erasure proof.

Data was synthetic throughout. No credential was transferred into the VM; the
controller/worker environment is explicitly constructed. The request UID cannot
read the private DB, diagnostic handles or raw capture. Selected synthetic facts
and metadata are retained in this audit; raw databases, captures and diagnostic
copies are not committed. Control files/empty lock handles and private diagnostic
containers are inventoried evaluation artifacts removed before VM shutdown;
not every control-directory pathname has a per-request TTL.

## Residual risk, roadmap and next action

CP-R03/JR-09 is corrected for the observed single-primary-loss sequence and the
newly listed variants. Failed-disposal ownership is now verified for one real
busy-mount fault, not every provider or storage failure.

Both guards dying, a live but hung guard, VM/kernel failure, clock uncertainty,
complete memory/PID/output quotas, midrun full/disconnected audit/evidence sinks,
unknown copies/backups and general native providers remain NOT_TESTED. The prior
CP-R05 blocked-profile trial still lacks a proven root cause; an explicit writer
transaction is not retrospective proof. Socket read/rate/concurrency budgets
(CP-R02), full SCA, derived-report authorization and independent human readiness
remain pending. No production readiness claim follows from this recovery.

REA-0 and REA-1 remain complete. REA-1.1 remains PARTIAL. REA-2..4 have not started.
No main/upstream change, merge, package publication, deploy, real credentials or
B•Code integration occurred. Human ownership/readiness is not attested.

Next close the configured resource limits and midrun storage-failure oracles with
bounded synthetic faults. Keep the new ownership/expiry regressions in that
validation and investigate contention explicitly; do not widen the fixture API.

**Next operational prompt:** Continue REA-1.1 with bounded memory/PID/output tests
and audit/evidence storage failures during a synthetic Linux capture. Verify
external stop, incomplete outcome, retained cleanup ownership and original
retention deadlines; retain JR-09 and RR-01..04 regressions. Investigate CP-R05
without inferring its cause from a later PASS. Use a disposable isolated VM;
preserve main, no platform integration, real credentials, native providers,
merge, publication or deploy.
