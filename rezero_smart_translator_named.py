import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import os
import json

# Configuration
base_url = "https://ncode.syosetu.com/n2267be/"
index_file = "index.html"
translated_data_file = "translated_data.json"
# Load custom HTML template from external file 'index.html' (must include a `{rows}` placeholder)
template_path = 'index.html'
if os.path.exists(template_path):
    with open(template_path, 'r', encoding='utf-8') as tf:
        html_template = tf.read()
else:
    # Fallback minimal template
    html_template = (
        "<html><head><meta charset='utf-8'><title>Chapters Index</title>"
        "<link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css\" rel=\"stylesheet\">"
        "</head><body><div class=\"container\">"
        "<h1>All Translated Chapters</h1>"
        "<table class=\"table\"><thead><tr>"
        "<th>ID</th><th>Title</th><th>Arc</th><th>Number</th><th>Type</th><th>Date</th><th>Actions</th>"
        "</tr></thead><tbody>{rows}</tbody></table>"
        "</div><script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/js/bootstrap.bundle.min.js\"></script>"
        "</body></html>"
    )

languages = {
    "en": "English", "ar": "Arabic", "fr": "French", "es": "Spanish",
    "de": "German", "ru": "Russian", "zh-cn": "Chinese", "ja": "Japanese",
    "ko": "Korean", "pt": "Portuguese", "hi": "Hindi", "it": "Italian",
    "tr": "Turkish", "id": "Indonesian"
}

ARC_NUMBER = 9
ARC_START_ID = 697

def fetch_chapter_list():
    response = requests.get(base_url)
    if response.status_code != 200:
        print("Failed to fetch main page.")
        return []
    soup = BeautifulSoup(response.content, 'html.parser')
    chapters = []
    for a in soup.select('dl.novel_sublist2 a'):
        href = a.get('href')
        chapter_id = href.strip('/').split('/')[-1]
        full_url = f"https://ncode.syosetu.com{href}"
        title = a.find('span', class_='subtitle').text.strip()
        dt = a.find_previous('dt')
        date_text = dt.text.strip() if dt else "Unknown"
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
            chapter_num = f"Ch. {int(chapter_id) - ARC_START_ID + 1}"
        chapters.append({
            'id': chapter_id,
            'url': full_url,
            'title': title,
            'date': date_text,
            'type': chapter_type,
            'arc': arc,
            'chapter_num': chapter_num
        })
    return chapters[::-1]

def get_adjacent_chapter(current_id, id_list, direction='next'):
    if current_id not in id_list:
        return None
    idx = id_list.index(current_id)
    if direction == 'next' and idx < len(id_list) - 1:
        return id_list[idx + 1]
    elif direction == 'prev' and idx > 0:
        return id_list[idx - 1]
    return None

def translate_and_save(chapter, all_ids):
    try:
        response = requests.get(chapter['url'])
        if response.status_code != 200:
            print(f"Failed to fetch chapter {chapter['id']}.")
            return False
        soup = BeautifulSoup(response.content, 'html.parser')
        content = soup.find('div', id='novel_honbun').get_text(separator='\n').strip()
        translated_title = GoogleTranslator(source='ja', target='en').translate(chapter['title'])

        for lang_code in languages:
            translated_content = GoogleTranslator(source='ja', target=lang_code).translate(content)
            html_content = translated_content.replace('\n', '<br>')

            prev_id = get_adjacent_chapter(chapter['id'], all_ids, direction='prev')
            next_id = get_adjacent_chapter(chapter['id'], all_ids, direction='next')

            nav_html = "<div class='d-flex justify-content-between mt-5'>"
            if prev_id:
                nav_html += f"<a href='chapter_{prev_id}_{lang_code}.html' class='btn btn-outline-secondary'>← Previous</a>"
            else:
                nav_html += "<div></div>"
            nav_html += "<a href='index.html' class='btn btn-outline-primary'>All Chapters</a>"
            if next_id:
                nav_html += f"<a href='chapter_{next_id}_{lang_code}.html' class='btn btn-outline-secondary'>Next →</a>"
            else:
                nav_html += "<div></div>"
            nav_html += "</div>"

            html = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                f"<title>{translated_title}</title>"
                '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">'
                "</head><body><div class='container'>"
                f"<h1>{translated_title}</h1>"
                f"<p>{html_content}</p>"
                f"{nav_html}"
                "</div><script src='https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/js/bootstrap.bundle.min.js'></script>"
                "</body></html>"
            )

            filename = f"chapter_{chapter['id']}_{lang_code}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)

        # Save metadata
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
        lang_modal_id = f"modal_{chap['id']}"
        modal_btn = (
            f"<button class='btn btn-sm btn-outline-primary' data-bs-toggle='modal' data-bs-target='#{lang_modal_id}'>"
            "View Languages</button>"
            f"<div class='modal fade' id='{lang_modal_id}' tabindex='-1'>"
            # Modal content
            "<ul class='list-group list-group-flush'>"
            + ''.join([f"<li class='list-group-item'><a href='chapter_{chap['id']}_{code}.html'>{languages[code]}</a></li>" for code in chap['languages']])
            + "</ul></div>"
        )
        rows += (
            f"<tr><td>{chap['id']}</td>"
            f"<td><a href='chapter_{chap['id']}_en.html'>{chap['title']}</a></td>"
            f"<td>{chap['arc']}</td>"
            f"<td>{chap['chapter_num']}</td>"
            f"<td>{chap['type']}</td>"
            f"<td>{chap['date']}</td>"
            f"<td>{modal_btn}</td></tr>\n"
        )

    content = html_template.format(rows=rows)
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(content)

def run():
    chapters = fetch_chapter_list()
    if not chapters:
        return
    all_ids = [c['id'] for c in chapters]
    latest = next((c for c in chapters if c['id'] == '726'), None)

    all_data = []
    if os.path.exists(translated_data_file):
        with open(translated_data_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)

    if not any(c['id'] == latest['id'] for c in all_data):
        print(f"Translating newest chapter: {latest['id']} — {latest['title']}")
        if translate_and_save(latest, all_ids):
            generate_index_html()
        else:
            print("Translation failed.")

if __name__ == "__main__":
    run()
