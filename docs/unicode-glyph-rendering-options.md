# Options de rendu pour caractères Unicode

Notes issues d'une discussion (2026-04-25) sur les standards de rendu de caractères Unicode et les options disponibles pour dessiner n'importe quel codepoint sans dépendre d'un *font system*.

## Questions de départ

1. Existe-t-il un standard précis décrivant comment dessiner chaque caractère Unicode (pixels ou traits vectoriels) ?
2. Existe-t-il un module Python permettant de dessiner n'importe quel caractère vers une grille (list[list[int]], image Pillow, surface Pygame) sans dépendance fonte ?
3. Même si la typographie est artistique, ne devrait-il pas exister au moins une « graphie minimale » par caractère, puisque la reconnaissance humaine implique des invariants topologiques ?

## Réponse synthétique

**Non**, Unicode n'impose aucune apparence visuelle — il définit codepoints et propriétés sémantiques (catégorie, bidi, normalisation, shaping), pas de géométrie. Les glyphes des charts officiels du Consortium sont illustratifs, non normatifs.

**Mais oui**, des invariants existent. La science cognitive (Pelli, Burns, Farell, Moore-Page 2006) montre que la reconnaissance d'une lettre repose sur ~7-9 *features* topologiques abstraites (jonctions, terminaisons, orientations relatives). Plusieurs projets ont essayé de les formaliser, sans qu'aucun ne couvre Unicode au complet.

## Catégories de standards et projets existants

### 1. Tableaux de formes de référence (sémantiques, pas géométriques)

- **Chine** : GF 0011-2009 (ordre des traits), 《通用规范汉字表》 (2013, 8105 caractères canoniques).
- **Japon** : 《常用漢字表》 (joyo kanji, 2136 caractères avec image de référence et contraintes en prose).
- **Corée** : KS X 1001 + règles de composition Hangul. Unicode encode 11 172 syllabes précomposées **et** la logique compositionnelle jamo → syllabe (logique formellement standardisée, géométrie libre).

### 2. Règles de shaping contextuel (formelles, mais non géométriques)

Pour scripts contextuels (arabe, indic, mongol, sud-est asiatique) :

- Propriétés Unicode : `Joining_Type` (R, L, D, U, T) pour l'arabe, `Indic_Syllabic_Category`, etc.
- Spec **Universal Shaping Engine** (USE).
- **OpenType** (ISO/IEC 14496-22) : tables GSUB/GPOS.
- **HarfBuzz** : implémentation de référence (Linux, Android, Chrome, Firefox).

→ Produit des identifiants de glyphes (gid 47, gid 213…) à des positions, pas des géométries. La géométrie reste dans la fonte.

### 3. Standards géométriques de niche

Géométrie pixel-précise, mais sous-ensembles minuscules :

- **OCR-A** (ISO 1073-1), **OCR-B** (ISO 1073-2) — lecture machine.
- **MICR E-13B** (ISO 1004), **CMC-7** — chèques bancaires.
- **DIN 1451** — panneaux routiers allemands.
- **Highway Gothic** (FHWA, USA), **Transport** (UK), **Frutiger Astra** (aéroports).
- **ISO 7000 / IEC 60417** — pictogrammes techniques.

### 4. Modèles pédagogiques d'écriture manuscrite

- France : modèle Dumont. Allemagne : Vereinfachte Ausgangsschrift. USA : Zaner-Bloser, D'Nealian, Palmer. Russie : *propisi*. CJK : grilles tian zi ge / genkō yōshi.
- Précis géométriquement, mais conçus pour la main humaine, sans valeur normative pour les fontes informatiques.

## Projets pratiques pour rendu pan-Unicode sans fonte système

### GNU Unifont — bitmap, couverture quasi-totale

- Police bitmap libre (SIL OFL), 8×16 (demi-chasse) ou 16×16 (pleine chasse).
- Couvre tout le BMP (Plan 0) + bonne partie du SMP.
- Format `.hex` trivial : `codepoint:bitmap_hex`.
- ~12 Mo complet, ~5 Mo pour le plan 0 seul.
- Lu nativement par **Pillow** via `ImageFont.load("unifont.pil")` (BDF/PCF supportés sans FreeType).
- Considéré comme le **« standard de fait »** consensuel pour 1 bitmap par codepoint Unicode, maintenu depuis 1998.
- Site : https://unifoundry.com/unifont/

```python
def parse_unifont_line(line):
    cp_hex, bits = line.strip().split(":")
    cp = int(cp_hex, 16)
    width = 8 if len(bits) == 32 else 16
    step = 2 if width == 8 else 4
    rows = [int(bits[i:i+step], 16) for i in range(0, len(bits), step)]
    grid = [[(r >> (width - 1 - c)) & 1 for c in range(width)] for r in rows]
    return cp, grid
```

### METAFONT (Knuth, 1977-1989) — paramétrique structurel

- Donald Knuth. Article fondateur : *The Concept of a Meta-Font* (1982).
- Philosophie : une lettre n'est pas une forme mais un **programme paramétrique** (opérations de plume + paramètres de style : chasse, inclinaison, contraste plein-délié, ductus).
- **Computer Modern** (TeX/LaTeX) est la concrétisation : un fichier source unique génère romaine, italique, bold, slanted, sans-serif, monospace, math.
- Couverture : Latin, Grec, Cyrillique, symboles maths. Pas Unicode complet.

```metafont
% 'x' minimaliste en METAFONT
beginchar("x", em#, x_height#, 0);
  pickup pencircle scaled pen_thickness;
  draw (0, x_height) -- (em, 0);   % oblique haut-gauche -> bas-droite
  draw (0, 0) -- (em, x_height);   % oblique bas-gauche -> haut-droite
endchar;
```

### Hershey fonts (1967) — vectoriel pratique

- Allen Hershey, US Naval Weapons Laboratory.
- ~4000 glyphes définis comme **séquences de traits** (segments avec stylet baissé/levé).
- Couverture : Latin (plusieurs styles), Grec, Cyrillique, kana japonais, math, astronomie, météo, cartographie, runes.
- Domaine public.
- Python : `HersheyFonts` sur PyPI.
- Idéal pour `pygame.draw.line` / `aalines`, plotters, CNC, gravure laser.

```python
# pseudo-format Hershey pour 'x'
strokes = [[(0, 16), (10, 0)],
           [(0, 0), (10, 16)]]
```

### CJK — formalisation presque complète

C'est le script où on est le plus proche d'un standard structurel utilisable :

- **Taxonomie de traits** : 永字八法 (8 traits classiques) historiquement, modernisée dans diverses méthodes de saisie. Codifiée par Unicode dans le bloc **CJK Strokes** (U+31C0-U+31EF).
- **Ordre des traits** standardisé : GF 0011-2009 (Chine), équivalents Japon et Taïwan.
- **Décomposition idéographique** : **Ideographic Description Sequences** (U+2FF0-U+2FFF), opérateurs ⿰ (gauche-droite), ⿱ (haut-bas), ⿸ (bordure haut-gauche)…
- Bases : **CHISE** et **IDS-UCS** fournissent des IDS pour la quasi-totalité des sinogrammes encodés.
- **Stroke data vectorielles** :
  - **Make Me a Hanzi** : ~9000 caractères chinois en SVG, avec ordre et médians de traits — https://github.com/skishore/makemeahanzi
  - **KanjiVG** : ~6500 kanji japonais en SVG — https://kanjivg.tagaini.net/

Combinés : « caractère X = composition IDS de composants Y, qui se décomposent en traits T dans l'ordre O ».

## Modules Python utiles

| Module | Usage |
|---|---|
| `Pillow` (PIL) | Lit BDF/PCF nativement (`ImageFont.load`), dessine via `ImageDraw` |
| `bdflib` | Parse BDF en objets manipulables |
| `fonttools` | Extraction de paths depuis TTF/OTF (`fontTools.pens`) |
| `freetype-py` | Rasterisation directe |
| `HersheyFonts` | Hershey ready-to-use |

## Pourquoi pas de standard Unicode-wide ?

1. **Culturelle** : la typographie est artistique. Imposer une géométrie est perçu comme appauvrissant — cf. controverses récurrentes autour de la Han unification où Chinois, Japonais, Coréens, Hong-Kongais réclament des variantes régionales pour les *mêmes* codepoints.
2. **Économique** : les fonderies vivent de fontes protégeables. Un standard géométrique gratuit casserait ce modèle.
3. **Technique** : un rendu de qualité dépend de la taille, du média, de la résolution (hinting, optical sizing, variable fonts). Une géométrie figée serait inadéquate hors de la taille pour laquelle elle a été définie.
4. **Hétérogénéité des scripts** :
   - Latin, Grec, Cyrillique, Hébreu : ~10-15 primitives suffisent (METAFONT s'en sort).
   - Arabe, indic : courbes de Bézier paramétrées par contexte de jonction + positionnement de marques.
   - CJK : hiérarchie de composition (IDS) + alphabet de traits.
   - Hangul : composition jamo dans une boîte syllabique avec mise à l'échelle non triviale.

   Aucun cadre primitif unifié n'est viable. Chaque branche a sa formalisation locale.

## Recommandation pratique pour videre

Pour un fallback structurel/bitmap garanti sans dépendance fonte système :

| Couche | Cible | Outil |
|---|---|---|
| Vectoriel par traits | Latin, Grec, Cyrillique, math | **Hershey fonts** (`HersheyFonts`) |
| Vectoriel SVG | CJK | **Make Me a Hanzi** + **KanjiVG** |
| Bitmap fallback | Indic, arabe, scripts rares | **GNU Unifont** (`.hex` direct ou via Pillow) |

Couverture Unicode quasi-complète avec définitions structurelles (donc redimensionnables proprement) là où c'est possible, repli bitmap pour le reste. Look hétérogène, mais absence totale de *tofu* (□).

## Références à creuser

- **GNU Unifont** : https://unifoundry.com/unifont/
- **METAFONT** et *The Concept of a Meta-Font* (Knuth, 1982)
- **Hershey fonts** (domaine public, original via NIST)
- **Make Me a Hanzi** : https://github.com/skishore/makemeahanzi
- **KanjiVG** : https://kanjivg.tagaini.net/
- **CHISE database** (CJK structural data) : http://www.chise.org/
- **Pelli, Burns, Farell, Moore-Page (2006)** — *Feature detection and letter identification*
- **Unicode CJK Strokes** block (U+31C0-U+31EF)
- **Unicode IDS** block (U+2FF0-U+2FFF)
- **OpenType / Universal Shaping Engine** (HarfBuzz docs)
\r