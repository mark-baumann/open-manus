"""
Handbook Compliance Module
==========================
Implementiert Policy-Enforcement für AI-Agenten basierend auf
"HANDBOOK.md: A Benchmark for Long-Context Agentic Instruction Following"
(arXiv:2607.25398).

Kernidee: Agenten verlieren lange Policy-Dokumente über die Zeit.
Dieses Modul implementiert:
1. Policy Chunking & Indexing
2. Pre-Action Policy Check (vor jeder Tool-Ausführung)
3. Post-Action Compliance Verification
4. Policy Drift Detection
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import hashlib


class PolicyRuleType(Enum):
    """Typ einer Policy-Regel."""
    MUST_DO = "must_do"       # Erforderliche Aktion
    MUST_NOT_DO = "must_not_do"  # Verbotene Aktion
    CONDITIONAL = "conditional"  # Bedingte Regel
    THRESHOLD = "threshold"      # Schwellwert-basierte Regel


@dataclass
class PolicyRule:
    """Eine einzelne Policy-Regel aus dem Handbook."""
    id: str
    rule_type: PolicyRuleType
    description: str
    condition: Optional[str] = None
    threshold: Optional[float] = None
    domain: str = "general"
    priority: int = 1  # 1=niedrig, 5=kritisch

    def to_prompt_snippet(self) -> str:
        """Konvertiert die Regel in ein kompaktes Prompt-Snippet."""
        prefix = {
            PolicyRuleType.MUST_DO: "⚠️ MUSS",
            PolicyRuleType.MUST_NOT_DO: "🚫 VERBOTEN",
            PolicyRuleType.CONDITIONAL: "❓ WENN",
            PolicyRuleType.THRESHOLD: "📏 SCHWELLE",
        }[self.rule_type]
        return f"[{prefix}] {self.description}"


@dataclass
class ComplianceCheck:
    """Ergebnis eines Compliance-Checks."""
    rule_id: str
    passed: bool
    reason: str
    action_taken: Optional[str] = None
    timestamp: str = ""


class HandbookPolicy:
    """
    Repräsentiert ein vollständiges Handbook/Policy-Dokument.
    
    Features:
    - Chunking langer Dokumente in thematische Sektionen
    - Regel-Extraktion mit Prioritäten
    - Domain-basierte Filterung (nur relevante Regeln laden)
    """

    def __init__(self, content: str, name: str = "handbook"):
        self.name = name
        self.content = content
        self.rules: List[PolicyRule] = []
        self.sections: Dict[str, str] = {}
        self._parse()

    def _parse(self):
        """Parst das Handbook in Sektionen und extrahiert Regeln."""
        # In Produktion: LLM-basierte Extraktion
        # Hier: regelbasierte Heuristik für Demo
        
        # Sektionen an ##-Überschriften erkennen
        sections = re.split(r'\n(?=## )', self.content)
        for section in sections:
            header_match = re.match(r'## (.+)', section)
            if header_match:
                section_name = header_match.group(1).strip().lower()
                self.sections[section_name] = section
        
        # Regeln aus MUST/MUST NOT/SHOULD-Patterns extrahieren
        rule_patterns = [
            (r'(?:MUST|MUSS)\s+(?:NOT|NICHT)\s+(.+)', PolicyRuleType.MUST_NOT_DO),
            (r'(?:MUST|MUSS)\s+(.+)', PolicyRuleType.MUST_DO),
            (r'(?:IF|WENN)\s+(.+?)(?:,\s*THEN|,\s*DANN)\s+(.+)', PolicyRuleType.CONDITIONAL),
        ]
        
        for pattern, rule_type in rule_patterns:
            for match in re.finditer(pattern, self.content, re.IGNORECASE):
                desc = match.group(1).strip().rstrip('.')
                rule_id = hashlib.md5(desc.encode()).hexdigest()[:8]
                self.rules.append(PolicyRule(
                    id=rule_id,
                    rule_type=rule_type,
                    description=desc,
                ))

    def get_relevant_rules(self, action_context: str, domain: Optional[str] = None) -> List[PolicyRule]:
        """
        Gibt die für eine geplante Aktion relevanten Regeln zurück.
        Verwendet Keyword-Matching zwischen Action-Context und Regel-Text.
        """
        relevant = []
        action_words = set(action_context.lower().split())
        
        for rule in self.rules:
            if domain and rule.domain != domain:
                continue
            rule_words = set(rule.description.lower().split())
            overlap = action_words & rule_words
            if len(overlap) > 0:
                relevant.append(rule)
        
        # Sortiere nach Priorität (kritische zuerst)
        relevant.sort(key=lambda r: r.priority, reverse=True)
        return relevant

    def build_policy_prompt(self, action_context: str, max_rules: int = 10) -> str:
        """
        Baut einen kompakten Policy-Prompt für den Agenten.
        Nur die relevantesten Regeln werden inkludiert.
        """
        rules = self.get_relevant_rules(action_context)[:max_rules]
        if not rules:
            return ""
        
        snippets = [r.to_prompt_snippet() for r in rules]
        return "📋 AKTIVE RICHTLINIEN:\n" + "\n".join(snippets)


class ComplianceGuard:
    """
    Pre-Action und Post-Action Compliance-Checks.
    
    Wird VOR jeder Tool-Ausführung und NACH jeder Aktion aufgerufen,
    um Policy-Verstöße zu verhindern und zu erkennen.
    """

    def __init__(self, policy: HandbookPolicy):
        self.policy = policy
        self.violation_log: List[ComplianceCheck] = []

    def pre_action_check(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Prüft VOR einer Aktion, ob sie gegen die Policy verstößt.
        Returns: (erlaubt, Begründung)
        """
        action_context = f"{action} {' '.join(str(v) for v in params.values())}"
        rules = self.policy.get_relevant_rules(action_context)
        
        for rule in rules:
            if rule.rule_type == PolicyRuleType.MUST_NOT_DO:
                # Prüfe, ob die Aktion einer verbotenen Regel ähnelt
                if self._action_matches_rule(action, rule):
                    check = ComplianceCheck(
                        rule_id=rule.id,
                        passed=False,
                        reason=f"Verbotene Aktion: {rule.description}",
                        action_taken=action,
                    )
                    self.violation_log.append(check)
                    return False, check.reason
        
        return True, "OK"

    def post_action_check(self, action: str, result: Any) -> ComplianceCheck:
        """
        Prüft NACH einer Aktion, ob das Ergebnis policy-konform ist.
        """
        # Prüfe MUST_DO-Regeln: Wurden erforderliche Aktionen ausgeführt?
        rules = self.policy.get_relevant_rules(action)
        
        for rule in rules:
            if rule.rule_type == PolicyRuleType.MUST_DO:
                if not self._action_satisfies_rule(action, result, rule):
                    check = ComplianceCheck(
                        rule_id=rule.id,
                        passed=False,
                        reason=f"Erforderliche Aktion nicht ausgeführt: {rule.description}",
                        action_taken=action,
                    )
                    self.violation_log.append(check)
                    return check
        
        return ComplianceCheck(
            rule_id="all",
            passed=True,
            reason="Alle Checks bestanden",
        )

    def _action_matches_rule(self, action: str, rule: PolicyRule) -> bool:
        """Prüft, ob eine Aktion einer Regel entspricht (Keyword-Overlap)."""
        action_words = set(action.lower().split())
        rule_words = set(rule.description.lower().split())
        overlap = action_words & rule_words
        return len(overlap) / max(len(rule_words), 1) > 0.3

    def _action_satisfies_rule(self, action: str, result: Any, rule: PolicyRule) -> bool:
        """Prüft, ob eine Aktion eine MUST_DO-Regel erfüllt."""
        # Vereinfacht: Prüft, ob die Aktion überhaupt stattfand
        return result is not None

    def get_violation_summary(self) -> str:
        """Gibt eine Zusammenfassung aller Verstöße."""
        if not self.violation_log:
            return "✅ Keine Policy-Verstöße."
        
        violations = [c for c in self.violation_log if not c.passed]
        return f"⚠️ {len(violations)} Policy-Verstoß(e):\n" + "\n".join(
            f"  - {v.reason}" for v in violations
        )


class PolicyDriftDetector:
    """
    Erkennt, wenn der Agent über die Zeit von der Policy abweicht
    (Policy Drift / "Lost in the Middle"-Effekt).
    """

    def __init__(self, policy: HandbookPolicy, window_size: int = 10):
        self.policy = policy
        self.window_size = window_size
        self.action_history: List[str] = []

    def record_action(self, action: str):
        """Zeichnet eine Aktion auf."""
        self.action_history.append(action)
        if len(self.action_history) > self.window_size * 2:
            self.action_history = self.action_history[-self.window_size:]

    def detect_drift(self) -> float:
        """
        Berechnet einen Drift-Score (0=perfekt, 1=komplett abgewichen).
        Vergleicht aktuelle Aktionen mit Policy-Regeln.
        """
        if len(self.action_history) < self.window_size:
            return 0.0
        
        recent = self.action_history[-self.window_size:]
        rules = self.policy.rules
        
        if not rules:
            return 0.0
        
        violations = 0
        for action in recent:
            for rule in rules:
                if rule.rule_type == PolicyRuleType.MUST_NOT_DO:
                    action_words = set(action.lower().split())
                    rule_words = set(rule.description.lower().split())
                    if len(action_words & rule_words) / max(len(rule_words), 1) > 0.3:
                        violations += 1
        
        return min(violations / (len(recent) * max(len(rules), 1)), 1.0)

    def should_reinject_policy(self) -> bool:
        """
        Entscheidet, ob die Policy erneut in den Kontext eingefügt werden muss.
        True wenn Drift > 0.3 (30% Abweichung).
        """
        return self.detect_drift() > 0.3
