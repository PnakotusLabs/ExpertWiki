# OKF Alignment

## Vision Baseline

The product vision is based on Andrej Karpathy's LLM Wiki gist, not a separate
repository. This implementation treats that gist as the conceptual source of
truth and uses Google Cloud's Open Knowledge Format as the interoperable file
format for the bundle.

## Verifiable Alignment Sources

This implementation aligns to:

- Andrej Karpathy's LLM Wiki pattern:
  https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Google Cloud Open Knowledge Format announcement:
  https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
- Google Cloud OKF v0.1 draft specification:
  https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

## Product Interpretation

ExpertWiki should not make a proprietary knowledge format the primary artifact.
The primary artifact should be an OKF-compatible knowledge bundle:

- a directory tree of markdown files,
- YAML frontmatter on every concept document,
- `type` as the only required field,
- normal markdown links for relationships,
- `index.md` for progressive disclosure,
- `log.md` for update history,
- citations at the bottom of sourced concepts.

ExpertWiki-specific verification metadata is added as producer-defined
frontmatter fields, which OKF consumers are expected to tolerate:

- `status`
- `confidence`
- `reviewers`
- `verified_at`
- `sources`

## Alignment Gaps To Resolve

1. Decide whether `Verified Claim` should remain the core concept type or be
   split into `Claim`, `Review`, and `Source`.
2. Implement an MCP server as the primary agent interface.
3. Add OKF conformance checks for frontmatter and reserved filenames.
4. Add a producer workflow that drafts OKF concepts from official docs and sends
   them through human review.
