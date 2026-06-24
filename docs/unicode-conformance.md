# Conformité Unicode — `videre/core/text_rendering` + `videre/fonts`

> Audit du 2026-06-16. Mesures issues d'une lecture exhaustive du code et de
> calculs exécutés contre la collection de polices embarquée (178 fontes
> analysées sur 188 fichiers présents — les 5 VF CJK et leurs 5 statiques
> Regular sont redondantes en couverture avec les statiques Light retenues).
> Outils sous-jacents : `unicodedataplus` 16.0.0 (source unique des propriétés
> via `core/textual/unicode_props.py`), `fontTools.unicodedata` (nomenclature ISO de
> script uniquement), `uharfbuzz` 0.54.1 (HarfBuzz 14.2.0).
>
> Mise à jour 2026-06-16 (a) : ajout de la fonte **NewGardiner** (OFL 1.1)
> couvrant les hiéroglyphes égyptiens (base + format controls + Extended-A) —
> couverture des caractères passée de 97,36 % à **99,58 %**.
> Mise à jour 2026-06-16 (b) : unification sur **Unicode 16.0 partout** via
> `core/textual/unicode_props.py` (fin de la dualité 16.0/15.1) — 5 191 classes bidi et
> 5 185 catégories de caractères 16.0 corrigées.

## 0. Résumé

Il n'existe **pas un seul** « taux de conformité » : la norme se décompose en
algorithmes (UAX/UTS), en couverture de caractères et en couverture de
séquences. Bilan par dimension :

| Dimension | Conformité | Version Unicode |
|---|---|---|
| UAX#29 — frontières de graphèmes (GB1–GB999) | **100 % des règles** | 16.0 |
| UAX#29 — frontières de mots (WB1–WB999) | **100 % des règles** | 16.0 |
| UAX#9 — bidi (niveaux + réordonnancement) | **100 % du calcul** (L1/L3/L4 délégués) | 16.0 |
| UAX#24 — runs de script | **Partiel** (pas de Script_Extensions) | 16.0 |
| UAX#14 — coupure de ligne | **Profil maison** (pas LB1–LB31) | 16.0 (classes) |
| UAX#29 — frontières de phrases (SB) | **Absent** (hors périmètre rendu) | — |
| UAX#11 — largeur est-asiatique | **Absent** (hors périmètre) | — |
| UAX#15 — normalisation (NF*) | **Absent** (délégué à GSUB) | — |
| Couverture des caractères (glyphes autonomes) | **99,58 %** (153 936 / 154 591) | 16.0 |
| Séquences de variation emoji | **100 %** (742 / 742) | 16.0 |
| Séquences de variation standardisées | **89,4 %** (1 167 / 1 306) | 16.0 |
| Séquences de variation idéographiques (IVD) | **50,3 %** (14 897 / 29 635) | IVD 2025-07-14 |
| Séquences emoji | **100 %** (1 136 / 1 136) | 16.0 |
| Séquences emoji ZWJ | **100 %** (1 468 / 1 468) | 16.0 |
| Validation de shaping (absence de `.notdef`) | **100 %** (0 manquant / 153 936) | 16.0 |

## 1. Versions Unicode — unifiées sur 16.0

Toutes les propriétés Unicode *versionnées* passent désormais par
`videre/core/textual/unicode_props.py`, qui fait de **`unicodedataplus` (16.0)** la
source unique : `category`, `bidirectional`, `decomposition`, `block`, et le
`script` (nom long 16.0 converti en code ISO 15924 via `fontTools.script_code`,
pure nomenclature non versionnée). `fontTools.unicodedata` ne sert plus qu'à deux
services *stables par version* : la nomenclature ISO (`script_code`) et la
direction de script (`script_horizontal_direction`, à jour pour les scripts 16.0
comme Garay → RTL). La stdlib `unicodedata` n'est plus utilisée pour les
propriétés.

Le module `unicode_props` asserte la version attendue (`16.0.0`) à l'import : un
bump de dépendance qui la changerait échoue bruyamment au lieu de mélanger
silencieusement deux versions. Les fichiers de données bundlés
(`vibidi/BidiBrackets.txt`, `tests/vibidi/data/BidiCharacterTest.txt`) sont en
16.0, et les gardes de version des tests comparent à
`unicode_props.UNICODE_VERSION`.

**Bénéfice de la migration** (depuis l'ancienne dualité 16.0/15.1) : 5 191
classes bidi et 5 185 catégories de caractères ajoutés en 16.0 — que la stdlib
15.1 voyait comme « inconnus » — sont désormais correctes. Le routage de fonte
est inchangé : le code ISO du script est identique entre `unicodedataplus` 16.0
et l'ancienne table `fontTools` 15.1 (0 divergence mesurée sur les 154 591
codepoints du profil).

## 2. Algorithmes Unicode (UAX/UTS)

### 2.1 UAX#29 — Graphèmes : ✅ complet (Unicode 16.0)

`text_editing.grapheme_boundaries` (`text_editing.py:103`) implémente **toutes**
les règles : GB1/GB2 (bords), GB3 (CR×LF), GB4/GB5 (Control), GB6/GB7/GB8
(Hangul), GB9 (Extend/ZWJ), GB9a (SpacingMark), GB9b (Prepend), **GB9c**
(conjonctions indiennes), **GB11** (séquences emoji ZWJ), GB12/GB13 (indicateurs
régionaux), GB999. C'est la granularité d'édition partagée (`EditUnit`).

### 2.2 UAX#29 — Mots : ✅ complet (Unicode 16.0)

`word_splitter.word_boundaries` (`word_splitter.py:91`) implémente WB1–WB16 :
WB3/3a/3b/3c/3d, WB4 (ignorables), WB5–WB13b, WB15/WB16 (indicateurs régionaux).
Formulation « Replacing Ignore Rules » (UAX#29 §6.2). Utilisé pour la
segmentation en mots/gaps, **pas** pour la coupure de ligne.

### 2.3 UAX#9 — Bidi : ✅ calcul complet, rendu délégué (Unicode 16.0)

`vibidi/vibidi.py` (implémentation maison, validée contre
`BidiCharacterTest.txt` 16.0) couvre toute la chaîne de calcul :

| Groupe | Statut | Emplacement |
|---|---|---|
| P2/P3 (direction de base) | ✅ | `_base_level` |
| X1–X8 (embeddings/overrides/isolates) | ✅ | `_resolve_explicit` (profondeur max 125, overflow géré) |
| X9 (suppression), X10 (run sequences) | ✅ | `_isolating_run_sequences` |
| W1–W7 (types faibles) | ✅ | `_resolve_weak` |
| N0 (crochets appariés) | ✅ | `_resolve_brackets` (pile BD16=63, `BidiBrackets.txt` 16.0) |
| N1–N2 (neutres) | ✅ | `_resolve_neutral` |
| I1–I2 (niveaux implicites) | ✅ | `_resolve_implicit` |
| **L2** (réordonnancement) | ✅ | `_l2_order` |
| **L1** (reset espaces/séparateurs) | ❌ **délégué** | logique de wrap de videre (réinitialise les espaces de tête) |
| **L3** (marques combinées) | ❌ **délégué** | HarfBuzz (shaping) |
| **L4** (miroir) | ❌ **délégué** | HarfBuzz (shaping, `direction=rtl`) |

L1/L3/L4 sont des étapes *de présentation*, correctement déléguées au shaper et
au moteur de wrap — la chaîne reste fonctionnellement conforme. (Le bug des
crochets RTL de `python-bidi`, qui n'avait pas N0, est ici corrigé.)

### 2.4 UAX#24 — Script : ⚠️ partiel

`partition_utils._split_by_script` (`partition_utils.py:25`) découpe en runs de
script avec résolution Common/Inherited (un neutre hérite du script voisin).
**Manque** : les **Script_Extensions** (`scx`) — un caractère partagé par
plusieurs scripts est rattaché à son script primaire seul, ce qui peut mal router
la fonte pour certains caractères partagés (ponctuation, chiffres).

### 2.5 UAX#14 — Coupure de ligne : ⚠️ profil maison, pas l'algorithme

`word_splitter` n'implémente **pas** les règles LB1–LB31. Il applique un *profil*
orienté rendu (`word_splitter.py:283` `_classify_span`) qui réutilise les
*classes* de ligne UAX#14 (BREAKABLE/TRAILING/LEADING/…) pour : coalescer le
CJK/Hangul, attacher la ponctuation, choisir le côté des guillemets. La coupure
fine est ensuite faite par grappe (cluster) dans `rendering/wrap.py`.

**Non pris en charge** explicitement :
- **Trait d'union conditionnel** (U+00AD, soft hyphen) — classé
  `EditUnitKind.SOFT_HYPHEN` (`text_editing.py:256`) mais **non câblé** : WB4
  l'absorbe (`Word_Break=Format`) avant que son `Line_Break=BA` ne s'applique
  (`word_splitter.py:17`). Documenté comme lacune connue.

### 2.6 Absents (hors périmètre d'un moteur basé glyphes)

- **UAX#29 Phrases (SB)** — non implémenté.
- **UAX#11 Largeur est-asiatique** — non utilisé ; la mise en page emploie les
  *advances* réels des glyphes, pas la largeur EAW.
- **UAX#15 Normalisation (NFC/NFD/NFKC/NFKD)** — aucune normalisation ; le texte
  est shapé tel quel et la composition/décomposition est laissée à HarfBuzz/GSUB.
  Conséquence : NFC et NFD d'un même texte peuvent produire des grappes
  différentes (généralement sans incidence visuelle).
- **Miroir / jointures arabes / ligatures / kerning** — délégués à HarfBuzz
  (GSUB/GPOS), donc conformes à la version de HarfBuzz (14.2.0), pas à une règle
  réimplémentée ici.

## 3. Couverture des caractères

Profil de référence : `coverage.requires_standalone_glyph` — codepoints de
`[0, 0x110000)` hors `{Cc, Cs, Co, Cn, Zl, Zp}` et hors Default_Ignorable
(Unicode 16.0). Les zones à usage privé (PUA) sont **délibérément** exclues.

| Mesure | Valeur |
|---|---|
| Codepoints requis (N_REQUIS) | **154 591** |
| Codepoints couverts par ≥1 fonte | **153 936** |
| **Taux de couverture** | **99,58 %** |
| Codepoints **non couverts** | **655** |
| Scripts dans le profil | 170 |
| Scripts entièrement couverts | **167** |
| Fontes analysées (sur 188 fichiers embarqués) | 178 |

### Ce qui n'est PAS pris en charge (655 codepoints)

| Plage | Taille | Script | Bloc |
|---|---|---|---|
| Signes « non-core » | **568** | Egyp | Egyptian Hieroglyphs Extended-A |
| U+11380–U+113FF | **80** | Tutg | **Tulu-Tigalari** (Unicode 16.0) |
| (7 codepoints épars) | **7** | Zyyy | Symbols and Pictographs Extended-A |

- **Hiéroglyphes égyptiens** : depuis l'ajout de **NewGardiner** (OFL 1.1, voir
  `SOURCES.md` source 6), le bloc de base (U+13000–U+1342F), les contrôles de
  format de quadrats (U+13430–U+1343F) et 3 427 des 3 995 signes de l'extension A
  sont couverts. Restent 568 signes « non-core » absents de la fonte.
- **Tulu-Tigalari** (80) : script **ajouté en Unicode 16.0** ; aucune fonte libre
  n'existe encore (ni Noto, ni académique). C'est le **seul script entièrement
  manquant**.
- **Symbols and Pictographs Extended-A** (7) : symboles récents (Unicode 16.0)
  sans glyphe dans la collection actuelle.

## 4. Couverture des séquences

Registre `unicode-sequences.json` (Unicode 16.0.0, IVD **2025-07-14**). Sources :
`StandardizedVariants.txt`, `emoji-variation-sequences.txt`, `emoji-sequences.txt`,
`emoji-zwj-sequences.txt` (16.0), registre IVD.

| Catégorie | Dans le registre | Couvert | Non couvert |
|---|---|---|---|
| Variation emoji (VS16/VS15) | 742 | **742** | **0** |
| Variation standardisée | 1 306 | 1 167 | **139** |
| Variation idéographique (IVD) | 29 635 | 14 897 | **14 738** |
| Séquence emoji | 1 136 | **1 136** | **0** |
| Séquence emoji ZWJ | 1 468 | **1 468** | **0** |

- Table de routage `sequence-to-font.json` : **19 203** séquences routées.
- Variation sequences distinctes annoncées par les fontes (cmap-14) : **17 902**.
- **IVD** : ~50 % des sélecteurs de variantes idéographiques (Adobe-Japan1,
  Hanyo-Denshi, Moji_Joho…) ne sont pas routés. **Impact faible** : le caractère
  Han de base s'affiche, seule la *forme variante exacte* demandée par le
  sélecteur n'est pas honorée.
- **Séquences emoji / ZWJ** (2 604) : **couvertes à 100 %** par NotoEmoji — la
  version **monochrome** (« Noto Emoji Regular ») qu'embarque videre, et *non* la
  version couleur. Le générateur vérifie que la police compose chaque séquence sans
  laisser de glyphe manquant : ~1 444 via un glyphe dédié unique, ~1 160 par
  superposition de plusieurs glyphes (p. ex. drapeau de base + symbole). La version
  monochrome est retenue pour que les emojis prennent la couleur du texte — une
  fonte couleur a des teintes figées dans le glyphe, qui n'en tiennent pas compte.

## 5. Validation de shaping

Le générateur (`_gen_char_cov.py`) repasse chaque codepoint couvert dans HarfBuzz
et vérifie l'absence de `.notdef` (le glyphe « non défini », c.-à-d. le *tofu*) :

- Codepoints vérifiés : **153 936**
- Échecs (glyphe manquant à l'exécution) : **0**

Autrement dit : tout ce que le profil déclare couvert se shape réellement sans
*tofu* — le carré vide ▯ affiché faute de dessin pour un caractère (le nom *Noto*
vient justement de « No Tofu »).

## 6. Conclusion consolidée — « ce qui n'est pas pris en charge »

1. **Caractères** (655) : 568 signes égyptiens « non-core » de l'Extended-A
   (NewGardiner en couvre 3 427 / 3 995), script Tulu-Tigalari (80, aucune fonte
   n'existe), 7 symboles récents. → manque de fontes, pas de bug logiciel.
2. **Variantes idéographiques IVD** (14 738, ~50 %) et **variantes standardisées**
   (139). → forme de base rendue, variante exacte non honorée.
3. **Trait d'union conditionnel** (U+00AD) : classé mais non câblé dans le wrap.
4. **Script_Extensions** (UAX#24) : non pris en compte → routage de fonte
   approximatif pour certains caractères partagés.
5. **Algorithme UAX#14 complet** : seul un profil est implémenté (pas LB1–LB31).
6. **Normalisation (UAX#15)**, **largeur est-asiatique (UAX#11)**, **frontières de
   phrases (UAX#29 SB)** : absents (hors périmètre d'un moteur de rendu).

Pour le **rendu de texte**, la conformité est **élevée** : segmentation UAX#29
intégrale (16.0), bidi UAX#9 complet (16.0) avec présentation déléguée à
HarfBuzz, et 99,58 % des caractères Unicode 16.0 rendus sans tofu. Les lacunes
sont soit du ressort des *fontes* (couverture, IVD), soit des raffinements
optionnels (soft hyphen, scx, UAX#14 complet), soit des algorithmes non
pertinents pour un moteur basé glyphes (NF*, EAW, SB).
