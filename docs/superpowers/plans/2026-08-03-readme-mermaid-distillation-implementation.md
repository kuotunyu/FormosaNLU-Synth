# FormosaNLU README Mermaid Distillation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以兩張 GitHub-native Mermaid diagrams 說清楚資料 pipeline 與 paired cross-family evidence，並再縮短 README，而不丟失任何可驗證的研究證據。

**Architecture:** README 只保留兩個視覺層級：第一張圖描述 data artifact lifecycle，第二張圖描述 evaluation evidence lifecycle。既有 static pipeline figure 移入 progressive disclosure；`scripts.verify_readme` 新增小型 structural contract，確保未來修改不會默默移除或合併這兩張圖。

**Tech Stack:** GitHub Flavored Markdown、Mermaid flowchart、Python 3.11、pytest、Ruff、既有 README/reproduce/closeout/contributors gates。

## Global Constraints

- 不修改 Dataset rows、model artifacts、prompt、parser、threshold、seed、training config、evaluation contract 或 report numbers。
- 不重跑 generation、training 或 evaluation，不修改 external publications 與 `v1.2.1` tag。
- README 以正體中文（台灣）為主，專有名詞保留原文。
- `interview.md` 維持 untracked/excluded，絕不 stage、commit 或 push。
- Git author/committer 必須是 `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`，不得有 `Co-Authored-By`；GitHub Contributors 只能有 `kuotunyu`。

## File Map

| File | Responsibility |
| --- | --- |
| `README.md` | 精簡公開敘事，承載兩張 Mermaid 與既有 evidence/artifact links |
| `scripts/verify_readme.py` | 驗證 Mermaid 數量與兩個流程的必要 markers |
| `tests/test_m12_artifacts.py` | 針對 README diagram structural contract 做 positive/negative regression tests |
| `docs/superpowers/specs/2026-08-03-readme-mermaid-distillation-design.md` | 已核准的資訊架構與不變邊界 |
| `docs/superpowers/plans/2026-08-03-readme-mermaid-distillation-implementation.md` | 執行清單與最後 verification record |

---

### Task 1: 建立 Mermaid structural regression contract

**Files:**
- Modify: `tests/test_m12_artifacts.py`
- Modify: `scripts/verify_readme.py`

**Interfaces:**
- Produces: `readme_diagram_checks(readme: str) -> dict[str, bool]`
- Consumes: raw UTF-8 contents of `README.md`

- [x] **Step 1: 先寫 failing tests**

在 `tests/test_m12_artifacts.py` 匯入 `readme_diagram_checks`，加入：

```python
def test_readme_diagram_checks_require_two_focused_flows() -> None:
    readme = """```mermaid
flowchart LR
MASSIVE --> F1-F4 --> F5-F6 --> F7
```
```mermaid
flowchart TB
real_only --> 2,974-row --> hierarchical paired --> cross-family
real_syn_filtered --> 2,974-row
```
"""
    assert all(readme_diagram_checks(readme).values())


def test_readme_diagram_checks_reject_one_overloaded_diagram() -> None:
    readme = """```mermaid
flowchart LR
MASSIVE --> F1-F4 --> F5-F6 --> F7 --> real_only --> cross-family
```
"""
    assert not readme_diagram_checks(readme)["exactly two Mermaid diagrams"]
```

- [x] **Step 2: 執行 focused tests，確認 RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_m12_artifacts.py -k readme_diagram_checks -q
```

Expected: collection/import fails because `readme_diagram_checks` does not exist.

- [x] **Step 3: 實作最小 verifier helper**

在 `scripts/verify_readme.py` 加入：

```python
def readme_diagram_checks(readme: str) -> dict[str, bool]:
    return {
        "exactly two Mermaid diagrams": readme.count("```mermaid") == 2,
        "data pipeline diagram": all(
            marker in readme for marker in ("MASSIVE", "F1-F4", "F5-F6", "F7")
        ),
        "paired evidence diagram": all(
            marker in readme
            for marker in ("real_only", "real_syn_filtered", "2,974-row", "hierarchical paired", "cross-family")
        ),
    }
```

在 `verify_readme` 中把三個結果加入 `checks`，不更動既有 report-derived checks。

- [x] **Step 4: 執行 focused tests，確認 GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_m12_artifacts.py -k readme_diagram_checks -q
```

Expected: 2 tests pass.

---

### Task 2: 精簡 README 並加入兩張 Mermaid diagrams

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-08-03-readme-mermaid-distillation-design.md`
- Produces: two GitHub-renderable Mermaid flowcharts and a shorter public README

- [x] **Step 1: 再壓縮 first-screen 與設定敘事**

刪除公開產物表後重複的 verification prose；把 `## 任務與設定` 改成一段 compact contract，不重複 hero 已說過的 Dataset、hardware 與 family positioning。保留 `MASSIVE zh-TW`、60 intents、55 slot types、`min(20, available)`、teacher、students、judge、RTX 4090 與 `$0`。

- [x] **Step 2: 加入資料產製與品質控管圖**

在 `## 方法` 下加入 `### 資料產製與品質控管` 與 `flowchart LR`。圖中必須包含 frozen split、four recipes、local teacher、11,264 generated、F1-F4、F5-F6，以及 3,760-row primary corpus / F7 / 3,754-row public Dataset 的正確分支。

- [x] **Step 3: 加入成對實驗與跨模型驗證圖**

緊接第一張圖加入 `### 成對實驗與跨模型驗證` 與 `flowchart TB`。圖中必須包含 shared frozen contract、Gemma/Phi、`real_only` / `real_syn_filtered`、seeds 42/43/44、2,974-row strict evaluation、hierarchical paired bootstrap、McNemar + Holm 與 preregistered cross-family criterion。

- [x] **Step 4: 移除 Mermaid 已承接的重複內容**

把 generation recipes table 改為一行 method summary + `docs/DESIGN.md` link；thresholds 改為單行 compact list。把 M11、reproduction verification 與 project status 中重複的完成說明各保留一次。

- [x] **Step 5: 將 static pipeline figure 移入 progressive disclosure**

使用：

```markdown
<details>
<summary><strong>查看 publication static pipeline figure</strong></summary>

![FormosaNLU pipeline](assets/m12_pipeline.png)

</details>
```

保留 `assets/m12_pipeline.png` marker，避免 publication asset 失聯。

- [x] **Step 6: 執行 README structural 與 evidence gates**

Run:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_readme
.\.venv\Scripts\python.exe -m scripts.verify_reproduce
.\.venv\Scripts\python.exe scripts/verify_closeout.py
```

Expected: all pass; README line count is less than 686.

---

### Task 3: 驗證 Mermaid、完整 gates 與公開 render

**Files:**
- Modify: `docs/superpowers/plans/2026-08-03-readme-mermaid-distillation-implementation.md`（勾選完成步驟並記錄結果）
- Verify only: all files above

**Interfaces:**
- Consumes: final README and verifier contract
- Produces: green local gates, verified GitHub render, sole-contributor audit

- [x] **Step 1: 驗證 Mermaid source**

抽取兩個 Mermaid blocks，確認每張圖 node 不超過 12 個、所有 `classDef` 都含 `color:`，並使用可用的 Mermaid validator；若本機 validator 不可用，以 GitHub rendered page 作為 authoritative render check，且在 execution notes 如實記錄。

- [x] **Step 2: 執行 formatting 與完整 gate suite**

Run:

```powershell
git diff --check
.\.venv\Scripts\python.exe -m scripts.check_gates --quiet
```

Expected: Ruff、full pytest、README、contributors、reproduce、closeout 全部通過。

- [x] **Step 3: 執行 Impeccable detector**

Run exactly once after the README is finished:

```powershell
node C:\Users\3Hml\.codex\skills\impeccable\scripts\detect.mjs --json README.md
```

Expected: no blocking issue; record any advisory without changing research content.

- [x] **Step 4: 稽核 diff 與 private boundary**

Run:

```powershell
git status --short
git diff --stat
git ls-files --error-unmatch interview.md
```

Expected: only approved README/verifier/test/spec/plan files are changed; the final command fails because `interview.md` is not tracked.

- [ ] **Step 5: Commit、push 與公開頁面驗收**

設定四個 Git identity environment variables為指定的 `kuotunyu` identity，stage only approved files，commit without trailers，push `main`。在 public repository 實際檢查兩張 Mermaid、badges、images、links、tables 與 `<details>`。

- [ ] **Step 6: 稽核 authorship 與 immutable tag**

透過 GitHub API 確認新 commits 的 author/committer 都是 `kuotunyu`、Contributors 只有 `kuotunyu`，並確認 `v1.2.1^{}` 仍是 `1f42372e97c98212f192362ec441c034815b37d5`。

## Self-review

- **Spec coverage:** Task 1 防止圖表回歸；Task 2 完成兩張圖、README 精簡與 static asset progressive disclosure；Task 3 覆蓋 Mermaid render、完整 gates、private boundary、Git identity、Contributors 與 immutable tag。
- **Placeholder scan:** 所有步驟都有明確檔案、指令與 expected result，沒有延後決策或未定欄位。
- **Interface consistency:** `readme_diagram_checks(readme: str) -> dict[str, bool]` 同時由 focused tests 與 production verifier 使用；README labels 與 helper markers 完全一致。
- **Scope boundary:** 只改 presentation 與 verifier contract，不修改任何研究產物或 external publication。
