# CleanModels

Desktop tool to clean up your ComfyUI models:

- **Used**: models referenced by your workflows, with the number of calls and workflows;
- **Unused**: models that no workflow references;
- **Duplicates**: files with identical content (search on demand);
- **Junk files**: incomplete and temporary downloads (`*.part`, `*.crdownload`, `*.tmp`, `*.download`, editable patterns).

Reference workflows: `<ComfyUI>/user/default/workflows/`, plus any workflow folders you add in
the application (remembered, removable).
Folders analyzed: `<ComfyUI>/models/` and the paths declared in `extra_model_paths.yaml`
(symbolic links and junctions included), limited to
`checkpoints`, `controlnet`, `diffusion_models`, `LLM`, `model_patches`, `text_encoders`, `unet`, `vae`.

The “Scope and analysis…” button opens the “Check scope” window: it shows the reference workflow
folders and the model folders that will be examined, with their origin and the real target of
links. Everything is checked by default; uncheck the folders you do not want to analyze, then
click “Analyze”. An unchecked workflow folder is still read again before each deletion: a model it
uses cannot be deleted.

At startup, the main window opens on the left of the screen and the “Check scope” window on its
right; it stays open after the analysis.

Top right of the main window: **Theme** (Light / Dark) and **Language** (Français / English /
Deutsch). Both choices are remembered; the log file stays in French.

**Graphics card**: its memory is read automatically (nvidia-smi, otherwise the Windows registry);
choose the reference card or enter the value manually. Files whose size is greater than or equal
to that memory are marked ⚠ and shown in orange (indicative only).

## ⚠ Permanent deletion

Deleted files do **not** go to the Recycle Bin. Every deletion requires explicit confirmation,
is checked again just before acting, and is recorded in the log
`%APPDATA%\CleanModels\cleanmodels.log`.

## Requirements

Python 3.10 or later, with no additional library.

## Running

Double-click `run_cleanmodels.bat`, or:

```bash
py -3 -m cleanmodels
```

## Tests

```bash
py -3 -m unittest discover -s tests -v
```

## Documentation (in French)

- Specification: `docs/specs/2026-10-10-cleanmodels-design.md`
- Implementation plan: `docs/superpowers/plans/2026-10-10-cleanmodels.md`
