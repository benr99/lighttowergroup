# Light Tower Group Remediation Implementation Plan

Purpose: instruct an AI coding agent to address the audit findings one by one, stopping once the current website, content pipeline, security posture, analytics readiness, and lead-capture foundation are stable. Do not build new speculative agents or new growth ideas in this phase.

Source audit: `COMPREHENSIVE_REPO_AUDIT_REPORT.md`

## Operating Principles

- Work in priority order.
- Keep changes narrowly scoped.
- Preserve existing site design and brand direction unless fixing a clear bug.
- Do not remove user-created content unless it is sensitive, unsafe, obsolete operational output, or explicitly redirected from public access.
- Do not introduce a new framework or build system.
- Do not build new agents in this phase.
- Do not add CRM, newsletter, new landing pages, new programmatic SEO systems, or new outreach systems yet.
- Focus on making the existing system safe, measurable, consistent, and ready for future growth.

## Definition of Done

This phase is complete when:

- No sensitive operational logs or API-key-bearing URLs are tracked.
- Internal/admin/targeting assets are not publicly exposed.
- Public pages preserve or improve current functionality.
- All insight pages have a consistent conversion path.
- Core analytics hooks are present and ready for a real measurement ID.
- Lead capture has a clearer, more reliable notification path.
- Generated content templates have basic schema, encoding, and QA protections.
- The daily content pipeline is less fragile and does not leak secrets.
- Validation checks pass for JSON, XML, Python syntax, Netlify function syntax, and key public page references.

Stop at that point. Do not proceed into new-agent or growth-feature implementation unless separately instructed.

---

## Phase 0: Preflight and Safety

### Tasks

1. Check working tree state.
2. Identify tracked files that are operational, internal, or sensitive.
3. Confirm the current repo root and branch.
4. Avoid reverting unrelated user changes.

### Suggested commands

```powershell
git status --short
git branch --show-current
git ls-files scripts/.env scripts/agent_log.json scripts/agent_run.log linkedin_essay_queue.json insights-admin.html origination.html data/targets.json agent memory
```

### Acceptance Criteria

- Agent knows what is tracked.
- Agent has not modified anything yet.
- Agent records any unexpected dirty files before editing.

---

## Phase 1: Remove Sensitive Logs and Prevent Future Secret Leakage

### Problem

`scripts/agent_run.log` is tracked and contains historical NewsAPI request URLs with the API key in query parameters. This is the highest-priority issue.

### Tasks

1. Add operational outputs to `.gitignore`.
2. Stop tracking `scripts/agent_run.log`.
3. Ensure future logging redacts API keys and request query strings.
4. Review scripts for places where full URLs with query parameters may be printed.
5. Add a short note to documentation that API keys must be rotated if logs were ever pushed.

### Files Likely Involved

- `.gitignore`
- `scripts/daily_news_agent.py`
- `DEPLOYMENT.md` or a new short security note
- Possibly `QUICKSTART.md`

### Implementation Guidance

Add ignore entries such as:

```gitignore
scripts/agent_run.log
scripts/agent_log.json
scripts/.env
scripts/__pycache__/
*.pyc
```

Consider whether to ignore:

```gitignore
linkedin_essay_queue.json
test_social_image.png
scripts/test_social_image.png
```

Only ignore generated/public files if doing so will not break deployment. If `linkedin_essay_queue.json` is required by the deployed Netlify function, do not remove it from tracking in this phase unless you also adjust the function storage approach. Safer first step: keep the redirect protection and document that it should later move outside public root.

For `daily_news_agent.py`, make sure logging never prints:

- Full NewsAPI URLs containing `apiKey=`.
- Authorization headers.
- Access tokens.
- Raw environment variables.

Use a helper such as:

```python
def redact_url(url: str) -> str:
    return re.sub(r"([?&](?:apiKey|key|token|access_token)=)[^&\\s]+", r"\\1[REDACTED]", url)
```

Apply it to any warning/error output that may include request URLs.

### Git Tracking

Use:

```powershell
git rm --cached scripts/agent_run.log
```

Do not delete the local file unless explicitly approved. Removing from tracking is enough for this phase.

### Acceptance Criteria

- `git ls-files scripts/agent_run.log` returns nothing.
- `.gitignore` includes `scripts/agent_run.log`.
- Searches do not find exposed full API keys in tracked files:

```powershell
git grep -n "apiKey="
git grep -n "sk-"
git grep -n "ACCESS_TOKEN"
```

- Documentation includes a clear note: rotate NewsAPI key if the log was ever pushed or shared.

---

## Phase 2: Block Internal and Origination Assets From Public Exposure

### Problem

Internal tools and target data exist in the repo:

- `insights-admin.html`
- `origination.html`
- `data/targets.json`
- `agent/`
- `memory/`
- `linkedin_essay_queue.json`

Some are redirected, but coverage is incomplete.

### Tasks

1. Add Netlify redirects/blocks for internal paths.
2. Keep existing redirect for `/linkedin_essay_queue.json`.
3. Keep existing redirect for `/origination.html`.
4. Add redirects or 404 blocks for:
   - `/insights-admin.html`
   - `/data/*`
   - `/agent/*`
   - `/memory/*`
   - `/scripts/*` if scripts are ever deployed
5. Confirm sitemap does not include internal pages.
6. Confirm robots alone is not relied on for protection.

### Files Likely Involved

- `netlify.toml`
- Possibly `robots.txt`, but do not rely on robots for security.

### Implementation Guidance

Prefer forced 404s:

```toml
[[redirects]]
  from = "/insights-admin.html"
  to = "/"
  status = 404
  force = true

[[redirects]]
  from = "/data/*"
  to = "/"
  status = 404
  force = true
```

Repeat for internal directories.

### Acceptance Criteria

- `netlify.toml` blocks all internal paths listed above.
- `sitemap.xml` does not contain internal pages.
- Public functionality remains unaffected.
- `origination.html` remains inaccessible in production unless explicitly enabled later behind real auth.

---

## Phase 3: Remove Client-Side Admin Password Risk

### Problem

`insights-admin.html` contains:

```js
const ADMIN_PASSWORD = 'ltg2026';
```

This is not real authentication.

### Tasks

1. Remove the hardcoded password.
2. Either:
   - Disable the page entirely with a clear internal-only message, or
   - Keep the file but make it nonfunctional unless served behind real auth later.
3. Ensure Netlify blocks the page from production as part of Phase 2.

### Files Likely Involved

- `insights-admin.html`
- `netlify.toml`

### Recommended Conservative Implementation

Do not build auth in this phase. Replace the client-side password flow with a static notice:

"This internal tool is disabled in production. Use the local content pipeline or enable server-side authentication before reactivating."

Keep any useful composer code only if not exposed or callable. Better: leave the file blocked by Netlify and remove the visible password.

### Acceptance Criteria

- `git grep -n "ADMIN_PASSWORD"` returns no hardcoded password.
- `git grep -n "ltg2026"` returns no result.
- `insights-admin.html` cannot be used as a public pseudo-admin.
- Netlify blocks `/insights-admin.html`.

---

## Phase 4: Activate Analytics Readiness Without Hardcoding Placeholder Noise

### Problem

GA snippets are currently commented placeholders. Active Google tag count is zero. The site cannot be managed as a lead-generation system without measurement.

### Tasks

1. Add a lightweight analytics loader that only activates when a real measurement ID is configured.
2. Avoid committing fake IDs such as `G-XXXXXXXXXX`.
3. Add conversion event functions for:
   - chat open
   - mandate form start
   - mandate form submit
   - service CTA click
   - article CTA click
   - email click
   - phone click
4. Wire events into existing UI where straightforward.
5. Document where to add the real measurement ID.

### Files Likely Involved

- `site.js`
- `index.html`
- `chat-widget.js`
- service pages
- insight templates or generated pages if backfilling
- `DEPLOYMENT.md` or `MONITORING_CHECKLIST.md`

### Implementation Guidance

Create a global helper in `site.js`:

```js
window.ltgTrack = function(eventName, params) {
  if (typeof window.gtag === 'function') {
    window.gtag('event', eventName, params || {});
  }
};
```

Do not require GA to exist. Calls should be no-ops when analytics are not installed.

If adding GA directly, use a single source of truth:

```html
<script>
  window.LTG_GA_ID = '';
</script>
```

Then only inject Google Analytics if `window.LTG_GA_ID` starts with `G-`.

### Acceptance Criteria

- No active placeholder `G-XXXXXXXXXX` remains.
- Tracking calls do not throw when GA is absent.
- Form submit and chat open can emit events if GA is configured.
- Documentation explains how to set the real measurement ID.

---

## Phase 5: Strengthen Lead Capture and Notification Reliability

### Problem

Lead capture is split:

- Homepage mandate form posts to Formspree.
- Chat sends transcript to `deal-notify.js` only when assistant text matches closing phrases.

The phrase-match trigger is fragile.

### Tasks

1. Keep the current Formspree flow unless replacing it with an existing Netlify function can be done safely.
2. Improve chat lead notification trigger.
3. Add structured lead extraction signals in the browser before sending to `deal-notify`.
4. Make `deal-notify.js` accept an explicit `source` and optional `leadFields`.
5. Ensure `deal-notify.js` never fails the chat UX.
6. Add basic anti-spam honeypot or timing guard if simple.

### Files Likely Involved

- `chat-widget.js`
- `netlify/functions/deal-notify.js`
- `netlify/functions/chat.js`
- `index.html`

### Implementation Guidance

Do not build a CRM yet.

Improve the trigger by tracking whether the conversation contains:

- Email-like string.
- Name-like response or company.
- Deal detail terms such as debt, equity, refinance, construction, bridge, acquisition, location, amount.

Then notify when enough criteria are met, not only when the model says "Ben will be in touch."

Add a one-time guard so the same chat session does not send repeated notifications.

Example criteria:

```js
const hasEmail = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}/i.test(transcriptText);
const hasDealSignal = /(debt|equity|loan|refi|refinance|bridge|construction|multifamily|office|retail|industrial|hotel|development|acquisition|recap)/i.test(transcriptText);
const hasSizeSignal = /\\$\\s?\\d|\\d+\\s?(m|million|mm)/i.test(transcriptText);
```

Only send once when email plus either deal signal or closing phrase is present.

### Acceptance Criteria

- Chat notification no longer depends solely on assistant phrase matching.
- `deal-notify.js` accepts and displays structured source metadata.
- Existing chat behavior still works.
- Formspree form still works or has an explicitly tested replacement.
- No CRM/new external system is introduced in this phase.

---

## Phase 6: Backfill Consistent Conversion Paths on Insight Pages

### Problem

Only 57 of 331 insight pages include `chat-widget.js`. Most content pages therefore lack the strongest on-page conversion path.

### Tasks

1. Add `site.js` and `chat-widget.js` consistently to insight pages.
2. Add or verify "Initiate Mandate" CTA on article pages.
3. Add a simple article footer CTA where absent.
4. Avoid changing article body content unnecessarily.
5. Make sure older building pages and newer news pages both work.

### Files Likely Involved

- `scripts/daily_news_agent.py` article template.
- `scripts/generate_building.py` article template.
- Existing `insights/*.html` files.
- Possibly a one-off backfill script.

### Implementation Guidance

Prefer updating generation templates first, then backfill existing pages.

For backfill, create or use a small script only if necessary. The script should:

- Open each `insights/*.html`.
- Check whether `/chat-widget.js` is already present.
- Insert `<script src="/site.js" defer></script>` if absent and appropriate.
- Insert `<script src="/chat-widget.js"></script>` before `</body>`.
- Add a CTA block only if the template lacks one and insertion point is reliable.

Do not manually edit 331 files one by one.

### Acceptance Criteria

- All 331 insight HTML files include `chat-widget.js`.
- No duplicate `chat-widget.js` script tags.
- Article pages still include valid canonical and OG metadata.
- Existing share functionality still works.

Verification:

```powershell
$files = Get-ChildItem insights -File -Filter *.html
($files | Where-Object { -not (Select-String -Path $_.FullName -Pattern 'chat-widget.js' -Quiet) }).Count
```

Expected: `0`

---

## Phase 7: Normalize Article Schema and Metadata

### Problem

Older building pages have richer schema. Newer daily news articles often lack JSON-LD. Metadata consistency matters for SEO, entity trust, and rich-result eligibility.

### Tasks

1. Update daily news article template to include Article or NewsArticle JSON-LD.
2. Include:
   - headline
   - description
   - datePublished
   - dateModified
   - author
   - publisher
   - image
   - mainEntityOfPage
   - articleSection
3. Ensure all generated articles include `meta name="robots" content="index, follow"`.
4. Ensure social image URLs point to existing files.
5. Backfill schema into newer news pages if feasible.

### Files Likely Involved

- `scripts/daily_news_agent.py`
- Existing `insights/*.html`

### Acceptance Criteria

- New daily article template emits JSON-LD.
- JSON-LD is valid JSON.
- At least all non-building daily news pages have schema after backfill, or the remaining gap is documented.
- No broken quote escaping in JSON-LD.

Verification:

```powershell
$files = Get-ChildItem insights -File -Filter *.html
($files | Where-Object { -not (Select-String -Path $_.FullName -Pattern 'application/ld\+json' -Quiet) }).Count
```

Target: reduce materially; ideally `0`, unless specific pages are intentionally excluded.

---

## Phase 8: Add Encoding and Content QA Guards

### Problem

Some generated outputs contain mojibake such as `’`, `Ã `, or replacement characters. This damages polish and trust.

### Tasks

1. Add a prepublish check for mojibake patterns.
2. Check generated article JSON before writing files.
3. Check `insights.json` before saving.
4. Fail or warn loudly on suspicious encoding artifacts.
5. Add a repair helper only for obvious mappings if safe.

### Files Likely Involved

- `scripts/daily_news_agent.py`
- `scripts/linkedin_essay_agent.py`
- Possibly a new small utility script under `scripts/`

### Implementation Guidance

Patterns to detect:

```text
â
Ã
�
```

The agent should not blindly replace every instance in all files unless the mapping is obvious. Prefer:

- Detect and block new publishing.
- Repair known current artifacts in manifest/queue if clear.

### Acceptance Criteria

- Daily pipeline checks for mojibake before publish.
- Current `insights.json` obvious mojibake is repaired if safe.
- `linkedin_essay_queue.json` obvious mojibake is repaired if safe and still valid JSON.
- JSON files still parse.

Verification:

```powershell
rg -n "â|Ã|�" insights.json linkedin_essay_queue.json insights scripts
```

Expected: no user-visible generated content hits, or documented intentional exceptions.

---

## Phase 9: Reduce Daily Agent Fragility

### Problem

Historical logs show:

- JSON decode crashes.
- Scoring failures falling back to raw order.
- Git push credential failures.
- LinkedIn 422 failures.
- External API/network failures.

### Tasks

1. Add structured-output repair/retry around article generation.
2. Avoid crashing the whole run on one article if multiple articles are generated.
3. Improve scoring fallback so it still sorts by deterministic heuristic if AI scoring fails.
4. Make git commit/push failure status explicit in the run log.
5. Keep LinkedIn in review-queue mode unless `--auto-post-linkedin` is explicitly used.
6. Ensure run data records partial failures clearly.

### Files Likely Involved

- `scripts/daily_news_agent.py`
- `scripts/linkedin_essay_agent.py`

### Implementation Guidance

Do not rewrite the whole agent.

Add conservative helper functions:

- `extract_json_object`
- `extract_json_array`
- `repair_common_json_issues` if safe
- `heuristic_story_score`
- `record_warning`

When a generated article fails JSON parsing:

1. Retry once with a "return valid JSON only" repair prompt if API access is part of normal run.
2. If still failing, skip that article and continue with the next candidate.
3. Log the failure without printing secrets.

### Acceptance Criteria

- One malformed AI response no longer kills the entire run.
- Run log records warnings without secrets.
- `--dry-run` remains safe.
- Python syntax check passes.

---

## Phase 10: Fix or Formalize LinkedIn Workflow

### Problem

Logged runs show repeated LinkedIn 422 errors and zero successful posts. The current state says automated posting exists, but evidence shows it has not worked.

### Tasks

1. Decide implementation mode for this phase:
   - Recommended: formalize review-queue mode and remove claims that auto-posting is live.
   - Optional: fix auto-posting only if credentials/API details are available and testable.
2. Update docs to match reality.
3. Ensure daily agent does not claim posted when queued.
4. Ensure LinkedIn queue review UI remains protected.

### Files Likely Involved

- `scripts/daily_news_agent.py`
- `DEPLOYMENT.md`
- `QUICKSTART.md`
- `MONITORING_CHECKLIST.md`
- `netlify/functions/linkedin-essay.js`
- `linkedin_essay_queue.json`

### Recommended Conservative Implementation

Use review queue as the official workflow:

- Generate LinkedIn essay packages.
- Queue them.
- Admin reviews/copies manually.
- Do not auto-post by default.
- Keep `--auto-post-linkedin` as an advanced/manual flag if desired.

### Acceptance Criteria

- Docs no longer claim automatic LinkedIn posting is live unless verified.
- Run logs clearly say "queued for review."
- No false success status for LinkedIn.
- LinkedIn review access remains token-protected.

---

## Phase 11: Clean Public Documentation and Placeholders

### Problem

Docs contain partial credential examples and statements that no longer match implementation. Some pages include placeholder integrations like GA and OneSignal.

### Tasks

1. Remove partial API key fragments from docs.
2. Replace with safe placeholders:

```text
DEEPSEEK_API_KEY=<set in scripts/.env or deployment environment>
NEWSAPI_KEY=<set in scripts/.env>
```

3. Update LinkedIn status to review queue unless auto-posting is verified.
4. Document analytics configuration.
5. Document internal file blocking.
6. Remove or clarify placeholder OneSignal comments if not in use.

### Files Likely Involved

- `DEPLOYMENT.md`
- `QUICKSTART.md`
- `MONITORING_CHECKLIST.md`
- `SOCIAL_IMAGES.md`
- Public HTML comments if appropriate

### Acceptance Criteria

- `git grep -n "sk-"` has no credential examples.
- Docs do not include partial real-looking tokens.
- Docs match actual workflow.
- Placeholders are clearly marked and do not imply live features.

---

## Phase 12: Final Validation Pass

### Required Checks

Run these checks before final report:

```powershell
git status --short

$ErrorActionPreference='Stop'
Get-Content insights.json -Raw | ConvertFrom-Json | Out-Null
[xml](Get-Content sitemap.xml -Raw) | Out-Null
[xml](Get-Content feed.xml -Raw) | Out-Null

$env:PYTHONDONTWRITEBYTECODE='1'
python -m py_compile scripts\daily_news_agent.py scripts\linkedin_essay_agent.py scripts\social_image_generator.py scripts\news_sources.py scripts\enhanced_prompts.py scripts\competitor_monitor.py scripts\find_buildings.py scripts\generate_building.py

node --check netlify\functions\chat.js
node --check netlify\functions\deal-notify.js
node --check netlify\functions\linkedin-essay.js

git grep -n "apiKey="
git grep -n "sk-"
git grep -n "ADMIN_PASSWORD"
git grep -n "ltg2026"

$files = Get-ChildItem insights -File -Filter *.html
"missing_chat=" + (($files | Where-Object { -not (Select-String -Path $_.FullName -Pattern 'chat-widget.js' -Quiet) }).Count)
"missing_social=" + ((Get-Content insights.json -Raw | ConvertFrom-Json | Where-Object { -not (Test-Path (Join-Path 'insights' ($_.slug + '_social.png'))) }).Count)
"missing_html=" + ((Get-Content insights.json -Raw | ConvertFrom-Json | Where-Object { -not (Test-Path (Join-Path 'insights' ($_.slug + '.html'))) }).Count)
```

### Expected Outcomes

- JSON/XML parse checks pass.
- Python/Node syntax checks pass.
- No tracked credential patterns.
- No client-side admin password.
- `missing_chat=0`.
- `missing_social=0`.
- `missing_html=0`.

If any check cannot pass, document why and what remains.

---

## Agent Execution Order

Implement in this exact order:

1. Preflight.
2. Sensitive log and secret leakage cleanup.
3. Internal path blocking.
4. Admin password removal/disablement.
5. Analytics readiness.
6. Lead notification reliability.
7. Insight page conversion backfill.
8. Article schema normalization.
9. Encoding/content QA guards.
10. Daily agent resilience.
11. LinkedIn workflow truth-in-docs.
12. Documentation cleanup.
13. Final validation.

Do not skip ahead to growth ideas.

---

## Final Agent Report Format

When implementation is complete, report:

- Files changed.
- Critical issues fixed.
- Security-sensitive actions still requiring human action, especially key rotation and git history purge.
- Validation commands run and results.
- Any remaining known risks.
- Clear statement that the repo is ready for the next phase of new ideas/agents, or what blocks that readiness.

