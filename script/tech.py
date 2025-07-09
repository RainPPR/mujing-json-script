import requests
import json
import shutil
import sys

def fetch_json(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f'Error fetching URL {url}: {e}')
        sys.exit(1)

def load_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except json.JSONDecodeError as e:
        print(f'Error decoding JSON from {file_path}: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'Error reading file {file_path}: {e}')
        sys.exit(1)

def write_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f'Error writing JSON to {file_path}: {e}')
        sys.exit(1)

def display_progress(file, current, total):
    bar_len = 50
    progress = current / total
    filled = int(bar_len * progress)
    bar = '#' * filled + '-' * (bar_len - filled)
    print(f'Progressing {file}: [{bar}] {current}/{total} ({progress*100:.2f}%)')

def action(file):
    data = load_json(file)
    progress_counter = 0
    total = len(data['wordList'])
    for item in data['wordList']:
        value = item['value']
        youdao = fetch_json(f'https://dict.youdao.com/jsonapi?q={value}&dicts=%7B%22count%22%3A99%2C%22dicts%22%3A%5B%5B%22syno%22%2C%22ec%22%5D%5D%7D')
        try:
            item['usphone'] = f'/{youdao["ec"]["word"][0]["usphone"]}/'
            item['ukphone'] = f'/{youdao["ec"]["word"][0]["ukphone"]}/'
            item['translation'] = '\n'.join(i['tr'][0]['l']['i'][0] for i in youdao['ec']['word'][0]['trs'])
            item['definition'] = item['pos'] = ''
        except (KeyError, IndexError, TypeError, ValueError):
            pass
        progress_counter += 1
        display_progress(file, progress_counter, total)
    # shutil.copy(file, f'{file}.bak')
    write_json(file, data)
    # print(f'\nUpdated {file} with phonetic information.')
    # print(f'Backup created as {file}.bak')
    # print('Done.')
