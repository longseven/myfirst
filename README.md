# 数学智能讲解生成服务

> AI 驱动的 K12 数学题目讲解生成平台 - 输入题目文本，自动生成 3D 交互/动画演示 + 语音讲解的多媒体教学课件

[![Tests](https://github.com/longseven/myfirst/actions/workflows/tests.yml/badge.svg)](https://github.com/longseven/myfirst/actions/workflows/tests.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 核心价值

| 特性 | 说明 |
|------|------|
| **自动化课件生成** | 输入题目文本，自动生成完整的多媒体讲解 |
| **多题型支持** | 立体几何、函数、导数、三角函数、数列、概率统计等 |
| **智能渲染路由** | 根据题目类型自动选择 3D 交互或动画演示 |
| **教学方法论驱动** | 基于结构化教学知识库生成符合教学规律的讲解 |

---

## 🏗️ 系统架构

```
┌─────────────────┐
│   用户提交题目    │
└────────┬────────┘
         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. 题型检测 (5%)  →  2. 教学数据加载 (10%)  →  3. 渲染器路由 (15%)  │
│     - 关键字匹配        - 学科/题型方法           - 立体几何→ThreeJS   │
│     - 特征 fallback     - 解题策略                - 函数/导数→Manim    │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. LLM 解题/作图 (15%→60%)  →  5. JSON 解析  →  6. 渲染输出 (85%)   │
│     - Claude Opus 4.6            - 多级修复         - HTML/MP4      │
│     - 教学数据注入               - 字段校验         - audio/*.mp3   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  7. TTS 语音生成 (95%)  →  8. 完成 (100%)                          │
│     - CosyVoice-v3.5-plus     - /lectures/{id}/index.html       │
│     - 步骤语音分段             - 状态追踪                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境准备

```bash
# Python 3.9+  required
pip install -r requirements.txt
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 API Key
```

**.env 配置示例：**
```ini
# DashScope API (通用模型)
DASHSCOPE_API_KEY=sk-your-api-key

# Claude Opus 4.6 (解题/作图专用)
PROBLEM_SOLVING_MODEL=claude-opus-4-6
PROBLEM_SOLVING_API_KEY=sk-cp-your-key
PROBLEM_SOLVING_API_URL=https://api.minimaxi.com/anthropic/v1/messages

# TTS 语音
TTS_ENABLED=true
TTS_API_KEYS=sk-tts-key1,sk-tts-key2
```

### 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 使用 Web 界面。

---

## 📡 API 接口

### POST /api/generate - 提交生成任务

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"problem": "已知函数 f(x) = x³ - 3x + 1，求单调区间和极值", "enable_tts": true}'
```

**响应：**
```json
{"lecture_id": "6413bac4"}
```

### GET /api/status/{lecture_id} - 查询任务状态

```bash
curl http://localhost:8000/api/status/6413bac4
```

**响应：**
```json
{
  "lecture_id": "6413bac4",
  "status": "done",
  "progress": 100,
  "message": "生成完成！",
  "url": "/lectures/6413bac4/index.html",
  "renderer": "manim"
}
```

### GET /api/tasks - 列出所有任务

```bash
curl http://localhost:8000/api/tasks
```

---

## 🎨 渲染器支持

| 渲染器 | 适用题型 | 输出形式 |
|--------|----------|----------|
| **ThreeJS** | 立体几何 | 3D 交互 HTML |
| **Manim** | 函数、导数、数列、三角函数 | 动画视频 + 步骤卡片 |
| **Video** | 综合题、压轴题 | 步骤卡片 + 视频匹配 |

---

## 📚 教学数据体系

```
data/teaching_data/
├── 立体几何/
│   ├── _通用.md
│   ├── 空间平行与垂直证明/
│   │   ├── _概述.md
│   │   ├── 中位线法.md
│   │   └── 坐标法.md
│   └── 空间向量求角度距离/
├── 函数/
├── 导数/
├── 三角函数/
├── 数列/
└── 排列组合概率统计/
```

每道题根据检测到的题型，自动注入对应的解题方法论到 LLM Prompt。

---

## 🧪 测试

```bash
# 运行全部测试（50 个用例）
python -m pytest tests/ -v

# 按模块测试
python -m pytest tests/test_detector.py -v   # 题型检测
python -m pytest tests/test_scene.py -v      # JSON 解析
python -m pytest tests/test_renderers.py -v  # 渲染器
python -m pytest tests/test_manim_handlers.py -v  # Manim 指令
python -m pytest tests/test_integration.py -v  # API 集成
```

---

## 📦 项目结构

```
geometry-lecture-service/
├── app/
│   ├── main.py                     # FastAPI 入口
│   ├── config.py                   # 配置管理
│   ├── models.py                   # 数据模型
│   ├── api/
│   │   ├── generate.py             # POST /api/generate
│   │   └── status.py               # GET /api/status
│   └── pipeline/
│       ├── detector.py             # 题型检测 (关键字 + 特征)
│       ├── teaching.py             # 教学数据加载
│       ├── llm.py                  # 多模型路由 (qwen/opus)
│       ├── scene.py                # JSON 提取与修复
│       ├── task_runner.py          # 任务编排 (LRU)
│       ├── tts.py                  # TTS 语音生成
│       ├── assembler.py            # HTML 组装
│       └── renderers/
│           ├── __init__.py         # 渲染器抽象基类
│           ├── threejs.py          # Three.js 渲染器
│           ├── manim_.py           # Manim 渲染器 (重构版)
│           ├── video.py            # Video 渲染器
│           └── manim_instructions/ # 指令处理器包
│               ├── __init__.py
│               └── handlers.py     # 13 种动画指令
├── data/
│   ├── template.html               # Three.js 模板
│   └── teaching_data/              # 教学方法论
├── tests/                          # 测试套件 (50 用例)
├── .github/workflows/tests.yml     # CI/CD 配置
├── DESIGN.md                       # 完整设计文档
├── requirements.txt
└── .env.example
```

---

## 🔬 技术亮点

### 1. 双模型策略
| 任务 | 模型 | 说明 |
|------|------|------|
| 题型检测 | qwen3.5-plus | 轻量任务，关键字匹配 |
| 解题/作图 | claude-opus-4-6 | 核心任务，强推理能力 |
| TTS 语音 | cosyvoice-v3.5-plus | 语音合成 |

### 2. 鲁棒的 JSON 解析
```python
# 多级修复策略处理 LLM 输出不稳定
1. 提取 markdown 代码块 → 2. 截取最外层{} → 3. 处理 Extra data
4. 修复尾随逗号 → 5. 修复 class='t' → 6. 修复非法转义
```

### 3. 策略模式渲染
- 13 种独立的动画指令处理器
- 每个处理器可单独测试和扩展
- 代码从 479 行优化到 230 行 (-52%)

### 4. LRU 任务管理
- 最大 100 任务，TTL 1 小时
- OrderedDict 维护访问顺序
- 自动清理过期任务

---

## 📊 性能指标

| 题目类型 | 平均时长 | 主要耗时 |
|----------|----------|----------|
| 立体几何 | 60-90s | LLM 生成 JSON |
| 函数/导数 | 30-50s | LLM + Manim 渲染 |
| 简单题目 | 20-30s | LLM 生成 |

---

## 📈 开发路线图

| 阶段 | 内容 |
|------|------|
| **短期** | 增加题型检测准确率、完善教学数据、OCR 识别 |
| **中期** | 支持 GeoGebra/Desmos、难度评估、批量生成 |
| **长期** | 自研渲染引擎、初中数学、多语言、SaaS 化 |

---

## 📄 文档

- **[DESIGN.md](DESIGN.md)** - 完整项目设计文档（系统架构、核心模块、Schema、部署配置）
- **README.md** - 本文件（快速开始指南）

---

## 🛠️ 技术栈

- **后端**: FastAPI + aiohttp + websockets
- **LLM**: DashScope (qwen3.5-plus) + MiniMax (Claude Opus 4.6)
- **TTS**: CosyVoice-v3.5-plus
- **前端**: Three.js r160 + KaTeX + Manim Community
- **部署**: Docker + GitHub Actions (CI/CD)
- **测试**: pytest + pytest-asyncio + httpx

---

## 📝 License

MIT License

---

## 📧 联系

GitHub: [@longseven](https://github.com/longseven)
