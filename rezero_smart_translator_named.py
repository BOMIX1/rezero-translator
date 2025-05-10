
# Re:Zero Smart Auto Translator
# وظيفته:
# - التحقق كل ساعة من الفصل الجديد، ترجمته مباشرة، وإضافته لـ index.html
# - ترجمة 5 فصول قديمة يوميًا
# - التمييز بين Main, Side Story, Extra
# - تحديد رقم الأرك + رقم الفصل داخل الأرك
# - توليد index.html بترتيب حسب تاريخ النشر

import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import os
from datetime import datetime
import time
import json

base_url = "https://ncode.syosetu.com/n2267be/"
index_file = "index.html"
translated_data_file = "translated_data.json"

languages = {

    "en": "English",
    "ar": "Arabic",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "ru": "Russian",
    "zh-cn": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "hi": "Hindi",
    "it": "Italian",
    "tr": "Turkish",
    "id": "Indonesian"
}

ARC_NUMBER = 9
ARC_START_ID = 697


language_names = {
    "en": "English", "ar": "Arabic", "fr": "French", "es": "Spanish", "de": "German",
    "ru": "Russian", "zh-cn": "Chinese", "ja": "Japanese", "ko": "Korean",
    "pt": "Portuguese", "hi": "Hindi", "it": "Italian", "tr": "Turkish", "id": "Indonesian"
}
  # Example: Chapter ID 697 = Arc 9, Chapter 1


def fetch_chapter_list():
    response = requests.get(base_url)
    if response.status_code != 200:
        print("Failed to fetch main page.")
        return []
    soup = BeautifulSoup(response.content, 'html.parser')
    chapters = []
    for a in soup.select('dl.novel_sublist2 a'):
        href = a.get('href')
        if href and href.startswith('/'):
            chapter_id = href.strip('/').split('/')[-1]
            full_url = f"https://ncode.syosetu.com{href}"
            title = a.find('span', class_='subtitle').text.strip()
            date_tag = a.find_next('dt')
            date_text = date_tag.text.strip() if date_tag else "Unknown"
            chapter_type = 'Main'
            arc = f"Arc {ARC_NUMBER}"
            chapter_num = "-"
            if chapter_id.lower().startswith('ss'):
                chapter_type = 'Side Story'
                arc = "-"
            elif chapter_id.lower().startswith('ex'):
                chapter_type = 'Extra'
                arc = "-"
            elif chapter_id.isdigit():
                chapter_num = int(chapter_id) - ARC_START_ID + 1
                chapter_num = f"Ch. {chapter_num}"
            chapters.append({
                'id': chapter_id,
                'url': full_url,
                'title': title,
                'date': date_text,
                'type': chapter_type,
                'arc': arc,
                'chapter_num': chapter_num
            })
    return chapters[::-1]  # الأحدث أولاً


def translate_and_save(chapter):
    try:
        response = requests.get(chapter['url'])
        if response.status_code != 200:
            print(f"Failed to fetch {chapter['id']}")
            return False

        soup = BeautifulSoup(response.content, 'html.parser')
        content = soup.find('div', id='novel_honbun').text.strip()
        translated_title = GoogleTranslator(source='ja', target='en').translate(chapter['title'])

        for lang_code, lang_name in languages.items():
            translated_content = GoogleTranslator(source='ja', target=lang_code).translate(content)
            html = f"""
<html>
<head><meta charset='utf-8'><title>{translated_title}</title></head>
<body>
<h1>{translated_title}</h1>
<p>{translated_content.replace('\n', '<br>')}</p>
</body>
</html>
"""
            filename = f"chapter_{chapter['id']}_{lang_code}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)

        # Save to JSON data
        record = {
            'id': chapter['id'],
            'title': translated_title,
            'arc': chapter['arc'],
            'chapter_num': chapter['chapter_num'],
            'type': chapter['type'],
            'date': chapter['date'],
            'languages': list(languages.keys())
        }

        all_data = []
        if os.path.exists(translated_data_file):
            with open(translated_data_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)

        if not any(c['id'] == chapter['id'] for c in all_data):
            all_data.append(record)
            all_data.sort(key=lambda x: x['date'], reverse=True)
            with open(translated_data_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        print(f"Error translating {chapter['id']}: {e}")
        return False

def generate_index_html():
    if not os.path.exists(translated_data_file):
        print("No data to build index.")
        return

    with open(translated_data_file, 'r', encoding='utf-8') as f:
        chapters = json.load(f)

    rows = ""
    for chap in chapters:
        row = f"<tr><td>{chap['id']}</td><td>{chap['title']}</td><td>{chap['arc']}</td><td>{chap['chapter_num']}</td><td>{chap['type']}</td><td>{chap['date']}</td><td>"
        for code in chap['languages']:
            row += f"<a href='chapter_{chap['id']}_{code}.html' class='btn btn-sm btn-outline-secondary m-1'>{code.upper()}</a>"
        row += "</td></tr>
"
        rows += row

    html = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Re:Zero - Translated Chapters</title>
<link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>
</head>
<body class='bg-light'>
<div class='container py-5'>
<h1 class='mb-3 text-center'>Re:Zero - Translated Chapters</h1>
<p class='text-center text-muted'>Automatically translated. All rights to Tappei Nagatsuki (長月達平).</p>
<div class='table-responsive'>
<table class='table table-striped'>
<thead class='table-dark'><tr><th>ID</th><th>Title</th><th>Arc</th><th>Chapter</th><th>Type</th><th>Date</th><th>Languages</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</div>
</div>
</body>
</html>
"""

    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(html)
