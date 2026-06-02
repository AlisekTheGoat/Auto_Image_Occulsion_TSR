from aqt import mw
from aqt.qt import QAction
from .canvas import OcclusionDialog

def start_occlusion_tool() -> None:
    """Spustí hlavní dialog nástroje."""
    dialog = OcclusionDialog(mw)
    dialog.exec()

def init_addon() -> None:
    """Inicializuje položku v menu Tools."""
    action = QAction("Auto Image Occlusion", mw)
    action.triggered.connect(start_occlusion_tool)
    mw.form.menuTools.addAction(action)

# Inicializace při načtení add-onu
init_addon()
