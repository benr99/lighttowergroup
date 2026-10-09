/* ===========================================================================
   Light Tower Insights: system map data.
   Edit this file, then run:  python docs/system-map/build.py
   Facts were checked against the code on 2026-10-09. Items marked "suspected"
   are inferences, not verified behaviour.
   =========================================================================== */
const MAP = {

/* ---------------------------------------------------------------- GROUPS */
groups: [
  /* ---- orientation ---- */
  { id:'g_intro', row:0, kind:'info', title:'Light Tower Insights: how the intelligence system works', x:60, y:40, w:980, cols:1,
    html:`<p><b>One sentence:</b> every morning at 07:07 New York time a GitHub Action reads ~150 feeds, turns the day's documents into <i>events</i>, reads the actual articles, scores and selects up to 70 stories, has an AI write each one from verbatim source quotes, fact-checks every sentence twice, publishes only what survives, then verifies the live site.</p>
    <p><b>How to read this map.</b> Follow the numbered <span class="chip c-live">LIVE</span> stages 1 to 11 left to right. Each box is a real file: what it does, what goes in and out, the numbers that control it, and what happens when it breaks. Click any box for the full card. Use <kbd>Tour</kbd> (bottom) to walk it step by step, and <kbd>Flags</kbd> for the critique list.</p>
    <p class="muted">Controls: drag to pan · scroll to zoom · <kbd>F</kbd> fit all · <kbd>/</kbd> search · <kbd>←</kbd><kbd>→</kbd> tour · <kbd>Esc</kbd> close</p>` },
  { id:'g_legend', row:0, kind:'info', title:'Legend', x:1080, y:40, w:560, cols:1,
    html:`<div class="legend">
      <div><span class="chip c-live">LIVE</span> runs in the daily production path</div>
      <div><span class="chip c-weekly">WEEKLY</span> Friday wrap path</div>
      <div><span class="chip c-sat">SATELLITE</span> real code, not in the daily workflow</div>
      <div><span class="chip c-prototype">PROTOTYPE</span> designed and tested, not in production</div>
      <div><span class="chip c-legacy">LEGACY</span> old pipeline, rollback only or dead</div>
      <div><span class="chip c-config">CONFIG</span> JSON the code reads</div>
      <div><span class="chip c-state">STATE</span> files the pipeline remembers between runs</div>
      <div><span class="chip c-ext">EXTERNAL</span> a service outside the repo</div>
      <div><span class="eg main"></span> main data flow &nbsp; <span class="eg ctl"></span> control &nbsp; <span class="eg fb"></span> feedback &nbsp; <span class="eg leg"></span> legacy</div>
      <div>🚩 a verified issue worth your critique (see Flags)</div></div>` },
  { id:'g_numbers', row:0, kind:'info', title:'The pipeline in numbers', x:1680, y:40, w:740, cols:1,
    html:`<div class="numgrid">
      <div><b>255</b><span>sources configured</span></div><div><b>171</b><span>marked active</span></div>
      <div><b>~148</b><span>working RSS feeds*</span></div><div><b>16</b><span>index pages (no feed)</span></div>
      <div><b>36 h</b><span>ingest lookback</span></div><div><b>0.62</b><span>event merge threshold</span></div>
      <div><b>7</b><span>sectors</span></div><div><b>10</b><span>stories per sector</span></div>
      <div><b>70</b><span>max stories per day</span></div><div><b>40</b><span>quality floor (of 100)</span></div>
      <div><b>2</b><span>fact-check passes</span></div><div><b>480</b><span>automated tests</span></div></div>
      <p class="muted">*171 active minus 7 NewsAPI entries the ingester skips (flag F7) minus 16 index pages. Example day (Aug 28): 773 documents became 725 events.</p>` },

  /* ---- trigger & external ---- */
  { id:'g_trigger', row:1, kind:'lane', title:'0 · Trigger and control', sub:'What starts a run, and what decides whether it may publish.', x:60, y:360, w:1560, cols:3, color:'#6b7280',
    layer:'live', failure:'If the cron is late the policy script still accepts 07:05–07:15 ET. If the wrong DST trigger fires it exits cleanly without doing anything.' },
  { id:'g_external', row:1, kind:'lane', title:'External services', sub:'Everything outside the repo that the system depends on.', x:1680, y:360, w:740, cols:2, color:'#475569', layer:'live' },

  /* ---- main pipeline: eleven stages ---- */
  { id:'s1', row:2, kind:'stage', step:1,  title:'Ingest', sub:'Pull every feed and index page from the last 36 hours into one list of documents.', x:60,    y:900, w:400, cols:1, color:'#0e7490', layer:'live',
    io:{ in:'config/sources.json, feeds, index pages', out:'~700+ CanonicalItem documents' },
    failure:'Fail-open. One dead feed never stops the rest; repeated failures open a circuit breaker. If ingestion crashes entirely the run records an error and stops ("no documents ingested").' },
  { id:'s2', row:2, kind:'stage', step:2,  title:'Classify', sub:'Label each document with a sector, subsector and event type. Nothing is rejected here.', x:530,   y:900, w:400, cols:1, color:'#0e7490', layer:'live',
    io:{ in:'documents', out:'documents with primary_sector (7 sectors)' },
    failure:'Fail-open: on an error documents continue unclassified and later fail the eligibility gate ("unclassified sector").' },
  { id:'s3', row:2, kind:'stage', step:3,  title:'Cluster into events', sub:'Merge documents that report the same event so one deal fills one slot, not three.', x:1000,  y:900, w:400, cols:1, color:'#0e7490', layer:'live',
    io:{ in:'classified documents', out:'IntelligenceObjects (one per event)' },
    failure:'Deterministic, no model. A bad merge would hide a story or double-count one; every merge records its reasons in the audit.' },
  { id:'s4', row:2, kind:'stage', step:4,  title:'Type and gate', sub:'Decide what each thing IS (news, explainer, interview...) and whether it can ever qualify.', x:1470,  y:900, w:400, cols:1, color:'#0e7490', layer:'live',
    io:{ in:'objects (RSS summary only)', out:'eligible / ineligible + reason' },
    failure:'Cheap first pass on thin summaries. It can wrongly reject, which is why stage 6 re-runs the gate on the full article.' },
  { id:'s5', row:2, kind:'stage', step:5,  title:'Check memory', sub:'Compare against 45 days of coverage so we do not rerun a story or rank a follow-up above news.', x:1940,  y:900, w:400, cols:1, color:'#0e7490', layer:'live',
    io:{ in:'objects', out:'novelty state per object' },
    failure:'Fail-open: if memory fails the run continues with every story marked new (risk: repeats).' },
  { id:'s6', row:2, kind:'stage', step:6,  title:'Read the articles', sub:'Fetch the real article text for up to 250 candidates, lawfully, then re-run the gate on the full body.', x:2410,  y:900, w:400, cols:1, color:'#0e7490', layer:'live',
    io:{ in:'shortlist of objects', out:'objects with full text + evidence level' },
    failure:'Fail-open: a blocked or slow page stays "summary only" and its depth is capped accordingly. Phase budget 420 s.' },
  { id:'s7', row:2, kind:'stage', step:7,  title:'Score importance', sub:'Give every event a 0-100 score from 8 measures, each one explaining itself.', x:2880,  y:900, w:400, cols:1, color:'#0e7490', layer:'live',
    io:{ in:'enriched objects', out:'final_score, tier, components' },
    failure:'A measure that stops varying is flagged as "degenerate" in the run report (it once let three dead measures run for months).' },
  { id:'s8', row:2, kind:'stage', step:8,  title:'Select the slate', sub:'Per-sector top 10 above the floor, then a global cap of 70, each with a writing depth the evidence earned.', x:3350,  y:900, w:400, cols:1, color:'#0e7490', layer:'live',
    io:{ in:'scored objects', out:'publication slate (≤70) with tier_a/b/c' },
    failure:'A slot stays empty rather than being filled with something weak. Shortfalls are reported with a reason (quiet day vs broken sources).' },
  { id:'s9', row:2, kind:'stage', step:9,  title:'Write and fact-check', sub:'AI drafts each story as quoted sentences; code and a second pass delete everything the source does not support.', x:3820,  y:900, w:400, cols:1, color:'#b45309', layer:'live',
    io:{ in:'selected objects + source text', out:'verified articles (or withheld/failed)' },
    failure:'FAIL-CLOSED. No checker, no publication. Thin results are "withheld" (not a failure). Provider errors are "failed".' },
  { id:'s10', row:2, kind:'stage', step:10, title:'Publish', sub:'Render pages, update the manifest, feed and sitemap, write the edition record, validate everything.', x:4290,  y:900, w:400, cols:1, color:'#15803d', layer:'live',
    io:{ in:'verified drafts', out:'files on disk + a declared file list' },
    failure:'One bad article is isolated. If validation fails, the run stops before anything is pushed.' },
  { id:'s11', row:2, kind:'stage', step:11, title:'Release and verify', sub:'Commit only declared files, push, watch the live site, roll back if it never shows up.', x:4760,  y:900, w:400, cols:1, color:'#15803d', layer:'live',
    io:{ in:'declared file list', out:'live site (or a review branch + PR)' },
    failure:'Any failed or skipped story routes the whole day to a review PR instead of main, and the run is marked failed.' },

  /* ---- gate zoom-in ---- */
  { id:'g_gate', row:3, kind:'zoom', title:'Zoom: inside stage 9, one article from source text to verified page', sub:'This runs per story, six at a time. Every box is a gate; red means the sentence or story is dropped.', x:3120, y:2420, w:2400, cols:4, color:'#b45309', layer:'live' },

  /* ---- state store ---- */
  { id:'g_state', row:3, kind:'lane', title:'Memory between runs: .editorial-state/', sub:'The pipeline is stateless except for these files. Several are committed to git so tomorrow\'s clean runner inherits them.', x:60, y:2420, w:2960, cols:4, color:'#7c3aed', layer:'live' },

  /* ---- public site ---- */
  { id:'g_public', row:2, kind:'lane', title:'The public site (Netlify)', sub:'What readers and crawlers actually see.', x:5260, y:900, w:860, cols:2, color:'#15803d', layer:'live' },
  { id:'g_readers', row:2, under:'g_public', kind:'lane', title:'Readers and the feedback loop', sub:'What the site records about readers, and where it goes.', x:5260, y:1700, w:860, cols:2, color:'#be185d', layer:'live' },

  /* ---- weekly wrap ---- */
  { id:'g_wrap', row:4, kind:'lane', title:'Friday weekly wrap (separate flow)', sub:'Runs Fridays 16:30 ET. Reads what the daily pipeline already published, groups it by sector, fact-checks every line, publishes one page.', x:60, y:3560, w:2920, cols:5, color:'#0f766e', layer:'weekly',
    failure:'More than half the items falling back to plain excerpts aborts publication. Fewer than 8 published items that week: no wrap.' },

  /* ---- monitoring ---- */
  { id:'g_monitor', row:4, kind:'lane', title:'Monitoring, CI and weekly analysis', sub:'Things that watch the system. Only CI blocks anything; the rest write reports.', x:3080, y:3560, w:1700, cols:2, color:'#4d7c0f', layer:'monitor' },

  /* ---- satellites ---- */
  { id:'g_social', row:4, kind:'lane', title:'Satellites: LinkedIn, PDFs, carousels, Ideas, buildings', sub:'Real code, but none of it is in the daily workflow. It is run by hand or by the old local scheduler.', x:4840, y:3560, w:1280, cols:2, color:'#9333ea', layer:'satellite' },

  /* ---- voice engine ---- */
  { id:'g_voice', row:5, kind:'lane', title:'Voice engine (designed and prototyped, not yet in production)', sub:`The next evolution of stage 9: a story brief, then a draft in Ben Rohr's voice, then a gate that proves the facts and polices the opinion.`, x:60, y:5000, w:2400, cols:3, color:'#c2410c', layer:'voice',
    failure:'Behind a flag when built. Fail-closed on facts exactly as today; opinion sentences that fail a rule are deleted, never published.' },

  /* ---- legacy ---- */
  { id:'g_legacy', row:6, kind:'lane', title:'Legacy: the v2 and v3 pipelines still in the repo', sub:'Not on the live path. Kept as rollback options (workflow dispatch can still run v3 or v2). Dashed boxes are dead weight unless you need rollback.', x:60, y:4760, w:6060, cols:6, color:'#78716c', layer:'legacy' }
],

/* ----------------------------------------------------------------- NODES */
nodes: [
  /* ===== 0 · TRIGGER ===== */
  { id:'wf_daily', group:'g_trigger', kind:'workflow', status:'live', name:'daily-insights-agent.yml', file:'.github/workflows/daily-insights-agent.yml',
    tagline:'The one production publisher. Cron 07:07 ET plus manual dispatch.',
    does:['Two cron triggers (11:07 and 12:07 UTC) cover daylight and standard time; the policy script keeps only the right one.',
      'Steps: checkout → resolve policy → install locked deps → compile + unit tests + validate_publication + JS tests → provider preflight → run insights_v3.py → validate again → write run report → zero-output gate → upload artifacts → decide branch → publish_generated → verify deployment or roll back → open review PR if needed.',
      'Manual dispatch can choose mode (shadow / preview / publish) and pipeline (v4 / v3 / v2).'],
    inputs:['cron or dispatch','secrets: DEEPSEEK_API_KEY, OPENAI_API_KEY, NEWSAPI_KEY'], outputs:['a commit on main, or a codex/editorial-review-<run> branch and PR','artifact: .editorial-state/ + editions/ (30 days)'],
    numbers:[['timeout','120 min'],['v4 args','--daily-target 70 --article-limit 70 --quality-floor 40'],['concurrency group','curated-insights-edition (shared with the weekly wrap)']],
    levers:['Change the schedule, the target (70) or the quality floor (40) in the v4 case block.','ARTICLE_COUNT input is ignored by v4 (fixed 70).'], flags:['F16','F7'], touches:['st_decision','st_generated'] },
  { id:'resolve_policy', group:'g_trigger', kind:'script', status:'live', name:'resolve_schedule_policy.py', file:'scripts/resolve_schedule_policy.py',
    tagline:'Decides run or skip from the cron expression that fired, not the clock.',
    does:['Looks at which cron string triggered the job and converts it to New York time.','Accepts 07:05–07:15 ET; anything else is "skip" (the inactive DST twin).','Schedule runs are always mode=publish; manual runs use the dispatch input.'],
    inputs:['GitHub event name, trigger cron'], outputs:['skip=true|false, mode=...'] },
  { id:'st_scheduler', group:'g_trigger', kind:'state', status:'state', name:'scheduler.json (lease)', file:'.editorial-state/scheduler.json',
    tagline:'Says GitHub Actions is the only active publisher.',
    does:['active_scheduler = "github-actions".','The old Windows task reads this and exits without publishing, preventing double publication.'], inputs:[], outputs:[] },
  { id:'model_router', group:'g_trigger', kind:'script', status:'live', name:'model_router.py', file:'scripts/model_router.py',
    tagline:'Picks the AI provider and logs every call.',
    does:['DeepSeek is primary (model deepseek-v4-pro); OpenAI is the fallback (gpt-4o for writing, gpt-4o-mini otherwise).','select_provider() sends a 4-token ping to each and returns the first healthy one.','log_provider_event() appends a secret-free line per call to provider-log.jsonl.','Also run as a script in the workflow as a provider preflight.'],
    inputs:['env keys'], outputs:['provider config dict','provider-log.jsonl'],
    numbers:[['health ping timeout','15 s'],['log kept','last 1,000 lines once >512 KB']],
    levers:['DEEPSEEK_MODEL / OPENAI_MODEL_WRITING env vars change models without code edits.'], flags:['F6','F11'], touches:['st_provider'] },
  { id:'agent_runtime', group:'g_trigger', kind:'script', status:'legacy', name:'agent_runtime.py + run_agent_runtime.bat', file:'scripts/agent_runtime.py',
    tagline:'The old local Windows scheduler. Yields to the lease.',
    does:['Ran the v2 publisher from an isolated git worktree on a PC.','Today it checks scheduler.json and exits successfully without publishing.'], inputs:[], outputs:[], flags:['F15'] },

  /* ===== EXTERNAL ===== */
  { id:'x_deepseek', group:'g_external', kind:'external', status:'external', name:'DeepSeek API', tagline:'Writer (thinking off) and fact-checker (reasoning on).',
    does:['Model deepseek-v4-pro.','Writer: temperature 0.35, 90 s per request.','Fact-check passes: reasoning mode, temperature 0, up to 16,000 output tokens.'], inputs:[], outputs:[], flags:['F6'] },
  { id:'x_openai', group:'g_external', kind:'external', status:'external', name:'OpenAI API', tagline:'Preferred independent fact-checker. Currently has no credit.',
    does:['As of 2026-10-08 the account returns insufficient_quota (429).','The fact-check client marks a provider dead after an auth or quota error and falls through to DeepSeek.'], inputs:[], outputs:[], flags:['F6'] },
  { id:'x_feeds', group:'g_external', kind:'external', status:'external', name:'Publisher feeds and index pages', tagline:'~148 RSS feeds plus up to 12 index pages.',
    does:['RSS from trade press, government bodies, research firms.','Index pages for publishers with no feed (robots.txt obeyed, no user-agent tricks).'], inputs:[], outputs:[] },
  { id:'x_github', group:'g_external', kind:'external', status:'external', name:'GitHub (repo + Actions)', tagline:'Scheduler, runner, and the durable store.',
    does:['Runs the workflows.','The repo itself is the database: memory, manifest and pages are committed back to main.'], inputs:[], outputs:[] },
  { id:'x_netlify', group:'g_external', kind:'external', status:'external', name:'Netlify', tagline:'Builds and serves the site on every push to main.',
    does:['Static hosting plus serverless functions in netlify/functions.','netlify.toml holds redirects and a daily analytics-retention schedule.'], inputs:[], outputs:[] },

  /* ===== 1 · INGEST ===== */
  { id:'cfg_sources', group:'s1', kind:'config', status:'config', name:'sources.json', file:'config/sources.json',
    tagline:'The source list: 255 entries, 171 marked active.',
    does:['Each source has a tier (1–4), sectors, type, fetch frequency, and a "health" block written by the feed probe.','Types among active: 91 industry publications, 34 government, 16 html_listing, 11 mainstream business, 7 research, 7 NewsAPI, 3 government research, 2 wires.','Tier counts among active: T1 40 · T2 73 · T3 39 · T4 19.'],
    inputs:['edited by hand and by source_health_probe'], outputs:['read by ingestion.py and insights_v3 (listing sources)'],
    levers:['Add or retire a feed here: set "active". This is the main lever on what the system can see.'], flags:['F7','F8'], touches:[] },
  { id:'ingestion', group:'s1', kind:'script', status:'live', name:'ingestion.py', file:'scripts/ingestion.py',
    tagline:'Fetches every active feed in parallel and normalises entries.',
    does:['8 worker threads; 8 s connect / 15 s read timeouts; up to 500 entries per feed.','Keeps only entries from the last 36 hours.','Hands feedparser the bytes (urllib has no timeout, which once stalled a whole run).','Skips any source whose URL is "newsapi.org" (the 7 NewsAPI entries).','Has no source-type filter, so index-page sources are also tried as RSS (suspected waste).'],
    inputs:['config/sources.json'], outputs:['list of CanonicalItem'], numbers:[['workers','8'],['lookback','36 h'],['max entries / feed','500']],
    levers:['LOOKBACK_HOURS widens or narrows the day.','MAX_WORKERS for speed.'], flags:['F7','F8'], touches:['st_health'] },
  { id:'source_health', group:'s1', kind:'script', status:'live', name:'source_health.py', file:'scripts/source_health.py',
    tagline:'Circuit breaker for broken feeds.',
    does:['Counts consecutive failures per source and opens a temporary circuit after repeated failures.','Retries after a cooldown so a transient outage recovers on its own.','Stores operational metadata only, never article content.'], inputs:['feed results'], outputs:['source-health.json'], touches:['st_health'] },
  { id:'canonical_item', group:'s1', kind:'script', status:'live', name:'canonical_item.py', file:'scripts/canonical_item.py',
    tagline:'The document data model every later stage shares.',
    does:['CanonicalItem: headline, summary, url, source, date, sector fields, transaction hints.','Repairs mojibake (UTF-8 read as Windows-1252), strips markup and control characters from headlines.'], inputs:['raw feed entry'], outputs:['CanonicalItem'] },
  { id:'html_listing', group:'s1', kind:'script', status:'live', name:'html_listing.py', file:'scripts/html_listing.py',
    tagline:'Reads publishers that have no feed, only if their robots.txt allows it.',
    does:['Reads an index page, extracts plausible article links, and returns up to 15 per source.','robots.txt is checked for the index and again for every article; a 401/403/429 is recorded as a refusal and never retried with another identity.','No user-agent rotation or proxy support exists by design.'],
    inputs:['listing sources from sources.json (first 12)'], outputs:['CanonicalItems from index pages'], numbers:[['sources read','12 of 16 active'],['items per source','15']],
    levers:['--listing-limit raises the 12.'], flags:['F8'] },

  /* ===== 2 · CLASSIFY ===== */
  { id:'classification', group:'s2', kind:'script', status:'live', name:'classification.py', file:'scripts/classification.py',
    tagline:'Assigns sector, subsector, event type and geography to every document.',
    does:['Source priors (e.g. The Real Deal → commercial real estate), then regex signal density per sector, then watchlist entities.','Seven sectors: commercial_real_estate, private_equity, data_centers, energy, banking_credit, fed_macro, local_government.','Never rejects: every document continues.'],
    inputs:['CanonicalItems','config/sectors.json','config/watchlists.json'], outputs:['items with primary_sector + secondary'], levers:['Edit the regex patterns or source priors to move stories between sectors.'] },
  { id:'cfg_sectors', group:'s2', kind:'config', status:'config', name:'sectors.json', file:'config/sectors.json',
    tagline:'The taxonomy: sectors, subsectors and event types.', does:['Commercial real estate alone lists 18 subsectors (multifamily, industrial_logistics, office, retail, hospitality...) and ~30 event types.','Used by classification and content_typing.'], inputs:[], outputs:[] },
  { id:'cfg_watchlists', group:'s2', kind:'config', status:'config', name:'watchlists.json', file:'config/watchlists.json',
    tagline:'Named entities that signal a sector.', does:['Companies, lenders and agencies used by entity recognition during classification.'], inputs:[], outputs:[] },

  /* ===== 3 · CLUSTER ===== */
  { id:'event_clustering', group:'s3', kind:'script', status:'live', name:'event_clustering.py', file:'scripts/event_clustering.py',
    tagline:'One event, one object, however many outlets covered it.',
    does:['Scores pairs of documents 0–1 using: shared dollar amount (strongest), shared capitalised entities, headline word overlap, and shared figures like units or square feet.','Merges at 0.62 or above; no embeddings and no model call, so every merge is explainable.','Records the reasons for each merge in an audit.'],
    inputs:['classified documents'], outputs:['IntelligenceObjects + merge audit'], numbers:[['MERGE_THRESHOLD','0.62']], levers:['Raise the threshold to merge less; lower it to merge more.'] },
  { id:'intelligence_object', group:'s3', kind:'script', status:'live', name:'intelligence_object.py', file:'scripts/intelligence_object.py',
    tagline:'The ranking unit: one thing that happened.',
    does:['Holds sources (with how each was retrieved), extracted facts, scores, novelty state, depth and selection rationale.','Defines the vocabularies: 17 content types, 5 evidence levels, 6 novelty states.','Evidence caps depth: corroborated → up to tier_a; one full text → tier_b; summary only → tier_c; nothing usable → none.'],
    inputs:['clusters'], outputs:['IntelligenceObject'], numbers:[['evidence levels','primary_corroborated · corroborated · single_full_text · single_summary · insufficient']] },

  /* ===== 4 · TYPE & GATE ===== */
  { id:'content_typing', group:'s4', kind:'script', status:'live', name:'content_typing.py', file:'scripts/content_typing.py',
    tagline:'Works out what a document IS before asking how important it is.',
    does:['Classifies into 17 content types. Marketing, explainers, listicles, personnel notices, event promotions, admin notices and digests are never eligible.','Interviews and opinion pieces are not blanket-excluded: they qualify only with a "material disclosure".','Also assigns event type and subsector from the configured lists.'],
    inputs:['title, summary, sector'], outputs:['content_type + evidence spans'] },
  { id:'eligibility', group:'s4', kind:'script', status:'live', name:'eligibility.py', file:'scripts/eligibility.py',
    tagline:'Decides if a story deserves a slot, by event family, and says why.',
    does:['Hard disqualifiers: never-eligible content type, no usable source, no sector, no recognisable Light Tower beat anchor.','Five families with different rules: transaction_or_development (needs a verb and scale), policy_or_macro and data_or_signal (needs an action or a number, no dollar figure required), interview_or_opinion (needs a material disclosure), primary_document (always eligible).','Nothing is eligible by default; every decision stores its rationale.'],
    inputs:['IntelligenceObject (and, in stage 6, the full article body)'], outputs:['eligible, reason, evidence'], levers:['The beat-anchor and consumer-property patterns decide what the desk considers on-topic.'] },

  /* ===== 5 · MEMORY ===== */
  { id:'editorial_memory', group:'s5', kind:'script', status:'live', name:'editorial_memory.py', file:'scripts/editorial_memory.py',
    tagline:'What we have already seen, chosen and published.',
    does:['Matches each object against 45 days of history using the same signals as clustering (match at 0.58).','Assigns: new · new_stage · material_update · minor_follow_up · duplicate · already_published.','A change of 15% or more in a figure counts as material.','Seeds itself from insights.json when empty; keeps records 120 days; marks stories published after stage 10.'],
    inputs:['objects','insights.json (seed)'], outputs:['novelty state per object','editorial-memory.json'], numbers:[['LOOKBACK_DAYS','45'],['MATCH_THRESHOLD','0.58'],['MATERIAL_CHANGE','0.15'],['RETENTION','120 days']], touches:['st_memory','pub_manifest'] },

  /* ===== 6 · ENRICH ===== */
  { id:'retrieval', group:'s6', kind:'script', status:'live', name:'retrieval.py', file:'scripts/retrieval.py',
    tagline:'Lawful, bounded article fetching. Always says what kind of thing it got.',
    does:['8 s connect / 15 s read timeouts, 3 MB cap, 6 workers, 1 s minimum gap per domain, 2 attempts, 6-hour cache.','robots.txt is obeyed: a disallowed path is skipped, never worked around.','Records a retrieval status (full_text, partial_text, blocked, failed) so nothing downstream mistakes a snippet for a full read.','Upgrades each object\'s evidence level, extracts facts, and caches pages on disk.'],
    inputs:['shortlist (≤250, eligible first)'], outputs:['full text on each SourceRef','retrieval-cache/*.json'], numbers:[['limit','250 objects'],['phase budget','420 s'],['cache TTL','6 h']],
    levers:['--enrich-limit and --enrich-budget on insights_v3.py.'], touches:['st_cache'] },
  { id:'fact_extractor', group:'s6', kind:'script', status:'live', name:'fact_extractor.py', file:'scripts/fact_extractor.py',
    tagline:'Pulls amounts, percentages, companies, addresses and dates by regex.',
    does:['No model calls.','Feeds the dossier\'s "facts" list and (in older paths) the post-hoc article fact audit.'], inputs:['retrieved text'], outputs:['Fact objects'] },

  /* ===== 7 · SCORE ===== */
  { id:'importance', group:'s7', kind:'script', status:'live', name:'importance.py', file:'scripts/importance.py',
    tagline:'0–100 importance with eight measures that must each vary and explain themselves.',
    does:['Measures and base weights: magnitude 1.5 · market_impact 1.3 · parties 1.1 · precedent 1.2 · novelty 1.2 · story_richness 1.2 · evidence 1.4 · right_to_win 1.1. (A ninth, "surprise", is retired.)','Magnitude uses a per-sector dollar ladder (a $100M trade is big in CRE, small in private equity).','Sector profiles from scoring_profiles.json nudge the weights; weighted average × 10.','Penalties: archive repetition −18, minor follow-up −8, uncorroborated press release −10, opinion format −6.','Bands: 90+ defining · 80 major · 70 important · 60 solid · 50 signal · 40 routine · <40 not publishable.','distribution_report() flags any measure that stops varying.'],
    inputs:['enriched objects','config/scoring_profiles.json'], outputs:['final_score, tier, per-measure rationale'], numbers:[['SCORE_VERSION','importance-v3']],
    levers:['MEASURE_CONTRACTS weights, the magnitude ladders, penalty sizes, or scoring_profiles.json per sector.'] },
  { id:'cfg_profiles', group:'s7', kind:'config', status:'config', name:'scoring_profiles.json', file:'config/scoring_profiles.json',
    tagline:'Per-sector nudges to the measure weights.', does:['Read by importance.py through a small alias table (e.g. "magnitude" → financial_magnitude).'], inputs:[], outputs:[] },

  /* ===== 8 · SELECT ===== */
  { id:'selection', group:'s8', kind:'script', status:'live', name:'selection.py', file:'scripts/selection.py',
    tagline:'Chooses the day\'s slate and can explain every choice.',
    does:['Per sector: eligible objects at or above the floor (40), best first, up to 10.','Soft diversity: at most 3 per publisher and 3 per company, but under-filling is worse, so deferred items refill.','Global ranking of all sector picks; the publication slate is the top 70 (7 sectors × 10).','Depth by score: ≥70 tier_a, ≥50 tier_b, else tier_c; tier_a also needs 3 independent sources and 2 full texts; then capped by the evidence level.','Records a runner-up and a shortfall reason for every sector.'],
    inputs:['scored objects'], outputs:['SlateReport (v3-slates.json)','recommended_depth on each object'], numbers:[['QUALITY_FLOOR','40'],['SECTOR_TARGET','10'],['MAX_DAILY_ARTICLES','70'],['MAX_PER_SOURCE / COMPANY','3 / 3'],['TIER_A / TIER_B floor','70 / 50']],
    levers:['These constants are hard-coded here. config/thresholds.json does NOT drive them (flag F2).'], flags:['F2'], touches:['st_slates'] },
  { id:'budget', group:'s8', kind:'script', status:'live', name:'budget.py', file:'scripts/budget.py',
    tagline:'Spending and time ceilings, kept in a daily ledger.',
    does:['Budget.allow() is asked before each model call and refuses past the daily ceiling ($25 in thresholds.json).','The ledger is keyed by date, so retries share one ceiling.','Is constructed and reported by insights_v3 but, in the v4 writer, is accepted and never used.'],
    inputs:['config/thresholds.json'], outputs:['spend-ledger.json'], numbers:[['max daily LLM cost','$25 (declared)']], flags:['F5'], touches:['st_spend'] },

  /* ===== 9 · WRITE ===== */
  { id:'v4_generation', group:'s9', kind:'script', status:'live', name:'v4_generation.py', file:'scripts/v4_generation.py',
    tagline:'The writer: Ben\'s voice for flagships and analyses, facts-only for briefs, nothing unverified.',
    does:['Voice path (INSIGHTS_VOICE=on; tier_a and tier_b): a brief call (shape, lens, hooks), the piece in Ben\'s voice, the fact gate on every fact, the voice gate on every take and voice line, one rewrite, then a single fallback to the facts-only writer.','Every model call goes through _chat(): DeepSeek only, retries after 0/4/12 s for rate limits, server errors and dropped connections, spend checked before and recorded after, and a shared health check that stops new stories after 3 exhausted calls or one refused key.','write_all(): 6 workers, 300 s per article (540 s in the voice path), edition window 2,700 s (set by insights_v3), at most 2 attempts per article.','_safe_dossier(): the factual boundary, each source capped at 5,000 characters.','_writer_prompt(): asks for JSON sentences, each with verbatim quotes; no opinions, predictions or closing advice.','write_one(): request → verify → assemble → validate → retry once with the rejections quoted back → choose the best verified candidate, else withheld or failed.','Writes an evidence file per article and a draft cache keyed by dossier hash and prompt version.','Lengths: brief 60–300 words, analysis 100–520, flagship 220–850; minimum 3 / 5 / 8 verified facts or the story is withheld.'],
    inputs:['IntelligenceObjects on the slate','provider config'], outputs:['DraftResult per story','v4-drafts/, v4-evidence/, v4-article-state.jsonl'], numbers:[['writer temperature','0.35'],['attempts / article','2'],['min facts (a/b/c)','8 / 5 / 3'],['edition window','2,700 s']],
    levers:['_writer_prompt wording, MIN_FACT_SENTENCES, DEPTH_SPEC, WRITER_PROMPT_VERSION (bump it to invalidate cached drafts).'], flags:['F5','F10','F11'], touches:['st_v4','st_evidence','st_provider'] },
  { id:'claim_verifier', group:'s9', kind:'script', status:'live', name:'claim_verifier.py', file:'scripts/claim_verifier.py',
    tagline:'The accuracy gate. Deterministic checks first, then two model passes.',
    does:['Quote check: every quote must appear verbatim in the source (≥4 words, ≤240 characters).','Numbers (including spelled-out), names, quoted phrases must appear in that sentence\'s own quote.','A sentence may not drop a qualifier (most, about, plans, expects, could) or an attribution (said, according to) that its quote carries.','Anything that is not a quoted fact (opinion, prediction, advice) is refused.','Pass 1: yes/no ruling per sentence. Pass 2: split into atomic claims and test each. Both must say supported; chunks of 8; fail-closed if the checker cannot answer.','verify_unquoted() applies the same gate to the weekly wrap (no quote requirement).'],
    inputs:['draft JSON','source text','a model callable'], outputs:['VerifiedDraft (kept sentences + rejection reasons)'], numbers:[['quote length','≤240 chars'],['chunk size','8 sentences'],['model passes','2']],
    levers:['MAX_QUOTE_CHARS, the qualifier and attribution lists, the two verifier prompts.'], flags:['F6'] },
  { id:'readability', group:'s9', kind:'script', status:'live', name:'readability.py', file:'scripts/readability.py',
    tagline:'Plain-English limits and the number/name tripwires.',
    does:['Warnings (retry feedback, not blocks): mean sentence ≤22 words, none over 35, paragraphs ≤60 words, "The" openings ≤35%, banned phrases, "what remains unknown" closers, incomplete excerpts.','Number guard that allows rescaling and rounding ($16,782,000 ≈ $16.8 million) but not derived or hypothetical figures.','Name tripwire for capitalised names missing from the source; sentence splitter that respects U.S., Gov., Aug., J.P.'], inputs:['paragraph text'], outputs:['warning strings'], levers:['The MAX_* constants at the top of the file.'] },
  { id:'v3_generation', group:'s9', kind:'script', status:'live', name:'v3_generation.py (partial)', file:'scripts/v3_generation.py',
    tagline:'Only three things are still used from the old writer.',
    does:['object_to_dossier() builds the evidence packet; DraftResult is the result type; DEPTH_SPEC is imported but v4 defines its own.','The rest (the 7-stage editorial_pipeline writer) is the v3 rollback path.'], inputs:['IntelligenceObject'], outputs:['dossier dict'], flags:['F10'] },

  /* ===== 10 · PUBLISH ===== */
  { id:'v3_publish', group:'s10', kind:'script', status:'live', name:'v3_publish.py', file:'scripts/v3_publish.py',
    tagline:'Puts finished drafts on the site, idempotently and without half-states.',
    does:['Slug from the title; an existing slug is skipped, so a rerun never double-publishes.','Maps each sector to a reader category (energy → "Market Commentary", banking → "Debt & Equity"...), trims subtitle and meta description at sentence or word boundaries.','Writes the social image, renders the page, then updates insights.json, feed.xml and sitemap.xml once at the end, then writes the related-articles JSON.','finalize_publication(): builds the edition record and decision, runs validation, and writes the declared-files list.'],
    inputs:['verified drafts','objects'], outputs:['insights/<slug>.html + _social.png + _related.json','insights.json, feed.xml, sitemap.xml'], levers:['_CATEGORY maps sectors to reader-facing categories.'], flags:['F1','F14'], touches:['pub_pages','pub_manifest','pub_feed','st_memory'] },
  { id:'site_renderer', group:'s10', kind:'script', status:'live', name:'site_renderer.py', file:'scripts/site_renderer.py',
    tagline:'Builds the article page, insights.json, feed.xml and sitemap.xml.',
    does:['render_html(): the full standalone article page (sanitised body, share buttons, structured data, CTA).','update_manifest(): adds or replaces the entry in insights.json, now with the story\'s sector so the page filters work.','update_feed_xml() and update_sitemap_xml(): rebuild the RSS feed and sitemap from the manifest.','Moved unchanged out of daily_news_agent.py on 2026-10-09; the legacy agent re-exports it.'],
    inputs:['article dict from v3_publish or weekly_wrap'], outputs:['insights/<slug>.html','insights.json','feed.xml','sitemap.xml'], numbers:[['lines','~520']],
    levers:['The page template inside render_html().'], flags:[], touches:['pub_pages','pub_manifest'] },
  { id:'daily_digest', group:'s10', kind:'script', status:'live', name:'daily_digest.py', file:'scripts/daily_digest.py',
    tagline:'The page Ben reads: every published sentence beside its source quote.',
    does:['Built offline after every v4 writing run from the run report, the drafts and the evidence files.','Shows each story\'s sentences with their kind (fact, Ben\'s read, voice), the quote or facts each rests on, and every cut with its reason.','Lists what was not published and why; writes a five-line health note (stories, checker, spend, time, problems).'],
    inputs:['v3-run.json','v3-drafts.json','v4-evidence/'], outputs:['digest.html','health.txt'], numbers:[], levers:[], flags:[], touches:['st_evidence'] },
  { id:'rehearsal', group:'s10', kind:'script', status:'satellite', name:'rehearsal.py + rehearsal.ps1', file:'scripts/rehearsal.py',
    tagline:'A full preview day outside the repo, for the dress-rehearsal week.',
    does:['Runs insights_v3 --pipeline v4 in preview with Ben\'s voice on into %USERPROFILE%/ltg-rehearsal/<date>/, then the digest.','Refuses to write inside the repository; DeepSeek only; optional spend cap.','rehearsal.ps1 documents the one Task Scheduler command that makes it daily (Ben runs it).'],
    inputs:['DEEPSEEK_API_KEY'], outputs:['a dated folder with digest.html and health.txt'], numbers:[['default slate','70 stories']], levers:['--article-limit, --max-usd, --voice'], flags:[], touches:[] },
  { id:'daily_news_agent', group:'s10', kind:'script', status:'legacy', name:'daily_news_agent.py', file:'scripts/daily_news_agent.py',
    tagline:'The old v2 monolith, still imported for four functions.',
    does:['Live use: render_html(), update_manifest(), update_feed_xml(), update_sitemap_xml() (plus sanitize_html and read time).','Importing it also loads 18 other modules (legacy scoring, LinkedIn essay agent, editorial room...) at import time.','Its own end-to-end flow (RSS + NewsAPI → score → write → publish) is the v2 rollback path.','The version in your working tree has an unfinished edit (a try/finally in update_manifest) that fails to compile; production uses the committed copy.'],
    inputs:['article dict'], outputs:['HTML page, manifest entry, feed.xml, sitemap.xml'], flags:['F1'] },
  { id:'social_image', group:'s10', kind:'script', status:'live', name:'social_image_generator.py', file:'scripts/social_image_generator.py',
    tagline:'Branded 1200×628 share card for each article.', does:['Pillow-based image: cream background, gold accent, serif title.','Failure degrades silently: a page is published without a card.'], inputs:['title, subtitle'], outputs:['<slug>_social.png'] },
  { id:'edition_manager', group:'s10', kind:'script', status:'live', name:'edition_manager.py', file:'scripts/edition_manager.py',
    tagline:'Builds the daily edition record and the list of files allowed to ship.',
    does:['build_edition_document(): latest-edition.json and editions/DATE.json (flagship, briefs, deal tape, reader prompt, selection summary).','Writes publication-decision.json, run records and run-summary.md.','write_generated_files(): the explicit allow-list that publish_generated.py will commit.'], inputs:['published article summaries'], outputs:['latest-edition.json','editions/*.json','generated-files.json','publication-decision.json'], flags:['F4','F16'], touches:['st_decision','st_generated','pub_edition'] },
  { id:'validate_publication', group:'s10', kind:'script', status:'live', name:'validate_publication.py', file:'scripts/validate_publication.py',
    tagline:'Last check before anything can reach main.',
    does:['For the 10 newest manifest entries: exactly one <h1>, a canonical link, the title present, a sources block, no mojibake.','feed.xml and sitemap.xml must parse; latest-edition.json must have a valid status and every referenced page must exist.','Runs twice in the workflow (before and after generation) and inside finalize_publication.'], inputs:['repo files'], outputs:['pass or a list of errors'] },
  { id:'content_governance', group:'s10', kind:'script', status:'live', name:'content_governance.py', file:'scripts/content_governance.py',
    tagline:'Shared helpers: load archive records, near-duplicate checks.', does:['load_insight_records() feeds the related-articles step.','Also used by the legacy writers for quality and independence checks.'], inputs:[], outputs:[] },

  /* ===== 11 · RELEASE ===== */
  { id:'publish_generated', group:'s11', kind:'script', status:'live', name:'publish_generated.py', file:'scripts/publish_generated.py',
    tagline:'Commits exactly the declared files, nothing else.',
    does:['Rejects absolute paths, "..", and .git paths; fails if a declared file is missing.','git add only the declared list → commit → fetch → rebase onto the latest remote → push → verify the remote SHA equals ours.','A rebase conflict stops publication rather than overwriting newer work.'], inputs:['.editorial-state/generated-files.json'], outputs:['a commit on main or on the review branch'], touches:['st_generated'] },
  { id:'verify_deployment', group:'s11', kind:'script', status:'live', name:'verify_deployment.py', file:'scripts/verify_deployment.py',
    tagline:'Polls the live site until the new edition is actually there.',
    does:['Fetches https://lighttowergroup.co/latest-edition.json with a release-keyed URL and compares date, generated_at, status and article slugs.','Gives up after 600 s.'], inputs:['latest-edition.json (local copy)'], outputs:['exit code'], flags:['F4'] },
  { id:'rollback_release', group:'s11', kind:'script', status:'live', name:'rollback_release.py', file:'scripts/rollback_release.py',
    tagline:'Reverts a failed release, only if main still points at it.', does:['Safe by construction: if anyone pushed since, it refuses to touch anything.'], inputs:['expected SHA'], outputs:['a revert commit'] },
  { id:'review_pr', group:'s11', kind:'human', status:'live', name:'Editorial review PR', tagline:'Where a day goes when anything failed or was skipped.',
    does:['Branch codex/editorial-review-<run id> plus a pull request whose body is run-summary.md.','Nothing reaches the site until you merge it.'], inputs:[], outputs:[], flags:['F16'] },

  /* ===== STATE STORE ===== */
  { id:'st_memory', group:'g_state', kind:'state', status:'state', name:'editorial-memory.json', file:'.editorial-state/editorial-memory.json', tagline:'Events seen, chosen, published (120 days).', does:['Read in stage 5, updated at the end of every run, committed to git.'], inputs:[], outputs:[] },
  { id:'st_cache', group:'g_state', kind:'state', status:'state', name:'retrieval-cache/', file:'.editorial-state/retrieval-cache', tagline:'Every fetched article, keyed by URL.', does:['One JSON per page with text, status and final URL; 6-hour TTL.','Also the corpus the accuracy audits ran against.'], inputs:[], outputs:[] },
  { id:'st_health', group:'g_state', kind:'state', status:'state', name:'source-health.json', file:'.editorial-state/source-health.json', tagline:'Circuit-breaker state per feed.', does:['Written by ingestion, committed.'], inputs:[], outputs:[] },
  { id:'st_slates', group:'g_state', kind:'state', status:'state', name:'v3-run / v3-slates / v3-candidates.json', file:'.editorial-state/v3-run.json', tagline:'Why each candidate was or was not chosen.', does:['v3-candidates.json holds every candidate with its score components, so a decision can be audited afterwards.','Only compact files are committed; the large ones are workflow artifacts.'], inputs:[], outputs:[] },
  { id:'st_v4', group:'g_state', kind:'state', status:'state', name:'v4-drafts/ and v4-article-state.jsonl', file:'.editorial-state/v4-drafts', tagline:'Cached verified drafts and a per-article event log.', does:['A draft is reused only if the dossier hash, depth and prompt version match and it carries the fact_checked stamp.'], inputs:[], outputs:[] },
  { id:'st_evidence', group:'g_state', kind:'state', status:'state', name:'v4-evidence/', file:'.editorial-state/v4-evidence', tagline:'Per article: every sentence with its quotes, and every rejection with its reason.', does:['The audit trail for "where did this sentence come from?".','Spot-check these before trusting a day\'s output.'], inputs:[], outputs:[] },
  { id:'st_provider', group:'g_state', kind:'state', status:'state', name:'provider-log.jsonl', file:'.editorial-state/provider-log.jsonl', tagline:'One secret-free line per model call.', does:['Writer calls, fact-check calls, wrap calls; used for the run summary.'], inputs:[], outputs:[] },
  { id:'st_spend', group:'g_state', kind:'state', status:'state', name:'spend-ledger.json', file:'.editorial-state/spend-ledger.json', tagline:'Daily spend by date.', does:['Written by budget.py. With the v4 writer it is not incremented.'], inputs:[], outputs:[], flags:['F5'] },
  { id:'st_decision', group:'g_state', kind:'state', status:'state', name:'publication-decision.json', file:'.editorial-state/publication-decision.json', tagline:'The verdict that routes the release.', does:['edition_status (ready / partial_failure / provider_failure / no_publishable_story), article and failed counts.','auto_publish_allowed is true only if nothing failed or was skipped and at least one article published.'], inputs:[], outputs:[], flags:['F16'] },
  { id:'st_generated', group:'g_state', kind:'state', status:'state', name:'generated-files.json', file:'.editorial-state/generated-files.json', tagline:'The allow-list of files a release may commit.', does:['Overwritten by whichever job published last (daily or wrap).'], inputs:[], outputs:[] },
  { id:'st_signals', group:'g_state', kind:'state', status:'state', name:'audience-signals(.live).json', file:'.editorial-state/audience-signals.json', tagline:'Reader and LinkedIn engagement weights.', does:['Written by the LinkedIn engagement scraper and by the editorial-feedback function.','Read only by the legacy v2 code and the weekly retrospective, not by the live pipeline.'], inputs:[], outputs:[], flags:['F13'] },
  { id:'st_queue', group:'g_state', kind:'state', status:'state', name:'assignment-queue.json, structured-candidates.json', file:'.editorial-state/assignment-queue.json', tagline:'Weekly commissioned investigations and SEC items.', does:['Written by the Sunday assignment desk.','Read only by daily_news_agent.py\'s legacy discovery.'], inputs:[], outputs:[], flags:['F3'] },
  { id:'st_runs', group:'g_state', kind:'state', status:'state', name:'runs/, run-summary.md, weekly-wraps/', file:'.editorial-state/runs', tagline:'Per-day run records and the Friday wrap records.', does:['run-summary.md becomes the PR body for review branches.'], inputs:[], outputs:[] },

  /* ===== GATE ZOOM ===== */
  { id:'gt1', group:'g_gate', kind:'script', status:'live', name:'W1 · Build the dossier', file:'scripts/v3_generation.py',
    tagline:'Source text + facts packed into the boundary the writer may use.', does:['object_to_dossier() then _safe_dossier(): each source text ≤5,000 characters, whole packet ≤18,000.','Quotes must come from source "text" only, never from derived summaries.'], inputs:['object'], outputs:['dossier'] },
  { id:'gt2', group:'g_gate', kind:'script', status:'live', name:'W2 · Writer request', file:'scripts/v4_generation.py',
    tagline:'DeepSeek returns structured sentences with quotes.', does:['Thinking off, temperature 0.35, 90 s timeout; a rate limit or 5xx is retried only through the attempt budget.','JSON shape: title, title_quote, excerpt, excerpt_quote, paragraphs → sentences {text, kind, quotes}.'], inputs:['prompt'], outputs:['draft JSON'] },
  { id:'gt3', group:'g_gate', kind:'script', status:'live', name:'V1 · Deterministic checks', file:'scripts/claim_verifier.py',
    tagline:'Code only, no model. The cheapest and most trusted gate.', does:['Quote verbatim in source · numbers incl. spelled-out · names · quoted phrases · dropped qualifier · dropped attribution · non-fact kinds refused.','A sentence failing here never reaches a model.'], inputs:['sentences + quotes'], outputs:['rejections (red)'], red:true },
  { id:'gt4', group:'g_gate', kind:'script', status:'live', name:'V2 · Model pass 1', file:'scripts/claim_verifier.py',
    tagline:'Yes/no: is every claim in this sentence in the source?', does:['Reasoning-mode model, temperature 0, chunks of 8 sentences.','Checks causes, rankings, sums, tense, plans-as-facts, misattribution.','Checker unreachable → whole article fails closed.'], inputs:['source + sentences'], outputs:['supported / unsupported + issue'], red:true, flags:['F6'] },
  { id:'gt5', group:'g_gate', kind:'script', status:'live', name:'V3 · Model pass 2', file:'scripts/claim_verifier.py',
    tagline:'Break each sentence into atomic claims and test each one.', does:['Differently framed so it fails differently from pass 1.','A "supported" verdict that lists an unsupported claim is treated as unsupported.'], inputs:['sentences that passed pass 1'], outputs:['supported / unsupported'], red:true },
  { id:'gt6', group:'g_gate', kind:'script', status:'live', name:'A1 · Assemble', file:'scripts/v4_generation.py',
    tagline:'Build the page from surviving sentences only.', does:['Title falls back to the story headline if the writer\'s title fails; excerpt falls back to the first verified fact.','Sources are copied from the dossier by code, never by the model.'], inputs:['verified sentences'], outputs:['article dict (fact_checked: true)'] },
  { id:'gt7', group:'g_gate', kind:'script', status:'live', name:'A2 · Structural + readability validation', file:'scripts/v4_generation.py',
    tagline:'HTML, length, sources, repeats, plain-English limits.', does:['Hard: paragraph-only HTML, word range, minimum paragraphs, sources inside the dossier, no repeated paragraphs.','Soft (retry feedback): sentence and paragraph length, banned phrases, closers, unsupported numbers and names.'], inputs:['article'], outputs:['valid? + warnings'], red:true },
  { id:'gt8', group:'g_gate', kind:'script', status:'live', name:'A3 · One corrective retry', file:'scripts/v4_generation.py',
    tagline:'If anything was rejected or too thin, ask once more.', does:['The retry prompt quotes the rejected sentences and reasons back to the writer.','Skipped when the first attempt was already clean.'], inputs:['rejections, warnings'], outputs:['second draft → back through V1–A2'] },
  { id:'gt9', group:'g_gate', kind:'script', status:'live', name:'A4 · Decide', file:'scripts/v4_generation.py',
    tagline:'Publish the best verified draft, or withhold, or fail.', does:['Best = no warnings, then most verified facts, then later attempt.','Too few verified facts (8 / 5 / 3 by tier) → status "withheld": not a failure, does not block the edition.','Provider or verifier errors → "failed" (blocks auto-publish).','Writes the evidence file and the draft cache.'], inputs:['candidates'], outputs:['completed | withheld | failed'], red:true },

  /* ===== PUBLIC SITE ===== */
  { id:'pub_pages', group:'g_public', kind:'public', status:'live', name:'insights/<slug>.html', file:'insights/', tagline:'One standalone page per article (about 1,450 live).', does:['Rendered by render_html(): headline, subtitle, byline, share buttons, body, tags, CTA block, related research, sources.','Alongside: <slug>_social.png and <slug>_related.json (top 3 by tag overlap).','insights/article-base.css styles the pages, including the weekly-wrap lists.'], inputs:[], outputs:[] },
  { id:'pub_manifest', group:'g_public', kind:'public', status:'live', name:'insights.json', file:'insights.json', tagline:'The manifest: title, slug, date, category, excerpt, tags, format, score, source.', does:['Read by insights.html, by editorial memory (seed) and by the weekly wrap.','Has no "sector" field: sector is only recoverable from tags and category.'], inputs:[], outputs:[], flags:['F14'] },
  { id:'pub_feed', group:'g_public', kind:'public', status:'live', name:'feed.xml + sitemap.xml', file:'feed.xml', tagline:'RSS (latest 50, Google News tags) and a sitemap of every page.', does:['Both regenerated from insights.json after each publish.'], inputs:[], outputs:[] },
  { id:'pub_edition', group:'g_public', kind:'public', status:'live', name:'latest-edition.json + editions/', file:'latest-edition.json', tagline:'The daily edition record.', does:['Written daily; used by verify_deployment.','edition.js can render it, but no page includes edition.js (verified by search).'], inputs:[], outputs:[], flags:['F4'] },
  { id:'pub_listing', group:'g_public', kind:'public', status:'live', name:'insights.html (the Intelligence page)', file:'insights.html', tagline:'Card grid with sector filters, search and a pinned Friday wrap.', does:['Loads /insights.json in the browser, sorts by date, 18 per page.','Filters map category names to buckets, but four of them (Energy, Banking, Fed & Macro, Government) match no current category; "Weekly Wrap" is its own filter plus a feature band.'], inputs:[], outputs:[], flags:['F14'] },
  { id:'pub_js', group:'g_public', kind:'public', status:'live', name:'site.js, chat-widget.js', file:'site.js', tagline:'Shared browser code.', does:['Related-research loader, share buttons, LinkedIn essay and PDF links, scroll tracking.'], inputs:[], outputs:[] },

  /* ===== READERS ===== */
  { id:'fn_track', group:'g_readers', kind:'script', status:'live', name:'track-read.js', file:'netlify/functions/track-read.js', tagline:'Records view, scroll_50, scroll_100, share, copy_link per article.', does:['Called from every article page.','Feeds the analytics dashboard.'], inputs:['browser events'], outputs:['analytics data'] },
  { id:'fn_feedback', group:'g_readers', kind:'script', status:'live', name:'editorial-feedback.js', file:'netlify/functions/editorial-feedback.js', tagline:'Collects reader feedback and tries to append it to audience signals.', does:['Sends a webhook and an email.','Appends to .editorial-state/audience-signals-live.json inside the function\'s own filesystem, which is probably not the repo (suspected).'], inputs:['reader feedback'], outputs:['webhook, email'], flags:['F13'], touches:['st_signals'] },
  { id:'fn_other', group:'g_readers', kind:'script', status:'live', name:'newsletter-subscribe, chat, mandate-submit, deal-notify, analytics-*', file:'netlify/functions/', tagline:'The rest of the serverless layer.', does:['Newsletter signup, chat widget, mandate and deal notifications, analytics dashboard and retention.'], inputs:[], outputs:[] },
  { id:'readers', group:'g_readers', kind:'human', status:'live', name:'Readers, LinkedIn, crawlers', tagline:'The audience.', does:['Sponsors, lenders, brokers, investors; Google News via feed.xml; LinkedIn via links and the satellite agents.'], inputs:[], outputs:[] },

  /* ===== WEEKLY WRAP ===== */
  { id:'wf_wrap', group:'g_wrap', kind:'workflow', status:'weekly', name:'weekly-wrap.yml', file:'.github/workflows/weekly-wrap.yml', tagline:'Fridays 16:30 ET, preview or publish.',
    does:['Two UTC crons (20:30 and 21:30) plus a --scheduled guard that only runs Friday 16:00–19:00 New York time.','Runs the unit tests, builds the wrap, validates, then publish_generated.py.','Shares the daily job\'s concurrency lock.'], inputs:[], outputs:[], numbers:[['timeout','25 min']] },
  { id:'w1', group:'g_wrap', kind:'script', status:'weekly', name:'W1 · Select the week', file:'scripts/weekly_wrap.py', tagline:'Saturday to Friday, from insights.json.', does:['load_week_items(): published items dated in the window, excluding earlier wraps.','Exits if fewer than 8.'], inputs:['insights.json'], outputs:['items'], touches:['pub_manifest'] },
  { id:'w2', group:'g_wrap', kind:'script', status:'weekly', name:'W2 · Classify into 12 sections', file:'scripts/weekly_wrap.py', tagline:'Tags first, then keywords.', does:['Fed/rates · Debt & capital markets · Multifamily · Industrial & warehouse · Office · Retail · Hospitality · Data centers · Energy · Private equity · Policy · Other CRE.','Tag order decides ties; keyword fallback for untagged older items.'], inputs:['items'], outputs:['sections'] },
  { id:'w3', group:'g_wrap', kind:'script', status:'weekly', name:'W3 · Rank, dedupe, cap', file:'scripts/weekly_wrap.py', tagline:'Best six per section.', does:['Score = mustReadScore + format bonus + source count + 12 for CRE-relevant wording.','Drop near-duplicates (same eventId or title similarity ≥0.7).'], inputs:['sections'], outputs:['≤6 items each'], levers:['--max-per-section; the CRE relevance regex.'] },
  { id:'w4', group:'g_wrap', kind:'script', status:'weekly', name:'W4 · Read the lead', file:'scripts/weekly_wrap.py', tagline:'Opening paragraphs of each published page.', does:['The factual boundary for the wrap is the daily article, not the open web.'], inputs:['insights/<slug>.html'], outputs:['~900 characters per item'], flags:['F12'] },
  { id:'w5', group:'g_wrap', kind:'script', status:'weekly', name:'W5 · Write each section', file:'scripts/weekly_wrap.py', tagline:'One model call per section, JSON out.', does:['Per item: a summary and a take that must be what the source itself says matters, or empty.','Guards: numbers must appear in the text, banned phrases, word limits; up to 2 tries.'], inputs:['items'], outputs:['summaries, takes'] },
  { id:'w6', group:'g_wrap', kind:'script', status:'weekly', name:'W6 · Fact-check every line', file:'scripts/claim_verifier.py', tagline:'Same gate as the daily articles, per item.', does:['verify_unquoted(): deterministic checks plus the two model passes against that item\'s own text.','A rejected summary reverts to the plain excerpt; a rejected take is dropped.','On 2026-10-02 data: 21 of 45 items had model lines rejected.'], inputs:['summaries'], outputs:['verified lines'], flags:['F6','F12'] },
  { id:'w7', group:'g_wrap', kind:'script', status:'weekly', name:'W7 · Overview', file:'scripts/weekly_wrap.py', tagline:'Headline, lede and three themes, checked against verified lines only.', does:['Overview lines may only characterise summaries that already passed.'], inputs:['verified summaries'], outputs:['headline, lede, themes'] },
  { id:'w8', group:'g_wrap', kind:'script', status:'weekly', name:'W8 · Build and publish', file:'scripts/weekly_wrap.py', tagline:'Render, then the same publish path as a daily article.', does:['Slug weekly-wrap-<Friday>; idempotent; format "weekly", category "Weekly Wrap".','Uses render_html, update_manifest, feed, sitemap, related; writes weekly-wraps/<date>.json; declares files; publish_generated pushes to main.','Refuses to publish if more than half the items fell back.'], inputs:['sections, overview'], outputs:['page + manifest entry'], touches:['pub_pages','st_runs'] },

  /* ===== MONITORING ===== */
  { id:'wf_quality', group:'g_monitor', kind:'workflow', status:'live', name:'quality.yml', file:'.github/workflows/quality.yml', tagline:'CI on every push: compile, unit tests, validation, JS checks.', does:['py_compile on all scripts, unittest discover, validate_publication, XML and netlify.toml parsing, npm checks.'], inputs:[], outputs:[] },
  { id:'tests', group:'g_monitor', kind:'script', status:'live', name:'tests/ (45 test files, 480 tests)', file:'tests/', tagline:'Offline proofs for each stage.', does:['Includes the v4 writer, claim verifier, readability, weekly wrap, publisher, eligibility, clustering and deployment verification tests.'], inputs:[], outputs:[] },
  { id:'wf_probe', group:'g_monitor', kind:'workflow', status:'live', name:'feed-health-probe.yml', file:'.github/workflows/feed-health-probe.yml', tagline:'Diagnoses every configured feed.', does:['Runs source_health_probe.py; uploads a report.'], inputs:[], outputs:[] },
  { id:'probe', group:'g_monitor', kind:'script', status:'live', name:'source_health_probe.py', file:'scripts/source_health_probe.py', tagline:'Why does or doesn\'t each feed deliver?', does:['Records state (ok, blocked, stale...) per source for the "health" block in sources.json.'], inputs:['sources.json'], outputs:['probe report'] },
  { id:'wf_health', group:'g_monitor', kind:'workflow', status:'live', name:'weekly-health-check.yml', file:'.github/workflows/weekly-health-check.yml', tagline:'Mondays 10:00 ET.', does:['health_report.py → HEALTH.md; weekly_retrospective.py; scoring_recalibration.py (monthly).','Commits HEALTH.md only.'], inputs:[], outputs:['HEALTH.md'] },
  { id:'wf_desk', group:'g_monitor', kind:'workflow', status:'live', name:'weekly-assignment-desk.yml', file:'.github/workflows/weekly-assignment-desk.yml', tagline:'Sundays 06:00 ET.', does:['weekly_assignment_desk.py finds patterns across the week\'s events and writes investigation prompts; structured_sources.py scans SEC EDGAR.','Commits assignment-queue.json and structured-candidates.json.','Nothing on the live path reads those files.'], inputs:[], outputs:['assignment-queue.json'], flags:['F3'], touches:['st_queue'] },
  { id:'recal', group:'g_monitor', kind:'script', status:'live', name:'weekly_retrospective.py, scoring_recalibration.py, scoring_evaluation.py', file:'scripts/weekly_retrospective.py', tagline:'Looks back at runs and asks whether scores matched reader engagement.', does:['Reports only; none of it changes scoring automatically.'], inputs:['runs, audience signals'], outputs:['reports'], touches:['st_signals'] },

  /* ===== SATELLITES ===== */
  { id:'li_essay', group:'g_social', kind:'script', status:'satellite', name:'linkedin_essay_agent.py', file:'scripts/linkedin_essay_agent.py', tagline:'Turns an article into LinkedIn essay candidates and a queue.', does:['Uses the editorial_voice persona and writes linkedin_essay_queue.json (200 entries).','netlify/functions/linkedin-essay.js serves it to the site.'], inputs:['published article'], outputs:['linkedin_essay_queue.json'] },
  { id:'voice', group:'g_social', kind:'script', status:'satellite', name:'editorial_voice.py', file:'scripts/editorial_voice.py', tagline:'The persona, voice modes, headline shapes and AI-tell list.', does:['Used by the LinkedIn, carousel and Ideas agents and the legacy writers.','NOT used by the v4 article writer, which has its own prompt and readability.py.'], inputs:[], outputs:[], flags:['F9'] },
  { id:'pdf', group:'g_social', kind:'script', status:'satellite', name:'article_pdf_generator, pdf_queue, linkedin_pdf_post, linkedin_pdf_scheduler', file:'scripts/article_pdf_generator.py', tagline:'Branded document PDFs posted to LinkedIn.', does:['Render a finished Insight as a document, queue it, upload via the LinkedIn API on a schedule.'], inputs:[], outputs:[] },
  { id:'carousel', group:'g_social', kind:'script', status:'satellite', name:'carousel agents and pipeline', file:'scripts/carousel_script_agent_2026.py', tagline:'LinkedIn carousel scripts and PDFs.', does:['carousel_script_agent(_2026), carousel_content_writer, generate_carousel_pdf, run_pdf_carousel_pipeline, run_social_pipeline_2026, social_strategy_selector, linkedin_thread_agent, article_adapter.'], inputs:[], outputs:[] },
  { id:'ideas', group:'g_social', kind:'script', status:'satellite', name:'ideas_*.py (Ideas product)', file:'scripts/ideas_daily_agent.py', tagline:'A separate publishing product with its own agent, prompts, quality gates and renderer.', does:['ideas_daily_agent, ideas_generator_2026, ideas_prompts, ideas_quality, ideas_renderer → ideas/ and ideas.html.'], inputs:[], outputs:[] },
  { id:'buildings', group:'g_social', kind:'script', status:'satellite', name:'generate_building.py, find_buildings.py', file:'scripts/generate_building.py', tagline:'Building biography pages.', does:['Finds qualifying NYC buildings and writes a biography page for each (buildings.html).'], inputs:[], outputs:[] },
  { id:'li_scrape', group:'g_social', kind:'script', status:'satellite', name:'linkedin_engagement_scraper.py, linkedin_auth.py', file:'scripts/linkedin_engagement_scraper.py', tagline:'LinkedIn token setup and engagement collection.', does:['Writes engagement-derived weights into audience-signals.json, which the live pipeline does not read.'], inputs:[], outputs:['audience-signals.json'], flags:['F13'], touches:['st_signals'] },
  { id:'maint', group:'g_social', kind:'script', status:'satellite', name:'backfills and audits', file:'scripts/archive_audit.py', tagline:'One-off maintenance scripts.', does:['archive_audit, backfill_article_cta, backfill_og_image, backfill_social_images, rebuild_articles, cleanup_article_images, content_maintenance, patch_nav_services, competitor_monitor, client_signal_digest, pipeline_audit.'], inputs:[], outputs:[] },

  /* ===== VOICE ENGINE ===== */
  { id:'v_guide', group:'g_voice', kind:'public', status:'prototype', name:'WRITING_GUIDE.md', file:'docs/voice/WRITING_GUIDE.md', tagline:'Thirty books distilled, how the trade press writes, the WSJ/FT standard, and the Ben Rohr character brief.',
    does:['14 laws for writing that gets read online; 8 story shapes; 10 lenses; 10 hook formulas; 10 headline formulas; 6 kicker types.',`Measured prose stats for Commercial Observer, Bisnow, Multi-Housing News, Connect CRE and others; The Real Deal, GlobeSt and Crain's block automated fetching, so those are general knowledge and marked so.`,'The Two-Layer Rule and the LinkedIn playbook.'], inputs:[], outputs:[] },
  { id:'v_prompts', group:'g_voice', kind:'config', status:'prototype', name:'system.txt, brief.txt, article.txt', file:'docs/voice/prompts/system.txt', tagline:'The prompts, as plain text files so they can be read and edited without code.',
    does:['system.txt: the Ben Rohr voice bible, the reader, hook and voice rules, significance and emotional-depth rules, WSJ/FT standards, the accuracy contract, the Two-Layer Rule with a worked example.','brief.txt: step 1, find the story (protagonist, tension, lens, shape, four hooks, four headlines, significance, kicker idea).','article.txt: step 2, write it as paragraph roles and typed sentences.'], inputs:['sources JSON','brief'], outputs:['brief JSON','article JSON'], levers:['Edit the text files directly; bump VOICE_PROMPT_VERSION in ben_voice.py.'] },
  { id:'v_module', group:'g_voice', kind:'script', status:'prototype', name:'ben_voice.py', file:'scripts/ben_voice.py', tagline:'Loads the prompts, defines the story shapes and lenses, and fills the templates.',
    does:['Eight story shapes with when-to-use and beats; ten lenses.','Loads the two banks and tells the writer plainly when a bank is empty.'], inputs:['prompt files','banks'], outputs:['filled prompts'] },
  { id:'v_gate', group:'g_voice', kind:'script', status:'prototype', name:'voice_gate.py', file:'scripts/voice_gate.py', tagline:'Verifies facts with claim_verifier, then polices the opinion layer.',
    does:['Sentence kinds: fact, take, voice, context, ben.','A take must be first person or framed as opinion, cite surviving facts in "because", add no number or name, avoid loaded labels (distressed, bargain, lower basis), attribute no decisions or inner states to a party, avoid sweeping market claims, and claim no experience without a note.','Voice lines carry no numbers or names; context and note lines must derive from their bank entry.','An independent model rubric then rules on every take and voice line; fail-closed.'], inputs:['draft JSON','source text'], outputs:['VoiceDraft (kept sentences by paragraph role)'], numbers:[['take limit','38 words'],['voice limit','26 words']], levers:['The _LOADED, _MENTAL and _SWEEPING patterns, and the rubric prompt.'], flags:['F9'] },
  { id:'v_banks', group:'g_voice', kind:'config', status:'prototype', name:'context-bank.json, ben-notes.json', file:'docs/voice/context-bank.json', tagline:`The only places depth may come from: verified context and Ben's real experiences. Both start empty.`,
    does:['Context Bank: short human-verified claims with a source link; the writer may cite an id and say nothing beyond the entry.',`Ben's Notes: real moments from Ben's career; first-person experience is only allowed with one.`], inputs:['written by hand'], outputs:['allowed context and experience'] },
  { id:'v_proto', group:'g_voice', kind:'script', status:'prototype', name:'prototype.py + SAMPLES.md', file:'outputs/voice/prototype.py', tagline:'Runs brief, draft and gate on real cached stories and writes samples.',
    does:['Four runs so far; each changed the prompts or the gate (see SAMPLES.md).','100 to 290 seconds per story with two attempts: too slow to run on all 70 without tiering.'], inputs:['retrieval cache','DeepSeek key'], outputs:['samples.json, samples.md'] },
  { id:'v_editor', group:'g_voice', kind:'script', status:'prototype', name:'Editor pass + LinkedIn derivative (planned)', tagline:'Score each piece on ten criteria, rewrite once if under 3.5, then build the post and first comment only from kept sentences.',
    does:['Not built yet. Plan items 7.4 and 7.5.'], inputs:['kept sentences'], outputs:['scored piece','LinkedIn post'] },

  /* ===== LEGACY ===== */
  { id:'lg_v2', group:'g_legacy', kind:'script', status:'legacy', name:'daily_news_agent.py (v2 flow)', file:'scripts/daily_news_agent.py', tagline:'The original end-to-end agent.', does:['RSS + NewsAPI discovery, scoring, writing, publishing, LinkedIn. Runs when the workflow is dispatched with pipeline=v2.'], inputs:[], outputs:[], flags:['F1'] },
  { id:'lg_p2', group:'g_legacy', kind:'script', status:'legacy', name:'pipeline_v2.py, v2_editorial.py', file:'scripts/pipeline_v2.py', tagline:'The multi-sector v2 selection and its publishing bridge.', does:['Uses ranking.py and scoring_engine.py rather than selection.py and importance.py.'], inputs:[], outputs:[] },
  { id:'lg_rank', group:'g_legacy', kind:'script', status:'legacy', name:'ranking.py, scoring_engine.py', file:'scripts/ranking.py', tagline:'v2 within-sector ranking and 100-point scorer.', does:['ranking.py is the only reader of config/thresholds.json: articles_per_sector, tier boundaries, diversity controls.'], inputs:[], outputs:[], flags:['F2'] },
  { id:'lg_story', group:'g_legacy', kind:'script', status:'legacy', name:'story_normalizer, bucketed_editorial, editorial_scoring, editorial_intelligence, editorial_room, editorial_store, editorial_scorer', file:'scripts/story_normalizer.py', tagline:'v2 editorial layers.', does:['Normalisation, volume routing, daily top-news scoring, deterministic editorial intelligence, planning controls and an old 14-dimension review rubric.'], inputs:[], outputs:[] },
  { id:'lg_epipe', group:'g_legacy', kind:'script', status:'legacy', name:'editorial_pipeline.py + v3_generation.write_one', file:'scripts/editorial_pipeline.py', tagline:'The 7-stage v3 article writer (rollback via pipeline=v3).', does:['Seven model stages per article, about five minutes each; the reason v4 was written as a single bounded request.'], inputs:[], outputs:[] },
  { id:'lg_prompts', group:'g_legacy', kind:'script', status:'legacy', name:'enhanced_prompts, sector_prompts, generation, UPDATED_PROMPTS_2026, research_dossier, analytical_brief', file:'scripts/enhanced_prompts.py', tagline:'Prompts and pre-writing reasoning used by the v2 and v3 writers.', does:['None are used by the v4 writer.'], inputs:[], outputs:[] },
  { id:'lg_sources', group:'g_legacy', kind:'script', status:'legacy', name:'news_sources.py', file:'scripts/news_sources.py', tagline:'88 hard-coded feeds, superseded by config/sources.json.', does:['Still imported by several legacy modules.'], inputs:[], outputs:[] },
  { id:'lg_ckpt', group:'g_legacy', kind:'script', status:'legacy', name:'checkpoint.py, cost_tracker.py, article_variants.py', file:'scripts/checkpoint.py', tagline:'Per-phase checkpointing, cost counter, A/B variants for the v2 flow.', does:['Imported by daily_news_agent.py only.'], inputs:[], outputs:[] },
  { id:'lg_thresholds', group:'g_legacy', kind:'config', status:'legacy', name:'thresholds.json', file:'config/thresholds.json', tagline:'Declares 30/sector, tier boundaries, diversity caps, a $25 daily cap, timeouts.', does:['Only ranking.py (v2) and budget.py read it. The live selection constants are hard-coded in selection.py.'], inputs:[], outputs:[], flags:['F2'] }
],

/* ----------------------------------------------------------------- EDGES */
edges: [
  { from:'g_trigger', to:'s1', kind:'ctl', label:'07:07 ET: run insights_v3 --pipeline v4' },
  { from:'g_external', to:'s1', kind:'data', label:'feeds' },
  { from:'s1', to:'s2', kind:'main', label:'documents' },
  { from:'s2', to:'s3', kind:'main', label:'classified documents' },
  { from:'s3', to:'s4', kind:'main', label:'events (IntelligenceObjects)' },
  { from:'s4', to:'s5', kind:'main', label:'+ eligibility' },
  { from:'s5', to:'s6', kind:'main', label:'+ novelty' },
  { from:'s6', to:'s7', kind:'main', label:'+ full text, evidence level' },
  { from:'s7', to:'s8', kind:'main', label:'+ scores' },
  { from:'s8', to:'s9', kind:'main', label:'slate ≤70 with depth' },
  { from:'s9', to:'s10', kind:'main', label:'verified articles' },
  { from:'s10', to:'s11', kind:'main', label:'declared files' },
  { from:'s11', to:'g_public', kind:'main', label:'git push → Netlify' },
  { from:'g_public', to:'g_readers', kind:'data', label:'page views' },
  { from:'g_readers', to:'st_signals', kind:'fb', label:'feedback (open loop)' },
  { from:'s6', to:'st_cache', kind:'data', label:'pages cached' },
  { from:'s5', to:'st_memory', kind:'data', label:'novelty' },
  { from:'s9', to:'g_gate', kind:'ctl', label:'per story' },
  { from:'g_gate', to:'s10', kind:'data', label:'verified' },
  { from:'g_wrap', to:'g_public', kind:'main', label:'reads insights.json → publishes weekly-wrap page' },
  /* gate internals */
  { from:'gt1', to:'gt2', kind:'main', label:'' },{ from:'gt2', to:'gt3', kind:'main', label:'' },{ from:'gt3', to:'gt4', kind:'main', label:'' },
  { from:'gt4', to:'gt5', kind:'main', label:'' },{ from:'gt5', to:'gt6', kind:'main', label:'' },{ from:'gt6', to:'gt7', kind:'main', label:'' },
  { from:'gt7', to:'gt8', kind:'ctl', label:'if rejected / thin' },{ from:'gt7', to:'gt9', kind:'main', label:'' },
  /* wrap internals */
  { from:'w1', to:'w2', kind:'main', label:'' },{ from:'w2', to:'w3', kind:'main', label:'' },{ from:'w3', to:'w4', kind:'main', label:'' },
  { from:'w4', to:'w5', kind:'main', label:'' },{ from:'w5', to:'w6', kind:'main', label:'' },{ from:'w6', to:'w7', kind:'main', label:'' },{ from:'w7', to:'w8', kind:'main', label:'' },
  { from:'wf_wrap', to:'w1', kind:'ctl', label:'Fri 16:30 ET' },
  { from:'wf_daily', to:'resolve_policy', kind:'ctl', label:'' },
  { from:'g_voice', to:'s9', kind:'leg', label:'replaces the writer prompt behind a flag' },
  { from:'v_prompts', to:'v_module', kind:'main', label:'' },{ from:'v_module', to:'v_gate', kind:'main', label:'' }
],

/* ----------------------------------------------------------------- TOUR */
steps: [
  { title:'The whole picture', focus:['g_intro','g_numbers'], text:'Eleven stages left to right turn ~700 raw documents into up to 70 verified articles. Everything above the stages starts it; everything below remembers, explains, or branches off it.' },
  { title:'0 · Trigger and control', focus:['g_trigger','g_external'], text:'A GitHub Action fires at 07:07 New York time. A tiny policy script decides run vs skip (two crons cover daylight saving). A lease file makes GitHub the only publisher so the old Windows task cannot double-post.' },
  { title:'1 · Ingest', focus:['s1'], edges:['s1-s2'], text:'~148 RSS feeds and up to 12 index pages are read in parallel with strict timeouts. Entries from the last 36 hours become CanonicalItems. Broken feeds trip a circuit breaker instead of stalling the run.' },
  { title:'2 · Classify', focus:['s2'], edges:['s2-s3'], text:'Source priors, keyword signal density and watchlists assign each document one of 7 sectors. Nothing is rejected: this stage only labels.' },
  { title:'3 · Cluster into events', focus:['s3'], edges:['s3-s4'], text:'Documents about the same event (shared dollar amount, entities, headline words) merge at similarity 0.62 into one IntelligenceObject, so the unit that gets ranked is the event, not the URL.' },
  { title:'4 · Type and gate', focus:['s4'], edges:['s4-s5'], text:'First decide what the document IS (news, explainer, interview, marketing...), then apply rules for its event family. This pass sees only the RSS summary, so it is cheap and sometimes wrong, which is why stage 6 revisits it.' },
  { title:'5 · Check memory', focus:['s5','st_memory'], edges:['s5-s6'], text:'Each event is compared with 45 days of coverage. New, follow-up or already published? Repeats are penalised later in scoring; already-published events are not read or written again.' },
  { title:'6 · Read the articles', focus:['s6','st_cache'], edges:['s6-s7'], text:'Up to 250 candidates are fetched lawfully (robots.txt obeyed). Full text upgrades evidence from "summary only" toward "corroborated", and borderline rejects are re-judged on the real article body.' },
  { title:'7 · Score importance', focus:['s7'], edges:['s7-s8'], text:'Eight measures (size, market impact, parties, precedent, novelty, richness, evidence, right-to-win) become a 0–100 score with a written reason for each. Penalties for repeats and weak formats come off the top.' },
  { title:'8 · Select the slate', focus:['s8'], edges:['s8-s9'], text:'Top 10 per sector above 40, at most 3 per publisher and company, then the best 70 overall. Each gets a depth (flagship, analysis or brief) that its evidence can honestly support.' },
  { title:'9 · Write and fact-check', focus:['s9','g_gate'], edges:['s9-s10'], text:'The model writes sentences with verbatim quotes. Code checks every quote and detail; two reasoning passes judge every claim; whatever fails is deleted. Too little left means the story is withheld. Zoom into the box below to see each gate.' },
  { title:'10 · Publish', focus:['s10'], edges:['s10-s11'], text:'Pages, social cards, manifest, feed and sitemap are written, an edition record and a publication decision are produced, and an explicit allow-list of files is declared.' },
  { title:'11 · Release and verify', focus:['s11','g_public'], edges:['s11-g_public'], text:'Only declared files are committed, rebased and pushed. Netlify deploys; a verifier polls the live site; a failure rolls back. The verified stories go straight to main unless more than 20% of the day failed or was skipped; then the whole day goes to a review PR.' },
  { title:'The Friday weekly wrap', focus:['g_wrap'], text:'A second, smaller pipeline summarises what the daily pipeline already published, by sector, and fact-checks every line with the same gate. It publishes through the same release path.' },
  { title:'Monitoring and satellites', focus:['g_monitor','g_social'], text:'CI, feed probes and weekly reports watch the system. LinkedIn, PDFs, carousels, Ideas and buildings are separate code that is not in the daily workflow.' },
  { title:'The voice engine (next)', focus:['g_voice'], text:`The planned evolution of stage 9: first decide what the story is about (angle, shape, lens, hooks), then draft it in Ben Rohr's voice as typed sentences, then prove the facts and police the opinion. Prototyped and tested on real stories; not in production.` },
  { title:'Legacy: what you can ignore', focus:['g_legacy'], text:'The v2 and v3 pipelines remain for rollback. Most of the repo\'s line count is here. Only four functions of daily_news_agent.py are still on the live path.' },
  { title:'Your critique list', focus:[], flags:true, text:'Open the Flags panel: nineteen verified issues, ranked, each linked to the box it concerns.' }
],

/* ----------------------------------------------------------------- FLAGS */
flags: [
  { id:'F5', fixed:'2026-10-09: every writer and fact-check call asks the budget first and records real token spend; the run reports it; a reached cap skips stories.', sev:'high', title:'The spending cap is not enforced on the v4 writer', nodes:['budget','v4_generation','st_spend'],
    detail:'config/thresholds.json declares a $25 daily cap and budget.py implements it, but v4 write_all() accepts a budget argument and never uses it. The ledger is not incremented, so spend reports read $0. The 70-story run can issue several hundred reasoning-mode calls per day with no ceiling.', fix:'Ask budget.allow() before each model call in write_one and the verifier, and record spend.' },
  { id:'F1', fixed:'2026-10-09, branch codex/phase-0-accurate-writer: render_html and the index writers moved to site_renderer.py; publishing no longer loads daily_news_agent (byte-identical pages).', sev:'high', title:'A 2,872-line legacy monolith sits on the publish path', nodes:['daily_news_agent','v3_publish'],
    detail:'v3_publish imports daily_news_agent for four functions. Importing it loads 18 modules at import time (legacy scoring, LinkedIn essay agent, editorial room...). Any edit or error there can stop publishing: your working copy currently fails to compile.', fix:'Move render_html, update_manifest, update_feed_xml, update_sitemap_xml into a small renderer module.' },
  { id:'F6', fixed:"2026-10-09, by Ben's decision (DeepSeek only): no second family is used. Independence comes from two differently framed reasoning passes at temperature 0 plus the deterministic checks.", sev:'high', title:'The second fact-checker is the same model family as the writer', nodes:['claim_verifier','x_openai','model_router','gt4','w6'],
    detail:'OpenAI is the preferred independent checker but the account returns insufficient_quota, so DeepSeek writes and checks. Code checks do not depend on a model, but the two model passes can share blind spots.', fix:'Add OpenAI credit or another provider; the verifier already prefers a different provider.' },
  { id:'F12', sev:'high', title:'The existing archive was never verified', nodes:['pub_pages','w4','w6'],
    detail:'In the 2026-10-08 audit, 23.6% of sentences from the old writer were unsupported (14 of 16 articles). About 1,450 live pages predate the gate, and the weekly wrap\'s fallback excerpts inherit their errors.', fix:'Run the audit across the archive; correct or unpublish the worst pages.' },
  { id:'F11', fixed:"2026-10-09: patient retries for rate limits, server errors and dropped connections; a shared health check stops new stories cleanly if DeepSeek is down. No second provider, by Ben's decision.", sev:'med', title:'The writer has no provider fallback', nodes:['v4_generation','model_router'],
    detail:'v4 deliberately makes one request per attempt with no provider chain. If DeepSeek is down, stories fail, and (with no OpenAI credit) there is nothing to fall back to anyway.', fix:'Decide whether a bounded fallback to a second provider is acceptable for writing.' },
  { id:'F16', fixed:'2026-10-09: the verified stories publish unless more than 20% of the day failed or was skipped; reasons and notes go into publication-decision.json.', sev:'med', title:'One skipped or failed story blocks the whole day', nodes:['st_decision','wf_daily','review_pr','edition_manager'],
    detail:'auto_publish_allowed requires zero failed and zero skipped stories. A single skipped story (for example when the generation window closes) routes all 70 to a review PR and the "fail visibly" step exits 1. Withheld stories are excluded, deliberately.', fix:'Consider publishing the completed subset and reporting the rest.' },
  { id:'F2', sev:'med', title:'thresholds.json does not control the live pipeline', nodes:['lg_thresholds','selection','lg_rank'],
    detail:'Per-sector targets, tier boundaries and diversity caps in config/thresholds.json are read only by legacy ranking.py. Live selection uses constants hard-coded in selection.py (floor 40, 10 per sector, 3 per source, 3 per company, tier cutoffs 70 and 50).', fix:'Make selection.py read the config, or delete the misleading keys.' },
  { id:'F3', sev:'med', title:'The Sunday assignment desk feeds nothing live', nodes:['wf_desk','st_queue'],
    detail:'assignment-queue.json and structured-candidates.json are consumed only by daily_news_agent.py\'s legacy discovery. A weekly workflow commits files that no live stage reads.', fix:'Wire the queue into selection, or retire the workflow.' },
  { id:'F4', sev:'med', title:'latest-edition.json is written daily but displayed nowhere', nodes:['pub_edition','edition_manager','verify_deployment'],
    detail:'edition.js can render it, but no page includes edition.js or edition.css (searched every page). The record is used only by verify_deployment. Under v4 the flagship, culture signal and deal tape fields are mostly empty.', fix:'Either render it on the homepage or simplify the edition record.' },
  { id:'F9', fixed:"2026-10-09: the voice engine (Ben's persona, merged with Codex's July voice work) writes flagships and analyses when INSIGHTS_VOICE is on; on for previews, off for production until Ben switches it.", sev:'med', title:'The voice persona does not shape the daily articles', nodes:['voice','v4_generation'],
    detail:'editorial_voice.py (556 lines of persona, voice modes, headline shapes) is used by the LinkedIn, carousel and Ideas agents. The v4 writer has its own prompt and readability.py, so voice and headline conventions can diverge between the site and LinkedIn.', fix:'Decide the single house style and apply it in one place.' },
  { id:'F13', sev:'med', title:'The audience feedback loop is open', nodes:['fn_feedback','st_signals','li_scrape'],
    detail:'Reader feedback writes audience-signals-live.json inside the Netlify function (probably not the repo, suspected), and the live pipeline does not read audience signals anyway. Only legacy v2 code and the weekly retrospective do.', fix:'Persist signals durably and feed them into importance.py or selection.py.' },
  { id:'F7', sev:'low', title:'Seven "active" NewsAPI sources are skipped', nodes:['cfg_sources','ingestion','wf_daily'],
    detail:'ingestion.py returns immediately for any source whose URL is newsapi.org. The workflow still passes NEWSAPI_KEY, and the source list reports 171 active sources of which only about 148 are real feeds.', fix:'Deactivate them in sources.json or implement the fetch.' },
  { id:'F8', sev:'low', title:'Index-page sources are tried as RSS and only 12 of 16 are read', nodes:['ingestion','html_listing','cfg_sources'],
    detail:'load_sources() applies no source-type filter, so html_listing sources are also fetched as feeds (suspected to fail quietly). The listing reader is capped at 12 by default, so 4 active index pages are never read.', fix:'Filter by type in ingestion; raise --listing-limit.' },
  { id:'F10', sev:'low', title:'DEPTH_SPEC exists twice; the old writer is imported for three symbols', nodes:['v3_generation','v4_generation'],
    detail:'v3_generation.DEPTH_SPEC (word ranges 180–1400) is stale; v4 defines its own. v4 still imports DraftResult, object_to_dossier and the old spec from v3_generation, which pulls the v3 writer into the import graph.', fix:'Move the shared types into their own module.' },
  { id:'F14', fixed:'2026-10-09: new manifest entries carry their sector and the page filters on it; older entries fall back to category.', sev:'high', title:'Four filter buttons on the Intelligence page match nothing', nodes:['pub_listing','pub_manifest','v3_publish'],
    detail:'v3_publish maps each sector to a reader category (energy → "Market Commentary", banking → "Debt & Equity", Fed → "Market Analysis", government → "Policy & Regulation"). insights.html filters Energy, Banking, Fed & Macro and Government by different names ("Energy", "Banking", "Federal Reserve", "Local Government"). Of 535 articles since Sep 1 these four buttons match 0; only Private Equity (23) and Data Centers (58) work, and everything else is lumped under "CRE". insights.json also has no sector field, so the page cannot filter by sector at all.', fix:'Store sector in each manifest entry and filter on it.' },
  { id:'F17', fixed:'2026-10-09: release notices, schedule changes, website notices and errata are typed as administrative notices (never eligible).', sev:'med', title:'An administrative notice passed eligibility', nodes:['content_typing','eligibility'],
    detail:'In the first live preview (2026-10-09) "Notice to Users of the H.8 Release" was selected for writing. Administrative notices are meant to be never-eligible; the content typer did not recognise it. The fact gate withheld it, so nothing wrong was published, but a slot was spent.', fix:'Add Federal Reserve release-notice patterns to content_typing and a test.' },
  { id:'F18', fixed:'2026-10-09: precedent now reads policy actions and disclosed terms; degeneracy is judged over the eligible pool. On the saved Aug 7 candidates no measure is degenerate.', sev:'med', title:'Two scoring measures do not vary on live data', nodes:['importance'],
    detail:'The live preview reported precedent and novelty as degenerate (no discriminating power). The top score was 64.4, so no story reached tier_a (flagship).', fix:'Inspect the two measures against a week of candidates; recalibrate or retire them.' },
  { id:'F19', fixed:'2026-10-09: source health and the retrieval cache follow --state-dir.', sev:'low', title:'Previews still write some state into the repo', nodes:['retrieval','source_health'],
    detail:'insights_v3.py --state-dir redirects run artifacts, memory, spend and provider logs, but source-health.json and the retrieval cache are written to the repo .editorial-state regardless.', fix:'Route both through the state directory.' },
  { id:'F15', sev:'low', title:'Local Windows scheduler remnants', nodes:['agent_runtime'],
    detail:'agent_runtime.py, the .bat wrappers and setup_scheduler.ps1 remain, though the lease makes them exit. A stale task on a PC is a quiet risk if the lease file is ever changed.', fix:'Delete once the cloud scheduler is trusted.' }
]
};
