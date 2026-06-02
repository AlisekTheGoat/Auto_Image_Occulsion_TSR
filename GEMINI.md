# 🧠 GEMINI.md - Auto Anki Image Occlusion

## 📋 1. Přehled projektu
Tento projekt je **bezplatný open-source doplněk** (Add-on) pro Anki.
Cíl → automatizovat tvorbu image occlusion kartiček.
Cílová skupina → studenti medicíny a high-volume learners.
Inspirace → Image Occlusion Enhanced + **přidaná automatizace**.

## 🛠️ 2. Tech Stack & Závislosti
* **Hlavní jazyk** → Python 3.9+ (kompatibilní s Anki ekosystémem).
* **GUI Framework** → PyQt6 / Qt6 (integrované v Anki).
* **OCR Engine** → Tesseract OCR (knihovna `pytesseract`).
* **Canvas systém** → Vlastní **SVG Canvas** pro úpravu, maskování a manipulaci s uzly.

## 🚀 3. Architektura & Workflow
1. **Uživatel vloží obrázek** → Načtení do vlastního SVG Canvasu.
2. **Automatizace na pozadí** → Tesseract OCR naskenuje text a štítky.
3. **Zpracování Bounding Boxů** → Souřadnice textu → automatická konverze na obdélníky.
4. **Generování masek** → SVG `<rect>` tvary se vykreslí přes detekovaný text.
5. **Anki Integrace** → Export masek přímo do SQLite databáze Anki.

## 🤖 4. Pravidla pro Gemini CLI
Při interakci přes Gemini CLI MUSÍŠ dodržovat tyto principy:
* **Role** → Působíš jako Lead MedTech Architect & Python Expert.
* **Styl kódu** → Modulární, type-hinted, kompatibilní s Anki hooks.
* **UI/UX Rule** → **SVG Canvas** musí být interaktivní (drag, drop, resize masek).
* **Formát odpovědí** → Vysoce strukturovaný, minimum omáčky, maximum přesnosti.