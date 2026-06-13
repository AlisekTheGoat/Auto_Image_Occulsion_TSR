import uuid
import shutil
import os
from typing import List

try:
    from aqt import mw
    from anki.notes import Note
    ANKI_AVAILABLE = True
except ImportError:
    mw = None
    Note = None
    ANKI_AVAILABLE = False

class AnkiHandler:
    NOTE_TYPE_NAME = "AutoImageOcclusion"
    
    # 9 fields as requested in GEMINI.md
    FIELDS = [
        "ID", "header", "question image", "footer", 
        "Remarks", "Sources", "Extra", "Answer mask", "Original mask"
    ]

    def __init__(self) -> None:
        if ANKI_AVAILABLE and mw and mw.col:
            self.col = mw.col
            self._ensure_note_type()
        else:
            self.col = None

    def _ensure_note_type(self) -> None:
        """Zkontroluje a případně vytvoří/aktualizuje Note Type AutoImageOcclusion."""
        model = self.col.models.by_name(self.NOTE_TYPE_NAME)
        
        qfmt = """<div class="io-wrapper">
  {{#header}}
  <div id="io-header" style="font-size: 1.2em; margin-bottom: 10px; font-weight: bold;">{{header}}</div>
  {{/header}}
  <div id="io-container">
    {{question image}}
  </div>
  {{#footer}}
  <div id="io-footer" style="font-size: 0.9em; margin-top: 10px; color: #555;">{{footer}}</div>
  {{/footer}}
</div>"""

        afmt = """<div class="io-wrapper">
  {{#header}}
  <div id="io-header" style="font-size: 1.2em; margin-bottom: 10px; font-weight: bold;">{{header}}</div>
  {{/header}}
  <div id="io-container" style="cursor: pointer;">
    {{Answer mask}}
  </div>
  {{#footer}}
  <div id="io-footer" style="font-size: 0.9em; margin-top: 10px; color: #555;">{{footer}}</div>
  {{/footer}}
  
  {{#Remarks}}
  <div class="io-extra"><strong>Remarks:</strong> {{Remarks}}</div>
  {{/Remarks}}
  {{#Sources}}
  <div class="io-extra"><strong>Sources:</strong> {{Sources}}</div>
  {{/Sources}}
  {{#Extra}}
  <div class="io-extra">{{Extra}}</div>
  {{/Extra}}
</div>

<script>
  (function() {
    var container = document.querySelector("#io-container");
    var answerImg = document.querySelector("#io-container img");
    var originalMaskHtml = `{{Original mask}}`;
    
    if (container && answerImg && originalMaskHtml) {
      var originalSrc = "";
      var match = originalMaskHtml.match(/src=["']([^"']+)["']/);
      if (match) {
        originalSrc = match[1];
      }
      
      if (originalSrc) {
        var isShowingOriginal = false;
        var answerSrc = answerImg.src;
        
        container.addEventListener("click", function() {
          if (isShowingOriginal) {
            answerImg.src = answerSrc;
          } else {
            answerImg.src = originalSrc;
          }
          isShowingOriginal = !isShowingOriginal;
        });
      }
    }
  })();
</script>"""

        css = """.card {
  font-family: arial;
  font-size: 20px;
  text-align: center;
  color: black;
  background-color: white;
}
.io-wrapper {
  display: inline-block;
  margin: 0 auto;
}
#io-container img {
  max-width: 100%;
  height: auto;
  display: block;
}
.io-extra {
  margin-top: 15px;
  padding: 10px;
  background-color: #f9f9f9;
  border-left: 3px solid #3b82f6;
  text-align: left;
}"""

        if model:
            # Model již existuje, zaktualizujeme jeho šablony a CSS pro responzivitu
            tmpl = model['tmpls'][0]
            tmpl['qfmt'] = qfmt
            tmpl['afmt'] = afmt
            model['css'] = css
            self.col.models.save(model)
            return

        # Vytvoření nového Note Type
        mm = self.col.models
        model = mm.new(self.NOTE_TYPE_NAME)
        
        for field_name in self.FIELDS:
            fm = mm.new_field(field_name)
            mm.add_field(model, fm)

        tmpl = mm.new_template("Occlusion Card")
        tmpl['qfmt'] = qfmt
        tmpl['afmt'] = afmt
        model['css'] = css
        
        mm.add_template(model, tmpl)
        mm.add(model)

    def save_assets_and_notes(self, image_path: str, om_svg: str, q_svgs: List[str], a_svgs: List[str], metadata: dict) -> int:
        """
        Uloží média (podkladový obrázek a SVG masky) a zapíše nové poznámky do databáze Anki.
        Vrací počet úspěšně přidaných karet.
        """
        if not ANKI_AVAILABLE or not mw:
            return 0

        from .export_handler import SVGExporter

        # 1. Zkopírování originálního obrázku na pozadí do složky médií Anki
        image_ext = os.path.splitext(image_path)[1] or ".png"
        image_name = f"io-bg-{uuid.uuid4().hex}{image_ext}"
        shutil.copy(image_path, os.path.join(self.col.media.dir(), image_name))
        
        # 2. Úprava a zápis Original Mask (OM) SVG souboru
        fixed_om_svg = SVGExporter.fix_svg_background(om_svg, image_name)
        om_name = f"io-om-{uuid.uuid4().hex}.svg"
        self.col.media.write_data(om_name, fixed_om_svg.encode("utf-8"))

        count = 0
        model = self.col.models.by_name(self.NOTE_TYPE_NAME)
        deck_id = mw.col.decks.get_current_id()

        # 3. Zápis poznámek pro každou masku
        for i, (q_svg, a_svg) in enumerate(zip(q_svgs, a_svgs)):
            q_name = f"io-q-{uuid.uuid4().hex}.svg"
            a_name = f"io-a-{uuid.uuid4().hex}.svg"
            
            # Oprava base64 odkazů v SVG na lokální soubory
            fixed_q_svg = SVGExporter.fix_svg_background(q_svg, image_name)
            fixed_a_svg = SVGExporter.fix_svg_background(a_svg, image_name)
            
            # Zápis SVG souborů do složky médií Anki
            self.col.media.write_data(q_name, fixed_q_svg.encode("utf-8"))
            self.col.media.write_data(a_name, fixed_a_svg.encode("utf-8"))

            note = Note(self.col, model)
            note["ID"] = f"{uuid.uuid4().hex}-{i}"
            note["header"] = metadata.get("header", "")
            note["footer"] = metadata.get("footer", "")
            note["question image"] = f'<img src="{q_name}">'
            note["Answer mask"] = f'<img src="{a_name}">'
            note["Original mask"] = f'<img src="{om_name}">'
            note["Remarks"] = metadata.get("Remarks", "")
            note["Sources"] = metadata.get("Sources", "")
            note["Extra"] = metadata.get("Extra", "")

            self.col.add_note(note, deck_id)
            count += 1

        return count
