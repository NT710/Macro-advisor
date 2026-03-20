# Skill 10: External Analyst Monitor

## Objective

Browse the feeds of two external macro analysts and read their actual content — including full articles, not just feed headlines. The system reads with fresh eyes — no pre-loaded expectations about what to find. Whatever they're focused on this week is what gets reported.

## Sources

### Andreas Steno Larsen
- **Feed:** https://x.com/AndreasSteno
- **Who:** Macro strategist, runs Steno Research. Publishes on X — mix of short posts and longer-form articles. The articles contain the real analysis (charts, specific data, trade calls, policy interpretation). The short posts are teasers.

### Alpine Macro
- **Feed:** https://www.linkedin.com/company/alpine-macro/posts/?feedView=all
- **Who:** Institutional macro research firm. Publishes on LinkedIn — typically excerpts and charts from their research reports with key conclusions.

## Execution Steps

### Step 1: Browse the feed
1. Use Chrome `tabs_context_mcp` to get available tabs (create if needed)
2. Navigate to the feed URL
3. Use `get_page_text` to extract the feed text
4. Identify the last 5-10 posts, noting dates

### Step 2: Follow links to full articles
This is the critical step the feed scan alone misses. Analysts post short teasers that link to full articles. The full article is where the real analysis lives.

For each post that appears to link to a longer article or thread:
1. Look for links in the post text or use `find` / `read_page` to locate clickable article links
2. Navigate to the full article URL
3. Use `get_page_text` to read the complete article
4. Extract the substantive analysis — specific data points, charts described, trade calls, policy interpretations, frameworks

If a post is self-contained (no link to a longer piece), the feed text is sufficient.

**Why this matters:** A feed scan of Steno's X might show "Iran is firing more and hitting more, while the Fed prepares to invent a new transitory." That's a headline. The linked article contains: a detailed Fed policy analysis (dovish despite inflation revision, Clarida suggesting new "transitory" language), a US energy export ban assessment (strongly recessionary if implemented), a phase 1/phase 2 timing framework (inflation shock now, growth shock in 1-2 months), and specific positioning calls. Missing the article means missing the analysis.

### Step 3: For each analyst, extract
For each relevant post or article, note:
- **Date** of the post (critical — undated views are worthless)
- **What they're saying** — the actual analysis, not a headline summary
- **Specific data, charts, or frameworks** they reference — describe charts in enough detail that someone who hasn't seen them understands the argument
- **Their positioning or trade implications** — explicit calls, what they're long/short, any sizing language
- **Policy interpretation** — how they read central bank actions (this is often where the alpha is — two analysts can read the same Fed statement differently)

### Step 4: Cross-reference
Compare their views against our current regime assessment. Note alignment, divergence, and anything they see that we might be missing.

### Fallback
If Chrome is not available, fall back to web search: "Andreas Steno latest [YEAR]" and "Alpine Macro latest research [YEAR]". Note in the output that this is a fallback and may miss longer-form content.

## How to Read Their Content

**Do not pre-filter for specific topics.** Read what's actually there.

**Follow the links.** The feed surface is advertising. The article is the product. If there's a link, read it.

**Capture the reasoning, not just the conclusion.** "Steno is bullish oil" is useless. "Steno argues the Fed is looking through the oil shock because they prioritize growth over inflation, Clarida suggested they'll redefine 'transitory,' and this means cuts are still in play even at $96 oil — which is dovish relative to market pricing" is useful. The reasoning is what the thesis monitor needs to cross-reference.

**Capture shifts in focus.** If an analyst who was talking about one theme suddenly pivots, that's a signal.

**Note when they disagree with each other.** Two smart macro analysts disagreeing is more useful than two agreeing.

**Date everything.** "Steno posted on March 19 that..." not "Steno thinks..."

## Output Format

```markdown
## External Analyst Monitor — [Date]

### Andreas Steno (@AndreasSteno)
**Posts reviewed:** [date range of posts scanned]
**Articles read in full:** [count — list URLs if possible]
**Current focus:** [What is he actually talking about this week? 1-2 sentences.]
**Key views:**
- [Specific view with date — include the reasoning, not just the conclusion]
- [Another specific view with date]
**Positioning signals:** [Explicit trade calls, what's he long/short, any sizing. If none: "No explicit positioning this period."]
**Policy interpretation:** [How does he read the Fed/ECB/other CBs? This often diverges from consensus and is where thesis-relevant insight lives.]

### Alpine Macro
**Posts reviewed:** [date range]
**Articles read in full:** [count]
**Current focus:** [What are they publishing about this week?]
**Key views:**
- [Specific view with date — include reasoning]
- [Another specific view with date]
**Frameworks or data:** [Charts, models, or data. Describe what a chart shows in enough detail that someone who hasn't seen it understands the argument.]

### Cross-Reference with Our Regime Assessment
**Our current regime:** [pull from this week's synthesis]
**Steno alignment:** [Confirms / Diverges / Different topic entirely — explain]
**Alpine alignment:** [Confirms / Diverges / Different topic entirely — explain]
**If both confirm:** Are we accidentally consensus? That reduces contrarian edge.
**If either diverges:** What do they see that we might be missing? Flag for investigation.
**If they disagree with each other:** Which view is more consistent with our data?

### Notable Frameworks or Insights to Track
[Only if something emerges organically. Don't force this section — skip it entirely most weeks. When something genuinely novel surfaces, describe what it is and why it matters. Let the content surprise you.]
```

## Quality Standards

- Every view attributed to a specific post date. No undated claims.
- Full articles must be read when linked — feed headlines alone are insufficient.
- Summarize what they actually said, not what you think they meant or what fits our narrative.
- Include the reasoning behind their conclusions, not just the conclusions. The reasoning is what makes this useful for thesis monitoring.
- If you couldn't access a feed or article (Chrome unavailable, paywall, rate-limited), say so explicitly. Don't fill in from memory.
- Keep the total output focused but thorough. A 3-5 minute read that captures the substance of their analysis.

## Meta Block

```yaml
---
meta:
  skill: analyst-monitor
  skill_version: "1.1"
  run_date: "[ISO date]"
  execution:
    steno_posts_scanned: [number]
    steno_articles_read_full: [number]
    alpine_posts_scanned: [number]
    alpine_articles_read_full: [number]
    steno_freshest_post: "[date]"
    alpine_freshest_post: "[date]"
    chrome_available: [true/false]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```

### Amendment log
- v1.1 (2026-W12): Added "Follow links to full articles" as Step 2. Root cause: feed scan captured headlines but missed substantive analysis in linked articles (e.g., Steno's full Iran/Fed article with phase 1/2 framework, export ban analysis, and Clarida "transitory" quote was invisible to the feed scrape). Expected impact: analyst monitor captures reasoning and data, not just headlines.
