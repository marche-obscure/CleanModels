# CleanModels

Outil de bureau pour faire le ménage dans les modèles ComfyUI :

- **Utilisés** : modèles cités par vos workflows, avec le nombre d'appels et de workflows ;
- **Non utilisés** : modèles qu'aucun workflow ne cite ;
- **Doublons** : fichiers au contenu identique (recherche à la demande) ;
- **Fichiers parasites** : téléchargements incomplets et temporaires (`*.part`, `*.crdownload`, `*.tmp`, `*.download`, motifs modifiables).

Workflows de référence : `<ComfyUI>/user/default/workflows/`, plus les dossiers de workflows
que vous ajoutez dans l'application (mémorisés, retirables).
Dossiers analysés : `<ComfyUI>/models/` et les chemins de `extra_model_paths.yaml` (liens
symboliques et jonctions compris), limités à
`checkpoints`, `controlnet`, `diffusion_models`, `LLM`, `model_patches`, `text_encoders`, `unet`, `vae`.

Le bouton « Périmètre et analyse… » ouvre la fenêtre « Périmètre du contrôle » : elle affiche
les dossiers de workflows de référence et les dossiers de modèles qui seront examinés, avec leur
origine et la cible réelle des liens. Tout est coché par défaut ; décochez les dossiers à ne pas
analyser, puis cliquez sur « Analyser ». Un dossier de workflows décoché est tout de même relu
avant chaque suppression : un modèle qu'il utilise ne peut pas être supprimé.

## ⚠ Suppression définitive

Les fichiers supprimés ne passent **pas** par la Corbeille. Chaque suppression demande une
confirmation explicite, est revérifiée juste avant d'agir et est inscrite dans le journal
`%APPDATA%\CleanModels\cleanmodels.log`.

## Prérequis

Python 3.10 ou plus récent, sans aucune bibliothèque supplémentaire.

## Lancement

Double-cliquez sur `run_cleanmodels.bat`, ou :

```bash
py -3 -m cleanmodels
```

## Tests

```bash
py -3 -m unittest discover -s tests -v
```

## Documentation

- Spécification : `docs/specs/2026-10-10-cleanmodels-design.md`
- Plan d'implémentation : `docs/superpowers/plans/2026-10-10-cleanmodels.md`
