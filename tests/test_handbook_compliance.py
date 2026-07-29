"""
Tests für Handbook Compliance Modul.
"""
import pytest
from app.handbook_compliance import (
    HandbookPolicy,
    ComplianceGuard,
    PolicyDriftDetector,
    PolicyRule,
    PolicyRuleType,
    ComplianceCheck,
)


SAMPLE_HANDBOOK = """
# Company Handbook v1.0

## Data Privacy
MUST NOT share customer data with third parties.
MUST encrypt all data at rest.
IF data contains PII, THEN anonymize before processing.

## Financial
MUST get manager approval for purchases over 1000 EUR.
MUST NOT approve your own expenses.
MUST log all financial transactions.

## Communication
MUST respond to customer emails within 24 hours.
MUST NOT use informal language in official communications.
"""


class TestHandbookPolicy:
    def test_parse_rules(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        assert len(policy.rules) > 0
        must_not_rules = [r for r in policy.rules if r.rule_type == PolicyRuleType.MUST_NOT_DO]
        assert len(must_not_rules) >= 2

    def test_parse_sections(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        assert "data privacy" in policy.sections
        assert "financial" in policy.sections
        assert "communication" in policy.sections

    def test_get_relevant_rules(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        rules = policy.get_relevant_rules("share customer data with partner")
        assert len(rules) > 0
        # Sollte die MUST NOT share customer data Regel finden
        assert any("customer data" in r.description.lower() for r in rules)

    def test_get_relevant_rules_no_match(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        rules = policy.get_relevant_rules("xyzabc notindocument")
        assert len(rules) == 0

    def test_build_policy_prompt(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        prompt = policy.build_policy_prompt("share customer data")
        assert "MUSS" in prompt or "VERBOTEN" in prompt
        assert "customer data" in prompt.lower()

    def test_empty_handbook(self):
        policy = HandbookPolicy("")
        assert len(policy.rules) == 0
        assert policy.build_policy_prompt("anything") == ""


class TestComplianceGuard:
    def test_pre_action_blocks_forbidden(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        guard = ComplianceGuard(policy)
        allowed, reason = guard.pre_action_check(
            "share_data", {"target": "third_party", "data_type": "customer"}
        )
        assert allowed is False
        assert "customer" in reason.lower() or "Verboten" in reason

    def test_pre_action_allows_safe(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        guard = ComplianceGuard(policy)
        allowed, reason = guard.pre_action_check(
            "read_file", {"path": "/tmp/test.txt"}
        )
        assert allowed is True

    def test_post_action_check(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        guard = ComplianceGuard(policy)
        check = guard.post_action_check("log_transaction", {"status": "ok"})
        assert isinstance(check, ComplianceCheck)

    def test_violation_summary(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        guard = ComplianceGuard(policy)
        guard.pre_action_check("share_data", {"target": "third_party", "data_type": "customer"})
        summary = guard.get_violation_summary()
        assert "Verstoß" in summary or "violation" in summary.lower()


class TestPolicyDriftDetector:
    def test_no_drift_initially(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        detector = PolicyDriftDetector(policy, window_size=5)
        assert detector.detect_drift() == 0.0

    def test_drift_detection(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        detector = PolicyDriftDetector(policy, window_size=3)
        # Simuliere Aktionen, die gegen Policy verstoßen
        detector.record_action("share customer data with third party")
        detector.record_action("share customer data with third party")
        detector.record_action("share customer data with third party")
        drift = detector.detect_drift()
        assert drift > 0.0

    def test_should_reinject_policy(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        detector = PolicyDriftDetector(policy, window_size=3)
        assert detector.should_reinject_policy() is False
        # Viele Verstöße simulieren
        for _ in range(10):
            detector.record_action("share customer data with third party")
        assert detector.should_reinject_policy() is True

    def test_window_limit(self):
        policy = HandbookPolicy(SAMPLE_HANDBOOK)
        detector = PolicyDriftDetector(policy, window_size=3)
        for i in range(20):
            detector.record_action(f"action_{i}")
        # Sollte nur die letzten 3 Aktionen behalten
        assert len(detector.action_history) <= 3
