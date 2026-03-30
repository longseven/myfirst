# 解题/作图模型替换为 Claude Opus

## 修改内容

### 1. 配置文件 (`app/config.py`)

新增配置项：
```python
# 解题/作图专用模型 (Claude Opus)
problem_solving_model: str = "claude-opus-4-6"
problem_solving_api_key: str = ""  # 留空时使用 dashscope_api_key
problem_solving_api_url: str = "https://api.anthropic.com/v1/messages"
```

### 2. LLM 模块 (`app/pipeline/llm.py`)

- 添加 `ModelPurpose` 枚举：区分通用任务和解题/作图任务
- 添加 `_get_config_for_purpose()` 函数：根据用途返回对应的模型配置
- `call_llm()` 函数新增 `purpose` 参数：
  - `ModelPurpose.GENERAL` → 使用默认模型（如 qwen3.5-plus）
  - `ModelPurpose.PROBLEM_SOLVING` → 使用 Claude Opus

### 3. 任务流水线 (`app/pipeline/task_runner.py`)

解题/作图调用 LLM 时使用专用模型：
```python
raw_output = await call_llm(
    messages,
    temperature=0.1,
    max_tokens=16000,
    purpose=ModelPurpose.PROBLEM_SOLVING,  # ← 使用 Claude Opus
)
```

### 4. 环境变量 (`.env`)

```ini
# 解题/作图专用模型 (Claude Opus)
PROBLEM_SOLVING_MODEL=claude-opus-4-6
PROBLEM_SOLVING_API_KEY=sk-ant-your-api-key-here
PROBLEM_SOLVING_API_URL=https://api.anthropic.com/v1/messages
```

## 模型分配策略

| 任务类型 | 使用模型 | 说明 |
|----------|----------|------|
| 题型检测 | qwen3.5-plus (默认) | 轻量任务，关键字匹配 |
| 解题/作图 | **claude-opus-4-6** | 核心任务，需要强推理和空间想象能力 |
| TTS 语音 | cosyvoice-v3.5-plus | 语音合成 |

## 使用说明

1. 编辑 `.env` 文件，填入你的 Anthropic API Key：
   ```
   PROBLEM_SOLVING_API_KEY=sk-ant-your-actual-api-key
   ```

2. 如果使用代理或国内镜像，修改 API URL：
   ```
   PROBLEM_SOLVING_API_URL=https://your-anthropic-proxy.com/v1/messages
   ```

3. 重启服务：
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## 验证

查看日志输出，确认解题任务使用 Claude Opus：
```
INFO: Anthropic API (streaming): model=claude-opus-4-6, url=...
```
