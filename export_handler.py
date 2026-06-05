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
    """Třída pro generování SVG řetězce kompatibilního s Anki Image Occlusion."""

    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    def generate(self, masks: List[Any]) -> str:
        """
        Převede seznam masek z plátna do SVG formátu.
        Anki IO očekává specifickou strukturu s ID a třídami.
        """
        # Vytvoření kořenového elementu <svg>
        svg_root = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": str(self.width),
            "height": str(self.height),
            "viewBox": f"0 0 {self.width} {self.height}"
        })

        # Přidání g (group) elementu pro masky
        g_layer = ET.SubElement(svg_root, "g", {
            "title": "Layer 1"
        })

        for i, mask in enumerate(masks):
            # Anki IO vyžaduje 'id' začínající na 'mask' a rozměry
            # mask.data obsahuje x, y, w, h
            data = mask.data
            ET.SubElement(g_layer, "rect", {
                "id": f"mask_{i}",
                "x": str(data.x),
                "y": str(data.y),
                "width": str(data.w),
                "height": str(data.h),
                "fill": "#FFE000",
                "stroke": "#000000"
            })

        # Převod na řetězec
        return ET.tostring(svg_root, encoding="unicode")

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
