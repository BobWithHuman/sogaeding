import pytest
from engine_image_gate import verify


def test_scanner_success_without_native_packages_is_rejected():
    with pytest.raises(ValueError,match='OS_SCAN_COVERAGE_INCOMPLETE'):
        verify({'bomFormat':'CycloneDX','components':[{'purl':'pkg:pypi/httpx@0.28.1'}]},
               {'format':'with-human-runtime-closure-1','os_packages':['libc6']},{})


def test_complete_native_inventory_and_high_critical_are_separate_gates():
    report = {'bomFormat':'CycloneDX','components':[{'purl':'pkg:deb/debian/libc6@2.41?distro=debian-13'}]}
    closure = {'format':'with-human-runtime-closure-1','os_packages':['libc6']}
    scan = {'Metadata':{'OS':{'Family':'debian'}},'Results':[{'Class':'os-pkgs','Type':'debian'}]}
    assert verify(report,closure,scan)['state'] == 'PASS'
    scan['Results'][0]['Vulnerabilities'] = [{'Severity':'HIGH'}]
    with pytest.raises(ValueError,match='HIGH_CRITICAL_VULNERABILITY'):
        verify(report,closure,scan)


@pytest.mark.parametrize('metadata,results',[
    ({'OS':{'Family':'none'}},[{'Class':'os-pkgs','Type':'debian'}]),
    ({'OS':{'Family':'debian'}},[{'Class':'lang-pkgs','Type':'python-pkg'}]),
])
def test_present_sbom_cannot_hide_missing_os_analysis(metadata,results):
    with pytest.raises(ValueError,match='OS_SCAN_COVERAGE_INCOMPLETE'):
        verify({'bomFormat':'CycloneDX','components':[{'purl':'pkg:deb/debian/libc6@2.41'}]},
               {'format':'with-human-runtime-closure-1','os_packages':['libc6']},
               {'Metadata':metadata,'Results':results})


def test_native_inventory_must_include_every_retained_library():
    with pytest.raises(ValueError,match='OS_SCAN_COVERAGE_INCOMPLETE'):
        verify({'bomFormat':'CycloneDX','components':[{'purl':'pkg:deb/debian/libc6@2.41'}]},
               {'format':'with-human-runtime-closure-1','os_packages':['libc6','libssl3t64']},
               {'Metadata':{'OS':{'Family':'debian'}},'Results':[{'Class':'os-pkgs','Type':'debian'}]})


@pytest.mark.parametrize('severity',['HIGH','CRITICAL'])
def test_native_inventory_does_not_override_vulnerability_failure(severity):
    with pytest.raises(ValueError,match='HIGH_CRITICAL_VULNERABILITY'):
        verify({'bomFormat':'CycloneDX','components':[{'purl':'pkg:deb/debian/libc6@2.41'}]},
               {'format':'with-human-runtime-closure-1','os_packages':['libc6']},
               {'Metadata':{'OS':{'Family':'debian'}},'Results':[{'Class':'os-pkgs','Type':'debian',
                 'Vulnerabilities':[{'Severity':severity}]}]})


def test_other_distribution_rating_does_not_replace_scanner_selected_severity():
    sbom = {'bomFormat':'CycloneDX','components':[{'purl':'pkg:deb/debian/libc6@2.41'}],
            'vulnerabilities':[{'ratings':[{'source':{'name':'other-distribution'},'severity':'high'}]}]}
    scan = {'Metadata':{'OS':{'Family':'debian'}},'Results':[{'Class':'os-pkgs','Type':'debian',
            'Vulnerabilities':[{'Severity':'MEDIUM','SeveritySource':'debian'}]}]}
    assert verify(sbom,{'format':'with-human-runtime-closure-1','os_packages':['libc6']},scan)['state'] == 'PASS'
