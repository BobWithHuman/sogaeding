import asyncio
import base64
import json
import ssl
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import hookgw_hook as hook
import hookgw_mcp as bridge
import product_codex as connector
import pytest

from app.transparent.engine import Rejected


def host_profile(tmp_path):
    workspace=tmp_path/"workspace"
    workspace.mkdir()
    runtime=tmp_path/"runtime"
    (runtime/"host").mkdir(parents=True)
    for name in connector.ROLE_FILES:
        (runtime/"host"/name).write_text("synthetic-"+name)
    (runtime/"host/storage.key").write_text("do-not-export")
    host=tmp_path/"client"
    connector.export_host(runtime,host,str(workspace),8130,8140)
    return workspace,host


def test_export_new_host_only_selected_credentials_and_never_replace(tmp_path):
    workspace,host=host_profile(tmp_path)
    assert {p.name for p in host.iterdir()}=={*connector.ROLE_FILES,"profile.json"}
    assert connector.profile_for(host)["workspace"]==str(workspace)
    with pytest.raises(ValueError,match="NEW_HOST"):
        connector.export_host(tmp_path/"runtime",host,str(workspace),8130,8140)


def test_private_windows_writer_bundle_excludes_server_secrets(tmp_path):
    host_profile(tmp_path)
    bundle=connector.export_bundle(tmp_path/"runtime")
    assert set(bundle)==set(connector.ROLE_FILES)
    assert base64.b64decode(bundle["machine.token"])==b"synthetic-machine.token"
    assert "do-not-export" not in json.dumps(bundle)


@pytest.mark.parametrize('adapter,tools',[(None,['read_file','write_file']),
    ('npm-lab-1',['read_github_issue','read_project_file','edit_project_file','run_npm_install'])])
def test_reattach_bundle_uses_existing_enrollment_without_server_keys(tmp_path,adapter,tools):
    host_profile(tmp_path)
    (tmp_path/'runtime/control').mkdir()
    (tmp_path/'runtime/control/grant.json').write_text(json.dumps({
        'adapter':adapter, 'workspace':'/files', 'tools':{'mcp':tools}}))
    bundle=connector.export_bundle(tmp_path/'runtime',include_metadata=True)
    assert bundle['format']=='product-connector-bundle-1' and bundle['adapter']==adapter
    assert set(bundle['roles'])==set(connector.ROLE_FILES)
    assert 'do-not-export' not in json.dumps(bundle)


def test_reattach_refuses_unknown_runtime_tool_enrollment(tmp_path):
    host_profile(tmp_path)
    (tmp_path/'runtime/control').mkdir()
    (tmp_path/'runtime/control/grant.json').write_text(json.dumps({
        'workspace':'/files', 'tools':{'mcp':['arbitrary_shell']}}))
    with pytest.raises(ValueError,match='SUPPORTED_PRODUCT_GRANT_REQUIRED'):
        connector.export_bundle(tmp_path/'runtime',include_metadata=True)


@pytest.mark.parametrize('transient',[ConnectionRefusedError(),ssl.SSLEOFError()])
def test_health_waits_for_startup_without_retrying_any_model_or_tool(tmp_path,monkeypatch,transient):
    _,host=host_profile(tmp_path)
    requests=[]
    def send(_host,endpoint,body,**kwargs):
        assert endpoint=="/health" and body is None and kwargs=={"method":"GET","timeout":2}
        requests.append(endpoint)
        if len(requests)==1:
            raise urllib.error.URLError(transient)
        return {"decision_policy":connector.POLICY,"judge_mode":"JEV_USER_LIVE"}
    monkeypatch.setattr(connector,"send",send)
    monkeypatch.setattr(connector.time,"sleep",lambda _:None)
    assert connector.check(host)["state"]=="READY" and len(requests)==2


@pytest.mark.parametrize("failure",[urllib.error.HTTPError("https://127.0.0.1",403,"denied",{},None),
                                   urllib.error.URLError(ssl.SSLCertVerificationError())])
def test_health_does_not_retry_authentication_or_tls_failure(tmp_path,monkeypatch,failure):
    _,host=host_profile(tmp_path)
    def send(*args,**kwargs):
        raise failure
    monkeypatch.setattr(connector,"send",send)
    monkeypatch.setattr(connector.time,"sleep",lambda _:pytest.fail("Do not retry auth or TLS failure"))
    with pytest.raises(urllib.error.URLError):
        connector.check(host)


def test_hook_verifies_actual_cwd_before_mapping_to_enrolled_mcp_namespace(tmp_path,monkeypatch):
    workspace,host=host_profile(tmp_path)
    sent=[]
    monkeypatch.setattr(hook,"send",lambda *args,**kwargs:sent.append(args) or {})
    value={"hook_event_name":"UserPromptSubmit","cwd":str(workspace),"session_id":"s","turn_id":"t","prompt":"Read the release."}
    hook.handle(host,value,"synthetic-connection")
    assert sent[0][2]["cwd"]=="/files" and sent[0][2]["prompt"]==value["prompt"]
    with pytest.raises(hook.HookFailure,match="WORKSPACE_MISMATCH"):
        hook.handle(host,{**value,"cwd":str(tmp_path)},"synthetic-connection")
    assert len(sent)==1


def test_mcp_only_profile_does_not_accept_native_tool_candidate(tmp_path,monkeypatch):
    workspace,host=host_profile(tmp_path)
    monkeypatch.setattr(hook,"send",lambda *args,**kwargs:pytest.fail("Native candidate must not be submitted"))
    value={"hook_event_name":"PreToolUse","cwd":str(workspace),"session_id":"s","turn_id":"t",
           "tool_name":"Bash","tool_use_id":"c","tool_input":{"command":"echo anything"}}
    with pytest.raises(hook.HookFailure,match="UNSUPPORTED_NATIVE_TOOL"):
        hook.handle(host,value,"synthetic-connection")


@pytest.mark.parametrize("mutation",["remote","http","wrong_namespace","missing_mcp_only"])
def test_invalid_product_profile_rejected(tmp_path,mutation):
    _,host=host_profile(tmp_path)
    profile=json.loads((host/"profile.json").read_text())
    if mutation=="remote":
        profile["control_url"]="https://untrusted.invalid:8130"
    elif mutation=="http":
        profile["gateway_url"]="http://127.0.0.1:8140/mcp"
    elif mutation=="wrong_namespace":
        profile["engine_workspace"]="/"
    else:
        profile.pop("mcp_only")
    (host/"profile.json").write_text(json.dumps(profile))
    with pytest.raises(ValueError):
        connector.profile_for(host)


def test_start_uses_existing_login_and_model_and_disconnects_after_cli(tmp_path,monkeypatch):
    workspace,host=host_profile(tmp_path)
    executable=tmp_path/"installed-codex.exe"
    executable.write_bytes(b"synthetic-not-executable")
    monkeypatch.chdir(workspace)
    events=[]
    def send(_host,endpoint,body,**kwargs):
        events.append((endpoint,body))
        if endpoint=="/health":
            return {"decision_policy":connector.POLICY,"judge_mode":"JEV_USER_LIVE"}
        if endpoint=="/connect":
            return {"connection":"synthetic-only"}
        assert endpoint=="/connections/close" and body=={"connection":"synthetic-only"}
        return {"state":"CLOSED"}
    monkeypatch.setattr(connector,"send",send)
    monkeypatch.setattr(connector.launcher,"check_conflicts",lambda root,args,**kwargs:None)
    monkeypatch.setattr(connector,'product_overrides',lambda root,host,exe:connector.launcher.overrides(root,host,'python',mcp_only=True))
    def run(argv,**kwargs):
        assert kwargs["env"]["WITH_HUMAN_CONNECTION"]=="synthetic-only"
        assert not any("model=" in item or "model_provider=" in item or "approval_policy=" in item or "sandbox=" in item for item in argv)
        assert any("hookgw_hook.py" in item for item in argv) and any("hookgw_mcp.py" in item for item in argv)
        assert "features.shell_tool=false" in argv
        return SimpleNamespace(returncode=17)
    monkeypatch.setattr(connector.subprocess,"run",run)
    assert connector.start(Path(__file__).resolve().parents[2],host,executable)==17
    assert [row[0] for row in events]==["/health","/connect","/connections/close"]


def test_history_reports_bounded_scope_without_prompt_or_quote(tmp_path,monkeypatch):
    _,host=host_profile(tmp_path)
    def send(*args,**kwargs):
        assert kwargs["human"] and kwargs["method"]=="GET"
        assert args[1]=="/history/summary"
        return {"scope":"LATEST_100_CALLS","counts":{"DENY":1},"calls":[{"id":"w","decision":"DENY","state":"DENIED",
            "policy":connector.POLICY,"reasons":["OUTSIDE_TASK_SCOPE"],"routing":"SEMANTIC"}]}
    monkeypatch.setattr(connector,"send",send)
    value=connector.history(host)
    assert value["counts"]=={"DENY":1} and value["scope"]=="LATEST_100_CALLS"
    assert "PRIVATE_DO_NOT_DISPLAY" not in json.dumps(value)


def test_cli_configuration_check_never_connects_or_starts_a_model(tmp_path,monkeypatch):
    workspace,host=host_profile(tmp_path)
    executable=tmp_path/"installed-codex.exe"
    executable.write_bytes(b"synthetic-not-executable")
    monkeypatch.chdir(workspace)
    monkeypatch.setattr(connector,"send",lambda *args,**kwargs:pytest.fail("No engine session in CLI check"))
    monkeypatch.setattr(connector.launcher,"check_conflicts",lambda *args,**kwargs:None)
    monkeypatch.setattr(connector,'product_overrides',lambda root,host,exe:connector.launcher.overrides(root,host,'python',mcp_only=True))
    def run(argv,**kwargs):
        assert argv[-2:]==["features","list"] and kwargs["timeout"]==30
        assert "features.shell_tool=false" in argv
        return SimpleNamespace(returncode=0,stdout="hooks stable true\nshell_tool stable false\n")
    monkeypatch.setattr(connector.subprocess,"run",run)
    assert connector.cli_check(tmp_path,host,executable)["interactive_session"]=="NOT_STARTED"


def test_cli_check_rejects_native_shell_still_enabled(tmp_path,monkeypatch):
    workspace,host=host_profile(tmp_path)
    executable=tmp_path/'codex'
    executable.write_bytes(b'synthetic')
    monkeypatch.chdir(workspace)
    monkeypatch.setattr(connector.launcher,'check_conflicts',lambda *a,**kw:None)
    monkeypatch.setattr(connector,'product_overrides',lambda root,host,exe:connector.launcher.overrides(root,host,'python',mcp_only=True))
    monkeypatch.setattr(connector.subprocess,'run',lambda *a,**kw:SimpleNamespace(
        returncode=0,stdout='hooks stable true\nshell_tool stable true\n'))
    with pytest.raises(ValueError,match='CODEX_HOOK_CONFIGURATION_UNAVAILABLE'):
        connector.cli_check(workspace,host,executable)


def test_file_workspace_metadata_preserves_schema_and_never_supplies_decision():
    schema={'type':'object','required':['path'],'additionalProperties':False}
    result={'tools':[{'name':'read_file','description':'old','inputSchema':schema},
                     {'name':'write_file','description':'old','inputSchema':schema},
                     {'name':'other','description':'unchanged','inputSchema':schema}]}
    bridge.product_metadata('tools/list',result)
    assert all(t['inputSchema']==schema for t in result['tools'])
    assert 'connected Docker file workspace' in result['tools'][0]['description']
    assert result['tools'][2]['description']=='unchanged'
    instructions=bridge.product_metadata('initialize',{})['instructions']
    assert 'not the host repository' in instructions and 'native user form' in instructions
    assert 'reason_details' in instructions and 'cannot grant consent' in instructions
    assert not any(s in instructions for s in ('release.md','release-normal.md','ask-demo.md','.env','SECURITY_REVIEW_REQUIRED'))


def test_shell_visibility_override_is_scoped_to_product_not_other_launchers(tmp_path):
    common=connector.launcher.overrides(tmp_path,tmp_path/'host','python')
    product=connector.launcher.overrides(tmp_path,tmp_path/'host','python',mcp_only=True)
    assert 'features.shell_tool=false' not in common
    assert 'features.shell_tool=false' in product
    assert not any('approval_policy=' in s or 'sandbox=' in s or 'model=' in s for s in product)


def test_product_mcp_catalog_disables_personal_and_auto_registered_servers_without_secrets(tmp_path,monkeypatch):
    executable=tmp_path/'codex'
    executable.write_bytes(b'synthetic')
    node=tmp_path/'node'
    node.write_bytes(b'synthetic')
    probes=[]
    def run(argv,**kwargs):
        assert argv[-3:]==['mcp','list','--json'] and kwargs['encoding']=='utf-8'
        probes.append(argv)
        assert 'PRIVATE_ENV_VALUE' not in str(argv) and 'PRIVATE_ARG_VALUE' not in str(argv)
        others_disabled='mcp_servers.bob-agentgateway.enabled=false' in argv
        if others_disabled and 'mcp_servers.cua_repl.command='+json.dumps(str(node)) not in argv:
            return SimpleNamespace(returncode=1,stdout='')
        return SimpleNamespace(returncode=0,stdout=json.dumps([
            {'name':'with_human','enabled':True,'transport':{'type':'stdio','command':str(node)}},
            {'name':'bob-agentgateway','enabled':not others_disabled,
             'transport':{'type':'streamable_http','url':'http://localhost:4400/mcp','http_headers':{'Authorization':'PRIVATE_ENV_VALUE'}}},
            {'name':'cua_repl','enabled':not others_disabled,
             'transport':{'type':'stdio','command':str(node),'args':['PRIVATE_ARG_VALUE'],'env':{'KEY':'PRIVATE_ENV_VALUE'}}}]))
    monkeypatch.setattr(connector.subprocess,'run',run)
    flags=connector.product_overrides(tmp_path,tmp_path/'host',executable)
    assert len(probes)==3 and 'mcp_servers.cua_repl.enabled=false' in flags
    assert 'mcp_servers.cua_repl.command='+json.dumps(str(node)) in flags
    assert not any('http://localhost:4400' in s for s in flags)


@pytest.mark.parametrize('kind',['missing_product','forced_server','malformed'])
def test_product_mcp_catalog_fails_closed_on_unverified_configuration(tmp_path,monkeypatch,kind):
    def run(argv,**kwargs):
        values=[{'name':'with_human','enabled':True}]
        if kind=='missing_product':
            values=[]
        if kind=='forced_server':
            values.append({'name':'unbound','enabled':True,'transport':{'type':'streamable_http','url':'http://localhost:4400/mcp'}})
        return SimpleNamespace(returncode=0,stdout='{}' if kind=='malformed' else json.dumps(values))
    monkeypatch.setattr(connector.subprocess,'run',run)
    with pytest.raises(ValueError):
        connector.product_overrides(tmp_path,tmp_path/'host',tmp_path/'codex')


def test_product_disables_configured_remote_mcp_without_copying_its_private_url(tmp_path,monkeypatch):
    def run(argv,**kwargs):
        assert 'PRIVATE_VALUE' not in str(argv)
        return SimpleNamespace(returncode=0,stdout=json.dumps([
            {'name':'with_human','enabled':True},
            {'name':'other','enabled':'mcp_servers.other.enabled=false' not in argv,
             'transport':{'type':'streamable_http','url':'https://example.invalid/mcp?token=PRIVATE_VALUE'}}]))
    monkeypatch.setattr(connector.subprocess,'run',run)
    flags=connector.product_overrides(tmp_path,tmp_path/'host',tmp_path/'codex')
    assert 'mcp_servers.other.enabled=false' in flags
    assert 'PRIVATE_VALUE' not in str(flags)


@pytest.mark.parametrize("stage",["READY","EXECUTING","ASK","PRESENTED"])
def test_session_close_revokes_authority_preserves_history_and_other_sessions(engine,observer,stage):
    token="synthetic-session-connection"
    engine.connect("m",token)
    engine.connection(token,"s")
    engine.turn("m","s","t","Write case 48217 internal margin to the draft.","/files")
    if stage in ("ASK","PRESENTED"):
        observer.b="UNCERTAIN"
    engine.register("m","s","t","w","write_file",{"path":"reports/draft.md","content":"Requested draft."},"mcp")
    result=asyncio.run(engine.authorize("m","w",ask_connection=token))
    if stage=="EXECUTING":
        engine.forward("m","w",connection_token=token)
    elif stage=="PRESENTED":
        ask=engine.pending_ask('m','s',token,'write_file',{'path':'reports/draft.md','content':'Requested draft.'})['ask']
        engine.ask_presented('m',token,ask['ask_id'],ask['nonce'])
    else:
        assert result["state"]==stage
    engine.connect("m","other-token")
    engine.connection("other-token","other-s")
    engine.turn("m","other-s","other-t","Read the release.","/files")
    with engine.db() as db:
        original_deadline=db.execute("SELECT deadline FROM expiry WHERE kind='session' AND id='s'").fetchone()[0]
    with pytest.raises(Rejected,match="CONNECTION_BINDING"):
        engine.close_session_connection("other-machine",token)
    assert engine.close_session_connection("m",token)=={"state":"CLOSED"}
    assert engine.close_session_connection("m",token)=={"state":"CLOSED"}
    with pytest.raises(Rejected):
        engine.connection(token)
    assert engine.connection("other-token")==("m","other-s")
    engine.connect("m","fresh-token")  # cleanup must not remove closed session history
    with pytest.raises(Rejected):
        engine.connection("fresh-token","s")
    with engine.db() as db:
        assert db.execute("SELECT deadline FROM expiry WHERE kind='session' AND id='s'").fetchone()[0]==original_deadline
        assert db.execute("SELECT state FROM calls WHERE id='w'").fetchone()[0]==("UNKNOWN" if stage=="EXECUTING" else "STALE")
        assert db.execute("SELECT count(*) FROM approvals WHERE consumed=0").fetchone()[0]==0
    assert any(row["id"]=="w" for row in engine.history())
    with pytest.raises(Rejected):
        engine.forward("m","w")


@pytest.mark.parametrize("layer",["root","profile"])
@pytest.mark.parametrize("conflict",["hooks","mcp"])
def test_product_launcher_rejects_all_profile_hook_and_reserved_mcp_conflicts(tmp_path,monkeypatch,layer,conflict):
    home=tmp_path/"codex-home"
    home.mkdir()
    workspace=tmp_path/"work"
    workspace.mkdir()
    monkeypatch.setenv("CODEX_HOME",str(home))
    monkeypatch.setattr(connector.launcher.Path,"home",classmethod(lambda cls:tmp_path/"empty-home"))
    section=("profiles.work." if layer=="profile" else "")+("hooks" if conflict=="hooks" else "mcp_servers.with_human")
    value="PreToolUse = []" if conflict=="hooks" else "url = 'https://existing.invalid/mcp'"
    (home/"config.toml").write_text("["+section+"]\n"+value+"\n")
    with pytest.raises(SystemExit,match="reviewed merge"):
        connector.launcher.check_conflicts(workspace,[],strict_product=True)
