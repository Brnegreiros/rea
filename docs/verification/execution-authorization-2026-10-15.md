# REA-1.1: external authorization contract definition

**Date:** 2026-10-15. **Scope:** documentation and acceptance definition only.
**Decision:** continue isolated specification/prototype work; production and
unrestricted-agent operation remain **NO-GO**.

Repository: `Brnegreiros/rea`. Branch: `fix/bcode-rea-1-1-containment`.
Parent baseline: `1f4dc6996d452b62c3870ac1d3a7559461e698fd`.
Main remains `6060de329de9f3636f63e24a2419847fd9d3f889`.
No runtime/controller, dependency, workflow, package identity, license or
canonical Evidence format is changed in this stage.

## Investigated evidence and conclusions

| Boundary | Evidence at the parent revision | Conclusion |
| --- | --- | --- |
| Base/explicit merge | `src/process/providerProcessEnvironment.ts` | Base filtering is separate from explicit overrides; the merge explicitly grants no authority |
| Public process input | `src/domain/process/processScenario.ts`, `src/process/capture/ProcessCaptureEnvironment.ts` | Caller environment values are accepted by shape and applied to the target |
| Runtime path resolution | `src/process/capture/ProcessScenarioRuntimeValidation.ts` | REA can resolve a command through selected PATH; the external plan must freeze an absolute executable and stable inputs before approval |
| Canonical capture | `src/domain/process/processScenario.ts`, `src/application/process/ProcessEvidence.ts` | Explicit environment is part of the scenario commitment and capture result; preserve canonical provenance |
| Evidence export | `src/application/EvidenceBundleCommands.ts`, `src/application/EvidenceBundleFiles.ts` | Export is an actual data boundary; an external retention/access/approval mechanism has not been demonstrated |
| Input journaling | `src/process/capture/ProcessCaptureJournal.ts` | A marked scripted input gets a placeholder; this does not establish redaction of target echoes or all output |
| Previous isolated proof | `tests/boundary/process/explicitEnvironmentAuthority.test.ts` and [its saved record](direct-environment-2026-10-15.json) | Synthetic explicit values reached a real PTY child and canonical Evidence; benign explicit preload executed. Earlier evidence, not rerun here |

This establishes the need for an independent execution decision. It does not
establish a complete inventory of all storage sinks or prove that every input
contains sensitive data. No real operator credential was collected or tested.

## Definition delivered

The [versioned contract](../external-execution-authorization.md) contains 12
requirements covering independent authority, complete binding, stable resources,
environment provenance, narrow admission, one-use decisions, containment,
mediation, evidence fidelity, retention, failure behavior and acceptance.

The initial proposed profile is Linux process capture with curated synthetic
fixtures. The controller holds approval outside the worker, binds the actual
parsed scenario and resolved execution inputs, consumes a decision atomically
and supervises external bounds. No signature service, credential vault,
platform gateway or IAM integration is required to prototype that boundary.
The requesting agent must have no host tool capable of forging approval state;
the proposed agent-visible response contains only fixed statuses and opaque IDs.

Environment provenance distinguishes runtime base, internal coordinates,
operator configuration and caller inputs. The initial profile denies caller
loader/injection controls, ambiguous names, unclassified data and real
credentials through any channel. Merely declaring a value synthetic is not
proof; only reviewed fixtures qualify.

Canonical raw Evidence remains private and unchanged. The contract requires
explicit raw/audit deadlines, bounded destinations, no automatic raw disclosure,
and disabled raw export initially. A later derived report must keep source
linkage and an explicit transformation ledger. Deletion receipts describe
controlled accessible copies; stopping a VM does not prove physical erasure or
deletion of unknown provider copies.

## Verification actually performed

The [definition-check record](execution-authorization-2026-10-15.json) retains
the exact host-side standard-library Python verification command, results,
source anchors and artifact hashes. It checks data/documents without importing
or executing REA, its dependencies, providers or target fixtures.

| Control | Status | Limit |
| --- | --- | --- |
| JSON parsing and case/requirement identity consistency | PASS | Catalogue structure, not controller behavior |
| Requirement-to-case coverage and explicit denial/cleanup/privacy oracles | PASS | Reviewed acceptance definition; not an execution proof |
| Referenced source anchors and local document links | PASS | Source traceability at the stated revision |
| Whitespace and code/dependency/workflow preservation | PASS | Document-only diff; main preserved |
| External controller admission, replay and revocation | NOT_TESTED | No controller implemented |
| Actual sink confinement, TTL enforcement and deletion | NOT_TESTED | Defined requirements only |
| New project build, CLI/MCP execution or provider tests | NOT_TESTED | Not necessary for this documentation-only change; no VM started |

The [acceptance catalogue](execution-authorization-acceptance-2026-10-15.json)
specifies **28 cases**, all with runtime status `NOT_TESTED`. It includes a real
admitted-workflow positive case and negatives for substitution, self-approval,
environment/identity changes, TOCTOU, replay, concurrency, cancellation, resource
bounds, alternate invocation, private sinks and interrupted retention/cleanup.
Denials require trusted launch observation, not only an error message.

The preceding round's 445 passing tests and eight platform skips are historical
results for its recorded patch. They are not claimed as freshly executed tests
or as acceptance of this external authorization contract. This stage incurred
no new cloud-worker execution. Token usage and document-check performance were
not measured separately; no performance claim is made.

## Residual risks and disposition

| Risk | Current state | Next evidence required |
| --- | --- | --- |
| Agent/caller can still supply explicit execution-affecting input directly to REA | OPEN / HIGH before autonomous use | Implement and exercise the external admission boundary; current runtime is unchanged |
| Approval could be bypassed, replayed or substituted | NOT_TESTED / HIGH | Real-controller negative and concurrency tests with zero/at-most-one launches |
| Raw evidence may contain literal caller data, echoes and target output | OPEN / HIGH with real data | Actual private sink, disclosure and retention controls; keep synthetic-only scope |
| Worker/provider boundaries and data disposal may be incomplete | NOT_TESTED | External probes, owned-family cleanup and enumerated storage receipts; provider-internal copies remain qualified |
| Frida/device inheritance, native providers and complete SCA | OPEN | Separate selected native-provider and supply-chain work; not enabled by this contract |

These are evaluation/operational risk ratings, not new upstream vulnerability
claims. Defining the contract does not close the implementation gaps.

## Roadmap and next action

REA-0 and REA-1 remain complete. REA-1.1 remains partial:
environment hardening and the external contract are prepared on the evaluation
branch; external enforcement, retention implementation, native-provider runtime
validation and complete dependency review remain pending. REA-2 through REA-4
have not started. Main/upstream and the independent repository boundary are
preserved. No PR, merge, publication, deploy or platform integration occurred.

The smallest next step is a disposable external-controller prototype for the
single synthetic process-capture profile, not a general authorization platform.
Prove decision isolation, exact binding, one-use admission, private output and
disposal before broadening tools or accepting real data.

**Next operational prompt:** Continue REA-1.1 with an isolated prototype of the
external execution controller for curated synthetic Linux process capture.
Implement the versioned contract and execute its acceptance catalogue, preserving
main, canonical Evidence and no platform integration. Report actual PASS/FAIL/
NOT_TESTED evidence, resource limits, cleanup and retention outcomes. Do not
enable native providers, real credentials, raw export, merge or deploy.
