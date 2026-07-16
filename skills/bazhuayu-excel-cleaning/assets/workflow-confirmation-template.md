# Workflow Confirmation Template

## Naming And Merge Entry

```text
研究项目名：{{RESEARCH_PROJECT_NAME}}
是否为新研究项目：{{IS_NEW_RESEARCH_PROJECT}}
产品名：{{PRODUCT_NAME}}
数据来源：{{DATA_SOURCE}}
合并总表：{{MERGED_FILENAME}}
标准化总表：{{STANDARDIZED_FILENAME}}
清洗后总表：{{CLEANED_FILENAME}}

请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。
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
