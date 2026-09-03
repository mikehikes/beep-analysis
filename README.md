# ATL Spoke ridership and cost analysis

A look at ridership and cost for **ATL Spoke**, the Atlanta Beltline's autonomous
shuttle pilot (operated by Beep), for June and July 2026. Source ridership data was
obtained from Atlanta Beltline, Inc. via an Open Records Act request.

**Read the summary: https://mikehikes.github.io/beep-analysis/**

## What's here

- `docs/index.html` — the published summary above (generated from `executive_summary.ipynb`)
- `executive_summary.ipynb` — plain-language notebook, code hidden, charts and tables only
- `data/` — extracted ridership CSVs plus published peer transit benchmarks (MARTA, CobbLinc, Beep's Cumberland Hopper)
- `src/` — the extraction and analysis pipeline (see below)
- `ABI Ridership Report *.pdf` — the two source reports the data was extracted from

The detailed technical notebook (`analysis.ipynb`) is not included in this repo.

## How the data was built

The two source PDFs are chart-only, no tables. Every number was recovered from bar
label positions using `pdftotext -bbox-layout`, matched to axis ticks by an
order-preserving assignment, then checked against the source's own printed totals.
All cost figures rest on a documented assumption register in
`src/service_parameters.py`, since the source reports contain ridership counts only,
no cost or service-hour data.

## Reproducing this

```
make data      # PDFs -> data/*.csv
make exec      # regenerate and execute executive_summary.ipynb
make docs      # export executive_summary.ipynb -> docs/index.html
make all       # all of the above
```

Requires [uv](https://docs.astral.sh/uv/). See `make help` for the full list.

## License

GPLv3. See `LICENSE`.
