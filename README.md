# velth carousels

Öffentliche Ablage für LinkedIn-Carousels von velth, damit Buffer die PDFs als Dokument anhängen kann.

- Ein Ordner pro Post: `posts/<Datum>_<thema>/carousel.pdf` und `cover.png`
- Ausgeliefert über GitHub Pages: `https://brunobauerquero-creator.github.io/velth-carousels/posts/...`
- Nur Inhalte, die ohnehin veröffentlicht werden. Keine Kundendaten, keine internen Unterlagen.

## Export

`tools/export_carousel.py` rendert die Boards aus dem Design-Canvas mit dessen eigener Runtime (`support.js`) zu `carousel.pdf` (1080 × 1350, eine Seite je Slide) und `cover.png`, und warnt bei Überlauf. Benötigt `playwright` und `pypdf`.

Buffer-Dokument-URL: `https://raw.githubusercontent.com/brunobauerquero-creator/velth-carousels/main/posts/<ordner>/carousel.pdf`
