import pytesseract
from PIL import Image
from typing import List, Dict, Any
from PyQt6.QtWidgets import QMessageBox

class OCRHandler:
    """Třída pro zpracování obrazu a detekci textu pomocí Tesseract OCR."""

    def __init__(self) -> None:
        # Zde lze v budoucnu přidat nastavení cesty k binárce Tesseractu
        pass

    def get_text_boxes(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Naskenuje obrázek a vrátí seznam bounding boxů pro nalezený text.
        
        Vrací list slov s metadaty: {'text': str, 'x': int, 'y': int, 'w': int, 'h': int}
        """
        try:
            # Načtení obrázku přes PIL
            img = Image.open(image_path)
            
            # Získání dat z OCR ve formátu slovníku
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            results = []
            num_boxes = len(data['level'])

            for i in range(num_boxes):
                conf = int(data['conf'][i])
                text = data['text'][i].strip()
                
                # Filtrace: pouze text s dostatečnou spolehlivostí
                if conf > 70 and text:
                    results.append({
                        'text': text,
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'w': data['width'][i],
                        'h': data['height'][i]
                    })
            
            return results

        except EnvironmentError:
            self._show_error("Tesseract OCR nebyl v systému nalezen. Prosím, nainstalujte jej.")
            return []
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
