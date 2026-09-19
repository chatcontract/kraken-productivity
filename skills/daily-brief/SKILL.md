---
name: daily-brief
description: Weekday morning briefing — today's calendar, email, chat and open tickets in one pass: every meeting, real scheduling conflicts with a suggested fix, and everything due or overdue, each item carrying a named owner, a by-when date and a verified status, emailed as one PDF that closes with its sources. Scheduled weekdays; runs any day on demand. Use for a daily brief, day plan, "what's on my day", "what's due today", a conflict check, or a recurring morning briefing.
---

# Daily Brief

**Read `${CLAUDE_PLUGIN_ROOT}/references/shared-run-policy.md` first.** It owns the weekday guard, the rate-limit backoff policy, the status taxonomy and its cross-channel verification rule, mailbox resolution, the delivery contract, the connector table, the renderer exit codes, the universal ground rules, **§11, the house format every document and email follows**, and **§9, the writing rules — specific over general, front-loaded facts, and the banned hedges and filler — which apply to every line of this brief.** Everything below is what is specific to this skill. Do not restate the shared policy here — follow it.

**Invoke this skill as `/productivity:daily-brief`.** Plain English reaches it too (see the description above); the namespaced command is what to use in a runbook or when it matters that the right skill runs first time.

**Run `${CLAUDE_PLUGIN_ROOT}/references/connector-prerequisite.md` FIRST — before the `date` call, before the weekday guard, before reading anything.** Calendar, Mail and Drive/SharePoint are all mandatory: any one missing or unusable and this skill **always renders Connect buttons** via the connector registry — `search_mcp_registry` with generic nouns (`email`, not `gmail`), then one `suggest_connectors` call carrying every gap — and **stops**: no PDF, no email, no drafts, no partial run, and no scheduled task either — a schedule for a skill that cannot run fires every weekday and produces nothing. Connect what is missing, run it again, and that run offers the schedule. Written instructions are the fallback only when the session has no registry tool at all, never because a search came back empty. Chat is optional and never blocks. That file owns the roles, the probes, the five connection states, the status table and the card; this skill restates none of it.

**A missing or unreachable connector is answered with a Connect / Enable / Reconnect button, never a question.** Never raise an `AskUserQuestion` about a connector gap — the connector prerequisite's ladder runs until a card is on screen, and it overrides anything in this file.

## Run contract

- **Run order is fixed by shared §1:** the `date` call that starts the clock, then the weekday guard, then **the connector gate**. **Calendar, Mail and Drive must all be connected and answering before anything else happens** — a gap ends the run in Connect buttons, with no output and no schedule created. Only once the gate passes does a manual run make the §10 schedule check for *this skill*.
- **Connector check at the start of every run** (shared §13). **Calendar, Mail and Drive are all mandatory (the connector gate) and a missing one stops the run.** Calendar is additionally this brief's spine — without it this is not a daily brief, so say so at the top rather than quietly omitting *Today's meetings*. Every other gap is named once, in *Worth double-checking*.
- **If the run cannot finish, report the exact error** (shared §12) as the one email, subject prefixed `[Failed]` — never a silent absence at 6 AM, and never "something went wrong".
- **Weekday guard** (shared §1). A **scheduled** Saturday or Sunday run stops and sends nothing. A **manual** run happens on any day and briefs **today** — every section, the subject line and the payload are built around today, so there is no supported way to brief a different date. Asked for another day → say plainly that this brief only covers today, then give today's.
- **Budget: ~30 tool calls.** The gathering phase alone is capped at 16 (see *Gather*); the rest is rendering and delivery. Spend spare room on verifying whether something is *actually* still open, never on reading more sources.
- **This brief is read at 6 AM. Late is the same as missing.** The deadline table below is the authority on timing for this skill.
- **Zero questions on a scheduled run** (shared §6). On a **manual** run there is exactly one permitted question: the one-time offer to schedule **this skill**, per shared §10 — checked and asked **before the clock starts and before any gathering**, only when no scheduled task for this skill exists, and never twice. A yes hands off to `onboarding` in single-skill mode, which schedules this skill alone and leaves the other two untouched.
- One email, to the user's work mailbox only (shared §5).

## Deadline

| Elapsed | What must happen |
|---|---|
| **T+6 min** | Target — gathering and cross-channel verification done. |
| **T+13 min** | **Stop gathering.** No new searches, thread reads or follow-up lookups, even if something looks unfinished. Exception: a call already in rate-limit backoff keeps retrying (shared §3). Anything unverified is tagged **Needs confirmation**, never guessed. |
| **T+16 min** | PDF rendered, email sent. |
| **T+18 min** | **Absolute ceiling.** Send the brief inline in the email body, no attachment, stop. |

**These numbers absorb the Graph concurrency cap (shared §3), and that is the only reason they moved.** On an all-Microsoft stack the gathering phase is about seven round trips rather than four. **Nothing was cut to pay for it** — the seven reads, six thread reads, two follow-up sweeps and 16-call gathering cap are all unchanged.

When the deadline cuts the run short, name what was skipped in *Worth double-checking* — `Ran out of time at 13 minutes. Chat asks were not swept this run; an ask may be missing from this brief.` — and still pass every section key, with empty lists for what you never reached.

**A coverage note is a statement about the run, not a task, so it carries `"informational": true`** and is the one kind of item exempt from the owner-and-deadline requirement below. It has no owner and no deadline; inventing one to satisfy the format would be fabrication. Never use that flag on a real task.

## Gather — one batch, chunked to the Graph cap, hard caps

**Issue these as parallel tool calls, in groups of at most 3 Microsoft-backed calls per message** (shared §3). Never a sequential chain, never one call per message, and never wait on a call inside a group before firing the rest of that group.

### Graph concurrency cap

**At most 3 in-flight calls to `outlook_*`, `outlook_calendar_*`, `microsoft365_*`, `teams_*`, `sharepoint_*` or `onedrive_*`** — three rather than Microsoft's four, for the margin (shared §3). Calls to anything else — Gmail, Google Calendar, Slack, Google Chat, Jira, GitHub — are uncapped and ride along in the first group.

**This batch on an all-Microsoft stack** splits as:

| Group | Calls |
|---|---|
| 1 | Calendar · inbound email · chat query (a) |
| 2 | Chat query (b) · due sweep · the user's own sent mail and chat |
| alongside group 1 | Tickets, if the tracker is Jira/GitHub/Linear/Asana — not a Graph call, so it does not count toward the 3 |

On a Google or mixed stack, fire whatever is not Microsoft-backed together and chunk only the Microsoft remainder. **All seven reads happen either way** — the cap changes the number of messages, never the number of reads.

1. **Calendar** — exactly 1 list call, today 00:00–23:59 **local**. Start and end **with their timezone**, attendees + RSVP, organizer, location/format, title. **Max 1 calendar call for the day.**

   **Times come from the event record and are converted to the user's local timezone** — the one this run's single `date` call established. A connector often returns UTC or the organiser's zone, and printing that unconverted is how a brief shows the wrong time. Duration comes from start and end, never from the title. An all-day event has no clock time: write `All day`, never an invented 9:00 am. A recurring event's time is **this occurrence's** time, read from the instance rather than the series. Conflict detection depends entirely on this being right — two meetings only overlap in the same timezone.
2. **Email** — 1 search, recent ~2 days, for threads where the user was personally asked something and hasn't replied. **At most 25 emails, from snippets only.**
3. **Chat** — **max 2 queries, ever**: (a) a question-style "?" sweep, (b) a sweep on the user's name/email for directives and mentions. Merge the results.
4. **Due sweep** — 1 search (~10 days, email + chat) for "due", "deadline", "by EOD", "overdue", "still waiting on". Covers overdue *and* due-today; never run it twice.
5. **Tickets** — if a tracker is connected, its query goes out **in the first group of the batch** — a tracker is not Graph-backed, so it never counts toward the concurrency cap — never as a follow-up round and never one query per project. **Pull ALL of the user's open/in-progress items, not only those due on or before today** — an undated pending task is still real and lands in *Needs attention* with `by_when: "no stated deadline — flag today"`. Filtering to due-dated items is exactly how a genuinely pending task goes unreported. Where the tracker and the due sweep return the same item, keep the tracker's version (it has the real status and assignee) and spend no call reconciling them.
6. **What the user already did — their own outbound actions.** One search of **their SENT mail and their own sent chat messages, last ~7 days**. This is not a follow-up sweep and it is not about other people; it is the answer to *"have I already handled this?"*

   **This read is what makes cross-channel verification possible at all** (shared §4). Without it, an ask raised in chat and satisfied by an email is invisible: the brief holds the question and none of the evidence, so it reports Open and is wrong. A real run did exactly that — Slack asked for a recording, the user emailed it, and the brief still said `[OPEN] … none of the three has posted one`, because the mailbox it needed was never opened.

   Match on the **people and the subject matter** of each candidate item, not on the channel it was raised in. An ask from Gaurav in Slack is answered by anything the user sent *to Gaurav* about that thing — an email, a file, a calendar invite, a message in another workspace.

Caps after the batch:

- **Max 6 chat threads** get a full-thread read — **fired in groups of at most 3 where chat is Teams** (shared §3), so six reads are two messages; all six in one message where chat is Slack or Google Chat. Only where the snippet genuinely doesn't say whether the ask is still open. Most do. **The cap is still 6 threads** — chunking does not reduce it.
- **At most 2 follow-up searches total** across all shortlisted items, broad not narrow. No resolution signal after them → **Needs confirmation**, never a guessed Open or Resolved.
- **Never re-read a thread already seen**, and never make a call whose answer you already hold. The commonest waste here is re-searching a person or ticket that already appeared in the batch, then reading the same thread twice from two different searches. Keep a list of what you have seen and check it before every call.
- Free/busy lookup only if a real conflict needs an alternate slot — 1 call max.
- A capped or partial connector result → note the coverage in *Worth double-checking*, tag affected items **Needs confirmation**, and do not retry.

**Spend the batch, then stop.** The batch is seven calls (calendar, inbound email, two chat queries, the due sweep, tickets, the user's own sent mail and chat); with at most six thread reads, two follow-up sweeps and at most one free/busy lookup, the gathering phase tops out at **16 calls**, and that is the whole of it. **That total is unchanged by the Graph concurrency cap** — 16 calls spread over more messages is still 16 calls, and the cap is never a reason to make fewer. Reaching for more is the wrong instinct: the 6 AM reader would rather have a brief with one named gap than a perfect one at 6:30.

## Every pending item must trace to something you actually read

This brief has previously surfaced "pending tasks" that were vague, misattributed, or inflated from a thin signal. The gate below applies to every candidate for *Due today & overdue* and *Needs attention*.

- **A pending item exists only if the user was actually named, @mentioned, directly addressed ("you", "can you", a direct question to them by name), CC'd with an explicit ask, or is the resolved assignee on a ticket.** Their name appearing in a message *about* them, in a group discussion they weren't the target of, or as a bystander CC with no ask directed at them is **not** a pending task. Drop it — do not soften it into one.
- **Every `action` must be traceable to a specific message, ticket, or event read this run.** Quote or closely paraphrase the real ask, and name where it came from in `source` (channel, sender, rough time, or ticket ID). An item you cannot point to a specific source for is not real enough to include, however plausible it sounds.
- **Cross-check the connector's own status field** — the ticket's assignee and state, the invite's organizer/required field, the thread's most recent message — before calling anything pending. That is shared §4's verification, run against the batch you already have.
- **Before any item is reported Open, check what the user themselves already did** — read 6 above. The commonest wrong item in this brief is not an invented one; it is a real ask the user **already handled on a different channel**, reported Open because only the channel it was raised on was read. An ask in Slack is satisfied by an email; an ask in email is satisfied by a Slack message, a shared file, or a booked meeting.
- **If read 6 came back empty or failed, an otherwise-Open item is `Needs confirmation`, not Open** — and say so in one clause: `could not confirm against your sent mail this run`. Reporting Open while blind to the user's own actions is asserting something you did not check.
- **A jointly-addressed ask is still the user's item, but any of the named people can close it.** "Muktida, Mahesh and Sachin — can one of you record this?" belongs in the brief, and **it is resolved the moment any of the three does it**, not only when the user does. Check all of their names in what the batch returned before calling it outstanding, and never write "none of the three has" unless the run actually looked for all three.
- **Where the ask is real but ownership is genuinely unclear, default the owner to the user** — but never invent the ask itself. A vague signal stays out of the brief or goes to *Worth double-checking*; it does not get dressed up as a concrete task with a fabricated action.

## Early exit

After the batch: **no meetings, no pending asks, nothing due or overdue, and nothing resolved worth reporting** → send a 3-line plain-text email ("Clear day — no meetings, nothing due, no open asks") and stop. **No PDF.** **Resolved items block this exit**: a day whose only content is "these three things you were worried about are now closed" is worth a brief, and dropping them silently is the same class of bug as dropping an open one. Take this path whenever it applies; it is the fastest one.

## Conflicts

Classify same-day event pairs:

1. **Hard double-book** — overlapping minutes, neither side declined. A tentative RSVP still counts.
2. **Impossible back-to-back** — no overlap, too little gap. Two internal virtual meetings with zero gap is *Needs attention*, not a conflict.
3. **Double duty** — organizer or required participant in two simultaneous events.

Ignore declined events, free/available blocks, and sub-15-minute placeholders.

**Every conflict gets a stated call plus a `fix` line.** Priority order: explicit "do not move"/"final"/"signing" > fixed-date (filing, renewal, close, board) > external over internal > scarce or senior counterpart > one-off over standing internal > user-organised is cheaper to move. A genuine toss-up → say so plainly rather than faking confidence.

Fix forms: a specific alternate slot; a short polite regrets note to the organizer; or delegation to a named person already on the thread. Always plain text the user acts on — never send anything, never modify a calendar event.

## Sections — fixed order, every run

Headline (one real thing, or "clear day") · stat strip (the four counts, rendered as borderless cells — pass them as the `stats` object, never as one pipe-delimited string) · timeline graphic · **Today's meetings** (every event, one line: time range, what, who, virtual/in-person) · **Conflicts** · **Due today & overdue** · **Worth double-checking** · **Needs attention** · **Resolved** · **Sources**.

Masthead, stat strip, timeline and the start of Today's meetings all belong on **page 1**. The renderer's layout puts them there, and its near-empty-page check catches a gross failure **when `pypdfium2` is installed and the brief runs to three or more pages** — so treat that check as a backstop, not a guarantee, and do not pad page 1 to satisfy it.

**Section headings travel with their first item, so none strands itself at a page foot.** **The brief renders on the shared reading grid (§11):** the gutter carries each item's owner, due date and source; the column carries the title, the action and the body. So put the citation in `source`, never in `body` — the gutter already shows it, and repeating it spends the reading column on nothing.

**Two pages maximum, and the renderer enforces it** (exit 5). The brief is a morning scan, not a report — on a busy day it used to simply grow. When it overruns: keep **every meeting and every real conflict**, because those are the brief, then cut in this order — *Resolved* to the items the reader was actually worried about, *Needs attention* to the asks that genuinely need them, *Due today & overdue* to what is truly due or late, and one line per item throughout. **Never answer exit 5 by shrinking type**, and never drop a section silently: a heading with a one-line empty state is honest, an absent heading reads as "nothing here" when it may mean "never checked".

An empty section renders its heading plus a one-line empty state; **Sources** alone renders nothing when empty. Never omit a required key, never pad with invented items — a silently absent section reads as "nothing there" when it may mean "never checked", and that distinction is the entire point of *Worth double-checking*.

### Every actionable item names an owner and a deadline

A client called an earlier version "very vague… does not specify who needs to take action and by when." That is now a format requirement, not a style preference. For **every item in Conflicts, Due today & overdue, Worth double-checking and Needs attention**:

- **`action`** — imperative, a specific next step. "Send the revised MSA to legal", not "MSA needs review" and not "there may be an issue with the MSA". **It must add something the `title` does not already say** (§11): a title of "Kaleb's pricing question" followed by an action of "Reply to Kaleb's pricing question" prints one fact twice and wastes the line that should tell the reader what to do.
- **`owner`** — a **named person**, resolved from who actually holds the ball. Never `"you"`, never `"team"`, never omitted. Genuinely undeterminable → the owner is the user; a daily brief with no named owner defaults to the person reading it, not to nobody.
- **`by_when`** — a real date or explicit deadline from the source (`"today 5pm"`, `"Thu Sep 12"`, `"before the 2pm call"`). No deadline in the source → `"no stated deadline — flag today"`. A missing deadline is itself information, not grounds to leave the field blank.
- **`status`** — per shared §4.
- **Resolved items are the one exception**: already closed, so no action/owner/by_when/status. Plain body text.

**Banned anywhere in `action`, `body`, `detail` or `meta` for an actionable item:** "might need attention", "could be worth a look", "worth checking on", "may want to follow up", "at some point", "when you get a chance", "no rush but". Replace each with a flat statement of what happens, to whom, by when. The reader should never have to infer the ask.

### Sources — every brief closes with what it drew on

Build a de-duplicated `sources` list as you go: **one entry per distinct thread, ticket or calendar event the brief actually cites** — not one per item, so three items from the same Teams thread cite that thread once. Each entry is a label precise enough to find it again — `"Teams — #acme-account, thread with Kaleb, 9 Sep"`, `"Jira ACME-3"`, `"Calendar — Daily dev sync, 9:15 am"` — plus a `url` where the connector returned one. Omit `url` rather than invent it.

This is the traceability half of the pending-item gate above: if an item is in the brief, its source is in this list.

## Build — emit JSON, call the renderer

Renderer mechanics, exit codes and the one-rebuild-maximum rule live in shared §8. Two steps, once, no loop: write the structured object to a JSON file, then run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/assets/pdf.py" \
  --kind daily_brief \
  --in  brief.json \
  --out "Daily_Brief_$(date +%F).pdf"
```

`headline` and `stats` must carry content. Every other key — `meetings`, `conflicts`, `due_today`, `worth_double_checking`, `needs_attention`, `resolved`, `sources` — must be **present**, though an empty list is fine. A missing key is exit 6.

```jsonc
{
  "title":    "Daily Brief — Tuesday, September 9",
  "headline": "one real thing, or \"Clear day\"",
  "stats":    { "Conflicts": 2, "Due today & overdue": 8,
                "Needs attention": 9, "Resolved": 4 },

  // Drives both the timeline graphic and the "Today's meetings" list.
  // start/end: "9:15", "2:30 pm", or minutes-from-midnight.
  // kind: "conflict" | "back_to_back" | omitted.
  "meetings": [
    { "start": "9:15", "end": "9:35", "kind": "conflict",
      "label": "9:15 – 9:35 am — Daily dev sync",
      "who":   "14 attendees (organizer: Lohit)",
      "format":"Virtual — Microsoft Teams" }
  ],

  // Every section below takes the same item shape, and each field has one
  // place it renders (§11's grid): `action` leads the reading column in bold ·
  // `owner` becomes the gutter label · `by_when` and `source` become gutter
  // citations · `status` is a coloured tag on the title line · `fix` renders
  // as the bold "Suggested fix:" line, conflicts only.
  // All of action/owner/by_when/status are required on every item in the four
  // actionable sections. None applies to resolved — those are closed.
  "conflicts":             [ { "title": "...", "body": "...", "fix": "...",
                                "action": "Send Acme the 3pm regrets note now",
                                "owner": "Muktida", "by_when": "before 2:45pm",
                                "status": "Open" } ],
  "due_today":             [ { "title": "ROOT-3 — ...",
                                "meta": "Due Sep 4 · 5 days overdue · Status: Backlog",
                                "action": "Close out ROOT-3 or post a status update",
                                "owner": "Muktida", "by_when": "today",
                                "status": "Blocked" } ],
  "worth_double_checking": [ { "body": "...",
                                "action": "Confirm with Priya whether the export ran",
                                "owner": "Muktida",
                                "by_when": "no stated deadline — flag today",
                                "status": "Needs confirmation" },
                              // A coverage note is a statement about the RUN,
                              // not a task: no owner, no deadline, no status.
                              // `informational` is what exempts it from the
                              // accountability gate — without the flag this
                              // item fails the render (exit 6).
                              { "body": "Chat asks were not swept this run; an ask may be missing from this brief.",
                                "informational": true } ],
  "needs_attention":       [ { "title": "...", "body": "...",
                                "source": "Teams, 5:04 am",
                                "action": "Reply to Kaleb's pricing question",
                                "owner": "Muktida", "by_when": "today",
                                "status": "Open" } ],

  // An item that LOOKED outstanding but was verified resolved elsewhere belongs
  // HERE — not tagged Completed inside Needs attention (shared §4).
  "resolved":              [ { "title": "Deploy pipeline flagged as failing",
                                "body": "Raised in Teams at 9:04 am — thread shows it was fixed and confirmed at 9:41 am; no action needed." } ],

  // One entry per distinct thread/ticket/event actually cited, de-duplicated.
  "sources": [
    { "label": "Teams — #acme-account, thread with Kaleb, 9 Sep" },
    { "label": "Jira ACME-3", "url": "https://example.atlassian.net/browse/ROOT-3" },
    { "label": "Calendar — Daily dev sync, 9:15 am" }
  ]
}
```

The renderer owns US Letter and margins, the palette, sentence case, `KeepTogether` per item, headings glued to their first item, timeline dots with conflict rings and dashed back-to-back rings, and the two-pass "Page X of Y" footer on every page.

## Delivery

Per shared §5, plus:

- Attach as `Daily_Brief_YYYY-MM-DD.pdf`. Drive fallback path: `Skills/Daily Brief/`.
- Subject: `Daily Brief — <Weekday>, <Month D>`.
- Body: headline, the stat counts, one delivery line, `Full detail also saved to Daily_Brief_YYYY-MM-DD.md`, plus "N pages" when multi-page.
- Clear day → one short email saying so, no attachment needed.
- A required connector failing mid-run → log it and render from what came back. **Any mandatory role failing stops the run** — Calendar, Mail or Drive (the connector gate). Among the optional roles, none does.
- Multi-page is fine. Never trim real content to force one page.

## Final check before the email goes

- **Completeness** — every meaningful open item, commitment and pending response actually found is in the brief, including undated tracker items.
- **Grounded** — every pending item traces to a specific message, ticket or event read this run; nothing is in because a name appeared nearby.
- **Already-done check** — no item is reported Open without having looked at what the user sent themselves (read 6). Where that read was unavailable, the item says so and is tagged Needs confirmation.
- **Accuracy** — every status reflects a check against the batch, not a first mention. Nothing is Open that a later message or another channel already resolved.
- **Accountable** — every actionable item states what happens, who owns it, and by when, with no banned vague phrasing.
- **Traceable** — every claim's source is in `sources`.
- **Times** — every meeting's start, end and duration match the event record, converted to the user's local timezone; an all-day event says so rather than showing an invented time.
- **Value** — the brief says what needs attention and what to do next, not just what was seen.
