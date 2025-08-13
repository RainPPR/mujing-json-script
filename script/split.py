import requests
import json
import sys
import os
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox

# ========== 你需要实现的函数 ==========
def mysplit(data):
    """
    将输入 JSON 中的 wordList 按 20 个一组拆分。
    - 每一组生成一个新的对象，继承原对象的其他字段；
    - 修改 name 为 `原name-组序号`（从 1 开始），如 "Unit1-1"、"Unit1-2"；
    - 修改 size：
        * 前面各组固定为 20
        * 最后一组为该组 wordList 的实际长度
    - 返回由这些对象组成的列表。
    """
    if not isinstance(data, dict):
        raise ValueError("mysplit: 输入必须是一个 JSON 对象(dict)。")

    word_list = data.get("wordList")
    if not isinstance(word_list, list):
        raise ValueError("mysplit: 字段 wordList 必须是数组(list)。")

    base_name = data.get("name", "")
    chunk_size = 20
    result = []

    for start in range(0, len(word_list), chunk_size):
        chunk = word_list[start:start + chunk_size]
        idx = start // chunk_size + 1

        # 复制原对象并覆盖必要字段
        part = dict(data)  # 浅拷贝即可，下面会替换 wordList
        part["wordList"] = chunk
        part["size"] = len(chunk)  # 对前面各组会是 20，最后一组是剩余长度
        part["name"] = f"{base_name}-{idx}" if base_name else f"part-{idx}"

        result.append(part)

    return result


# ========== 工具函数 ==========
def compute_md5_for_json(obj):
    """
    对 JSON 对象进行稳定序列化（键排序、紧凑分隔符，不转义非 ASCII），然后计算 md5。
    """
    canonical = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    return hashlib.md5(canonical.encode('utf-8')).hexdigest()


def write_json_safe(file_path, data):
    """
    与上面的 write_json 类似，但不调用 sys.exit，便于在 GUI 中用 messagebox 报错。
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        raise IOError(f'写入文件失败: {file_path}, 错误: {e}') from e


def process_file(file_path):
    # 校验扩展名
    base, ext = os.path.splitext(file_path)
    if ext.lower() != '.json':
        messagebox.showerror('错误', '请选择 .json 文件。')
        return

    # 读取 JSON（使用不退出进程的方式）
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        messagebox.showerror('JSON 解析错误', f'文件: {file_path}\n错误: {e}')
        return
    except Exception as e:
        messagebox.showerror('读取失败', f'文件: {file_path}\n错误: {e}')
        return

    # 调用用户的 mysplit
    try:
        parts = mysplit(data)
    except NotImplementedError as e:
        messagebox.showwarning('未实现', str(e))
        return
    except Exception as e:
        messagebox.showerror('mysplit 出错', f'调用 mysplit 时发生错误:\n{e}')
        return

    if not isinstance(parts, (list, tuple)):
        messagebox.showerror('类型错误', 'mysplit 必须返回 list 或 tuple。')
        return

    if len(parts) == 0:
        messagebox.showinfo('提示', 'mysplit 返回了空列表，没有生成任何文件。')
        return

    generated_files = []
    for i, obj in enumerate(parts, start=1):
        # 序列化检查并计算 md5
        try:
            _ = json.dumps(obj)  # 序列化合法性检查
            md5sum = compute_md5_for_json(obj)
        except TypeError as e:
            messagebox.showerror('序列化失败', f'第 {i} 个元素无法 JSON 序列化:\n{e}')
            return
        except Exception as e:
            messagebox.showerror('错误', f'第 {i} 个元素处理 md5 时出错:\n{e}')
            return

        out_path = f'{base}-{i}-{md5sum}.part.json'
        try:
            write_json_safe(out_path, obj)
            generated_files.append(out_path)
        except Exception as e:
            messagebox.showerror('写入失败', f'写入文件时发生错误:\n{e}')
            return

    messagebox.showinfo('完成', f'已生成 {len(generated_files)} 个文件:\n' + '\n'.join(generated_files))


# ========== 简单 GUI ==========
def launch_gui():
    root = tk.Tk()
    root.title('JSON 拆分器')
    root.geometry('420x200')  # 简单窗口尺寸

    # 居中按钮
    btn = tk.Button(root, text='选择 JSON 文件并处理', width=28, height=2,
                    command=lambda: (
                        lambda p=filedialog.askopenfilename(
                            title='选择 JSON 文件',
                            filetypes=[('JSON 文件', '*.json'), ('所有文件', '*.*')]
                        ): process_file(p) if p else None
                    )())
    btn.place(relx=0.5, rely=0.5, anchor='center')

    root.mainloop()


if __name__ == '__main__':
    launch_gui()
