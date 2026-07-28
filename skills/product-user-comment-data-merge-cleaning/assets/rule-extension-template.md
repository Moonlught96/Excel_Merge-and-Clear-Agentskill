# Rule Extension Template

```text
Change type: header alias / platform preprocessing config / stable account-ID mapping /
display-name fallback / fixed cleaner term / standardized column / cleaning threshold /
filename / audit / execution guard / other

Exact user-confirmed rule change:
Locked base rules that remain unchanged:
Affected language or platform:
User confirmation record:
Platform-specific schema evidence (headers/schema only; no raw identity values):
Complete ordered header signature (each item must match literally):
Preprocessing fields, fixed operations, and retain/omit policy:
Standardized-audit structural checks added or changed:
Identity type and worksheet-wide priority:
Canonical configuration files changed:
Scripts changed:
Reference files changed:
Assets/templates changed:
New or updated deterministic tests:
Standalone Skill verification result:
```

## Execution Guard Checklist

- A cleaner rule change updates the canonical root `config/comment-cleaner.json` and bundled Skill copy; no external or temporary cleaner JSON is created.
- Each output overwrite test proves `--overwrite` alone fails and `--confirm-overwrite` names every exact existing output.
- A retention test proves a deleted `.deletions.csv` cannot be regenerated at the same final output path or recreated by cleanup `--summary`.
- The change preserves original inputs, final cleaned `.xlsx`/`.csv`, deterministic processing, and no-AI data judgment.

## Identity Mapping Constraints

- 未经确认的身份别名不得添加。
- 新增平台或表头别名必须获得用户明确确认和平台专属证据。
- `用户身份` 禁止作为身份来源。
- 评论 ID 和父评论 ID 禁止作为身份来源。
- URL 和主页链接禁止作为身份来源。
- IP 字段禁止作为身份来源。
- Evidence must contain headers/schema only or be redacted.
- Raw identity values must never be committed.
- 来源自带的 `哈希ID` 禁止作为身份来源。

Use this template to record every rule extension. Base rules not explicitly named by the user must remain unchanged.
