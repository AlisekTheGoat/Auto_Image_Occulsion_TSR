from typing import List
try:
    from aqt import gui_hooks
    from aqt.editor import Editor
    ANKI_AVAILABLE = True
except ImportError:
    ANKI_AVAILABLE = False

from .canvas import OcclusionDialog
from .anki_handler import AnkiHandler

def on_init_buttons(buttons: List[str], editor: Editor) -> List[str]:
    """DIAGNOSTIKA: Přidá tlačítko všem typům karet pro ověření funkčnosti."""
    if not ANKI_AVAILABLE:
        return buttons
        
    # Přidáme tlačítko bez ohledu na Note Type pro test
    btn = editor.addButton(
        icon=None,
        label="AUTO IO",
        cmd="auto_io_open",
        tip="Auto Image Occlusion",
        func=lambda ed: open_occlusion_editor(ed),
        id="auto_io_btn"
    )
    buttons.append(btn)
    return buttons

def open_occlusion_editor(editor: Editor) -> None:
    """Otevře PyQt6 editor a po zavření obnoví okno Add Cards."""
    dialog = OcclusionDialog(editor.widget, editor)
    if dialog.exec():
        # Obnovení editoru, pokud byly přidány karty
        # Většinou se karty přidávají do decku přímo, 
        # takže editor v "Add Cards" zůstane čistý pro další vstup.
        editor.loadNote()

def init_hooks() -> None:
    """Zaregistruje hooky pro integraci do editoru."""
    if ANKI_AVAILABLE:
        gui_hooks.editor_did_init_buttons.append(on_init_buttons)
        # Inicializace modelu až když je profil (a databáze) připraven
        gui_hooks.profile_did_open.append(lambda: AnkiHandler())
