"""Profil interne du rendu "shaped" : ou passe le temps de l'etape couteuse ?

    PYTHONUTF8=1 uv run python tools/profile_shaping.py

bench_text.py a montre que ~80 % du cout du shaped est l'etape "shape"
(document(), independante de la largeur, mise en cache) et ~20 % le "paint".
Ce script decompose ces 80 % :

    document() = partition_text          +  shape_line(...)
                 (segmentation + bidi +      (HarfBuzz : production des glyphes
                  decoupage en mots +         + bornes d'encre FreeType)
                  routage police)

  1. PARTITION vs SHAPE  -- la coupe principale des 80 %.
  2. DANS LA PARTITION   -- poids des grands algos (edit units, bidi, mots,
                            mesures isolement) + part reelle du font provider
                            (partition normale moins partition a provider neutralise).
  3. FONT PROVIDER       -- cout par appel de get_font_info (lookup direct) et
                            get_font_info_for_cluster (avec fallback eventuel).

Mediane sur plusieurs appels, en microsecondes (us). Aucune fenetre / backend :
on mesure le pipeline pur (HarfBuzz + FreeType), pas le dessin.
"""

import statistics
import time

from videre.core.shaping.shaper import Shaper, shape_line
from videre.core.shaping.text_partition.partitioner import partition_text
from videre.core.shaping.text_partition.word_splitter import split_word_spans
from videre.core.text_editing import segment_edit_units
from videre.core.vibidi.vibidi import vibidi
from videre.fonts.provider import FONT_NOTO_REGULAR, FontProvider, get_font_provider
from videre.testing.utils import LOREM_IPSUM, TEXT_SAMPLES

SIZE = 16


def samples() -> dict[str, str]:
    """Memes echantillons que bench_text.py (etiquettes ASCII)."""
    lorem = LOREM_IPSUM.split("\n\n")[0].strip()
    return {
        "latin court": "Open file",
        "latin phrase": "The quick brown fox jumps over the lazy dog.",
        "latin paragraphe": lorem,
        "arabe": TEXT_SAMPLES["arabic"].splitlines()[0],
        "hebreu": TEXT_SAMPLES["hebrew"].splitlines()[0],
        "devanagari": TEXT_SAMPLES["devanagari"],
        "thai": TEXT_SAMPLES["thai"],
        "bidi mixte": "Hello مرحبا World العالم 123 שלום test",
        "cjk japonais": TEXT_SAMPLES["japanese"].replace("\n", " ")[:60],
        "emoji + ZWJ": TEXT_SAMPLES["emoji"],
        "ligatures": TEXT_SAMPLES["latin_ligatures"],
        "hieroglyphes": TEXT_SAMPLES["egyptian_hieroglyphs"].splitlines()[0],
    }


def _median_us(call, iters: int) -> float:
    durations = []
    for _ in range(iters):
        t0 = time.perf_counter_ns()
        call()
        durations.append(time.perf_counter_ns() - t0)
    return statistics.median(durations) / 1000.0


def measure(call, target_s: float = 0.2, lo: int = 5, hi: int = 5000) -> float:
    """Auto-cadence : chauffe, estime, choisit le nombre d'iterations pour
    ~target_s, renvoie la mediane (us). Pour les operations a l'echelle us-ms."""
    for _ in range(3):
        call()
    t0 = time.perf_counter_ns()
    call()
    one_s = max((time.perf_counter_ns() - t0) / 1e9, 1e-9)
    iters = min(hi, max(lo, int(target_s / one_s)))
    return _median_us(call, iters)


def measure_micro(call, batch: int = 2000, rounds: int = 11) -> float:
    """Pour les operations sub-us (provider) : on chronometre des paquets de
    `batch` appels et on divise, sinon la resolution de l'horloge domine."""
    for _ in range(batch):
        call()
    per_call = []
    for _ in range(rounds):
        t0 = time.perf_counter_ns()
        for _ in range(batch):
            call()
        per_call.append((time.perf_counter_ns() - t0) / batch)
    return statistics.median(per_call) / 1000.0


def _count_provider_calls(text: str) -> tuple[int, int]:
    """Nombre d'appels a get_font_info / get_font_info_for_cluster pendant UNE
    partition (en enveloppant temporairement les methodes de classe)."""
    info = [0]
    cluster = [0]
    orig_info = FontProvider.get_font_info
    orig_cluster = FontProvider.get_font_info_for_cluster

    def wrap_info(self, c, _orig=orig_info):
        info[0] += 1
        return _orig(self, c)

    def wrap_cluster(self, t, preferred_font_name=None, _orig=orig_cluster):
        cluster[0] += 1
        return _orig(self, t, preferred_font_name=preferred_font_name)

    FontProvider.get_font_info = wrap_info
    FontProvider.get_font_info_for_cluster = wrap_cluster
    try:
        partition_text(text)
    finally:
        FontProvider.get_font_info = orig_info
        FontProvider.get_font_info_for_cluster = orig_cluster
    return info[0], cluster[0]


def _measure_partition_neutralized(text: str) -> float:
    """Partition avec le provider neutralise (retourne une police fixe sans
    aucun calcul). partition_reelle - partition_neutralisee ~= part du provider."""
    name, path = FONT_NOTO_REGULAR.name, FONT_NOTO_REGULAR.path
    orig_info = FontProvider.get_font_info
    orig_cluster = FontProvider.get_font_info_for_cluster
    FontProvider.get_font_info = lambda self, c: (name, path)
    FontProvider.get_font_info_for_cluster = lambda self, t, preferred_font_name=None: (
        name,
        path,
    )
    try:
        return measure(lambda: partition_text(text))
    finally:
        FontProvider.get_font_info = orig_info
        FontProvider.get_font_info_for_cluster = orig_cluster


def section_partition_vs_shape(samp: dict[str, str], shaper: Shaper) -> None:
    print("1. PARTITION vs SHAPE  (la coupe principale des 80 % du shaped)\n")
    head = (
        f"{'texte':16} | {'partition':>10} {'shape':>10} {'total':>10} | "
        f"{'part%':>6} {'shape%':>6}"
    )
    print(head)
    print("-" * len(head))
    for name, text in samp.items():
        part = measure(lambda: partition_text(text))
        partition = partition_text(text)
        shape = measure(
            lambda: [shape_line(line, shaper, SIZE) for line in partition.lines]
        )
        total = part + shape
        print(
            f"{name:16} | {part:10.0f} {shape:10.0f} {total:10.0f} | "
            f"{part / total * 100:5.0f}% {shape / total * 100:5.0f}%"
        )


def section_inside_partition(samp: dict[str, str]) -> None:
    print("\n2a. DANS LA PARTITION  (grands algos, mesures isolement -- us)\n")
    head = f"{'texte':16} | {'edit_units':>10} {'bidi':>8} {'mots':>8}"
    print(head)
    print("-" * len(head))
    for name, text in samp.items():
        eu = measure(lambda: segment_edit_units(text))
        bd = measure(lambda: vibidi(text))
        wd = measure(lambda: split_word_spans(text))
        print(f"{name:16} | {eu:10.0f} {bd:8.0f} {wd:8.0f}")

    print("\n2b. PART DU FONT PROVIDER DANS LA PARTITION\n")
    head2 = (
        f"{'texte':16} | {'partition':>10} {'provider':>9} {'prov%':>6} | "
        f"{'appels info':>11} {'appels clus':>11}"
    )
    print(head2)
    print("-" * len(head2))
    for name, text in samp.items():
        full = measure(lambda: partition_text(text))
        neutral = _measure_partition_neutralized(text)
        prov = max(full - neutral, 0.0)
        n_info, n_cluster = _count_provider_calls(text)
        print(
            f"{name:16} | {full:10.0f} {prov:9.0f} {prov / full * 100:5.0f}% | "
            f"{n_info:11} {n_cluster:11}"
        )


def section_provider(provider: FontProvider) -> None:
    print("\n3a. FONT PROVIDER -- get_font_info(char)  (lookup direct, us/appel)\n")
    info_inputs = {
        "latin": "A",
        "arabe": "م",
        "cjk": "世",
        "devanagari": "ह",
        "thai": "ก",
        "emoji": "\U0001f44d",
    }
    for label, c in info_inputs.items():
        us = measure_micro(lambda: provider.get_font_info(c))
        print(f"  {label:14} {us:8.3f}")

    print(
        "\n3b. get_font_info_for_cluster(cluster)  (avec fallback eventuel, us/appel)\n"
    )
    cluster_inputs = {
        "latin 'e'": "e",
        "arabe": "م",
        "cjk": "世",
        "devanagari": "ह",
        "famille ZWJ": "\U0001f468‍\U0001f469‍\U0001f467‍\U0001f466",
        "drapeau FR": "\U0001f1eb\U0001f1f7",
        "teinte peau": "\U0001f44d\U0001f3fd",
    }
    for label, t in cluster_inputs.items():
        us = measure_micro(lambda: provider.get_font_info_for_cluster(t))
        print(f"  {label:14} {us:8.3f}")


def run() -> None:
    samp = samples()
    shaper = Shaper()
    provider = get_font_provider()
    section_partition_vs_shape(samp, shaper)
    section_inside_partition(samp)
    section_provider(provider)


if __name__ == "__main__":
    run()
