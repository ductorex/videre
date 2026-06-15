# Modèle « cluster » pour le shaping (plan B)

État : **plan B implémenté (B1→B5), validé par les tests. Plan C fait —
voir `docs/text-document-and-contract.md`.**
Suite des correctifs perf du 2026-06-14 (wrap O(n²) → O(n)). Ceux-ci ont
supprimé du gaspillage ; ici on a supprimé la *re-dérivation* qui rendait le
wrap lourd à la base. `ShapedUnit` / `ShapedTextLine.units` n'existent plus.

## Problème

Le modèle transporte des glyphes à plat. Le wrap et le caret, eux, raisonnent
par *cluster* (le morceau insécable : une base + ses marques, ou une ligature).
Le shaper calcule déjà ces clusters, puis les jette. Du coup chaque passe les
reconstruit : `_atomize` les re-groupe (`_clusters`) et les re-mesure
(`measure_glyphs`), `_rebuild` re-colle des `ShapedUnit` aussitôt ré-aplatis par
le reorder, `_line_clusters` les re-groupe pour le caret.

## Idée

Le **cluster devient une valeur de premier ordre, mesurée une fois au shape**
(`ShapedCluster` : ses glyphes, son advance, son encre, sa position source, ses
drapeaux de coupure). La ligne devient une **liste plate de clusters**.
`ShapedUnit` disparaît (« full flat »).

## Ce que ça supprime

`_clusters`, le re-`measure_glyphs` du wrap, le re-collage de `_rebuild`, le
re-groupement de `_line_clusters`, et `ShapedUnit`. `_atomize` se réduit à une
passe `mark_breaks` qui combine les drapeaux du cluster avec `wrap_words`.

## Coupures : intrinsèque vs mode

Le caractère sécable dépend de `wrap_words`, donc on ne fige pas tout au shape
(sinon on casse « shaper une fois, wrapper N largeurs », utile pour C). Le
cluster porte les drapeaux **intrinsèques** (texte seul) ; le wrap les combine
avec le mode en une passe O(n).

## Reorder

Réordonné **par cluster** (un cluster = un seul niveau bidi) au lieu de par
glyphe. Plus simple (plus de tri stable). Étape la **plus risquée** —
oracle = snapshots bidi.

## Edit units (double segmentation)

On ne remet pas `edit_units` par sous-ligne (c'était du code mort). Ils vont au
niveau **document**, dans l'objet à état de C : segmentés une fois, partagés
entre le rendu et `TextInput` (qui cesse de re-segmenter). Livrable de C.

## Plan incrémental (chaque étape = équivalence exacte + tests verts)

- **B1.** Ajouter `ShapedCluster` ; le shaper le produit *en parallèle* des
  glyphes. Test de parité (mesure cluster == `measure_glyphs`). ← socle, invisible.
- **B2.** `_atomize` consomme les clusters (supprime `_clusters` + re-mesure).
- **B3.** Porter les clusters dans wrap + reorder ; supprimer le re-collage de
  `_rebuild` ; reorder par cluster.
- **B4.** Render / caret / `render_char` sur clusters.
- **B5.** Retirer l'ancien chemin (glyphes à plat, `ShapedUnit`).
- **(C).** Objet à état : cache le shape, ne rejoue que wrap+reorder au resize ;
  porte les edit units pour `TextInput`.

## Risques

1. Parité des mesures — verrou avant tout (B1).
2. Reorder par cluster sur bidi mixte (B3, le plus délicat).
3. Gaps multi-espaces — groupés en une glue au wrap selon le mode.

Le renderer shapé n'étant pas branché, tout ceci est interne ; le garde-fou est
la suite de tests (160+) plus les snapshots.
