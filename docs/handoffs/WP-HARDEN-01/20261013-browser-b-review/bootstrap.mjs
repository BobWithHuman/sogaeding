import {launch} from '../../../../tools/browser_helpers.mjs';
const context = await launch('artifacts/profile-browser-b-review');
await context.newPage();
console.log(JSON.stringify({browser:context.browser().version(),action:'Dedicated profile initialization',ignoreHTTPSErrors:false}));
await context.close();
