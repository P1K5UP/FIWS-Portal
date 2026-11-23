import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (ROOT / "src/index.template.html", ROOT / "index.html")


def extract_css(source: str, path: Path) -> str:
    blocks = re.findall(r"<style\b[^>]*>(.*?)</style>", source, flags=re.I | re.S)
    if len(blocks) != 1:
        raise AssertionError(f"{path}: expected exactly one style block, found {len(blocks)}")
    return blocks[0]


def brace_balance(css: str) -> int:
    """Count CSS structural braces, ignoring comments and quoted strings."""
    depth = 0
    quote = None
    escaped = False
    comment = False
    i = 0
    while i < len(css):
        char = css[i]
        nxt = css[i + 1] if i + 1 < len(css) else ""
        if comment:
            if char == "*" and nxt == "/":
                comment = False
                i += 2
                continue
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and nxt == "*":
            comment = True
            i += 2
            continue
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise AssertionError("CSS contains a closing brace without a matching opening brace")
        i += 1
    if quote:
        raise AssertionError("CSS contains an unterminated quoted string")
    if comment:
        raise AssertionError("CSS contains an unterminated comment")
    return depth


class FrontendCssIntegrityTests(unittest.TestCase):
    def test_stylesheets_have_balanced_rules(self):
        for path in SOURCES:
            with self.subTest(path=path.name):
                css = extract_css(path.read_text(encoding="utf-8"), path)
                self.assertEqual(brace_balance(css), 0, f"{path}: unbalanced CSS braces")

    def test_leaderboard_row_rule_is_closed_before_position_rule(self):
        for path in SOURCES:
            with self.subTest(path=path.name):
                css = extract_css(path.read_text(encoding="utf-8"), path)
                match = re.search(r"\.tr\s*\{([^{}]*)\}\s*\.pos\s*\{", css)
                self.assertIsNotNone(match, f"{path}: .tr rule must close before .pos")
                self.assertIn("transition:", match.group(1))
                self.assertIn("transform", match.group(1))


if __name__ == "__main__":
    unittest.main()
