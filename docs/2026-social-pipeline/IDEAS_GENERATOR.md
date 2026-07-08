# Light Tower Ideas Generator

The recovered Ideas system from the older repo is now curated into one safe script:

```powershell
python scripts/ideas_generator_2026.py status
python scripts/ideas_generator_2026.py daily-menu --offline
python scripts/ideas_generator_2026.py draft --offline --render
```

## What It Does

- Builds a private Daily Ten idea ranking for Light Tower Ideas.
- Scores stories against the older Ideas rubric: place, capital, power, design, psychology, narrative, originality, and business relevance.
- Saves private source artifacts under `data/ideas/`, which is blocked by Netlify and ignored by git.
- Renders optional local draft review pages under `ideas/_drafts/`, which is ignored by git and blocked by Netlify.

## What It Does Not Do

- It does not commit.
- It does not push.
- It does not post to LinkedIn.
- It does not auto-publish to `/ideas/`.
- It does not call an AI API by default.

## Why This Is The Right Recovery

The older repo did contain the Ideas generator, but the published JSON files were scaffold output with placeholder bodies. The reusable value was the editorial system: source scouting, Daily Ten ranking, scoring rubric, and voice prompts.

The live Downloads repo already has a stronger article/social pipeline, so this generator is intentionally review-first. It gives us the missing Ideas ideation workflow without adding unsafe auto-publishing behavior.

## Review Flow

1. Run the offline mode first:

```powershell
python scripts/ideas_generator_2026.py daily-menu --offline
python scripts/ideas_generator_2026.py draft --offline --render
```

2. Review `data/ideas/internal/daily-ten/YYYY-MM-DD.json`.
3. Review local HTML drafts in `ideas/_drafts/`.
4. Promote only human-approved, fully edited essays into public `ideas/*.html`.

