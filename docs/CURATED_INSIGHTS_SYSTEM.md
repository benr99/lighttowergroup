# The Light Tower Curated Insights System

## Editorial constitution

Light Tower publishes only when it can make a smart reader see a capital
decision differently.

Accuracy is the floor. Finished work must add mechanism, consequence, human or
institutional stakes, candor, and a bounded point of view. Routine facts belong
in the deal tape. Wit must be earned by a true observation. A valid editorial
decision is to kill, shorten, defer, or publish nothing.

The desk targets three useful pieces each publishing day. That is a discovery
and research requirement, not permission to inflate weak evidence into essays.
Finite reader attention still governs format: a bounded brief can satisfy the
daily target, while routine facts stay in Deal Tape and repeated events stay
suppressed.

## Product architecture

The public Insights surface is article-first: readers see the current research
and analysis archive rather than an on-page Daily Capital Note. The pipeline
still produces a structured daily edition behind the scenes so selection,
hierarchy, Deal Tape, audit records, and distribution remain coherent.

An edition can contain:

- one Flagship Analysis;
- one Culture of Capital item;
- one primary-source Data Note;
- a small number of Intelligence Briefs;
- a compact Deal Tape;
- a reader poll and open editorial prompt;
- or no publishable story.

The production workflow researches up to five standalone pieces and targets
three publishable articles. The extra research capacity absorbs source failure,
duplication, and editorial kills. Deal Tape entries never become padded article
pages.

## Discovery

The system gathers the established CRE, finance, banking, federal, and
government source universe, then supplements it with NewsAPI searches and the
editable `.editorial-state/discovery-watchlist.json`.

Before portfolio scoring, a bounded set of CRE-anchored candidates receives
full-text enrichment. This lets a generic headline recover material facts such
as project cost, square footage, occupancy, rent movement, capital expenditure,
or redevelopment scope. The wider feed pool can then corroborate a selected
event without admitting unrelated low-quality stories into the edition.

The watchlist deliberately looks beyond transaction announcements:

- money and status;
- sports and public subsidies;
- AI infrastructure and electricity;
- climate, insurance, and migration;
- labor and operating capacity;
- office attendance and city life;
- luxury, hospitality, and private clubs;
- housing and generational inequality;
- universities, hospitals, and nonprofit real estate.

Reader submissions provide an original-reporting radar. They are prompts to
investigate, never publishable facts by themselves.

## Event memory

`scripts/editorial_intelligence.py` creates a stable event fingerprint from
title concepts, parties, amounts, markets, asset classes, and source URLs.

The similarity model combines title-token overlap with shared amounts, parties,
markets, and assets. Multiple publishers covering the same event become one
source cluster. The cluster is then compared with the Light Tower archive.

Archive matching compares not only headline language but also normalized
amounts, street addresses, institutions, markets, asset classes, and context.
A recent same-event match is suppressed before assignment; an older or genuinely
new development remains visible to the assigning editor with an explicit
`archive_matches` record.

## Must-read scoring

The score is inspectable:

- consequence: 15;
- novelty: 15;
- conflict and power: 15;
- explanatory value: 15;
- cultural relevance: 10;
- human stakes: 10;
- evidence depth: 10;
- Light Tower right-to-win: 10;
- conversation potential: 10;
- bounded audience-learning adjustment: -5 to +5;
- routine-event penalty: up to -18;
- archive-repetition penalty: up to -18.

The score is not a guarantee of publication. Evidence and format controls can
still downgrade or kill an assignment. Scores at or above 56 compete for the
strict must-read queue. A second, quality-bounded daily-depth queue can research
scores at or above 24 only when the event has a concrete capital or operating
signal, a recognizable CRE anchor, no recent archive repeat, and no legal-risk
signal.

Audience learning is deliberately weak relative to judgment. It can refine
attention within a beat but cannot override evidence, duplication, or a routine
event penalty.

## Research dossier

Every selected event receives a dossier before writing:

- every independent source URL;
- authority and source tier;
- retrieved text availability;
- extractable reported facts;
- direct quotations with provenance during the live run;
- prior Light Tower coverage and potential comparables;
- reporting gaps;
- skeptical counterquestions.

Evidence levels:

- `deep`: at least three independent sources and two usable full-text sources;
- `adequate`: at least two sources or a primary source;
- `thin`: one usable source;
- `insufficient`: too little factual material to write.

Flagship long-form requires deep evidence. A thin flagship is automatically
shortened. Insufficient evidence becomes Deal Tape or is killed.

## Editorial room

The implementation separates responsibilities that the former prompt collapsed:

1. **Scout**: discovery, normalization, and event clustering.
2. **Portfolio editor**: must-read scoring and edition scarcity.
3. **Researcher**: source retrieval and evidence ledger.
4. **Angle editor**: alternate framings and bounded thesis.
5. **Skeptic**: counterargument, missing evidence, and overclaim risk.
6. **Writer**: format-specific draft from the verified dossier.
7. **Copy and standards editor**: negative and positive quality gates.
8. **Editor-in-chief control**: kill, defer, shorten, Deal Tape, review, or
   automatic publication.

The model cannot fetch, invent, or upgrade evidence. Its role begins after the
deterministic system establishes the factual boundary.

## Formats

### Flagship Analysis

- 750–1,050 words.
- Three independent sources.
- Two usable full-text sources.
- Counterargument and claim/evidence map.
- Human review required.

### Intelligence Brief

- 240–430 words.
- One or more verified sources.
- One fact, one bounded inference, one practical consequence.
- A daily-depth brief may auto-publish with at least one retrieved full-text
  source, at least three source-mapped facts, an editorial-room write or shorten
  decision, and all normal quality gates.
- A fact-poor, unsupported, legally sensitive, or repetitive brief is held even
  when the daily target has not been met.

### Culture of Capital

- 300–550 words.
- Two independent sources.
- Connects money to status, politics, place, labor, entertainment, technology,
  or city life.
- Human review required because cultural judgment is difficult to automate.

### One Chart, One Argument

- 200–400 words.
- Primary-source data or filing.
- At least one source-mapped data point.
- Rendered with a compact data panel.

### Deal Tape

- Facts plus one bounded implication.
- No standalone long-form page.
- Used for material events that do not earn an essay.

## Recurring franchises

- Credit Committee Theater.
- Five Minutes Before Maturity.
- Who Got Paid / Who Got Stuck.
- What the Press Release Left Out.
- Capital After Dark.
- The Most Expensive Assumption.
- One Chart, One Argument.

The franchise is a reporting promise, not a verbal template.

## Excellence controls

Negative checks reject fallback writing, invalid sources, title duplication,
unsafe retrieved instructions, encoding corruption, canned AI pivots,
repetitive paragraph openings, contrast templates, and malformed output.

Positive checks require:

- why the event matters now;
- one bounded original inference;
- the strongest counterargument;
- a source-supported concrete detail;
- human or institutional stakes;
- explicit reader value;
- a memorable line that actually appears in the article;
- a claim/evidence map using only verified dossier URLs;
- format-appropriate word count and source depth.

The gate limits repeated house abstractions such as “the question is,” “the
signal is,” and “this is not.”

## Distribution

Distribution follows editorial format:

- flagship: full LinkedIn essay and document package;
- Culture of Capital: edge-oriented native essay and document package;
- brief and data note: compressed native post, no automatic PDF;
- Deal Tape: edition only.

All platform output remains in review unless explicit auto-post flags are used.

## Audience loop

The edition includes direct subscription through Resend, a rotating poll, an
open prompt to send the desk a story or question, and analytics events for
subscriptions, story clicks, poll responses, and reader prompts.

`editorial-feedback.js` can deliver to a durable webhook and the Light Tower
inbox.

Qualified feedback can be summarized into
`.editorial-state/audience-signals.json`. Weights are capped at five points and
must be based on saves, forwards, replies, poll responses, and qualified
business conversations—not raw clicks alone.

## Release safety

The scheduled workflow validates committed `main`, generates without Git side
effects, validates the new edition, preserves an audit artifact, stages only the
generated allowlist, rebases safely if the target moved, stops on conflicts,
and verifies the remote SHA.

Review-required work goes to a branch and pull request. Validated,
evidence-bounded briefs can update `main` automatically. Flagship, cultural,
legally sensitive, insufficient-evidence, and fact-poor work remains review
only. A no-story edition is still permitted as a last-resort safety outcome,
but the run records the missed daily target explicitly.

## File map

Core intelligence:

- `scripts/editorial_intelligence.py`
- `scripts/research_dossier.py`
- `scripts/editorial_room.py`
- `scripts/edition_manager.py`

Generation and controls:

- `scripts/daily_news_agent.py`
- `scripts/enhanced_prompts.py`
- `scripts/content_governance.py`
- `scripts/editorial_voice.py`

Release:

- `scripts/validate_publication.py`
- `scripts/publish_generated.py`
- `.github/workflows/daily-insights-agent.yml`
- `.github/workflows/quality.yml`

Audience:

- `edition.js`
- `edition.css`
- `netlify/functions/newsletter-subscribe.js`
- `netlify/functions/editorial-feedback.js`
