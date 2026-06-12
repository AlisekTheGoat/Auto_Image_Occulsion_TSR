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
        Naskenuje obrázek, provede předzpracování a vrátí seznam shluknutých bounding boxů.
        """
        if not self.tesseract_path:
            self._show_error(
                "Tesseract OCR nebyl nalezen.\n\n"
                "Ujistěte se, že je Tesseract nainstalován v systému, "
                "nebo umístěn ve složce doplňku 'bin/'."
            )
            return []

        try:
            # 1.1 Předzpracování obrazu
            orig_img = Image.open(image_path)
            scale_factor = 2.0
            processed_img = self._preprocess_image(orig_img, scale_factor)
            
            # 1.2 Konfigurace Tesseractu (--psm 12 pro sparse text)
            custom_config = r'--psm 12'
            data = pytesseract.image_to_data(processed_img, config=custom_config, output_type=pytesseract.Output.DICT)
            
            words = []
            num_boxes = len(data['level'])

            for i in range(num_boxes):
                conf = int(data['conf'][i])
                text = data['text'][i].strip()
                
                # Filtrace: pouze slova (level 5) s jistotou > 40
                if data['level'][i] == 5 and conf > 40 and text:
                    # Přepočet souřadnic zpět na původní velikost
                    words.append({
                        'x1': data['left'][i] / scale_factor,
                        'y1': data['top'][i] / scale_factor,
                        'x2': (data['left'][i] + data['width'][i]) / scale_factor,
                        'y2': (data['top'][i] + data['height'][i]) / scale_factor,
                        'text': text
                    })
            
            if not words:
                return []

            # 1.3 Dynamické shlukování (Word Clustering)
            # Parametry z GEMINI.md / Heuristika
            M_HORIZ = 1.2
            M_VERT = 0.8  # Pro sloučení slov na stejném řádku

            merged = True
            while merged:
                merged = False
                new_words = []
                while words:
                    curr = words.pop(0)
                    has_merged = False
                    
                    # Výpočet průměrné výšky aktuálního slova pro dynamický práh
                    h_curr = curr['y2'] - curr['y1']
                    
                    for i, other in enumerate(words):
                        h_other = other['y2'] - other['y1']
                        h_avg = (h_curr + h_other) / 2.0
                        
                        x_threshold = h_avg * M_HORIZ
                        y_threshold = h_avg * M_VERT
                        
                        # Kontrola prostorové blízkosti
                        horizontal_gap = max(0, max(curr['x1'], other['x1']) - min(curr['x2'], other['x2']))
                        vertical_overlap = min(curr['y2'], other['y2']) - max(curr['y1'], other['y1'])
                        
                        # Podmínka pro sloučení: 
                        # 1. Malá horizontální mezera
                        # 2. Významný vertikální překryv (jsou na stejném řádku)
                        if horizontal_gap < x_threshold and vertical_overlap > (h_avg * 0.3):
                            
                            curr['x1'] = min(curr['x1'], other['x1'])
                            curr['y1'] = min(curr['y1'], other['y1'])
                            curr['x2'] = max(curr['x2'], other['x2'])
                            curr['y2'] = max(curr['y2'], other['y2'])
                            
                            # Seřazení textu podle X souřadnice
                            if other['x1'] < curr['x1']:
                                curr['text'] = other['text'] + " " + curr['text']
                            else:
                                curr['text'] += " " + other['text']
                            
                            words.pop(i)
                            has_merged = True
                            merged = True
                            break
                    
                    new_words.append(curr)
                words = new_words

            # Finální filtrace pomocí IoU (Intersection over Union)
            # Zamezuje duplicitním nebo vnořeným maskám
            final_boxes = []
            for w in words:
                keep = True
                box_a = [w['x1'], w['y1'], w['x2'], w['y2']]
                for existing in final_boxes:
                    box_b = [existing['x1'], existing['y1'], existing['x2'], existing['y2']]
                    if self._calculate_iou(box_a, box_b) > 0.4:
                        keep = False
                        break
                if keep:
                    final_boxes.append(w)

            return [{
                'text': w['text'],
                'x': w['x1'],
                'y': w['y1'],
                'w': w['x2'] - w['x1'],
                'h': w['y2'] - w['y1']
            } for w in final_boxes]

        except Exception as e:
            self._show_error(f"Chyba při zpracování OCR: {str(e)}")
            return []

    def _calculate_iou(self, boxA: List[float], boxB: List[float]) -> float:
        """Vypočítá Intersection over Union pro dva obdélníky [x1, y1, x2, y2]."""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        iou = interArea / float(boxAArea + boxBArea - interArea) if (boxAArea + boxBArea - interArea) > 0 else 0
        return iou

    def _preprocess_image(self, img: Image.Image, scale: float) -> Image.Image:
        """
        Převede obrázek na stupně šedi a provede upscaling pomocí Lanczos.
        """
        # Konverze na stupně šedi
        img = img.convert('L')
        
        # Upscaling (Lanczos)
        new_size = (int(img.width * scale), int(img.height * scale))
        # Použití moderního API Pillow pokud je k dispozici
        resample_filter = getattr(Image, "Resampling", Image).LANCZOS
        return img.resize(new_size, resample=resample_filter)

    def _show_error(self, message: str) -> None:
        """Zobrazí chybové hlášení uživateli."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText("Chyba OCR")
        msg.setInformativeText(message)
        msg.setWindowTitle("Chyba")
        msg.exec()
