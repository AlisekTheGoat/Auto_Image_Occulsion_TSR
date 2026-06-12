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
        Naskenuje obrázek, provede předzpracování a vrátí seznam shluknutých bounding boxů
        optimalizovaných pro anatomické popisky (Phrase Clustering).
        """
        if not self.tesseract_path:
            self._show_error(
                "Tesseract OCR nebyl nalezen.\n\n"
                "Ujistěte se, že je Tesseract nainstalován v systému, "
                "nebo umístěn ve složce doplňku 'bin/'."
            )
            return []

        try:
            # 1. Předzpracování obrazu
            orig_img = Image.open(image_path)
            scale_factor = 2.0
            processed_img = self._preprocess_image(orig_img, scale_factor)
            
            # 2. Konfigurace Tesseractu
            custom_config = r'--psm 12'
            data = pytesseract.image_to_data(processed_img, config=custom_config, output_type=pytesseract.Output.DICT)
            
            raw_words = []
            num_boxes = len(data['level'])

            # Sběr surových slov - snížíme práh spolehlivosti pro medicínské diagramy
            for i in range(num_boxes):
                try:
                    conf = int(data['conf'][i])
                except:
                    conf = 0
                text = data['text'][i].strip()
                
                # Snížení conf na 20 pro zachycení drobných popisků
                if data['level'][i] == 5 and conf > 20 and text:
                    raw_words.append({
                        'x1': data['left'][i] / scale_factor,
                        'y1': data['top'][i] / scale_factor,
                        'x2': (data['left'][i] + data['width'][i]) / scale_factor,
                        'y2': (data['top'][i] + data['height'][i]) / scale_factor,
                        'text': text,
                        'h': (data['height'][i]) / scale_factor
                    })
            
            if not raw_words:
                return []

            # 3. Výpočet globálního H_avg
            global_h_avg = sum(w['h'] for w in raw_words) / len(raw_words)
            
            # 4. Phrase Clustering Algoritmus - AGRESIVNĚJŠÍ SHLUKOVÁNÍ
            M_HORIZ = 2.0 # Více prostoru mezi slovy
            M_VERT = 0.5  # Větší tolerance pro "vlnitý" text
            
            merged_boxes = []
            words = sorted(raw_words, key=lambda w: (w['y1'], w['x1']))

            while words:
                curr = words.pop(0)
                phrase_group = [curr]
                
                i = 0
                while i < len(words):
                    other = words[i]
                    
                    dx = other['x1'] - curr['x2']
                    dy = abs(other['y1'] - curr['y1'])
                    
                    if dy < (global_h_avg * M_VERT) and dx < (global_h_avg * M_HORIZ):
                        phrase_group.append(words.pop(i))
                        curr['x2'] = max(curr['x2'], other['x2'])
                        curr['y1'] = min(curr['y1'], other['y1'])
                        curr['y2'] = max(curr['y2'], other['y2'])
                    else:
                        i += 1
                
                # Sloučení skupiny do jednoho boxu
                text = " ".join(w['text'] for w in phrase_group)
                x1 = min(w['x1'] for w in phrase_group)
                y1 = min(w['y1'] for w in phrase_group)
                x2 = max(w['x2'] for w in phrase_group)
                y2 = max(w['y2'] for w in phrase_group)
                
                merged_boxes.append({
                    'text': text,
                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2
                })

            # 5. Finální filtrace pomocí IoU
            final_boxes = []
            for b in merged_boxes:
                keep = True
                box_a = [b['x1'], b['y1'], b['x2'], b['y2']]
                for existing in final_boxes:
                    box_b = [existing['x1'], existing['y1'], existing['x2'], existing['y2']]
                    if self._calculate_iou(box_a, box_b) > 0.4:
                        keep = False
                        break
                if keep:
                    final_boxes.append(b)

            return [{
                'text': b['text'],
                'x': b['x1'],
                'y': b['y1'],
                'w': b['x2'] - b['x1'],
                'h': b['y2'] - b['y1']
            } for b in final_boxes]

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
