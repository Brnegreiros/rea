# B•Code fork execution readiness

This fork is evaluated independently of the B•Code Platform. REA remains a local
investigation tool. No IAM, billing, Intelligence, production database, or bot
integration is established by these controls.

## Distribution boundary

Every job in `release.yml`, `release-recovery.yml`, and `website-pages.yml` is
restricted to the exact upstream repository identity `morluto/rea`. This denies
release proposals, release creation, package qualification/publication,
publication recovery, and website publishing from `Brnegreiros/rea` and other
repository identities. The package and MCP identifiers still belong to the
upstream; they are retained for provenance, not permission to publish them.

These are workflow job conditions, not protection against a repository
administrator editing the workflow. They only take effect on revisions that
contain the guards. Existing `main` revisions and their settings are unchanged
until an authorized merge. No Actions setting, environment, registry credential,
or upstream configuration is changed by editing these files.

The remaining artifact Actions in `real-cutter.yml` are pinned to the commit
objects resolved for their existing v4 references. Future updates need a reviewed
SHA change; a tag alone is not a reviewed update.

## Browser launch boundary

| Operation                                        | Default                                                | Compatibility exception                                                    |
| ------------------------------------------------ | ------------------------------------------------------ | -------------------------------------------------------------------------- |
| Launched browser scenario on Linux/macOS/Windows | `chromiumSandbox: true`; failed launch returns failure | None; no automatic unsandboxed retry                                       |
| Launched browser scenario on Android/Termux      | Explicit unsandboxed, single-process mode              | Existing platform compatibility; excluded from untrusted B•Code evaluation |
| Native module resolution                         | `chromiumSandbox: true`; failed launch returns failure | Only `REA_BROWSER_NO_SANDBOX=true` explicitly disables it                  |
| Attached browser scenario                        | Existing caller-owned browser                          | Sandbox state is not established by REA                                    |

The module resolver's compatibility opt-out and Android scenario mode must not
be used for untrusted B•Code investigations without a separately verified
isolation boundary. Browser flags do not isolate REA, Frida, GDB, native parsers,
or other subprocesses. A sandbox request is not runtime evidence that a given
browser/OS combination enforces the intended boundary.

## Required evaluation worker

Use one disposable VM or independently validated equivalent per evaluation.
Provision dependencies in the disposable environment; do not install REA or its
providers globally on an operator's host to perform the evaluation.

| Control          | Required observation before project execution                                                                                                                        |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity         | The runtime user is non-root and cannot elevate privileges                                                                                                           |
| Filesystem       | Only the selected source, fixtures, temporary work, and output are exposed; private files, production credentials, host sockets, and personal directories are absent |
| Network          | Egress is denied for offline tests; any later acquisition window has an explicit destination allowlist and is closed before executing targets                        |
| Resources        | CPU, whole-process-family memory, PIDs, disk and job duration are bounded externally                                                                                 |
| Process lifetime | Cancellation removes owned descendants; test completion leaves no running target processes                                                                           |
| Browser          | Supported launchers request the sandbox and fail without downgrade; runtime launch flags and OS behavior are verified                                                |
| Output           | Logs and evidence contain only selected synthetic data; synthetic credentials are checked at each retained/shared sink                                               |
| Disposal         | The environment is destroyed and retained outputs are enumerated                                                                                                     |

Before running the project, probe these controls using benign fixtures. A
container label, a temporary directory, `shell:false`, a tool annotation, a PID,
or a successful syntax check does not demonstrate this worker boundary.

Use `.nvmrc` and `package.json#packageManager` for the toolchain, the reviewed
commit for source, and its unchanged lockfile for dependencies. Start acquisition
with dependency lifecycle scripts disabled; review each necessary native script
before executing it in the worker. Do not invoke the generic upstream installer
as a way to validate this fork's source revision.

## Verification and remaining gates

The changes include launch-boundary regression cases for Linux, macOS, Windows,
the explicit module opt-out, and preserved Android scenario behavior. Mock
launchers can verify requested options and absence of a retry; they cannot prove
actual Chromium sandbox enforcement. Run the relevant tests in the verified
worker, then the real browser smoke with benign targets.

Relevant existing test files:

- `src/browser/PlaywrightScenarioBrowser.test.ts`
- `src/browser/modules/NativeModuleResolver.test.ts`
- `tests/boundary/filesystem/releaseWorkflow.test.ts`
- `tests/boundary/filesystem/releaseRecovery.test.ts`
- `tests/conformance/releaseConfiguration.test.ts`

The [isolated runtime report](verification/fork-runtime-validation-2026-10-15.md)
records build, typecheck, 206 passed tests and one platform skip for the
containment revision. It also records a bounded real-browser compatibility
probe, selected synthetic redaction checks and worker cleanup observations.
These results cover the stated revision and selected scenarios. The supported
OS smoke, full suite, MCP end-to-end flow and remaining provider coverage are
still required; the report distinguishes PASS from NOT_TESTED.

The [provider environment policy](provider-process-environment.md) restricts
implicit inheritance at the owned launcher and selected parallel boundaries.
Its [isolated verification](verification/provider-environment-2026-10-15.md)
uses synthetic credentials. The [direct-route audit](verification/direct-environment-2026-10-15.md)
extends the policy to shared command executors, updater and MCP self-diagnostics.
Explicit-variable authorization, native Frida/device spawning and real-provider
compatibility remain open. Capability authorization, classification/retention
policy, and external-provider SCA also remain open. The
[Frida source-admission correction](verification/frida-source-read-2026-10-15.md)
records regular-file checks, a 4 MiB file/inline budget, cooperative cancellation
and retained descriptor cleanup. Its selected 99 tests passed in an isolated
Linux worker; native Frida instrumentation and other operating systems remain
unverified. These controls apply to the evaluation branch until an authorized
merge.

REA-1.1 remains partial until the prepared controls are reviewed and the
necessary runtime evidence is available. No merge, publication, deployment, or
production integration is authorized by successful static checks.

## External authorization specification

The [minimum external contract](external-execution-authorization.md) binds a
one-use operator decision to a concrete execution plan and its environment,
worker, limits and evidence policy. The initial proposed profile admits only
curated synthetic Linux process-capture fixtures; raw output stays private and
raw export is disabled. Existing ambient-name filtering is not an authorization
decision and recognized configuration is not automatically safe.

The [acceptance catalogue](verification/execution-authorization-acceptance-2026-10-15.json)
contains 28 cases for admission, substitution, replay, cancellation, bypass and
retention. Its status fields describe the definition stage. The
[definition verification record](verification/execution-authorization-2026-10-15.md)
records only the checks actually performed for this documentation revision.
No IAM service or production runtime enforcement is introduced. The separate
[experimental prototype](../experiments/execution-controller/README.md) now
exercises a fixed Linux fixture profile using Unix peer roles, namespaces,
cgroups and an independent storage janitor. The [runtime report](verification/controller-prototype-2026-10-15.md)
separates actual PASS observations from partial/NOT_TESTED cases. It does not
enable the prototype in published REA or establish human review. Production and
unrestricted-agent use remain NO-GO.

The [janitor follow-up](verification/controller-janitor-2026-10-16.md) requires
readiness before admission and tests earlier controller death. It also proves
that killing the storage janitor leaves intent/audit past their deadlines.
The later [retention recovery](verification/controller-retention-2026-10-16.md)
addresses that observed sequence with an independent standby and tests both
single-guard-loss variants, restart blocking and real failed-disposal ownership.
The [resource/storage follow-up](verification/controller-resource-storage-2026-10-16.md)
adds bounded real memory/PID/output pressure and selected midrun audit/evidence
faults. The external owner caps private stream bytes before writing, reconciles
kernel limit events and closes SQLite transactions/FDs explicitly. Failed raw
deletion retains ownership and blocks admission; an empty stopped cgroup can be
released independently of a busy evidence mount. Original retention regressions
are rerun with this change; the linked runtime record owns their actual results.
REA-1.1 remains partial. Both-guard loss, hung guards, clock uncertainty, complete
EA-18/EA-26 coverage, whole-control-volume failure, durability and unresolved
contention diagnostics remain pending. Forced deletion failure is not reported
as timely expiry. No production integration or general readiness is established.

## Bounded REA-1.1 audit closeout

The [ten-objective closeout matrix](verification/rea-1-1-closeout-matrix-2026-10-16.md)
reconciles historical evidence and the remaining static/supply-chain review.
The prototype is frozen for this closeout plan, superseding older next-step
suggestions for additional prototype fault tests in this sequence. Those gaps
remain blockers rather than automatic implementation work. A final NO-GO opinion can retain
explicit FAIL/NOT_TESTED controls; it does not require a broader implementation.
The final consolidated readiness opinion remains pending. Main still lacks the
evaluation branch safeguards, and no merge or production authority is implied.
