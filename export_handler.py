import re

class SVGExporter:
    """Třída pro úpravu a zpracování SVG masek z Fabric.js plátna."""

    @staticmethod
    def fix_svg_background(svg_content: str, image_name: str) -> str:
        """
        Nahradí base64 data URL pozadí v SVG souboru odkazem na soubor v collection.media Anki.
        Tím se zajistí, že SVG soubor bude malý a bude správně odkazovat na pozadí.
        """
        # Hledáme atributy href="data:..." nebo xlink:href="data:..." a nahradíme je odkazem na image_name
        pattern = r'(href|xlink:href)="data:image/[^"]+"'
        replacement = f'\\1="{image_name}"'
        
        # Provedeme nahrazení
        fixed_svg = re.sub(pattern, replacement, svg_content)
        return fixed_svg
