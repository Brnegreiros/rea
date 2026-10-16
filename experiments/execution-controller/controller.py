"""Experimental, Linux-only external capture controller. NOT a production service.

Run as root only INSIDE a disposable, credential-free evaluation VM. The agent
has a separate UID and a Unix request socket, never a host shell or approval DB.
Operator methods authenticate SO_PEERCRED UID 0; tests exercise that OS boundary,
not human review, IAM, native providers or arbitrary user-supplied programs.
"""
import argparse
from contextlib import contextmanager
import hashlib
import fcntl
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
BASELINE = 'ecea596a7ccb8a822f7b3483737e6c34205d04e4'
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


@contextmanager
def connect_db(state, timeout=3):
    # sqlite3.Connection.__exit__ commits/rolls back; it does not close the FD.
    # Bound ownership to this transaction, including setup/commit failures.
    connection = sqlite3.connect(f'file:{state}/state.db?mode=rw', uri=True, timeout=timeout)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA secure_delete=ON')
        connection.execute('PRAGMA max_page_count=2048')
        with connection:
            yield connection
    finally:
        connection.close()


def publish_launch_count(state, count):
    """Private observer metric: readers see an old or new whole integer."""
    temporary = Path(state) / 'launch-counter.next'
    temporary.write_text(str(count))
    temporary.replace(Path(state) / 'launch-counter')


class CaptureSink:
    """The external owner writes at most the approved bytes, through fixed files."""
    def __init__(self, directory, total_limit, file_limit):
        self.directory, self.total_limit, self.file_limit = directory, total_limit, file_limit
        self.files, self.identities, self.written = {}, {}, {'stdout': 0, 'stderr': 0}
        self.limit_hit = False
        try:
            for name, leaf in [('stdout', 'stdout.json'), ('stderr', 'stderr.log')]:
                stream = open(directory / leaf, 'wb', buffering=0)
                self.files[name] = stream
                info = os.fstat(stream.fileno())
                self.identities[name] = (info.st_dev, info.st_ino)
        except OSError:
            self.close()
            raise

    def check(self):
        for name, stream in self.files.items():
            leaf = 'stdout.json' if name == 'stdout' else 'stderr.log'
            info = (self.directory / leaf).lstat()
            current = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != self.identities[name] or \
                    current.st_nlink != 1 or current.st_size != self.written[name]:
                raise Denied('CONTROL_UNVERIFIED')

    def write(self, name, data):
        self.check()
        remaining = min(self.total_limit - sum(self.written.values()), self.file_limit - self.written[name])
        selected = memoryview(data)[:remaining]
        while selected:
            count = self.files[name].write(selected)
            if not count:
                raise OSError('evidence write made no progress')
            self.written[name] += count
            selected = selected[count:]
        if len(data) > remaining:
            self.limit_hit = True
        return not self.limit_hit

    def observations(self):
        return {'bytes': dict(self.written), 'totalBytes': sum(self.written.values()),
                'totalLimit': self.total_limit, 'fileLimit': self.file_limit, 'limitHit': self.limit_hit}

    def close(self):
        for stream in self.files.values():
            stream.close()


def kernel_snapshot(group):
    result = {}
    for name in ['memory.peak', 'memory.events', 'memory.max', 'memory.oom.group',
                 'pids.peak', 'pids.events', 'pids.max', 'cpu.stat', 'cpu.max']:
        try:
            result[name] = (group / name).read_text()
        except FileNotFoundError:
            pass  # An independent owner may already have removed this family.
    return result


def kernel_limit_hit(snapshot):
    memory = dict(line.split() for line in snapshot.get('memory.events', '').splitlines())
    pids = dict(line.split() for line in snapshot.get('pids.events', '').splitlines())
    return int(memory.get('oom_kill', 0)) > 0 or int(memory.get('oom', 0)) > 0 or int(pids.get('max', 0)) > 0


def stop_family(cgroup):
    path = Path(cgroup)
    if not path.exists():
        return True
    try:
        (path / 'cgroup.kill').write_text('1')
        for _ in range(100):
            if 'populated 0' in (path / 'cgroup.events').read_text():
                return True
            time.sleep(0.01)
    except FileNotFoundError:
        return not path.exists()  # Another owned disposer removed the empty cgroup.
    return False


def dispose_unlocked(row, state):
    """Fixed controller-owned paths only; never accept a caller deletion path."""
    run = row['run']
    if not run:
        return True
    try:
        group = Path('/sys/fs/cgroup') / ('rea-eval-' + run)
        if not stop_family(group):
            raise OSError('owned family still populated')
        # Release the verified empty family even if evidence deletion is busy.
        # The run/lease still owns failed raw disposal and keeps the profile shut.
        if group.exists():
            group.rmdir()
        root = Path(state) / 'runs' / run
        if root.exists():
            shutil.rmtree(root)
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


def dispose(row, state):
    # Controller settlement and expiry owner serialize the same fixed handles.
    lock = os.open(Path(state) / 'dispose.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        deadline = time.monotonic() + 2
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    (Path(state) / 'blocked').touch()
                    return False
                time.sleep(0.01)
        return dispose_unlocked(row, state)
    finally:
        os.close(lock)


def janitor(state, owner, pidfd, peer_fd, keepalive_fd, role, ready_fd):
    """One expiry owner plus one independent standby; no renewed deadlines.

    Lifetime flock owns cleanup, while private pipe EOF identifies loss of the
    exact peer. Parent copies are closed before admission. Neither process
    accepts a model-provided lease, PID, deadline or deletion path.
    """
    leader = os.open(state / (owner + '.retention.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    active = False
    poll = selectors.DefaultSelector()
    poll.register(pidfd, selectors.EVENT_READ, 'controller')
    poll.register(peer_fd, selectors.EVENT_READ, 'peer')
    try:
        for name in ['state.db', 'leases', 'runs']:
            info = (state / name).lstat()
            expected = stat.S_ISREG if name == 'state.db' else stat.S_ISDIR
            if not expected(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
                raise OSError('private storage ownership unverified')
        info = os.fstat(leader)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise OSError('retention lease ownership unverified')
        if role == 'primary':
            try:
                fcntl.flock(leader, fcntl.LOCK_EX | fcntl.LOCK_NB)
                active = True
            except BlockingIOError:
                if not any(key.data == 'controller' for key, _ in poll.select(timeout=0)):
                    raise
                # Parent died before primary startup; standby already owns expiry.
        elif role != 'standby':
            raise OSError('unknown retention role')
        with connect_db(state) as db:
            for table in ['requests', 'decisions', 'audit']:
                db.execute('SELECT * FROM ' + table + ' LIMIT 0')
        try:
            os.write(ready_fd, b'R')
        except BrokenPipeError:
            pass  # Still owns this boot's controlled copies if the parent died.
    finally:
        os.close(ready_fd)
    retired = False
    deadlines = {}
    while True:
        for key, _ in poll.select(timeout=0.05):
            retired = True
            (state / 'blocked').touch()
            poll.unregister(key.fileobj)
        if not active:
            if not retired:
                continue
            try:
                fcntl.flock(leader, fcntl.LOCK_EX | fcntl.LOCK_NB)
                active = True
            except BlockingIOError:
                continue
        try:
            with connect_db(state) as db:
                db.execute('BEGIN IMMEDIATE')
                rows = db.execute('SELECT * FROM requests WHERE boot=?', (owner,)).fetchall()
                for row in rows:
                    raw_deadline, audit_deadline = deadlines.setdefault(row['id'], (
                        time.monotonic() + max(0, row['raw_until'] - time.time()),
                        time.monotonic() + max(0, row['audit_until'] - time.time())))
                    if (row['intent'] is not None and (retired or time.monotonic() >= raw_deadline)) or row['cleanup'] == 'FAILED':
                        clean = dispose(row, state)
                        db.execute('UPDATE requests SET intent=NULL, hash=NULL, phase=?, cleanup=? WHERE id=?',
                                   ('expired', 'VERIFIED' if clean else 'FAILED', row['id']))
                        if time.monotonic() < audit_deadline:
                            db.execute('INSERT INTO audit VALUES (?,?,?,?,?)',
                                       (row['id'], 'raw_disposed' if clean else 'disposal_failed', time.time(), row['audit_until'], owner))
                        db.execute('DELETE FROM decisions WHERE request=?', (row['id'],))
                    # A failed disposal receipt never relinquishes ownership.
                    current = db.execute('SELECT cleanup FROM requests WHERE id=?', (row['id'],)).fetchone()
                    if time.monotonic() >= audit_deadline:
                        db.execute('DELETE FROM audit WHERE request=?', (row['id'],))
                        if current['cleanup'] == 'FAILED':
                            (state / 'blocked').touch()
                            continue  # Retain opaque run/owner receipt and lease; retry.
                        if row['run']:
                            for path in [state / f"{row['run']}.metrics.json",
                                         state / 'leases' / f"{owner}-{row['run']}.json"]:
                                path.unlink(missing_ok=True)
                        db.execute('DELETE FROM decisions WHERE request=?', (row['id'],))
                        db.execute('DELETE FROM requests WHERE id=?', (row['id'],))
                remaining = db.execute('SELECT count(*) FROM requests WHERE boot=?', (owner,)).fetchone()[0]
                db.execute('DELETE FROM audit WHERE owner=? AND expires<=?', (owner, time.time()))
                audits = db.execute('SELECT count(*) FROM audit WHERE owner=?', (owner,)).fetchone()[0]
            if retired and remaining == 0 and audits == 0:
                break
        except (sqlite3.Error, OSError) as error:
            print('RETENTION_FAILURE', type(error).__name__,
                  getattr(error, 'sqlite_errorname', 'IO_ERROR'), file=sys.stderr, flush=True)
            for lease in (state / 'leases').glob(owner + '-*.json'):
                info = decode(lease.read_text())
                stop_family('/sys/fs/cgroup/rea-eval-' + info['run'])
            (state / 'blocked').touch()
            # Keep the owner alive to retry; unknown deletion is never success.
    poll.close()
    for fd in [pidfd, peer_fd, keepalive_fd, leader]:
        os.close(fd)


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
        pidfd = os.pidfd_open(os.getpid())
        first_read, first_write = os.pipe()
        second_read, second_write = os.pipe()
        ready_a, notify_a = os.pipe()
        ready_b, notify_b = os.pipe()
        owned_fds = {pidfd, first_read, first_write, second_read, second_write,
                     ready_a, notify_a, ready_b, notify_b}
        self.janitor = self.guardian = None
        try:
            for role, peer, keepalive, notify, attribute in [
                    ('primary', second_read, first_write, notify_a, 'janitor'),
                    ('standby', first_read, second_write, notify_b, 'guardian')]:
                with (self.state / (attribute + '.log')).open('ab') as log:
                    process = subprocess.Popen(
                        [sys.executable, __file__, 'janitor', str(self.state), self.boot,
                         str(pidfd), str(peer), str(keepalive), role, str(notify)],
                        pass_fds=(pidfd, peer, keepalive, notify), stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL, stderr=log,
                        env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
                    setattr(self, attribute, process)
            for fd in [first_read, first_write, second_read, second_write, notify_a, notify_b]:
                os.close(fd)
                owned_fds.remove(fd)
            deadline = time.monotonic() + 2
            await_janitor(self.janitor, ready_a, max(0, deadline - time.monotonic()))
            await_janitor(self.guardian, ready_b, max(0, deadline - time.monotonic()))
        except (Denied, OSError):
            (self.state / 'blocked').touch()
            for process in [self.janitor, self.guardian]:
                if process is not None:
                    process.kill()
                    process.wait(timeout=2)
            raise Denied('CONTROL_UNVERIFIED')
        finally:
            for fd in owned_fds:
                os.close(fd)

    def event(self, db, request, event, expiry):
        db.execute('INSERT INTO audit VALUES (?,?,?,?,?)', (request, event, time.time(), expiry, self.boot))

    def denial(self, uid, message, reason):
        request = None
        expiry = time.time() + 30
        with connect_db(self.state) as db:
            candidate = message.get('requestId') if isinstance(message, dict) else None
            if isinstance(candidate, str):
                row = db.execute('SELECT id,requester,audit_until FROM requests WHERE id=?', (candidate,)).fetchone()
                if row is not None and (uid == 0 or uid == row['requester']):
                    request = row['id']
                    expiry = row['audit_until']
            request = request or uuid.uuid4().hex
            self.event(db, request, 'denied_' + reason, expiry)
        return result(request, reason=reason)

    def preflight(self):
        if self.janitor.poll() is not None or self.guardian.poll() is not None:
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
            if name not in ['basic','echo','wait','probe','disk','cpu','error','memory','pids','output','output-budget'] or \
                    scenario['environment'] != expected_explicit or scenario['executable'] != '/runtime/bin/node' or \
                    scenario['arguments'] != ['/app/experiments/execution-controller/fixture.mjs', name] or \
                    scenario['working_directory'] != '/work':
                raise Denied('POLICY_DENIED')
        for path in [self.app, self.runtime, self.registry_path]:
            mode = path.stat().st_mode
            if path.stat().st_uid != 0 or mode & 0o022:
                raise Denied('CONTROL_UNVERIFIED')
        for name in ['cgroup.kill', 'memory.max', 'memory.oom.group', 'pids.max', 'cpu.max']:
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
                                       'readerUid': 0, 'rawMaxBytes': 1048576, 'auditMaxPages': 2048}}
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
        if operation in ['approve', 'execute']:
            # Hash immutable runtime/policy inputs before acquiring the SQLite
            # writer transaction. Consumption below remains atomic and fresh.
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

    def prepare_evidence(self, directory):
        # Fixed owned path; privileged tests may provision a bounded filesystem
        # here. There is no caller-selected destination or fault flag.
        raw = directory / 'raw'
        raw.mkdir(mode=0o700)
        return raw

    def execute(self, request, run, plan, valid):
        group = Path('/sys/fs/cgroup') / ('rea-eval-' + run)
        directory = self.state / 'runs' / run
        read_fd = write_fd = None
        sink = worker = None
        reason, exit_code, captured_at, stage = 'NONE', None, None, 'SETUP'
        probe = None
        metrics, observed = {}, {}
        error_number = None
        sqlite_error = None
        clean = False
        selector = selectors.DefaultSelector()
        try:
            lease = self.state / 'leases' / f'{self.boot}-{run}.json'
            pending_lease = lease.with_suffix('.next')
            pending_lease.write_text(encoded({'run': run}))
            pending_lease.replace(lease)
            directory.mkdir(mode=0o700)
            (directory / 'root').mkdir()
            (directory / 'input').mkdir(mode=0o755)
            os.chmod(directory / 'input', 0o755)
            (directory / 'input/scenario.json').write_text(encoded(plan['operation']['scenario']))
            os.chmod(directory / 'input/scenario.json', 0o444)
            group.mkdir()
            enforcers = [('memory.max', str(plan['limits']['memoryBytes'])), ('memory.swap.max', '0'),
                         ('memory.oom.group', '1'), ('pids.max', str(plan['limits']['pids'])),
                         ('cpu.max', plan['limits']['cpuMax'])]
            for name, value in enforcers:
                (group / name).write_text(value)
                if (group / name).read_text().strip() != value:
                    raise Denied('CONTROL_UNVERIFIED')
            config = {'root': str(directory / 'root'), 'input': str(directory / 'input'),
                      'app': str(self.app), 'runtime': str(self.runtime), 'cgroup': str(group),
                      **plan['limits'], 'environment': plan['environment']['base'] | plan['environment']['parentProbe']}
            (directory / 'config.json').write_text(encoded(config))
            stage = 'EVIDENCE'
            sink = CaptureSink(self.prepare_evidence(directory), plan['evidencePolicy']['rawMaxBytes'],
                               plan['limits']['fileBytes'])
            read_fd, write_fd = os.pipe()
            os.set_blocking(read_fd, False)
            if time.time() >= valid:
                raise Denied('EXPIRED')
            worker = subprocess.Popen(
                ['/usr/bin/unshare', '--mount', '--pid', '--fork', '--kill-child=KILL', '--net',
                 sys.executable, str(Path(__file__).with_name('worker.py')), str(directory / 'config.json'), str(write_fd)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, pass_fds=(write_fd,),
                env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, start_new_session=True)
            os.close(write_fd)
            write_fd = None
            for name, stream in [('stdout', worker.stdout), ('stderr', worker.stderr)]:
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            selector.register(read_fd, selectors.EVENT_READ, 'report')
            pending = b''
            deadline = time.monotonic() + min(valid - time.time(), plan['limits']['wallSeconds'])
            while True:
                if self.janitor.poll() is not None or self.guardian.poll() is not None:
                    reason = 'CONTROL_UNVERIFIED'
                    break
                stage = 'EVIDENCE'
                sink.check()
                available = selector.select(timeout=0.02)
                for key, _ in available:
                    data = os.read(key.fd, 65536 if key.data != 'report' else 4096)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data != 'report':
                        stage = 'EVIDENCE'
                        if not sink.write(key.data, data):
                            reason = 'LIMIT_REACHED'
                            break
                        continue
                    pending += data
                    if len(pending) > 16384:
                        raise Denied('CONTROL_UNVERIFIED')
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        report = decode(line)
                        if 'probe' in report:
                            probe = report['probe']
                            (directory / 'probe.json').write_text(encoded(probe))
                            if report.get('failed'):
                                reason = 'CONTROL_UNVERIFIED'
                        if report.get('launched'):
                            with self.lock:
                                self.launches += 1
                                publish_launch_count(self.state, self.launches)
                            stage = 'AUDIT'
                            with connect_db(self.state, timeout=0.2) as db:
                                self.event(db, request, 'launched', plan['evidencePolicy']['auditUntil'])
                        if 'exitCode' in report:
                            exit_code = report['exitCode']
                metrics = kernel_snapshot(group)
                if kernel_limit_hit(metrics):
                    reason = 'LIMIT_REACHED'
                stage = 'AUDIT'
                with connect_db(self.state, timeout=0.2) as db:
                    row = db.execute('SELECT phase FROM requests WHERE id=?', (request,)).fetchone()
                    self.event(db, request, 'heartbeat', plan['evidencePolicy']['auditUntil'])
                if row is None or row['phase'] == 'revoked':
                    reason = 'REVOKED'
                # exitCode is sent after the real CLI has exited. Drain its
                # already-written pipe bytes before exposing capture.done.
                if exit_code is not None and captured_at is None and not available:
                    stage = 'EVIDENCE'
                    captured_at = time.monotonic()
                    (directory / 'capture.done').write_text(str(exit_code))
                if captured_at is None and time.monotonic() >= deadline:
                    reason = 'EXPIRED' if time.time() >= valid else 'LIMIT_REACHED'
                if captured_at is not None and time.monotonic() - captured_at >= 0.8:
                    break
                if reason != 'NONE' or worker.poll() is not None:
                    break
        except sqlite3.Error as error:
            sqlite_error = getattr(error, 'sqlite_errorname', 'SQLITE_ERROR')
            reason = 'AUDIT_UNAVAILABLE'
            (self.state / 'blocked').touch()
        except OSError as error:
            error_number = error.errno
            reason = 'AUDIT_UNAVAILABLE' if stage == 'AUDIT' else 'CONTROL_UNVERIFIED'
            (self.state / 'blocked').touch()
        except Denied as error:
            reason = str(error)
            if reason == 'CONTROL_UNVERIFIED':
                (self.state / 'blocked').touch()
        finally:
            selector.close()
            for fd in [read_fd, write_fd]:
                if fd is not None:
                    os.close(fd)
            if sink is not None:
                observed = sink.observations()
                sink.close()
            # Reconcile terminal kernel facts even if the worker died between
            # polling iterations (e.g. whole-family OOM).
            final_metrics = kernel_snapshot(group)
            if final_metrics:
                metrics = final_metrics
            if kernel_limit_hit(metrics) and reason == 'NONE':
                reason = 'LIMIT_REACHED'
            clean = dispose({'run': run}, self.state)
            if worker is not None:
                try:
                    worker.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait(timeout=2)
                    clean = False
                for stream in [worker.stdout, worker.stderr]:
                    stream.close()
            try:
                with connect_db(self.state, timeout=0.2) as db:
                    db.execute('UPDATE requests SET intent=NULL,hash=NULL,phase=?,cleanup=? WHERE id=?',
                               ('settled', 'VERIFIED' if clean else 'FAILED', request))
                    db.execute('DELETE FROM decisions WHERE request=?', (request,))
                    self.event(db, request, 'raw_disposed' if clean else 'disposal_failed', plan['evidencePolicy']['auditUntil'])
            except (sqlite3.Error, OSError):
                clean = False
                (self.state / 'blocked').touch()
            receipt = {'limits': plan['limits'], 'probe': probe, 'cgroup': metrics,
                       'exitCode': exit_code, 'cleanup': clean, 'reason': reason,
                       'evidence': observed, 'faultStage': stage if error_number is not None else None,
                       'osErrno': error_number, 'sqliteError': sqlite_error}
            try:
                (self.state / f'{run}.metrics.json').write_text(encoded(receipt))
            except OSError:
                clean = False
                (self.state / 'blocked').touch()
        if self.janitor.poll() is not None or self.guardian.poll() is not None:
            (self.state / 'blocked').touch()
            if reason == 'NONE':
                reason = 'CONTROL_UNVERIFIED'
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
            (self.server.controller.state / 'blocked').touch()
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
        janitor(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5]),
                int(sys.argv[6]), sys.argv[7], int(sys.argv[8]))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--state', required=True)
        parser.add_argument('--app', required=True)
        parser.add_argument('--runtime', required=True)
        parser.add_argument('--registry', required=True)
        parser.add_argument('--socket', default='/run/rea-controller.sock')
        serve(parser.parse_args())
