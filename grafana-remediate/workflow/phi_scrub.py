#!/usr/bin/env python3
# PHI / governance egress gate (scope 146, Phase 2) — the hard stop before ANY egress.
#
# Approach: deterministic detect-and-redact, conservative (over-redact rather than
# leak). Runs on every outbound payload — email body AND PR title/description/diff —
# BEFORE it reaches SES or GitHub. Autoplan's top finding: alarm labels carry tenant
# ids and root-cause pulls logs that can hold patient data; for a SATU SEHAT product
# that egress is a compliance decision, not an implementation detail. This gate makes
# "no PHI / tenant-identifying data leaves the estate" mechanical and testable.
#
# NOT an LLM step: PHI detection must be deterministic and auditable, not probabilistic.
# gate(text) -> (ok, findings, redacted). Caller policy: ok False => HOLD the egress,
# emit only the redacted form to a human, never auto-send the raw.
#
# Stdlib only.

import re

# Order matters: more specific patterns first so a JWT isn't split by the digit rule.
PATTERNS = [
    ("jwt",         re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
    ("bearer",      re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")),
    ("service_key", re.compile(r"(?i)(x-service-key|api[_-]?key|secret)\s*[:=]\s*\S+")),
    ("nik",         re.compile(r"\b\d{16}\b")),                         # Indonesian national ID
    ("ihs",         re.compile(r"\b[PNО]\d{8,12}\b")),                  # SATU SEHAT IHS patient/practitioner id
    ("email",       re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone_id",    re.compile(r"(?<!\d)(?:\+62|62|0)8\d{7,12}\b")),    # ID mobile
    ("tenant",      re.compile(r"\bclinic_\d+\b")),                     # tenant schema id
]

def scan(text):
    """Return list of (type, matched_text) findings, most-specific-first."""
    found, spans = [], []
    for name, rx in PATTERNS:
        for m in rx.finditer(text):
            # skip if this span overlaps an already-claimed (more specific) span
            if any(m.start() < e and s < m.end() for s, e in spans):
                continue
            spans.append((m.start(), m.end()))
            found.append((name, m.group()))
    return found

def redact(text):
    out = text
    for name, rx in PATTERNS:
        out = rx.sub(f"[REDACTED:{name}]", out)
    return out

def gate(text):
    """(ok, findings, redacted). ok True only when NOTHING sensitive was found."""
    findings = scan(text)
    return (len(findings) == 0, findings, redact(text))

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        ok, f, red = gate(open(sys.argv[1]).read())
        print(f"ok={ok} findings={[t for t,_ in f]}")
        print(red)
    else:
        # self-test with synthetic PHI/secrets (no real data)
        sample = ("Incident on clinic_5: patient NIK 3204012509900001 (IHS P02478375538) "
                  "hit a 500. Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.abc-_123 "
                  "reported by ops@kalpahealth.com / +6281234567890. x-service-key=supersecretval")
        ok, findings, red = gate(sample)
        assert not ok, "should have flagged"
        types = {t for t, _ in findings}
        for expect in {"nik", "ihs", "jwt", "email", "phone_id", "tenant", "service_key"}:
            assert expect in types, f"missed {expect} (got {types})"
        assert "3204012509900001" not in red and "supersecretval" not in red and "clinic_5" not in red
        print("self-test PASS — flagged:", sorted(types))
        print("redacted:", red)
