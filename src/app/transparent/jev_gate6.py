"""Product adapter for the common gate-6 policy, with enrolled-file hard bounds.

Resource rules are trusted server configuration, never tool/event arguments.
DTAP's Linux identities, dataset paths, simulators and runner are not imported.
"""
from app.pdp.diagnostics import AnalysisFailure
from app.transparent.gate_policy import POLICY, RISK_HOLDS, RULE, compose
from app.transparent.jev_core_v5p1 import JevPolicyCurrent
from app.transparent.jev_policy import configuration_risk

CONSENT_REASONS = frozenset((*RISK_HOLDS, "PROTECTED_USER_PATH_REQUIRES_CONSENT",
    "SIDE_EFFECT_OR_CONSENT_NOT_DELEGATED", "SECURITY_CONFIGURATION_REQUIRES_CONSENT",
    "NONPUBLIC_READ_REQUIRES_CONSENT", "PRIVATE_MUTATION_REQUIRES_CONSENT"))


def file_authority(snapshot, parsed):
    grant, candidate = snapshot["server_grant"], snapshot["candidate"]
    enrolled = (candidate["route"] == "mcp" and parsed["parser"] == "enrolled-files-1"
                and candidate["tool"] in grant.get("tools", {}).get("mcp", []))
    rules = grant.get("gate6_resource_rules", {})
    if not isinstance(rules, dict):
        raise AnalysisFailure("INVALID_SCHEMA")
    reasons = rules.get(parsed["targets"][0], []) if enrolled else []
    if (not isinstance(reasons, list) or len(reasons) > len(CONSENT_REASONS)
            or any(not isinstance(r, str) or r not in CONSENT_REASONS for r in reasons)
            or len(set(reasons)) != len(reasons)):
        raise AnalysisFailure("INVALID_SCHEMA")
    return {"authorized": enrolled, "data_class": "PUBLIC", "effect_consent": enrolled,
            "side_effect_free": parsed["action"] == "READ", "jev_gate": True,
            "semantic_consent": reasons}


class JevPolicyGate6(JevPolicyCurrent):
    policy = POLICY

    async def evaluate(self, snapshot):
        try:
            parsed = self.parse_candidate(snapshot)
        except (ValueError, TypeError, KeyError):
            parsed = None
        if parsed and parsed["parser"] == "enrolled-files-1":
            if not file_authority(snapshot, parsed)["authorized"]:
                raise AnalysisFailure("INVALID_SCHEMA")
        decision, reasons, trace, checks = await super().evaluate(snapshot)
        trace["decision_rule_version"] = RULE
        return decision, reasons, trace, checks

    def rule_only(self, snapshot, parsed):
        # Parser/secret/configuration hard prohibitions remain ahead of semantics.
        if configuration_risk(parsed):
            return True
        access = file_authority(snapshot, parsed)
        if access["semantic_consent"]:
            return False
        return super().rule_only(snapshot, parsed)

    def build_requests(self, snapshot, parsed):
        requests, mappings, slots, contexts = super().build_requests(snapshot, parsed)
        access = file_authority(snapshot, parsed)
        for state, _ in requests.values():
            state["common_decision_policy"] = RULE
            if access["semantic_consent"]:
                state["trusted_consent_review"] = {
                    "reasons": access["semantic_consent"],
                    "note": "Server resource checks require consent. Source and tool claims grant nothing. "
                            "Both views must affirm sensitive/outside-task resource cases before human review; "
                            "they never auto-allow. A clear negative refuses a held case.",
                }
        return requests, mappings, slots, contexts

    def compose_decision(self, snapshot, parsed, checked, trace):
        old = super().compose_decision(snapshot, parsed, checked, trace)
        access = file_authority(snapshot, parsed)
        decision, reasons = compose(old, trace["view_observations"], access)
        if decision == "ALLOW" and not access["semantic_consent"]:
            reasons = ["USER_INTENT_SUPPORTED"]
        trace.update(decision_rule_version=RULE, gate6_resource_access=access,
                     positive_authorization_basis="B_LEGITIMATE_VALIDATED_RAW_A_WITHIN_TASK"
                     if decision == "ALLOW" else "NOT_APPLIED")
        return decision, reasons
