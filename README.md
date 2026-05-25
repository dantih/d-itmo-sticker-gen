# d-itmo-sticker-gen

Генератор наклеек с QR-кодом для помещений ИТМО.

Берёт PDF-макет наклейки (110×35 мм), генерирует QR-код из ссылки,
вставляет его в макет и отдаёт готовый PDF.

Используется для массового создания стикеров «Сканируй код и отправляй заявку
на уборку или ремонт» — расклейка по помещениям университета.

## Возможности

- CLI: `sticker-gen --url "https://..." --output sticker.pdf`
- HTTP-сервер: `sticker-gen --serve --port 8080`
- Веб-интерфейс: форма ввода ссылки, превью PDF, скачивание
- Замена QR-кода в существующем PDF-макете с сохранением всей остальной вёрстки
- Готовый systemd unit для автозапуска

## Быстрый старт

```bash
# Установка
pip install sticker-gen

# Скачай или положи шаблон maket.pdf рядом (или укажи --template)
# Встроенный шаблон используется по умолчанию

# CLI: сгенерировать одну наклейку
sticker-gen --url "https://forms.yandex.ru/u/..." -o nakleika.pdf

# HTTP-сервер
sticker-gen --serve --port 8080
# → http://localhost:8080/
```

## Использование

### CLI

```bash
sticker-gen [OPTIONS]

Options:
  --url URL           Ссылка для QR-кода
  --output, -o FILE   Выходной PDF-файл
  --template FILE     Путь к PDF-шаблону (по умолч. встроенный maket.pdf)
  --serve             Режим HTTP-сервера
  --port PORT         Порт (по умолч. 8080)
  --host HOST         Хост (по умолч. 0.0.0.0)
```

### HTTP API

```
GET /generate?url=<URL>
  → Content-Type: application/pdf
  → attachment-скачивание

GET / → веб-интерфейс
GET /health → OK
```

### Примеры

```bash
# Яндекс.Форма
sticker-gen --url "https://forms.yandex.ru/u/67e1a2c3d046880e2b8f4a12/" -o itmo_sticker.pdf

# Любая ссылка
sticker-gen --url "https://itmo.ru" -o itmo_sticker.pdf

# Сервер
sticker-gen --serve --port 8080 --template /etc/sticker/maket.pdf
```

## Установка как сервис (systemd)

```bash
sudo cp sticker-gen.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sticker-gen
```

Сервис запускается на порту 8080, слушает на всех интерфейсах.

## Разработка

```bash
git clone https://github.com/dantih/d-itmo-sticker-gen
cd d-itmo-sticker-gen
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Как это работает

1. Сервер получает URL
2. Библиотека `qrcode` генерирует QR-код как PNG
3. `reportlab` рисует QR в PDF-оверлей нужного размера и позиции
4. `PyPDF2` мерджит оверлей с исходным макетом (merge_page)
5. Возвращается готовый PDF

Макет (110×35 мм) содержит:
- Левую часть: поле для QR-кода
- Правую часть: заголовок «Что-то сломано? Грязно?», логотип ИТМО, призыв к действию

## Лицензия

MIT
