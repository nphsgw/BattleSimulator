# TODO History Before The Surrogate Roadmap

This file preserves the implementation history that was replaced when the tactical
simulator roadmap became the active `docs/todo.md`.

## Completed Work

- Product, simulation, implementation, and current-spec documents were established.
- Target indexes were corrected to use indexes in the complete unit matrix.
- `Terrain(form=None)`, GIF filenames, pre-army errors, numeric validation, and
  Numba/type modernization were addressed.
- Debug overlays, terrain diagnostics, a static renderer, and the local Web UI were
  implemented and tested.
- README visualization guidance was migrated from notebook-first usage to CLI/Web UI.

## Legacy Backlog

These items were still open when the roadmap was replaced. They remain valid cleanup
work but do not block the tactical simulation kernel.

- Classify notebooks as teaching material, exploration, or usage examples.
- Remove the notebook extra when `ipywidgets` is no longer required.
- Document `sim_jupyter()` as a compatibility interface.
- Clean up Ruff findings in examples and teaching notebooks.

The exact pre-roadmap checklist remains available in Git history. This summary is the
stable link from the active roadmap so unfinished work is not silently lost.
