import os
import re
import datetime
import feedparser
from bs4 import BeautifulSoup

# URL вашей ленты Google Alerts
RSS_URL = "https://www.google.ru/alerts/feeds/07900584025514455075/18417236125185111965"
# Папка, куда Hugo сохраняет посты (обычно content/posts)
OUTPUT_DIR = "content/posts"

def clean_text(html_content):
    """Очищает текст от HTML-тегов Google Alerts и лишних ссылок."""
    soup = BeautifulSoup(html_content, "html.parser")
    # Удаляем трекинговые ссылки Google, оставляя чистый текст
    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def slugify(title):
    """Создает безопасное имя файла из заголовка."""
    title = title.lower()
    # Оставляем только латиницу, кириллицу и цифры
    title = re.sub(r'[^a-z0-9а-яё\s-]', '', title)
    title = re.sub(r'[\s-]+', '-', title)
    return title.strip('-')[:50]

def parse_and_generate():
    # Создаем папку для постов, если её нет
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print("Получаем новости из Google Alerts...")
    feed = feedparser.parse(RSS_URL)

    if not feed.entries:
        print("Новых новостей не найдено.")
        return

    for entry in feed.entries:
        title = entry.title
        # Извлекаем чистую дату публикации
        date_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+03:00")
        
        # Очищаем контент новости
        raw_content = entry.summary if 'summary' in entry else entry.description
        clean_content = clean_text(raw_content)
        
        # Оригинальная ссылка на источник (полезно для Google бота, показывает цитирование)
        source_link = entry.link
        if "url?q=" in source_link:
            # Очищаем ссылку от редиректа Google
            source_link = source_link.split("url?q=")[1].split("&")[0]

        # Формируем имя файла
        file_name = f"{slugify(title)}.md"
        file_path = os.path.join(OUTPUT_DIR, file_name)

        # Проверяем, не скачивали ли мы эту новость ранее
        if os.path.exists(file_path):
            continue

        # Шаблон разметки (Front Matter) для Hugo, который обожает Google
        hugo_post = f"""---
title: "{title.replace('"', '\\"')}"
date: {date_str}
draft: false
summary: "{clean_content[:150]}..."
---

{clean_content}

---
*По материалам первоисточника: [{title}]({source_link})*
"""

        # Сохраняем новость на диск
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(hugo_post)
        
        print(f"Добавлена новость: {title}")

if __name__ == "__main__":
    parse_and_generate()
