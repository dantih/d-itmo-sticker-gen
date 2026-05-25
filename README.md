# d-itmo-sticker-gen

Генератор наклеек с QR-кодом для помещений ИТМО.

Берёт PDF-макет наклейки (110×35 мм), генерирует QR-код из ссылки,
вставляет его в макет и отдаёт готовый PDF.

Используется для массового создания стикеров «Сканируй код и отправляй заявку
на уборку или ремонт» — расклейка по помещениям университета.

## Возможности

- **CLI:** `sticker-gen --url "https://..." --output sticker.pdf`
- **HTTP-сервер:** `sticker-gen --serve` — встроенная веб-морда с превью
- **API:** `GET /generate?url=<URL>` — возвращает готовый PDF
- Замена QR-кода в PDF-макете с сохранением всей вёрстки
- **Подпись** — опциональное текстовое поле, мелким шрифтом печатается снизу наклейки (чтобы не путать помещения при расклейке)
- **A4-лист** — генерация полного листа A4 с 8 одинаковыми стикерами для печати и нарезки
- systemd-юнит для автозапуска

## Установка

### Быстрая (одной командой)

```bash
pip install git+https://github.com/dantih/d-itmo-sticker-gen.git
```

После этого доступна команда `sticker-gen`. Пробуй:

```bash
sticker-gen --help
```

### Если система не даёт глобальную установку

```bash
pip3 install --user git+https://github.com/dantih/d-itmo-sticker-gen.git
```

После этого `sticker-gen` будет в `~/.local/bin/`. Если команда не находится:

```bash
export PATH="$HOME/.local/bin:$PATH"
sticker-gen --serve
```

### В изолированное окружение (venv)

```bash
python3 -m venv venv
source venv/bin/activate
pip install git+https://github.com/dantih/d-itmo-sticker-gen.git
sticker-gen --serve
```

### Локально из репозитория

```bash
git clone https://github.com/dantih/d-itmo-sticker-gen
cd d-itmo-sticker-gen
pip install .
```

После установки доступна команда `sticker-gen`.

## Использование

### CLI

```bash
# Одна наклейка
sticker-gen --url "https://forms.yandex.ru/u/..." -o nakleika.pdf

# С подписью (для маркировки помещения)
sticker-gen --url "https://forms.yandex.ru/u/..." -o nakleika.pdf \
  --caption "Коворкинг Альфа, 3 этаж"

# Со своим шаблоном
sticker-gen --url "https://itmo.ru" -o sticker.pdf --template my_maket.pdf
```

### HTTP-сервер

```bash
# Запуск на порту 8080 (по умолчанию)
sticker-gen --serve
# → http://localhost:8080/ — веб-интерфейс

# На другом порту (например, 9090)
sticker-gen --serve --port 9090

# На конкретном IP/хосте
sticker-gen --serve --host 127.0.0.1 --port 8080

# Вся цепочка — свой шаблон + подпись
sticker-gen --serve --port 8080 --template my_maket.pdf
```

В веб-интерфейсе два поля: **ссылка** и **подпись** (опционально).
После генерации появляются две кнопки:
- **«Скачать PDF»** — один стикер
- **«Скачать PDF A4»** — лист A4 с 8 стикерами для печати

### API

```
# Один стикер
GET /generate?url=https://forms.yandex.ru/u/...&caption=Коворкинг%20Альфа
Content-Type: application/pdf

# Лист A4 (8 стикеров для печати)
GET /generate?mode=a4&url=https://forms.yandex.ru/u/...&caption=Коворкинг%20Альфа
Content-Type: application/pdf
```

Параметры:
- `url` — обязательный, ссылка для QR-кода
- `caption` — опциональный, текст подписи снизу наклейки
- `mode` — `single` (по умолчанию, один стикер) или `a4` (лист A4 с 8 стикерами)

## Установка как systemd-сервис

```bash
# Скопировать юнит
sudo cp sticker-gen.service /etc/systemd/system/

# Отредактировать User/WorkingDirectory под свою среду
sudo systemctl daemon-reload
sudo systemctl enable --now sticker-gen
```

## Как это работает

1. Сервер получает URL
2. Библиотека `qrcode` генерирует QR-код (уровень коррекции H — 30%)
3. `reportlab` рисует QR как PDF-оверлей с точными координатами из макета
4. `PyPDF2.merge_page` накладывает оверлей поверх исходного PDF
5. Возвращается готовый PDF

Макет (110×35 мм):
```
┌──────────┬──────────────────────────┐
│          │  вітмо                    │
│   QR     │  Что-то сломано? Грязно?  │
│   код    │  Сканируй код и отправляй │
│          │  заявку на уборку/ремонт  │
└──────────┴──────────────────────────┘
```

## Разработка

```bash
git clone https://github.com/dantih/d-itmo-sticker-gen
cd d-itmo-sticker-gen
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Зависимости

- Python ≥ 3.10
- PyPDF2
- qrcode[pil]
- Pillow
- reportlab

## Лицензия

MIT
