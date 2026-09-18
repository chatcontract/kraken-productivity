---
name: kraken-follow-ups
description: Find my follow-ups — who do I need to follow up with, who has gone silent, whose next step is overdue, what did I promise and never send, create the follow-up drafts, review my pending follow-ups. Scans sent mail, inbox, chat, calendar and CRM with a 10-day zero-gap floor, ranks what needs a reply, and creates thread-preserving drafts in the user's own voice — never sending — then emails one plain-text summary. No attachments. Scheduled weekdays; any day on demand.
---

# Kraken Follow-Ups

**Read `${CLAUDE_PLUGIN_ROOT}/references/shared-run-policy.md` first.** It owns the weekday guard, the rate-limit backoff policy, the status taxonomy and cross-channel verification, mailbox resolution, the delivery contract, the connector table, the universal ground rules, and **§11, the house format — including the five-part shape this skill's summary email follows**. **§9's writing rules govern that email too** — specific over general, front-loaded facts, no hedges or filler. They do **not** govern the drafts: those are written in the user's own voice per Step 3, with this skill's own banned-AI-tells list. Everything below is what is specific to this skill.

**Invoke this skill as `/kraken-productivity:kraken-follow-ups`.** Plain English reaches it too (see the description above); the namespaced command is what to use in a runbook or when it matters that the right skill runs first time.

**Run `${CLAUDE_PLUGIN_ROOT}/references/connector-prerequisite.md` FIRST — before the `date` call, before the weekday guard, before reading anything.** Calendar, Mail and Drive/SharePoint are all mandatory: any one missing or unusable and this skill **always renders Connect buttons** via the connector registry — `search_mcp_registry` with generic nouns (`email`, not `gmail`), then one `suggest_connectors` call carrying every gap — and **stops**: no PDF, no email, no drafts, no partial run, and no scheduled task either — a schedule for a skill that cannot run fires every weekday and produces nothing. Connect what is missing, run it again, and that run offers the schedule. Written instructions are the fallback only when the session has no registry tool at all, never because a search came back empty. Chat is optional and never blocks. That file owns the roles, the probes, the five connection states, the status table and the card; this skill restates none of it.

**A missing or unreachable connector is answered with a Connect / Enable / Reconnect button, never a question.** Never raise an `AskUserQuestion` about a connector gap — the connector prerequisite's ladder runs until a card is on screen, and it overrides anything in this file.

**This skill's one documented divergence from shared policy: it attaches nothing, ever.** No PDF, no markdown file, no renderer, no upload-and-link fallback. The plain-text email body plus the drafts sitting in the Drafts folder are the entire deliverable — which is also why this skill cannot be taken down by a renderer or sandbox outage, the exact thing that compounded a real incident.

## Run contract

- **Run order is fixed by shared §1:** the `date` call that starts the clock, then the weekday guard, then **the connector gate**. **Calendar, Mail and Drive must all be connected and answering before anything else happens** — a gap ends the run in Connect buttons, with no output and no schedule created. Only once the gate passes does a manual run make the §10 schedule check for *this skill*.
- **Connector check at the start of every run** (shared §13). **Calendar, Mail and Drive are all mandatory (the connector gate) and a missing one stops the run with no output.** Mail is additionally this skill's subject — both the source and the place the drafts land. Name every other gap in the lead line, including a role that was connected at setup and is not now.
- **If the run cannot finish, report the exact error** (shared §12) as the one email, subject prefixed `[Failed]`.
- **Weekday guard** (shared §1). A **scheduled** Saturday or Sunday run stops and sends nothing. A **manual** run happens on any day — the coverage floor is 10 *calendar* days, so a weekend run's window still lands on real dates.
- **Budget: ~60 tool calls.** Raised from an earlier fast-path budget because **completeness outranks speed here.** Real runs missed genuine follow-ups by stopping at the first page of search results and capping thread review too low. Speed still matters — batch everything, never re-read — but never at the cost of coverage.
- **Zero questions on a scheduled run** (shared §6). On a **manual** run there is exactly one permitted question: the one-time offer to schedule **this skill**, per shared §10 — checked and asked **before the clock starts and before any gathering**, only when no scheduled task for this skill exists, and never twice. A yes hands off to `kraken-onboarding` in single-skill mode, which schedules this skill alone and leaves the other two untouched.
- One email, to the user's work mailbox only (shared §5). **Follow-up messages themselves are drafts only, never sent — absolute.**

## Deadline

| Elapsed | What must happen |
|---|---|
| **T+10 min** | Target — batch read (pagination followed to completion) and ranking done. |
| **T+18 min** | **Stop gathering and stop drafting.** Ship the drafts already created; start no new one. |
| **T+21 min** | Summary composed, one email sent. |
| **T+23 min** | **Absolute ceiling** — send the summary as-is and stop. |

**These numbers absorb the Graph concurrency cap (shared §3), and that is the only reason they moved.** On an Outlook stack Rule 1 becomes two round trips instead of one, and eight drafts become three messages instead of one. **Nothing was cut to pay for it** — the ~60-call budget, the six-source batch, the pagination-to-completion rule, the 10-day floor and the absence of a thread cap are all exactly as they were.

**The 10-day coverage floor below is the one exception to this table** — the single documented override in the whole plugin. The clock governs the optional 10-to-21-day extension and all drafting; it does **not** license stopping short of a fully paginated last-10-calendar-days read. If the floor is not done at T+18, keep reading until it is, then go straight to ranking, drafting and sending on whatever time remains. When the floor overruns the ceiling, the email goes the moment the floor completes — the override buys coverage, never silence.

**Say what the deadline cost** per shared §2. Drafts planned but not written → list them under *Needs your input* with the reason `ran out of time — not drafted`. **Never report a clear day because time ran out.** And if the Drafts folder was never read, say so explicitly — otherwise unsent drafts from earlier runs silently vanish, which is a bug this skill has already shipped once.

## Rule 1 — one batch, chunked to the Graph cap

Issue **every independent read as parallel tool calls, in groups of at most 3 Microsoft-backed calls per message** (shared §3). Never a sequential chain, never account-by-account. Skip any role that isn't connected (shared §7).

### Graph concurrency cap

**At most 3 in-flight calls to `outlook_*`, `outlook_calendar_*`, `microsoft365_*`, `teams_*`, `sharepoint_*` or `onedrive_*`** — three rather than Microsoft's four, for the margin (shared §3). Gmail, Google Calendar, Slack, Google Chat, Salesforce and HubSpot are uncapped and ride along in the first group.

**On an Outlook + Teams stack** the six reads below split as: group 1 — sent mail, inbox, calendar; group 2 — chat, Drafts folder, and CRM alongside if it is Salesforce or HubSpot. On Gmail, all six go in one message as before.

**All six reads happen either way, and so does every page of each one.** Pagination continuation calls are themselves subject to the cap — follow at most 3 Microsoft continuations at a time — but **the pagination-to-completion rule below is untouched**: a search is still not done until its cursor is exhausted or the clock stops it.

1. **Sent mail, last 21 days** — external recipients. Doubles as the follow-up signal *and* the style corpus.
2. **Inbox, last 21 days** — external senders.
3. **Calendar** — past 14 days and next 7 days, external attendees only.
4. **Chat** — one search on the user's name and mentions, last 14 days. (Chat's target window is 14 days, not 21; the 10-day floor below still applies to it in full.)
5. **CRM** — open opportunities with last-activity date, if connected.
6. **Drafts folder** — read it **explicitly**, folder-scoped. Drafts appear in neither an inbox nor a sent-mail sweep. This serves the duplicate guard *and* the unsent-draft backlog reported under *Still open*.

### Follow pagination to completion — the direct fix for missed follow-ups

Real runs missed genuine follow-ups because a search returned a `nextPageToken` / `@odata.nextLink` / cursor and only the first page was read. The search looked complete and wasn't. **A search is not done until its pagination is exhausted or the time budget forces a stop.**

- Any continuation token → **follow it**, repeating until the token is empty or absent.
- **Pagination calls never count against the query cap in Rule 2** — that cap counts distinct constructed queries, not the pages one query takes to exhaust.
- A stop mid-pagination must be stated precisely in the summary, with the denominator above.
- This applies to every read in the batch, the Drafts-folder read included.

### Coverage floor — last 10 calendar days, zero gaps, non-negotiable

- **Sent mail, inbox and chat for the last 10 calendar days (today back through day-10) must each be read to full pagination completion.** Not 10 business days — 10 calendar days, so the window always lands on real dates. Every page, every continuation token, for each of those three sources. No sampling, no "first page looked thin so I stopped."
- The floor is **separate from, and senior to,** the 21-day window above. Twenty-one days is the target; ten days is the guarantee. If time runs short, the 10–21 day extension is what gets cut — never the 0–10 day floor.
- **Rate-limit responses are backed off and retried per shared §3, never treated as a stop signal**, and that backoff may run past the deadline when it is what completes the floor.
- **State the floor's outcome explicitly in the summary's lead line** — either "last 10 days fully covered across sent, inbox and chat, zero gaps" or, if a source genuinely could not be reached (connector down or not connected — **never** elapsed time, never a rate limit), name exactly which source and which days: "chat unavailable this run — last 10 days of sent mail and inbox fully covered." An unstated floor reads as met when it might not be.
- Only an actual tool failure may leave the floor incomplete. **Treat an incomplete floor as seriously as a crash** — it is one.

### Reading the Drafts folder — expect a thin listing

A drafts search typically returns `recipients` and a date but **`subject` and `sender` as null**, because an unsent draft has no envelope yet. So:

- **Match on recipient + thread/conversation ID + date. Never on subject alone** — a null subject is not an empty subject, and treating it as one either misses the duplicate or invents a false match.
- Use the draft's date field (`sentDateTime` / `receivedDateTime` / last-modified, whichever the connector returns) as its **created date** for aging.
- Need the subject or body to describe an item? Fetch that one draft's full content by ID — only for drafts you will actually report, up to the draft cap, never for the whole folder.
- **Ignore drafts this skill did not create.** An unaddressed scratch draft, or one with no external recipient, is not a follow-up. Match against the follow-ups identified this run and in the recent past, not everything in the folder.

## Rule 2 — caps that protect against runaway, never against coverage

- **One constructed query per source role in Rule 1 (six maximum), plus at most 2 clarifying searches** across the whole run. Broad queries, not narrow ones. Pagination continuation is not a query (see above). *This replaces an earlier "3 distinct searches" cap that contradicted the six-source batch it sat next to and could be read as forbidding half the batch.*
- **No cap on how many threads are examined** from what the batch returns. The old 30-thread ceiling is exactly what caused real follow-ups to go unreported on busy weeks — removed. The only limit is the time budget, and an early stop must state what fraction was covered.
- **Never re-read a thread already seen.** Search results are the evidence; do not open threads to "confirm". Open a full thread only where the batch result is genuinely ambiguous — a snippet that already shows the last message and who sent it needs no further read, so in practice this stays small on its own. Fire every ambiguous one together, in groups of at most 3 where the source is Graph-backed (shared §3).
- **Drafting is capped at the top 15 follow-ups per run.** The cap keeps the created-drafts list reviewable in one sitting; it is not a coverage limit. **It never removes an item from the report** — anything beyond 15 still appears at its real priority with the reason ending `— not drafted this run, draft cap reached`, and still counts in the subject line and lead.

## Rule 3 — early exit

Nothing warrants a follow-up → **one 3-line email**, no attachment ("Checked X threads over N days. Nothing needs a follow-up today. No drafts created."), zero drafts, stop. Do not pad the list.

**This exit is available only when there is genuinely nothing — including nothing already drafted and unsent.** Check the Drafts folder before taking it. One unsent follow-up draft means the day is **not** clear: report it under *Still open* and send the full summary instead.

## Step 1 — pick the follow-ups

From the batch results only. A follow-up is warranted when:

- The user promised something and never sent it.
- The other side promised a reply and hasn't, past ~3–5 business days.
- A direct question sits unanswered.
- A proposal, quote, deck or pricing went out with no reply (~7–10 days).
- A named date or agreed next step has passed.
- An account went quiet after real activity.

**Do not look only for the literal phrase "follow-up."** Most real commitments never use it. Scan for the language people actually use:

- Requests: "Can you…", "Could you…", "Please…", "Would you mind…"
- First-person commitments: "I will…", "I'll send…", "I'll get back to you on…", "Let me…"
- Group commitments implying a next step: "We should…", "Let's…", "We'll follow up once…"
- A promise to **send** something (a doc, quote, intro, link) that never went out.
- A promise to **schedule** something (a call, demo, review) that was never booked.
- A **pending approval** — something waiting on a yes/no that hasn't come.
- A decision reached whose implied next step was never confirmed or acted on. The decision isn't the follow-up; the un-executed next step is.
- An item explicitly awaiting confirmation from either side.

**Suppress:** thread resolved · **the user already did the thing, on any channel** — the commitment was to send a recording and they emailed it, or to share numbers and they posted them in chat; match on the person and the subject, never on the channel the promise was made on (shared §4, check 1) · **the user actually sent** a follow-up in the last 5 business days · a next meeting is booked and the ball isn't theirs · deal closed · they asked to be contacted later and that date hasn't arrived · internal-only, newsletters, notifications, automated mail.

### An unsent draft NEVER suppresses an item

**A draft is not a follow-up. Only a sent message is.** An existing draft means the user was told to send something and hasn't — the follow-up is *more* overdue, not resolved. Suppressing it makes the item vanish from every later run while the user is told "nothing needs a follow-up" and the ask sits unsent in Drafts. That is the single worst failure this skill can produce, and it has happened.

For every item with a draft in the folder and no sent reply on the thread:

- **Keep it. Report it under *Still open*.** Never omit it, never fold it into a count, never call the day clear because of it.
- Say how long it has waited: `drafted 4 Sep · still unsent · 3 business days`.
- **Escalate with age.** Unsent 3+ business days → at least **Medium**. Unsent 5+ business days → **High**, listed above the new items, because the user has now sat on a written follow-up for a working week.
- Do not create a second draft — reuse the existing one and point at it.

A run where every item is an unsent draft is **not** a clear day. It is a day whose whole report is "these are waiting on you to hit send", and Rule 3's early exit does not apply to it.

## Step 2 — rank, with a stated reason

Sort High → Medium → Low. Every item carries a one-clause reason grounded in a real fact and date ("said 2 Sep he'd confirm budget by 5 Sep").

- **High** — missed explicit commitment or deadline; someone actively waiting on the user; deal near a decision.
- **Medium** — active thread with an unclear next step; gone quiet after a real conversation.
- **Low** — older or relationship-maintenance touches.

De-duplicate to one follow-up per contact per topic. **The list itself has no cap** — draft the top 15, list the rest as not drafted. An item with genuinely **no discernible ask to write from** is flagged rather than drafted — but that is rare, and "uncertain whether they replied" is not it (that is a coverage gap, and it still gets a draft; see Step 3.5).

## Step 3 — writing-style mirroring

Drafts must read as though the user wrote them. This is not optional polish.

### The corpus — their Sent folder is the style guide

**Sampling costs no extra round trip.** The sent-mail read in Rule 1's batch *is* the corpus; never spend a separate call on it.

- **Use the 15–20 most recent sent emails**, and read their **full bodies**, not snippets — a snippet cannot show you a sign-off, a signature or a blank line, which are three of the things that matter most.
- **Prefer replies to external people** over internal notes and over first-contact emails: a follow-up is a reply, so replies are the closest match.
- **Prefer any prior sent email to this exact recipient.** If one exists it outranks everything else (see *Per-recipient override*).
- **Never use received mail as the corpus.** Other people's writing is not theirs. Only messages the user actually sent.

### The fingerprint — extract it once, before drafting anything

**Structure and spacing** (the half that makes a draft *look* right at a glance, and the half most often skipped):

- **Greeting form, verbatim** — `Hi X,` / `Hey X` / `X —` / `X,` / none at all — including its punctuation and whether a blank line follows it.
- **Blank-line pattern**: between greeting and first line · between paragraphs · before the sign-off · between sign-off and signature. Record what they actually do, gap by gap.
- **Paragraph shape** — how many sentences before they break, and whether they break at all.
- **Bullets**: do they ever use them? If not, never introduce one. If yes, which marker and whether items end in punctuation.
- **Indentation and leading whitespace** — almost always none in real email. If their samples have none, **use none**: a leading space or tab on a body line is an instant tell that something machine-generated wrote it.
- **Line breaks inside a paragraph** — some people hard-wrap, most let it flow. Match theirs.
- **Sign-off and signature block, verbatim** (see the dedicated rule below).

**Voice:**

- **Typical length in sentences — record the median. This governs everything.**
- Sentence length and rhythm; short and clipped, or flowing.
- Formality, contractions, hedging vs directness.
- Recurring stock phrases — "circling back", "let me know", "quick one", "sounds good".
- Whether they use the recipient's first name mid-body.
- Punctuation quirks: dashes, ellipses, exclamation marks, Oxford comma.
- Casing habits — do sentences start lowercase?
- Emoji: which ones, how often, or never.

**Write the fingerprint down before the first draft**, and draft every item in the run against that same record. Re-deriving the voice per draft is how five drafts end up in five slightly different registers.

### Per-recipient override

**Prior sent mail to *this* recipient beats the global fingerprint, every time.** People write differently to a boss than to a vendor, and the recipient sees only their own thread — so the register that matters is the one they already recognise.

- One or more prior sent emails to this person → mirror **that** thread's greeting, length, formality and sign-off, even where it departs from the global pattern.
- The same thread being replied to is the strongest signal of all: match how the user wrote in it.
- No prior mail to this person → the global fingerprint, and lean slightly more formal than their average. Over-familiarity with a stranger is the more damaging error.

### Signature block — lifted verbatim, never invented

The signature is the most identity-revealing part of an email, so it gets its own rule:

- Pull the **exact** sign-off word and signature block (name, title, company, phone, every line the user actually includes) from their **most recent sent email that has one** — character for character, including its internal line breaks. Prefer the version used with this recipient or this kind of thread; otherwise the most recent overall.
- **Never construct, complete, or "clean up" a signature.** Not a title they didn't type, not a full name where they sign with a first name, not a phone number from a directory or CRM. Only what appears in their own sent mail. Where sent mail is inconsistent, use the most recent one that has a signature — never average or merge two versions into a new one.
- Genuinely **zero** sent emails with any sign-off → end on the sign-off word alone (whichever appears most often, or none) and append nothing. Note it once in `style_note`.
- One signature copied verbatim and reused unchanged across every draft in a run is **correct**, not lazy. Consistency with their real signature is the goal.

**Draft rules**

- **Match the median length above all else.** Most people write far shorter than an AI does. Fingerprint says 3 sentences → write 3.
- Reuse their actual stock phrases, greeting and sign-off. Never introduce vocabulary, punctuation or structure absent from their samples.
- Reply into the existing thread; open by referencing the real conversation.
- Never invent facts, figures, pricing, dates or names.
- **Spacing must read like a real email.** A blank line between the last sentence and the sign-off, and between the sign-off and the signature block — mirroring whatever gap pattern their own samples use. If their samples run sign-off and signature together, match that. The one thing never acceptable is a sign-off or signature butted onto the last sentence with no break at all.

**Banned AI tells** — never write any of these: "I hope this email finds you well" · "I wanted to reach out" · "Just circling back to touch base" / "bumping this up your inbox" / "per my last email" · em-dash-heavy constructions they don't use · bulleted lists if they never bullet · over-hedged closings ("Please don't hesitate to reach out", "at your earliest convenience") · any greeting/sign-off pair appearing nowhere in their samples.

### Draft completeness gate — nothing half-finished is ever saved

**Read every draft back in full before saving it, and check all nine.** A draft that fails any one is **not saved** — fix it, or move the item to `needs_your_input` with the reason. An unfinished draft in someone's Drafts folder is worse than no draft: they may send it without re-reading, and it goes out over their name.

1. **Complete sentences throughout.** No line ends mid-clause, no trailing comma or dangling "and", no sentence that stops before its point. If the thought wasn't finished, finish it or cut the sentence.
2. **Every part their own style actually uses is present, in order:** greeting · body · sign-off · signature block. **Measured against the fingerprint, not against a template** — a user whose sent mail carries no greeting, or no signature, gets drafts with none, and that is complete. What fails is a part that is *missing relative to their own habit*: they always open with "Hi X," and this draft doesn't, or they always sign off and this one trails away. The body is the one part required unconditionally.
3. **No placeholder, ever.** No `[name]`, `<date>`, `TBD`, `XX`, `TODO`, `insert…here`, no "as discussed on [date]". If a fact is needed and not known, the item is flagged, not drafted around.
4. **No unresolved reference.** "the attached" with nothing attached, "the document I mentioned" that was never named, "last week's call" when no such call is in the thread. Every reference points at something real in the thread you read.
5. **Recipient resolved and correct** — lifted from this thread's headers, past all four Step 3.5 checks.
6. **Threaded.** Created as a reply on the real message, with the `Re:` subject and quoted history intact. Never a standalone compose.
7. **Spacing correct** (see *Draft rules*): a blank line between the last sentence and the sign-off, and between the sign-off and the signature. Never a wall of text, never a sign-off welded to the last sentence.
8. **Within their median length**, and free of every banned AI tell.
9. **No meta-commentary.** Nothing addressed to the user rather than the recipient, nothing explaining the draft's own origin.

**Then ask the one question that matters: would this pass as theirs, and could they send it right now without editing a word?** If the honest answer to either half is no, it is not ready. Saving it anyway is how a half-written sentence ends up in front of a customer.

**Thin corpus.** Fewer than 5 usable sent emails → **say so in the summary** and fall back to short, plain, neutral drafts: a plain greeting, two or three sentences, "Thanks," and their name as it appears on the account. **Never invent a voice from two samples** — a confidently wrong voice reads worse than a neutral one, because the user has to unpick it rather than just add to it. No sent mail readable at all → still draft (neutral), still say so, and never fabricate a signature.

## Step 3.5 — correctness gate, before every single draft

A real run shipped drafts for a meeting that had already happened and to a wrong address — both invisible to a check that only asked "does this need a follow-up," never "is this specific draft correct?" Every item surviving Step 2 passes all four checks. Fail one → do not draft; move it to `needs_your_input` with the specific reason, **and still list it in the summary.** A flagged item is a working outcome. A wrong draft is not.

### Default to draft — withholding is the exception

The user reviews every draft before anything sends; this skill never sends. So the bar for creating a draft is deliberately low and the bar for withholding one is deliberately high. **Draft it unless a check below found something concretely, affirmatively wrong — never merely because information was incomplete.**

A real run reported zero new drafts on a day with more than a dozen live candidates, because a connector was rate-limited partway through and "confirming no reply already exists" couldn't be done with full confidence. That is the wrong trade: an unsent draft the user discards in one click costs nothing, while a real follow-up that never got drafted can cost a relationship.

- **Incomplete coverage is never, by itself, grounds to withhold.** Source rate-limited, partially read, or briefly unavailable, and that is the *only* open question → draft it and add one clause to `reason` naming the gap: "inbox only partially reviewed this run — confirm no reply already arrived before sending." The user has the full thread in the draft view and can check in seconds; the skill, mid-run, often cannot.
- **Withhold only for something affirmatively wrong:** a real bounce (check 4), a genuinely unresolvable or malformed address (check 2), two threads sharing a subject that truly cannot be told apart (check 3), or direct evidence the matter is resolved or the meeting already happened with no usable past-tense angle (check 1). These stay hard stops. "This run didn't read every remaining message" is not one.

**1 — Temporal validity.** Re-check the actual date of the meeting, deadline or commitment against **today's real date** (the run's own `date` call), not against when the thread was last read.
  - A "looking forward to our call" or "ahead of Thursday" follow-up needs that meeting still **in the future**. Already happened → either rewrite in past tense grounded in what the thread shows was said, or, with no evidence the call happened at all, flag it. Never guess.
  - A deadline you're chasing must not show a later message in the same thread already satisfying it. Skim the thread's most recent 1–2 messages — already in the batch, not a new call.
  - Genuinely **conflicting** dates across sources is a real ambiguity: flag it. But merely not having read every message that *might* contain a reply is a **coverage gap, not timing ambiguity** — draft it and name the gap.

**2 — Recipient validity.** The To/Cc address must be lifted directly from the message headers you actually read in this thread — never a CRM contact card, a display-name guess, autocomplete, or a similar-looking address from a different thread with the same person's name. One person can have several addresses; only the one on this thread's messages is correct.
  - No resolvable address on the thread's most recent external message, or an address that looks malformed (no `@`, obviously truncated, an internal alias where an external reply is needed) → flag it, never draft to a best guess.
  - Never draft to a distribution list or a no-reply address as though it were a person.

**3 — Thread identity.** Confirm the message or thread ID this draft replies into is the one Step 1 identified. A subject line repeats across unrelated threads ("Re: Contract", "Quick question") — use the conversation ID from the batch to pick the right one. Cannot disambiguate → flag rather than guess.

**4 — Address plausibility: bounce and domain mismatch.** A well-formed address from a real thread can still be wrong — a typo the other side made, an address that stopped working, a lookalike domain. Check both **using data already in the batch**, never a new lookup per item:
  - **Bounce check.** Scan the inbox and sent-mail results already read for a non-delivery / bounce / "undeliverable" notice naming this exact address anywhere in the window. One exists → **do not draft.** Move to `needs_your_input` with `status: "Needs confirmation"` and say plainly: *"This address may be incorrect — a bounce notice was found for it on `<date>`. Review the address before following up."*
  - **Domain-mismatch check.** Compare the address's domain against other known-good addresses for the same person or company already visible in the batch — other thread participants, a calendar invite for the same account, a CRM record. No match and no other supporting evidence → **do not draft.** Flag: *"This address's domain doesn't match other contacts at `<company>` — verify it's correct before following up."*
  - Absence of a bounce is not proof of one, and is not grounds to block a draft that passed checks 1–3. Never spend an extra search chasing bounce evidence that isn't already in the batch.
  - **A flagged address is still reported, never dropped.** The point is to warn the user before they send to a bad address, not to make the item disappear.

## Step 4 — create drafts (drafts only, always as a reply on the real thread)

- One draft per selected follow-up, up to the cap, for every item that passed Step 3.5. Create them without asking — a draft is inert.
- **A follow-up is a reply, never a new email.** Use the connector's **thread-preserving reply-draft** tool against the real message validated in Step 3.5, so the draft lands in the existing conversation with quoted history and correct `Re:` threading. **Never a standalone/new-compose draft** — a follow-up as its own separate email loses the thread, arrives with no context for the recipient, and is a materially worse email than the one the user would have sent. Where the connector offers reply-to-sender and reply-all, default to reply-to-sender unless the thread genuinely has multiple active participants who need to stay on it.

### Replying to the user's OWN last sent message is normal and required

A real run reported "couldn't create a threaded reply draft… the connector needs an inbound message to reply into, and they haven't replied yet" and skipped the draft — for precisely the most common case this skill exists to handle. **That is wrong and must not recur.**

- **The message you reply into can be ANY message in the thread, including the user's own last sent message.** No mail system requires a reply to target an inbound message. Replying to your own sent message to nudge someone is standard, and is exactly what this skill is for.
- Chasing the user's own unanswered message → thread the reply-draft against **that message**, not an earlier inbound one. That produces the correct `Re:` subject and keeps the full quoted history.
- **If a reply-draft call errors on the user's own sent message, retry once against the thread's very first message** before concluding the connector cannot do it. Only after both attempts genuinely fail does it go to `needs_your_input` — and the reason is a **connector limitation encountered this run**, never "they haven't replied yet", which is not a real blocker and must never be given as a reason.
- Check this every time, not just once per run.

- **The draft is a clean, ready-to-send email — nothing else.** No meta-commentary about how it was produced or where its content came from: never "Note attached below…", "Context from previous message…", or any line explaining the draft to the user rather than to the recipient. If it wouldn't read naturally to the actual recipient, it doesn't belong.
- **Write all the drafts first, then issue the create calls in groups of at most 3** (shared §3). Eight drafts created one at a time is eight round trips and the slowest part of the run; composed in one pass and fired in groups of three it is three. **Draft creation is a Graph *write*, which is the operation Microsoft throttles hardest**, so the cap matters more here than on the reads — and the group size is 3 whether or not the run has seen a 429 yet. **Never drop a draft to save a round trip:** every draft that passed the completeness gate gets created, in as many groups as that takes.
- **Never send an outward-facing email. Ever.**
- **Duplicate guard:** match existing drafts on thread/conversation ID, then recipient **plus date** — never subject, which a drafts listing usually returns as null. Already exists → leave it in place, do not write a second. Only a material change (they replied, a new commitment, a different ask) justifies *updating* it. Never two drafts for one thread. **Leaving the draft alone is a drafting decision, not a reporting one — the item still appears under *Still open* with its unsent age.** Marking something `already drafted` and dropping it from the summary is the bug that told a user "nothing needs a follow-up" while two written follow-ups sat unsent for five days.

## Step 5 — compose the plain-text summary, send one email

**No PDF, no renderer, no markdown file, no attachment of any kind.** Compose the body directly as plain text (or simple HTML paragraphs where the mail tool prefers it) — no JSON payload, no build step. Group items High → Medium → Low within each of `new_today`, `still_open` and `needs_your_input`, and write it straight into the send call.

**Subject:** `Follow-ups ready for review — N new, M awaiting send, P flagged · <date>`

`N` = drafts created this run · `M` = drafts still unsent from earlier runs · `P` = everything not drafted this run: the `needs_your_input` items (correctness-gate failures, address flags) **plus** the draft-cap overflow listed in part 3.

**Count each item exactly once**, and count the rendered lists rather than trusting a number worked out earlier — a cap-overflow item appears in part 3 *and* in `P`, so it must not also be counted under `needs_your_input`. Per shared §11 check 2, the three numbers must reconcile against the items actually in the body; a subject promising more than the body lists means something real went missing.

**All three numbers always appear, even at zero.** A subject reading "0 new, 0 awaiting send" while a real item sits flagged is exactly the misleading pattern this fixes. Every number 0 → `Follow-ups checked — nothing open · <date>`.

### Body — a fixed structure, nothing outside it

Client feedback flagged an earlier body as cluttered: a parenthetical aside about unrelated account activity folded in alongside required content. **The body has exactly these parts, in this order, and nothing else:**

1. **One lead line** — threads reviewed, window used, the **10-day coverage-floor outcome**, drafts created, and how many earlier drafts are still unsent. If the 10–21 day extension was cut short, say so precisely here.
2. **Still open** — every unsent draft from an earlier run, one line each with its age in business days. **Ordered by age, oldest first** — age is the escalation here, so it outranks the High/Medium/Low grouping used elsewhere, and anything 5+ business days sits at the top of the whole body. A 3-day unsent draft belongs here too; there is no age below which an unsent draft goes unreported.
3. **Every new follow-up drafted this run**, one line each with contact, topic and reason. This is the only place the detail lives, so do not truncate to a "top 3" — list all of them.
4. **Needs your input**, one line each, if any — correctness-gate failures and address flags. **Draft-cap overflow does not go here**: those items are listed in part 3 at their real priority with the reason `— not drafted this run, draft cap reached`, which keeps them in one place and keeps the counts reconcilable (§11).
5. **Closing line** — review, edit, send; nothing has been sent — plus `Sent to <resolved work address>`.

**Nothing else goes in the body.** No parenthetical asides about an account's general activity, no editorial colour, no explaining your own reasoning, no "by the way" tangents, however true. A fact relevant to one item belongs in that item's own line as one clause, not as a freestanding aside. Every sentence must map to one of the five parts; if it doesn't, cut it. Well-formatted means real paragraph breaks between the parts and a blank line around each list — not one dense block.

## Pre-send gate — before any draft is created or the email sent

**Coverage** — the last 10 calendar days of sent mail, inbox and chat are confirmed fully paginated with zero gaps (rate limits backed off and retried, never abandoned), **and that outcome is stated plainly in the lead line** — unstated or vague fails this check. Every meaningful commitment was considered, not only ones using the literal word "follow-up". Nothing was dropped from the report to save time: the draft cap limits drafting, never reporting. Drafts folder unreadable → said so in one line, never reported as a clear day.

**Correctness** — every draft passed all four Step 3.5 checks. Nothing was withheld merely for incomplete coverage; every item not drafted carries an affirmative reason. No draft references a commitment already overtaken by events, and no draft goes to an address that wasn't lifted from the thread actually read, or that carries a known bounce or unexplained domain mismatch.

**Voice and form** — every draft's greeting, sign-off and signature block are verbatim from the user's own sent mail, spacing matches their own samples, it is within their median length, it contains no banned AI tell and no meta-commentary, and it lands as a **reply on its real thread** — never a new standalone email.

**Delivery** — exactly one email, to the stamped or resolved work address, composed per Step 5's fixed structure, with **no attachment attempted**. Nothing outward-facing was sent. **Never a clear day while a follow-up draft sits unsent** — an unsent draft is an open item that ages. No mail role that can create drafts → still send the one summary saying so, then stop.

**No fabrication** — no invented recipient, deadline, commitment, resolution or signature.
