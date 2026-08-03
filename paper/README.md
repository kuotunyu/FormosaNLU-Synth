# FormosaNLU-Synth English technical report

`formosanlu_synth.tex` is an evidence-bounded technical report, not a peer-reviewed publication.
It summarizes only claims already supported by the
tracked machine-readable reports. If manuscript prose and machine-readable
evidence ever differ, the tracked reports are authoritative.

## Build

The project records that no TeX engine is installed locally in the project environment. The package uses
only standard Overleaf/arXiv-compatible dependencies (`article`, `booktabs`,
`hyperref`, `geometry`, and `natbib`). Upload this directory to Overleaf or run
the following sequence in an environment with LaTeX and BibTeX:

```text
pdflatex formosanlu_synth.tex
bibtex formosanlu_synth
pdflatex formosanlu_synth.tex
pdflatex formosanlu_synth.tex
```

No generated PDF or LaTeX auxiliary files are tracked. The repository's Python
closeout verifier checks the manuscript structure, required limitations, and
headline values without pretending to perform a local TeX compilation.
