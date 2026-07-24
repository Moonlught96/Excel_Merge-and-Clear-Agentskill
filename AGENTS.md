## Agent Skill Packaging Standard

本项目以后创建或修改任何 Agent Skill，必须遵守以下标准；不得只创建一份孤立的 `SKILL.md`：

1. **创建完整的 Skill 文件夹结构。** 每个 Skill 至少包含 `SKILL.md`、`agents/openai.yaml`、`references/`、`scripts/` 和 `assets/`；需要执行配置时同时包含 `config/`。
2. **`SKILL.md` 必须写清楚 Skill 职责、触发场景、执行步骤、输出标准。** `description` 只描述触发条件并以 `Use when...` 开头；入口文档保持简洁，通过链接按需加载详细资料，不得把所有规则堆积在入口中。
3. **`references/` 放入所有已确认的格式要求和内容标准。** 工作流、数据契约、字段映射、阈值、固定规则、命名、留存和扩展政策必须有明确归属；不得因整理或拆分文档而省略已确认规则。
4. **可自动化的步骤必须写入 `scripts/`。** 数据处理必须由确定性脚本执行，不得让 Agent 用自然语言临时重写处理逻辑；脚本应使用相对 Skill 的资源路径并提供可验证的命令入口。
5. **`assets/` 放入需要复用的模板文件。** 对话确认模板、规则扩展表、输出模板或其它可复用静态资源必须作为实际文件保存，不得只留在聊天记录中。
6. **Skill 必须可移植。** 将完整 Skill 文件夹单独复制到另一个目录或 Agent 环境后，不依赖原项目根目录也能独立运行；不得使用只在原仓库成立的隐藏路径。
7. **Skill 必须可验证。** 创建或修改 Skill 时必须检查目录完整性、入口章节、references 规则覆盖、脚本/配置一致性，并执行单独复制后的独立运行测试。测试通过前不得宣称封装完成。

以上标准是本项目的系统级项目指令。后续所有 Skill 创建、整理和扩展默认执行此标准，除非用户明确修改其中某一条。

# 产品用户评论数据合并与清洗固定流程

本项目的基础清洗规则以 `skills/product-user-comment-data-merge-cleaning/` 中的 `SKILL.md`、`references/` 和 `config/` 为准。后续新增功能时，不得修改其中的基础规则；只有用户明确指出要修改某一条规则时，才允许同步修改 Skill、配置、代码和测试。

当用户提供抓取或导出的 Excel/CSV 用户评论文件进行合并或清洗时，必须执行表头标准化：新建一个独立的标准化 Excel 文档，只保留并排序为 `评论日期`、`评论内容`、`产品名`、`电商平台评分`、`用户属性`、`哈希ID`、`点赞数`、`子评论数/追评数`、`一级评论`、`二级评论`、`三级评论`。昵称、IP 数据以及其它不在保留清单内的列不得进入后续文件。`电商平台评分`、`用户属性`均为可选保留列：评分只按完全一致的已登记表头复制，源表不存在时保留空列；评分通常为 1–5，除已确认的平台预处理固定解析外，工具不校验、推断、四舍五入或改写评分。`用户属性`逐行按固定规则生成：优先保留已登记源表头 `用户属性` 的非空值；该值为空或不存在时，依次读取已登记的 `性别`、`年龄`，去除首尾空白后用一个空格拼接非空值；两者都没有时保留空列。不得推断、补全或语义改写用户属性；`性别`、`年龄`不再作为输出表头，且评分和用户属性均不得作为 `哈希ID` 身份来源。该过程必须使用确定性工具，不接入 AI 判断。源表头名称不一致时，只能通过固定别名映射处理；缺少必需标准列的已登记别名时必须停止并让用户确认映射。未登记且不在保留清单内的额外列按删除规则省略，不得猜测为标准列。
CSV 输入必须先通过确定性兼容层读取；CSV 单元格值按文本保留，不得自动推断数字、日期、ID 或时间戳类型。CSV 原文件不得修改，后续标准化、合并和清洗输出仍然生成新的 `.xlsx` 工作簿，并按既有规则导出清洗后的 `.csv`。
CSV 兼容层只按确定性顺序支持 UTF-8、带 BOM 的 UTF-16 和 GB18030；无法解码时必须停止，不得猜测其它编码。
CSV 中以 `=` 开头的值在合并、B站回复前缀处理、标准化和直接清洗生成 XLSX 时必须保持文本类型，不得被 `openpyxl` 提升为公式；XLSX/XLSM 源文件中的真实公式仍按 `data_only=False` 保留。
合并、B站回复前缀处理和表头标准化读取 Excel 时必须保留公式文本（`data_only=False`），不得把没有缓存值的公式单元格静默转换为空值。
若源表头为淘宝 `评论日期与产品`，只能按固定格式拆分：开头的 `YYYY年M月D日`、`YYYY/M/D` 或 `YYYY-M-D` 进入 `评论日期`，日期后可选的 `已购：` 之后的文本进入 `产品名`。若源表已有 `购买产品`、`产品名`、`商品名称` 或 `商品` 列，则直接映射到 `产品名`。若该来源产品字段不存在或该单元格为空，则只能使用本轮命名确认中用户明确给出的产品名，通过 `tools/standardize_excel_headers.py --product-name` 原样填入；源字段非空时不得覆盖，且不得根据评论内容、文件内容或 AI 推断产品名。`子评论数/追评数` 是标准输出必保留列，但源文件没有对应表头时允许保留空列。不得使用 AI 或语义判断拆分产品名。

当用户后续补充“别名映射表”时，只更新 `config/header-standardizer.json` 中对应标准列的 `aliases`；除非用户明确修改标准输出列，否则不得改动标准输出列顺序和名称。
当前已确认的淘宝别名映射包括：`点赞量` -> `点赞数`，`评论数` -> `子评论数/追评数`，`追评` -> `一级评论`。当前已确认的英文表头映射包括：`timestamp` -> `评论日期`，`content` -> `评论内容`，`like_count` -> `点赞数`。`timestamp` 必须按北京时间（UTC+8）转换为 `YYYY-MM-DD` 日期，只保留年月日，不输出时分秒。`rpid`、`parent_rpid`、`username`、`ip_location` 必须作为 ID、昵称或 IP 相关列丢弃；其中 `parent_rpid` 是父评论 ID，不得映射为 `子评论数/追评数`。这些映射只作为固定别名处理，不允许扩展为 AI 语义判断。
标准化输出中的 `哈希ID` 是确定性伪名化字段，不是法律意义上的匿名化。整张工作表优先选择第一个至少含有一个非空值的已登记稳定账号 ID 列；只有所有已登记账号 ID 列整列为空时，才按 `config/hash-id.json` 中的平台优先级选择显示名兜底。选择必须作用于整张工作表，不得逐行切换；一旦选中的账号 ID 列含有有效值，该列中个别空白行的 `哈希ID` 必须留空，不得回退到该行显示名。
当前精确身份映射为：YouTube 账号 ID 依次为 `author_channel_id`、`authorChannelId`、`Author Channel ID`，显示名依次兜底为 `author`、`author_name`；`YouTube` 与 `YouTube Shorts` 必须归一到同一个 `youtube` 平台命名空间，因此同项目下相同标准化显示名复用同一哈希。小红书账号 ID 为 `用户ID`，兜底为 `用户名称`；B站兜底为 `username`；TikTok 依次兜底为 `用户名`、`昵称`，绝不使用 `用户身份`；淘宝依次兜底为 `用户名称`、`用户名`；京东兜底为 `用户名`；亚马逊没有已登记稳定账号 ID，仅以预处理临时列 `名称` 作为显示名兜底；Twitter/X 使用同一个 `twitter` 平台命名空间，临时 `Twitter用户ID` 是稳定账号 ID，只有该整列均为空时才以临时 `Twitter昵称` 作为显示名兜底，绝不逐行回退。
同一研究项目、同一平台、同一标准化显示名必须得到相同的 64 位小写十六进制哈希，无论已登记源表头是 username 还是 nickname 类字段。不同研究项目、不同平台的哈希必须不同，账号 ID 与显示名哈希必须不同。
显示名关联属于弱伪名化，不是法律意义上的匿名化：昵称变化会拆分同一用户，同名用户可能被合并。不得把显示名哈希解释为稳定账号归属或法律匿名化。
原始账号 ID、用户名、昵称不得进入标准化或清洗输出、日志或摘要；已登记字段即使仅在内存中参与哈希，原始列仍必须省略。评论 ID、父评论 ID、URL、主页链接、IP、来源自带的 `哈希ID`、`用户身份` 和其它含义不明确的字段绝不得作为身份来源。
新增账号 ID 或显示名别名必须先获得用户确认和平台专属证据，且只能加入对应平台和身份类型的固定配置；不得根据字段值或 AI 语义猜测。整个选择、标准化和哈希过程必须由确定性工具完成，不接入 AI。
项目密钥必须由 Windows DPAPI 保护并保存在用户本地项目密钥仓库，不得进入仓库、输出文件、日志或摘要。新增显示名兜底不得改变任何既有合并、清洗、命名、确认或留存规则。
当前已确认的 TikTok/YouTube 平台表头映射包括：`createTime`、`publishedAt`、`published_at`、`publishedTime`、`createdAt`、`created_at`、`date`、`time` -> `评论日期`；`评论`、`text`、`comment`、`commentText`、`comment_text`、`Comment Text`、`message`、`body` -> `评论内容`；`Digg Count`、`likeCount`、`likes`、`diggCount` -> `点赞数`；`回复数`、`replyCount`、`replyCommentTotal`、`replies` -> `子评论数/追评数`；`replyText`、`reply_text` -> `一级评论`。这些平台时间字段必须按确定性规则转换为北京时间 `YYYY-MM-DD`，支持 Unix 秒/毫秒时间戳和 ISO 时间；不得使用 AI 判断。中文 `评论时间` 或 `评论日期` 源列只在值为数字时间戳或带时分秒的日期时间文本时转换为 `YYYY-MM-DD`；纯日期文本保持原值。Relative platform time values such as `1年前`, `9个月前`, `1 year ago`, and `9 months ago` are converted deterministically from the current Beijing date. Relative year values output only `YYYY`; relative month values output only `YYYY-MM`. Relative day/week values output `YYYY-MM-DD`, and missing month/day must not be inferred beyond that fixed granularity. `id`、`comment_id`、`commentId`、`cid`、`uid`、`user_id`、`userId`、`uniqueId`、`author`、`authorName`、`authorDisplayName`、`authorChannelId`、`channelId`、`profileUrl`、`avatar`、`videoId`、`videoUrl`、`url`、`permalink` 必须作为 ID、昵称、账号或链接相关列丢弃。
八位数字 `YYYYMMDD` 必须先按日历日期解析，再判断 Unix 时间戳，避免被转换成 1970 年日期。

B站数据在标准化前必须按固定规则去掉 `回复@xxx：` 或 `回复 @xxx:` 前缀，只保留冒号后的真实评论内容。多文件流程在用户确认合并完成后处理原始合并总表；单文件流程在用户确认只有该文件后处理原始输入。该步骤只处理 `content` 或 `评论内容` 列的固定文本前缀，必须输出新的临时前缀清理表，不得覆盖原始输入或原始合并总表；不得在该步骤中移动回复行或推断父子层级，不得新增层级列，不得删除行。

标准化前的 `tools/preprocess_platform_comments.py` 是平台预处理分流器：平台规则必须保存在 `config/platform-preprocessing.json` 的独立固定配置中，不得把新的平台特有原始表头、拼接或解析规则混入通用 `config/header-standardizer.json`。分流器只根据完整且有序的已登记 `header_signature` 选择一个平台配置或其中的具名变体；不得根据文件名、内容、语言、单个相似表头、AI、语义或模糊匹配猜测平台。已登记配置与源表头不完全相等时，包括多列、少列、重复列或顺序不同，必须停止并报告 `No configured platform signature matched`，不得套用其它平台规则。未登记的既有平台继续使用已确认的通用固定别名规则，除非用户明确确认迁移。当前亚马逊配置只在原始表头依次完整等于 `标题`、`标题链接`、`图片`、`aprofile_链接`、`名称`、`aiconalt`、`查看`、`状态`、`查看1`、`asizebase`、`crhelpfultext`、`asizebase_链接`、`asizebase2` 时运行：`标题` 与 `查看1` 用固定顺序和 `\n\n` 合并为评论内容；`查看` 按固定 `YYYY年M月D日在…发布评论` 解析为 `YYYY-MM-DD`；`aiconalt` 的固定 `X 颗星，最多 5 颗星` 解析为 1–5 范围内的原始分数字符串；`asizebase` 的固定 `N 个人发现此评论有用` 解析为点赞数；`名称` 只在临时文件内用于亚马逊显示名哈希；`crhelpfultext`、链接、图片、状态和其它原始字段不进入预处理输出。乐天市场使用同一个 `rakuten` 分流配置中的五个精确具名变体：`reviewer-title-body-review-date`、`reviewer-date-body-title`、`title-review-date-body-reviewer`、`poster-title-body-review-date`、`reviewer-name-title-content`；每个变体都必须完整命中其登记的有序表头。乐天的 `レビュータイトル` 与 `レビュー本文` 或 `レビュー内容` 按固定标题后正文及 `\n\n` 拼接；`投稿日` 或 `レビュー投稿日` 的固定日期格式转换为 `YYYY-MM-DD`；`評価`原样映射至`电商平台评分`；`参考になった数`的固定`N人`格式转换为点赞数；`レビュアー属性`只保留固定`男性/女性`和数字年龄标记（包括`70代以上`）；`レビュー投稿者`、`投稿者名`或`レビュアー名`只输出为临时`乐天市场昵称`以用于显示名哈希，其中精确的`購入者さん`必须置空且不生成`哈希ID`。`注文日`、`カラー`及其它乐天原始字段不得输出。解析不匹配的非空原值必须按各注册操作的固定规则原样保留或为空，绝不得猜测或丢失。预处理必须输出新的临时 `.xlsx` 和摘要，不得覆盖输入；其规则与执行过程必须纯工具完成，不接入 AI。

Twitter/X 使用独立 `twitter` 分流器，且仅当完整有序原始表头精确等于 `id`、`created_at`、`full_text`、`media`、`screen_name`、`name`、`profile_image_url`、`user_id`、`in_reply_to`、`retweeted_status`、`quoted_status`、`media_tags`、`favorite_count`、`retweet_count`、`bookmark_count`、`quote_count`、`reply_count`、`views_count`、`favorited`、`retweeted`、`bookmarked`、`url`、`metadata` 时运行。它只能固定复制 `created_at` -> 临时`评论日期`、`full_text` -> 临时`评论内容`、`favorite_count` -> 临时`点赞数`、`reply_count` -> 临时`子评论数/追评数`、`user_id` -> 临时`Twitter用户ID`、`screen_name` -> 临时`Twitter昵称`；其它字段不得进入临时输出。Twitter/X 标准化审查通过并经用户确认后，必须先询问本轮保留关键词，用户提供后必须再询问“是否已经提供完成所有 Twitter/X 保留关键词？你确认后我将执行关键词筛选，再进入通用 KOL 清理词与清洗流程。”；确认后只允许由 `tools/filter_comments_by_keywords.py` 用 Unicode `casefold()` 的字面包含规则保留“评论内容”命中任一关键词的整行，不命中的整行删除。该筛选绝不翻译、扩词、模糊匹配、推断产品关联或接入 AI；筛选临时 `.xlsx` 与 `.keyword-filter.summary.json` 必须在最终清洗成功后作为显式中间产物清理，之后才进入既有 KOL 清理词和通用清洗流程。

当同一已确认平台注册分流的多文件批次原始合并因表头不同抛出 `HeaderMismatchError` 时，只有在每个输入工作表都完整命中该平台注册的一个具名精确变体、且这些变体的临时输出列完全同名同序时，才允许改用 `tools/preprocess_platform_comments.py --merge-registered-variants --platform <已确认分流器>`。该工具按各文件的精确变体先做固定预处理、再按用户提供顺序写入一个新的“平台预处理合并总表”；原始输入不改写，未匹配任一签名时不得产生部分输出、不得回退到其他平台或变体、不得使用 AI 判断。这个平台预处理合并总表就是本轮合并确认节点；用户确认合并完整后直接进入通用表头标准化，不得再次运行平台预处理器。相同原始表头的批次仍必须走既有原始合并流程，不能把本例外用于绕过表头一致性检查。

每次标准化完成后、返回用户确认之前，必须运行 `tools/audit_standardized_comments.py`，并传入标准化输入源文件。审查只做确定性结构核验：每个工作表是否具有锁定的完整表头及顺序、是否存在重复或原始身份表头、每个非空 `哈希ID` 是否为 64 位小写十六进制、工作表名称/顺序以及源文件与标准化输出的数据行数是否一致。审查报告只能包含路径、工作表名、表头、计数和问题代码，不得包含评论文本或原始身份值。任一核验失败时，必须停止，不得把标准化表格送入用户确认、KOL 清理词或清洗流程；审查通过后仍必须保留原有“标准化后的表格已生成，请确认是否可以进入清洗流程”的用户确认门槛。该审查也必须完全由工具完成，不接入 AI。

清洗工具成功生成并核对清洗后的 `.xlsx` 和 `.csv` 后，必须立即删除本次流程生成的合并总表、回复前缀清理表、平台预处理表、Twitter/X 关键词筛选表及其摘要、标准化总表、标准化审查报告及其摘要文件，默认同时删除清洗日志和清洗摘要，不再额外询问用户是否清理；除非用户在清洗前明确要求保留日志、摘要或审查报告用于核对，最终默认只保留清洗后的 `.xlsx` 和 `.csv`。删除时只能使用明确传入的中间文件路径，不得扫描文件夹批量删除；不得删除原始输入文件、清洗后的 `.xlsx`、清洗后的 `.csv`，也不得删除用户明确要求保留的日志或摘要。调用清理工具时，必须把所有原始输入文件以及最终清洗后的 `.xlsx`、`.csv` 作为受保护路径传入；默认不得生成额外的清理摘要文件。
中间文件清理至少必须传入一个受保护路径；没有 `--protect` 时工具必须拒绝执行。

当用户提供多个 Excel/CSV 文件并要求合并时，只合并用户明确提供的文件清单，不扫描文件夹内的其它 Excel/CSV 文件。合并过程也必须使用确定性工具处理，不接入 AI 判断或改写数据。
合并输入中出现重复路径时必须停止，不得把同一文件重复追加。所有 CLI 输出默认禁止覆盖已有文件；只有展示确切目标路径并获得用户明确确认后才可传入 `--overwrite`。输出必须先写入目标目录内的临时文件，成功后再原子替换。

合并之前必须先确认研究项目名、产品名和数据来源。研究项目名在同一研究项目中固定复用；用户明确说明新项目时才创建新的项目密钥。文件名格式固定为 `YYYYMMDD_产品名_数据来源_步骤名`，日期使用北京时间（Asia/Shanghai），步骤名固定为 `合并总表`、`标准化总表`、`清洗后总表`。同一流程只确认一次产品名和数据来源；确认后后续文件名只根据步骤自动替换步骤名，不再重复确认命名。

返回任何合并、标准化或清洗文件时，链接文字必须使用实际完整文件名（含扩展名），不得使用“下载合并总表”等泛化标签。
产品名和数据来源只能通过确定性规则获取：文件名、父级文件夹名、已登记的产品表头（`产品名`、`购买产品`、`商品名称`、`商品`）或 `评论日期与产品` 的固定拆分；数据来源只能通过固定关键词如 `淘宝`、`京东`、`亚马逊`、`Amazon`、`amazon`、`小红书`、`抖音`、`微博`、`B站`、`TikTok`、`TTCommentExporter`、`Twitter`、`twitter`、`YouTube`、`youtube`、`yt-comments` 获取。亚马逊输入路径含已登记地区关键词时，`亚马逊日本`、`Amazon Japan` 或 `amazon.co.jp` 必须显示为 `亚马逊日本评论数据`；`亚马逊美国`、`Amazon USA`、`Amazon US` 或 `amazon.com` 必须显示为 `亚马逊美国评论数据`；未带地区关键词时才显示为 `亚马逊评论数据`。Twitter/Twitter 小写路径关键词固定显示为 `Twitter评论数据`，计划分流器固定为 `twitter`，但显示命名不等于通过分流校验，仍必须完整命中 Twitter/X 已登记有序表头。日本和美国都必须进入同一个 `amazon` 平台预处理分流器，地区显示命名不得作为平台预处理匹配证据，也不得创建另一套标准化规则；若同一批输入同时命中多个亚马逊地区，数据来源必须判为歧义并要求用户确认。YouTube 输入路径含独立目录段 `Shorts` 时，显示数据来源必须优先确定为 `YouTube Shorts评论数据`；该显示命名不改变与长视频共享的 `youtube` 哈希命名空间。若无法唯一确定产品名或数据来源，必须先询问用户，不能用 AI 猜测。命名工具输出 JSON 时必须兼容 Windows 非 UTF-8 控制台和包含表情符号的文件名，不得因控制台编码失败而改变或中断命名识别。
若存在多个待处理原始文件，必须在展示产品名、数据来源、计划平台预处理分流器及其“完整有序表头指纹校验”状态、合并 `.xlsx`、标准化 `.xlsx`、清洗 `.xlsx` 和清洗 `.csv` 四个输出文件名时一次性询问“请确认以上产品名、数据来源、平台预处理分流和文件命名是否正确，并确认是否可以进入合并流程。”用户确认后才允许执行合并。确认分流器不等于跳过校验；合并后实际预处理仍必须通过完整有序表头指纹，否则停止。若当前只收到 1 个文件，必须先询问“当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。”只有在用户确认确实只有一个文件后，才允许跳过合并步骤并直接进入标准化。

多文件流程必须先合并原始输入文件；对同表头批次，输出一个新的原始合并总表，合并完成后先返回原始合并总表，并确认“是否已经提供并合并完所有需要合并的表格”。若原始合并因表头不一致安全停止，且满足已登记平台注册混合精确变体的例外条件，则只能使用上述 `--merge-registered-variants` 输出一个新的平台预处理合并总表并在同一确认节点返回它。用户确认所有需要合并的表格都已合并后，才允许对原始合并总表先运行适用的 B站前缀清理和/或精确平台注册预处理，或对平台预处理合并总表直接执行表头标准化，输出一个新的标准化合并总表。标准化后必须自动审查通过，才可返回标准化表供用户确认。原始输入文件和原始合并总表都不得被后续步骤改写；平台预处理合并总表同样不得被后续步骤改写。

表头标准化必须不只改表头文字，而是把匹配到的源表头及其下面整列数据一起移动到标准列位置；只有不在保留清单内的列才会从标准化输出中省略。

当用户要求“合并后再清洗”时，对同表头批次必须先合并原始输入文件，合并完成后暂停并确认“是否已经提供并合并完所有需要合并的表格”。只有已确认平台注册的混合精确变体才可在原始合并安全停止后走平台预处理后合并例外。用户确认所有需要合并的表格都已合并后，才允许对原始合并总表运行适用的确定性平台预处理和表头标准化，或对平台预处理合并总表直接表头标准化；标准化完成后必须先通过自动审查，才把标准化后的表格返回给用户确认；用户明确确认标准化表格可以进入清洗流程后，若为 `twitter` 分流必须先完成 Twitter/X 保留关键词提供、完整性确认和确定性筛选，再允许询问或确认 KOL 清理词并进入通用清洗流程。

合并必须输出到一个新建的独立 Excel 文档/工作簿文件作为总表，不是在原 Excel 文档里新建子表/Sheet，也不能把合并结果写回任何原始输入表格。合并完成后必须先把新合并表返回给用户，再等待用户确认是否进行标准化。

当用户提供一个或多个 KOL 清理词时，不能立刻执行清洗，必须先确认“是否已经提供完成所有 KOL 清理词”。用户明确确认后，才允许把这些清理词传入工具并执行清洗。

当用户给出 Excel/CSV 文件并说“清洗这个文件”“数据清洗”“处理抓取导出的评论表格”等类似请求时，按以下固定流程执行。

## 固定对话流程

1. 如果用户已经提供了 `.xlsx`、`.xlsm` 或 `.csv` 文件路径，直接进入下一步；如果没有文件，先让用户提供文件。
2. 单文件流程也必须先确认产品名、数据来源和输出命名；若无法唯一确定，先询问用户，不能猜测。
3. 若当前只收到 1 个文件，必须询问“当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。”
4. 用户确认确实只有一个文件后，才允许跳过合并，并先执行适用的固定 B站前缀清理和/或精确平台注册预处理，再执行表头标准化与自动审查。
5. 标准化自动审查通过后，标准化后的表格返回给用户确认；若为 `twitter` 分流，必须先询问“请提供本轮 Twitter/X 评论保留关键词。仅保留‘评论内容’包含任一关键词的整行数据；请一次性提供所有关键词。”，收到一个或多个关键词后再询问“是否已经提供完成所有 Twitter/X 保留关键词？你确认后我将执行关键词筛选，再进入通用 KOL 清理词与清洗流程。”，确认后用 `tools/filter_comments_by_keywords.py` 执行筛选；其他平台才直接询问 KOL 清理词。
   - 对非 Twitter/X 平台，标准化后的表格返回给用户确认后，才允许询问 KOL 清理词。
   - 如果没有，让用户回复“没有”。
   - 如果有，让用户一次性发来所有清理词。
6. 如果用户提供一个或多个 KOL 清理词，必须再确认“是否已经提供完成所有 KOL 清理词”；用户确认后才允许清洗。
7. 用户确认清理词后，直接运行本项目已有工具：
   - `tools/strip_bilibili_reply_prefixes.py`（仅 B站合并表在标准化前需要）
   - `tools/preprocess_platform_comments.py`（仅完整命中已登记平台签名时，在标准化前需要；已确认平台注册混合精确变体在原始合并安全停止后必须传入 `--merge-registered-variants`）
   - `tools/standardize_excel_headers.py`
   - `tools/audit_standardized_comments.py`（标准化后必须通过，才可进入用户确认与清洗）
   - `tools/filter_comments_by_keywords.py`（仅 `twitter` 分流在标准化审查及用户确认后、KOL 清理词前使用；每个确认的保留词传入一个独立 `--keep-keyword` 参数）
   - `tools/clean_excel_comments.py`
   - `tools/cleanup_intermediate_outputs.py`（清洗成功生成 `.xlsx` 和 `.csv` 后立即清理中间产物）
   - 不要让用户手动输入命令。
   - 不要要求用户打开命令行。
8. 如果用户说没有清理词，运行工具时不要传入任何 `--clean-word` 参数。
9. 如果用户提供清理词，每个清理词都作为一个独立的 `--clean-word` 参数传入。
10. 清洗完成并自动清理本轮中间产物后，只返回清洗后的 `.xlsx` 和 `.csv` 文件链接；只有用户在清洗前明确要求保留日志或摘要用于核对时，才保留并返回这些文件。

## 处理边界

- 原始 Excel/CSV 文件不得修改，必须另存为新文件。
- 单文件清洗时，适用的平台预处理、表头标准化与标准化自动审查必须先于清洗执行；多文件流程中，必须先合并原始输入文件；同表头批次再对原始合并总表执行适用的平台预处理、表头标准化与自动审查。已确认平台注册的混合精确变体只可在原始合并安全停止后先做平台预处理后合并，再直接标准化与自动审查。`twitter` 分流的标准化输出经用户确认后必须先进行本轮确认保留词的确定性行筛选，然后才进入 KOL 和通用清洗；其他平台标准化后的清洗按表头“评论内容”定位评论列。
- 表格内容清洗必须是纯工具规则处理，不能接入 AI 判断某条评论是否应该删除。
- AI 只负责调用工具、检查输出文件是否生成、返回结果路径。
- 不要基于语义、情绪、质量、疑似广告等主观判断删除评论。
- 不要添加用户未确认的额外清理词。
- 不要使用旧的八爪鱼 RPA 画布或不存在的 CLI。

## 当前工具规则

- 支持 `.xlsx`、`.xlsm` 和 `.csv`。
- CSV 输入必须先通过确定性兼容层读取；CSV 单元格值按文本保留，不自动推断数字、日期、ID 或时间戳类型。
- 旧的直接清洗模式默认第 3 列是评论列；标准化后的文件按“评论内容”表头定位评论列。
- 默认第 1 行是表头，从第 2 行开始清洗。
- 删除首尾空白后长度小于等于 7 的中文主评论。
- Chinese comments delete by character length; non-Chinese comments delete by deterministic word count.
- Deterministic script classification gives Japanese Kana, Korean Hangul, Thai, and Devanagari precedence over Han characters for both length and fixed-word rules. Han-only text is treated as Chinese because distinguishing Han-only Japanese from Chinese would require semantic inference.
- Non-Chinese comments with four or fewer words are deleted.
- For unspaced non-Chinese scripts, only very short text with four or fewer characters is deleted by the short-text rule.
- Pure numeric comments keep the legacy seven-character threshold for backward compatibility.
- 删除完全等于占位文案的评论。
- 删除包含用户提供 KOL 清理词的评论。
- 固定清理词只能追加，不能覆盖或移除原有固定词“链接”。
- When adding a fixed delete word later, add confirmed equivalents for Chinese, English, Japanese, Korean, Spanish, Thai, and Hindi where applicable.
- Fixed delete words must be isolated by deterministic script group. Chinese comments only use Chinese fixed words; Japanese, Korean, Thai, and Hindi comments only use their respective script groups. English and Spanish share the Latin-script group because deterministic script inspection cannot distinguish them reliably. Language-neutral URL markers `http://` and `https://` apply to all groups.
- Latin-script fixed words must match complete lexical boundaries. Matching remains case-insensitive where configured, but `test` may match `test` or `TEST` and must not match `TESTV`, `contest`, or `testing`.
- 完整固定清理词清单以 `config/comment-cleaner.json` 为准；当前配置覆盖中文、英文、日文、韩文、西语、泰文和印地语。
- 删除包含任一固定清理词的整行评论。当前固定清理词包括：“链接”、“凑字数”、“水经验”、“赚积分”、“为了金币”、“赚硬币”、“赚京豆”、“淘气值”、“为了评论而评论”、“混个脸熟”、“完成任务”、“代下”、“代买”、“内部券”、“加微”、“加v”、“私聊我”、“主页看”、“点击链接”、“http://”、“https://”、“第一”、“打卡”、“路过”、“来了”、“冒泡”、“占座”、“测试”、“test”、“无”、“无内容”、“略”、“暂无评价”、“蹲”、“蹲一个”、“求链接”、“求分享”、“多少钱”、“怎么卖”、“啥牌子”、“什么牌子”、“求品牌”、“求私”、“加群”、“裙内”、“互赞”、“互粉”、“互关”、“回关”、“秒回”、“交朋友”、“リンク”、“プロフィール見て”、“プロフ見て”、“DMして”、“フォロー返し”、“相互フォロー”、“テスト”、“内容なし”、“評価なし”、“コメント稼ぎ”、“링크”、“맞팔”、“테스트”、“내용 없음”。
- “加v”以及英文固定清理词必须按大小写不敏感方式匹配，例如“加v”和“加V”都删除；英文固定清理词包括：“link in bio”、“click link”、“click the link”、“check my profile”、“see my profile”、“visit my profile”、“dm me”、“message me”、“follow me”、“follow back”、“follow for follow”、“sub4sub”、“sub for sub”、“subscribe to my channel”、“earn coins”、“free coins”、“for coins”、“comment for points”、“promo code”、“coupon code”、“discount code”、“whatsapp”、“telegram”、“first”、“test”、“n/a”、“no content”、“no comment”、“nothing to say”。
- 完全不含中文字符且命中随机英文/数字堆砌阈值的评论必须整行删除；该规则只能使用确定性正则和阈值，不得接入 AI 或语义判断。
- 删除同一工作表内重复评论，默认保留最后一条。
- 对 `一级评论`、`二级评论`、`三级评论` 的重复内容只清空重复子评论单元格，默认保留最后一次出现；不得删除整行，不得修改主评论列 `评论内容`。
- 对子评论列删除首尾空白后长度小于等于 5 的内容只清空对应单元格；不得删除整行，不得修改主评论列 `评论内容`。
- 导出清洗后的 `.xlsx`、首个工作表 `.csv`、删除日志 `.deletions.csv`、摘要 `.summary.json`。

## 标准回复方式

当用户只说“清洗这个文件”且还没说明清理词时，只回复：

```text
是否有 KOL 清理词？没有就回复“没有”；有的话请一次性发来所有清理词。
```

当处理完成时，回复保持简短，只给结果文件和必要说明。
