# FormosaNLU-Synth English technical report

`formosanlu_synth.tex` is an evidence-bounded technical report, not a peer-reviewed publication.
It summarizes only claims already supported by the
tracked machine-readable reports. If manuscript prose and machine-readable
evidence ever differ, the tracked reports are authoritative.

## Build

The tracked `formosanlu_synth.pdf` is built from the adjacent TeX and BibTeX
sources with Tectonic. The package uses only standard Overleaf/arXiv-compatible
dependencies (`article`, `booktabs`, `xurl`, `hyperref`, `geometry`, and `natbib`). A
conventional LaTeX environment can reproduce it with:

```text
pdflatex formosanlu_synth.tex
bibtex formosanlu_synth
pdflatex formosanlu_synth.tex
pdflatex formosanlu_synth.tex
```

LaTeX auxiliary files remain untracked. The repository's Python closeout
verifier checks the manuscript structure, required limitations, headline
values, and the presence of the compiled `formosanlu_synth.pdf`. The tracked
reports are authoritative if prose and machine-readable evidence differ.
