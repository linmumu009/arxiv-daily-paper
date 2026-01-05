# 论文摘要生成器


## 运行流程及参数说明

将 config copy 文件夹名称中的 copy 去掉，然后补充 configDepositary.py文件中的 minerU_Token 和 qwen_api_key 两个参数的值

- minerU_Token可以去 https://mineru.net/apiManage/token 中创建
- qwen_api_key可以去 https://bailian.console.aliyun.com/?spm=a2c4g.11186623.0.0.519511fceUTPZn&tab=model#/api-key 中创建

> python app2.py

会在 dataSelect/summary_gather/YYYY-MM-DD/ 生成摘要文件,请在文件名中带copy的txt文件中删掉自己不想看的论文摘要，保留自己想看的，然后运行下一步

保持Zotero客户端处于打开状态，并点击到你想要导入的目录下，然后运行下面的指令
> python app2_post.py


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

1. 参数解析与入口：主入口 [main](./app2.py#L108-L118) 解析 --limit-files、--decide-concurrency、--org-search-concurrency、--window-hours、--configdepositary（默认 B）
2. 时间窗口计算：在 [main](./app2.py#L121-L126) 使用北京时间“昨天”或按 --window-hours 计算；辅助函数 [beijing_previous_day_window](./filters.py)
3. 基线候选收集：函数 [_collect_baseline_entries](./app2.py#L38-L51) 调用 [iter_recent_cs](./fetch_arxiv.py) 并用 [is_cs](./filters.py)、[in_time_window](./filters.py) 过滤
4. 直搜补齐与合并：函数 [build_candidates_with_fallback](./app2.py#L54-L106) 基于 [group_by_org](./classify.py) 粗分机构，对缺失机构并发调用 [search_by_terms](./fetch_arxiv.py) 合并去重
5. 主题过滤：在 [main](./app2.py#L134-L139) 使用 [is_target_topic](./filters.py) 过滤；规则见 [config.py:L268-L298](./config.py#L268-L298)
6. PDF 缓存：在 [main](./app2.py#L146-L156) 调用 [cache_pdfs](./prefetch.py) 将候选论文 PDF 落盘到 PDF_CACHE_DIR/当日日期
7. 配置读取：A 模式从 mineru.txt/qwen_api.txt/summary_prompt.py 读取；B 模式集中从 [configDepositary.py](./config/configDepositary.py) 读取（参见 [main](./app2.py#L161-L182) 与 [main](./app2.py#L187-L205)）
8. 机构识别：在 on_json 回调中（[app2.py:L216-L223](./app2.py#L216-L223)）提取 JSON 前两页文本并调用 [json2decide.call_qwen_plus](./json2decide.py#L46-L55)；结果写入 [append_result](./json2decide.py#L75-L93)
9. 选择与摘要生成：若 is_large 为真，复制对应 pdf/md 到 dataSelect 并生成摘要（[app2.py:L227-L255](./app2.py#L227-L255)）；摘要生成由 [pdfSummary.make_client](./pdfSummary.py#L34-L39) 与 [pdfSummary.summarize_md](./pdfSummary.py#L52-L68) 完成，B 模式可覆盖 system/user 提示词
10. 并发与 MinerU：使用线程池按 decide_concurrency 并发；通过 [pdf2md.run_local_batch](./pdf2md.py) 驱动 MinerU 生成 md/json 并在 JSON 完成时触发 on_json
11. 产出：生成 dataSelect/summary/YYYY-MM-DD/*.txt 与 dataSelect/summary_gather/YYYY-MM-DD/*.txt，并输出 data_output/decide/YYYY-MM-DD.json 路径


