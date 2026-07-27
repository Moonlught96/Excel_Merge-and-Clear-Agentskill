# Workflow Confirmation Template

## Naming And Merge Entry

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
