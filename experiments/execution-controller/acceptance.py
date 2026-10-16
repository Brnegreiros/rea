"""Privileged synthetic acceptance driver, for a disposable VM only.

The operator side is automated test orchestration authenticated by the kernel
as UID 0. This is not evidence of a human review or production authorization.
No raw capture is returned to the agent client or included in the output report.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import traceback
import uuid

HERE = Path(__file__).resolve().parent
APP = HERE.parent.parent
RUNTIME = Path('/vercel/toolchain/node-v24.18.0-linux-x64')
REGISTRY = Path('/var/lib/rea-controller/registry.json')
STATE = Path('/var/lib/rea-controller/test-' + uuid.uuid4().hex)
SOCKET = '/run/rea-controller.sock'
CLIENT = '''import socket,sys
s=socket.socket(socket.AF_UNIX);s.settimeout(20);s.connect(sys.argv[1]);s.sendall(sys.stdin.buffer.read()+b'\\n')
f=s.makefile('rb');sys.stdout.buffer.write(f.readline(65537))
'''
pool = ThreadPoolExecutor(max_workers=4)
records = []
server = None


def call(message=None, role='agent', raw=None):
    data = raw if raw is not None else json.dumps(message)
    if role == 'operator':
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(20)
            client.connect(SOCKET)
            client.sendall(data.encode() + b'\n')
            return json.loads(client.makefile('rb').readline(65537))
    process = subprocess.run(['/usr/bin/setpriv', '--reuid=1002', '--regid=1002', '--clear-groups', '--no-new-privs',
                              '/usr/bin/python3', '-c', CLIENT, SOCKET], input=data.encode(),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
    if process.returncode:
        raise RuntimeError('agent transport terminated')
    return json.loads(process.stdout)


@contextmanager
def db():
    connection = sqlite3.connect(STATE / 'state.db', timeout=3)
    try:
        connection.row_factory = sqlite3.Row
        with connection:
            yield connection
    finally:
        connection.close()


def start():
    global server
    STATE.mkdir(mode=0o700, exist_ok=True)
    log = open(STATE / 'server.log', 'ab')
    server = subprocess.Popen([sys.executable, str(HERE / 'controller.py'), '--state', str(STATE),
                               '--app', str(APP), '--runtime', str(RUNTIME), '--registry', str(REGISTRY)],
                              stdin=subprocess.DEVNULL, stdout=log, stderr=log)
    log.close()
    for _ in range(100):
        if Path(SOCKET).exists():
            try:
                call({'op': 'propose', 'fixture': 'basic'})
                return
            except (OSError, ValueError, RuntimeError):
                pass
        if server.poll() is not None:
            raise RuntimeError('controller did not start')
        time.sleep(0.03)
    raise RuntimeError('controller socket not ready')


def count():
    return int((STATE / 'launch-counter').read_text())


def propose(fixture='basic', ttl=12):
    response = call({'op': 'propose', 'fixture': fixture})
    assert response['reasonCode'] == 'NO_APPROVAL', response
    request = response['requestId']
    review = call({'op': 'review', 'requestId': request}, 'operator')
    approval = call({'op': 'approve', 'requestId': request, 'digest': review['digest'], 'ttl': ttl}, 'operator')
    assert approval['decision'] == 'ALLOW', approval
    return request, review


def denied(message=None, raw=None):
    before = count()
    response = call(message, raw=raw)
    assert response['status'] == 'DENIED' and response['runId'] is None, response
    assert count() == before, 'denial launched REA'
    assert set(response) == {'contractVersion', 'requestId', 'runId', 'status', 'reasonCode', 'coverage', 'cleanupStatus'}
    assert 'SYNTHETIC_' not in json.dumps(response)
    if response['reasonCode'] != 'AUDIT_UNAVAILABLE':
        with db() as connection:
            assert connection.execute('SELECT count(*) FROM audit WHERE request=? AND event LIKE ?',
                                      (response['requestId'], 'denied_%')).fetchone()[0] > 0
    return response


def row_for(request):
    with db() as connection:
        return connection.execute('SELECT * FROM requests WHERE id=?', (request,)).fetchone()


def capture(fixture='basic'):
    request, _ = propose(fixture)
    before = count()
    future = pool.submit(call, {'op': 'execute', 'requestId': request})
    observed = None
    for _ in range(600):
        row = row_for(request)
        if row and row['run']:
            directory = STATE / 'runs' / row['run']
            if (directory / 'capture.done').exists():
                raw = (directory / 'raw/stdout.json').read_bytes()
                try:
                    document = json.loads(raw)
                except json.JSONDecodeError:
                    Path('/vercel/output/controller-private-debug.log').write_bytes((directory / 'raw/stderr.log').read_bytes())
                    raise AssertionError('CLI did not produce JSON; private stderr saved for operator diagnosis')
                text = raw.decode()
                if 'normalized_result' not in document:
                    Path('/vercel/output/controller-private-debug.log').write_bytes(raw + b'\nSTDERR\n' + (directory / 'raw/stderr.log').read_bytes())
                terminal = ''.join(frame.get('data', '') for frame in document.get('normalized_result', {}).get('frames', []))
                flags = None
                fixture_probe = None
                for line in terminal.splitlines():
                    if line.startswith('{') and '"empty"' in line:
                        flags = json.loads(line)
                    if line.startswith('{') and '"writeDenied"' in line:
                        fixture_probe = json.loads(line)
                probe = json.loads((directory / 'probe.json').read_text())
                reader = subprocess.run(['/usr/bin/setpriv', '--reuid=1002', '--regid=1002', '--clear-groups', '--no-new-privs',
                                         '/usr/bin/python3', '-c',
                                         'import sys\ntry: open(sys.argv[1],"rb").read(); print("UNEXPECTED_READ")\nexcept OSError as error: print(error.errno)',
                                         str(directory / 'raw/stdout.json')], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
                assert reader.returncode == 0 and reader.stdout == b'13\n', 'agent could access private raw capture'
                observed = {'rawSha256': hashlib.sha256(raw).hexdigest(), 'rawBytes': len(raw),
                            'agentRawReadDenied': True,
                            'canonicalEvidence': 'normalized_result' in document,
                            'explicitRetained': 'SYNTHETIC_EXPLICIT_CANARY' in text,
                            'ambientAbsent': 'SYNTHETIC_AMBIENT_CANARY' not in text,
                            'targetFlags': flags,
                            'fixtureProbe': fixture_probe,
                            'markedPlaceholder': '<redacted-input:' in text,
                            'markedEchoRetained': 'SYNTHETIC_MARKED_INPUT' in text,
                            'privateDiagnostic': 'SYNTHETIC_DIAGNOSTIC_CANARY' in text,
                            'probe': probe}
                break
        if future.done():
            break
        time.sleep(0.02)
    response = future.result(timeout=15)
    assert response['status'] == 'COMPLETED', response
    assert response['cleanupStatus'] == 'VERIFIED'
    assert count() - before == 1
    assert observed and observed['canonicalEvidence'], 'no canonical CLI Evidence observed'
    if fixture == 'basic':
        assert observed['targetFlags'] == {'explicit':'SYNTHETIC_EXPLICIT_CANARY','empty':True,'absent':True,'ambient':True,'owned':True}
        observed['targetFlags'] = {'allExpectedBooleans':True,'syntheticExplicitValueMatched':True}
    if fixture == 'probe':
        assert observed['fixtureProbe'] == {'denied':[True,True,True], 'writeDenied':True,
                                           'importWriteDenied':True,'networkDenied':True}, observed['fixtureProbe']
    assert observed['probe']['capEffZero'] and observed['probe']['noNewPrivs']
    assert observed['probe']['networkDenied'] and not observed['probe']['controllerVisible']
    assert not (STATE / 'runs' / response['runId']).exists()
    observed['resources'] = json.loads((STATE / (response['runId'] + '.metrics.json')).read_text())
    observed['rawDisposed'] = True
    return response, observed


def check(case_id, function, pending=None):
    started = time.monotonic()
    try:
        observation = function()
        record = {'id': case_id, 'status': 'NOT_TESTED' if pending else 'PASS',
                  'observation': observation, 'remaining': pending,
                  'evidenceKind': ('DECLARATION_ONLY_NO_RUNTIME_CONTROL' if case_id in ['EA-23', 'EA-28'] else
                                   'PARTIAL_REAL_LINUX_OBSERVATIONS' if pending else
                                   'REAL_LINUX_CONTROLLER_SOCKET_AND_KERNEL_BOUNDARIES')}
    except Exception as error:
        record = {'id': case_id, 'status': 'FAIL', 'errorType': type(error).__name__,
                  'diagnostic': str(error)[:700], 'traceback': traceback.format_exc(limit=4),
                  'remaining': 'Required observation failed; no readiness claim.'}
    record['wallSeconds'] = round(time.monotonic() - started, 3)
    records.append(record)
    print(case_id, record['status'], flush=True)
    save()


def save():
    Path('/vercel/output/controller-acceptance.json').write_text(json.dumps({
        'baseline': 'ecea596a7ccb8a822f7b3483737e6c34205d04e4',
        'cases': records, 'summary': {status: sum(r['status'] == status for r in records) for status in ['PASS','FAIL','NOT_TESTED']},
        'productionAndUnrestrictedAgents': 'NO_GO',
        'operatorReview': 'AUTOMATED_UID_0_TEST_ORCHESTRATION_NOT_HUMAN_REVIEW',
        'statePath': str(STATE), 'newRealCredentials': False,
    }, indent=2) + '\n')


def mutations(keys):
    request, review = propose()
    original = json.dumps(review['intent'], sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    for key in keys:
        changed = json.loads(original)
        cursor = changed
        path = key.split('.')
        for piece in path[:-1]:
            cursor = cursor[piece]
        cursor[path[-1]] = {'syntheticMutation': True}
        with db() as connection:
            connection.execute('UPDATE requests SET intent=? WHERE id=?',
                               (json.dumps(changed, sort_keys=True, separators=(',', ':')), request))
        response = denied({'op': 'execute', 'requestId': request})
        assert response['reasonCode'] == 'INTENT_CHANGED'
        with db() as connection:
            connection.execute('UPDATE requests SET intent=? WHERE id=?', (original, request))
    return {'mutationsRejected': keys, 'method': 'privileged stored-intent fault injection; independent peer isolation tested separately'}


def proposals(fields):
    for field in fields:
        denied({'op': 'propose', 'fixture': 'basic', field: 'SYNTHETIC_NEGATIVE_INPUT'})
    return {'strictRequestFieldsRejected': fields}


def stop_running(kind):
    request, _ = propose('wait', ttl=1 if kind == 'expiry' else 12)
    before = count()
    future = pool.submit(call, {'op': 'execute', 'requestId': request})
    for _ in range(300):
        if count() > before:
            break
        time.sleep(0.01)
    assert count() == before + 1
    if kind != 'expiry':
        call({'op': 'revoke' if kind == 'revoke' else 'cancel', 'requestId': request},
             'operator' if kind == 'revoke' else 'agent')
    response = future.result(timeout=15)
    assert response['status'] == 'CANCELLED' and response['cleanupStatus'] == 'VERIFIED', response
    assert not (Path('/sys/fs/cgroup') / ('rea-eval-' + response['runId'])).exists()
    return response['reasonCode']


def main():
    start()
    if '--smoke' in sys.argv:
        check('EA-01', lambda: capture()[1])
        server.terminate(); server.wait(timeout=5)
        return
    check('EA-01', lambda: capture()[1])
    check('EA-02', lambda: [proposals(['approved', 'approvalId', 'approval']),
                           denied({'op': 'execute', 'requestId': 'invented'}),
                           denied({'op': 'approve', 'requestId': 'invented', 'digest': 'invented', 'ttl': 12})])
    check('EA-03', lambda: proposals(['requesterId', 'operatorUid', 'supervisorApproval', 'targetInstructions']))
    check('EA-04', lambda: mutations(['command.executable','command.argv','command.cwd','target.sha256',
                                    'operation.scenario.arguments','operation.scenario.events','operation.scenario.terminal',
                                    'operation.scenario.filesystem_observation_paths','operation.scenario.timeout_ms','operation.scenario.normalization']))
    check('EA-05', lambda: mutations(['environment.base','environment.internal','environment.explicit','environment.parentProbe']))
    check('EA-06', lambda: mutations(['source.reaCommit','source.image','source.files','source.controllerBoot','worker.id','worker.platform','evidencePolicy.rawUntil','limits.memoryBytes']))
    def resource_identity():
        request, _ = propose()
        source = HERE / 'fixture.mjs'
        original = source.read_bytes()
        try:
            source.write_bytes(original + b'\n// privileged mutation test\n')
            assert denied({'op':'execute','requestId':request})['reasonCode'] == 'INTENT_CHANGED'
        finally:
            source.write_bytes(original)
        backup = source.with_suffix('.test-held')
        source.rename(backup)
        try:
            source.symlink_to(backup)
            assert denied({'op':'execute','requestId':request})['reasonCode'] == 'INTENT_CHANGED'
        finally:
            source.unlink()
            backup.rename(source)
        _, facts = capture('probe')
        return {'changedFixtureAndSymlinkDenied': True, 'immutableNamespace': facts['probe'],
                'targetWriteImportAndNetworkProbes':facts['fixtureProbe']}
    check('EA-07', resource_identity)
    def invalid_input():
        denied(raw='{"op":"propose","op":"execute","fixture":"basic"}')
        denied(raw='{"op":"propose","fixture":"basic","environment":{"X":"a","X":"b"}}')
        denied(raw='{malformed')
        denied(raw='{"op":[] ,"fixture":"basic"}')
        return proposals(['environment','platform','envOverrides','REA_PROCESS_RUN_ID','', '\x00', '='])
    check('EA-08', invalid_input)
    check('EA-09', lambda: capture()[1])
    check('EA-10', lambda: proposals(['envOverrides','config.env','SDKROOT','DEVELOPER_DIR','TOOLCHAINS','CLANG_MODULE_CACHE_PATH','REA_PROCESS_RUN_ID']))
    check('EA-11', lambda: proposals(['NODE_OPTIONS','LD_PRELOAD','PYTHONPATH','JAVA_TOOL_OPTIONS','PATH','HOME','LD_LIBRARY_PATH','DISPLAY']))
    check('EA-12', lambda: proposals(['environment','arguments','stdin','script','file','providerConfig','url','classification']))
    check('EA-13', lambda: [denied({'op':'propose','fixture':name}) for name in
                           ['frida','device','attach','lldb','ida','ghidra','browser','update','install','shell','root','remote']])
    def decision_lifetime():
        request, _ = propose(ttl=0.1)
        time.sleep(0.15)
        assert denied({'op':'execute','requestId':request})['reasonCode'] == 'EXPIRED'
        request, _ = propose()
        call({'op':'revoke','requestId':request}, 'operator')
        assert denied({'op':'execute','requestId':request})['reasonCode'] == 'REVOKED'
        request, _ = propose()
        with db() as connection:
            connection.execute('UPDATE requests SET issued=? WHERE id=?', (time.time()+60,request))
        assert denied({'op':'execute','requestId':request})['reasonCode'] == 'EXPIRED'
        return {'expiredRevokedFutureDenied':True}
    check('EA-14', decision_lifetime,
          'Restart/crash evidence is collected by EA-24; ambiguous consumed retry is covered by EA-15. Trusted-clock uncertainty is not injected here.')
    def concurrency():
        request, _ = propose()
        before = count()
        a = pool.submit(call, {'op':'execute','requestId':request})
        b = pool.submit(call, {'op':'execute','requestId':request})
        responses = [a.result(timeout=15), b.result(timeout=15)]
        assert sorted(r['status'] for r in responses) == ['COMPLETED','DENIED'], responses
        assert count() == before + 1
        denied({'op':'execute','requestId':request})
        return {'launches':1,'responses':[r['status'] for r in responses],'retryDenied':True}
    check('EA-15', concurrency)
    check('EA-16', lambda: {mode:stop_running(mode) for mode in ['revoke','cancel','expiry']},
          'Controller death is separately measured by EA-24; forced cleanup-failure retention/ownership branch is not dynamically certified.')
    def missing_control():
        request, _ = propose()
        previous = APP.stat().st_mode & 0o777
        try:
            os.chmod(APP,0o777)
            assert denied({'op':'execute','requestId':request})['reasonCode'] == 'CONTROL_UNVERIFIED'
        finally:
            os.chmod(APP,previous)
        return {'writableInputRootDenied':True}
    check('EA-17', missing_control,
          'Actual worker non-root/capability/filesystem/network probes run on positive captures; each missing CPU/memory/PID/disk/network enforcement is not independently fault-injected.')
    check('EA-18', lambda: {'disk':capture('disk')[1], 'cpu':capture('cpu')[1]},
          'Finite disk/file and CPU fixtures executed; memory/PID exhaustion and global evidence-quota failure are not stress-tested. Complete resource case remains NOT_TESTED.')
    def bypass():
        for name in ['tool','mcp','cli','nested','update','approve-from-target']:
            denied({'op':name,'requestId':'invented'})
        attempt = subprocess.run(['/usr/bin/setpriv','--reuid=1002','--regid=1002','--clear-groups','--no-new-privs',
                                  '/usr/bin/python3','-c','import sys;open(sys.argv[1]).read()', str(APP/'scripts/rea.mjs')],
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert attempt.returncode != 0
        return {'unsupportedRoutesDenied':True,'agentCannotReadOrInvokeCheckout':True}
    check('EA-19', bypass)
    def sink_check():
        response, facts = capture('error')
        with db() as connection:
            audit = json.dumps([tuple(row) for row in connection.execute('SELECT * FROM audit')])
        assert 'SYNTHETIC_' not in audit and 'SYNTHETIC_' not in json.dumps(response)
        assert facts['privateDiagnostic'] and facts['ambientAbsent']
        return {'auditAndAgentResponseExcludeRawCanaries':True,'rawObservedThenDisposed':facts}
    check('EA-20', sink_check)
    def echo():
        _, facts = capture('echo')
        assert facts['markedPlaceholder'] and facts['markedEchoRetained'], facts
        return facts
    check('EA-21', echo)
    def export_denial():
        for destination in ['public-git','ci-artifact','../escape','/tmp/link','shared-terminal','telemetry']:
            denied({'op':'export','destination':destination})
        denied({'op':'report','requestId':'invented'})
        _, facts = capture()
        return {'exportAndReportApiAbsent':True,'noCallerDestinationAccepted':True,
                'liveRawReadDeniedByUid':facts['agentRawReadDenied']}
    check('EA-22', export_denial)
    check('EA-23', lambda: {'implemented':False},
          'Separate approved derived-report workflow and transformation ledger are not implemented; raw Evidence is not rewritten.')
    def controller_death():
        request, _ = propose('wait')
        before = count()
        future = pool.submit(call, {'op':'execute','requestId':request})
        for _ in range(300):
            if count() > before: break
            time.sleep(0.01)
        row = row_for(request)
        assert row and row['run'] and count() == before + 1
        run = row['run']
        server.kill(); server.wait(timeout=5)
        try: future.result(timeout=5)
        except (RuntimeError, ValueError): pass
        for _ in range(300):
            row = row_for(request)
            if row and row['intent'] is None and not (STATE/'runs'/run).exists(): break
            time.sleep(0.02)
        assert row['intent'] is None and row['hash'] is None and row['cleanup'] == 'VERIFIED'
        assert not (STATE/'runs'/run).exists()
        assert not (Path('/sys/fs/cgroup')/('rea-eval-'+run)).exists()
        until = row['audit_until']
        while time.time() <= until + 0.3: time.sleep(0.1)
        assert row_for(request) is None
        with db() as connection:
            assert connection.execute('SELECT count(*) FROM audit WHERE request=?',(request,)).fetchone()[0] == 0
        start()
        denied({'op':'execute','requestId':request})
        return {'controllerSigkill':True,'independentJanitorStoppedFamily':True,'rawHandleRemoved':True,
                'auditAndDecisionExpired':True,'restartDidNotRestoreApproval':True,
                'scope':'controlled logical copies only; no physical erasure claim'}
    check('EA-24', controller_death)
    def blocked():
        (STATE/'blocked').touch()
        try: denied({'op':'propose','fixture':'basic'})
        finally: (STATE/'blocked').unlink()
        return {'operatorInjectedBlockedProfileDenies':True}
    check('EA-25', blocked,
          'Blocked-profile denial is real; unknown provider backups, failed deletion receipts and cleanup failures are not fully injected.')
    def audit_unavailable():
        path = STATE/'state.db'
        moved = STATE/'state.db.test-held'
        request, _ = propose()
        path.rename(moved)
        try:
            assert denied({'op':'execute','requestId':request})['reasonCode'] == 'AUDIT_UNAVAILABLE'
        finally:
            moved.rename(path)
            time.sleep(0.2)  # Let the independent storage owner record the failed profile.
            (STATE/'blocked').unlink(missing_ok=True)
        return {'missingDatabaseDeniedBeforeLaunch':True}
    check('EA-26', audit_unavailable,
          'Prelaunch audit unavailability exercised. Midrun full/disconnected audit and evidence sinks are not certified; NOT_TESTED for the complete case.')
    def boundaries():
        for path in [STATE/'state.db', STATE/'server.log']:
            attempt = subprocess.run(['/usr/bin/setpriv','--reuid=1002','--regid=1002','--clear-groups','--no-new-privs',
                                      '/usr/bin/python3','-c','import sys;open(sys.argv[1],"rb").read()',str(path)],
                                     stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            assert attempt.returncode != 0
        denied({'op':'approve','requestId':'forged','digest':'forged','ttl':10})
        return {'peerCredentialRoleEnforced':True,'privateStateUnreadableToAgentUid':True,'workerProbe':capture('probe')[1]['probe']}
    check('EA-27', boundaries)
    check('EA-28', lambda: {'productionAndUnrestrictedAgents':'NO_GO','acceptanceReportIsNotAnApprovalCapability':True},
          'No independent release/human-attestation gate is implemented. Partial catalogue and automated operator tests cannot establish readiness.')
    server.terminate(); server.wait(timeout=5)
    pool.shutdown(wait=True)
    save()


if __name__ == '__main__':
    try:
        main()
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            server.wait(timeout=5)
    if any(record['status'] == 'FAIL' for record in records):
        raise SystemExit(1)
