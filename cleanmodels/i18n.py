"""Textes de l'interface en français, anglais et allemand, et langue courante.

Les messages produits par le moteur sont des `Message` : leur valeur de chaîne est le texte
français (utilisé tel quel dans le journal, qui reste en français), et `localized()` les
traduit dans la langue courante pour l'affichage.
"""

LANGUAGES = {"fr": "Français", "en": "English", "de": "Deutsch"}
DEFAULT_LANGUAGE = "fr"

TEXTS = {
    "fr": {
        # Raccourci et logo
        "create_shortcut": "Créer le raccourci sur le bureau",
        "shortcut_title": "Raccourci",
        "offer_shortcut": "Créer un raccourci CleanModels sur le bureau ?",
        "offer_yes": "Oui, le créer",
        "offer_no": "Non merci",
        "shortcut_created": "Raccourci créé :\n{path}",
        "shortcut_failed": "Impossible de créer le raccourci :\n{error}",
        "err_desktop_missing": "Le dossier Bureau est introuvable : {path}",
        "err_shortcut_failed": "la création du raccourci a échoué",
        # Carte vidéo
        "gpu_label": "Carte vidéo :",
        "gpu_none": "Aucune carte vidéo détectée",
        "gpu_entry": "{name} — {size}",
        "gpu_manual_entry": "Saisie manuelle — {size}",
        "gpu_manual_button": "Saisir manuellement…",
        "gpu_manual_title": "Mémoire de la carte vidéo",
        "gpu_manual_prompt": "Mémoire de la carte vidéo, en Go :",
        "col_vram": "≥ VRAM",
        "vram_count": "{count} ≥ VRAM",
        "vram_hint": "⚠ = fichier dont la taille est supérieure ou égale à la mémoire de la carte vidéo "
                     "(indicatif : ComfyUI peut décharger en mémoire vive ou utiliser des versions GGUF).",
        # Fenêtre principale
        "install_folder": "Dossier d'installation de Votre ComfyUI :",
        "browse": "Parcourir…",
        "browse_title": "Dossier d'installation de ComfyUI",
        "scope_button": "Périmètre et analyse…",
        "theme": "Thème :",
        "theme_light": "Clair",
        "theme_dark": "Sombre",
        "language": "Langue :",
        "summary_start": "Choisissez le dossier d'installation de votre ComfyUI puis lancez l'analyse "
                         "depuis la fenêtre « Périmètre du contrôle ».",
        "details": "Détails…",
        "tab_used": "Utilisés",
        "tab_unused": "Non utilisés",
        "tab_duplicates": "Doublons",
        "tab_junk": "Fichiers parasites",
        "path_missing": "Choisissez le dossier d'installation de ComfyUI.",
        "settings_title": "Réglages",
        "error_title": "Erreur",
        "error_unexpected": "Une erreur inattendue s'est produite :\n{error}",
        "analysis_done": "Analyse terminée.",
        "summary_line1": "Workflows lus : {read}   ignorés : {skipped}   —   "
                         "Dossiers analysés : {dirs}   introuvables : {missing}",
        "summary_line2": "Modèles : {count} ({size})   —   utilisés : {used}   "
                         "non utilisés : {unused} ({unused_size})",
        "summary_excluded": "Dossiers décochés (non analysés) : {count} — voir « Détails… ».",
        "summary_warnings": "⚠ Des avertissements sont disponibles dans « Détails… ».",
        "details_title": "Détails de l'analyse",
        "details_workflows": "Workflows de référence :",
        "details_dirs": "Dossiers analysés :",
        "details_excluded": "Dossiers de modèles décochés (non analysés) :",
        "details_missing": "Dossiers déclarés introuvables :",
        "details_skipped": "Workflows ignorés :",
        "details_warnings": "Avertissements :",
        "details_errors": "Fichiers inaccessibles :",
        "suffix_missing": " — introuvable",
        "suffix_unchecked": " — décoché",
        "deleting": "Suppression en cours…",
        # Origines des dossiers
        "origin_standard": "standard",
        "origin_added": "ajouté",
        "origin_yaml": "extra_model_paths.yaml — section « {section} »",
        "detail_missing": "{origin} — introuvable",
        "detail_link": "{origin}  →  {target}  (lien symbolique / jonction)",
        # Onglets
        "col_category_name": "Catégorie / Nom",
        "col_group_name": "Groupe / Nom",
        "col_root": "Dossier racine",
        "col_size": "Taille",
        "col_calls": "Appels",
        "col_workflows": "Workflows",
        "col_full_path": "Chemin complet",
        "col_path": "Chemin",
        "col_referenced": "Référencé",
        "col_pattern": "Motif",
        "used_hint": "Double-cliquez sur un modèle pour voir les workflows qui l'utilisent.",
        "workflow_node": "{workflow} — nœud {node} ({type})",
        "usage_title": "Utilisation de {name}",
        "select_all": "Tout sélectionner",
        "unselect_all": "Tout désélectionner",
        "selected_count_one": "{count} fichier sélectionné – {size}",
        "selected_count_other": "{count} fichiers sélectionnés – {size}",
        "delete": "Supprimer",
        "note_unchecked_workflows": "Dossiers de workflows décochés lors de l'analyse — ils sont quand même "
                                    "relus maintenant, et la suppression d'un modèle qu'ils utilisent sera "
                                    "refusée :\n{folders}",
        "note_unreadable": "{count} workflow(s) illisible(s) : la suppression sera refusée tant qu'ils ne "
                           "sont pas corrigés ou retirés (voir « Détails… »).",
        "search_duplicates": "Rechercher les doublons",
        "cancel": "Annuler",
        "dup_hint": "La recherche lit le contenu des fichiers : elle peut être longue.",
        "dup_click_search": "Cliquez sur « Rechercher les doublons ».",
        "dup_searching": "Recherche en cours…",
        "dup_cancelled": "Recherche annulée.",
        "yes": "oui",
        "dup_group": "Groupe {number} — {name}",
        "dup_result_one": "{count} groupe – {size} récupérables",
        "dup_result_other": "{count} groupes – {size} récupérables",
        "dup_all_selected": "Toutes les copies d'au moins un groupe sont cochées.\n"
                            "Gardez au moins une copie de chaque groupe.",
        "note_referenced_copies": "Attention : ces copies sont citées par un workflow, qui devra pointer "
                                  "vers une autre copie :\n{paths}",
        "junk_patterns": "Motifs (séparés par « ; ») :",
        "apply": "Appliquer",
        "reset_patterns": "Rétablir les motifs par défaut",
        # Fenêtres de dialogue
        "confirm_title": "Confirmer la suppression",
        "files_count_one": "{count} fichier – {size}",
        "files_count_other": "{count} fichiers – {size}",
        "delete_warning": "Cette suppression est définitive et ne peut pas être annulée.",
        "confirm_delete": "Supprimer définitivement",
        "close": "Fermer",
        "report_title": "Bilan de la suppression",
        "report_deleted": "Supprimés : {count}",
        "report_refused": "Refusés : {count}",
        "report_errors": "Erreurs : {count}",
        "report_freed": "Espace libéré : {size}",
        "report_refused_list": "Refusés :",
        "report_errors_list": "Erreurs :",
        "report_log_errors": "Journal non écrit :",
        # Fenêtre du périmètre
        "scope_title": "Périmètre du contrôle",
        "scope_hint": "Décochez les dossiers à ne pas analyser. Les dossiers introuvables sont affichés "
                      "sans case.",
        "scope_need_path": "Indiquez le dossier d'installation de ComfyUI pour afficher le périmètre "
                           "du contrôle.",
        "col_folder": "Dossier",
        "col_origin": "Origine",
        "add_workflow_dir": "Ajouter un dossier de workflows…",
        "remove_workflow_dir": "Retirer le dossier sélectionné",
        "workflow_dir_title": "Dossier de workflows supplémentaire",
        "analyze": "Analyser",
        "warn_unchecked_workflows": "Attention : les modèles utilisés par les workflows décochés apparaîtront "
                                    "« non utilisés ». Leur suppression sera toutefois refusée, car tous les "
                                    "dossiers de workflows sont relus juste avant chaque suppression.",
        "warn_no_model_dir": "Cochez au moins un dossier dans « {group} » pour analyser.",
        "group_workflows": "Workflows de référence",
        "group_models": "Dossiers de modèles analysés",
        # Messages du moteur
        "err_dir_missing": "Le dossier « {path} » n'existe pas.",
        "err_no_models": "Le dossier « {path} » ne contient pas de sous-dossier models/.",
        "err_no_workflows": "Le dossier « {path} » ne contient pas user/default/workflows/.",
        "warn_yaml_unreadable": "{file} est illisible ({error}) : seul le dossier models/ est analysé.",
        "warn_settings_corrupt": "Le fichier de réglages était illisible ({error}). Il a été renommé en "
                                 "{backup} et les réglages par défaut sont utilisés.",
        "err_unknown_structure": "structure de workflow inconnue",
        "step_dirs": "Lecture des dossiers…",
        "step_inventory": "Inventaire des modèles…",
        "step_workflows": "Lecture des workflows…",
        "step_matching": "Correspondance…",
        "step_junk": "Fichiers parasites…",
        "reason_missing": "fichier introuvable",
        "reason_not_file": "n'est plus un fichier",
        "reason_size": "taille modifiée",
        "reason_check_failed": "vérification impossible ({error})",
        "reason_referenced": "cité par un workflow",
        "reason_unreadable": "{count} workflow(s) illisible(s) : corrigez-les ou retirez-les du dossier "
                             "des workflows",
        "reason_no_group": "groupe de doublons introuvable",
        "reason_no_copy": "aucune autre copie conservée",
        "reason_pattern": "ne correspond plus à un motif",
        "log_not_written": "{path} ({status}) : journal non écrit — {error}",
    },
    "en": {
        "create_shortcut": "Create desktop shortcut",
        "shortcut_title": "Shortcut",
        "offer_shortcut": "Create a CleanModels shortcut on the desktop?",
        "offer_yes": "Yes, create it",
        "offer_no": "No thanks",
        "shortcut_created": "Shortcut created:\n{path}",
        "shortcut_failed": "Cannot create the shortcut:\n{error}",
        "err_desktop_missing": "The Desktop folder cannot be found: {path}",
        "err_shortcut_failed": "the shortcut could not be created",
        "gpu_label": "Graphics card:",
        "gpu_none": "No graphics card detected",
        "gpu_entry": "{name} — {size}",
        "gpu_manual_entry": "Manual entry — {size}",
        "gpu_manual_button": "Enter manually…",
        "gpu_manual_title": "Graphics card memory",
        "gpu_manual_prompt": "Graphics card memory, in GB:",
        "col_vram": "≥ VRAM",
        "vram_count": "{count} ≥ VRAM",
        "vram_hint": "⚠ = file whose size is greater than or equal to the graphics card memory "
                     "(indicative: ComfyUI can offload to system RAM or use GGUF versions).",
        "install_folder": "Your ComfyUI installation folder:",
        "browse": "Browse…",
        "browse_title": "ComfyUI installation folder",
        "scope_button": "Scope and analysis…",
        "theme": "Theme:",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "language": "Language:",
        "summary_start": "Choose your ComfyUI installation folder, then start the analysis from the "
                         "“Check scope” window.",
        "details": "Details…",
        "tab_used": "Used",
        "tab_unused": "Unused",
        "tab_duplicates": "Duplicates",
        "tab_junk": "Junk files",
        "path_missing": "Choose the ComfyUI installation folder.",
        "settings_title": "Settings",
        "error_title": "Error",
        "error_unexpected": "An unexpected error occurred:\n{error}",
        "analysis_done": "Analysis complete.",
        "summary_line1": "Workflows read: {read}   skipped: {skipped}   —   "
                         "Folders analyzed: {dirs}   not found: {missing}",
        "summary_line2": "Models: {count} ({size})   —   used: {used}   "
                         "unused: {unused} ({unused_size})",
        "summary_excluded": "Unchecked folders (not analyzed): {count} — see “Details…”.",
        "summary_warnings": "⚠ Warnings are available in “Details…”.",
        "details_title": "Analysis details",
        "details_workflows": "Reference workflows:",
        "details_dirs": "Folders analyzed:",
        "details_excluded": "Unchecked model folders (not analyzed):",
        "details_missing": "Declared folders not found:",
        "details_skipped": "Skipped workflows:",
        "details_warnings": "Warnings:",
        "details_errors": "Inaccessible files:",
        "suffix_missing": " — not found",
        "suffix_unchecked": " — unchecked",
        "deleting": "Deleting…",
        "origin_standard": "standard",
        "origin_added": "added",
        "origin_yaml": "extra_model_paths.yaml — section “{section}”",
        "detail_missing": "{origin} — not found",
        "detail_link": "{origin}  →  {target}  (symbolic link / junction)",
        "col_category_name": "Category / Name",
        "col_group_name": "Group / Name",
        "col_root": "Root folder",
        "col_size": "Size",
        "col_calls": "Calls",
        "col_workflows": "Workflows",
        "col_full_path": "Full path",
        "col_path": "Path",
        "col_referenced": "Referenced",
        "col_pattern": "Pattern",
        "used_hint": "Double-click a model to see the workflows that use it.",
        "workflow_node": "{workflow} — node {node} ({type})",
        "usage_title": "Usage of {name}",
        "select_all": "Select all",
        "unselect_all": "Unselect all",
        "selected_count_one": "{count} file selected – {size}",
        "selected_count_other": "{count} files selected – {size}",
        "delete": "Delete",
        "note_unchecked_workflows": "Workflow folders unchecked during the analysis — they are still read "
                                    "now, and deleting a model they use will be refused:\n{folders}",
        "note_unreadable": "{count} unreadable workflow(s): deletion will be refused until they are fixed "
                           "or removed (see “Details…”).",
        "search_duplicates": "Find duplicates",
        "cancel": "Cancel",
        "dup_hint": "The search reads the content of the files: it may take a while.",
        "dup_click_search": "Click “Find duplicates”.",
        "dup_searching": "Searching…",
        "dup_cancelled": "Search cancelled.",
        "yes": "yes",
        "dup_group": "Group {number} — {name}",
        "dup_result_one": "{count} group – {size} recoverable",
        "dup_result_other": "{count} groups – {size} recoverable",
        "dup_all_selected": "All copies of at least one group are checked.\n"
                            "Keep at least one copy of each group.",
        "note_referenced_copies": "Warning: these copies are used by a workflow, which will have to point "
                                  "to another copy:\n{paths}",
        "junk_patterns": "Patterns (separated by “;”):",
        "apply": "Apply",
        "reset_patterns": "Restore default patterns",
        "confirm_title": "Confirm deletion",
        "files_count_one": "{count} file – {size}",
        "files_count_other": "{count} files – {size}",
        "delete_warning": "This deletion is permanent and cannot be undone.",
        "confirm_delete": "Delete permanently",
        "close": "Close",
        "report_title": "Deletion report",
        "report_deleted": "Deleted: {count}",
        "report_refused": "Refused: {count}",
        "report_errors": "Errors: {count}",
        "report_freed": "Space freed: {size}",
        "report_refused_list": "Refused:",
        "report_errors_list": "Errors:",
        "report_log_errors": "Log not written:",
        "scope_title": "Check scope",
        "scope_hint": "Uncheck the folders not to analyze. Folders that cannot be found are shown "
                      "without a checkbox.",
        "scope_need_path": "Enter the ComfyUI installation folder to display the check scope.",
        "col_folder": "Folder",
        "col_origin": "Origin",
        "add_workflow_dir": "Add a workflow folder…",
        "remove_workflow_dir": "Remove the selected folder",
        "workflow_dir_title": "Additional workflow folder",
        "analyze": "Analyze",
        "warn_unchecked_workflows": "Warning: models used by unchecked workflows will appear “unused”. "
                                    "Deleting them will still be refused, because all workflow folders are "
                                    "read again just before each deletion.",
        "warn_no_model_dir": "Check at least one folder in “{group}” to analyze.",
        "group_workflows": "Reference workflows",
        "group_models": "Model folders analyzed",
        "err_dir_missing": "The folder “{path}” does not exist.",
        "err_no_models": "The folder “{path}” has no models/ subfolder.",
        "err_no_workflows": "The folder “{path}” has no user/default/workflows/.",
        "warn_yaml_unreadable": "{file} cannot be read ({error}): only the models/ folder is analyzed.",
        "warn_settings_corrupt": "The settings file could not be read ({error}). It was renamed to "
                                 "{backup} and the default settings are used.",
        "err_unknown_structure": "unknown workflow structure",
        "step_dirs": "Reading folders…",
        "step_inventory": "Listing models…",
        "step_workflows": "Reading workflows…",
        "step_matching": "Matching…",
        "step_junk": "Junk files…",
        "reason_missing": "file not found",
        "reason_not_file": "is no longer a file",
        "reason_size": "size changed",
        "reason_check_failed": "check impossible ({error})",
        "reason_referenced": "used by a workflow",
        "reason_unreadable": "{count} unreadable workflow(s): fix them or remove them from the workflow "
                             "folder",
        "reason_no_group": "duplicate group not found",
        "reason_no_copy": "no other copy kept",
        "reason_pattern": "no longer matches a pattern",
        "log_not_written": "{path} ({status}): log not written — {error}",
    },
    "de": {
        "create_shortcut": "Desktop-Verknüpfung erstellen",
        "shortcut_title": "Verknüpfung",
        "offer_shortcut": "Eine CleanModels-Verknüpfung auf dem Desktop erstellen?",
        "offer_yes": "Ja, erstellen",
        "offer_no": "Nein danke",
        "shortcut_created": "Verknüpfung erstellt:\n{path}",
        "shortcut_failed": "Die Verknüpfung kann nicht erstellt werden:\n{error}",
        "err_desktop_missing": "Der Desktop-Ordner wurde nicht gefunden: {path}",
        "err_shortcut_failed": "die Verknüpfung konnte nicht erstellt werden",
        "gpu_label": "Grafikkarte:",
        "gpu_none": "Keine Grafikkarte erkannt",
        "gpu_entry": "{name} — {size}",
        "gpu_manual_entry": "Manuelle Eingabe — {size}",
        "gpu_manual_button": "Manuell eingeben…",
        "gpu_manual_title": "Grafikspeicher",
        "gpu_manual_prompt": "Speicher der Grafikkarte, in GB:",
        "col_vram": "≥ VRAM",
        "vram_count": "{count} ≥ VRAM",
        "vram_hint": "⚠ = Datei, deren Größe mindestens dem Grafikspeicher entspricht "
                     "(Hinweis: ComfyUI kann in den Arbeitsspeicher auslagern oder GGUF-Versionen nutzen).",
        "install_folder": "Installationsordner Ihres ComfyUI:",
        "browse": "Durchsuchen…",
        "browse_title": "ComfyUI-Installationsordner",
        "scope_button": "Umfang und Analyse…",
        "theme": "Design:",
        "theme_light": "Hell",
        "theme_dark": "Dunkel",
        "language": "Sprache:",
        "summary_start": "Wählen Sie den Installationsordner Ihres ComfyUI und starten Sie die Analyse "
                         "im Fenster „Prüfumfang“.",
        "details": "Details…",
        "tab_used": "Verwendet",
        "tab_unused": "Nicht verwendet",
        "tab_duplicates": "Duplikate",
        "tab_junk": "Störende Dateien",
        "path_missing": "Wählen Sie den ComfyUI-Installationsordner.",
        "settings_title": "Einstellungen",
        "error_title": "Fehler",
        "error_unexpected": "Ein unerwarteter Fehler ist aufgetreten:\n{error}",
        "analysis_done": "Analyse abgeschlossen.",
        "summary_line1": "Gelesene Workflows: {read}   übersprungen: {skipped}   —   "
                         "Analysierte Ordner: {dirs}   nicht gefunden: {missing}",
        "summary_line2": "Modelle: {count} ({size})   —   verwendet: {used}   "
                         "nicht verwendet: {unused} ({unused_size})",
        "summary_excluded": "Abgewählte Ordner (nicht analysiert): {count} — siehe „Details…“.",
        "summary_warnings": "⚠ Warnungen sind unter „Details…“ verfügbar.",
        "details_title": "Analysedetails",
        "details_workflows": "Referenz-Workflows:",
        "details_dirs": "Analysierte Ordner:",
        "details_excluded": "Abgewählte Modellordner (nicht analysiert):",
        "details_missing": "Deklarierte, nicht gefundene Ordner:",
        "details_skipped": "Übersprungene Workflows:",
        "details_warnings": "Warnungen:",
        "details_errors": "Nicht zugängliche Dateien:",
        "suffix_missing": " — nicht gefunden",
        "suffix_unchecked": " — abgewählt",
        "deleting": "Wird gelöscht…",
        "origin_standard": "Standard",
        "origin_added": "hinzugefügt",
        "origin_yaml": "extra_model_paths.yaml — Abschnitt „{section}“",
        "detail_missing": "{origin} — nicht gefunden",
        "detail_link": "{origin}  →  {target}  (symbolischer Link / Junction)",
        "col_category_name": "Kategorie / Name",
        "col_group_name": "Gruppe / Name",
        "col_root": "Stammordner",
        "col_size": "Größe",
        "col_calls": "Aufrufe",
        "col_workflows": "Workflows",
        "col_full_path": "Vollständiger Pfad",
        "col_path": "Pfad",
        "col_referenced": "Referenziert",
        "col_pattern": "Muster",
        "used_hint": "Doppelklicken Sie auf ein Modell, um die Workflows zu sehen, die es verwenden.",
        "workflow_node": "{workflow} — Knoten {node} ({type})",
        "usage_title": "Verwendung von {name}",
        "select_all": "Alle auswählen",
        "unselect_all": "Auswahl aufheben",
        "selected_count_one": "{count} Datei ausgewählt – {size}",
        "selected_count_other": "{count} Dateien ausgewählt – {size}",
        "delete": "Löschen",
        "note_unchecked_workflows": "Bei der Analyse abgewählte Workflow-Ordner — sie werden jetzt trotzdem "
                                    "gelesen, und das Löschen eines Modells, das sie verwenden, wird "
                                    "abgelehnt:\n{folders}",
        "note_unreadable": "{count} unlesbare(r) Workflow(s): Das Löschen wird abgelehnt, bis sie "
                           "korrigiert oder entfernt sind (siehe „Details…“).",
        "search_duplicates": "Duplikate suchen",
        "cancel": "Abbrechen",
        "dup_hint": "Die Suche liest den Inhalt der Dateien: Sie kann lange dauern.",
        "dup_click_search": "Klicken Sie auf „Duplikate suchen“.",
        "dup_searching": "Suche läuft…",
        "dup_cancelled": "Suche abgebrochen.",
        "yes": "ja",
        "dup_group": "Gruppe {number} — {name}",
        "dup_result_one": "{count} Gruppe – {size} freizugeben",
        "dup_result_other": "{count} Gruppen – {size} freizugeben",
        "dup_all_selected": "Alle Kopien mindestens einer Gruppe sind ausgewählt.\n"
                            "Behalten Sie mindestens eine Kopie jeder Gruppe.",
        "note_referenced_copies": "Achtung: Diese Kopien werden von einem Workflow verwendet, der auf eine "
                                  "andere Kopie verweisen muss:\n{paths}",
        "junk_patterns": "Muster (getrennt durch „;“):",
        "apply": "Anwenden",
        "reset_patterns": "Standardmuster wiederherstellen",
        "confirm_title": "Löschen bestätigen",
        "files_count_one": "{count} Datei – {size}",
        "files_count_other": "{count} Dateien – {size}",
        "delete_warning": "Dieses Löschen ist endgültig und kann nicht rückgängig gemacht werden.",
        "confirm_delete": "Endgültig löschen",
        "close": "Schließen",
        "report_title": "Löschbericht",
        "report_deleted": "Gelöscht: {count}",
        "report_refused": "Abgelehnt: {count}",
        "report_errors": "Fehler: {count}",
        "report_freed": "Freigegebener Speicher: {size}",
        "report_refused_list": "Abgelehnt:",
        "report_errors_list": "Fehler:",
        "report_log_errors": "Protokoll nicht geschrieben:",
        "scope_title": "Prüfumfang",
        "scope_hint": "Wählen Sie die Ordner ab, die nicht analysiert werden sollen. Nicht gefundene "
                      "Ordner werden ohne Kontrollkästchen angezeigt.",
        "scope_need_path": "Geben Sie den ComfyUI-Installationsordner an, um den Prüfumfang anzuzeigen.",
        "col_folder": "Ordner",
        "col_origin": "Herkunft",
        "add_workflow_dir": "Workflow-Ordner hinzufügen…",
        "remove_workflow_dir": "Ausgewählten Ordner entfernen",
        "workflow_dir_title": "Zusätzlicher Workflow-Ordner",
        "analyze": "Analysieren",
        "warn_unchecked_workflows": "Achtung: Modelle, die von abgewählten Workflows verwendet werden, "
                                    "erscheinen als „nicht verwendet“. Ihr Löschen wird dennoch abgelehnt, "
                                    "da alle Workflow-Ordner vor jedem Löschen erneut gelesen werden.",
        "warn_no_model_dir": "Wählen Sie mindestens einen Ordner unter „{group}“ aus, um zu analysieren.",
        "group_workflows": "Referenz-Workflows",
        "group_models": "Analysierte Modellordner",
        "err_dir_missing": "Der Ordner „{path}“ existiert nicht.",
        "err_no_models": "Der Ordner „{path}“ enthält keinen Unterordner models/.",
        "err_no_workflows": "Der Ordner „{path}“ enthält kein user/default/workflows/.",
        "warn_yaml_unreadable": "{file} ist nicht lesbar ({error}): Nur der Ordner models/ wird analysiert.",
        "warn_settings_corrupt": "Die Einstellungsdatei war nicht lesbar ({error}). Sie wurde in {backup} "
                                 "umbenannt, und die Standardeinstellungen werden verwendet.",
        "err_unknown_structure": "unbekannte Workflow-Struktur",
        "step_dirs": "Ordner werden gelesen…",
        "step_inventory": "Modelle werden erfasst…",
        "step_workflows": "Workflows werden gelesen…",
        "step_matching": "Abgleich…",
        "step_junk": "Störende Dateien…",
        "reason_missing": "Datei nicht gefunden",
        "reason_not_file": "ist keine Datei mehr",
        "reason_size": "Größe geändert",
        "reason_check_failed": "Prüfung nicht möglich ({error})",
        "reason_referenced": "von einem Workflow verwendet",
        "reason_unreadable": "{count} unlesbare(r) Workflow(s): korrigieren oder aus dem Workflow-Ordner "
                             "entfernen",
        "reason_no_group": "Duplikatgruppe nicht gefunden",
        "reason_no_copy": "keine andere Kopie behalten",
        "reason_pattern": "entspricht keinem Muster mehr",
        "log_not_written": "{path} ({status}): Protokoll nicht geschrieben — {error}",
    },
}

_current = DEFAULT_LANGUAGE


def set_language(code: str) -> None:
    global _current
    _current = code if code in TEXTS else DEFAULT_LANGUAGE


def get_language() -> str:
    return _current


def _text(key: str, language: str) -> str:
    return TEXTS[language].get(key) or TEXTS[DEFAULT_LANGUAGE][key]


def t(key: str, **kwargs) -> str:
    """Texte traduit dans la langue courante ; les arguments `Message` sont traduits aussi."""
    return _text(key, _current).format(**{k: localized(v) for k, v in kwargs.items()})


def tn(key: str, count: int, **kwargs) -> str:
    """Variante singulier (« _one ») / pluriel (« _other ») selon count."""
    return t(f"{key}_{'one' if count == 1 else 'other'}", count=count, **kwargs)


class Message(str):
    """Message du moteur : vaut son texte français, se traduit avec localized()."""

    def __new__(cls, key: str, **kwargs):
        text = _text(key, DEFAULT_LANGUAGE).format(**{k: str(v) for k, v in kwargs.items()})
        message = super().__new__(cls, text)
        message.key = key
        message.kwargs = kwargs
        return message

    def localized(self) -> str:
        return t(self.key, **self.kwargs)


def localized(value) -> str:
    """Texte à afficher : un Message est traduit, toute autre valeur est convertie en chaîne."""
    return value.localized() if isinstance(value, Message) else str(value)
