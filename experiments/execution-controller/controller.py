"""Experimental, Linux-only external capture controller. NOT a production service.

Run as root only INSIDE a disposable, credential-free evaluation VM. The agent
has a separate UID and a Unix request socket, never a host shell or approval DB.
Operator methods authenticate SO_PEERCRED UID 0; tests exercise that OS boundary,
not human review, IAM, native providers or arbitrary user-supplied programs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import socket
import socketserver
import sqlite3
import stat
import struct
import subprocess
import sys
import threading
import time
import uuid

VERSION = 'rea-evaluation-authorization/1'
BASELINE = '0140bc2882db8a86639a366faa10dd969ce1a4ef'
IMAGE = 'sha256:6ad1291a9fe7d243ee9f23626e6b08614a596431801c55e14cc5ee9d525f28d1'
AGENT_UID = 1002


class Denied(Exception):
    pass


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise Denied('POLICY_DENIED')
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Denied('POLICY_DENIED')))


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def digest(path):
    hashed = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            hashed.update(block)
    return hashed.hexdigest()


def result(request_id=None, run_id=None, status='DENIED', reason='POLICY_DENIED', cleanup='NOT_STARTED'):
    return {'contractVersion': VERSION, 'requestId': request_id or uuid.uuid4().hex,
            'runId': run_id, 'status': status, 'reasonCode': reason,
            'coverage': 'NOT_STARTED' if run_id is None else
                        ('SELECTED_PROFILE_ONLY' if status == 'COMPLETED' else 'INCOMPLETE'),
            'cleanupStatus': cleanup}


def connect_db(state):
    connection = sqlite3.connect(f'file:{state}/state.db?mode=rw', uri=True, timeout=3)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA secure_delete=ON')
    connection.execute('PRAGMA max_page_count=2048')
    return connection


def publish_launch_count(state, count):
    """Private observer metric: readers see an old or new whole integer."""
    temporary = Path(state) / 'launch-counter.next'
    temporary.write_text(str(count))
    temporary.replace(Path(state) / 'launch-counter')


def stop_family(cgroup):
    path = Path(cgroup)
    if not path.exists():
        return True
    (path / 'cgroup.kill').write_text('1')
    for _ in range(100):
        if 'populated 0' in (path / 'cgroup.events').read_text():
            return True
        time.sleep(0.01)
    return False


def dispose(row, state):
    """Fixed controller-owned paths only; never accept a caller deletion path."""
    run = row['run']
    if not run:
        return True
    try:
        group = Path('/sys/fs/cgroup') / ('rea-eval-' + run)
        if not stop_family(group):
            raise OSError('owned family still populated')
        root = Path(state) / 'runs' / run
        if root.exists():
            shutil.rmtree(root)
        if group.exists():
            group.rmdir()
        return not root.exists() and not group.exists()
    except OSError:
        (Path(state) / 'blocked').touch()
        return False


def await_janitor(process, ready_fd, timeout=2):
    """A live child and its private byte are both required before admission."""
    with selectors.DefaultSelector() as ready:
        ready.register(ready_fd, selectors.EVENT_READ)
        if not ready.select(timeout) or os.read(ready_fd, 2) != b'R' or process.poll() is not None:
            raise Denied('CONTROL_UNVERIFIED')


def janitor(state, owner, pidfd, ready_fd):
    """Separate storage owner; survives controller termination, bounded by TTL."""
    poll = selectors.DefaultSelector()
    poll.register(pidfd, selectors.EVENT_READ)
    # The parent opens its own pidfd BEFORE fork. Even an early death or PID
    # reuse cannot redirect this janitor to an unrelated process.
    try:
        for name in ['state.db', 'leases', 'runs']:
            info = (state / name).lstat()
            expected = stat.S_ISREG if name == 'state.db' else stat.S_ISDIR
            if not expected(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
                raise OSError('private storage ownership unverified')
        with connect_db(state) as db:
            for table in ['requests', 'decisions', 'audit']:
                db.execute('SELECT * FROM ' + table + ' LIMIT 0')
        dead = bool(poll.select(timeout=0))
        if not dead:
            try:
                os.write(ready_fd, b'R')
            except BrokenPipeError:
                dead = True
    finally:
        os.close(ready_fd)
    deadlines = {}
    while True:
        dead = dead or bool(poll.select(timeout=0.05))
        try:
            with connect_db(state) as db:
                db.execute('BEGIN IMMEDIATE')
                rows = db.execute('SELECT * FROM requests WHERE boot=?', (owner,)).fetchall()
                for row in rows:
                    raw_deadline, audit_deadline = deadlines.setdefault(row['id'], (
                        time.monotonic() + max(0, row['raw_until'] - time.time()),
                        time.monotonic() + max(0, row['audit_until'] - time.time())))
                    if row['intent'] is not None and (dead or time.monotonic() >= raw_deadline):
                        clean = dispose(row, state)
                        db.execute('UPDATE requests SET intent=NULL, hash=NULL, phase=?, cleanup=? WHERE id=?',
                                   ('expired', 'VERIFIED' if clean else 'FAILED', row['id']))
                        db.execute('INSERT INTO audit VALUES (?,?,?,?,?)',
                                   (row['id'], 'raw_disposed' if clean else 'disposal_failed', time.time(), row['audit_until'], owner))
                        db.execute('DELETE FROM decisions WHERE request=?', (row['id'],))
                    if time.monotonic() >= audit_deadline:
                        if row['run']:
                            for path in [Path(state) / f"{row['run']}.metrics.json",
                                         Path(state) / 'leases' / f"{owner}-{row['run']}.json"]:
                                path.unlink(missing_ok=True)
                        db.execute('DELETE FROM audit WHERE request=?', (row['id'],))
                        db.execute('DELETE FROM decisions WHERE request=?', (row['id'],))
                        db.execute('DELETE FROM requests WHERE id=?', (row['id'],))
                remaining = db.execute('SELECT count(*) FROM requests WHERE boot=?', (owner,)).fetchone()[0]
                db.execute('DELETE FROM audit WHERE owner=? AND expires<=?', (owner, time.time()))
                audits = db.execute('SELECT count(*) FROM audit WHERE owner=?', (owner,)).fetchone()[0]
            if dead and remaining == 0 and audits == 0:
                break
        except (sqlite3.Error, OSError) as error:
            print('RETENTION_FAILURE', type(error).__name__,
                  getattr(error, 'sqlite_errorname', 'IO_ERROR'), file=sys.stderr, flush=True)
            # Fail closed independently of a broken DB: remove live workers
            # owned by this boot from the small immutable run-lease files.
            for lease in (Path(state) / 'leases').glob(owner + '-*.json'):
                info = decode(lease.read_text())
                stop_family('/sys/fs/cgroup/rea-eval-' + info['run'])
            (Path(state) / 'blocked').touch()
            if dead:
                break  # UNKNOWN retention; never claim deletion or keep retrying forever.
    poll.close()
    os.close(pidfd)


class Controller:
    def __init__(self, state, app, runtime, registry):
        self.state, self.app, self.runtime = Path(state), Path(app), Path(runtime)
        self.registry_path = Path(registry)
        self.registry = decode(self.registry_path.read_text())
        self.boot = uuid.uuid4().hex
        self.wall, self.mono = time.time(), time.monotonic()
        self.launches = 0
        self.lock = threading.Lock()
        self.policy_files = [Path(__file__), Path(__file__).with_name('worker.py'),
                             Path(__file__).with_name('fixture.mjs'), self.registry_path,
                             Path(__file__).with_name('prepare.mjs'), self.app / 'package.json',
                             self.app / 'package-lock.json', self.app / 'scripts/rea.mjs',
                             self.runtime / 'bin/node']
        self.fingerprint = {str(p): digest(p) for p in self.policy_files}
        self.identities = {str(p): (p.stat().st_dev, p.stat().st_ino) for p in self.policy_files}
        self.state.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.state, 0o700)
        for name in ['runs', 'leases']:
            (self.state / name).mkdir(mode=0o700, exist_ok=True)
        db = sqlite3.connect(self.state / 'state.db')
        db.executescript('''
          PRAGMA secure_delete=ON;
          PRAGMA max_page_count=2048;
          CREATE TABLE IF NOT EXISTS requests (
            id TEXT PRIMARY KEY, requester INTEGER, boot TEXT, intent TEXT, hash TEXT,
            phase TEXT, issued REAL, valid REAL, raw_until REAL, audit_until REAL,
            run TEXT, cleanup TEXT);
          CREATE TABLE IF NOT EXISTS audit (request TEXT, event TEXT, at REAL, expires REAL, owner TEXT);
          CREATE TABLE IF NOT EXISTS decisions (request TEXT PRIMARY KEY, approval TEXT,
            operator INTEGER, decision TEXT, hash TEXT, worker TEXT, issued REAL, valid REAL);
        ''')
        db.close()
        os.chmod(self.state / 'state.db', 0o600)
        publish_launch_count(self.state, 0)
        ready_fd, notify_fd = os.pipe()
        pidfd = os.pidfd_open(os.getpid())
        self.janitor = None
        try:
            with (self.state / 'janitor.log').open('ab') as log:
                self.janitor = subprocess.Popen(
                    [sys.executable, __file__, 'janitor', str(self.state), self.boot, str(pidfd), str(notify_fd)],
                    pass_fds=(pidfd, notify_fd), stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=log,
                    env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
            os.close(notify_fd)
            notify_fd = None
            await_janitor(self.janitor, ready_fd)
        except (Denied, OSError):
            (self.state / 'blocked').touch()
            if self.janitor is not None:
                self.janitor.kill()
                self.janitor.wait(timeout=2)
            raise Denied('CONTROL_UNVERIFIED')
        finally:
            os.close(ready_fd)
            os.close(pidfd)
            if notify_fd is not None:
                os.close(notify_fd)

    def event(self, db, request, event, expiry):
        db.execute('INSERT INTO audit VALUES (?,?,?,?,?)', (request, event, time.time(), expiry, self.boot))

    def denial(self, uid, message, reason):
        request = None
        with connect_db(self.state) as db:
            candidate = message.get('requestId') if isinstance(message, dict) else None
            if isinstance(candidate, str):
                row = db.execute('SELECT id,requester FROM requests WHERE id=?', (candidate,)).fetchone()
                if row is not None and (uid == 0 or uid == row['requester']):
                    request = row['id']
            request = request or uuid.uuid4().hex
            self.event(db, request, 'denied_' + reason, time.time() + 30)
        return result(request, reason=reason)

    def preflight(self):
        if self.janitor.poll() is not None:
            (self.state / 'blocked').touch()
        if (self.state / 'blocked').exists() or os.getuid() != 0:
            raise Denied('CONTROL_UNVERIFIED')
        if abs((time.time() - self.wall) - (time.monotonic() - self.mono)) > 1:
            raise Denied('CONTROL_UNVERIFIED')
        for path, identity in self.identities.items():
            info = Path(path).lstat()
            if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != identity:
                raise Denied('INTENT_CHANGED')
        if any(digest(path) != expected for path, expected in self.fingerprint.items()):
            raise Denied('INTENT_CHANGED')
        if self.registry['fixtureSha256'] != self.fingerprint[str(Path(__file__).with_name('fixture.mjs'))]:
            raise Denied('INTENT_CHANGED')
        # This is intentionally a fixed fixture policy, not a generic env API.
        expected_base = {'PATH':'/runtime/bin:/usr/bin:/bin', 'HOME':'/work', 'TMPDIR':'/work',
                         'LANG':'C.UTF-8', 'TERM':'xterm'}
        expected_explicit = {'SYNTHETIC_VALUE':'SYNTHETIC_EXPLICIT_CANARY', 'EMPTY':''}
        if self.registry['base'] != expected_base:
            raise Denied('POLICY_DENIED')
        for name, scenario in self.registry['profiles'].items():
            if name not in ['basic','echo','wait','probe','disk','cpu','error'] or \
                    scenario['environment'] != expected_explicit or scenario['executable'] != '/runtime/bin/node' or \
                    scenario['arguments'] != ['/app/experiments/execution-controller/fixture.mjs', name] or \
                    scenario['working_directory'] != '/work':
                raise Denied('POLICY_DENIED')
        for path in [self.app, self.runtime, self.registry_path]:
            mode = path.stat().st_mode
            if path.stat().st_uid != 0 or mode & 0o022:
                raise Denied('CONTROL_UNVERIFIED')
        for name in ['cgroup.kill', 'memory.max', 'pids.max', 'cpu.max']:
            if not (Path('/sys/fs/cgroup') / name).exists():
                raise Denied('CONTROL_UNVERIFIED')

    def dispatch(self, uid, message):
        if not isinstance(message, dict) or uid not in [0, AGENT_UID]:
            raise Denied('POLICY_DENIED')
        operation = message.get('op')
        allowed = {'propose': {'op', 'fixture'}, 'execute': {'op', 'requestId'},
                   'status': {'op', 'requestId'}, 'cancel': {'op', 'requestId'},
                   'review': {'op', 'requestId'}, 'approve': {'op', 'requestId', 'digest', 'ttl'},
                   'revoke': {'op', 'requestId'}}
        if operation not in allowed or set(message) != allowed[operation]:
            raise Denied('OUT_OF_SCOPE')
        if operation in ['review', 'approve', 'revoke'] and uid != 0:
            raise Denied('POLICY_DENIED')
        if operation in ['propose', 'execute', 'status', 'cancel'] and uid != AGENT_UID:
            raise Denied('POLICY_DENIED')
        if operation == 'propose':
            self.preflight()
            name = message['fixture']
            if not isinstance(name, str) or name not in self.registry['profiles']:
                raise Denied('OUT_OF_SCOPE')
            request = uuid.uuid4().hex
            now = time.time()
            plan = {'contractVersion': VERSION, 'requestId': request, 'requesterId': f'uid:{uid}',
                    'operation': {'entryPoint': 'capture-process', 'capability': 'capture_process_scenario',
                                  'scenario': self.registry['profiles'][name]},
                    'source': {'reaCommit': BASELINE, 'image': IMAGE, 'controllerBoot': self.boot,
                               'files': self.fingerprint},
                    'worker': {'id': uuid.uuid4().hex, 'platform': 'linux', 'uid': 1001},
                    'command': {'executable': '/runtime/bin/node', 'sha256': digest(self.runtime / 'bin/node'),
                                'argv': self.registry['profiles'][name]['arguments'], 'cwd': '/work'},
                    'target': {'fixture': name, 'sha256': self.registry['fixtureSha256']},
                    'environment': {'base': self.registry['base'], 'internal': {},
                                    'explicit': self.registry['profiles'][name]['environment'],
                                    'parentProbe': {'UNRELATED_AMBIENT': 'SYNTHETIC_AMBIENT_CANARY'},
                                    'classification': 'operator-provisioned-curated-synthetic'},
                    'limits': {'memoryBytes': 536870912, 'pids': 64, 'cpuMax': '100000 100000',
                               'diskBytes': 16777216, 'fileBytes': 2097152, 'wallSeconds': 10, 'network': 'deny-all'},
                    'evidencePolicy': {'rawUntil': now + 20, 'auditUntil': now + 30, 'rawExport': False,
                                       'readerUid': 0, 'rawMaxBytes': 8388608, 'auditMaxPages': 2048}}
            intent = encoded(plan)
            with connect_db(self.state) as db:
                if db.execute('SELECT count(*) FROM requests').fetchone()[0] >= 128:
                    raise Denied('LIMIT_REACHED')
                db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                           (request, uid, self.boot, intent, hashlib.sha256(intent.encode()).hexdigest(),
                            'pending', now, 0, now + 20, now + 30, None, 'NOT_STARTED'))
                self.event(db, request, 'proposed', now + 30)
            return result(request, reason='NO_APPROVAL')
        request = message['requestId']
        if not isinstance(request, str):
            raise Denied('POLICY_DENIED')
        if operation == 'approve':
            self.preflight()
        with connect_db(self.state) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM requests WHERE id=?', (request,)).fetchone()
            if row is None or (uid != 0 and row['requester'] != uid):
                raise Denied('NO_APPROVAL')
            if operation == 'review':
                return {'intent': decode(row['intent']) if row['intent'] else None, 'digest': row['hash']}
            if operation == 'approve':
                ttl = message['ttl']
                if row['phase'] != 'pending' or not isinstance(ttl, (int, float)) or isinstance(ttl, bool):
                    raise Denied('POLICY_DENIED')
                if message['digest'] != row['hash'] or not 0 < ttl <= 15 or time.time() + ttl > row['raw_until']:
                    raise Denied('INTENT_CHANGED')
                approval, issued = uuid.uuid4().hex, time.time()
                db.execute('UPDATE requests SET phase=?,issued=?,valid=? WHERE id=?',
                           ('approved', issued, issued + ttl, request))
                db.execute('INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?)',
                           (request, approval, uid, 'ALLOW', row['hash'], decode(row['intent'])['worker']['id'], issued, issued + ttl))
                self.event(db, request, 'approved', row['audit_until'])
                return {'decision': 'ALLOW', 'requestId': request, 'approvalId': approval}
            if operation in ['revoke', 'cancel']:
                db.execute('UPDATE requests SET phase=? WHERE id=?', ('revoked', request))
                self.event(db, request, 'revoked', row['audit_until'])
                return result(request, row['run'], status='CANCELLED', reason='REVOKED', cleanup=row['cleanup'])
            if operation == 'status':
                return result(request, row['run'], status='INCOMPLETE' if row['run'] else 'DENIED',
                              reason='NO_APPROVAL' if row['phase'] == 'pending' else 'CONSUMED', cleanup=row['cleanup'])
            self.preflight()
            if row['boot'] != self.boot:
                raise Denied('INTENT_CHANGED')
            if row['phase'] == 'revoked':
                raise Denied('REVOKED')
            if row['phase'] != 'approved':
                raise Denied('NO_APPROVAL' if row['phase'] == 'pending' else 'CONSUMED')
            if not row['intent'] or time.time() >= row['valid'] or time.time() < row['issued']:
                raise Denied('EXPIRED')
            if hashlib.sha256(row['intent'].encode()).hexdigest() != row['hash']:
                raise Denied('INTENT_CHANGED')
            decision = db.execute('SELECT * FROM decisions WHERE request=?', (request,)).fetchone()
            if decision is None or decision['operator'] != 0 or decision['decision'] != 'ALLOW' or \
                    decision['hash'] != row['hash'] or decision['worker'] != decode(row['intent'])['worker']['id'] or \
                    decision['issued'] != row['issued'] or decision['valid'] != row['valid']:
                raise Denied('INTENT_CHANGED')
            run = uuid.uuid4().hex
            db.execute('UPDATE requests SET phase=?,run=? WHERE id=?', ('consumed', run, request))
            self.event(db, request, 'consumed', row['audit_until'])
        # The SQLite transaction commits consumption and audit before any fork.
        return self.execute(request, run, decode(row['intent']), row['valid'])

    def execute(self, request, run, plan, valid):
        group = Path('/sys/fs/cgroup') / ('rea-eval-' + run)
        directory = self.state / 'runs' / run
        directory.mkdir(mode=0o700)
        (directory / 'root').mkdir()
        (directory / 'input').mkdir(mode=0o755)
        os.chmod(directory / 'input', 0o755)
        (directory / 'input/scenario.json').write_text(encoded(plan['operation']['scenario']))
        os.chmod(directory / 'input/scenario.json', 0o444)
        group.mkdir()
        for name, value in [('memory.max', str(plan['limits']['memoryBytes'])), ('memory.swap.max', '0'),
                            ('pids.max', str(plan['limits']['pids'])), ('cpu.max', plan['limits']['cpuMax'])]:
            (group / name).write_text(value)
        config = {'root': str(directory / 'root'), 'input': str(directory / 'input'),
                  'app': str(self.app), 'runtime': str(self.runtime), 'cgroup': str(group),
                  **plan['limits'], 'environment': plan['environment']['base'] | plan['environment']['parentProbe']}
        (directory / 'config.json').write_text(encoded(config))
        (self.state / 'leases' / f'{self.boot}-{run}.json').write_text(encoded({'run': run}))
        read_fd, write_fd = os.pipe()
        os.set_blocking(read_fd, False)
        reason, exit_code, captured_at = 'NONE', None, None
        probe = None
        worker = None
        try:
            if time.time() >= valid:
                raise Denied('EXPIRED')
            with open(directory / 'stdout.json', 'wb') as out, open(directory / 'stderr.log', 'wb') as err:
                worker = subprocess.Popen(
                    ['/usr/bin/unshare', '--mount', '--pid', '--fork', '--kill-child=KILL', '--net',
                     sys.executable, str(Path(__file__).with_name('worker.py')), str(directory / 'config.json'), str(write_fd)],
                    stdout=out, stderr=err, stdin=subprocess.DEVNULL, pass_fds=(write_fd,),
                    env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, start_new_session=True)
                os.close(write_fd)
                write_fd = None
                pending = b''
                deadline = time.monotonic() + min(valid - time.time(), plan['limits']['wallSeconds'])
                while True:
                    if self.janitor.poll() is not None:
                        (self.state / 'blocked').touch()
                        reason = 'CONTROL_UNVERIFIED'
                        break
                    try:
                        pending += os.read(read_fd, 4096)
                    except BlockingIOError:
                        pass
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        report = decode(line)
                        if 'probe' in report:
                            probe = report['probe']
                            (directory / 'probe.json').write_text(encoded(probe))
                            if report.get('failed'):
                                reason = 'CONTROL_UNVERIFIED'
                                break
                        if report.get('launched'):
                            with self.lock:
                                self.launches += 1
                                publish_launch_count(self.state, self.launches)
                            with connect_db(self.state) as db:
                                self.event(db, request, 'launched', plan['evidencePolicy']['auditUntil'])
                        if 'exitCode' in report:
                            exit_code, captured_at = report['exitCode'], time.monotonic()
                            (directory / 'capture.done').write_text(str(exit_code))
                    with connect_db(self.state) as db:
                        state = db.execute('SELECT phase FROM requests WHERE id=?', (request,)).fetchone()
                        self.event(db, request, 'heartbeat', plan['evidencePolicy']['auditUntil'])
                    if state is None or state['phase'] == 'revoked':
                        reason = 'REVOKED'
                    if out.tell() + err.tell() >= plan['evidencePolicy']['rawMaxBytes']:
                        reason = 'LIMIT_REACHED'
                    if captured_at is None and time.monotonic() >= deadline:
                        reason = 'EXPIRED' if time.time() >= valid else 'LIMIT_REACHED'
                    if captured_at is not None and time.monotonic() - captured_at >= 0.8:
                        break  # Operator test observer gets a bounded private inspection window.
                    if reason != 'NONE' or worker.poll() is not None:
                        break
                    time.sleep(0.05)
            # Close every parent raw FD before disposal; the helper/target FDs
            # are closed by the cgroup kill. No stdout is returned to the agent.
        except (sqlite3.Error, OSError):
            reason = 'AUDIT_UNAVAILABLE'
        except Denied as error:
            reason = str(error)
        finally:
            os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)
            metrics = {p: (group / p).read_text() for p in ['memory.peak', 'memory.events', 'cpu.stat', 'pids.events'] if (group / p).exists()}
            clean = dispose({'run': run}, self.state)
            if worker is not None:
                try:
                    worker.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait(timeout=2)
                    clean = False
            try:
                with connect_db(self.state) as db:
                    db.execute('UPDATE requests SET intent=NULL,hash=NULL,phase=?,cleanup=? WHERE id=?',
                               ('settled', 'VERIFIED' if clean else 'FAILED', request))
                    db.execute('DELETE FROM decisions WHERE request=?', (request,))
                    self.event(db, request, 'raw_disposed' if clean else 'disposal_failed', plan['evidencePolicy']['auditUntil'])
            except sqlite3.Error:
                clean = False
            # Private metadata: no raw bytes, argv, environment values or diagnostics.
            (self.state / f'{run}.metrics.json').write_text(encoded({'limits': plan['limits'], 'probe': probe, 'cgroup': metrics,
                                                                  'exitCode': exit_code, 'cleanup': clean}))
        if not clean:
            (self.state / 'blocked').touch()
            return result(request, run, 'INCOMPLETE', 'CLEANUP_UNVERIFIED', 'FAILED')
        if reason != 'NONE':
            return result(request, run, 'CANCELLED' if reason in ['REVOKED', 'EXPIRED'] else 'INCOMPLETE', reason, 'VERIFIED')
        return result(request, run, 'COMPLETED' if exit_code == 0 else 'FAILED', 'NONE', 'VERIFIED')


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        uid = struct.unpack('3i', self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[1]
        message = None
        try:
            raw = self.rfile.readline(65538)
            if not raw.endswith(b'\n') or len(raw) > 65536:
                raise Denied('POLICY_DENIED')
            message = decode(raw)
            response = self.server.controller.dispatch(uid, message)
        except Denied as error:
            try:
                response = self.server.controller.denial(uid, message, str(error))
            except (sqlite3.Error, OSError):
                response = result(reason='AUDIT_UNAVAILABLE')
        except (ValueError, TypeError, KeyError):
            try:
                response = self.server.controller.denial(uid, message, 'POLICY_DENIED')
            except (sqlite3.Error, OSError):
                response = result(reason='AUDIT_UNAVAILABLE')
        except (sqlite3.Error, OSError):
            response = result(reason='AUDIT_UNAVAILABLE')
        try:
            self.wfile.write((encoded(response) + '\n').encode())
        except BrokenPipeError:
            pass


def serve(args):
    if os.getuid() != 0:
        raise SystemExit('Use only inside the disposable evaluation VM as operator/root.')
    marker = Path('/run/rea-evaluation-vm')
    if not marker.is_file() or marker.stat().st_uid != 0 or marker.stat().st_mode & 0o077 or \
            marker.read_text().strip() != 'isolated-synthetic-only':
        raise SystemExit('Missing private operator-created VM marker; refuse accidental host execution.')
    os.umask(0o077)
    controller = Controller(args.state, args.app, args.runtime, args.registry)
    path = Path(args.socket)
    if path.exists():
        path.unlink()
    with socketserver.ThreadingUnixStreamServer(str(path), Handler) as server:
        server.controller = controller
        os.chmod(path, 0o666)
        server.serve_forever(poll_interval=0.05)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'janitor':
        janitor(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--state', required=True)
        parser.add_argument('--app', required=True)
        parser.add_argument('--runtime', required=True)
        parser.add_argument('--registry', required=True)
        parser.add_argument('--socket', default='/run/rea-controller.sock')
        serve(parser.parse_args())
