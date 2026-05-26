# Comprehensive Website, Agent, SEO, and Lead Generation Audit Prompt

Use this prompt to run a full, expert-level assessment of the Light Tower Group repository. The goal is not a surface review. The goal is to inspect every meaningful part of the website, content system, automation scripts, lead intake funnel, SEO footprint, technical implementation, security posture, brand positioning, and growth engine.

---

## Role

You are acting as a senior website architect, full-stack engineer, technical SEO specialist, conversion-rate optimization expert, AI automation strategist, and digital marketing advisor for a commercial real estate capital advisory firm.

Assess this repository as if the business depends on the site producing qualified borrower, sponsor, developer, investor, lender, and referral leads.

Your work should be rigorous, skeptical, practical, and commercially minded. Think like the best website development consultant, technical auditor, SEO strategist, and institutional CRE marketing operator in one.

---

## Repository Context

This repo appears to contain:

- A static website for Light Tower Group, a CRE capital advisory firm.
- Core public pages such as `index.html`, `about.html`, `services.html`, `transactions.html`, `research.html`, and financing-service pages.
- A large generated `insights/` content library with corresponding social images.
- Global frontend assets including `site.css`, `site.js`, and `chat-widget.js`.
- Netlify configuration and functions in `netlify.toml` and `netlify/functions/`.
- Python automation scripts in `scripts/`, including a daily CRE news/content agent, LinkedIn essay tooling, social image generation, building discovery tooling, and source configuration.
- SEO files such as `sitemap.xml`, `robots.txt`, `feed.xml`, and `insights.json`.
- Documentation such as `DEPLOYMENT.md`, `QUICKSTART.md`, `MONITORING_CHECKLIST.md`, and `SOCIAL_IMAGES.md`.

Treat this as a production marketing and lead-generation system, not merely a static brochure site.

---

## Core Mission

Perform a full assessment in two major parts:

1. Find errors, issues, risks, broken behavior, technical debt, inconsistencies, and missed fundamentals.
2. Make serious, prioritized recommendations for enhancement, growth, lead generation, traffic acquisition, content strategy, AI agent development, automation, conversion improvement, and operational maturity.

Do not stop at generic advice. Every finding and recommendation should be grounded in actual files, actual code, actual pages, actual content, or actual missing systems in this repository.

---

## Audit Rules

- Inspect the entire repository structure before drawing conclusions.
- Read representative samples from every major class of file.
- For generated or repeated files, sample enough examples to identify patterns, quality issues, metadata consistency, duplicate content risks, internal linking issues, schema quality, and conversion opportunities.
- Prefer evidence over assumptions. Cite file paths and, when possible, line numbers.
- Separate definite issues from hypotheses that require live-site verification.
- Do not modify files during the initial audit unless explicitly instructed.
- If tests, builds, or validation commands are available, identify them and run safe read-only checks where appropriate.
- If live-site verification is needed, state exactly what must be checked externally.
- Prioritize business impact: the best technical fix is the one that helps trust, rankings, speed, conversion, reliability, or lead quality.

---

## Phase 1: Technical Repository Inventory

Start by mapping the repo.

Document:

- Site architecture and page inventory.
- Public pages and their business purpose.
- Shared assets and scripts.
- Netlify deployment setup.
- Serverless functions and their role.
- Python automation agents and scripts.
- Content generation pipeline.
- Data files and generated artifacts.
- SEO artifacts.
- Any admin/internal pages.
- Any sensitive files, secrets, or operational risks.

Deliverable:

- A concise but complete repo map.
- A list of systems and subsystems.
- A description of how content flows from source to publication.
- A description of how a visitor becomes a lead.

---

## Phase 2: Error, Risk, and Quality Assessment

Find and categorize all meaningful issues.

### Technical Correctness

Check for:

- Broken links.
- Missing assets.
- Invalid references.
- JavaScript errors.
- CSS mistakes.
- HTML validity problems.
- Duplicate IDs.
- Malformed JSON-LD.
- Broken canonical URLs.
- Incorrect redirects.
- Public exposure of internal pages or data.
- Inconsistent file names, slugs, or paths.
- Generated file drift between manifests, sitemap, RSS, and actual files.
- Encoding problems, mojibake, or corrupted characters.
- Dead code, unused scripts, stale docs, or mismatched comments.
- Any mismatch between documentation and implementation.

### Security and Privacy

Check for:

- Hardcoded API keys or secrets in documentation, scripts, or committed files.
- Public exposure of automation queues, internal admin pages, logs, or source data.
- CORS and origin validation quality.
- Chat endpoint abuse risks.
- Prompt-injection risks.
- Rate limiting gaps.
- Bot/spam risks on forms or chat flows.
- Content Security Policy strengths and weaknesses.
- Netlify headers and redirects.
- Accidental publication of internal lead data.

### Performance

Check for:

- Large images.
- Unoptimized social images accidentally loaded in pages.
- Render-blocking assets.
- Font loading behavior.
- Excessive DOM size.
- Overly large JSON files fetched client-side.
- Slow insight pages.
- Missing lazy loading.
- Cache policy problems.
- Mobile performance risks.
- Core Web Vitals risks.

### Accessibility

Check for:

- Heading hierarchy.
- Form labeling.
- Button labels.
- Keyboard navigation.
- Focus states.
- Color contrast.
- Alt text quality.
- Semantic HTML.
- Chat widget accessibility.
- Mobile readability.

### SEO and Indexability

Check for:

- Title and meta description quality.
- Canonical consistency.
- Sitemap correctness.
- Robots directives.
- RSS quality.
- Internal linking depth.
- Duplicate/thin content risks.
- Keyword targeting by page.
- Service-page search intent match.
- Local SEO signals.
- Schema.org correctness.
- E-E-A-T signals.
- Author/entity signals.
- Open Graph/Twitter card quality.
- Insight article metadata.
- Pagination or content discovery issues.
- Crawl budget concerns from large generated content libraries.

### Content Quality

Check for:

- Brand voice consistency.
- Credibility and specificity.
- Repetitive AI-written phrasing.
- Thin or generic pages.
- Overclaiming.
- Missing proof points.
- Weak calls to action.
- Missing case studies.
- Missing transaction details.
- Missing client-fit qualification.
- Lack of service differentiation.
- Whether articles attract qualified CRE capital markets audiences or only low-intent traffic.

### Conversion and Lead Capture

Check for:

- Clarity of primary CTA.
- Contact paths.
- Deal submission flow.
- Chat widget quality.
- Friction and trust signals.
- Above-the-fold value proposition.
- Mobile CTA visibility.
- Whether visitors know what to do next.
- Whether the site captures enough qualification data.
- Whether the lead flow routes to a useful CRM or notification system.
- Whether there are conversion events ready for analytics.
- Whether forms and chat produce assignments, not just conversations.

### Operations and Maintainability

Check for:

- Repeatability of the content generation pipeline.
- Logs and monitoring.
- Failure handling.
- Idempotency.
- Duplicate prevention.
- Dependency management.
- Secrets management.
- Build/deploy reliability.
- Git automation risks.
- Local-vs-production drift.
- Test coverage gaps.
- Documentation accuracy.

Deliverable:

Create an issue table with these columns:

- Severity: Critical, High, Medium, Low.
- Category.
- File or system.
- Evidence.
- Business impact.
- Recommended fix.
- Estimated effort.

Lead with the highest-impact issues.

---

## Phase 3: Live-Site and Browser Review

If possible, run or inspect the site in a browser.

Review:

- Desktop homepage.
- Mobile homepage.
- Navigation.
- Service pages.
- Insights listing.
- Individual insight articles.
- Chat widget.
- Contact or lead flow.
- Page speed and interaction quality.
- Visual polish.
- Layout breakpoints.
- Console errors.
- Network failures.
- Broken image loading.

Deliverable:

- Screenshot-based observations if browser tooling is available.
- A list of visual or UX problems by viewport.
- A list of conversion blockers.
- A list of live-site checks that could not be completed locally.

---

## Phase 4: Marketing, SEO, and Positioning Assessment

Evaluate the site as a CRE capital advisory growth engine.

Assess:

- Who the site is really for.
- Whether the value proposition is immediately clear.
- Whether it speaks to borrowers, developers, sponsors, owners, lenders, investors, and referral sources appropriately.
- Whether the site establishes trust fast enough.
- Whether "250,000+ capital sources" is credible and well-supported.
- Whether the firm sounds institutional, differentiated, and assignment-worthy.
- Whether the service pages target profitable search intent.
- Whether content is designed to rank, build authority, and convert.
- Whether insights should be segmented by intent, asset class, geography, capital type, or deal stage.
- Whether LinkedIn and website content reinforce each other.
- Whether there is a clear path from article reader to mandate submission.

Deliverable:

Write a strategic diagnosis of the current positioning and growth model.

Then recommend:

- Homepage messaging improvements.
- Service page improvements.
- Case study/transaction page improvements.
- Article template improvements.
- CTA improvements.
- Trust-building additions.
- Lead magnet ideas.
- Local SEO strategy.
- Programmatic SEO opportunities.
- High-intent keyword clusters.
- Content hubs.
- Internal linking strategy.
- LinkedIn distribution strategy.
- Email capture and nurture strategy.
- Analytics and attribution improvements.

---

## Phase 5: Agent and Automation Strategy

Evaluate the current automation system and propose additional agents.

Current apparent agents or automations may include:

- Daily news/content agent.
- LinkedIn essay agent.
- Social image generator.
- Building discovery tools.
- Chat/intake assistant.
- Deal notification function.
- Competitor monitor.

Assess each for:

- Purpose.
- Inputs and outputs.
- Reliability.
- Business value.
- Failure modes.
- Security risks.
- Content quality risks.
- Lead-generation value.
- Monitoring needs.
- How it could be improved.

Then propose additional agents that can drive traffic, leads, assignments, and operational leverage.

Consider agents such as:

- SEO Technical Auditor Agent: checks sitemap, schema, metadata, broken links, duplicate titles, broken images, and indexability.
- Content Quality Editor Agent: reviews generated articles for originality, tone, source quality, repetition, and commercial relevance before publishing.
- Internal Linking Agent: adds contextual links from insights to relevant service pages, market pages, and transaction examples.
- Lead Scoring Agent: scores chat/form leads by deal size, asset type, urgency, location, capital need, and likelihood of assignment.
- CRM Sync Agent: routes qualified leads into a CRM or structured pipeline.
- Follow-Up Drafting Agent: drafts personalized follow-up emails based on intake details.
- Market Intelligence Agent: tracks lender appetite, spreads, capital markets news, and competitor content.
- Deal-Match Agent: maps borrower mandates against lender/investor categories.
- Programmatic Landing Page Agent: creates controlled, high-quality pages for asset class, geography, and capital type combinations.
- Refresh Agent: updates stale evergreen pages and older insights.
- Analytics Agent: reviews traffic, search queries, conversions, and recommends next actions.
- LinkedIn Repurposing Agent: turns site insights into posts, carousels, comments, and outbound messages.
- Referral Partner Agent: identifies attorneys, accountants, brokers, developers, and lenders for targeted outreach.
- Reputation and Citation Agent: manages directories, profiles, local SEO citations, and entity consistency.
- Compliance/Risk Agent: checks content for unsupported claims, regulatory-sensitive language, and privacy issues.

For each proposed agent, provide:

- Objective.
- Business value.
- Inputs.
- Outputs.
- Trigger schedule.
- Required APIs or tools.
- Data storage needs.
- Human approval points.
- Risks.
- First version scope.
- Future version scope.

Deliverable:

Create an agent roadmap split into:

- Immediate agents to build now.
- Next-stage agents after the foundation is stable.
- Advanced agents that require more data, integrations, or human approval workflows.

---

## Phase 6: Traffic, Leads, and Assignments Growth Plan

Create a practical growth plan focused on qualified commercial real estate capital assignments.

Answer:

- What traffic should this site pursue?
- Which traffic is likely worthless?
- Which search terms show real mandate intent?
- Which pages should be built or improved first?
- What offers would convert owners, developers, and sponsors?
- How should the chat assistant qualify visitors?
- What data should be captured on every lead?
- How should insights convert into assignments?
- How can LinkedIn followers be moved into owned channels?
- How can the site support outbound and referral development?
- How can the site build credibility with lenders and capital sources, not just borrowers?

Recommend:

- A 30-day plan.
- A 60-day plan.
- A 90-day plan.
- A 6-month plan.
- A measurement framework.
- Key performance indicators.
- Weekly operating cadence.

Suggested KPI categories:

- Organic impressions.
- Organic clicks.
- Rankings for high-intent terms.
- Service page entrances.
- Insight-to-service clickthrough rate.
- Chat starts.
- Qualified lead captures.
- Mandate submissions.
- Meetings booked.
- Assignments signed.
- Closed transaction value.
- LinkedIn post engagement.
- Email list growth.
- Returning visitors.

---

## Phase 7: Prioritized Implementation Roadmap

Create a clear, serious roadmap.

Split recommendations into:

- Critical fixes.
- Quick wins.
- High-leverage build items.
- Strategic growth systems.
- Nice-to-have improvements.

For each recommendation include:

- Why it matters.
- What to change.
- Where in the repo it likely belongs.
- Expected impact.
- Estimated effort.
- Dependencies.
- Risk level.

Use this prioritization lens:

1. Fix anything that creates security, trust, broken UX, indexability, or lead-loss risk.
2. Improve the core conversion path.
3. Strengthen technical SEO and content quality.
4. Build automation that compounds traffic and lead generation.
5. Add advanced growth systems after measurement is reliable.

---

## Final Report Format

Write the final assessment as a comprehensive expert report with these sections:

1. Executive Summary
2. Repo and System Map
3. Most Important Findings
4. Critical and High-Severity Issues
5. Medium and Low-Severity Issues
6. Technical SEO Assessment
7. Content and Editorial Assessment
8. UX, Design, and Conversion Assessment
9. Security, Privacy, and Operational Risk Assessment
10. Agent and Automation Assessment
11. Recommended New Agents
12. Traffic, Lead, and Assignment Growth Strategy
13. 30/60/90-Day Roadmap
14. 6-Month Strategic Roadmap
15. Measurement Plan and KPIs
16. Implementation Backlog
17. Open Questions
18. Immediate Next Actions

Tone:

- Expert.
- Direct.
- Commercially serious.
- Specific.
- Not fluffy.
- Not generic.
- Written for a founder/operator who wants more qualified CRE capital assignments.

---

## First Commands To Consider

Use commands appropriate to the environment. On Windows PowerShell, examples include:

```powershell
Get-ChildItem -Force
rg --files
git status --short
Get-Content -TotalCount 120 index.html
Get-Content -TotalCount 120 site.js
Get-Content -TotalCount 120 site.css
Get-Content -TotalCount 120 chat-widget.js
Get-Content -TotalCount 120 netlify.toml
Get-Content -TotalCount 160 netlify/functions/chat.js
Get-Content -TotalCount 160 netlify/functions/deal-notify.js
Get-Content -TotalCount 160 scripts/daily_news_agent.py
Get-Content -TotalCount 160 scripts/linkedin_essay_agent.py
Get-Content -TotalCount 160 scripts/news_sources.py
Get-Content -TotalCount 160 scripts/enhanced_prompts.py
Get-Content -TotalCount 80 robots.txt
Get-Content -TotalCount 80 sitemap.xml
Get-Content -TotalCount 80 feed.xml
```

Also consider targeted searches:

```powershell
rg -n "TODO|FIXME|API_KEY|SECRET|TOKEN|password|localhost|console.log|debugger|unsafe-inline|canonical|schema.org|gtag|analytics|form|chat|lead|email|tel|linkedin|sitemap|robots|noindex|nofollow"
rg -n "â|Ã|�"
rg -n "href=|src="
rg -n "application/ld\\+json"
```

For generated insight pages, sample at least 10 to 20 files across old and new content rather than only reading one.

---

## Definition of Done

The assessment is complete only when it answers these questions clearly:

- What is broken or risky right now?
- What is silently costing traffic or leads?
- What would make the firm appear more credible and assignment-worthy?
- What should be fixed first?
- What should be built next?
- Which agents or automations would create compounding advantage?
- How can the site drive more qualified traffic?
- How can the site convert that traffic into real CRE capital assignments?
- What should be measured every week?
- What is the practical roadmap from current state to a stronger growth system?

