# Workflow Confirmation Template

## Confirmation Integrity

The confirmation text below must be sent in the current conversation and answered explicitly by the user. Do not replace a response with a CLI flag, a JSON/state file, an old log, a historical confirmation, or a request to process quickly.

## X Data-Type Gate

Use this before output naming, merge planning, or preprocessing whenever the user identifies the supplied data as X/Twitter. Do not infer the type from filenames, headers, row values, or content.

```text
检测到 X/Twitter 数据，请选择本轮数据类型：
[1] 推文：使用既有 `twitter` 推文分流和推文保留关键词流程。
[2] 评论：使用独立的 X 评论分流，不套用推文分流或推文保留关键词流程。

请回复“推文”或“评论”。
```

Only `推文` selects the registered `twitter` profile. `评论` selects the separate registered `twitter-comments` profile. Both profiles deliberately require the same complete ordered exporter signature, so the selected type must be passed explicitly; do not infer it from a filename, header, or value. The confirmed `twitter-comments` mapping uses `user_id` -> temporary `Twitter用户ID` and `screen_name` -> temporary `Twitter昵称`, then reuses the `twitter` hash namespace. X 评论 never runs the X 推文 keep-keyword filter and proceeds from standardization approval to the KOL clean-word gate.

## Naming And Merge Entry

### Amazon Routing Constraint

For Amazon inputs, the confirmation must display exactly one region-specific
preprocessing profile: `amazon-japan` for `亚马逊日本评论数据`, or `amazon-us`
for `亚马逊美国评论数据`. The generic token `amazon` is only a source-discovery
keyword and must never be displayed as a preprocessing profile or passed to
`preprocess_platform_comments.py --platform`.

```text
研究项目名：{{RESEARCH_PROJECT_NAME}}
是否为新研究项目：{{IS_NEW_RESEARCH_PROJECT}}
产品名：{{PRODUCT_NAME}}
数据来源：{{DATA_SOURCE}}
平台预处理分流：{{PLATFORM_PREPROCESSING_PROFILE}}
分流校验：{{PLATFORM_PREPROCESSING_VALIDATION}}
合并总表：{{MERGED_FILENAME}}
标准化总表：{{STANDARDIZED_FILENAME}}
清洗后总表：{{CLEANED_FILENAME}}

请确认以上产品名、数据来源、平台预处理分流和文件命名是否正确，并确认是否可以进入合并流程。
```

## New Research Project Hash-Key Privacy Confirmation

Use this only before the first standardization run for a newly confirmed research project. Do not show it when the project already has a protected key.

```text
本轮将首次为研究项目「{{RESEARCH_PROJECT_NAME}}」创建当前 Windows 用户受 DPAPI 保护的项目密钥，并将已登记的账号 ID 或昵称转换为同项目、同平台可关联的哈希 ID。原始身份字段不会进入输出、日志或摘要；哈希 ID 属于伪名化，不是法律意义上的匿名化。

请确认是否同意创建此项目密钥并进入标准化。
```

After the user confirms, the standardizer command must use `--initialize-project --confirm-project-key-creation "{{RESEARCH_PROJECT_NAME}}"`. This command argument records the confirmed project name and does not replace the required user confirmation.

## Single Input

```text
当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。
```

## Merge Completion

```text
是否已经提供并合并完所有需要合并的表格？你确认后我再进行标准化。
```

## Standardization Approval

```text
标准化后的表格已生成，请确认是否可以进入清洗流程？你确认后我再询问 KOL 清理词并清洗。
```

## KOL Clean Words

```text
是否有 KOL 清理词？没有就回复“没有”；有的话请一次性发来所有清理词。
```

```text
是否已经提供完成所有 KOL 清理词？你确认后我再进行清洗。
```

## X Tweet Keep Keywords

Only when the user selected `推文` and the confirmed preprocessing profile is `twitter`, after standardized-workbook approval and before the KOL clean-word gate. This does not apply to X 评论:

```text
请提供本轮 X 推文保留关键词。仅保留“评论内容”包含任一关键词的整行数据；请一次性提供所有关键词。
```

```text
是否已经提供完成所有 X 推文保留关键词？你确认后我将执行关键词筛选，再进入通用 KOL 清理词与清洗流程。
```

## Existing Output Replacement

Use this only when one or more exact output files already exist. Show every path that would be replaced; do not infer approval from an earlier workflow confirmation.

```text
以下输出文件已存在，覆盖会替换现有内容：
{{EXISTING_OUTPUT_PATHS}}

请确认是否覆盖以上每一个确切路径？确认后才可使用 --overwrite，并为每个已存在输出传入一次 --confirm-overwrite <确切路径>。
```

Do not ask the user to approve an external or temporary cleaner configuration: it is prohibited. After default cleanup removes a cleaner deletion log or summary, do not offer to restore it; a fresh run requires a new confirmed final output path.
