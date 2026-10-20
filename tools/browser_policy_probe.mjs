import {launch} from './browser_helpers.mjs';
const c=await launch('artifacts/profile-browser-b-firefox');
try { const p=await c.newPage(); await p.goto('about:policies',{waitUntil:'commit',timeout:5000});
  console.log(JSON.stringify({browser:c.browser().version(),url:p.url(),policies:await p.locator('body').innerText({timeout:5000})}));
} finally {await c.close();}
