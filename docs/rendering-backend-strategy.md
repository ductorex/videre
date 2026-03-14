# Videre — Stratégie de backend de rendu

## Contexte

Videre est un framework GUI Python (~4000 lignes) construit sur Pygame.
Pygame fonctionne bien pour les jeux 2D, mais il est limitant pour du GUI applicatif :

- **Rendu software uniquement** : chaque widget produit une `pygame.Surface`, pas d'accélération GPU.
- **Texte de qualité médiocre** : pas de subpixel rendering, pas de hinting natif, pas de text shaping (ligatures, kerning, bidirectionnel).
- **Pas d'intégration OS** : pas de high-DPI automatique, pas d'accessibilité.
- **Réinvention coûteuse** : Videre reconstruit par-dessus Pygame tout ce que des moteurs de rendu modernes fournissent nativement (font fallback, layout texte, métriques de glyphes).

Le système de rendu texte actuel illustre bien le problème : ~1 244 lignes de code
pour gérer manuellement le font fallback par caractère Unicode, le word wrapping,
l'alignement justify, la sélection de texte, les métriques de glyphes — tout cela
en s'appuyant sur `pygame.freetype`, `fontTools`, et `unicodedataplus`.

## Objectif

Refactoriser Videre pour **abstraire le backend de rendu**, permettant de choisir
entre plusieurs implémentations :

1. **Pygame** (backend actuel) — pour les jeux 2D et le prototypage rapide
2. **Skia + SDL2** (nouveau backend) — pour les applications GUI performantes

L'architecture widget/layout/événements de Videre reste inchangée.
Seule la couche basse de rendu est interchangeable.

## Pourquoi Skia

Skia est le moteur de rendu 2D de Google, utilisé par Chrome, Android et Flutter.
C'est la référence industrielle pour le rendu 2D GPU-accéléré.

### Ce que Skia apporte

- **Rendu GPU natif** (OpenGL, Vulkan, Metal)
- **Texte de qualité native** : subpixel rendering, hinting, shaping complexe
  (arabe, hindi, emoji) via HarfBuzz intégré
- **Font fallback natif** : `FontMgr.matchFamilyStyleCharacter()` trouve
  automatiquement la meilleure police pour chaque caractère
- **Layout texte** : le module `skia.textlayout` (SkParagraph) gère le word wrap,
  l'alignement (left/center/right/justify), le hit testing, les rectangles de sélection
- **Primitives riches** : paths, gradients, ombres, blur, clipping, anti-aliasing
- **Licence** : BSD-3 (simple et permissif, contrairement à Qt GPL/LGPL/Commercial)

### Impact sur le code existant

Le système de rendu texte actuel (~1 244 lignes) serait réduit à ~280 lignes :

| Composant | Lignes actuelles | Avec Skia |
|-----------|-----------------|-----------|
| Couverture polices (`_gen_char_cov`, `font_utils`) | 152 | Supprimé (FontMgr natif) |
| Chargement/cache polices (`pygame_font_factory`) | 93 | Supprimé (skia.Typeface) |
| Rendu texte (`pygame_text_rendering`) | 362 | ~50 lignes (wrapper Canvas/TextBlob) |
| Layout texte (`font_factory_utils`) | 195 | Supprimé si SkParagraph disponible |
| Font provider (`provider.py`) | 127 | ~30 lignes (config FontCollection) |
| Unicode utils | 62 | Supprimé (Skia gère nativement) |
| Widgets (`text.py`, `character.py`) | 253 | ~200 lignes (API quasi identique) |

Les dépendances `fontTools` et `unicodedataplus` deviendraient inutiles
avec le backend Skia (Skia gère tout ça nativement).

### Bindings Python

`skia-python` (package PyPI) fournit des bindings Python matures via pybind11.
Pour le fenêtrage et la boucle d'événements (que Skia ne gère pas),
il faut coupler avec **SDL2** via `pysdl2`.

## Pourquoi garder Pygame

Pygame n'est pas dépassé — il ne joue pas dans la même catégorie que Skia.
Pour un **jeu 2D**, Pygame fournit des choses que Skia ne fait pas :

- **`pygame.sprite`** : groupes de sprites, collision detection
  (bounding box, cercle, masque pixel-perfect)
- **Tilemaps** : écosystème de chargement Tiled/TMX, scrolling de caméra
- **Input jeu** : joystick, gamepad, événements de jeu
- **Son** : `pygame.mixer` pour les effets sonores et la musique
- **Simplicité** : idéal pour le prototypage rapide et l'apprentissage

Un cas d'usage concret : un jeu 2D pourrait utiliser Videre (backend Pygame) pour
le HUD, les menus, l'inventaire (boutons, texte, listes), et Pygame directement
pour le rendu du monde de jeu (sprites, tiles, particules).

## Architecture cible

```
videre/
├── core/
│   ├── rendering/
│   │   ├── abstract_renderer.py      # Interface commune (Surface, Canvas, Font, Text)
│   │   ├── pygame_renderer.py        # Implémentation Pygame
│   │   └── skia_renderer.py          # Implémentation Skia + SDL2
│   ├── windowing/
│   │   ├── abstract_window.py        # Interface fenêtrage + event loop
│   │   ├── pygame_window.py          # Fenêtrage via pygame.display
│   │   └── sdl2_window.py            # Fenêtrage via pysdl2
│   └── ...                           # (layouts, events, etc. — inchangés)
├── widgets/                           # Inchangés — appellent abstract_renderer
├── layouts/                           # Inchangés
└── windowing/                         # Inchangés
```

### Surface d'abstraction

L'interface commune doit couvrir trois domaines :

**Rendu** : créer une surface, dessiner rect/image/texte, composer des surfaces
```python
# Exemple d'interface commune
class AbstractRenderer:
    def create_surface(self, width, height) -> Surface: ...
    def draw_rect(self, surface, rect, color): ...
    def draw_text(self, surface, text, font, pos, color) -> Rect: ...
    def blit(self, target, source, pos): ...
```

**Texte** : charger une police, mesurer du texte, rendre du texte
```python
class AbstractFontFactory:
    def load_font(self, path, size) -> Font: ...
    def measure_text(self, text, font) -> (width, height): ...
    def render_text(self, text, font, color, ...) -> Surface: ...
```

**Fenêtrage** : créer la fenêtre, gérer la boucle d'événements
```python
class AbstractWindow:
    def create(self, width, height, title): ...
    def get_events(self) -> list[Event]: ...
    def flip(self): ...  # présenter le frame
```

Le reste de Videre (arbre de widgets, dirty-tracking, event propagation,
layouts Column/Row/Container, focus management) ne dépend pas du backend
et reste intact.

## Positionnement de Videre

### Par rapport à Qt (PySide6)

Qt est supérieur en maturité, widgets, accessibilité, et intégration OS.
Videre ne cherche pas à le remplacer. Ses avantages propres :

- **Pur Python** : 4000 lignes lisibles et debuggables, vs ~150 Mo de binaires C++ opaques
- **API Python-native** : composition déclarative, pas de concepts C++ (signals/slots, QObject)
- **Contrôle pixel** : chaque widget a un `draw()` overridable, rendu identique cross-platform
- **Léger** : ~20-30 Mo (Skia) vs ~150 Mo (PySide6)
- **Testing visuel** : StepWindow + FakeUser + snapshot testing intégré
- **Licence simple** : BSD-3 vs GPL/LGPL/Commercial

Cas d'usage où Videre l'emporte : prototypage rapide, applications embarquées (Raspberry Pi),
outils internes au look custom, jeux avec GUI, enseignement.

### Par rapport à Flet

Flet = Python qui pilote un runtime Flutter via un pont (WebSocket/FFI).
Architecture fondamentalement différente :

| | Flet | Videre |
|---|---|---|
| Architecture | 2 processus (Python + Flutter/Dart) | 1 processus Python |
| Rendu | Widgets Material/Cupertino pré-faits | Dessin direct (Pygame ou Skia) |
| Widgets custom | Composer les existants, ou écrire du Dart | Override `draw()` en Python |
| Latence UI | Pont Python-Dart sur chaque événement | Zéro, même processus |
| Debugging | Complexe (2 runtimes) | Simple (pur Python) |
| Mobile | Oui (via Flutter) | Non |
| Web | Oui (Pyodide + WASM) | Non |
| Jeux 2D | Non | Oui (backend Pygame) |

L'analogie : Flet est à Videre ce que React Native est à Flutter.
React Native pilote des widgets natifs via un pont JS.
Flutter possède tout le pipeline de rendu via Skia.
Flutter a gagné face à React Native grâce à cette architecture.

### Positionnement unique

Videre avec backend Skia serait **le seul framework GUI Python qui possède
son pipeline de rendu GPU** — l'équivalent de Flutter, mais en Python.

Aucun autre projet Python n'occupe ce créneau :
- Qt/PySide6 : wrapper C++, widgets natifs
- Tkinter : wrapper Tcl/Tk, widgets natifs
- Flet : télécommande vers Flutter, pont Python-Dart
- Dear ImGui : mode immédiat, pas de widget tree persistant
- Kivy : framework complet mais architecture différente (langage KV)

## Dépendances par backend

### Backend Pygame (actuel)
- `pygame` — rendu, fenêtrage, événements, son
- `fontTools` — extraction de couverture Unicode des polices
- `unicodedataplus` — blocs Unicode, printabilité
- `pillow` — chargement d'images
- `numpy` — opérations numériques

### Backend Skia + SDL2 (cible)
- `skia-python` — rendu 2D GPU, texte, polices, images
- `pysdl2` — fenêtrage, boucle d'événements, input
- (`fontTools`, `unicodedataplus`, `pillow` deviennent optionnels — Skia les remplace)

## Étapes de migration suggérées

1. **Identifier la surface de contact** : lister tous les appels directs à `pygame`
   dans le code de Videre (hors tests et exemples)
2. **Définir l'interface abstraite** : `AbstractRenderer`, `AbstractFontFactory`,
   `AbstractWindow` — basée sur les besoins réels, pas sur une API imaginée
3. **Extraire le backend Pygame** : déplacer les appels `pygame` derrière
   l'interface abstraite, sans changer le comportement
4. **Valider** : tous les tests existants passent avec le backend Pygame abstrait
5. **Implémenter le backend Skia** : `skia_renderer.py`, `sdl2_window.py`
6. **Valider** : les mêmes tests passent avec le backend Skia
7. **Nettoyer** : supprimer le code de rendu texte devenu inutile avec Skia
