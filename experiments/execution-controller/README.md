# Isolated external execution-controller prototype

Experimental evaluation code, excluded from the published REA package and not
imported by the CLI/MCP runtime. This is a narrow implementation of
[`rea-evaluation-authorization/1`](../../docs/external-execution-authorization.md),
not production authorization or B•Code Platform integration.

## Execution boundary

Run only inside an operator-provisioned, credential-free disposable Linux VM.
The root process prepares mount/PID/network namespaces and cgroup v2 controls;
REA and its selected target execute as UID/GID 1001 with zero capabilities,
`no_new_privs`, immutable input mounts and a small writable tmpfs. The controller,
SQLite approval/audit records and storage janitor stay outside those namespaces.
This shares the VM's kernel; it is not a separate microVM for each capture or a
claim of resistance to kernel exploits. The outer VM isolates the operator host.

The requesting client is UID 1002 and can only use the fixed Unix request
protocol. `SO_PEERCRED`, not a message field, determines its role. Operator-only
`review`, `approve` and `revoke` require UID 0. The requesting client must not
be given operator tools or a host shell. The prototype does not implement an AI
agent, human account login, SSO, a network API or a privileged service installer.

The executable is always the existing REA `capture-process` CLI. Only the seven
curated modes produced by `prepare.mjs` qualify. There is no arbitrary command,
env dictionary, local-config file or raw MCP route in the request protocol.
Environment provenance and exact selected scenario bytes are retained privately
for approval. The fixture policy independently restricts base/explicit maps and
command coordinates; no credential-name guessing or secret scanner is used.

## Files and protocol

| File | Owner / purpose |
| --- | --- |
| `prepare.mjs` | Operator provisioning using REA's owning scenario parser and runtime-environment producer; no duplicated parser defaults |
| `controller.py` | Strict Unix protocol, peer roles, private intent/decision records, atomic consume-before-launch, external supervision and bounded public results |
| `worker.py` | Reviewed privileged namespace setup, fixed CLI entry point, UID/capability drop, runtime probes and private reporting pipe |
| `fixture.mjs` | Curated synthetic process behavior; no device, credentials, service or remote target |
| `acceptance.py` | Automated operator/client integration tests and private operator observations; no claim of human review |

Agent requests are exact objects: `propose` with `fixture`, or `execute`, `status`
and `cancel` with a controller-issued `requestId`. Unknown/duplicate fields deny.
Operator review returns the complete private intent and its digest. Approval
requires that digest and an explicit positive `ttl` no greater than 15 seconds,
within the raw deadline. Approval IDs never become caller capabilities.

An external result contains only the contract's fixed fields/statuses and opaque
IDs. `COMPLETED` means the capture workflow completed, not that the target exited
successfully or that every REA/provider capability is safe. A denied admission
has no run ID. A status query for an already started run conservatively returns
incomplete coverage; the prototype is not a durable result-delivery service.

## Reproduction prerequisites

Use a fresh nonpersistent VM with no exposed ports, no credentials or host
mounts, a finite session deadline and network deny-all during execution. The
recorded run used a pinned Node image, Node 24.18.0, npm 11.16.0, Python 3.14
stdlib and the unchanged npm lockfile. Dependency acquisition was limited to
official registries/repositories, with npm lifecycle scripts disabled.

Provision the public source under `/vercel/evaluation/rea`, the pinned Node
runtime under `/vercel/toolchain/node-v24.18.0-linux-x64`, worker UID/GID 1001 and
request-client UID/GID 1002. Build using the repository's documented command.
Enable cgroup CPU/memory/PID controllers after moving VM control processes into
a housekeeping child; do not move processes on an operator host. This requires
root and delegated cgroup v2/mount/network/PID namespace support. If any control
cannot be established, stop rather than weaken the worker.

`/run/rea-evaluation-vm` must be a root-owned private file containing exactly
`isolated-synthetic-only`. This startup guard prevents accidental invocation;
it is an operator assertion, not proof of isolation. Obtain actual VM/API and
kernel observations before creating it.

Inside that VM, provision the parser-derived registry and make source/runtime
trees root-owned and unwritable to both clients and targets. Keep their host
parent directories private to root; they are mounted explicitly into the worker.
Then run, with the pinned Node runtime on PATH:

```sh
node experiments/execution-controller/prepare.mjs /var/lib/rea-controller/registry.json
chmod 444 /var/lib/rea-controller/registry.json
python3 -m py_compile experiments/execution-controller/*.py
node_modules/.bin/oxfmt --check experiments/execution-controller/*.mjs
node_modules/.bin/oxlint experiments/execution-controller/*.mjs
python3 experiments/execution-controller/acceptance.py
```

The driver starts a temporary controller and invokes real Unix clients under
different kernel UIDs. Operator decisions are automated for these known fixtures.
It runs the real compiled CLI, inspects synthetic canonical output privately,
tests controller SIGKILL and restart, and writes a selected-observation report
to `/vercel/output/controller-acceptance.json`. It does not return raw capture
bytes to the requesting client. Privileged fault injection into a stored intent
or fixture tests binding; it is not proof that an agent can modify that state.

## Limits, retention and disposal

Each capture has one CPU of quota, 512 MiB whole-family memory, 64 PIDs,
16 MiB writable work tmpfs, 2 MiB per-file write limit, a 10-second external run
timeout and no network interface providing external access. The parent VM has
its separately recorded aggregate limits. These values are an evaluation
profile, not sizing or compatibility guarantees.

Pending raw intent expires 20 seconds after proposal; audit metadata expires
after 30 seconds. A successful/error/cancelled capture closes raw FDs, kills the
owned cgroup, removes its namespace/input/raw directory and clears raw intent/
digest/decision rows. A separate janitor observes controller death through a
pidfd, disposes outstanding runs and applies expiry. Per-run metric/lease files
expire with audit metadata. SQLite uses secure deletion, but no physical erasure
or provider-backup guarantee is made. Failed cleanup blocks the profile.

Startup now requires a private janitor acknowledgement within two seconds,
after private storage and schema checks. The controller opens its own pidfd
before spawning the janitor and passes that stable reference to the child;
no request socket is exposed before readiness. Missing, malformed or absent
acknowledgement fails closed and reaps the child. Janitor loss denies proposal,
approval and execution; an active capture detects that loss and disposes its
owned family. The private observer counter is published by atomic replacement.

**Known failed control:** killing the janitor itself leaves pending raw intent
and audit records past their deadlines. Blocking admission does not replace the
storage owner. Do not certify retention or enable this profile. The separate
[readiness follow-up](../../docs/verification/controller-janitor-2026-10-16.md)
records real startup/death tests and this failed expiry assertion. Its
`janitor_acceptance.py` intentionally exits nonzero while JR-09 fails. Private
janitor diagnostics remain operator-only and must be enumerated and removed
with the other evaluation copies before VM disposal.

The privileged test observer gets a bounded private capture window before
disposal, retains only selected synthetic facts/integrity observations for the
requested audit and can save private diagnostics on a failed smoke. Those test
artifacts are outside the agent API; enumerate and remove their raw diagnostic
copies before disposing the outer VM. Source, summary and this report can remain
in Git; raw intent/capture databases and provider artifacts must not be committed.

## Acceptance limits

Consult the [case-by-case runtime report](../../docs/verification/controller-prototype-2026-10-15.md)
and its evidence JSON. A partial case remains NOT_TESTED. In particular, do not
infer full resource-stress, sink-failure, failed-deletion or human-readiness
certification from a working positive capture. The original catalogue remains
the acceptance specification; its definition-time NOT_TESTED fields are not the
later runtime result store.

Keep production, unrestricted agents, arbitrary target inputs, native providers,
real credentials, raw export and platform integration unavailable. There is no
automatic merge, publication, deployment, background installation or go-live
action in this prototype.
