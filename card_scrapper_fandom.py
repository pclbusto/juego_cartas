#!/usr/bin/env python3
"""
card_scrapper_fandom.py

Dos modos de uso:

  1) Recolectar URLs (necesita Playwright por Cloudflare):
     python card_scrapper_fandom.py scrape-urls [--from-page N] [--to-page M] [--out urls.txt] [--delay S]

  2) Descargar imágenes desde un txt de URLs (no necesita Playwright):
     python card_scrapper_fandom.py download-urls [--input urls.txt] [--output DIR] [--delay S]
"""

import argparse
import re
import time
import requests
from pathlib import Path
from urllib.parse import unquote

BASE_URL       = "https://yugioh.fandom.com"
CATEGORY_URL   = "https://yugioh.fandom.com/es/wiki/Categor%C3%ADa:Carta"
DEFAULT_OUTPUT = "/mnt/green/card_scrapper"
DEFAULT_URLS   = "fandom_image_urls.txt"

DL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}


# ── Helpers comunes ───────────────────────────────────────────────────────────

def image_filename_from_url(url):
    m = re.search(r"/images/[0-9a-f]/[0-9a-f]{2}/(.+?)(?:/revision|$)", url)
    if m:
        return unquote(m.group(1))
    return unquote(url.rstrip("/").split("/")[-1].split("?")[0]) or "card.jpg"


# ── Modo 1: scrape-urls ───────────────────────────────────────────────────────

def cmd_scrape_urls(args):
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    out_path = Path(args.out)
    # Cargar URLs ya guardadas para no duplicar
    existing = set()
    if out_path.exists():
        with open(out_path, "r", encoding="utf-8") as f:
            existing = {line.strip() for line in f if line.strip()}
    print(f"[*] URLs ya en archivo: {len(existing)}")

    found_new = 0

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            user_agent=DL_HEADERS["User-Agent"],
            locale="es-ES",
        )
        page = context.new_page()

        current_url = CATEGORY_URL
        page_num    = 1

        print(f"[*] Páginas: {args.from_page} → {args.to_page or '∞'}")
        print(f"[*] Salida : {out_path}\n")

        with open(out_path, "a", encoding="utf-8") as out_file:
            while current_url:
                if args.to_page and page_num > args.to_page:
                    print(f"[*] Límite alcanzado ({args.to_page}).")
                    break

                # Saltar páginas anteriores a from_page
                if page_num < args.from_page:
                    print(f"[~] Saltando página {page_num}...", end="\r")
                    try:
                        _, current_url = _get_category_page(page, current_url)
                    except Exception as e:
                        print(f"\n[!] Error saltando pág {page_num}: {e}")
                        break
                    page_num += 1
                    time.sleep(args.delay)
                    continue

                print(f"[Página {page_num}] {current_url}")
                try:
                    card_links, next_url = _get_category_page(page, current_url)
                except Exception as e:
                    print(f"  [!] Error en página {page_num}: {e}")
                    break

                print(f"  {len(card_links)} cartas")

                for card_name, card_url in card_links:
                    img_url = _get_card_image_url(page, card_url, args.delay)

                    if not img_url:
                        print(f"  [-] Sin imagen: {card_name}")
                        print(f"      carta : {card_url}")
                        time.sleep(args.delay)
                        continue

                    if img_url in existing:
                        print(f"  [=] Ya existe: {image_filename_from_url(img_url)}")
                    else:
                        out_file.write(img_url + "\n")
                        out_file.flush()
                        existing.add(img_url)
                        found_new += 1
                        print(f"  [+] {card_name}")
                        print(f"      carta  : {card_url}")
                        print(f"      imagen : {img_url}")

                    time.sleep(args.delay)

                current_url = next_url
                page_num   += 1
                time.sleep(args.delay)

        browser.close()

    print(f"\n[Fin] URLs nuevas guardadas: {found_new} | Total en archivo: {len(existing)}")


def _get_category_page(page, url):
    from playwright.sync_api import TimeoutError as PWTimeout
    page.goto(url, wait_until="domcontentloaded", timeout=40_000)
    links = []
    for a in page.query_selector_all(".category-page__member-link"):
        href = a.get_attribute("href") or ""
        name = a.inner_text().strip()
        if "categor" not in href.lower():
            links.append((name, BASE_URL + href if href.startswith("/") else href))
    next_url = None
    nxt = page.query_selector(".category-page__pagination-next")
    if nxt:
        href = nxt.get_attribute("href") or ""
        if href:
            next_url = BASE_URL + href if href.startswith("/") else href
    return links, next_url


def _get_card_image_url(page, card_url, delay):
    from playwright.sync_api import TimeoutError as PWTimeout
    try:
        page.goto(card_url, wait_until="domcontentloaded", timeout=40_000)
        try:
            page.wait_for_selector("aside img", timeout=8_000)
        except PWTimeout:
            pass
    except PWTimeout:
        print(f"    [!] Timeout: {card_url}")
        return None

    for img in page.query_selector_all("aside img, figure img, img"):
        src = img.get_attribute("data-src") or img.get_attribute("src") or ""
        if "static.wikia.nocookie.net/yugiohenespanol/images" in src and ".jpg" in src.lower():
            src = re.sub(r"/revision/latest/scale-to-width-down/\d+", "/revision/latest", src)
            return src.split("?")[0]

    return None


# ── Modo 2: download-urls ─────────────────────────────────────────────────────

def cmd_download_urls(args):
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[!] Archivo no encontrado: {input_path}")
        return

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"[*] {len(urls)} URLs en {input_path}")
    print(f"[*] Destino: {output_dir}\n")

    downloaded = skipped = errors = 0
    session = requests.Session()
    session.headers.update(DL_HEADERS)

    for url in urls:
        filename = image_filename_from_url(url)
        dest = output_dir / filename

        if dest.exists():
            print(f"[=] Ya existe : {filename}")
            skipped += 1
            continue

        try:
            resp = session.get(url, timeout=30, stream=True)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            print(f"[+] {filename}")
            downloaded += 1
        except Exception as e:
            print(f"[!] Error {filename}: {e}")
            errors += 1

        time.sleep(args.delay)

    print(f"\n[Fin] Descargadas: {downloaded} | Ya existían: {skipped} | Errores: {errors}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scraper de imágenes de cartas desde yugioh.fandom.com/es"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # scrape-urls
    p_scrape = sub.add_parser("scrape-urls", help="Recolecta URLs de imágenes → txt")
    p_scrape.add_argument("--from-page", type=int, default=1, metavar="N")
    p_scrape.add_argument("--to-page",   type=int, default=None, metavar="M")
    p_scrape.add_argument("--out",       type=str, default=DEFAULT_URLS,
                          help=f"Archivo de salida (default: {DEFAULT_URLS})")
    p_scrape.add_argument("--delay",     type=float, default=1.0,
                          help="Segundos entre requests (default: 1.0)")

    # download-urls
    p_dl = sub.add_parser("download-urls", help="Descarga imágenes desde un txt de URLs")
    p_dl.add_argument("--input",  type=str, default=DEFAULT_URLS,
                      help=f"Archivo de URLs (default: {DEFAULT_URLS})")
    p_dl.add_argument("--output", type=str, default=DEFAULT_OUTPUT,
                      help=f"Directorio de destino (default: {DEFAULT_OUTPUT})")
    p_dl.add_argument("--delay",  type=float, default=0.2,
                      help="Segundos entre descargas (default: 0.2)")

    args = parser.parse_args()
    if args.cmd == "scrape-urls":
        cmd_scrape_urls(args)
    else:
        cmd_download_urls(args)


if __name__ == "__main__":
    main()
