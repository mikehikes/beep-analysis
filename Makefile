.PHONY: help data notebook exec lab serve all clean

help:	## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

data:	## Extract the PDFs to data/*.csv (asserts every validation gate)
	uv run python src/extract_ridership.py

notebook: data	## Regenerate and execute analysis.ipynb
	uv run python src/build_notebook.py
	uv run jupyter nbconvert --to notebook --execute --inplace analysis.ipynb

exec:	## Regenerate and execute executive_summary.ipynb
	uv run python src/build_exec_notebook.py
	uv run jupyter nbconvert --to notebook --execute --inplace executive_summary.ipynb

lab:	## Start JupyterLab with both notebooks open
	uv run jupyter lab executive_summary.ipynb analysis.ipynb

serve:	## Start the classic Notebook server (no auto-open browser)
	uv run jupyter notebook --no-browser analysis.ipynb

all: data notebook exec	## Full rebuild of every deliverable

clean:	## Remove generated CSVs and caches (leaves the PDFs and notebook)
	rm -rf data/*.csv src/__pycache__ .ipynb_checkpoints
