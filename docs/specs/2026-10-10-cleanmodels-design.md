# CleanModels — Spécification de conception

- **Date** : 2026-10-10
- **Statut** : en relecture
- **Version cible** : 1.0.0

## 1. Objectif

CleanModels aide l'utilisateur de ComfyUI à libérer de l'espace disque en repérant les
modèles qu'aucun de ses workflows n'utilise, ainsi que les doublons et les fichiers
parasites, puis en lui permettant de les supprimer de façon contrôlée.

### Critères de nettoyage

| Priorité | Critère | Description |
|---|---|---|
| Principal | **Non référencé** | Le modèle n'est cité par aucun workflow de référence. |
| Secondaire | **Doublon** | Un autre fichier a un contenu strictement identique. |
| Secondaire | **Motif de nom** | Le nom correspond à un motif de fichier parasite (téléchargement incomplet, temporaire…). |

### Critères de réussite

- L'utilisateur voit les modèles utilisés avec le nombre d'appels, et les modèles non utilisés.
- Aucun fichier n'est supprimé sans sélection explicite **et** confirmation d'un avertissement de suppression définitive.
- L'outil fonctionne sur toute version de Python ≥ 3.10 sans aucune dépendance externe.

## 2. Contraintes techniques

- **Langage** : Python, **bibliothèque standard uniquement** (aucun `pip install`).
- **Version minimale** : Python 3.10. Aucune fonctionnalité postérieure à 3.10 n'est utilisée.
- **Interface** : tkinter / ttk (inclus dans Python).
- **Plateforme** : Windows en priorité ; le moteur n'utilise que des API portables (`pathlib`, `os`).
- **Versionnement** : SemVer. Les versions 1.x restent compatibles entre elles, notamment
  le format du fichier de réglages (champ `config_version`).

## 3. Périmètre

### Workflows de référence

- `<ComfyUI>/user/default/workflows/`, sous-dossiers compris, fichiers `*.json`.
- Plus les **dossiers de workflows supplémentaires** ajoutés à la main par l'utilisateur
  (mémorisés dans les réglages, retirables). Un dossier ajouté introuvable est signalé et
  ignoré, sans être retiré de la liste. Pas de détection automatique d'autres profils.
- Le chemin `<ComfyUI>` est fourni par l'utilisateur (libellé « Dossier d'installation de
  Votre ComfyUI »).
- La fenêtre **Périmètre du contrôle** (bouton « Périmètre et analyse… ») affiche les dossiers
  de workflows de référence et les dossiers de modèles analysés, avec leur origine (`models` ou
  section de `extra_model_paths.yaml`) et la cible réelle des liens symboliques / jonctions.
  Chaque dossier disponible a une case, **cochée par défaut à chaque ouverture** (décochages non
  mémorisés). Le bouton **Analyser** de cette fenêtre analyse les seuls dossiers cochés ; il est
  grisé si aucun dossier de modèles n'est coché. Un dossier de modèles décoché est exclu de tout
  (utilisés, non utilisés, doublons, parasites). Un dossier de workflows décoché n'est pas lu à
  l'analyse, mais **reste relu lors de la revérification avant suppression** : un modèle qu'il
  utilise ne peut pas être supprimé (avertissement affiché dans la fenêtre et dans la confirmation).

### Dossiers analysés

- `<ComfyUI>/models/`
- Les chemins déclarés dans `<ComfyUI>/extra_model_paths.yaml` (s'il existe).
- Dans chacune de ces racines, **seules** ces catégories sont analysées :
  `checkpoints`, `controlnet`, `diffusion_models`, `LLM`, `model_patches`,
  `text_encoders`, `unet`, `vae`.
- Les liens symboliques et jonctions sont suivis. Un même fichier physique atteint par
  plusieurs chemins n'est compté qu'une fois (dédoublonnage par chemin réel résolu).

### Hors périmètre (v1)

- Les autres catégories (`loras`, `upscale_models`, `clip_vision`…).
- Les workflows intégrés aux images PNG ou situés hors de `user/default/workflows/`.
- Le signalement des modèles référencés mais absents du disque.
- La quarantaine et la Corbeille : la suppression est définitive (sur validation).

## 4. Architecture

Le **moteur**, sans interface, est entièrement testable. L'**interface** tkinter ne fait
qu'afficher les résultats et appeler le moteur.

```
CleanModels/
├─ cleanmodels/
│  ├─ __init__.py        # __version__ = "1.0.0"
│  ├─ __main__.py        # point d'entrée : python -m cleanmodels
│  ├─ settings.py        # réglages utilisateur (JSON versionné)
│  ├─ yaml_lite.py       # lecteur YAML minimal pour extra_model_paths.yaml
│  ├─ roots.py           # validation du dossier ComfyUI + liste des dossiers à analyser
│  ├─ inventory.py       # inventaire des fichiers modèles
│  ├─ workflows.py       # extraction des références depuis les workflows
│  ├─ matching.py        # correspondance références ↔ fichiers, comptage
│  ├─ duplicates.py      # recherche de doublons (taille puis SHA-256)
│  ├─ junk.py            # fichiers parasites par motifs
│  ├─ deletion.py        # revalidation, suppression, journal
│  └─ gui/
│     ├─ app.py          # fenêtre principale, sélection du chemin, analyse
│     ├─ tabs.py         # onglets Utilisés / Non utilisés / Doublons / Parasites
│     └─ dialogs.py      # confirmation de suppression, détail d'un modèle, bilan
├─ tests/                # unittest
├─ docs/specs/
├─ run_cleanmodels.bat   # lanceur Windows (py -3 -m cleanmodels)
└─ README.md
```

### Unités du moteur

| Module | Entrée | Sortie |
|---|---|---|
| `yaml_lite` | texte YAML | `dict` imbriqué de chaînes |
| `roots` | chemin ComfyUI | liste de `ModelDir(category, path, origin)` |
| `inventory` | liste de `ModelDir` | liste de `ModelFile(path, real_path, category, rel_path, size, root)` |
| `workflows` | dossier des workflows | liste de `Reference(value, workflow, node_id, node_type)` + liste des erreurs de lecture |
| `matching` | fichiers + références | `UsageReport` : utilisés (avec appels et workflows), non utilisés |
| `duplicates` | fichiers + rappel de progression + jeton d'annulation | groupes de doublons |
| `junk` | dossiers + motifs | liste de fichiers parasites |
| `deletion` | fichiers sélectionnés + contexte | `DeletionResult` (supprimés, échecs) + écriture du journal |

## 5. Règles détaillées

### 5.1 Lecture de `extra_model_paths.yaml` (`yaml_lite`)

Sous-ensemble YAML géré, suffisant pour le format ComfyUI :

- commentaires `#` (ligne entière ou fin de ligne hors guillemets) et lignes vides ;
- mappings imbriqués par indentation (espaces) ;
- valeurs scalaires simples, entre guillemets simples ou doubles ;
- blocs littéraux `|` (une valeur par ligne → plusieurs chemins).

Interprétation :

- Chaque section de premier niveau (ex. `comfyui:`, `a111:`) est un ensemble de chemins.
- `base_path` est la base des chemins relatifs de la section ; `~` et les variables
  d'environnement sont développés. Sans `base_path`, la base est le dossier du fichier YAML.
- Les clés `is_default` et `base_path` ne sont pas des catégories.
- Une clé de catégorie dont la valeur contient plusieurs lignes déclare plusieurs dossiers.
- Seules les clés correspondant aux 8 catégories retenues sont prises en compte
  (comparaison insensible à la casse).
- Les dossiers déclarés mais inexistants sont signalés dans le résumé et ignorés.
- Une erreur de syntaxe dans le fichier est signalée clairement ; l'analyse continue
  avec `<ComfyUI>/models/` seul.

### 5.2 Inventaire (`inventory`)

- Parcours récursif de chaque dossier de catégorie.
- Extensions de modèles : `.safetensors`, `.ckpt`, `.pt`, `.pth`, `.bin`, `.gguf`, `.sft`, `.onnx`.
- Pour le dossier `LLM`, qui contient souvent des modèles en plusieurs fichiers dans
  un sous-dossier, chaque fichier modèle est inventorié individuellement (même règle).
- `rel_path` = chemin du fichier relatif au dossier de catégorie (ex. `flux\model.safetensors`).
- Les fichiers inaccessibles (droits) sont signalés et ignorés.

### 5.3 Extraction des références (`workflows`)

- Formats gérés :
  - **format interface** : objet avec une liste `nodes` ; les nœuds des sous-graphes
    (`definitions.subgraphs[*].nodes`) sont aussi parcourus ;
  - **format API** : objet dont les valeurs sont des nœuds `{class_type, inputs}`.
- Dans chaque nœud, on parcourt récursivement `widgets_values` (format interface) ou
  `inputs` (format API) et on retient toute chaîne se terminant par une extension de modèle.
- Le champ `properties.models` (métadonnées de téléchargement) est **ignoré**, pour ne pas
  compter deux fois un même usage.
- Une même chaîne citée plusieurs fois dans un même nœud compte pour **un** appel.
- Les autres chaînes courtes (une ligne, 255 caractères au plus) sont aussi relevées comme
  **références par nom** : certains chargeurs LLM désignent un modèle par son dossier
  (ex. `Qwen2.5-VL` ou `Qwen/Qwen2.5-VL-3B`).
- Un fichier JSON illisible ou de structure inconnue est listé dans le résumé
  (« workflows ignorés ») sans interrompre l'analyse.

### 5.4 Correspondance (`matching`)

Normalisation : séparateurs unifiés (`\`), casse ignorée, espaces de début et de fin retirés,
forme Unicode NFC (accents composés ou décomposés équivalents).

Les autres chemins d'un même fichier physique (liens, liens durs) sont des **alias** :
une référence à un alias rend le fichier utilisé.

Une **référence par nom** (sans extension de modèle) ne concerne que la catégorie `LLM` :
elle rend utilisés tous les fichiers situés sous un dossier dont le chemin relatif, ou le
nom, est égal à la référence (ou à son dernier segment).

Pour chaque référence :

1. **Correspondance exacte** : la référence normalisée est égale au `rel_path` normalisé
   d'un ou plusieurs fichiers → ces fichiers sont utilisés.
2. **Sinon, par nom de fichier** : le nom de fichier de la référence est égal au nom d'un
   ou plusieurs fichiers → ces fichiers sont utilisés.
3. Sinon, la référence est ignorée (modèle absent ou hors périmètre, ex. LoRA).

Comptage pour chaque fichier utilisé :

- **Appels** = nombre de nœuds (tous workflows confondus) dont une référence correspond au fichier.
- **Workflows** = nombre de fichiers workflow distincts concernés.

Un fichier sans aucun appel est **non utilisé**.

### 5.5 Doublons (`duplicates`)

- Lancement **à la demande** par le bouton « Rechercher les doublons » (le calcul est long).
- Étape 1 : regroupement par taille exacte ; les tailles uniques sont écartées.
- Étape 2 : pour les candidats, empreinte SHA-256 lue par blocs de 8 Mio.
- Progression affichée (octets traités / total) ; annulation possible.
- Chaque groupe indique pour chaque copie si elle est **référencée** par un workflow
  (selon la règle 5.4).
- Les fichiers qui sont le même fichier physique (lien, jonction) ne sont pas des doublons.

### 5.6 Fichiers parasites (`junk`)

- Recherche dans les mêmes dossiers de catégorie, par motifs `fnmatch` insensibles à la casse.
- Motifs par défaut : `*.part`, `*.crdownload`, `*.tmp`, `*.download`.
- La liste des motifs est modifiable dans l'onglet et enregistrée dans les réglages ;
  un bouton « Rétablir les motifs par défaut » est disponible.

### 5.7 Suppression (`deletion`)

1. Le bouton **Supprimer** d'un onglet n'est actif que si au moins une case est cochée.
2. Fenêtre de confirmation : nombre de fichiers, volume total, liste des chemins
   (avec défilement) et l'avertissement :
   **« Cette suppression est définitive et ne peut pas être annulée. »**
   Boutons : « Annuler » (par défaut, touche Échap) et « Supprimer définitivement ».
3. Revalidation juste avant la suppression de chaque fichier :
   - le fichier existe toujours avec la même taille ;
   - **non utilisés** : les workflows sont relus et le fichier n'est toujours cité par aucun
     (la correspondance ne tient compte que des fichiers encore présents) ; si un workflow
     est illisible, la suppression est refusée, ses références étant inconnues ;
   - **doublons** : au moins une autre copie du groupe existe toujours et n'est pas
     sélectionnée ; l'outil refuse de supprimer toutes les copies d'un groupe. Si la copie
     sélectionnée est référencée, la confirmation le signale spécialement ;
   - **parasites** : le nom correspond toujours à un motif actif.
   Un fichier qui échoue à la revalidation n'est pas supprimé et figure dans le bilan.
4. Suppression par `os.remove` sur le chemin listé (jamais sur la cible d'un lien).
5. Journal `cleanmodels.log` (dossier des réglages) : horodatage, onglet d'origine,
   chemin, taille, résultat (`SUPPRIMÉ` / `REFUSÉ: <raison>` / `ERREUR: <message>`).
6. Une erreur sur un fichier (verrouillé, droits) n'arrête pas les suivants.
7. Bilan affiché : supprimés, refusés, erreurs, espace libéré. Les listes sont ensuite
   mises à jour sans les fichiers supprimés.

## 6. Interface

### Écran principal

- **Dossier ComfyUI** : champ + bouton « Parcourir… ». Validation : présence de
  `models/` et de `user/default/workflows/` ; message clair sinon.
- Le dernier chemin valide est mémorisé.
- **Analyser** : lance réglages → racines → inventaire → workflows → correspondance → parasites
  dans un fil d'exécution en arrière-plan ; l'interface reste réactive ; barre de progression.
- **Résumé** : workflows lus / ignorés, dossiers analysés (avec leur origine : `models` ou
  section YAML), dossiers déclarés introuvables, nombre et volume des modèles.

### Onglets

| Onglet | Colonnes | Actions |
|---|---|---|
| **Utilisés** | Nom, Catégorie, Dossier racine, Taille, Appels, Workflows | Double-clic → liste des workflows et nœuds qui l'utilisent |
| **Non utilisés** | ☐, Nom, Catégorie, Chemin, Taille | Tout sélectionner / Tout désélectionner / **Supprimer** |
| **Doublons** | ☐, Groupe, Chemin, Taille, Référencé | Rechercher les doublons / Annuler / **Supprimer** |
| **Fichiers parasites** | ☐, Nom, Chemin, Taille, Motif | Champ des motifs / Rétablir par défaut / **Supprimer** |

- Toutes les colonnes sont triables par clic sur l'en-tête.
- Les onglets avec cases à cocher affichent « X fichiers sélectionnés – Y Go ».
- Les cases à cocher sont simulées dans un `ttk.Treeview` (symbole ☐/☑ dans la première colonne,
  basculé au clic ou à la barre d'espace).

### Disposition, thème et langue

- Au lancement : fenêtre principale à gauche (60 % de la largeur de l'écran), fenêtre
  « Périmètre du contrôle » ouverte en même temps, collée à sa droite. Elle reste ouverte
  pendant et après l'analyse ; le bouton « Périmètre et analyse… » la rouvre si elle est fermée.
- Bouton **Analyser** en vert (texte blanc gras) ; boutons **Supprimer** gris quand inactifs,
  rouges (texte blanc) quand actifs. Thème ttk « clam » (nécessaire aux couleurs sous Windows).
- **Thème** Clair / Sombre et **Langue** Français / English / Deutsch, choisis uniquement dans
  l'interface (aucune question au démarrage), mémorisés. Défauts : Clair, Français.
- Changer de thème ou de langue reconstruit l'interface : résultats d'analyse, doublons et
  fichiers parasites réaffichés, cases à cocher remises à zéro.
- Le journal `cleanmodels.log` reste en français quelle que soit la langue.

## 7. Réglages

Fichier `%APPDATA%\CleanModels\settings.json` (sur d'autres systèmes : `~/.cleanmodels/`) :

```json
{
  "config_version": 2,
  "comfyui_path": "D:/ComfyUI",
  "junk_patterns": ["*.part", "*.crdownload", "*.tmp", "*.download"],
  "extra_workflow_dirs": ["E:/MesWorkflows"],
  "language": "fr",
  "theme": "light"
}
```

- Clé inconnue : conservée telle quelle (compatibilité avec une version plus récente).
- Clé absente : valeur par défaut.
- Version antérieure : portée à la version courante ; version plus récente : conservée.
- Fichier corrompu : renommé en `settings.json.bak` et remplacé par les valeurs par défaut,
  avec un message à l'utilisateur.

## 8. Gestion des erreurs

| Situation | Comportement |
|---|---|
| Dossier ComfyUI invalide | Message, bouton Analyser désactivé |
| `extra_model_paths.yaml` absent | Normal, analyse de `models/` seul |
| `extra_model_paths.yaml` invalide | Avertissement, analyse de `models/` seul |
| Dossier déclaré introuvable | Listé dans le résumé, ignoré |
| Workflow illisible | Listé dans « workflows ignorés », ignoré |
| Fichier inaccessible à l'inventaire | Listé dans le résumé, ignoré |
| Échec de suppression | Journalisé, présent dans le bilan, la suite continue |
| Exception inattendue | Message d'erreur + trace dans le journal ; l'application reste ouverte |

## 9. Tests

- Framework : `unittest` (bibliothèque standard), lancement : `python -m unittest discover tests`.
- Chaque test construit une fausse installation ComfyUI dans un dossier temporaire
  (`tempfile`), avec de petits fichiers factices.
- Couverture visée du moteur :
  - `yaml_lite` : sections, `base_path`, blocs `|`, commentaires, guillemets, erreurs ;
  - `roots` : filtre des 8 catégories, chemins relatifs/absolus, dossiers manquants ;
  - `inventory` : extensions, sous-dossiers, dédoublonnage par chemin réel ;
  - `workflows` : format interface, sous-graphes, format API, `properties.models` ignoré,
    JSON invalide ;
  - `matching` : correspondance exacte, par nom, casse/séparateurs, comptage appels/workflows ;
  - `duplicates` : groupes par taille puis empreinte, liens non considérés comme doublons ;
  - `junk` : motifs, casse ;
  - `deletion` : revalidations, refus de supprimer toutes les copies, journal, erreurs.
- L'interface est vérifiée manuellement sur une installation de test.
- Les tests sont exécutés sur Python 3.10 et sur la version stable la plus récente
  disponible avant chaque publication.
