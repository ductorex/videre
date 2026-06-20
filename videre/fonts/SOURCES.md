# Sources et licences des polices videre

Catalogue des fichiers présents dans `videre/fonts/`, leur source upstream, et la licence applicable. Sert pour la traçabilité, le re-téléchargement, et la conformité de redistribution OFL/APL.

Pour les variantes Bold/Italic/BoldItalic disponibles upstream et non encore téléchargées, voir `docs/font-bold-italic-availability.md`.

Le dernier audit fichier par fichier des versions upstream et de leur couverture
est consigné dans `videre/fonts/FONT_UPDATE_AUDIT.md`.

## Licences présentes dans le dépôt

- `videre/fonts/LICENSE_OFL.txt` — SIL Open Font License 1.1. Couvre **toutes** les polices Noto, indépendamment du sous-dossier (`noto/sans/`, `noto/serif/`, `noto/mono/`, `noto/cjk/`).
- `videre/fonts/other-ttf/LICENSE_APL.txt` — Arphic Public License. Couvre `BabelStoneHan.ttf` exclusivement.
- `videre/fonts/plangothic/LICENSE_OFL.txt` — SIL Open Font License 1.1. Couvre les fichiers `PlangothicP1-Regular.ttf` et `PlangothicP2-Regular.ttf`. Ce LICENSE upstream ne contient pas de ligne de copyright explicite ; le copyright se trouve dans la table `name` du TTF (NameID 0) : `Copyright (c) 2024 by Fitzgerald P. Köeingsegg. All rights reserved.`
- `videre/fonts/newgardiner/OFL.txt` — SIL Open Font License 1.1. Couvre `NewGardiner.ttf` (Reserved Font Name « NewGardiner »), copyright (c) 2020 Mark-Jan Nederhof.

Toutes ces licences autorisent l'usage commercial, la modification et la redistribution, à condition de redistribuer le texte de licence avec les polices.

## Décompte

- Source 1 (`notofonts/notofonts.github.io`) : 168 familles
- Source 2 (`notofonts/noto-cjk`) : 5 familles (Variable TTF)
- Source 2bis (`notofonts/noto-cjk` SubsetOTF) : 10 familles (Light + Regular static OTF)
- Source 3 (`google/fonts`) : 1 famille
- Source 4 (`babelstone.co.uk`) : 1 famille
- Source 5 (`Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project`) : 2 familles
- Source 6 (`nederhof/newgardiner`) : 1 famille
- **Total** : 188 fichiers

Parmi ces 188 fichiers, 178 participent au routage des caractères et séquences.
Les cinq fontes variables CJK et les cinq variantes CJK Regular sont conservées
pour référence, mais ne sont pas chargées par `FontProvider` ; les cinq variantes
CJK Light sont utilisées à leur place.

## Source 1 : `notofonts/notofonts.github.io`

Patron d'URL : `https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/<Famille>/unhinted/ttf/<Famille>-Regular.ttf`

Licence : OFL 1.1 (`videre/fonts/LICENSE_OFL.txt`).

| Fichier local | URL upstream |
|---|---|
| `noto/sans/unhinted/TTF/NotoFangsongKSSVertical-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoFangsongKSSVertical/unhinted/ttf/NotoFangsongKSSVertical-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoMusic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoMusic/unhinted/ttf/NotoMusic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoNastaliqUrdu-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoNastaliqUrdu/unhinted/ttf/NotoNastaliqUrdu-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSans-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSans/unhinted/ttf/NotoSans-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansAdlam-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansAdlam/unhinted/ttf/NotoSansAdlam-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansAnatolianHieroglyphs-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansAnatolianHieroglyphs/unhinted/ttf/NotoSansAnatolianHieroglyphs-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansArabic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansArabic/unhinted/ttf/NotoSansArabic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansArmenian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansArmenian/unhinted/ttf/NotoSansArmenian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansAvestan-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansAvestan/unhinted/ttf/NotoSansAvestan-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansBalinese-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBalinese/unhinted/ttf/NotoSansBalinese-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansBamum-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBamum/unhinted/ttf/NotoSansBamum-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansBassaVah-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBassaVah/unhinted/ttf/NotoSansBassaVah-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansBatak-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBatak/unhinted/ttf/NotoSansBatak-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansBengali-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBengali/unhinted/ttf/NotoSansBengali-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansBhaiksuki-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBhaiksuki/unhinted/ttf/NotoSansBhaiksuki-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansBrahmi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBrahmi/unhinted/ttf/NotoSansBrahmi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansBuginese-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBuginese/unhinted/ttf/NotoSansBuginese-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansBuhid-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansBuhid/unhinted/ttf/NotoSansBuhid-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansCanadianAboriginal-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCanadianAboriginal/unhinted/ttf/NotoSansCanadianAboriginal-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansCarian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCarian/unhinted/ttf/NotoSansCarian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansCaucasianAlbanian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCaucasianAlbanian/unhinted/ttf/NotoSansCaucasianAlbanian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansChakma-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansChakma/unhinted/ttf/NotoSansChakma-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansCham-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCham/unhinted/ttf/NotoSansCham-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansCherokee-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCherokee/unhinted/ttf/NotoSansCherokee-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansChorasmian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansChorasmian/unhinted/ttf/NotoSansChorasmian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansCoptic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCoptic/unhinted/ttf/NotoSansCoptic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansCuneiform-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCuneiform/unhinted/ttf/NotoSansCuneiform-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansCypriot-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCypriot/unhinted/ttf/NotoSansCypriot-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansCyproMinoan-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansCyproMinoan/unhinted/ttf/NotoSansCyproMinoan-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansDeseret-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansDeseret/unhinted/ttf/NotoSansDeseret-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansDevanagari-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansDevanagari/unhinted/ttf/NotoSansDevanagari-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansDuployan-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansDuployan/unhinted/ttf/NotoSansDuployan-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansEgyptianHieroglyphs-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansEgyptianHieroglyphs/unhinted/ttf/NotoSansEgyptianHieroglyphs-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansElbasan-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansElbasan/unhinted/ttf/NotoSansElbasan-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansElymaic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansElymaic/unhinted/ttf/NotoSansElymaic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansEthiopic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansEthiopic/unhinted/ttf/NotoSansEthiopic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansGeorgian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGeorgian/unhinted/ttf/NotoSansGeorgian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansGlagolitic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGlagolitic/unhinted/ttf/NotoSansGlagolitic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansGothic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGothic/unhinted/ttf/NotoSansGothic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansGrantha-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGrantha/unhinted/ttf/NotoSansGrantha-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansGujarati-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGujarati/unhinted/ttf/NotoSansGujarati-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansGunjalaGondi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGunjalaGondi/unhinted/ttf/NotoSansGunjalaGondi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansGurmukhi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansGurmukhi/unhinted/ttf/NotoSansGurmukhi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansHanifiRohingya-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansHanifiRohingya/unhinted/ttf/NotoSansHanifiRohingya-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansHanunoo-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansHanunoo/unhinted/ttf/NotoSansHanunoo-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansHatran-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansHatran/unhinted/ttf/NotoSansHatran-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansHebrew-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansHebrew/unhinted/ttf/NotoSansHebrew-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansImperialAramaic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansImperialAramaic/unhinted/ttf/NotoSansImperialAramaic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansIndicSiyaqNumbers-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansIndicSiyaqNumbers/unhinted/ttf/NotoSansIndicSiyaqNumbers-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansInscriptionalPahlavi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansInscriptionalPahlavi/unhinted/ttf/NotoSansInscriptionalPahlavi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansInscriptionalParthian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansInscriptionalParthian/unhinted/ttf/NotoSansInscriptionalParthian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansJavanese-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansJavanese/unhinted/ttf/NotoSansJavanese-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansKaithi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKaithi/unhinted/ttf/NotoSansKaithi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansKannada-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKannada/unhinted/ttf/NotoSansKannada-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansKawi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKawi/unhinted/ttf/NotoSansKawi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansKayahLi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKayahLi/unhinted/ttf/NotoSansKayahLi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansKharoshthi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKharoshthi/unhinted/ttf/NotoSansKharoshthi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansKhmer-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKhmer/unhinted/ttf/NotoSansKhmer-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansKhojki-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKhojki/unhinted/ttf/NotoSansKhojki-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansKhudawadi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansKhudawadi/unhinted/ttf/NotoSansKhudawadi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansLao-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansLao/unhinted/ttf/NotoSansLao-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansLepcha-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansLepcha/unhinted/ttf/NotoSansLepcha-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansLimbu-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansLimbu/unhinted/ttf/NotoSansLimbu-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansLinearA-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansLinearA/unhinted/ttf/NotoSansLinearA-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansLinearB-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansLinearB/unhinted/ttf/NotoSansLinearB-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansLisu-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansLisu/unhinted/ttf/NotoSansLisu-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansLycian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansLycian/unhinted/ttf/NotoSansLycian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansLydian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansLydian/unhinted/ttf/NotoSansLydian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMahajani-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMahajani/unhinted/ttf/NotoSansMahajani-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMalayalam-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMalayalam/unhinted/ttf/NotoSansMalayalam-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMandaic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMandaic/unhinted/ttf/NotoSansMandaic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansManichaean-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansManichaean/unhinted/ttf/NotoSansManichaean-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMarchen-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMarchen/unhinted/ttf/NotoSansMarchen-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMasaramGondi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMasaramGondi/unhinted/ttf/NotoSansMasaramGondi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMath-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMath/unhinted/ttf/NotoSansMath-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMayanNumerals-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMayanNumerals/unhinted/ttf/NotoSansMayanNumerals-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMedefaidrin-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMedefaidrin/unhinted/ttf/NotoSansMedefaidrin-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMeeteiMayek-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMeeteiMayek/unhinted/ttf/NotoSansMeeteiMayek-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMendeKikakui-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMendeKikakui/unhinted/ttf/NotoSansMendeKikakui-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMeroitic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMeroitic/unhinted/ttf/NotoSansMeroitic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMiao-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMiao/unhinted/ttf/NotoSansMiao-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansModi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansModi/unhinted/ttf/NotoSansModi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMongolian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMongolian/unhinted/ttf/NotoSansMongolian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMro-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMro/unhinted/ttf/NotoSansMro-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMultani-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMultani/unhinted/ttf/NotoSansMultani-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansMyanmar-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMyanmar/unhinted/ttf/NotoSansMyanmar-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansNKo-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansNKo/unhinted/ttf/NotoSansNKo-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansNabataean-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansNabataean/unhinted/ttf/NotoSansNabataean-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansNagMundari-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansNagMundari/unhinted/ttf/NotoSansNagMundari-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansNandinagari-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansNandinagari/unhinted/ttf/NotoSansNandinagari-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansNewTaiLue-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansNewTaiLue/unhinted/ttf/NotoSansNewTaiLue-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansNewa-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansNewa/unhinted/ttf/NotoSansNewa-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansNushu-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansNushu/unhinted/ttf/NotoSansNushu-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOgham-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOgham/unhinted/ttf/NotoSansOgham-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOlChiki-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOlChiki/unhinted/ttf/NotoSansOlChiki-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOldHungarian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOldHungarian/unhinted/ttf/NotoSansOldHungarian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOldItalic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOldItalic/unhinted/ttf/NotoSansOldItalic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOldNorthArabian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOldNorthArabian/unhinted/ttf/NotoSansOldNorthArabian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOldPermic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOldPermic/unhinted/ttf/NotoSansOldPermic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOldPersian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOldPersian/unhinted/ttf/NotoSansOldPersian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOldSogdian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOldSogdian/unhinted/ttf/NotoSansOldSogdian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOldSouthArabian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOldSouthArabian/unhinted/ttf/NotoSansOldSouthArabian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOldTurkic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOldTurkic/unhinted/ttf/NotoSansOldTurkic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOriya-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOriya/unhinted/ttf/NotoSansOriya-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOsage-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOsage/unhinted/ttf/NotoSansOsage-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansOsmanya-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansOsmanya/unhinted/ttf/NotoSansOsmanya-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansPahawhHmong-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansPahawhHmong/unhinted/ttf/NotoSansPahawhHmong-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansPalmyrene-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansPalmyrene/unhinted/ttf/NotoSansPalmyrene-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansPauCinHau-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansPauCinHau/unhinted/ttf/NotoSansPauCinHau-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansPhagsPa-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansPhagsPa/unhinted/ttf/NotoSansPhagsPa-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansPhoenician-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansPhoenician/unhinted/ttf/NotoSansPhoenician-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansPsalterPahlavi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansPsalterPahlavi/unhinted/ttf/NotoSansPsalterPahlavi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansRejang-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansRejang/unhinted/ttf/NotoSansRejang-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansRunic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansRunic/unhinted/ttf/NotoSansRunic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSamaritan-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSamaritan/unhinted/ttf/NotoSansSamaritan-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSaurashtra-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSaurashtra/unhinted/ttf/NotoSansSaurashtra-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSharada-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSharada/unhinted/ttf/NotoSansSharada-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansShavian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansShavian/unhinted/ttf/NotoSansShavian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSiddham-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSiddham/unhinted/ttf/NotoSansSiddham-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSignWriting-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSignWriting/unhinted/ttf/NotoSansSignWriting-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSinhala-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSinhala/unhinted/ttf/NotoSansSinhala-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSogdian-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSogdian/unhinted/ttf/NotoSansSogdian-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSoraSompeng-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSoraSompeng/unhinted/ttf/NotoSansSoraSompeng-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSoyombo-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSoyombo/unhinted/ttf/NotoSansSoyombo-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSundanese-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSundanese/unhinted/ttf/NotoSansSundanese-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSylotiNagri-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSylotiNagri/unhinted/ttf/NotoSansSylotiNagri-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSymbols-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSymbols/unhinted/ttf/NotoSansSymbols-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSymbols2-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSymbols2/unhinted/ttf/NotoSansSymbols2-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSunuwar-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSunuwar/unhinted/ttf/NotoSansSunuwar-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSyriac-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSyriac/unhinted/ttf/NotoSansSyriac-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSyriacEastern-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSyriacEastern/unhinted/ttf/NotoSansSyriacEastern-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansSyriacWestern-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansSyriacWestern/unhinted/ttf/NotoSansSyriacWestern-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTagalog-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTagalog/unhinted/ttf/NotoSansTagalog-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTagbanwa-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTagbanwa/unhinted/ttf/NotoSansTagbanwa-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTaiLe-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTaiLe/unhinted/ttf/NotoSansTaiLe-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTaiTham-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTaiTham/unhinted/ttf/NotoSansTaiTham-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTaiViet-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTaiViet/unhinted/ttf/NotoSansTaiViet-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTakri-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTakri/unhinted/ttf/NotoSansTakri-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTamil-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTamil/unhinted/ttf/NotoSansTamil-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTamilSupplement-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTamilSupplement/unhinted/ttf/NotoSansTamilSupplement-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTangsa-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTangsa/unhinted/ttf/NotoSansTangsa-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTelugu-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTelugu/unhinted/ttf/NotoSansTelugu-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTest-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTest/unhinted/ttf/NotoSansTest-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansThaana-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansThaana/unhinted/ttf/NotoSansThaana-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansThaiLooped-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansThaiLooped/unhinted/ttf/NotoSansThaiLooped-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTifinagh-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTifinagh/unhinted/ttf/NotoSansTifinagh-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansTirhuta-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansTirhuta/unhinted/ttf/NotoSansTirhuta-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansUgaritic-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansUgaritic/unhinted/ttf/NotoSansUgaritic-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansVai-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansVai/unhinted/ttf/NotoSansVai-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansVithkuqi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansVithkuqi/unhinted/ttf/NotoSansVithkuqi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansWancho-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansWancho/unhinted/ttf/NotoSansWancho-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansWarangCiti-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansWarangCiti/unhinted/ttf/NotoSansWarangCiti-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansYi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansYi/unhinted/ttf/NotoSansYi-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoSansZanabazarSquare-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansZanabazarSquare/unhinted/ttf/NotoSansZanabazarSquare-Regular.ttf> |
| `noto/sans/unhinted/TTF/NotoZnamennyMusicalNotation-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoZnamennyMusicalNotation/unhinted/ttf/NotoZnamennyMusicalNotation-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifAhom-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifAhom/unhinted/ttf/NotoSerifAhom-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifDogra-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifDogra/unhinted/ttf/NotoSerifDogra-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifKhojki-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifKhojki/unhinted/ttf/NotoSerifKhojki-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifMakasar-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifMakasar/unhinted/ttf/NotoSerifMakasar-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifNPHmong-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifNPHmong/unhinted/ttf/NotoSerifNPHmong-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifOldUyghur-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifOldUyghur/unhinted/ttf/NotoSerifOldUyghur-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifOttomanSiyaq-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifOttomanSiyaq/unhinted/ttf/NotoSerifOttomanSiyaq-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifTangut-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifTangut/unhinted/ttf/NotoSerifTangut-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifTibetan-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifTibetan/unhinted/ttf/NotoSerifTibetan-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifTodhri-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifTodhri/unhinted/ttf/NotoSerifTodhri-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifToto-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifToto/unhinted/ttf/NotoSerifToto-Regular.ttf> |
| `noto/serif/unhinted/TTF/NotoSerifYezidi-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifYezidi/unhinted/ttf/NotoSerifYezidi-Regular.ttf> |
| `noto/mono/unhinted/TTF/NotoSansMono-Regular.ttf` | <https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansMono/unhinted/ttf/NotoSansMono-Regular.ttf> |

## Source 2 : `notofonts/noto-cjk` (variable fonts CJK)

Patron d'URL : `https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/<Famille>-VF.ttf`

Licence : OFL 1.1 (`videre/fonts/LICENSE_OFL.txt`).

Ces fichiers sont des variable fonts dont l'axe `wght` couvre 100-900 (Bold = 700). Pas d'axe italique : la synthèse italique reste nécessaire si demandée.

**Limite connue** : `pygame.freetype` ne supporte pas les axes de variation OpenType. Ces VF sont donc rendues à leur valeur par défaut (`wght=100`, soit Thin), trop fin pour un usage normal. Les fichiers static OTF de la Source 2bis sont chargés à la place pour le rendu réel.

| Fichier local | URL upstream |
|---|---|
| `noto/cjk/variable-fonts/NotoSansHK-VF.ttf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansHK-VF.ttf> |
| `noto/cjk/variable-fonts/NotoSansJP-VF.ttf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansJP-VF.ttf> |
| `noto/cjk/variable-fonts/NotoSansKR-VF.ttf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansKR-VF.ttf> |
| `noto/cjk/variable-fonts/NotoSansSC-VF.ttf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansSC-VF.ttf> |
| `noto/cjk/variable-fonts/NotoSansTC-VF.ttf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/Variable/TTF/Subset/NotoSansTC-VF.ttf> |

## Source 2bis : `notofonts/noto-cjk` (static OTF CJK)

Patron d'URL : `https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/<LANG>/NotoSans<LANG>-<Weight>.otf`

Licence : OFL 1.1 (`videre/fonts/LICENSE_OFL.txt`). Identique au texte de la Source 2 (le LICENSE upstream `Sans/LICENSE` couvre toutes les variantes).

Les variantes Light (`wght=300`) sont **chargées et prioritaires** dans le mapping char→font (rangs 3 à 7 dans `_gen_char_cov.py:generate_char_to_font`), pour donner aux blocs CJK courants (URO, Hiragana, Katakana, Hangul) un rendu sans-serif aéré proche de Yu Gothic UI Regular sur Windows 11. Mesure de référence : NotoSansJP-Light rend à ~5,07 % de pixels noirs vs Yu Gothic UI Regular à 5,91 % (`pygame.freetype`, taille 64).

Les variantes Regular (`wght=400`) sont **conservées sur disque mais pas chargées** : leur `full name` entre en collision avec celui des VF (Source 2), et leur rendu est ~1,5× plus gras que la cible Yu Gothic UI Regular.

| Fichier local | URL upstream |
|---|---|
| `noto/cjk/light/NotoSansJP-Light.otf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/JP/NotoSansJP-Light.otf> |
| `noto/cjk/light/NotoSansHK-Light.otf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/HK/NotoSansHK-Light.otf> |
| `noto/cjk/light/NotoSansSC-Light.otf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/SC/NotoSansSC-Light.otf> |
| `noto/cjk/light/NotoSansTC-Light.otf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/TC/NotoSansTC-Light.otf> |
| `noto/cjk/light/NotoSansKR-Light.otf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/KR/NotoSansKR-Light.otf> |
| `noto/cjk/regular/NotoSansJP-Regular.otf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/JP/NotoSansJP-Regular.otf> |
| `noto/cjk/regular/NotoSansHK-Regular.otf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/HK/NotoSansHK-Regular.otf> |
| `noto/cjk/regular/NotoSansSC-Regular.otf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf> |
| `noto/cjk/regular/NotoSansTC-Regular.otf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/TC/NotoSansTC-Regular.otf> |
| `noto/cjk/regular/NotoSansKR-Regular.otf` | <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/KR/NotoSansKR-Regular.otf> |

## Source 3 : `google/fonts` (NotoEmoji monochrome)

Le repo `googlefonts/noto-emoji` ne contient que la version **couleur** (NotoColorEmoji.ttf). La version monochrome utilisée par videre est répliquée dans le repo `google/fonts` qui sert de catalogue Google Fonts.

Licence : OFL 1.1 (`videre/fonts/LICENSE_OFL.txt`). Texte spécifique aussi disponible à <https://raw.githubusercontent.com/google/fonts/main/ofl/notoemoji/OFL.txt>.

| Fichier local | URL upstream |
|---|---|
| `noto/sans/unhinted/TTF/NotoEmoji-Regular.ttf` | <https://raw.githubusercontent.com/google/fonts/main/ofl/notoemoji/NotoEmoji%5Bwght%5D.ttf> |

Le fichier statique Regular local n'est plus publié directement dans le dépôt
Google Fonts. L'upstream actuel est la fonte variable indiquée ci-dessus
(`wght` 300-700, valeur par défaut 400), de même version 3.002 et de même
couverture Unicode. Une mise à jour doit soit recréer une instance statique à
`wght=400`, soit tester puis adopter la fonte variable ou
`NotoColorEmoji.ttf`.

## Source 4 : `babelstone.co.uk`

Licence : Arphic Public License (`videre/fonts/other-ttf/LICENSE_APL.txt`).

Page d'accueil de la fonte : <https://www.babelstone.co.uk/Fonts/Han.html>.

| Fichier local | URL upstream |
|---|---|
| `other-ttf/BabelStoneHan.ttf` | <https://www.babelstone.co.uk/Fonts/Download/BabelStoneHan.ttf> |

## Source 5 : `Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project`

Famille pan-CJK conçue pour couvrir tous les blocs CJK Unified Ideographs Extensions ainsi que les caractères Unicode rares non couverts par Noto Sans CJK. Distribuée en deux fichiers (P1 et P2) à cause de la limite de 65 535 glyphes par font OpenType.

Licence : SIL Open Font License 1.1 (`videre/fonts/plangothic/LICENSE_OFL.txt`). Le code de build du projet upstream est sous MIT, mais ce code n'est pas redistribué ici — seuls les binaires TTF le sont, donc seule la licence OFL s'applique au contenu de `videre/fonts/plangothic/`.

Page de releases : <https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project/releases>.

| Fichier local | URL upstream |
|---|---|
| `plangothic/PlangothicP1-Regular.ttf` | <https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project/releases/download/V2.9.5792/PlangothicP1-Regular.ttf> |
| `plangothic/PlangothicP2-Regular.ttf` | <https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project/releases/download/V2.9.5792/PlangothicP2-Regular.ttf> |

Note : l'URL upstream est versionnée (V2.9.5792 = release du 2026-01-01). Pour rafraîchir, récupérer la dernière release et adapter le tag dans l'URL.

## Source 6 : `nederhof/newgardiner`

Fonte hiéroglyphique égyptienne (Mark-Jan Nederhof, standard Gardiner) ajoutée
pour couvrir le bloc **Egyptian Hieroglyphs Extended-A** (U+13460–U+143FF,
Unicode 16.0), absent de la collection Noto. Elle couvre 3 427 des 3 995
codepoints du bloc (85,8 %), sur les vrais codepoints SMP. TTF statique (pas de
fonte variable), version 3.08.

NewGardiner couvre aussi le bloc de base (U+13000–U+1342F, 1072 cp) ET les
contrôles de format de quadrats (U+13430–U+1343F, 16 cp) que la Noto Sans
Egyptian Hieroglyphs locale (2.002) ne couvre PAS. Le routage la sélectionne donc
pour **tout** l'égyptien : rendu cohérent dans une seule fonte. La Noto Sans
Egyptian Hieroglyphs ne route plus aucun caractère (conservée mais redondante) ;
aucune des deux n'expose de GSUB/GPOS égyptien, donc pas de régression de layout.

Impact : couverture globale 97,36 % → **99,58 %** (153 936 / 154 591 ; 0 `.notdef`
au shaping). Les 568 signes « non-core » restants ne sont pas dans
`NewGardiner.ttf` (le `NewGardinerNonCore.ttf` upstream ne contient que 8
codepoints et n'est donc pas embarqué).

Licence : SIL Open Font License 1.1 (`videre/fonts/newgardiner/OFL.txt`),
Reserved Font Name « NewGardiner », copyright (c) 2020 Mark-Jan Nederhof.

| Fichier local | URL upstream |
|---|---|
| `newgardiner/NewGardiner.ttf` | <https://raw.githubusercontent.com/nederhof/newgardiner/master/fonts/NewGardiner.ttf> |
| `newgardiner/OFL.txt` | <https://raw.githubusercontent.com/nederhof/newgardiner/master/fonts/OFL.txt> |

## Versions

Pas de tracking de version actuel. Le metadata `name` table de chaque TTF contient une chaîne version, lisible via `fontTools.ttLib.TTFont(path)['name'].getDebugName(5)`. À ajouter au catalogue ci-dessus si un pinning précis devient nécessaire.

## Données Unicode de couverture

Les fichiers de couverture générés ne reposent pas seulement sur le `cmap` des
polices. Ils utilisent aussi les registres Unicode officiels suivants :

- `StandardizedVariants.txt` pour les séquences de variation standardisées ;
- `emoji-variation-sequences.txt` pour les présentations texte/emoji ;
- `emoji-sequences.txt` pour les séquences emoji ;
- `emoji-zwj-sequences.txt` pour les séquences emoji utilisant ZWJ ;
- `IVD_Sequences.txt` pour les variantes idéographiques enregistrées dans
  l'Ideographic Variation Database.

Les URL exactes, la version Unicode et la version IVD sont enregistrées dans
`unicode-sequences.json`. Ce fichier est régénéré par
`videre/fonts/_update_unicode_font_data.py`.

## Mise à jour

Pour rafraîchir une police :

1. Télécharger l'URL upstream correspondante et écraser le fichier local.
2. Vérifier que les variantes disponibles upstream listées dans
   `docs/font-bold-italic-availability.md` sont toujours cohérentes.
3. Régénérer les capacités, le routage et le rapport de couverture :

   ```bash
   uv run python -m videre.fonts._gen_char_cov
   ```

4. Vérifier le résultat lisible :

   ```bash
   uv run python -m videre.fonts._cov_stats
   ```

5. Exécuter les tests qui comparent les fichiers JSON de production à une
   nouvelle génération :

   ```bash
   uv run pytest tests/videre_tests/test_fonts.py
   ```

Lors d'un changement de version Unicode ou IVD, régénérer d'abord le registre
des séquences :

```bash
uv run python -m videre.fonts._update_unicode_font_data
uv run python -m videre.fonts._gen_char_cov
```

Les artefacts de production concernés sont `font-to-characters.json`,
`font-capabilities.json`, `sequence-to-font.json` et `_coverage-report.json`, tous dans `videre/fonts/cov/`.
