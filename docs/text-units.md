# Unités de texte : codepoint, graphème (edit unit), cluster

Trois découpages des **mêmes caractères**, décidés par trois autorités
différentes. Les confondre est la source classique de bugs de curseur et de
wrapping, d'où ce mémo.

## Codepoint

Un point de code Unicode — un caractère de la `str` Python à l'index `i`.
C'est l'unité la plus fine, et celle que Python manipule par défaut
(`text[i]`, `len(text)`, `enumerate(text)`).

Exemple : « é » écrit `e` + accent combinant = **2 codepoints**.

## Graphème = edit unit

Un **« caractère perçu »** par l'utilisateur : un *grapheme cluster* au sens
**UAX#29**. Un ou plusieurs codepoints regroupés.

- Défini par le **texte seul** (la norme Unicode) — **indépendant de la police**.
- C'est l'**unité d'édition** : ce sur quoi portent le curseur, la sélection,
  le backspace. On supprime « é » d'un bloc, pas seulement l'accent.
- Dans le code Videre : `EditUnit` / `segment_edit_units` (`core/text_editing.py`).

**« Graphème » et « edit unit » sont la même chose**, à une nuance près :
l'`EditUnit` de Videre est un graphème UAX#29 **plus une étiquette de type**
(`kind` : texte, saut de ligne, tabulation, contrôle invisible, invalide…).
La *segmentation* (où sont les frontières) est exactement celle des graphèmes ;
le `kind` n'ajoute qu'une classification par-dessus. On dit « graphème » quand
on parle de la norme, « edit unit » quand on parle du type Videre.

Exemples (1 graphème chacun) : « é » (e + accent) = 2 codepoints ;
👨‍👩‍👧 (famille ZWJ) = 5 codepoints ; un akshara devanagari = plusieurs codepoints.

## Shaped cluster

Un groupe de codepoints ↔ glyphes produit par le **shaping** (HarfBuzz).

- Défini par le **shaping** : la police **et** les règles OpenType — donc
  **dépend de la police**.
- C'est l'**unité de rendu** : ce que HarfBuzz a regroupé pour fabriquer les
  glyphes.
- Dans le code Videre : `ShapedCluster` (`core/text_rendering/glyph_partition.py`).

## Comment ils se rangent

```
codepoints   c  a  f  e  ◌́            (← texte brut)
graphèmes   [c][a][f][ e+◌́ ]          (← UAX#29, indépendant de la police)
clusters    [c][a][ f+i→ﬁ  ]          (← HarfBuzz, dépend de la police)
```

| Cas | graphèmes | clusters | relation |
|---|---|---|---|
| `e` + accent combinant (« é ») | 1 | 1 | coïncident |
| ligature `f`+`i` → `ﬁ` | **2** | **1** | le cluster engloble 2 graphèmes |
| emoji ZWJ 👨‍👩‍👧 | 1 | 1 (si police ok) | coïncident le plus souvent |
| script complexe (Indic) | 1 (akshara) | 1 (réordonné) | souvent, pas garanti |

## En une phrase

- **Graphème / edit unit** = unité du **texte**, stable, c'est l'unité
  d'**édition** (curseur, sélection).
- **Cluster** = unité du **shaping**, dépend de la police, c'est l'unité de
  **rendu** (glyphes).

Ils coïncident le plus souvent mais **pas toujours** (ligatures surtout). Le
curseur doit se déplacer par **graphème** ; le rendu travaille par **cluster**.
Tout code qui mélange les deux doit convertir explicitement de l'un à l'autre.
