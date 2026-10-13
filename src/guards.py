"""Phase 5 policy guards: deterministic PII, advice, and returns checks.

No Groq, no UI, no ingest. Returns a structured result:
{"action": "allow" | "refuse" | "returns_redirect", "message": str | None,
 "citation_url": str | None}
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GuardResult:
    action: str
    message: str | None
    citation_url: str | None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SCHEME_URLS: dict[str, str] = {
    "large-cap": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "large cap": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "flexi-cap": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    "flexi cap": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    "equity fund": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    "elss": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    "tax saver": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    "small-cap": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "small cap": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "balanced advantage": "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
    "hybrid": "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
}
_DEFAULT_LINK = "https://groww.in/mutual-funds"


def _scheme_link(question: str) -> str | None:
    q = question.lower()
    # Check longer phrases first.
    for key in sorted(_SCHEME_URLS, key=len, reverse=True):
        if key in q:
            return _SCHEME_URLS[key]
    return None


def _mentions_pii(text: str) -> bool:
    q = text
    patterns = [
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",  # PAN
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Aadhaar-like 12 digits
        r"\b(?:\+?91[-\s]?)?[6-9]\d{9}\b",  # Indian mobile number
        r"\b[\w.+-]+@[\w-]+\.[A-Za-z]{2,}\b",  # email
        r"\b\d{9,18}\b",  # account-like long numeric runs
    ]
    if any(re.search(p, q) for p in patterns):
        return True

    low = q.lower()
    if re.search(r"\botp\b", low) and re.search(r"\b\d{4,8}\b", q):
        return True
    if "aadhaar" in low or "pan card" in low or "account number" in low:
        # Only treat as PII if a number is present; otherwise it is just a topic.
        if re.search(r"\d", q):
            return True
    return False


_ADVICE_PATTERNS = [
    r"\bbuy\b",
    r"\bsell\b",
    r"\bswitch\b",
    r"\bshould i\b",
    r"\bbest for me\b",
    r"\bbest fund\b",
    r"\brecommend(?:ed|ation)?\b",
    r"\badvice\b",
    r"\bshould you\b",
    r"\bworth (?:buying|investing)\b",
]

_RETURNS_PATTERNS = [
    r"\breturn(s)?\b",
    r"\bcagr\b",
    r"\bperformed better\b",
    r"\boutperform(?:ed|s)?\b",
    r"\btrack record\b",
    r"\bpast performance\b",
    r"\bwhich (?:fund|one|is) better\b",
    r"\branking\b",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    low = text.lower()
    return any(re.search(p, low, flags=re.IGNORECASE) for p in patterns)


def guard(question: str) -> GuardResult:
    """Run deterministic PII, advice, and returns guards."""
    if not isinstance(question, str):
        question = str(question)

    if _mentions_pii(question):
        return GuardResult(
            action="refuse",
            message=(
                "I can't help with personal or account identifiers. "
                "Please don't share PAN, Aadhaar, account numbers, OTPs, "
                "email, or phone numbers here. For account-specific help, "
                "use Groww/HDFC official support channels."
            ),
            citation_url=_DEFAULT_LINK,
            reason="pii",
        )

    if _matches_any(question, _ADVICE_PATTERNS):
        link = _scheme_link(question) or _DEFAULT_LINK
        return GuardResult(
            action="refuse",
            message=(
                "I can only provide facts about the listed HDFC schemes. "
                "I can't advise buying, selling, switching, or choosing "
                "investments. For scheme facts, see: " + link
            ),
            citation_url=link,
            reason="advice",
        )

    if _matches_any(question, _RETURNS_PATTERNS):
        link = _scheme_link(question) or _DEFAULT_LINK
        return GuardResult(
            action="returns_redirect",
            message=(
                "I can't compute or compare returns or performance. "
                "Please check the latest scheme page and official "
                "factsheet here: " + link
            ),
            citation_url=link,
            reason="returns",
        )

    return GuardResult(
        action="allow",
        message=None,
        citation_url=None,
        reason="allow",
    )


def main() -> int:
    tests = [
        ("PII", "My PAN is ABCDE1234F and OTP 482910, what is my balance?"),
        ("advice", "Should I buy HDFC Small Cap Fund Direct Growth?"),
        ("returns", "What is the CAGR of HDFC Large Cap Fund Direct Growth?"),
        ("normal", "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"),
    ]

    failures = 0
    for label, question in tests:
        result = guard(question)
        print(f"{label:8s} -> action={result.action}")
        if result.citation_url:
            print(f"           citation_url={result.citation_url}")
        # Never echo the test PII value itself.
        if result.action not in {"refuse", "returns_redirect", "allow"}:
            failures += 1

    expected = {"PII": "refuse", "advice": "refuse", "returns": "returns_redirect", "normal": "allow"}
    for label, question in tests:
        if guard(question).action != expected[label]:
            print(f"FAIL: {label} expected {expected[label]}")
            failures += 1

    print("\nSmoke test:", "PASS" if failures == 0 else "FAIL")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
