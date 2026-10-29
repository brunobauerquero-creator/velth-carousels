"""Render design-canvas boards (.dc.html) to a LinkedIn carousel PDF + cover PNG.

Uses the canvas' own runtime (support.js = artifact-type/dc-runtime.js), so mascots,
components and loops render exactly as in the canvas.

Usage:
  python3 tools/export_carousel.py --project DIR --blobs DIR --out posts/2026-10-30_thema \
      Board1 Board2 ...

  --project  folder with the .dc.html boards and support.js
  --blobs    folder with the canvas assets, one file per asset id (<id>.png, <id>.jpg, ...)
  --out      output folder; writes carousel.pdf and cover.png
"""
import argparse
import http.server
import io
import pathlib
import threading

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

W, H = 1080, 1350


def make_handler(project: pathlib.Path, blobs: pathlib.Path):
    index = {p.stem: p for p in blobs.iterdir() if p.is_file()}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(project), **k)

        def do_GET(self):
            if self.path.startswith("/_blob/"):
                f = index.get(self.path.split("/")[2].split("?")[0])
                if f is None:
                    return self.send_error(404)
                self.send_response(200)
                self.send_header("Content-Type", self.guess_type(str(f)))
                self.end_headers()
                self.wfile.write(f.read_bytes())
                return
            super().do_GET()

        def log_message(self, *a):
            pass

    return Handler


def overflow_px(page) -> int:
    """Pixels by which the main content runs past its bottom padding (0 or less is fine)."""
    return page.evaluate(
        """() => { const m = document.querySelector('[data-main]'); if (!m) return 0;
        const limit = m.getBoundingClientRect().bottom - parseFloat(getComputedStyle(m).paddingBottom);
        let w = -9999; for (const c of m.children) w = Math.max(w, c.getBoundingClientRect().bottom - limit);
        return Math.round(w); }""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, type=pathlib.Path)
    ap.add_argument("--blobs", required=True, type=pathlib.Path)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("boards", nargs="+")
    a = ap.parse_args()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(a.project.resolve(), a.blobs.resolve()))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    a.out.mkdir(parents=True, exist_ok=True)
    writer, problems = PdfWriter(), []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        for i, name in enumerate(a.boards):
            page.goto(f"http://127.0.0.1:{a.port}/{name}.dc.html")
            page.wait_for_load_state("networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(1200)
            if (o := overflow_px(page)) > 0:
                problems.append(f"{name}: content overflows by {o}px")
            if i == 0:
                page.screenshot(path=str(a.out / "cover.png"))
            page.add_style_tag(content=f"@page{{size:{W}px {H}px;margin:0}} html,body{{margin:0}}")
            writer.append(PdfReader(io.BytesIO(page.pdf(width=f"{W}px", height=f"{H}px", print_background=True, page_ranges="1"))))
        browser.close()
    srv.shutdown()

    with open(a.out / "carousel.pdf", "wb") as f:
        writer.write(f)
    print(f"{a.out / 'carousel.pdf'}: {len(writer.pages)} pages")
    for pr in problems:
        print("WARNING", pr)


if __name__ == "__main__":
    main()
