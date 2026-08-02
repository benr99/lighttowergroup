"""Multi-stage editorial pipeline with real LLM calls for each stage.

Orchestrates: analytical brief (deterministic) â†’ prompt assembly â†’ 
drafting (LLM) â†’ financial review (LLM) â†’ editorial review (LLM) â†’ 
fact verification (deterministic) â†’ final revision (LLM).
"""

from __future__ import annotations
import json
import re
from typing import Any
from urllib.parse import urlparse

from canonical_item import CanonicalItem
from analytical_brief import build_analytical_brief
from research_dossier import dossier_prompt_payload


# Try to import call_deepseek â€” may not be available in test environments
try:
    from editorial_scoring import call_deepseek
    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False


class EditorialPipeline:
    """Multi-stage article generation with separated reasoning and prose."""

    def __init__(self, api_key: str = "", provider: dict[str, Any] | None = None):
        self.api_key = api_key
        self.provider = dict(provider or {})
        self.stages_run: list[str] = []
        self.errors: list[str] = []

    # â”€â”€ Stage 1: Analytical Brief (deterministic, no LLM) â”€â”€
    def stage_analytical_brief(self, item: CanonicalItem, dossier: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build the structured pre-writing analytical brief."""
        self.stages_run.append("analytical_brief")
        try:
            brief = build_analytical_brief(item, dossier)
        except Exception as e:
            self.errors.append(f"analytical_brief: {e}")
            raise
        if _HAS_LLM and self.api_key:
            try:
                from analytical_brief import enhance_brief_with_llm
                brief = enhance_brief_with_llm(
                    brief,
                    item,
                    self.api_key,
                    provider=self.provider or None,
                )
            except Exception as e:
                self.errors.append(f"analytical_brief_enhance: {e}")
        return brief

    # â”€â”€ Stage 2: Assemble Writing Prompt â”€â”€
    def stage_assemble_prompt(
        self,
        item: CanonicalItem,
        brief: dict[str, Any],
        dossier: dict[str, Any] | None = None,
        article_format: str | None = None,
    ) -> dict[str, Any]:
        """Assemble the complete writing prompt from brief + dossier + sector prompt."""
        self.stages_run.append("assemble_prompt")

        try:
            from generation import get_sector_prompt
            system_prompt = get_sector_prompt(item.primary_sector or "commercial_real_estate")
        except ImportError:
            system_prompt = "You are a financial journalist writing for Light Tower Group."
        except Exception as e:
            self.errors.append(f"assemble_prompt: {e}")
            system_prompt = "You are a financial journalist writing for Light Tower Insights. Write articles that are analytically rigorous, source-grounded, and professionally voiced."

        # Build a rich user prompt with the analytical brief
        thesis = brief.get("thesis", "")
        tension = brief.get("core_tension", "")
        question = brief.get("central_financial_question", "")
        architecture = brief.get("article_architecture", {})
        depth = brief.get("article_depth", {})
        parties = brief.get("parties_and_incentives", [])
        economics = brief.get("transaction_economics", {})
        key_numbers = brief.get("key_numbers", [])
        unknowns = brief.get("unknowns", [])
        requested_words = str(depth.get("words", "800-1300"))
        format_label = str(article_format or "analysis")
        if article_format:
            try:
                from editorial_intelligence import FORMAT_SPECS

                format_spec = FORMAT_SPECS.get(article_format)
                if format_spec:
                    requested_words = f"{format_spec['min_words']}-{format_spec['max_words']}"
                    format_label = str(format_spec.get("label") or article_format)
            except ImportError:
                pass

        summary_text = _strip_html_tags(item.raw_summary or item.raw_text or 'No summary available')
        dossier_text = (
            dossier_prompt_payload(dossier, max_chars=24000)
            if isinstance(dossier, dict)
            else "No research dossier was provided. The article is not eligible for automatic publication."
        )

        parties_json = _safe_truncate_json(parties, max_chars=1500)
        economics_json = _safe_truncate_json(economics, max_chars=1000)
        key_numbers_json = _safe_truncate_json(key_numbers, max_chars=800)
        unknowns_json = _safe_truncate_json(unknowns, max_chars=500)

        user_prompt = f"""ARTICLE ASSIGNMENT

STORY: {item.headline}
SOURCE: {item.source_name} (tier {item.source_tier})
SECTOR: {item.primary_sector}
SUMMARY: {summary_text}

SOURCE DOSSIER â€” THIS IS THE FACTUAL BOUNDARY
{dossier_text}

ANALYTICAL BRIEF
The following structured analysis has been prepared. Use it to guide your writing.

CENTRAL QUESTION: {question}

CORE TENSION: {tension}

THESIS: {thesis}

PARTIES AND INCENTIVES:
{parties_json}

TRANSACTION ECONOMICS:
{economics_json}

KEY NUMBERS TO INTERPRET:
{key_numbers_json}

IMPORTANT UNKNOWNS:
{unknowns_json}

ARTICLE STRUCTURE: {architecture.get('name', 'Standard analysis')}
EDITORIAL FORMAT: {format_label}
HARD LENGTH CONTRACT: {requested_words} words

WRITING INSTRUCTIONS
1. Open with the most revealing fact, number, or tension from the brief â€” not a generic announcement.
2. Build the article around the central question and thesis.
3. Interpret the key numbers â€” don't just list them. Explain what they mean.
4. Name the parties. Explain what each gains and risks.
5. Distinguish clearly between reported facts, reasonable inferences, and unknowns.
6. Vary sentence rhythm. Avoid formulaic openings like "The most important X is not Y."
7. End with the unresolved question or next signal to watch.
8. Do not use "signals," "highlights," "underscores," or "showcases" as analytical verbs.
9. Every factual and numerical claim must be supported by the source dossier.
10. Label calculations and reasonable inferences explicitly. Never invent a market statistic, return target, tenant, financing term, motive, quote, or source.
11. The sources array must contain only the canonical article URLs provided in the dossier. Do not substitute publication homepages.
12. Never mention an internal editorial, ranking, composite, or significance score in public copy.

OUTPUT FORMAT
Return one valid JSON object with these public fields and internal control ledgers:
{{
  "title": "Specific headline under 90 characters",
  "subtitle": "One-sentence consequence under 150 characters",
  "slug": "lowercase-kebab-case-max-six-words",
  "category": "Capital Markets | Market Analysis | Debt & Equity | Policy & Regulation | Deal Intelligence",
  "meta_description": "Specific description under 160 characters",
  "tags": ["three", "to", "five", "specific", "tags"],
  "body_html": "<p>Complete article using paragraph tags only.</p>",
  "data_points": [
    {{"label": "Short source-supported label", "value": "Reported value", "source_url": "Exact dossier URL"}}
  ],
  "sources": [{{"name": "Exact source name", "url": "Exact dossier URL"}}],
  "excerpt": "One- or two-sentence preview",
  "narrative_ledger": {{
    "anchor": "Reported anchor",
    "tension": "Economic tension",
    "cast": ["Party: documented constraint or clock"],
    "mechanism": "Supported financial or operating mechanism",
    "claim": "Bounded interpretation",
    "reader_consequence": "What a market participant should test",
    "reported_facts": ["Reported fact"],
    "interpretations": ["Clearly labeled inference"],
    "open_questions": ["Material unknown"],
    "scene": {{"used": false, "detail": "", "source_basis": ""}}
  }},
  "excellence_ledger": {{
    "why_now": "Why this deserves attention now",
    "original_inference": "The article's one bounded added insight",
    "counterargument": "Strongest plausible alternative explanation",
    "concrete_detail": "A detail supported by a named source",
    "human_stakes": "The supported human, institutional, or physical consequence",
    "reader_value": "What the reader understands or can test after reading",
    "memorable_line": "One exact sentence that appears verbatim in body_html",
    "claim_evidence": [
      {{"claim": "Factual claim", "source_url": "Exact dossier URL"}}
    ]
  }}
}}
The ledgers are internal audit evidence and must be complete. Never discuss them
in body_html. Use only URLs present in the dossier. Return JSON only.
"""

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": 8000,
            "temperature": 0.2,
            "article_format": str(article_format or "analysis"),
            "requested_words": requested_words,
        }

    # â”€â”€ Stage 3: Draft (LLM call) â”€â”€
    def stage_draft(self, prompt_context: dict[str, Any]) -> dict[str, Any]:
        """Generate the first draft via LLM."""
        self.stages_run.append("draft")
        if not _HAS_LLM or not self.api_key:
            return {"status": "skipped", "reason": "No LLM available (offline or no API key)"}

        try:
            raw = call_deepseek(
                prompt_context["user_prompt"],
                self.api_key,
                max_tokens=prompt_context.get("max_tokens", 5200),
                temperature=prompt_context.get("temperature", 0.2),
                json_mode=True,
                system=prompt_context.get("system_prompt", ""),
                provider=self.provider or None,
            )
            article = _extract_json(
                raw,
                required_fields=[
                    "body_html", "title", "excerpt", "sources", "excellence_ledger"
                ],
            )
            if not isinstance(article.get("sources"), list) or not article["sources"]:
                raise ValueError("LLM response did not include a non-empty sources array")
            return {"status": "completed", "article": article}
        except Exception as e:
            self.errors.append(f"draft: {e}")
            return {"status": "failed", "error": str(e)}

    # â”€â”€ Stage 4: Financial Review (LLM call) â”€â”€
    def stage_financial_review(
        self,
        article: dict[str, Any],
        brief: dict[str, Any],
        dossier: dict[str, Any] | None = None,
        article_format: str | None = None,
    ) -> dict[str, Any]:
        """Review the article for financial accuracy and depth."""
        self.stages_run.append("financial_review")
        if not _HAS_LLM or not self.api_key:
            return {"status": "skipped", "reason": "No LLM available"}

        body = article.get("body_html", "")
        body_clean = re.sub(r'<[^>]+>', ' ', body or "").strip()
        evidence_level = str((dossier or {}).get("evidence_level") or "unknown")
        source_count = int((dossier or {}).get("independent_source_count") or 0)
        evidence_text = (
            dossier_prompt_payload(dossier, max_chars=9000)
            if isinstance(dossier, dict)
            else "No dossier supplied."
        )
        prompt = f"""You are a financial editor reviewing an article for accuracy and analytical depth.

ARTICLE:
{body_clean[:8000]}

EVIDENCE STANDARD:
- Editorial format: {article_format or 'analysis'}
- Dossier evidence level: {evidence_level}
- Independent sources: {source_count}

SOURCE DOSSIER - THE ONLY FACTUAL BOUNDARY:
{evidence_text}

ANALYTICAL BRIEF (what the article SHOULD cover):
- Central question: {brief.get('central_financial_question', '')}
- Thesis: {brief.get('thesis', '')}
- Key numbers: {_safe_truncate_json(brief.get('key_numbers', []), max_chars=800)}

Check for:
1. Are any financial figures incorrect or unsupported?
2. Does the article explain what the numbers MEAN, not just what they ARE?
3. Are any claims about returns, valuations, or market conditions unsupported?
4. Does the article distinguish reported facts from calculated metrics?
5. Is the incentive analysis clear â€” who gains, who risks, why now?

CALIBRATION RULES:
- Judge the article against what the dossier actually discloses, not against an
  imagined underwriting file.
- For a 240-430 word Intelligence Brief, one credible source can support a
  bounded article when every claim is attributed and material unknowns are
  stated clearly.
- Do NOT fail an article because undisclosed loan pricing, returns, valuations,
  market comparables, or a second source are absent. Fail it if the article
  invents them, hides the gap, or makes a conclusion that requires them.
- Do NOT require financial figures when the source contains none. In that case,
  assess whether the article makes one useful, evidence-bounded argument and
  explicitly identifies what cannot be known.
- A reported claim may be attributed to its named publication. Do not reject it
  solely because Light Tower did not independently verify the publication's
  reporting; reject it if the attribution is missing or overstated.
- Set passed=true when there is no specific factual or analytical defect. Do not
  use a generic desire for more depth as a veto.

Return JSON with: {{issues: [list of specific problems], passed: true/false, score_1_10: int, summary: string}}
"""
        try:
            raw = call_deepseek(
                prompt,
                self.api_key,
                # Reasoning-capable DeepSeek models count hidden reasoning
                # against this ceiling. A 1,000-token cap can expire before
                # the compact JSON review reaches message.content.
                max_tokens=4000,
                temperature=0.1,
                json_mode=True,
                provider=self.provider or None,
            )
            result = _extract_json(raw)
            result["status"] = "completed"
            result["passed"] = result.get("passed") is True
            return result
        except Exception as e:
            self.errors.append(f"financial_review: {e}")
            return {
                "status": "unavailable",
                "issues": [f"Financial review unavailable: {type(e).__name__}"],
                "passed": False,
                "score_1_10": 0,
                "summary": "Financial review failed closed",
            }

    # â”€â”€ Stage 5: Editorial Review (LLM call) â”€â”€
    def stage_editorial_review(self, article: dict[str, Any]) -> dict[str, Any]:
        """Review the article for writing quality."""
        self.stages_run.append("editorial_review")
        if not _HAS_LLM or not self.api_key:
            return {"status": "skipped", "reason": "No LLM available"}

        body = article.get("body_html", "")
        body_clean = re.sub(r'<[^>]+>', ' ', body or "").strip()
        prompt = f"""You are an editorial reviewer. Score this article on writing quality.

ARTICLE:
{body_clean[:8000]}

Check for:
1. Opening quality: Does it hook the reader with something specific, not generic?
2. Structure: Does the article flow logically, or follow a formulaic template?
3. Sentence quality: Are sentences varied in length and structure? Any repetitive patterns?
4. AI language: Does it use "signals," "highlights," "underscores," "showcases"?
5. Conclusion: Does it end with the right implication, not a vague forward look?
6. Voice: Does it sound like a knowledgeable professional, not an institution?

Return JSON with: {{issues: [list], passed: true/false, score_1_10: int, opening_quality: string, worst_sentence: string, summary: string}}
"""
        try:
            raw = call_deepseek(
                prompt,
                self.api_key,
                # Leave enough room for hidden reasoning plus the complete
                # typed review contract; truncated contracts still fail closed.
                max_tokens=4000,
                temperature=0.1,
                json_mode=True,
                provider=self.provider or None,
            )
            result = _extract_json(raw)
            result["status"] = "completed"
            result["passed"] = result.get("passed") is True
            return result
        except Exception as e:
            self.errors.append(f"editorial_review: {e}")
            return {
                "status": "unavailable",
                "issues": [f"Editorial review unavailable: {type(e).__name__}"],
                "passed": False,
                "score_1_10": 0,
                "summary": "Editorial review failed closed",
            }

    # â”€â”€ Stage 6: Fact Verification (deterministic) â”€â”€
    def stage_fact_verification(
        self,
        article: dict[str, Any],
        brief: dict[str, Any],
        dossier: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Verify key facts against the analytical brief."""
        self.stages_run.append("fact_verification")
        body = article.get("body_html", "")
        issues = []

        if not isinstance(dossier, dict):
            issues.append("Research dossier is missing")
        else:
            canonical_urls = {
                str(source.get("url", "")).strip()
                for source in dossier.get("sources", [])
                if isinstance(source, dict)
                and str(source.get("url", "")).startswith(("https://", "http://"))
            }
            if not canonical_urls:
                issues.append("Research dossier has no canonical source URL")
            generated_sources = article.get("sources")
            if not isinstance(generated_sources, list) or not generated_sources:
                issues.append("Article has no source list")
            else:
                for source in generated_sources:
                    url = str(source.get("url", "")).strip() if isinstance(source, dict) else ""
                    if url not in canonical_urls:
                        issues.append(f"Article source is not present in dossier: {url or '[missing URL]'}")

        # Check that key numbers from the brief appear in the article
        for kn in brief.get("key_numbers", [])[:3]:
            num = kn.get("number", "")
            if num and num not in body:
                issues.append(f"Key number '{num}' from brief not found in article")

        # Check for unsupported claims
        unsupported = [
            "is expected to", "analysts predict", "sources say",
            "widely viewed as", "market believes",
        ]
        for phrase in unsupported:
            if phrase in body.lower():
                issues.append(f"Potentially unsupported claim: '{phrase}'")

        if isinstance(dossier, dict) and dossier.get("source_facts"):
            try:
                from fact_extractor import audit_article_facts

                source_tier = min(
                    (int(source.get("tier", 3) or 3) for source in dossier.get("sources", []) if isinstance(source, dict)),
                    default=3,
                )
                audit = audit_article_facts(body, dossier["source_facts"], source_tier=source_tier)
                if audit.get("hold_for_review"):
                    unmatched_amounts = audit.get("unmatched_amounts", [])
                    unmatched_companies = audit.get("unmatched_companies", [])
                    unmatched_addresses = audit.get("unmatched_addresses", [])
                    amount_detail = ", ".join(
                        f"{item.get('raw', '[missing]')} near "
                        f"{str(item.get('context', ''))[:120]!r}"
                        for item in unmatched_amounts[:3]
                        if isinstance(item, dict)
                    )
                    company_detail = ", ".join(
                        str(value) for value in unmatched_companies[:5]
                    )
                    address_detail = ", ".join(
                        str(value) for value in unmatched_addresses[:3]
                    )
                    evidence_detail = "; ".join(
                        value for value in (
                            f"amounts: {amount_detail}" if amount_detail else "",
                            f"companies: {company_detail}" if company_detail else "",
                            f"addresses: {address_detail}" if address_detail else "",
                        ) if value
                    )
                    issues.append(
                        "Article contains dossier-unverified claims "
                        f"({len(unmatched_amounts)} amounts, "
                        f"{len(unmatched_companies)} companies, "
                        f"{len(unmatched_addresses)} addresses)"
                        + (f": {evidence_detail}" if evidence_detail else "")
                    )
            except Exception as exc:
                issues.append(f"Deterministic fact audit unavailable: {type(exc).__name__}")

        passed = len(issues) == 0
        return {"issues": issues, "passed": passed, "score_1_10": 10 if passed else 6}

    # â”€â”€ Stage 7: Final Revision (LLM call) â”€â”€
    def stage_final_revision(
        self,
        article: dict[str, Any],
        prompt_context: dict[str, Any],
        financial_review: dict[str, Any],
        editorial_review: dict[str, Any],
        fact_issues: dict[str, Any],
    ) -> dict[str, Any]:
        """Revise the article incorporating all review feedback."""
        self.stages_run.append("final_revision")
        if not _HAS_LLM or not self.api_key:
            return {"status": "skipped", "article": article}

        # Only revise if there are issues
        all_issues = (
            financial_review.get("issues", []) +
            editorial_review.get("issues", []) +
            fact_issues.get("issues", [])
        )
        if financial_review.get("passed") is not True and not financial_review.get("issues"):
            all_issues.append("Financial review did not pass")
        if editorial_review.get("passed") is not True and not editorial_review.get("issues"):
            all_issues.append("Editorial review did not pass")
        if not all_issues:
            return {"status": "no_issues", "article": article}

        original_json = _safe_truncate_json(article, max_chars=15000)
        dossier_text = dossier_prompt_payload(
            prompt_context.get("dossier", {}), max_chars=12000
        ) if isinstance(prompt_context.get("dossier"), dict) else ""
        prompt = f"""REVISE this article to fix the following issues.

CURRENT ARTICLE JSON:
{original_json}

SOURCE DOSSIER â€” DO NOT EXCEED THIS EVIDENCE:
{dossier_text}

ISSUES TO FIX:
{_safe_truncate_json(all_issues, max_chars=2000)}

FINANCIAL REVIEW: {financial_review.get('summary', '')}
EDITORIAL REVIEW: {editorial_review.get('summary', '')}

Rewrite the COMPLETE article as JSON. Fix every issue. Keep all source-grounded facts.
Delete an unsupported claim when the dossier supplies no valid replacement.
Do not introduce new unsupported claims, numbers, names, or motives. Maintain
the evidence-bounded thesis and the original {prompt_context.get('requested_words', 'assigned')} word contract.

Return valid JSON with the same fields as the original, including title,
subtitle, slug, category, meta_description, body_html, data_points, sources,
tags, excerpt, narrative_ledger, and excellence_ledger. The complete
excellence_ledger is mandatory; its memorable_line must appear verbatim in
body_html and every claim_evidence source_url must be an exact dossier URL.
"""
        try:
            raw = call_deepseek(
                prompt,
                self.api_key,
                max_tokens=10000,
                temperature=0.15,
                json_mode=True,
                provider=self.provider or None,
            )
            revised = _extract_json(
                raw,
                required_fields=[
                    "body_html", "title", "excerpt", "sources", "excellence_ledger"
                ],
            )
            revised = {**article, **revised}
            return {"status": "revised", "article": revised}
        except Exception as e:
            self.errors.append(f"final_revision: {e}")
            return {"status": "revision_failed", "article": article}

    # â”€â”€ Run full pipeline â”€â”€
    def run(
        self,
        item: CanonicalItem,
        dossier: dict[str, Any] | None = None,
        api_key: str = "",
        article_format: str | None = None,
    ) -> dict[str, Any]:
        """Execute the complete 7-stage editorial pipeline.

        If api_key is provided, it overrides the instance-level key for this run
        (useful when reusing a pipeline instance across many articles with different keys).
        """
        if api_key:
            self.api_key = api_key
        self.stages_run = []
        self.errors = []
        result: dict[str, Any] = {
            "item_id": item.item_id,
            "headline": item.headline,
            "stages": {},
            "article": None,
            "status": "started",
        }

        try:
            # Stage 1: Analytical Brief
            brief = self.stage_analytical_brief(item, dossier)
            result["stages"]["analytical_brief"] = {"status": "completed"}

            # Stage 2: Assemble Prompt
            prompt_ctx = self.stage_assemble_prompt(
                item,
                brief,
                dossier,
                article_format=article_format,
            )
            prompt_ctx["dossier"] = dossier
            result["stages"]["assemble_prompt"] = {"status": "completed"}

            # Stage 3: Draft
            draft_result = self.stage_draft(prompt_ctx)
            result["stages"]["draft"] = draft_result
            if draft_result.get("status") == "skipped":
                result["status"] = "offline"
                result["stages_run"] = self.stages_run
                result["errors"] = list(self.errors)
                return result
            if draft_result.get("status") != "completed":
                result["status"] = "draft_failed"
                result["stages_run"] = self.stages_run
                result["errors"] = list(self.errors)
                return result
            article = draft_result.get("article")
            if article is None:
                result["status"] = "draft_failed"
                result["stages_run"] = self.stages_run
                result["errors"] = list(self.errors) + ["Missing 'article' key in draft result"]
                return result
            result["article"] = article

            # Stage 4: Financial Review
            fin_review = self.stage_financial_review(
                article,
                brief,
                dossier=dossier,
                article_format=article_format,
            )
            result["stages"]["financial_review"] = fin_review

            # Stage 5: Editorial Review
            ed_review = self.stage_editorial_review(article)
            result["stages"]["editorial_review"] = ed_review

            # Stage 6: Fact Verification
            fact_issues = self.stage_fact_verification(article, brief, dossier)
            result["stages"]["fact_verification"] = fact_issues

            # Stage 7: Final Revision (only if issues found)
            revision = self.stage_final_revision(article, prompt_ctx, fin_review, ed_review, fact_issues)
            result["stages"]["final_revision"] = revision
            if revision.get("status") not in ("revised", "no_issues"):
                result["status"] = "review_required"
                result["stages_run"] = self.stages_run
                result["errors"] = list(self.errors)
                return result

            final_article = revision.get("article", article)
            result["article"] = final_article

            if revision.get("status") == "revised":
                post_fin = self.stage_financial_review(
                    final_article,
                    brief,
                    dossier=dossier,
                    article_format=article_format,
                )
                post_ed = self.stage_editorial_review(final_article)
                post_fact = self.stage_fact_verification(final_article, brief, dossier)
                result["stages"]["post_revision_financial_review"] = post_fin
                result["stages"]["post_revision_editorial_review"] = post_ed
                result["stages"]["post_revision_fact_verification"] = post_fact
            else:
                post_fin, post_ed, post_fact = fin_review, ed_review, fact_issues

            if not (
                post_fin.get("passed") is True
                and post_ed.get("passed") is True
                and post_fact.get("passed") is True
            ):
                result["status"] = "review_required"
                result["stages_run"] = self.stages_run
                result["errors"] = list(self.errors)
                return result

            result["status"] = "completed"
            result["stages_run"] = self.stages_run
            result["errors"] = list(self.errors)

        except Exception as e:
            self.errors.append(str(e))
            result["status"] = "failed"
            result["error"] = str(e)
            result["errors"] = list(self.errors)

        return result


def _extract_json(raw: str, required_fields: list[str] | None = None) -> dict[str, Any]:
    """Extract JSON from LLM response. Optionally validates required fields.
    
    Raises ValueError on parse failure or missing required fields.
    """
    raw = raw or ""
    validation_error: ValueError | None = None
    
    # Strategy 1: Try extracting from markdown code blocks ```json ... ```
    m = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', raw)
    if m:
        try:
            data = _load_json_object(m.group(1))
            return _validate_required(data, required_fields)
        except json.JSONDecodeError:
            pass
        except ValueError as exc:
            validation_error = exc
    
    # Strategy 2: Greedy match { ... }
    m = re.search(r'\{[\s\S]*\}', raw)
    if m:
        try:
            data = _load_json_object(m.group())
            return _validate_required(data, required_fields)
        except json.JSONDecodeError:
            pass
        except ValueError as exc:
            validation_error = exc
    
    # Strategy 3: Non-greedy match, taking the first complete JSON object
    m = re.search(r'\{[\s\S]*?\}(?:\s*$|\s*\n)', raw)
    if m:
        try:
            data = _load_json_object(m.group())
            return _validate_required(data, required_fields)
        except json.JSONDecodeError:
            pass
        except ValueError as exc:
            validation_error = exc

    if validation_error is not None:
        raise validation_error

    raise ValueError(f"Could not parse JSON from response: {str(raw)[:200]}")


def _load_json_object(candidate: str) -> dict[str, Any]:
    """Parse provider JSON without accepting a non-object review contract.

    Some otherwise valid JSON-mode responses contain an unescaped newline in
    a reviewer explanation or a trailing comma. Python's strict parser rejects
    both even though the response's typed decision fields are intact. The
    bounded fallbacks below repair only those two syntax defects; they do not
    infer missing review fields or turn a failed review into a pass.
    """
    value = str(candidate or "").strip().lstrip("\ufeff")
    variants = [value]
    without_trailing_commas = re.sub(r",\s*([}\]])", r"\1", value)
    if without_trailing_commas != value:
        variants.append(without_trailing_commas)
    last_error: Exception | None = None
    for variant in variants:
        for strict in (True, False):
            try:
                parsed = json.loads(variant, strict=strict)
                if not isinstance(parsed, dict):
                    raise ValueError("Provider JSON contract must be an object")
                return parsed
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
    raise ValueError(f"Invalid provider JSON object: {last_error}")


def _validate_required(data: dict[str, Any], required_fields: list[str] | None) -> dict[str, Any]:
    if required_fields:
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(
                f"LLM response missing required fields: {missing}. "
                f"Got keys: {list(data.keys())[:20]}"
            )
    return data


def _strip_html_tags(text: str) -> str:
    """Strip HTML tags and decode HTML entities from text."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&mdash;', '\u2014')
    text = text.replace('&rsquo;', '\u2019')
    text = text.replace('&ldquo;', '\u201c')
    text = text.replace('&rdquo;', '\u201d')
    text = text.replace('&lsquo;', '\u2018')
    text = text.replace('&#39;', "'")
    text = text.replace('&quot;', '"')
    text = re.sub(r'&#\d+;', ' ', text)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _safe_truncate_json(data: Any, max_chars: int) -> str:
    """Dump data as JSON, truncating safely to avoid broken JSON.

    Truncates list/array items or dict keys before serialization
    rather than slicing the JSON string mid-structure.
    """
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    if len(json_str) <= max_chars:
        return json_str

    if isinstance(data, list):
        truncated = []
        for item in data:
            candidate = json.dumps(truncated + [item], indent=2, ensure_ascii=False)
            if len(candidate) > max_chars:
                break
            truncated.append(item)
        if not truncated and data:
            return json.dumps(
                [{"_truncated": f"{len(data)} items, first item too large to include"}],
                indent=2, ensure_ascii=False,
            )
        return json.dumps(truncated, indent=2, ensure_ascii=False)

    if isinstance(data, dict):
        truncated: dict[str, Any] = {}
        for key, value in data.items():
            candidate = json.dumps(truncated | {key: value}, indent=2, ensure_ascii=False)
            if len(candidate) > max_chars:
                break
            truncated[key] = value
        if not truncated and data:
            return json.dumps(
                {"_truncated": f"{len(data)} keys, first value too large to include"},
                indent=2, ensure_ascii=False,
            )
        return json.dumps(truncated, indent=2, ensure_ascii=False)

    return json_str[:max_chars]


def _hard_truncate_json_string(data: Any, max_chars: int) -> str:
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    if len(json_str) <= max_chars:
        return json_str
    if isinstance(data, list) and data:
        return json.dumps([{"_truncated": f"{len(data)} items"}], indent=2, ensure_ascii=False)
    if isinstance(data, dict):
        return json.dumps({"_truncated": f"{len(data)} keys, data too large"}, indent=2, ensure_ascii=False)
    return json.dumps({"_truncated": True}, indent=2, ensure_ascii=False)


def run_editorial_pipeline(
    item: CanonicalItem,
    dossier: dict[str, Any] | None = None,
    api_key: str = "",
    provider: dict[str, Any] | None = None,
    article_format: str | None = None,
) -> dict[str, Any]:
    """Convenience function."""
    pipeline = EditorialPipeline(api_key=api_key, provider=provider)
    return pipeline.run(item, dossier, article_format=article_format)


def get_pipeline_stats(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate statistics across pipeline runs. Non-dict items are skipped."""
    valid = [r for r in results if isinstance(r, dict)]
    total = len(valid)
    completed = sum(1 for r in valid if r.get("status") == "completed")
    failed = sum(1 for r in valid if r.get("status") == "failed")
    return {
        "total_stories": total,
        "completed": completed,
        "failed": failed,
        "completion_rate": round(completed / max(1, total) * 100, 1),
    }


def story_to_canonical_item(story: dict[str, Any]) -> CanonicalItem:
    """Convert a daily_news_agent story dict to a CanonicalItem for the pipeline.

    Handles the bridge between the existing story-based system and the
    pipeline's typed CanonicalItem inputs.
    """
    item = CanonicalItem()
    item.headline = story.get("title") or story.get("headline", "")
    item.source_name = story.get("source", "")
    item.source_url = story.get("url", "")
    item.raw_summary = story.get("summary", "")
    item.raw_text = story.get("full_text", "")
    item.publication_date = story.get("published", "")
    item.source_tier = int(story.get("source_tier", 3))
    item.source_authority = "primary" if item.source_tier == 1 else "secondary"

    topics = story.get("topics", []) or []
    if "capital_placement" in topics or "major_sale" in topics or "distress" in topics or "cmbs" in topics or "reit_public_markets" in topics or "development_finance" in topics or "private_credit" in topics or "policy" in topics:
        item.primary_sector = "commercial_real_estate"
    elif "private_equity" in topics or "mna" in topics:
        item.primary_sector = "private_equity"
    elif "fed_rates" in topics:
        item.primary_sector = "fed_macro"
    elif "bank_credit" in topics:
        item.primary_sector = "banking_credit"
    elif "government_action" in topics:
        item.primary_sector = "local_government"
    else:
        item.primary_sector = "commercial_real_estate"

    entities = story.get("entities") or {}
    if isinstance(entities, dict):
        item.companies = entities.get("companies", [])
        amounts = entities.get("amounts", [])
        if amounts:
            item.transaction_value_raw = amounts[0]

    features = story.get("attention_features") or {}
    if isinstance(features, dict):
        if features.get("has_big_number"):
            item.composite_score = max(item.composite_score, 65.0)
        if features.get("has_known_institution"):
            item.composite_score = max(item.composite_score, 55.0)
    item.composite_score = item.composite_score or 50.0
    item.tier = story.get("selection_tier", "tier_3_useful_coverage")

    item.item_id = item.generate_id()
    return item
