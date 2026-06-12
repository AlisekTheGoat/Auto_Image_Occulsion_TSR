# 🧠 GEMINI.md - Auto Anki Image Occlusion

---

## 📋 1. Přehled projektu & Strategické Cíle

Tento projekt je bezplatný open-source doplněk (Add-on) pro **Anki**.

Cíl → **Plná automatizace** tvorby image occlusion kartiček pomocí **OCR**.

Cílová skupina → **Studenti medicíny** + high-volume learners (maximalizace rychlosti studia).

Inspirace → **Image Occlusion Enhanced (IOE)** + integrovaná AI/OCR inteligence.

UI/UX Cíl → Maximální **přehlednost**, čistota rozhraní a eliminace klikání (vše na 1 kliknutí přes kouzelnou hůlku 🪄).

---

## 🛠️ 2. Tech Stack, Závislosti & Spouštěcí Režimy

Hlavní jazyk → **Python 3.9+** (plná kompatibilní s Anki ekosystémem).

GUI Framework → **PyQt6 / Qt6** (nativně integrované v Anki).

OCR Engine → **Tesseract OCR** (knihovna `pytesseract`).

### Pravidlo přenositelnosti (Portable Mode)

Vyhledávání binárky **Tesseractu** probíhá v tomto pořadí:

1. Lokální složka doplňku `bin/tesseract/` (Windows/macOS) → **Nejvyšší priorita**.
2. Systémové cesty (Fallback) → `/usr/bin/tesseract` nebo Homebrew cesty na macOS.

### Canvas systém (Hybridní Architektura)

1. **Nativní PyQt6 plátno (`QGraphicsView`)** → Slouží pro pokročilé lokální kreslení, drag-and-drop a rychlé testování.
2. **WebView Bridge (`pycmd`)** → Slouží pro přímou integraci do vnitřního HTML editoru Anki.

---

## 📊 3. Komparativní Analýza Databází (Proč emulujeme IOE?)

Doplněk implementuje klasickou architekturu **Image Occlusion Enhanced (IOE)**, protože nativní řešení Anki neposkytuje dostatečnou flexibilitu pro pokročilé medicínské popisy.

| Technický parametr / Vlastnost | Nativní Image Occlusion (Anki v23.10+)         | Image Occlusion Enhanced (Náš Add-on)           |
| ------------------------------ | ---------------------------------------------- | ----------------------------------------------- |
| **Název typu poznámky**        | `Auto Image Occlusion`                         | `Auto Image Occlusion Enhanced`                 |
| **Struktura polí**             | Header, Image, Occlusion, Back Extra, Comments | 11 specifických polí (viz sekce 4)              |
| **Reprezentace masek**         | Textový řetězec v poli `Occlusion`             | Vektorové soubory **SVG** v `collection.media`  |
| **Vztah Note → Card**          | 1 Note = Více sourozeneckých karet             | 1 Maska = 1 Nezávislá Note (unikátní ID)        |
| **Vliv na FSRS**               | Funguje "Bury Siblings"                        | Karty jsou zcela nezávislé → precizní hodnocení |
| **Režie synchronizace**        | Extrémně nízká (text v SQLite)                 | Vyšší (generování fyzických SVG souborů)        |

---

## 🗃️ 4. Datová Struktura Note Type & Šablony

Při spuštění doplňku v `__init__.py` probíhá kontrola existence Note Type `AutoImageOcculsion`. Pokud neexistuje, automaticky se vytvoří těchto **11 polí** v přesném pořadí:

1. `ID (hidden)` → UUID s indexem karty (`uuid-oa-1`).
2. `Header` → Text nad obrázkem.
3. `Image` → HTML reference na zdroj `<img src="base_image.png">`.
4. `Question Mask` → HTML reference na aktivní masku `<img src="base_image-q1.svg">`.
5. `Footer` → Text pod obrázkem.
6. `Remarks` → Doplňující poznámky k dané struktuře.
7. `Sources` → Zdroj (učebnice/atlas).
8. `Extra 1` → Volitelné pole.
9. `Extra 2` → Volitelné pole.
10. `Answer Mask` → HTML reference na odkrytou masku `<img src="base_image-a1.svg">`.
11. `Original Mask` → HTML reference na kompletní přehled masek `<img src="base_image-om.svg">`.

### HTML Šablony Karet

**Lícová strana (Front Template):**

```html
<div class="io-wrapper">
  {{#Header}}
  <div id="io-header">{{Header}}</div>
  {{/Header}}
  <div id="io-container" style="position: relative; display: inline-block;">
    <div id="io-original" style="visibility: hidden;">{{Image}}</div>
    <div
      id="io-overlay"
      style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
    >
      {{Question Mask}}
    </div>
  </div>
  {{#Footer}}
  <div id="io-footer">{{Footer}}</div>
  {{/Footer}}
</div>

<script>
  // Prevence probliknutí obrázku před načtením masky
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
```

**Rubová strana (Back Template):**

```html
<div class="io-wrapper">
  {{#Header}}
  <div id="io-header">{{Header}}</div>
  {{/Header}}
  <div id="io-container" style="position: relative; display: inline-block;">
    <div>{{Image}}</div>
    <div
      id="io-overlay"
      style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
    >
      {{Answer Mask}}
    </div>
  </div>
  {{#Footer}}
  <div id="io-footer">{{Footer}}</div>
  {{/Footer}} {{#Remarks}}
  <div class="io-extra"><strong>Remarks:</strong> {{Remarks}}</div>
  {{/Remarks}} {{#Sources}}
  <div class="io-extra"><strong>Sources:</strong> {{Sources}}</div>
  {{/Sources}} {{#Extra 1}}
  <div class="io-extra">{{Extra 1}}</div>
  {{/Extra 1}}
</div>

<script>
  // Kliknutím na obrázek dočasně skryješ/zobrazíš masku odpovědi
  var toggle = function () {
    var amask = document.querySelector("#io-overlay img");
    if (amask) {
      amask.style.display = amask.style.display === "none" ? "block" : "none";
    }
  };
  document.querySelector("#io-container").addEventListener("click", toggle);
</script>
```

**Styling (Všechny karty - CSS):**

```css
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
```

---

## 👁️‍🗨️ 5. Výpočetní OCR Jádro & Předzpracování (`ocr.py`)

Kvalita detekce anatomických schémat závisí na předzpracování obrazu přes knihovnu **Pillow (PIL)**.

### Pipeline zpracování obrazu

1. Vstupní obrázek → Konverze do stupňů šedi (`Grayscale`) → Odstranění barevného šumu.
2. Vyhlazovací **Lanczosův Upscaling (2x)** → Zvýšení hustoty pixelů pro malá písma.
3. Spuštění Tesseractu s parametrem **PSM 12 (Sparse text with OSD)** → Optimalizace pro izolované textové štítky v diagramech.

### Hierarchie a filtrace dat z TSV výstupu (`pytesseract.image_to_data`)

| Název sloupce v TSV | Význam v hierarchii OCR     | Pravidla filtrace a interpretace dat                                 |
| ------------------- | --------------------------- | -------------------------------------------------------------------- |
| `level`             | Hierarchický stupeň detekce | Filtrujeme výhradně úroveň **5 (Slovo)**.                            |
| `block_num`         | Číslo prostorového bloku    | Identifikace koherentních vizuálních celků.                          |
| `line_num`          | Číslo řádku v bloku         | Určuje slova ležící na stejné horizontální ose.                      |
| `left` / `top`      | X / Y souřadnice v pixelech | Vzdálenost od levého / horního okraje upscalovaného obrazu.          |
| `width` / `height`  | Šířka / výška v pixelech    | Geometrický rozměr detekovaného slova.                               |
| `conf`              | Míra spolehlivosti (%)      | Hodnoty 0 až 100. Práh filtrace striktně nastaven na $>40$.          |
| `text`              | Rozpoznaný textový řetězec  | Samotné slovo. Prázdné řetězce a samostatná interpunkce se zahazují. |

---

## 📐 6. Prostorová Heuristika, Shlukování & SVG

Surová slova z Tesseractu se musí sloučit do víceslovných lékařských termínů (např. _Vena cava superior_) pomocí algoritmu **Box Merging**.

### Matematický model shlukování slov do řádku

Mějme dvě slova $W_1$ a $W_2$ na stejném řádku (`line_num`) se souřadnicemi $[x_1, y_1, w_1, h_1]$ a $[x_2, y_2, w_2, h_2]$, kde $x_2 > x_1$.

Průměrná výška slov:

$$H_{avg} = \frac{h_1 + h_2}{2}$$

Horizontální mezera:

$$G_{horiz} = x_2 - (x_1 + w_1)$$

Podmínka pro sloučení do jednoho Bounding Boxu:

$$G_{horiz} \le H_{avg} \times M_{horiz}$$

> `config.json` default hodnoty → $M_{horiz} = 1.2$ (horizontální multiplikátor), $M_{vert} = 1.5$ (vertikální multiplikátor s podmínkou minimálně 30% horizontálního překryvu).

### Detekce kolizí (Intersection over Union - IoU)

Zamezuje duplicitnímu překrývání masek. Pro novou masku $B_{new}$ a existující masku $B_{existing}$ platí:

$$IoU = \frac{\text{Obsah}(B_{new} \cap B_{existing})}{\text{Obsah}(B_{new} \cup B_{existing})}$$

Pokud je

$$IoU > 0.4$$

, nová maska se **zahodí**.

### Absolutní SVG Geometrie

Pro zamezení posunu masek na mobilních zařízeních generujeme SVG s atributem `viewBox` odpovídajícím přesným pixelům původního obrázku:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W_img H_img">
  <rect x="left" y="top" width="width" height="height" fill="#FFD700" stroke="#000000" stroke-width="1.5" />
</svg>

```

- **Original Mask (`-om.svg`)** → Všechny obdélníky jsou žluté (`#fffcc4`), krytí `opacity="1"`.
- **Question Mask (`-q[idx].svg`)** → Aktivní obdélník je červený (`#fc4242`), ostatní jsou žluté.
- **Answer Mask (`-a[idx].svg`)** → Aktivní obdélník má `display="none"`, ostatní jsou žluté.

---

## ⚡ 7. Asynchronní Architektura & Bridge (`QueryOp`)

Zpracování OCR nesmí nikdy zablokovat hlavní UI vlákno Anki (prevence zamrznutí aplikace).

Výpočetní operace na pozadí se provádí asynchronně přes `aqt.utils.QueryOp`.

### Workflow komunikace:

1. JavaScript ve WebView (`auto_io.js`) detekuje nástrojovou lištu a vloží tlačítko 🪄.
2. Uživatel klikne na 🪄 → JS odešle zprávu backendu: `pycmd(JSON.stringify({action: "run_ocr", image: imageName}));`.
3. Tlačítko se změní na ikonu načítání (⌛) a deaktivuje se.
4. Python zachytí zprávu přes `WebView` bridge, spustí `QueryOp` na pozadí.
5. Po úspěšném dokončení Python vrátí pole souřadnic a zavolá klientskou funkci `window.handleOcrResults(boxes);`.
6. Pokud dojde k chybě (chybějící Tesseract, nepodporovaný formát), asynchronní callback vyvolá `QMessageBox.critical` s jasným popisem problému.

---

## 🤖 8. Striktní Instrukce pro Gemini CLI

Při generování nebo refaktorování kódu tohoto projektu **MUSÍŠ** dodržovat následující pravidla:

### 1. Role & Styl Kódu

- Působíš jako **Lead MedTech Architect & Python Expert**.
- Kód musí být čistě modulární, plně **type-hinted**, komentovaný a využívat moderní Anki hooks API.

### 2. Limit délky souborů (Striktní Refaktorizace)

- **Čistá logika (např. `ocr.py`)** → Max **300 řádků** kódu.
- **Uživatelské rozhraní / Plátno (`canvas.py`)** → Max **500 řádků** kódu.
- Pokud kód přesahuje limit, striktně ho rozděl do sub-modulů!

### 3. Standalone mode (Izolované testování UI)

- Modul `canvas.py` a další UI komponenty musí jít spustit jako samostatná aplikace bez běžícího Anki!
- Používej bezpečné importy:

```python
try:
    import aqt
    from aqt import mw
except ImportError:
    # Režim Mockování / Spuštění čistého PyQt6 okna
    mw = None

```

### 4. Pravidla pro Git Commity

- Každý vygenerovaný kód musí na konci obsahovat návrh Git commit zprávy ve formátu **Conventional Commits**.
- Příklady: `feat(ocr): pridano prostorove shlukovani slov`, `fix(canvas): osetreni nulovych souradnic`.

### 5. Formátování textových výstupů (Pro tebe, Gemini!)

- **Tučně** zvýrazňuj důležité pojmy.
- Používej logické šipky (`→`, `↑`, `↓`, `←`) pro odstranění omáčky.
- Každou myšlenku nebo položku strukturuj do **samostatného odstavce s 1 prázdným řádkem navíc** pro dokonalou scannability!
