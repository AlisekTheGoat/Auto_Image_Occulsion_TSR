import os
import uuid
import shutil
from typing import List, Dict, Any, Optional

try:
    from aqt import mw
    from anki.notes import Note
    from anki.models import NotetypeId
    ANKI_AVAILABLE = True
except ImportError:
    mw = None
    Note = None
    NotetypeId = None
    ANKI_AVAILABLE = False

class AnkiHandler:
    NOTE_TYPE_NAME = "Image Occlusion V2"
    
    FIELDS = [
        "ID (hidden)", "Header", "Image", "Question Mask", "Footer", 
        "Remarks", "Sources", "Extra 1", "Extra 2", "Answer Mask", "Original Mask"
    ]

    def __init__(self) -> None:
        if ANKI_AVAILABLE and mw:
            self.col = mw.col
            self._ensure_note_type()

    def _ensure_note_type(self) -> None:
        """Zkontroluje a případně vytvoří Note Type."""
        model = self.col.models.by_name(self.NOTE_TYPE_NAME)
        if model:
            return

        # Vytvoření nového modelu
        mm = self.col.models
        model = mm.new(self.NOTE_TYPE_NAME)
        
        # Přidání polí
        for field_name in self.FIELDS:
            fm = mm.new_field(field_name)
            mm.add_field(model, fm)

        # Šablony
        tmpl = mm.new_template("Occlusion Card")
        
        # Front Template (z GEMINI.md)
        tmpl['qfmt'] = """
<div class="io-wrapper">
  {{#Header}}<div id="io-header">{{Header}}</div>{{/Header}}
  <div id="io-container" style="position: relative; display: inline-block;">
    <div id="io-original" style="visibility: hidden;">{{Image}}</div>
    <div id="io-overlay" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
      {{Question Mask}}
    </div>
  </div>
  {{#Footer}}<div id="io-footer">{{Footer}}</div>{{/Footer}}
</div>
<script>
  var mask = document.querySelector("#io-overlay img");
  function showImage() { document.querySelector("#io-original").style.visibility = "visible"; }
  if (mask === null || mask.complete) { showImage(); } else { mask.addEventListener("load", showImage); }
</script>
        """
        
        # Back Template (z GEMINI.md)
        tmpl['afmt'] = """
{{FrontSide}}
<hr id="answer">
<div class="io-wrapper">
  <div id="io-container" style="position: relative; display: inline-block;">
    <div id="io-overlay" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
      {{Answer Mask}}
    </div>
  </div>
  {{#Remarks}}<div class="io-extra"><strong>Remarks:</strong> {{Remarks}}</div>{{/Remarks}}
  {{#Sources}}<div class="io-extra"><strong>Sources:</strong> {{Sources}}</div>{{/Sources}}
</div>
        """
        
        # CSS (z GEMINI.md)
        model['css'] = """
.card { font-family: arial; font-size: 20px; text-align: center; color: black; background-color: white; }
.io-wrapper { display: inline-block; margin: 0 auto; }
#io-container img { max-width: 100%; height: auto; display: block; }
.io-extra { margin-top: 15px; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #3b82f6; text-align: left; }
        """
        
        mm.add_template(model, tmpl)
        mm.add(model)

    def save_assets_and_notes(self, image_path: str, om_svg: str, q_svgs: List[str], a_svgs: List[str], masks_data: List[Any]) -> int:
        """Uloží média a vytvoří karty v Anki."""
        if not ANKI_AVAILABLE or not mw:
            return 0

        # 1. Uložení původního obrázku
        image_name = f"io-bg-{uuid.uuid4().hex}.png"
        shutil.copy(image_path, os.path.join(self.col.media.dir(), image_name))
        
        # 2. Uložení OM SVG
        om_name = f"io-om-{uuid.uuid4().hex}.svg"
        self.col.media.write_data(om_name, om_svg.encode("utf-8"))

        count = 0
        model = self.col.models.by_name(self.NOTE_TYPE_NAME)
        deck_id = mw.col.decks.get_current_id()

        for i, (q_svg, a_svg) in enumerate(zip(q_svgs, a_svgs)):
            # Uložení Q a A SVG
            q_name = f"io-q-{uuid.uuid4().hex}.svg"
            a_name = f"io-a-{uuid.uuid4().hex}.svg"
            self.col.media.write_data(q_name, q_svg.encode("utf-8"))
            self.col.media.write_data(a_name, a_svg.encode("utf-8"))

            # Vytvoření Note
            note = Note(self.col, model)
            note["ID (hidden)"] = f"{uuid.uuid4().hex}-{i}"
            note["Image"] = f'<img src="{image_name}">'
            note["Question Mask"] = f'<img src="{q_name}">'
            note["Answer Mask"] = f'<img src="{a_name}">'
            note["Original Mask"] = f'<img src="{om_name}">'
            
            # Pokud je k dispozici text z OCR, dáme ho do Remarks
            if hasattr(masks_data[i], 'data') and masks_data[i].data.text:
                note["Remarks"] = masks_data[i].data.text

            self.col.add_note(note, deck_id)
            count += 1

        return count
