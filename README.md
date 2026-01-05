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


