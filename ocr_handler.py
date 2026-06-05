import pytesseract
import os
import sys
import platform
import shutil
from PIL import Image
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import QMessageBox

class OCRHandler:
    """Třída pro zpracování obrazu a detekci textu pomocí Tesseract OCR."""

    def __init__(self) -> None:
        """Inicializace a automatická detekce cesty k Tesseractu."""
        self.tesseract_path = self._find_tesseract_binary()
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def _find_tesseract_binary(self) -> Optional[str]:
        """
        Vyhledá binárku Tesseractu. 
        Pořadí: 1. Lokálně v doplňku (Portable), 2. Systémová cesta (Fallback).
        """
        system = platform.system().lower()
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 1. Definice lokálních cest v doplňku (bin/)
        local_paths = {
            "windows": os.path.join(addon_dir, "bin", "tesseract-win", "tesseract.exe"),
            "darwin": os.path.join(addon_dir, "bin", "tesseract-mac", "tesseract"),
            "linux": os.path.join(addon_dir, "bin", "tesseract-linux", "tesseract")
        }
        
        local_binary = local_paths.get(system)
        if local_binary and os.path.exists(local_binary):
            return local_binary

        # 2. Systémové fallbacky pro macOS/Linux (pokud není lokální)
        if system != "windows":
            # Časté cesty na macOS (Homebrew) a Linuxu
            common_paths = [
                "/usr/local/bin/tesseract",
                "/usr/bin/tesseract",
                "/opt/homebrew/bin/tesseract"
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
        
        # 3. Poslední pokus: zkusit, zda je v PATH (funguje i pro Windows)
        path_in_env = shutil.which("tesseract")
        if path_in_env:
            return path_in_env

        return None

    def get_text_boxes(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Naskenuje obrázek a vrátí seznam shluknutých (grouped) bounding boxů.
        """
        if not self.tesseract_path:
            self._show_error(
                "Tesseract OCR nebyl nalezen.\n\n"
                "Ujistěte se, že je Tesseract nainstalován v systému, "
                "nebo umístěn ve složce doplňku 'bin/'."
            )
            return []

        try:
            img = Image.open(image_path)
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            words = []
            num_boxes = len(data['level'])

            for i in range(num_boxes):
                conf = int(data['conf'][i])
                text = data['text'][i].strip()
                
                if conf > 70 and text:
                    words.append({
                        'x1': data['left'][i],
                        'y1': data['top'][i],
                        'x2': data['left'][i] + data['width'][i],
                        'y2': data['top'][i] + data['height'][i],
                        'text': text
                    })
            
            if not words:
                return []

            # Algoritmus shlukování (Merging)
            X_THRESHOLD = 20 
            Y_THRESHOLD = 15

            merged = True
            while merged:
                merged = False
                new_words = []
                while words:
                    curr = words.pop(0)
                    has_merged = False
                    for i, other in enumerate(words):
                        if (max(curr['x1'], other['x1']) < min(curr['x2'], other['x2']) + X_THRESHOLD and
                            max(curr['y1'], other['y1']) < min(curr['y2'], other['y2']) + Y_THRESHOLD):
                            
                            curr['x1'] = min(curr['x1'], other['x1'])
                            curr['y1'] = min(curr['y1'], other['y1'])
                            curr['x2'] = max(curr['x2'], other['x2'])
                            curr['y2'] = max(curr['y2'], other['y2'])
                            curr['text'] += " " + other['text']
                            
                            words.pop(i)
                            has_merged = True
                            merged = True
                            break
                    new_words.append(curr)
                words = new_words

            return [{
                'text': w['text'],
                'x': w['x1'],
                'y': w['y1'],
                'w': w['x2'] - w['x1'],
                'h': w['y2'] - w['y1']
            } for w in words]

        except Exception as e:
            self._show_error(f"Chyba při zpracování OCR: {str(e)}")
            return []

    def _show_error(self, message: str) -> None:
        """Zobrazí chybové hlášení uživateli."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText("Chyba OCR")
        msg.setInformativeText(message)
        msg.setWindowTitle("Chyba")
        msg.exec()
