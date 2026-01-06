# 论文摘要生成器


## 运行流程及参数说明

### 需修改和补充的文件

> 共两部分：config/configDepositary.py | config.py

**config/configDepositary.py**

将 config copy 文件夹名称中的 copy 去掉，然后补充 configDepositary.py 文件中的 minerU_Token 和 qwen_api_key 两个参数的值

- minerU_Token 可以去 https://mineru.net/apiManage/token 中创建
- qwen_api_key 可以去 https://bailian.console.aliyun.com/?spm=a2c4g.11186623.0.0.519511fceUTPZn&tab=model#/api-key 中创建
- 机构识别模型配置：包括机构识别所用的大模型接口地址和模型名称
- 摘要生成模型配置：包括摘要生成所用的大模型接口地址和模型名称
- 提示词配置：集中管理机构识别和摘要生成使用的系统提示词和可选用户前缀，控制输出风格与内容结构【system_prompt、user_prompt、org_system_prompt】


**config.py**

ORG_SEARCH_TERMS 这个为具体的搜索机构列表
> 具体可见README0.md中的说明（原始作者的 readme ）

### 运行指令

> python app2.py

会在 dataSelect/summary_gather/YYYY-MM-DD/ 生成摘要文件,请在文件名中带copy的txt文件中删掉自己不想看的论文摘要，保留自己想看的，然后运行下一步

保持Zotero客户端处于打开状态，并点击到你想要导入的目录下，然后运行下面的指令
> python app2_post.py


参数运行示例：（如没有特殊参数要求，可以直接运行）
> python app2.py --limit-files 10 --window-hours 72

表示：
- 限制处理的 PDF 数量为 10 篇
- 时间窗口小时数为 72 小时（表示从“昨天”开始的 72 小时内的论文）


app2.py
|参数名称|值类型|默认值|说明|
|--|--|--|--|
|--limit-files|int|0|限制处理的 PDF 数量（0 表示不限）|
|--decide-concurrency|int|10|机构判断与摘要生成的并发线程数|
|--org-search-concurrency|int|6|机构直搜并发数（per-org 搜索）|
|--window-hours|int|0|时间窗口小时数；0 表示使用北京时间“昨天”窗口|
|--configdepositary|A/B|B|配置来源：A=文本文件（mineru.txt/qwen_api.txt/summary_prompt.py），B=集中配置（config/configDepositary.py）|

app2_post.py
|参数名称|值类型|默认值|说明|
|--|--|--|--|
|--date|str|""|指定日期（YYYY-MM-DD）；为空自动使用当天|
|--gather-root|str|dataSelect/summary_gather|汇总摘要根目录|
|--summary-root|str|dataSelect/summary|单篇摘要根目录|
|--pdf-root|str|dataSelect/pdf|选择后的 PDF 根目录|
|--md-root|str|dataSelect/md|选择后的 MD 根目录|
|--out-root|str|selectPapers/PDF|输出 PDF 目标目录|
|--out-md-root|str|selectPapers/md|输出 MD 目标目录|
|--push-zotero|flag|True|完成后是否导入 Zotero（桌面 Connector）|
|--configdepositary|A/B|B|配置来源（与 app2 保持一致；本脚本当前不直接读取配置）|

app2_post_later.py
|参数名称|值类型|默认值|说明|
|--|--|--|--|
|--date|str|""|指定日期（YYYY-MM-DD）；为空自动使用当天|
|--md-root|str|selectPapers/md|MD 输入根目录|
|--out-root|str|SelectPaperRewrite|改写输出根目录|
|--model|str|claude-sonnet-4-5-all|改写模型名称|
|--concurrency|int|8|改写并发数|
|--overwrite|flag|False|是否覆盖已存在改写输出|


## app2.py 代码流程解析

### app2.py 相关目录结构（示意）

```text
项目根目录
├─ config/                             # 集中配置目录（原 config copy，重命名后）
│   └─ configDepositary.py            # B 模式：MinerU Token、大模型 API Key、模型参数与提示词配置
│
├─ data/                               # MinerU 解析输出（由 pdf2md.py 写入）
│   ├─ md/
│   │   └─ YYYY-MM-DD/*.md            # 每篇论文解析后的 md 原文
│   └─ json/
│       └─ YYYY-MM-DD/*.json          # 每篇论文解析后的 json（第 8 步机构识别的输入）
│
├─ data_output/
│   └─ decide/
│       └─ YYYY-MM-DD.json            # 机构识别“决定文件”：记录每篇论文的机构与 is_large 标记
│
├─ dataSelect/                         # 为“大机构论文 + 摘要”准备的工作区
│   ├─ md/
│   │   └─ YYYY-MM-DD/*.md            # 大机构论文拷贝后的 md（从 data/md 中筛选复制）
│   ├─ pdf/
│   │   └─ YYYY-MM-DD/*.pdf           # 大机构论文拷贝后的 pdf（从 PDF 缓存目录中筛选复制）
│   ├─ summary/
│   │   └─ YYYY-MM-DD/*.txt           # 单篇摘要（每篇论文生成一个 txt）
│   └─ summary_gather/
│       └─ YYYY-MM-DD.txt             # 当天所有摘要的汇总文件 + 一份 “YYYY-MM-DD copy.txt”
│
├─ selectPapers/                       # 最终“精选论文”输出目录（供 Zotero 等工具导入）
│   ├─ PDF/
│   │   └─ *.pdf                      # 准备导入的 pdf（来自 dataSelect/pdf）
│   └─ md/
│       └─ *.md                       # 与之对应的 md（来自 dataSelect/md）
│
├─ PDF_CACHE_DIR/YYYY-MM-DD/*.pdf     # PDF 缓存目录（由配置决定）
│   
│
├─ app2.py                            # 主入口：串起所有步骤（时间窗口 → 抓取 → 缓存 → MinerU → 机构识别 → 拷贝 + 摘要）
│
├─ config.py                          # 通用配置：机构搜索关键词、主题过滤规则、PDF 缓存目录、HTTP 超时等
│
├─ fetch_arxiv.py                     # 第 3 步：封装 arXiv API，提供基线列表与 per-org 直搜（iter_recent_cs、search_by_terms）
├─ filters.py                         # 第 2、4 步：时间窗口转换与主题过滤（beijing_previous_day_window、in_time_window、is_target_topic）
├─ classify.py                        # 第 3 步：基于正则的机构匹配与分组，用于确定哪些机构需要 per-org 直搜
├─ prefetch.py                        # 第 5 步：根据 arXiv ID 下载并缓存 PDF 到 PDF_CACHE_DIR/YYYY-MM-DD（cache_pdfs）
├─ utils.py                           # 第 2 步：提供本地时间工具 now_local，用于构造“昨天窗口”等
│
├─ pdf2md.py                          # 第 7 步：调用 MinerU 将缓存 PDF 按批次解析为 md/json（run_local_batch）
├─ json2decide.py                     # 第 8 步：从 json 中抽取前几页文本并调用大模型做机构识别（load_first_pages_text、call_qwen_plus）
├─ pdfSummary.py                      # 第 9 步：基于 md 调用大模型生成摘要（summarize_md），写单篇与汇总摘要
└─ pdfSelect.py                       # 第 10 步：在交互模式下再次筛选、再次摘要（app2 尾部通过 sys.argv 调用）
```

![app2.py 目录结构示意图](<carbon (2).png>)

![项目主目录结构示意图](<ray-so-export.png>)

1. 参数解析与入口：主入口 main 负责解析参数，并驱动后续所有流程

    ```text
    对应代码文件：
        - app2.py 负责解析命令行参数，并按配置串联后续所有步骤
    主要函数：
        - main（app2.py#L108-L298）
    入口说明：
        - 支持的参数：--limit-files、--decide-concurrency、--org-search-concurrency、--window-hours、--configdepositary
        - 将参数归一化为内部变量，并在后续步骤中统一使用
    ```

2. 计算“昨天窗口”：决定本次抓取论文的时间范围

    ```text
    对应代码文件：
        - app2.py 负责读取 window-hours 参数，决定使用“昨天窗口”还是“最近 N 小时窗口”
        - utils.py 负责返回带 LOCAL_TZ 的当前本地时间【now_local()】
        - filters.py 负责将本地时间转换为用于抓取 arXiv 的 UTC 时间窗口，并提供基于时间窗口的过滤函数用于后续筛选论文【in_time_window】
    主要函数：
        - now_local（utils.py#L6-L7）
        - beijing_previous_day_window（filters.py#L6-L20）
        - in_time_window（filters.py#L22-L24）
    入口代码片段：main（app2.py#L120-L127）
    时间窗口策略：
        - window-hours > 0：使用“当前 UTC 往前 N 小时”的滑动窗口
        - 否则：使用基于北京时间“昨天”的整日窗口，并向后错开 8 小时以覆盖完整发布批次
    ```

3. 构建候选论文列表（基线 + 直搜补齐）：先按 cs./stat.ML 拉取近期论文作为基线，再对缺失机构做 per-org 直搜补齐并合并去重（内部有多线程并发执行）

    ```text
    对应代码文件：
        - app2.py 负责在给定时间窗口内先收集一批“最近论文”的基础列表，作为后续筛选与补充搜索的起点，并根据配置决定是否对部分或全部机构再执行一次按机构关键字的补充搜索（FILL_MISSING_BY_ORG、ALWAYS_PER_ORG_SEARCH）
        - fetch_arxiv.py 负责封装 arXiv API：先按分类拉取近期论文列表（iter_recent_cs），再按机构关键词做 per-org 搜索以补齐特定机构的论文（search_by_terms），最终返回可用于后续下载的论文元数据
        - classify.py 负责基于机构匹配规则对基线论文做机构粗分，以确定需要 per-org 搜索的机构集合（INSTITUTIONS_PATTERNS）
        - config.py 负责提供机构搜索关键词列表（ORG_SEARCH_TERMS）、机构匹配规则（INSTITUTIONS_PATTERNS）以及 per-org 搜索分页参数（PER_ORG_SEARCH_LIMIT_PAGES、PER_ORG_SEARCH_PAGE_SIZE）
    主要函数：
        - _collect_baseline_entries（app2.py#L38-L51）
        - build_candidates_with_fallback（app2.py#L54-L106）
    数据抓取接口：
        - iter_recent_cs（fetch_arxiv.py#L184-L189）
        - search_by_terms（fetch_arxiv.py#L192-L209）
    机构粗分函数：
        - group_by_org（classify.py#L25-L31）
    并发策略：
        - main 中通过 org-search-concurrency 参数设置 per-org 搜索的并发线程数（build_candidates_with_fallback._org_search_concurrency）
        - build_candidates_with_fallback 内部使用线程池并发执行每个机构的搜索任务，并对返回结果按时间窗口过滤后合并去重【ThreadPoolExecutor、search_by_terms】
    ```

4. 主题过滤（可选）：对候选集按关键词规则做筛选（默认开启）

    ```text
    对应代码文件：
        - app2.py 负责根据主题过滤开关决定是否启用过滤，并对候选列表做一次筛选（ENABLE_TOPIC_FILTER）
        - filters.py 负责实现基于正则的主题判断函数，用于判断论文是否命中目标主题（is_target_topic）
        - config.py 负责提供主题包含/排除规则（TOPIC_INCLUDE_PATTERNS、TOPIC_EXCLUDE_PATTERNS）以及主题过滤开关（ENABLE_TOPIC_FILTER）
    入口代码片段：main（app2.py#L135-L139）
    主要函数：is_target_topic（filters.py#L36-L45）
    规则配置（均定义在 config.py 中）：
        - TOPIC_INCLUDE_PATTERNS：主题包含规则列表，用于判断“想要哪些类型的论文”
        - TOPIC_EXCLUDE_PATTERNS：主题排除规则列表，用于过滤掉“不想要的论文”
        - ENABLE_TOPIC_FILTER：是否启用主题过滤的开关
    ```

5. 缓存候选 PDF：将候选论文的 PDF 下载/缓存到本地（避免后续处理中重复下载），使用 requests.Session 顺序遍历；本步骤本身不做显式线程池，但整体运行在单进程中

    ```text
    对应代码文件：
        - app2.py 负责根据时间窗口与 limit-files 参数确定需要缓存的候选集合，并构造当日日期子目录（limit-files）
        - prefetch.py 负责根据 entry 计算 arXiv ID，拼接 PDF 下载链接，将文件缓存到 PDF 缓存目录下的日期子目录（PDF_CACHE_DIR）
        - fetch_arxiv.py 通过 get_arxiv_id 提供统一的 arXiv ID 抽取逻辑
        - config.py 负责提供 PDF 缓存根目录（PDF_CACHE_DIR）以及 HTTP 超时配置（CONNECT_TIMEOUT_SEC、READ_TIMEOUT_SEC）
    入口代码片段：main（app2.py#L147-L159）
    主要函数：
        - cache_pdfs（prefetch.py#L24-L63）
        - get_arxiv_id（fetch_arxiv.py#L218-L220）
    缓存结果：
        - 返回 {arxiv_id: 本地 PDF 路径} 映射，并在后续步骤中用于定位和拷贝 PDF 文件
    输入：
        - 来源：上一步构建的候选论文元数据列表（包含 arXiv ID 和 PDF 链接）
    输出：
        - 本地缓存 PDF：PDF_CACHE_DIR/YYYY-MM-DD/*.pdf（YYYY-MM-DD 为本次运行日期）
    ```

6. 读取运行配置（A/B 模式）：决定 MinerU Token、Qwen API Key、摘要/机构识别提示词从哪里读取

    ```text
    对应代码文件：
        - app2.py 负责根据 --configdepositary 参数选择配置来源，并加载 MinerU Token、Qwen API Key 以及提示词（--configdepositary）
        - config/configDepositary.py（B 模式）集中存放 MinerU Token（minerU_Token）、Qwen API Key（qwen_api_key）、摘要系统提示词（system_prompt、user_prompt）、大模型机构识别系统提示词（org_system_prompt）
        - config 目录中的文本文件（A 模式）：mineru.txt / qwen_api.txt
    入口代码片段：
        - MinerU Token 加载与校验：main（app2.py#L161-L182）
        - Qwen API Key 与提示词加载：main（app2.py#L184-L203）
    模式说明：
        - B 模式（默认）：从 config/configDepositary.py 统一读取全部配置，便于集中管理
        - A 模式：从文本文件 mineru.txt / qwen_api.txt 读取 Token 与 API Key，提示词使用代码内置默认值
    ```

7. PDF → MD/JSON（MinerU 批处理）：对缓存 PDF 调用 MinerU 转换；

    ```text
    原理说明：将缓存的 PDF 列表按 batch_size（默认 10）切分为多个小批次；
    对每一批，先统一向 MinerU 申请上传任务，再用线程池按 upload_concurrency（默认 10）在批内并发上传；
    随后按批次轮询 MinerU 处理结果，下载对应 zip，并为该批中的每篇论文写出 md/json 文件并触发 on_json 回调。

    举例说明：例如有 100 篇论文，先按 batch_size=10 切成 10 批；
    对每一批，先向 MinerU 申请上传任务，然后用线程池按 upload_concurrency=10 在批内并发上传这最多 10 篇论文；
    等这一批在 MinerU 侧处理完成后，一次性下载对应 zip，解出 10 个 md/json 文件，
    并依次触发 on_json 进入后续流程，再继续处理下一批。

    触发时机说明：
        - 先完成所有候选 PDF 的本地缓存（步骤 5），得到完整的 pdfs 列表
        - 然后一次性将 pdfs 列表传入 run_local_batch，由 MinerU 以“小批次”方式按 batch_size 逐批处理
        - 每处理完一批，就为这一批中的每个 PDF 写出对应的 md/json 文件，并立即触发 on_json 回调，而不是等所有批次全部完成后再统一触发

    对应代码文件：app2.py / pdf2md.py
    入口代码片段：main（app2.py#L257-L279）
    主要函数：run_local_batch（pdf2md.py#L215-L245）
    并发/批处理参数（由 app2 固定传入）：batch_size=10（每次提交 PDF 数量）、upload_concurrency=10（上传并发）

    输入：
        - PDF 输入：PDF_CACHE_DIR/YYYY-MM-DD/*.pdf（由步骤 5 缓存得到的全部 PDF 列表，经 limit-files 截断）
    输出：
        - data/md 与 data/json
        - 输出 data/md ：论文经过解析后的 md 格式原文件（data/md/YYYY-MM-DD/*.md）
        - 输出 data/json ：论文经过解析后的 json 格式原文件（data/json/YYYY-MM-DD/*.json），同时作为 on_json 回调的输入
    ```
       



8. 机构识别与决定文件写入（on_json 回调）：对每个 JSON 的前两页文本调用大模型识别机构，判断是否为大机构（is_large=true），并把结果追加写入 data_output/decide/YYYY-MM-DD.json

    ```text
    概念说明：
        - 每当 MinerU 在第 7 步为某个 PDF 写出一个 JSON 文件时，就会立即调用一个“机构识别 + 决策更新”的回调函数，对这篇论文做机构判断并更新决定文件【on_json】
        - 如果模型判断该论文属于“大机构”（is_large=true），后续会在第 9 步对这篇论文执行拷贝与摘要生成
    对应代码文件：
        - app2.py 负责接收每个 JSON 文件的路径，提交机构识别与后续处理任务到线程池执行，并将识别结果追加写入决定文件【on_json、job、ThreadPoolExecutor】
        - json2decide.py 负责从 JSON 文件中抽取前几页文本并调用 Qwen 模型做机构识别，返回包含机构信息与是否大机构标记的结果对象【load_first_pages_text、call_qwen_plus、append_result】
    回调入口：
        - 第 7 步在写出每个 JSON 文件后调用机构识别回调，触发本步骤的处理【on_json、job（app2.py#L213-L256）】
    文本抽取：
        - 从 JSON 文件中抽取前两页正文和列表内容，作为机构识别模型的输入【load_first_pages_text（json2decide.py#L24-L43）】
    机构判断：
        - 调用指定模型，根据抽取的文本判断论文所属机构，并标记是否为大机构【call_qwen_plus（json2decide.py#L46-L72）、model=qwen-plus】
    结果落盘：
        - 将每篇论文的机构识别结果累积追加到 data_output/decide/YYYY-MM-DD.json 中，作为后续筛选和审阅的依据【append_result（json2decide.py#L75-L93）】
    输入：
        - JSON 输入：data/json/YYYY-MM-DD/*.json（由第 7 步 MinerU 解析生成）
    输出：
        - 决定文件：data_output/decide/YYYY-MM-DD.json（每天一份，包含当日所有论文的机构识别结果）
    并发说明：
        - 使用线程池按 decide-concurrency 指定的并发度同时处理多个 JSON 文件，run_local_batch 每生成一个 JSON 就提交一个机构识别任务【ThreadPoolExecutor、decide-concurrency】
    ```

9. 大机构论文的“拷贝 + 摘要生成”：当 is_large=true 时，将对应 pdf/md 复制到 dataSelect，并生成摘要写入 dataSelect/summary，同时追加到 dataSelect/summary_gather

    ```text
    对应代码文件：
        - app2.py 负责对被判定为大机构的论文，根据识别结果里的文件名字段的值反查对应的 pdf/md，将其复制到 dataSelect/md 与 dataSelect/pdf，并在此基础上触发单篇摘要生成与汇总写入【on_json、job】
        - pdfSummary.py 提供创建大模型客户端和生成摘要的函数，用于基于 md 文本调用 Qwen 模型生成摘要（带示例提示词）【make_client、summarize_md】
        - config/configDepositary.py（B 模式）提供摘要系统提示词和用户提示前缀，用于控制摘要风格（system_prompt、user_prompt）
    入口代码片段：
        - 处理单个机构识别结果并执行拷贝与摘要生成的回调逻辑【on_json、job（app2.py#L220-L253）】
    摘要生成：
        - make_client（pdfSummary.py#L34-L39）
        - summarize_md（pdfSummary.py#L51-L70）
    输出说明：
        - 单篇摘要：dataSelect/summary/YYYY-MM-DD/{论文名}.txt
        - 汇总摘要：追加写入 dataSelect/summary_gather/YYYY-MM-DD.txt
    ```

10. 等待并收尾：等待所有并发任务结束，确保摘要与聚合文件写入完成

    ```text
    对应代码文件：
        - app2.py
    主要行为：
        - 等待所有机构识别和摘要相关的后台任务执行完成，并关闭线程池【futures、ex.shutdown】
        - 通过临时修改命令行参数依次调用筛选脚本和摘要脚本，在交互式模式下支持再次筛选与再次生成摘要【sys.argv、pdfSelect.main、pdfSummary.main】
        - 将当天的汇总摘要文件 summary_gather/YYYY-MM-DD.txt 复制一份为同目录下的 “YYYY-MM-DD copy.txt”，用于手工删除不感兴趣的摘要
    收尾代码片段：main（app2.py#L281-L305）
    ```


