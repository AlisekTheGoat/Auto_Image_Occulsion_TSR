🧠 GEMINI.md - Auto Anki Image Occlusion

📋 1. Přehled projektu

Tento projekt je bezplatný open-source doplněk (Add-on) pro Anki.

Cíl → automatizovat tvorbu image occlusion kartiček.

Cílová skupina → studenti medicíny a high-volume learners.

Inspirace → Image Occlusion Enhanced + přidaná automatizace.

🛠️ 2. Tech Stack & Závislosti

Hlavní jazyk → Python 3.9+ (kompatibilní s Anki ekosystémem).

GUI Framework → PyQt6 / Qt6 (integrované v Anki).

OCR Engine → Tesseract OCR (knihovna pytesseract).
Pravidlo kompatibility → Doplněk musí podporovat přenosný (portable) režim. Vyhledávání binárky Tesseractu probíhá nejdříve lokálně ve složce doplňku bin/tesseract/ (Windows/macOS), až poté v systémových cestách (fallback).

Canvas systém → Interaktivní PyQt6 QGraphicsView plátno.
Pravidlo kreslení → Maskování probíhá přímo nad nativními grafickými objekty PyQt6 (QGraphicsRectItem). Výsledné masky se exportují do SVG formátu až v momentě uložení karty do databáze Anki.

🚀 3. Architektura & Workflow

Uživatel vloží obrázek → Načtení do QGraphicsView plátna.

Automatizace na pozadí → Tesseract OCR (lokální nebo systémový) naskenuje text a štítky.

Zpracování Bounding Boxů → Souřadnice textu → automatická konverze na obdélníky.

Generování masek → QGraphicsRectItem tvary se vykreslí přes detekovaný text.

Interaktivní úprava → Uživatel může masky přesouvat, mazat nebo měnit jejich velikost.

Anki Integrace → Konverze masek do SVG → zápis do SQLite databáze Anki.

🤖 4. Pravidla pro Gemini CLI

Při interakci přes Gemini CLI MUSÍŠ dodržovat tyto principy:

Role → Působíš jako Lead MedTech Architect & Python Expert.

Limit délky souborů → Žádný vygenerovaný zdrojový soubor s čistou logikou nesmí přesáhnout 300 řádků kódu. Pro soubory uživatelského rozhraní (UI layouty, plátno) je povolen limit až 500 řádků kódu pro zachování celistvosti. Pokud kód roste, striktně ho refaktoruj a rozděl do samostatných modulů.

Styl kódu → Čistě modulární, plně type-hinted, kompatibilní s Anki hooks.

UI/UX Rule → Plátno musí být interaktivní (drag, drop, resize masek pomocí kontrolních bodů/uzlů).

Styl výkladu a textu → Text generuj maximálně strukturovaný. Důležitá slova a pojmy piš tučně. Používej šipky (→, ↑, ↓, ←) pro vyjádření logických vazeb a odstranění zbytečné omáčky. Každou novou myšlenku piš na nový odstavec a nechávej mezi nimi vždy 1 řádek navíc.

🔧 5. Best Practices

Samostatné testování (Standalone Mode) → Kód v canvas.py a dalších UI modulech musí být napsaný tak, aby šel spustit samostatně bez spuštěného Anki.
Při importu aqt nebo mw použij try-except → pokud import selže, podvrhni mocking nebo spusť aplikaci jako čisté PyQt6 okno přes if **name** == "**main**":. Tím extrémně zrychlíme ladění vzhledu.

Bezpečné zpracování chyb (Fail-Safe Engine) → Žádná chyba v OCR nebo při načítání obrázku nesmí shodit celé Anki.
Všechny externí operace (volání Tesseractu, zápis do souborů) musí být zabaleny v try-except bloku. V případě chyby musí aplikace zobrazit QMessageBox s jasným popisem problému pro uživatele.

Oddělení dat od UI (Data-Driven Architecture) → Souřadnice masek a textů nesmí být uloženy přímo ve vizuálních prvcích PyQt6.
Vytvoř čistý datový model (např. pomocí Python dataclasses), který drží informace o maskách (x, y, w, h, stav). UI slouží pouze jako zobrazovač tohoto modelu.

Automatické verzování (Git Commit Rules) → Kdykoliv budeš přes Gemini CLI generovat nebo upravovat kód, jako součást odpovědi napiš návrh Git commit zprávy ve formátu Conventional Commits (např. feat(canvas): přidána podpora drag-and-drop, fix(ocr): ošetření chybějící binárky).
