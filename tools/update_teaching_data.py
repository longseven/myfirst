"""
update_teaching_data.py — 从视频转录文本自动更新 teaching_data 目录

用法:
  python update_teaching_data.py --input "D:\...\output" --output "./data/teaching_data"

流程:
  1. 扫描 input 目录下所有子目录的 .txt 文件（排除 _diff.txt / _题目.txt）
  2. 按子目录名自动映射到学科（立体几何/三角函数/函数/...）
  3. 对每个学科的文件，调用 LLM 提取题型+方法的结构化 JSON
  4. 合并已有 teaching_data 内容 + 新提取内容，生成/更新 markdown 文件
  5. 更新 manifest.json
"""

import os
import sys
import json
import glob
import asyncio
import argparse
import re
from datetime import datetime

import aiohttp

# ============================================================
# 配置
# ============================================================

API_KEY = os.environ.get('DASHSCOPE_API_KEY', 'sk-bcdef141f9c040d0970b7c048ad9646c')
API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
MODEL = 'qwen-plus'
CONCURRENCY = 5
CHUNK_SIZE = 60000    # 单次 LLM 调用的最大字符数（qwen-plus 支持 128k token）
BATCH_SIZE = 60000    # 合并多个文件时的批次上限

# 子目录名 → 学科名的映射（处理命名差异）
DIR_TO_SUBJECT = {
    '立体几何': '立体几何',
    '三角函数': '三角函数',
    '函数': '函数',
    '导数': '导数',
    '解析几何': '解析几何',
    '平面向量解三角形': '解三角形',
    '平面向量': '平面向量',
    '数列': '数列',
    '排列组合概率统计': '排列组合概率统计',
    '衔接、集合不等式': '集合与不等式',
    '数学最后十课': '高考冲刺综合',
}

# ============================================================
# 标准题型+方法命名参考表（LLM 必须优先使用这些名称）
# ============================================================

STANDARD_NAMES = {
    '立体几何': {
        '题型': ['证平行垂直', '求二面角', '求距离', '求截面体积', '求体积表面积', '外接球内切球'],
        '方法': ['坐标法', '向量法', '综合法'],
    },
    '解三角形': {
        '题型': ['求边角', '求面积周长', '求范围最值', '判断三角形形状'],
        '方法': ['正弦定理', '余弦定理', '面积公式', '三角换元', '判别式法'],
    },
    '三角函数': {
        '题型': ['求解析式', '求值', '求最值值域', '求单调区间', '图像变换', '三角恒等变换'],
        '方法': ['辅助角公式', '二倍角公式', '和差化积', '万能公式', '数形结合'],
    },
    '函数': {
        '题型': ['求定义域值域', '判断单调性奇偶性', '零点问题', '函数图像', '抽象函数'],
        '方法': ['换元法', '分离参数', '数形结合', '构造函数', '分类讨论'],
    },
    '导数': {
        '题型': ['求切线方程', '求单调区间', '求极值最值', '证明不等式', '零点问题', '恒成立问题'],
        '方法': ['分离参数', '构造函数', '放缩法', '分类讨论', '端点效应'],
    },
    '解析几何': {
        '题型': ['求轨迹方程', '求弦长', '求面积', '求定点定值', '求范围最值', '存在性问题'],
        '方法': ['联立韦达', '设点法', '参数法', '齐次化', '极点极线'],
    },
    '数列': {
        '题型': ['求通项公式', '求前n项和', '证明不等式', '数列与递推'],
        '方法': ['累加法', '累乘法', '待定系数法', '错位相减', '裂项相消', '放缩法', '数学归纳法'],
    },
    '平面向量': {
        '题型': ['求模', '求夹角', '求坐标', '向量应用'],
        '方法': ['坐标法', '基底法', '数量积'],
    },
    '排列组合概率统计': {
        '题型': ['计数问题', '古典概型', '条件概率', '分布列期望', '回归分析', '独立性检验'],
        '方法': ['分类加法', '分步乘法', '捆绑法', '插空法', '隔板法', '容斥原理', '递推法'],
    },
    '集合与不等式': {
        '题型': ['集合运算', '一元二次不等式', '线性规划', '基本不等式', '含参不等式'],
        '方法': ['数轴标根法', '图解法', '分离参数', '配凑法'],
    },
    '复数': {
        '题型': ['复数运算', '复数几何意义', '复数与方程'],
        '方法': ['代数形式运算', '共轭复数法', '模的公式'],
    },
}

# ============================================================
# LLM 提取 Prompt（按教研组模板格式）
# ============================================================

EXTRACT_PROMPT = """你是高中数学教研组资深专家。下面是「{subject}」学科的多段讲课视频语音转录文本。

请严格按以下结构归纳，输出 JSON。每个题型必须包含完整的6大板块：

{{
  "subject": "{subject}",
  "types": [
    {{
      "type_name": "题型名称",
      "difficulty": "易/易-中档/中档/中档-拔高/拔高",
      "common_forms": [
        "常见出题形式1（如：折叠问题——正方形沿某线折叠后证新线∥某平面）",
        "常见出题形式2",
        "常见出题形式3"
      ],
      "methods": [
        {{
          "name": "方法名",
          "applicable": "适用场景（什么条件下优先用这个方法）",
          "not_applicable": "不适用场景（什么条件下不该用）",
          "teaching_flow": [
            "步骤1：审题定位——明确...",
            "步骤2：选法决策——根据...",
            "步骤3：构造辅助元素——...",
            "步骤4：逻辑闭环——写出..."
          ],
          "key_techniques": [
            "✅ 技巧1：具体描述（含公式/口诀）",
            "✅ 技巧2：..."
          ],
          "common_mistakes": [
            "❌ 易错点1：具体描述（含扣分后果）",
            "❌ 易错点2：..."
          ],
          "scoring_notes": [
            "评分点1（如：正确构造辅助点 → 1分）",
            "评分点2（如：证明中点关系 → 2分）"
          ],
          "formulas": ["$公式1$", "$公式2$"]
        }}
      ]
    }}
  ],
  "general_advice": {{
    "strategy_priority": ["策略优先级1（如：建系策略——垂足 > 直角顶点 > 对称中心）"],
    "construction_rules": ["辅助线构造铁律1（如：中点必连——中点出现即想中位线）"],
    "writing_standards": ["书写规范红线1（如：三要素缺一不可）"],
    "cognitive_tips": ["认知突破法1（如：动点问题画极限位置图）"]
  }}
}}

⚠️ 命名规范（必须遵守）：
题型名称优先从以下标准名选取：{standard_types}
方法名称优先从以下标准名选取：{standard_methods}
如果文本中出现了标准名之外的全新题型或方法，可以新增，但命名风格保持一致（简洁动宾短语）。

⚠️ 质量要求：
- teaching_flow 必须是可操作的具体步骤，不要空泛（参考示例："审题定位→选法决策→构造辅助元素→逻辑闭环"）
- key_techniques 要包含公式/口诀/定理名称
- common_mistakes 要写具体错法和后果（如"忽略书写前提→高考扣1分"）
- scoring_notes 要按高考阅卷标准写分值分配
- 只基于文本内容提取，不要编造
- 同一方法在多个视频中出现时，合并归纳
- formulas 用 LaTeX 格式，$...$包裹
- 已有题型供参考（优先对齐）：{existing_types}

只输出 JSON，不要其他内容。"""

# ============================================================
# 工具函数
# ============================================================

def scan_files(input_dir):
    """扫描目录，返回 {学科: [文件路径]} 的映射"""
    result = {}

    # 根目录下的文件
    root_files = []
    for f in glob.glob(os.path.join(input_dir, '*.txt')):
        if f.endswith('_diff.txt') or f.endswith('_题目.txt'):
            continue
        root_files.append(f)

    # 根据文件名猜测学科（根目录文件通常是解析几何相关）
    if root_files:
        result['解析几何'] = result.get('解析几何', []) + root_files

    # 子目录
    for entry in os.listdir(input_dir):
        subdir = os.path.join(input_dir, entry)
        if not os.path.isdir(subdir):
            continue
        if entry == '分P大合集版本':
            continue  # 跳过分P版本，内容和其他目录重复

        subject = DIR_TO_SUBJECT.get(entry, entry)
        files = []
        for f in glob.glob(os.path.join(subdir, '*.txt')):
            if f.endswith('_diff.txt') or f.endswith('_题目.txt'):
                continue
            files.append(f)
        if files:
            result[subject] = result.get(subject, []) + files

    return result


def read_and_clean(filepath):
    """读取转录文件，去掉时间戳"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = []
    for line in content.strip().split('\n'):
        bracket_end = line.find(']')
        if bracket_end > 0:
            lines.append(line[bracket_end + 1:].strip())
        else:
            lines.append(line.strip())
    return '\n'.join(lines)


def get_existing_types(teaching_data_dir, subject):
    """读取现有 teaching_data 中该学科的题型名称列表"""
    subject_dir = os.path.join(teaching_data_dir, subject)
    if not os.path.isdir(subject_dir):
        return []
    types = []
    for entry in os.listdir(subject_dir):
        if os.path.isdir(os.path.join(subject_dir, entry)) and not entry.startswith('_'):
            types.append(entry)
    return types


# ============================================================
# LLM 调用
# ============================================================

def _split_text_into_chunks(text, chunk_size=CHUNK_SIZE):
    """将单个大文本按段落边界切分为多个 chunk，每块不超过 chunk_size 字符"""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    paragraphs = text.split('\n')
    current = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para) + 1  # +1 for newline
        if current_len + para_len > chunk_size and current:
            chunks.append('\n'.join(current))
            current = [para]
            current_len = para_len
        else:
            current.append(para)
            current_len += para_len

    if current:
        chunks.append('\n'.join(current))

    return chunks


async def extract_subject(session, sem, subject, files, existing_types):
    """对一个学科的所有文件调用 LLM 提取结构化信息。

    大文件处理策略:
    - 每个文件不再截断，而是完整读入
    - 单个文件 > CHUNK_SIZE 时，拆分为多个 chunk 分别调用 LLM
    - 多个小文件合并为一个 batch（不超过 BATCH_SIZE）
    - 所有 batch 的提取结果合并后去重
    """
    # 读取所有文件，标注文件名
    file_texts = []
    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        text = read_and_clean(fp)
        file_texts.append((name, text))
        size_kb = len(text) / 1024
        if size_kb > 50:
            print(f"  [{subject}] {name}: {size_kb:.0f}K 字符（大文件，将分块处理）")

    # 构建 batches：先处理大文件（拆 chunk），再把小文件打包
    batches = []
    small_buffer = []
    small_buffer_len = 0

    for name, text in file_texts:
        tagged = f"=== {name} ===\n{text}"

        if len(tagged) > BATCH_SIZE:
            # 大文件：先把小文件缓冲区清空
            if small_buffer:
                batches.append('\n\n'.join(small_buffer))
                small_buffer = []
                small_buffer_len = 0
            # 拆分为多个 chunk
            chunks = _split_text_into_chunks(text, CHUNK_SIZE)
            for ci, chunk in enumerate(chunks):
                label = f"=== {name} (第{ci+1}/{len(chunks)}部分) ===\n{chunk}"
                batches.append(label)
        else:
            # 小文件：尝试合并到当前 buffer
            if small_buffer_len + len(tagged) > BATCH_SIZE and small_buffer:
                batches.append('\n\n'.join(small_buffer))
                small_buffer = [tagged]
                small_buffer_len = len(tagged)
            else:
                small_buffer.append(tagged)
                small_buffer_len += len(tagged)

    if small_buffer:
        batches.append('\n\n'.join(small_buffer))

    all_types = []
    all_advice = []
    types_str = '、'.join(existing_types) if existing_types else '（暂无，请自行命名）'

    # 获取标准命名
    std = STANDARD_NAMES.get(subject, {})
    std_types_str = '、'.join(std.get('题型', [])) if std.get('题型') else '（无标准名，自行命名）'
    std_methods_str = '、'.join(std.get('方法', [])) if std.get('方法') else '（无标准名，自行命名）'

    for i, batch_text in enumerate(batches):
        async with sem:
            prompt = EXTRACT_PROMPT.format(
                subject=subject,
                existing_types=types_str,
                standard_types=std_types_str,
                standard_methods=std_methods_str,
            )
            payload = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": batch_text}
                ],
                "temperature": 0.1,
                "max_tokens": 8000
            }
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }

            for attempt in range(3):
                try:
                    async with session.post(API_URL, json=payload, headers=headers,
                                            timeout=aiohttp.ClientTimeout(total=120)) as resp:
                        data = await resp.json()
                        result_text = data['choices'][0]['message']['content'].strip()

                        # 提取 JSON
                        if '```' in result_text:
                            result_text = result_text.split('```')[1]
                            if result_text.startswith('json'):
                                result_text = result_text[4:]
                            result_text = result_text.strip()

                        parsed = json.loads(result_text)
                        batch_types = parsed.get('types', [])
                        all_types.extend(batch_types)
                        # 收集 general_advice
                        ga = parsed.get('general_advice')
                        if ga:
                            all_advice.append(ga)
                        print(f"  [{subject}] 批次 {i+1}/{len(batches)}: 提取到 {len(batch_types)} 个题型")
                        break

                except json.JSONDecodeError:
                    if attempt == 2:
                        print(f"  [{subject}] 批次 {i+1} JSON解析失败，跳过")
                except Exception as e:
                    if attempt == 2:
                        print(f"  [{subject}] 批次 {i+1} 失败: {e}")
                    else:
                        await asyncio.sleep(2)

    return subject, {
        'types': _dedup_types(all_types),
        'general_advice': _merge_general_advice(all_advice),
    }


def _dedup_types(types_list):
    """合并同名题型，同名方法去重"""
    merged = {}
    for t in types_list:
        name = t.get('type_name', '未命名')
        if name not in merged:
            merged[name] = {
                'type_name': name,
                'difficulty': t.get('difficulty', ''),
                'common_forms': [],
                'methods': [],
                '_form_set': set(),
                '_method_names': set(),
            }
        # 合并 common_forms（去重）
        for form in t.get('common_forms', []):
            if form not in merged[name]['_form_set']:
                merged[name]['_form_set'].add(form)
                merged[name]['common_forms'].append(form)
        # 合并方法（按 name 去重）
        for m in t.get('methods', []):
            mname = m.get('name', '')
            if mname not in merged[name]['_method_names']:
                merged[name]['_method_names'].add(mname)
                merged[name]['methods'].append(m)

    # 移除辅助字段
    result = []
    for v in merged.values():
        del v['_form_set']
        del v['_method_names']
        result.append(v)
    return result


def _merge_general_advice(advice_list):
    """合并多个 batch 的 general_advice，去重"""
    merged = {
        'strategy_priority': [],
        'construction_rules': [],
        'writing_standards': [],
        'cognitive_tips': [],
    }
    seen = {k: set() for k in merged}

    for advice in advice_list:
        if not isinstance(advice, dict):
            continue
        for key in merged:
            for item in advice.get(key, []):
                if item not in seen[key]:
                    seen[key].add(item)
                    merged[key].append(item)
    return merged


async def extract_all(subject_files, teaching_data_dir):
    """并发提取所有学科"""
    sem = asyncio.Semaphore(CONCURRENCY)
    results = {}

    async with aiohttp.ClientSession() as session:
        tasks = []
        for subject, files in subject_files.items():
            existing = get_existing_types(teaching_data_dir, subject)
            tasks.append(extract_subject(session, sem, subject, files, existing))

        for coro in asyncio.as_completed(tasks):
            subject, data = await coro
            results[subject] = data

    return results


# ============================================================
# 写入 teaching_data 目录
# ============================================================

def sanitize_filename(name):
    """清理文件名中的非法字符"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip('. ')
    return name[:80]  # 限制长度


def write_method_md(filepath, method, type_name=''):
    """写入单个方法的 markdown 文件（按教研组模板格式）"""
    name = method.get('name', '未命名方法')
    lines = [f"# {name}\n"]

    # 适用/不适用场景
    if method.get('applicable') or method.get('not_applicable'):
        lines.append("## 适用场景\n")
        if method.get('applicable'):
            lines.append(f"**适用**：{method['applicable']}\n")
        if method.get('not_applicable'):
            lines.append(f"**不适用**：{method['not_applicable']}\n")

    # 标准教学流程（步骤化）
    if method.get('teaching_flow'):
        lines.append("## 标准教学流程（步骤化）\n")
        for i, step in enumerate(method['teaching_flow'], 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    # 关键技巧清单
    if method.get('key_techniques'):
        lines.append("## 关键技巧清单\n")
        for t in method['key_techniques']:
            lines.append(f"- {t}")
        lines.append("")

    # 核心公式
    if method.get('formulas'):
        lines.append("## 核心公式\n")
        for f in method['formulas']:
            lines.append(f"- {f}")
        lines.append("")

    # 常见易错点
    if method.get('common_mistakes'):
        lines.append("## 常见易错点\n")
        for m in method['common_mistakes']:
            lines.append(f"- {m}")
        lines.append("")

    # 评分要点
    if method.get('scoring_notes'):
        lines.append("## 评分要点（高考阅卷标准）\n")
        for s in method['scoring_notes']:
            lines.append(f"- {s}")
        lines.append("")

    # 兼容旧格式字段（steps / key_points）
    if not method.get('teaching_flow') and method.get('steps'):
        lines.append("## 解题步骤\n")
        for i, step in enumerate(method['steps'], 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    if not method.get('key_techniques') and method.get('key_points'):
        lines.append("## 关键要点\n")
        for p in method['key_points']:
            lines.append(f"- {p}")
        lines.append("")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def write_overview_md(filepath, type_info):
    """写入题型概述文件（按教研组模板格式）"""
    type_name = type_info.get('type_name', '未命名')
    lines = [
        f"# {type_name}\n",
        f"**难度**: {type_info.get('difficulty', '未标注')}\n",
    ]

    # 1. 常见出题形式
    forms = type_info.get('common_forms', [])
    if forms:
        lines.append("## 1. 常见出题形式\n")
        for form in forms:
            lines.append(f"- {form}")
        lines.append("")

    # 2. 推荐解题方法及适用场景（表格）
    methods = type_info.get('methods', [])
    if methods:
        lines.append("## 2. 推荐解题方法及适用场景\n")
        lines.append("| 方法 | 适用场景 | 不适用场景 |")
        lines.append("|--------|------------|--------------|")
        for m in methods:
            name = m.get('name', '')
            ok = m.get('applicable', '')
            nok = m.get('not_applicable', '')
            lines.append(f"| **{name}** | {ok} | {nok} |")
        lines.append("")

    # 3. 包含方法列表（快速索引）
    if methods:
        lines.append("## 3. 包含方法\n")
        for m in methods:
            lines.append(f"- **{m.get('name', '')}** → `{sanitize_filename(m.get('name', ''))}.md`")
        lines.append("")

    # 兼容旧格式 description
    desc = type_info.get('description', '')
    if desc and not forms:
        lines.append(f"## 概述\n")
        lines.append(f"{desc}\n")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def write_general_md(filepath, subject, general_advice):
    """写入学科通用教学建议（按教研组模板格式）"""
    lines = [
        f"# {subject} · 跨题型通用教学建议\n",
        f"**（高中数学教研组·结构化归纳版）**\n",
    ]

    sections = [
        ('strategy_priority', '建系/解题策略优先级'),
        ('construction_rules', '辅助线构造铁律'),
        ('writing_standards', '高考书写规范红线'),
        ('cognitive_tips', '学生认知断层突破法'),
    ]

    num = 1
    for key, title in sections:
        items = general_advice.get(key, [])
        if items:
            lines.append(f"## {num}. {title}\n")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
            num += 1

    if num == 1:
        # 没有任何 general_advice 内容，写占位
        lines.append("## 概述\n\n待补充。\n")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def merge_and_write(extracted, teaching_data_dir, mode='merge'):
    """
    将提取结果写入 teaching_data 目录。

    mode:
      'merge'     — 保留已有文件，只添加新的题型/方法（默认）
      'overwrite' — 覆盖已有同名文件
    """
    stats = {'subjects': 0, 'types_added': 0, 'methods_added': 0, 'files_written': 0}

    for subject, data in extracted.items():
        # 兼容两种格式：直接 list[types] 或 dict{types, general_advice}
        if isinstance(data, dict):
            types = data.get('types', [])
            general_advice = data.get('general_advice', {})
        else:
            types = data if data else []
            general_advice = {}

        if not types and not general_advice:
            continue

        subject_dir = os.path.join(teaching_data_dir, subject)
        os.makedirs(subject_dir, exist_ok=True)
        stats['subjects'] += 1

        # 写入 _通用.md（跨题型通用教学建议）
        general_path = os.path.join(subject_dir, '_通用.md')
        if general_advice and (mode == 'overwrite' or not os.path.exists(general_path)):
            write_general_md(general_path, subject, general_advice)
            stats['files_written'] += 1
        elif not os.path.exists(general_path):
            with open(general_path, 'w', encoding='utf-8') as f:
                f.write(f"# {subject} · 学科通用\n\n## 概述\n\n待补充。\n")
            stats['files_written'] += 1

        for type_info in types:
            type_name = sanitize_filename(type_info.get('type_name', '未命名'))
            type_dir = os.path.join(subject_dir, type_name)
            os.makedirs(type_dir, exist_ok=True)

            # 写入/更新 _概述.md
            overview_path = os.path.join(type_dir, '_概述.md')
            if mode == 'overwrite' or not os.path.exists(overview_path):
                write_overview_md(overview_path, type_info)
                stats['files_written'] += 1
                if not os.path.exists(overview_path):
                    stats['types_added'] += 1

            # 写入方法文件
            for method in type_info.get('methods', []):
                method_name = sanitize_filename(method.get('name', '未命名方法'))
                method_path = os.path.join(type_dir, f"{method_name}.md")

                if mode == 'overwrite' or not os.path.exists(method_path):
                    write_method_md(method_path, method, type_name)
                    stats['files_written'] += 1
                    stats['methods_added'] += 1

    return stats


def update_manifest(teaching_data_dir):
    """重新扫描目录，生成 manifest.json"""
    structure = {}
    subjects = []

    for entry in sorted(os.listdir(teaching_data_dir)):
        entry_path = os.path.join(teaching_data_dir, entry)

        if entry == 'manifest.json':
            continue

        if entry == '_通用':
            files = [f for f in os.listdir(entry_path) if f.endswith('.md')]
            structure['_通用'] = {'files': sorted(files)}
            continue

        if not os.path.isdir(entry_path):
            continue

        subjects.append(entry)
        subj_data = {'files': [], '题型': {}}

        for item in sorted(os.listdir(entry_path)):
            item_path = os.path.join(entry_path, item)
            if item.endswith('.md'):
                subj_data['files'].append(item)
            elif os.path.isdir(item_path) and not item.startswith('_'):
                type_files = sorted([
                    f for f in os.listdir(item_path) if f.endswith('.md')
                ])
                subj_data['题型'][item] = {'files': type_files}

        structure[entry] = subj_data

    manifest = {
        '_meta': {
            'version': '2.1',
            'description': '高中数学教学资料三级目录结构：学科 → 题型 → 方法',
            'updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        },
        '学科列表': subjects,
        'structure': structure,
    }

    manifest_path = os.path.join(teaching_data_dir, 'manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nmanifest.json 已更新: {len(subjects)} 个学科")


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='从视频转录文本更新 teaching_data')
    parser.add_argument('--input', '-i', required=True,
                        help='转录文件根目录 (如 D:\\...\\output)')
    parser.add_argument('--output', '-o', default='./data/teaching_data',
                        help='teaching_data 目录路径 (默认 ./data/teaching_data)')
    parser.add_argument('--mode', choices=['merge', 'overwrite'], default='merge',
                        help='merge=只添加新内容(默认), overwrite=覆盖同名文件')
    parser.add_argument('--save-json', default=None,
                        help='保存 LLM 提取的原始 JSON 到指定文件（调试用）')
    parser.add_argument('--from-json', default=None,
                        help='跳过 LLM，直接从之前保存的 JSON 文件读取（省钱）')
    args = parser.parse_args()

    input_dir = args.input
    output_dir = args.output

    if not os.path.isdir(input_dir):
        print(f"错误: 输入目录不存在: {input_dir}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # ── 1. 扫描文件 ──
    print(f"扫描目录: {input_dir}")
    subject_files = scan_files(input_dir)

    total_files = sum(len(f) for f in subject_files.values())
    print(f"找到 {total_files} 个转录文件，分布在 {len(subject_files)} 个学科:\n")
    for subj, files in sorted(subject_files.items()):
        print(f"  {subj}: {len(files)} 个文件")

    # ── 2. LLM 提取 ──
    if args.from_json:
        print(f"\n从缓存加载: {args.from_json}")
        with open(args.from_json, 'r', encoding='utf-8') as f:
            extracted = json.load(f)
    else:
        print(f"\n开始 LLM 提取（模型: {MODEL}，并发: {CONCURRENCY}）...\n")
        extracted = asyncio.run(extract_all(subject_files, output_dir))

    # 保存原始 JSON（可选）
    if args.save_json:
        with open(args.save_json, 'w', encoding='utf-8') as f:
            json.dump(extracted, f, ensure_ascii=False, indent=2)
        print(f"\n原始 JSON 已保存: {args.save_json}")

    # ── 3. 写入 teaching_data ──
    print(f"\n写入 teaching_data 目录: {output_dir} (mode={args.mode})\n")
    stats = merge_and_write(extracted, output_dir, mode=args.mode)

    print(f"  学科: {stats['subjects']}")
    print(f"  新增题型: {stats['types_added']}")
    print(f"  新增方法: {stats['methods_added']}")
    print(f"  写入文件: {stats['files_written']}")

    # ── 4. 更新 manifest ──
    update_manifest(output_dir)

    print(f"\n完成！")


if __name__ == '__main__':
    main()
