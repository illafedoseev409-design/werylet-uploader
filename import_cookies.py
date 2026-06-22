"""
import_cookies.py — импортирует куки в профили Octo по номеру в имени файла

Структура:
  - Куки файлы: ALM01.json, TGDR092.json, ZER005.json и т.д.
  - Профили в Octo называются так же или похоже: ALM001, TGDR092 и т.д.
  - Совпадение идёт по ПОСЛЕДНИМ ЦИФРАМ в имени файла и профиля

Использование:
  python import_cookies.py                    # все файлы из папки cookies/
  python import_cookies.py --dir C:/куки      # из другой папки
  python import_cookies.py --file ALM01.json  # один файл
  python import_cookies.py --dry              # тест без импорта
"""

import os
import sys
import json
import re
import time
import argparse
import requests

# =====================
# НАСТРОЙКИ
# =====================

OCTO_API_URL  = "https://app.octobrowser.net/api/v2/automation"
OCTO_TOKEN    = "2765eb1aedde4725af7e3a8ed3272959"  # твой токен

COOKIES_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies")
NAMES_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles_names.json")

HEADERS = {
    "Content-Type": "application/json",
    "X-Octo-Api-Token": OCTO_TOKEN,
}

# =====================
# HELPERS
# =====================

def get_number(name):
    """Извлекает последние цифры из имени файла/профиля"""
    m = re.search(r'(\d+)$', os.path.splitext(name)[0])
    return m.group(1).lstrip('0') or '0' if m else None

def load_profiles():
    """Загружает profiles_names.json → {uuid: name}"""
    if not os.path.exists(NAMES_FILE):
        print(f"❌ {NAMES_FILE} не найден")
        sys.exit(1)
    with open(NAMES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_cookies(filepath):
    """Загружает куки из файла"""
    with open(filepath, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    # Фильтруем невалидные куки
    valid = []
    for c in cookies:
        if c.get("name") and c.get("domain"):
            valid.append(c)
    return valid

def import_cookies(uuid, cookies, dry=False):
    """Импортирует куки в профиль через Octo API"""
    if dry:
        return True
    url = f"{OCTO_API_URL}/profiles/{uuid}/import_cookies"
    r = requests.post(url, headers=HEADERS, json={"cookies": cookies}, timeout=30)
    r.raise_for_status()
    return True

# =====================
# MAIN
# =====================

def process_file(filepath, profiles_by_num, dry=False):
    filename = os.path.basename(filepath)
    num = get_number(filename)
    if not num:
        print(f"⚠ {filename} — не удалось извлечь номер, пропускаем")
        return False

    # Ищем профиль с таким же номером
    matches = profiles_by_num.get(num, [])
    if not matches:
        print(f"⚠ {filename} (#{num}) — профиль не найден")
        return False

    if len(matches) > 1:
        print(f"⚠ {filename} (#{num}) — найдено {len(matches)} профилей: {[m[1] for m in matches]}")
        print(f"   Используем первый: {matches[0][1]}")

    uuid, profile_name = matches[0]

    try:
        cookies = load_cookies(filepath)
        print(f"📦 {filename} → {profile_name} ({len(cookies)} куки)", end="")

        if dry:
            print(" [DRY RUN]")
            return True

        import_cookies(uuid, cookies)
        print(" ✅")
        return True

    except Exception as e:
        print(f" ❌ {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Импорт куки в Octo профили")
    parser.add_argument("--dir",  default=COOKIES_DIR, help="Папка с куки файлами")
    parser.add_argument("--file", default=None,        help="Один конкретный файл")
    parser.add_argument("--dry",  action="store_true", help="Тест без реального импорта")
    args = parser.parse_args()

    if args.dry:
        print("🔍 DRY RUN — реального импорта не будет\n")

    # Загружаем профили и строим индекс по номеру
    print("📋 Загружаем профили...")
    profiles = load_profiles()  # {uuid: name}
    profiles_by_num = {}  # num → [(uuid, name)]
    for uuid, name in profiles.items():
        num = get_number(name)
        if num:
            if num not in profiles_by_num:
                profiles_by_num[num] = []
            profiles_by_num[num].append((uuid, name))
    print(f"   Загружено {len(profiles)} профилей, {len(profiles_by_num)} уникальных номеров\n")

    # Список файлов для обработки
    if args.file:
        files = [args.file if os.path.isabs(args.file)
                 else os.path.join(args.dir, args.file)]
    else:
        if not os.path.exists(args.dir):
            print(f"❌ Папка не найдена: {args.dir}")
            print(f"   Создай папку 'cookies' и положи туда файлы .json")
            sys.exit(1)
        files = [
            os.path.join(args.dir, f)
            for f in sorted(os.listdir(args.dir))
            if f.lower().endswith(".json")
        ]

    if not files:
        print(f"❌ Нет .json файлов в {args.dir}")
        sys.exit(1)

    print(f"📁 Найдено файлов: {len(files)}\n")

    ok = 0
    fail = 0
    for filepath in files:
        result = process_file(filepath, profiles_by_num, dry=args.dry)
        if result:
            ok += 1
        else:
            fail += 1
        time.sleep(0.3)  # небольшая пауза чтобы не спамить API

    print(f"\n✅ Успешно: {ok}  ❌ Ошибок: {fail}")

if __name__ == "__main__":
    main()
