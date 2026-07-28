# Workflow Confirmation Template

## Confirmation Integrity

The confirmation text below must be sent in the current conversation and answered explicitly by the user. Do not replace a response with a CLI flag, a JSON/state file, an old log, a historical confirmation, or a request to process quickly.

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

## Twitter/X Keep Keywords

Only for a confirmed `twitter` preprocessing profile, after standardized-workbook approval and before the KOL clean-word gate:

```text
请提供本轮 Twitter/X 评论保留关键词。仅保留“评论内容”包含任一关键词的整行数据；请一次性提供所有关键词。
```

```text
是否已经提供完成所有 Twitter/X 保留关键词？你确认后我将执行关键词筛选，再进入通用 KOL 清理词与清洗流程。
```

## Existing Output Replacement

Use this only when one or more exact output files already exist. Show every path that would be replaced; do not infer approval from an earlier workflow confirmation.

```text
以下输出文件已存在，覆盖会替换现有内容：
{{EXISTING_OUTPUT_PATHS}}

请确认是否覆盖以上每一个确切路径？确认后才可使用 --overwrite，并为每个已存在输出传入一次 --confirm-overwrite <确切路径>。
```

Do not ask the user to approve an external or temporary cleaner configuration: it is prohibited. After default cleanup removes a cleaner deletion log or summary, do not offer to restore it; a fresh run requires a new confirmed final output path.
