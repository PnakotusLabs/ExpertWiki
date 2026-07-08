# Verification Policy

## Verification Standard

A claim can be marked `verified` only when:

1. The claim is supported by at least one reliable source.
2. The source is linked and includes publication or retrieval metadata.
3. The claim text does not overstate what the source says.
4. A reviewer identity is recorded.
5. The claim has a `last_verified_at` date.

## Preferred Sources

Highest priority:

- Official documentation.
- Standards bodies and specifications.
- Company filings and official announcements.
- Project repositories and release notes.

Secondary sources can be used for context, but they should not be the only
support for a high-impact technical claim when a primary source exists.

## Review Types

- `source_audit`: reviewer checked that the citation supports the claim.
- `expert_review`: reviewer has domain expertise and approved the claim.
- `cross_check`: second reviewer confirmed or challenged the claim.
- `field_validation`: reviewer used the guidance in a real task and observed
  the result.

## Negative States

- `draft`: extracted or written but not reviewed.
- `reviewed`: checked but not strong enough for verified status.
- `disputed`: credible conflicting evidence exists.
- `stale`: likely out of date or source changed.
- `rejected`: unsupported, misleading, duplicated, or not useful to agents.

## Staleness Triggers

- Source page changed materially.
- Product/API version changed.
- User or agent reports contradiction.
- Claim references pricing, model behavior, limits, regulations, or other
  fast-changing facts older than the review window.

## Review Windows

Default review windows:

- API behavior and limits: 30 days.
- Pricing and availability: 14 days.
- Security guidance: 30 days.
- Stable standards and concepts: 180 days.
