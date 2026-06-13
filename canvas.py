import sys
import os
import base64
from typing import Optional, List, Any, Dict

from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QComboBox, QMessageBox, QFileDialog, QWidget, QFormLayout,
    QLineEdit, QTextEdit, QGroupBox, QLabel, QButtonGroup
)
from PyQt6.QtCore import QUrl, QObject, pyqtSlot, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QPixmap

try:
    from .ocr_handler import OCRHandler
    from .anki_handler import AnkiHandler
except ImportError:
    from ocr_handler import OCRHandler
    from anki_handler import AnkiHandler

try:
    import aqt
    from aqt import mw
    from aqt.utils import QueryOp
    ANKI_AVAILABLE = True
except ImportError:
    mw = None
    ANKI_AVAILABLE = False

class DebugPage(QWebEnginePage):
    """Vlastní stránka pro zachytávání a výpis JS konzolových zpráv do Pythonu."""
    def javaScriptConsoleMessage(self, level: int, message: str, line: int, source_id: str) -> None:
        print(f"JS CONSOLE [{source_id}:{line}]: {message}")

class WebBridge(QObject):
    """Most mezi JavaScriptem (Fabric.js) a Pythonem."""
    
    selectionChanged = pyqtSignal(bool)
    boxAdded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    @pyqtSlot(bool)
    def onSelectionChanged(self, has_selection: bool):
        self.selectionChanged.emit(has_selection)

    @pyqtSlot()
    def onBoxAdded(self):
        self.boxAdded.emit()

class OcclusionDialog(QDialog):
    def __init__(self, parent: Optional[Any] = None, editor: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Auto Image Occlusion (Fabric.js Engine)")
        self.resize(1300, 850)
        
        self.editor = editor
        self.ocr = OCRHandler()
        self.anki = AnkiHandler() if ANKI_AVAILABLE else None
        self.current_image_path: Optional[str] = None
        
        self.setup_ui()
        self.setup_bridge()

    def setup_ui(self) -> None:
        # Hlavní rozložení (horizontální - vlevo plátno, vpravo sidebar)
        main_layout = QHBoxLayout(self)
        
        # Levý panel (plátno + toolbar)
        left_panel = QVBoxLayout()
        
        # WebView - hlavní plátno
        self.web_view = QWebEngineView()
        self.web_view.setPage(DebugPage(self.web_view))
        left_panel.addWidget(self.web_view)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # Tlačítko Načíst
        self.load_btn = QPushButton("Načíst obrázek 🖼️")
        self.load_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                padding: 6px 12px;
                background-color: #f1f2f6;
                border: 1px solid #ced6e0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
            }
        """)
        self.load_btn.clicked.connect(self.on_load_clicked)
        toolbar.addWidget(self.load_btn)

        # Skupina tlačítek pro nástroje (Výběr, Obdélník, Elipsa, Lasso)
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        tool_btn_style = """
            QPushButton {
                font-size: 16px;
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
                background-color: #f1f2f6;
                border: 1px solid #ced6e0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
            }
            QPushButton:checked {
                background-color: #3b82f6;
                color: white;
                border: 1px solid #2563eb;
            }
        """

        self.select_tool_btn = QPushButton("⬈")
        self.select_tool_btn.setCheckable(True)
        self.select_tool_btn.setChecked(True)
        self.select_tool_btn.setToolTip("Výběr a přesun objektů")
        self.select_tool_btn.setStyleSheet(tool_btn_style)
        self.select_tool_btn.clicked.connect(lambda: self.on_tool_btn_clicked('select'))
        
        self.rect_tool_btn = QPushButton("⬜")
        self.rect_tool_btn.setCheckable(True)
        self.rect_tool_btn.setToolTip("Kreslit obdélník")
        self.rect_tool_btn.setStyleSheet(tool_btn_style)
        self.rect_tool_btn.clicked.connect(lambda: self.on_tool_btn_clicked('rect'))

        self.ellipse_tool_btn = QPushButton("⭕")
        self.ellipse_tool_btn.setCheckable(True)
        self.ellipse_tool_btn.setToolTip("Kreslit elipsu")
        self.ellipse_tool_btn.setStyleSheet(tool_btn_style)
        self.ellipse_tool_btn.clicked.connect(lambda: self.on_tool_btn_clicked('ellipse'))

        self.lasso_tool_btn = QPushButton("✍️")
        self.lasso_tool_btn.setCheckable(True)
        self.lasso_tool_btn.setToolTip("Kreslit volnou rukou (Lasso)")
        self.lasso_tool_btn.setStyleSheet(tool_btn_style)
        self.lasso_tool_btn.clicked.connect(lambda: self.on_tool_btn_clicked('lasso'))

        self.tool_group.addButton(self.select_tool_btn)
        self.tool_group.addButton(self.rect_tool_btn)
        self.tool_group.addButton(self.ellipse_tool_btn)
        self.tool_group.addButton(self.lasso_tool_btn)

        toolbar.addWidget(self.select_tool_btn)
        toolbar.addWidget(self.rect_tool_btn)
        toolbar.addWidget(self.ellipse_tool_btn)
        toolbar.addWidget(self.lasso_tool_btn)

        # Tlačítko Smazat
        self.delete_btn = QPushButton("Smazat 🗑️")
        self.delete_btn.setToolTip("Smazat vybrané masky")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                padding: 6px 12px;
                background-color: #f1f2f6;
                border: 1px solid #ced6e0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ffcccb;
                border-color: #ff3333;
            }
        """)
        self.delete_btn.clicked.connect(lambda: self.run_js("deleteSelected()"))
        toolbar.addWidget(self.delete_btn)

        # Seskupování
        self.group_btn = QPushButton("Seskupit 🔗")
        self.group_btn.setToolTip("Seskupit vybrané objekty")
        self.group_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                background-color: #f1f2f6;
                border: 1px solid #ced6e0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
            }
        """)
        self.group_btn.clicked.connect(lambda: self.run_js("groupSelected()"))
        toolbar.addWidget(self.group_btn)

        self.ungroup_btn = QPushButton("Rozdělit 🔓")
        self.ungroup_btn.setToolTip("Rozdělit vybranou skupinu")
        self.ungroup_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                background-color: #f1f2f6;
                border: 1px solid #ced6e0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
            }
        """)
        self.ungroup_btn.clicked.connect(lambda: self.run_js("ungroupSelected()"))
        toolbar.addWidget(self.ungroup_btn)

        # Auto-OCR
        self.occlude_btn = QPushButton("Auto-OCR 🪄")
        self.occlude_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; 
                color: white; 
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.occlude_btn.clicked.connect(self.run_ocr_auto)
        toolbar.addWidget(self.occlude_btn)
        
        left_panel.addLayout(toolbar)
        main_layout.addLayout(left_panel)
        
        # Pravý panel (Sidebar)
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(10, 0, 10, 0)
        
        # Metadata Group Box
        meta_group = QGroupBox("Metadata karty")
        meta_form = QFormLayout()
        
        self.header_input = QLineEdit()
        self.footer_input = QLineEdit()
        self.remarks_input = QTextEdit()
        self.remarks_input.setMaximumHeight(100)
        self.sources_input = QLineEdit()
        self.extra_input = QTextEdit()
        self.extra_input.setMaximumHeight(100)
        
        meta_form.addRow("Header (nadpis):", self.header_input)
        meta_form.addRow("Footer (pata):", self.footer_input)
        meta_form.addRow("Remarks:", self.remarks_input)
        meta_form.addRow("Sources:", self.sources_input)
        meta_form.addRow("Extra:", self.extra_input)
        meta_group.setLayout(meta_form)
        sidebar.addWidget(meta_group)
        
        # Sekce pro uložení karet (každá logika má vlastní tlačítko)
        save_group = QGroupBox("Uložit do Anki")
        save_layout = QVBoxLayout()

        save_btn_style = """
            QPushButton {
                font-weight: bold;
                padding: 10px;
                color: white;
                border-radius: 6px;
                font-size: 13px;
            }
        """

        self.btn_hide_one_guess_one = QPushButton("Hide one, Guess one 🟢")
        self.btn_hide_one_guess_one.setStyleSheet(save_btn_style + "QPushButton { background-color: #2ecc71; } QPushButton:hover { background-color: #27ae60; }")
        self.btn_hide_one_guess_one.setToolTip("Skryje aktivní masku, ostatní nechá viditelné. Zkouší se právě jedna.")
        self.btn_hide_one_guess_one.clicked.connect(lambda: self.on_save_clicked("Hide One, Reveal One"))

        self.btn_hide_all_guess_one = QPushButton("Hide all, Guess one 🔵")
        self.btn_hide_all_guess_one.setStyleSheet(save_btn_style + "QPushButton { background-color: #3b82f6; } QPushButton:hover { background-color: #2563eb; }")
        self.btn_hide_all_guess_one.setToolTip("Skryje všechny masky. Zkouší se jedna zvýrazněná červeně, ostatní zůstávají zakryté žlutě.")
        self.btn_hide_all_guess_one.clicked.connect(lambda: self.on_save_clicked("Hide All, Reveal One"))

        self.btn_hide_all_guess_all = QPushButton("Hide all, Guess all 🟣")
        self.btn_hide_all_guess_all.setStyleSheet(save_btn_style + "QPushButton { background-color: #8e44ad; } QPushButton:hover { background-color: #7d3c98; }")
        self.btn_hide_all_guess_all.setToolTip("Skryje všechny masky najednou. Při odpovědi se odkryjí všechny.")
        self.btn_hide_all_guess_all.clicked.connect(lambda: self.on_save_clicked("Hide All, Reveal All"))

        save_layout.addWidget(self.btn_hide_one_guess_one)
        save_layout.addWidget(self.btn_hide_all_guess_one)
        save_layout.addWidget(self.btn_hide_all_guess_all)
        save_group.setLayout(save_layout)
        
        sidebar.addWidget(save_group)
        sidebar.addStretch()
        
        # Vytvoření widgetu pro sidebar k nastavení pevné šířky
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setFixedWidth(340)
        main_layout.addWidget(sidebar_widget)

        # Načtení index.html
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(addon_dir, "web", "index.html")
        self.web_view.setUrl(QUrl.fromLocalFile(html_path))
        self.web_view.loadFinished.connect(self.on_load_finished)

    def setup_bridge(self):
        self.bridge = WebBridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

    def run_js(self, code: str):
        self.web_view.page().runJavaScript(code)

    def on_tool_btn_clicked(self, tool_id: str):
        self.run_js(f"setTool('{tool_id}')")

    def on_load_finished(self, ok: bool) -> None:
        """Slot volaný po dokončení načítání HTML stránky ve WebView."""
        if not ok:
            return
        if self.editor:
            self.load_image_from_editor()

    def load_image_from_editor(self) -> None:
        """Vyhledá první obrázek v polích poznámky editoru a automaticky jej načte, včetně metadat."""
        if not self.editor or not self.editor.note:
            return
            
        import re
        import urllib.parse
        
        note = self.editor.note
        
        # Předvyplnění metadat z Anki poznámky
        if "header" in note:
            self.header_input.setText(note["header"])
        if "footer" in note:
            self.footer_input.setText(note["footer"])
        if "Remarks" in note:
            self.remarks_input.setPlainText(note["Remarks"])
        if "Sources" in note:
            self.sources_input.setText(note["Sources"])
        if "Extra" in note:
            self.extra_input.setPlainText(note["Extra"])

        image_name = None
        
        # Prohledáme všechna pole poznámky pro vyhledání obrázku
        for field_name, value in note.items():
            match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', value, re.IGNORECASE)
            if match:
                image_name = urllib.parse.unquote(match.group(1))
                print(f"DEBUG: Nalezen obrázek v poli {field_name}: {image_name}")
                break
                
        if not image_name:
            print("DEBUG: V polích poznámky nebyl nalezen žádný obrázek (tag <img>).")
            return
            
        # Získání absolutní cesty k obrázku v kolekci médií Anki
        if ANKI_AVAILABLE and mw and mw.col:
            media_dir = mw.col.media.dir()
            abs_path = os.path.join(media_dir, image_name)
            if os.path.exists(abs_path):
                print(f"DEBUG: Načítám obrázek z absolutní cesty: {abs_path}")
                self.load_image_into_canvas(abs_path)
            else:
                print(f"DEBUG: Soubor obrázku neexistuje na disku: {abs_path}")

    def load_image_into_canvas(self, path: str) -> None:
        """Načte obrázek z dané cesty, převede ho na base64 a odešle do Fabric.js."""
        self.current_image_path = path
        pixmap = QPixmap(path)
        w, h = pixmap.width(), pixmap.height()
        
        try:
            with open(path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode()
                img_url = f"data:image/png;base64,{b64_data}"
                self.run_js(f"loadImage('{img_url}', {w}, {h})")
        except Exception as e:
            QMessageBox.warning(self, "Chyba načítání", f"Nepodařilo se načíst obrázek: {str(e)}")

    def on_load_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Vybrat obrázek", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.load_image_into_canvas(path)

    def run_ocr_auto(self) -> None:
        if not self.current_image_path:
            QMessageBox.warning(self, "OCR", "Nejdříve načtěte obrázek.")
            return
        
        if ANKI_AVAILABLE:
            self.occlude_btn.setEnabled(False)
            self.occlude_btn.setText("Skenuji... ⌛")
            op = QueryOp(
                parent=self,
                op=lambda col: self.ocr.get_text_boxes(self.current_image_path),
                success=self._handle_ocr_results
            )
            op.with_progress("Probíhá OCR analýza...").run_in_background()
        else:
            boxes = self.ocr.get_text_boxes(self.current_image_path)
            self._handle_ocr_results(boxes)

    def _handle_ocr_results(self, boxes: List[Dict[str, Any]]) -> None:
        if ANKI_AVAILABLE:
            self.occlude_btn.setEnabled(True)
            self.occlude_btn.setText("Auto-OCR 🪄")
            
        for b in boxes:
            self.run_js(f"addRect({b['x']}, {b['y']}, {b['w']}, {b['h']}, '{b['text']}')")

    def on_save_clicked(self, mode: str) -> None:
        if not self.current_image_path:
            QMessageBox.warning(self, "Uložit", "Nejdříve načtěte obrázek.")
            return
            
        # Spustíme generování SVG v JS pro konkrétní vybraný režim
        self.web_view.page().runJavaScript(
            f"generateAllSVGs('{mode}')", 
            self._finalize_save
        )

    def _finalize_save(self, json_data: str):
        if not json_data:
            QMessageBox.warning(self, "Uložit", "Chyba při generování SVG masek na plátně.")
            return

        import json
        try:
            svg_data = json.loads(json_data)
            om_svg = svg_data.get("om_svg")
            q_svgs = svg_data.get("q_svgs", [])
            a_svgs = svg_data.get("a_svgs", [])
            
            if not q_svgs or not a_svgs:
                QMessageBox.warning(self, "Uložit", "Na plátně nebyly nalezeny žádné masky pro vytvoření karet.")
                return

            # Sběr metadat ze sidebar polí
            metadata = {
                "header": self.header_input.text().strip(),
                "footer": self.footer_input.text().strip(),
                "Remarks": self.remarks_input.toPlainText().strip(),
                "Sources": self.sources_input.text().strip(),
                "Extra": self.extra_input.toPlainText().strip()
            }

            # Volání AnkiHandleru pro uložení
            if self.anki:
                self.btn_hide_one_guess_one.setEnabled(False)
                self.btn_hide_all_guess_one.setEnabled(False)
                self.btn_hide_all_guess_all.setEnabled(False)
                
                op = QueryOp(
                    parent=self,
                    op=lambda col: self.anki.save_assets_and_notes(
                        self.current_image_path, om_svg, q_svgs, a_svgs, metadata
                    ),
                    success=self._handle_save_success
                )
                op.with_progress("Ukládám karty do Anki...").run_in_background()
            else:
                # Fallback mimo Anki (např. testování)
                print("DEBUG: Zápis mimo Anki - simulace")
                print(f"Metadata: {metadata}")
                print(f"Vygenerováno {len(q_svgs)} karet.")
                QMessageBox.information(
                    self, 
                    "Simulace uložení", 
                    f"Simulace úspěšná! Vygenerováno {len(q_svgs)} karet mimo prostředí Anki."
                )
                self.accept()

        except Exception as e:
            QMessageBox.warning(self, "Chyba", f"Chyba při zpracování SVG dat: {str(e)}")

    def _handle_save_success(self, count: int) -> None:
        self.btn_hide_one_guess_one.setEnabled(True)
        self.btn_hide_all_guess_one.setEnabled(True)
        self.btn_hide_all_guess_all.setEnabled(True)
        QMessageBox.information(self, "Uloženo", f"Úspěšně vytvořeno {count} karet v Anki.")
        self.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OcclusionDialog()
    window.show()
    sys.exit(app.exec())
