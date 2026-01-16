# Mujing JSON Script

[![Auto Vocabulary Update](https://github.com/RainPPR/mujing-json-script/actions/workflows/action.yml/badge.svg)](https://github.com/RainPPR/mujing-json-script/actions/workflows/action.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

一个用于批量处理和增强木境（Mujing）词汇 JSON 文件的自动化工具集。通过与有道词典 API 集成，自动为词汇添加音标、释义等详细信息，并提供多种实用工具脚本进行数据管理和音频合成。

## ✨ 功能特性

- **🔄 自动数据增强**：自动从有道词典 API 获取单词的音标（美式/英式）、释义等详细信息
- **⚡ 智能并发处理**：采用自适应线程池，根据网络状况和错误率动态调整并发数
- **🛡️ 可靠的错误处理**：内置重试机制和错误恢复，确保数据完整性
- **📊 进度跟踪**：实时显示处理进度，支持断点续传
- **🔧 多种辅助工具**：
  - GUI 工具：创建新词汇表
  - 拆分工具：将大词汇表按固定大小拆分
  - 合成工具：生成词汇音频文件
  - CSV 导出工具：将 JSON 词汇数据导出为 CSV 格式
  - 尺寸修复工具：自动修正 JSON 文件中的词汇数量字段
- **🤖 GitHub Actions 集成**：自动化处理和提交更新

## 📋 目录

- [功能概览](#-功能特性)
- [安装](#-安装)
- [快速开始](#-快速开始)
- [项目结构](#-项目结构)
- [使用方法](#-使用方法)
  - [主处理流程](#主处理流程)
  - [GUI 词汇生成器](#gui-词汇生成器)
  - [JSON 拆分工具](#json-拆分工具)
  - [音频合成工具](#音频合成工具)
  - [CSV 导出工具](#csv-导出工具)
  - [尺寸修复工具](#尺寸修复工具)
- [数据格式](#-数据格式)
- [工作原理](#-工作原理)
- [技术细节](#-技术细节)
- [GitHub Actions 自动化](#-github-actions-自动化)
- [常见问题](#-常见问题)
- [贡献](#-贡献)
- [许可证](#-许可证)
- [致谢](#-致谢)

## 🚀 安装

### 环境要求

- Python 3.12 或更高版本
- pip 包管理器

### 安装步骤

1. **克隆仓库**

   ```bash
   git clone https://github.com/RainPPR/mujing-json-script.git
   cd mujing-json-script
   ```

2. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

   主要依赖：
   - `requests`：用于 HTTP 请求（有道词典 API）

### 可选依赖

对于使用 GUI 工具和音频合成功能，需要额外安装：

- **GUI 词汇生成器**（`tool_gui.py`）：

  ```bash
  pip install PySide6
  ```

- **音频合成工具**（`tool_mix.py`）：

  ```bash
  pip install PySide6 pydub
  # 同时需要安装 ffmpeg（用于音频处理）
  ```

## 🎯 快速开始

### 1. 准备数据文件

在 `data/` 目录下创建或编辑配置文件 `config.json`：

```json
{
  "file": [
    "选择性必修一",
    "选择性必修二",
    "选择性必修三",
    "困难词库"
  ]
}
```

### 2. 运行主脚本

```bash
python scripts/main.py
```

脚本会自动处理 `config.json` 中列出的所有词汇分类。

## 📁 项目结构

```
mujing-json-script/
├── .github/
│   └── workflows/
│       └── action.yml          # GitHub Actions 自动化工作流
├── data/                        # 词汇数据存储目录
│   ├── config.json              # 主配置文件
│   ├── ecdict.db                # ECDICT 词典数据库（可选）
│   ├── 选择性必修一/            # 词汇分类示例
│   │   ├── config.json         # 分类配置
│   │   ├── Unit1.json          # 单元词汇文件
│   │   ├── Unit2.json
│   │   └── ...
│   ├── 选择性必修二/
│   ├── 选择性必修三/
│   ├── 困难词库/
│   │   ├── config.json
│   │   ├── 1.json              # 词汇数据文件
│   │   ├── 1.csv               # CSV 导出文件
│   │   └── ...
│   ├── BNC/                     # British National Corpus 词汇
│   └── COCA/                    # Corpus of Contemporary American English
├── scripts/                     # 脚本目录
│   ├── main.py                  # 主处理脚本
│   ├── tech.py                  # 核心技术实现（API 客户端、并发管理等）
│   ├── tool_gui.py              # GUI 词汇生成器
│   ├── tool_split.py            # JSON 拆分工具
│   ├── tool_mix.py              # 音频合成工具
│   ├── tool_json_to_csv.py      # JSON 到 CSV 转换工具
│   └── fix_json_size.py         # JSON 尺寸修复工具
├── requirements.txt             # Python 依赖
├── LICENSE                      # MIT 许可证
└── README.md                    # 项目文档
```

## 📖 使用方法

### 主处理流程

主处理脚本 `main.py` 会遍历配置文件中的所有分类，自动处理未完成的词汇文件。

**运行方式：**

```bash
python scripts/main.py
```

**处理逻辑：**

1. 读取 `data/config.json` 获取需要处理的分类列表
2. 对于每个分类，读取该分类的 `config.json`
3. 处理 `file` 列表中尚未在 `completed` 列表中的文件
4. 为每个词汇调用有道词典 API 获取详细信息
5. 更新 JSON 文件并标记为已完成

**示例输出：**

```
2026-01-15 13:57:28 - INFO - == Processing Category: 选择性必修一 ==
Unit1.json: |████████████████████████████████████████| 52/52 (100.0%)
2026-01-15 13:58:42 - INFO - Done: Unit1.json
```

### GUI 词汇生成器

图形界面工具，用于快速创建新的词汇 JSON 文件。

**运行方式：**

```bash
python scripts/tool_gui.py
```

**功能：**

- 输入词汇表名称
- 设置保存文件名和位置
- 批量输入单词/短语（支持多行）
- 自动从 ECDICT 和有道词典获取词汇信息
- 一键生成符合格式规范的 JSON 文件

**界面特点：**

- 现代化 UI 设计
- 实时进度显示
- 后台多线程处理

### JSON 拆分工具

将大型词汇 JSON 文件按指定大小（默认 20 个单词/组）拆分成多个小文件。

**运行方式：**

```bash
python scripts/tool_split.py
```

**功能：**

- 自动拆分 `wordList` 数组
- 为每个拆分文件生成唯一的 MD5 标识
- 保留原始文件的所有元数据
- 自动更新 `name` 和 `size` 字段

**输出格式：**

```
原文件名-序号-MD5哈希.part.json
```

例如：`Unit1-1-a1b2c3d4.part.json`

### 音频合成工具

为词汇表生成连续的英语发音音频文件。

**运行方式：**

```bash
python scripts/tool_mix.py
```

**功能：**

- 从有道词典下载单词发音（美式/英式）
- 智能音频缓存机制
- 自动去除静音部分
- 使用 FFmpeg 合成最终音频
- 支持拖拽导入 JSON 文件
- 实时显示网络状态和处理进度

**注意事项：**

- 需要安装 FFmpeg
- 首次处理会下载并缓存音频文件
- 缓存存储在 `cache/` 目录（已在 `.gitignore` 中忽略）

### CSV 导出工具

将 JSON 格式的词汇数据导出为 CSV 格式，便于在 Excel 等工具中查看和编辑。

**运行方式：**

```bash
python scripts/tool_json_to_csv.py
```

**功能：**

- 自动将 JSON 词汇数据转换为 CSV 格式
- 保留所有词汇字段（单词、音标、释义等）
- 换行符自动转换为 HTML `<br>` 标签，便于在表格中查看
- 与原 JSON 文件同名存储（`.csv` 扩展名）

**主要字段：**

- `value`：单词
- `usphone`：美式音标
- `ukphone`：英式音标
- `translation`：中文释义

### 尺寸修复工具

自动修复 JSON 文件中的 `size` 字段，确保其与实际单词列表数量一致。

**运行方式：**

```bash
python scripts/fix_json_size.py
```

**功能：**

- 扫描指定目录下的所有 JSON 文件
- 检查 `size` 字段是否与 `wordList` 数组长度匹配
- 自动修正不一致的数据
- 生成修复报告

## 📝 数据格式

### 词汇文件格式 (JSON)

```json
{
  "name": "Unit1",
  "type": "DOCUMENT",
  "language": "",
  "size": 52,
  "relateVideoPath": "",
  "subtitlesTrackId": 0,
  "wordList": [
    {
      "value": "mood",
      "usphone": "/muːd/",
      "ukphone": "/muːd/",
      "definition": "",
      "translation": "n. 心境，情绪；气氛...",
      "pos": "",
      "collins": 3,
      "oxford": true,
      "tag": "cet4 cet6 ky toefl ielts",
      "bnc": 2324,
      "frq": 2344,
      "exchange": "s:moods",
      "externalCaptions": [],
      "captions": []
    }
  ]
}
```

**字段说明：**

- `name`: 词汇表名称
- `type`: 文档类型（固定为 `"DOCUMENT"`）
- `size`: 词汇数量
- `wordList`: 词汇列表数组
  - `value`: 单词
  - `usphone`/`ukphone`: 美式/英式音标
  - `translation`: 中文释义
  - `collins`/`oxford`: 柯林斯/牛津词典等级
  - `tag`: 考试标签（如 cet4, cet6, toefl 等）
  - `bnc`/`frq`: BNC 和 COCA 词频
  - `exchange`: 词形变化

### 配置文件格式

**主配置** (`data/config.json`)：

```json
{
  "file": [
    "选择性必修一",
    "选择性必修二"
  ]
}
```

**分类配置** (例如 `data/选择性必修一/config.json`)：

```json
{
  "name": "选择性必修一",
  "file": [
    "Unit1.json",
    "Unit2.json"
  ],
  "completed": [
    "Unit1.json"
  ]
}
```

## ⚙️ 工作原理

### 核心处理流程

1. **配置解析**：读取主配置和分类配置文件
2. **任务调度**：识别需要处理的词汇文件
3. **并发处理**：使用线程池并发处理多个单词
4. **API 调用**：调用有道词典 API 获取单词详细信息
5. **数据更新**：将获取的信息写入 JSON 文件
6. **状态持久化**：更新 `completed` 列表，支持断点续传

### 自适应并发管理

项目实现了智能的并发控制机制（`ConcurrencyManager` 类）：

- **初始并发数**：8 个线程
- **动态调整**：
  - 检测到错误（如 429 Too Many Requests）：并发数减半
  - 连续 10 次成功：并发数逐步恢复
- **错误处理**：
  - 单次请求最多重试 3 次
  - 支持指数退避（Exponential Backoff）
  - 持续失败会触发程序退出

### API 集成

使用有道词典的非官方 API：

- **端点**：`https://dict.youdao.com/jsonapi`
- **参数**：
  - `q`：查询单词
  - `dicts`：指定返回的词典数据
- **返回数据**：音标、释义、词形变化等

## 🔬 技术细节

### 核心模块

**`tech.py` - 核心技术实现**

- `ConcurrencyManager`：自适应并发管理器
  - 动态调整线程数
  - 错误率监控
  - 自动恢复机制
  
- `YoudaoClient`：有道词典 API 客户端
  - HTTP 请求封装
  - 重试逻辑
  - 响应解析
  
- 工具函数：
  - `load_json()` / `write_json()`：JSON 文件读写
  - `display_progress()`：进度条显示
  - `process_word()`：单词处理逻辑
  - `action()`：文件级处理入口

**`main.py` - 主入口程序**

- `process_subdirectory()`：处理单个词汇分类
- `main()`：程序主入口，遍历所有分类

### 并发策略

项目使用 Python 的 `concurrent.futures.ThreadPoolExecutor` 实现并发：

```python
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(process_word, client, item): item 
               for item in word_list}
    
    for future in as_completed(futures):
        # 处理结果
        pass
```

### 错误恢复机制

1. **API 速率限制检测**：识别 429/403 状态码
2. **指数退避**：失败后延迟时间翻倍（2^attempt 秒）
3. **并发数降级**：错误时并发数减半
4. **自动恢复**：连续成功后逐步提升并发数

## 🤖 GitHub Actions 自动化

项目配置了 GitHub Actions 工作流，可以自动处理词汇更新。

### 触发条件

- Push 到 `main` 或 `master` 分支
- Pull Request 到 `main` 或 `master` 分支
- 手动触发（`workflow_dispatch`）

### 工作流步骤

1. **Checkout Repository**：检出代码
2. **Setup Python 3.12 Environment**：配置 Python 环境
3. **Install Python Dependencies**：安装依赖（使用 pip 缓存加速）
4. **Run Vocabulary Update Script**：运行 `scripts/main.py`
5. **Commit and Push Updated Vocabulary**：自动提交和推送更新的 JSON 文件

### 文件监控

工作流会忽略以下文件的变更：

- `.gitignore`
- `.gitattributes`
- `README.md`
- `LICENSE`

## ❓ 常见问题

### Q1: 如何添加新的词汇分类？

1. 在 `data/` 目录下创建新文件夹，例如 `必修一/`
2. 在新文件夹中创建 `config.json`：

   ```json
   {
     "name": "必修一",
     "file": ["Unit1.json"],
     "completed": []
   }
   ```

3. 创建词汇文件 `Unit1.json`（可使用 GUI 工具）
4. 更新 `data/config.json`，添加新分类名称

### Q2: 处理时遇到 429 错误怎么办？

这是有道词典的速率限制。程序会自动：

- 降低并发数
- 增加重试延迟
- 在连续成功后逐步恢复

如果频繁出现，可考虑：

- 减小初始并发数（修改 `tech.py` 中的 `initial_limit`）
- 增加请求间隔

### Q3: 音频合成失败？

确保已安装 FFmpeg：

- **Windows**：下载并添加到 PATH
- **macOS**：`brew install ffmpeg`
- **Linux**：`sudo apt-get install ffmpeg`

### Q4: 如何备份数据？

重要文件都在 `data/` 目录下，定期备份该目录即可。建议使用 Git 进行版本控制。

### Q5: CSV 文件中的换行符显示为 `<br>` 怎么办？

这是为了在表格软件中正确显示多行内容而设计的。如果需要纯文本换行，可以在 Excel 等软件中使用"查找替换"功能将 `<br>` 替换为换行符。

### Q6: 如何查看单个词汇表的详细信息？

可以使用 CSV 导出工具将 JSON 文件转换为 CSV 格式，然后在 Excel 或其他表格软件中查看：

```bash
python scripts/tool_json_to_csv.py
```

## 🤝 贡献

本项目主要由个人维护，**欢迎纠错和建议**，但由于精力有限，暂不接受大型功能请求。

如果您发现任何问题（如拼写错误、bug、数据错误等），欢迎：

- 提交 Issue 报告问题
- 创建 Pull Request（针对明确的错误修正）

### 贡献指南

**✅ 欢迎的贡献类型：**

- Bug 修复
- 文档改进和错别字修正
- 性能优化
- 数据准确性纠错

**❌ 暂不接受：**

- 大型新功能请求（除非经过事先讨论并获得同意）
- 重大架构改动

### 提交 Pull Request 前请确保：

1. 代码风格与现有代码保持一致
2. 测试过您的更改
3. 在 PR 描述中清楚说明更改内容和原因

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

```
MIT License

Copyright (c) 2025 RainPPR

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🙏 致谢

- **有道词典**：提供词汇数据 API
- **ECDICT**：提供离线词典数据库
- **BNC** 和 **COCA**：提供语料库词频数据
- **Python 社区**：提供优秀的开源库和工具

---

## 📌 附注

> **本 README 文件由人工智能 (Antigravity, powered by Google Gemini 2.0 Flash Thinking Experimental) 生成，并经人工审核。**  
> 生成时间：2026-01-16  
> 
> 如发现文档中的任何错误或不准确之处，欢迎提 Issue 或 PR 进行修正。
