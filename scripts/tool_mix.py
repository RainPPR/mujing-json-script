import sys
import json
import time
import io
import os
import shutil
import hashlib
import subprocess
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                               QCheckBox, QRadioButton, QButtonGroup, 
                               QDoubleSpinBox, QFileDialog, QProgressBar, 
                               QMessageBox, QGroupBox, QTextEdit, QSpinBox, 
                               QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QUrl, QPropertyAnimation
from PySide6.QtGui import QIcon, QColor, QDesktopServices, QDragEnterEvent, QDropEvent, QFont, QPalette, QTextCursor

# 音频处理库
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

# --- 全局配置 ---
CACHE_DIR = Path("cache")
CACHE_EXPIRY = 30 * 24 * 3600
TEMP_DIR = Path("temp_chunks")

# --- 强制亮色主题样式表 (Force Light Theme QSS) ---
PREMIUM_STYLESHEET = """
/* 全局设定 */
QWidget {
    color: #1E293B; /* Slate-800 */
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
}

/* 主窗口背景 */
QMainWindow {
    background-color: #F8FAFC; /* Slate-50 */
}

/* 卡片容器 */
QFrame#CardFrame {
    background-color: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F0; /* Slate-200 */
}

/* 标题 */
QLabel#HeaderTitle {
    font-size: 20px;
    font-weight: 800;
    color: #0F172A; /* Slate-900 */
}

/* 分组框 */
QGroupBox {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: 24px;
    font-weight: bold;
    color: #334155;
    background-color: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    background-color: #FFFFFF; /* 遮挡边框 */
}

/* 输入控件 (强制白底黑字，解决暗色模式Bug) */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #3B82F6;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #3B82F6; /* Blue-500 */
    padding: 5px 9px; /* 调整padding防止抖动 */
}
QLineEdit:read-only {
    background-color: #F1F5F9; /* Slate-100 */
    color: #64748B;
}

/* 按钮 */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    color: #475569;
}
QPushButton:hover {
    background-color: #F8FAFC;
    border-color: #94A3B8;
    color: #0F172A;
}
QPushButton:pressed {
    background-color: #E2E8F0;
}
QPushButton:disabled {
    background-color: #F1F5F9;
    color: #CBD5E1;
    border-color: #E2E8F0;
}

/* 主操作按钮 (蓝色) */
QPushButton#PrimaryBtn {
    background-color: #3B82F6;
    border: 1px solid #2563EB;
    color: #FFFFFF;
}
QPushButton#PrimaryBtn:hover {
    background-color: #2563EB;
}
QPushButton#PrimaryBtn:pressed {
    background-color: #1D4ED8;
}

/* 危险按钮 (红色) */
QPushButton#DangerBtn {
    background-color: #EF4444;
    border: 1px solid #DC2626;
    color: #FFFFFF;
}
QPushButton#DangerBtn:hover {
    background-color: #DC2626;
}

/* 进度条 */
QProgressBar {
    background-color: #E2E8F0;
    border-radius: 6px;
    height: 10px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #60A5FA);
    border-radius: 6px;
}

/* 拖拽区域 */
QLabel#DropArea {
    border: 2px dashed #CBD5E1;
    border-radius: 12px;
    background-color: #F8FAFC;
    color: #64748B;
    font-size: 15px;
    font-weight: 600;
}
QLabel#DropArea:hover {
    border-color: #3B82F6;
    background-color: #EFF6FF;
    color: #3B82F6;
}

/* 日志终端 (深色风格) */
QTextEdit#Console {
    background-color: #0F172A; /* Slate-900 */
    color: #E2E8F0;
    border: 1px solid #1E293B;
    border-radius: 8px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    padding: 5px;
}
QScrollBar:vertical {
    border: none;
    background: #0F172A;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}
"""

# --- 业务逻辑 ---

class AudioUtils:
    @staticmethod
    def trim_silence(audio: AudioSegment) -> AudioSegment:
        if len(audio) == 0: return audio
        ranges = detect_nonsilent(audio, min_silence_len=50, silence_thresh=-40)
        if ranges: return audio[ranges[0][0]:ranges[-1][1]]
        return audio

    @staticmethod
    def get_cache_path(word: str, type_code: int) -> Path:
        safe = "".join([c for c in word if c.isalnum() or c in ('-', '_')]).strip()
        if not safe: safe = hashlib.md5(word.encode()).hexdigest()
        return CACHE_DIR / f"{safe}_{type_code}.mp3"

    @staticmethod
    def fetch_task(word: str, type_code: int):
        if not CACHE_DIR.exists(): CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = AudioUtils.get_cache_path(word, type_code)
        
        # Cache Hit
        if path.exists():
            try:
                if time.time() - path.stat().st_mtime < CACHE_EXPIRY:
                    data = path.read_bytes()
                    if data: return 200, data, True
            except: pass

        # Network
        url = f"https://dict.youdao.com/dictvoice?audio={requests.utils.quote(word)}&type={type_code}"
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if r.status_code == 200 and r.content:
                try: path.write_bytes(r.content)
                except: pass
                return 200, r.content, False
            return r.status_code, None, False
        except:
            return -1, None, False

    @staticmethod
    def ffmpeg_merge(files, out_path):
        list_path = TEMP_DIR / "list.txt"
        with open(list_path, 'w', encoding='utf-8') as f:
            for p in files: f.write(f"file '{p.absolute().as_posix()}'\n")
        
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
               "-acodec", "libmp3lame", "-q:a", "2", str(out_path)]
        
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(cmd, startupinfo=si, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

class PipelineWorker(QThread):
    progress = Signal(int, int, str)
    log = Signal(str, str) 
    finished = Signal(bool, str)
    thread_adj = Signal(int)

    def __init__(self, json_path, out_path, cfg):
        super().__init__()
        self.json_path = json_path
        self.out_path = out_path
        self.cfg = cfg
        self._cancel = False

    def kill(self): self._cancel = True

    def run(self):
        if TEMP_DIR.exists(): shutil.rmtree(TEMP_DIR)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        executor = None
        chunks = []
        
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                words = json.load(f).get("wordList", [])
            
            if not words: raise Exception("JSON 文件中未找到单词列表")
            total = len(words)
            
            # Init Pipeline
            max_th = self.cfg['max_threads']
            curr_th = max_th
            last_change = time.time()
            
            executor = ThreadPoolExecutor(max_workers=32)
            futures = {} 
            processed = 0
            submitted = 0
            
            batch_audio = AudioSegment.empty()
            batch_count = 0
            
            self.log.emit("info", f"🚀 开始任务，共 {total} 个单词")
            
            while processed < total:
                if self._cancel: raise Exception("操作已取消")

                # Recovery
                if submitted < total and curr_th < max_th and (time.time() - last_change > 5):
                    new_th = min(int(curr_th * 1.5) + 1, max_th)
                    curr_th = new_th
                    last_change = time.time()
                    self.thread_adj.emit(curr_th)
                    self.log.emit("success", f"📈 网络稳定，线程恢复至 {curr_th}")

                # Submit
                while submitted < total and (submitted - processed < 50) and (submitted - processed < curr_th * 2):
                    if self._cancel: break
                    w_txt = words[submitted].get("value", "")
                    tasks = {}
                    if w_txt:
                        if self.cfg['uk']: tasks['uk'] = executor.submit(AudioUtils.fetch_task, w_txt, 1)
                        if self.cfg['us']: tasks['us'] = executor.submit(AudioUtils.fetch_task, w_txt, 2)
                        if not tasks: tasks['us'] = executor.submit(AudioUtils.fetch_task, w_txt, 2)
                    futures[submitted] = tasks
                    submitted += 1

                # Process
                current_task = futures.get(processed)
                if not current_task:
                    processed += 1; continue
                
                if not all(f.done() for f in current_task.values()):
                    time.sleep(0.02); continue

                w_txt = words[processed].get("value", "")
                segments = []
                keys = []
                if self.cfg['uk']: keys.append('uk')
                if self.cfg['us']: keys.append('us')
                if not keys: keys.append('us')

                for k in keys:
                    if k in current_task:
                        try:
                            code, data, cached = current_task[k].result()
                            if code == 200 and data:
                                seg = AudioSegment.from_mp3(io.BytesIO(data))
                                segments.append(AudioUtils.trim_silence(seg))
                            elif code == 429 and not cached:
                                self.log.emit("warning", f"⚠️ 429 限流: {w_txt} - 正在避让")
                                curr_th = max(1, curr_th // 2)
                                last_change = time.time()
                                self.thread_adj.emit(curr_th)
                        except: pass

                # Merge
                if segments:
                    for i, seg in enumerate(segments):
                        batch_audio += seg
                        is_last = (i == len(segments)-1) and (processed == total-1)
                        if not is_last:
                            ms = self.cfg['fix_val']*1000 if self.cfg['interval_mode']=='fixed' else len(seg)*self.cfg['rate_val']
                            batch_audio += AudioSegment.silent(duration=int(ms))
                
                del futures[processed]
                processed += 1
                batch_count += 1
                
                if processed % 5 == 0 or processed == total:
                    self.progress.emit(processed, total, f"处理中: {w_txt}")

                # Flush to Disk
                if len(batch_audio) > 60000 or batch_count >= 50:
                    fname = TEMP_DIR / f"part_{len(chunks):04d}.wav"
                    batch_audio.export(fname, format="wav")
                    chunks.append(fname)
                    batch_audio = AudioSegment.empty()
                    batch_count = 0
                    import gc; gc.collect()

            # Flush remaining
            if len(batch_audio) > 0:
                fname = TEMP_DIR / f"part_{len(chunks):04d}.wav"
                batch_audio.export(fname, format="wav")
                chunks.append(fname)

            executor.shutdown(wait=True)
            if self._cancel: raise Exception("用户取消")
            if not chunks: raise Exception("未生成有效音频")

            # Final Merge
            self.progress.emit(100, 100, "最终编码合并中...")
            self.log.emit("info", "🎬 正在调用 FFmpeg 进行高速合并...")
            
            try:
                subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                AudioUtils.ffmpeg_merge(chunks, self.out_path)
            except FileNotFoundError:
                self.log.emit("warning", "❌ 未检测到 FFmpeg，使用备用方案（较慢）...")
                full = AudioSegment.empty()
                for c in chunks: full += AudioSegment.from_wav(c)
                full.export(self.out_path, format="mp3")

            shutil.rmtree(TEMP_DIR)
            self.finished.emit(True, f"文件已保存至: {self.out_path}")

        except Exception as e:
            if executor: executor.shutdown(wait=False)
            if TEMP_DIR.exists(): shutil.rmtree(TEMP_DIR)
            self.finished.emit(False, str(e))

class NetworkThread(QThread):
    status = Signal(bool)
    def run(self):
        while True:
            try:
                requests.get("https://dict.youdao.com", timeout=3)
                self.status.emit(True)
            except: self.status.emit(False)
            time.sleep(10)

# --- UI 组件 ---

class FileDropArea(QLabel):
    fileDropped = Signal(str)
    clicked = Signal() # [修复] 新增点击信号
    
    def __init__(self):
        super().__init__("拖拽 JSON 文件到此处\n或点击选择")
        self.setObjectName("DropArea")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setCursor(Qt.PointingHandCursor)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): 
            self.setStyleSheet("border-color: #3B82F6; background-color: #EFF6FF; color: #3B82F6;")
            event.acceptProposedAction()
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("") # Revert to QSS default

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.json'):
                self.fileDropped.emit(path)
                break

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: 
            self.clicked.emit() # [修复] 发射信号，而不是调用 parent()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("单词音频合成工作室")
        self.resize(900, 700)
        self.force_light_theme()
        self.setup_ui()
        self.net_thread = NetworkThread()
        self.net_thread.status.connect(self.update_net_icon)
        self.net_thread.start()

    def force_light_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(248, 250, 252))
        palette.setColor(QPalette.WindowText, QColor(30, 41, 59))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(241, 245, 249))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(30, 41, 59))
        palette.setColor(QPalette.Text, QColor(30, 41, 59))
        palette.setColor(QPalette.Button, QColor(255, 255, 255))
        palette.setColor(QPalette.ButtonText, QColor(30, 41, 59))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(59, 130, 246))
        palette.setColor(QPalette.Highlight, QColor(59, 130, 246))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        QApplication.setPalette(palette)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 1. Header
        header = QHBoxLayout()
        title = QLabel("Audio Forge")
        title.setObjectName("HeaderTitle")
        self.net_badge = QLabel(" ● 连接中 ")
        self.net_badge.setStyleSheet("background: #E2E8F0; color: #64748B; border-radius: 12px; padding: 4px 10px; font-size: 12px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.net_badge)
        layout.addLayout(header)

        # 2. Content Cards
        content = QHBoxLayout()
        content.setSpacing(20)

        # Left Card
        left_card = QFrame()
        left_card.setObjectName("CardFrame")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20); shadow.setXOffset(0); shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 15))
        left_card.setGraphicsEffect(shadow)
        
        lc_layout = QVBoxLayout(left_card)
        lc_layout.setContentsMargins(20, 20, 20, 20)

        self.drop_area = FileDropArea()
        self.drop_area.fileDropped.connect(self.load_file)
        self.drop_area.clicked.connect(self.open_file_dialog) # [修复] 连接信号
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("未加载文件")
        self.path_edit.setReadOnly(True)
        
        log_title = QLabel("运行终端")
        log_title.setStyleSheet("font-weight: bold; margin-top: 10px; border: none;")
        
        self.console = QTextEdit()
        self.console.setObjectName("Console")
        self.console.setReadOnly(True)
        self.console.setHtml("<span style='color:#64748B'>等待任务开始...</span>")

        lc_layout.addWidget(self.drop_area)
        lc_layout.addWidget(self.path_edit)
        lc_layout.addWidget(log_title)
        lc_layout.addWidget(self.console)
        
        # Right Card
        right_card = QFrame()
        right_card.setObjectName("CardFrame")
        shadow2 = QGraphicsDropShadowEffect()
        shadow2.setBlurRadius(20); shadow2.setXOffset(0); shadow2.setYOffset(4)
        shadow2.setColor(QColor(0, 0, 0, 15))
        right_card.setGraphicsEffect(shadow2)

        rc_layout = QVBoxLayout(right_card)
        rc_layout.setContentsMargins(20, 20, 20, 20)
        
        grp_voice = QGroupBox("发音设置")
        v_layout = QVBoxLayout()
        self.chk_uk = QCheckBox("🇬🇧 英式发音 (UK)"); self.chk_uk.setChecked(True)
        self.chk_us = QCheckBox("🇺🇸 美式发音 (US)"); self.chk_us.setChecked(True)
        v_layout.addWidget(self.chk_uk); v_layout.addWidget(self.chk_us)
        grp_voice.setLayout(v_layout)

        grp_perf = QGroupBox("性能控制")
        p_layout = QVBoxLayout()
        row_th = QHBoxLayout()
        row_th.addWidget(QLabel("并发线程:"))
        self.spin_th = QSpinBox(); self.spin_th.setRange(1, 64); self.spin_th.setValue(16)
        row_th.addWidget(self.spin_th)
        p_layout.addLayout(row_th)
        self.lbl_th_status = QLabel("状态: 空闲")
        self.lbl_th_status.setStyleSheet("color: #64748B; font-size: 11px; border:none;")
        p_layout.addWidget(self.lbl_th_status)
        grp_perf.setLayout(p_layout)

        grp_int = QGroupBox("合成间隔")
        i_layout = QVBoxLayout()
        self.bg_int = QButtonGroup()
        r1 = QHBoxLayout()
        rb1 = QRadioButton("固定"); rb1.setChecked(True)
        self.v_fix = QDoubleSpinBox(); self.v_fix.setValue(0.5); self.v_fix.setSuffix(" s")
        r1.addWidget(rb1); r1.addWidget(self.v_fix)
        r2 = QHBoxLayout()
        rb2 = QRadioButton("倍率")
        self.v_rate = QDoubleSpinBox(); self.v_rate.setValue(0.6); self.v_rate.setSuffix(" x")
        r2.addWidget(rb2); r2.addWidget(self.v_rate)
        self.bg_int.addButton(rb1, 1); self.bg_int.addButton(rb2, 2)
        i_layout.addLayout(r1); i_layout.addLayout(r2)
        grp_int.setLayout(i_layout)

        rc_layout.addWidget(grp_voice)
        rc_layout.addWidget(grp_perf)
        rc_layout.addWidget(grp_int)
        rc_layout.addStretch()

        content.addWidget(left_card, 3)
        content.addWidget(right_card, 2)
        layout.addLayout(content)

        # 3. Actions
        bottom = QVBoxLayout()
        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setTextVisible(False)
        
        btns = QHBoxLayout()
        self.btn_path = QPushButton("更改保存路径")
        self.btn_path.clicked.connect(self.change_out)
        self.btn_open = QPushButton("打开文件夹")
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self.open_folder)
        self.btn_cancel = QPushButton("终止任务")
        self.btn_cancel.setObjectName("DangerBtn")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_task)
        self.btn_start = QPushButton("开始合成")
        self.btn_start.setObjectName("PrimaryBtn")
        self.btn_start.setMinimumWidth(120)
        self.btn_start.clicked.connect(self.start_task)
        
        btns.addWidget(self.btn_path)
        btns.addWidget(self.btn_open)
        btns.addStretch()
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_start)
        
        bottom.addWidget(self.pbar)
        bottom.addLayout(btns)
        layout.addLayout(bottom)

        self.json_path = ""
        self.out_path = ""

    def update_net_icon(self, ok):
        if ok:
            self.net_badge.setText("● 网络正常")
            self.net_badge.setStyleSheet("background: #DCFCE7; color: #166534; border-radius: 12px; padding: 4px 10px; font-weight: bold;")
        else:
            self.net_badge.setText("● 网络断开")
            self.net_badge.setStyleSheet("background: #FEE2E2; color: #991B1B; border-radius: 12px; padding: 4px 10px; font-weight: bold;")

    def open_file_dialog(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "JSON (*.json)")
        if f: self.load_file(f)

    def load_file(self, path):
        self.json_path = path
        self.path_edit.setText(Path(path).name)
        p = Path(path)
        self.out_path = str(p.parent / (p.stem + "_audio.mp3"))
        self.append_log("info", f"文件已加载: {p.name}")
        self.append_log("info", f"默认输出至: {Path(self.out_path).name}")

    def change_out(self):
        if not self.out_path: return
        f, _ = QFileDialog.getSaveFileName(self, "保存路径", self.out_path, "*.mp3")
        if f:
            self.out_path = f
            self.append_log("info", f"输出路径变更: {Path(f).name}")

    def open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.out_path).parent)))

    def append_log(self, type_, msg):
        colors = {"info": "#94A3B8", "success": "#4ADE80", "warning": "#FACC15", "error": "#F87171"}
        timestamp = time.strftime("%H:%M:%S")
        c = colors.get(type_, "#E2E8F0")
        html = f"<div style='margin-bottom:2px;'><span style='color:#555'>[{timestamp}]</span> <span style='color:{c}'>{msg}</span></div>"
        self.console.append(html)
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def start_task(self):
        if not self.json_path: return QMessageBox.warning(self, "提示", "请先选择 JSON 文件")
        
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.spin_th.setEnabled(False)
        self.drop_area.setEnabled(False)
        self.btn_open.setEnabled(False)
        self.console.clear()
        self.pbar.setValue(0)
        
        self.user_threads = self.spin_th.value()
        cfg = {
            'uk': self.chk_uk.isChecked(), 'us': self.chk_us.isChecked(),
            'max_threads': self.user_threads,
            'interval_mode': 'fixed' if self.bg_int.checkedId() == 1 else 'rate',
            'fix_val': self.v_fix.value(), 'rate_val': self.v_rate.value()
        }
        
        self.worker = PipelineWorker(self.json_path, self.out_path, cfg)
        self.worker.progress.connect(self.on_prog)
        self.worker.log.connect(self.append_log)
        self.worker.thread_adj.connect(self.on_th_adj)
        self.worker.finished.connect(self.on_done)
        self.worker.start()

    def cancel_task(self):
        if hasattr(self, 'worker'):
            self.worker.kill()
            self.btn_cancel.setText("停止中...")

    def on_prog(self, cur, tot, txt):
        if tot > 0:
            pct = int(cur/tot*100)
            self.pbar.setValue(pct)
            self.setWindowTitle(f"[{pct}%] {txt} - Audio Forge")
        else:
            self.setWindowTitle("Audio Forge")

    def on_th_adj(self, n):
        if n < self.user_threads:
            self.lbl_th_status.setText(f"🔥 流控生效: {n} 线程")
            self.lbl_th_status.setStyleSheet("color: #EF4444; font-weight: bold; border:none;")
        else:
            self.lbl_th_status.setText(f"✅ 全速运行: {n} 线程")
            self.lbl_th_status.setStyleSheet("color: #10B981; font-weight: bold; border:none;")

    def on_done(self, ok, msg):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setText("终止任务")
        self.spin_th.setEnabled(True)
        self.drop_area.setEnabled(True)
        self.setWindowTitle("单词音频合成工作室")
        
        if ok:
            self.append_log("success", "任务成功完成")
            self.btn_open.setEnabled(True)
            QMessageBox.information(self, "完成", msg)
        else:
            self.append_log("error", f"任务失败: {msg}")
            QMessageBox.critical(self, "错误", msg)

if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    app.setStyleSheet(PREMIUM_STYLESHEET)
    
    font = QFont("Segoe UI")
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())