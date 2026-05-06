"""
语言检测工具
Feature: i18n-language-switch

提供用户输入语言检测功能，用于决定 AI 回复语言。
"""

# 英文指令常量：注入到 prompt 开头，指示 AI 用英文回复
ENGLISH_INSTRUCTION = (
    "IMPORTANT: You must respond ENTIRELY in English. "
    "All text fields in your JSON response (reasoning, descriptions, "
    "analysis, labels, titles) must be written in English.\n\n"
)

# 英文指令尾部强化：追加到 prompt 末尾，强制 AI 用英文回复
ENGLISH_INSTRUCTION_SUFFIX = (
    "\n\nREMINDER: Your entire response MUST be in English. "
    "Do NOT use Chinese or any other language."
)

# 中文指令：强制 AI 用中文回复（不强制标题名称，交由各阶段 prompt 自身规范控制）
CHINESE_INSTRUCTION = (
    "IMPORTANT: You must respond ENTIRELY in Chinese. "
    "For single-sentence answers, also use Chinese. "
    "Keep business terms (e.g. Paid Attendance, region names) in original form as per 术语不翻译规则.\n\n"
)

# JSON 阶段中文指令：仅要求中文文本字段与严格 JSON 输出，禁止段落标题/额外文本
CHINESE_INSTRUCTION_JSON = (
    "IMPORTANT: You must respond ENTIRELY in Chinese for all natural-language text fields. "
    "Return ONLY one valid JSON object. "
    "No markdown, no code fences, no headings, no prose before/after JSON.\n\n"
)

# JSON 阶段英文指令
ENGLISH_INSTRUCTION_JSON = (
    "IMPORTANT: You must respond ENTIRELY in English for all natural-language text fields. "
    "Return ONLY one valid JSON object. "
    "No markdown, no code fences, no headings, no prose before/after JSON.\n\n"
)

# 中英文 stage 标签映射字典
STAGE_LABEL_MAP: dict[str, str] = {
    "意图识别": "Intent Recognition",
    "智能选表": "Table Selection",
    "意图澄清": "Intent Clarification",
    "模型思考": "Model Thinking",
    "SQL生成": "SQL Generation",
    "SQL执行": "SQL Execution",
    "数据结果描述": "Result Description",
    "生成图表": "Chart Generation",
    "结果解读": "Result Interpretation",
    "数据分析": "Data Analysis",
}

# 反向映射（英文 → 中文），用于双向查找
_STAGE_LABEL_MAP_REVERSE: dict[str, str] = {v: k for k, v in STAGE_LABEL_MAP.items()}


def detect_language(text: str) -> str:
    """
    检测文本语言，返回 'en' 或 'zh'。

    规则：非空白字符中 ASCII 字母占比 > 0.5 → 'en'，否则 → 'zh'。
    空字符串或无法判断时返回 'zh'。

    Args:
        text: 待检测的文本字符串

    Returns:
        'en' 表示英文，'zh' 表示中文（默认）
    """
    if not text:
        return 'zh'

    # 过滤空白字符，只保留非空白字符
    non_whitespace = [ch for ch in text if not ch.isspace()]

    if not non_whitespace:
        return 'zh'

    # 统计 ASCII 字母字符数量
    ascii_alpha_count = sum(1 for ch in non_whitespace if ch.isascii() and ch.isalpha())

    ratio = ascii_alpha_count / len(non_whitespace)

    return 'en' if ratio > 0.5 else 'zh'


def inject_language_instruction(prompt: str, language: str, stage: str | None = None) -> str:
    """
    根据语言参数向 prompt 开头注入语言指令。

    当 language='en' 时，在 prompt 开头注入英文指令常量；
    当 language='zh' 时，在 prompt 开头注入中文指令（文本阶段会包含段落标题规范）。
    对 JSON 输出阶段，注入严格 JSON 指令，避免输出摘要标题等非 JSON 内容。

    Args:
        prompt: 原始 prompt 字符串
        language: 语言代码，'en' 或 'zh'

    Returns:
        注入指令后的 prompt（或原始 prompt）
    """
    json_stages = {
        "intent_recognition",
        "table_selection",
        "intent_clarification",
        "sql_generation",
        "chart_recommendation",
        "error_recovery",
    }
    is_json_stage = stage in json_stages if stage else False

    if language == 'en':
        if is_json_stage:
            return ENGLISH_INSTRUCTION_JSON + prompt
        return ENGLISH_INSTRUCTION + prompt + ENGLISH_INSTRUCTION_SUFFIX
    if language == 'zh':
        if is_json_stage:
            return CHINESE_INSTRUCTION_JSON + prompt
        return CHINESE_INSTRUCTION + prompt
    return prompt


def translate_stage_label(label: str, language: str) -> str:
    """
    翻译 stage 标签。

    当 language='en' 时，将中文 stage 标签翻译为英文；
    当 language='zh' 时，返回原始标签不变。
    未知标签原样返回。

    Args:
        label: stage 标签字符串（中文或英文）
        language: 语言代码，'en' 或 'zh'

    Returns:
        翻译后的标签字符串
    """
    if language == 'en':
        return STAGE_LABEL_MAP.get(label, label)
    return label
