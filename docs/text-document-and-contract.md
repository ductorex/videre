# Plan C — objet « document » + contrat de navigation en edit units

État : **IMPLÉMENTÉ — plan C entier (C1→C5), 2026-06-14.** Suite du plan B
(modèle full-flat cluster). Fusionne deux objectifs qui partagent le même socle :

1. **Cache resize** — au redimensionnement (largeur change, texte identique), ne
   rejouer que wrap+reorder+paint, pas partition+shape (le coût HarfBuzz).
2. **Contrat en edit units** — le curseur navigue par **graphème** (edit unit) en
   ordre **visuel**, et le renderer ne rend que des positions valides. Fin de la
   double segmentation et du snapping dans `TextInput`.

Voir `docs/text-units.md` pour codepoint / graphème (= edit unit) / cluster.

> **Écarts vs ce cadrage (tel qu'implémenté).** La factory n'est pas
> `backend.text_document(...)` mais **`AbstractTextRendering.document(text)`** (le
> rendering porte déjà size/strong/italic/height_delta). Le caret au milieu d'une
> ligature (point ouvert #1) a été tranché : **pas de split** — une ligature reste
> un item, le caret la saute entière (= comportement d'avant). L'alignement
> d'insertion explicite est remplacé par un **re-sync dans `_ensure_state`** (le
> curseur brut est aligné par le contrat au prochain accès). Le reste est conforme.

## Le constat (rappel)

Aujourd'hui le contrat `TextRenderingResult` parle en **codepoints** (positions
source) et **codepoints visuels**. Mais l'unité d'édition est le **graphème**.
Du coup `TextInput` re-segmente le texte (`_segmentation`) et réconcilie en
permanence : `_snap_state_to_cluster`, la boucle `while pos not in boundaries`
de `_step_char`, `align_to_boundary` à l'insertion. Toute cette plomberie
existe parce que **le renderer ignore qu'il manipule des graphèmes**.

Par ailleurs, partition+shape ne dépendent que du **texte** (size/bold/italic),
pas de la **largeur** — mais le pipeline les rejoue à chaque frame de resize.

## L'objet document

Un objet de niveau **document** qui détient ce qui ne dépend que du texte, et
sert de socle aux deux objectifs.

```
AbstractTextDocument:
    text: str
    edit_units: tuple[EditUnit, ...]          # segmentés UNE fois
    layout(width, *, align, wrap_words, space_policy)
        -> TextRenderingResult                # mise en page SANS peinture
    render(width, *, color, align, wrap_words, space_policy, underline,
           selection) -> (TextRenderingResult, Rendering)
```

- Construit via une factory backend : `backend.text_document(text, size, *,
  strong, italic, height_delta)`. Cette construction fait `partition_text` +
  `shape_line` (+ la segmentation en edit units) — **le coût HarfBuzz**.
- `render(width, ...)` fait collapse + wrap + reorder + paint — **pas de
  re-shape**. C'est ce qu'on rejoue au resize.
- Ce qui va dans la **factory** (= invalide le document) : `text, size, strong,
  italic, height_delta` (tout ce qui change le shape/les métriques).
- Ce qui va dans **`render`** (= rejoué librement) : `width, color, align,
  wrap_words, space_policy, underline, selection` (largeur + effets de peinture).

`render_char` reste une méthode séparée du backend (un seul glyphe, pas de
document).

### Où il vit

Le **widget `Text`** cache le document (nouveau `_document`), invalidé par
`_set_wprop` quand `text`/`size`/`strong`/`italic`/`height_delta` change — mais
**pas** au resize. `draw` devient : créer le document si absent, puis
`document.render(width, …)`. Le widget passe toujours par le contrat abstrait,
donc reste backend-agnostique.

## `layout()` — mesurer sans peindre (suivi go-live)

`render(width)` fait *layout + paint*. Mais la navigation de `TextInput` (caret,
flèches, hit-test) n'a besoin que du `TextRenderingResult`, pas de la surface ;
or elle le lit aujourd'hui sur `Text._rendered`, rafraîchi seulement au `draw`.
Entre une mutation et le `draw` suivant (même frame, plusieurs events), ce
`_rendered` est périmé — d'où un caret faux pendant 1 frame, le jour où le shapé
sera live (pitfall #4).

`layout(width, …)` renvoie ce `TextRenderingResult` **sans peindre** : on scinde
`paint_glyph_lines` en `assemble_glyph_lines` (géométrie → `AssembledText`, sans
surface) + `paint_assembled` (peinture). `layout` et `render` passent par le même
`AssembledText`, **mémoïsé** sur `(width, wrap_words, space_policy, align)` :

- coût : ni re-shape (déjà caché) ni re-paint ; seulement wrap + reorder +
  géométrie — la moitié légère ;
- cache à **une entrée** : entre deux frappes la clé est stable, donc une frame
  d'édition = `layout` (event) qui calcule puis `render` (draw) qui **réutilise**
  = un seul layout, comme aujourd'hui (pas de double-wrap) ;
- invalidation gratuite : le document est immuable par `(text, size, …)`, donc un
  nouveau document = cache vide.

**Pas encore branché** : `TextInput` lit toujours `_rendered`. `layout()` est la
primitive prête pour le go-live shapé — et, plus largement, la **mesure de texte
sans peinture** dont dépendront `Drawer` / `text_sizing` / une passe de mesure
(un parent peut demander sa hauteur à une largeur sans forcer de paint). Le legacy
l'implémente en rejouant `render_text` et jetant la surface (pas de split ; il
n'est pas la cible perf).

## Le contrat de navigation, révisé

**Mêmes 11 méthodes, même forme state-based, même ADN visuel.** Le seul
changement est l'**unité** d'une position : le graphème, plus le codepoint.

- `visual_pos` = index dans la séquence **visuelle des edit units** (au lieu des
  codepoints visuels). C'est ce que `TextInput` stocke pour une sélection en
  ruban contigu.
- `pos` = position **source** (codepoint), mais **garantie alignée** sur une
  frontière d'edit unit. `TextInput` slice le texte avec, directement.
- `next_visual`/`prev_visual` avancent d'**un edit unit** vers la droite/gauche à
  l'écran. Le renderer fait le pas + l'alignement lui-même → plus de boucle de
  snapping côté `TextInput`.
- `visual_state_at_pixel` rend déjà une frontière d'edit unit → plus de
  `_snap_state_to_cluster`.
- `total_visual_count` = **nombre d'edit units** (Ctrl+A).
- `visual_range_to_source_set(start, end)` = positions source couvertes par les
  edit units visuels `[start, end)` (inchangé dans l'esprit).

Le renderer shaped, qui aujourd'hui navigue par **cluster**, navigue désormais
par **edit unit** : il groupe ses clusters par graphème (via les `EditUnit` du
document) et expose ces groupes au caret. Le cluster reste l'unité interne de
rendu ; le graphème devient l'unité publique de position.

## Ce que `TextInput` perd (la simplification)

- `_edit_segmentation` + `_segmentation()` → lit `…_document.edit_units` (plus de
  **deuxième** segmentation) ;
- `_snap_state_to_cluster` → supprimé (positions déjà alignées) ;
- la boucle `while pos not in boundaries` de `_step_char` → supprimée ;
- `align_to_boundary` dans `_insert_text` → supprimé ;
- backspace/delete : `previous_edit_unit(document.edit_units, pos)` au lieu de
  re-segmenter (la logique reste, la source des edit units change).

`next_visual_word`/`prev_visual_word` (Ctrl+flèche, via `cursword` sur le texte)
ne bougent pas — les **mots** sont une autre échelle, orthogonale aux graphèmes.

## Le legacy

`PygameTextDocument` : le parsing actuel fait une fois (factory), `render(width)`
fait le layout. Il expose `edit_units` en supposant **1 edit unit = 1 codepoint**
(un edit unit trivial par codepoint). Conséquence assumée : sur un graphème
multi-codepoints (« é » décomposé), le legacy laisse le caret entre les deux —
imparfait, mais acceptable (le legacy n'est pas le futur). Sa navigation reste
`pos ± 1`, désormais lue comme « ± 1 edit unit ».

## Plan de migration (incrémental, test-gated)

Les deux objectifs sont séparables ; je ferais le **cache d'abord** (sûr, pas de
changement de contrat), puis le **contrat edit-unit** (le morceau sensible).

- **C1 ✅** — `AbstractTextDocument` + `AbstractTextRendering.document(text)`.
  Shaped : `ShapedDocument` (cache partition+shape, `edit_units`, `render(width)`).
  `render.py` scindé `build_glyph_lines` / `layout_glyph_lines` / `paint_glyph_lines`.
  `render_text` gardé en parallèle.
- **C2 ✅** — le widget `Text` cache `_document`, appelle `document.render(width)`.
  **Gain resize mesuré ~5×** (`tools/bench_text.py`). `underline` déplacé en arg
  de rendu pour ne pas invalider le cache.
- **C3 ✅** — le renderer shaped navigue par edit unit (`render.py::_line_items`
  groupe les clusters par graphème). Ligatures non splittées.
- **C4 ✅** — `TextInput` dégraissé (`_segmentation` / `_snap_state_to_cluster` /
  boucle de snapping / align d'insertion supprimés ; lit `document.edit_units`).
- **C5 ✅** — legacy : `PygameTextDocument`, `edit_units` = 1 cp = 1 eu
  (`segment_codepoints`).
- **C6 ✅** — `document.layout(width)` : mise en page sans peinture
  (`assemble_glyph_lines` / `paint_assembled` / `AssembledText`), cache partagé
  `layout`/`render` sur `(width, wrap_words, space_policy, align)`. Primitive pour
  le go-live (#4) et la mesure sans paint ; `TextInput` pas encore rebranché.

Validé : 282 widget_tests (legacy) + 296 shaped + 7 grapheme mirror ; divergences
snapshot inchangées (64/190) = zéro régression de rendu.

## Décisions & points ouverts

1. **Caret au milieu d'une ligature** (cluster englobe 2+ graphèmes) : **tranché —
   pas de split.** Une ligature reste un item ; le caret la saute entière, comme
   le legacy le faisait. Le caret-au-milieu (position pixel interpolée) serait un
   raffinement ultérieur, non requis pour l'édition courante.
2. **`pos` source vs index d'edit-unit** : je propose `pos` = position source
   alignée (le plus simple pour slicer). L'alternative (pos = index d'edit unit,
   conversion vers source via le document) est plus « pure » mais ajoute une
   indirection partout. Recommandation : position source alignée.
3. **Accès `TextInput` → document** : via `self._text._document` (comme
   l'accès actuel à `self._text._rendered`). Couplage déjà existant.
4. **`edit_units` au niveau document, pas par sous-ligne** : c'est le pendant de
   leur suppression à l'étape A (où ils étaient morts *par sous-ligne*). Ici ils
   sont vivants *au niveau document* — besoin réel, foyer correct.
