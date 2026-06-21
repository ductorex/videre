"""Audit the bundled fonts against their upstream sources.

Network-heavy and meant to be run deliberately (never in CI). For every bundled
font it downloads the current upstream file and compares the binary (SHA-256),
the OpenType version string, the ``cmap`` codepoints, the ``cmap`` format-14
variation sequences and the GSUB/GPOS script tags. A binary that differs but
keeps the same version, coverage and scripts is reported as *equivalent* (e.g.
an upstream variable font replacing a bundled static), not as an update.

It also queries the Noto hub for families published upstream but not bundled
yet, and measures what each would add: codepoints currently *missing* that it
would cover, plus codepoints it would *shape better* (today routed to a fallback
font that lacks the script's GSUB/GPOS).

The result is written to ``FONT_UPDATE_AUDIT.md`` next to this module. Only the
factual tables are generated; any editorial commentary is a manual addition.

Downloads are cached under ``<repo>/.run/.fonts/`` (gitignored) so re-runs are
fast; delete that folder to force a fresh fetch.

Usage::

    python -m videre.fonts._audit_fonts            # full audit (network)
    python -m videre.fonts._audit_fonts --catalog  # offline: print the catalog
"""

import datetime
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from fontTools.ttLib import TTFont

from videre.core.textual.coverage import (
    open_type_script_tags,
    requires_standalone_glyph,
)
from videre.core.textual.unicode_char import get_character
from videre.fonts.provider import FOLDER_FONT, FontProvider, get_font_provider

_REPO_ROOT = os.path.abspath(os.path.join(FOLDER_FONT, os.pardir, os.pardir))
_CACHE_DIR = os.path.join(_REPO_ROOT, ".run", ".fonts")
_AUDIT_PATH = os.path.join(FOLDER_FONT, "FONT_UPDATE_AUDIT.md")
_COVERAGE_REPORT_PATH = os.path.join(FOLDER_FONT, "cov", "_coverage-report.json")

_HUB_RAW = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/main"
_HUB_API = "https://api.github.com/repos/notofonts/notofonts.github.io/contents/fonts"
_CJK_RAW = "https://raw.githubusercontent.com/notofonts/noto-cjk/main"
_PLANGOTHIC_TAG = "V2.9.5792"

# Families published on the hub but never bundled on purpose (aggregated /
# color / variable-only variants that the per-script statics already cover).
_DISCOVERY_IGNORE = frozenset(
    {"NotoColorEmoji", "NotoSansCJK", "NotoSerifCJK", "NotoSansMonoCJK"}
)


def _hub_url(family: str) -> str:
    return f"{_HUB_RAW}/fonts/{family}/unhinted/ttf/{family}-Regular.ttf"


@dataclass(slots=True, frozen=True)
class LocalFont:
    rel_path: str  # POSIX, relative to FOLDER_FONT
    abs_path: str
    source: str  # human label of the upstream source
    url: str
    family: str | None  # hub family name when applicable


def _classify(rel: str, abs_path: str) -> LocalFont | None:
    """Map a local font file to its upstream URL, or None if unknown."""
    name = rel.rsplit("/", 1)[-1]

    def font(source: str, url: str, family: str | None = None) -> LocalFont:
        return LocalFont(rel, abs_path, source, url, family)

    if rel.startswith("noto/sans/unhinted/TTF/"):
        if name == "NotoEmoji-Regular.ttf":
            return font(
                "google/fonts (monochrome emoji)",
                "https://raw.githubusercontent.com/google/fonts/main/ofl/"
                "notoemoji/NotoEmoji%5Bwght%5D.ttf",
            )
        family = name.removesuffix("-Regular.ttf")
        return font("notofonts.github.io", _hub_url(family), family)
    if rel.startswith(("noto/serif/unhinted/TTF/", "noto/mono/unhinted/TTF/")):
        family = name.removesuffix("-Regular.ttf")
        return font("notofonts.github.io", _hub_url(family), family)
    if rel.startswith("noto/cjk/variable-fonts/"):
        region = name.removeprefix("NotoSans").removesuffix("-VF.ttf")
        return font(
            "notofonts/noto-cjk (Variable)",
            f"{_CJK_RAW}/Sans/Variable/TTF/Subset/NotoSans{region}-VF.ttf",
        )
    if rel.startswith(("noto/cjk/light/", "noto/cjk/regular/")):
        stem = name.removeprefix("NotoSans").removesuffix(".otf")  # e.g. "HK-Light"
        region, _, weight = stem.partition("-")
        return font(
            "notofonts/noto-cjk (SubsetOTF)",
            f"{_CJK_RAW}/Sans/SubsetOTF/{region}/NotoSans{region}-{weight}.otf",
        )
    if rel == "other-ttf/BabelStoneHan.ttf":
        return font(
            "babelstone.co.uk",
            "https://www.babelstone.co.uk/Fonts/Download/BabelStoneHan.ttf",
        )
    if rel.startswith("plangothic/") and name.endswith(".ttf"):
        return font(
            "Plangothic_Project (release)",
            "https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project"
            f"/releases/download/{_PLANGOTHIC_TAG}/{name}",
        )
    if rel == "newgardiner/NewGardiner.ttf":
        return font(
            "nederhof/newgardiner",
            "https://raw.githubusercontent.com/nederhof/newgardiner/master/"
            "fonts/NewGardiner.ttf",
        )
    return None


def catalog() -> tuple[list[LocalFont], list[str]]:
    """Return the mapped local fonts and the relative paths left unmapped."""
    mapped: list[LocalFont] = []
    unmapped: list[str] = []
    for root, _dirs, files in os.walk(FOLDER_FONT):
        for fname in files:
            if not fname.endswith((".ttf", ".otf")):
                continue
            abs_path = os.path.join(root, fname)
            rel = os.path.relpath(abs_path, FOLDER_FONT).replace(os.sep, "/")
            entry = _classify(rel, abs_path)
            if entry is None:
                unmapped.append(rel)
            else:
                mapped.append(entry)
    mapped.sort(key=lambda f: f.rel_path)
    return mapped, sorted(unmapped)


@dataclass(slots=True, frozen=True)
class FontMeta:
    version: str
    codepoints: frozenset[int]
    variations: frozenset[str]
    gsub: frozenset[str]
    gpos: frozenset[str]


def _scripts(font: TTFont, table_name: str) -> frozenset[str]:
    if table_name not in font:
        return frozenset()
    script_list = font[table_name].table.ScriptList  # ty: ignore[unresolved-attribute]
    if script_list is None:
        return frozenset()
    return frozenset(record.ScriptTag for record in script_list.ScriptRecord)


def read_meta(data: bytes) -> FontMeta:
    with TTFont(io.BytesIO(data), fontNumber=0, lazy=True) as font:
        version = font["name"].getDebugName(5) or ""
        cmap = font.getBestCmap() or {}
        variations = frozenset(
            chr(base) + chr(selector)
            for table in font["cmap"].tables
            if table.format == 14
            for selector, entries in table.uvsDict.items()
            for base, _glyph in entries
        )
        gsub, gpos = _scripts(font, "GSUB"), _scripts(font, "GPOS")
    return FontMeta(version, frozenset(cmap.keys()), variations, gsub, gpos)


def read_meta_path(path: str) -> FontMeta:
    with open(path, "rb") as handle:
        return read_meta(handle.read())


def _cache_path(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return os.path.join(_CACHE_DIR, f"{digest}_{url.rsplit('/', 1)[-1]}")


def fetch(url: str) -> bytes | None:
    """Download ``url`` (cached on disk). None if upstream is unreachable."""
    cached = _cache_path(url)
    if os.path.isfile(cached):
        with open(cached, "rb") as handle:
            return handle.read()
    request = urllib.request.Request(url, headers={"User-Agent": "videre-audit"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
    except (urllib.error.URLError, TimeoutError):
        return None
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(cached, "wb") as handle:
        handle.write(data)
    return data


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def missing_codepoints() -> set[int]:
    with open(_COVERAGE_REPORT_PATH, encoding="utf-8") as handle:
        report = json.load(handle)
    return {int(codepoint, 16) for codepoint in report["codepoints"]["missing"]}


@dataclass(slots=True, frozen=True)
class Comparison:
    local: LocalFont
    local_meta: FontMeta
    upstream_meta: FontMeta | None  # None if unreachable
    identical: bool  # same SHA-256

    @property
    def equivalent(self) -> bool:
        """Same bytes, or different bytes but same version/coverage/scripts.

        An upstream variable font shipped in place of a bundled static binary
        differs in SHA-256 yet carries the same glyph coverage; that is not an
        actionable update.
        """
        up = self.upstream_meta
        if up is None:
            return False
        return self.identical or (
            up.version == self.local_meta.version
            and up.codepoints == self.local_meta.codepoints
            and up.variations == self.local_meta.variations
            and up.gsub == self.local_meta.gsub
            and up.gpos == self.local_meta.gpos
        )


def _compare_one(entry: LocalFont) -> Comparison:
    local_meta = read_meta_path(entry.abs_path)
    with open(entry.abs_path, "rb") as handle:
        local_bytes = handle.read()
    upstream = fetch(entry.url)
    if upstream is None:
        return Comparison(entry, local_meta, None, False)
    identical = _sha256(local_bytes) == _sha256(upstream)
    upstream_meta = local_meta if identical else read_meta(upstream)
    return Comparison(entry, local_meta, upstream_meta, identical)


def compare_all(entries: list[LocalFont]) -> list[Comparison]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(_compare_one, entries))


@dataclass(slots=True, frozen=True)
class NewFamily:
    family: str
    coverage_gain: int  # currently-missing codepoints it would cover
    layout_gain: int  # covered codepoints today routed to a font lacking the
    # script's GSUB/GPOS, that this family would shape
    blocks: list[tuple[str, int]]
    scripts: frozenset[str]

    @property
    def total(self) -> int:
        return self.coverage_gain + self.layout_gain


def discover_new_families(local_families: set[str]) -> list[str]:
    request = urllib.request.Request(_HUB_API, headers={"User-Agent": "videre-audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        listing = json.load(response)
    hub = {
        item["name"]
        for item in listing
        if item.get("type") == "dir" and item["name"].startswith("Noto")
    }
    new = hub - local_families - _DISCOVERY_IGNORE
    return sorted(new)


def measure_new_family(
    family: str, missing: set[int], provider: FontProvider
) -> NewFamily | None:
    data = fetch(_hub_url(family))
    if data is None:
        return None
    meta = read_meta(data)
    new_scripts = meta.gsub | meta.gpos
    coverage: list[int] = []
    layout: list[int] = []
    for codepoint in meta.codepoints:
        character = chr(codepoint)
        if not requires_standalone_glyph(character):
            continue
        if codepoint in missing:
            coverage.append(codepoint)
            continue
        script_tags = open_type_script_tags(character)
        if not script_tags or not (new_scripts & script_tags):
            continue
        current_name, _ = provider.get_font_info(character)
        current = provider._capabilities.get(current_name)
        if current is not None and not current.layout_support(script_tags):
            layout.append(codepoint)
    blocks = Counter(get_character(chr(cp)).block for cp in coverage + layout)
    return NewFamily(
        family, len(coverage), len(layout), blocks.most_common(), new_scripts
    )


def _scripts_label(meta: FontMeta) -> str:
    tags = sorted(meta.gsub | meta.gpos)
    return ", ".join(tags) if tags else "—"


def _coverage_delta(comparison: Comparison) -> str:
    upstream = comparison.upstream_meta
    if upstream is None:
        return "—"
    added = len(upstream.codepoints - comparison.local_meta.codepoints)
    removed = len(comparison.local_meta.codepoints - upstream.codepoints)
    return f"+{added} / -{removed}"


def _status(comparison: Comparison) -> str:
    if comparison.upstream_meta is None:
        return "Inaccessible upstream"
    if comparison.identical:
        return "À jour, binaire identique"
    if comparison.equivalent:
        return "À jour (variante upstream, couverture identique)"
    return "Mise à jour disponible"


def render_markdown(comparisons: list[Comparison], new: list[NewFamily]) -> str:
    today = datetime.date.today().isoformat()
    reachable = [c for c in comparisons if c.upstream_meta is not None]
    identical = [c for c in reachable if c.identical]
    equivalent = [c for c in reachable if c.equivalent and not c.identical]
    updates = [c for c in reachable if not c.equivalent]
    unreachable = [c for c in comparisons if c.upstream_meta is None]
    useful = sorted((f for f in new if f.total > 0), key=lambda f: (-f.total, f.family))
    stylistic = sorted(f.family for f in new if f.total == 0)

    lines: list[str] = []
    add = lines.append
    add("# Audit des mises à jour de polices")
    add("")
    add(f"Date de vérification : **{today}**.")
    add("")
    add(
        "Généré automatiquement par `python -m videre.fonts._audit_fonts`. Seules "
        "les tables factuelles ci-dessous sont produites par le script ; toute "
        "analyse éditoriale (recommandations, arbitrages) est un ajout manuel."
    )
    add("")
    add(
        "Chaque fichier local est comparé à son fichier upstream actuel : SHA-256 "
        "du binaire, version OpenType, codepoints `cmap`, séquences `cmap 14` et "
        "scripts GSUB/GPOS. Un binaire différent mais de même version, couverture "
        "et scripts est dit *équivalent* (p.ex. une variable font upstream à la "
        "place d'une statique embarquée), pas une mise à jour. Les familles Noto "
        "publiées sur le hub mais non embarquées sont aussi listées, avec ce "
        "qu'elles apporteraient."
    )
    add("")
    add("## Résumé")
    add("")
    add(f"- Fichiers strictement identiques au binaire upstream : {len(identical)}.")
    if equivalent:
        add(
            "- Fichiers équivalents (binaire différent, même version, couverture et "
            f"scripts) : {len(equivalent)}."
        )
    add(f"- Mises à jour réelles disponibles : {len(updates)}.")
    if unreachable:
        add(f"- Fichiers inaccessibles upstream : {len(unreachable)}.")
    add(
        f"- Familles Noto supplémentaires sur le hub : {len(new)} (dont {len(useful)} "
        "à gain de couverture ou de layout)."
    )
    add("")

    add("## Mises à jour disponibles")
    add("")
    if updates:
        add(
            "| Fichier | Version locale | Version upstream | Couverture brute (+/-) "
            "| Layout upstream |"
        )
        add("|---|---:|---:|---:|---|")
        for c in sorted(updates, key=lambda c: c.local.rel_path):
            up = c.upstream_meta
            assert up is not None
            add(
                f"| `{c.local.rel_path}` | {c.local_meta.version or '—'} | "
                f"{up.version or '—'} | {_coverage_delta(c)} | {_scripts_label(up)} |"
            )
    else:
        add("Aucune : tous les fichiers joignables sont à jour ou équivalents.")
    add("")

    add("## Nouvelles familles Noto disponibles")
    add("")
    add(
        "*Couverture* = codepoints aujourd'hui manquants que la famille couvrirait. "
        "*Layout* = codepoints aujourd'hui rendus par une police de repli sans le "
        "GSUB/GPOS du script, que cette famille shaperait correctement."
    )
    add("")
    if useful:
        add("| Famille | Couverture | Layout | Blocs principaux | GSUB/GPOS |")
        add("|---|---:|---:|---|---|")
        for fam in useful:
            blocks = (
                ", ".join(f"{name} ({count})" for name, count in fam.blocks[:3]) or "—"
            )
            tags = ", ".join(sorted(fam.scripts)) or "—"
            add(
                f"| {fam.family} | {fam.coverage_gain} | {fam.layout_gain} | "
                f"{blocks} | {tags} |"
            )
    else:
        add("Aucune famille candidate n'apporte de couverture ni de layout.")
    add("")
    if stylistic:
        add(
            f"{len(stylistic)} autres familles sont disponibles sans gain de "
            "couverture ni de layout (variantes purement stylistiques — serif, UI, "
            "display, etc.) : " + ", ".join(stylistic) + "."
        )
        add("")

    add(f"## Statut des {len(comparisons)} fichiers")
    add("")
    add("| Fichier | Version locale | Version upstream | Statut |")
    add("|---|---:|---:|---|")
    for c in comparisons:
        up = c.upstream_meta
        up_version = "—" if up is None else (up.version or "—")
        add(
            f"| `{c.local.rel_path}` | {c.local_meta.version or '—'} | "
            f"{up_version} | {_status(c)} |"
        )
    add("")

    add("## Sources officielles consultées")
    add("")
    for url in (
        "https://github.com/notofonts/notofonts.github.io",
        "https://github.com/notofonts/noto-cjk",
        "https://github.com/google/fonts/tree/main/ofl/notoemoji",
        "https://www.babelstone.co.uk/Fonts/Han.html",
        "https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project",
        "https://github.com/nederhof/newgardiner",
    ):
        add(f"- <{url}>")
    add("")
    return "\n".join(lines)


def _print_catalog() -> None:
    mapped, unmapped = catalog()
    for entry in mapped:
        meta = read_meta_path(entry.abs_path)
        print(f"{entry.rel_path}\n    -> {entry.url}\n    version: {meta.version}")
    print(f"\n{len(mapped)} fonts mapped, {len(unmapped)} unmapped.")
    for rel in unmapped:
        print(f"    UNMAPPED: {rel}")


def main() -> None:
    if "--catalog" in sys.argv[1:]:
        _print_catalog()
        return

    mapped, unmapped = catalog()
    for rel in unmapped:
        print(f"WARNING: unmapped local font (no upstream URL): {rel}")

    print(f"Comparing {len(mapped)} local fonts to upstream...")
    comparisons = compare_all(mapped)

    local_families = {f.family for f in mapped if f.family is not None}
    print("Discovering new Noto families on the hub...")
    new_names = discover_new_families(local_families)
    missing = missing_codepoints()
    provider = get_font_provider()
    print(
        f"Measuring {len(new_names)} candidate families against {len(missing)} gaps..."
    )
    with ThreadPoolExecutor(max_workers=8) as pool:
        measured = pool.map(
            lambda fam: measure_new_family(fam, missing, provider), new_names
        )
    new_families = [item for item in measured if item is not None]

    markdown = render_markdown(comparisons, new_families)
    with open(_AUDIT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown)
    print(f"Wrote {_AUDIT_PATH}")


if __name__ == "__main__":
    main()
