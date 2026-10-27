"""Reject a scanner success that omitted the engine's native dependencies."""
import argparse
import json
from pathlib import Path
from urllib.parse import unquote


def verify(sbom, closure, scan):
    expected = set(closure.get('os_packages',[]))
    if sbom.get('bomFormat') != 'CycloneDX' or closure.get('format') != 'with-human-runtime-closure-1' or not expected:
        raise ValueError('IMAGE_INVENTORY_REQUIRED')
    found = set()
    for component in sbom.get('components',[]):
        purl = component.get('purl','')
        if purl.startswith('pkg:deb/debian/'):
            found.add(unquote(purl.removeprefix('pkg:deb/debian/').split('@',1)[0]))
    if found != expected:
        raise ValueError('OS_SCAN_COVERAGE_INCOMPLETE')
    if (scan.get('Metadata',{}).get('OS',{}).get('Family') != 'debian'
            or not any(r.get('Class') == 'os-pkgs' and r.get('Type') == 'debian' for r in scan.get('Results',[]))):
        raise ValueError('OS_SCAN_COVERAGE_INCOMPLETE')
    # CycloneDX contains ratings from several distributions. Apply the actual
    # scanner-selected severity/source for THIS distribution, retain all ratings.
    if any(v.get('Severity') in ('HIGH','CRITICAL') for r in scan.get('Results',[]) for v in r.get('Vulnerabilities',[])):
        raise ValueError('HIGH_CRITICAL_VULNERABILITY')
    return {'state':'PASS','native_packages_expected':len(expected),'native_packages_scanned':len(found)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sbom',type=Path,required=True)
    parser.add_argument('--closure',type=Path,required=True)
    parser.add_argument('--scan',type=Path,required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(json.loads(args.sbom.read_text(encoding='utf-8-sig')),
                                json.loads(args.closure.read_text(encoding='utf-8-sig')),
                                json.loads(args.scan.read_text(encoding='utf-8-sig')))))
    except (ValueError,OSError,TypeError,KeyError):
        print(json.dumps({'state':'FAILED','reason':'IMAGE_VULNERABILITY_OR_SCAN_COVERAGE'}))
        raise SystemExit(1) from None
