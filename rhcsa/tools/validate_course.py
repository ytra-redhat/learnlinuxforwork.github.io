#!/usr/bin/env python3
"""Validate generated content and exercise safe regressions, never guest commands."""
from pathlib import Path
import ast
import html.parser
import importlib.util
import json
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, **kwargs)


class PreParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.active = False

    def handle_starttag(self, tag, attrs):
        if tag == 'pre':
            self.active = True
            self.blocks.append('')

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.blocks[-1] += data


def main():
    for path in ROOT.rglob('*.py'):
        ast.parse(path.read_text())
    shell_files = list(ROOT.rglob('*.sh')) + list(ROOT.rglob('*.command'))
    for path in shell_files:
        result = run(['bash', '-n', str(path)])
        assert result.returncode == 0, (path, result.stderr)
    for page in (ROOT / 'lab').glob('*.html'):
        assert not re.search(r'firewall-cmd[^\n]*--zone=[^\n]*(?:--reload|--get-default-zone)', page.read_text()), page
    data = json.loads((ROOT / 'data/rhcsa.json').read_text())
    assert len(data['weeks']['items']) == 12
    spec = importlib.util.spec_from_file_location('course_labs', ROOT / 'tools/build_labs.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(module.LABS) == 12
    parsed_blocks = 0
    scripts = {}
    for lab in module.LABS:
        parser = PreParser()
        parser.feed((ROOT / 'lab' / (lab['id'] + '.html')).read_text())
        expected = [code for section in lab['sections'] for _, code in section['code']]
        expected += [lab['breakfix']['break'], lab['breakfix']['fix']]
        assert parser.blocks == expected, f"Generated lab drift: {lab['id']}"
        for section in lab['sections']:
            for title, code in section['code']:
                result = run(['bash', '-n'], input=code + '\n')
                assert result.returncode == 0, (lab['id'], title, result.stderr)
                parsed_blocks += 1
                for match in re.finditer(r"cat > ([a-z]+\.sh) <<'EOF'\n(.*?)\nEOF", code, re.S):
                    scripts[match[1]] = match[2] + '\n'
    cloud = (ROOT / 'scripts/build-cloud-lab.sh').read_text().strip()
    for path in (ROOT / 'cloud').glob('*.html'):
        parser = PreParser()
        parser.feed(path.read_text())
        assert any(block.strip() == cloud for block in parser.blocks), f'Cloud script drift: {path}'
    with tempfile.TemporaryDirectory(prefix='rhcsa-validation-') as temp:
        work = Path(temp)
        for name, code in scripts.items():
            (work / name).write_text(code)
            result = run(['bash', '-n', str(work / name)])
            assert result.returncode == 0, (name, result.stderr)
        for arguments, status in [([], 1), (['Name With Spaces', '2'], 0),
                                  (['Name', 'wrong'], 1), (['Name', '0'], 1),
                                  (['Name', '02'], 1), (['Name', '1001'], 1)]:
            result = run(['bash', str(work / 'args.sh'), *arguments])
            assert result.returncode == status, (arguments, result)
            if arguments == ['Name With Spaces', '2']:
                assert result.stdout.splitlines() == ['1. Hello, Name With Spaces', '2. Hello, Name With Spaces']
        # Exercise real shell device-name construction with multiple disk families.
        disk_code = module.LABS[7]['sections'][0]['code'][1][1]
        naming = disk_code[disk_code.index('case "$DISK"'):disk_code.index('\nlsblk "$DISK"')]
        for device, partition in [('/dev/sdb', '/dev/sdb1'),
                                  ('/dev/nvme0n2', '/dev/nvme0n2p1'),
                                  ('/dev/mmcblk1', '/dev/mmcblk1p1')]:
            result = run(['bash', '-c', naming + '\nprintf "%s" "$P1"'], env={**os.environ, 'DISK': device})
            assert result.returncode == 0 and result.stdout == partition, (device, result)
        mock_cloud(ROOT, work)
    print(f'OK: {len(shell_files)} shell entry points, {parsed_blocks} command blocks, '
          f'{len(scripts)} embedded scripts, 12 matching lab pages, 4 matching cloud pages; '
          'argument/device regression checks and mocked cloud lifecycle passed.')
    print('No guest administration, real hypervisor operation or live cloud API call was executed.')


def mock_cloud(root, work):
    """Test resource ownership/state and failure handling with isolated CLI doubles."""
    commands = work / 'commands'
    commands.mkdir()
    executable = commands / 'provider.py'
    executable.write_text('''#!/usr/bin/env python3
import json,os,sys
a=sys.argv[1:]; name=os.path.basename(sys.argv[0])
with open(os.environ['RHCSA_TEST_LOG'],'a') as f: f.write(json.dumps([name,*a])+'\\n')
if os.environ.get('RHCSA_TEST_FAIL') and 'instances' in a and 'create' in a: sys.exit(17)
if name=='aws':
 if 'describe-images' in a: print('ami-mock')
 elif 'describe-security-groups' in a: print('sg-mock')
 elif 'describe-instances' in a: print('i-mock-a i-mock-b')
 elif 'run-instances' in a: print('i-mock')
elif name=='doctl':
 if 'create' in a and '--output' in a: print('[{"id":"mock-resource"}]')
 elif 'droplet' in a and 'create' in a: print('123456')
elif name=='vultr-cli':
 if 'create' in a: print('{"resource":{"id":"mock-resource"}}')
''')
    executable.chmod(0o755)
    for name in ['gcloud', 'aws', 'doctl', 'vultr-cli']:
        (commands / name).symlink_to(executable)
    key = work / 'mock.pub'
    key.write_text('ssh-ed25519 AAAATEST lab-test\n')
    log = work / 'provider-log.jsonl'
    env = {**os.environ, 'PATH': str(commands) + os.pathsep + os.environ['PATH'],
           'RHCSA_CLOUD_STATE': str(work / 'cloud-state'), 'RHCSA_SSH_KEY': str(key),
           'RHCSA_SSH_CIDR': '192.0.2.1/32', 'RHCSA_TEST_LOG': str(log),
           'DO_KEY_ID': 'test-key', 'VULTR_KEY_ID': 'test-key',
           'VULTR_OS_ID': 'test-os', 'VULTR_FIREWALL_GROUP': 'user-owned-firewall'}
    script = root / 'scripts/build-cloud-lab.sh'
    for provider in ['gcp', 'aws', 'do', 'vultr']:
        result = run(['bash', str(script), provider], env=env)
        assert result.returncode == 0, (provider, result.stdout, result.stderr)
        state = work / 'cloud-state' / provider
        assert (state / 'created').exists()
        token = (state / 'token').read_text().strip()
        assert re.fullmatch(r'[a-f0-9]{12}', token)
        repeated = run(['bash', str(script), provider], env=env)
        assert repeated.returncode != 0, 'A repeated create must preserve existing state'
        # Cleanup must not depend on a key still existing or CIDR environment.
        key.rename(work / 'missing.pub')
        result = run(['bash', str(script), provider, '--destroy'], env={**env, 'RHCSA_SSH_CIDR': ''})
        (work / 'missing.pub').rename(key)
        assert result.returncode == 0 and not state.exists(), (provider, result.stdout, result.stderr)
    failed = run(['bash', str(script), 'gcp'], env={**env, 'RHCSA_TEST_FAIL': '1'})
    assert failed.returncode != 0
    state = work / 'cloud-state/gcp'
    assert (state / 'token').exists() and not (state / 'created').exists()
    assert 'preserved' in failed.stderr.lower()
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert any('volume' in event and 'delete' in event for event in events)
    assert any('block-storage' in event and 'delete' in event for event in events)
    assert any('delete-security-group' in event for event in events)


if __name__ == '__main__':
    main()
