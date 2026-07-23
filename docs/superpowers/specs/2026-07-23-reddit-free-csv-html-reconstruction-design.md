# Reddit 免费 CSV 与 HTML 确定性重建设计

日期：2026-07-23  
状态：已完成对话设计确认，等待书面规格审阅

## 1. 目标

创建一个独立的确定性工具，将评论抓取工具导出的免费 Reddit CSV 与用户保存的完整 Reddit HTML 合并，生成一份包含帖子信息、评论点赞数、评论层级和父子关系的结构化原始数据表。

工具不使用 AI，不根据评论语义推断层级，不调用第三方付费插件，也不修改输入文件。

## 2. 与现有清洗流程的边界

本工具生成的是“结构化原始表”，不是项目既有的九列标准化表或清洗结果。

- 原始 Reddit 作者名、评论 ID 和父评论 ID可以存在于本工具输出中。
- 若后续进入项目既有标准化/清洗流程，必须继续执行项目现有的表头保留、账号哈希、昵称删除和清洗规则。
- 本工具不得修改 `skills/product-user-comment-data-merge-cleaning/`、`config/header-standardizer.json` 或 `config/comment-cleaner.json` 的基础规则。

## 3. 输入

正式运行只需要两个输入：

1. 免费抓取 CSV：
   - 文件开头包含 `title`、`body`、`url` 元数据行；
   - 空行后包含评论表头；
   - 评论表头至少包含 `author_name`、`date_time`、`comment`、`comment_url`；
   - `upvote_number` 允许存在但为空。
2. 完整 Reddit HTML：
   - 用户在评论已尽量全部展开后保存；
   - 必须包含与免费 CSV 评论 URL 对应的评论节点；
   - 评论节点必须提供可确定的评论 ID、父对象 ID 和层级；
   - 点赞数允许因 Reddit 未公开而缺失。

`付费插件获取.csv` 只用于开发期校验前 20 条结果，不是正式运行输入，也不能成为生产逻辑依赖。

## 4. 确定性读取规则

### 4.1 CSV

- 复用 `tools/csv_excel_compat.py` 的固定编码顺序：UTF-8、带 BOM 的 UTF-16、GB18030。
- 所有单元格按文本读取，不自动推断数字、日期、ID 或公式。
- 从开头逐行读取元数据，直到识别到评论表头。
- `title`、`body`、`url` 必须各出现一次；重复或缺失时停止。
- 评论表头必须包含全部必需列；未登记列允许忽略。
- `comment_url` 必须通过固定 URL 结构 `/comment/<comment_id>/` 提取评论 ID。
- 评论 URL 缺失、格式不合法或评论 ID 重复时停止。

### 4.2 HTML

- 使用 Python 标准库确定性解析，不引入 AI。
- 只读取 Reddit 评论节点和帖子节点的固定属性/固定子节点。
- 评论 ID来自 `thingid`、等价已登记属性或固定 Reddit comment URL。
- 父对象 ID来自 `parentid` 或等价已登记属性。
- 层级来自 `depth` 或等价已登记属性。
- 评论点赞数来自固定评分属性或固定评分子节点。
- 帖子作者、总点赞数和总评论数来自帖子节点固定属性/固定子节点。
- 未登记的 HTML 结构不得靠正文含义猜测。
- HTML 中的推广内容不会主动进入输出：程序只处理免费 CSV 已登记的评论 ID。

## 5. 合并键和一致性

唯一主键为 `Comment ID`：

1. 从免费 CSV 的 `comment_url` 提取 ID。
2. 从 HTML 评论节点提取 ID。
3. 仅按完全一致的 ID 合并。

不得使用以下方式作为正式合并键：

- 评论正文模糊匹配；
- 作者名相似匹配；
- 时间近似匹配；
- AI 语义判断；
- 评论顺序猜测。

付费样本校验可以按作者、时间、正文和顺序生成测试断言，但不能进入生产合并逻辑。

## 6. 完整性规则

- 免费 CSV 中每条评论都必须在 HTML 中找到相同评论 ID。
- 每条匹配评论必须取得 `Parent ID` 和 `Thread Level`。
- 任一评论缺少 HTML 节点、父 ID 或层级时，程序停止，不生成结果文件，并列出缺失评论 ID。
- 评论点赞数若 Reddit 页面明确未显示，可以留空；这不阻止输出。
- 帖子作者、总点赞数和总评论数若 HTML 缺失，必须由用户通过明确 CLI 参数提供，否则停止。
- 免费 CSV 的评论正文、作者、精确时间和评论 URL 是内容来源；HTML 不得覆盖这些字段。
- HTML 只补充层级、父 ID、点赞数和缺失的帖子统计字段。

## 7. 输出数据契约

每条评论占一行。帖子级字段重复写入每一行。

固定列顺序：

1. `Title`
2. `Post Body`
3. `Post URL`
4. `Post Author`
5. `Post Score`
6. `Post Comment Count`
7. `Author`
8. `Time`
9. `Score`
10. `Thread Level`
11. `Is Reply`
12. `Comment`
13. `Comment URL`
14. `Comment ID`
15. `Parent ID`

字段规则：

- `Title`、`Post Body`、`Post URL` 来自免费 CSV。
- `Post Author`、`Post Score`、`Post Comment Count` 来自 HTML 或明确 CLI 备用值。
- `Author`、`Time`、`Comment`、`Comment URL` 来自免费 CSV。
- `Score`、`Thread Level`、`Parent ID` 来自 HTML。
- `Is Reply` 在 `Thread Level = 0` 时为 `No`，其它层级为 `Yes`。
- 评论顺序完全保留免费 CSV 的原始顺序。
- 缺失的可选点赞数输出空文本，不输出 `None`、`null` 或推断值。

## 8. 输出文件

工具同时生成内容相同的：

- `.xlsx`
- UTF-8 BOM `.csv`

规则：

- 默认输出到用户明确指定的目标路径或目录。
- 禁止默认覆盖已有文件。
- 只有用户展示确切目标路径并明确传入 `--overwrite` 时允许覆盖。
- 两个输出先写入目标目录内的临时文件，全部成功后再原子替换。
- 原始免费 CSV 和 HTML 永不修改。
- 以 `=`、`+`、`-` 或 `@` 开头的文本在 XLSX 中必须保持文本类型，在 CSV 中按原始文本输出。
- 不额外生成包含作者名或评论正文的日志/摘要文件。

## 9. CLI

工具文件：

`tools/reconstruct_reddit_comments.py`

正式参数：

```text
--free-csv <path>
--html <path>
--output-xlsx <path>
--output-csv <path>
--post-author <text>          可选，仅在 HTML 缺失时使用
--post-score <text>           可选，仅在 HTML 缺失时使用
--post-comment-count <text>   可选，仅在 HTML 缺失时使用
--overwrite                   可选，默认关闭
```

程序成功时只打印输入路径、输出路径、评论总数、缺失点赞数和 HTML 匹配数，不打印作者名或评论正文。

## 10. 当前样本

开发与测试样本：

- `C:\Users\Eddie.J.Lu\Downloads\免费数据.csv`
- `C:\Users\Eddie.J.Lu\Downloads\付费插件获取.csv`

当前帖子在 HTML 缺失帖子统计字段时可显式使用：

```text
Post Author = exotic123567
Post Score = 267
Post Comment Count = 65
```

这些值只属于当前帖子，不能写死到通用程序中。

## 11. 测试策略

自动化测试必须覆盖：

- 免费 CSV 的元数据区和评论区解析；
- 多行帖子正文和多行评论；
- UTF-8、UTF-16 BOM、GB18030；
- 必需元数据缺失和重复；
- 评论表头缺失；
- 评论 URL 提取 ID；
- 重复和非法评论 ID；
- HTML 评论节点、父 ID、层级、点赞数；
- HTML 帖子作者、总点赞数和总评论数；
- HTML 未公开评论点赞数时留空；
- 免费 CSV 评论缺少 HTML 匹配时拒绝输出；
- HTML 缺少父 ID或层级时拒绝输出；
- 评论顺序保持；
- `Is Reply` 推导；
- XLSX/CSV 字段顺序一致；
- Unicode、表情、逗号、引号和换行；
- 公式样文本保持文本；
- 默认拒绝覆盖；
- 原子输出失败时不留下半成品。

开发期校验：

- 用 `付费插件获取.csv` 核对前 20 条的 `Score`、`Thread Level`、`Is Reply`；
- 核对只能作为测试，不能增加生产依赖。

## 12. 验收条件

满足以下全部条件才能声明工具完成：

- 工具不调用 AI、LLM 或外部分析服务；
- 正式运行只依赖免费 CSV 和完整 HTML；
- 付费 CSV 不是生产必需输入；
- 全部评论按 ID 精确匹配；
- 帖子标题和正文来自免费 CSV并完整保留；
- 点赞、层级和父关系来自 HTML 固定字段；
- 缺失关键层级数据时停止而不是猜测；
- 输出 `.xlsx` 与 `.csv` 行数、列顺序和内容一致；
- 输入文件保持原样；
- 所有自动化测试通过；
- 使用真实 HTML 后完成一次端到端验收。
