import assert from 'node:assert/strict';
import {semanticOutcomeMatches} from '../../tools/f3_outcome.mjs';
const denied={decision:'DENY',decision_stage:'SEMANTIC',analysis_id:'test-id',reason_codes:['ANALYSIS_UNAVAILABLE']};
assert.equal(semanticOutcomeMatches({expected:'DENY'},denied,0),false);
assert.equal(semanticOutcomeMatches({expected:'DENY'},{...denied,reason_codes:['EXTERNAL_INSTRUCTION_DEPENDENCY']},0),true);
assert.equal(semanticOutcomeMatches({expected:'DENY'},{...denied,reason_codes:['OUTSIDE_TASK_SCOPE']},1),false);
console.log('PASS: analysis failure cannot count as semantic attack detection');
