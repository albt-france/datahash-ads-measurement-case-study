"""Optional LLM call for the report draft. Off by default: the repository's deliverables use the sentence templates.

Turned on only when .env (never committed) sets LLM_PROVIDER, LLM_MODEL and LLM_API_KEY. The LLM may only rephrase
the template draft; every number it writes is then checked by src/check_numbers.py, and the draft is rejected if a
number cannot be traced to the fact sheet. Supported provider: "anthropic" (Messages API).
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                v = v.split(" #", 1)[0].strip()
                if v:
                    os.environ.setdefault(k.strip(), v)


def available() -> bool:
    _load_env()
    return bool(os.getenv("LLM_PROVIDER") and os.getenv("LLM_MODEL") and os.getenv("LLM_API_KEY"))


PROMPT = """You edit a client measurement report. Rewrite the draft below for a marketing director: clearer, shorter
sentences, same structure and headings. Rules: keep every number exactly as written (same digits, sign, unit and
decimals); add no number; never present EMQ or match rate as business value; keep the words "reported", "incremental",
"interval" where they are. Return only the rewritten markdown.

DRAFT:
"""


def rewrite(draft: str) -> str:
    """Return the LLM rewrite of the draft, or the draft itself when no LLM is configured."""
    if not available():
        return draft
    provider = os.environ["LLM_PROVIDER"].lower()
    if provider == "anthropic":
        import anthropic                                           # optional dependency
        client = anthropic.Anthropic(api_key=os.environ["LLM_API_KEY"])
        msg = client.messages.create(model=os.environ["LLM_MODEL"], max_tokens=2000,
                                     messages=[{"role": "user", "content": PROMPT + draft}])
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
