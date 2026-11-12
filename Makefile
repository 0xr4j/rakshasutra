# Reproduce everything. Needs Python 3.10+, the packages in requirements.txt, a C compiler and Node for
# the parity tests, and (for the PDFs) a LaTeX install with latexmk.
PY=python3
.PHONY: test results examples figures generated assets book whitepaper site all
test:
	$(PY) -m pytest tests -q
results:      # every study; a few seconds, all seeds fixed
	$(PY) experiments/write_params.py
	$(PY) experiments/run_all.py
examples:
	$(PY) experiments/make_examples.py
figures:
	$(PY) experiments/figures.py
generated: figures      # numbers, tables and AUDIT.md shared by the book, the white paper, the README and the site
	$(PY) generated/make_numbers.py
assets: generated       # README banner, diagrams and the walk animation
	$(PY) experiments/readme_assets.py
book: generated
	cd book && latexmk -pdf -silent -interaction=nonstopmode main.tex && cp main.pdf ../docs/A-Thread-Through-the-Crowd-Rakshasutra.pdf
whitepaper: generated
	cd whitepaper && latexmk -pdf -silent -interaction=nonstopmode main.tex && cp main.pdf ../docs/Rakshasutra-White-Paper-WP01.pdf
site: generated
	$(PY) demo/build_web.py
all: results examples generated assets book whitepaper site test
