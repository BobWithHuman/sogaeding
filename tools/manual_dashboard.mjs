import {launch} from './browser_helpers.mjs';
import fs from 'node:fs/promises';
const context=await launch('artifacts/profile-f3-01',false);
const page=await context.newPage();
await page.goto('https://127.0.0.1:8020');
await page.locator('#token').fill((await fs.readFile('artifacts/runtime-f3-01/control/human.token','utf8')).trim());
if(process.argv[2]) await fs.writeFile(process.argv[2],JSON.stringify({ready:true,models_started:0,sessions_created:0}));
// No session creation, tool/candidate submission or model invocation here.
await new Promise(resolve=>context.on('close',resolve));
