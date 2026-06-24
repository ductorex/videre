"""Benchmark du moteur de rendu de texte "shaped" (HarfBuzz).

Lancement (Windows : forcer l'UTF-8 de la console par securite) ::

    PYTHONUTF8=1 uv run python tools/bench_text.py

POURQUOI CES MESURES ?
----------------------
Un widget texte garde son image rendue en cache : tant que rien ne change, il
ne recalcule RIEN (un texte statique a donc un cout nul). Le rendu n'est paye
qu'a deux moments precis -- les deux seuls qu'on mesure ici :

  1. LE TEXTE CHANGE  (on tape une lettre, on affiche un nouveau contenu)
     Tout est refait : segmentation + shaping + bidi, puis mise en page + dessin.
     C'est le cout de reactivite a la frappe.

  2. LA LARGEUR CHANGE  (on redimensionne la fenetre, reflow)
     Le texte est identique, seule la largeur bouge. Le widget reutilise le
     "document" deja calcule : le shaping (l'etape couteuse) n'est PAS refait,
     juste la mise en page + le dessin.

Un 3e tableau decompose le cout en "shape" (l'analyse bidi+HarfBuzz, payee une
fois puis mise en cache) et "paint" (mise en page + dessin a une largeur).

Chaque nombre est la mediane sur plusieurs appels, en microsecondes (us), et
aussi en % d'une frame a 60 FPS (16 667 us). Au-dela de 100 %, un seul rendu
suffit a faire sauter une frame.
"""

import statistics
import time

from videre.colors import Color
from videre.core.text_rendering import TextRendering
from videre.testing.step_window import StepWindow
from videre.testing.utils import LOREM_IPSUM, TEXT_SAMPLES

SIZE = 16
WIDTH = 600  # largeur de reference pour le scenario "le texte change"
RESIZE_WIDTHS = [300, 350, 400, 450, 500, 550, 600, 650]  # un balayage de resize
FRAME_US = 1_000_000 / 60  # 16 667 us = une frame a 60 FPS
BLACK = Color(0, 0, 0)


def samples() -> dict[str, str]:
    """Etiquette (ASCII) -> texte, couvrant deux familles : latin simple, et
    scripts complexes / bidi / emoji (au text_rendering non trivial)."""
    lorem = LOREM_IPSUM.split("\n\n")[0].strip()
    return {
        # --- latin simple ---
        "latin court": "Open file",
        "latin phrase": "The quick brown fox jumps over the lazy dog.",
        "latin paragraphe": lorem,
        # --- scripts complexes / bidi / emoji ---
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


def _measure(call, target_s: float = 0.2, lo: int = 5, hi: int = 3000) -> float:
    """Chauffe les caches, estime le cout d'un appel, choisit un nombre
    d'iterations pour que la mesure dure ~target_s, puis renvoie la mediane (us).
    Les textes lourds tournent donc moins souvent, sans reglage manuel."""
    for _ in range(3):
        call()
    t0 = time.perf_counter_ns()
    call()
    one_call_s = max((time.perf_counter_ns() - t0) / 1e9, 1e-9)
    iters = min(hi, max(lo, int(target_s / one_call_s)))
    return _median_us(call, iters)


def _pct_frame(us: float) -> float:
    return us / FRAME_US * 100.0


def _row(name: str, us: float) -> str:
    return f"{name:16} | {us:10.0f} {_pct_frame(us):6.1f}"


def run() -> None:
    samp = samples()
    with StepWindow(width=900, height=600) as win:
        shaped = TextRendering(win.backend, size=SIZE)

        head = f"{'texte':16} | {'rendu us':>10} {'%fr':>6}"

        # 1. LE TEXTE CHANGE -- document reconstruit a chaque appel (le texte a
        # change), caches bas niveau chauds (regime permanent, ex. on tape).
        print("1. LE TEXTE CHANGE  (frappe / nouveau contenu)")
        print("   mediane par rendu -- us et % d'une frame 60 FPS\n")
        print(head)
        print("-" * len(head))
        for name, text in samp.items():
            sh = _measure(
                lambda: shaped.document(text).render(
                    WIDTH, color=BLACK, wrap_words=True
                )
            )
            print(_row(name, sh))

        # 2. LA LARGEUR CHANGE -- document construit UNE fois, puis rendu a
        # chaque largeur du balayage ; on ramene au cout d'UNE largeur.
        print("\n2. LA LARGEUR CHANGE  (resize -- document reutilise)")
        print("   mediane par rendu d'une largeur -- us et % de frame\n")
        print(head)
        print("-" * len(head))
        resize_paint = {}
        for name, text in samp.items():
            sdoc = shaped.document(text)
            n = len(RESIZE_WIDTHS)
            sh = (
                _measure(
                    lambda: [
                        sdoc.render(w, color=BLACK, wrap_words=True)
                        for w in RESIZE_WIDTHS
                    ]
                )
                / n
            )
            resize_paint[name] = sh
            print(_row(name, sh))

        # 3. DECOMPOSITION -- shape = document(text) seul (analyse bidi+HarfBuzz) ;
        # paint = rendu d'une largeur (mesure en 2.).
        print(
            "\n3. DECOMPOSITION  (shape = analyse bidi+HarfBuzz, paint = mise en page + dessin)"
        )
        print(
            "   shape est paye 1x puis mis en cache ; au resize, seul paint est refait\n"
        )
        head3 = f"{'texte':16} | {'shape us':>9} {'paint us':>9} {'total us':>9} | {'shape%':>6}"
        print(head3)
        print("-" * len(head3))
        for name, text in samp.items():
            shape = _measure(lambda: shaped.document(text))
            paint = resize_paint[name]
            total = shape + paint
            print(
                f"{name:16} | {shape:9.0f} {paint:9.0f} {total:9.0f} | {shape / total * 100:5.0f}%"
            )


if __name__ == "__main__":
    run()
