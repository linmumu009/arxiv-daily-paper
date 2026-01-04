try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except Exception:
    ZoneInfo = None
    class ZoneInfoNotFoundError(Exception): ...
from datetime import timezone, timedelta

def get_beijing_tz():
    if ZoneInfo:
        try:
            return ZoneInfo("Asia/Shanghai")
        except ZoneInfoNotFoundError:
            pass
    return timezone(timedelta(hours=8))  # 兜底

LOCAL_TZ = get_beijing_tz()

# -------------------------------
# 调试 / 行为
# -------------------------------
DEBUG = True
DRY_RUN = False                 # 先干跑
LIMIT_PER_ORG = 2
DOWNLOAD_CONCURRENCY = 4
CONNECT_TIMEOUT_SEC = 30
READ_TIMEOUT_SEC = 120

# 时间窗口依据： 'updated'（昨天有任何更新就算）| 'published'（昨天首次投稿）| 'both'
WINDOW_FIELD = "published"       # ← 新增：用来解决“跨月编号”带来的困惑

# -------------------------------
# PDF 分类相关
# -------------------------------
CLASSIFY_FROM_PDF = True          # True=按 PDF 作者/单位区匹配；False=沿用摘要/标题
PDF_CACHE_DIR = "cache_pdfs"      # 统一缓存目录
USE_HARDLINKS = True              # Windows若无权限会自动回退为复制
MAX_PDF_PAGES_TO_SCAN = 2         # 只扫前2页（作者/单位通常在首页/次页）
PDF_EXTRACT_ENGINE = "pymupdf"    # "pymupdf"（推荐）| "pypdf"（备选）

# （可选）作者/单位区“关键词”提示，用于简单启发式筛行
AFFIL_HINT_KEYWORDS = [
    "University", "Institute", "Laboratory", "Lab", "Dept", "Department",
    "College", "School", "Center", "Centre"
]

# -------------------------------
# arXiv API & 网络
# -------------------------------
ARXIV_API_ENDPOINTS = [
    "https://arxiv.org/api/query",       # ← 先用主站
    "https://export.arxiv.org/api/query",
    "http://export.arxiv.org/api/query",
]
REQUEST_TIMEOUT = (20, 120)   # (connect_timeout, read_timeout)

RETRY_TOTAL = 7               # ↑稍微加大重试次数更稳
RETRY_BACKOFF = 1.5

REQUESTS_UA = "DailyPaper/1.0 (+contact: your_email@example.com)"

PROXIES = None
RESPECT_ENV_PROXIES = True
NO_PROXY_HOSTS = ["arxiv.org", "export.arxiv.org"]

# 拉取范围 / 分页
MAX_RESULTS_PER_PAGE = 100     # 每页上限 200
MAX_PAGES = 5                # 10 页≈2000条（足够覆盖昨天窗口）

# 直搜（fallback）分页（给 app.py 的 per-org 直搜使用）
PER_ORG_SEARCH_LIMIT_PAGES = 5       # ← 新增：每个机构直搜最多扫几页
PER_ORG_SEARCH_PAGE_SIZE   = 200     # ← 新增：每页多少条（建议 200）

# -------------------------------
# 输出 & 匹配
# -------------------------------
OUT_BASE_DIR = "output_org_pdfs"

INSTITUTIONS_PATTERNS = {
    # ---- 国际公司 ----
    "Apple":        [r"\bApple(?:\s+Research)?\b"],
    "Meta":         [r"\bMeta(?:\s+AI)?\b", r"\bFAIR\b", r"\bFacebook\s*AI\s*Research\b"],
    "Google":       [r"\bGoogle(?:\s*Research)?\b", r"\bGoogle\s*DeepMind\b", r"\bDeepMind\b"],
    "NVIDIA":       [r"\bNVIDIA\b", r"\bNVidia\b"],

    # ---- 中国公司 ----
    "Tencent":      [r"\bTencent\b", r"腾讯"],
    "ByteDance":    [r"\bByteDance\b", r"字节跳动"],
    "Alibaba":      [r"\bAlibaba\b", r"\bAliyun\b", r"阿里巴巴"],

    # ---- 顶尖高校 ----
    "MIT":          [r"\bMIT\b", r"\bMassachusetts\s*Institute\s*of\s*Technology\b", r"\bCSAIL\b"],
    "Stanford":     [r"\bStanford\b", r"\bStanford\s*University\b"],

    # ---- 国际科技公司 ----
    "Microsoft":    [r"\bMicrosoft\b", r"\bMicrosoft\s*Research\b", r"\bMSR\b",
                     r"\bMSRA\b", r"\bMicrosoft\s*Research\s*Asia\b"],
    "OpenAI":       [r"\bOpenAI\b"],
    "Anthropic":    [r"\bAnthropic\b"],
    "IBM":          [r"\bIBM\b", r"\bIBM\s*Research\b"],
    "Amazon":       [r"\bAmazon\b", r"\bAWS\b", r"\bAmazon\s*AI\b", r"\bAWS\s*AI\b",
                     r"\bAmazon\s*Science\b", r"\bAWS\s*AI\s*Labs?\b"],

    # ---- 中国大厂 ----
    "Huawei":       [r"\bHuawei\b", r"\bHuawei\s*Noah'?s\s*Ark\s*Lab\b", r"华为", r"诺亚方舟"],
    "Baidu":        [r"\bBaidu\b", r"百度"],
    "SenseTime":    [r"\bSenseTime\b", r"商汤"],
    "Megvii":       [r"\bMegvii\b", r"旷视"],
    "Yitu":         [r"\bYitu\b", r"依图"],

    # ---- 开源/研究组织 ----
    "AI2":          [r"\bAllen\s*Institute\s*for\s*AI\b", r"\bAllen\s*Institute\b", r"\bAI2\b", r"\bAllen\s*AI\b"],
    "HuggingFace":  [r"\bHugging\s*Face\b", r"\bHuggingFace\b"],
    "LAION":        [r"\bLAION\b"],
    "EleutherAI":   [r"\bEleuther\s*AI\b", r"\bEleutherAI\b"],

    # ---- 高校扩展 ----
    "CMU":          [r"\bCMU\b", r"\bCarnegie\s*Mellon\b", r"\bCarnegie\s*Mellon\s*University\b"],
    "Berkeley":     [r"\bUC\s*Berkeley\b", r"\bUniversity\s*of\s*California,\s*Berkeley\b"],
    "Tsinghua":     [r"\bTsinghua\b", r"清华", r"\bTsinghua\s*University\b"],
    "PekingU":      [r"\bPeking\s*University\b", r"\bPKU\b", r"北京大学"],
    "Oxford":       [r"\bUniversity\s*of\s*Oxford\b"],
    "Cambridge":    [r"\bUniversity\s*of\s*Cambridge\b"],
    "ETH":          [r"\bETH\b", r"\bETH\s*Z(?:u|ü)rich\b", r"\bETH\s*Zurich\b", r"\bETH\s*Zürich\b"],

        # ---- 更多可信大厂/研究机构（建议补充）----
    "xAI":          [r"\bxAI\b"],
    "Mistral":      [r"\bMistral\b", r"\bMistral\s*AI\b"],
    "Cohere":       [r"\bCohere\b"],
    "Salesforce":   [r"\bSalesforce\b", r"\bSalesforce\s*Research\b"],
    "Adobe":        [r"\bAdobe\b", r"\bAdobe\s*Research\b"],
    "Databricks":   [r"\bDatabricks\b", r"\bMosaicML\b"],
    "Snowflake":    [r"\bSnowflake\b"],
    "Intel":        [r"\bIntel\b", r"\bIntel\s*Labs?\b"],
    "Qualcomm":     [r"\bQualcomm\b"],
    "Samsung":      [r"\bSamsung\b", r"\bSamsung\s*Research\b"],
    "LG":           [r"\bLG\b", r"\bLG\s*AI\s*Research\b"],
    "NAVER":        [r"\bNAVER\b", r"\bNAVER\s*AI\s*Lab\b"],

    # ---- 中国大厂别名补齐（减少漏检）----
    "Alibaba":      [
        r"\bAlibaba\b", r"\bAliyun\b", r"阿里巴巴",
        r"\bDAMO\b", r"达摩院",                 # ✅ 阿里达摩院
        r"\bAnt\s*Group\b", r"蚂蚁集团"         # ✅ 蚂蚁（作者常挂Ant）
    ],
    "ByteDance":    [
        r"\bByteDance\b", r"字节跳动",
        r"\bSeed\b", r"\bByteDance\s*Seed\b",   # ✅ ByteDance Seed
        r"\bVolcano\s*Engine\b", r"火山引擎"
    ],
    "Tencent":      [
        r"\bTencent\b", r"腾讯",
        r"\bTencent\s*AI\s*Lab\b", r"腾讯\s*AI\s*Lab",
        r"\bRobotics\s*X\b"
    ],
    "Baidu":        [
        r"\bBaidu\b", r"百度",
        r"\bBaidu\s*Research\b", r"百度研究院"
    ],
        # ---- 中国：新型但技术过硬 ----
    "ShanghaiAI Lab": [
        r"上海人工智能实验室", r"上海AI实验室",
        r"\bShanghai\s*AI\s*Lab(?:oratory)?\b",
        r"\bShanghai\s*Artificial\s*Intelligence\s*Laboratory\b",
        r"\bShanghai\s*AI\s*Laboratory\b",
    ],
    "MiniMax": [
        r"\bMiniMax\b", r"\bMiniMax\s*AI\b",
        r"稀宇科技",   # MiniMax 的中文公司名，PDF 里偶尔会写
    ],
    "ZhipuAI": [
        r"\bZhipu(?:\.?AI)?\b", r"智谱(?:AI)?", r"智谱华章",
    ],
    "DeepSeek": [r"\bDeepSeek\b", r"深度求索"],
    "MoonshotAI": [r"\bMoonshot\s*AI\b", r"月之暗面"],
    "Baichuan": [r"\bBaichuan\b", r"百川智能"],
    "01AI": [r"\b01\.?AI\b", r"零一万物"],

    # ---- 世界：LLM 高产的新势力/研究型公司（可按需取舍）----
    "Mistral": [r"\bMistral\b", r"\bMistral\s*AI\b"],
    "Cohere": [r"\bCohere\b"],
    "xAI": [r"\bxAI\b"],
    "TogetherAI": [r"\bTogether\s*AI\b", r"\bTogether\.?ai\b"],
    "StabilityAI": [r"\bStability\s*AI\b"],
    "Runway": [r"\bRunway\b", r"\bRunway\s*ML\b"],


}

ORG_SEARCH_TERMS = {
    "Apple":    ['"Apple"', '"Apple Research"'],
    "Meta":     ['"Meta"', '"Meta AI"', '"FAIR"', '"Facebook AI Research"'],
    "Google":   ['"Google"', '"Google Research"', '"Google DeepMind"', '"DeepMind"'],
    "NVIDIA":   ['"NVIDIA"'],
    "Tencent":  ['"Tencent"', '腾讯'],
    "ByteDance":['"ByteDance"', '字节跳动'],
    "Alibaba":  ['"Alibaba"', '"Aliyun"', '阿里巴巴'],
    "MIT":      ['"MIT"', '"Massachusetts Institute of Technology"', '"CSAIL"'],
    "Stanford": ['"Stanford"', '"Stanford University"'],
    "Microsoft": ['"Microsoft"', '"Microsoft Research"', '"MSR"', '"MSRA"', '"Microsoft Research Asia"'],
    "OpenAI":    ['"OpenAI"'],
    "Anthropic": ['"Anthropic"'],
    "IBM":       ['"IBM"', '"IBM Research"'],
    "Amazon":    ['"Amazon"', '"AWS"', '"Amazon AI"', '"AWS AI"', '"Amazon Science"', '"AWS AI Labs"'],
    "Huawei":    ['"Huawei"', '"Noah\'s Ark Lab"', '华为', '诺亚方舟'],
    "Baidu":     ['"Baidu"', '百度'],
    "SenseTime": ['"SenseTime"', '商汤'],
    "Megvii":    ['"Megvii"', '旷视'],
    "Yitu":      ['"Yitu"', '依图'],
    "AI2":          ['"Allen Institute for AI"', '"Allen Institute"', '"AI2"', '"Allen AI"'],
    "HuggingFace":  ['"Hugging Face"', '"HuggingFace"'],
    "LAION":        ['"LAION"'],
    "EleutherAI":   ['"Eleuther AI"', '"EleutherAI"'],
    "CMU":       ['"CMU"', '"Carnegie Mellon"', '"Carnegie Mellon University"'],
    "Berkeley":  ['"UC Berkeley"', '"UCB"', '"Berkeley"', '"University of California, Berkeley"'],
    "Tsinghua":  ['"Tsinghua"', '清华', '"Tsinghua University"'],
    "PekingU":   ['"Peking University"', '"PKU"', '北京大学'],
    "Oxford":    ['"Oxford"', '"University of Oxford"'],
    "Cambridge": ['"Cambridge"', '"University of Cambridge"'],
    "ETH":       ['"ETH"', '"ETH Zurich"', '"ETH Zürich"'],
    "xAI":        ['"xAI"'],
    "Mistral":    ['"Mistral"', '"Mistral AI"'],
    "Cohere":     ['"Cohere"'],
    "Salesforce": ['"Salesforce"', '"Salesforce Research"'],
    "Adobe":      ['"Adobe"', '"Adobe Research"'],
    "Databricks": ['"Databricks"', '"MosaicML"'],
    "Snowflake":  ['"Snowflake"'],
    "Intel":      ['"Intel"', '"Intel Labs"'],
    "Qualcomm":   ['"Qualcomm"'],
    "Samsung":    ['"Samsung"', '"Samsung Research"'],
    "LG":         ['"LG AI Research"', '"LG"'],
    "NAVER":      ['"NAVER"', '"NAVER AI Lab"'],

    # 中国大厂别名
    "Alibaba":    ['"Alibaba"', '"Aliyun"', '阿里巴巴', '"DAMO"', '达摩院', '"Ant Group"', '蚂蚁集团'],
    "ByteDance":  ['"ByteDance"', '字节跳动', '"ByteDance Seed"', '"Seed"', '"Volcano Engine"', '火山引擎'],
    "Tencent":    ['"Tencent"', '腾讯', '"Tencent AI Lab"', '"Robotics X"'],
    "Baidu":      ['"Baidu"', '百度', '"Baidu Research"', '百度研究院'],
        "ShanghaiAI Lab": [
        '"Shanghai AI Lab"', '"Shanghai AI Laboratory"',
        '"Shanghai Artificial Intelligence Laboratory"',
        "上海人工智能实验室", "上海AI实验室",
    ],
    "MiniMax": ['"MiniMax"', '"MiniMax AI"', "稀宇科技"],
    "ZhipuAI": ['"Zhipu"', '"Zhipu AI"', '"Zhipu.AI"', "智谱", "智谱AI", "智谱华章"],
    "DeepSeek": ['"DeepSeek"', "深度求索"],
    "MoonshotAI": ['"Moonshot AI"', "月之暗面"],
    "Baichuan": ['"Baichuan"', "百川智能"],
    "01AI": ['"01.AI"', '"01AI"', "零一万物"],

    "Mistral": ['"Mistral"', '"Mistral AI"'],
    "Cohere": ['"Cohere"'],
    "xAI": ['"xAI"'],
    "TogetherAI": ['"Together AI"', '"Together.ai"'],
    "StabilityAI": ['"Stability AI"'],
    "Runway": ['"Runway"', '"Runway ML"'],


}

# 只看计算机领域（兜底）
# ARXIV_CATEGORIES = ["cs."]
ARXIV_CATEGORIES = ["cs.", "stat.ML"]


# ===============================
# Topic filter (LLM / Training / Agents)
# ===============================
TOPIC_INCLUDE_PATTERNS = [
    # LLM / foundation models
    r"\blarge language model(s)?\b", r"\bLLM(s)?\b", r"\bfoundation model(s)?\b",
    r"\btransformer(s)?\b", r"\bmixture of experts\b|\bMoE\b",

    # training / post-training
    r"\bpre-?train(ing)?\b", r"\bpost-?train(ing)?\b",
    r"\binstruction tuning\b|\bSFT\b",
    r"\bRLHF\b|\bRLAIF\b|\balignment\b",
    r"\bscaling law(s)?\b", r"\bdistill(ation)?\b",
    r"\bquantiz(ation|e|ing)\b", r"\bLoRA\b|\bPEFT\b",

    # agents
    r"\bagent(s)?\b", r"\bagentic\b",
    r"\btool use\b|\bfunction calling\b",
    r"\bplanning\b", r"\bmulti-?agent\b",
    r"\bReAct\b", r"\bworkflow\b",
    r"\bRAG\b|retrieval augmented generation",

    # ---- 文本/语言建模核心 ----
    r"\blanguage model(ing)?\b", r"\bnext-?token\b", r"\bcausal\b",
    r"\btokenizer\b|\bBPE\b|\bSentencePiece\b",
    r"\bembedding(s)?\b", r"\bin-?context\b|\bICL\b",
    r"\blong context\b|\bcontext window\b",
    r"\battention\b", r"\bKV cache\b",

    # ---- 解码/推理加速（很典型的大模型论文）----
    r"\bdecoding\b", r"\bbeam search\b",
    r"\b(sampling|top-?p|top-?k|temperature)\b",
    r"\bspeculative decoding\b", r"\bmedusa\b|\bLookahead\b",
]



TOPIC_EXCLUDE_PATTERNS = []
TOPIC_EXCLUDE_PATTERNS = [
    r"\brobot(s|ics)?\b", r"\bmanipulation\b", r"\bgrasp(ing)?\b",
    r"\bSLAM\b", r"\bnavigation\b", r"\blocomo(tion)?\b",
    r"\bquadru(ped)?\b", r"\bdrone\b|\bUAV\b",
    r"\bcontrol\b", r"\bmotion planning\b",
]


ENABLE_TOPIC_FILTER = True
