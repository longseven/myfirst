# 数学智能讲解生成服务 - 项目设计文档

## 1. 项目概述

### 1.1 项目定位

一个基于 AI 的 K12 数学智能讲解生成服务，能够根据输入的数学题目自动生成包含 3D 交互/动画演示、语音讲解的多媒体教学课件。

### 1.2 核心价值

- **自动化课件生成**：输入题目文本，自动生成完整的多媒体讲解
- **多题型支持**：立体几何、函数、导数、三角函数、数列、概率统计等
- **智能渲染路由**：根据题目类型自动选择 3D 交互或动画演示
- **教学方法论驱动**：基于结构化教学知识库生成符合教学规律的讲解

### 1.3 目标用户

- 高中数学教师：快速生成教学课件
- 学生：获取直观的题目讲解
- 教育机构：批量生产教学内容

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Client Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Web 前端     │  │  移动端 H5    │  │  API 调用方    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           API Gateway                                │
│                     FastAPI Application                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  HTTP 请求日志中间件  │  全局异常处理器  │  CORS 中间件            │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API Router Layer                             │
│  ┌─────────────────────┐    ┌─────────────────────┐                 │
│  │  /api/generate      │    │  /api/status/{id}   │                 │
│  │  (提交生成任务)      │    │  (查询任务状态)      │                 │
│  └─────────────────────┘    └─────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Pipeline Layer                                │
│                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │
│  │ 题型检测 │ → │ 教学数据 │ → │ 渲染器   │ → │ LLM 调用  │          │
│  │Detector │    │Teaching │    │ Routing │    │ 解题    │          │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘          │
│       │                                          │                   │
│       ▼                                          ▼                   │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │
│  │ 学科识别 │    │ 方法匹配 │    │ ThreeJS │    │  Manim  │          │
│  │         │    │         │    │ 立体几何 │    │ 函数等  │          │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘          │
│                                                                      │
│                                    │                                 │
│                                    ▼                                 │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                          │
│  │  JSON   │    │  HTML   │    │  TTS    │                          │
│  │  解析   │    │  组装   │    │  语音   │                          │
│  └─────────┘    └─────────┘    └─────────┘                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Output Layer                                  │
│  ┌───────────────────┐  ┌───────────────────┐  ┌────────────────┐  │
│  │  lectures/{id}/   │  │  lectures/{id}/   │  │  lectures/{id}/│  │
│  │   index.html      │  │   audio/*.mp3     │  │   *_data.json  │  │
│  │   (交互课件)       │  │   (语音讲解)       │  │   (中间数据)    │  │
│  └───────────────────┘  └───────────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心流程

```
用户提交题目
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 题型检测 (5%)                                       │
│ - 关键字匹配 + LLM 分类                                      │
│ - 输出：[(学科，[题型，方法]), ...]                          │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 加载教学数据 (10%)                                  │
│ - 根据学科/题型加载对应的教学方法论 markdown                  │
│ - 输出：教学指导文本                                         │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 渲染器路由 (15%)                                    │
│ - 立体几何 → ThreeJSRenderer (3D 交互)                       │
│ - 函数/导数/数列等 → ManimRenderer (动画视频)                │
│ - 其他 → VideoRenderer (步骤演示)                            │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: LLM 解题/作图 (15% → 60%)                            │
│ - 使用 Claude Opus 4.6 (MiniMax API)                        │
│ - 输入：题目 + 教学数据 + 系统提示词                          │
│ - 输出：结构化 JSON (scene_data / manim_data)               │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: JSON 解析与验证 (60%)                               │
│ - 多级 JSON 修复策略 (处理 LLM 输出不稳定)                     │
│ - 必要字段校验                                               │
│ - 输出：dict                                                │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 6: 渲染输出 (65% → 85%)                                │
│ - ThreeJS: JSON 注入 HTML 模板 → 交互式 3D 页面                 │
│ - Manim: 生成 Python 脚本 → 渲染 MP4 → HTML 播放器            │
│ - Video: 步骤卡片 HTML                                       │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 7: TTS 语音生成 (85% → 95%)                            │
│ - 使用 CosyVoice-v3.5-plus                                │
│ - 每个教学步骤生成一段 MP3                                   │
│ - 输出：audio/*.mp3                                         │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 8: 完成 (100%)                                         │
│ - 输出：/lectures/{lecture_id}/index.html                   │
│ - 状态更新：status="done"                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块设计

### 3.1 配置管理 (`app/config.py`)

```python
class Settings(BaseSettings):
    # LLM - 通用模型（题型检测等）
    dashscope_api_key: str
    dashscope_api_url: str
    llm_model: str = "qwen3.5-plus"

    # LLM - 解题/作图专用模型 (Claude Opus 4.6)
    problem_solving_model: str = "claude-opus-4-6"
    problem_solving_api_key: str
    problem_solving_api_url: str

    # TTS 配置
    tts_enabled: bool = True
    tts_api_keys: str
    tts_voice: str
    tts_model: str = "cosyvoice-v3.5-plus"

    # 路径配置
    lectures_dir: str = "./lectures"
    teaching_data_dir: str = "./data/teaching_data"

    # 限制配置
    max_concurrent: int = 3
    request_timeout: int = 300
    max_retries: int = 3
```

### 3.2 多模型路由 (`app/pipeline/llm.py`)

```python
class ModelPurpose(Enum):
    GENERAL = "general"              # 通用任务
    PROBLEM_SOLVING = "problem_solving"  # 解题/作图

def _get_config_for_purpose(purpose: ModelPurpose) -> tuple[str, str, str]:
    """根据用途返回 (model, api_key, api_url)"""
    if purpose == ModelPurpose.PROBLEM_SOLVING:
        return (settings.problem_solving_model,
                settings.problem_solving_key,
                settings.problem_solving_api_url)
    else:
        return (settings.llm_model,
                settings.dashscope_api_key,
                settings.dashscope_api_url)

async def call_llm(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 16000,
    purpose: ModelPurpose = ModelPurpose.GENERAL,
) -> str:
    """调用 LLM API，支持 OpenAI 和 Anthropic 格式"""
```

**模型分配策略：**

| 任务类型 | 使用模型 | API 提供方 | 说明 |
|----------|----------|------------|------|
| 题型检测 | qwen3.5-plus | DashScope | 轻量任务 |
| 解题/作图 | claude-opus-4-6 | MiniMax | 核心任务，强推理 |
| TTS 语音 | cosyvoice-v3.5-plus | DashScope | 语音合成 |

### 3.3 渲染器抽象 (`app/pipeline/renderers/__init__.py`)

```python
class RendererBase(abc.ABC):
    """渲染器抽象基类"""

    name: str = "base"

    @abc.abstractmethod
    def get_prompt_schema(self) -> str:
        """返回 LLM prompt schema"""

    @abc.abstractmethod
    def get_system_prompt(self, teaching_data: str) -> str:
        """返回系统提示词"""

    @abc.abstractmethod
    async def parse_llm_output(self, raw: str) -> dict:
        """解析 LLM 输出为结构化数据"""

    @abc.abstractmethod
    async def render(self, data: dict, output_dir: str) -> str:
        """渲染为最终输出，返回 index.html 路径"""
```

### 3.4 渲染器路由表

```python
# 学科 → 渲染器映射
_registry = {
    # 立体几何 → Three.js 3D 交互
    "立体几何": ThreeJSRenderer,

    # 计算/分析类 → Manim 动画
    "解三角形": ManimRenderer,
    "三角函数": ManimRenderer,
    "函数": ManimRenderer,
    "导数": ManimRenderer,
    "数列": ManimRenderer,
    "排列组合概率统计": ManimRenderer,
    "集合与不等式": ManimRenderer,
    "解析几何": ManimRenderer,
    "复数": ManimRenderer,
    "平面向量": ManimRenderer,

    # 默认回退
    "_default": ThreeJSRenderer,
}
```

---

## 4. JSON 输出 Schema

### 4.1 Three.js Schema (立体几何)

```json
{
  "title": "题目简短标题",
  "problem_html": "题目 HTML（含几何元素标注）",
  "questions": [{"label": "(1)", "html": "..."}],
  "vertices": {"A": [x, y, z], ...},
  "vertex_styles": {"A": {"label": "A", "position": "above"}},
  "base_edges_solid": [["A", "B"], ...],
  "base_edges_dashed": [["A", "C"], ...],
  "base_edges_special": [{"from": "P", "to": "A", "color": "0xff4444"}],
  "base_face_vertices": ["A", "B", "C", "D"],
  "right_angles": [{"vertex": "A", "dir1_toward": "B", "dir2_toward": "P"}],
  "lines": [{"id": "ln_PA", "from": "P", "to": "A"}],
  "planes": [{"id": "pl_PBC", "vertices": ["P", "B", "C"]}],
  "coord_system": {"origin": "A", "axes": [...]},
  "vectors": [{"id": "vec_AD", "from": "A", "to": "D"}],
  "normals": [{"id": "nrm_ACP", "center_vertices": ["A", "C", "P"]}],
  "shapes": [{"type": "frustum", ...}],
  "solution_script": [
    {
      "phase": "审题",
      "speech": "这一步的讲解...",
      "els": ["ln_PA", "pl_PBC"],
      "cam": {"position": [5, 4, 5], "target": [0, 0, 0]}
    }
  ]
}
```

### 4.2 Manim Schema (函数/导数等)

```json
{
  "title": "题目简短标题",
  "problem_tex": "题目 LaTeX 表示",
  "scenes": [
    {
      "scene_id": 1,
      "title": "步骤标题",
      "speech": "口语化讲解 (30-80 字)",
      "instructions": [
        {"type": "write_tex", "tex": "f(x) = x^2", "color": "white"},
        {"type": "transform_tex", "from_tex": "...", "to_tex": "..."},
        {"type": "draw_axes", "x_range": [-3, 3, 1], "y_range": [-5, 5, 1]},
        {"type": "plot_function", "expr": "x**2 - 3*x + 1", "color": "blue"},
        {"type": "mark_point", "x": 1, "y": -1, "label": "极小值", "color": "red"},
        {"type": "highlight_interval", "x_from": -1, "x_to": 1},
        {"type": "draw_table", "headers": [...], "rows": [...]},
        {"type": "draw_triangle", "vertices": [[0,0], [3,0], [1.5, 2.6]]},
        {"type": "draw_number_line", "range": [-5, 5], "marks": [...]},
        {"type": "draw_tree", "root": "开始", "branches": [...]}
      ]
    }
  ],
  "summary": {
    "key_formula": "$核心公式$",
    "method_name": "方法名称",
    "tips": ["注意点 1", "注意点 2"]
  }
}
```

---

## 5. 关键技术实现

### 5.1 鲁棒的 JSON 提取 (`app/pipeline/scene.py`)

```python
def _extract_json(text: str) -> dict:
    """多级 JSON 修复策略"""

    # Step 1: 从 markdown 代码块提取
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    candidate = m.group(1).strip() if m else text.strip()

    # Step 2: 找到最外层 braces
    first = candidate.find("{")
    last = candidate.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidate = candidate[first : last + 1]

    # Step 3: 处理 "Extra data" 错误
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        if "Extra data" in str(e):
            # 提取第一个完整 JSON 对象
            depth = 0
            for i, ch in enumerate(candidate):
                if ch == "{": depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = candidate[:i+1]
                        break

    # Step 4: 修复常见错误
    # - class='t' 语法
    # - 尾随逗号
    # - 无效转义
    # - 控制字符

    # Step 5: 激进清理
    # ...
```

### 5.2 LRU 任务管理 (`app/pipeline/task_runner.py`)

```python
_tasks: OrderedDict[str, dict] = OrderedDict()
_MAX_TASKS = 100
_TASK_TTL = 3600  # 1 小时

def _evict_old_tasks():
    """清理过期任务和超出数量的任务"""
    now = time.time()
    # 清理过期
    expired = [tid for tid, t in _tasks.items()
               if now - t.get("created_at", now) > _TASK_TTL]
    for tid in expired:
        del _tasks[tid]
    # 清理最旧
    while len(_tasks) > _MAX_TASKS:
        oldest_id = next(iter(_tasks))
        del _tasks[oldest_id]
```

### 5.3 TTS 语音生成 (`app/pipeline/tts.py`)

```python
async def generate_all(tts_data: dict, audio_dir: str) -> int:
    """批量生成所有语音片段"""
    from ..config import settings

    script = tts_data.get("solution_script", [])
    keys = settings.tts_keys  # 轮询使用

    count = 0
    for i, step in enumerate(script):
        speech = step.get("speech", "")
        if not speech:
            continue

        api_key = keys[count % len(keys)]
        output_path = os.path.join(audio_dir, f"{i:03d}.mp3")

        await generate_single(speech, output_path, api_key)
        count += 1

    return count
```

---

## 6. API 接口设计

### 6.1 POST /api/generate

**提交生成任务**

```json
// 请求
{
  "problem": "已知函数 f(x) = x³ - 3x + 1，求单调区间和极值",
  "answer": "(1) 递增：(-∞,-1)∪(1,+∞); 递减：(-1,1); 极大值 3; 极小值 -1",
  "problem_type": "auto",  // 或具体类型："function", "derivative"等
  "enable_tts": true
}

// 响应
{
  "lecture_id": "6413bac4"
}
```

### 6.2 GET /api/status/{lecture_id}

**查询任务状态**

```json
// 响应
{
  "lecture_id": "6413bac4",
  "status": "done",          // queued | detecting | generating | rendering | generating_tts | done | failed
  "progress": 100,           // 0-100
  "message": "生成完成！",
  "url": "/lectures/6413bac4/index.html",
  "renderer": "manim",       // 使用的渲染器
  "created_at": 1774849752.53,
  "updated_at": 1774849807.55
}
```

### 6.3 GET /api/tasks

**列出所有任务**（最近优先）

```json
[
  {
    "lecture_id": "6413bac4",
    "status": "done",
    "progress": 100,
    "renderer": "manim"
  },
  ...
]
```

---

## 7. 教学数据体系

### 7.1 目录结构

```
data/teaching_data/
├── 立体几何/
│   ├── _通用.md
│   ├── 线面平行/
│   │   ├── _概述.md
│   │   ├── 中位线法.md
│   │   └── 平行四边形法.md
│   ├── 空间角度/
│   └── ...
├── 函数/
│   ├── _通用.md
│   ├── 求定义域值域/
│   ├── 判断单调性奇偶性/
│   └── ...
├── 导数/
│   ├── _通用.md
│   ├── 求单调区间/
│   ├── 恒成立问题/
│   └── ...
└── ...
```

### 7.2 文件格式

```markdown
# 方法名称

## 适用场景
描述该方法适用的题目类型

## 解题步骤
1. 第一步...
2. 第二步...

## 典型案例
示例题目和解答

## 注意事项
- 注意点 1
- 注意点 2
```

---

## 8. 前端技术栈

### 8.1 Three.js 渲染器 (立体几何)

- **Three.js r160**: 3D 场景渲染
- **CSS2DRenderer**: HTML 标签标注
- **OrbitControls**: 相机控制
- **KaTeX**: 公式渲染

**核心功能：**
- 顶点/棱/面的高亮和显示控制
- 3D 相机动画
- 向量/法线可视化
- 直角符号标注
- 可交互旋转/缩放

### 8.2 Manim HTML 播放器 (函数/导数等)

- **KaTeX**: 公式渲染
- **步骤卡片**: 分步展示讲解
- **公式高亮**: 自动提取并展示

---

## 9. 部署配置

### 9.1 环境变量

```ini
# .env
DASHSCOPE_API_KEY=sk-your-api-key
REQUEST_TIMEOUT=600

# 解题/作图专用模型 (Claude Opus 4.6 via MiniMax)
PROBLEM_SOLVING_MODEL=claude-opus-4-6
PROBLEM_SOLVING_API_KEY=sk-cp-your-key
PROBLEM_SOLVING_API_URL=https://api.minimaxi.com/anthropic/v1/messages

# TTS 配置
TTS_ENABLED=true
TTS_API_KEYS=sk-key1,sk-key2,sk-key3
TTS_VOICE=cosyvoice-v3.5-plus-teacher-xxx
TTS_MODEL=cosyvoice-v3.5-plus
```

### 9.2 启动命令

```bash
# 开发环境
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产环境
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Docker
docker compose up -d
```

---

## 10. 性能指标

### 10.1 生成时长参考

| 题目类型 | 平均时长 | 主要耗时 |
|----------|----------|----------|
| 立体几何 | 60-90s | LLM 生成 JSON |
| 函数/导数 | 30-50s | LLM + Manim 渲染 |
| 简单题目 | 20-30s | LLM 生成 |

### 10.2 并发限制

- 最大并发任务数：3
- 单个任务超时：300s
- 最大重试次数：3

---

## 11. 错误处理

### 11.1 JSON 解析错误

```
问题：LLM 返回的 JSON 不合法
解决：
1. 提取代码块内容
2. 截取最外层 {}
3. 修复 class='t' 语法
4. 移除尾随逗号
5. 修复非法转义
6. 移除控制字符
```

### 11.2 LLM API 错误

```
问题：API 返回 403/500
解决：
1. 指数退避重试 (2^attempt 秒)
2. 最多重试 3 次
3. 记录详细错误日志
```

### 11.3 任务状态

```
queued → detecting → loading_teaching → generating → rendering → generating_tts → done/failed
```

---

## 12. 后续优化方向

### 12.1 短期优化

- [ ] 增加题型检测准确率（引入 LLM 分类）
- [ ] 完善教学数据覆盖（更多题型和方法）
- [ ] 优化 JSON 解析成功率（更多修复策略）
- [ ] 添加题目图片 OCR 识别

### 12.2 中期优化

- [ ] 支持更多渲染器（GeoGebra、Desmos）
- [ ] 添加题目难度评估
- [ ] 支持多题目批量生成
- [ ] 添加用户反馈机制

### 12.3 长期优化

- [ ] 自研轻量级渲染引擎
- [ ] 支持初中数学题型
- [ ] 多语言支持
- [ ] SaaS 化部署

---

## 13. 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-03 | 初始版本，仅立体几何 |
| v1.1 | 2026-03 | 添加 Manim 渲染器，支持函数/导数 |
| v1.2 | 2026-03 | 引入 Claude Opus 4.6，优化 JSON 解析 |

---

## 14. 联系方式

项目地址：`geometry-lecture-service`

技术栈：FastAPI + Three.js + Manim + Claude Opus 4.6 + CosyVoice
