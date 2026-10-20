// Initialize NSS through Firefox before importing the task CA. No URL visit.
import {launch} from './browser_helpers.mjs';
import path from 'node:path';
const profile=path.resolve(process.argv[2]??'artifacts/profile-browser-b-firefox');
const scope=path.resolve('artifacts')+path.sep;
if(!profile.startsWith(scope)||!path.basename(profile).includes('profile')) throw new Error('Dedicated profile required');
const context=await launch(profile);
await context.close();
console.log(JSON.stringify({profile:path.relative(process.cwd(),profile),initialized:true,network_page_visit:false}));
