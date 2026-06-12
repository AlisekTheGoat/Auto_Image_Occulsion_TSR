import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class SVGMask:
    x: float
    y: float
    w: float
    h: float
    id: int

class SVGExporter:
    """Třída pro generování SVG řetězců kompatibilních s Anki IO Enhanced."""

    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    def generate_om(self, masks: List[Any]) -> str:
        """Generuje Original Mask (všechny masky žluté)."""
        return self._build_svg(masks, active_idx=-1, mode="om")

    def generate_q(self, masks: List[Any], active_idx: int) -> str:
        """Generuje Question Mask (aktivní červená, ostatní žluté)."""
        return self._build_svg(masks, active_idx=active_idx, mode="q")

    def generate_a(self, masks: List[Any], active_idx: int) -> str:
        """Generuje Answer Mask (aktivní skrytá, ostatní žluté)."""
        return self._build_svg(masks, active_idx=active_idx, mode="a")

    def _build_svg(self, masks: List[Any], active_idx: int, mode: str) -> str:
        svg_root = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {self.width} {self.height}"
        })

        g_layer = ET.SubElement(svg_root, "g", {"title": "Layer 1"})

        for i, mask in enumerate(masks):
            data = mask.data
            
            # Barvy dle GEMINI.md
            color_yellow = "#fffcc4"
            color_red = "#fc4242"
            
            fill = color_yellow
            if mode == "q" and i == active_idx:
                fill = color_red
            
            attribs = {
                "id": f"mask_{i}",
                "fill": fill,
                "stroke": "#000000",
                "stroke-width": "1.5"
            }

            if mode == "a" and i == active_idx:
                attribs["display"] = "none"

            if data.shape_type == "rect":
                attribs.update({
                    "x": str(data.x), "y": str(data.y),
                    "width": str(data.w), "height": str(data.h)
                })
                ET.SubElement(g_layer, "rect", attribs)
            
            elif data.shape_type == "ellipse":
                attribs.update({
                    "cx": str(data.x + data.w/2), "cy": str(data.y + data.h/2),
                    "rx": str(data.w/2), "ry": str(data.h/2)
                })
                ET.SubElement(g_layer, "ellipse", attribs)
            
            elif data.shape_type == "path":
                # Pro path musíme získat data z QPainterPath
                if hasattr(mask, "path"):
                    path_str = self._qt_path_to_svg(mask.path())
                    attribs["d"] = path_str
                    ET.SubElement(g_layer, "path", attribs)

        return ET.tostring(svg_root, encoding="unicode")

    def _qt_path_to_svg(self, path: Any) -> str:
        """Převod QPainterPath na SVG path string (d atribut)."""
        path_str = ""
        for i in range(path.elementCount()):
            el = path.elementAt(i)
            if el.isMoveTo():
                path_str += f"M {el.x} {el.y} "
            elif el.isLineTo():
                path_str += f"L {el.x} {el.y} "
            elif el.isCurveTo():
                # CurveTo v Qt má 3 elementy (control1, control2, end)
                # Pro zjednodušení v tomto doplňku u lassa používáme LineTo
                path_str += f"L {el.x} {el.y} "
        return path_str.strip()

    @staticmethod
    def get_anki_note_data(svg_content: str, image_name: str) -> Dict[str, str]:
        """
        Příprava polí pro Anki kartu (Note).
        Typické IO karty mají pole: Image, ID, Question Mask, Answer Mask, Original Mask.
        """
        return {
            "Image": f'<img src="{image_name}">',
            "Question Mask": svg_content, # Zde se v Anki IO logice skrývají/odkrývají masky
            "Original Mask": svg_content
        }
