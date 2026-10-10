# CleanModels — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** Application de bureau Python/tkinter qui liste les modèles ComfyUI utilisés et non utilisés par les workflows de l'utilisateur, détecte doublons et fichiers parasites, et permet leur suppression définitive après confirmation.

**Architecture :** Un moteur sans interface (`cleanmodels/*.py`), entièrement couvert par `unittest`, produit des dataclasses ; un orchestrateur (`analysis.py`) les enchaîne ; l'interface (`cleanmodels/gui/`) n'affiche que ces résultats et appelle le moteur depuis un fil d'arrière-plan.

**Tech Stack :** Python ≥ 3.10, bibliothèque standard uniquement (`pathlib`, `json`, `hashlib`, `fnmatch`, `threading`, `tkinter/ttk`, `unittest`).

**Spec :** `docs/specs/2026-10-10-cleanmodels-design.md`

## Global Constraints

- Aucune dépendance externe : seuls les modules de la bibliothèque standard sont importés.
- Python 3.10 minimum : interdits `tomllib`, `ExceptionGroup`/`except*`, `typing.Self`, `datetime.UTC`, `TaskGroup`, `StrEnum`, f-strings imbriquant les mêmes guillemets (3.12), `itertools.batched`. Autorisés : `X | None`, `match`, `dataclass(slots=True)`.
- Catégories analysées (exactement) : `checkpoints`, `controlnet`, `diffusion_models`, `LLM`, `model_patches`, `text_encoders`, `unet`, `vae`.
- Extensions de modèles : `.safetensors`, `.ckpt`, `.pt`, `.pth`, `.bin`, `.gguf`, `.sft`, `.onnx`.
- Motifs parasites par défaut : `*.part`, `*.crdownload`, `*.tmp`, `*.download`.
- Workflows de référence : `<ComfyUI>/user/default/workflows/**/*.json` uniquement.
- Réglages : `%APPDATA%\CleanModels\settings.json` (hors Windows : `~/.cleanmodels/`), `config_version: 1`, clés inconnues conservées. Journal : `cleanmodels.log` dans le même dossier. Variable `CLEANMODELS_HOME` : remplace ce dossier (tests).
- Texte de l'avertissement (exact) : « Cette suppression est définitive et ne peut pas être annulée. » ; boutons « Annuler » (défaut, Échap) et « Supprimer définitivement ».
- Toute lecture/écriture de texte en UTF-8 (`utf-8-sig` en lecture pour JSON et YAML).
- Tests : `python -m unittest discover -s tests -v` doit passer sur `py -3.12` et `py -3.14` (installés sur la machine).
- Commits : messages en français, préfixes `feat:`, `test:`, `docs:`, `chore:`, terminés par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Workflow enregistré avec BOM UTF-8** (éditeurs Windows) → lu normalement, pas classé « ignoré ». Test : Task 5.
2. **`extra_model_paths.yaml` en fins de ligne CRLF, chemins Windows `D:\...` avec barres inverses et `base_path` terminé par `/`** → dossiers correctement résolus. Test : Tasks 2 et 3.
3. **Fichier modifié ou supprimé entre l'analyse et la suppression** → refusé avec motif, jamais d'exception. Test : Task 9.
4. **Fichier verrouillé (PermissionError) au milieu d'une sélection** → erreur consignée, les fichiers suivants sont supprimés. Test : Task 9.
5. **Noms de fichiers accentués** (`modèle_été.safetensors`) → correspondance, affichage et journal UTF-8 corrects. Tests : Tasks 6 et 9.

---

## Structure des fichiers

```
cleanmodels/__init__.py      __version__
cleanmodels/constants.py     CATEGORIES, MODEL_EXTENSIONS, DEFAULT_JUNK_PATTERNS
cleanmodels/settings.py      réglages JSON versionnés
cleanmodels/yaml_lite.py     lecteur YAML minimal
cleanmodels/roots.py         validation ComfyUI + dossiers de catégories
cleanmodels/inventory.py     inventaire des modèles
cleanmodels/workflows.py     extraction des références
cleanmodels/matching.py      correspondance + comptage
cleanmodels/duplicates.py    doublons
cleanmodels/junk.py          fichiers parasites
cleanmodels/deletion.py      revalidation, suppression, journal
cleanmodels/analysis.py      orchestration de l'analyse
cleanmodels/__main__.py      point d'entrée
cleanmodels/gui/format.py    format_size
cleanmodels/gui/checktree.py Treeview à cases à cocher
cleanmodels/gui/dialogs.py   confirmation, détail, bilan
cleanmodels/gui/tabs.py      quatre onglets
cleanmodels/gui/app.py       fenêtre principale
tests/helpers.py             fabrique de fausse installation ComfyUI
tests/test_*.py
run_cleanmodels.bat, README.md
```

---

### Task 1 : Squelette, constantes et réglages

**Files :**
- Create : `cleanmodels/__init__.py`, `cleanmodels/constants.py`, `cleanmodels/settings.py`, `tests/__init__.py`, `tests/helpers.py`, `tests/test_settings.py`

**Interfaces :**
- Produces :
  - `cleanmodels.__version__ = "1.0.0"`
  - `constants.CATEGORIES: tuple[str, ...]`, `constants.MODEL_EXTENSIONS: tuple[str, ...]` (minuscules), `constants.DEFAULT_JUNK_PATTERNS: tuple[str, ...]`, `constants.CONFIG_VERSION = 1`
  - `settings.settings_dir() -> Path` (crée le dossier)
  - `settings.load_settings() -> tuple[dict, str | None]` — renvoie (réglages, avertissement éventuel)
  - `settings.save_settings(data: dict) -> None`
  - `tests.helpers.make_comfy(root: Path, files: dict[str, bytes | str]) -> Path` — crée `root/ComfyUI` avec `models/` et `user/default/workflows/`, puis chaque chemin relatif de `files` (bytes écrits tels quels, str en UTF-8) ; renvoie le dossier ComfyUI.
  - `tests.helpers.TempHomeMixin` — `setUp` crée un dossier temporaire, positionne `CLEANMODELS_HOME`, `tearDown` restaure l'environnement et nettoie ; expose `self.tmp: Path`.

- [ ] **Step 1 : Écrire les tests en échec** — `tests/test_settings.py`, classe `SettingsTest(TempHomeMixin, unittest.TestCase)` :
  - `test_defaults_when_missing` : `load_settings()` → `({"config_version": 1, "comfyui_path": "", "junk_patterns": list(DEFAULT_JUNK_PATTERNS)}, None)`.
  - `test_roundtrip_keeps_unknown_keys` : sauver `{"config_version": 1, "comfyui_path": "D:/ComfyUI", "junk_patterns": ["*.tmp"], "future_key": 42}` puis recharger → identique.
  - `test_missing_key_gets_default` : fichier `{"config_version": 1}` → `junk_patterns` vaut la liste par défaut.
  - `test_corrupt_file_is_backed_up` : fichier contenant `{pas du json` → réglages par défaut, avertissement non `None`, `settings.json.bak` existe avec le contenu d'origine.
  - `test_settings_dir_uses_env` : `settings_dir() == self.tmp`.
- [ ] **Step 2 : Lancer** `python -m unittest tests.test_settings -v` → ÉCHEC (`ModuleNotFoundError`).
- [ ] **Step 3 : Implémenter** constantes, `settings.py` (dossier : `CLEANMODELS_HOME` sinon `%APPDATA%\CleanModels` sinon `~/.cleanmodels`), et `tests/helpers.py`. `save_settings` écrit via fichier temporaire + `os.replace`.
- [ ] **Step 4 : Lancer** `python -m unittest discover -s tests -v` → OK.
- [ ] **Step 5 : Commit** `feat: squelette, constantes et réglages versionnés`.

---

### Task 2 : Lecteur YAML minimal

**Files :** Create `cleanmodels/yaml_lite.py`, `tests/test_yaml_lite.py`

**Interfaces :**
- Produces : `yaml_lite.parse(text: str) -> dict` (valeurs : `str` ou `dict` imbriqué) ; `yaml_lite.YamlError(Exception)` avec attribut `line: int` (1-based).

- [ ] **Step 1 : Tests en échec** — `YamlLiteTest` :
  - `test_nested_mapping_and_comments` :
    ```python
    text = "# entête\ncomfyui:\n  base_path: D:/AI/  # fin\n  checkpoints: models/checkpoints\n"
    assert parse(text) == {"comfyui": {"base_path": "D:/AI/", "checkpoints": "models/checkpoints"}}
    ```
  - `test_block_literal` : `"a:\n  unet: |\n    models/unet\n    other/unet\n  vae: v\n"` → `{"a": {"unet": "models/unet\nother/unet", "vae": "v"}}`.
  - `test_quotes` : `k: "a # b"` → `"a # b"` ; `k: 'x'` → `"x"`.
  - `test_crlf_and_backslashes` : `"s:\r\n  base_path: D:\\AI\\\r\n  vae: models\\vae\r\n"` → `{"s": {"base_path": "D:\\AI\\", "vae": "models\\vae"}}` *(Review Focus 2)*.
  - `test_empty_value_is_empty_dict_or_string` : `"s:\n"` → `{"s": {}}`.
  - `test_bad_indent_raises` : `"s:\n  a: 1\n b: 2\n"` → `YamlError` avec `line == 3`.
  - `test_tab_indent_raises` : ligne indentée par tabulation → `YamlError`.
- [ ] **Step 2 : Lancer** `python -m unittest tests.test_yaml_lite -v` → ÉCHEC.
- [ ] **Step 3 : Implémenter `parse`.** Pile de `(indent, dict)` ; `clé: valeur` ; `clé:` seule ouvre un mapping (vide si rien ne suit plus indenté) ; `clé: |` lit les lignes suivantes plus indentées que la clé, retire l'indentation commune, joint par `\n`, sans `\n` final ; commentaire = `#` précédé d'un espace hors guillemets ; listes `- x` non gérées → `YamlError`.
- [ ] **Step 4 : Lancer** → OK.
- [ ] **Step 5 : Commit** `feat: lecteur YAML minimal pour extra_model_paths.yaml`.

---

### Task 3 : Racines (dossier ComfyUI et dossiers de catégories)

**Files :** Create `cleanmodels/roots.py`, `tests/test_roots.py`

**Interfaces :**
- Consumes : `yaml_lite.parse`, `YamlError`, `constants.CATEGORIES`.
- Produces :
  - `@dataclass(frozen=True) ModelDir(category: str, path: Path, origin: str)` — `category` = nom canonique de `CATEGORIES` ; `origin` = `"models"` ou `"yaml:<section>"`.
  - `@dataclass RootsResult(dirs: list[ModelDir], missing: list[ModelDir], warnings: list[str])`
  - `validate_comfyui(path: Path) -> str | None` — message d'erreur en français ou `None`.
  - `workflows_dir(comfy: Path) -> Path` = `comfy / "user" / "default" / "workflows"`.
  - `collect_model_dirs(comfy: Path) -> RootsResult`

- [ ] **Step 1 : Tests en échec** — avec `make_comfy` :
  - `test_validate_ok` / `test_validate_missing_workflows` (message contient `user/default/workflows`) / `test_validate_not_a_dir`.
  - `test_models_dir_filtered_to_categories` : `models/checkpoints/a.safetensors`, `models/loras/b.safetensors`, `models/VAE/c.pt` → `dirs` contient `checkpoints` et `vae` (catégorie canonique `vae`), pas `loras`.
  - `test_yaml_relative_to_base_path` : YAML `extra:\n  base_path: <tmp>/ext/\n  unet: |\n    m/unet\n    n/unet\n  loras: l\n  is_default: true\n` avec `ext/m/unet` existant et `ext/n/unet` absent → `ModelDir("unet", ext/m/unet, "yaml:extra")` dans `dirs`, `ext/n/unet` dans `missing`, aucune entrée `loras`.
  - `test_yaml_without_base_path_is_relative_to_comfy`.
  - `test_yaml_windows_paths_crlf` : YAML CRLF, `base_path: <tmp>\ext\` (barres inverses) → dossier résolu *(Review Focus 2)*.
  - `test_yaml_invalid_falls_back` : YAML invalide → `dirs` contient les dossiers de `models/`, `warnings` a 1 message mentionnant `extra_model_paths.yaml`.
  - `test_same_dir_declared_twice_listed_once` : YAML qui redéclare `<comfy>/models/checkpoints` → un seul `ModelDir` pour ce chemin réel.
- [ ] **Step 2 : Lancer** `python -m unittest tests.test_roots -v` → ÉCHEC.
- [ ] **Step 3 : Implémenter.** Correspondance des catégories insensible à la casse ; `os.path.expandvars` + `expanduser` ; chemins relatifs joints à `base_path` (sinon au dossier ComfyUI) ; dédoublonnage par `os.path.normcase(os.path.realpath(p))`.
- [ ] **Step 4 : Lancer** → OK.
- [ ] **Step 5 : Commit** `feat: résolution des dossiers de modèles (models + extra_model_paths)`.

---

### Task 4 : Inventaire

**Files :** Create `cleanmodels/inventory.py`, `tests/test_inventory.py`

**Interfaces :**
- Consumes : `roots.ModelDir`, `constants.MODEL_EXTENSIONS`.
- Produces :
  - `@dataclass(frozen=True) ModelFile(path: Path, real_path: Path, category: str, rel_path: str, size: int, root: Path)` — `rel_path` relatif au dossier de catégorie, séparateur `os.sep`.
  - `@dataclass InventoryResult(files: list[ModelFile], errors: list[str])`
  - `scan_models(dirs: list[ModelDir]) -> InventoryResult`
  - `file_key(path: Path) -> str` = `os.path.normcase(os.path.realpath(path))` (réutilisé par matching, duplicates, gui).

- [ ] **Step 1 : Tests en échec** :
  - `test_lists_model_extensions_recursively` : `checkpoints/a.safetensors`, `checkpoints/sub/b.GGUF`, `checkpoints/readme.txt` → 2 fichiers ; `rel_path` de b = `os.path.join("sub", "b.GGUF")` ; `size` correct.
  - `test_llm_multifile_each_listed` : `LLM/qwen/model-00001.safetensors`, `LLM/qwen/model-00002.safetensors`, `LLM/qwen/config.json` → 2 fichiers.
  - `test_symlinked_dir_counted_once` : lien symbolique de répertoire vers un dossier déjà inventorié (utiliser `os.symlink(..., target_is_directory=True)` ; `skipTest` si `OSError` faute de privilège) → chaque fichier une seule fois.
  - `test_hardlink_counted_once` : `os.link` → une seule entrée.
- [ ] **Step 2 : Lancer** → ÉCHEC.
- [ ] **Step 3 : Implémenter** avec `os.walk(followlinks=True)` ; dédoublonnage par `file_key` puis par `(st_dev, st_ino)` quand `st_ino != 0` ; `OSError` → message dans `errors`.
- [ ] **Step 4 : Lancer** → OK.
- [ ] **Step 5 : Commit** `feat: inventaire des fichiers modèles`.

---

### Task 5 : Extraction des références des workflows

**Files :** Create `cleanmodels/workflows.py`, `tests/test_workflows.py`

**Interfaces :**
- Consumes : `constants.MODEL_EXTENSIONS`.
- Produces :
  - `@dataclass(frozen=True) Reference(value: str, workflow: Path, node_id: str, node_type: str)`
  - `@dataclass WorkflowScan(references: list[Reference], workflow_count: int, skipped: list[tuple[Path, str]])` — `workflow_count` = fichiers lus avec succès.
  - `references_from_json(data: object, workflow: Path) -> list[Reference]` — lève `ValueError` si structure inconnue.
  - `scan_workflows(folder: Path) -> WorkflowScan`

- [ ] **Step 1 : Tests en échec** :
  - `test_ui_format` : `{"nodes": [{"id": 4, "type": "CheckpointLoaderSimple", "widgets_values": ["sd\\a.safetensors"]}]}` → `[Reference("sd\\a.safetensors", wf, "4", "CheckpointLoaderSimple")]`.
  - `test_nested_widget_values_dict` : `widgets_values: {"model": "x.gguf", "n": 3}` → une référence `x.gguf`.
  - `test_subgraph_nodes` : référence dans `definitions.subgraphs[0].nodes` → trouvée.
  - `test_api_format` : `{"3": {"class_type": "UNETLoader", "inputs": {"unet_name": "f.sft", "w": "default"}}}` → `Reference("f.sft", wf, "3", "UNETLoader")`.
  - `test_properties_models_ignored` : nœud avec `properties.models = [{"name": "z.safetensors"}]` et `widgets_values: []` → aucune référence.
  - `test_same_value_twice_in_node_counts_once`.
  - `test_extension_case_insensitive` : `"A.SafeTensors"` retenu ; `"photo.png"` ignoré.
  - `test_scan_skips_invalid_json` : `bad.json` = `{oups` et `ok.json` valide dans un sous-dossier → `workflow_count == 1`, `skipped[0][0].name == "bad.json"`.
  - `test_scan_reads_utf8_bom` : fichier écrit avec `encoding="utf-8-sig"` → lu, `skipped == []` *(Review Focus 1)*.
  - `test_unknown_structure_skipped` : `[1, 2]` → dans `skipped`.
- [ ] **Step 2 : Lancer** → ÉCHEC.
- [ ] **Step 3 : Implémenter.** Format interface si `dict` avec `nodes` liste ; format API si `dict` non vide dont toutes les valeurs sont des `dict` contenant `class_type` ; sinon `ValueError`. Parcours récursif (listes, dicts) des chaînes ; filtre `value.strip().lower().endswith(MODEL_EXTENSIONS)` ; `rglob("*.json")` trié.
- [ ] **Step 4 : Lancer** → OK.
- [ ] **Step 5 : Commit** `feat: extraction des références de modèles dans les workflows`.

---

### Task 6 : Correspondance et comptage

**Files :** Create `cleanmodels/matching.py`, `tests/test_matching.py`

**Interfaces :**
- Consumes : `ModelFile`, `file_key`, `Reference`.
- Produces :
  - `normalize(value: str) -> str` — `strip`, `/`→`\`, `casefold`.
  - `class FileIndex` : `__init__(files: list[ModelFile])`, `lookup(value: str) -> list[ModelFile]` (règle 1 : `rel_path` normalisé exact ; sinon règle 2 : nom de fichier normalisé ; sinon `[]`).
  - `@dataclass Usage(file: ModelFile, calls: int, workflows: list[Path], references: list[Reference])`
  - `@dataclass UsageReport(used: list[Usage], unused: list[ModelFile])`
  - `match_usage(files: list[ModelFile], references: list[Reference]) -> UsageReport`

- [ ] **Step 1 : Tests en échec** :
  - `test_exact_rel_path_wins_over_name` : fichiers `checkpoints/flux/m.safetensors` et `checkpoints/sdxl/m.safetensors`, référence `"flux/M.safetensors"` → seul le fichier `flux` est utilisé.
  - `test_basename_fallback_matches_all_same_name` : référence `"m.safetensors"` sans sous-dossier ne correspondant à aucun `rel_path` → les deux fichiers sont utilisés.
  - `test_absolute_path_reference_matches_by_name` : `"D:\\AI\\models\\vae\\v.pt"` → `vae/v.pt`.
  - `test_calls_and_workflows_counts` : 3 références du même fichier, dans 2 nœuds de `w1.json` et 1 nœud de `w2.json` → `calls == 3`, `len(workflows) == 2`.
  - `test_unreferenced_goes_to_unused` et `test_lora_reference_ignored` (référence sans fichier → aucun effet).
  - `test_accented_names` : fichier `modèle_été.safetensors`, référence `"MODÈLE_ÉTÉ.safetensors"` → utilisé *(Review Focus 5)*.
- [ ] **Step 2 : Lancer** → ÉCHEC.
- [ ] **Step 3 : Implémenter** (clé des fichiers = `file_key`, `workflows` triés, sans doublon).
- [ ] **Step 4 : Lancer** → OK.
- [ ] **Step 5 : Commit** `feat: correspondance références/fichiers et comptage des appels`.

---

### Task 7 : Doublons

**Files :** Create `cleanmodels/duplicates.py`, `tests/test_duplicates.py`

**Interfaces :**
- Consumes : `ModelFile`.
- Produces :
  - `class Cancelled(Exception)`
  - `@dataclass DuplicateGroup(digest: str, size: int, files: list[ModelFile])`
  - `find_duplicates(files: list[ModelFile], progress: Callable[[int, int], None] | None = None, cancel: threading.Event | None = None, chunk_size: int = 8 * 1024 * 1024) -> list[DuplicateGroup]` — `progress(octets_traités, total)` ; groupes triés par taille décroissante ; fichiers d'un groupe triés par chemin.

- [ ] **Step 1 : Tests en échec** :
  - `test_identical_content_grouped` : `a` et `b` = `b"x" * 1000`, `c` = `b"y" * 1000`, `d` = `b"x" * 999` → un groupe `[a, b]`, digest = `hashlib.sha256(b"x"*1000).hexdigest()`.
  - `test_unique_sizes_not_hashed` : `progress` reçoit un total égal à la somme des tailles des seuls candidats (taille partagée).
  - `test_cancel_raises` : `cancel` positionné depuis le premier appel de `progress`, `chunk_size=10` → `Cancelled`.
  - `test_unreadable_file_skipped` : fichier supprimé après inventaire → ignoré, pas d'exception.
- [ ] **Step 2 : Lancer** → ÉCHEC.
- [ ] **Step 3 : Implémenter** (regroupement par `size`, SHA-256 par blocs, vérification de `cancel` entre chaque bloc).
- [ ] **Step 4 : Lancer** → OK.
- [ ] **Step 5 : Commit** `feat: recherche de doublons par taille puis SHA-256`.

---

### Task 8 : Fichiers parasites

**Files :** Create `cleanmodels/junk.py`, `tests/test_junk.py`

**Interfaces :**
- Consumes : `ModelDir`.
- Produces :
  - `@dataclass(frozen=True) JunkFile(path: Path, category: str, size: int, pattern: str)`
  - `match_pattern(name: str, patterns: list[str]) -> str | None` — premier motif correspondant, insensible à la casse (`fnmatch.fnmatchcase` sur `casefold`).
  - `find_junk(dirs: list[ModelDir], patterns: list[str]) -> list[JunkFile]` — récursif, dédoublonné par `file_key`, trié par chemin.

- [ ] **Step 1 : Tests en échec** : `test_default_patterns` (`a.part`, `b.CRDOWNLOAD`, `c.safetensors` → 2 résultats, `pattern` renseigné) ; `test_custom_pattern` (`["*.old"]`) ; `test_empty_patterns_returns_nothing`.
- [ ] **Step 2 : Lancer** → ÉCHEC.
- [ ] **Step 3 : Implémenter.**
- [ ] **Step 4 : Lancer** → OK.
- [ ] **Step 5 : Commit** `feat: détection des fichiers parasites par motifs`.

---

### Task 9 : Suppression, revalidation et journal

**Files :** Create `cleanmodels/deletion.py`, `tests/test_deletion.py`

**Interfaces :**
- Consumes : `ModelFile`, `scan_workflows`, `FileIndex`, `DuplicateGroup`, `match_pattern`, `file_key`.
- Produces :
  - `@dataclass(frozen=True) DeletionItem(path: Path, size: int, source: str)` — `source ∈ {"unused", "duplicates", "junk"}`.
  - `@dataclass DeletionResult(deleted: list[DeletionItem], refused: list[tuple[DeletionItem, str]], errors: list[tuple[DeletionItem, str]])` + propriété `freed_bytes: int`.
  - `Checker = Callable[[DeletionItem], str | None]` (motif de refus ou `None`).
  - `unused_checker(workflows_folder: Path, files: list[ModelFile]) -> Checker` — relit les workflows **une fois** à la création ; refuse (`"cité par un workflow"`) si une référence actuelle désigne ce fichier via `FileIndex(files)`.
  - `duplicates_checker(groups: list[DuplicateGroup], selected: set[str]) -> Checker` — `selected` = `file_key` des cases cochées ; refuse (`"aucune autre copie conservée"`) si aucune autre copie du groupe n'existe hors sélection.
  - `fully_selected_groups(groups: list[DuplicateGroup], selected: set[str]) -> list[DuplicateGroup]` — pour bloquer la confirmation.
  - `junk_checker(patterns: list[str]) -> Checker` — refuse (`"ne correspond plus à un motif"`).
  - `delete_files(items: list[DeletionItem], checker: Checker, log_path: Path) -> DeletionResult`

- [ ] **Step 1 : Tests en échec** :
  - `test_deletes_and_logs` : supprime 2 fichiers ; journal UTF-8 avec une ligne par fichier, champs séparés par tabulation : horodatage ISO, `source`, `SUPPRIMÉ`, taille, chemin.
  - `test_missing_or_changed_file_refused` : un fichier supprimé et un fichier dont la taille a changé depuis la création de l'item → `refused` avec motifs `"fichier introuvable"` et `"taille modifiée"`, aucune exception *(Review Focus 3)*.
  - `test_permission_error_continues` : `unittest.mock.patch("os.remove")` levant `PermissionError` pour le 1er fichier seulement → 1 entrée `errors` (journal `ERREUR: ...`), 2e fichier supprimé *(Review Focus 4)*.
  - `test_unused_checker_refuses_newly_referenced` : workflow ajouté après l'analyse citant le fichier → refusé, journal `REFUSÉ: cité par un workflow`.
  - `test_duplicates_keeps_one_copy` : groupe `[a, b]`, sélection `{a, b}` → `fully_selected_groups` renvoie le groupe ; avec `delete_files` sur `a` et `b` et ce checker, les deux sont refusés et restent sur le disque ; avec la sélection `{a}`, `a` est supprimé.
  - `test_junk_checker` : motif retiré → refusé.
  - `test_accented_path_logged` : `modèle_été.safetensors` → la ligne du journal relue en UTF-8 contient ce nom *(Review Focus 5)*.
- [ ] **Step 2 : Lancer** → ÉCHEC.
- [ ] **Step 3 : Implémenter.** Ordre par item : existence (`os.path.lexists` puis `is_file`), taille, `checker`, puis `os.remove(path)` ; `duplicates_checker` accepte un fichier seulement si une autre copie du groupe existe réellement sur le disque **et** n'est pas dans `selected` (vérifié au moment de l'appel).
- [ ] **Step 4 : Lancer** → OK.
- [ ] **Step 5 : Commit** `feat: suppression revalidée avec journal`.

---

### Task 10 : Orchestration de l'analyse

**Files :** Create `cleanmodels/analysis.py`, `tests/test_analysis.py`

**Interfaces :**
- Consumes : `collect_model_dirs`, `workflows_dir`, `scan_models`, `scan_workflows`, `match_usage`, `find_junk`.
- Produces :
  - `@dataclass AnalysisResult(comfy: Path, roots: RootsResult, inventory: InventoryResult, workflows: WorkflowScan, usage: UsageReport, junk: list[JunkFile])` + propriété `total_bytes: int`.
  - `run_analysis(comfy: Path, junk_patterns: list[str], progress: Callable[[str], None] | None = None) -> AnalysisResult` — `progress` reçoit un libellé d'étape en français (« Lecture des dossiers… », « Inventaire des modèles… », « Lecture des workflows… », « Correspondance… », « Fichiers parasites… »).

- [ ] **Step 1 : Test en échec** `test_end_to_end` : fausse installation avec 3 modèles dont 1 référencé 2 fois, 1 workflow invalide, 1 `x.part`, un YAML ajoutant un dossier `unet` externe → `len(usage.used) == 1`, `usage.used[0].calls == 2`, `len(usage.unused) == 2`, `len(workflows.skipped) == 1`, `len(junk) == 1`, 5 libellés reçus par `progress`.
- [ ] **Step 2 : Lancer** → ÉCHEC.
- [ ] **Step 3 : Implémenter.**
- [ ] **Step 4 : Lancer** `python -m unittest discover -s tests -v` → OK.
- [ ] **Step 5 : Commit** `feat: orchestration de l'analyse`.

---

### Task 11 : Composants d'interface de base (format, Treeview à cases, dialogues)

**Files :** Create `cleanmodels/gui/__init__.py`, `cleanmodels/gui/format.py`, `cleanmodels/gui/checktree.py`, `cleanmodels/gui/dialogs.py`, `tests/test_gui_widgets.py`

**Interfaces :**
- Produces :
  - `format_size(n: int) -> str` — base 1024, une décimale, virgule française : `0 → "0 o"`, `1536 → "1,5 Ko"`, `5 * 1024**3 → "5,0 Go"`.
  - `class CheckTree(ttk.Frame)` : `__init__(master, columns: list[tuple[str, str, int]], on_selection_change: Callable[[], None])` (id, titre, largeur) ; `set_rows(rows: list[tuple[str, tuple, int]])` (clé, valeurs affichées, taille en octets pour le compteur) ; `checked_keys() -> list[str]` ; `check_all()`, `uncheck_all()`, `toggle(key: str)` ; tri par clic d'en-tête (numérique si la colonne est déclarée numérique via un id finissant par `_n`) ; clic dans la colonne ☐ ou barre d'espace → `toggle`.
  - `class SortableTree(ttk.Frame)` : même chose sans cases (onglet Utilisés), `set_rows`, `bind_double_click(callback: Callable[[str], None])`.
  - `confirm_deletion(parent, paths: list[Path], total_bytes: int, notes: list[str]) -> bool` — modale ; texte exact de l'avertissement et des boutons (Global Constraints) ; `notes` affichées en rouge (ex. copies référencées).
  - `show_details(parent, title: str, lines: list[str]) -> None` ; `show_report(parent, result: DeletionResult) -> None` (supprimés, refusés avec motifs, erreurs, espace libéré via `format_size`).

- [ ] **Step 1 : Tests en échec** — `format_size` (3 valeurs ci-dessus) ; `CheckTreeTest` (créé sur `tk.Tk()` masqué, `skipTest` si `tk.TclError`) : `set_rows` de 3 lignes, `toggle("b")` → `checked_keys() == ["b"]` et `on_selection_change` appelé ; `check_all()` → 3 clés ; `uncheck_all()` → `[]` ; `set_rows` vide les coches.
- [ ] **Step 2 : Lancer** `python -m unittest tests.test_gui_widgets -v` → ÉCHEC.
- [ ] **Step 3 : Implémenter.** Coche = symbole `☐`/`☑` dans une première colonne `check` (largeur 30, non triable) ; `show="headings"`.
- [ ] **Step 4 : Lancer** → OK.
- [ ] **Step 5 : Commit** `feat: composants d'interface (tableaux triables, cases, dialogues)`.

---

### Task 12 : Fenêtre principale, onglets et point d'entrée

**Files :** Create `cleanmodels/gui/tabs.py`, `cleanmodels/gui/app.py`, `cleanmodels/__main__.py`, `run_cleanmodels.bat`, `README.md`

**Interfaces :**
- Consumes : toutes les interfaces précédentes.
- Produces :
  - `tabs.UsedTab`, `tabs.UnusedTab`, `tabs.DuplicatesTab`, `tabs.JunkTab` (`ttk.Frame`), chacun avec `show(result: AnalysisResult) -> None` ; les trois derniers reçoivent `on_delete: Callable[[list[DeletionItem], Checker, list[str]], None]` (items, checker, notes).
  - `app.CleanModelsApp(tk.Tk)` ; `app.main() -> None` ; `__main__.py` appelle `main()`.

- [ ] **Step 1 : Fenêtre principale** — champ « Dossier ComfyUI » + « Parcourir… » (`filedialog.askdirectory`), validation en direct via `validate_comfyui` (message sous le champ, bouton **Analyser** désactivé si invalide), chemin chargé/sauvé via `settings` ; avertissement de `load_settings` affiché au démarrage.
- [ ] **Step 2 : Analyse en arrière-plan** — `threading.Thread(daemon=True)` exécute `run_analysis` ; communication par `queue.Queue` relevée toutes les 100 ms avec `after` ; barre `ttk.Progressbar` indéterminée + libellé d'étape ; boutons désactivés pendant l'analyse ; exception → `messagebox.showerror` + trace dans `cleanmodels.log`.
- [ ] **Step 3 : Résumé** — workflows lus / ignorés (bouton « Détails » → `show_details` avec chemins et motifs), dossiers analysés avec origine, dossiers introuvables, avertissements, nombre et volume des modèles.
- [ ] **Step 4 : Onglets Utilisés / Non utilisés** — colonnes et actions du §6 de la spec ; double-clic Utilisés → `show_details` listant `workflow — nœud <id> (<type>)` ; compteur « X fichiers sélectionnés – Y » ; **Supprimer** actif seulement si sélection ; `on_delete` avec `unused_checker`.
- [ ] **Step 5 : Onglet Doublons** — « Rechercher les doublons » lance `find_duplicates` en arrière-plan avec barre déterminée (octets) et « Annuler » (`threading.Event`) ; colonne « Référencé » = `oui` si `file_key` du fichier est dans les fichiers de `usage.used` ; avant confirmation, `fully_selected_groups` non vide → message bloquant ; copie référencée sélectionnée → ajoutée à `notes`.
- [ ] **Step 6 : Onglet Fichiers parasites** — champ des motifs (séparés par `;`), « Appliquer » (relance `find_junk`, sauve dans les réglages), « Rétablir les motifs par défaut ».
- [ ] **Step 7 : Suppression** — `on_delete` : `confirm_deletion` → si oui, `delete_files` en arrière-plan → `show_report` → retrait des lignes supprimées dans tous les onglets.
- [ ] **Step 8 : Lanceur et README** — `run_cleanmodels.bat` : `@echo off`, `cd /d "%~dp0"`, `py -3 -m cleanmodels`, `if errorlevel 1 pause`. README : prérequis (Python ≥ 3.10), lancement, lancement des tests, avertissement sur la suppression définitive.
- [ ] **Step 9 : Vérification** — `python -m unittest discover -s tests -v` sur `py -3.12` et `py -3.14` → OK ; `py -3 -m cleanmodels` sur une fausse installation (`tests.helpers.make_comfy` dans un dossier temporaire) : analyse, double-clic, sélection, tri, doublons + annulation, motifs, suppression avec confirmation et bilan, contenu du journal.
- [ ] **Step 10 : Commit** `feat: interface tkinter, onglets et lanceur`.
