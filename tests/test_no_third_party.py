"""ADR-0009 (linkling-api): the public site carries no third-party asset, script
or embed. This reads site/*.html directly rather than a running container --
the Dockerfile copies site/ into nginx verbatim with no templating (ADR-0008),
so the files on disk are byte-for-byte what gets served.
"""
import re
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent / "site"

ABSOLUTE_ASSET_URL = re.compile(
    r"""(?:href|src)\s*=\s*["']https?://[^"']+["']""", re.IGNORECASE
)
SCRIPT_TAG = re.compile(r"<script\b", re.IGNORECASE)


def test_no_third_party_reference_in_served_html():
    files = sorted(SITE_DIR.glob("*.html"))
    assert files, f"blind: no HTML files found in {SITE_DIR} -- nothing was checked"

    violations = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for match in ABSOLUTE_ASSET_URL.finditer(text):
            violations.append(f"{path.name}: absolute asset URL {match.group(0)!r}")
        if SCRIPT_TAG.search(text):
            violations.append(f"{path.name}: loads a <script>")

    assert not violations, "third-party reference(s) found:\n" + "\n".join(violations)
