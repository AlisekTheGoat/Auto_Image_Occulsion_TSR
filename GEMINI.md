🧠 GEMINI.md - Auto Anki Image Occlusion

**📋 1. Přehled projektu & Strategické Cíle**

Tento projekt je pokročilý open-source doplněk (Add-on) pro Anki.

Cíl → Plná automatizace tvorby image occlusion kartiček pomocí OCR a moderního hybridního rozhraní.

Cílová skupina → Studenti medicíny (maximalizace rychlosti studia komplexních anatomických schémat).

UX/UI Standard → Plynulost a přesnost na úrovni moderních webových vektorových editorů, plná integrace do nativního Add Cards dialogu Anki.

**🛠️ 2. Tech Stack & Hybridní Architektura plátna**

Pro eliminaci chyb PyQt6 při komplexní vektorové grafice (skákavé úchyty, sekavý freehand) přechází projekt na hybridní model.

Technologická struktura doplňku:

Python 3.9+ Backend → Zajišťuje OCR analýzu, registraci Note Type, správu médií a přímé zápisy do databáze Anki (add_note).

QWebEngineView (PyQt6) → Nativní okno Qt, které v doplňku slouží jako embedded webový prohlížeč.

Fabric.js Engine (HTML5 Canvas) → Běží uvnitř QWebEngineView a zajišťuje grafickou část:

100% plynulý resizing přes nativní bounding boxy.

Bezchybné freehand/lasso kreslení masek.

Desktopový výběr tažením myši (rubber-band selection).

Snadné seskupování (grouping) a zarovnávání objektů.

QWebChannel Bridge → Obousměrný komunikační most pro přenos souřadnic a SVG dat mezi JavaScriptem a Pythonem.

**🔄 3. Nativní Anki Workflow (Add Cards Integration)**

Doplněk se neotevírá z horní lišty Anki, ale je hluboce integrován do standardního procesu přidávání karet:

Postup uživatele (Step-by-Step):

Uživatel klikne na hlavní tlačítko Add v hlavním okně Anki.

Vybere specifický Card Type → AutoImageOculsion. (není povinné)

V editoru se zobrazí nativní pole typu poznámky (viz sekce 4).

Editor Toolbar Injection → Na formátovací liště editoru se stále zobrazuje ikona Auto Image Occlusion (umístěná na samém konci lišty).

Po kliknutí na ikonu se otevře hybridní editor s načteným obrázkem z pole karty.

Uživatel tvoří masky:

Automaticky přes tlačítko [Auto OCR] → detekce textu a vykreslení masek na plátno.

Manuálně pomocí nástrojů [Rectangle] | [Ellipse] | [Freehand].

Výběr karet → Uživatel označí masky a zvolí logiku generování:

Hide One, Reveal One

Hide All, Reveal All 

Hide All, Reveal One

Uložení karet → Kliknutím na [Add cards] v našem editoru se automaticky vygenerují SVG, uloží se do collection.media, zapíšou se nové karty do vybraného Decku a editor se zavře.

**🗃️ 4. Datová Struktura Note Type (9 Polí)**

Při spuštění doplňku v **init**.py probíhá kontrola existence Note Type AutoImageOculsion.

Pokud model v databázi chybí, automaticky se zaregistruje s těmito 9 poli v přesném pořadí:

ID → Unikátní identifikátor sady masek (UUID).

header → Textové pole pro nadpis nad obrázkem.

question image → HTML kód odkazující na podkladový obrázek překrytý červenou maskou aktivního dotazu (<img src="img_q_1.png">).

footer → Textové pole pod obrázkem.

Remarks → Doplňující poznámky pro studium.

Sources → Informace o zdroji (učebnice, atlas, strana).

Extra → Další volitelné textové pole pro extra poznámky ke kartičce.

Answer mask → HTML kód odkazující na podkladový obrázek s odkrytou zkoušenou maskou (<img src="img_a_1.png">).

Original mask → HTML kód odkazující na obrázek se všemi žlutými maskami pro celkový přehled (<img src="img_om.png">).

**👁️‍Cairo 5. Výpočetní OCR Jádro & Anatomické Shlukování Slov**

Pro medicínské snímky je klíčové, aby se samostatná slova neshlukovala chaoticky, ale tvořila logické víceslovné řetězce (např. Arteria laryngea superior).

Algoritmus horizontálního řetězení (Phrase Clustering):

Mějme dvě slova $W_1$ a $W_2$ na stejném řádku (line_num) se souřadnicemi $[x_1, y_1, w_1, h_1]$ a $[x_2, y_2, w_2, h_2]$, kde $x_2 > x_1$.

Průměrná výška slov:

$$H_{avg} = \frac{h_1 + h_2}{2}$$

Horizontální mezera:

$$G_{horiz} = x_2 - (x_1 + w_1)$$

Podmínka pro sloučení do jedné masky:

$$G_{horiz} \le H_{avg} \times M_{horiz}$$

Vertikální odchylka řádku:

$$\Delta Y \le H_{avg} \times M_{vert}$$

Default hodnoty v configu → $M_{horiz} = 1.2$ a $M_{vert} = 0.3$.
Splnění obou podmínek spojí slova do jednoho kompaktního obdélníku namísto izolovaných fragmentů.

**📐 6. JS Canvas Engine (Fabric.js & Komunikace)**

Doplněk využívá lokální instanci Fabric.js načtenou v HTML šabloně uvnitř QWebEngineView.

Klíčové vlastnosti JS Editoru:

Plynulý resizing → Zajištěn nativním transformačním matrixem Fabric.js (odstraňuje PyQt6 lagování).

Rubber-band Selection → Možnost tažením myši na prázdné ploše označit více masek najednou.

Group Objects → Kliknutím na [Group] se označené masky spojí do jedné logické entity (ideální pro zakrytí dlouhého popisku s šipkou).

Freehand Tool → Režim volné ruky kreslí hladkou křivku (smooth bezier path) převedenou na SVG element <path>.

Schéma komunikace přes QWebChannel:

[PyQt6 Python Backend]
│
├── (1) Načtení obrázku → Posílá base64 data do JS plátna
│
├── (2) Kliknutí na [Auto OCR] → Spustí Tesseract → Vrací JSON souřadnic masek
│
└── (4) Kliknutí na [Add cards] ← Přijímá pole vygenerovaných SVG masek z JS

**💾 7. Generování masek & Zápis do Anki DB**

Při uložení doplňku se vygenerují 3 stavy masek a zapíšou se jako samostatné notes pro každou vybranou masku (nebo skupinu masek).

Original mask (om.png) → Všechny masky vykresleny žlutou barvou (#fffcc4, opacity="0.8").

Question mask (q\_[idx].png) → Aktivní maska je červená (#fc4242), ostatní jsou žluté.

Answer mask (a\_[idx].png) → Aktivní maska je skrytá (display="none"), ostatní jsou žluté.

Databázový zápis v Pythonu:

# Pro každou generovanou kartu:

note = mw.col.new_note(model_auto_io)
note["ID"] = f"{uuid.uuid4()}"
note["header"] = user_header_input
note["question image"] = f'<img src="{generated_q_filename}">'
note["Answer mask"] = f'<img src="{generated_a_filename}">'
note["Original mask"] = f'<img src="{generated_om_filename}">'
note["Remarks"] = remarks_input
note["Sources"] = sources_input
mw.col.add_note(note, target_deck_id)

**🤖 8. Striktní Instrukce pro Gemini CLI**

Při generování nebo refaktorování kódu tohoto projektu MUSÍŠ dodržovat následující pravidla:

Striktní modularita → Upravuj vždy pouze jeden soubor na jeden turn.

Čistý otypovaný kód → Používej plný Python Type-Hinting a robustní ošetření chyb.

Anki API standardy → Používej výhradně moderní hooks API a asynchronní QueryOp pro operace na pozadí.

Komentáře → Veškerý kód musí obsahovat jasné a srozumitelné komentáře vysvětlující logiku algoritmu.

docs(gemini.md): kompletni prepis architektury na hybridni model a integraci do add cards workflow
