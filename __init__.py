import sys

try:
    from aqt import mw
    from aqt.qt import QAction
    ANKI_AVAILABLE = True
except ImportError:
    # Mocks pro Standalone Mode (mimo Anki)
    mw = None
    ANKI_AVAILABLE = False
    class QAction:
        def __init__(self, *args, **kwargs): pass
        def triggered(self): pass

from .canvas import OcclusionDialog

def start_occlusion_tool() -> None:
    """Spustí hlavní dialog nástroje."""
    # V Anki režimu předáme mw jako parenta, v standalone None
    dialog = OcclusionDialog(mw)
    dialog.exec()

def init_addon() -> None:
    """Inicializuje položku v menu Tools v Anki."""
    if not ANKI_AVAILABLE or mw is None:
        return
        
    action = QAction("Auto Image Occlusion", mw)
    action.triggered.connect(start_occlusion_tool)
    mw.form.menuTools.addAction(action)

# Inicializace proběhne pouze pokud jsme v Anki
if ANKI_AVAILABLE:
    init_addon()
