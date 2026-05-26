#!/usr/bin/env python3
"""
QR Sticker Generator v3
========================
Берёт PDF-макет наклейки, генерирует QR-код из ссылки,
накладывает его поверх макета (или заменяет) и отдаёт готовый PDF.

Подход: reportlab рисует макет как background изображение, 
поверх печатает QR-код.

Использование:
  python3 qr_sticker.py --url "https://example.com" -o sticker.pdf
  python3 qr_sticker.py --serve --port 8080
"""

import argparse
import io
import os
import sys
import uuid

from PIL import Image
import qrcode

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

# --- Конфигурация ---

# Пути по умолчанию — ищем maket.pdf рядом с пакетом, затем в templates/
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(_PKG_DIR, "templates", "maket.pdf")
OUTPUT_DIR = os.path.join(os.getcwd(), "sticker_output")

# Размер и позиция QR в PDF (pt)
QR_X = 9.843       # лево
QR_Y = 9.585       # низ (от нижнего края страницы)
QR_W = 72.563      # ширина
QR_H = 76.882      # высота

# Размер QR в пикселях рендеринга
QR_PX_W = 302
QR_PX_H = 320

# Размер страницы макета (pt)
PAGE_W = 311.811
PAGE_H = 99.2126

# Коэффициент для PDF -> PPM
PT_TO_MM = 0.3528


# =====================
# Шрифт для подписи (с кириллицей)
# =====================

def _get_cyrillic_font_name() -> str:
    """Возвращает имя шрифта с поддержкой кириллицы для reportlab.
    Пробует DejaVu Sans по известным путям, затем через fc-match,
    иначе Helvetica (без кириллицы).
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import subprocess as _sp

    _font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/DejaVuSans.ttf',
    ]
    _found = None
    for _fp in _font_paths:
        if os.path.exists(_fp):
            _found = _fp
            break
    if not _found:
        try:
            _found = _sp.check_output(
                ['fc-match', '-f', '%{file}', 'DejaVu Sans'],
                text=True
            ).strip()
            if not _found or not os.path.exists(_found):
                _found = None
        except Exception:
            _found = None
    if _found:
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', _found))
            return 'DejaVuSans'
        except Exception:
            pass
    return 'Helvetica'


def generate_qr_png(url: str, width=QR_PX_W, height=QR_PX_H) -> bytes:
    """Генерирует QR-код как PNG (RGBA)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((width, height), Image.NEAREST)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()







# =====================
# Подход без pdf2image (не требует дополнительных зависимостей)
# =====================

def generate_sticker_pypdf2_overlay(template_path: str, url: str, output_path: str,
                                     caption: str = ""):
    """
    Используем PyPDF2 + reportlab для оверлея QR на макет.
    Создаём PDF с QR, мерджим с макетом.
    """
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import io as py_io

    # QR как RGBA изображение
    qr_png = generate_qr_png(url, QR_PX_W, QR_PX_H)
    qr_img = Image.open(py_io.BytesIO(qr_png)).convert("RGBA")

    # Создаём overlay PDF
    overlay_buf = py_io.BytesIO()
    c = canvas.Canvas(overlay_buf, pagesize=(PAGE_W, PAGE_H))
    c.drawImage(
        ImageReader(qr_img),
        QR_X, QR_Y,
        width=QR_W,
        height=QR_H,
        mask='auto',
        preserveAspectRatio=True,
        anchor='sw',
    )
    # Подпись — мелкий шрифт снизу по центру
    if caption:
        c.setFont(_get_cyrillic_font_name(), 3.5)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawCentredString(PAGE_W / 2, 1.5, caption)
    c.save()

    # Читаем макет
    overlay_buf.seek(0)
    reader = PdfReader(template_path)
    overlay_reader = PdfReader(overlay_buf)

    writer = PdfWriter()

    page = reader.pages[0]
    overlay_page = overlay_reader.pages[0]

    # merge_page накладывает содержимое overlay поверх макета
    page.merge_page(overlay_page)

    writer.add_page(page)
    writer.write(output_path)


# =====================
# A4 лист — 8 одинаковых стикеров на странице
# =====================

def _make_filename(caption: str, prefix: str = "sticker") -> str:
    """
    Генерирует имя файла на основе подписи:
    - если подпись есть: транслитерирует, спецсимволы → '_'
    - если подписи нет: случайные 6 символов
    """
    import re
    if not caption:
        import string
        import random
        rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{prefix}_{rand}.pdf"
    # Простая транслитерация
    trans = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e',
        'ж':'zh','з':'z','и':'i','й':'i','к':'k','л':'l','м':'m',
        'н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u',
        'ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch',
        'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
        'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'E',
        'Ж':'Zh','З':'Z','И':'I','Й':'I','К':'K','Л':'L','М':'M',
        'Н':'N','О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U',
        'Ф':'F','Х':'Kh','Ц':'Ts','Ч':'Ch','Ш':'Sh','Щ':'Shch',
        'Ъ':'','Ы':'Y','Ь':'','Э':'E','Ю':'Yu','Я':'Ya',
        ' ':'_', '-':'_', '—':'_', '(':'_', ')':'_',
    }
    result = ''.join(trans.get(c, c) for c in caption)
    result = re.sub(r'_+', '_', result).strip('_')
    result = re.sub(r'[^a-zA-Z0-9_-]', '_', result)
    result = re.sub(r'_+', '_', result).strip('_')
    if not result:
        result = 'sticker'
    return f"{prefix}_{result[:40].rstrip('_')}.pdf"


A4_W = 841.89  # pt — альбомный A4 (297 × 210 мм)
A4_H = 595.28

STICKER_W = PAGE_W   # 311.811 pt
STICKER_H = PAGE_H   # 99.2126 pt

# Раскладка: 2 колонки по 5 обычных + 1 повёрнутый справа = 11 стикеров
A4_COLS = 2
A4_ROWS = 5

# Межстикерные промежутки
A4_GAP_X = 8   # pt между колонками
A4_GAP_Y = 6   # pt между рядами

# Ширина блока обычных (2 колонки)
BLOCK_W = A4_COLS * STICKER_W + (A4_COLS - 1) * A4_GAP_X
# + ширина повёрнутого стикера + зазор
TOTAL_W = BLOCK_W + A4_GAP_X + STICKER_H

# Высота блока обычных (5 рядов)
TOTAL_H = A4_ROWS * STICKER_H + (A4_ROWS - 1) * A4_GAP_Y

# Отступы для центрирования всей композиции
A4_MARGIN_X = (A4_W - TOTAL_W) / 2
A4_MARGIN_Y = (A4_H - TOTAL_H) / 2

STICKERS_PER_SHEET = A4_COLS * A4_ROWS + 1  # 11

# Позиция повёрнутого стикера (колонка 2, после двух колонок)
ROTATED_X = A4_MARGIN_X + BLOCK_W + A4_GAP_X
# После поворота на -90°, визуальная высота = STICKER_W (311.8 pt)
# Низ повёрнутого стикера = верхняя граница блока обычных минус его высота
ROTATED_Y = A4_MARGIN_Y + STICKER_W




def generate_sticker_a4_sheet(template_path: str, url: str, output_path: str,
                               caption: str = ""):
    """
    Генерирует альбомный лист A4.

    Раскладка: 2 колонки по 5 обычных стикеров + 1 повёрнутый на 90° справа.
    Всего 11 стикеров на листе.
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from pdf2image import convert_from_path
    from io import BytesIO
    import io as py_io

    # QR
    qr_png = generate_qr_png(url, QR_PX_W, QR_PX_H)
    qr_img = Image.open(py_io.BytesIO(qr_png)).convert("RGBA")

    # Рендерим макет один раз в PNG
    template_img = convert_from_path(
        template_path, dpi=150, first_page=1, last_page=1
    )[0]
    tmpl_buf = BytesIO()
    template_img.save(tmpl_buf, format='PNG')
    tmpl_buf.seek(0)

    # Компонуем A4
    a4_buf = py_io.BytesIO()
    c = canvas.Canvas(a4_buf, pagesize=(A4_W, A4_H))

    # Кешируем шрифт один раз до цикла
    _caption_font = _get_cyrillic_font_name() if caption else None

    # --- Обычные стикеры (2 колонки × 5 рядов) ---
    for i in range(A4_COLS * A4_ROWS):
        col = i % A4_COLS
        row = i // A4_COLS

        x = A4_MARGIN_X + col * (STICKER_W + A4_GAP_X)
        y = A4_MARGIN_Y + row * (STICKER_H + A4_GAP_Y)

        c.drawImage(
            ImageReader(tmpl_buf),
            x, y, width=STICKER_W, height=STICKER_H,
            preserveAspectRatio=True, anchor='sw',
        )
        c.drawImage(
            ImageReader(qr_img),
            x + QR_X, y + QR_Y,
            width=QR_W, height=QR_H,
            mask='auto', preserveAspectRatio=True, anchor='sw',
        )
        if caption and _caption_font:
            c.setFont(_caption_font, 3.5)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawCentredString(x + STICKER_W / 2, y + 1.5, caption)

    # --- Повёрнутый стикер справа ---
    rot_x = ROTATED_X
    rot_y = ROTATED_Y

    # Сохраняем контекст, поворачиваем на 90° против часовой
    c.saveState()
    # reportlab поворот вокруг (rot_x, rot_y)
    c.translate(rot_x, rot_y)
    # Поворот на 90° CCW: ширина станет высотой и наоборот
    c.rotate(-90)
    # Теперь (0,0) — нижний левый угол повёрнутого стикера.
    # После поворота на -90: то что было вдоль X теперь вдоль -Y.
    # Чтобы QR и подпись оказались в правильном месте,
    # отрисовываем макет с шириной STICKER_H и высотой STICKER_W
    # (поменяны местами из-за поворота).
    c.drawImage(
        ImageReader(tmpl_buf),
        0, 0,
        width=STICKER_W, height=STICKER_H,
        preserveAspectRatio=True, anchor='sw',
    )
    c.drawImage(
        ImageReader(qr_img),
        QR_X, QR_Y,
        width=QR_W, height=QR_H,
        mask='auto', preserveAspectRatio=True, anchor='sw',
    )
    if caption and _caption_font:
        c.setFont(_caption_font, 3.5)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawCentredString(STICKER_W / 2, 1.5, caption)

    c.restoreState()

    c.save()

    a4_buf.seek(0)
    with open(output_path, 'wb') as f:
        f.write(a4_buf.read())

    print(f"✅ A4-лист (альбомный): {output_path} ({STICKERS_PER_SHEET} стикеров)")


# =====================
# HTTP Сервис
# =====================

def run_http_server(host='0.0.0.0', port=8080, template=DEFAULT_TEMPLATE):
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    class StickerHandler(BaseHTTPRequestHandler):
        template_path = template

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            # http.server подаёт parsed.query как str в Python 3.12+,
            # но кириллица в сыром виде (UTF-8 octets как Latin-1).
            # Если строка содержит suspect-символы, перекодируем.
            raw_qs = parsed.query
            if isinstance(raw_qs, bytes):
                raw_qs = raw_qs.decode('utf-8', errors='replace')
            # Пытаемся «исправить» double-encoded UTF-8
            try:
                fixed = raw_qs.encode('latin-1').decode('utf-8')
                raw_qs = fixed
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
            params = urllib.parse.parse_qs(raw_qs)

            if parsed.path == '/':
                # Главная страница
                html_path = os.path.join(_PKG_DIR, 'templates', 'index.html')
                if os.path.exists(html_path):
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    with open(html_path, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b'QR Sticker Service. Use /generate?url=<URL>')
                return

            if parsed.path == '/health':
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK')
                return

            if parsed.path != '/generate':
                # favicon и прочее — 404
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                body = '404 Not Found\n'
                self.wfile.write(body.encode('utf-8'))
                return

            url = params.get('url', [None])[0]
            caption = params.get('caption', [None])[0] or ""


            if not url:
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'Missing "url" parameter')
                return

            allowed = ('http://', 'https://', 'tg://', 'itmo://')
            if not url.startswith(allowed):
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                msg = f'URL must start with: {", ".join(allowed)}'
                self.wfile.write(msg.encode('utf-8'))
                return

            try:
                # Определяем режим — по умолчанию один стикер
                mode = params.get('mode', ['single'])[0]

                if mode == 'a4':
                    out_name = _make_filename(caption, 'sticker_a4')
                    out_path = os.path.join(OUTPUT_DIR, out_name)
                    generate_sticker_a4_sheet(
                        self.template_path, url, out_path, caption=caption,
                    )
                else:
                    out_name = _make_filename(caption, 'sticker')
                    out_path = os.path.join(OUTPUT_DIR, out_name)
                    generate_sticker_pypdf2_overlay(
                        self.template_path, url, out_path, caption=caption,
                    )

                with open(out_path, 'rb') as f:
                    pdf_data = f.read()

                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Disposition',
                                 f'attachment; filename="{out_name}"')
                self.send_header('Content-Length', str(len(pdf_data)))
                self.end_headers()
                self.wfile.write(pdf_data)

                os.unlink(out_path)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'Error: {e}'.encode('utf-8'))

        def log_message(self, fmt, *args):
            print(f"[{self.log_date_time_string()}] {args[0]} {args[1]} {args[2]}")

    server = HTTPServer((host, port), StickerHandler)
    print(f"QR Sticker Service → http://{host}:{port}/generate?url=<URL>")
    print(f"Health check       → http://{host}:{port}/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


# =====================
# CLI
# =====================

def main():
    parser = argparse.ArgumentParser(description='Генератор наклеек с QR-кодом')
    parser.add_argument('--url', help='Ссылка для QR-кода')
    parser.add_argument('--output', '-o', help='Выходной PDF-файл')
    parser.add_argument('--caption', default='',
                        help='Подпись (мелкий текст справа внизу наклейки)')
    parser.add_argument('--template', default=DEFAULT_TEMPLATE,
                        help='Путь к PDF-шаблону (по умолчанию maket.pdf)')
    parser.add_argument('--serve', action='store_true',
                        help='Запустить HTTP-сервер')
    parser.add_argument('--port', type=int, default=8080, help='Порт')
    parser.add_argument('--host', default='0.0.0.0', help='Хост')

    args = parser.parse_args()

    if args.serve:
        run_http_server(host=args.host, port=args.port, template=args.template)
        return

    if not args.url:
        parser.print_help()
        print("\nУкажите --url <ссылка> или --serve для запуска сервера")
        sys.exit(1)

    output = args.output or os.path.join(OUTPUT_DIR, 'sticker_output.pdf')
    os.makedirs(os.path.dirname(output) or '.', exist_ok=True)

    generate_sticker_pypdf2_overlay(
        args.template, args.url, output, caption=args.caption,
    )
    print(f"✅ Готово: {output}")


if __name__ == '__main__':
    main()


# Для pip-установленного entry_point — main уже определена выше.
