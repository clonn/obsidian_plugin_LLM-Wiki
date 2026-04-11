"""Classification rules for the reorganize script.

Each rule is (category, patterns). Patterns match the lowercased concatenation
of filename + first ~500 bytes of file content. First matching rule wins.

Categories map to subfolders under `notes/` inside the vault, EXCEPT for the
special categories:
- `__archive__` → move to `_archive/misc/`
- `__delete__`  → remove (tiny / empty / pure junk)

The destination folder layout (under vault root):

    notes/
      cymkube/        — Cymkube / cympotek / acrylic manufacturing
      openclaw/       — OpenClaw lobster / agent product
      sowork/         — sowork HR OS
      ai-tooling/     — Claude, prompts, LLM tooling, general AI howtos
      business/       — business strategy, company ops, value prop
      finance/        — trading, stocks, payments, accounting
      people-meetings/— people notes, meeting minutes
      blog-drafts/    — explicit blog drafts
      infra/          — secrets, credentials, server config
      misc/           — everything else that's still worth keeping

The `notes/` zone sits alongside `raw/` and `wiki/`:
- `raw/` — externally ingested sources
- `notes/` — user-authored working notes (legacy + new)
- `wiki/` — LLM-compiled concept articles (auto-generated)
- `_archive/` — frozen legacy content, candidate for deletion
"""

from __future__ import annotations

RULES: list[tuple[str, list[str]]] = [
    # Project-specific buckets first (most specific).
    # OpenClaw runs before Cymkube because the lobster story ('養蝦') is
    # more specific than the general manufacturing cymkube bucket.
    (
        "openclaw",
        [
            "openclaw",
            "龍蝦現象",
            "養蝦",
            "龍蝦",
        ],
    ),
    (
        "cymkube",
        [
            "cymkube",
            "cympotek",
            "cympack",
            "壓克力客製化",
            "3d 客製化列印",
            "3d客製化列印",
            "正美零售",
            "value proposition",
            "價值主張",
            "軟包整體規劃",
            "dx team",
        ],
    ),
    (
        "sowork",
        [
            "sowork",
            "共生型企業",
            "傳討企業",
            "功能模組完整介紹",
        ],
    ),
    # Cross-cutting AI / tooling.
    (
        "ai-tooling",
        [
            "claude code",
            "claude skill",
            "claude.ai",
            "沙箱技術",
            "chandra ocr",
            "agent flow",
            "ai partner",
            "mbti template",
            "nanobanana",
            "notebooklm",
            "notebook lm",
            "bloom",
            "prompt.md",
            "prompt ",
            "ai 簡報",
            "ai 加速人力",
            "生成式引擎",
            "geo",
            "slide_inpaiting",
            "inpainting",
            "slide inpaiting",
        ],
    ),
    # Business / strategy / company ops.
    (
        "business",
        [
            "1人公司",
            "戶政事務所",
            "許願",
        ],
    ),
    # Finance / money / markets.
    (
        "finance",
        [
            "stock analytics",
            "stock analy",
            "永豐",
            "藍新",
            "交易資料",
        ],
    ),
    # People / meetings / contacts.
    (
        "people-meetings",
        [
            "何大",
            "月會",
        ],
    ),
    # Blog drafts.
    (
        "blog-drafts",
        [
            "blog - ",
            "blog -",
            "blog-",
        ],
    ),
    # Infra / secrets / credentials.
    (
        "infra",
        [
            "api key",
            "azure vm",
            "azure vm server",
        ],
    ),
]

# Destination folder for unmatched files
DEFAULT_CATEGORY = "misc"

# Files whose base name matches any of these get dropped instead of moved.
# Reserved for obvious junk. Tiny/empty detection is separate from this list.
DELETE_EXACT = {
    "未命名.base",
    "未命名.canvas",
    "Untitled.md",
}
