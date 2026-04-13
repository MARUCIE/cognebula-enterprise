#!/usr/bin/env python3
"""Content quality validator — detect HTML junk, nav garbage, boilerplate.

Used by:
  - audit_content_quality.py (bulk audit)
  - kg_quality_gate.py (D6 Authenticity dimension)
  - chinatax_fulltext_backfill.py (pre-write validation)
  - content_health_monitor.py (hourly checks)
"""
import re
import unicodedata


# Navigation/boilerplate patterns (Chinese government sites)
NAV_KEYWORDS = [
    "首页", "网站地图", "English", "关于我们", "联系我们",
    "通知公告", "政策法规", "信息公开", "互动交流", "专题专栏",
    "纳税服务", "新闻发布", "搜索", "登录", "注册",
    "本站热词", "总局概况", "政务公开", "在线办事",
    "无障碍", "适老化", "简", "繁",
]

BOILERPLATE_PATTERNS = [
    r"版权所有",
    r"ICP备\d+号",
    r"技术支持",
    r"建议使用.*浏览器",
    r"主办[：:]",
    r"地址[：:].*邮编",
    r"电话[：:].*传真",
    r"网站标识码",
    r"京公网安备",
    r"©\s*\d{4}",
    r"All Rights Reserved",
]

# LLM output markers (for authoritative content policy enforcement)
LLM_OUTPUT_MARKERS = [
    "核心要点：", "适用范围：", "实务影响：", "注意事项：",
    "概念定义：", "关键要点：", "以下是", "总结如下",
    "**概念定义", "**关键要点", "**适用场景", "**注意事项",
]


def _cjk_ratio(text: str) -> float:
    """Ratio of CJK characters to total printable characters."""
    if not text:
        return 0.0
    printable = sum(1 for c in text if not c.isspace())
    if printable == 0:
        return 0.0
    cjk = sum(1 for c in text
              if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
    return cjk / printable


def _nav_density(text: str, window: int = 500) -> float:
    """Count navigation keywords in first N chars."""
    head = text[:window]
    count = sum(1 for kw in NAV_KEYWORDS if kw in head)
    return count


def _boilerplate_density(text: str) -> int:
    """Count boilerplate pattern matches."""
    return sum(1 for pat in BOILERPLATE_PATTERNS if re.search(pat, text))


def _html_entity_ratio(text: str) -> float:
    """Ratio of HTML entities to text length."""
    if not text:
        return 0.0
    entities = len(re.findall(r'&(?:gt|lt|amp|nbsp|quot|#\d+);', text))
    return entities / len(text)


def _has_llm_markers(text: str) -> bool:
    """Check if text has LLM output patterns."""
    return any(marker in text for marker in LLM_OUTPUT_MARKERS)


def is_junk(text: str) -> tuple[bool, str]:
    """Determine if text content is junk (nav garbage, boilerplate, etc).

    Returns (is_junk: bool, reason: str).
    """
    if not text or len(text.strip()) < 10:
        return True, "empty_or_too_short"

    text = text.strip()

    # Check navigation keyword density in first 500 chars
    nav_count = _nav_density(text)
    if nav_count >= 5:
        return True, f"nav_keywords({nav_count})"

    # Check if starts with common nav patterns
    head = text[:100]
    if any(head.startswith(p) for p in ["简\n繁", "首页\n", "首页 ", "网站地图"]):
        return True, "starts_with_nav"

    # Check boilerplate density
    bp_count = _boilerplate_density(text)
    if bp_count >= 3:
        return True, f"boilerplate({bp_count})"

    # Check CJK ratio (legal/tax content should be mostly Chinese)
    cjk = _cjk_ratio(text)
    if len(text) > 100 and cjk < 0.2:
        return True, f"low_cjk_ratio({cjk:.2f})"

    # Check HTML entity leakage
    entity_ratio = _html_entity_ratio(text)
    if entity_ratio > 0.03:
        return True, f"html_entities({entity_ratio:.3f})"

    # Check for pipe-separated menu items (nav menu capture)
    pipe_segments = text[:500].count("|")
    if pipe_segments > 8:
        short_segments = sum(1 for s in text[:500].split("|")
                           if 0 < len(s.strip()) < 8)
        if short_segments > 6:
            return True, f"pipe_menu({pipe_segments})"

    # Check for JSON object in fullText (legacy ingestion artifact)
    if text.startswith("{") and "title" in text[:50]:
        return True, "json_object_in_text"

    return False, "ok"


def is_llm_generated(text: str) -> tuple[bool, str]:
    """Check if content appears to be LLM-generated (for authoritative policy)."""
    if not text:
        return False, "empty"
    if _has_llm_markers(text):
        return True, "llm_output_markers"
    # Check for bullet-point heavy structure (LLM pattern)
    lines = text.split("\n")
    bullet_lines = sum(1 for l in lines if l.strip().startswith(("- ", "* ", "• ", "1.", "2.", "3.")))
    if len(lines) > 5 and bullet_lines / len(lines) > 0.5:
        return True, "high_bullet_ratio"
    return False, "ok"


def content_quality_score(text: str) -> dict:
    """Comprehensive content quality assessment."""
    if not text:
        return {"score": 0, "is_junk": True, "reason": "empty",
                "cjk_ratio": 0, "effective_length": 0}

    junk, reason = is_junk(text)
    cjk = _cjk_ratio(text)
    llm, llm_reason = is_llm_generated(text)

    # Effective length = actual content after stripping junk
    effective_length = len(text.strip()) if not junk else 0

    # Score: 0-100
    score = 0
    if not junk:
        # Length component (0-40)
        if effective_length >= 500:
            score += 40
        elif effective_length >= 200:
            score += 30
        elif effective_length >= 50:
            score += 20
        else:
            score += 10

        # CJK quality (0-30)
        score += min(30, int(cjk * 40))

        # Not LLM generated bonus (0-20)
        if not llm:
            score += 20

        # Structural quality (0-10)
        if "\n" in text and len(text.split("\n")) > 3:
            score += 10

    return {
        "score": score,
        "is_junk": junk,
        "reason": reason,
        "is_llm": llm,
        "llm_reason": llm_reason if llm else "",
        "cjk_ratio": round(cjk, 3),
        "effective_length": effective_length,
        "nav_density": _nav_density(text),
        "boilerplate_count": _boilerplate_density(text),
    }


if __name__ == "__main__":
    # Self-test with known patterns
    tests = [
        ("简\n繁\nEN\n本站热词：\n发票\n小微企业\n首页\n总局概况", True, "nav"),
        ("中华人民共和国增值税法第一条 为了规范增值税的征收和缴纳", False, "real"),
        ('{"title": "关于发行印花税票的通告", "summary": "本通告"}', True, "json"),
        ("", True, "empty"),
        ("版权所有 © 2024 ICP备12345号 技术支持：某公司 京公网安备", True, "boilerplate"),
        ("核心要点：增值税是以商品流转中的增值额为计税依据的一种流转税", False, "llm"),
    ]
    for text, expected_junk, label in tests:
        result, reason = is_junk(text)
        status = "PASS" if result == expected_junk else "FAIL"
        print(f"  [{status}] {label}: junk={result} reason={reason}")

        if label == "llm":
            llm_result, llm_reason = is_llm_generated(text)
            print(f"         LLM: {llm_result} ({llm_reason})")
