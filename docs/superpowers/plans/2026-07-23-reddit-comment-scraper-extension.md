# Reddit Single-Post Comment Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally installed Chrome Manifest V3 extension that scrapes all discoverable public comments from the current Reddit post and exports the approved enhanced CSV without a 20-comment product limit.

**Architecture:** A module-based content script owns scraping state for the current tab. It prefers Reddit's browser-session JSON responses, expands discovered `more` children, and merges a DOM fallback when structured retrieval is incomplete. The popup only controls the content script, renders progress, and creates the local CSV download.

**Tech Stack:** Chrome Manifest V3, browser-native JavaScript ES modules, HTML/CSS, Node.js built-in `node:test`, no production dependencies.

---

## File map

Create the extension under `extensions/reddit-single-post-scraper/` so it remains isolated from the existing Python comment-cleaning tools.

```text
extensions/reddit-single-post-scraper/
├── manifest.json                         Chrome permissions and entry points
├── package.json                          Node test commands only
├── README.md                             Local installation and usage
├── src/
│   ├── content-loader.js                 Loads the ES-module content entry
│   ├── content-main.js                   Chrome message boundary
│   ├── core/
│   │   ├── comment-tree.js               Tree flattening and ID deduplication
│   │   ├── csv-export.js                 Approved 14-column CSV contract
│   │   ├── filename.js                   Safe deterministic download name
│   │   └── scrape-controller.js          State machine, cancellation, fallback
│   ├── reddit/
│   │   ├── reddit-json.js                Thread JSON and morechildren parsing
│   │   └── reddit-dom.js                 Page-expansion and DOM fallback
│   └── popup/
│       ├── popup.html                    Popup markup
│       ├── popup.css                     Independent visual design
│       ├── popup.js                      Chrome messaging and download action
│       └── view-model.js                 Pure state-to-UI mapping
└── tests/
    ├── manifest.test.js
    ├── comment-tree.test.js
    ├── csv-export.test.js
    ├── filename.test.js
    ├── reddit-json.test.js
    ├── reddit-dom.test.js
    ├── scrape-controller.test.js
    ├── content-main.test.js
    └── view-model.test.js
```

Do not add a build system. `src/content-loader.js` dynamically imports the extension module, and the module files are exposed only on Reddit through `web_accessible_resources`.

### Task 1: Scaffold the loadable Manifest V3 extension

**Files:**
- Create: `extensions/reddit-single-post-scraper/package.json`
- Create: `extensions/reddit-single-post-scraper/tests/manifest.test.js`
- Create: `extensions/reddit-single-post-scraper/manifest.json`
- Create: `extensions/reddit-single-post-scraper/src/content-loader.js`
- Create: `extensions/reddit-single-post-scraper/src/popup/popup.html`
- Create: `extensions/reddit-single-post-scraper/src/popup/popup.css`
- Create: `extensions/reddit-single-post-scraper/src/popup/popup.js`

- [ ] **Step 1: Write the failing manifest test**

```js
// extensions/reddit-single-post-scraper/tests/manifest.test.js
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const manifestUrl = new URL("../manifest.json", import.meta.url);

test("manifest uses minimal Reddit-only MV3 access", async () => {
  const manifest = JSON.parse(await readFile(manifestUrl, "utf8"));

  assert.equal(manifest.manifest_version, 3);
  assert.deepEqual(manifest.host_permissions, ["https://www.reddit.com/*"]);
  assert.equal(manifest.action.default_popup, "src/popup/popup.html");
  assert.deepEqual(manifest.content_scripts[0].matches, [
    "https://www.reddit.com/r/*/comments/*",
  ]);
  assert.deepEqual(manifest.permissions ?? [], []);
  assert.equal(manifest.background, undefined);
});
```

- [ ] **Step 2: Run the test and verify the scaffold is absent**

Run:

```powershell
Set-Location "extensions/reddit-single-post-scraper"
node --test tests/manifest.test.js
```

Expected: FAIL because `manifest.json` does not exist.

- [ ] **Step 3: Add the minimal package and manifest**

`extensions/reddit-single-post-scraper/package.json`:

```json
{
  "name": "reddit-single-post-scraper",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test"
  }
}
```

`extensions/reddit-single-post-scraper/manifest.json`:

```json
{
  "manifest_version": 3,
  "name": "Reddit Single-Post Scraper",
  "version": "0.1.0",
  "description": "Export public comments from the current Reddit post to an enhanced CSV.",
  "action": {
    "default_popup": "src/popup/popup.html"
  },
  "host_permissions": [
    "https://www.reddit.com/*"
  ],
  "content_scripts": [
    {
      "matches": [
        "https://www.reddit.com/r/*/comments/*"
      ],
      "js": [
        "src/content-loader.js"
      ],
      "run_at": "document_idle"
    }
  ],
  "web_accessible_resources": [
    {
      "resources": [
        "src/*.js",
        "src/core/*.js",
        "src/reddit/*.js"
      ],
      "matches": [
        "https://www.reddit.com/*"
      ]
    }
  ]
}
```

```js
// extensions/reddit-single-post-scraper/src/content-loader.js
void import(chrome.runtime.getURL("src/content-main.js"));
```

```html
<!-- extensions/reddit-single-post-scraper/src/popup/popup.html -->
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Reddit Single-Post Scraper</title>
    <link rel="stylesheet" href="./popup.css">
  </head>
  <body>
    <main id="app">
      <h1>Reddit 评论抓取</h1>
      <p id="status">正在检测当前帖子…</p>
    </main>
    <script type="module" src="./popup.js"></script>
  </body>
</html>
```

```css
/* extensions/reddit-single-post-scraper/src/popup/popup.css */
:root {
  color-scheme: light;
  font-family: Inter, "Segoe UI", sans-serif;
}

body {
  width: 360px;
  margin: 0;
  background: #f6f7f9;
  color: #17212b;
}

main {
  padding: 18px;
}

h1 {
  margin: 0 0 12px;
  font-size: 18px;
}
```

```js
// extensions/reddit-single-post-scraper/src/popup/popup.js
document.querySelector("#status").textContent = "基础扩展已加载";
```

- [ ] **Step 4: Run the manifest test**

Run:

```powershell
npm test
```

Expected: 1 test passes.

- [ ] **Step 5: Load the directory in Chrome**

Open `chrome://extensions`, enable Developer mode, choose “Load unpacked,” and select:

```text
D:\八爪鱼cli Project\extensions\reddit-single-post-scraper
```

Expected: the extension loads without a manifest error, and its popup shows “基础扩展已加载”.

- [ ] **Step 6: Commit the scaffold**

```powershell
git add extensions/reddit-single-post-scraper
git commit -m "feat: scaffold Reddit scraper extension"
```

### Task 2: Flatten and deduplicate the comment tree

**Files:**
- Create: `extensions/reddit-single-post-scraper/tests/comment-tree.test.js`
- Create: `extensions/reddit-single-post-scraper/src/core/comment-tree.js`

- [ ] **Step 1: Write failing tree tests**

```js
// extensions/reddit-single-post-scraper/tests/comment-tree.test.js
import assert from "node:assert/strict";
import test from "node:test";
import { flattenCommentTree } from "../src/core/comment-tree.js";

test("flattens parent-first and derives level and reply status", () => {
  const roots = [{
    id: "c1",
    parentId: "post1",
    author: "alpha",
    time: "2026-07-01T00:00:00.000Z",
    score: 4,
    comment: "Parent",
    links: [],
    replies: [{
      id: "c2",
      parentId: "c1",
      author: "beta",
      time: "2026-07-01T00:01:00.000Z",
      score: 2,
      comment: "Child",
      links: ["https://example.com"],
      replies: [],
    }],
  }];

  assert.deepEqual(flattenCommentTree("post1", roots), [
    {
      author: "alpha",
      time: "2026-07-01T00:00:00.000Z",
      score: 4,
      threadLevel: 0,
      isReply: "No",
      comment: "Parent",
      links: [],
      commentId: "c1",
      parentId: "post1",
    },
    {
      author: "beta",
      time: "2026-07-01T00:01:00.000Z",
      score: 2,
      threadLevel: 1,
      isReply: "Yes",
      comment: "Child",
      links: ["https://example.com"],
      commentId: "c2",
      parentId: "c1",
    },
  ]);
});

test("keeps the first occurrence of a duplicate comment ID", () => {
  const duplicate = {
    id: "c1",
    parentId: "post1",
    author: "alpha",
    time: "",
    score: 1,
    comment: "same",
    links: [],
    replies: [],
  };

  assert.equal(flattenCommentTree("post1", [duplicate, duplicate]).length, 1);
});
```

- [ ] **Step 2: Run the focused test**

Run:

```powershell
node --test tests/comment-tree.test.js
```

Expected: FAIL because `comment-tree.js` does not exist.

- [ ] **Step 3: Implement deterministic flattening**

```js
// extensions/reddit-single-post-scraper/src/core/comment-tree.js
export function flattenCommentTree(postId, roots) {
  const rows = [];
  const seen = new Set();

  function visit(node, level) {
    if (!node?.id || seen.has(node.id)) return;
    seen.add(node.id);

    rows.push({
      author: node.author ?? "",
      time: node.time ?? "",
      score: node.score ?? "",
      threadLevel: level,
      isReply: level === 0 ? "No" : "Yes",
      comment: node.comment ?? "",
      links: Array.isArray(node.links) ? node.links : [],
      commentId: node.id,
      parentId: level === 0 ? postId : (node.parentId ?? ""),
    });

    for (const reply of node.replies ?? []) {
      visit(reply, level + 1);
    }
  }

  for (const root of roots ?? []) visit(root, 0);
  return rows;
}

export function summarizeComments(rows) {
  return {
    extractedCount: rows.length,
    rootCount: rows.filter((row) => row.threadLevel === 0).length,
    replyCount: rows.filter((row) => row.threadLevel > 0).length,
    maxDepth: rows.reduce(
      (maximum, row) => Math.max(maximum, row.threadLevel),
      0,
    ),
  };
}
```

- [ ] **Step 4: Add and run summary assertions**

Append:

```js
import { summarizeComments } from "../src/core/comment-tree.js";

test("summarizes extracted rows", () => {
  assert.deepEqual(summarizeComments([
    { threadLevel: 0 },
    { threadLevel: 1 },
    { threadLevel: 3 },
  ]), {
    extractedCount: 3,
    rootCount: 1,
    replyCount: 2,
    maxDepth: 3,
  });
});
```

Run:

```powershell
node --test tests/comment-tree.test.js
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit tree handling**

```powershell
git add extensions/reddit-single-post-scraper/src/core/comment-tree.js extensions/reddit-single-post-scraper/tests/comment-tree.test.js
git commit -m "feat: normalize Reddit comment trees"
```

### Task 3: Generate the approved enhanced CSV and filename

**Files:**
- Create: `extensions/reddit-single-post-scraper/tests/csv-export.test.js`
- Create: `extensions/reddit-single-post-scraper/tests/filename.test.js`
- Create: `extensions/reddit-single-post-scraper/src/core/csv-export.js`
- Create: `extensions/reddit-single-post-scraper/src/core/filename.js`

- [ ] **Step 1: Write failing CSV contract tests**

```js
// extensions/reddit-single-post-scraper/tests/csv-export.test.js
import assert from "node:assert/strict";
import test from "node:test";
import { CSV_COLUMNS, buildCsv } from "../src/core/csv-export.js";

test("uses the approved 14-column order and UTF-8 BOM", () => {
  const csv = buildCsv({
    post: {
      id: "post1",
      author: "poster",
      time: "2026-07-01T00:00:00.000Z",
      content: "Post body",
      score: 99,
      commentCount: 1,
    },
    comments: [{
      author: "commenter",
      time: "2026-07-01T00:01:00.000Z",
      score: 3,
      threadLevel: 0,
      isReply: "No",
      comment: "Line 1,\n\"Line 2\" 😀",
      links: ["https://example.com/a", "/relative"],
      commentId: "c1",
      parentId: "post1",
    }],
  });

  assert.equal(csv.charCodeAt(0), 0xfeff);
  assert.equal(csv.slice(1).split("\r\n")[0], CSV_COLUMNS.join(","));
  assert.match(csv, /"Line 1,\n""Line 2"" 😀"/);
  assert.match(csv, /https:\/\/example\.com\/a; \/relative/);
});
```

- [ ] **Step 2: Write the failing filename tests**

```js
// extensions/reddit-single-post-scraper/tests/filename.test.js
import assert from "node:assert/strict";
import test from "node:test";
import { buildCsvFilename } from "../src/core/filename.js";

test("creates a safe title and Beijing-date filename", () => {
  assert.equal(
    buildCsvFilename('A/B: "ScreenBar"?', new Date("2026-07-23T03:00:00Z")),
    "A_B_ _ScreenBar___2026-07-23.csv",
  );
});
```

- [ ] **Step 3: Run both tests**

Run:

```powershell
node --test tests/csv-export.test.js tests/filename.test.js
```

Expected: FAIL because both modules are absent.

- [ ] **Step 4: Implement CSV serialization**

```js
// extensions/reddit-single-post-scraper/src/core/csv-export.js
export const CSV_COLUMNS = [
  "Author",
  "Time",
  "Score",
  "Thread Level",
  "Is Reply",
  "Comment",
  "Links",
  "Comment ID",
  "Parent ID",
  "Post Author",
  "Post Time",
  "Post Content",
  "Post Score",
  "Post Comment Count",
];

function escapeCell(value) {
  const text = value == null ? "" : String(value);
  if (!/[",\r\n]/.test(text)) return text;
  return `"${text.replaceAll('"', '""')}"`;
}

export function buildCsv({ post, comments }) {
  const lines = [CSV_COLUMNS.map(escapeCell).join(",")];

  for (const row of comments) {
    lines.push([
      row.author,
      row.time,
      row.score,
      row.threadLevel,
      row.isReply,
      row.comment,
      row.links.join("; "),
      row.commentId,
      row.parentId,
      post.author,
      post.time,
      post.content,
      post.score,
      post.commentCount,
    ].map(escapeCell).join(","));
  }

  return `\ufeff${lines.join("\r\n")}\r\n`;
}
```

- [ ] **Step 5: Implement deterministic filename handling**

```js
// extensions/reddit-single-post-scraper/src/core/filename.js
function beijingDate(now) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

export function buildCsvFilename(title, now = new Date()) {
  const safeTitle = String(title || "reddit-comments")
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
    .replace(/[. ]+$/g, "")
    .slice(0, 120) || "reddit-comments";

  return `${safeTitle}_${beijingDate(now)}.csv`;
}
```

- [ ] **Step 6: Run the focused tests and correct only test-proven defects**

Run:

```powershell
node --test tests/csv-export.test.js tests/filename.test.js
```

Expected: all tests pass.

- [ ] **Step 7: Commit export support**

```powershell
git add extensions/reddit-single-post-scraper/src/core/csv-export.js extensions/reddit-single-post-scraper/src/core/filename.js extensions/reddit-single-post-scraper/tests/csv-export.test.js extensions/reddit-single-post-scraper/tests/filename.test.js
git commit -m "feat: export enhanced Reddit CSV"
```

### Task 4: Parse Reddit thread JSON into the internal model

**Files:**
- Create: `extensions/reddit-single-post-scraper/tests/reddit-json.test.js`
- Create: `extensions/reddit-single-post-scraper/src/reddit/reddit-json.js`

- [ ] **Step 1: Write failing JSON parser tests**

```js
// extensions/reddit-single-post-scraper/tests/reddit-json.test.js
import assert from "node:assert/strict";
import test from "node:test";
import {
  buildThreadJsonUrl,
  parseThreadPayload,
} from "../src/reddit/reddit-json.js";

test("builds a same-origin raw JSON URL", () => {
  assert.equal(
    buildThreadJsonUrl(
      "https://www.reddit.com/r/desksetup/comments/1tbschi/title/?sort=best",
    ),
    "https://www.reddit.com/r/desksetup/comments/1tbschi/title.json?raw_json=1&limit=500&sort=best",
  );
});

test("normalizes post, nested comments, links, and more placeholders", () => {
  const payload = [
    { data: { children: [{ kind: "t3", data: {
      id: "p1",
      author: "poster",
      created_utc: 100,
      selftext: "Post body",
      score: 10,
      num_comments: 3,
      title: "Post title",
    } }] } },
    { data: { children: [
      { kind: "t1", data: {
        id: "c1",
        parent_id: "t3_p1",
        author: "alpha",
        created_utc: 101,
        score: 2,
        body: "See [source](https://example.com)",
        replies: { data: { children: [
          { kind: "t1", data: {
            id: "c2",
            parent_id: "t1_c1",
            author: "beta",
            created_utc: 102,
            score: 1,
            body: "Reply",
            replies: "",
          } },
          { kind: "more", data: { parent_id: "t1_c1", children: ["c3"] } },
        ] } },
      } },
    ] } },
  ];

  const result = parseThreadPayload(payload);
  assert.equal(result.post.id, "p1");
  assert.equal(result.post.time, "1970-01-01T00:01:40.000Z");
  assert.equal(result.roots[0].replies[0].parentId, "c1");
  assert.deepEqual(result.roots[0].links, ["https://example.com"]);
  assert.deepEqual(result.more, [{ parentId: "c1", children: ["c3"] }]);
});
```

- [ ] **Step 2: Run the focused test**

Run:

```powershell
node --test tests/reddit-json.test.js
```

Expected: FAIL because `reddit-json.js` is absent.

- [ ] **Step 3: Implement the pure parser**

```js
// extensions/reddit-single-post-scraper/src/reddit/reddit-json.js
function stripFullname(value) {
  return String(value ?? "").replace(/^(t1|t3)_/, "");
}

function isoFromSeconds(value) {
  return Number.isFinite(value)
    ? new Date(value * 1000).toISOString()
    : "";
}

export function extractLinks(markdown) {
  const text = String(markdown ?? "");
  const links = [];
  const seen = new Set();
  const pattern = /\[[^\]]*]\(([^)\s]+)(?:\s+"[^"]*")?\)|https?:\/\/[^\s<>"')\]]+/g;

  for (const match of text.matchAll(pattern)) {
    const value = match[1] ?? match[0];
    if (!seen.has(value)) {
      seen.add(value);
      links.push(value);
    }
  }
  return links;
}

export function buildThreadJsonUrl(pageUrl) {
  const url = new URL(pageUrl);
  const sort = url.searchParams.get("sort");
  url.hash = "";
  url.search = "";
  url.pathname = `${url.pathname.replace(/\/$/, "")}.json`;
  url.searchParams.set("raw_json", "1");
  url.searchParams.set("limit", "500");
  if (sort) url.searchParams.set("sort", sort);
  return url.href;
}

function parseCommentChildren(children, more) {
  const comments = [];
  for (const child of children ?? []) {
    if (child.kind === "more") {
      const ids = (child.data?.children ?? []).filter(Boolean);
      if (ids.length) {
        more.push({
          parentId: stripFullname(child.data?.parent_id),
          children: ids,
        });
      }
      continue;
    }
    if (child.kind !== "t1") continue;

    const data = child.data ?? {};
    const replyChildren = data.replies?.data?.children ?? [];
    comments.push({
      id: stripFullname(data.id),
      parentId: stripFullname(data.parent_id),
      author: data.author ?? "",
      time: isoFromSeconds(data.created_utc),
      score: data.score ?? "",
      comment: data.body ?? "",
      links: extractLinks(data.body),
      replies: parseCommentChildren(replyChildren, more),
    });
  }
  return comments;
}

export function parseThreadPayload(payload) {
  const postData = payload?.[0]?.data?.children?.[0]?.data;
  const commentChildren = payload?.[1]?.data?.children;
  if (!postData || !Array.isArray(commentChildren)) {
    throw new Error("Reddit returned an unsupported thread payload");
  }

  const more = [];
  return {
    post: {
      id: stripFullname(postData.id),
      title: postData.title ?? "",
      author: postData.author ?? "",
      time: isoFromSeconds(postData.created_utc),
      content: postData.selftext ?? "",
      score: postData.score ?? "",
      commentCount: postData.num_comments ?? "",
    },
    roots: parseCommentChildren(commentChildren, more),
    more,
  };
}
```

- [ ] **Step 4: Run the parser test**

Run:

```powershell
node --test tests/reddit-json.test.js
```

Expected: all tests pass.

- [ ] **Step 5: Commit the parser**

```powershell
git add extensions/reddit-single-post-scraper/src/reddit/reddit-json.js extensions/reddit-single-post-scraper/tests/reddit-json.test.js
git commit -m "feat: parse Reddit thread JSON"
```

### Task 5: Fetch the thread and expand `morechildren`

**Files:**
- Modify: `extensions/reddit-single-post-scraper/tests/reddit-json.test.js`
- Modify: `extensions/reddit-single-post-scraper/src/reddit/reddit-json.js`

- [ ] **Step 1: Add failing fetch and merge tests**

Append:

```js
import { scrapeThreadJson } from "../src/reddit/reddit-json.js";

test("expands morechildren in batches and attaches replies to their parents", async () => {
  const calls = [];
  const fetchImpl = async (url) => {
    calls.push(String(url));
    if (calls.length === 1) {
      return {
        ok: true,
        json: async () => ([
          { data: { children: [{ kind: "t3", data: {
            id: "p1", author: "poster", created_utc: 100,
            selftext: "", score: 1, num_comments: 2, title: "Title",
          } }] } },
          { data: { children: [
            { kind: "t1", data: {
              id: "c1", parent_id: "t3_p1", author: "alpha",
              created_utc: 101, score: 1, body: "Root",
              replies: { data: { children: [
                { kind: "more", data: {
                  parent_id: "t1_c1", children: ["c2"],
                } },
              ] } },
            } },
          ] } },
        ]),
      };
    }
    return {
      ok: true,
      json: async () => ({ json: { data: { things: [
        { kind: "t1", data: {
          id: "c2", parent_id: "t1_c1", author: "beta",
          created_utc: 102, score: 1, body: "Child", replies: "",
        } },
      ] } } }),
    };
  };

  const result = await scrapeThreadJson({
    pageUrl: "https://www.reddit.com/r/x/comments/p1/title/",
    fetchImpl,
    signal: undefined,
    onProgress: () => {},
  });

  assert.equal(calls.length, 2);
  assert.equal(result.roots[0].replies[0].id, "c2");
  assert.equal(result.complete, true);
});
```

- [ ] **Step 2: Run the test**

Run:

```powershell
node --test tests/reddit-json.test.js
```

Expected: FAIL because `scrapeThreadJson` is not exported.

- [ ] **Step 3: Implement bounded morechildren retrieval**

Append to `src/reddit/reddit-json.js`:

```js
function indexComments(roots) {
  const index = new Map();
  const visit = (node) => {
    index.set(node.id, node);
    for (const reply of node.replies) visit(reply);
  };
  for (const root of roots) visit(root);
  return index;
}

export async function scrapeThreadJson({
  pageUrl,
  fetchImpl = fetch,
  signal,
  onProgress = () => {},
  sleepImpl = (milliseconds) =>
    new Promise((resolve) => setTimeout(resolve, milliseconds)),
}) {
  async function requestWithRetry(url, options) {
    let response;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      response = await fetchImpl(url, options);
      if (response.ok) return response;
      const retryable = response.status === 429 || response.status >= 500;
      if (!retryable || attempt === 2) return response;
      await sleepImpl(250 * (2 ** attempt));
    }
    return response;
  }

  const response = await requestWithRetry(buildThreadJsonUrl(pageUrl), {
    credentials: "include",
    signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Reddit thread request failed: ${response.status}`);

  const parsed = parseThreadPayload(await response.json());
  const index = indexComments(parsed.roots);
  const unresolved = [];
  const queued = new Set(parsed.more.flatMap((item) => item.children));
  const pendingIds = [...queued];

  function attach(node) {
    if (!node?.id || index.has(node.id)) return;
    const replies = node.replies;
    node.replies = [];
    const parent = index.get(node.parentId);
    if (parent) parent.replies.push(node);
    else parsed.roots.push(node);
    index.set(node.id, node);
    for (const reply of replies) attach(reply);
  }

  while (pendingIds.length > 0) {
    const batch = pendingIds.splice(0, 100);
    const url = new URL("/api/morechildren.json", pageUrl);
    url.searchParams.set("api_type", "json");
    url.searchParams.set("raw_json", "1");
    url.searchParams.set("link_id", `t3_${parsed.post.id}`);
    url.searchParams.set("children", batch.join(","));

    const moreResponse = await requestWithRetry(url, {
      credentials: "include",
      signal,
      headers: { Accept: "application/json" },
    });
    if (!moreResponse.ok) {
      unresolved.push(...batch);
      continue;
    }

    const payload = await moreResponse.json();
    const returnedIds = new Set();
    for (const thing of payload?.json?.data?.things ?? []) {
      if (thing.kind === "more") {
        for (const id of thing.data?.children ?? []) {
          if (!queued.has(id)) {
            queued.add(id);
            pendingIds.push(id);
          }
        }
        continue;
      }
      if (thing.kind !== "t1") continue;
      const nestedMore = [];
      const node = parseCommentChildren([thing], nestedMore)[0];
      if (!node) continue;
      const collectIds = (item) => {
        returnedIds.add(item.id);
        for (const reply of item.replies) collectIds(reply);
      };
      collectIds(node);
      attach(node);
      for (const more of nestedMore) {
        for (const id of more.children) {
          if (!queued.has(id)) {
            queued.add(id);
            pendingIds.push(id);
          }
        }
      }
    }
    unresolved.push(...batch.filter((id) => !returnedIds.has(id) && !index.has(id)));
    onProgress({ discovered: index.size });
  }

  return {
    post: parsed.post,
    roots: parsed.roots,
    complete: unresolved.length === 0,
    unresolved,
  };
}
```

- [ ] **Step 4: Add an HTTP failure assertion**

Append:

```js
test("reports the status for a failed thread request", async () => {
  await assert.rejects(
    scrapeThreadJson({
      pageUrl: "https://www.reddit.com/r/x/comments/p1/title/",
      fetchImpl: async () => ({ ok: false, status: 429 }),
    }),
    /429/,
  );
});

test("marks a successful response incomplete when requested IDs are missing", async () => {
  let call = 0;
  const result = await scrapeThreadJson({
    pageUrl: "https://www.reddit.com/r/x/comments/p1/title/",
    fetchImpl: async () => {
      call += 1;
      if (call === 1) {
        return {
          ok: true,
          json: async () => ([
            { data: { children: [{ kind: "t3", data: {
              id: "p1", title: "Title", author: "poster",
              created_utc: 100, selftext: "", score: 1, num_comments: 1,
            } }] } },
            { data: { children: [{ kind: "more", data: {
              parent_id: "t3_p1", children: ["missing"],
            } }] } },
          ]),
        };
      }
      return {
        ok: true,
        json: async () => ({ json: { data: { things: [] } } }),
      };
    },
  });

  assert.equal(result.complete, false);
  assert.deepEqual(result.unresolved, ["missing"]);
});

test("retries HTTP 429 twice with bounded backoff", async () => {
  let calls = 0;
  const delays = [];
  const result = await scrapeThreadJson({
    pageUrl: "https://www.reddit.com/r/x/comments/p1/title/",
    sleepImpl: async (milliseconds) => delays.push(milliseconds),
    fetchImpl: async () => {
      calls += 1;
      if (calls < 3) return { ok: false, status: 429 };
      return {
        ok: true,
        json: async () => ([
          { data: { children: [{ kind: "t3", data: {
            id: "p1", title: "Title", author: "poster",
            created_utc: 100, selftext: "", score: 1, num_comments: 0,
          } }] } },
          { data: { children: [] } },
        ]),
      };
    },
  });

  assert.equal(result.complete, true);
  assert.equal(calls, 3);
  assert.deepEqual(delays, [250, 500]);
});
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
node --test tests/reddit-json.test.js
```

Expected: all tests pass.

- [ ] **Step 6: Commit structured retrieval**

```powershell
git add extensions/reddit-single-post-scraper/src/reddit/reddit-json.js extensions/reddit-single-post-scraper/tests/reddit-json.test.js
git commit -m "feat: expand Reddit more comments"
```

### Task 6: Add a bounded DOM fallback

**Files:**
- Create: `extensions/reddit-single-post-scraper/tests/reddit-dom.test.js`
- Create: `extensions/reddit-single-post-scraper/src/reddit/reddit-dom.js`

- [ ] **Step 1: Write failing pure DOM-record tests**

```js
// extensions/reddit-single-post-scraper/tests/reddit-dom.test.js
import assert from "node:assert/strict";
import test from "node:test";
import {
  normalizeDomPost,
  normalizeDomRecord,
  shouldExpandButton,
} from "../src/reddit/reddit-dom.js";

test("recognizes only known expansion labels", () => {
  assert.equal(shouldExpandButton("View more comments"), true);
  assert.equal(shouldExpandButton("More replies"), true);
  assert.equal(shouldExpandButton("Give Award"), false);
});

test("normalizes a shreddit comment record", () => {
  assert.deepEqual(normalizeDomRecord({
    id: "t1_c1",
    parentId: "t3_p1",
    depth: "0",
    author: "alpha",
    score: "12",
    time: "2026-07-01T00:00:00.000Z",
    body: "Body",
  }), {
    id: "c1",
    parentId: "p1",
    depth: 0,
    author: "alpha",
    score: 12,
    time: "2026-07-01T00:00:00.000Z",
    comment: "Body",
    links: [],
  });
});

test("normalizes post metadata used when JSON retrieval fails", () => {
  assert.deepEqual(normalizeDomPost({
    id: "t3_p1",
    title: "Post title",
    author: "poster",
    time: "2026-07-01T00:00:00.000Z",
    content: "Post body",
    score: "15",
    commentCount: "22",
  }), {
    id: "p1",
    title: "Post title",
    author: "poster",
    time: "2026-07-01T00:00:00.000Z",
    content: "Post body",
    score: 15,
    commentCount: 22,
  });
});
```

- [ ] **Step 2: Run the focused test**

Run:

```powershell
node --test tests/reddit-dom.test.js
```

Expected: FAIL because `reddit-dom.js` is absent.

- [ ] **Step 3: Implement deterministic selectors and normalization**

```js
// extensions/reddit-single-post-scraper/src/reddit/reddit-dom.js
import { extractLinks } from "./reddit-json.js";

const EXPAND_LABEL = /^(view more comments|more replies|continue this thread)$/i;

function stripFullname(value) {
  return String(value ?? "").replace(/^(t1|t3)_/, "");
}

export function shouldExpandButton(text) {
  return EXPAND_LABEL.test(String(text ?? "").trim());
}

export function normalizeDomRecord(record) {
  const numericScore = Number(record.score);
  return {
    id: stripFullname(record.id),
    parentId: stripFullname(record.parentId),
    depth: Number.parseInt(record.depth, 10) || 0,
    author: record.author ?? "",
    score: Number.isFinite(numericScore) ? numericScore : "",
    time: record.time ?? "",
    comment: record.body ?? "",
    links: extractLinks(record.body),
  };
}

export function normalizeDomPost(record) {
  const score = Number(record.score);
  const commentCount = Number(record.commentCount);
  return {
    id: stripFullname(record.id),
    title: record.title ?? "",
    author: record.author ?? "",
    time: record.time ?? "",
    content: record.content ?? "",
    score: Number.isFinite(score) ? score : "",
    commentCount: Number.isFinite(commentCount) ? commentCount : "",
  };
}

function readCommentElement(element) {
  const body =
    element.querySelector('[slot="comment"]') ??
    element.querySelector('[slot="commentBody"]') ??
    element.querySelector('[data-testid="comment"]');

  return normalizeDomRecord({
    id: element.getAttribute("thingid") ?? element.id,
    parentId: element.getAttribute("parentid"),
    depth: element.getAttribute("depth"),
    author: element.getAttribute("author"),
    score: element.getAttribute("score"),
    time: element.getAttribute("created-timestamp"),
    body: body?.textContent?.trim() ?? "",
  });
}

function readPost(documentImpl, pageUrl) {
  const postElement = documentImpl.querySelector("shreddit-post");
  const idFromUrl = new URL(pageUrl).pathname.match(/\/comments\/([^/]+)/)?.[1] ?? "";
  const titleElement =
    documentImpl.querySelector("h1") ??
    documentImpl.querySelector('[slot="title"]');
  const contentElement =
    documentImpl.querySelector('shreddit-post [slot="text-body"]') ??
    documentImpl.querySelector('shreddit-post [data-post-click-location="text-body"]');
  const description = documentImpl.querySelector('meta[name="description"]');

  return normalizeDomPost({
    id: postElement?.getAttribute("thingid") ?? idFromUrl,
    title: titleElement?.textContent?.trim() ?? "",
    author: postElement?.getAttribute("author") ?? "",
    time: postElement?.getAttribute("created-timestamp") ?? "",
    content:
      contentElement?.textContent?.trim() ??
      description?.getAttribute("content") ??
      "",
    score: postElement?.getAttribute("score"),
    commentCount:
      postElement?.getAttribute("comment-count") ??
      postElement?.getAttribute("commentcount"),
  });
}

function recordsToRoots(records, postId) {
  const nodes = new Map(records.map((record) => [
    record.id,
    { ...record, replies: [] },
  ]));
  const roots = [];

  for (const node of nodes.values()) {
    const parent = nodes.get(node.parentId);
    if (parent) parent.replies.push(node);
    else if (node.parentId === postId || node.depth === 0) roots.push(node);
    else roots.push(node);
  }
  return roots;
}

export async function scrapeThreadDom({
  documentImpl = document,
  pageUrl = location.href,
  postId = "",
  signal,
  onProgress = () => {},
  maxPasses = 50,
}) {
  for (let pass = 0; pass < maxPasses; pass += 1) {
    if (signal?.aborted) throw new DOMException("Cancelled", "AbortError");
    const buttons = [...documentImpl.querySelectorAll("button")]
      .filter((button) => shouldExpandButton(button.textContent));
    if (buttons.length === 0) break;
    for (const button of buttons) button.click();
    await new Promise((resolve) => setTimeout(resolve, 250));
    onProgress({ expansionPass: pass + 1 });
  }

  const elements = [...documentImpl.querySelectorAll("shreddit-comment")];
  const records = elements
    .map(readCommentElement)
    .filter((record) => record.id);
  const post = readPost(documentImpl, pageUrl);
  const resolvedPostId = postId || post.id;
  if (!resolvedPostId) throw new Error("Unable to identify the Reddit post in the page");

  return {
    post,
    roots: recordsToRoots(records, resolvedPostId),
    complete: [...documentImpl.querySelectorAll("button")]
      .every((button) => !shouldExpandButton(button.textContent)),
  };
}
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
node --test tests/reddit-dom.test.js
```

Expected: all tests pass.

- [ ] **Step 5: Commit the fallback**

```powershell
git add extensions/reddit-single-post-scraper/src/reddit/reddit-dom.js extensions/reddit-single-post-scraper/tests/reddit-dom.test.js
git commit -m "feat: add Reddit DOM fallback"
```

### Task 7: Implement the scrape state machine and merge policy

**Files:**
- Create: `extensions/reddit-single-post-scraper/tests/scrape-controller.test.js`
- Create: `extensions/reddit-single-post-scraper/src/core/scrape-controller.js`

- [ ] **Step 1: Write failing controller tests**

```js
// extensions/reddit-single-post-scraper/tests/scrape-controller.test.js
import assert from "node:assert/strict";
import test from "node:test";
import { createScrapeController } from "../src/core/scrape-controller.js";

const post = {
  id: "p1", title: "Title", author: "poster", time: "",
  content: "", score: 1, commentCount: 2,
};

const root = {
  id: "c1", parentId: "p1", author: "alpha", time: "",
  score: 1, comment: "Root", links: [], replies: [],
};

test("completes when the primary adapter is complete", async () => {
  const controller = createScrapeController({
    primary: async () => ({ post, roots: [root], complete: true }),
    fallback: async () => { throw new Error("must not run"); },
  });

  await controller.start("https://www.reddit.com/r/x/comments/p1/title/");
  const state = controller.getState();
  assert.equal(state.status, "complete");
  assert.equal(state.comments.length, 1);
});

test("merges a fallback result and marks unresolved retrieval partial", async () => {
  const child = {
    id: "c2", parentId: "c1", author: "beta", time: "",
    score: 1, comment: "Child", links: [], replies: [],
  };
  const controller = createScrapeController({
    primary: async () => ({ post, roots: [root], complete: false }),
    fallback: async () => ({
      roots: [{ ...root, replies: [child] }],
      complete: false,
    }),
  });

  await controller.start("https://www.reddit.com/r/x/comments/p1/title/");
  const state = controller.getState();
  assert.equal(state.status, "partial");
  assert.deepEqual(state.comments.map((row) => row.commentId), ["c1", "c2"]);
});

test("uses DOM post metadata when structured retrieval fails", async () => {
  const controller = createScrapeController({
    primary: async () => { throw new Error("blocked"); },
    fallback: async () => ({ post, roots: [root], complete: true }),
  });

  await controller.start("https://www.reddit.com/r/x/comments/p1/title/");
  const state = controller.getState();
  assert.equal(state.status, "complete");
  assert.equal(state.post.id, "p1");
});
```

- [ ] **Step 2: Run the controller test**

Run:

```powershell
node --test tests/scrape-controller.test.js
```

Expected: FAIL because the controller is absent.

- [ ] **Step 3: Implement the controller**

```js
// extensions/reddit-single-post-scraper/src/core/scrape-controller.js
import {
  flattenCommentTree,
  summarizeComments,
} from "./comment-tree.js";

function mergeRoots(primaryRoots, fallbackRoots) {
  const all = new Map();

  function ingest(node) {
    if (!node?.id) return;
    const existing = all.get(node.id);
    if (!existing) {
      all.set(node.id, { ...node, replies: [] });
    } else {
      all.set(node.id, {
        ...existing,
        ...node,
        replies: existing.replies,
      });
    }
    for (const reply of node.replies ?? []) ingest(reply);
  }

  for (const root of [...(primaryRoots ?? []), ...(fallbackRoots ?? [])]) {
    ingest(root);
  }

  const roots = [];
  for (const node of all.values()) node.replies = [];
  for (const node of all.values()) {
    const parent = all.get(node.parentId);
    if (parent) parent.replies.push(node);
    else roots.push(node);
  }
  return roots;
}

export function createScrapeController({ primary, fallback }) {
  let abortController;
  let state = {
    status: "idle",
    phase: "ready",
    discovered: 0,
    post: null,
    comments: [],
    summary: null,
    error: "",
  };

  function update(patch) {
    state = { ...state, ...patch };
  }

  return {
    getState() {
      return structuredClone(state);
    },

    cancel() {
      abortController?.abort();
    },

    async start(pageUrl) {
      if (state.status === "running") return;
      abortController = new AbortController();
      update({
        status: "running",
        phase: "structured",
        discovered: 0,
        post: null,
        comments: [],
        summary: null,
        error: "",
      });

      try {
        const progress = ({ discovered = state.discovered } = {}) =>
          update({ discovered });
        let primaryResult;
        let primaryError;
        try {
          primaryResult = await primary({
            pageUrl,
            signal: abortController.signal,
            onProgress: progress,
          });
        } catch (error) {
          if (error?.name === "AbortError") throw error;
          primaryError = error;
        }

        let post;
        let roots;
        let complete;
        if (!primaryResult) {
          update({ phase: "dom-fallback" });
          const fallbackResult = await fallback({
            pageUrl,
            signal: abortController.signal,
            onProgress: progress,
          });
          if (!fallbackResult.post?.id) throw primaryError;
          post = fallbackResult.post;
          roots = fallbackResult.roots;
          complete = fallbackResult.complete;
        } else if (!primaryResult.complete) {
          update({ phase: "dom-fallback" });
          const fallbackResult = await fallback({
            pageUrl,
            postId: primaryResult.post.id,
            signal: abortController.signal,
            onProgress: progress,
          });
          post = primaryResult.post;
          roots = mergeRoots(primaryResult.roots, fallbackResult.roots);
          complete = false;
        } else {
          post = primaryResult.post;
          roots = primaryResult.roots;
          complete = true;
        }

        const comments = flattenCommentTree(post.id, roots);
        update({
          status: complete ? "complete" : "partial",
          phase: "finished",
          post,
          comments,
          summary: summarizeComments(comments),
          discovered: comments.length,
        });
      } catch (error) {
        if (error?.name === "AbortError") {
          update({
            status: "cancelled",
            phase: "cancelled",
            post: null,
            comments: [],
            summary: null,
            error: "",
          });
          return;
        }
        update({
          status: "failed",
          phase: "failed",
          post: null,
          comments: [],
          summary: null,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    },
  };
}
```

- [ ] **Step 4: Add cancellation and failure tests**

Append:

```js
test("cancellation clears non-exportable results", async () => {
  let rejectRequest;
  const controller = createScrapeController({
    primary: ({ signal }) => new Promise((resolve, reject) => {
      rejectRequest = () => reject(new DOMException("Cancelled", "AbortError"));
      signal.addEventListener("abort", rejectRequest, { once: true });
    }),
    fallback: async () => ({ roots: [], complete: false }),
  });

  const running = controller.start("https://www.reddit.com/r/x/comments/p1/");
  controller.cancel();
  await running;
  assert.deepEqual(controller.getState(), {
    status: "cancelled",
    phase: "cancelled",
    discovered: 0,
    post: null,
    comments: [],
    summary: null,
    error: "",
  });
});
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
node --test tests/scrape-controller.test.js
```

Expected: all tests pass.

- [ ] **Step 6: Commit orchestration**

```powershell
git add extensions/reddit-single-post-scraper/src/core/scrape-controller.js extensions/reddit-single-post-scraper/tests/scrape-controller.test.js
git commit -m "feat: orchestrate Reddit scraping"
```

### Task 8: Connect the content script to Chrome messaging

**Files:**
- Create: `extensions/reddit-single-post-scraper/tests/content-main.test.js`
- Create: `extensions/reddit-single-post-scraper/src/content-main.js`

- [ ] **Step 1: Write a failing message-handler test**

```js
// extensions/reddit-single-post-scraper/tests/content-main.test.js
import assert from "node:assert/strict";
import test from "node:test";
import { createMessageHandler } from "../src/content-main.js";

test("exposes state, start, and cancellation messages", async () => {
  const calls = [];
  const controller = {
    getState: () => ({ status: "idle" }),
    start: async (url) => calls.push(["start", url]),
    cancel: () => calls.push(["cancel"]),
  };
  const handler = createMessageHandler({
    controller,
    pageUrl: "https://www.reddit.com/r/x/comments/p1/title/",
  });

  assert.deepEqual(await handler({ type: "GET_STATE" }), { status: "idle" });
  await handler({ type: "START" });
  await handler({ type: "CANCEL" });
  assert.deepEqual(calls, [
    ["start", "https://www.reddit.com/r/x/comments/p1/title/"],
    ["cancel"],
  ]);
});
```

- [ ] **Step 2: Run the focused test**

Run:

```powershell
node --test tests/content-main.test.js
```

Expected: FAIL because `createMessageHandler` is absent.

- [ ] **Step 3: Implement the message boundary**

```js
// extensions/reddit-single-post-scraper/src/content-main.js
import { createScrapeController } from "./core/scrape-controller.js";
import { scrapeThreadDom } from "./reddit/reddit-dom.js";
import { scrapeThreadJson } from "./reddit/reddit-json.js";

export function createMessageHandler({ controller, pageUrl }) {
  return async function handle(message) {
    if (message?.type === "GET_STATE") return controller.getState();
    if (message?.type === "START") {
      await controller.start(pageUrl);
      return controller.getState();
    }
    if (message?.type === "CANCEL") {
      controller.cancel();
      return controller.getState();
    }
    throw new Error(`Unsupported message type: ${message?.type ?? ""}`);
  };
}

if (globalThis.chrome?.runtime?.onMessage) {
  const controller = createScrapeController({
    primary: scrapeThreadJson,
    fallback: scrapeThreadDom,
  });
  const handle = createMessageHandler({
    controller,
    pageUrl: location.href,
  });

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    handle(message)
      .then((value) => sendResponse({ ok: true, value }))
      .catch((error) => sendResponse({
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      }));
    return true;
  });
}
```

- [ ] **Step 4: Run the focused test**

Run:

```powershell
node --test tests/content-main.test.js
```

Expected: all tests pass.

- [ ] **Step 5: Commit messaging**

```powershell
git add extensions/reddit-single-post-scraper/src/content-main.js extensions/reddit-single-post-scraper/tests/content-main.test.js
git commit -m "feat: connect scraper to extension messages"
```

### Task 9: Build the popup workflow and local download

**Files:**
- Create: `extensions/reddit-single-post-scraper/tests/view-model.test.js`
- Create: `extensions/reddit-single-post-scraper/src/popup/view-model.js`
- Modify: `extensions/reddit-single-post-scraper/src/popup/popup.html`
- Modify: `extensions/reddit-single-post-scraper/src/popup/popup.css`
- Modify: `extensions/reddit-single-post-scraper/src/popup/popup.js`

- [ ] **Step 1: Write failing view-model tests**

```js
// extensions/reddit-single-post-scraper/tests/view-model.test.js
import assert from "node:assert/strict";
import test from "node:test";
import { toViewModel } from "../src/popup/view-model.js";

test("enables export for complete and partial results only", () => {
  assert.equal(toViewModel({
    status: "complete", post: { title: "Title" },
    discovered: 30, summary: { extractedCount: 30 },
  }).canExport, true);
  assert.equal(toViewModel({
    status: "partial", post: { title: "Title" },
    discovered: 20, summary: { extractedCount: 20 },
  }).warning, "部分回复未能补齐，导出将只包含已获取数据。");
  assert.equal(toViewModel({ status: "cancelled" }).canExport, false);
});
```

- [ ] **Step 2: Run the focused test**

Run:

```powershell
node --test tests/view-model.test.js
```

Expected: FAIL because `view-model.js` is absent.

- [ ] **Step 3: Implement the pure view model**

```js
// extensions/reddit-single-post-scraper/src/popup/view-model.js
export function toViewModel(state = {}) {
  const terminalWithData =
    (state.status === "complete" || state.status === "partial") &&
    state.post &&
    state.comments?.length > 0;

  return {
    title: state.post?.title ?? "当前 Reddit 帖子",
    status: state.status ?? "idle",
    phase: state.phase ?? "ready",
    discovered: state.discovered ?? 0,
    summary: state.summary,
    error: state.error ?? "",
    warning: state.status === "partial"
      ? "部分回复未能补齐，导出将只包含已获取数据。"
      : "",
    canStart: state.status !== "running",
    canCancel: state.status === "running",
    canExport: Boolean(terminalWithData),
  };
}
```

- [ ] **Step 4: Replace the popup markup**

```html
<!-- extensions/reddit-single-post-scraper/src/popup/popup.html -->
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Reddit Single-Post Scraper</title>
    <link rel="stylesheet" href="./popup.css">
  </head>
  <body>
    <main>
      <header>
        <span class="eyebrow">REDDIT SINGLE-POST SCRAPER</span>
        <h1 id="post-title">正在检测当前帖子…</h1>
      </header>
      <section class="status-card" aria-live="polite">
        <strong id="status-label">准备就绪</strong>
        <span id="progress">已获取 0 条评论</span>
        <p id="warning" hidden></p>
        <p id="error" hidden></p>
      </section>
      <section id="summary" class="summary" hidden>
        <span>实际提取 <strong id="extracted">0</strong></span>
        <span>顶层 <strong id="roots">0</strong></span>
        <span>回复 <strong id="replies">0</strong></span>
        <span>最深 <strong id="depth">0</strong></span>
      </section>
      <div class="actions">
        <button id="start">抓取全部评论</button>
        <button id="cancel" class="secondary" hidden>取消</button>
        <button id="export" disabled>导出增强 CSV</button>
      </div>
      <footer>数据仅在当前浏览器中处理</footer>
    </main>
    <script type="module" src="./popup.js"></script>
  </body>
</html>
```

- [ ] **Step 5: Implement popup messaging, polling, and download**

```js
// extensions/reddit-single-post-scraper/src/popup/popup.js
import { buildCsv } from "../core/csv-export.js";
import { buildCsvFilename } from "../core/filename.js";
import { toViewModel } from "./view-model.js";

const elements = Object.fromEntries([
  "post-title", "status-label", "progress", "warning", "error",
  "summary", "extracted", "roots", "replies", "depth",
  "start", "cancel", "export",
].map((id) => [id, document.getElementById(id)]));

let tabId;
let latestState;
let pollTimer;

async function send(type) {
  if (tabId == null) throw new Error("没有可用的当前标签页");
  const response = await chrome.tabs.sendMessage(tabId, { type });
  if (!response?.ok) throw new Error(response?.error || "插件页面通信失败");
  return response.value;
}

function render(state) {
  latestState = state;
  const view = toViewModel(state);
  elements["post-title"].textContent = view.title;
  elements["status-label"].textContent = view.status;
  elements.progress.textContent = `已获取 ${view.discovered} 条评论`;
  elements.warning.hidden = !view.warning;
  elements.warning.textContent = view.warning;
  elements.error.hidden = !view.error;
  elements.error.textContent = view.error;
  elements.start.disabled = !view.canStart;
  elements.cancel.hidden = !view.canCancel;
  elements.export.disabled = !view.canExport;

  elements.summary.hidden = !view.summary;
  if (view.summary) {
    elements.extracted.textContent = view.summary.extractedCount;
    elements.roots.textContent = view.summary.rootCount;
    elements.replies.textContent = view.summary.replyCount;
    elements.depth.textContent = view.summary.maxDepth;
  }
}

async function refresh() {
  render(await send("GET_STATE"));
  if (latestState.status === "running") {
    pollTimer = setTimeout(refresh, 500);
  }
}

elements.start.addEventListener("click", async () => {
  clearTimeout(pollTimer);
  void send("START");
  await refresh();
});

elements.cancel.addEventListener("click", async () => {
  await send("CANCEL");
  await refresh();
});

elements.export.addEventListener("click", () => {
  const csv = buildCsv({
    post: latestState.post,
    comments: latestState.comments,
  });
  const url = URL.createObjectURL(new Blob([csv], {
    type: "text/csv;charset=utf-8",
  }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = buildCsvFilename(latestState.post.title);
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
});

try {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  tabId = tab?.id;
  await refresh();
} catch (error) {
  render({
    status: "failed",
    error: "请打开一个具体的 Reddit 帖子后重试。",
  });
}
```

- [ ] **Step 6: Complete the independent popup styling**

Replace `src/popup/popup.css` with:

```css
:root {
  font-family: Inter, "Segoe UI", sans-serif;
  color: #18212b;
  background: #f4f6f8;
}

* { box-sizing: border-box; }
body { width: 380px; margin: 0; }
main { padding: 18px; }
.eyebrow { color: #586574; font-size: 10px; letter-spacing: .12em; }
h1 { margin: 6px 0 14px; font-size: 17px; line-height: 1.35; }
.status-card {
  display: grid;
  gap: 6px;
  padding: 14px;
  border: 1px solid #dfe4e9;
  border-radius: 12px;
  background: white;
}
.status-card span, footer { color: #697585; font-size: 12px; }
#warning { color: #8a5b00; }
#error { color: #a12828; }
.summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin: 12px 0;
  font-size: 12px;
}
.actions { display: grid; gap: 8px; margin-top: 14px; }
button {
  min-height: 38px;
  border: 0;
  border-radius: 9px;
  background: #ff4f1f;
  color: white;
  font-weight: 700;
  cursor: pointer;
}
button.secondary { background: #53606d; }
button:disabled { cursor: not-allowed; opacity: .45; }
footer { margin-top: 12px; text-align: center; }
```

- [ ] **Step 7: Run popup and full automated tests**

Run:

```powershell
npm test
```

Expected: every Node test passes.

Reload the unpacked extension in `chrome://extensions`.

Expected: the popup shows the independent three-stage workflow, and it does not reuse Adlicio branding or assets.

- [ ] **Step 8: Commit the popup**

```powershell
git add extensions/reddit-single-post-scraper/src/popup extensions/reddit-single-post-scraper/tests/view-model.test.js
git commit -m "feat: add Reddit scraper popup workflow"
```

### Task 10: Document installation and perform real-post acceptance

**Files:**
- Create: `extensions/reddit-single-post-scraper/README.md`
- Modify only if a test proves a defect:
  - `extensions/reddit-single-post-scraper/src/reddit/reddit-json.js`
  - `extensions/reddit-single-post-scraper/src/reddit/reddit-dom.js`
  - `extensions/reddit-single-post-scraper/src/core/scrape-controller.js`
- Test output: user-selected temporary download location; do not commit exported comments

- [ ] **Step 1: Write the user-facing README**

```markdown
# Reddit Single-Post Scraper

本地 Chrome 扩展：抓取当前 Reddit 帖子的公开评论并导出增强 CSV。

## 安装

1. 打开 `chrome://extensions`。
2. 开启“开发者模式”。
3. 点击“加载已解压的扩展程序”。
4. 选择本文件夹。

## 使用

1. 打开一个具体的 `www.reddit.com/r/.../comments/...` 帖子。
2. 点击扩展图标。
3. 点击“抓取全部评论”。
4. 等待状态变为 `complete`；若显示 `partial`，导出只包含已获取数据。
5. 点击“导出增强 CSV”。

## 隐私

评论和帖子数据只在当前浏览器会话中处理，不上传到本项目或第三方服务器。本扩展不读取 Cookie、令牌或非 Reddit 网站内容。

请仅抓取你有权访问的公开内容，并遵守 Reddit 规则和适用法律。
```

- [ ] **Step 2: Run all deterministic checks**

Run:

```powershell
Set-Location "D:\八爪鱼cli Project\extensions\reddit-single-post-scraper"
npm test
```

Expected: all tests pass with zero failures.

Run:

```powershell
Get-Content -Raw manifest.json | ConvertFrom-Json | Out-Null
```

Expected: command exits successfully.

- [ ] **Step 3: Test the approved real Reddit post**

Open:

```text
https://www.reddit.com/r/desksetup/comments/1tbschi/i_thought_screenbars_were_overhyped_but_this_one/
```

Reload the extension, start scraping, and record:

- terminal status (`complete` or `partial`);
- Reddit-reported comment count;
- actual extracted count;
- root count, reply count, and maximum depth;
- whether extracted count exceeds 20 when the currently accessible post contains more than 20 public comments.

Expected: no artificial 20-comment limit. If Reddit prevents complete retrieval, the popup must show `partial` and still allow explicit partial export.

- [ ] **Step 4: Compare the first seven columns with the reference**

Reference:

```text
C:\Users\Eddie.J.Lu\Downloads\付费插件获取.csv
```

Check:

```powershell
$reference = Import-Csv -LiteralPath 'C:\Users\Eddie.J.Lu\Downloads\付费插件获取.csv'
$exportPath = (Get-ChildItem -LiteralPath 'C:\Users\Eddie.J.Lu\Downloads' -Filter 'I thought screenbars were overhyped*_2026-07-23.csv' | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
$export = Import-Csv -LiteralPath $exportPath
$reference[0].PSObject.Properties.Name
$export[0].PSObject.Properties.Name
```

Expected:

- exported first seven headers are `Author`, `Time`, `Score`, `Thread Level`, `Is Reply`, `Comment`, `Links`;
- remaining headers match the approved seven appended fields;
- parent/child rows remain in parent-first order;
- multiline text, emoji, and links open correctly in Excel.

- [ ] **Step 5: Verify privacy and failure states manually**

Perform these checks:

1. Open a non-Reddit tab and click the extension: it must instruct the user to open a Reddit post.
2. Start a scrape and cancel it: export must remain disabled.
3. Temporarily disable the network after the initial page loads and start a scrape: status must become `partial` or `failed`, never false `complete`.
4. Inspect `chrome://extensions` permissions: only `www.reddit.com` site access appears.
5. Search the source for external collection endpoints:

```powershell
rg -n "tryadlicio|analytics|telemetry|Authorization|Cookie|Bearer" src manifest.json
```

Expected: no matches.

- [ ] **Step 6: Commit documentation and any test-proven fixes**

```powershell
git add extensions/reddit-single-post-scraper
git commit -m "docs: add Reddit scraper installation and acceptance"
```

### Task 11: Final verification and handoff

**Files:**
- Verify only; do not create build artifacts or commit downloaded comment data

- [ ] **Step 1: Run the complete test suite from the extension root**

```powershell
Set-Location "D:\八爪鱼cli Project\extensions\reddit-single-post-scraper"
npm test
```

Expected: all tests pass.

- [ ] **Step 2: Inspect repository state**

```powershell
Set-Location "D:\八爪鱼cli Project"
git status --short
git log --oneline -12
```

Expected: no unintended CSV exports, CRX packages, `node_modules`, browser profiles, tokens, or unrelated files are staged.

- [ ] **Step 3: Apply the verification-before-completion skill**

Required checks:

- cite the exact automated test command and fresh result;
- cite the real-post acceptance result and whether it was `complete` or `partial`;
- confirm the enhanced CSV header order;
- confirm Chrome loads the unpacked extension without errors;
- confirm no comments or session data are uploaded.

- [ ] **Step 4: Present the deliverable**

Provide a clickable link to:

```text
D:\八爪鱼cli Project\extensions\reddit-single-post-scraper
```

State any Reddit-side limitation plainly. Do not claim “all comments” when the run status was `partial`.
