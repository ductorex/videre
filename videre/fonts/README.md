# `videre/fonts/` — polices embarquées et données de couverture

Ce dossier contient les polices embarquées (Noto + quelques extras) et le système
de **découverte de police par caractère** utilisé par `FontProvider`
(`provider.py`) : pour un caractère ou une grappe (*cluster*) donné, il indique
quelle police sait le dessiner.

- Provenance des fichiers de police (URLs upstream, licences) → [`SOURCES.md`](SOURCES.md)
- Comparaison local ↔ upstream (SHA-256, versions) → [`FONT_UPDATE_AUDIT.md`](FONT_UPDATE_AUDIT.md)
- Audit de conformité Unicode → [`../../docs/unicode-conformance.md`](../../docs/unicode-conformance.md)
- Disponibilité des variantes gras/italique → [`../../docs/font-bold-italic-availability.md`](../../docs/font-bold-italic-availability.md)

## Fichiers de données (`cov/*.json`)

**Tous auto-générés — ne pas éditer à la main.** Ils sont rangés dans le
sous-dossier `cov/`. Tous portent un en-tête (`schema_version`,
`unicode_version`) vérifié à leur lecture pour refuser des données périmées
(mauvaise version Unicode, schéma incompatible).

| Fichier | Rôle | Généré par | Lu à l'exécution ? |
|---|---|---|---|
| `unicode-sequences.json` | Registre **source** des séquences Unicode (variations standardisées + variations emoji + IVD ; séquences emoji + séquences ZWJ), recopié depuis Unicode et l'IVD | `_update_unicode_font_data` | **Non** — c'est l'*entrée* de la génération |
| `font-capabilities.json` | Par police : plages de caractères couverts, séquences de variation annoncées (table `cmap` format 14), écritures gérées (tables OpenType GSUB/GPOS) | `_gen_char_cov` | **Oui** (`provider.py`) |
| `font-to-characters.json` | Par police : la liste des caractères qu'elle couvre | `_gen_char_cov` | **Oui** (`provider.py`) |
| `sequence-to-font.json` | Par séquence (drapeau, emoji ZWJ, variation…) : la police à utiliser pour la rendre | `_gen_char_cov` | **Oui** (`provider.py`) |
| `_coverage-report.json` | **Rapport d'audit** : taux de couverture, caractères/séquences manquants, contrôle de rendu HarfBuzz | `_gen_char_cov` | **Non** — lu par `_cov_stats` |

> Sigles : *IVD* = Ideographic Variation Database (variantes de forme des
> sinogrammes) ; *ZWJ* = Zero Width Joiner, le « liant invisible » qui compose
> plusieurs emojis en un seul (familles, métiers…) ; *cmap* = la table
> caractère → glyphe d'une police ; *GSUB/GPOS* = les tables OpenType de mise en
> forme avancée (ligatures/formes contextuelles, et positionnement).

### Pourquoi JSON, et pas des modules Python ?

Ces fichiers sont volumineux (0,4–0,8 Mo chacun) et entièrement auto-générés.
`json.load` (écrit en C) charge les trois fichiers lus à l'exécution en **~23 ms
au total**. Un module Python équivalent (gros dictionnaire littéral) serait au
mieux aussi rapide, mais plus lourd à compiler au premier import, illisible
(dictionnaires de dizaines de milliers d'entrées que personne ne lit à la main)
et générerait d'énormes diffs git à chaque régénération. Le format JSON est donc
volontaire.

## (Re)génération

L'ordre compte : les artefacts dépendent du registre source.

1. **Registre Unicode** — uniquement quand on change de version Unicode / IVD :

   ```
   python -m videre.fonts._update_unicode_font_data
   ```

   Télécharge les données depuis Unicode et l'IVD, puis réécrit
   `unicode-sequences.json`.

2. **Artefacts de couverture** — après tout ajout/retrait de police ou tout
   changement du registre ci-dessus :

   ```
   python -m videre.fonts._gen_char_cov
   ```

   Lit `unicode-sequences.json` + les polices embarquées, puis réécrit
   `font-capabilities.json`, `font-to-characters.json`, `sequence-to-font.json`
   et `_coverage-report.json`.

3. **Inspection** (optionnel) :

   ```
   python -m videre.fonts._cov_stats
   ```

   Affiche les statistiques de couverture à partir de `_coverage-report.json`.

## Code principal

- `provider.py` — `FontProvider` : charge `font-to-characters`,
  `font-capabilities` et `sequence-to-font` au démarrage ; `get_font_info(char)`
  et `get_font_info_for_cluster(text)` choisissent la police.
- `_unicode_sequences.py` — chargement validé de `unicode-sequences.json`.
- `_update_unicode_font_data.py` — (re)télécharge les registres Unicode/IVD et
  réécrit `unicode-sequences.json` ; à lancer via
  `python -m videre.fonts._update_unicode_font_data`.
- `_gen_char_cov.py` — génère les quatre artefacts.
- `_cov_stats.py` — rapport lisible à partir de `_coverage-report.json`.
- `_audit_fonts.py` — compare les polices locales à leur upstream et repère les
  familles Noto à ajouter ; régénère `FONT_UPDATE_AUDIT.md` via
  `python -m videre.fonts._audit_fonts` (réseau, exécution délibérée).
- `font_utils.py` — accès bas niveau aux fichiers de police.

Les primitives Unicode partagées vivent désormais dans
[`../core/textual/`](../core/textual/) — profil de couverture et capacités
OpenType (`coverage.py`), propriétés par caractère (`unicode_char.py`) et
propriétés versionnées 16.0 (`unicode_props.py`) — et sont importées par les
modules ci-dessus.
