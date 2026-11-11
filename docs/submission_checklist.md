# Preprint Submission Checklist (owner actions)

`docs/manuscript.md` is generated from the executed results at release v0.4.0, with
two figures (`docs/figures/`). Everything the analysis can supply is filled in.
The items below need the owner. None of them can be done from an agent session.

## Before submitting

1. **Push the release tags** so the manuscript can cite a frozen version
   (`v0.2.0`, `v0.3.0`, `v0.4.0`; commands in `docs/audit.md`).
2. **Contact the dataset authors** (requests read from the OpenNeuro records on
   2026-11-11):
   - **ds002778** asks to be emailed (address in its README) *before submitting
     a manuscript*. Its README also **strongly advises against PD-vs-control
     classification on this dataset** because it has too few patients. This paper
     uses it as one of three external test sets and as one leave-one-site-out
     training site. The manuscript states this as a limitation, but the authors
     may object or ask for changes. Contact them first and take their feedback
     seriously, including possibly dropping ds002778 from the classification
     results. That decision is yours.
   - **ds007526**'s "how to acknowledge" field says "Please contact the authors."
3. **Associated papers not yet cited.** These could not be fully verified from
   this session. Add them once you have confirmed the details:
   - ds007526: *Electroencephalography-Based Clustering Reveals Robust
     Neurophysiological Subtypes in Parkinson's Disease*, Movement Disorders,
     doi:10.1002/mds.70348 (author list unconfirmed);
   - ds004584: preprint doi:10.1101/2022.07.26.22278079 (title unconfirmed).
4. **Fill the `[owner to complete]` fields** in `scripts/generate_manuscript.py`
   (not in the generated `docs/manuscript.md`, which is overwritten), then run
   `uv run python scripts/generate_manuscript.py`:
   - affiliation;
   - funding;
   - competing interests;
   - author contributions;
   - any ethics wording the server or your institution requires;
   - confirm the AI-tools statement.
5. **Read the whole draft.** Check that it says what you are willing to put your
   name to. The scientific content follows ADRs 0013–0018; do not edit numbers by
   hand.

## Choosing a server

- **medRxiv** (health sciences) asks for ethics, funding and competing-interest
  declarations at submission. Check its current submission guide; requirements
  change.
- **bioRxiv** (Neuroscience) is also suitable for a methods- and
  generalization-focused paper.
- Both accept a PDF. One way to make one from the Markdown:
  `pandoc docs/manuscript.md -o manuscript.pdf --resource-path=docs` (requires
  pandoc and a LaTeX engine; convert the SVG figures to PDF/PNG first if your
  engine cannot embed SVG).

## Licence

Choose the preprint licence (CC BY is common). The code stays MIT and the data
remain CC0 under their original authors.

## Not to do

- Do not describe NeuroPD as diagnosing Parkinson's disease (spec Section 6.5).
- Do not add references without checking them against a public record. The
  manuscript test requires every cited DOI to be listed in `CITATION.cff`.
