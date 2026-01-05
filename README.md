# 论文摘要生成器


## 运行流程及参数说明

### 需修改和补充的文件

> 共两部分：config/configDepositary.py | config.py

** config/configDepositary.py **
将 config copy 文件夹名称中的 copy 去掉，然后补充 configDepositary.py文件中的 minerU_Token 和 qwen_api_key 两个参数的值

- minerU_Token可以去 https://mineru.net/apiManage/token 中创建
- qwen_api_key可以去 https://bailian.console.aliyun.com/?spm=a2c4g.11186623.0.0.519511fceUTPZn&tab=model#/api-key 中创建


** config.py **
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

1. 参数解析与入口：主入口 main 负责解析参数，并驱动后续所有流程
    > 对应代码文件：app2.py
    > 主要函数：[main](./app2.py#L108-L159)

2. 计算“昨天窗口”：决定本次抓取论文的时间范围
    > 对应代码文件：app2.py / utils.py / filters.py
    > 主要函数：[now_local](./utils.py#L6-L7)、[beijing_previous_day_window](./filters.py#L6-L20)
    > 入口代码片段：[main](./app2.py#L120-L127)

3. 构建候选论文列表（基线 + 直搜补齐）：先按 cs./stat.ML 拉取近期论文作为基线，再对缺失机构做 per-org 直搜补齐并合并去重（内部有多线程并发执行）
    > 对应代码文件：app2.py / fetch_arxiv.py / classify.py / config.py
    > 主要函数：[_collect_baseline_entries](./app2.py#L38-L51)、[build_candidates_with_fallback](./app2.py#L54-L106)
    > 数据抓取接口：[iter_recent_cs](./fetch_arxiv.py#L184-L190)、[search_by_terms](./fetch_arxiv.py#L192-L209)
    > 机构粗分函数：[group_by_org](./classify.py#L25-L31)

4. 主题过滤（可选）：对候选集按关键词规则做筛选（默认开启）
    > 对应代码文件：app2.py / filters.py / config.py
    > 入口代码片段：[main](./app2.py#L135-L139)
    > 主要函数：[is_target_topic](./filters.py#L36-L45)
    > 规则配置：[config.py:L268-L298](./config.py#L268-L298)

5. 缓存候选 PDF：将候选论文的 PDF 下载/缓存到本地（避免后续处理中重复下载），使用 requests.Session 顺序遍历；本步骤本身不做显式线程池，但整体运行在单进程中
    > 对应代码文件：app2.py / prefetch.py
    > 入口代码片段：[main](./app2.py#L147-L159)
    > 主要函数：[cache_pdfs](./prefetch.py#L24-L63)

6. 读取运行配置（A/B 模式）：决定 MinerU Token、Qwen API Key、摘要/机构识别提示词从哪里读取
    > 对应代码文件：app2.py / config/configDepositary.py
    > 入口代码片段：[main](./app2.py#L161-L205)
    > B 模式集中配置：[configDepositary.py](./config/configDepositary.py)

7. PDF → MD/JSON（MinerU 批处理）：对缓存 PDF 调用 MinerU 转换；
    > 原理说明：将缓存的 PDF 列表按 batch_size（默认 10）切分为多个小批次；对每一批，先统一向 MinerU 申请上传任务，再用线程池按 upload_concurrency（默认 10）在批内并发上传；随后按批次轮询 MinerU 处理结果，下载对应 zip，并为该批中的每篇论文写出 md/json 文件并触发 on_json 回调。
    > 举例说明：例如有 100 篇论文，先按 batch_size=10 切成 10 批；对每一批，先向 MinerU 申请上传任务，然后用线程池按 upload_concurrency=10 在批内并发上传这最多 10 篇论文；等这一批在 MinerU 侧处理完成后，一次性下载对应 zip，解出 10 个 md/json 文件，并依次触发 on_json 进入后续流程，再继续处理下一批。
    > 对应代码文件：app2.py / pdf2md.py
    > 入口代码片段：[main](./app2.py#L257-L279)
    > 主要函数：[run_local_batch](./pdf2md.py#L215-L245)
    > 并发/批处理参数（由 app2 固定传入）：batch_size=10（每次提交 PDF 数量）、upload_concurrency=10（上传并发）
    > 输出：data/md 与 data/json
    > 输出data/md : 论文经过解析后的md格式原文件
    > 输出data/json : 论文经过解析后的json格式原文件
       



8. on_json 回调（机构识别 + decide 聚合）：对 JSON 前两页文本做机构判断，看是否为大机构（is_large=true），并把结果追加写入 data_output/decide/YYYY-MM-DD.json
    > 对应代码文件：app2.py / json2decide.py
    > 回调入口：[on_json/job](./app2.py#L213-L219)
    > 文本抽取：[load_first_pages_text](./json2decide.py#L24-L43)
    > 机构判断：[call_qwen_plus](./json2decide.py#L46-L72)
    > 结果落盘：[append_result](./json2decide.py#L75-L93)

9. 大机构论文的“拷贝 + 摘要生成”：当 is_large=true 时，将对应 pdf/md 复制到 dataSelect，并生成摘要写入 dataSelect/summary，同时追加到 dataSelect/summary_gather
    > 对应代码文件：app2.py / pdfSummary.py
    > 入口代码片段：[on_json/job](./app2.py#L220-L253)
    > 摘要生成：[make_client](./pdfSummary.py#L34-L39)、[summarize_md](./pdfSummary.py#L52-L68)

10. 等待并收尾：等待所有并发任务结束，确保摘要与聚合文件写入完成
    > 对应代码文件：app2.py


