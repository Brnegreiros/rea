"""Real Linux retention fault tests, synthetic disposable VM only.

RR-04 expects a real failed deletion and checks retained ownership before
operator recovery. Its PASS does not certify deletion within that deadline.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import janitor_acceptance as harness

OUT = Path('/vercel/output/retention-acceptance.json')
CASES = []


def check(name, function):
    started = time.monotonic()
    try:
        facts = function()
        record = {'id': name, 'status': 'PASS', 'observation': facts,
                  'evidenceKind': 'REAL_LINUX_PEERS_SIGNALS_DEADLINES_AND_OWNED_HANDLES'}
    except Exception as error:
        record = {'id': name, 'status': 'FAIL', 'errorType': type(error).__name__,
                  'diagnostic': str(error)[:500]}
    record['wallSeconds'] = round(time.monotonic() - started, 3)
    CASES.append(record)
    OUT.write_text(json.dumps({'cases': CASES, 'summary': {
        s: sum(c['status'] == s for c in CASES) for s in ['PASS', 'FAIL', 'NOT_TESTED']},
        'scope': 'Single guard loss, original deadlines, restart block and failed-disposal ownership.',
        'productionAndUnrestrictedAgents': 'NO_GO'}, indent=2) + '\n')
    print(name, record['status'], flush=True)


def row(state, rid):
    with harness.database(state) as db:
        return db.execute('SELECT * FROM requests WHERE id=?', (rid,)).fetchone()


def approve(sock, state, fixture):
    response = harness.query(sock, {'op': 'propose', 'fixture': fixture})
    assert response['reasonCode'] == 'NO_APPROVAL', response
    rid = response['requestId']
    review = harness.query(sock, {'op': 'review', 'requestId': rid}, True)
    reply = harness.query(sock, {'op': 'approve', 'requestId': rid,
                                'digest': review['digest'], 'ttl': 12}, True)
    assert reply['decision'] == 'ALLOW'
    original = row(state, rid)
    return rid, {'issued': original['issued'], 'rawUntil': original['raw_until'],
                 'auditUntil': original['audit_until'], 'boot': original['boot']}


def ready():
    p, state, sock, primary = harness.launch('normal')
    harness.wait_for(lambda: Path(sock).exists(), 5)
    backup = int((state / 'guardian.pid').read_text())
    return p, state, sock, primary, backup


def raw_gone(state, rid):
    value = row(state, rid)
    return value is not None and value['intent'] is None and value['hash'] is None


def expiry(state, rid, original):
    # Observe the original request at its original audit deadline. No new TTL.
    harness.wait_for(lambda: time.time() > original['auditUntil'] + 0.25, 33)
    assert row(state, rid) is None
    with harness.database(state) as db:
        assert db.execute('SELECT count(*) FROM decisions WHERE request=?', (rid,)).fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM audit WHERE request=?', (rid,)).fetchone()[0] == 0
    return {'rawDeadlineSeconds': original['rawUntil'] - (original['auditUntil'] - 30),
            'auditDeadlineSeconds': 30, 'originalAuditDeadline': original['auditUntil'],
            'inspectedAt': time.time(), 'requestDecisionAuditAbsent': True}


def pending_loss(lose_backup=False):
    p, state, sock, primary, backup = ready()
    try:
        rid, original = approve(sock, state, 'basic')
        lost = backup if lose_backup else primary
        survivor = primary if lose_backup else backup
        os.kill(lost, signal.SIGKILL)
        harness.wait_for(lambda: raw_gone(state, rid), 4)
        assert (state / 'blocked').exists() and harness.alive(survivor)
        assert (state / 'launch-counter').read_text() == '0'
        value = row(state, rid)
        assert value['raw_until'] == original['rawUntil'] and value['audit_until'] == original['auditUntil']
        if lose_backup:
            harness.terminate(p)
        receipt = expiry(state, rid, original)
        assert lose_backup or p.poll() is None  # Variant keeps controller alive throughout expiry.
        return {'lost': 'standby' if lose_backup else 'primary',
                'controllerDuringExpiry': 'terminated' if lose_backup else 'alive',
                'rawClearedBeforeOriginalDeadline': True, 'noTtlRenewal': True,
                'actualReaLaunches': 0, 'expiry': receipt}
    finally:
        harness.terminate(p)


def active_loss(fail_disposal=False):
    p, state, sock, primary, backup = ready()
    mounted = None
    second = None
    try:
        rid, original = approve(sock, state, 'wait')
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(harness.query, sock, {'op': 'execute', 'requestId': rid})
            harness.wait_for(lambda: (state / 'launch-counter').read_text() == '1', 8)
            value = row(state, rid)
            run = value['run']
            directory = state / 'runs' / run
            group = Path('/sys/fs/cgroup') / ('rea-eval-' + run)
            if fail_disposal:
                mounted = directory / 'input'
                subprocess.run(['/usr/bin/mount', '--bind', str(mounted), str(mounted)], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=3)
            os.kill(primary, signal.SIGKILL)
            harness.terminate(p)
            try:
                future.result(timeout=4)
            except (AssertionError, ValueError, RuntimeError):
                pass  # Expected loss of the controller transport, not a fabricated result.
        harness.wait_for(lambda: raw_gone(state, rid), 5)
        assert (state / 'blocked').exists()
        assert harness.alive(backup)
        if fail_disposal:
            harness.wait_for(lambda: row(state, rid)['cleanup'] == 'FAILED', 4)
            harness.wait_for(lambda: time.time() > original['auditUntil'] + 0.25, 33)
            value = row(state, rid)
            lease = state / 'leases' / (original['boot'] + '-' + run + '.json')
            assert value is not None and value['cleanup'] == 'FAILED' and value['run'] == run
            assert value['intent'] is None and value['hash'] is None
            assert lease.exists() and directory.exists() and (state / 'blocked').exists()
            with harness.database(state) as db:
                assert db.execute('SELECT count(*) FROM decisions WHERE request=?', (rid,)).fetchone()[0] == 0
            failure = {'actualDeletion': 'FAILED_AT_DEADLINE', 'ownershipReceiptRetained': True,
                       'opaqueLeaseRetained': True, 'rawIntentCleared': True, 'profileBlocked': True,
                       'remainingHandle': 'owned run directory containing busy mount'}
            subprocess.run(['/usr/bin/umount', str(mounted)], check=True, timeout=3)
            mounted = None
            harness.wait_for(lambda: row(state, rid) is None and not directory.exists() and not group.exists(), 5)
            assert not lease.exists()
            return {'realFault': 'EBUSY from operator-created bind mount', 'failure': failure,
                    'recovery': 'Operator unmounted fault; surviving owner retried and verified removal.',
                    'retentionDeadlineVerdict': 'FAIL_UNDER_FORCED_DELETION_FAILURE_RECOVERED_LATE',
                    'testOracle': 'Detect failure, retain ownership, block and recover; not timely-deletion PASS.'}
        harness.wait_for(lambda: not directory.exists() and not group.exists(), 5)
        # Restart before original audit expiry. A blocked profile stays blocked.
        with (state / 'restart.log').open('ab') as log:
            second = subprocess.Popen([harness.sys.executable, str(harness.HERE / 'controller.py'),
                        '--state', str(state), '--app', str(harness.APP), '--runtime', harness.RUNTIME,
                        '--registry', str(harness.REGISTRY), '--socket', sock], stdout=log, stderr=log)
        # Old socket is stale; wait for a response from the new controller.
        denied = None
        until = time.monotonic() + 5
        while time.monotonic() < until:
            try:
                denied = harness.query(sock, {'op': 'execute', 'requestId': rid})
                break
            except (AssertionError, ValueError, OSError):
                time.sleep(0.03)
        assert denied and denied['status'] == 'DENIED' and denied['reasonCode'] == 'CONTROL_UNVERIFIED', denied
        assert (state / 'launch-counter').read_text() == '0'
        value = row(state, rid)
        assert value['audit_until'] == original['auditUntil'] and value['raw_until'] == original['rawUntil']
        receipt = expiry(state, rid, original)
        return {'primaryAndControllerSigkill': True, 'standbySurvived': True,
                'ownedFamilyAndRawHandleRemoved': True, 'restartDidNotReapproveOrLaunch': True,
                'blockedPersisted': True, 'noTtlRenewal': True, 'expiry': receipt}
    finally:
        if mounted is not None:
            subprocess.run(['/usr/bin/umount', str(mounted)], timeout=3, check=True)
        harness.terminate(p)
        if second is not None:
            harness.terminate(second)


def main():
    assert os.getuid() == 0 and Path('/run/rea-evaluation-vm').read_text().strip() == 'isolated-synthetic-only'
    check('RR-01', pending_loss)
    check('RR-02', lambda: pending_loss(True))
    check('RR-03', active_loss)
    check('RR-04', lambda: active_loss(True))
    if any(c['status'] == 'FAIL' for c in CASES):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
