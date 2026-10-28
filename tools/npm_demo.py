"""Compose the optional npm lab in memory, using the product's single Compose file.

Only this synthetic lab gets Node, registry and receiver services. No personal
workspace, Docker socket, real secret, public npm registry or host trust change.
"""
import argparse
import hashlib
import ipaddress
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

NODE = 'node:24-alpine@sha256:50c8e8ca1d27439048670df5883f32d57cf81cff6233222c893fd0d9884cbd81'


def stage_scenario(runtime, assets, scenario, *, check_only=False):
    """Operator-only fixture switch. Keep every session's history and evidence.

    No source deletion from an active session and no policy/limit/budget change.
    Refuse active connectors; each document starts a new independent session.
    """
    if scenario not in ('normal', 'attack', 'ask') or runtime.is_symlink():
        raise ValueError('INVALID_SCENARIO')
    runtime = runtime.resolve()
    grant = json.loads((runtime / 'control/grant.json').read_text())
    if grant.get('adapter') != 'npm-lab-1' or grant.get('workspace') != '/files':
        raise ValueError('NPM_LAB_REQUIRED')
    if (scenario=='ask' and 'SENSITIVE_RESOURCE_REQUIRES_CONSENT'
            not in grant.get('gate6_resource_rules',{}).get('reports/review.md',[])):
        raise ValueError('EXISTING_ASK_RESOURCE_RULE_REQUIRED')
    with sqlite3.connect((runtime / 'control-data/control.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        active = db.execute("SELECT count(*) FROM connections c JOIN expiry e ON e.id=c.hash AND e.kind='connection' WHERE c.session IS NOT NULL AND e.deadline>?", (time.time(),)).fetchone()[0]
        pending = db.execute("SELECT count(*) FROM calls WHERE state IN ('ANALYZING','READY','EXECUTING','UNKNOWN')").fetchone()[0]
    if active or pending:
        raise ValueError('CLOSE_CODEX_FIRST_ACTIVE_SESSION_OR_PENDING_CALL')
    workspace = runtime / 'workspace'
    evidence = runtime / 'lab-evidence'
    source = assets / ('install-' + ('normal' if scenario=='ask' else scenario) + '.md')
    report = workspace / 'reports/review.md'
    fixed_paths = [workspace, evidence, workspace / 'docs', runtime / 'upstream', source,
                   *(workspace / name for name in ('.npmrc', 'node_modules', 'package-lock.json', '.impact-demo')),
                   workspace / 'docs/install-guide.md', runtime / 'upstream/issue.md']
    if scenario=='ask':
        fixed_paths += [workspace/'reports',report,assets/'review-ask.md']
    if any(path.is_symlink() for path in fixed_paths):
        raise ValueError('SCENARIO_LINK_REJECTED')
    if scenario=='ask' and report.exists() and (not report.is_file() or report.stat().st_nlink!=1):
        raise ValueError('SCENARIO_REPORT_FILE_REQUIRED')
    if check_only:
        return {'state': 'SCENARIO_READY_TO_STAGE', 'scenario': scenario}
    archive = evidence / ('scenario-' + str(time.time_ns()) + '-' + uuid4().hex[:8])
    archive.mkdir(mode=0o700)
    # Preserve prior files/output instead of deleting them or their audit trail.
    for path, name in ((workspace / '.npmrc', 'previous.npmrc'),
                       (workspace / 'docs/install-guide.md', 'previous-guide.md'),
                       (runtime / 'upstream/issue.md', 'previous-issue.md')):
        if path.exists():
            shutil.copyfile(path, archive / name)
    if scenario=='ask':
        if report.exists():
            shutil.copyfile(report,archive/'previous-review.md')
        report.parent.mkdir(exist_ok=True)
        shutil.copyfile(assets/'review-ask.md',report)
    for name in ('node_modules', 'package-lock.json', '.impact-demo'):
        path = workspace / name
        if path.exists():
            path.rename(archive / name)
    initial = 'registry=https://npm-registry.lab:4873/\nstrict-ssl=true\n'
    (workspace / '.npmrc').write_text(initial, encoding='utf-8')
    workspace.joinpath('docs').mkdir(exist_ok=True)
    shutil.copyfile(source, workspace / 'docs/install-guide.md')
    shutil.copyfile(source, runtime / 'upstream/issue.md')
    result = {'state': 'SCENARIO_STAGED', 'scenario': scenario,
              'document': 'docs/install-guide.md', 'document_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'initial_npmrc_sha256': hashlib.sha256(initial.encode()).hexdigest(),
              'history_preserved': True, 'model_requests': 0, 'archive': archive.name}
    (archive / 'staged.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def configuration(root, name, connection, prepared, networks):
    env = {**os.environ, 'SOGAEDING_RUNTIME_NAME': name, 'SOGAEDING_TEAM_VOLUME': prepared['volume'],
           'SOGAEDING_JEV_KEY_FILE': connection['key_file'],
           'SOGAEDING_JEV_POLICY_FILE': str(connection['policy_file']),
           'SOGAEDING_CONTROL_PORT': str(connection['control_port']),
           'SOGAEDING_GATEWAY_PORT': str(connection['gateway_port']),
           'SOGAEDING_DASHBOARD_PORT': str(connection['gateway_port'] + 10),
           'SOGAEDING_PROTECTED_SUBNET': networks['protected'], 'SOGAEDING_INGRESS_SUBNET': networks['ingress']}
    result = subprocess.run(['docker', 'compose', '-f', str(root / 'compose.yaml'), '--profile', '*', 'config', '--format', 'json'],
                            env=env, capture_output=True, text=True, encoding='utf-8', check=True)
    value = json.loads(result.stdout)
    # Rendered Compose JSON includes names derived before the final -p flag.
    # Let the final project name own networks, never share a generic root name.
    for network in value['networks'].values():
        network.pop('name', None)
    services = value['services']
    services['upstream']['command'] = ['python', '-m', 'app.transparent.npm_lab']
    assets = root / 'demos/npm-tls'
    prefix = f'artifacts/team-dev/{name}/'

    def volume(subpath, destination, readonly=True):
        return {'type': 'volume', 'source': 'team-runtime', 'target': destination, 'read_only': readonly,
                'volume': {'subpath': prefix + subpath}}

    def node(command, mounts, nets):
        return {'image': NODE, 'user': '10001:10001', 'read_only': True, 'init': True,
                'cap_drop': ['ALL'], 'security_opt': ['no-new-privileges:true'],
                'tmpfs': ['/tmp:size=128m,mode=1777'], 'pids_limit': 64, 'mem_limit': '256m',
                'command': ['node', '/lab/' + command], 'networks': {n: None for n in nets},
                'volumes': [{'type': 'bind', 'source': str(assets / command), 'target': '/lab/' + command, 'read_only': True}, *mounts]}

    if 'npm_lab' not in networks:
        inventory = subprocess.run(['docker', 'network', 'ls', '-q'], capture_output=True, text=True, check=True).stdout.split()
        inspected = json.loads(subprocess.run(['docker', 'network', 'inspect', *inventory], capture_output=True, text=True, check=True).stdout)
        occupied = [ipaddress.ip_network(c['Subnet'], strict=False) for n in inspected
                    for c in n.get('IPAM', {}).get('Config') or [] if c.get('Subnet')]
        occupied += [ipaddress.ip_network(networks[k]) for k in ('protected', 'ingress')]
        for index in range(256):
            candidate = ipaddress.ip_network(f'10.253.{index}.0/24')
            if not any(o.version == 4 and o.overlaps(candidate) for o in occupied):
                networks['npm_lab'] = str(candidate)
                break
        else:
            raise ValueError('NO_LAB_SUBNET_AVAILABLE')
    value['networks']['npm-lab'] = {'internal': True, 'ipam': {'config': [{'subnet': networks['npm_lab']}]}}
    services['npm-worker'] = node('worker.js', [volume('npm-worker', '/runtime'),
        volume('workspace', '/project', False), volume('lab-evidence', '/evidence', False)], ['protected', 'npm-lab'])
    services['registry'] = node('registry.js', [volume('registry', '/runtime'), volume('lab-assets', '/lab/assets')], ['npm-lab'])
    services['registry']['networks']['npm-lab'] = {'aliases': ['npm-registry.lab']}
    services['impact-receiver'] = node('receiver.js', [volume('lab-evidence', '/evidence', False)], ['npm-lab'])
    services['upstream']['depends_on'] = {'npm-worker': {'condition': 'service_started'}}
    services['npm-worker']['depends_on'] = {s: {'condition': 'service_started'} for s in ('registry', 'impact-receiver')}
    return value


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['up', 'down', 'check', 'dashboard', 'status', 'scenario'])
    p.add_argument('--runtime', required=True)
    p.add_argument('--host', type=Path, required=True)
    p.add_argument('--scenario', choices=['normal', 'attack', 'ask'])
    args = p.parse_args()
    root = Path(__file__).resolve().parent.parent
    connection = json.loads((args.host.parent / 'connection.json').read_text(encoding='utf-8-sig'))
    if connection.get('adapter') != 'npm-lab-1':
        raise ValueError('NPM_LAB_PROFILE_REQUIRED')
    connection['policy_file'] = root / 'artifacts/team-dev' / args.runtime / 'jev-policy.json'
    runtime = root / 'artifacts/team-dev' / args.runtime
    prepared = json.loads((runtime / 'prepared.json').read_text(encoding='utf-8-sig'))
    networks = json.loads((runtime / 'networks.json').read_text(encoding='utf-8-sig'))
    root_id = hashlib.sha256(str(root).lower().encode()).hexdigest()[:8]
    project = f'sogaeding-team-{root_id}-{args.runtime}'
    if prepared['volume'] != project + '-runtime':
        raise ValueError('RUNTIME_IDENTITY_MISMATCH')
    value = configuration(root, args.runtime, connection, prepared, networks)
    (runtime / 'networks.json').write_text(json.dumps(networks), encoding='utf-8')
    command = ['docker', 'compose', '-p', project, '-f', '-']
    if args.mode == 'scenario':
        if args.scenario is None:
            raise ValueError('SCENARIO_REQUIRED')
        script = ("import sys,json; from pathlib import Path; sys.path.insert(0,'/tools'); "
                  "from npm_demo import stage_scenario; "
                  "print(json.dumps(stage_scenario(Path(sys.argv[1]),Path('/demos/npm-tls'),sys.argv[2],check_only=sys.argv[3]=='check')))")
        staging = ['docker', 'run', '--rm', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                   '--network', 'none', '--tmpfs', '/tmp', '-e', 'PYTHONDONTWRITEBYTECODE=1',
                   '--mount', f'type=bind,source={root / "tools"},target=/tools,readonly',
                   '--mount', f'type=bind,source={root / "demos"},target=/demos,readonly',
                   '--mount', f'type=volume,source={prepared["volume"]},target=/team',
                   'with-human-engine:local', 'python', '-c', script,
                   '/team/artifacts/team-dev/' + args.runtime, args.scenario]
        subprocess.run(staging + ['check'], check=True)
        subprocess.run(command + ['stop', 'upstream', 'npm-worker'], input=json.dumps(value), text=True, encoding='utf-8', check=True)
        try:
            subprocess.run(staging + ['stage'], check=True)
        finally:
            # A stop/start discards the worker's tmpfs npm cache between arms.
            subprocess.run(command + ['start', 'npm-worker', 'upstream'], input=json.dumps(value), text=True, encoding='utf-8', check=True)
        subprocess.run(command + ['restart', 'control'], input=json.dumps(value), text=True, encoding='utf-8', check=True)
        # Wait on read-only health only; never retry a tool or model request.
        subprocess.run([sys.executable, '-I', str(root / 'tools/product_codex.py'), 'check', '--host', str(args.host)], check=True)
        return
    modes = {'up': ['up', '-d', 'control', 'upstream', 'gateway'], 'down': ['--profile', '*', 'down'],
             'check': ['run', '--rm', '--no-deps', 'check'], 'dashboard': ['--profile', 'dashboard', 'up', '-d', 'dashboard'],
             'status': ['ps']}
    subprocess.run(command + modes[args.mode], input=json.dumps(value), text=True, encoding='utf-8', check=True, cwd=root)


if __name__ == '__main__':
    main()
