

import sys
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QProgressBar,
    QMessageBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QThread, Signal, Property, QSize, QPoint
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QBrush, QPen

# Import tech module from the same directory
try:
    import tech
except ImportError:
    # If running from root, maybe need this
    sys.path.append(str(Path(__file__).parent))
    import tech

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Modern Style Constants ---
BACKGROUND_COLOR = "#202020"
SURFACE_COLOR = "#2D2D2D"
ACCENT_COLOR = "#7F5AF0" # A nice purple
TEXT_COLOR = "#FFFFFE"
SECONDARY_TEXT_COLOR = "#94A1B2"
INPUT_BG_COLOR = "#16161a"
BORDER_RADIUS = 10

STYLESHEET = f"""
QMainWindow {{
    background-color: {BACKGROUND_COLOR};
}}
QWidget {{
    background-color: {BACKGROUND_COLOR};
    color: {TEXT_COLOR};
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
}}
QLabel {{
    color: {SECONDARY_TEXT_COLOR};
    background-color: transparent;
    font-weight: bold;
    margin-bottom: 5px;
}}
QLineEdit {{
    background-color: {INPUT_BG_COLOR};
    border: 1px solid #444;
    border-radius: {BORDER_RADIUS}px;
    padding: 10px;
    color: {TEXT_COLOR};
    selection-background-color: {ACCENT_COLOR};
}}
QLineEdit:focus {{
    border: 2px solid {ACCENT_COLOR};
}}
QTextEdit {{
    background-color: {INPUT_BG_COLOR};
    border: 1px solid #444;
    border-radius: {BORDER_RADIUS}px;
    padding: 10px;
    color: {TEXT_COLOR};
}}
QTextEdit:focus {{
    border: 2px solid {ACCENT_COLOR};
}}
QPushButton {{
    background-color: {ACCENT_COLOR};
    color: white;
    border: none;
    border-radius: {BORDER_RADIUS}px;
    padding: 12px 24px;
    font-weight: bold;
    font-size: 15px;
}}
QPushButton:hover {{
    background-color: #6a4bd8;
}}
QPushButton:pressed {{
    background-color: #583db8;
}}
QPushButton:disabled {{
    background-color: #444;
    color: #888;
}}
QProgressBar {{
    background-color: {INPUT_BG_COLOR};
    border-radius: {BORDER_RADIUS}px;
    text-align: center;
    color: white;
}}
QProgressBar::chunk {{
    background-color: {ACCENT_COLOR};
    border-radius: {BORDER_RADIUS}px;
}}
"""

BASE_DIR = Path(__file__).resolve().parent.parent

class Worker(QThread):
    progress = Signal(int, int, str) # current, total, status message
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, vocabulary: List[str], unit_name: str, save_name: str, save_location: str):
        super().__init__()
        self.vocabulary = vocabulary
        self.unit_name = unit_name
        self.save_name = save_name
        self.save_location = save_location
        self.running = True

    def run(self):
        try:
            total_words = len(self.vocabulary)
            processed_data = []

            # DB Connection
            db_path = BASE_DIR / "data/ecdict.db"
            if not db_path.exists():
                self.error.emit(f"Database not found at {db_path}")
                return

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Initialize Youdao Client
            manager = tech.ConcurrencyManager(initial_limit=4)
            client = tech.YoudaoClient(manager)

            for idx, word_str in enumerate(self.vocabulary):
                if not self.running:
                    break
                
                word_str = word_str.strip()
                if not word_str:
                    continue

                self.progress.emit(idx + 1, total_words, f"Processing: {word_str}")

                # 1. Fetch from ECDICT
                cursor.execute("SELECT * FROM ecdict WHERE word = ?", (word_str,))
                row = cursor.fetchone()
                
                # Default empty item
                item = {
                    "value": word_str,
                    "usphone": "",
                    "ukphone": "",
                    "definition": "",
                    "translation": "",
                    "pos": "",
                    "collins": 0,
                    "oxford": False,
                    "tag": "",
                    "bnc": 0,
                    "frq": 0,
                    "exchange": "",
                    "externalCaptions": [],
                    "captions": []
                }

                if row:
                    # Mapping based on DB schema
                    # word, british_phonetic, american_phonetic, definition, translation, pos, collins, oxford, tag, bnc, frq, exchange
                    if row[2]: item["usphone"] = f"/{row[2]}/"
                    if row[1]: item["ukphone"] = f"/{row[1]}/"
                    if row[3]: item["definition"] = row[3]
                    if row[4]: item["translation"] = row[4]
                    if row[5]: item["pos"] = row[5]
                    
                    try:
                        item["collins"] = int(row[6]) if row[6] else 0
                    except: pass
                    
                    try:
                        item["oxford"] = bool(int(row[7])) if row[7] else False
                    except: pass
                    
                    if row[8]: item["tag"] = row[8]
                    try:
                        item["bnc"] = int(row[9]) if row[9] else 0
                    except: pass
                    try:
                        item["frq"] = int(row[10]) if row[10] else 0
                    except: pass
                    if row[11]: item["exchange"] = row[11]

                # 2. Add Info from Youdao
                try:
                    yg_info = client.fetch_word_info(word_str)
                    if yg_info:
                        ec_data = yg_info.get("ec", {}).get("word", [{}])[0]
                        # Prioritize Youdao phonetics if missing
                        if "usphone" in ec_data and not item["usphone"]:
                            item["usphone"] = f"/{ec_data['usphone']}/"
                        if "ukphone" in ec_data and not item["ukphone"]:
                            item["ukphone"] = f"/{ec_data['ukphone']}/"
                        
                        trs = ec_data.get("trs", [])
                        translations = []
                        for tr in trs:
                            l_data = tr.get("tr", [{}])[0].get("l", {}).get("i", [])
                            if l_data:
                                translations.append(l_data[0])
                        
                        if translations:
                             if not item["translation"]:
                                 item["translation"] = "\n".join(translations)
                except SystemExit:
                    self.error.emit(f"Youdao API fatal error for {word_str}")
                    return
                except Exception as e:
                    pass # Ignore recoverable API errors

                processed_data.append(item)
            
            conn.close()

            # Construct Final JSON
            final_json = {
                "name": self.unit_name,
                "type": "DOCUMENT",
                "language": "",
                "size": len(processed_data),
                "relateVideoPath": "",
                "subtitlesTrackId": 0,
                "wordList": processed_data
            }

            # Save File
            base_path = BASE_DIR / "data" / self.save_location
            try:
                base_path.mkdir(parents=True, exist_ok=True)
                full_path = base_path / self.save_name
                if not self.save_name.endswith(".json"):
                    full_path = full_path.with_suffix(".json")

                with open(full_path, "w", encoding="utf-8") as f:
                    json.dump(final_json, f, ensure_ascii=False, indent=4)
            
                self.finished.emit(str(full_path))
            except Exception as e:
                self.error.emit(f"Failed to save file: {e}")

        except Exception as e:
            logger.exception("Error in worker")
            self.error.emit(str(e))

    def stop(self):
        self.running = False


class ModernInput(QWidget):
    def __init__(self, label_text, placeholder="", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(label_text)
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        
        layout.addWidget(self.label)
        layout.addWidget(self.input)

    def text(self):
        return self.input.text()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Vocabulary Generator")
        self.resize(500, 700)
        
        # Apply Global Stylesheet
        QApplication.instance().setStyleSheet(STYLESHEET)

        # Main Widget
        central_widget = QWidget()
        central_widget.setObjectName("central")
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        title = QLabel("Create Vocabulary Unit")
        title.setStyleSheet(f"font-size: 24px; color: {TEXT_COLOR}; border: none;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Inputs
        self.unit_name_input = ModernInput("Dictionary Name (e.g., Unit1)", "Unit1")
        layout.addWidget(self.unit_name_input)
        
        self.file_name_input = ModernInput("Save Filename (e.g., Unit1.json)", "Unit1.json")
        layout.addWidget(self.file_name_input)
        
        self.location_input = ModernInput("Save Location (Subdirectory)", "选择性必修四")
        layout.addWidget(self.location_input)

        # Word List
        word_label = QLabel("Word List (One per line)")
        layout.addWidget(word_label)
        
        self.word_input = QTextEdit()
        self.word_input.setPlaceholderText("Enter words here...\napple\nbanana\norange")
        layout.addWidget(self.word_input)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Action Button
        self.generate_btn = QPushButton("Generate JSON")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self.start_generation)
        
        # Add shadow to button
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.generate_btn.setGraphicsEffect(shadow)
        
        layout.addWidget(self.generate_btn)
        
        # Status Label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #03DAC6; font-size: 12px; font-weight: normal;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def start_generation(self):
        unit_name = self.unit_name_input.text().strip()
        save_name = self.file_name_input.text().strip()
        location = self.location_input.text().strip()
        raw_words = self.word_input.toPlainText().strip()

        if not all([unit_name, save_name, location, raw_words]):
            QMessageBox.warning(self, "Missing Info", "Please fill in all fields.")
            return

        vocab_list = [line.strip() for line in raw_words.split('\n') if line.strip()]

        self.generate_btn.setEnabled(False)
        self.word_input.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing...")

        self.worker = Worker(vocab_list, unit_name, save_name, location)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.generation_finished)
        self.worker.error.connect(self.generation_error)
        self.worker.start()

    def update_progress(self, current, total, msg):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(msg)

    def generation_finished(self, saved_path):
        self.status_label.setText("Completed!")
        QMessageBox.information(self, "Success", f"File created successfully at:\n{saved_path}")
        self.reset_ui()

    def generation_error(self, error_msg):
        self.status_label.setText("Error occurred.")
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_msg}")
        self.reset_ui()

    def reset_ui(self):
        self.generate_btn.setEnabled(True)
        self.word_input.setEnabled(True)
        self.progress_bar.setVisible(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

