
import json
import csv
import sys
from pathlib import Path

def convert_json_to_csv(json_path: str):
    """
    Converts a JSON file containing a 'wordList' into a CSV file.
    The CSV will contain columns: value, usphone, ukphone, translation.
    Format: utf-8, no header, \n in translations preserved as newlines.
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

    word_list = data.get('wordList', [])
    if not word_list:
        print("Warning: No 'wordList' found in JSON.")
        return

    # Construct CSV path in the same directory
    csv_path = path.with_suffix('.csv')

    try:
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            # Use csv.writer for accurate CSV formatting
            # quotechar='"' and quoting=csv.QUOTE_MINIMAL is default and usually best
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            
            for word in word_list:
                # Extract fields in specified order: value, usphone, ukphone, translation
                # Replace \n with <br> as requested
                row = [
                    word.get('value', ''),#.replace('\n', '<br>'),
                    word.get('usphone', ''),#.replace('\n', '<br>'),
                    word.get('ukphone', ''),#.replace('\n', '<br>'),
                    word.get('translation', ''),#.replace('\n', '<br>')
                ]
                writer.writerow(row)
        
        print(f"Successfully converted {json_path} to {csv_path}")
    except Exception as e:
        print(f"Error writing CSV: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            convert_json_to_csv(arg)
    else:
        # Default example if no args provided, or just show usage
        print("Usage: python tool_json_to_csv.py <path_to_json>")
        # For testing purposes if you want to run it on the example provided:
        # convert_json_to_csv("data/困难词库/1.json")
