import sys
import os

try:
    from aqt import mw
    ANKI_AVAILABLE = True
except ImportError:
    mw = None
    ANKI_AVAILABLE = False

from .anki_integration import init_hooks

def init_addon() -> None:
    """Inicializuje doplňěk v Anki."""
    if not ANKI_AVAILABLE or mw is None:
        return
        
    # Inicializace hooků pro Editor a registrace Note Type
    init_hooks()

# Inicializace proběhne pouze pokud jsme v Anki
if ANKI_AVAILABLE:
    init_addon()
