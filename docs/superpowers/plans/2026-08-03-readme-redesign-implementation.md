# FormosaNLU README Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓第一次造訪 GitHub 的讀者在十秒內理解 FormosaNLU 的研究問題、跨 model-family 結果與可直接使用的公開 artifacts，同時修復 DOI badge 並保留完整可驗證 evidence。

**Architecture:** 以 README 首屏作為結論層，後續章節作為 evidence 層；使用 `<details>` 對低頻細節做 progressive disclosure。DOI 顯示改為穩定的 Shields.io static badge，closeout verifier 仍從 Zenodo report 產生並驗證 exact version DOI。

**Tech Stack:** GitHub Flavored Markdown、Python 3.11、pytest、Ruff、GitHub Markdown API、既有 `scripts.verify_readme`／`scripts.verify_closeout` gates。

## Global Constraints

- 公開 prose 以正體中文（台灣）為主，技術專有名詞直接使用原文。
- 不修改 Dataset rows、model tensors、frozen corpus、prompt、parser、threshold、seeds、train config、evaluation contract 或 report 數字。
- 不重新執行 generation、training 或 evaluation；不移動 `v1.2.1` tag。
- 不修改 Hugging Face artifacts、Zenodo record 或 DOI `10.5281/zenodo.21767493`。
- 私有 `interview.md` 不得被 stage、commit 或 push。
- Git author/committer 僅能是 `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`，不得有 `Co-Authored-By`；GitHub Contributors 必須只有 `kuotunyu`。

## File Map

| File | Responsibility |
| --- | --- |
| `README.md` | Public first impression, results, artifacts, methods, caveats, reproduction, citation |
| `scripts/verify_closeout.py` | Derive and verify the exact stable DOI badge plus citation backlinks |
| `tests/test_verify_closeout.py` | Regression test for DOI badge markup and exact report-derived DOI |
| `docs/superpowers/specs/2026-08-03-readme-redesign-design.md` | Approved redesign contract |
| `docs/superpowers/plans/2026-08-03-readme-redesign-implementation.md` | Execution checklist and verification record |

---

### Task 1: Replace the fragile DOI badge contract

**Files:**
- Modify: `tests/test_verify_closeout.py:153-183`
- Modify: `scripts/verify_closeout.py:232-236`

**Interfaces:**
- Consumes: `doi` and `doi_url` from `reports/v121_zenodo.json`
- Produces: exact Markdown badge `[![DOI](https://img.shields.io/badge/DOI-<encoded DOI>-1682D4)](<doi_url>)`

- [x] **Step 1: Change the positive test to the stable badge and keep an explicit rejection case**

Use this expected Markdown in `test_accepts_exact_doi_backlinks`:

```python
badge = (
    "[![DOI](https://img.shields.io/badge/DOI-"
    f"{doi.replace('-', '--').replace('/', '%2F')}-1682D4)]({doi_url})"
)
```

Add a focused test that writes the old `zenodo.org/badge/DOI/...svg` markup and asserts the `doi_backlinks` check fails with `README.md` in `observed`.

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_verify_closeout.py -k doi_backlinks -q
```

Expected: the new stable-badge acceptance test fails because the verifier still requires the old Zenodo SVG markup.

- [x] **Step 3: Generate the stable badge from the report-derived DOI**

In `_doi_backlink_check`, replace the old badge construction with:

```python
badge_doi = doi.replace("-", "--").replace("/", "%2F")
badge = (
    "[![DOI](https://img.shields.io/badge/DOI-"
    f"{badge_doi}-1682D4)]({doi_url})"
)
```

Do not loosen the checks for `## 引用`, `record_url`, `CITATION.cff`, handoff, or release notes.

- [x] **Step 4: Run focused tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_verify_closeout.py -k doi_backlinks -q
```

Expected: all DOI backlink tests pass.

- [x] **Step 5: Commit the verifier regression fix**

Stage only the two files, set all four Git identity environment variables to the required `kuotunyu` identity, and commit:

```powershell
git add -- tests/test_verify_closeout.py scripts/verify_closeout.py
git commit -m "Test: stabilize DOI badge verification"
```

Expected: commit message has no trailer and both author and committer are `kuotunyu`.

---

### Task 2: Rebuild the README first screen around proof

**Files:**
- Modify: `README.md:1-120`

**Interfaces:**
- Consumes: verifier-backed values already present in README and tracked reports
- Produces: title, concise positioning, five-link badge row, three headline findings, main-results image, public artifact table

- [x] **Step 1: Replace the title and dense status block**

Use this hierarchy:

```markdown
# FormosaNLU — Synthetic Data Distillation for Low-resource NLU

以本機 open-weight teacher 生成與過濾 synthetic data，並在 20-shot
MASSIVE `zh-TW` 上驗證它能否改善 intent classification、slot filling 與
strict JSON output。效果已在 Gemma 與 Phi-4-mini 兩個 student model
families 上以相同 paired contract 複製。
```

Do not bold or foreground 「正體中文（台灣）」；the `zh-TW` identifier is enough in the hero.

- [x] **Step 2: Add the compact badge row**

Add badges for Release, Dataset, Model, DOI, and MIT. The DOI badge must exactly match Task 1. Every badge must have a direct destination URL; no badge may be decorative-only.

- [x] **Step 3: Add the three headline findings**

Use a compact table or bullets containing only verifier-backed facts:

```markdown
| 核心證據 | 結果 |
| --- | --- |
| Gemma，3 paired seeds | intent `+4.14 pp`；joint exact match `+3.86 pp` |
| Phi-4-mini replication | intent `+5.09 pp`；joint exact match `+4.71 pp` |
| Local-first pipeline | `11,264` generated → `3,760` frozen primary；單張 RTX 4090；`$0` API spend |
```

Immediately follow it with the existing `m12_main_results.png` asset, using
the README-relative path `assets/m12_main_results.png`.

- [x] **Step 4: Move public artifacts ahead of implementation detail**

Retain the four existing public artifact URLs, anonymous verification status, Dataset load example, Dataset row count `3,754`, and Model Card link. Replace the long milestone status paragraph with one concise line stating that the project and local GPU stages are complete and public artifacts passed anonymous download/hash verification.

- [x] **Step 5: Keep the real-output demo, but tighten its introduction**

Retain both verbatim evidence examples required by `scripts.verify_readme`, the `0/5` versus `5/5 valid JSON` finding, the prompt asymmetry caveat (`zero-shot` and `catalog`), and the report link. Remove repeated explanations already made in the hero.

- [x] **Step 6: Run README and closeout verifiers**

Run:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_readme
.\.venv\Scripts\python.exe scripts/verify_closeout.py
```

Expected: both pass; every headline number remains traceable to tracked reports.

- [x] **Step 7: Commit the first-screen redesign**

Stage only `README.md`, set exact Git identity, and commit:

```powershell
git add -- README.md
git commit -m "Docs: sharpen README first impression"
```

Expected: no experiment or artifact file is staged.

---

### Task 3: Distill the evidence layer without losing research integrity

**Files:**
- Modify: `README.md:121-686`

**Interfaces:**
- Consumes: existing result tables, report links, images, caveats, commands, citation, licenses
- Produces: shorter hierarchy with progressive disclosure and no duplicated conclusion paragraphs

- [x] **Step 1: Remove the standalone `TL;DR` duplication**

Merge its unique uncertainty and cross-family caveats into the corresponding result subsections. Do not remove:

- three-seed descriptive intervals;
- hierarchical paired bootstrap evidence;
- the preregistered Phi criterion;
- M19 `seed 42（n=1）`, `2.5 percentage points`, and no recipe-level causal claim.

- [x] **Step 2: Reorder results from strongest evidence to diagnostic detail**

Use this order inside `## 實驗結果`:

1. three-seed paired results;
2. cross-family replication;
3. seed-42 primary matrix and gap closure;
4. M19 equal-N negative result;
5. per-intent diagnostics.

Keep the exact verifier-required Markdown rows unchanged even when they move.

- [x] **Step 3: Fold low-frequency tables**

Wrap the per-intent table, seed-42 robustness probe breakdown, and long reproduction environment/command detail in descriptive `<details>` blocks. Each `<summary>` must state what evidence is inside; examples:

```markdown
<details>
<summary>查看各 intent 的完整變化</summary>

...existing verifier-backed table...

</details>
```

Do not wrap the main three-seed table, cross-family replication, core method diagram, limitations, or citation.

- [x] **Step 4: Consolidate method and cost language**

State each hardware/runtime/resource fact once. Preserve all verifier-required markers: primary training hours, evaluation hours, core/auxiliary/total GPU hours, TDP envelope, generation count, accepted count, F7 release count, and random-stratum miss rate.

- [x] **Step 5: Replace the completed Roadmap checklist with a closeout statement**

Keep one concise paragraph indicating research, publication, DOI, Dataset, Model, portability, robustness, and cross-family replication are complete. Preserve links to handoff and project documents; remove only duplicated completion prose.

- [x] **Step 6: Verify README coverage after distillation**

Run:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_readme
.\.venv\Scripts\python.exe -m scripts.verify_reproduce
.\.venv\Scripts\python.exe scripts/verify_closeout.py
```

Expected: all pass, proving that progressive disclosure did not remove machine-checked evidence or commands.

- [x] **Step 7: Commit the evidence-layer distillation**

Stage only `README.md`, set exact Git identity, and commit:

```powershell
git add -- README.md
git commit -m "Docs: streamline README evidence trail"
```

---

### Task 4: Render, audit, and publish the README

**Files:**
- Modify: `docs/superpowers/plans/2026-08-03-readme-redesign-implementation.md` (mark completed steps)
- Verify only: all files listed above

**Interfaces:**
- Consumes: finished Markdown and green local gates
- Produces: rendered public README, verified Git identity, sole GitHub contributor

- [x] **Step 1: Run formatting and content hygiene checks**

Run:

```powershell
git diff --check
rg -n "正體中文（台灣）|zenodo.org/badge/DOI|目前狀態" README.md
```

Expected: no whitespace errors, no old Zenodo badge, no dense `目前狀態` hero, and no emphasized regional phrase in the title.

- [x] **Step 2: Render through GitHub-compatible Markdown**

Use GitHub's Markdown API with `context=kuotunyu/FormosaNLU-Synth`, inspect the generated HTML for `h1`, badge images, artifact links, `<details>`, result image paths, tables, and headings. Reject the render if any image `src` is empty or any DOI link differs from the report-derived URL.

- [x] **Step 3: Run the complete six-gate suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_gates --quiet
```

Expected: Ruff, full pytest, README, contributors, reproduce, and closeout all pass.

- [x] **Step 4: Audit the final diff and private-file boundary**

Run:

```powershell
git status --short
git diff --stat origin/main...HEAD
git ls-files --error-unmatch interview.md
```

Expected: only approved README/verifier/test/spec/plan files changed; `git ls-files` fails for `interview.md`, proving it is not tracked.

- [x] **Step 5: Commit the completed plan record**

Stage only this plan file, set exact Git identity, and commit:

```powershell
git add -- docs/superpowers/plans/2026-08-03-readme-redesign-implementation.md
git commit -m "Docs: record README redesign verification"
```

- [ ] **Step 6: Push `main` and inspect the public render**

Run `git push origin main`, then open the public repository README and verify title wrapping, badge rendering, main result figure, artifact links, tables, and details controls at desktop width.

- [ ] **Step 7: Verify sole authorship and immutable release boundary**

Confirm through GitHub API that every new commit has author/committer `kuotunyu`, the contributors endpoint returns only `kuotunyu`, and tag `v1.2.1` still resolves to `1f42372e97c98212f192362ec441c034815b37d5`.

- [x] **Step 8: Run the Impeccable detector once**

Run:

```powershell
node C:\Users\3Hml\.codex\skills\impeccable\scripts\detect.mjs --json README.md
```

Expected: no blocking issue. Record any advisory finding in the handoff; do not make unplanned data or research changes.

## Self-review

- **Spec coverage:** Tasks 1–2 cover the stable DOI and first-screen proof; Task 3 covers concision, progressive disclosure, language and evidence preservation; Task 4 covers rendering, gates, identity, Contributors and immutable tag verification.
- **Placeholder scan:** Every implementation and test step is fully specified; nothing is deferred.
- **Interface consistency:** Task 1 defines one exact report-derived stable badge consumed by Task 2 and checked again in Task 4. README content continues to feed the existing raw-text verifiers without changing report schemas.
- **Scope boundary:** Only documentation presentation and its exact-markup regression test change; no research artifact or external release is rewritten.
