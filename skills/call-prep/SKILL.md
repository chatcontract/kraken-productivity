---
name: call-prep
description: Prep for a call, get ready for a meeting, brief me on an account, who am I talking to, prep my day — on demand any day, or as the 4 AM sweep of today's external calls. Requires Calendar, Email and Drive; marks meetings external by attendee domain, never by title, then books a private prep block before each call carrying a fact card under 200 words, and links a 1-2 page briefing PDF with named owners for every action. No email unless a run fails, and then with the exact error.
---

# Call Prep

**Read `${CLAUDE_PLUGIN_ROOT}/references/shared-run-policy.md` first.** It owns the weekday guard and run order, rate-limit backoff, the status taxonomy and its cross-channel verification rule, mailbox resolution, the connector table, the renderer exit codes, the writing rules, the house format, **§12 failure reporting** and **§13 the per-run connector check**. Everything below is specific to this skill.

**Invoke this skill as `/productivity:call-prep`.** Plain English reaches it too (see the description above); the namespaced command is what to use in a runbook or when it matters that the right skill runs first time.

**Run `${CLAUDE_PLUGIN_ROOT}/references/connector-prerequisite.md` FIRST — before the `date` call, before the weekday guard, before reading anything.** Calendar, Mail and Drive/SharePoint are all mandatory: any one missing or unusable and this skill **always renders Connect buttons** via the connector registry — `search_mcp_registry` with generic nouns (`email`, not `gmail`), then one `suggest_connectors` call carrying every gap — and **stops**: no PDF, no email, no drafts, no partial run, and no scheduled task either — a schedule for a skill that cannot run fires every weekday and produces nothing. Connect what is missing, run it again, and that run offers the schedule. Written instructions are the fallback only when the session has no registry tool at all, never because a search came back empty. Chat is optional and never blocks. That file owns the roles, the probes, the five connection states, the status table and the card; this skill restates none of it.

**A missing or unreachable connector is answered with a Connect / Enable / Reconnect button, never a question.** Never raise an `AskUserQuestion` about a connector gap — the connector prerequisite's ladder runs until a card is on screen, and it overrides anything in this file.

## What this skill delivers, and what it does not

**It books a private prep block on your calendar before each external call.** That block is the deliverable: a 10-minute hold ending when the call starts, carrying a fact card you can read in under two minutes, with the full briefing linked from it.

**It does not email you a brief.** Not one email per call, not one summary. The reason is the whole point of the skill: a brief that lives in an inbox is a brief you have to remember to go and read, and under time pressure nobody does. The calendar reminder arrives five minutes before the block, while you are between things and about to need it.

**The one email it ever sends is a failure report** (shared §12), subject prefixed `[Failed]`. A clean run is silent in your inbox by design.

## Run contract

- **Scheduled: weekday mornings, Monday to Friday, 04:00 local, prepping TODAY** — `onboarding` owns the cron and is the only thing that writes it. Four o'clock gives every call of the day, including an 8 AM one, a booked block well before anyone is awake to need it.

  **What 04:00 costs, and it is worth stating.** The day's calendar is read about four hours before the working day starts, so **a call added to the calendar after the run does not get a prep block** — the skill cannot prep a meeting that did not exist when it looked. A same-morning invite is the case this misses. Where that matters, invoke the skill by hand: a manual run preps today's remaining calls on demand, any day. Nothing else about the run changes with the hour.
- **Run order is fixed by shared §1:** the `date` call that starts the clock, then the weekday guard, then **the connector gate**. **Calendar, Mail and Drive must all be connected and answering before anything else happens** — a gap ends the run in Connect buttons, with no output and no schedule created. Only once the gate passes does a manual run make the §10 schedule check for *this skill*.
- **The weekday guard applies to scheduled runs only** (shared §1). **A manual invocation runs on any day, weekend included** — what changes is which calls it finds, not whether it runs. See *Which day, and which calls*.
- **The connector gate first** — Calendar, Mail and Drive are all mandatory and a missing one stops the run with no output. Calendar is additionally this skill's *subject*: without it there are no meetings to classify and nowhere to book. Every non-mandatory role degrades and says so.
- **Four absolutes. Nothing below may override them:** every external call gets **its own** prep block · every block carries a fact card under 200 words · every fact card links its briefing PDF · a run that cannot finish reports its exact error.
- **Zero questions on a scheduled run** (shared §6). On a **manual** run there are at most two: the one-time offer to schedule this skill (shared §10), and — on the very first run only — the internal-meetings preference below.
- **Depth over speed.** Budget ~70 tool calls. Speed comes from parallel batches, never from researching less. Running long → cut web searches first, transcripts last.

## Deadline

| Elapsed | What must happen |
|---|---|
| **T+11 min** | Target — research complete for every call of the day. |
| **T+16 min** | **Stop researching.** Write the cards from what you have. |
| **T+20 min** | Every prep block booked, every briefing rendered and linked. |
| **T+25 min** | **Absolute ceiling.** Book a block for every remaining call with whatever card exists — even a one-line one — then stop. |

**These numbers absorb the Graph concurrency cap (shared §3), and that is the only reason they moved.** This skill pays the most for it: attendee resolution is one batch across every external attendee of the day, so on an Outlook stack a day with four calls and five attendees each becomes seven round trips rather than one. **Nothing was cut to pay for it** — the ~70-call budget, 5 history lookups per company, 8 web searches and 1 forward-calendar check per company are all unchanged.

**A booked block with a thin card always beats an unbooked one.** The block is the thing that gets the person to look; the card can admit its own gaps. So when the clock runs out, **booking comes first and research is what gets cut** — and each affected card says so in one clause: `research cut short at 16 minutes — no transcript review for this account`.

## First run only — the internal-meetings preference

Some people want prep only for external calls. Others want it for internal 1:1s too, where the useful context is just as scattered.

**On the first run, and only when no preference is on record, ask once** via one `AskUserQuestion` card:

- **External calls only** (the default, and what the rest of this file assumes)
- **External calls and internal 1:1s** — a two-person internal meeting is treated like an external call
- **Every meeting with another human on it** — excludes focus blocks, holds and all-hands

**Record the answer in the settings record** (below) as one line, using **exactly one of these three strings** so the next run can parse what this one wrote:

- `prep scope: external only`
- `prep scope: external and internal 1:1s`
- `prep scope: every meeting with another human`

**On a scheduled run, never ask** — assume `external only` and say so in one clause on the first card of the run.

## The settings record

**Preferences live in one durable event, not in a prep block.** Prep blocks get deleted — by the person, or by the calendar when a call moves — and a preference stored in one dies with it. So this skill keeps a single event of its own:

| Field | Value |
|---|---|
| **Title** | `Call Prep — settings` |
| **When** | All-day, on the date of the first run. Never moved, never duplicated. |
| **Attendees** | **None.** Private, marked free. |
| **Body** | One `key: value` line each, in this order — `prep scope:`, `prep lead:`, `prep busy:`, then `opted out:` followed by one indented line per suppressed call. |

**Find it by title search, not by date** — a `search_events` for `Call Prep — settings`, fired in Step 1's batch. It is not on today's calendar, so the day's `list_events` will never return it.

**If no settings record exists**, this is a first run: create it, with the defaults for anything not asked (`prep lead: 10 min`, `prep busy: free`, an empty `opted out:`). **If it exists but a key is missing**, use that key's documented default and write the key back — never re-ask. **If the body cannot be parsed**, use every default, say so in one clause on the first card, and leave the record alone rather than overwriting someone's settings with a guess.

## Which day, and which calls

| Run | Day |
|---|---|
| **Scheduled, 04:00** | **Today.** |
| **Manual, a day named** ("prep Tuesday") | That day. |
| **Manual, a meeting or account named** ("prep my Acme call") | Find it in today through +7 days and prep only that. |
| **Manual, nothing named** | **Today**, if it still has calls ahead of the current time. Otherwise the next day that has one, within 7 days — state which: `prepping Monday 15 Sep — the next day with external calls`. |

**A manual run skips calls that have already started.** Prepping a call you are already in is noise. Say so in one clause if that is why a call was skipped.

---

# PART 1 — FINDING THE CALLS

**This is the part that has failed before. Read every line.** A missed client call is the worst outcome this skill can produce.

## Step 0 — establish the user's own domains, before reading the calendar

You cannot classify anything until you know what "internal" means. **Never assume a single domain.** Build an **own-domain set**, in one batch chunked to groups of at most 3 Graph-backed calls (shared §3) — the 30-day calendar read stays inside the batch and is never a follow-up round:

1. The signed-in account's own address, from the mail or calendar identity lookup. Its domain is the anchor.
2. Every domain in the user's own sent-mail **From** header — aliases, country variants, two brands on one company.
3. The chat workspace's verified domains, where the connector exposes them.
4. Domains appearing on ≥10 distinct people in meetings over the last 30 days. **This needs its own calendar read, back 30 days**, fired in the same batch. If it fails, **skip the signal** — items 1–3 suffice, and a missing corroboration never justifies guessing the set wider or narrower.

Also build a **corporate-infrastructure set** to ignore: room and resource addresses (`*@resource.calendar.google.com`, `*.rooms@`, anything flagged as a room or equipment), and no-reply/automation senders.

Record the own-domain set in the run log. **If identity lookup fails entirely, treat every meeting with any attendee as external** and say so in every card. Never fall back to "assume internal".

## Step 1 — read the calendar

**Two calls, one batch:**

1. One `list_events` for the resolved day, **00:00–23:59 local**, with the fullest attendee expansion the connector offers. **Include events not yet accepted, and tentative ones. Do not filter by response status.**
2. One `search_events` for the title `Call Prep — settings` — the settings record, which holds the scope preference, the lead time, and the opt-out and booked lists. **It is dated to the first run, so the day's `list_events` will never return it**; it has to be searched for by title.

**Where a meeting or account was named** rather than a day, widen call 1 to **today through +7 days** and prep only the match. That is still one call.

Capture per event: title, description/agenda body, **start and end with their timezone**, location, conferencing link, organizer (address **and** display name), and the full attendee list with addresses, display names, response status and resource flags.

**Attendees returned without addresses, or a truncated list, is a data gap — not evidence of an internal meeting.** One follow-up `get_event` per affected event, then classify.

### The date and time must be exactly right

**The prep block is booked from these numbers.** Get the time wrong and the block lands in the wrong slot, which is worse than no block at all.

- **Take start and end from the event record**, with the event's own timezone, and **convert to the user's local timezone** — the one this run's single `date` call established. Connectors commonly return UTC or the organiser's zone; booking against that unconverted is the classic wrong-slot bug.
- **State the weekday and date on the card**, not just a clock time: `Mon 15 Sep · 10:00 – 10:45 am`.
- **Compute duration from start and end**, never from the title. A "30-min sync" booked for 45 minutes is 45 minutes.
- **An all-day event has no clock time and gets no prep block** — there is no "before" to book. Mention it in one line on the day's first card instead.
- **A recurring event's time is *this* occurrence's**, read from the instance, never the series.
- **A moved event uses its current record**, which beats any time mentioned in an email or transcript.
- **A time that genuinely cannot be established → no block, and say why** in the failure report (§12). Never book against a guessed time.

## Step 2 — classify: ONE test, domain only

**A meeting is EXTERNAL if and only if at least one address on the invite — any attendee, or the organizer — has a domain outside the own-domain set and is not in the corporate-infrastructure set.** That is the entire test.

This replaced a version that also fired on the *title* — a company name, "sync with", "demo", "client", or a CRM match on title text. That mis-briefed two genuinely internal meetings whose titles happened to carry a customer's name — every attendee on both was on the user's own domain, but the name in the title tripped the title rule. **A meeting held to discuss an external account is not itself an external meeting.** Only the people on the invite decide that.

**The following may NEVER promote a meeting to external, alone or together:**

- **The title**, however it reads — a company name, "sync", "demo", "client", "internal", "kickoff", "with", "QBR", `<>`, `/`, `x`, any wording at all.
- **The conferencing link's tenant** on its own — a Teams/Zoom/Meet link can sit on any tenant regardless of who joins.
- **A CRM match** on the title's subject matter, with no matching attendee address.
- **"This would make a more useful brief"** or any variant of a hunch.
- **The word "internal" or "sync" anywhere.** That word is evidence *for* internal, never grounds to override the test.

**Data gaps are the one legitimate exception**, because the test needs addresses:

- Attendees without addresses, or a truncated list → one follow-up `get_event` before deciding.
- If addresses still cannot be obtained, **prep it** and say exactly why on the card: `attendee addresses could not be retrieved — the domain test could not run, so this was prepped rather than skipped`. **Never write "classified external on the title" or any equivalent.**
- Once addresses ARE available, the domain test decides, full stop.

### Cases, decided by domain alone

| Situation | Correct call |
|---|---|
| Every attendee and the organizer on the own-domain set, whatever the title says | **Internal. Skip** — unless the recorded preference includes internal meetings. |
| One attendee, anywhere, on an outside domain | **External.** One address is enough. |
| Organizer outside the set, every attendee internal | **External.** The organizer's address counts like any other. |
| An attendee on free mail (gmail, outlook.com, yahoo, icloud, proton, gmx…) | **External.** Free mail is never an internal colleague — still a domain fact. |
| No attendees returned, title names a company | **Data gap.** Fetch the record; still nothing → prep and flag. Never on the title alone. |
| Contractor or partner on the user's own domain | **Internal. Skip.** Their address is what matters, not their employment relationship. |
| Recruiting screen, candidate's personal email on the invite | **External.** |
| Personal appointment, focus block, no attendees | **Skip.** Never a prep block. |
| Large all-hands, every attendee on own domain | **Skip**, regardless of size. |
| A two-person internal meeting | **Skip by default**; prep it where the recorded preference includes internal 1:1s. |

### Deduplicate, don't drop

Two events for the same call (a duplicate invite, a held slot plus the real one) → **one** prep block, noting both times on the card. A recurring meeting still gets a block, focused on **what changed since the last occurrence**.

## Step 3 — scope

- **No cap on blocks.** Every external call gets its own.
- **More than 8 companies** (the research unit, not the meeting count) → keep every block and reduce **research depth**: rank by stakes (new logo / no history first, then exec attendees, then external headcount, then earliest start) and give the top 8 companies full depth, the rest core depth — skip web search and competitive context, keep transcripts, email, CRM, agenda and the card.
- Note on the affected cards which got core rather than full depth.

## Early exit — genuinely nothing

Only after Steps 0–2 classify **zero** calls in scope: **book nothing, email nothing, and say so in the reply if this was a manual run.** A scheduled run with no external calls is correctly silent — there is no failure to report and nothing to deliver. Log the count of events examined so a silent misclassification is visible in the run log.

---

# PART 2 — RESEARCH

Every batch below goes out as parallel calls, **in groups of at most 3 Microsoft-backed calls per message** (shared §3) — never a sequential chain, never one meeting at a time.

## Graph concurrency cap

**At most 3 in-flight calls to `outlook_*`, `outlook_calendar_*`, `microsoft365_*`, `teams_*`, `sharepoint_*` or `onedrive_*`** — three rather than Microsoft's four, for the margin (shared §3). Web search, a CRM, a transcript connector, Slack and Google Workspace are uncapped and ride along in the first group.

**Where this bites in this skill, in order of cost:**

| Batch | Chunking |
|---|---|
| **Attendee resolution** — 1 batch for every external attendee across all calls | The largest fan-out here. Groups of **≤3** Graph calls; twenty attendees is seven messages. **Resolve every attendee** — never trim the list to save a round trip, because an unresolved attendee is the error that attributes one person's history to another. |
| **History lookups** — 5 per company | Groups of **≤3**. A transcript or CRM connector that is not Graph-backed does not count toward the 3. |
| **Step 0 own-domain set** — identity, sent-mail From headers, chat domains, 30-day calendar read | Groups of **≤3**. The 30-day calendar read stays in the batch; it is still never a follow-up round. |
| **Step 1** — the day's `list_events` plus the settings `search_events` | Two Graph calls, so **one group**, unchanged. |

**Booking the prep blocks is a Graph write, and writes throttle hardest**: create or update **at most 3 blocks per message**. A day with seven external calls is three messages, not one. **Never skip a block to save a round trip** — shared §5 makes the block the delivery, and the four absolutes make it unconditional.

## Research once per COMPANY, not once per call

**Group the calls by company first, then research each company once and write every card for that company from the shared result.**

Three calls with one account today is **one** research pass, not three. Five lookups × 3 calls = 15 becomes 5. The cards still differ — each gets its own attendees, time and opener — but the account history behind them is identical.

Build the group key from the external domain, falling back to the company name in the title. **Write the grouping in the run log before any research call** — `Acme → 3 calls · Rand → 1`. That company count is what the budget is spent on.

**Global caps, not per-call caps:**

| Resource | Cap |
|---|---|
| History lookups (transcripts, email, CRM, chat, docs) | **5 per company** |
| Web searches | **8 across the whole run**, highest-stakes companies first |
| Attendee resolution | **1 batch for every external attendee across all calls** |
| Forward-calendar / renewal check | **1 per company** |

## Contact and account matching

**Resolve each external attendee's address to a real record before using anything about them.**

- **Match on the email address**, against CRM contacts and the participants on prior email threads. An address match is a fact.
- **A name-string match is a fallback, not a match** — flag it. "Dana Whitfield" in the CRM and `d.whitfield@acme.com` on the invite are probably the same person, and "probably" belongs on the card: `[CRM: Contact record — matched by name, not address]`.
- **No match at all is a normal outcome.** Say `no prior record` rather than reaching for a same-company record that belongs to someone else. Attributing one person's history to another is the most damaging error this skill can make.

## Batch A — history: groups of at most 3 Graph calls

Query by **company/domain**, never per attendee or per call. Up to **5 lookups per company** — every company's lookups issued together, **chunked into groups of at most 3 Microsoft-backed calls per message** (shared §3). Reads 1, 3 and 5 often sit on a transcript connector, a CRM and a tracker that are not Graph-backed; those do not count toward the 3 and go in the first group.

1. **Past meeting transcripts and recordings** — the highest-value source. The **2 most recent** prior calls with this company or these attendees. Extract: what was promised and by whom, objections raised, **the language *they* used for their own problem**, who spoke most, decision-makers named but absent, and any explicit next step with a date. **Quote at most two short lines verbatim.**
2. **Email threads** with the company domain, last 90 days — latest state, unanswered questions, anything the user promised.
3. **CRM** — stage, owner, amount, close date, last activity, open next step.
4. **Chat** — mentions of the company or contacts, last 30 days. Internal chatter often holds the real status; a reaction is real acknowledgement evidence.
5. **Docs / tickets** — proposals, SOWs, security reviews, open tickets, prior briefings for the same account. A ticket's **current status** is direct evidence for or against an item still being open.

**Also check what the user already sent** (shared §4, check 1) before calling any commitment of theirs outstanding. Batch A's email read covers the company domain; a commitment satisfied in chat, by a shared file or by a booked meeting is only visible in the chat and docs reads. **Telling someone they still owe a document they sent last week is worse than saying nothing** — it is wrong, checkable, and they will check it in front of the customer.

**Upcoming context too:** the calendar forward 30 days **from the call** for other meetings with this company, and CRM for a deadline, renewal or close date falling soon. A call three days before a renewal is a different call.

**Never re-read** a thread, doc or record already returned this run. An empty result is an answer.

## Freshness — a fact has an age, and the age matters

**Every cited fact carries its date, and anything older than 90 days is flagged rather than presented as current.**

- `[CRM: Deal 4471 — stage last changed 12 Mar, 6 months ago]` is honest. `Stage: Negotiation` alone implies today.
- **Write the exact date and the plain-English gap together** — `2 Sep, 13 days ago`. The date is checkable; the gap is what the reader actually reasons with.
- A stale fact is not dropped. It is labelled: `possibly stale`.

## Conflicts — flag them, never resolve them silently

Sources disagree. CRM says the deal closed; the last email says they are still negotiating. **Say so on the card, name both sources, and do not pick a winner.**

`[CRM: Deal 4471 says Closed Won, 4 Aug] but [Gmail, 2 Sep] has Dana still asking about terms — worth confirming which is current.`

**Silently choosing one is the failure mode.** The reader can resolve it in ten seconds on the call; they cannot resolve a conflict they were never shown.

## Batch B — public signal: all in one message

**Web search is not Graph-backed, so the concurrency cap does not apply here** (shared §3) — these still all go in one message.

**8 web searches for the whole run.** One on the company (news, funding, leadership, product), and a second on its primary external attendee only where they are senior and the account is high-stakes. **A company with rich internal history rarely needs a search** — internal signal beats a headline. Nothing found → `no recent public signal found`. Never invent, and never search to confirm what a transcript already said.

## Batch C — attendee resolution: groups of at most 3 Graph calls

**This is the largest fan-out in the skill and the one most likely to trip Graph throttling** — one batch across every external attendee of the day. Signature-block and chat-profile lookups are Graph-backed; **at most 3 per message** (shared §3), so twenty attendees is seven messages. CRM and public search ride along uncapped. **Resolve every attendee** — never trim the list to save a round trip, because an unresolved attendee is what leads to attributing one person's history to another.

Resolve every external attendee's title and role from the richest source available — signature blocks in prior threads, CRM contact record, chat profile, public search. Where a title cannot be established, write **"title not established"** rather than guessing.

---

# PART 3 — THE FACT CARD

**This is what goes in the calendar invite. Target 120 words. Hard ceiling 200.** It must be readable in under two minutes on a phone, without a second scroll.

**It is a fact card, not a memo.** Label-led fragments and bullets. **No paragraphs.**

## Structure — five short blocks, in this order

**Labels sit on their own line, in sentence case.** Not ALL CAPS — a card in shouting capitals reads like machine output, and this one is read five minutes before a call by a person on a phone.

### 1 · Header — two lines, never one

```
Payal Sharma (LegalGraph AI) · Jira → GEMS integration demo
Vignesh's call · you're optional · 1:00–1:15 pm
```

- **Line 1: who you're meeting and what the meeting is.** Name, org in brackets, then the meeting's own name.
- **Line 2: whose call it is, your role in it, the time.** "You're optional" and "you're the organiser" are worth a reader's attention; both change how they treat the next 15 minutes.
- **Add the objective to line 2 only when a source actually states one** — `goal: agree the three-year term [CRM: Deal 4471]`.

**Never announce a fact you do not have.** No `title not established`, no `goal: none stated`, no `no prior record` on the card. **Omit the clause.** A reader scanning a card in ten seconds should spend none of them reading about what the research could not find — the briefing PDF is where a gap gets named, and only where it changes what a section can claim. This rule overrides any earlier instinct to fill a slot for completeness.

### 2 · Before you join

**Up to 2 bullets of context** — the state of things, and what moved recently. Each carries its source.

> • Sachin closed testing of the Jira Assets → GEMS workflow on 10 Sep, 6 days ago, against Vignesh's test cases `[Drive: LegalGraph Status Tracker]`
> • Payal's live thread with you is Agiloft, not GEMS — her test deck came via Mahesh on 15 Sep, 1 day ago `[Gmail, 15 Sep]`

### 3 · Your move

**What the reader personally owes, or has to decide — up to 2 bullets.** Omit the block entirely when they owe nothing.

> • Tell Vignesh whether you're attending — your invite is still unanswered, and so are Payal's and Mahesh's `[Calendar, today]`

**This block exists because merging it into the context bullets was the card's worst defect.** The old format had one heading, *What's changed*, holding three things that were defined never to be the same kind of thing: the last interaction, an open commitment, and a risk. A commitment the reader owes is not a change, and burying it among facts is how it gets skimmed past. **Context and obligation are separated because the reader acts on only one of them.**

### 4 · Open with

**One sentence they could say out loud**, tied to the first bullet or to the decision in *Your move*. Plain speech. No source tag — it is yours, not a fact.

> "Vignesh, I'm optional on this one — do you want me there for Payal, or shall I drop?"

### 5 · Ask

**One question worth asking**, where the research suggests a real one. **Skip the block rather than inventing one.**

> Payal, does the Jira Assets to GEMS flow match what your team expected?

### Then, last, two lines and nothing else

```
Full briefing → <link>
ref: call-prep/<call key>
```

**The `ref:` line is machinery, not content** — it is how the next run recognises this block as one of its own (Part 4). Keep it to one short line, last, so it reads as a footer rather than as something the reader was meant to act on. **Never put it above the content, and never let it wrap onto two lines.**


## A complete card, as it should look

This is a real run's card, rewritten to the format above — 128 words, every factual line sourced, no announced gaps, no raw system values:

```
Payal Sharma (LegalGraph AI) · Jira → GEMS integration demo
Vignesh's call · you're optional · 1:00–1:15 pm

Before you join
• Sachin closed testing of the Jira Assets → GEMS workflow on 10 Sep,
  6 days ago, against Vignesh's test cases [Drive: LegalGraph Status Tracker]
• Payal's live thread with you is Agiloft, not GEMS — her test deck came
  via Mahesh on 15 Sep, 1 day ago, and you sent dashboard screenshots
  the same day [Gmail, 15 Sep]

Your move
• Tell Vignesh whether you're attending — your invite is still unanswered,
  and so are Payal's and Mahesh's [Calendar, today]

Open with
"Vignesh, I'm optional on this one — do you want me there for Payal,
or shall I drop?"

Ask
Payal, does the Jira Assets to GEMS flow match what your team expected?

Full briefing → <link>
ref: call-prep/5gglp4va2edl3cco4qpkd7nqjh
```

**What this fixed, from a card that actually shipped.** The original ran everything into one header line (`Payal Sharma, title not established, LegalGraph AI · Jira → GEMS integration demo, Vignesh's call · goal: none stated — you are optional`), then put the state of the work, a decision the reader owed, and a correction under a single heading called *What's changed* — where only one of the three was a change. It printed `needsAction`, and announced two things the research had failed to find. Every one of those is now a named rule above.

## Tone and language

- **Second person, plain and declarative.** "You last discussed pricing on 2 Sep" — not "the user last discussed" and not "it appears that pricing was discussed".
- **Keep the source's own *domain* terminology.** If the CRM says `MQL`, write `MQL`. If the customer calls it "the GEMS flow", call it that. Never translate a customer's or a team's words into your own.
- **But never print a system's raw field value.** `needsAction`, `tentative`, `declined`, `PROPOSED`, `Closed Won` as a bare token, an enum, an ID, a `camelCase` status — these are protocol, not language. Say what they mean: **"still unanswered"**, "hasn't accepted", "turned it down". The distinction is simple — a word a *person* on this account would use goes through unchanged; a word only an *API* would use never appears on the card. A real run printed `your invite is optional and still needsAction`, which is the tell.
- **Exact dates, with the gap in English** — `2 Sep, 13 days ago`. Both, always.
- **Numbers exactly as the source has them.** `$180k ARR`, not "around 180 thousand".
- Shared §9's writing rules apply in full: specific over general, front-load the fact, no hedges, no filler.

## Source tags on every non-obvious line

**Every factual line carries a pointer** — a live link where the destination supports one, a bracketed tag where it does not:

`[Gmail, 2 Sep]` · `[CRM: Deal 4471]` · `[Transcript, 14 Aug call]` · `[Jira ACME-204]` · `[Slack #acme-account, 5 Sep]`

- **A live link wherever the connector returned a URL.** A tag is the fallback, not the default.
- **Anything reasoned rather than read is tagged `inferred`.** Never given a fake source.
- **The opener needs no tag.** Common knowledge needs no tag. Everything else does.
- **Target: every factual line traceable.** A line you cannot tag is a line you cannot support — cut it.

---

# PART 4 — BOOKING THE PREP BLOCK

**One private calendar event per external call.** This is the delivery.

**Order within the run: render and upload the briefing first, then book the block.** The block's body has to contain a real link, and a link cannot be written before the file exists. The one exception is the T+25 ceiling, where a block is booked with whatever exists — naming the briefing's local path, or saying plainly that no briefing was produced for this call.

**Which calendar:** the same calendar the call itself is on. Where several are connected and the call's own calendar cannot be determined, the user's default/primary calendar. **Never a shared, team or resource calendar.**

## The event

| Field | Value |
|---|---|
| **Start** | The call's start **minus the lead time** (default **10 minutes**), subject to the fitting rules below. |
| **End** | The call's start. The block ends exactly when the call begins. |
| **Subject** | `Review call prep notes for <meeting name>` |
| **Body** | The fact card's five blocks (Part 3), then the briefing link, then the one `ref:` line. Nothing else. |
| **Reminder** | **5 minutes before the block** — so 09:45 for a 10:00 call with a 10-minute lead. On a block shorter than 5 minutes, the reminder fires at the block's own start instead, so it cannot ring inside the preceding meeting. |
| **Attendees** | **None. Ever.** |
| **Visibility** | Private, and marked as such where the connector supports it. **Free, not busy**, unless `prep busy: busy` is in the settings record. |

**Worked example.** A 10:00 call → a block at **09:50–10:00**, titled `Review call prep notes for Acme renewal call`, reminder at **09:45**.

## The marker line, and why the dedupe key is not the title

The body's last line is exactly:

```
ref: call-prep/<call key>
```

**The call key is the calendar event's own ID** where the connector returns one, and only otherwise a stable fallback: the organiser's address plus the call's start in `YYYYMMDDTHHMM` local. **Never the meeting name and never the slot** — a renamed call, a moved call, or a block booked with a shortened lead changes both of those, which produces exactly the duplicate the check exists to prevent.

Where the event carries a **recurring-series ID**, the line carries both: `ref: call-prep/<series id>/<occurrence id>`. Capture the series ID in Step 1 alongside start and end; the series half is what an opt-out is recorded against.

## Never double-book, never overwrite blindly

- **Before booking, search the day's blocks for the marker line's call key** — that is one `list_events` you have already made in Step 1, re-read, plus a `search_events` on the subject prefix `Review call prep notes for` where the connector supports body search. A match → **update that event in place**. Two prep blocks for one call is the most visible bug this skill can ship.
- **Never delete, move or modify a calendar event that does not carry this skill's marker line.** Read-only everywhere else (shared §6).

## Fitting the block into a real day

These rules are ordered. **Apply the first one that matches and stop** — the earlier version had two rules describing the same back-to-back day and giving different answers.

1. **A free gap of at least the lead time before the call** → book the full block. The ordinary case.
2. **A free gap shorter than the lead time but at least 5 minutes** → shorten the block to the gap. A 09:05 call after an 09:00–09:00 meeting that ends 08:58 gets a 7-minute block.
3. **Less than 5 minutes free, including a zero gap** → book a **5-minute block ending at the call's start, marked free, overlaying whatever is there**, and say so in one clause on the card: `your 09:55 is already booked — this block is an overlay`. Overlaying is safe precisely because the block is free and has no attendees; it shows up as a reminder, not as a competing commitment. **Never shorten below 5 minutes, and never skip the block** — a short block is worth far more than none.
4. **Two prep blocks that would overlap each other** — calls at 10:00 and 10:05 — → the **earlier call's block keeps its slot; the later call's block is shortened to end at its own call's start and to begin no earlier than the earlier call's start.** Where that leaves less than 5 minutes, rule 3 applies. **The two cards stay separate**; never merge two calls into one block.

**A block is never booked overlapping the call it precedes**, in any rule above.

## Per-call opt-out

**A person can suppress prep for a specific call.** Honour any of these, say nothing further about that call, and do not count it as a failure:

- The call's own description contains `no prep` or `productivity: skip`.
- The call key, or its series ID, appears under `opted out:` in the settings record.

**A deleted prep block is an opt-out — which is why deletions have to be recorded.** At the start of every run, for each call in scope that a **previous** run booked (its key is under `booked:` in the settings record) but which has **no** prep block on the calendar now, treat the block as deleted by the person: append its key — the **series ID where there is one**, so the whole series is covered — under `opted out:` in the settings record, and prep nothing for it again.

**Without that record a deleted block is indistinguishable from a block never booked, and the next run re-creates exactly what the person threw away.** That is the single fastest way to make an assistant unwelcome. So every run also appends the keys it booked under `booked:` in the settings record — one line each — which is what makes the absence detectable next time.

**Trim both lists to the last 60 days** so the record does not grow without bound.

---

# PART 5 — THE BRIEFING PDF

**One PDF per call**, rendered by the plugin's renderer, **saved to the connected drive and linked from the prep block.**

Save to `call-prep/<day YYYY-MM-DD>/<HHMM>-<account>.pdf`, upload to `Call Prep/<date>/` on the drive, and put the returned link in the card. **Drive is a mandatory connector** (the connector prerequisite), so a run that got this far has one; an upload *rejected* on a byte-correct file is retried once, then the card carries the local path and the run reports it (§12).

## It is a 1–2 page executive briefing, not a dossier

**This replaced a fifteen-section document that ran to five and six pages.** The old version gave every fact its own heading and repeated the call's basics three times, so its length grew with how much source material existed rather than with what the reader needed. It is now **nine sections, two pages maximum, one page legitimate** for a short call.

**The renderer enforces the ceilings and will fail the job rather than shrink type.** Length is managed by cutting, and the test for every line is one sentence:

> **If it does not help the reader prepare, decide, ask, act or follow up, it does not belong.**

So: no generic company background, no repetition of the glance strip later in the body, no "how to perform well" advice that would read true for any meeting, no narrating the research, no metadata nobody acts on.

## Structure

Renderer mechanics, exit codes and the one-rebuild-maximum rule are in shared §8.

**Pass every key below, empty lists included. A missing key is exit 6**, even where the value is empty.

- **Required and non-empty:** `company`, `context`, `time`, `attendees`, `what_you_need_to_know`, `objective`, `desired_outcome`, `questions` (**4–6**), `sources`.
- **Required, may be empty:** `duration`, `format`, `owner`, `stage`, `last_contact`, `classification_note`, `absent_decision_maker`, `risks`, `actions`.

**Sections, in render order:**

| # | Section | Content | Ceiling |
|---|---|---|---|
| 1 | **Masthead** | `company`, then `context` — **one sentence on why this call is happening.** | 28 words |
| 2 | **Call at a glance** | `time`, `duration`, `format`, `owner`, `stage`, `last_contact` as a label/value strip, then `desired_outcome` in an accent box. **Every basic fact appears here once and is never repeated below.** | `desired_outcome` 22 words |
| 3 | **Who you'll be speaking with** | A table: name, role · company, and **one line on why that person matters**, grounded in something real. Set `first_time: true` on a first-time attendee. Note an absent decision-maker in `absent_decision_maker`. | **20 words, 1 sentence** per attendee |
| 4 | **What you need to know before the call** | The bullets that change how the call is run — current state, what moved, a source conflict. Each with its `source`. | **4 bullets**, 28 words each |
| 5 | **What you should accomplish** | `objective` — the specific outcome, with a name and a date. Never "build rapport". | 25 words, 1 sentence |
| 6 | **Questions you should ask** | 4–6, specific to this account and this moment, each unanswerable from the briefing itself. | 20 words each |
| 7 | **Risks to watch** | Likely objections and real sensitivities, merged. Only where research shows something real — **never invent a landmine, and never pad because the section exists.** | **3 bullets**, 28 words each |
| 8 | **Actions & owners** | A table: `owner`, `body`, `by_when`, `status` (shared §4). Every commitment in one place — what you owe, what they owe, what is undecided. **An undelivered one the user owes goes first.** | 22 words per action |
| 9 | **Sources** | A descriptive label per source, which **is** the link. Real `url` only where the connector returned one. | — |

## The rules the renderer enforces as hard failures

- **Over 4 `what_you_need_to_know` or 3 `risks`** → exit 6, naming the count. A briefing that lists everything prioritises nothing.
- **Fewer than 4 or more than 6 `questions`** → exit 6.
- **An action with no owner** → exit 6. **Name the person, including when it is the user** — use their own name from the Step 0 identity lookup; `you`, `them` and `the team` are rejected.
- **A field well past its word limit** → exit 6, naming the field.
- **Over 2 pages** → exit 5, with an ordered list of what to cut. **Never answer exit 5 by shrinking type.**

## Sources must be usable

- **A descriptive label, not a raw URL.** `Q2 company update` — never `https://example.com/news/2024/q2-update?src=...`.
- **A real `url` only where a connector returned one.** The renderer drops a malformed or non-http URL to plain text rather than rendering a dead link.
- **Never invent a URL**, and never reconstruct one that looks plausible.
- **Only what was actually consulted**, and at most the 6 the briefing genuinely cites.

## Only use what you found

**Never invent a commitment, a sentiment, a role, a date or a history.** Where something is not in the sources, leave it out — or say plainly that it is unknown where the reader would otherwise assume. `title not established` is honest; a guessed title is not. A briefing's whole value is that every line is checkable.


# PART 6 — REPORTING, AND FAILURE

## A clean run says nothing in the inbox

Blocks booked, briefings linked, done. **No summary email.** On a **manual** run, say it in the reply instead — one line: `Booked 3 prep blocks for today: Acme 10:00, Rand 14:00, Initech 16:30. Full briefings linked in each.`

## A failed or partial run emails, per shared §12

**Subject:** `[Failed] Call prep — <what broke, in five words>`

**Body — the five elements of shared §12, in order, then the closing line:**

1. **Which skill and when it stopped** — `Call Prep, 07:04, stopped after reading the calendar`.
2. **What was already done** — blocks booked, briefings rendered, by name.
3. **The exact error, verbatim**, with the step and tool that produced it. Quote it; never paraphrase. **Quoted error text is exempt from the placeholder check in shared §11** — a connector's own message may contain a bracketed token, and altering it defeats the purpose.
4. **One plain sentence on what it means** — no jargon.
5. **What to do next**, or plainly that there is nothing.

Then the closing line, `Sent to <address>`, as every email in this plugin carries (shared §5).

**Send this whenever any of these is true:**

- The calendar could not be read, or **a block could not be booked** for a call that needed one.
- A briefing could not be rendered after one retry, or **the drive rejected the upload** after one retry. (Drive is a mandatory connector, so a run reaching this point has one — a rejected upload is a real fault, not an absent role.)
- **A mandatory role was missing** — Calendar, Mail or Drive. That is a *block*, not a failure: it shows the connector card and sends no `[Failed]` email (the gate's Part 6 owns what it does send). A missing optional role is silent.
- The run hit its ceiling with calls still unprepped.
- Any step raised an error the run could not work around.

**Not a failure, and never emailed:** a day with no external calls, a call the person opted out of, a call skipped because it had already started, and any optional connector being absent. **A quiet day is a clean run.**

**Also put a marker where the person will see it:** an event titled `Call Prep failed — <short reason>` in the slot the first prep block would have occupied. Someone who does not read email before their 10 AM still sees their calendar.

**When the calendar is itself what failed, there is no slot and no write access — so the marker cannot be placed.** Do not retry it and do not go silent: send the email and say in it that no calendar marker could be placed, and why. If mail is unavailable too, a manual run says it in the reply and a scheduled run logs the verbatim error and exits (shared §12).

**A partial run reports partially and still delivers.** Two blocks booked of four is two blocks more than nothing — book them, and let the email name the two that failed and why.

---

## Pre-send gate — run this before booking anything

**Classification** — the own-domain set was actually established, not assumed · every event on the day was classified **by domain alone** · no meeting with an external address was skipped · every in-scope call has a block. **If you can point to a title word, a conferencing tenant or a CRM match as the reason a call was prepped, and no address was actually outside the own-domain set, that call is misclassified and must be corrected before booking.**

**Times** — **every block's slot is derived from the event record, converted to local time** · duration computed from start and end · no block booked against a guessed time · no block overlapping the call it precedes.

**Cards** — under 200 words · the five blocks in order, labels in sentence case · **no announced gaps** (`title not established`, `goal: none stated` and the like are omitted, not printed) · **no raw system values** (`needsAction`, enums, IDs) · context and the reader's own obligations in **separate** blocks · every factual line tagged · exact dates with the plain-English gap · second person · the customer's own domain terms kept · briefing linked · the `ref:` line last and on one line. Nothing invented. Anything over 90 days flagged. Any source conflict shown rather than resolved.

**Blocks** — private, no attendees, correct reminder, **marker line present and carrying the event ID**, no duplicate for a call whose key already appears on the day, no re-creation of a block whose key is under `opted out:`, no block overlapping the call it precedes, nothing modified that does not carry this skill's marker line.

**Settings record** — read before booking, written back after: this run's booked keys appended, any block missing since the last run recorded as an opt-out, both lists trimmed to 60 days.

**Failure** — if anything above could not be done, the failure email carries the **exact error**, not a paraphrase.

## Skill-specific ground rules

Shared §6 applies in full, plus:

- **Transcripts contain other people's words.** Quote sparingly, never more than two short lines per briefing, and **never forward a transcript**.
- **Read-only everywhere except the prep blocks this skill creates**, the briefing files, and the failure email. Never modify a real meeting, never write to CRM, never message anyone.
- **A prep block is private by default and is not a team artifact.** No attendees, ever — not the account owner, not a manager.
- A missing optional connector (shared §13) is **never** a reason to skip a block.

## Reference

`${CLAUDE_PLUGIN_ROOT}/references/positioning-notes.md` — optional org-specific positioning, messaging and competitive framing.

**The test is one string:** the file is still the shipped default if its first heading line contains `SHIPPED DEFAULT, NOT YET CUSTOMISED`. Present → **skip it silently**. Absent → it has been customised, so read it and use it. A part-edited file that still carries the banner counts as default, which is the safe direction: stale positioning is worse than none.
