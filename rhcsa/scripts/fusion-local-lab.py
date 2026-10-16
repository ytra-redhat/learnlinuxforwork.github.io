#!/usr/bin/env python3
"""Native macOS/Fusion orchestration; Python standard library only.
RHCSA Course — Copyright (C) 2026 Shea's Tech. AGPL-3.0-or-later.
"""
import argparse
import configparser
import fcntl
import getpass
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
VERSION = '2026-10-02-course-corrections'
INSTALL_SETTINGS = {}
PASSWORD = 'rhcsa'
DEFAULTS = {'username': 'shea', 'language': 'en_US.UTF-8', 'timezone': 'UTC'}
NODES = {'servera': ('192.168.56.10', True), 'serverb': ('192.168.56.11', False)}
LAB = Path.home() / 'Virtual Machines.localized'
APP = Path(os.environ.get('FUSION_APP', '/Applications/VMware Fusion.app'))
VMRUN = APP / 'Contents/Library/vmrun'
VDISK = APP / 'Contents/Library/vmware-vdiskmanager'


def run(args, capture=False, check=True, timeout=None):
    return subprocess.run([str(x) for x in args], check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None, timeout=timeout)


def fail(message):
    raise RuntimeError(message)


def atomic(path, data):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(data)
    tmp.replace(path)


def save(directory, state):
    atomic(directory / 'fusion-state.json', json.dumps(state, indent=2) + '\n')


def vrun(*args, **kwargs):
    return run([VMRUN, '-T', 'fusion', *args], **kwargs)


def running(vmx):
    result = vrun('list', capture=True, timeout=30)
    return str(vmx) in result.stdout.splitlines()[1:]


def select_iso(explicit=None):
    pattern = re.compile(r'^Rocky-10(?:\.(\d+)|-latest)?-aarch64-dvd1?\.iso$', re.I)
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file() or not pattern.fullmatch(path.name):
            fail('--iso must name an existing Rocky-10.x-aarch64-dvd[1].iso')
        return path
    candidates = [p for p in (Path.home() / 'Downloads/Images').glob('*')
                  if p.is_file() and pattern.fullmatch(p.name)]
    if not candidates:
        fail('No Rocky 10 aarch64 DVD ISO in ~/Downloads/Images. Download the DVD, then retry.')
    # Prefer a known numerical release over an ambiguous "latest" filename.
    return max(candidates, key=lambda p: (int(pattern.fullmatch(p.name).group(1) or -1),
                                         p.stat().st_mtime_ns)).resolve()


def extract(iso, iso_path, output):
    run(['xorriso', '-abort_on', 'FAILURE', '-osirrox', 'on', '-indev', iso,
         '-extract', iso_path, output], capture=True)
    # DVD Rock Ridge modes are read-only; only these private copies are edited.
    output.chmod(0o600)


def inspect_iso(iso, work):
    tree = work / '.treeinfo'
    extract(iso, '/.treeinfo', tree)
    info = configparser.ConfigParser(interpolation=None)
    info.read(tree)
    if (info.get('tree', 'arch', fallback='') != 'aarch64' or
        info.get('release', 'name', fallback='') != 'Rocky Linux' or
        not re.fullmatch(r'10(?:\.\d+)*', info.get('release', 'version', fallback=''))):
        fail('ISO metadata does not identify Rocky Linux 10.x aarch64.')
    # A boot/minimal image is insufficient. Check both DVD repositories.
    for repo in ('BaseOS', 'AppStream'):
        extract(iso, '/' + repo + '/repodata/repomd.xml', work / (repo + '.xml'))
    extract(iso, '/EFI/BOOT/BOOTAA64.EFI', work / 'BOOTAA64.EFI')
    extract(iso, '/EFI/BOOT/grub.cfg', work / 'grub.cfg')
    extract(iso, '/images/efiboot.img', work / 'efiboot.img')
    return info


def grub_config(original):
    # Preserve the vendor's bootloader setup, label and kernel options. Keep only
    # the first (normal install) entry, never the media-check/rescue/FIPS entries.
    match = re.search(r'^menuentry .*?^}', original, flags=re.M | re.S)
    if not match:
        fail('Unrecognized vendor GRUB configuration: missing installation entry.')
    result = original[:match.start()] + match.group(0) + '\n'
    result, defaults = re.subn(r'^set default=.*$', 'set default="0"', result, flags=re.M)
    result, timeouts = re.subn(r'^set timeout=.*$', 'set timeout=3', result, flags=re.M)
    result, kernels = re.subn(r'^(\s*linux(?:efi)?\s+[^\n]+)$',
                             r'\1 inst.ks=cdrom:/ks.cfg inst.text', result, flags=re.M)
    if defaults != 1 or timeouts != 1 or kernels != 1 or 'inst.stage2=' not in result:
        fail('Unrecognized GRUB configuration; refusing to produce an uncertain boot image.')
    return result


def render_ks(name, state):
    text = (HERE / 'fusion-kickstart.cfg.in').read_text()
    values = {'NAME': name, 'IP': NODES[name][0], 'NAT_MAC': state['nat_mac'],
              'LAB_MAC': state['lab_mac'], 'BUILD_ID': state['build_id'],
              'USERNAME': state.get('settings', DEFAULTS)['username'],
              'LANGUAGE': state.get('settings', DEFAULTS)['language'],
              'TIMEZONE': state.get('settings', DEFAULTS)['timezone'],
              'PASSWORD_HASH': state.get('settings', {}).get('password_hash') or password_hash('rhcsa')}
    for key, value in values.items():
        text = text.replace('@' + key + '@', value)
    if re.search(r'@[A-Z_]+@', text):
        fail('Unresolved Kickstart placeholder.')
    return text


def remaster(iso, directory, name, state):
    target = directory / 'installer.iso'
    with tempfile.TemporaryDirectory(prefix='iso-', dir=directory) as temp:
        work = Path(temp)
        info = inspect_iso(iso, work)
        grub = work / 'grub.cfg'
        grub.write_text(grub_config(grub.read_text()))
        ks = work / 'ks.cfg'
        ks.write_text(render_ks(name, state))
        efi = work / 'efiboot.img'
        run(['mcopy', '-o', '-i', efi, grub, '::/EFI/BOOT/grub.cfg'], capture=True)
        # Read back from the FAT EFI image, not only from the ISO filesystem.
        run(['mcopy', '-i', efi, '::/EFI/BOOT/grub.cfg', work / 'efi-check.cfg'], capture=True)
        if (work / 'efi-check.cfg').read_bytes() != grub.read_bytes():
            fail('EFI GRUB read-back mismatch.')
        info['checksums']['images/efiboot.img'] = 'sha256:' + hashlib.sha256(efi.read_bytes()).hexdigest()
        with (work / '.treeinfo').open('w') as stream:
            info.write(stream)
        partial = directory / 'installer.partial.iso'
        partial.unlink(missing_ok=True)
        # Register the replaced FAT image explicitly: replay can retain the old
        # node identity after -map replaced it. This target is a UEFI DVD, not USB.
        run(['xorriso', '-abort_on', 'FAILURE', '-indev', iso, '-outdev', partial,
             '-map', grub, '/EFI/BOOT/grub.cfg', '-map', efi, '/images/efiboot.img',
             '-map', ks, '/ks.cfg', '-map', work / '.treeinfo', '/.treeinfo',
             '-boot_image', 'any', 'discard',
             '-boot_image', 'any', 'efi_path=/images/efiboot.img',
             '-boot_image', 'any', 'cat_path=/boot.catalog',
             '-boot_image', 'any', 'load_size=full', '-commit', '-end'], capture=True)
        for source, iso_path in ((grub, '/EFI/BOOT/grub.cfg'), (ks, '/ks.cfg'),
                                 (efi, '/images/efiboot.img')):
            output = work / ('verify-' + source.name)
            extract(partial, iso_path, output)
            if hashlib.sha256(output.read_bytes()).digest() != hashlib.sha256(source.read_bytes()).digest():
                fail('Remastered ISO read-back mismatch: ' + iso_path)
        report = run(['xorriso', '-indev', partial, '-report_el_torito', 'plain'], capture=True)
        boot = re.search(r'El Torito boot img\s*:\s*1\s+UEFI\s+y\s+none\s+'
                         r'\S+\s+\S+\s+(\d+)\s+(\d+)', report.stdout + report.stderr)
        if not boot:
            fail('Remastered ISO has no bootable UEFI El Torito entry.')
        expected = efi.read_bytes()
        # Verify the actual sectors the firmware will load, not just the file tree.
        with partial.open('rb') as stream:
            stream.seek(int(boot.group(2)) * 2048)
            actual = stream.read(len(expected))
        if actual != expected or int(boot.group(1)) * 512 < len(expected):
            fail('UEFI boot catalog does not point to the complete modified EFI image.')
        atomic(directory / 'boot-report.txt', report.stdout + report.stderr)
        partial.replace(target)


def vmx_text(name, state, installer=True, extra=False):
    entries = {
        '.encoding': 'UTF-8', 'config.version': '8', 'virtualHW.version': '20',
        'displayName': name + ' — Rocky RHCSA', 'guestOS': 'arm-rhel9-64', 'firmware': 'efi',
        'uefi.secureBoot.enabled': 'FALSE', 'memsize': '4096', 'numvcpus': '2',
        'pciBridge0.present': 'TRUE', 'pciBridge4.present': 'TRUE',
        'pciBridge4.virtualDev': 'pcieRootPort', 'pciBridge4.functions': '8',
        'nvme0.present': 'TRUE', 'nvme0:0.present': 'TRUE',
        'nvme0:0.fileName': disk_relative(name, state), 'sata0.present': 'TRUE',
        'sata0:0.present': 'TRUE', 'sata0:0.deviceType': 'cdrom-image',
        'sata0:0.fileName': 'installer.iso',
        'sata0:0.startConnected': 'TRUE' if installer else 'FALSE',
        'bios.bootOrder': 'cdrom,hdd' if installer else 'hdd,cdrom',
        'ethernet0.present': 'TRUE', 'ethernet0.connectionType': 'nat',
        'ethernet0.virtualDev': 'vmxnet3', 'ethernet0.addressType': 'static',
        'ethernet0.address': state['nat_mac'], 'ethernet1.present': 'TRUE',
        'ethernet1.connectionType': 'hostonly', 'ethernet1.virtualDev': 'vmxnet3',
        'ethernet1.addressType': 'static', 'ethernet1.address': state['lab_mac'],
        'usb.present': 'TRUE', 'usb_xhci.present': 'TRUE', 'sound.present': 'FALSE',
        'tools.syncTime': 'TRUE',
    }
    if extra:
        entries.update({'nvme0:1.present': 'TRUE', 'nvme0:1.fileName': disk_relative(name, state, extra=True)})
    return ''.join(f'{k} = "{v}"\n' for k, v in entries.items())


def edit_vmx(vmx, changes):
    if running(vmx):
        fail('Refusing to edit a running VM: ' + str(vmx))
    # Preserve Fusion-assigned UUID, PCI slots, NVRAM and all other settings.
    text = vmx.read_text()
    for key, value in changes.items():
        pattern = r'^' + re.escape(key) + r'\s*=.*$'
        line = f'{key} = "{value}"'
        if re.search(pattern, text, re.M):
            text = re.sub(pattern, lambda _: line, text, flags=re.M)
        else:
            text += '\n' + line + '\n'
    atomic(vmx, text)


def create_disk(path, size):
    run([VDISK, '-c', '-s', f'{size}GB', '-a', 'lsilogic', '-t', '1', path], capture=True)


def wait_off(vmx, deadline):
    while running(vmx):
        if time.monotonic() > deadline:
            fail('Timeout waiting for installation/shutdown. VM left intact: ' + str(vmx))
        time.sleep(10)


def guest_ready(vmx, name, state, deadline, extra=False):
    # A fresh nonce prevents a stale file from making a failed check look ready.
    token = secrets.token_hex(12)
    guest = '/tmp/rhcsa-ready-' + token
    command = (
        'set -eu; '
        f'test "$(cat /etc/rhcsa-installed)" = "{state["build_id"]}"; '
        '. /etc/os-release; test "$ID" = rocky; case "$VERSION_ID" in 10|10.*) ;; *) exit 1;; esac; '
        'test "$(uname -m)" = aarch64; '
        'test "$(getenforce)" = Enforcing; '
        'for service in sshd firewalld vmtoolsd NetworkManager; do systemctl is-active --quiet $service; done; '
        f'test "$(hostname -s)" = {name}; '
        f'ip -4 address show | grep -q "inet {NODES[name][0]}/24 "; '
        'test "$(cat /sys/block/nvme0n1/size)" = 62914560; '
    )
    if extra:
        command += ('test "$(cat /sys/block/nvme0n2/size)" = 20971520; '
                    'test -z "$(ls /sys/block/nvme0n2/ | grep -E \'^nvme0n2p[0-9]+$\' || true)"; ')
    command += ("iface=$(ip -4 route show default | awk 'NR==1 {print $5}'); test -n \"$iface\"; "
                "addr=$(ip -4 -o address show dev \"$iface\" scope global | awk 'NR==1 {print $4}'); "
                'test -n "$addr"; '
                f'printf "%s\\n%s\\n" "{token}" "$addr" > {guest}')
    destination = vmx.parent / 'guest-ready.txt'
    local_script = vmx.parent / 'guest-check.sh'
    guest_script = guest + '.sh'
    guest_log = guest + '.log'
    local_log = vmx.parent / 'guest-check.log'
    # vmrun joins program arguments into a guest command line. Transfer a script
    # instead of relying on nested shell quoting in a long bash -c argument.
    atomic(local_script, '#!/bin/bash\nexec > ' + guest_log + ' 2>&1\n'
           'set -eux\nexport PATH=/usr/sbin:/usr/bin:/sbin:/bin\n' + command + '\n')
    auth = ('-gu', state.get('settings', DEFAULTS)['username'], '-gp', PASSWORD)
    deadline = min(deadline, time.monotonic() + 300)
    last = 'Waiting for VMware Tools.'
    next_notice = 0
    while time.monotonic() < deadline:
        if not running(vmx):
            fail(name + ' shut down before guest verification succeeded.')
        try:
            copied = vrun(*auth, 'copyFileFromHostToGuest', vmx, local_script, guest_script,
                          capture=True, check=False, timeout=30)
            last = (copied.stdout + copied.stderr).strip()
            if copied.returncode == 0:
                result = vrun(*auth, 'runProgramInGuest', vmx, '/bin/bash', guest_script,
                              capture=True, check=False, timeout=45)
                last = (result.stdout + result.stderr).strip()
                diagnostic = vrun(*auth, 'copyFileFromGuestToHost', vmx, guest_log, local_log,
                                  capture=True, check=False, timeout=30)
                copy = vrun(*auth, 'copyFileFromGuestToHost', vmx, guest, destination,
                            capture=True, check=False, timeout=30)
                if copy.returncode == 0:
                    lines = destination.read_text().splitlines()
                    if len(lines) == 2 and lines[0] == token:
                        for path in (guest, guest_script, guest_log):
                            vrun(*auth, 'deleteFileInGuest', vmx, path,
                                 capture=True, check=False, timeout=30)
                        return lines[1].split('/')[0]
                if diagnostic.returncode == 0:
                    last = '\n'.join(local_log.read_text().splitlines()[-4:])
                elif not last:
                    last = (copy.stdout + copy.stderr).strip()
        except subprocess.TimeoutExpired:
            last = 'VMware Tools not responding yet.'
        if time.monotonic() >= next_notice:
            print(f'{name}: eindcontrole nog niet geslaagd: {last}', flush=True)
            next_notice = time.monotonic() + 30
        time.sleep(10)
    fail(f'{name}: guest checks timed out. VM preserved. See {local_log}. Last result: {last}')


def ensure_started(vmx):
    if not running(vmx):
        vrun('start', vmx, 'gui', capture=True, timeout=90)


def disk_relative(name, state, extra=False):
    filename = name + ('-extra' if extra else '') + '.vmdk'
    if state.get('disk_layout') == 'directories':
        return ('disks/extra/' if extra else 'disks/system/') + filename
    return filename


def ensure_disk(directory, name, state, extra=False):
    target = directory / disk_relative(name, state, extra)
    size = 10 if extra else 30
    if target.parent.exists():
        if not target.is_file():
            fail('Incomplete disk directory; preserved for inspection: ' + str(target.parent))
        # Read-only consistency check. Never repair or replace an existing disk.
        run([VDISK, '-e', target], capture=True)
        sectors = sum(int(line.split()[1]) for line in target.read_text().splitlines()
                      if line.startswith('RW '))
        if sectors != size * 2097152:
            fail('Unexpected disk capacity: ' + str(target))
        return
    target.parent.parent.mkdir(parents=True, exist_ok=True)
    # Publish the descriptor and every extent together. Interrupted temporary
    # directories are never attached to a VM and are not reused as valid disks.
    with tempfile.TemporaryDirectory(prefix='.disk-build-', dir=directory) as temp:
        staging = Path(temp) / 'complete'
        staging.mkdir()
        create_disk(staging / target.name, size)
        run([VDISK, '-e', staging / target.name], capture=True)
        staging.rename(target.parent)


def prepare_vm(directory, name, state, iso):
    vmx = directory / (name + '.vmx')
    # A VMX/log/NVRAM/lock means the VM might already have been booted. An
    # uncertain state must never trigger an automatic reinstall.
    if vmx.exists() or any(directory.glob('*.lck')) or (directory / 'vmware.log').exists():
        fail('Preparation state conflicts with VM files; preserved: ' + str(directory))
    if state.get('disk_layout') != 'directories':
        if any(directory.glob('*.vmdk')):
            fail('Legacy disks exist in unfinished preparation; preserved: ' + str(directory))
        state['disk_layout'] = 'directories'
        save(directory, state)
    # The ISO is replaceable installation media. Rebuild on resumed preparation
    # rather than trusting an interrupted copy or a stale Kickstart template.
    print(f'{name}: preparing unattended DVD and 30 GiB system disk.', flush=True)
    remaster(iso, directory, name, state)
    ensure_disk(directory, name, state)
    if NODES[name][1]:
        ensure_disk(directory, name, state, extra=True)
    # Commit state BEFORE publishing VMX. If interrupted here, the prepared
    # branch may recreate a missing VMX; it never recreates missing disks.
    state['phase'] = 'prepared'
    save(directory, state)
    atomic(vmx, vmx_text(name, state))


def provision(name, iso, args):
    directory = LAB / (name + '.vmwarevm')
    vmx = directory / (name + '.vmx')
    statefile = directory / 'fusion-state.json'
    if directory.exists():
        if not statefile.is_file():
            fail(f'{directory} already exists without this installer\'s state. '
                 'Existing VMs/disks are never overwritten. Move the old directory aside first.')
        state = json.loads(statefile.read_text())
        if state.get('schema') != 1 or state.get('name') != name:
            fail('Unrecognized state: ' + str(statefile))
    else:
        directory.mkdir(parents=True)
        def mac():
            return '00:50:56:' + ':'.join(f'{v:02x}' for v in
                                        (secrets.randbelow(64), secrets.randbelow(256), secrets.randbelow(256)))
        state = {'schema': 1, 'name': name, 'phase': 'creating', 'build_id': secrets.token_hex(16),
                 'nat_mac': mac(), 'lab_mac': mac(), 'source_iso': str(iso), 'settings': dict(INSTALL_SETTINGS)}
        save(directory, state)
    if state['phase'] == 'creating':
        state['settings'] = dict(INSTALL_SETTINGS or state.get('settings', DEFAULTS))
        state['source_iso'] = str(iso)
        save(directory, state)
        try:
            prepare_vm(directory, name, state, iso)
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            atomic(directory / 'preparation-error.txt',
                   (getattr(error, 'stderr', None) or str(error)) + '\n')
            raise
        (directory / 'preparation-error.txt').unlink(missing_ok=True)
    if state['phase'] == 'prepared' and not vmx.exists():
        required = [directory / disk_relative(name, state), directory / 'installer.iso']
        if NODES[name][1]:
            required.append(directory / disk_relative(name, state, extra=True))
        if not all(path.is_file() for path in required):
            fail('Prepared VM has missing media/disks; preserved: ' + str(directory))
        atomic(vmx, vmx_text(name, state))
    if args.prepare_only:
        print(f'{name}: {state["phase"]}; {vmx}', flush=True)
        return
    deadline = time.monotonic() + args.timeout * 60
    if state['phase'] == 'prepared':
        # Save intent before start. A resume never blindly starts an installer
        # that may already have written the disk.
        state['phase'] = 'installing'
        save(directory, state)
        print(f'{name}: installing Rocky; spare disk disconnected.', flush=True)
        ensure_started(vmx)
    if state['phase'] == 'installing':
        wait_off(vmx, deadline)
        edit_vmx(vmx, {'sata0:0.startConnected': 'FALSE', 'bios.bootOrder': 'hdd,cdrom'})
        state['phase'] = 'verifying'
        save(directory, state)
    if state['phase'] in ('verifying', 'ready', 'attaching'):
        ensure_started(vmx)
        print(f'{name}: checking installed OS, services, network and disk.', flush=True)
        address = guest_ready(vmx, name, state, deadline,
                              extra=state['phase'] == 'ready' and NODES[name][1])
        if NODES[name][1] and state['phase'] != 'ready':
            state['phase'] = 'attaching'
            save(directory, state)
            vrun('stop', vmx, 'soft', capture=True, timeout=90)
            wait_off(vmx, deadline)
            edit_vmx(vmx, {'nvme0:1.present': 'TRUE', 'nvme0:1.fileName': disk_relative(name, state, extra=True)})
            ensure_started(vmx)
            address = guest_ready(vmx, name, state, deadline, extra=True)
        state['phase'] = 'ready'
        state['nat_address'] = address
        save(directory, state)
        print(f"{name} ready: ssh {state.get('settings', DEFAULTS)['username']}@{address} | lab address {NODES[name][0]}", flush=True)
    else:
        fail('Unsupported state phase: ' + str(state['phase']))


def password_hash(password):
    # Password travels over stdin, never as an openssl command-line argument.
    candidates = ['/opt/homebrew/opt/openssl@3/bin/openssl',
                  '/opt/homebrew/bin/openssl', shutil.which('openssl')]
    for candidate in candidates:
        if candidate and os.access(candidate, os.X_OK):
            result = subprocess.run([candidate, 'passwd', '-6', '-stdin'],
                                    input=password + '\n', text=True, capture_output=True)
            value = result.stdout.strip()
            if result.returncode == 0 and re.fullmatch(r'\$6\$[./A-Za-z0-9$]+', value):
                return value
    fail('OpenSSL with SHA-512 support is required: brew install openssl@3')


def ask(label, default, valid):
    while True:
        value = input(f'{label} [{default}]: ').strip() or default
        if valid(value):
            return value
        print('Ongeldige invoer; probeer opnieuw.')


def wizard(preparing, assume_defaults=False):
    global INSTALL_SETTINGS, PASSWORD
    existing = []
    for name in NODES:
        path = LAB / (name + '.vmwarevm') / 'fusion-state.json'
        if path.is_file():
            state = json.loads(path.read_text())
            if state.get('phase') != 'creating':
                existing.append(state.get('settings', DEFAULTS))
    print(f'RHCSA automatische installatie — {VERSION}\nScript: {HERE / "build-local-lab.sh"}')
    print(f'VM-map: {LAB}\nservera + serverb: elk 2 CPU / 4 GB / 30 GB; servera extra 10 GB.')
    if assume_defaults:
        INSTALL_SETTINGS = dict(existing[0] if existing else DEFAULTS)
        PASSWORD = os.environ.get('RHCSA_PASSWORD', '')
        if not PASSWORD:
            fail('--yes requires RHCSA_PASSWORD; no weak default password is used.')
    else:
        if not sys.stdin.isatty():
            fail('Start in een terminal voor de vragen, of gebruik --yes met RHCSA_PASSWORD.')
        if existing:
            INSTALL_SETTINGS = dict(existing[0])
            print('Bestaande installatie hervatten; opgeslagen gebruikers- en taalinstellingen blijven behouden.')
            print('Gebruiker: ' + INSTALL_SETTINGS['username'])
            PASSWORD = getpass.getpass('Bestaand labwachtwoord (oude versie: rhcsa): ')
        else:
            INSTALL_SETTINGS = dict(DEFAULTS)
            INSTALL_SETTINGS['username'] = ask('Beheeraccount', 'shea',
                lambda v: bool(re.fullmatch(r'[a-z_][a-z0-9_-]{0,30}', v)) and v != 'root')
            while True:
                PASSWORD = getpass.getpass('Kies het labwachtwoord (minimaal 8 tekens): ')
                if len(PASSWORD) >= 8 and '\n' not in PASSWORD and '\r' not in PASSWORD and '\0' not in PASSWORD:
                    if getpass.getpass('Herhaal het wachtwoord: ') == PASSWORD:
                        break
                print('Gebruik minimaal 8 tekens en voer twee keer hetzelfde wachtwoord in.')
            language = ask('Systeemtaal: en of nl', 'en', lambda v: v in ('en', 'nl'))
            INSTALL_SETTINGS['language'] = 'nl_NL.UTF-8' if language == 'nl' else 'en_US.UTF-8'
            INSTALL_SETTINGS['timezone'] = ask('Tijdzone', 'UTC',
                lambda v: bool(re.fullmatch(r'[A-Za-z0-9_+/-]+', v)) and '..' not in v
                and (Path('/usr/share/zoneinfo') / v).is_file())
        if input('Start de automatische installatie/controle? [ja/nee]: ').strip().lower() not in ('ja','j','yes','y'):
            fail('Gestopt op verzoek; er zijn geen nieuwe VM-disks aangemaakt.')
    if not PASSWORD or any(c in PASSWORD for c in ('\n','\r','\0')):
        fail('Een geldig labwachtwoord is vereist.')
    if preparing:
        INSTALL_SETTINGS['password_hash'] = password_hash(PASSWORD)


def choose_existing(assume_defaults):
    managed = [LAB / (name + '.vmwarevm') for name in NODES
               if (LAB / (name + '.vmwarevm') / 'fusion-state.json').is_file()]
    if not managed or assume_defaults:
        return
    if not sys.stdin.isatty():
        fail('Gebruik een terminal voor de installatievragen.')
    print('Er bestaat al een eerdere installatie in de gekozen Fusion-map.')
    action = ask('Hervatten [h] of bestaande VM bewaren en nieuw installeren [n]', 'h',
                 lambda v: v in ('h', 'n'))
    if action == 'h':
        return
    print('De bestaande VM-bundels worden volledig bewaard in een aparte backupmap.')
    print("Draaiende VM's moeten eerst volledig worden afgesloten; er wordt niets geforceerd gestopt.")
    for directory in managed:
        vmx = directory / (directory.stem + '.vmx')
        if running(vmx) or any(directory.glob('*.lck')):
            fail('Sluit deze VM eerst volledig af in Fusion en start opnieuw: ' + str(directory))
    backup = Path(tempfile.mkdtemp(prefix='RHCSA-backup-', dir=LAB))
    for directory in managed:
        directory.rename(backup / directory.name)
    print('Oude VM-bundels bewaard in: ' + str(backup))


def provision_all(iso, args):
    errors = []
    prepared = []
    prepare_args = argparse.Namespace(**vars(args))
    prepare_args.prepare_only = True
    # Prepare both bundles before waiting for installation or guest checks.
    for name in NODES:
        try:
            provision(name, iso, prepare_args)
            prepared.append(name)
        except (RuntimeError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            errors.append(f'{name}: {getattr(error, "stderr", None) or str(error)}')
            print(errors[-1], file=sys.stderr, flush=True)
    if not args.prepare_only:
        for name in prepared:
            try:
                provision(name, iso, args)
            except (RuntimeError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                errors.append(f'{name}: {getattr(error, "stderr", None) or str(error)}')
                print(errors[-1], file=sys.stderr, flush=True)
                print('Verder met de andere VM; bestaande disks blijven behouden.', flush=True)
    if errors:
        fail('Niet alle VM-controles zijn geslaagd:\n' + '\n'.join(errors))


def main():
    parser = argparse.ArgumentParser(description='Rocky 10 aarch64 RHCSA lab on VMware Fusion (macOS).')
    parser.add_argument('--provider', choices=['vmware', 'ws'], default='vmware')
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--yes', action='store_true', help='Skip questions; use defaults and RHCSA_PASSWORD')
    parser.add_argument('--iso', help='Rocky 10 aarch64 DVD ISO; default: latest numbered ISO in ~/Downloads/Images')
    parser.add_argument('--prepare-only', action='store_true', help='Create and validate media/VM files without starting VMs')
    parser.add_argument('--timeout', type=int, default=60, help='Install/verification timeout in minutes per VM (default 60)')
    parser.add_argument('--destroy', action='store_true', help='Unsupported: existing VMs are preserved')
    args = parser.parse_args()
    if args.destroy:
        fail('--destroy is deliberately unsupported on Fusion; manage existing VMs in Fusion.')
    if platform.system() != 'Darwin' or platform.machine() not in ('arm64', 'aarch64'):
        fail('Run natively on an Apple Silicon Mac, not Intel/Rosetta.')
    if os.geteuid() == 0:
        fail('Run as your regular Mac user (siebe:staff), without sudo.')
    if args.timeout < 1:
        fail('--timeout must be positive.')
    for tool in (VMRUN, VDISK):
        if not os.access(tool, os.X_OK):
            fail('Missing Fusion tool: ' + str(tool))
    os.umask(0o077)
    LAB.mkdir(parents=True, exist_ok=True)
    with (LAB / '.fusion-build.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail('Another Fusion lab build is running.')
        vrun('list', capture=True, timeout=30)
        # Refuse all incompatible directories before changing either VM.
        for name in NODES:
            directory = LAB / (name + '.vmwarevm')
            if directory.exists() and not (directory / 'fusion-state.json').is_file():
                fail(f'Existing VM directory is protected: {directory}. Move it aside before building a fresh lab.')
        print('Installer checks expect an unpartitioned extra disk. After starting storage labs, use Fusion directly; do not rerun installer readiness checks.')
        choose_existing(args.yes)
        preparing = []
        for name in NODES:
            statefile = LAB / (name + '.vmwarevm') / 'fusion-state.json'
            if not statefile.exists() or json.loads(statefile.read_text()).get('phase') == 'creating':
                preparing.append(name)
        iso = None
        if preparing:
            for tool in ('xorriso', 'mcopy'):
                if not shutil.which(tool):
                    fail('Native ISO tools required. Run once: brew install xorriso mtools')
            iso = select_iso(args.iso)
        config = Path('/Library/Preferences/VMware Fusion/networking')
        if config.is_file():
            settings = dict(re.findall(r'^answer (\S+) (\S+)$', config.read_text(), re.M))
            subnet = settings.get('VNET_8_HOSTONLY_SUBNET')
            mask = settings.get('VNET_8_HOSTONLY_NETMASK')
            if subnet and mask and ipaddress.ip_network(f'{subnet}/{mask}', strict=False).overlaps(
                    ipaddress.ip_network('192.168.56.0/24')):
                fail('Fusion NAT overlaps the course network 192.168.56.0/24. '
                     'Choose a different NAT subnet in Fusion before building.')
        new_count = len(preparing)
        # Sparse VMDKs still need room for the installed systems, plus two DVDs.
        required = new_count * (iso.stat().st_size + 8 * 1024**3) if iso else 0
        if shutil.disk_usage(LAB).free < required:
            fail(f'Insufficient free space: allow at least {required // 1024**3 + 1} GiB for this build.')
        print('Fusion VM directory: ' + str(LAB), flush=True)
        if iso:
            print('Source ISO: ' + str(iso), flush=True)
        wizard(preparing, args.yes)
        provision_all(iso, args)
    if not args.prepare_only:
        print('Both VMs verified. Login with your chosen account and password; sudo uses the same password. '
              'Create a clean snapshot in Fusion before starting the course.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, EOFError, subprocess.SubprocessError) as error:
        detail = getattr(error, 'stderr', None) or str(error)
        print('STOPPED: ' + detail, file=sys.stderr)
        sys.exit(1)
