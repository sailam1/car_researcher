from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str, **kwargs: str) -> str:
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    text = path.read_text(encoding="utf-8")
    for key, value in kwargs.items():
        text = text.replace("{" + key + "}", value)
    return text
