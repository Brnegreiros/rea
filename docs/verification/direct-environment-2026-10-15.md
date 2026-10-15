# REA-1.1: direct subprocesses and explicit environment authority

**Date:** 2026-10-15. **Decision:** GO for continued isolated evaluation;
**NO-GO for production or unrestricted agents**. F03 remains partially mitigated.

Repository: Brnegreiros/rea. Evaluation branch:
`fix/bcode-rea-1-1-containment`. Parent:
`33b6537b96fb8d7bb8b5c3c24e850deff671768c`. Main remains
`6060de329de9f3636f63e24a2419847fd9d3f889`.
The validated patch is identified by the tested-file SHA-256 values in
[the evidence record](direct-environment-2026-10-15.json).
[Policy and compatibility contract](../provider-process-environment.md).

## Observed problem and minimal correction

Direct command consumers used either a full selected environment or Node's
implicit process.env fallback. The shared owned-process filter from the previous
round did not cover these consumers or the separate diagnostic SDK transport.

Four real-child regressions fail against the parent revision: selected execFile
base, implicit execFile base, bounded-output command and updater command.
Only synthetic values are supplied. GITHUB_TOKEN, OPENAI_API_KEY, DATABASE_URL
and an ordinary setting are observed as present where applicable. A separate
baseline SDK-doctor regression also fails, showing that its broad selected map
reaches the diagnostic child. The baseline tests check names/booleans and runtime
options, not real operator credentials. The preload-marker assertion occurs
after the first failing baseline assertion; separate baseline marker execution
is not claimed.

The correction centralizes base selection in providerCommandEnvironment.
ExecFileOutput/execFileBytes now filter options.env or the implicit fallback.
ExecFileBoundedOutput and the updater filter their bases. Mac Hopper utilities,
Hopper opening and Windows taskkill reuse the shared executor; migrated utility
calls retain an explicit 1 MiB capture bound. The owned launcher uses the same
merge producer and still applies its owned run ID last.

Two related provenance defects were corrected: adb version inspection now uses
the selected provider environment, and the Darwin helper receives its selected
host snapshot even when a custom startup timeout is present. Its compiler can
explicitly receive SDKROOT, DEVELOPER_DIR, TOOLCHAINS and
CLANG_MODULE_CACHE_PATH from the internal producer. Unknown base values are not
forwarded through this override map.

MCP self-diagnostics select runtime names plus exact configuration names derived
from the configuration parser. The SDK's ambient defaults are explicitly blanked
before selected values are applied. Target-selection fields remain removed.
The diagnostic timeout fixture now receives its PID path as an explicit argument,
rather than relying on an arbitrary inherited test variable.

**Compatibility change:** arbitrary base variables, including NODE_OPTIONS,
proxy configuration, package-registry settings and custom launcher variables,
are no longer automatically forwarded at these boundaries. Recognized REA
configuration is preserved for the diagnostic child. Additional adapter values
require an explicit reviewed input; the override mechanism itself does not grant
authorization. No dependency, package identity or license change is made.

## Route inventory and evidence limits

| Route / producer | Environment origin and result | Verification scope |
| --- | --- | --- |
| OwnedProviderProcess | Runtime base + explicit adapter map + owned run ID | Real Node child regressions and ownership tests |
| ExecFileOutput / execFileBytes | Selected or global base filtered; separate internal envOverrides | Real child, cancellation, timeout and byte-capture tests |
| ExecFileBoundedOutput | Selected base filtered | Real child and bounded-output tests |
| UpdateRuntime | Package-runner identity removal plus runtime selection | Benign Node command; no actual update or package install |
| adb/apktool inspection | Shared executor; adb now uses selected provider context | Real synthetic adb launcher and provider tests; no device contact certification |
| Apple asset/disk, Doctor, Hopper utilities, native UI, ps/sampling | Shared executor; former promisified raw calls migrated | Static route tracing and selected fixtures; real macOS utilities NOT_TESTED |
| Darwin process-token compiler/readers | Selected snapshot; four named compiler overrides | Real executable fixtures on Linux; actual Swift/macOS reader NOT_TESTED |
| Ghidra synchronous Java probe | Existing ghidraJavaEnvironment producer | Static provenance plus selected launcher tests; real Ghidra NOT_TESTED |
| Ghidra LaunchSupport | Shared command base filter; provider-generated environment entries can enter analysis JVM map | Provider installation is a trust boundary; complete native behavior NOT_TESTED |
| PTY capability / Android Windows guardian | Existing small explicit maps | Inspected; Windows guardian native behavior NOT_TESTED |
| Process capture | Filtered base + caller scenario.environment | Real PTY proof, capture cleanup and CLI workflow |
| IDA stdio | Filtered base + explicit local registration config.env | SDK Node fixture; real IDA NOT_TESTED |
| MCP diagnostic SDK transport | Runtime names + exact parser-owned configuration; no inherited SDK fallback | Real startup canaries, production MCP full/compact profiles and lifecycle tests |
| Browser/Electron | Existing separate environment producers | Unchanged; no new real-browser certification |
| Frida native/device spawn | SDK call leaves env/envp selection unspecified | OPEN; native/remote backend inheritance not measured |
| LLDB target launch | Caller environment copied into bridge request; native target environment merged there | Source-derived; real macOS target execution NOT_TESTED |
| Packaged helpers / target-created descendants | Hopper helper receives filtered parent environment; Electron hook observes target child creation | These are not a universal child-process policy; external code requires isolation |

The Frida core upstream source consulted during the audit contains an
environment fallback when envp is absent:
[HostSpawnOptions](https://github.com/frida/frida-core/blob/main/lib/base/session.vala).
This is source-derived support for further investigation, not runtime proof for
the locked native binding, a remote server or a particular device. No Frida
native library or target was installed/executed for this round.

The focused regressions are in `tests/boundary/process/directCommandEnvironment.test.ts`
and `tests/boundary/mcp/mcpDoctorEnvironment.test.ts`. The explicit-value proof is
in `tests/boundary/process/explicitEnvironmentAuthority.test.ts`.

## Authority of explicit values

| Input | Who supplies it | Present enforcement / residual risk |
| --- | --- | --- |
| Owned-process env / command envOverrides | Internal adapters | Reviewed call-site selection; no IAM decision is performed by the merge |
| Compiler envOverrides | Selected internal compiler producer | Four exact coordinate names, not an arbitrary caller dictionary |
| IDA config.env | Selected local registration file | File/schema input; no per-key operator approval or file-integrity certification |
| Process scenario.environment | CLI/MCP caller, potentially an agent | Shape validation and reserved run-ID protection; no independent operator approval |
| Native-call environment | CLI/MCP caller; LLDB bridge applies it to target | Caller authority and evidence-data risk; source-derived in this round |
| Diagnostic configuration | Names owned by the REA configuration parser | Recognition is not proof that values are safe; explicit reference-secret patterns remain intentional configuration |

A real isolated PTY test uses the public tool schema to supply a synthetic
explicit variable and a benign NODE_OPTIONS preload. The variable is visible to
the child, the preload marker is created, and the literal explicit value appears
in process capture Evidence. The unrelated ambient canary is absent. This proves
that base filtering does not authorize explicit values or redact caller data.
Native-call code similarly retains explicit target environment fields in its
observations; native execution was not tested.

For B•Code evaluation, keep the worker credential-free and use synthetic inputs.
Authorize the executable, arguments, target and explicit variable names/values
together. An approval field controlled by the model would not establish operator
authority. An external execution policy is needed before autonomous operation.
No IAM/gateway integration or new per-key approval service is implemented here.

## Findings and disposition

| Finding | Severity / impact | Evidence | Disposition |
| --- | --- | --- | --- |
| DE01 broad direct-command inheritance | HIGH: ambient credentials/options can reach external commands | Four failing baseline regressions | Mitigated for mapped shared-command routes |
| DE02 diagnostic SDK bypass | HIGH: credentials/options can reach self-diagnostic child | Separate baseline failure and corrected startup probe | Mitigated at SDK boundary |
| DE03 selected-host provenance loss | MEDIUM: wrong PATH/compiler context can be selected | adb and compiler executable fixtures | Corrected |
| DE04 explicit values lack independent authorization | HIGH before agents: caller can choose executable-affecting settings | Real PTY + public-schema acceptance | OPEN; approval must be external to model input |
| DE05 explicit data persists in evidence | HIGH with real secrets: evidence/export may disclose supplied values | Real process Evidence contains synthetic explicit value | OPEN data policy; caller-data contract preserved |
| DE06 native/device inheritance and provider trust | HIGH before operation | Frida/LLDB/provider routes inspected; native behavior unmeasured | NOT_TESTED / OPEN |

## Isolated verification

The first 8 GiB worker expired before the full evidence transfer completed.
Its observed test results are not used as the durable acceptance record.
The final patch was revalidated in a fresh 4-vCPU, 8-GiB disposable worker with
Node 24.18.0 and npm 11.16.0, pinned image digest and unchanged npm lockfile.
Python 3.14 plus its standard library was acquired only in the worker from
official Ubuntu repositories for benign Hopper helper tests.

A dedicated UID/GID 1001 ran project commands with no effective capabilities,
cleared groups and no_new_privs. Operator-home access and sudo elevation were
denied. Memory was bounded at 8589934592 bytes, PIDs at 512, CPU allocation at
four vCPUs and session duration at 30 minutes. Acquisition used a destination
allowlist; project tests ran after egress returned to deny-all. Dependency
lifecycle scripts were disabled during npm ci. No production credential,
native injection, deploy, package publication or host installation occurred.

| Executed control | Status | Observed result |
| --- | --- | --- |
| Parent direct-command reproduction | PASS (reproduction) | Four expected failures; three name-filter exclusions |
| Parent SDK-doctor reproduction | PASS (reproduction) | One expected failure with synthetic startup canaries |
| Final selected source/CLI/MCP tests | PASS | 440 passed, 8 platform skips, 34 files; 60.24 s |
| Documentation consistency tests | PASS | 5 passed; part of docs:check |
| TypeScript | PASS | npm run typecheck, exit 0; 56.570 s wall |
| Runtime and skill build | PASS | npm run build:cached, 3 successful tasks, no cached task; 39.393 s wall |
| Formatting | PASS | 20 changed TS/MJS files checked |
| Ordinary selected-file lint | PASS with warnings | 35 warnings, 0 errors; warning debt remains |
| Module boundaries | PASS | 1888 source files checked |
| Documentation/metadata/license consistency | PASS | docs:check, exit 0; no dependency/license change |
| Native Frida/device spawning | NOT_TESTED | No native binding installation, instrumentation or device execution |
| Actual macOS/Windows providers | NOT_TESTED | Cross-platform producer fixtures do not certify native runtimes |
| Independent approval of explicit environment values | FAIL for autonomous readiness | No separate operator authorization is enforced by those input schemas |
| Real secrets and production integration | NOT_TESTED | Only synthetic values and isolated fixtures were used |

The 440-case pass count includes the selected CLI/MCP flows and MCP-doctor tests.
Together with five distinct documentation tests, 445 cases passed. Baseline
failures are negative reproduction evidence and are not counted as passing
functional tests. The successful run is a fresh worker acceptance run, not an
aggregate of failed runs and targeted retries.

Logs, exit codes, source hashes, acquisition commands, preflight and shutdown
metadata are retained in JSON. The eight final skips are platform/native-host
cases; the baseline's name-filter exclusions are separately recorded and are
not counted as final platform skips. Synthetic canaries are test data only.
The complete suite and complete external-provider SCA were not executed.

## Resource observations and disposal

Final worker: `sbx_yWIKmOa7nmq5n4OJIBKJJ7ujEK0X`; stopped at
2026-10-15T20:03:46.869000+00:00.
API wall duration: 644.566 s. API active CPU: 360.406 s.
Cgroup CPU at evidence capture: 323.950841 s. Whole-worker memory peak:
5,243,609,088 bytes (about 4.88 GiB). OOM and oom_kill counters: zero.
No rea-user processes remained before shutdown.

The earlier expired worker (`sbx_sZkDTcw2QiJnwh1fhdwlGicjALng`) consumed
2400.397 s API wall duration and 867.056 s active CPU.
Across these two workers, recorded API wall duration was
3044.963 s and active CPU was
1227.462 s.
The earlier worker's filesystem was discarded before full evidence export;
only its API lifecycle metadata is retained.

Timings cover their stated commands; whole-worker metrics include setup,
acquisition, baseline failures, verification and evidence transfer. Cold/warm
runs and different VM sizes do not form a controlled performance comparison.
Agent token usage and peak per-process-family RSS were not measured separately.
The worker is stopped with deny-all retained and persistent false.

## Roadmap and next action

REA-0 and REA-1 remain complete. REA-1.1 is partial; REA-2 through REA-4 have not
started. This patch is prepared only on the evaluation branch. Main, upstream,
B•Code Platform, package/dependency identity and license remain preserved.
No PR, merge, publication or deployment was performed.

The minimal next step is an execution-authorization contract outside agent input,
covering explicit variables and their retained evidence, followed by a selected
native-provider matrix. Keep Frida/device spawning and credential-bearing
workflows unavailable to unrestricted B•Code agents until those controls are
demonstrated.

**Next operational prompt:** Continue REA-1.1 by defining the minimum external
authorization contract for command execution and explicit environment values,
including evidence retention. Separate internal adapter coordinates, operator
configuration and agent-controlled inputs. Prepare verifiable acceptance cases
without main changes, IAM integration, deploy or real credentials.
