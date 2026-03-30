# 立体几何 3D 讲解生成服务

输入一道立体几何题目（+ 可选答案），自动生成 Three.js 3D 交互式讲解课件。

## 架构

```
输入: 题目文本 + 答案(可选)
        │
        ▼
  ┌─────────────┐
  │ 题型检测     │  关键字匹配 → 线面平行/空间角度/空间距离/垂直关系
  └─────┬───────┘
        ▼
  ┌─────────────┐
  │ 教学数据加载  │  按题型加载对应的教学方法论 markdown
  └─────┬───────┘
        ▼
  ┌─────────────┐
  │ LLM 场景生成  │  qwen3.5-plus → 结构化 JSON (vertices, edges, solution_script)
  └─────┬───────┘
        ▼
  ┌─────────────┐
  │ HTML 组装    │  JSON 注入到 Three.js 模板 (template.html)
  └─────┬───────┘
        ▼
  ┌─────────────┐
  │ TTS 语音生成  │  CosyVoice WebSocket API → 每步骤 MP3
  └─────┬───────┘
        ▼
输出: 完整的单页 3D 交互讲解 HTML + 语音文件
```

## 快速开始

### 1. 环境准备

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env，填入你的 DashScope API Key
```

### 3. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 打开前端页面。

### Docker 部署

```bash
docker compose up -d
```

## API 接口

### POST /api/generate
提交生成任务。

**请求体：**
```json
{
  "problem": "四棱锥P-ABCD中，PA⊥底面ABCD...",
  "answer": "(1) 证明见解析 (2) AD=√3",
  "problem_type": "auto",
  "enable_tts": true
}
```

**响应：**
```json
{
  "lecture_id": "a1b2c3d4"
}
```

### GET /api/status/{lecture_id}
轮询任务状态。

**响应：**
```json
{
  "lecture_id": "a1b2c3d4",
  "status": "generating_scene",
  "progress": 30,
  "message": "AI 正在分析题目...",
  "url": null
}
```

status 取值：`queued` → `detecting` → `generating_scene` → `assembling` → `generating_tts` → `done` / `failed`

### GET /lectures/{lecture_id}/index.html
访问生成的 3D 讲解页面。

## 项目结构

```
geometry-lecture-service/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 环境变量配置
│   ├── models.py             # 请求/响应 schema
│   ├── api/
│   │   ├── router.py         # 路由汇总
│   │   ├── generate.py       # POST /api/generate
│   │   └── status.py         # GET /api/status/{id}
│   ├── pipeline/
│   │   ├── detector.py       # 题型检测
│   │   ├── teaching.py       # 教学数据加载
│   │   ├── llm.py            # 异步 LLM 客户端
│   │   ├── scene.py          # 场景数据生成 + JSON 提取
│   │   ├── assembler.py      # HTML 模板组装
│   │   ├── tts.py            # 异步 TTS 语音生成
│   │   └── task_runner.py    # 后台任务编排
│   └── static/
│       └── index.html        # 前端页面
├── data/
│   ├── template.html         # Three.js 3D 渲染模板
│   └── teaching_data/        # 教学方法论 (5 个 markdown)
├── lectures/                 # 生成的讲解文件 (运行时创建)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 技术栈

- **后端**: FastAPI + aiohttp + websockets
- **LLM**: DashScope (qwen3.5-plus)，兼容 OpenAI API 格式
- **TTS**: CosyVoice (cosyvoice-v3.5-plus)
- **前端渲染**: Three.js r160 + KaTeX + CSS2DRenderer
- **部署**: Docker / docker-compose
