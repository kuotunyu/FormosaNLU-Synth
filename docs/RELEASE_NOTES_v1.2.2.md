# v1.2.2 — Phi adapter and archival technical report

[Zenodo all versions](https://doi.org/10.5281/zenodo.21767492) ·
[GitHub Release](https://github.com/kuotunyu/FormosaNLU-Synth/releases/tag/v1.2.2)

v1.2.2 把已完成的第二個 student family 證據轉成可直接重用的公開 artifact，並將
English technical report 編譯、驗證及納入 versioned archive。它不重跑任何 generation、
training 或 evaluation，也不改 frozen corpus、prompts、seeds、thresholds、metrics 或
preregistered criterion。

## 新增公開 artifact

- [`steven0226/phi-4-mini-formosanlu-lora`](https://huggingface.co/steven0226/phi-4-mini-formosanlu-lora)：
  `real_syn_filtered` seed-42 Phi-4-mini LoRA adapter。
- [`paper/formosanlu_synth.pdf`](../paper/formosanlu_synth.pdf)：由 tracked LaTeX 與
  bibliography 編譯的 archival technical report。
- `reports/m20_phi_adapter_publication.json`：authenticated upload、remote SHA-256、
  file allowlist、visibility 與 anonymous verification evidence。

## Phi adapter integrity

| 項目 | 固定值 |
|---|---|
| Base model | `microsoft/Phi-4-mini-instruct` |
| Revision | `cfbefacb99257ffa30c83adab238a50856ac3083` |
| Adapter SHA-256 | `e9e4c77d79eb12da8cba64a7a484d260f753d000396752f51159e3c0f4e34376` |
| Size | `92,309,112` bytes |
| Tensor count | `256` |
| Training arm / seed | `real_syn_filtered` / `42` |

上傳 bundle 只包含 inference 所需檔案、card、license 與 manifest；不包含 optimizer
state、checkpoint、`training_args.bin`、base weights、token 或本機絕對路徑。上傳先以
Private repository staging，完成 authenticated hash check 後才轉 Public，再以 anonymous
client 驗證。

## Research scope

v1.2.2 沒有新增 headline experiment。它公開的 Phi adapter 是 M15 六組 runs 之一；
三-seed paired 結論仍來自 `real_only` 與 `real_syn_filtered` 各三組獨立 runs。預先登記的
cross-family criterion 維持原判定：Gemma 與 Phi 的 intent accuracy、exact match mean
delta 都為正，且各自 hierarchical 95% CI 下界大於零。

## Unchanged artifacts

- Public Dataset 仍為 `3,754` rows，train SHA-256 仍為
  `c65d7209d953e144299625f6a9224b98557b2677d55258a463a2992e5acf4665`。
- Gemma adapter 仍為 `155,609,536` bytes，SHA-256 仍為
  `f70f423814dcd47943c92c0beb8b08a4e7f65e60a44355d3dcd95bed9f0bd60a`。
- `v1.0.0`–`v1.2.1` tags、GitHub Releases 與 Zenodo version records 保持 immutable。

## Release evidence assets

GitHub Release 附上 technical report PDF、Phi paired／cross-family reports、Phi publication
evidence、資源帳本與 `SHA256SUMS.txt`。Zenodo concept DOI
[`10.5281/zenodo.21767492`](https://doi.org/10.5281/zenodo.21767492) 連結所有 versions；
v1.2.2 的 version DOI 由 release archive minting 後另行回填至 `main`。
