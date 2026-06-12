import sys
import os

try:
    from aqt import mw, gui_hooks
    from aqt.qt import QAction, QPushButton
    from aqt.addcards import AddCards
    ANKI_AVAILABLE = True
except ImportError:
    # Mocks pro Standalone Mode (mimo Anki)
    mw = None
    ANKI_AVAILABLE = False
    class QAction:
        def __init__(self, *args, **kwargs): pass
    gui_hooks = None

from .canvas import OcclusionDialog
from .anki_handler import AnkiHandler

def start_occlusion_tool() -> None:
    """Spustí hlavní dialog nástroje z menu Tools."""
    dialog = OcclusionDialog(mw)
    dialog.exec()

def on_add_cards_init(add_cards: AddCards) -> None:
    """Přidá tlačítko do okna Add Cards."""
    btn = QPushButton("Auto Image Occlusion 🪄")
    btn.clicked.connect(lambda: start_occlusion_tool_from_editor(add_cards))
    # Vložíme tlačítko do rozvržení okna Add Cards
    add_cards.form.verticalLayout.insertWidget(0, btn)

def start_occlusion_tool_from_editor(add_cards: AddCards) -> None:
    """Spustí nástroj a po dokončení se pokusí vyplnit pole v editoru."""
    dialog = OcclusionDialog(add_cards)
    if dialog.exec():
        # Zde můžeme volitelně automaticky vybrat náš Note Type
        # ale AnkiHandler ho již vytváří/kontroluje při startu dialogu
        pass

def init_addon() -> None:
    """Inicializuje doplňěk v Anki."""
    if not ANKI_AVAILABLE or mw is None:
        return
        
    # 1. Menu Tools
    action = QAction("Auto Image Occlusion", mw)
    action.triggered.connect(start_occlusion_tool)
    mw.form.menuTools.addAction(action)

    # 2. Hook do Add Cards okna
    gui_hooks.add_cards_did_init.append(on_add_cards_init)

# Inicializace proběhne pouze pokud jsme v Anki
if ANKI_AVAILABLE:
    init_addon()
