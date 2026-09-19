# Productivity

Four skills: three that do the work every weekday, one that schedules them.

## Install and start

Install the plugin, then run **`/productivity:onboarding`**. Plain English works too — "onboard me" reaches the same skill — but the namespaced command is the one to put in setup instructions, because it hits the right skill first time.

Every skill is namespaced the same way:

| Skill | Command |
|---|---|
| Onboarding — run first | `/productivity:onboarding` |
| Call Prep | `/productivity:call-prep` |
| Daily Brief | `/productivity:daily-brief` |
| Follow-Ups | `/productivity:follow-ups` |

**If you skip that and just run a skill, it will notice.** The first time you invoke one by hand with no task for it, that skill offers to schedule **itself** — one click, before it starts work — then does the job you asked for either way. It checks and schedules only the skill you ran; the other two are left alone until you try them. Once a task exists the check is silent and never mentioned again. So nobody ends up with a plugin that only runs when they remember to ask.

**It preflights first, in three tiers.** Before creating anything it checks — reading none of your data, only what is available — which connector roles are present and whether the renderer's Python packages are installed.

- **One hard blocker:** no scheduling tool. There is nothing to create a task with, so it stops.
- **A minimum set it offers to connect: one mail connector (Gmail or Outlook), one calendar, one chat.** Where one is missing it **suggests the connector itself** — a prompt you can act on in place, rather than an instruction to go and find it — then asks in one card what to do next: you connected them just now, continue anyway, or stop and come back. Only if the registry has nothing, or the suggestion fails, does it fall back to telling you in words. Nothing is created until you answer.
- **Recommended, reported not asked:** a tracker (Jira, GitHub, Linear, Asana), call transcripts, CRM. The tracker gets the one extra question on that same card, because it is the only gap nothing else compensates for — without it, **undated open work goes unreported entirely.**

Whatever you choose, the gaps are repeated in the setup summary so the decision is on the record, and **every gap closes itself**: connect the tool later and the next scheduled run picks it up, with no need to re-onboard.

**It never asks what timezone you are in.** It reads it from your machine and schedules in your own local time — 6 AM means 6 AM where you are, not 6 AM UTC converted into your afternoon.

It then creates all three recurring tasks in one pass — no questions about days or times — removes every task left behind by the predecessor plugin so nothing double-sends, and finishes with the click-by-click steps for setting Permissions to automatic, **then asks whether you have done it.** That one question is the point of the instructions: left on *Manually approve*, every unattended run halts on a prompt nobody is there to click, and you find out days later by noticing nothing ever arrived.

**One thing onboarding cannot do, and does not claim to:** pre-authorise your connectors. An approval prompt only appears when a tool is actually called, so triggering one would mean reading your mail and calendar during setup. The real fix is the Permissions setting it walks you through. Running each skill once by hand while you watch is worth doing too, but as a confidence check rather than a substitute — it tells you the connectors work, not that an unattended 6 AM run will be allowed to use them.

It also has a **single-skill mode**, used when you ask for one skill by name or when a skill schedules itself. That mode touches exactly one task and cleans up only that skill's legacy task — so if you came from the predecessor and adopt one skill at a time, the other two old tasks keep firing until you get to them. Running "onboard me" once clears the lot. On the hand-off path it skips the preflight, since the skill that sent it there is already running and its connectors evidently work.

## What runs, when

| Skill | Cadence | Local time | Delivered as |
|---|---|---|---|
| Daily Brief | Weekdays Mon–Fri | 6:00 AM | One email, PDF attached |
| Call Prep | Weekdays Mon–Fri | 7:00 AM | A private prep block before each call |
| Follow-Ups | Weekdays Mon–Fri | 4:00 PM | One email, plus drafts in your Drafts folder |

**The schedule is Monday to Friday — nothing fires by itself at the weekend.** Enforced twice: the cron day field is fixed at `1-5`, and each skill independently checks the weekday before doing any work **on a scheduled run**. Call Prep preps today's calls from its 4 AM run, so it needs only today's weekday — the same check every skill makes.

**A first manual run offers to schedule that one skill.** Invoke a skill by hand with no task for it and it asks once, before starting work — schedule this skill, or not now — then runs regardless of the answer. With a task already in place the check is completely silent.

**Scope is deliberately narrow: it checks the invoked skill and schedules the invoked skill.** Someone who ran Daily Brief asked about Daily Brief; signing them up for two skills they have not tried would bury the decision they actually care about. Each skill makes its own offer if and when it gets run, and a "not now" is remembered for that skill only.

A yes hands off to `onboarding` in its **single-skill mode**. **No worker skill ever writes a scheduled task itself** — only onboarding's prompts carry the version stamp and the marker that identifies a run as scheduled, so a task written anywhere else would fire, be mistaken for a manual run, and skip the weekend guard. One writer, one definition of the schedule.

**On demand, all three run any day, weekend included.** The weekend rule keeps unattended automation quiet; it never refuses a person who asks. A manual Call Prep run also picks its own target day — today if calls remain ahead of the clock, otherwise the soonest day in the next seven that has one, so asking on Friday evening preps Monday.

## The three

**Daily Brief** — every meeting, every open ask, everything due, plus real scheduling-conflict calls with a suggested fix. Every actionable item names what to do, who owns it, and by when. Pending items must trace to a real message, ticket or event where the user was actually named or assigned — never invented from a nearby mention — and the brief closes with a Sources list citing exactly where each claim came from. One PDF by email before the day starts. Clear day → three lines, no PDF.

**Follow-Ups** — finds who has gone quiet, whose next step is overdue, and what you promised. Guarantees the last 10 calendar days of sent mail, inbox and chat are read to full pagination with zero gaps, regardless of how long that takes. Defaults to drafting: it withholds a draft only for a concrete problem — a bounce, an unresolvable address, a genuinely ambiguous thread — never merely because a source was partially read. Ranks by priority and writes the drafts **in your voice**: it samples your recent sent mail for greeting, sign-off, length, rhythm and stock phrases, copies your exact signature block verbatim, mirrors the register you use with that particular recipient, and bans the usual AI tells. Every draft is a reply on its real thread — including a reply to your own last sent message when you're chasing silence. No PDF, no attachment: a plain-text summary email plus the drafts themselves is the whole deliverable. **Drafts only — it never sends.**

**Call Prep** — runs at 4 AM and **books a private 10-minute prep block before each external call today**. That block is the deliverable, not an email: it holds 09:50–10:00 for a 10 AM call, reminds you at 09:45, and carries a **fact card under 200 words** in the invite body — 120 is the target — with the full dossier linked as a PDF.

The reason is the whole point of the skill. A brief that lives in an inbox is one you have to remember to go and read, and under time pressure nobody does. The calendar reminder arrives while you are between things and about to need it. **A clean run sends no email at all** — it emails only when something failed, and then with the exact error.

The briefing behind the card is **one or two pages**, in a fixed order that answers eight questions: why this call is happening, who is on it and why each person matters, what you need to know, what you should accomplish, what to ask, what could go wrong, who owes what, and where it all came from. Commitments land in a single **Actions & owners** table with a named owner on every row.

It mines **past meeting transcripts** where a call-intelligence connector is available, so it knows what was actually promised, what objections came up, and the words the other side used for their own problem. It also looks 30 days *forward* — a call three days before a renewal is a different call.

**Times come from the event record, converted to your timezone, and carry the weekday and date** — `Mon 14 Sep · 12:00 – 12:45 pm`, not a bare clock range. Duration is computed from start and end rather than taken from the title, a recurring meeting uses *this* occurrence's time, and an all-day event says "All day" instead of being given an invented one. A brief with the wrong time is worse than no brief: someone reads 12:00 and misses a 12:30 call.

### How Call Prep decides what's external

This is the part that matters most, because a missed client call is the worst thing this skill can do.

**One test, domain only.** A meeting is external if and only if at least one attendee or the organizer has an address outside your own domain set. That's the whole rule — nothing else gets a vote.

None of these may ever promote a meeting to external on their own: the title (a company name, "sync", "demo", "client", "internal", "kickoff"), the conferencing link's tenant, or a CRM match on subject matter. That list exists because an earlier version fired on title text and briefed two internal syncs as external calls, even though every attendee on both was on the user's own domain. A meeting held *about* an external account is not itself an external meeting — only the people actually on the invite decide that.

The one exception is a genuine data gap: if attendee addresses can't be retrieved at all, that's briefed and flagged as a gap, never silently skipped and never decided by the title. There is no cap — every meeting the domain test marks external gets its own brief. Busy days reduce research depth, never the number of briefs, and the depth trigger counts **companies**, because that is the unit research is actually spent on.

## Delivery

**Every run reaches you exactly once, through its own channel.** For the Daily Brief and Follow-Ups that channel is email, and it is unconditional: empty results, thin days and rendering failures all still send, and a run that goes silent is a failed run. **Call Prep's channel is your calendar** — the prep blocks are the delivery, so a clean run is deliberately silent in your inbox and emails only when something broke, with the exact error. The only run that reaches you through no channel at all is a **scheduled** weekend run, which exits before doing any work. A manual weekend run delivers like any other — it was asked for.

**The Daily Brief attaches a PDF.** Never Word or HTML. Where the mail tool can't attach, the PDF uploads to a per-skill `Skills/` folder on your drive and arrives as a link with the content inline as well. If PDF generation fails after the format gate, the markdown backup is attached in its place — because the email still goes, and never with a silently missing attachment. **Call Prep's briefings are uploaded to your drive and linked from each prep block**; its one possible email, the failure report, attaches nothing.

**Follow-Ups never attaches anything, by design.** No PDF, no markdown file — the summary email is composed directly as plain text, and the drafts sitting in your Drafts folder are the actual deliverable. This also means it can't be knocked out by a renderer or sandbox outage the way an attachment-based run can.

Every skill emails **only the signed-in user** — no cc, no bcc, never a meeting attendee or customer.

## How the plugin is put together

```
.claude-plugin/plugin.json
references/shared-run-policy.md      ← the policy all three skills share
references/positioning-notes.md      ← optional, org-specific (Call Prep)
assets/pdf.py                 ← the only PDF renderer + the accuracy gate
skills/onboarding/
skills/daily-brief/
skills/follow-ups/
skills/call-prep/
```

**`references/shared-run-policy.md` is the single source of truth** for the weekday guard, rate-limit backoff, the status taxonomy and its cross-channel verification rule, mailbox resolution, the delivery contract, the connector table, the renderer's exit codes, the universal ground rules, and the writing rules that keep every output crisp and specific. Each skill reads it first and then states only what is specific to itself. In the predecessor plugin those policies were restated in six places — each of the three skills and each of the three generated task prompts — which is how one shipped with a rule the skill had already retired.

## After a plugin update

**Run `/productivity:onboarding` again.** It regenerates all three prompts, refreshes the version stamp, and overwrites the existing tasks in place — same task IDs, so your schedules, run history and stored tool approvals survive. It's safe to run as often as you like.

Why that matters less here than it usually would: a scheduled task stores a **copy** of its prompt, and updating the plugin does not update that copy. The prompts this plugin generates are deliberately thin — a version stamp, the skill-resolution preamble, the run parameters, a four-line safety floor, and one line handing the full run contract back to the skill. Everything substantive lives in the skill files, which *are* plugin content and so update immediately. A plugin update now reaches a live schedule on its own; re-onboarding just refreshes the stamp.

## One-time setup

Onboarding creates the tasks. One setting on each is only reachable in the interface, and no tool can set it. For **Daily Brief**, **Follow-Ups** and **Call Prep** in turn:

1. Go to **Scheduled** in the sidebar.
2. Locate the skill and click **Edit**.
3. Click **Edit** again to open the schedule settings.
4. Under **Permissions**, change **Manually approve** to **Automatically approve**.
5. Click **Save**.

Left on **Manually approve**, every run stops waiting for you to click through connector prompts — nobody clicks at 6 AM, so the run never finishes.

If you also want runs to fire while your machine is asleep, turn off *Only on this computer* under Advanced; a cloud-run task can only reach connectors Claude hosts, so leave it on for anything that depends on something local.

## Built for speed, except where depth wins

Daily Brief and Follow-Ups issue their independent reads in parallel rather than as a sequential chain, and each has a cheap early exit for the common empty case. Parallel batches are chunked to the Graph concurrency cap below.

| Skill | Call budget | Stop gathering | Absolute ceiling |
|---|---|---|---|
| Daily Brief | ~30 (15 in the gathering phase) | T+13 min | T+18 min |
| Follow-Ups | ~60 | T+18 min | T+23 min * |
| Call Prep | ~70 | T+16 min | T+25 min |

**The time budgets are sized for chunked batches; the call budgets are the full ones.** That is the Graph concurrency cap doing what it is meant to: the same number of reads, travelling in more messages. Nothing was trimmed to win the minutes back.

\* Follow-Ups' 10-day zero-gap coverage floor is the one documented override of a ceiling in the whole plugin. When the floor overruns, the email goes the moment the floor completes — the override buys coverage, never silence.

Call Prep is deliberately the slow one. It still batches everything in parallel, but it trades minutes for depth, because a brief you can walk into a meeting with is worth more than a fast one. Its research unit is the **company**, not the meeting — three meetings with one account is one research pass, not three.

## How the PDFs are built

All PDFs render through one tested renderer, `assets/pdf.py`. Skills emit a JSON payload; the renderer owns every bit of layout — page size, margins, palette, the timeline graphic, Call Prep's two-column reading grid, item grouping, and the "Page X of Y" footer.

This replaced hand-written rendering, which shipped a real brief with a corrupt page-1 content stream: the timeline lost its dots, the "Today's meetings" heading disappeared, page 1 sat two-thirds empty with no footer, and the meeting list resumed mid-way down page 2.

The renderer is hardened against exactly that. Content streams are uncompressed, so there is no compressed block to corrupt. Every computed coordinate is rounded, so a value can never reach the file in scientific notation and be misread as a garbage operator. Custom drawing brackets its graphics state. Gathered text is escaped as data.

Then it checks its own work before the file is handed over, and refuses to exit clean unless every page's content stream decodes, no coordinate is malformed, the graphics state is balanced, every page carries its footer, and, where `pypdfium2` is installed and the document runs to three or more pages, no page is left mostly empty while later pages carry content. A skill trusts the exit code — it never has to render pages to images and squint at them. Page ceilings are enforced there too — **2 pages for both documents.** Over it, the renderer rejects the job, deletes the oversized file so nothing stale can be attached, and names what to cut in priority order. It never answers a page overrun by shrinking type, and never pads with a blank page. A briefing that only just spilled onto a near-empty second page is pulled back onto one. The payload is checked against each output's documented format before rendering, so a dropped section or a brief with no objective fails loudly instead of producing a plausible-looking but incomplete document. A missing `reportlab` now reports itself as a dependency error with the install command, rather than as an unhandled traceback.

The same pass runs the **accuracy gate**: a status outside the vocabulary, a Completed claim with no trace, an unaccountable actionable item or an owner of "you" fails the render outright, while softer defects print as `ACCURACY WARNING` lines without costing the document. These were all rules the skills asked for in prose and nothing checked.

Every render that gets past the format gate also writes a plain-text markdown copy next to the PDF — automatic, and written before the PDF itself, so a rendering failure still leaves the content on disk. A payload rejected at exit 6 produces neither: there is no verified content yet to back up. It exists for the one failure mode the renderer's own checks cannot see: a clean, verified PDF that never reaches the user because a mail tool silently drops the attachment.

Where a run produces several PDFs — a Call Prep morning with a dossier per call — they are all rendered in **one** process via batch mode. Loading the PDF library costs about half a second, so eight separate invocations paid it eight times; batching five briefs measured 0.47s against 1.87s.

## Connectors

**Three connectors are mandatory, plugin-wide: Calendar, Email and Drive/SharePoint.** Chat is optional. Everything else — CRM, ticketing, meeting transcripts, web search — is detected and used where present, skipped silently where not.

| Connector | Requirement | Used for |
|---|---|---|
| Calendar | **Mandatory** | Meetings, conflicts, Call Prep's prep blocks |
| Email | **Mandatory** | The delivery channel, and the largest single source |
| Drive / SharePoint | **Mandatory** | Where rendered documents live and are linked from |
| Chat | Optional | Where a large share of real asks live |

**The gate is plugin-wide and no skill can bypass it.** `references/connector-prerequisite.md` is a single shared prerequisite every skill runs *first* — ahead of the clock, the weekday guard and any data access. If Calendar, Email or Drive is missing or unusable, the skill shows a connector card and **stops with no output**: no PDF, no email, no drafts, no partial brief. Each skill's SKILL.md carries one line pointing at that file and restates none of its logic, so the rule cannot drift between skills, and a skill added later inherits it by calling it.

**Present is not the same as usable.** The gate probes each mandatory role with the cheapest read its provider offers, and distinguishes five states: not connected, expired, permission revoked, temporarily unavailable, and usable. The first three block and offer **Reconnect**; a 429 or 5xx does not block, because that is a working connector having a bad minute — rate limits are already handled. Nothing is cached between runs: a connector revoked at 5 AM is caught by the 6 AM run rather than assumed good.

**A blocked scheduled run emails once, not daily.** The first one sends a `[Blocked]` note naming the missing role; later runs stay silent while it is still missing and log the reason. When it comes back the next run just works.

Vendor is never hardcoded: roles are matched by tool-name prefix, so Google and Microsoft stacks are equally first-class.

## The PDF design system

Both documents are **1–2 page executive briefings**, and length is controlled by cutting content, never by shrinking type. The test applied to every line: *if it doesn't help the reader prepare, decide, ask, act or follow up, it doesn't belong.*

**Call Prep** answers eight questions in the order a person needs them — why this call is happening, who is on it, what to know, what to accomplish, what to ask, what could go wrong, who owes what, and where it all came from. A glance strip carries the basics once. Attendees get a real table with a line each on why they matter. Commitments land in one **Actions & owners** table, and the renderer **rejects an action with no named owner** — an unowned action reads as a commitment while committing nobody. Headings are second-person: *What you should accomplish*, *Questions you should ask*, *What you need to know before the call*.

**Ceilings are enforced, not requested.** At most 4 *what you need to know* bullets, 3 *risks*, 4–6 questions, one 20-word line per attendee. Over any of them is a hard failure that names what to cut. The Daily Brief has a 2-page ceiling for the first time — on a busy day it simply used to grow.

**Colour carries meaning or is not used.** Blue for context and links, green for actions, amber for risk, red for critical, grey for metadata. Both documents share one grid, one type scale and one set of compact components — a label/value strip, a banded table, a one-line semantic bullet — so the mechanical half cannot drift between them.

**Sources are descriptive labels that are themselves the link.** The Daily Brief used to print the label *and* the raw URL beside it, which spent a line on something nobody reads. A malformed or non-http URL is now dropped to plain text rather than rendered as a dead link, and a URL is never invented.

## Release notes — v1.0.0

First release of Productivity. It is not a first draft: the plugin descends from an internal predecessor whose rules were rewritten across roughly fourteen rounds of production incidents and client feedback, and everything below either carries that behaviour forward or fixes something found while consolidating it. Version numbering starts fresh here because the plugin, the skills and the renderer are all renamed.

### What shipped

**Three weekday skills and a scheduler.** Call Prep at 4 AM, Daily Brief at 6 AM, Follow-Ups at 4 PM, scheduled Monday to Friday, enforced both in the cron day field and independently inside each skill — while a manual invocation runs any day, because the weekend rule is about unattended automation, not about refusing someone who asks. `onboarding` creates all three in one pass and removes any task left by the predecessor so nothing double-sends.

**A Graph concurrency cap of 3.** Microsoft Graph throttles on concurrency, not only on volume, and its documented limit for Outlook resources is four concurrent requests per mailbox — so a batch of seven reads fired at once loses the overflow to HTTP 429 before any backoff policy gets a say. Every parallel batch is chunked into groups of **at most 3** Graph-backed calls: three rather than four, so there is a slot spare for the person's own Outlook client or a retry landing mid-batch. It covers the Daily Brief's seven-read batch and six-thread read, Follow-Ups' Rule 1 batch and draft creation, and Call Prep's own-domain, attendee-resolution, history-lookup and block-booking batches. Nothing else is capped — Gmail, Slack, Jira, Salesforce and web search have no such limit. The time budgets are sized for the extra round trips; **no coverage, volume or call-count cap was reduced to win the minutes back.**

**The cap's known limit, stated rather than buried:** it bounds concurrency *within* one run and cannot coordinate across runs. Installing two brand packages side by side, or scheduling a separate five-skill assistant set against the same mailbox, puts two runs in one slot and doubles the concurrent load. Stagger them by hand, or run one package per mailbox.

**Call Prep runs at 4 AM, and that has a cost worth knowing.** Every call of the day has its prep block booked hours before anyone needs it, and the run sits two hours clear of the 6 AM Daily Brief on the same mailbox. But the day's calendar is read about four hours before the working day starts, so **a meeting added after the run gets no prep block** — a same-morning invite is the case this misses. Run the skill by hand for those; a manual run preps today's remaining calls on demand, any day.

**One shared policy file.** `references/shared-run-policy.md` is the single source of truth for the weekday guard, rate-limit backoff, the status taxonomy and its cross-channel verification rule, mailbox resolution, the delivery contract, the connector table, the renderer's exit codes, the universal ground rules, the writing rules, and the first-manual-run scheduling offer. In the predecessor each of those lived in six places — the three skills plus the three scheduled-task prompts — so every fix had to land six times and one always got missed. One shipped with a rule its own skill had already retired.

**Thin scheduled-task prompts.** A scheduled task stores a *copy* of its prompt, and updating a plugin does not update that copy. The predecessor worked around this by baking every policy detail into a ~700-word prompt per task, which created the drift it was trying to prevent. Each prompt here is about 350 words — a version stamp, the skill-resolution preamble, the run parameters, a four-line safety floor, and one line handing the run contract back to the skill. A plugin update now reaches a live schedule without re-onboarding.

**Call Prep reads like a briefing.** The brief sets on a two-column grid: a narrow gutter for the label and source citation, a 4.95in reading column (about 74 characters) for substance. The predecessor set body text across the full 6.7in measure at 10pt — over 100 characters a line, well past the 65–75 that reads comfortably — with an italic grey citation under every claim. Those two things, not the amount of content, are what made a complete brief feel like a wall. Body text is near-black rather than grey, leading is 15pt, every section opens with a hairline rule, and discovery questions are numbered so you can say "let me come back to three" on a live call.

**Writing discipline, with the limits checked.** Every Call Prep field has a hard word and sentence limit (attendee stake 1 sentence / 25 words; one line per attendee at 20 words; each *what you need to know* and *risk* bullet 28; each action 22; the objective 25 and the desired outcome 22). The universal half — specific over general, front-load the verb, one fact per line, a date on anything that moved, and banned lists for hedges, throat-clearing openers, corporate filler and meta-commentary — is shared §9, so the daily brief and follow-up summary get it too. A hedge is allowed only when the uncertainty is the point, and then it is a **status**, not an adverb.

**An accuracy gate in the renderer, not a request in prose.** `assets/pdf.py` validates the payload in two tiers.

*Hard — exit 6, fix and re-render:* a status outside the six-word vocabulary · `Completed` with no `source` · a Daily Brief actionable item missing `action`, `owner`, `by_when` or `status` · an owner that names nobody ("you", "team", "TBD") · fewer than 4 or more than 6 discovery questions · a field well past its word limit.

*Warn — printed, exit unchanged:* a `related_to` matching no question or discussion point · a citation carrying a specific identifier that appears nowhere in `sources` · placeholder text. These warn rather than fail because losing a whole brief to protect a footnote is the wrong trade — but a defect that only prints is a defect that ships, so shared §8 tells every skill to read the warning lines.

*One documented exemption:* a coverage note is a statement about the run, not a task. "Chat asks were not swept this run" has no owner and no deadline, and inventing one to satisfy the gate would be fabrication, so such items pass `"informational": true`, which exempts them from action, owner, by-when and status alike. Nothing else is exempt.

**Run mode decides the weekend rule, and a direct run offers to schedule itself.** Two behaviours that only exist because an early build got them wrong:

- The weekend guard originally applied "however the run started… not overridable, not even on explicit request." So typing `/call-prep` on a Friday evening produced a refusal and an explanation of the schedule. **The guard now covers scheduled runs only** — it exists to keep unattended automation quiet, not to turn down someone who asked. A manual run works any day.
- A manual Call Prep run with nothing named preps **today**, if today still has calls ahead of the current time; otherwise it looks forward up to 7 days and preps **the next day that has an external call**, saying which — so asking on a Friday evening preps Monday. Name a meeting, an account or a day and it preps that instead, in the same single calendar call.
- A person who never ran onboarding used to get one-off runs forever. **The first manual run of a skill with no task for it now offers to schedule that skill**, once, before starting work, and runs either way — checking and creating only the skill invoked, never all three. A yes invokes `onboarding` in single-skill mode; **no worker skill writes a task itself.** That is a correctness rule, not tidiness: only onboarding's prompts carry the version stamp and the marker that identifies a run as scheduled, and a task written without them would fire, be treated as manual, skip the weekend guard, and offer to schedule itself again.

**One house format, and the renderer owns the half that can drift.** Both PDFs now share a single layout system — masthead, a strip of counts or account snapshot, then a reading grid whose narrow gutter carries labels and citations and whose ~74-character column carries only substance, with hairline-ruled section headings that travel with their first item. Before this, Daily Brief set its body across the full 6.7in measure with orange headings while Call Prep used the grid and quiet ones: two visual languages from one plugin, arriving in the same inbox on the same day. Shared §11 writes the standard down — the document anatomy, the email shape each skill follows, and a table stating exactly which parts the renderer enforces and which are the skill's to hold.

**A cross-channel rule is worthless unless the run reads the other channel.** The Daily Brief reported `[OPEN] End-to-end recording for Ted — none of the three has posted one` when the user had already emailed it to the person who asked. The rule requiring a cross-channel check had been in place for releases; the problem was the data. That skill's gathering batch read the inbox, chat, the due sweep and tickets — and **never the user's own sent mail**, so the evidence was not merely overlooked, it was never fetched. Follow-Ups reads sent mail thirteen times over; Daily Brief not once.

The batch now includes a seventh read: the user's own sent mail and sent chat, last seven days, matched on **the person and the subject matter rather than the channel the ask arrived on**. Where that read fails, an otherwise-Open item is *Needs confirmation* and says so, because reporting Open while blind to your own actions is asserting something unchecked. Shared §4 promotes this to the **first** cross-channel check for every skill, and adds the rule the same item broke twice: a jointly-addressed ask is resolved when **any** of the named people does it, and "none of the three has" may not be written unless the run actually looked for all three.

### Why the rules look the way they do

Most of the stranger-looking rules are scar tissue. Kept here because a rule whose reason is invisible is a rule someone eventually "simplifies".

- **Call Prep classifies external by attendee domain and nothing else.** An earlier version also fired on the meeting *title*, and briefed two entirely internal syncs as client calls because a customer's name sat in the title. A meeting held *about* an account is not a meeting *with* it.
- **Follow-Ups guarantees the last 10 calendar days with zero gaps.** Real follow-ups were missed because a search returned a continuation token and only page one was ever read. The search looked complete and wasn't.
- **Follow-Ups drafts by default.** A live run produced zero drafts against a dozen real candidates, because a rate limit mid-run meant "no reply has already arrived" couldn't be confirmed. An unsent draft costs one click to discard; a follow-up that was never drafted can cost a relationship.
- **An unsent draft never suppresses an item.** A user was told "nothing needs a follow-up" while two written follow-ups sat unsent for five days.
- **Replying to your own last sent message is normal.** A run refused to draft because "they haven't replied yet" — for precisely the case the skill exists to handle.
- **A stamped delivery address wins outright.** A summary landed in a same-domain colleague's mailbox, because both addresses passed the "corporate domain" test.
- **Rate limits are retried, never reported.** A 429 answers promptly, so it gets four minutes of backoff per source; and the user is told the effect ("chat could not be checked"), never the cause.
- **No more than three Microsoft calls are ever in flight at once.** Runs on Outlook were hitting HTTP 429 mid-gather. Microsoft Graph throttles on *concurrency*, not only on volume, and its documented limit for Outlook resources is **four concurrent requests per mailbox** — so a batch of seven reads fired all at once loses three of them to 429 before the backoff policy above ever gets a say. Every parallel batch is now chunked into groups of **at most 3** Graph-backed calls. Three rather than four is the point: a cap set exactly at the ceiling leaves no margin for the user's own Outlook client, a second plugin on the same mailbox, or a retry landing while three fresh calls go out. Three leaves one slot free. The cap is applied by tool-name prefix (`outlook_*`, `outlook_calendar_*`, `microsoft365_*`, `teams_*`, `sharepoint_*`, `onedrive_*`) and **nothing else is capped** — Gmail, Google Calendar, Slack, Jira, GitHub, Salesforce and web search have no such limit, so a Google-stack run batches exactly as it always did. Draft creation and prep-block booking are Graph *writes*, which throttle hardest, and are capped at 3 per message too. A 429 that still arrives keeps the existing one-retry-then-back-off treatment.
- **Nothing is called Open without a cross-channel check.** Briefs were reporting a thread's opening line as its final state, when a later message had already resolved it.
- **Every Daily Brief item names an owner and a deadline.** A client called an earlier version "very vague… does not specify who needs to take action and by when."
- **All PDFs go through one tested renderer.** Hand-written rendering shipped a brief with a corrupt page-1 content stream: the timeline lost its dots, a heading vanished, page 1 sat two-thirds empty with no footer, and the meeting list resumed midway down page 2. Every self-check in the renderer is a defect that build actually had.
- **The markdown backup is unconditional.** A verified PDF can still fail to reach someone for reasons no skill can observe.

### Known limitations

- **Permissions on a scheduled task is UI-only.** No tool can set it, so onboarding cannot flip it and never claims to — see *One-time setup* above. Left on *Manually approve*, an unattended 6 AM run waits forever for a click nobody makes.
- **`references/positioning-notes.md` ships as a marked default** and is skipped silently until someone customises it.
- **The `follow_ups` renderer kind is deprecated and unused.** Follow-Ups attaches nothing, so nothing in this plugin calls it; it is kept so that a hand-written or externally-stored payload naming that kind still renders rather than erroring. Do not build on it.
- **The citation-traceability check uses a heuristic** — a citation with no digit in it is treated as a generic locator and skipped. That is why it warns rather than fails.
