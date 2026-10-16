"""Bounded resource/storage fault tests; only inside a synthetic disposable VM.

The tiny-evidence launcher changes the privileged filesystem provisioning
boundary, not the agent protocol or REA result. All errors come from actual
Linux cgroups, SQLite and filesystem operations, never mocked return values.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import errno
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import traceback

import janitor_acceptance as harness
import retention_acceptance as retention

OUT = Path('/vercel/output/resource-acceptance.json')
CASES = []
EXPIRIES = []
POOL = ThreadPoolExecutor(max_workers=12)
ORIGINAL_STARTER = harness.STARTER
FAULT_PROVISION = r'''
if mode=='tiny-evidence':
    original_prepare=m.Controller.prepare_evidence
    def provision(self,directory):
        raw=original_prepare(self,directory)
        subprocess.run(['/usr/bin/mount','-t','tmpfs','-o','size=262144,mode=700','tmpfs',str(raw)],check=True)
        (state/'fault-mount').write_text(str(raw))
        return raw
    m.Controller.prepare_evidence=provision
'''
harness.STARTER = ORIGINAL_STARTER.replace('m.serve(', FAULT_PROVISION+'\nm.serve(', 1)


def save():
    OUT.write_text(json.dumps({'cases': CASES, 'summary': {
        s: sum(c['status'] == s for c in CASES) for s in ['PASS','FAIL','NOT_TESTED']},
        'scope':'Fixed synthetic CLI fixtures; real bounded kernel/storage faults; no production readiness.',
        'productionAndUnrestrictedAgents':'NO_GO'}, indent=2)+'\n')


def check(name, fn):
    started=time.monotonic()
    try:
        facts=fn()
        record={'id':name,'status':'PASS','observation':facts,
                'evidenceKind':'REAL_LINUX_CLI_KERNEL_SQLITE_FILESYSTEM'}
    except Exception as error:
        record={'id':name,'status':'FAIL','errorType':type(error).__name__,'diagnostic':str(error)[:600], 'trace':traceback.format_exc(limit=6)[-1000:]}
    record['wallSeconds']=round(time.monotonic()-started,3)
    CASES.append(record);save();print(name,record['status'],flush=True)


def ready(mode='normal'):
    p,state,sock,primary=harness.launch(mode)
    harness.wait_for(lambda:Path(sock).exists(),5)
    return p,state,sock


def approve(sock,state,fixture):
    return retention.approve(sock,state,fixture)


def snapshot(state,rid):
    value=retention.row(state,rid)
    return value


def receipt(state,run):
    path=state/(run+'.metrics.json')
    harness.wait_for(path.exists,4)
    return json.loads(path.read_text())


def expiry_observer(state,rid,original,run):
    harness.wait_for(lambda:time.time()>original['auditUntil']+0.5,34)
    assert retention.row(state,rid) is None
    with harness.database(state) as db:
        assert db.execute('SELECT count(*) FROM audit WHERE request=?',(rid,)).fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM decisions WHERE request=?',(rid,)).fetchone()[0]==0
    if run:
        assert not (state/'runs'/run).exists()
        assert not list((state/'leases').glob('*-'+run+'.json'))
        assert not (state/(run+'.metrics.json')).exists()
    return {'state':str(state),'requestId':rid,'originalAuditDeadline':original['auditUntil'],
            'inspectedAt':time.time(),'rowsAndOwnedHandlesAbsent':True,'toleranceSeconds':0.5}


def finish(p,state,rid,original,run):
    value=retention.row(state,rid)
    if value:
        assert value['raw_until']==original['rawUntil'] and value['audit_until']==original['auditUntil']
    harness.terminate(p)
    EXPIRIES.append(POOL.submit(expiry_observer,state,rid,original,run))


def no_raw_reply(reply):
    assert set(reply)=={'contractVersion','requestId','runId','status','reasonCode','coverage','cleanupStatus'}
    assert 'SYNTHETIC_' not in json.dumps(reply)


def counts(text):
    return {key:int(value) for key,value in (line.split() for line in text.splitlines())}


def resource(fixture):
    p,state,sock=ready()
    rid=original=run=None
    try:
        rid,original=approve(sock,state,fixture)
        started=time.monotonic()
        if fixture=='output-budget':
            future=POOL.submit(harness.query,sock,{'op':'execute','requestId':rid})
            observed=None
            until=time.monotonic()+12
            while time.monotonic()<until:
                value=snapshot(state,rid)
                if value and value['run']:
                    run=value['run'];directory=state/'runs'/run
                    if (directory/'capture.done').exists():
                        raw=(directory/'raw/stdout.json').read_bytes()
                        doc=json.loads(raw)
                        normalized=doc['normalized_result']
                        observed={'canonicalTruncated':normalized['truncated'],
                                  'truncationDetails':normalized['truncation_details'],
                                  'rawBytes':len(raw),'rawSha256':hashlib.sha256(raw).hexdigest()}
                        assert observed['canonicalTruncated'] is True
                        break
                if future.done():break
                time.sleep(0.02)
            reply=future.result(timeout=15)
            assert observed and reply['status']=='COMPLETED' and reply['coverage']=='SELECTED_PROFILE_ONLY',reply
        else:
            reply=harness.query(sock,{'op':'execute','requestId':rid})
            assert reply['status'] in ['INCOMPLETE','CANCELLED'] and reply['reasonCode'] in ['LIMIT_REACHED','EXPIRED'],reply
            observed=None
        no_raw_reply(reply);run=reply['runId'];facts=receipt(state,run)
        assert reply['cleanupStatus']=='VERIFIED' and not (state/'runs'/run).exists()
        assert not Path('/sys/fs/cgroup','rea-eval-'+run).exists()
        assert int((state/'launch-counter').read_text())==1
        assert facts['evidence']['totalBytes']<=facts['evidence']['totalLimit']==1048576
        if fixture=='memory':
            assert counts(facts['cgroup']['memory.events'])['oom_kill']>0,facts
            assert facts['cgroup']['memory.max'].strip()=='536870912'
            assert facts['cgroup']['memory.oom.group'].strip()=='1'
        elif fixture=='pids':
            assert counts(facts['cgroup']['pids.events'])['max']>0,facts
            assert int(facts['cgroup']['pids.peak'])<=64
        elif fixture=='output':
            assert facts['evidence']['limitHit'] and facts['evidence']['totalBytes']==1048576,facts
        elif fixture=='wait':
            assert time.monotonic()-started<13
        return {'fixture':fixture,'response':reply,'metrics':facts,'canonicalObservation':observed,
                'elapsedSeconds':round(time.monotonic()-started,3),'actualReaLaunches':1,
                'controlledFamilyAndRawRemoved':True}
    finally:
        if rid and original:finish(p,state,rid,original,run)
        else:harness.terminate(p)


def unmount(path):
    if path.name=='state.db':
        subprocess.run(['/usr/bin/mount','-o','remount,bind,rw',str(path)],check=True,timeout=3)
    until=time.monotonic()+3
    while True:
        outcome=subprocess.run(['/usr/bin/umount',str(path)],stderr=subprocess.PIPE,timeout=3)
        if outcome.returncode==0:return
        if time.monotonic()>=until:
            raise OSError('operator fault mount remained busy; ownership retained: '+str(path))
        time.sleep(0.03)


def storage(kind):
    p,state,sock=ready('tiny-evidence' if kind=='evidence-full' else 'normal')
    rid=original=run=None
    held=None;mounted=None;fill=None;outside=None
    try:
        rid,original=approve(sock,state,'output' if kind=='evidence-full' else 'wait')
        if kind=='prelaunch-audit-missing':
            held=state/'state.db.held';(state/'state.db').rename(held)
            reply=harness.query(sock,{'op':'execute','requestId':rid})
            assert reply['status']=='DENIED' and reply['runId'] is None and (state/'launch-counter').read_text()=='0',reply
            held.rename(state/'state.db');held=None
            assert (state/'blocked').exists()
            return {'fault':kind,'response':reply,'actualReaLaunches':0,'profileBlocked':True}
        future=POOL.submit(harness.query,sock,{'op':'execute','requestId':rid})
        harness.wait_for(lambda:(state/'launch-counter').read_text()=='1',8)
        value=snapshot(state,rid);run=value['run'];directory=state/'runs'/run
        injected=None
        if kind=='audit-missing':
            held=state/'state.db.held';(state/'state.db').rename(held)
            injected='database path disconnected by privileged operator rename'
        elif kind=='audit-full':
            with closing(sqlite3.connect(state/'state.db',timeout=2,isolation_level=None)) as db:
                db.execute('PRAGMA max_page_count=2048')
                db.execute('CREATE TABLE synthetic_fill(value BLOB)')
                for _ in range(160):
                    try:db.execute('INSERT INTO synthetic_fill VALUES (zeroblob(65536))')
                    except sqlite3.DatabaseError as error:
                        assert error.sqlite_errorcode==sqlite3.SQLITE_FULL,error
                        injected=error.sqlite_errorname;break
            assert injected=='SQLITE_FULL'
            fill=True
        elif kind=='evidence-disconnected':
            outside=state/'outside-sentinel'
            outside.write_text('SYNTHETIC_UNTOUCHED_SENTINEL')
            path=directory/'raw/stdout.json';path.rename(directory/'raw/stdout.held')
            path.symlink_to(outside)
            injected='raw output path replaced by symlink; original open inode lost its named handle'
        elif kind=='audit-readonly':
            mounted=state/'state.db'
            subprocess.run(['/usr/bin/mount','--bind',str(mounted),str(mounted)],check=True,timeout=3)
            subprocess.run(['/usr/bin/mount','-o','remount,bind,ro',str(mounted)],check=True,timeout=3)
            injected='actual read-only bind mount on SQLite database'
        elif kind=='evidence-full':
            harness.wait_for(lambda:(state/'fault-mount').exists(),3)
            mounted=Path((state/'fault-mount').read_text())
            injected='actual ENOSPC on isolated 256 KiB evidence tmpfs; audit filesystem unaffected'
        reply=future.result(timeout=15)
        no_raw_reply(reply)
        assert reply['status']=='INCOMPLETE' and reply['coverage']=='INCOMPLETE',reply
        assert (state/'blocked').exists(),'profile not blocked'
        assert not Path('/sys/fs/cgroup','rea-eval-'+run).exists()
        facts=receipt(state,run)
        if kind=='evidence-full':
            assert facts['osErrno']==errno.ENOSPC and facts['faultStage']=='EVIDENCE',facts
            assert facts['evidence']['totalBytes']<=262144
            assert reply['cleanupStatus']=='FAILED',reply  # Busy mount is still owned, not silently discarded.
            assert directory.exists() and list((state/'leases').glob('*-'+run+'.json'))
        if outside is not None:
            assert outside.read_text()=='SYNTHETIC_UNTOUCHED_SENTINEL'
            outside.unlink();outside=None
        # Restore only the operator's fault, never clear the blocked profile or renew TTL.
        if held is not None:held.rename(state/'state.db');held=None
        if fill:
            with closing(sqlite3.connect(state/'state.db',timeout=3)) as db:db.execute('DROP TABLE synthetic_fill')
            fill=None
        if mounted is not None:
            unmount(mounted);mounted=None
        harness.terminate(p)
        harness.wait_for(lambda:not (state/'runs'/run).exists(),5)
        return {'fault':kind,'injected':injected,'response':reply,'metrics':facts,
                'profileBlocked':True,'actualReaLaunches':1,'rawRemovedAfterFaultRecovery':True,
                'operatorOnlyRestoredFault':True,'noDestinationLeak':True}
    finally:
        if held is not None:held.rename(state/'state.db')
        if fill:
            with closing(sqlite3.connect(state/'state.db',timeout=3)) as db:db.execute('DROP TABLE IF EXISTS synthetic_fill')
        if mounted is not None:unmount(mounted)
        if outside is not None:outside.unlink(missing_ok=True)
        if rid and original:finish(p,state,rid,original,run)
        else:harness.terminate(p)


def retention_checks():
    facts=[future.result(timeout=35) for future in EXPIRIES]
    POOL.shutdown(wait=True)
    return {'originalDeadlineInspections':facts,'noTtlRenewal':True,'scope':'Original request audit/decision/run handles; independent denials retain their own bounded deadline.'}


def main():
    assert os.getuid()==0 and Path('/run/rea-evaluation-vm').read_text().strip()=='isolated-synthetic-only'
    for case,fixture in [('RS-01','memory'),('RS-02','pids'),('RS-03','output-budget'),('RS-04','output'),('RS-05','wait')]:
        check(case,lambda f=fixture:resource(f))
    for case,kind in [('SF-01','prelaunch-audit-missing'),('SF-02','audit-missing'),('SF-03','audit-full'),
                      ('SF-04','evidence-disconnected'),('SF-05','evidence-full'),('SF-06','audit-readonly')]:
        check(case,lambda k=kind:storage(k))
    check('SF-07',retention_checks)
    if any(c['status']=='FAIL' for c in CASES):raise SystemExit(1)


if __name__=='__main__':main()
