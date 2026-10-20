import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';

const require = createRequire(import.meta.url);
export const bundle = 'C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
export const {firefox} = require(bundle + '/playwright');
export const runtime = path.resolve(process.env.WITH_HUMAN_BROWSER_RUNTIME??'artifacts/runtime-browser-b');
export const baseURL = process.env.WITH_HUMAN_BROWSER_BASE_URL??'https://127.0.0.1:8010';
export const executable = path.resolve('artifacts/browser-tools-b/firefox-1538/firefox/firefox.exe');
export const policyPath = path.join(path.dirname(executable), 'distribution/policies.json');

export async function policy(trusted) {
  await fs.mkdir(path.dirname(policyPath), {recursive:true});
  await fs.writeFile(policyPath, JSON.stringify({policies:{
    Certificates:{ImportEnterpriseRoots:false, Install:trusted?[path.join(runtime,'ca.pem')]:[]},
    DisableAppUpdate:true, DisableTelemetry:true, DisableFirefoxStudies:true,
    DisableDefaultBrowserAgent:true, DontCheckDefaultBrowser:true, OfferToSaveLogins:false,
    DisableFormHistory:true, PasswordManagerEnabled:false,
  }},null,2));
}

export async function launch(profile, headless=true) {
  const browserEnv={};
  for(const key of ['PATH','SystemRoot','WINDIR','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])if(process.env[key])browserEnv[key]=process.env[key];
  return await firefox.launchPersistentContext(path.resolve(process.env.WITH_HUMAN_BROWSER_PROFILE??profile), {executablePath:executable,env:browserEnv,
    headless, ignoreHTTPSErrors:false, viewport:{width:1280,height:1000},
    firefoxUserPrefs:{'security.enterprise_roots.enabled':false, 'browser.policies.alternatePath':policyPath,
      'browser.sessionstore.resume_from_crash':false, 'browser.formfill.enable':false,
      'signon.rememberSignons':false, 'toolkit.telemetry.enabled':false}});
}

export async function driver(value) {
  return await new Promise((resolve,reject)=>{
    const child=spawn('docker',['compose','-f',process.env.WITH_HUMAN_BROWSER_COMPOSE??'compose.browser.yaml','run','--rm','-T','--no-deps',
                               'driver','python',process.env.WITH_HUMAN_BROWSER_DRIVER??'tools/browser_driver.py'],{windowsHide:true});
    let output='';
    child.stdout.on('data',data=>{output+=data.toString('utf8');});
    child.stderr.on('data',()=>{}); // Docker lifecycle only; no raw peer output.
    child.on('error',()=>reject(new Error('DRIVER_PROCESS_UNAVAILABLE')));
    child.on('close',code=>{
      try { const data=JSON.parse(output.trim());
        if(code!==0||data.driver_error) reject(new Error('SAFE_DRIVER_FAILURE'));
        else resolve(data);
      } catch { reject(new Error('SAFE_DRIVER_OUTPUT_ERROR')); }
    });
    child.stdin.end(JSON.stringify(value));
  });
}

export async function humanToken() { return (await fs.readFile(path.join(runtime,'control/human.token'),'utf8')).trim(); }
export async function screenshot(page,file) {
  await page.screenshot({path:file,fullPage:true,mask:[page.locator('input[type=password]'),page.locator('#request,#body')]});
}
