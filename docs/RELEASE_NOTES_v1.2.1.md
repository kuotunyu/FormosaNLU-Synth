# v1.2.1 — Publication metadata and documentation closeout

## 範圍

v1.2.1 是 publication-layer patch。它修正版本 metadata、文件連結、授權範圍、
Hugging Face card 說明、可引用技術報告與 release preservation；不改變任何研究
資料或結果。

這個版本**沒有**：

- 增減或改寫 Dataset rows；
- 改動 Model tensors 或重新訓練 adapter；
- 重跑 generation、filtering、training、evaluation 或 robustness；
- 改變 frozen prompt、threshold、seed、parser、evaluation contract；
- 改寫 M19 的 2.5 percentage points 預先登記門檻或 causal-claim 限制。

## 不變的公開 artifacts

- Dataset：3,754 rows；train SHA-256
  `c65d7209d953e144299625f6a9224b98557b2677d55258a463a2992e5acf4665`
- Gemma LoRA adapter：155,609,536 bytes；SHA-256
  `f70f423814dcd47943c92c0beb8b08a4e7f65e60a44355d3dcd95bed9f0bd60a`
- Phi-4-mini 僅作 cross-family replication；本版本不發布其 weights 或 adapter。

## 修正與新增

- 將 software／citation metadata 同步為 `1.2.1`。
- 修正 v1.2.0 GitHub Release 的五個 tag-pinned evidence links。
- 修正接手文件中 M15／M16 report 路徑。
- 將 canonical MIT `LICENSE` 與第三方 artifact 授權範圍分離。
- 明確區分 Apache-2.0 Gemma roles 與 MIT Phi-4-mini replication model。
- 新增 evidence-bounded English technical report 與 publication closeout verifier。
- 更新 Hugging Face Dataset／Model cards，但不改動 Dataset rows 或 Model tensors。
- 建立 deterministic GitHub Release evidence bundle，並由 Zenodo 保存 GitHub Release。

## v1.2.1 evidence

- [研究摘要與重現入口](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.1/README.md)
- [English technical report](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.1/paper/formosanlu_synth.tex)
- [M19 equal-N aggregate](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.1/reports/m19_ablation.md)
- [完整資源帳本](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.1/reports/m12_resource_ledger.json)
- [第三方授權聲明](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.1/THIRD_PARTY_NOTICES.md)

舊版 `v1.0.0`、`v1.1.0`、`v1.2.0` tags 與其 artifacts 保持 immutable。
