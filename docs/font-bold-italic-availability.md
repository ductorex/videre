# Disponibilité Bold/Italic upstream pour les polices videre

> Mise à jour 2026-06-19 : inventaire resynchronisé sur les **188 fichiers /
> 178 familles** réellement présents (l'inventaire précédent en listait
> 172/171). Pour la liste de référence des fichiers et de leurs URLs, c'est
> `videre/fonts/SOURCES.md` qui fait foi ; ce document se concentre sur la
> *disponibilité des variantes Bold/Italic en amont*.

Inventaire des 188 fichiers de police actuellement présents dans le dépôt videre (178 familles distinctes), avec pour chaque famille la liste des variantes Bold, Italic et BoldItalic disponibles en amont. Sert de base de décision pour télécharger les vraies variantes là où elles existent et synthétiser le reste.

## Synthèse

- **Total inventorié** : 188 fichiers (178 familles distinctes). Toutes les familles sont livrées en Regular mono-graisse, sauf les 5 familles CJK livrées en triple — VF à axe poids **plus** statiques Light et Regular (cf. section CJK ci-dessous).
- **Set complet (Bold + Italic + BoldItalic) en amont** : **1 famille** (NotoSans uniquement).
- **Bold seul disponible** : **51 familles** (49 chez Noto + NotoSansMono + 1 chez Google `ofl/notoemoji` via VF à axe poids).
- **Italic seul disponible** : **0 famille**.
- **Variable font à axe poids couvrant Bold** (équivalent fonctionnel d'un Bold) : **6 familles** (les 5 Noto Sans CJK, plus NotoEmoji disponible en VF chez `google/fonts`). ⚠️ Voir la réserve pygame.freetype dans la section CJK : l'axe de variation n'est pas exploitable à l'exécution.
- **Regular seul (pas de Bold ni Italic en amont)** : **120 familles** (dont 8 ajoutées depuis la dernière révision : NewGardiner, Plangothic P1/P2, NotoSansMendeKikakui, NotoSansNushu, NotoSansSunuwar, NotoSerifKhojki, NotoSerifTodhri).
- **BabelStoneHan** : Regular seul, pas de variantes upstream.

Décompte final par catégorie de décision :

| Catégorie | Nombre | Action recommandée |
|---|---|---|
| Set complet (B + I + BI) | 1 | Télécharger les 3 variantes |
| Bold seul (TTF statique) | 51 | Télécharger Bold ; synthétiser Italic et BoldItalic |
| Bold via VF axe poids (CJK + Emoji) | 5 + 1 | VF non exploitable sous pygame.freetype ; télécharger le statique Bold ou synthétiser ; synthétiser Italic |
| Regular seul | 120 | Synthétiser Bold, Italic et BoldItalic |

## Licences

- **Noto fonts** (toutes familles `notofonts/*` sur GitHub, y compris CJK et Emoji) : **SIL Open Font License 1.1**.
  - Texte de référence pour le hub agrégé : <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/LICENSE>
  - Texte pour Noto CJK : <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/LICENSE>
  - Texte pour NotoEmoji (variante monochrome hébergée chez `google/fonts`) : <https://raw.githubusercontent.com/google/fonts/main/ofl/notoemoji/OFL.txt>
- **BabelStoneHan** : **Arphic Public License (APL)** d'origine, autorise usage commercial, modification et redistribution sous nom différent en cas de modification.
  - Texte de référence (mirroir GNU) : <http://ftp.gnu.org/non-gnu/chinese-fonts-truetype/LICENSE>
  - Page d'accueil de la fonte : <https://www.babelstone.co.uk/Fonts/Han.html>

Toutes les polices listées ci-dessous sont donc librement redistribuables, y compris dans un projet open source ou commercial, à condition de fournir le texte de licence original.

## Sources upstream et patron d'URL

- **Hub Noto principal** (`notofonts/notofonts.github.io`) : URL brute sous la forme `https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/<Famille>/unhinted/ttf/<Fichier>.ttf`. Couvre 168 des 174 familles Noto utilisées par videre (les 6 restantes : 5 CJK via `noto-cjk` + NotoEmoji via `google/fonts`). Les 4 familles hors-Noto (BabelStoneHan, NewGardiner, Plangothic P1/P2) ont leurs propres sources.
- **Noto CJK** (`notofonts/noto-cjk`) : pour HK / JP / KR / SC / TC, videre utilise les VF **régionales** — chemin upstream `Sans/Variable/TTF/Subset/` (un fichier par région), et non le pan-CJK `Sans/Variable/TTF/`. URL brute : `https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSans<XX>-VF.ttf`. En local, ces fichiers sont sous `videre/fonts/noto-cjk-static/variable-fonts/`.
- **NotoEmoji monochrome** : pas dans `googlefonts/noto-emoji` (qui ne contient que la version couleur). La version monochrome utilisée par videre est hébergée dans `google/fonts` à `ofl/notoemoji/NotoEmoji[wght].ttf` (variable font, axe `wght` 300-900).
- **BabelStoneHan** : <https://www.babelstone.co.uk/Download/BabelStoneHan.ttf>.

## Polices avec Bold + Italic + BoldItalic disponibles

Une seule famille dans tout l'inventaire fournit le set complet en amont :

| Famille | Fichier actuel videre | URL Bold | URL Italic | URL BoldItalic |
|---|---|---|---|---|
| NotoSans | NotoSans-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSans/unhinted/ttf/NotoSans-Bold.ttf> | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSans/unhinted/ttf/NotoSans-Italic.ttf> | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSans/unhinted/ttf/NotoSans-BoldItalic.ttf> |

NotoSans couvre Latin/Greek/Cyrillic. C'est la seule famille du repo Noto agrégé qui possède un fichier `-Italic.ttf` parmi celles utilisées par videre. Trois autres familles Noto (NotoSerif, NotoSerifDisplay, NotoSerifTamil) ont aussi un Italic upstream mais elles **ne sont pas** dans videre, donc sans impact.

## Polices avec Bold seul disponible (TTF statique)

51 familles fournissent un fichier `-Bold.ttf` mais pas d'Italic. Elles correspondent quasi-systématiquement aux scripts vivants à forte adoption (indic, sémitiques, sud-est asiatique, africains majeurs) ainsi qu'à NotoSansMono.

| Famille | Fichier actuel videre | URL Bold |
|---|---|---|
| NotoNastaliqUrdu | NotoNastaliqUrdu-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoNastaliqUrdu/unhinted/ttf/NotoNastaliqUrdu-Bold.ttf> |
| NotoSansAdlam | NotoSansAdlam-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansAdlam/unhinted/ttf/NotoSansAdlam-Bold.ttf> |
| NotoSansArabic | NotoSansArabic-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansArabic/unhinted/ttf/NotoSansArabic-Bold.ttf> |
| NotoSansArmenian | NotoSansArmenian-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansArmenian/unhinted/ttf/NotoSansArmenian-Bold.ttf> |
| NotoSansBalinese | NotoSansBalinese-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBalinese/unhinted/ttf/NotoSansBalinese-Bold.ttf> |
| NotoSansBamum | NotoSansBamum-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBamum/unhinted/ttf/NotoSansBamum-Bold.ttf> |
| NotoSansBassaVah | NotoSansBassaVah-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBassaVah/unhinted/ttf/NotoSansBassaVah-Bold.ttf> |
| NotoSansBengali | NotoSansBengali-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBengali/unhinted/ttf/NotoSansBengali-Bold.ttf> |
| NotoSansCanadianAboriginal | NotoSansCanadianAboriginal-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCanadianAboriginal/unhinted/ttf/NotoSansCanadianAboriginal-Bold.ttf> |
| NotoSansCham | NotoSansCham-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCham/unhinted/ttf/NotoSansCham-Bold.ttf> |
| NotoSansCherokee | NotoSansCherokee-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCherokee/unhinted/ttf/NotoSansCherokee-Bold.ttf> |
| NotoSansDevanagari | NotoSansDevanagari-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansDevanagari/unhinted/ttf/NotoSansDevanagari-Bold.ttf> |
| NotoSansDuployan | NotoSansDuployan-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansDuployan/unhinted/ttf/NotoSansDuployan-Bold.ttf> |
| NotoSansEthiopic | NotoSansEthiopic-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansEthiopic/unhinted/ttf/NotoSansEthiopic-Bold.ttf> |
| NotoSansGeorgian | NotoSansGeorgian-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGeorgian/unhinted/ttf/NotoSansGeorgian-Bold.ttf> |
| NotoSansGujarati | NotoSansGujarati-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGujarati/unhinted/ttf/NotoSansGujarati-Bold.ttf> |
| NotoSansGunjalaGondi | NotoSansGunjalaGondi-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGunjalaGondi/unhinted/ttf/NotoSansGunjalaGondi-Bold.ttf> |
| NotoSansGurmukhi | NotoSansGurmukhi-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGurmukhi/unhinted/ttf/NotoSansGurmukhi-Bold.ttf> |
| NotoSansHanifiRohingya | NotoSansHanifiRohingya-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansHanifiRohingya/unhinted/ttf/NotoSansHanifiRohingya-Bold.ttf> |
| NotoSansHebrew | NotoSansHebrew-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansHebrew/unhinted/ttf/NotoSansHebrew-Bold.ttf> |
| NotoSansJavanese | NotoSansJavanese-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansJavanese/unhinted/ttf/NotoSansJavanese-Bold.ttf> |
| NotoSansKannada | NotoSansKannada-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKannada/unhinted/ttf/NotoSansKannada-Bold.ttf> |
| NotoSansKawi | NotoSansKawi-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKawi/unhinted/ttf/NotoSansKawi-Bold.ttf> |
| NotoSansKayahLi | NotoSansKayahLi-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKayahLi/unhinted/ttf/NotoSansKayahLi-Bold.ttf> |
| NotoSansKhmer | NotoSansKhmer-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKhmer/unhinted/ttf/NotoSansKhmer-Bold.ttf> |
| NotoSansLao | NotoSansLao-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansLao/unhinted/ttf/NotoSansLao-Bold.ttf> |
| NotoSansLisu | NotoSansLisu-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansLisu/unhinted/ttf/NotoSansLisu-Bold.ttf> |
| NotoSansMalayalam | NotoSansMalayalam-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMalayalam/unhinted/ttf/NotoSansMalayalam-Bold.ttf> |
| NotoSansMedefaidrin | NotoSansMedefaidrin-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMedefaidrin/unhinted/ttf/NotoSansMedefaidrin-Bold.ttf> |
| NotoSansMeeteiMayek | NotoSansMeeteiMayek-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMeeteiMayek/unhinted/ttf/NotoSansMeeteiMayek-Bold.ttf> |
| NotoSansMyanmar | NotoSansMyanmar-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMyanmar/unhinted/ttf/NotoSansMyanmar-Bold.ttf> |
| NotoSansNagMundari | NotoSansNagMundari-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansNagMundari/unhinted/ttf/NotoSansNagMundari-Bold.ttf> |
| NotoSansNewTaiLue | NotoSansNewTaiLue-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansNewTaiLue/unhinted/ttf/NotoSansNewTaiLue-Bold.ttf> |
| NotoSansOlChiki | NotoSansOlChiki-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOlChiki/unhinted/ttf/NotoSansOlChiki-Bold.ttf> |
| NotoSansOriya | NotoSansOriya-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOriya/unhinted/ttf/NotoSansOriya-Bold.ttf> |
| NotoSansSinhala | NotoSansSinhala-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSinhala/unhinted/ttf/NotoSansSinhala-Bold.ttf> |
| NotoSansSoraSompeng | NotoSansSoraSompeng-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSoraSompeng/unhinted/ttf/NotoSansSoraSompeng-Bold.ttf> |
| NotoSansSundanese | NotoSansSundanese-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSundanese/unhinted/ttf/NotoSansSundanese-Bold.ttf> |
| NotoSansSymbols | NotoSansSymbols-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSymbols/unhinted/ttf/NotoSansSymbols-Bold.ttf> |
| NotoSansTaiTham | NotoSansTaiTham-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTaiTham/unhinted/ttf/NotoSansTaiTham-Bold.ttf> |
| NotoSansTamil | NotoSansTamil-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTamil/unhinted/ttf/NotoSansTamil-Bold.ttf> |
| NotoSansTangsa | NotoSansTangsa-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTangsa/unhinted/ttf/NotoSansTangsa-Bold.ttf> |
| NotoSansTelugu | NotoSansTelugu-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTelugu/unhinted/ttf/NotoSansTelugu-Bold.ttf> |
| NotoSansThaana | NotoSansThaana-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansThaana/unhinted/ttf/NotoSansThaana-Bold.ttf> |
| NotoSansThaiLooped | NotoSansThaiLooped-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansThaiLooped/unhinted/ttf/NotoSansThaiLooped-Bold.ttf> |
| NotoSansVithkuqi | NotoSansVithkuqi-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansVithkuqi/unhinted/ttf/NotoSansVithkuqi-Bold.ttf> |
| NotoSansMono | NotoSansMono-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMono/unhinted/ttf/NotoSansMono-Bold.ttf> |
| NotoSerifNPHmong | NotoSerifNPHmong-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifNPHmong/unhinted/ttf/NotoSerifNPHmong-Bold.ttf> |
| NotoSerifTibetan | NotoSerifTibetan-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifTibetan/unhinted/ttf/NotoSerifTibetan-Bold.ttf> |
| NotoSerifToto | NotoSerifToto-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifToto/unhinted/ttf/NotoSerifToto-Bold.ttf> |
| NotoSerifYezidi | NotoSerifYezidi-Regular.ttf | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifYezidi/unhinted/ttf/NotoSerifYezidi-Bold.ttf> |

Note : pour chacune de ces familles, le fichier `-Italic.ttf` et `-BoldItalic.ttf` n'existe **pas** en amont. Italic et BoldItalic doivent donc être synthétisés (cisaillement par pygame.freetype). Beaucoup de ces familles disposent aussi d'un fichier variable `<Famille>[wght].ttf` qui couvre Bold via l'axe de poids, alternative possible si videre adopte les variable fonts.

## Polices avec Italic seul disponible

Aucune. Sur les 178 familles videre, aucune ne fournit un Italic upstream sans Bold. Pour les rares familles Noto qui ont un Italic en amont (NotoSerif, NotoSerifDisplay, NotoSerifTamil), elles ne sont pas utilisées par videre.

## Polices avec variable font à axe poids couvrant Bold

Les 5 sous-ensembles Noto Sans CJK sont livrés en VF dans videre, ainsi que NotoEmoji disponible en VF chez `google/fonts`. L'axe `wght` couvre au moins 100 → 900, ce qui *en théorie* inclut le Bold (700). Pas d'axe italique : Italic et BoldItalic doivent être synthétisés.

**⚠️ Réserve pygame.freetype** : le moteur de rendu actuel ne supporte pas les axes de variation OpenType — une VF est rendue à sa valeur par défaut (`wght=100`, Thin), inutilisable. C'est pourquoi videre charge en réalité des **instances statiques** pour le CJK (cf. `SOURCES.md`, sources 2 et 2bis) : la statique **Light** (`wght=300`) est chargée et prioritaire pour les blocs CJK courants ; la statique **Regular** est conservée sur disque mais **non chargée** (collision de `full name` avec la VF + rendu trop gras). Conséquence : un **vrai Bold CJK n'est pas disponible** via les fichiers chargés ; il faudrait télécharger la statique Bold (`Sans/SubsetOTF/<LANG>/NotoSans<LANG>-Bold.otf`) ou instancier la VF à 700 (impossible sous pygame.freetype aujourd'hui).

| Famille | Fichier actuel videre | URL VF (axe poids) |
|---|---|---|
| NotoSansHK | NotoSansHK-VF.ttf | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansHK-VF.ttf> |
| NotoSansJP | NotoSansJP-VF.ttf | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansJP-VF.ttf> |
| NotoSansKR | NotoSansKR-VF.ttf | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansKR-VF.ttf> |
| NotoSansSC | NotoSansSC-VF.ttf | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansSC-VF.ttf> |
| NotoSansTC | NotoSansTC-VF.ttf | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansTC-VF.ttf> |
| NotoEmoji | NotoEmoji-Regular.ttf | <https://raw.githubusercontent.com/google/fonts/main/ofl/notoemoji/NotoEmoji%5Bwght%5D.ttf> |

NotoEmoji actuellement en TTF statique Regular (300-Light dans la nomenclature Google Fonts) ; pour récupérer un Bold dédié, il faut soit télécharger le VF et instancier à 700, soit télécharger le statique Bold ; la version "static TTF Bold" est aussi disponible via `https://github.com/google/fonts/tree/main/ofl/notoemoji/static/NotoEmoji-Bold.ttf` (à confirmer si on bascule vers les statiques).

## Polices Regular only

120 familles : pas de Bold ni d'Italic en amont. Bold et Italic devront être synthétisés systématiquement par pygame.freetype.

> Les 8 familles ajoutées depuis la dernière révision sont intégrées ci-dessous. Les 3 hors-Noto (NewGardiner, Plangothic P1/P2) sont nativement mono-graisse. Les 5 Noto (MendeKikakui, Nushu, Sunuwar, NotoSerifKhojki, NotoSerifTodhri) sont **présumées Regular-only** — aucune variante Bold/Italic connue en amont, ce qui est cohérent avec tous les scripts rares comparables, mais à confirmer auprès de `notofonts` avant un éventuel téléchargement.

Groupées par grande catégorie :

### Scripts historiques et anciens (zéro variante upstream)

NotoSansAnatolianHieroglyphs, NotoSansAvestan, NotoSansBrahmi, NotoSansCarian, NotoSansCaucasianAlbanian, NotoSansChorasmian, NotoSansCoptic, NotoSansCuneiform, NotoSansCypriot, NotoSansCyproMinoan, NotoSansDeseret, NotoSansEgyptianHieroglyphs, NotoSansElbasan, NotoSansElymaic, NotoSansGlagolitic, NotoSansGothic, NotoSansGrantha, NotoSansHatran, NotoSansImperialAramaic, NotoSansInscriptionalPahlavi, NotoSansInscriptionalParthian, NotoSansKaithi, NotoSansKharoshthi, NotoSansKhojki, NotoSansKhudawadi, NotoSansLinearA, NotoSansLinearB, NotoSansLycian, NotoSansLydian, NotoSansMahajani, NotoSansManichaean, NotoSansMarchen, NotoSansMasaramGondi, NotoSansMeroitic, NotoSansModi, NotoSansMultani, NotoSansNabataean, NotoSansNandinagari, NotoSansNewa, NotoSansNushu, NotoSansOgham, NotoSansOldHungarian, NotoSansOldItalic, NotoSansOldNorthArabian, NotoSansOldPermic, NotoSansOldPersian, NotoSansOldSogdian, NotoSansOldSouthArabian, NotoSansOldTurkic, NotoSansOsmanya, NotoSansPahawhHmong, NotoSansPalmyrene, NotoSansPauCinHau, NotoSansPhagsPa, NotoSansPhoenician, NotoSansPsalterPahlavi, NotoSansRunic, NotoSansSamaritan, NotoSansSharada, NotoSansShavian, NotoSansSiddham, NotoSansSogdian, NotoSansSoyombo, NotoSansTagalog, NotoSansTagbanwa, NotoSansTakri, NotoSansTirhuta, NotoSansUgaritic, NotoSansWarangCiti, NotoSansZanabazarSquare, NotoSerifAhom, NotoSerifKhojki, NotoSerifMakasar, NotoSerifOldUyghur, NotoSerifOttomanSiyaq, NotoSerifTangut, NotoSerifTodhri.

### Scripts minoritaires modernes (zéro variante upstream)

NotoSansBatak, NotoSansBhaiksuki, NotoSansBuginese, NotoSansBuhid, NotoSansChakma, NotoSansHanunoo, NotoSansLepcha, NotoSansLimbu, NotoSansMandaic, NotoSansMendeKikakui, NotoSansMiao, NotoSansMongolian, NotoSansMro, NotoSansNKo, NotoSansRejang, NotoSansSaurashtra, NotoSansSignWriting, NotoSansSylotiNagri, NotoSansSyriac, NotoSansSyriacEastern, NotoSansSyriacWestern, NotoSansTaiLe, NotoSansTaiViet, NotoSansTifinagh, NotoSansVai, NotoSansWancho, NotoSansYi, NotoSerifDogra.

### Scripts récents ou en cours d'enrichissement

NotoSansOsage, NotoSansSunuwar, NotoSansTamilSupplement, NotoSansTest (police de test), NotoSansIndicSiyaqNumbers, NotoSansMayanNumerals.

### Symboles, math, musique, divers

NotoSansMath, NotoSansSymbols2, NotoMusic, NotoZnamennyMusicalNotation, NotoFangsongKSSVertical.

### Cas hors-Noto

- **BabelStoneHan** : un seul fichier monolithique de 49,5 Mo couvrant ~64 000 caractères CJK, pas de variante.
- **NewGardiner** : fonte académique pour les hiéroglyphes égyptiens (OFL 1.1), mono-graisse, pas de variante Bold/Italic en amont.
- **Plangothic P1 / P2** : projet Plangothic (couverture CJK des plans étendus, U+20000+), mono-graisse, pas de variante en amont.

## Notes par famille particulière

- **NotoSans (Latin/Greek/Cyrillic)** : seul cas où télécharger les 3 variantes apporte un gain sans ambiguïté. Couvre la quasi-totalité du texte d'interface et de document Western. Les variantes Italic et BoldItalic existent aussi dans des sous-axes (Condensed, ExtraLight, etc.) mais videre n'utilise actuellement que les axes principaux.
- **NotoSansCJK (HK/JP/KR/SC/TC)** : présentes en VF **et** en statiques OTF (Light + Regular) dans videre. ⚠️ `pygame.freetype` n'instancie pas les axes de variation : la VF rend en Thin (`wght=100`) et n'est donc **pas** chargée — c'est la statique **Light** (`wght=300`) qui est chargée et prioritaire pour le CJK, la statique **Regular** étant conservée mais non chargée (collision de `full name` avec la VF + rendu ~1,5× trop gras). Pour un "vrai Bold", il faut donc télécharger la statique Bold (`Sans/SubsetOTF/<LANG>/NotoSans<LANG>-Bold.otf`), l'instanciation de la VF à 700 n'étant pas possible sous pygame.freetype. Pas d'axe italique. Ces cinq familles sont les versions **régionales** de Noto Sans CJK (une par langue : HK/JP/KR/SC/TC), et non le fichier pan-CJK unique : côté upstream elles proviennent du dossier `Subset/` du dépôt `notofonts/noto-cjk`, mais en local elles sont rangées sous `videre/fonts/noto-cjk-static/` — il n'existe aucun dossier `Subset/` dans le dépôt videre.
- **NotoEmoji** : seul cas où le fichier vient de `google/fonts` plutôt que de `notofonts/*`. Le repo `googlefonts/noto-emoji` ne contient que la version **couleur** (NotoColorEmoji.ttf) ; la version monochrome utilisée par videre (`NotoEmoji-Regular.ttf`) est répliquée dans Google Fonts à `ofl/notoemoji/`. Variante VF (`NotoEmoji[wght].ttf`) couvre Light->Black ; pas d'axe italique. Italique sur emoji n'a pas de sens typographique.
- **NotoSansMono** : Bold disponible (et même Black, Condensed, etc.) mais pas d'Italic. Standard pour les fontes monospace : la version "italique" est rare, parfois remplacée par une oblique synthétique.
- **NotoSansSymbols vs NotoSansSymbols2** : Symbols a un Bold, Symbols2 non. C'est cohérent avec la mission : Symbols couvre les symboles courants (flèches, ponctuation étendue) où le Bold sert à harmoniser avec NotoSans Bold ; Symbols2 couvre les symboles techniques rares où Bold n'est jamais demandé.
- **NotoNastaliqUrdu** : seule fonte Nastaliq de Noto. Bold disponible, pas d'Italic (le Nastaliq est intrinsèquement calligraphique, l'italique n'a pas de sens). Note : Noto a aussi `NotoNaskhArabic` avec Bold mais il n'est pas dans videre car `NotoSansArabic` couvre déjà Naskh.
- **NotoSansThaiLooped** : variante "loopée" du thaï. videre n'embarque pas `NotoSansThai` standard, donc le bold thaï passe par cette variante. Bold disponible.
- **NotoSerifTibetan vs NotoSansTibetan** : videre n'a que la version Serif. Les deux sont disponibles upstream avec Bold. Si videre veut homogénéiser le rendu sans empattement avec le reste, il faudrait basculer sur NotoSansTibetan (mais ce n'est pas le sujet de ce rapport).
- **NotoSansFangsongKSS** : style fangsong (calligraphique chinois) pour le coréen, sous-utilisé. Une seule variante upstream, c'est conforme à la rareté de la fonte.
- **Familles avec variable font à axe poids mais pas dans la liste "VF dans videre"** : beaucoup de familles `Bold seul` (NotoSansBalinese, NotoSansArabic, NotoSansLisu, NotoSansBengali, etc.) ont aussi un fichier `<Famille>[wght].ttf` upstream qui couvrirait l'axe poids. Si videre adopte plus tard les variable fonts pour ces familles, il pourrait remplacer Regular + Bold statique par un seul VF.
- **BabelStoneHan** : ne pas confondre avec NotoSansCJK. BabelStoneHan a une couverture caractères beaucoup plus large (caractères rares, variantes historiques, sinogrammes vietnamiens chữ Nôm, écritures dérivées Tangut/Khitan) mais pas de Bold ni d'Italic.

## Décisions à prendre

1. **NotoSans** : télécharger Bold + Italic + BoldItalic. Gain net pour le texte Latin/Greek/Cyrillic, qui est le cas le plus fréquent.
2. **51 familles avec Bold seul** : choix entre (a) télécharger le Bold statique pour chacune (~ 51 fichiers supplémentaires, gain visible sur indic et arabe principalement) ou (b) maintenir la synthèse universelle. Une approche intermédiaire serait de cibler les familles fréquemment utilisées (Arabic, Hebrew, Devanagari, Bengali, Tamil, Thai-looped, Khmer, Myanmar, Ethiopic, CJK) et synthétiser pour le reste.
3. **CJK + NotoEmoji en VF** : l'instanciation de VF n'est **pas** exploitable sous pygame.freetype (rendu Thin) ; le contournement actuel charge des statiques Light. Pour un Bold CJK réel, télécharger les statiques Bold (`Sans/SubsetOTF/<LANG>/…-Bold.otf`) plutôt que de compter sur l'axe de variation.
4. **Regular only (120 familles)** : aucune action, synthèse universelle conforme aux 4 logiciels de référence (cf. `bold-italic-synthesis-survey.md`).
