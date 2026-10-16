# External execution authorization for isolated REA evaluation

**Version:** `rea-evaluation-authorization/1`. **Date:** 2026-10-15.
**State:** specified evaluation contract; isolated experimental enforcement is
PARTIAL. See the [prototype runtime record](verification/controller-prototype-2026-10-15.md)
for case-specific results. The public REA CLI/MCP runtime has no independent
operator authorization added by this prototype. This document does not enable a
tool or approve production operation. Definition baseline:
`1f4dc6996d452b62c3870ac1d3a7559461e698fd` on
`fix/bcode-rea-1-1-containment`.

The [2026-10-16 janitor follow-up](verification/controller-janitor-2026-10-16.md)
records the original failed retention control after janitor loss. The later
[retention recovery](verification/controller-retention-2026-10-16.md) adds an
independent standby, original-deadline expiry and failed-disposal ownership.
These narrow synthetic tests do not certify all storage faults. The profile
remains NO-GO.

The [direct-route audit](verification/direct-environment-2026-10-15.md) proved
that filtering inherited environment values does not authorize explicit values.
A public-schema process scenario can select a benign Node preload, and its
synthetic explicit value is retained in canonical Evidence. REA is not a sandbox.
This contract places the missing decision outside the model and the worker,
without introducing B•Code IAM, a gateway service, or platform integration.

## Initial scope and trust boundary

The first implementation may expose only a reviewed, single process-capture
workflow on Linux, using benign fixtures and declared synthetic data in a
disposable worker. This is a proposed acceptance scope, not certification of
every Linux host. Approving an investigation does not approve all REA tools.

| Actor / input | Authority in this contract |
| --- | --- |
| Operator using a trusted control channel | Reviews the effective plan and grants or denies one execution |
| Requesting agent / CLI / MCP input | Proposes a request; cannot approve itself or select its authoritative identity |
| External controller | Resolves the reviewed plan, verifies the operator decision, consumes it once, starts and supervises the worker |
| REA and target inside the worker | Execute only the selected entry point inside external bounds; their output cannot grant authority |
| Internal adapter configuration | May provide reviewed runtime coordinates under the bound policy; being internal is not an unrestricted override grant |

The controller and its approval state must be outside the worker's filesystem,
OS identity, environment, sockets and accessible network. A different module or
process sharing writable approval state with a target is not this boundary.
The requesting agent must also lack host-shell, file or API access capable of
reading or changing that state or impersonating the operator channel. Otherwise
the approval boundary is unverified, even when the target VM is well isolated.
For a local prototype, operator confirmation and an in-memory controller record
are sufficient if their isolation is demonstrated. A signed-token service is
not required. A signature alone would not solve replay, revocation or mediation.

No generic shell, unrestricted MCP connection, update/install command, browser
attachment, native debugger, Frida/device operation, remote target, elevation or
production credential is admitted by the initial profile. Independent REA usage
outside the controller remains possible and is outside its guarantee; the
evaluation worker must expose no alternate invocation path to an agent.

## Required effective intent

The controller prepares one immutable UTF-8 JSON artifact after parsing with the
owning REA input contract and resolving all defaults and worker coordinates.
Its exact bytes are committed by SHA-256. Approval binds that artifact, the
controller-owned worker identity and policy revisions. Do not hash one request
and execute a separately reconstructed command. A digest proves byte identity,
not that an operator approved or understood those bytes.

The trusted review displays executable, argument boundaries, scripts, target,
working directory, environment origins and exact synthetic values, side effects,
resource limits and retained outputs. Showing only a digest is insufficient.
Unknown or duplicate JSON fields and duplicate environment names are rejected
before normalization. No secret is inferred from a variable name or regex.

| Required intent field | Binding and rejection rule |
| --- | --- |
| `contractVersion`, `requestId`, `requesterId` | Exact version and controller-issued opaque request ID; requester identity comes from the control channel, not the proposed payload |
| `operation` | Exact REA entry point, capability, parsed input artifact and expected child-process family; only reviewed process capture is initially eligible |
| `source` | REA commit, lockfile digest, runtime image/toolchain and controller/adapter policy revision; a change requires a new plan |
| `worker` | Controller-issued identity, Linux platform, non-root UID, immutable input roots and private writable roots; no host credentials or production mounts |
| `command` | Absolute executable path and content digest, ordered argv, absolute resolved cwd and exact script/fixture artifacts; no command-name PATH lookup after approval |
| `target` | Exact owned fixture path/digest and declared effects; not a PID alone, wildcard, arbitrary endpoint or permission to attach |
| `environment` | Approved runtime profile revision, complete selected base map, reviewed internal coordinates and exact caller map with provenance/classification |
| `limits` | Externally enforced CPU, whole-family memory, PIDs, disk, output/evidence bytes, elapsed deadline and deny-all network policy |
| `evidencePolicy` | Private raw location, allowed reader, raw deadline, audit destination/deadline, byte caps and export policy; absent policy denies execution |

The binding covers the complete parsed scenario, including input events,
timeouts, terminal shape, filesystem observations and normalization, not merely
the executable and environment. Script content in `-e`, arguments, stdin, files,
configuration and interpreter startup paths are execution inputs too.

Input files, executable, dependencies, runtime configuration and directory
bindings must remain immutable between review and use. Stage reviewed copies
in read-only worker inputs; resolve symlinks and reject links/paths whose final
identity cannot be kept stable. A hash check followed by use of a mutable path
does not close that race. The target can write only the separately approved
scratch/output roots. Unavailable file identity or configuration provenance
denies execution. The immutable image plus selected fixture manifest bounds the
dependency closure; an unreviewed runtime download is not permitted.

The declaration of expected children covers reviewed adapters and the root's
owned process family within the same worker constraints. It does not pretend to
authorize every target-created descendant separately. External-device access,
new providers or effects outside that family require a new scope and decision.

## Normative requirements

**EA-R01 — Independent authority.** Only a decision obtained through the trusted
operator channel grants permission. Agent fields such as `approved: true`, tool
annotations, comments, target text and earlier broad task approval grant none.
The operator's decision is stored by the controller, never accepted back from
the request as authoritative data.

**EA-R02 — Complete binding.** Bind the exact effective intent and all policy,
source and worker identities above. Any meaningful change requires a new
decision. No silent clamping, new defaults, extra environment entry or fallback
provider may widen an approved plan.

**EA-R03 — Stable resources.** Resolve and freeze executable, script, input,
configuration, cwd and target identities before review. Validate them at use
inside an immutable boundary. Do not authorize arbitrary files based only on
basename, PATH, owner name or a previous digest.

**EA-R04 — Environment provenance.** Apply the rules in the next section once
at the owning boundary; reject ambiguity. The merge utility grants no authority.

**EA-R05 — Narrow initial profile.** Admit only classified synthetic inputs and
reviewed runtime coordinates. Deny unknown classification and real credentials
through any channel. Loader/injection overrides, unreviewed paths, devices and
unvalidated providers remain unavailable in this profile.

**EA-R06 — Decision lifetime.** The controller record contains `approvalId`,
`decision` (`ALLOW` or `DENY`), authenticated operator identity, request/intent
binding, worker identity,
`issuedAt`, `validUntil`, policy revision and revocation/consumption state. A
bounded validity period is mandatory and cannot exceed worker lifetime. Missing,
expired, not-yet-valid, revoked, wrong-worker or already consumed decisions deny.
Only an authenticated `ALLOW` record can permit execution. Consume
atomically before launch: concurrent retries start at most one execution.
Recheck validity immediately before launch; consumption does not extend expiry.
Revoke/expiry during execution triggers cancellation and cleanup. The effective
deadline is the earliest of approval expiry, run timeout and worker expiry.
Use a trusted time source and a monotonic elapsed timer; clock uncertainty
denies a new launch. A retry after a crash needs a new decision, not restored
consumption state. This intentionally favors safety over transparent retry.

**EA-R07 — External containment.** Probe non-root/no-elevation identity,
filesystem isolation, network deny-all, whole-family limits and disposal before
project execution. Bounds must be positive, finite and enforced outside REA.
Missing enforcement denies. A resource violation stops the run and retains an
incomplete result. The prior 8-GiB worker is a measured test configuration, not
a universal sizing requirement or a sandbox certificate for future workers.

**EA-R08 — Complete mediation.** Admit only the reviewed entry point. Raw MCP,
alternate CLI paths and tools that can create an unreviewed process are not
exposed to the requesting agent. Target output, logs and generated files remain
untrusted data. No nested approval request from the target changes scope.

**EA-R09 — Evidence fidelity and confidentiality.** Keep canonical REA Evidence
unchanged in its private raw area. Apply the sink rules below; classification,
authorization and redaction are separate decisions. Do not advertise a
secret-free result merely because selected inputs were marked sensitive.

**EA-R10 — Retention and export.** Require explicit deadlines and enumerate all
retained copies. Raw export is disabled in the initial profile. New retention,
readers or destinations require a separate operator decision. Expiry must be
enforced by the controller/storage owner even after controller interruption.
Disposal is reported with its actual scope; physical media erasure is not
inferred from a stopped VM or a successful API deletion.

**EA-R11 — Failure behavior and audit.** Durably record a minimal admission
decision before launch; audit unavailability denies. Record consumption, launch,
stop/exit, resource failures, cleanup, exports and deletion outcomes. If the
durable audit or private evidence sink becomes unavailable or full during a run,
cancel and clean up; mark the result incomplete. Failed cleanup keeps ownership
and blocks reuse. External worker destruction remains the fallback. A missing
exit observation or deletion receipt is unknown, never a successful outcome.

**EA-R12 — Acceptance before enabling.** The linked acceptance cases must be
executed against the actual controller/worker and public admitted workflow.
Static review, schema acceptance or a fake approver does not establish runtime
authorization. Native-provider readiness is a separate later gate.

### Controller result boundary

Request, approval and external run IDs are generated by the controller; do not
reuse a target string as an audit identifier. Keep the private association to
REA's separately generated ownership run ID. Approval records are never placed
in tool input, returned to the agent as reusable capabilities or mounted in the
worker. An opaque result ID does not grant another execution or raw-data access.

The agent-visible result has only `contractVersion`, controller-issued
`requestId`, `runId` (null before launch), `status`, `reasonCode`, `coverage`
and `cleanupStatus`. Its allowed values are fixed:

| Field | Allowed values |
| --- | --- |
| `status` | `DENIED`, `COMPLETED`, `FAILED`, `CANCELLED`, `INCOMPLETE` |
| `reasonCode` | `NONE`, `NO_APPROVAL`, `INTENT_CHANGED`, `EXPIRED`, `REVOKED`, `CONSUMED`, `OUT_OF_SCOPE`, `CONTROL_UNVERIFIED`, `AUDIT_UNAVAILABLE`, `LIMIT_REACHED`, `CLEANUP_UNVERIFIED`, `RETENTION_UNVERIFIED`, `POLICY_DENIED` |
| `coverage` | `NOT_STARTED`, `SELECTED_PROFILE_ONLY`, `INCOMPLETE` |
| `cleanupStatus` | `NOT_STARTED`, `VERIFIED`, `FAILED`, `UNKNOWN` |

A decision denial is `DENIED` with `runId: null`, `NOT_STARTED` coverage/cleanup
and a non-`NONE` reason. `COMPLETED` requires the reviewed workflow to finish
within bounds and cleanup to be verified; it is not a provider-wide safety
certificate. Missing observations are `INCOMPLETE`/`UNKNOWN`. Error text and
raw REA results never become additional fields. This is a proposed response
contract, not a new REA public-tool schema.
`cleanupStatus` describes execution-family settlement; later retention expiry
and data disposal have separate audit events. `VERIFIED` does not certify
future deletion of retained copies.

## Environment rules and minimal protection

| Origin | Required selection and authority |
| --- | --- |
| Ambient operator/controller environment | Never copied into the worker or override map. Construct a clean worker profile; do not scan or collect operator credential values |
| Worker runtime base | Use the exact runtime-name producer in `providerProcessEnvironment.ts`; inspect its actual selected values and approve the profile. Names such as HOME, PATH, LD_LIBRARY_PATH and DISPLAY are not intrinsically safe |
| Internal adapter coordinates | Policy owns the exact names, value source, allowed worker roots and consumer. Darwin's four compiler coordinates are an example, not permission to enable that provider in this Linux profile |
| Operator configuration | Bind the selected immutable file/profile, exact entries and provenance. File/schema validity alone is not approval; IDA registration remains out of initial scope |
| Agent/caller explicit values | Exact name/value pairs, classified synthetic and separately operator-approved. Unknown names, changed values or values moved to another consumer deny |
| Ownership run ID | Generated by the reviewed owner after admission, applied last and correlated to the approved run. This is the sole declared generated target-environment field, not a caller override exception |

For Linux, names are case-sensitive. Reject empty names, NUL, `=`, reserved
ownership names and duplicate keys. Preserve strings literally: an empty value,
an absent variable and an omitted field are distinct before approved defaults
are applied. On a future Windows profile, reject case-insensitive duplicates
before canonical normalization; the current snapshot function selecting one
variant is not sufficient as an external authorization rule. Windows is
NOT_TESTED and excluded from initial admission.

The initial caller allowlist must contain exact reviewed fixture names and
values; it has no wildcard or inherited fallback. Runtime loader controls such
as NODE_OPTIONS, LD_PRELOAD, PYTHONPATH, JVM injection options and library/home
path changes are executable-affecting inputs, not ordinary app settings. They
are denied as caller overrides in this profile even if their values are
synthetic. A later dedicated benign injection test needs its own profile and
operator decision; this contract does not disable REA's general functionality.

A value needs both provenance and data classification (`synthetic` or reviewed
runtime coordinate) from the trusted review. A field claiming `synthetic` in an
agent payload is not a credential-safety guarantee. No name/regex classifier is
introduced. Because reliable arbitrary-secret detection is not established,
only curated fixtures qualify; unknown user/target data is denied initially.

## Evidence retention and disclosure

The initial policy deliberately avoids a credential vault, redaction service,
long-lived archive or automatic Intelligence ingestion. The controller can
implement admission with a local private record and a disposable VM.

| Sink | Minimum policy |
| --- | --- |
| Raw intent/scenario and canonical Evidence | Private worker/controller area; only the operator and required execution components. Never a model-visible audit payload. Bound bytes and lifetime; preserve original bytes and provenance |
| Child stdout/stderr, terminal frames, files, crash output and temporary captures | Treat as raw Evidence, even if a target echoes a marked input. No automatic forwarding to a model, shared terminal, telemetry, public CI artifact or repository |
| Controller audit | Opaque request/approval/run IDs, operator/control-channel identity, policy revision, admission reason code, timings, limits, exit/cleanup and disposal state. No argv, variable values, script text, stdin or raw diagnostic text |
| Private integrity manifest | Raw artifact identifiers, hashes, sizes, provenance and destinations; restrict it with the raw data. Do not publish per-secret hashes or treat hashes as anonymization |
| Agent-visible response | Fixed allowlisted status, opaque run ID and coverage/cleanup limitations. No raw evidence; a later operator-reviewed derived report is a separate disclosure |
| Reviewed derived report | Explicitly selected synthetic observations, source raw IDs and transformation/redaction ledger. Preserve uncertainty; do not silently rewrite a canonical record and reuse its identity |

Raw lifetime is explicitly chosen for each run and must not extend beyond the
disposable worker lifetime; external controller copies need the same or earlier
deadline. Audit metadata has a separately explicit retention deadline and a
bounded private destination. No hidden forever/default duration is allowed.
All output collectors, redirected streams and temporary controller copies count
as retention. An enabled durable snapshot, backup or log sink carrying these
outputs without a verified expiry policy disqualifies that execution profile.
Provider-internal copies that cannot be inspected remain a stated residual
risk, not a certified deletion claim. An export creates another managed
copy with its own destination, reader, bytes/digest and deletion deadline.

Expiry removes accessible raw copies, revokes readers and disposes the worker;
record each storage handle and outcome. If deletion cannot be confirmed, record
`UNKNOWN`/`FAILED`, keep the incident open and prohibit another run in that
profile. A manifest proves only the copies the controller controls. User-made
downloads, provider backups and physical media erasure remain outside that
proof and must not be claimed covered.

REA's marked scripted input is persisted as a placeholder in its input journal,
but that does not guarantee removal from echoed output or other evidence.
Explicit environment values have no such environment-level redaction guarantee.
The minimum protection for this stage is to exclude real credentials, isolate
all raw output and forbid automatic disclosure. Altering REA's canonical
Evidence contract is neither necessary nor authorized by this document.

## Verifiable acceptance and current state

The [machine-readable acceptance catalogue](verification/execution-authorization-acceptance-2026-10-15.json)
defines positive, denial, concurrency, mutation, containment and retention
oracles. Its stored `NOT_TESTED` fields describe the definition revision;
they are not the result store for subsequent executions. Actual observations
and incomplete cases are in the [prototype runtime record](verification/controller-prototype-2026-10-15.md).
The [verification record](verification/execution-authorization-2026-10-15.md)
separates document checks from runtime enforcement and links the earlier
synthetic proof; earlier tests are not rerun or counted again in this stage.

Before enabling the profile, each admission-denial test must show that no REA
entry point, provider or target started, rather than merely an error response.
Record a trusted launch counter and absence of a benign child marker. Positive
tests must use the real admitted CLI/MCP workflow and retain private linkage
from operator decision to intent, execution, raw manifest and disposal outcome.
Expiry/cancellation tests must also prove termination of the owned family and
worker disposal. A structurally valid record is never an ALLOW decision by itself.

The [resource/storage evaluation](verification/controller-resource-storage-2026-10-16.md)
exercises finite synthetic memory, PID and output loads plus selected real
midrun SQLite/filesystem failures. It adds no execution authority to the
contract. Its narrow PASS oracles and retained failed-deletion outcomes do not
promote the complete EA-18/EA-26 criteria or authorize human/production readiness.

REA-1.1 remains partial and production/unrestricted-agent use remains NO-GO.
Next: close the prototype's remaining acceptance gaps before broadening the
profile. Preserve no platform integration, main changes, native providers or
production credentials.
