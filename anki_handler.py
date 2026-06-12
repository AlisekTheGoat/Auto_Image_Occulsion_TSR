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
    NOTE_TYPE_NAME = "AutoImageOcclusion"
    
    # 9 fields as requested
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
        """Zkontroluje a případně vytvoří Note Type AutoImageOculsion."""
        model = self.col.models.by_name(self.NOTE_TYPE_NAME)
        if model:
            return

        mm = self.col.models
        model = mm.new(self.NOTE_TYPE_NAME)
        
        for field_name in self.FIELDS:
            fm = mm.new_field(field_name)
            mm.add_field(model, fm)

        tmpl = mm.new_template("Occlusion Card")
        
        # Front Template
        tmpl['qfmt'] = """
<div class="io-wrapper">
  {{#header}}
  <div id="io-header">{{header}}</div>
  {{/header}}
  <div id="io-container" style="position: relative; display: inline-block;">
    <div id="io-original" style="visibility: hidden;">{{question image}}</div>
    <div
      id="io-overlay"
      style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
    >
      {{Original mask}}
    </div>
  </div>
  {{#footer}}
  <div id="io-footer">{{footer}}</div>
  {{/footer}}
</div>

<script>
  var mask = document.querySelector("#io-overlay img");
  function showImage() {
    document.querySelector("#io-original").style.visibility = "visible";
  }
  if (mask === null || mask.complete) {
    showImage();
  } else {
    mask.addEventListener("load", showImage);
  }
</script>
        """
        
        # Back Template
        tmpl['afmt'] = """
<div class="io-wrapper">
  {{#header}}
  <div id="io-header">{{header}}</div>
  {{/header}}
  <div id="io-container" style="position: relative; display: inline-block;">
    <div>{{question image}}</div>
    <div
      id="io-overlay"
      style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
    >
      {{Answer mask}}
    </div>
  </div>
  {{#footer}}
  <div id="io-footer">{{footer}}</div>
  {{/footer}} {{#Remarks}}
  <div class="io-extra"><strong>Remarks:</strong> {{Remarks}}</div>
  {{/Remarks}} {{#Sources}}
  <div class="io-extra"><strong>Sources:</strong> {{Sources}}</div>
  {{/Sources}} {{#Extra}}
  <div class="io-extra">{{Extra}}</div>
  {{/Extra}}
</div>

<script>
  var toggle = function () {
    var amask = document.querySelector("#io-overlay img");
    if (amask) {
      amask.style.display = amask.style.display === "none" ? "block" : "none";
    }
  };
  document.querySelector("#io-container").addEventListener("click", toggle);
</script>
        """
        
        model['css'] = """
.card {
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
}
        """
        
        mm.add_template(model, tmpl)
        mm.add(model)

    def save_assets_and_notes(self, image_path: str, om_svg: str, q_svgs: List[str], a_svgs: List[str], card_data: List[str]) -> int:
        """Uloží média a vytvoří karty v Anki."""
        if not ANKI_AVAILABLE or not mw:
            return 0

        image_name = f"io-bg-{uuid.uuid4().hex}.png"
        shutil.copy(image_path, os.path.join(self.col.media.dir(), image_name))
        
        count = 0
        model = self.col.models.by_name(self.NOTE_TYPE_NAME)
        deck_id = mw.col.decks.get_current_id()

        for i, (q_svg, a_svg) in enumerate(zip(q_svgs, a_svgs)):
            q_name = f"io-q-{uuid.uuid4().hex}.svg"
            a_name = f"io-a-{uuid.uuid4().hex}.svg"
            self.col.media.write_data(q_name, q_svg.encode("utf-8"))
            self.col.media.write_data(a_name, a_svg.encode("utf-8"))

            note = Note(self.col, model)
            note["ID"] = f"{uuid.uuid4().hex}-{i}"
            note["question image"] = f'<img src="{image_name}">'
            note["Original mask"] = f'<img src="{q_name}">' # Question View
            note["Answer mask"] = f'<img src="{a_name}">'   # Answer View
            
            if i < len(card_data) and card_data[i]:
                note["Remarks"] = str(card_data[i])

            self.col.add_note(note, deck_id)
            count += 1

        return count
