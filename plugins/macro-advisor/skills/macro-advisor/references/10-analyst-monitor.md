# Skill 10: External Analyst Monitor

## Objective

Browse the feeds and publications of external macro analysts and read their actual content — including full articles, not just feed headlines. The system reads with fresh eyes — no pre-loaded expectations about what to find. Whatever they're focused on this week is what gets reported.

Eight analysts are monitored. They vary in publishing frequency — some post daily, others monthly. The skill checks all sources each week but only reports substance when new content exists. "No new content since last check" is a valid output for any individual source.

---

## Sources

### Group A: Frequent Publishers (weekly or more)
These analysts publish frequently enough that there will almost always be new content each week. Scan thoroughly.

#### Andreas Steno Larsen
- **Feed:** https://x.com/AndreasSteno
- **Who:** Macro strategist, runs Steno Research. Publishes on X — mix of short posts and longer-form articles. The articles contain the real analysis (charts, specific data, trade calls, policy interpretation). The short posts are teasers.
- **Access:** Chrome browse X feed → follow article links. Fallback: web search `"Andreas Steno" latest [YEAR]`.
- **What to extract:** Policy interpretation (Fed/ECB reads), positioning calls, phase/timing frameworks, specific data references.

#### Luke Gromen (@LukeGromen)
- **Feed:** https://x.com/LukeGromen
- **Who:** Founder of FFTT, LLC. Macro strategist focused on fiscal dominance, sovereign debt sustainability, energy/dollar intersection, and hard assets (gold, bitcoin). Publishes on X (short posts, threads) and appears frequently on macro podcasts. His X posts are often compressed versions of FFTT research — high signal density per word.
- **Access:** Chrome browse X feed. Fallback: web search `"Luke Gromen" OR "FFTT" latest [YEAR]` — his podcast appearances often surface substantive views.
- **What to extract:** Whatever he's actually saying. Gromen's core lens is fiscal math (sovereign debt sustainability, Fed monetization, hard assets) — when he shifts emphasis within that framework or introduces a new theme, it's a signal. But don't filter for his usual topics — if he's talking about something unexpected, that's more interesting than his tenth fiscal dominance thread this month.

#### Alfonso Peccatiello (The Macro Compass)
- **Feed:** https://themacrocompass.substack.com
- **Who:** Former head of a €20bn investment portfolio. Runs The Macro Compass — macro education, analysis, and positioning. 150k+ subscribers. Publishes newsletters and podcast episodes on Substack.
- **Access:** WebFetch on substack homepage → follow links to recent posts → read full articles. Content is free (no paywall).
- **What to extract:** Whatever he's publishing. Alf is systematic and his frameworks are often directly comparable to our regime model — but capture what he's actually focused on, not just what maps to our categories. If he's exploring a theme we don't track, that's a blind spot signal.

#### MacroVoices Podcast
- **Feed:** https://www.macrovoices.com/podcast-transcripts
- **Who:** Erik Townsend hosts long-form macro interviews with institutional analysts. Full transcripts published free. Guests rotate — the guest's identity IS part of the signal (who's being invited to speak indicates what themes are hot).
- **Access:** WebFetch on transcript page → identify latest 1-2 transcripts → follow links to read full text. Transcripts are long (60+ min conversations) — focus on extracting key arguments, disagreements with consensus, specific data, and positioning.
- **What to extract:** Guest identity and their framework, specific macro calls with reasoning, data or models referenced, disagreements between host and guest. One week might have a gold bug, the next a Fed apologist — capture what's there, not what fits our model. The guest rotation IS part of the signal — who's being invited to speak indicates what themes the macro community considers important.

### Group B: Less Frequent Publishers (bi-weekly to monthly)
These analysts publish less frequently. Check each week, but expect "no new content" some weeks. When they do publish, the content tends to be higher-density and more considered — read carefully.

#### Howard Marks (Oaktree Capital)
- **Feed:** https://www.oaktreecapital.com/insights
- **Who:** Co-chairman of Oaktree Capital. Publishes memos on market cycles, risk, investor psychology. Memos are infrequent (roughly monthly or less) but dense — typically 3,000-8,000 words of reasoned argument about where we are in cycles. Also occasional market commentary from the broader Oaktree team.
- **Access:** WebFetch on `/insights` → check for new memos or commentary → follow link to read full text.
- **What to extract:** Whatever the memo covers. Marks doesn't make short-term calls — his value is the meta-view on cycles, risk, and investor psychology. When he publishes, read the full thing. Don't skim for keywords that match our thesis framework — his memos are arguments that build over thousands of words, and the conclusion often depends on the setup.
- **No new content protocol:** If the most recent memo is the same as last week's check, output: "No new Oaktree content since [date of last memo]. Last memo: '[title]'." Move on.

#### Lyn Alden
- **Feed:** https://www.lynalden.com/[month]-[year]-newsletter/
  - URL pattern: `https://www.lynalden.com/march-2026-newsletter/` (month name in lowercase, 4-digit year)
  - To check for the latest: construct the URL with the current month and year. If 404, try previous month.
- **Who:** Independent macro analyst. Publishes monthly newsletter — typically 5,000-10,000 words covering Fed balance sheet, sovereign debt, commodities, precious metals, and portfolio positioning. Rigorous, data-heavy, non-sensationalist.
- **Access:** WebFetch on constructed URL. Content is free and full-text.
- **What to extract:** Whatever the newsletter covers. Alden's strength is quantified reasoning — capture the numbers and the logic chain, not just the conclusions. She often covers Fed balance sheet, sovereign debt, commodities, and precious metals, but if she's pivoting to a new topic, that pivot is itself a signal worth flagging.
- **No new content protocol:** If the current month's newsletter isn't available yet and last month's was already captured, output: "No new Lyn Alden newsletter since [month]. Awaiting [current month] issue." Move on.

#### Evergreen Gavekal
- **Feed:** https://evergreengavekal.com/blog/
- **Who:** Evergreen Capital (David Hay) + Gavekal Research (Louis-Vincent Gave). Blog posts cover commodities, geopolitics, sector analysis, portfolio construction. Multiple authors — Louis-Vincent Gave's posts carry the most macro weight.
- **Access:** WebFetch on `/blog/` → identify new posts since last check → follow "Read This" links to full articles. Content is free.
- **What to extract:** Whatever they're publishing. Gavekal's China/Asia/commodity expertise is distinctive among our sources — capture that angle when it appears, but don't filter for it exclusively. If David Hay is writing about US credit markets, that's relevant too.
- **No new content protocol:** If all posts on the front page predate last week's check, output: "No new Evergreen Gavekal content since [date]." Move on.

#### Alpine Macro
- **Feed:** https://www.linkedin.com/company/alpine-macro/posts/?feedView=all
- **Who:** Institutional macro research firm. Publishes on LinkedIn — typically excerpts and charts from their research reports with key conclusions.
- **Access:** Chrome browse LinkedIn feed. Fallback: web search `"Alpine Macro" research latest [YEAR]`.
- **What to extract:** Regime assessment frameworks, cross-asset views, charts with specific data. Their institutional lens is a useful counterweight to the more independent voices above.

---

## Execution Steps

### Step 1: Scan all sources for new content

Work through the sources systematically. For each source:

1. **Read the Last Seen table** from `outputs/collection/analyst-themes.md` (the section at the bottom). This tells you the date and title of the most recent content captured for each source last week.
2. **Navigate to the feed/page using the correct access method for that source.** This is not optional — each source specifies its access method:
   - **Chrome browser** (requires login): Steno (X), Gromen (X), Alpine Macro (LinkedIn)
   - **WebFetch** (no login needed): Macro Compass (Substack), MacroVoices (transcript page), Oaktree (insights page), Lyn Alden (constructed URL), Evergreen Gavekal (blog)
   - **Do NOT use web search as a shortcut when the proper access method is available.** Web search is a fallback for when Chrome is unavailable, not a default. WebFetch sources should always use WebFetch directly on the URL — it returns the actual page content, which is far richer than a search result snippet.
3. **Compare against Last Seen.** If the newest content on the page matches (same date and title), there's nothing new. Note it and move on. Don't re-analyze stale content.
4. **If new content exists** (date is newer than Last Seen, or title is different): Proceed to Steps 2-3 for that source.
5. **If Last Seen table is missing** (first run, or analyst-themes.md doesn't exist yet): treat all content as new.

**Efficiency note:** Sources in Group A will almost always have new content. Start there. Group B sources may be quick "no new content" checks on most weeks.

### Step 2: Follow links to full articles

This is the critical step the feed scan alone misses. Analysts post short teasers that link to full articles. The full article is where the real analysis lives.

For each post that appears to link to a longer article, thread, or transcript:
1. Look for links in the post text or use `find` / `read_page` to locate clickable article links
2. Navigate to the full article URL
3. Use `get_page_text` or WebFetch to read the complete article
4. Extract the substantive analysis — specific data points, charts described, trade calls, policy interpretations, frameworks

If a post is self-contained (no link to a longer piece), the feed text is sufficient.

**Why this matters:** A feed scan of Steno's X might show "Iran is firing more and hitting more, while the Fed prepares to invent a new transitory." That's a headline. The linked article contains: a detailed Fed policy analysis (dovish despite inflation revision, Clarida suggesting new "transitory" language), a US energy export ban assessment (strongly recessionary if implemented), a phase 1/phase 2 timing framework (inflation shock now, growth shock in 1-2 months), and specific positioning calls. Missing the article means missing the analysis. The same applies to all sources — follow the links.

### Step 3: For each analyst with new content, extract

For each relevant post or article, note:
- **Date** of the post (critical — undated views are worthless)
- **What they're saying** — the actual analysis, not a headline summary
- **Specific data, charts, or frameworks** they reference — describe charts in enough detail that someone who hasn't seen them understands the argument
- **Their positioning or trade implications** — explicit calls, what they're long/short, any sizing language
- **Policy interpretation** — how they read central bank actions (this is often where the alpha is — two analysts can read the same Fed statement differently)

### Step 4: Cross-reference

Compare analyst views against each other and against our current regime assessment:
- Where do multiple analysts agree? (Potential consensus — reduces contrarian edge)
- Where do they disagree? (One of them is seeing something — flag for investigation)
- What are they focused on that we're not monitoring? (Blind spot check)
- Does any analyst's framework directly challenge or support an active thesis?

### Fallback

If Chrome is not available, fall back to:
- **X feeds (Steno, Gromen):** Web search `"[analyst name]" latest [YEAR]`
- **LinkedIn (Alpine Macro):** Web search `"Alpine Macro" research latest [YEAR]`
- **Direct URLs (Oaktree, Lyn Alden, Evergreen Gavekal, MacroVoices, Macro Compass):** WebFetch works without Chrome

Note in the output that this is a fallback and may miss longer-form content for the social media sources.

---

## How to Read Their Content

**Do not pre-filter for specific topics.** Read what's actually there.

**Follow the links.** The feed surface is advertising. The article is the product. If there's a link, read it.

**Capture the reasoning, not just the conclusion.** "Steno is bullish oil" is useless. "Steno argues the Fed is looking through the oil shock because they prioritize growth over inflation, Clarida suggested they'll redefine 'transitory,' and this means cuts are still in play even at $96 oil — which is dovish relative to market pricing" is useful. The reasoning is what the thesis monitor needs to cross-reference.

**Capture shifts in focus.** If an analyst who was talking about one theme suddenly pivots, that's a signal.

**Note when they disagree with each other.** Eight analysts disagreeing is more useful than eight agreeing. Map the disagreement — who's on which side, and what data supports each view.

**Date everything.** "Steno posted on March 19 that..." not "Steno thinks..."

**Distinguish conviction levels.** A Howard Marks memo arguing something over 5,000 words is a different conviction signal than a Luke Gromen tweet. A Lyn Alden newsletter changing her portfolio allocation is a different signal than her describing a scenario. Note the medium and the weight the analyst is putting behind the view.

---

## Output Format

```markdown
## External Analyst Monitor — [Date]

---
### GROUP A: FREQUENT PUBLISHERS
---

### Andreas Steno (@AndreasSteno)
**Posts reviewed:** [date range of posts scanned]
**Articles read in full:** [count — list URLs if possible]
**Current focus:** [What is he actually talking about this week? 1-2 sentences.]
**Key views:**
- [Specific view with date — include the reasoning, not just the conclusion]
- [Another specific view with date]
**Positioning signals:** [Explicit trade calls, what's he long/short, any sizing. If none: "No explicit positioning this period."]
**Policy interpretation:** [How does he read the Fed/ECB/other CBs?]

### Luke Gromen (@LukeGromen)
**Posts reviewed:** [date range]
**Content read:** [X posts / threads / podcast appearances — list sources]
**Current focus:** [1-2 sentences]
**Key views:**
- [Specific view with date and reasoning]
- [Another specific view with date]
**Fiscal dominance update:** [Any shift in his core fiscal math framework? New data points he's citing? If unchanged: "Core thesis unchanged — still focused on [X]."]
**Positioning signals:** [Explicit calls if any]

### Alfonso Peccatiello — The Macro Compass
**Posts reviewed:** [date range]
**Articles read in full:** [count — list URLs]
**Current focus:** [1-2 sentences]
**Key views:**
- [Specific view with date and reasoning]
- [Another specific view with date]
**Frameworks or models:** [Any systematic frameworks, liquidity models, or cross-asset signals he's using? Describe in enough detail to be actionable.]
**Positioning signals:** [Portfolio moves, allocation shifts, explicit calls]

### MacroVoices Podcast
**Episodes reviewed:** [episode title(s), date(s), guest(s)]
**Transcripts read:** [count]
**Current focus:** [What theme did the guest(s) address?]
**Key views:**
- [Guest name, date: specific view with reasoning]
- [Another view]
**Notable data or frameworks:** [Specific models, charts, or data the guest introduced]
**Host-guest disagreements:** [If any — these are often the most revealing moments]

---
### GROUP B: LESS FREQUENT PUBLISHERS
---

### Howard Marks (Oaktree Capital)
**Status:** [New memo: "[title]" / No new content since [date] — last memo: "[title]"]
[If new content:]
**Published:** [date]
**Theme:** [What is the memo about?]
**Key arguments:**
- [Argument with reasoning — Marks builds cumulative cases, capture the chain of logic]
- [Another argument]
**Cycle positioning:** [Where does Marks think we are in the cycle? Bullish/cautious/defensive?]
**Historical analogies:** [Which periods does he compare to? These inform his forward expectations.]

### Lyn Alden
**Status:** [New newsletter: [month year] / No new content since [month year]]
[If new content:]
**Published:** [date]
**Key topics:**
- [Topic 1 with specific data and reasoning]
- [Topic 2]
**Fed balance sheet:** [Her latest view on direction and magnitude — she tracks this weekly]
**Precious metals / commodities:** [Valuation assessment — is she seeing fair value, overvalued, undervalued?]
**Scenario analysis:** [Baseline vs. tail risk scenarios she describes — include the conditions for each]
**Portfolio changes:** [Any allocation moves mentioned]

### Evergreen Gavekal
**Status:** [New posts since [date]: [count] / No new content since [date]]
[If new content:]
**Posts reviewed:** [titles, dates, authors]
**Key views:**
- [Author name, date: specific view with reasoning]
- [Another view]
**Commodity / geopolitical focus:** [Gavekal's differentiated lens — capture the Asia/commodity/contrarian angle]

### Alpine Macro
**Status:** [New posts since [date]: [count] / No new content since [date]]
[If new content:]
**Posts reviewed:** [date range]
**Articles read in full:** [count]
**Current focus:** [What are they publishing about?]
**Key views:**
- [Specific view with date — include reasoning]
- [Another specific view with date]
**Frameworks or data:** [Charts, models, or data. Describe what a chart shows.]

---
### CROSS-REFERENCE & SYNTHESIS
*This section is for the user reading the briefing. No downstream skill consumes it programmatically. Skill 7 uses the themes index (analyst-themes.md) for thesis cross-referencing, not this section. Write it to inform human judgment, not to feed an algorithm.*
---

### Analyst View Map
**Our current regime:** [pull from this week's synthesis]

Map what each analyst sees FIRST, then compare to our regime SECOND. The point is to understand their view on its own terms, not to score it against ours.

| Analyst | Their current view (1 sentence) | Challenges our model? | What they see that we might not |
|---------|-------------------------------|----------------------|-------------------------------|
| Steno | [what he's actually saying] | [Yes: how / No] | [blind spot or novel angle, if any] |
| Gromen | [what he's actually saying] | [Yes: how / No] | [blind spot or novel angle, if any] |
| Alf (Macro Compass) | [what he's actually saying] | [Yes: how / No] | [blind spot or novel angle, if any] |
| MacroVoices guest | [what they're actually saying] | [Yes: how / No] | [blind spot or novel angle, if any] |
| Marks | [view, or "No new content"] | [Yes: how / No / N/A] | [blind spot or novel angle, if any] |
| Lyn Alden | [view, or "No new content"] | [Yes: how / No / N/A] | [blind spot or novel angle, if any] |
| Evergreen Gavekal | [view, or "No new content"] | [Yes: how / No / N/A] | [blind spot or novel angle, if any] |
| Alpine Macro | [view, or "No new content"] | [Yes: how / No / N/A] | [blind spot or novel angle, if any] |

### Consensus and Contrarian Check
**Where most analysts agree:** [Theme — and what that consensus means for our positioning. If we're aligned with 6/8 analysts, we might BE the consensus, which reduces edge.]
**Where analysts split:** [Theme — map who's on which side. This is often where the opportunity lives.]
**Where our model is an outlier:** [Are we seeing something nobody else sees? That's either insight or error — flag for scrutiny either way.]
**Blind spots:** [What are analysts watching that our system doesn't currently track?]

### Notable Frameworks or Insights to Track
[Only if something emerges organically. Don't force this section — skip it entirely most weeks. When something genuinely novel surfaces, describe what it is and why it matters. Let the content surprise you.]
```

## Step 5: Update Analyst Themes Index

After writing the weekly analyst monitor output, update `outputs/collection/analyst-themes.md`. This file is **overwritten each week** (not appended). It is a lightweight pointer that tells downstream skills what analysts are currently focused on and where to find the detail.

```markdown
## Analyst Themes (updated YYYY-Www)

### Andreas Steno
**Current focus:** [2-3 themes, comma-separated]
**Weeks on theme:** [For each theme, consecutive week count. Check prior week's analyst-themes.md. New theme = 1.]
**Strongest current view:** [One sentence — highest-conviction call this week, with direction]
**Detail:** `outputs/collection/YYYY-Www-analyst-monitor.md`

### Luke Gromen
**Current focus:** [2-3 themes]
**Weeks on theme:** [consecutive week count per theme]
**Strongest current view:** [One sentence]
**Detail:** `outputs/collection/YYYY-Www-analyst-monitor.md`

### Alfonso Peccatiello (Macro Compass)
**Current focus:** [2-3 themes]
**Weeks on theme:** [consecutive week count per theme]
**Strongest current view:** [One sentence]
**Detail:** `outputs/collection/YYYY-Www-analyst-monitor.md`

### MacroVoices
**Current focus:** [2-3 themes — attribute to guest name]
**Weeks on theme:** [consecutive week count per theme]
**Strongest current view:** [One sentence — attribute to guest]
**Detail:** `outputs/collection/YYYY-Www-analyst-monitor.md`

### Howard Marks (Oaktree)
**Current focus:** [2-3 themes, or "No new content — last published [date]"]
**Weeks on theme:** [consecutive week count, or N/A]
**Strongest current view:** [One sentence if new content. If no new content, carry forward with: "(From [date] memo — not refreshed, [N] weeks old)". Macro cycle views age slowly — a Marks memo on cycle positioning is relevant for months. The view stays until he publishes something that supersedes it.]
**Detail:** `outputs/collection/YYYY-Www-analyst-monitor.md`

### Lyn Alden
**Current focus:** [2-3 themes, or "No new content — last newsletter [month year]"]
**Weeks on theme:** [consecutive week count, or N/A]
**Strongest current view:** [One sentence if new content. If no new content, carry forward with: "(From [month] newsletter — not refreshed, [N] weeks old)". Her structural analyses (Fed balance sheet, sovereign debt) remain relevant across multiple months. The view stays until a newer newsletter supersedes it.]
**Detail:** `outputs/collection/YYYY-Www-analyst-monitor.md`

### Evergreen Gavekal
**Current focus:** [2-3 themes, or "No new content since [date]"]
**Weeks on theme:** [consecutive week count, or N/A]
**Strongest current view:** [One sentence]
**Detail:** `outputs/collection/YYYY-Www-analyst-monitor.md`

### Alpine Macro
**Current focus:** [2-3 themes, or "No new content since [date]"]
**Weeks on theme:** [consecutive week count, or N/A]
**Strongest current view:** [One sentence]
**Detail:** `outputs/collection/YYYY-Www-analyst-monitor.md`

### Theme Persistence
[List any theme that has appeared for 3+ consecutive weeks from ANY analyst. These are the themes worth cross-referencing against active theses — persistent analyst focus suggests the theme has legs, not noise.]

### Cross-Analyst Convergence
[List any theme that 3+ analysts are simultaneously focused on this week. Convergence across independent analysts is a stronger signal than persistence from one. But also note: if everyone sees the same thing, the market probably does too — flag the consensus risk.

**Sampling bias check:** Our analyst panel has structural overlaps. Gromen, Lyn Alden, and Gavekal share views on sovereign debt, fiscal dominance, and hard assets. Steno and Alf both focus on central bank policy. When counting convergence, note whether the agreeing analysts are genuinely independent voices or share a common intellectual framework. "3 analysts agree on fiscal dominance" means less if those 3 are Gromen, Alden, and Gavekal — that's one school of thought, not three independent signals.]

### Last Seen (for new-content detection)
Used by Step 1 next week to determine what's already been covered. Overwritten each run.
| Source | Freshest content date | Title/identifier |
|--------|----------------------|-----------------|
| Steno | [date of newest post scanned] | [post topic or URL] |
| Gromen | [date] | [post topic or URL] |
| Macro Compass | [date] | [article title] |
| MacroVoices | [date] | [episode title + guest] |
| Oaktree | [date] | [memo title] |
| Lyn Alden | [month year] | [newsletter month] |
| Evergreen Gavekal | [date] | [post title] |
| Alpine Macro | [date] | [post topic] |
```

This file exists so Skill 7 can quickly scan what analysts are watching without reading every weekly file. When a theme is relevant to a thesis, Skill 7 follows the `Detail` link back to the full weekly output for the substance.

**Why overwrite instead of append:** Old analyst themes become stale. If Steno was focused on oil in W10 but has moved to credit by W14, the W10 oil focus shouldn't sit alongside the W14 credit focus as if both are current. The "Weeks on theme" counter preserves continuity — if he's been on credit for 3 weeks, that's visible. But the file only shows what's current.

---

## Quality Standards

- Every view attributed to a specific post date. No undated claims.
- Full articles must be read when linked — feed headlines alone are insufficient.
- Summarize what they actually said, not what you think they meant or what fits our narrative.
- Include the reasoning behind their conclusions, not just the conclusions. The reasoning is what makes this useful for thesis monitoring.
- If you couldn't access a feed or article (Chrome unavailable, paywall, rate-limited), say so explicitly. Don't fill in from memory.
- **No new content is a valid output.** Do not pad a source section with old analysis to fill space. If Howard Marks hasn't published since last month, say so in one line and move on.
- Keep individual analyst sections focused. The total output will be longer with 8 sources, but each section should still be dense — reasoning and data, not filler.
- The Cross-Reference & Synthesis section is where the real value lives. Individual analyst sections are inputs; the synthesis is the output that matters for downstream skills.

## Meta Block

```yaml
---
meta:
  skill: analyst-monitor
  skill_version: "2.0"
  run_date: "[ISO date]"
  execution:
    sources_checked: 8
    sources_with_new_content: [number]
    # Group A
    steno_posts_scanned: [number]
    steno_articles_read_full: [number]
    steno_freshest_post: "[date]"
    gromen_posts_scanned: [number]
    gromen_articles_read_full: [number]
    gromen_freshest_post: "[date]"
    macrocompass_posts_scanned: [number]
    macrocompass_articles_read_full: [number]
    macrocompass_freshest_post: "[date]"
    macrovoices_transcripts_read: [number]
    macrovoices_freshest_episode: "[date]"
    # Group B
    oaktree_new_content: [true/false]
    oaktree_freshest_post: "[date]"
    lynalden_new_content: [true/false]
    lynalden_freshest_newsletter: "[month year]"
    evergreen_posts_scanned: [number]
    evergreen_freshest_post: "[date]"
    alpine_posts_scanned: [number]
    alpine_articles_read_full: [number]
    alpine_freshest_post: "[date]"
    chrome_available: [true/false]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues — access failures, paywalls hit, fallback methods used]"
---
```

### Amendment log
- v1.1 (2026-W12): Added "Follow links to full articles" as Step 2. Root cause: feed scan captured headlines but missed substantive analysis in linked articles (e.g., Steno's full Iran/Fed article with phase 1/2 framework, export ban analysis, and Clarida "transitory" quote was invisible to the feed scrape). Expected impact: analyst monitor captures reasoning and data, not just headlines.
- v2.0 (2026-W13): Expanded from 2 analysts to 8. Added: Howard Marks/Oaktree Capital (memos on cycles/risk), MacroVoices (weekly podcast transcripts), Evergreen Gavekal (commodity/geopolitical blog), Lyn Alden (monthly newsletter — Fed balance sheet, sovereign debt, precious metals), Luke Gromen/FFTT (fiscal dominance, hard assets — X feed), The Macro Compass/Alfonso Peccatiello (cross-asset frameworks — Substack). Grouped into frequent (Group A: Steno, Gromen, Alf, MacroVoices) and less frequent (Group B: Marks, Lyn Alden, Evergreen Gavekal, Alpine Macro) with explicit "no new content" protocol for Group B. Added alignment map table and Cross-Analyst Convergence to themes index. Rationale: broader analyst coverage reduces blind spots and provides more cross-reference surface for thesis monitoring.
