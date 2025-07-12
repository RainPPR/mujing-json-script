import requests
import json
import shutil
import sys
import tech

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

def action(sub):
    path = f'./json/{sub}/config.json'
    config = load_json(path)
    print(f'Processing {config['name']}...')
    completed = config['completed']
    print(completed)
    for item in config['file']:
        if not item in completed:
            print(item)
            tech.action(f'./json/{sub}/{item}')
            completed.append(item)
    config['completed'] = completed
    write_json(path, config)

if __name__ == '__main__':
    data = load_json('./json/config.json')
    for item in data['file']:
        action(item)
