# Workflow And Confirmation Gates

## Global Order

The fixed workflow is:

1. Confirm research project name, product name, data source, and planned filenames once.
2. Confirm whether the supplied file list is complete enough to enter merge or, for one file, whether it is the only intended input.
3. Merge multiple raw inputs into a new raw merged workbook.
4. Return the raw merged workbook and wait for merge-completion confirmation.
5. For B站 data, create a separate reply-prefix-stripped merged workbook.
6. Standardize the raw or prefix-stripped workbook into a new standardized workbook.
7. Return the standardized workbook and wait for approval.
8. Ask for optional KOL clean words and, when words exist, confirm the list is complete.
9. Clean with deterministic tools.
10. Verify final `.xlsx` and `.csv`, clean up current-run intermediates, and return retained outputs.

Do not collapse or reorder the confirmation gates.

## Initial File Handling

- If no file path is provided, ask the user to provide the files.
- Accept `.xlsx`, `.xlsm`, and `.csv`.
- Use only files explicitly provided by the user. Never scan a folder for additional files.
- Confirm research project name, product name, and data source once per workflow. Reuse the existing protected key until the user explicitly identifies a new research project. Later phases change only the step name in the output filename.

## Single-File Workflow

After showing product name, data source, and the planned `标准化总表` and `清洗后总表` filenames, ask exactly:

```text
当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。
```

- Do not skip merge until the user confirms this is the only intended input.
- After confirmation, standardize the original input into a separate workbook.
- Return the standardized workbook and wait for approval before asking for KOL clean words or cleaning.

## Multi-File Workflow

This is the default for same-platform batches with the same original format.

1. Show product name, data source, and all three planned filenames.
2. Ask exactly:

   ```text
   请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。
   ```

3. Do not run merge until the user confirms both naming and entry into merge.
4. Merge the explicitly provided original files in their provided order into a new raw merged `.xlsx`.
5. Return the raw merged workbook before any standardization.
6. Ask exactly:

   ```text
   是否已经提供并合并完所有需要合并的表格？你确认后我再进行标准化。
   ```

7. Do not standardize until the user confirms all intended files are included.
8. If the data source is B站, run the fixed reply-prefix step on the merged workbook and create a separate output.
9. Standardize into a new workbook; never overwrite the raw merged workbook.
10. Return the standardized workbook and ask exactly:

    ```text
    标准化后的表格已生成，请确认是否可以进入清洗流程？你确认后我再询问 KOL 清理词并清洗。
    ```

11. Do not clean until the user explicitly approves the standardized workbook.

Do not standardize individual files before merging a same-platform batch.

## KOL Clean-Word Gate

After standardized-workbook approval, ask exactly:

```text
是否有 KOL 清理词？没有就回复“没有”；有的话请一次性发来所有清理词。
```

- If the user says there are no KOL clean words, pass no `--clean-word` arguments and continue.
- If one or more words are provided, do not clean yet. Ask exactly:

  ```text
  是否已经提供完成所有 KOL 清理词？你确认后我再进行清洗。
  ```

- After confirmation, pass each clean word as a separate `--clean-word` argument.
- Never add an unconfirmed KOL clean word.

## B站 Reply Prefix Step

- Run the step only after merge-completion confirmation and before standardization.
- Process only a fixed prefix in `content` or `评论内容` matching `回复@xxx：`, `回复 @xxx：`, `回复@xxx:`, or `回复 @xxx:`.
- Keep only the text after the first matching Chinese or English colon in the same cell.
- Save a separate reply-prefix-stripped merged workbook.
- Do not overwrite the raw merged workbook.
- Do not move reply rows, infer parent-child hierarchy, add hierarchy columns, or delete rows.

## Completion

- Verify the cleaned `.xlsx` and `.csv` exist before cleanup.
- Do not ask for another cleanup confirmation.
- Return only the final cleaned `.xlsx` and `.csv` unless the user requested audit files before cleaning.
