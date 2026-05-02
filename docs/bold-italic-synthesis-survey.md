# Synthèse bold/italique : enquête sur 4 logiciels de référence

Notes pour décider de la politique de videre vis-à-vis du bold et de l'italique sur l'ensemble d'Unicode. Référence prise sur Firefox, Chrome, Microsoft Word et Google Docs.

## Question

Pour chaque famille de caractères Unicode, faut-il :

- **Police dédiée** : charger un fichier de police explicitement bold ou italic conçu par un typographe ?
- **Calcul** : synthétiser à la volée à partir de la police Regular (épaississement du contour pour bold, cisaillement pour italic) ?

## Réponse synthétique

Les quatre logiciels suivent **la même logique** :

1. Demande utilisateur (bold / italic / bold+italic).
2. Si la police chargée fournit la variante → police dédiée.
3. Sinon → calcul (synthèse).

**Aucun des quatre n'opère de distinction par script Unicode** pour la décision de synthétiser. Tous les quatre synthétiseront aveuglément le bold sur du chinois, et l'italique sur de l'arabe ou du japonais, même si typographiquement ces concepts n'existent pas dans ces écritures. Le résultat est moche pour certaines combinaisons, mais le comportement est universel et prévisible.

Les différences entre logiciels sont marginales :

| | Firefox | Chrome | Word | Google Docs |
|---|---|---|---|---|
| Synthèse activée par défaut | Oui | Oui | Oui | Oui |
| Distinction par script | Non | Non | Non | Non |
| Désactivable par l'utilisateur | Oui (`font-synthesis: none` en CSS) | Oui (idem) | Non | Non (héritage navigateur) |
| Source des fontes | Système + @font-face | Système + @font-face | Système Windows | Catalogue Google Fonts |

Tous suivent CSS Fonts Module Level 4 ou un équivalent : `font-synthesis: weight style small-caps` activé par défaut.

## Tableau des familles Unicode

Légende :
- **Réel** : un fichier de police officiel existe avec cette variante (Bold ou Italic conçu par un typographe).
- **Calcul** : synthétisé par le logiciel à partir du Regular.
- ✅ existe en réel chez les producteurs majeurs (Noto, Microsoft, Adobe, etc.).
- ⚠️ existe partiellement (quelques polices, pas la majorité).
- ❌ n'existe pas en réel ; tous les logiciels recourent au calcul.

### Scripts avec tradition bold ET italique

| Famille Unicode | Bold réel | Italic réel | B+I réel | Comportement des 4 logiciels |
|---|---|---|---|---|
| Latin (Basic + Latin-1 + Latin Extended) | ✅ | ✅ | ✅ | Police dédiée si présente, sinon calcul |
| Greek (incl. Polytonic) | ✅ | ✅ | ✅ | Idem |
| Cyrillic (incl. extensions) | ✅ | ✅ | ✅ | Idem |
| Armenian | ✅ | ✅ | ✅ | Idem (italique Bolorgir traditionnel) |
| Georgian (Mkhedruli) | ✅ | ✅ | ✅ | Idem |

### Scripts avec tradition bold mais pas italique

| Famille Unicode | Bold réel | Italic réel | B+I réel | Comportement des 4 logiciels |
|---|---|---|---|---|
| Hebrew | ✅ | ❌ | ❌ | Bold = police dédiée. Italic = calcul (cisaillement) |
| Arabic / Persian / Urdu / Pashto | ✅ | ❌ | ❌ | Idem. Note : Naskh, Kufi, Thuluth sont des **styles** distincts, pas un italique |
| Devanagari | ✅ | ❌ | ❌ | Bold dédié (NotoSansDevanagari-Bold). Italic synthétisé |
| Bengali, Gurmukhi, Gujarati, Oriya, Tamil, Telugu, Kannada, Malayalam, Sinhala | ✅ | ❌ | ❌ | Idem (toutes ces écritures indic) |
| Thai | ✅ | ⚠️ | ⚠️ | Bold dédié. Quelques fontes Thai modernes incluent un italic intégré, mais ce n'est pas la norme |
| Lao | ✅ | ❌ | ❌ | Bold dédié. Italic calculé |
| Khmer | ✅ | ❌ | ❌ | Idem |
| Myanmar (Birman) | ✅ | ❌ | ❌ | Idem |
| Ethiopic (Ge'ez, Amharic, Tigrinya) | ✅ | ❌ | ❌ | Idem |
| Han (CJK Unified Ideographs) | ✅ | ❌ | ❌ | Bold via poids dédié (Heavy/Black/W7-W9). Italic synthétisé — résultat mauvais mais universellement appliqué |
| Hiragana, Katakana | ✅ | ❌ | ❌ | Cohérent avec Han pour le japonais |
| Hangul | ✅ | ❌ | ❌ | Bold via axe poids. Italic synthétisé (rare en pratique) |

### Scripts avec disponibilité partielle ou nulle

| Famille Unicode | Bold réel | Italic réel | B+I réel | Comportement des 4 logiciels |
|---|---|---|---|---|
| Syriac (Estrangela, Eastern, Western) | ⚠️ | ❌ | ❌ | Calcul dans la majorité des cas |
| Thaana (maldivien), N'Ko, Tibetan, Mongolian | ⚠️ | ❌ | ❌ | Calcul presque toujours |
| Cherokee, Canadian Aboriginal Syllabics | ⚠️ | ❌ | ❌ | Calcul |
| Adlam, Vai, Bamum, Yi, Lisu, Bopomofo | ❌ ou ⚠️ | ❌ | ❌ | Calcul |
| Tous les scripts historiques (Cuneiform, Egyptian Hieroglyphs, Linear A/B, Phoenician, Old Italic, Runic, Ogham, Avestan, Brahmi, etc.) | ❌ | ❌ | ❌ | Calcul. Visuellement souvent absurde, mais demandé par les apps quand l'utilisateur clique Bold/Italic |
| Tous les scripts minoritaires modernes sans variantes (Batak, Buginese, Cham, Buhid, Hanunoo, etc.) | ❌ | ❌ | ❌ | Calcul |

### Symboles et blocs spéciaux

| Famille Unicode | Bold réel | Italic réel | B+I réel | Comportement des 4 logiciels |
|---|---|---|---|---|
| General Punctuation, Currency, Letterlike Symbols | hérite de la fonte Latin | hérite de la fonte Latin | hérite de la fonte Latin | Police dédiée Latin |
| Mathematical Operators, Arrows, Misc Symbols | ❌ | ❌ | ❌ | Calcul si demandé (rarement utile) |
| **Mathematical Alphanumeric Symbols** (U+1D400-U+1D7FF) | n/a | n/a | n/a | **Cas spécial** : Unicode encode déjà bold (𝐀), italic (𝐴), bold-italic (𝑨), script (𝒜), fraktur (𝔄), double-struck (𝔸), monospace (𝙰) comme **codepoints distincts**. Pas de synthèse — la fonte fournit le glyphe directement |
| Music Symbols | ❌ | ❌ | ❌ | Calcul (généralement absurde) |
| Box Drawing, Block Elements | ❌ | ❌ | ❌ | Calcul (souvent inoffensif) |
| Emoji (Emoticons, Misc Symbols and Pictographs, Supplemental Symbols) | n/a | n/a | n/a | Bold/italic ignoré ou très laid (les emoji ont une couleur intrinsèque, l'embolden détruit l'image) |

## Détail par logiciel

### Firefox

- Spec : CSS Fonts Module Level 4, propriété `font-synthesis`.
- Défaut : `font-synthesis: weight style small-caps` → synthèse activée pour bold, italic, small-caps.
- Implémentation : FreeType (Linux), DirectWrite (Windows), CoreText (macOS).
- Synthèse bold = `FT_Outline_Embolden` ou équivalent plate-forme. Synthèse italic = matrice de cisaillement.
- Comportement uniforme pour tous les scripts. Aucune liste d'exceptions.
- L'auteur d'une page peut désactiver via `font-synthesis: none` (utile pour CJK soigneux).

### Chrome / Chromium

- Même spec CSS, même défaut.
- Implémentation : Skia + HarfBuzz pour le shaping.
- Comportement de synthèse identique à Firefox.

### Microsoft Word (Office 365 / 2024)

- Utilise GDI / DirectWrite via le sélecteur de polices Windows.
- "Theme fonts" séparées : Latin, Asian, Complex Scripts. Pour chacune, la variante Bold ou Italic est cherchée parmi les polices Windows installées.
- Si trouvée → police dédiée. Sinon → synthèse DirectWrite.
- **Cas notoire** : Word applique le faux italique aux caractères CJK (kanji/hanzi/hangul slantés à ~12°), comportement critiqué depuis ~2010 mais jamais corrigé. Pas de désactivation par script.
- Pour le bold CJK, Word préfère pointer vers une police dédiée si elle est installée (ex : MS Mincho → MS Mincho Bold). Sinon synthèse.

### Google Docs

- Application web, donc s'appuie sur le moteur de rendu du navigateur (Chrome ou Firefox côté utilisateur).
- Catalogue de polices : Google Fonts, qui inclut une grande partie de Noto avec ses variantes Bold et Italic là où Noto les fournit upstream.
- Pour bold/italic : sélectionne d'abord la variante Google Font appropriée (ex : `Noto Sans Bold`). Sinon le navigateur synthétise.
- Mêmes limites que les navigateurs : synthèse appliquée pour CJK italique sans distinction.

## Implications pour videre

### 1. Synthèse non négociable

videre doit supporter le maximum d'Unicode (texte de document via `TextInput`, pas juste l'UI). Refuser la synthèse pour les scripts sans variante Bold/Italic réelle reviendrait à offrir une expérience moins riche que les quatre références. Quand l'utilisateur appuie sur Bold dans un éditeur de document, le texte doit changer d'apparence, indépendamment de l'écriture.

Conclusion : **synthétiser quand pas de fichier réel disponible**. Aucun des quatre logiciels de référence ne fait autrement.

### 2. Pas de différenciation par script

Aucun des quatre n'a de logique "ne pas synthétiser pour CJK". Implémenter une telle logique dans videre serait un écart par rapport au standard, demanderait une table de scripts à entretenir, et briserait l'attente utilisateur.

Conclusion : **synthèse uniforme**, sans distinction par script.

### 3. Préférer la police dédiée quand elle existe

Pour les scripts où Noto fournit Bold (et parfois Italic), charger le vrai fichier produit un meilleur rendu et des métriques précises sans réplication d'algorithme. Ça concerne principalement :

- NotoSans Latin/Greek/Cyrillic : Bold + Italic + BoldItalic.
- ~25-30 scripts non-latins majeurs : Bold seul.
- 5 polices CJK variables : Bold via axe poids.

Le `FontProvider` doit donc, à terme, savoir résoudre `(char, strong, italic)` → fichier de police le plus précis disponible. Quand le fichier dédié existe, on n'envoie plus `strong=True` à pygame ; quand il n'existe pas, on envoie `strong=True` et pygame synthétise.

### 4. Architecture cohérente avec ce standard

L'architecture cible :

```
DrawerFont(path, strong, italic)
   │
   ├─ Si path pointe vers fichier dédié (NotoSans-Bold.ttf) :
   │     strong=False, italic=False (déjà baked in)
   │     → métriques fontTools sur le fichier
   │     → rendu pygame sans pf.strong/pf.oblique
   │
   └─ Si path pointe vers Regular avec strong=True ou italic=True :
         → synthèse nécessaire
         → métriques via pygame.freetype.get_rect/get_metrics avec pf.strong=True/pf.oblique=True
         → rendu pygame avec mêmes pf.strong/pf.oblique
         → cohérence garantie (même moteur des deux côtés)
```

Le code complexe avec `ctypes` + `FT_Outline_Embolden` du WIP actuel devient inutile : pour les cas où la synthèse s'applique, on délègue à pygame.freetype qui est l'oracle de ses propres pixels.

## Limites de cette enquête

- Données collectées sur la base de connaissances générales des spécifications CSS Fonts L4, du comportement documenté des navigateurs, et de la pratique typographique courante en mai 2026.
- Les détails fins (versions exactes, exceptions ponctuelles) peuvent varier ; les tendances générales sont robustes.
- Les producteurs de polices évoluent : Noto ajoute régulièrement des variantes pour des écritures qui n'en avaient pas. Une réévaluation périodique du tableau de disponibilité Bold/Italic est utile.
