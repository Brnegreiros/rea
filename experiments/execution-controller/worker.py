"""Privileged namespace setup only. Run inside a disposable evaluation VM.

No request-selected command is accepted here. The only project entry point is
the compiled REA capture CLI, using a previously parsed, immutable scenario.
"""
import ctypes
import json
import os
from pathlib import Path
import resource
import socket
import subprocess
import sys
import time


def command(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)


def mount(source, destination, *options):
    destination.mkdir(parents=True, exist_ok=True)
    command('/usr/bin/mount', *options, str(source), str(destination))


def main():
    config = json.loads(Path(sys.argv[1]).read_text())
    root = Path(config['root'])
    report_fd = int(sys.argv[2])
    Path(config['cgroup'], 'cgroup.procs').write_text(str(os.getpid()))
    command('/usr/bin/mount', '--make-rprivate', '/')
    mount('tmpfs', root, '-t', 'tmpfs', '-o', 'size=2m,mode=755')
    for source, target in [(config['app'], 'app'), (config['runtime'], 'runtime'),
                           (config['input'], 'input'), ('/usr', 'usr'),
                           ('/lib', 'lib'), ('/lib64', 'lib64'), ('/bin', 'bin')]:
        if Path(source).exists():
            mount(source, root / target, '--bind')
            command('/usr/bin/mount', '-o', 'remount,bind,ro', str(root / target))
    mount('tmpfs', root / 'work', '-t', 'tmpfs', '-o', f"size={config['diskBytes']},mode=1777")
    mount('tmpfs', root / 'dev', '-t', 'tmpfs', '-o', 'size=1m,mode=755')
    for name, minor in [('null', 3), ('zero', 5), ('random', 8), ('urandom', 9)]:
        os.mknod(root / 'dev' / name, 0o20666, os.makedev(1, minor))
        os.chmod(root / 'dev' / name, 0o666)
    mount('devpts', root / 'dev/pts', '-t', 'devpts', '-o', 'newinstance,ptmxmode=0666,mode=0620')
    os.symlink('pts/ptmx', root / 'dev/ptmx')
    mount('proc', root / 'proc', '-t', 'proc', '-o', 'nosuid,nodev,noexec')
    (root / 'etc').mkdir()
    os.chmod(root / 'etc', 0o755)
    (root / 'etc/passwd').write_text('rea:x:1001:1001:synthetic worker:/work:/bin/false\n')
    (root / 'etc/group').write_text('rea:x:1001:\n')
    (root / 'etc/nsswitch.conf').write_text('passwd: files\ngroup: files\nhosts: files\n')
    (root / 'etc/ssl').mkdir()
    os.chmod(root / 'etc/ssl', 0o755)
    (root / 'etc/ssl/openssl.cnf').write_text('# Isolated synthetic runtime: no external includes.\n')
    for path in ['etc/passwd', 'etc/group', 'etc/nsswitch.conf', 'etc/ssl/openssl.cnf']:
        os.chmod(root / path, 0o444)
    os.symlink('work', root / 'tmp')
    command('/usr/bin/mount', '-o', 'remount,ro', str(root))
    os.chroot(root)
    os.chdir('/work')
    os.setgroups([])
    libc = ctypes.CDLL(None, use_errno=True)
    for capability in range(41):
        libc.prctl(24, capability, 0, 0, 0)  # PR_CAPBSET_DROP
    os.setgid(1001)
    os.setuid(1001)
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        raise OSError(ctypes.get_errno(), 'no_new_privs')
    libc.prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE: protect init's reporting FD.
    resource.setrlimit(resource.RLIMIT_FSIZE, (config['fileBytes'], config['fileBytes']))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    status = Path('/proc/self/status').read_text()
    probe = {'uid': os.getuid(), 'gid': os.getgid(),
             'capEffZero': 'CapEff:\t0000000000000000' in status,
             'noNewPrivs': 'NoNewPrivs:\t1' in status,
             'controllerVisible': Path('/run/rea-controller.sock').exists(),
             'appWritable': os.access('/app', os.W_OK),
             'rootWritable': os.access('/', os.W_OK),
             'scenarioReadable': os.access('/input/scenario.json', os.R_OK),
             'workWritable': os.access('/work', os.W_OK)}
    try:
        with socket.create_connection(('1.1.1.1', 443), timeout=0.3):
            probe['networkDenied'] = False
    except OSError:
        probe['networkDenied'] = True
    if not (probe['uid'] == 1001 and probe['gid'] == 1001
            and probe['capEffZero'] and probe['noNewPrivs']
            and not probe['controllerVisible'] and not probe['appWritable']
            and not probe['rootWritable'] and probe['scenarioReadable']
            and probe['workWritable'] and probe['networkDenied']):
        os.write(report_fd, (json.dumps({'probe': probe, 'failed': True}) + '\n').encode())
        return 77
    os.write(report_fd, (json.dumps({'probe': probe}) + '\n').encode())
    child = subprocess.Popen(
        ['/runtime/bin/node', '/app/scripts/rea.mjs', 'capture-process', '/input/scenario.json', '--json'],
        env=config['environment'], close_fds=True, stdin=subprocess.DEVNULL,
    )
    os.write(report_fd, (json.dumps({'launched': True}) + '\n').encode())
    code = child.wait()
    os.write(report_fd, (json.dumps({'exitCode': code}) + '\n').encode())
    # Keep this disposable worker alive until the external owner removes raw
    # data at its deadline and kills the cgroup. This is not a reusable worker.
    while True:
        time.sleep(0.1)


if __name__ == '__main__':
    raise SystemExit(main())
