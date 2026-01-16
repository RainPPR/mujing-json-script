
import json
import sys
from pathlib import Path

def fix_json_size(json_path: str):
    """
    Updates the 'size' field in the JSON file to match the length of 'wordList'.
    """
    path = Path(json_path)
    if not path.exists():
        print(f"Error: File not found: {json_path}")
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    if 'wordList' not in data:
        print("Error: 'wordList' not found in JSON.")
        return

    actual_size = len(data['wordList'])
    old_size = data.get('size')

    if actual_size == old_size:
        print(f"Size is already correct ({actual_size}) for {json_path}")
        return

    data['size'] = actual_size

    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Successfully updated 'size' from {old_size} to {actual_size} in {json_path}")
    except Exception as e:
        print(f"Error writing JSON: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            fix_json_size(arg)
    else:
        print("Usage: python fix_json_size.py <path_to_json>")
