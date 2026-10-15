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

The generic provider environment inheritance, capability authorization,
classification/retention policy, and external-provider SCA remain open. Frida
source-file admission and read bounds need their own focused change and
regular-file, size, cancellation and cleanup tests; these workflow/browser
changes do not close that finding.

REA-1.1 remains partial until the prepared controls are reviewed and the
necessary runtime evidence is available. No merge, publication, deployment, or
production integration is authorized by successful static checks.
