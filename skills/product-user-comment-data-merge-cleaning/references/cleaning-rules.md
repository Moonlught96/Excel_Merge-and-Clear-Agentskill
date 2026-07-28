# Deterministic Comment Cleaning Rules

## Main Comment Cleaning

- Trim leading and trailing whitespace before evaluating a main comment.
- The public workflow CLI must explicitly pass `--target-header 评论内容` and the confirmed `--platform`. Both the CLI and internal cleaner reject missing or different target headers; numeric `target_column` / third-column fallback is disabled.
- Chinese comments whose trimmed length is less than or equal to 7 characters are deleted.
- Chinese comments use character length. Non-Chinese comments use deterministic word count.
- Script classification is deterministic and gives Japanese Kana, Korean Hangul, Thai, and Devanagari precedence over Han characters, so mixed Japanese/Korean text does not inherit the Chinese length threshold.
- Text containing Han characters but no Kana, Hangul, Thai, or Devanagari is treated as Chinese. A Han-only Japanese comment cannot be distinguished from Chinese without semantic inference and therefore follows the Chinese threshold.
- Non-Chinese comments with four or fewer words are deleted.
- For unspaced non-Chinese scripts, only text with four or fewer characters is deleted by the short-text rule.
- Pure numeric comments keep the legacy seven-character threshold for backward compatibility.
- Delete comments exactly equal to `该用户未填写评价内容` or `此用户未填写评价内容`.
- Delete a row when the main comment contains any user-confirmed KOL clean word.
- Delete duplicate main comments only within the same worksheet, keeping the row with the highest deterministic numeric value in `点赞数` and deleting the other rows. If likes are tied, blank, non-numeric, or the `点赞数` column is absent, keep the last occurrence. Non-numeric likes are treated as `0`; no semantic or abbreviated-number inference is permitted.
- Never use AI, semantic quality review, sentiment, relevance, suspected-advertising judgment, or fuzzy matching.
- Fixed delete words are isolated by deterministic script group. Chinese comments use only Chinese fixed words; Japanese, Korean, Thai, and Hindi comments use only their corresponding script group. English and Spanish share the Latin-script group because script inspection cannot reliably distinguish those languages without semantic inference.
- The base configuration applies language-neutral URL markers such as `http://` and `https://` to every script group and platform, including Twitter/X. No platform-specific URL/link exemption is active.
- Latin-script fixed words use complete lexical boundaries with case-insensitive matching where configured. A configured whole word must not match a longer token: `TESTV`, `contest`, and `testing` do not match a configured `test` term.

## Fixed Delete Words

Fixed delete words are appended to the original `链接` rule; do not replace or remove `链接`.

The executable source of truth is `config/comment-cleaner.json`. The exact active base lists are duplicated below for documentation and must be kept synchronized with that configuration. No platform-specific cleaner exception is currently registered; external, copied, and temporary cleaner configurations are prohibited.

### Ambiguous Chinese Substring Exclusions

The following short Chinese strings are deliberately **not** fixed delete terms: `无`, `第一`, `略`, `测试`, `来了`, and `路过`. They caused false positives under literal Chinese substring matching, for example `无炫光设计让我很满意`, `第一次购买屏幕挂灯效果很好`, `价格略贵但整体品质不错`, and `感应到人来了就会自动亮灯`.

Do not re-add these six terms through a temporary per-run configuration. A future change requires explicit user confirmation, an update to the canonical `config/comment-cleaner.json`, synchronization of the bundled config, and both positive and nearby-negative regression tests. When any narrative list conflicts with the executable JSON configuration, the JSON configuration is authoritative.

### Contextual Latin Exclusions

`first`, `test`, `how much`, and `price?` are deliberately not active fixed delete terms. They occur in normal long-form product discussion, such as a first purchase, a test report, a price comparison, or a question with additional product context. Short standalone forms still go through the existing non-Chinese length rule; this exclusion does not add semantic judgment.

Do not restore these four terms through an external, copied, or temporary configuration. A future change requires explicit user confirmation, a canonical-config update, synchronized documentation, and positive/nearby-negative regression tests.

`链接`, `凑字数`, `水经验`, `赚积分`, `为了金币`, `赚硬币`, `赚京豆`, `淘气值`, `为了评论而评论`, `混个脸熟`, `完成任务`, `代下`, `代买`, `内部券`, `加微`, `加v`, `私聊我`, `主页看`, `点击链接`, `http://`, `https://`, `打卡`, `冒泡`, `占座`, `无内容`, `暂无评价`, `蹲`, `蹲一个`, `求链接`, `求分享`, `多少钱`, `怎么卖`, `啥牌子`, `什么牌子`, `求品牌`, `求私`, `加群`, `裙内`, `互赞`, `互粉`, `互关`, `回关`, `秒回`, `交朋友`, `リンク`, `プロフィール見て`, `プロフ見て`, `DMして`, `フォロー返し`, `相互フォロー`, `テスト`, `内容なし`, `評価なし`, `コメント稼ぎ`, `링크`, `맞팔`, `테스트`, `내용 없음`.

Case-insensitive configured terms include:

- Chinese/English: `加v`, `link in bio`, `click link`, `click the link`, `check my profile`, `see my profile`, `visit my profile`, `dm me`, `message me`, `follow me`, `follow back`, `follow for follow`, `sub4sub`, `sub for sub`, `subscribe to my channel`, `earn coins`, `free coins`, `for coins`, `comment for points`, `promo code`, `coupon code`, `discount code`, `whatsapp`, `telegram`, `n/a`, `no content`, `no comment`, `nothing to say`, `what brand`, `brand?`, `share link`, `need link`, `passing by`, `check in`.
- Spanish: `enlace`, `link en bio`, `haz clic en el enlace`, `mira mi perfil`, `revisa mi perfil`, `mándame dm`, `mandame dm`, `escríbeme`, `escribeme`, `sígueme`, `sigueme`, `te sigo`, `cupón`, `cupon`, `código promocional`, `codigo promocional`, `descuento`, `primero`, `prueba`, `sin contenido`, `sin comentario`, `nada que decir`, `cuánto cuesta`, `cuanto cuesta`, `precio`, `qué marca`, `que marca`, `marca?`, `pásame el link`, `pasame el link`, `necesito el link`.
- Thai: `ลิงก์`, `ขอลิงก์`, `ส่งลิงก์`, `ดูโปรไฟล์`, `ทัก dm`, `dm มา`, `ติดตามกลับ`, `ฟอลกลับ`, `ทดสอบ`, `ไม่มีเนื้อหา`, `ไม่มีความคิดเห็น`, `ปั๊มคอมเมนต์`, `เก็บแต้ม`, `ราคาเท่าไหร่`, `กี่บาท`, `ยี่ห้ออะไร`, `แบรนด์อะไร`, `ผ่านมา`, `เช็คชื่อ`, `ทำภารกิจ`.
- Hindi: `लिंक`, `लिंक दो`, `लिंक भेजो`, `प्रोफाइल देखें`, `डीएम करें`, `dm करें`, `फॉलो बैक`, `मुझे फॉलो करें`, `टेस्ट`, `कोई सामग्री नहीं`, `कोई टिप्पणी नहीं`, `पॉइंट कमाने`, `सिक्के कमाने`, `कितने का है`, `कीमत`, `कौन सा ब्रांड`, `ब्रांड क्या है`, `बस गुजर रहा`, `चेक इन`, `काम पूरा`.

`加v` must match both lowercase and uppercase forms such as `加v` and `加V`.

When adding a fixed delete word later, add confirmed equivalents for Chinese, English, Japanese, Korean, Spanish, Thai, and Hindi where applicable. Do not generate translations with AI during data processing.

## Random Alphanumeric Heap Rule

For comments with no Chinese characters, delete only by configured deterministic regex and thresholds:

- pure digit token length at least 9;
- mixed letter/digit token length at least 10;
- letter-only token length at least 10 combined with vowel ratio at most 0.2 or consonant run at least 5.

This rule must not use a normal-English semantic dictionary or AI judgment.

## Subcomment Cleaning

- Apply these rules only to `一级评论`, `二级评论`, and `三级评论`.
- For duplicate subcomment text in the same worksheet, keep the last occurrence and clear only each earlier duplicate cell.
- Clear `一级评论`, `二级评论`, and `三级评论` cells whose trimmed length is less than or equal to 5 characters.
- Duplicate matching uses exact trimmed text only.
- These rules must not delete the row and must not modify the main `评论内容` column.
- Do not deduplicate across worksheets.

## Cleaning Outputs

The cleaner generates:

- cleaned `.xlsx`;
- first-worksheet `.csv` using UTF-8 with BOM;
- `.deletions.csv`, with `delete_row` for row deletion and `clear_cell` for subcomment clearing;
- `.summary.json`.

Retention of logs and summaries is governed by `naming-and-retention.md`.
