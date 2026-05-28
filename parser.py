import os
import re
import html
import datetime
import requests
import feedparser
from bs4 import BeautifulSoup

# Настройки
RSS_URL = "https://google.ru"
OUTPUT_DIR = "content/posts"
API_KEY = os.getenv("OPENROUTER_API_KEY")

def extract_real_url(alert_link):
    """Извлекает прямую ссылку на новость из редиректа Google."""
    if "url?q=" in alert_link:
        return alert_link.split("url?q=")[1].split("&")[0]
    return alert_link

def fetch_full_text(url):
    """Скачивает страницу и пытается забрать основной текст новости."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Удаляем мусор
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
            
        paragraphs = soup.find_all("p")
        text = " ".join([p.get_text() for p in paragraphs])
        return re.sub(r'\s+', ' ', text).strip()[:4000] # Ограничим 4к символов
    except:
        return ""

def ai_rewrite(text):
    """Бесплатно переписывает новость через OpenRouter API."""
    if not API_KEY or not text:
        return text, "Без рерайта"
        
    url = "https://openrouter.ai"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = (
        "Ты профессиональный новостной журналист. Перепиши следующий текст своими словами на русском языке. "
        "Сделай его уникальным, кликабельным и интересным. Напиши сначала новый Заголовок, а затем Текст новости. "
        "Формат ответа строго такой:\nЗАГОЛОВОК: [новый заголовок]\nТЕКСТ: [текст новости]\n\n"
        f"Вот исходный текст:\n{text}"
    )
    
    data = {
        "model": "meta-llama/llama-3-8b-instruct:free", # Используем стабильный бесплатный вариант
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        res = requests.post(url, headers=headers, json=data, timeout=30)
        res_json = res.json()
        ai_reply = res_json['choices'][0]['message']['content']
        
        # Парсим ответ ИИ
        title_match = re.search(r"ЗАГОЛОВОК:\s*(.*?)\n", ai_reply)
        text_match = re.search(r"ТЕКСТ:\s*(.*)", ai_reply, re.DOTALL)
        
        new_title = title_match.group(1).strip() if title_match else "Новое событие в индустрии"
        new_text = text_match.group(1).strip() if text_match else ai_reply
        
        return new_text, new_title
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return text, "Ошибка генерации"

def slugify(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9а-яё\s-]', '', title)
    title = re.sub(r'[\s-]+', '-', title)
    return title.strip('-')[:50]

def parse_and_generate():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print("Сканируем ленту Google Alerts...")
    feed = feedparser.parse(RSS_URL)

    for entry in feed.entries:
        source_link = extract_real_url(entry.link)
        clean_title = html.unescape(BeautifulSoup(entry.title, "html.parser").get_text())
        
        # Проверяем уникальность по заголовку
        file_name = f"{slugify(clean_title)}.md"
        file_path = os.path.join(OUTPUT_DIR, file_name)
        if os.path.exists(file_path):
            continue

        print(f"Обрабатываем: {clean_title}")
        
        # Собираем полный текст из источника, если не вышло — берем кусок из RSS
        full_text = fetch_full_text(source_link)
        if len(full_text) < 200:
            full_text = BeautifulSoup(entry.summary, "html.parser").get_text()

        # Рерайт
        rewritten_text, ai_title = ai_rewrite(full_text)
        if ai_title == "Ошибка генерации" or ai_title == "Без рерайта":
            ai_title = clean_title

        date_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+03:00")

        hugo_post = f"""---
title: "{ai_title.replace('"', '\\"')}"
date: {date_str}
draft: false
summary: "{rewritten_text[:150].replace('"', '\\"')}..."
---

{rewritten_text}

---
*Основано на материалах: [{clean_title}]({source_link})*
"""

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(hugo_post)
        
        print(f"Успешно добавлен уникальный пост: {ai_title}")

if __name__ == "__main__":
    parse_and_generate()
