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

当用户提供抓取或导出的 Excel/CSV 用户评论文件进行合并或清洗时，必须执行表头标准化：新建一个独立的标准化 Excel 文档，只保留并排序为 `评论日期`、`评论内容`、`产品名`、`电商平台评分`、`性别`、`年龄`、`哈希ID`、`点赞数`、`子评论数/追评数`、`一级评论`、`二级评论`、`三级评论`。昵称、IP 数据以及其它不在保留清单内的列不得进入后续文件。`电商平台评分`、`性别`、`年龄`均为可选保留列：当前只按完全一致的已登记表头复制，源表不存在时保留空列；评分通常为 1–5，但工具不校验、推断或改写评分，性别和年龄也不得推断，三者均不得作为 `哈希ID` 身份来源。该过程必须使用确定性工具，不接入 AI 判断。源表头名称不一致时，只能通过固定别名映射处理；缺少必需标准列的已登记别名时必须停止并让用户确认映射。未登记且不在保留清单内的额外列按删除规则省略，不得猜测为标准列。
CSV 输入必须先通过确定性兼容层读取；CSV 单元格值按文本保留，不得自动推断数字、日期、ID 或时间戳类型。CSV 原文件不得修改，后续标准化、合并和清洗输出仍然生成新的 `.xlsx` 工作簿，并按既有规则导出清洗后的 `.csv`。
CSV 兼容层只按确定性顺序支持 UTF-8、带 BOM 的 UTF-16 和 GB18030；无法解码时必须停止，不得猜测其它编码。
CSV 中以 `=` 开头的值在合并、B站回复前缀处理、标准化和直接清洗生成 XLSX 时必须保持文本类型，不得被 `openpyxl` 提升为公式；XLSX/XLSM 源文件中的真实公式仍按 `data_only=False` 保留。
合并、B站回复前缀处理和表头标准化读取 Excel 时必须保留公式文本（`data_only=False`），不得把没有缓存值的公式单元格静默转换为空值。
若源表头为淘宝 `评论日期与产品`，只能按固定格式拆分：开头的 `YYYY年M月D日`、`YYYY/M/D` 或 `YYYY-M-D` 进入 `评论日期`，日期后可选的 `已购：` 之后的文本进入 `产品名`。若源表已有 `购买产品`、`产品名`、`商品名称` 或 `商品` 列，则直接映射到 `产品名`。`子评论数/追评数` 是标准输出必保留列，但源文件没有对应表头时允许保留空列。不得使用 AI 或语义判断拆分产品名。

当用户后续补充“别名映射表”时，只更新 `config/header-standardizer.json` 中对应标准列的 `aliases`；除非用户明确修改标准输出列，否则不得改动标准输出列顺序和名称。
当前已确认的淘宝别名映射包括：`点赞量` -> `点赞数`，`评论数` -> `子评论数/追评数`，`追评` -> `一级评论`。当前已确认的英文表头映射包括：`timestamp` -> `评论日期`，`content` -> `评论内容`，`like_count` -> `点赞数`。`timestamp` 必须按北京时间（UTC+8）转换为 `YYYY-MM-DD` 日期，只保留年月日，不输出时分秒。`rpid`、`parent_rpid`、`username`、`ip_location` 必须作为 ID、昵称或 IP 相关列丢弃；其中 `parent_rpid` 是父评论 ID，不得映射为 `子评论数/追评数`。这些映射只作为固定别名处理，不允许扩展为 AI 语义判断。
标准化输出中的 `哈希ID` 是确定性伪名化字段，不是法律意义上的匿名化。整张工作表优先选择第一个至少含有一个非空值的已登记稳定账号 ID 列；只有所有已登记账号 ID 列整列为空时，才按 `config/hash-id.json` 中的平台优先级选择显示名兜底。选择必须作用于整张工作表，不得逐行切换；一旦选中的账号 ID 列含有有效值，该列中个别空白行的 `哈希ID` 必须留空，不得回退到该行显示名。
当前精确身份映射为：YouTube 账号 ID 依次为 `author_channel_id`、`authorChannelId`、`Author Channel ID`，显示名依次兜底为 `author`、`author_name`；`YouTube` 与 `YouTube Shorts` 必须归一到同一个 `youtube` 平台命名空间，因此同项目下相同标准化显示名复用同一哈希。小红书账号 ID 为 `用户ID`，兜底为 `用户名称`；B站兜底为 `username`；TikTok 依次兜底为 `用户名`、`昵称`，绝不使用 `用户身份`；淘宝依次兜底为 `用户名称`、`用户名`；京东兜底为 `用户名`。
同一研究项目、同一平台、同一标准化显示名必须得到相同的 64 位小写十六进制哈希，无论已登记源表头是 username 还是 nickname 类字段。不同研究项目、不同平台的哈希必须不同，账号 ID 与显示名哈希必须不同。
显示名关联属于弱伪名化，不是法律意义上的匿名化：昵称变化会拆分同一用户，同名用户可能被合并。不得把显示名哈希解释为稳定账号归属或法律匿名化。
原始账号 ID、用户名、昵称不得进入标准化或清洗输出、日志或摘要；已登记字段即使仅在内存中参与哈希，原始列仍必须省略。评论 ID、父评论 ID、URL、主页链接、IP、来源自带的 `哈希ID`、`用户身份` 和其它含义不明确的字段绝不得作为身份来源。
新增账号 ID 或显示名别名必须先获得用户确认和平台专属证据，且只能加入对应平台和身份类型的固定配置；不得根据字段值或 AI 语义猜测。整个选择、标准化和哈希过程必须由确定性工具完成，不接入 AI。
项目密钥必须由 Windows DPAPI 保护并保存在用户本地项目密钥仓库，不得进入仓库、输出文件、日志或摘要。新增显示名兜底不得改变任何既有合并、清洗、命名、确认或留存规则。
当前已确认的 TikTok/YouTube 平台表头映射包括：`createTime`、`publishedAt`、`published_at`、`publishedTime`、`createdAt`、`created_at`、`date`、`time` -> `评论日期`；`评论`、`text`、`comment`、`commentText`、`comment_text`、`Comment Text`、`message`、`body` -> `评论内容`；`Digg Count`、`likeCount`、`likes`、`diggCount` -> `点赞数`；`回复数`、`replyCount`、`replyCommentTotal`、`replies` -> `子评论数/追评数`；`replyText`、`reply_text` -> `一级评论`。这些平台时间字段必须按确定性规则转换为北京时间 `YYYY-MM-DD`，支持 Unix 秒/毫秒时间戳和 ISO 时间；不得使用 AI 判断。中文 `评论时间` 或 `评论日期` 源列只在值为数字时间戳或带时分秒的日期时间文本时转换为 `YYYY-MM-DD`；纯日期文本保持原值。Relative platform time values such as `1年前`, `9个月前`, `1 year ago`, and `9 months ago` are converted deterministically from the current Beijing date. Relative year values output only `YYYY`; relative month values output only `YYYY-MM`. Relative day/week values output `YYYY-MM-DD`, and missing month/day must not be inferred beyond that fixed granularity. `id`、`comment_id`、`commentId`、`cid`、`uid`、`user_id`、`userId`、`uniqueId`、`author`、`authorName`、`authorDisplayName`、`authorChannelId`、`channelId`、`profileUrl`、`avatar`、`videoId`、`videoUrl`、`url`、`permalink` 必须作为 ID、昵称、账号或链接相关列丢弃。
八位数字 `YYYYMMDD` 必须先按日历日期解析，再判断 Unix 时间戳，避免被转换成 1970 年日期。

B站数据在标准化前必须按固定规则去掉 `回复@xxx：` 或 `回复 @xxx:` 前缀，只保留冒号后的真实评论内容。多文件流程在用户确认合并完成后处理原始合并总表；单文件流程在用户确认只有该文件后处理原始输入。该步骤只处理 `content` 或 `评论内容` 列的固定文本前缀，必须输出新的临时前缀清理表，不得覆盖原始输入或原始合并总表；不得在该步骤中移动回复行或推断父子层级，不得新增层级列，不得删除行。

清洗工具成功生成并核对清洗后的 `.xlsx` 和 `.csv` 后，必须立即删除本次流程生成的合并总表、回复前缀清理表、标准化总表及其摘要文件，默认同时删除清洗日志和清洗摘要，不再额外询问用户是否清理；除非用户在清洗前明确要求保留日志或摘要用于核对，最终默认只保留清洗后的 `.xlsx` 和 `.csv`。删除时只能使用明确传入的中间文件路径，不得扫描文件夹批量删除；不得删除原始输入文件、清洗后的 `.xlsx`、清洗后的 `.csv`，也不得删除用户明确要求保留的日志或摘要。调用清理工具时，必须把所有原始输入文件以及最终清洗后的 `.xlsx`、`.csv` 作为受保护路径传入；默认不得生成额外的清理摘要文件。
中间文件清理至少必须传入一个受保护路径；没有 `--protect` 时工具必须拒绝执行。

当用户提供多个 Excel/CSV 文件并要求合并时，只合并用户明确提供的文件清单，不扫描文件夹内的其它 Excel/CSV 文件。合并过程也必须使用确定性工具处理，不接入 AI 判断或改写数据。
合并输入中出现重复路径时必须停止，不得把同一文件重复追加。所有 CLI 输出默认禁止覆盖已有文件；只有展示确切目标路径并获得用户明确确认后才可传入 `--overwrite`。输出必须先写入目标目录内的临时文件，成功后再原子替换。

合并之前必须先确认研究项目名、产品名和数据来源。研究项目名在同一研究项目中固定复用；用户明确说明新项目时才创建新的项目密钥。文件名格式固定为 `YYYYMMDD_产品名_数据来源_步骤名`，日期使用北京时间（Asia/Shanghai），步骤名固定为 `合并总表`、`标准化总表`、`清洗后总表`。同一流程只确认一次产品名和数据来源；确认后后续文件名只根据步骤自动替换步骤名，不再重复确认命名。

返回任何合并、标准化或清洗文件时，链接文字必须使用实际完整文件名（含扩展名），不得使用“下载合并总表”等泛化标签。
产品名和数据来源只能通过确定性规则获取：文件名、父级文件夹名、已登记的产品表头（`产品名`、`购买产品`、`商品名称`、`商品`）或 `评论日期与产品` 的固定拆分；数据来源只能通过固定关键词如 `淘宝`、`京东`、`小红书`、`抖音`、`微博`、`B站`、`TikTok`、`TTCommentExporter`、`YouTube`、`youtube`、`yt-comments` 获取。YouTube 输入路径含独立目录段 `Shorts` 时，显示数据来源必须优先确定为 `YouTube Shorts评论数据`；该显示命名不改变与长视频共享的 `youtube` 哈希命名空间。若无法唯一确定产品名或数据来源，必须先询问用户，不能用 AI 猜测。命名工具输出 JSON 时必须兼容 Windows 非 UTF-8 控制台和包含表情符号的文件名，不得因控制台编码失败而改变或中断命名识别。
若存在多个待处理原始文件，必须在展示产品名、数据来源、合并 `.xlsx`、标准化 `.xlsx`、清洗 `.xlsx` 和清洗 `.csv` 四个输出文件名时一次性询问“请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。”用户确认后才允许执行合并。若当前只收到 1 个文件，必须先询问“当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。”只有在用户确认确实只有一个文件后，才允许跳过合并步骤并直接进入标准化。

多文件流程必须先合并原始输入文件，输出一个新的原始合并总表；合并完成后先返回原始合并总表，并确认“是否已经提供并合并完所有需要合并的表格”。用户确认所有需要合并的表格都已合并后，才允许对该原始合并总表执行表头标准化，输出一个新的标准化合并总表。原始输入文件和原始合并总表都不得被标准化步骤改写。

表头标准化必须不只改表头文字，而是把匹配到的源表头及其下面整列数据一起移动到标准列位置；只有不在保留清单内的列才会从标准化输出中省略。

当用户要求“合并后再清洗”时，必须先合并原始输入文件，合并完成后暂停并确认“是否已经提供并合并完所有需要合并的表格”。用户确认所有需要合并的表格都已合并后，才允许对该原始合并总表执行表头标准化。标准化完成后必须把标准化后的表格返回给用户确认；用户明确确认标准化表格可以进入清洗流程后，才允许询问或确认 KOL 清理词并进入清洗流程。

合并必须输出到一个新建的独立 Excel 文档/工作簿文件作为总表，不是在原 Excel 文档里新建子表/Sheet，也不能把合并结果写回任何原始输入表格。合并完成后必须先把新合并表返回给用户，再等待用户确认是否进行标准化。

当用户提供一个或多个 KOL 清理词时，不能立刻执行清洗，必须先确认“是否已经提供完成所有 KOL 清理词”。用户明确确认后，才允许把这些清理词传入工具并执行清洗。

当用户给出 Excel/CSV 文件并说“清洗这个文件”“数据清洗”“处理抓取导出的评论表格”等类似请求时，按以下固定流程执行。

## 固定对话流程

1. 如果用户已经提供了 `.xlsx`、`.xlsm` 或 `.csv` 文件路径，直接进入下一步；如果没有文件，先让用户提供文件。
2. 单文件流程也必须先确认产品名、数据来源和输出命名；若无法唯一确定，先询问用户，不能猜测。
3. 若当前只收到 1 个文件，必须询问“当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。”
4. 用户确认确实只有一个文件后，才允许跳过合并并执行表头标准化。
5. 标准化后的表格返回给用户确认后，才允许询问 KOL 清理词。
   - 如果没有，让用户回复“没有”。
   - 如果有，让用户一次性发来所有清理词。
6. 如果用户提供一个或多个 KOL 清理词，必须再确认“是否已经提供完成所有 KOL 清理词”；用户确认后才允许清洗。
7. 用户确认清理词后，直接运行本项目已有工具：
   - `tools/strip_bilibili_reply_prefixes.py`（仅 B站合并表在标准化前需要）
   - `tools/standardize_excel_headers.py`
   - `tools/clean_excel_comments.py`
   - `tools/cleanup_intermediate_outputs.py`（清洗成功生成 `.xlsx` 和 `.csv` 后立即清理中间产物）
   - 不要让用户手动输入命令。
   - 不要要求用户打开命令行。
8. 如果用户说没有清理词，运行工具时不要传入任何 `--clean-word` 参数。
9. 如果用户提供清理词，每个清理词都作为一个独立的 `--clean-word` 参数传入。
10. 清洗完成并自动清理本轮中间产物后，只返回清洗后的 `.xlsx` 和 `.csv` 文件链接；只有用户在清洗前明确要求保留日志或摘要用于核对时，才保留并返回这些文件。

## 处理边界

- 原始 Excel/CSV 文件不得修改，必须另存为新文件。
- 单文件清洗时，表头标准化必须先于清洗执行；多文件流程中，必须先合并原始输入文件，再对合并总表执行表头标准化。标准化后的清洗按表头“评论内容”定位评论列。
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
