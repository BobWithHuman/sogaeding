"""Build an auditable Python-only rootfs; retain truthful package inventory.

No shell, package manager, mount/login/systemd programs, terminal extensions or
libuuid extension are needed by the registered file engine. All retained ELF
dependencies are resolved from ldd and copied with their package metadata.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import certifi

root = Path('/rootfs')
root.mkdir()
shutil.copytree('/usr/local', root/'usr/local', symlinks=True)
# Dependencies are installed in the build stage. The immutable runtime never
# installs packages; omit the inherited installer and its vulnerable code paths.
site = root/'usr/local/lib/python3.12/site-packages'
for path in site.iterdir():
    if path.name == 'pip' or re.fullmatch(r'pip-[0-9][A-Za-z0-9.]*\.dist-info', path.name):
        if path.is_symlink() or path.resolve().parent != site.resolve():
            raise RuntimeError('UNSAFE_INSTALLER_PATH')
        shutil.rmtree(path)
for name in ('pip', 'pip3', 'pip3.12'):
    (root/'usr/local/bin'/name).unlink(missing_ok=True)
removed = []
extensions = root/'usr/local/lib/python3.12/lib-dynload'
for pattern in ('_curses*','readline*','_uuid*','_tkinter*'):
    for path in extensions.glob(pattern):
        removed.append('/'+path.relative_to(root).as_posix())
        path.unlink()

needed = set()
elfs = []
for path in (root/'usr/local').rglob('*'):
    if path.is_file() and not path.is_symlink():
        with path.open('rb') as stream:
            if stream.read(4) == b'\x7fELF':
                elfs.append(path)
for path in elfs:
    # Resolve against the original builder paths; wheel RUNPATH entries are
    # sometimes absolute. The output tree receives the same /usr/local layout.
    original = Path('/')/path.relative_to(root)
    result = subprocess.run(['/usr/bin/ldd', str(original)], capture_output=True, text=True, check=False)
    for line in result.stdout.splitlines():
        if 'not found' in line:
            raise RuntimeError('MISSING_RUNTIME_LIBRARY:'+str(original)+':'+line.strip())
        match = re.search(r'(?:=>\s*)?(/[^\s]+)',line)
        if match and not match[1].startswith('/usr/local/') and not match[1].startswith('/rootfs/'):
            needed.add(Path(match[1]))
for path in sorted(needed):
    target = root/path.relative_to('/')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,target)

packages = set()
resolved = {p.resolve() for p in needed}
for listing in Path('/var/lib/dpkg/info').glob('*.list'):
    for name in listing.read_text().splitlines():
        path = Path(name)
        if path.is_absolute() and path.exists() and path.resolve() in resolved:
            packages.add(listing.name.removesuffix('.list').split(':')[0])
paragraphs = Path('/var/lib/dpkg/status').read_text().split('\n\n')
selected = [p for p in paragraphs if any(line.startswith('Package: ') and line[9:] in packages for line in p.splitlines())]
status = root/'var/lib/dpkg/status'
status.parent.mkdir(parents=True)
status.write_text('\n\n'.join(selected)+'\n')
(root/'etc').mkdir()
shutil.copy2('/etc/os-release',root/'etc/os-release')
shutil.copy2('/etc/debian_version',root/'etc/debian_version')
(root/'etc/passwd').write_text('root:x:0:0:root:/root:/nonexistent\napp:x:10001:10001:app:/home/app:/nonexistent\n')
(root/'etc/group').write_text('root:x:0:\napp:x:10001:\n')
cert = root/'etc/ssl/certs/ca-certificates.crt'
cert.parent.mkdir(parents=True)
shutil.copy2(certifi.where(),cert)
for name in ('tmp','data','home/app','product'):
    (root/name).mkdir(parents=True,exist_ok=True)
    os.chown(root/name,10001,10001)
# Standard sticky temporary directory, not a credential store. Docker tmpfs may
# inherit this mode with root ownership; 0700 would block the application UID.
os.chmod(root/'tmp',0o1777)  # nosec B103
inventory = {'format':'with-human-runtime-closure-1','os_packages':sorted(packages),
             'copied_libraries':[str(p) for p in sorted(needed)],'excluded_extensions':removed,
             'certificate_store':'certifi bundle; no old distribution CA bundle',
             'excluded_package_managers':['pip']}
(root/'runtime-closure.json').write_text(json.dumps(inventory,indent=2)+'\n')
print(json.dumps(inventory))
