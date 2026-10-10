# CleanModels

Outil de bureau pour faire le ménage dans les modèles ComfyUI :

- **Utilisés** : modèles cités par vos workflows, avec le nombre d'appels et de workflows ;
- **Non utilisés** : modèles qu'aucun workflow ne cite ;
- **Doublons** : fichiers au contenu identique (recherche à la demande) ;
- **Fichiers parasites** : téléchargements incomplets et temporaires (`*.part`, `*.crdownload`, `*.tmp`, `*.download`, motifs modifiables).

Workflows de référence : `<ComfyUI>/user/default/workflows/` uniquement.
Dossiers analysés : `<ComfyUI>/models/` et les chemins de `extra_model_paths.yaml`, limités à
`checkpoints`, `controlnet`, `diffusion_models`, `LLM`, `model_patches`, `text_encoders`, `unet`, `vae`.

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
