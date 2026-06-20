# Audit des mises à jour de polices

Date de vérification : **13 juin 2026**.

Cet audit compare chaque fichier local à son fichier officiel actuel. La comparaison porte sur le SHA-256 du binaire, la version OpenType, les codepoints `cmap`, les séquences de variation `cmap 14` et les scripts GSUB/GPOS.

## Résumé

- 163 fichiers sont strictement identiques à leur upstream.
- 22 fichiers Noto ont une version plus récente.
- `BabelStoneHan.ttf` est en version locale 15.1.4 contre 16.0.3 upstream.
- La fonte monochrome statique `NotoEmoji-Regular.ttf` n'est plus publiée à son ancienne URL. La variante variable monochrome conserve la même couverture ; `NotoColorEmoji.ttf` 2.051 apporte une meilleure couverture.
- Plangothic P1/P2 est déjà sur la dernière release officielle V2.9.5792.

Aucune des 22 mises à jour Noto de même famille ne comble les 4 082 codepoints actuellement manquants. Elles restent intéressantes pour les corrections de dessins et de shaping.

## Actions recommandées

### 1. Noto Color Emoji

`NotoColorEmoji.ttf` version 2.051 couvre les sept emoji Unicode 16 actuellement manquants :

`U+1FA89`, `U+1FA8F`, `U+1FABE`, `U+1FAC6`, `U+1FADC`, `U+1FADF`, `U+1FAE9`.

Elle façonne aussi correctement les 742 variations emoji, 1 136 séquences emoji et 1 468 séquences ZWJ du registre de Videre. Son ajout ferait passer les codepoints manquants de 4 082 à 4 075.

### 2. BabelStone Han

Le passage de 15.1.4 à 16.0.3 ne comble aucun codepoint Unicode 16 actuellement manquant, mais améliore les séquences :

- 8 variations standardisées supplémentaires ;
- 25 variantes idéographiques gagnées et 2 perdues, soit un gain net de 23 ;
- nouvelle URL officielle : `https://www.babelstone.co.uk/Fonts/Download/BabelStoneHan.ttf`.

### 3. Polices Noto ajoutées à Videre

| Police | Amélioration par rapport au routage actuel | GSUB/GPOS |
|---|---|---|
| Noto Serif Khojki 2.005 | couvre `U+11241`, le seul caractère Khojki absent de Noto Sans Khojki ; les grappes qui le contiennent restent désormais dans une vraie police Khojki | GSUB + GPOS `khoj` |
| Noto Sans Sunuwar 1.000 | remplace Plangothic pour les 44 caractères Sunuwar | GPOS `sunu` |
| Noto Serif Todhri 1.000 | remplace Plangothic pour les 52 caractères Todhri | GPOS générique |

### 4. Familles Noto restantes intéressantes

| Police | Amélioration par rapport au routage actuel | GSUB/GPOS |
|---|---|---|
| Noto Serif Dives Akuru 2.000 | remplace Plangothic pour 49 caractères Dives Akuru | GSUB + GPOS `diak` |
| Noto Serif Hentaigana 1.000 | remplace BabelStone pour 290 kana historiques | pas de layout spécialisé |

Dives Akuru resterait toutefois partiel : la fonte Noto publique couvre 49 des 72 caractères Unicode du bloc ; les 23 autres continueraient à dépendre de Plangothic.

Les cinq fontes CJK Noto complètes Light absentes du dépôt ne couvrent que 12 caractères supplémentaires actuellement confiés à Plangothic, sans ajouter de variantes idéographiques. Elles ajouteraient environ 53 Mo au dépôt par rapport aux cinq `SubsetOTF` Light : gain trop faible.

### 5. Manques sans solution Noto publiée

- **Egyptian Hieroglyphs Extended-A** : 3 995 codepoints. La Noto Sans Egyptian Hieroglyphs locale est déjà identique à la version officielle 2.002. Le dépôt de développement Noto ne contient que deux dessins Extended-A placés dans `LeftForFuture`, pas une fonte couvrant le bloc.
- **Tulu-Tigalari** : 80 codepoints. Aucune famille Tulu-Tigalari n'est publiée dans le catalogue Noto, Google Fonts ou l'organisation GitHub Noto.
- **Variantes idéographiques** : après mise à jour de BabelStone, 14 715 séquences IVD resteraient absentes. Les fichiers Noto CJK locaux sont déjà identiques à upstream, et les variantes Light/Regular/variables ont les mêmes tables `cmap 14`.

## Mises à jour disponibles

| Fichier | Version locale | Version upstream | Différence de couverture brute | Évolution layout notable |
|---|---:|---:|---:|---|
| `noto/serif/unhinted/TTF/NotoSerifOldUyghur-Regular.ttf` | Version 1.003 | Version 1.004 | +0 / -0 codepoints | ajout de GPOS `ougr` |
| `noto/serif/unhinted/TTF/NotoSerifTangut-Regular.ttf` | Version 2.169 | Version 2.170 | +0 / -219 codepoints | — |
| `noto/serif/unhinted/TTF/NotoSerifToto-Regular.ttf` | Version 2.001 | Version 2.002 | +0 / -0 codepoints | ajout de GPOS `toto` |
| `noto/sans/unhinted/TTF/NotoNastaliqUrdu-Regular.ttf` | Version 3.009 | Version 4.000 | +3 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSans-Regular.ttf` | Version 2.013 | Version 2.015 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansArabic-Regular.ttf` | Version 2.012 | Version 2.013 | +0 / -1 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansBatak-Regular.ttf` | Version 2.003 | Version 2.004 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansBengali-Regular.ttf` | Version 2.003 | Version 3.011 | +0 / -39 codepoints | ajout du tag GPOS `beng` |
| `noto/sans/unhinted/TTF/NotoSansKaithi-Regular.ttf` | Version 2.005 | Version 2.006 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansKannada-Regular.ttf` | Version 2.005 | Version 2.006 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansMongolian-Regular.ttf` | Version 3.001 | Version 3.002 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansNagMundari-Regular.ttf` | Version 1.000 | Version 1.001 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansNandinagari-Regular.ttf` | Version 1.002 | Version 1.003 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansOldItalic-Regular.ttf` | Version 2.003 | Version 2.004 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansOldSogdian-Regular.ttf` | Version 2.002 | Version 2.003 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansOldTurkic-Regular.ttf` | Version 2.003 | Version 2.004 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansOriya-Regular.ttf` | Version 2.006 | Version 2.007 | +1 / -1 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansPsalterPahlavi-Regular.ttf` | Version 2.002 | Version 2.003 | +0 / -0 codepoints | ajout de `DFLT` à GSUB/GPOS |
| `noto/sans/unhinted/TTF/NotoSansRejang-Regular.ttf` | Version 2.002 | Version 2.003 | +0 / -0 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansSinhala-Regular.ttf` | Version 2.006 | Version 3.000 | +52 / -4 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansSyriacWestern-Regular.ttf` | Version 3.000 | Version 3.001 | +2 / -1 codepoints | — |
| `noto/sans/unhinted/TTF/NotoSansThaiLooped-Regular.ttf` | Version 1.001 | Version 2.000 | +12 / -14 codepoints | — |

Les suppressions constatées dans certaines mises à jour concernent des caractères communs couverts par d'autres polices, des caractères ignorables par défaut ou des PUA. Elles ne réduisent pas le profil de couverture Unicode 16 de Videre.

## Statut des 187 fichiers

| Fichier | Version locale | Version upstream | Statut |
|---|---:|---:|---|
| `noto/cjk/light/NotoSansHK-Light.otf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/light/NotoSansJP-Light.otf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/light/NotoSansKR-Light.otf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/light/NotoSansSC-Light.otf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/light/NotoSansTC-Light.otf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/regular/NotoSansHK-Regular.otf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/regular/NotoSansJP-Regular.otf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/regular/NotoSansKR-Regular.otf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/regular/NotoSansSC-Regular.otf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/regular/NotoSansTC-Regular.otf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/variable-fonts/NotoSansHK-VF.ttf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/variable-fonts/NotoSansJP-VF.ttf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/variable-fonts/NotoSansKR-VF.ttf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/variable-fonts/NotoSansSC-VF.ttf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/cjk/variable-fonts/NotoSansTC-VF.ttf` | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | Version 2.004;hotconv 1.0.118;makeotfexe 2.5.65603 | À jour, binaire identique |
| `noto/mono/unhinted/TTF/NotoSansMono-Regular.ttf` | Version 2.014 | Version 2.014 | À jour, binaire identique |
| `noto/serif/unhinted/TTF/NotoSerifAhom-Regular.ttf` | Version 2.007 | Version 2.007 | À jour, binaire identique |
| `noto/serif/unhinted/TTF/NotoSerifDogra-Regular.ttf` | Version 1.007 | Version 1.007 | À jour, binaire identique |
| `noto/serif/unhinted/TTF/NotoSerifKhojki-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/serif/unhinted/TTF/NotoSerifMakasar-Regular.ttf` | Version 1.001 | Version 1.001 | À jour, binaire identique |
| `noto/serif/unhinted/TTF/NotoSerifNPHmong-Regular.ttf` | Version 1.001 | Version 1.001 | À jour, binaire identique |
| `noto/serif/unhinted/TTF/NotoSerifOldUyghur-Regular.ttf` | Version 1.003 | Version 1.004 | Mise à jour disponible |
| `noto/serif/unhinted/TTF/NotoSerifOttomanSiyaq-Regular.ttf` | Version 1.006 | Version 1.006 | À jour, binaire identique |
| `noto/serif/unhinted/TTF/NotoSerifTangut-Regular.ttf` | Version 2.169 | Version 2.170 | Mise à jour disponible |
| `noto/serif/unhinted/TTF/NotoSerifTibetan-Regular.ttf` | Version 2.103 | Version 2.103 | À jour, binaire identique |
| `noto/serif/unhinted/TTF/NotoSerifTodhri-Regular.ttf` | Version 1.000 | Version 1.000 | À jour, binaire identique |
| `noto/serif/unhinted/TTF/NotoSerifToto-Regular.ttf` | Version 2.001 | Version 2.002 | Mise à jour disponible |
| `noto/serif/unhinted/TTF/NotoSerifYezidi-Regular.ttf` | Version 1.001 | Version 1.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoEmoji-Regular.ttf` | Version 3.002 | Version 3.002 / Color 2.051 | Statique retirée upstream ; VF 3.002 équivalente, Color Emoji 2.051 meilleure |
| `noto/sans/unhinted/TTF/NotoFangsongKSSVertical-Regular.ttf` | Version 1.000;November 16, 2022;FontCreator 11.5.0.2427 64-bit | Version 1.000;November 16, 2022;FontCreator 11.5.0.2427 64-bit | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoMusic-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoNastaliqUrdu-Regular.ttf` | Version 3.009 | Version 4.000 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSans-Regular.ttf` | Version 2.013 | Version 2.015 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansAdlam-Regular.ttf` | Version 3.002 | Version 3.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansAnatolianHieroglyphs-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansArabic-Regular.ttf` | Version 2.012 | Version 2.013 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansArmenian-Regular.ttf` | Version 2.008 | Version 2.008 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansAvestan-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansBalinese-Regular.ttf` | Version 2.006 | Version 2.006 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansBamum-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansBassaVah-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansBatak-Regular.ttf` | Version 2.003 | Version 2.004 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansBengali-Regular.ttf` | Version 2.003 | Version 3.011 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansBhaiksuki-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansBrahmi-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansBuginese-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansBuhid-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansCanadianAboriginal-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansCarian-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansCaucasianAlbanian-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansChakma-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansCham-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansCherokee-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansChorasmian-Regular.ttf` | Version 1.004 | Version 1.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansCoptic-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansCuneiform-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansCypriot-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansCyproMinoan-Regular.ttf` | Version 1.503 | Version 1.503 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansDeseret-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansDevanagari-Regular.ttf` | Version 2.006 | Version 2.006 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansDuployan-Regular.ttf` | Version 3.002 | Version 3.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansEgyptianHieroglyphs-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansElbasan-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansElymaic-Regular.ttf` | Version 1.002 | Version 1.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansEthiopic-Regular.ttf` | Version 2.102 | Version 2.102 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansGeorgian-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansGlagolitic-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansGothic-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansGrantha-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansGujarati-Regular.ttf` | Version 2.106 | Version 2.106 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansGunjalaGondi-Regular.ttf` | Version 1.004 | Version 1.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansGurmukhi-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansHanifiRohingya-Regular.ttf` | Version 2.102 | Version 2.102 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansHanunoo-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansHatran-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansHebrew-Regular.ttf` | Version 3.001 | Version 3.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansImperialAramaic-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansIndicSiyaqNumbers-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansInscriptionalPahlavi-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansInscriptionalParthian-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansJavanese-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansKaithi-Regular.ttf` | Version 2.005 | Version 2.006 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansKannada-Regular.ttf` | Version 2.005 | Version 2.006 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansKawi-Regular.ttf` | Version 1.000 | Version 1.000 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansKayahLi-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansKharoshthi-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansKhmer-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansKhojki-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansKhudawadi-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansLao-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansLepcha-Regular.ttf` | Version 2.006 | Version 2.006 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansLimbu-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansLinearA-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansLinearB-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansLisu-Regular.ttf` | Version 2.102 | Version 2.102 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansLycian-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansLydian-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMahajani-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMalayalam-Regular.ttf` | Version 2.104 | Version 2.104 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMandaic-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansManichaean-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMarchen-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMasaramGondi-Regular.ttf` | Version 1.005 | Version 1.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMath-Regular.ttf` | Version 3.000 | Version 3.000 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMayanNumerals-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMedefaidrin-Regular.ttf` | Version 1.002 | Version 1.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMeeteiMayek-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMendeKikakui-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMeroitic-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMiao-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansModi-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMongolian-Regular.ttf` | Version 3.001 | Version 3.002 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansMro-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMultani-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansMyanmar-Regular.ttf` | Version 2.107 | Version 2.107 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansNKo-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansNabataean-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansNagMundari-Regular.ttf` | Version 1.000 | Version 1.001 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansNandinagari-Regular.ttf` | Version 1.002 | Version 1.003 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansNewTaiLue-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansNewa-Regular.ttf` | Version 2.007 | Version 2.007 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansNushu-Regular.ttf` | Version 1.003 | Version 1.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansOgham-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansOlChiki-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansOldHungarian-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansOldItalic-Regular.ttf` | Version 2.003 | Version 2.004 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansOldNorthArabian-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansOldPermic-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansOldPersian-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansOldSogdian-Regular.ttf` | Version 2.002 | Version 2.003 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansOldSouthArabian-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansOldTurkic-Regular.ttf` | Version 2.003 | Version 2.004 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansOriya-Regular.ttf` | Version 2.006 | Version 2.007 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansOsage-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansOsmanya-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansPahawhHmong-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansPalmyrene-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansPauCinHau-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansPhagsPa-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansPhoenician-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansPsalterPahlavi-Regular.ttf` | Version 2.002 | Version 2.003 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansRejang-Regular.ttf` | Version 2.002 | Version 2.003 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansRunic-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSamaritan-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSaurashtra-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSharada-Regular.ttf` | Version 2.006 | Version 2.006 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansShavian-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSiddham-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSignWriting-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSinhala-Regular.ttf` | Version 2.006 | Version 3.000 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansSogdian-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSoraSompeng-Regular.ttf` | Version 2.101 | Version 2.101 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSoyombo-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSundanese-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSylotiNagri-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSymbols-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSymbols2-Regular.ttf` | Version 2.008 | Version 2.008 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSunuwar-Regular.ttf` | Version 1.000 | Version 1.000 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSyriac-Regular.ttf` | Version 3.000 | Version 3.000 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSyriacEastern-Regular.ttf` | Version 3.001 | Version 3.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansSyriacWestern-Regular.ttf` | Version 3.000 | Version 3.001 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansTagalog-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTagbanwa-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTaiLe-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTaiTham-Regular.ttf` | Version 2.002; ttfautohint (v1.8.4.7-5d5b) | Version 2.002; ttfautohint (v1.8.4.7-5d5b) | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTaiViet-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTakri-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTamil-Regular.ttf` | Version 2.004 | Version 2.004 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTamilSupplement-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTangsa-Regular.ttf` | Version 1.506 | Version 1.506 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTelugu-Regular.ttf` | Version 2.005 | Version 2.005 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTest-Regular.ttf` | Version 1.002 | Version 1.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansThaana-Regular.ttf` | Version 3.001; ttfautohint (v1.8.4.7-5d5b) | Version 3.001; ttfautohint (v1.8.4.7-5d5b) | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansThaiLooped-Regular.ttf` | Version 1.001 | Version 2.000 | Mise à jour disponible |
| `noto/sans/unhinted/TTF/NotoSansTifinagh-Regular.ttf` | Version 2.006 | Version 2.006 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansTirhuta-Regular.ttf` | Version 2.003 | Version 2.003 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansUgaritic-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansVai-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansVithkuqi-Regular.ttf` | Version 1.001 | Version 1.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansWancho-Regular.ttf` | Version 2.001 | Version 2.001 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansWarangCiti-Regular.ttf` | Version 3.002 | Version 3.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansYi-Regular.ttf` | Version 2.002 | Version 2.002 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoSansZanabazarSquare-Regular.ttf` | Version 2.006 | Version 2.006 | À jour, binaire identique |
| `noto/sans/unhinted/TTF/NotoZnamennyMusicalNotation-Regular.ttf` | Version 1.003 | Version 1.003 | À jour, binaire identique |
| `other-ttf/BabelStoneHan.ttf` | Version 15.1.4; March 15, 2024 | Version 16.0.3 | Mise à jour disponible (URL documentée obsolète) |
| `plangothic/PlangothicP1-Regular.ttf` | Version 6.400;January 1, 2026;FontCreator 14.0.0.2901 64-bit | Version 6.400;January 1, 2026;FontCreator 14.0.0.2901 64-bit | À jour, binaire identique |
| `plangothic/PlangothicP2-Regular.ttf` | Version 3.178;January 1, 2026;FontCreator 14.0.0.2901 64-bit | Version 3.178;January 1, 2026;FontCreator 14.0.0.2901 64-bit | À jour, binaire identique |

## Sources officielles consultées

- <https://github.com/notofonts/notofonts.github.io>
- <https://github.com/notofonts/noto-cjk>
- <https://github.com/google/fonts/tree/main/ofl/notoemoji>
- <https://github.com/googlefonts/noto-emoji/releases/tag/v2.051>
- <https://www.babelstone.co.uk/Fonts/Han.html>
- <https://github.com/notofonts/egyptian-hieroglyphs>
- <https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project/releases/tag/V2.9.5792>
