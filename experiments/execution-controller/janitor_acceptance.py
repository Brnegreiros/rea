"""VM-only readiness regression tests; never a readiness or human approval gate.

JR-01..04 substitute only the OS child startup at the privileged test boundary.
JR-05 freezes the real janitor before exec, then kills its exact parent. Other
cases use the unchanged controller and real Unix peers / Linux cgroups.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid

HERE = Path(__file__).resolve().parent
APP = HERE.parent.parent
RUNTIME = '/vercel/toolchain/node-v24.18.0-linux-x64'
ROOT = Path('/var/lib/rea-controller')
REGISTRY = ROOT / 'registry.json'
OUTPUT = Path('/vercel/output/janitor-acceptance.json')
CASES = []
LOST_STORES = []

# Injection exists only in this privileged driver, never in the socket policy.
STARTER = r'''
import importlib.util,json,os,signal,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('controller',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
state=Path(sys.argv[2]);mode=sys.argv[3];real=m.subprocess.Popen

def spawn(argv,**kwargs):
    if len(argv)>2 and argv[2]=='janitor':
        role=argv[-2]
        if role=='standby':
            if mode=='standby-silent': argv=[sys.executable,'-c','import time;time.sleep(10)']
            elif mode=='standby-wrong': argv=[sys.executable,'-c',f'import os,time;os.write({argv[-1]},b"X");time.sleep(10)']
            p=real(argv,**kwargs);(state/'guardian.pid').write_text(str(p.pid));return p
        if mode=='eof': argv=[sys.executable,'-c','pass']
        elif mode=='silent': argv=[sys.executable,'-c','import time;time.sleep(10)']
        elif mode=='wrong': argv=[sys.executable,'-c',f'import os,time;os.write({argv[-1]},b"X");time.sleep(10)']
        elif mode=='stopped': argv=[sys.executable,'-c','import os,signal,time;os.kill(os.getpid(),signal.SIGSTOP);time.sleep(10)']
        elif mode=='early-death': argv=[sys.executable,'-c','import os,signal,sys;os.kill(os.getpid(),signal.SIGSTOP);os.execv(sys.argv[1],sys.argv[1:])']+argv
        p=real(argv,**kwargs);(state/'janitor.pid').write_text(str(p.pid));return p
    return real(argv,**kwargs)
m.subprocess.Popen=spawn
m.serve(SimpleNamespace(state=str(state),app=sys.argv[4],runtime=sys.argv[5],registry=sys.argv[6],socket=sys.argv[7]))
'''


def wait_for(predicate, seconds=4):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if predicate(): return
        time.sleep(0.02)
    raise AssertionError('bounded observation timed out')


def launch(mode):
    state=ROOT/('janitor-test-'+uuid.uuid4().hex)
    state.mkdir(mode=0o700)
    sock='/run/rea-jr-'+uuid.uuid4().hex+'.sock'
    with (state/'server.log').open('wb') as log:
        p=subprocess.Popen([sys.executable,'-c',STARTER,str(HERE/'controller.py'),str(state),mode,
                            str(APP),RUNTIME,str(REGISTRY),sock],stdout=log,stderr=log)
    wait_for(lambda:(state/'janitor.pid').exists())
    return p,state,sock,int((state/'janitor.pid').read_text())


def query(sock,message,operator=False):
    client="""import socket,sys
s=socket.socket(socket.AF_UNIX);s.settimeout(15);s.connect(sys.argv[1]);s.sendall(sys.stdin.buffer.read()+b'\\n');sys.stdout.buffer.write(s.makefile('rb').readline(65537))"""
    args=[sys.executable,'-c',client,sock]
    if not operator: args=['/usr/bin/setpriv','--reuid=1002','--regid=1002','--clear-groups','--no-new-privs']+args
    p=subprocess.run(args,input=json.dumps(message).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=18)
    assert p.returncode==0,'peer transport failed'
    return json.loads(p.stdout)


@contextmanager
def database(state):
    c=sqlite3.connect(state/'state.db')
    try:
        c.row_factory=sqlite3.Row
        with c:yield c
    finally:c.close()


def alive(pid):
    try:
        return Path('/proc',str(pid),'stat').read_text().split(') ',1)[1].split()[0]!='Z'
    except FileNotFoundError:return False


def terminate(p):
    if p.poll() is None:p.kill()
    p.wait(timeout=4)


def check(name,kind,fn):
    start=time.monotonic()
    try:
        observation=fn()
        r={'id':name,'status':'PASS','evidenceKind':kind,'observation':observation}
    except Exception as error:
        r={'id':name,'status':'FAIL','errorType':type(error).__name__,'diagnostic':str(error)[:300]}
    r['wallSeconds']=round(time.monotonic()-start,3);CASES.append(r)
    OUTPUT.write_text(json.dumps({'cases':CASES,'summary':{s:sum(c['status']==s for c in CASES) for s in ['PASS','FAIL','NOT_TESTED']},
      'scope':'Janitor readiness regressions, separate from the 28 acceptance cases; synthetic VM only.',
      'retentionAfterPrimaryLoss':'JR-09 checks primary loss followed by controller termination while the independent standby survives.'},indent=2)+'\n')
    print(name,r['status'],flush=True)


def startup_failure(mode):
    p,state,sock,jpid=launch(mode)
    try:
        started=time.monotonic();p.wait(timeout=4)
        assert p.returncode!=0 and (state/'blocked').exists()
        assert not Path(sock).exists() and (state/'launch-counter').read_text()=='0'
        assert not alive(jpid)
        if (state/'guardian.pid').exists():
            assert not alive(int((state/'guardian.pid').read_text()))
        with database(state) as db:assert db.execute('SELECT count(*) FROM requests').fetchone()[0]==0
        return {'noSocket':True,'noRequests':True,'reaLaunches':0,'blocked':True,'childReaped':True,
                'boundedFailureSeconds':round(time.monotonic()-started,3)}
    finally:terminate(p)


def early_death():
    p,state,sock,jpid=launch('early-death')
    try:
        wait_for(lambda:Path('/proc',str(jpid),'stat').read_text().split(') ',1)[1].startswith('T'))
        assert not Path(sock).exists()
        # Privileged fault fixture, not a request admitted before readiness.
        with database(state) as db:
            owner=db.execute('SELECT count(*) FROM requests').fetchone()[0]
            assert owner==0
        # Read real janitor arguments from its stopped wrapper command line.
        args=Path('/proc',str(jpid),'cmdline').read_bytes().split(b'\0')
        index=args.index(b'janitor');boot=args[index+2].decode()
        now=time.time()
        with database(state) as db:
            db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       ('operator-injected',1002,boot,'synthetic-private', 'synthetic-digest','pending',now,0,now+2,now+2,None,'NOT_STARTED'))
        terminate(p);os.kill(jpid,signal.SIGCONT)
        wait_for(lambda:not alive(jpid),5)
        with database(state) as db:
            counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['requests','decisions','audit']}
        assert all(v==0 for v in counts.values()),counts
        assert not Path(sock).exists() and (state/'launch-counter').read_text()=='0'
        return {'parentKilledBeforeJanitorExec':True,'survivingOwnerObservedParentDeath':True,
                'injectedPrivateIntentExpired':True,'rows':counts,'reaLaunches':0,'noSocket':True}
    finally:
        terminate(p)
        if alive(jpid):os.kill(jpid,signal.SIGKILL)


def normal_death():
    p,state,sock,jpid=launch('normal')
    try:
        wait_for(lambda:Path(sock).exists())
        assert (state/'launch-counter').read_text()=='0'
        terminate(p);wait_for(lambda:not alive(jpid),4)
        return {'parentKilledAfterReadyBeforeFirstRequest':True,'janitorExited':True,'reaLaunches':0}
    finally:terminate(p)


def loss(active):
    p,state,sock,jpid=launch('normal')
    try:
        wait_for(lambda:Path(sock).exists())
        proposed=query(sock,{'op':'propose','fixture':'wait' if active else 'basic'});rid=proposed['requestId']
        review=query(sock,{'op':'review','requestId':rid},True)
        approval=query(sock,{'op':'approve','requestId':rid,'digest':review['digest'],'ttl':12},True)
        assert approval['decision']=='ALLOW'
        LOST_STORES.append(state)
        if active:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(query,sock,{'op':'execute','requestId':rid})
                wait_for(lambda:(state/'launch-counter').read_text()=='1',8)
                os.kill(jpid,signal.SIGKILL)
                response=future.result(timeout=5)
            assert response['reasonCode']=='CONTROL_UNVERIFIED' and response['status']=='INCOMPLETE',response
            assert response['cleanupStatus']=='VERIFIED'
            run=response['runId']
            assert not (state/'runs'/run).exists()
            assert not Path('/sys/fs/cgroup','rea-eval-'+run).exists()
            with database(state) as db:
                row=db.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
                assert row['intent'] is None and row['hash'] is None
        else:
            os.kill(jpid,signal.SIGKILL);wait_for(lambda:not alive(jpid))
            response=query(sock,{'op':'execute','requestId':rid})
            assert response['status']=='DENIED' and response['reasonCode']=='CONTROL_UNVERIFIED',response
            response=query(sock,{'op':'approve','requestId':rid,'digest':review['digest'],'ttl':12},True)
            assert response['status']=='DENIED' and response['reasonCode']=='CONTROL_UNVERIFIED',response
        response=query(sock,{'op':'propose','fixture':'basic'})
        assert response['status']=='DENIED' and response['reasonCode']=='CONTROL_UNVERIFIED'
        assert (state/'blocked').exists()
        return {'janitorSigkill':True,'profileBlocked':True,'activeFamilyRemoved':active,
                'reaLaunches':int((state/'launch-counter').read_text()),
                'retentionAfterPrimaryLoss':'Measured separately by JR-09, not certified by this subcase'}
    finally:terminate(p)


def retention_after_primary_loss():
    """Original-deadline assertion; a failed control must exit nonzero."""
    assert len(LOST_STORES)==2
    deadlines=[]
    for state in LOST_STORES:
        with database(state) as db:
            deadlines.extend(r[0] for r in db.execute('SELECT audit_until FROM requests'))
            deadlines.extend(r[0] for r in db.execute('SELECT expires FROM audit'))
    wait_for(lambda:time.time()>max(deadlines)+0.2,32)
    facts=[]
    for state in LOST_STORES:
        with database(state) as db:
            rows=db.execute('SELECT intent IS NOT NULL,raw_until,audit_until FROM requests').fetchall()
            facts.append({'state':str(state),'blocked':(state/'blocked').exists(),
                          'rawIntentsPastDeadline':sum(bool(r[0]) and time.time()>r[1] for r in rows),
                          'requestsPastAuditDeadline':sum(time.time()>r[2] for r in rows),
                          'auditRows':db.execute('SELECT count(*) FROM audit').fetchone()[0]})
    (OUTPUT.parent/'janitor-loss-retention-observation.json').write_text(json.dumps(facts,indent=2)+'\n')
    assert not any(f['rawIntentsPastDeadline'] or f['requestsPastAuditDeadline'] or f['auditRows'] for f in facts), \
        'Storage-owner loss left raw intent / audit past deadline; profile is blocked but expiry failed.'
    return facts


def atomic_counter():
    from controller import publish_launch_count
    with tempfile.TemporaryDirectory(prefix='rea-counter-',dir=ROOT) as directory:
        state=Path(directory)
        publish_launch_count(state,0)
        done=threading.Event()
        def read():
            samples=0;previous=0
            while not done.is_set():
                current=int((state/'launch-counter').read_text())
                assert current>=previous
                previous=current;samples+=1
            return samples
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(read)
            try:
                for value in range(1,1001):publish_launch_count(state,value)
            finally:done.set()
            samples=future.result(timeout=3)
        assert samples>0 and (state/'launch-counter').read_text()=='1000'
        return {'atomicPublications':1000,'concurrentReads':samples,'wholeMonotonicIntegers':True,
                'scope':'private metric producer; not approval authority or launch durability'}


def main():
    assert os.getuid()==0 and Path('/run/rea-evaluation-vm').read_text().strip()=='isolated-synthetic-only'
    for n,mode in enumerate(['eof','silent','wrong','stopped'],1):
        check('JR-%02d'%n,'PRIVILEGED_STARTUP_FAULT_WITH_REAL_CHILD_AND_FDS',lambda m=mode:startup_failure(m))
    check('JR-05','REAL_JANITOR_DELAYED_EXEC_AND_PARENT_SIGKILL_WITH_INJECTED_PRIVATE_ROW',early_death)
    check('JR-06','REAL_UNMODIFIED_CONTROLLER_AND_JANITOR',normal_death)
    check('JR-07','REAL_UNMODIFIED_CONTROLLER_AND_JANITOR',lambda:loss(False))
    check('JR-08','REAL_REA_CLI_WORKER_AND_JANITOR_SIGKILL',lambda:loss(True))
    check('JR-09','REAL_DEADLINES_AFTER_PRIMARY_LOSS_WITH_STANDBY',retention_after_primary_loss)
    check('JR-10','REAL_PRIVATE_METRIC_PRODUCER_WITH_CONCURRENT_READER',atomic_counter)
    check('JR-11','PRIVILEGED_STANDBY_STARTUP_FAULT_WITH_REAL_CHILD',lambda:startup_failure('standby-silent'))
    check('JR-12','PRIVILEGED_STANDBY_STARTUP_FAULT_WITH_REAL_CHILD',lambda:startup_failure('standby-wrong'))
    if any(c['status']=='FAIL' for c in CASES):raise SystemExit(1)


if __name__=='__main__':main()
