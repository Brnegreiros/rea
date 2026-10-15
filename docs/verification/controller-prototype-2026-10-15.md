# REA-1.1: isolated external-controller prototype

**Date:** 2026-10-15. **Decision:** prototype PARTIAL; production and unrestricted
agents remain **NO-GO**. Repository: `Brnegreiros/rea`.
Branch: `fix/bcode-rea-1-1-containment`.
Parent: `fd886f8c9e16f50385dbbab57edf1f147f913d05`.
Main remains `6060de329de9f3636f63e24a2419847fd9d3f889`.

## Implementation and scope

The [experimental implementation](../../experiments/execution-controller/README.md)
is separate from `src/`, the CLI/MCP registration and the published package.
It adds no dependency, platform integration, network API or installed service.
The only admitted workflow is the actual existing `capture-process` CLI with
seven operator-provisioned synthetic Linux fixtures. There is no arbitrary
command or arbitrary environment-input API.

The controller resolves the parser-derived plan and keeps it in a private
SQLite database. `SO_PEERCRED` supplies the Unix client's actual UID: 1002 is
the request role; UID 0 is the operator role. Caller approval flags or claimed
identities cannot replace that channel. The operator reviews the complete
private plan and approves its digest for one bounded execution. A transaction
records approval consumption before launch. Source/fixture identities,
environment maps, worker and policy data are bound to that plan.

The test operator is automated orchestration under UID 0, authorized only for
these curated fixtures. This verifies OS role separation, not human review,
human identity management or the authority of an autonomous B•Code agent.
The startup VM marker is an accidental-host-execution guard; it is not proof
of isolation. Actual observations are recorded separately.

## Isolation actually observed

One disposable Firecracker VM hosted the privileged test controller. Its capture
workers used fresh mount, PID and network namespaces inside that VM. The
controller and storage janitor stayed outside those namespaces and their
filesystems. Each worker ran the project and target as UID/GID 1001 with empty
effective capabilities and `no_new_privs`; its kernel probes and target fixture
checked immutable input access, private-control invisibility and blocked network.

This is a shared-kernel Linux namespace prototype inside an outer VM, not a
dedicated microVM per capture or a kernel-exploit resistance claim. The outer VM
protected the operator host. No target/providers ran on the operator's host.

| Bound | Observed test configuration |
| --- | --- |
| Outer VM | 4 vCPUs, 8 GiB, 512 PIDs, finite session timeout, persistent=false, no exposed ports |
| Runtime | Node 24.18.0, npm 11.16.0, Python 3.14 stdlib; pinned image digest and unchanged npm lockfile |
| Input closure | Root-owned immutable source/runtime/input mounts; private root-owned host parent directories; critical-file regularity/content/inode checks |
| Capture family | One CPU quota, 512 MiB memory, 64 PIDs, no swap |
| Writable target storage | 16 MiB work tmpfs and 2 MiB per-file write bound |
| Time | Ten-second external run deadline, shortened by approval expiry |
| Network | Namespace with no external interface; outer firewall deny-all during execution |
| Output | Private stdout/stderr files, bounded file writes and aggregate evidence policy; no raw bytes in agent result |

Dependencies were acquired only inside the VM using an acquisition allowlist;
npm lifecycle scripts were disabled. The runtime archive matched its official
checksum. The build used the parent REA revision; no core source was modified.
Native Frida, devices, debuggers and real credentials were not used.

## Acceptance results

The [evidence record](controller-prototype-2026-10-15.json) contains the final
case-specific observations, source hashes, commands, resource metadata and
disposal evidence. The original [28-case catalogue](execution-authorization-acceptance-2026-10-15.json)
is the acceptance specification; its initial NOT_TESTED fields remain historical.

**Final result: 20 PASS, 0 FAIL, 8 NOT_TESTED.**

| Case | Status | Observation / remaining scope |
| --- | --- | --- |
| EA-01 | PASS | Real CLI Evidence, explicit/ambient canaries, private output and cleanup |
| EA-02 | PASS | Missing/self/copy approval denied before REA launch |
| EA-03 | PASS | Caller identity/authority claims denied; kernel role owns authority |
| EA-04 | PASS | Ten bound command/scenario mutations denied |
| EA-05 | PASS | Base/internal/explicit/host-probe map mutations denied |
| EA-06 | PASS | Source, worker, policy/limits identity mutations denied |
| EA-07 | PASS | Changed fixture and symlink denied; target input/import writes and network blocked |
| EA-08 | PASS | Duplicate/malformed JSON and unsupported fields denied with private audit |
| EA-09 | PASS | Empty/absent/case-sensitive fixture values and generated ownership ID observed |
| EA-10 | PASS | Caller attempts to select internal/config/ownership inputs denied |
| EA-11 | PASS | Caller loader/path/display overrides unavailable in the fixed profile |
| EA-12 | PASS | Unknown data/input channels and caller classification denied; no real credential scan |
| EA-13 | PASS | Native/device/attach/update/shell/remote/elevation profiles denied |
| EA-14 | NOT_TESTED | Restart/crash evidence is collected by EA-24; ambiguous consumed retry is covered by EA-15. Trusted-clock uncertainty is not injected here. |
| EA-15 | PASS | Two actual concurrent clients caused one launch; consumed retry denied |
| EA-16 | NOT_TESTED | Controller death is separately measured by EA-24; forced cleanup-failure retention/ownership branch is not dynamically certified. |
| EA-17 | NOT_TESTED | Actual worker non-root/capability/filesystem/network probes run on positive captures; each missing CPU/memory/PID/disk/network enforcement is not independently fault-injected. |
| EA-18 | NOT_TESTED | Finite disk/file and CPU fixtures executed; memory/PID exhaustion and global evidence-quota failure are not stress-tested. Complete resource case remains NOT_TESTED. |
| EA-19 | PASS | Unsupported tools/routes denied; request UID could not read/invoke the host checkout |
| EA-20 | PASS | Known raw canaries stayed out of agent response and audit table |
| EA-21 | PASS | Sensitive-input journal placeholder distinguished from retained target echo |
| EA-22 | PASS | Export destinations rejected; live raw-file read by requesting UID returned EACCES |
| EA-23 | NOT_TESTED | Separate approved derived-report workflow and transformation ledger are not implemented; raw Evidence is not rewritten. |
| EA-24 | PASS | Live controller SIGKILL, independent cleanup/expiry and restart replay denial |
| EA-25 | NOT_TESTED | Blocked-profile denial is real; unknown provider backups, failed deletion receipts and cleanup failures are not fully injected. |
| EA-26 | NOT_TESTED | Prelaunch audit unavailability exercised. Midrun full/disconnected audit and evidence sinks are not certified; NOT_TESTED for the complete case. |
| EA-27 | PASS | Private-state/role boundary and real target namespace probes observed |
| EA-28 | NOT_TESTED | No independent release/human-attestation gate is implemented. Partial catalogue and automated operator tests cannot establish readiness. |

A PASS refers to the narrow stated fixture/socket/kernel oracle. Cases with
partial observations remain NOT_TESTED; successful subcases are not promoted
to full acceptance. Binding substitutions used privileged fault injection into
the private stored intent, in addition to real unprivileged peer denial tests.
They do not demonstrate that the requesting client can alter controller state.

Case EA-24 killed the controller with SIGKILL during a live run. The independent
janitor stopped the owned cgroup, removed the raw run handle, cleared raw intent/
digest/decision rows, expired the request/audit metadata and denied replay after
restart. These are observations of controlled logical copies, not physical
media erasure or proof about unknown provider backups.

## Retention and disclosure

Pending intent had a 20-second raw deadline and 30-second audit deadline.
Normal/error/cancelled runs removed their raw captures at settlement, before
those maximum deadlines. The requesting UID was denied an actual raw-file read
while that file existed. Raw export, traversal destinations and report requests
were rejected by the fixed protocol. A separate approved derived-report workflow
is not implemented; EA-23 remains NOT_TESTED.

The privileged acceptance observer inspected synthetic raw captures for the
requested audit and kept only selected booleans, integrity observations and
resource metadata in the retained report. Failed development smokes could save
a private diagnostic file; that temporary copy is included in final cleanup.
No raw capture, intent database, provider project or operator credential is
committed. Canonical REA Evidence bytes and identities were not rewritten.

Test coverage distinguishes marked scripted input placeholders from target
echoes that remain in private terminal evidence. No blanket redaction or
secret-free guarantee is inferred from either base filtering or a sensitive flag.

## Validation, resources and disposal

Build of the parent revision, Python compile checks, MJS formatting and selected
MJS lint were executed in the VM. The final acceptance driver evaluates every
catalogue ID and exits nonzero on a FAIL; NOT_TESTED cases remain explicitly
pending. A complete REA regression suite or SCA was not rerun for this experiment.

Development smokes initially found unreadable minimal OpenSSL/account files and
an unreadable scenario-directory mount caused by the controller's private umask.
Explicit minimal-file/directory modes corrected the producing setup; the worker
now probes scenario readability before launching REA. A successful smoke and
subsequent complete runs are recorded separately from those failures.

Final worker: `sbx_K15U3lAdq8ccCI8IV6tycc7kPo4t`. API status **stopped**, persistent=false,
network deny-all retained, no exposed routes. Stopped at
2026-10-15T23:13:23.315000+00:00.
API wall duration: 2683.681 s; active CPU: 590.640 s.
Whole-VM memory peak at collection: 4,467,425,280 bytes (about 4.16 GiB),
with zero OOM/oom_kill events and a peak of 84 PIDs.
Cgroup CPU at collection: 536.121055 s. Final acceptance command: 81.75 s wall,
33.20 s user and 5.52 s system. Format: PASS, two MJS files. Selected lint:
zero warnings/errors. Three Python files compiled. Final driver exit: 0.
An intentionally disallowed registry generated an expected FAIL and exit 1,
with zero REA launches; that negative gate is not counted as an acceptance FAIL.

Nine private test stores had zero request, decision and audit rows after expiry,
and zero raw run handles. No controller/worker/janitor process or owned capture
cgroup remained. A separate UID scan found no live UID-1001 worker processes.
The private-store root, socket, VM marker and raw diagnostic copy were removed
before VM shutdown. Selected synthetic audit summaries and source were retained;
logical removal and VM stop do not establish physical erasure.

The transferred evidence archive matched SHA-256
`7e7e1ba971288caebf959255e040f55017df17e2656ce149d01853657aab4af4`. All nine collected file hashes (six
experiment files plus package, lock and license) matched the local copy.
Lifecycle metadata is appended after that verified transfer.


Timings and whole-VM metrics include their stated setup/check work. They are not
a controlled before/after performance comparison. Model token usage was not
measured. Per-capture cgroup observations are retained; they do not establish
the maximum cost of arbitrary targets.

## Remaining risks and next step

The implemented profile is deliberately limited to curated fixtures. It is not
an authorization layer for direct REA users, arbitrary commands or all providers.
The controller assumes a trusted operator and no operator tools for the request
role. Availability hardening of the local controller, complete stress/fault
coverage, independent human-readiness attestation, general derived-report
authorization and provider-internal data copies remain outside certification.

REA-0 and REA-1 remain complete. REA-1.1 remains partial. REA-2 through REA-4 have
not started. No main/upstream change, merge, package publication, deployment or
B•Code Platform integration occurred.

Source review also found that janitor startup has no readiness acknowledgement
before the request socket is exposed. Early controller death in that window
was not tested; the tested SIGKILL occurred during a live run. Make readiness
a prerequisite for admission and verify early-death behavior before broadening
use. Per-client socket timeout/rate controls also remain unverified.

The next step is targeted closure of the NOT_TESTED cases with benign fault
injection, preserving the fixed fixture scope. Do not broaden the protocol into
a general gateway or accept real data to compensate for incomplete tests.

**Next operational prompt:** Continue REA-1.1 by closing the prototype's remaining
acceptance gaps, starting with janitor startup acknowledgement and early
controller death, then real memory/PID/output bounds and midrun audit/
evidence-sink failure. Verify cleanup ownership and independent retention after
failure. Preserve main, the synthetic fixture-only scope and no platform
integration, native providers, real credentials, merge or deploy.
