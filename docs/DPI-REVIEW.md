# Revue sévère du commit DPI

Commit revu : `fee4414 Make videre DPI-aware`

Verdict court : l'idée architecturale est bonne, mais le commit n'est pas
merge-ready. Le modèle "layout logique, Drawer device, scale appliqué à la
frontière `window.drawing`" est cohérent sur le papier, mais plusieurs chemins
centraux violent ses propres invariants : taille de fenêtre, crop de
`ScrollView`, cache texte, et opt-in DPI Windows. Les tests ajoutés donnent une
confiance trop locale : ils valident surtout les scènes choisies à 1.5x et 2x,
pas les cas fractionnaires courants comme 1.25x.

## Mise à jour après les correctifs non commités

Verdict actualisé : les deux problèmes P1 de la revue initiale sont traités de
façon convaincante. Le patch va dans le bon sens et répond réellement aux bugs
visibles à 125 %. Il reste cependant deux points importants avant de considérer
le chantier DPI propre : le cache `TextDocument` est seulement partiellement
corrigé, et l'idempotence de l'opt-in DPI Windows reste ouverte.

### Corrigé : taille de fenêtre DPI

Le passage de `_to_device()` à `_size_to_device()` basé sur
`to_device_ceil()` est la bonne correction. Les tailles de fenêtre demandées au
backend sont maintenant cohérentes avec les surfaces `Drawer.at_scale()`, qui
utilisent elles aussi `ceil(logical × scale)`.

Le nouveau test `test_window_opens_ceil_device_size_at_125_percent` cible
exactement le trou de couverture que la revue pointait : largeur logique `101`,
scale `1.25`, bordures aux quatre bords, et round-trip device → logique. C'est
nettement plus probant que les snapshots 1.5x/2x.

### Corrigé : `crop_drawer` en DPI fractionnaire

Le nouveau `crop_drawer()` ne part plus d'un rectangle device edge-scaled trop
court; il dérive maintenant la fenêtre device depuis les pixels du blit de
référence. C'est le bon invariant : le crop doit produire les mêmes pixels que
le blit complet avec offset, pas seulement une approximation géométrique du
rectangle logique.

La matrice `test_crop_pixels_match_offset_blit_scaled` est le bon type de test :
petites tailles exhaustives, scales `1.25`, `1.75`, `170/96`, comparaison
crop-vs-blit en bytes RGBA. Elle couvre précisément les résidus de rounding que
les snapshots ne voient pas. Le test sur le global fill est aussi utile : il
vérifie que `FillArgs(rectangle=None)` ne déborde pas au-delà de la surface
source lorsque la vue est plus grande que le contenu.

### Partiellement corrigé : cache `TextDocument`

La correction actuelle invalide le document quand `window.scale_factor` change.
Elle corrige donc le repro exact de la revue initiale : même `Text` rendu à 1x
puis à 2x. Mais elle ne couvre pas tout le contexte que `TextDocument` bake.

Repro encore cassé :

1. Créer `text = videre.Text("Scale")`.
2. Le rendre dans une `StepWindow(font_size=14)`.
3. Le rendre ensuite dans une `StepWindow(font_size=28)`.
4. Le document reste à `_size == 14` et la surface garde la même largeur.

Cause : `Text.get_document()` ne clé que sur `window.scale_factor`, alors que
`Window.text_rendering()` résout aussi `size=size or self._font_size_pts`, et
que `TextDocument` bake la taille résolue, `height_delta`, `bold`, `italic`, le
scale, le mode subpixel et le couple shaper/rasterizer.

Correction attendue : remplacer `_document_scale` par une vraie clé de document,
par exemple une petite tuple contenant au minimum la taille logique résolue, le
scale, `strong`, `italic`, `height_delta`, `compact`, `subpixel`, et idéalement
l'identité du shaper/rasterizer ou du contexte de fenêtre. Le test à ajouter
doit réutiliser le même `Text` entre deux fenêtres de même scale mais de
`font_size` différent.

### Toujours ouvert : opt-in DPI Windows idempotent

Le code lit encore `system_scale_factor()` uniquement si
`declare_dpi_awareness()` retourne `True`. Cela laisse ouvert le cas où le
processus est déjà DPI-aware parce qu'une autre bibliothèque ou une fenêtre
précédente a fixé l'état global. Dans ce cas, l'appel de déclaration peut
échouer sans signifier que le scale vaut 1.0.

Ce point n'est pas aggravé par les nouveaux changements, mais il reste non
résolu par rapport à la revue initiale. Il faudrait distinguer au moins :
succès, déjà déclaré, indisponible, et échec tardif; puis lire le scale dans les
cas où le processus est déjà DPI-aware.

### Vérification des nouveaux changements

Tests exécutés pendant la deuxième revue :

```text
uv run pytest tests/videre_tests/test_dpi.py tests/videre_tests/test_drawer_crop.py tests/widget_tests/test_dpi_text.py -q
42 passed

uv run ruff check videre/widgets/text.py videre/core/drawer_crop.py videre/core/pygame_backend/backend.py videre/core/abstract_backend.py tests/videre_tests/test_dpi.py tests/videre_tests/test_drawer_crop.py tests/widget_tests/test_dpi_text.py
All checks passed

uv run poe typecheck
All checks passed
```

Mini-repro manuel encore échoué : même widget `Text("Scale")`, rendu dans une
fenêtre `font_size=14` puis dans une fenêtre `font_size=28`, garde le document à
taille 14.

## Ce qui est solide

- La séparation conceptuelle entre pixels logiques et pixels device est la
  bonne direction pour garder les widgets backend-agnostic.
- `Drawing` comme frontière de recording est une bonne abstraction : elle garde
  le renderer scale-free et préserve l'idée que le `Drawer` est un IR.
- Le texte est pensé avec plus de soin que la moyenne : glyphes en device,
  mesures exposées en logique, hit-test converti au bord.
- Les tests ciblent quelques risques réels : edge scaling, ancrage flush, texte
  à 1.5x, resize OS avec taille device arbitraire.
- La correction de `AbstractSides.__eq__` est une vraie correction utile, même
  si elle est mélangée à un commit déjà très large.

## Findings bloquants

### P1 - La taille de fenêtre DPI utilise le mauvais rounding

Fichiers :

- `videre/core/pygame_backend/backend.py`
- `videre/core/drawing.py`
- `videre/core/abstract_backend.py`

Le backend ouvre la fenêtre avec `_to_device()`, qui utilise `to_device()`
half-up :

```python
def _to_device(self, value: LogicalPx) -> DevicePx:
    scale = self._scale_factor
    return value if scale == 1.0 else to_device(value, scale)
```

Puis `start()` et `resize_screen()` utilisent ce résultat pour `set_mode()`.
Or les surfaces du modèle DPI utilisent `ceil(logical * scale)`, via
`Drawer.at_scale()` et `Drawing.new_surface()`. Pour une taille, `ceil` est
le rounding documenté comme "cover"; half-up est seulement correct pour des
positions, ancres, strokes et tailles de fonte.

Conséquence à 125 % :

- largeur logique `101`
- `to_device(101, 1.25) == 126`
- `to_device_ceil(101, 1.25) == 127`
- la fenêtre OS fait donc 126 px, mais le contenu plein écran attend 127 px

J'ai confirmé le symptôme avec une fenêtre `101x20` à scale forcé `1.25` :
un `Container` full-width avec bordure noire perd sa bordure gauche. Le pixel
`(0, 10)` est rouge au lieu d'être noir, tandis que la bordure droite reste
visible. Ce n'est pas seulement une divergence théorique; c'est un rendu faux.

Cause aggravante : `ScaledDrawing.blit()` a une logique d'ancrage flush :

```python
if position[0] + drawer.get_width() == surface.get_width():
    x = min(x, surface.device_width - drawer.device_width)
```

Si le root device est trop petit, `surface.device_width - drawer.device_width`
peut devenir négatif, donc un enfant plein écran peut être blitté à `x = -1`.

Correction attendue :

- les tailles de fenêtre demandées au backend doivent utiliser
  `to_device_ceil()`, pas `to_device()`;
- `AbstractWindowing.device_width/device_height` avant ouverture doivent être
  cohérents avec cette même politique;
- ajouter un test à `scale=1.25`, taille logique impaire/non ronde, avec une
  bordure aux deux bords.

### P1 - `crop_drawer` n'est pas pixel-identique en DPI fractionnaire

Fichiers :

- `videre/core/drawer_crop.py`
- `videre/layouts/scroll/scrollview.py`
- `tests/videre_tests/test_drawer_crop.py`

`ScrollView` promet que cropper le contenu visible puis le blitter à `(0, 0)`
est pixel-identique au blit du contenu complet avec offset. Cette promesse est
même documentée dans `scrollview.py` :

```python
# Pixel-identical to blitting `content` at the offset
visible = Rectangle(-self._content_x, -self._content_y, width, height)
drawing.blit(view, crop_drawer(content, visible), (0, 0))
```

Le problème est dans `crop_drawer()` :

```python
prect = rect if scale == 1.0 else _scale_rect(rect, scale)
out = Drawer.at_scale(rect.width, rect.height, scale)
_crop_into(out, drawer, prect)
```

Le rectangle visible est scalé edge-wise avec half-up, mais la surface de
sortie est allouée avec `ceil`. À 125 %, un viewport logique de 1 px peut avoir
2 device pixels, alors que le `prect` half-up ne couvre qu'un seul pixel.

Repro minimal confirmé :

- `ScaledDrawing(1.25)`
- contenu logique de largeur `2`
- viewport logique de largeur `1`
- comparaison :
  - blit complet du contenu avec offset
  - `crop_drawer(content, Rectangle(0, 0, 1, h))`
- différence au pixel device `(1, 0)` : le crop rend transparent là où le blit
  complet garde du contenu.

Impact : une `ScrollView` peut perdre une colonne ou une ligne visible à des
scales fractionnaires courants. Les tests actuels ne le voient pas parce que
`test_crop_pixels_match_offset_blit` utilise des `Drawer` 1.0 et compare des
coordonnées logiques/device identiques.

Correction attendue :

- définir explicitement si le crop doit prendre un rectangle logique ou device;
- si l'API reste logique, le rectangle device utilisé pour le crop doit couvrir
  exactement la surface de sortie device, pas seulement le slot edge-scaled;
- ajouter une matrice de tests `scale=1.25` avec petites tailles et offsets
  exhaustifs, en comparant pixel par pixel crop vs blit complet.

### P2 - Le cache `TextDocument` ignore la fenêtre et le scale

Fichiers :

- `videre/widgets/text.py`
- `videre/windowing/window.py`
- `videre/core/text_rendering/renderer.py`
- `videre/core/text_rendering/document.py`

`Text.get_document()` garde un document tant que les props texte ne changent
pas :

```python
if self._document is None:
    self._document = self._text_rendering(window).document(self.text)
return self._document
```

Mais `TextRendering` encode maintenant le `scale_factor` dans le document :

```python
return TextRendering(..., scale=self.scale_factor, ...)
```

Le même widget peut être rendu dans une autre fenêtre; `Widget.render()` le
supporte déjà puisque sa clé de cache contient `window`. Le document texte, lui,
n'est pas invalidé quand la fenêtre ou le scale change.

Repro confirmé :

1. Créer `t = videre.Text("Scale")`.
2. Le rendre dans une `StepWindow()` à scale 1.0.
3. Le rendre ensuite dans une `StepWindow(dpi_aware=True)` avec scale forcé 2.0.
4. `t._document._scale` reste `1.0`, et la surface device reste non doublée.

Impact : texte flou/trop petit/faux si un widget texte est réutilisé entre
fenêtres, ou si un backend futur supporte un changement dynamique de scale.

Correction attendue :

- inclure une clé de document qui contient au minimum le scale, le shaper, le
  rasterizer et la config de texte qui influence le rendu;
- ou stocker le document dans une structure par fenêtre/rendering context;
- ajouter un test avec le même `Text` rendu dans deux fenêtres de scales
  différents.

### P2 - L'opt-in DPI Windows n'est pas robuste/idempotent

Fichiers :

- `videre/core/dpi.py`
- `videre/core/pygame_backend/backend.py`
- `tests/videre_tests/test_dpi.py`

Le backend lit `system_scale_factor()` seulement si `declare_dpi_awareness()`
retourne `True` :

```python
if dpi_aware and declare_dpi_awareness():
    scale = system_scale_factor()
    if scale > 0 and scale != 1.0:
        self._scale_factor = scale
```

Sur Windows, déclarer le DPI est un état global du processus. Les appels peuvent
échouer parce que l'état est déjà fixé, parce qu'une autre bibliothèque l'a déjà
fait, ou parce qu'une fenêtre existe déjà. Ce n'est pas équivalent à "pas de
scale". Le code traite pourtant tous ces cas comme scale 1.0.

Le test `test_dpi_helpers_are_safe_to_call()` appelle réellement
`declare_dpi_awareness()`. Sur Windows, ce test peut modifier l'état global du
processus pytest, et donc influencer les tests qui suivent. C'est une mauvaise
idée pour un test unitaire.

Correction attendue :

- rendre `declare_dpi_awareness()` plus explicite : succès, déjà déclaré,
  indisponible, échec tardif;
- lire le scale quand l'état est déjà DPI-aware au lieu de forcer 1.0;
- ne pas appeler la vraie API globale dans les tests ordinaires : monkeypatcher
  ou isoler ce test dans un process séparé.

## Couverture de tests : trop optimiste

Tests exécutés pendant la revue :

```text
.venv\Scripts\python.exe -m pytest tests\videre_tests\test_dpi.py tests\pygame_tests\test_scaled_drawing.py -q
23 passed

.venv\Scripts\python.exe -m pytest tests\widget_tests\test_dpi_text.py -q
6 passed
```

Ces tests passent, mais ils ne prouvent pas les invariants généraux. Les zones
non couvertes ou mal couvertes sont exactement les zones cassées :

- taille de fenêtre à `scale=1.25` et largeur logique dont le produit finit par
  `.25`;
- crop vs blit complet à scale fractionnaire;
- réutilisation d'un widget texte entre deux fenêtres de scales différents;
- vraie idempotence Windows de l'opt-in DPI.

La doc de `test_dpi_text.py` dit que 1.5 est "the interesting case". C'est vrai
pour beaucoup de roundings, mais faux comme couverture exhaustive : 1.25 expose
des cas où `ceil` et half-up divergent dans l'autre sens.

## Recommandations de correction

1. Corriger les tailles device de fenêtre.
   - `PygameWindowing._to_device()` ne devrait probablement pas servir aux
     tailles.
   - Ajouter `_size_to_device()` basé sur `to_device_ceil()`.
   - Utiliser cette conversion dans `start()`, `resize_screen()` et les valeurs
     par défaut de `AbstractWindowing.device_width/device_height`.

2. Repenser `crop_drawer` en termes d'intervalles device couverts.
   - Le crop doit produire exactement les pixels qu'un blit complet aurait
     exposés dans la surface cible.
   - Tester exhaustivement de petites largeurs/hauteurs pour `scale=1.25`.

3. Rendre le cache texte scale-aware.
   - Le document caché doit être invalidé quand le contexte de rendu change.
   - Le plus simple : stocker une clé de document incluant `window.scale_factor`
     et l'identité du couple shaper/rasterizer.

4. Isoler le plumbing Windows.
   - Ne pas appeler les fonctions DPI globales dans un test de type "safe".
   - Modéliser "déjà déclaré" comme un état acceptable, pas comme un fallback
     silencieux à 1.0.

5. Ajouter une suite DPI fractionnaire minimale.
   - `scale=1.25` doit devenir obligatoire.
   - Tester tailles `1`, `2`, `3`, `10`, `101`.
   - Tester border gauche/droite et haut/bas, `ScrollView` crop, texte réutilisé.

## Avis final

Ce commit mérite d'être scindé ou corrigé avant merge. L'architecture générale
est prometteuse, mais le niveau de risque est élevé parce que les erreurs sont
dans les fondations : size rounding, crop, cache texte, et état global Windows.
Le plus inquiétant n'est pas qu'il y ait des bugs; c'est que les tests actuels
passent avec ces bugs. Il faut donc renforcer les invariants par des tests
petits, exhaustifs, et explicitement construits autour des roundings qui
divergent.
