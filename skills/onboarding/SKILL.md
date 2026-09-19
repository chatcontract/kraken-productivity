---
name: onboarding
description: Schedules the Productivity weekday skills — Call Prep 4 AM, Daily Brief 6 AM, Follow-Ups 4 PM, Monday to Friday. All three, or one when a skill is named. Runs the mandatory-connector gate first, resolves skill names whatever the namespace, deletes legacy tasks so nothing double-sends, then asks you to set Permissions to Automatically approve. Creates tasks only. Use /productivity:onboarding, "onboard me", or after a plugin update.
---

# Onboarding

Creates the recurring scheduled tasks. **It creates tasks. It does not run any of the three skills, read any data, or produce any brief, report or plan.** Finish in under a minute of actual work — a card waiting on a human does not count against that, and never rush a blocker decision to beat a clock. Budget ~12 tool calls in single-skill mode and **up to ~20 in full mode** — the Step 3 preflight batch, three creates, and as many as ten legacy deletes. The ceiling is there to stop exploration, never to skip a delete.

**Two modes:**

| Mode | When | What it touches |
|---|---|---|
| **Full** (default) | `/productivity:onboarding`, "onboard me", "set up my Productivity skills", or after a plugin update | All three tasks. |
| **Single-skill** | A target skill is named — by shared §10's offer, or by a person asking for one ("just schedule my daily brief") | **That one task only.** The other two are left completely alone: not created, not updated, not deleted, not mentioned. |

Everything below applies to both modes. **In single-skill mode, every instruction phrased around three tasks means the one target skill** — "all three", "the three", "each of the three", "the three prompts", "Repeat for all three". There is no step whose three-ness survives the mode. **The one thing that never changes is that this skill is the only writer of scheduled tasks** — see *Why the worker skills hand off here*.

## How to invoke these skills

**Each skill is namespaced by the plugin, so the exact command is the plugin name, a colon, then the skill name:**

| Skill | Command |
|---|---|
| Onboarding — run this first | `/productivity:onboarding` |
| Call Prep | `/productivity:call-prep` |
| Daily Brief | `/productivity:daily-brief` |
| Follow-Ups | `/productivity:follow-ups` |

**Plain English works too** — "onboard me", "what's on my day", "find my follow-ups" — and is what most people use. The namespaced command is what to give someone when it matters that they hit the right skill first time: in setup instructions, in a runbook, or when two plugins expose similarly named skills.

**The namespace is never matched against when *resolving* a name** (see *Resolving skill names*). It is how a person types the command; it is not how this skill identifies a target.

## Ground rules

1. **Never prompt for days or times.** The schedule is fixed. No AskUserQuestion for scheduling.
2. **Never run the underlying skills.** No calendar reads, no email reads, no web research, no drafts, no briefs. **Detecting that a connector exists is not reading it** — the preflight in Step 3 checks which roles are *available* by tool name and reads nothing at all. If you find yourself listing events or searching mail, you have crossed the line.
3. **Reconcile, never skip.** List existing tasks first, then bring **every task in scope** to the installed plugin version — create the missing ones, **overwrite the ones that already exist**, and **delete their legacy equivalents** (see *Migration*). Scope is all three in full mode, the named skill in single-skill mode.
4. **Ask only what is genuinely missing.** Nothing missing → ask nothing.
5. **Never assume a bare skill name resolves.** Always resolve per *Resolving skill names*.
6. Cron is evaluated in the user's **local** time — write local times directly.
7. **Always finish with the Step 7 table plus the permissions block — and nothing beyond it.** The single exception is a Step 3 **blocker stop**: no scheduling tool means no task exists to set permissions on, so that run ends with the blocker stated and nothing else.
8. **The schedule is Monday to Friday. Strictly.** Never create, widen or suggest a cron including Saturday or Sunday.

## The fixed schedule

| # | Skill | Cadence | Local time | Cron |
|---|-------|---------|-----------|------|
| 1 | `call-prep` | Weekdays Mon–Fri | 4:00 AM | `0 4 * * 1-5` |
| 2 | `daily-brief` | Weekdays Mon–Fri | 6:00 AM | `0 6 * * 1-5` |
| 3 | `follow-ups` | Weekdays Mon–Fri | 4:00 PM | `0 16 * * 1-5` |

**The schedule is Monday to Friday only.** (Manual invocations are unrestricted — the weekend rule governs unattended runs, per shared §1.) The `1-5` day field is fixed — never widen it to `0-4`, `0-6`, `*`, or anything including day 0 or day 6, not even if the user asks for weekend or Monday-morning coverage. Each skill also carries its own weekend guard, so the rule is enforced twice: in the cron and in the skill.

Call Prep preps **today's** calls at 04:00, early enough that even an 8 AM call has its prep block booked hours ahead. The trade-off is that a meeting added to the calendar after 4 AM gets no block — say so in one clause if the person asks, and point them at running the skill by hand. It delivers by **booking a private prep block before each external call**, not by email — so its scheduled task produces nothing in the inbox unless the run fails.

**A manual Call Prep run works on any day, weekend included**, and where today has no calls left ahead of the clock it targets the next day that does. Never widen the cron to cover a weekend.

## Thin task prompts — the schedule points at the skill, it does not copy it

**A scheduled task stores a copy of its prompt, taken when the task was created. Updating the plugin does not update that copy.** This plugin's predecessor worked around that by baking every policy detail into a ~700-word prompt per task, which created the problem it was trying to solve: each fix then existed in two places — the SKILL.md and the stored prompt — and the copies drifted. One shipped with a sentence duplicated mid-clause; another kept a rule the skill had already retired.

**The prompts this skill generates are therefore deliberately thin.** Each one carries only:

1. The **version stamp**, so a stale task is visible.
2. The **resolution preamble**, so the right skill is found whatever the namespace.
3. The **run parameters** — the resolved local timezone (never asked for; see *Timezone*), the delivery address, and for Call Prep the "today, book a block per call" instruction.
4. A **four-line safety floor** — the rules that must hold even if something goes wrong loading the skill: weekend guard, one email to the stamped address only, never send outward-facing mail, never ask a question.
5. One line handing the complete run contract back to the skill.

Everything else — deadlines, rate-limit backoff, coverage floors, correctness gates, the classification rule, delivery and attachment handling — lives in the skill and in `references/shared-run-policy.md`, which are **real plugin content and therefore update the moment the plugin updates.** So a plugin update now reaches a live schedule without re-onboarding, for everything except the version stamp and the parameters. Re-running onboarding remains cheap, safe, and the way to refresh the stamp.

**Never put `${CLAUDE_PLUGIN_ROOT}` in a task prompt.** That placeholder resolves in *plugin* skill content; a scheduled task is stored outside plugin content, so it would be passed through as a literal path and the run would fail to find the renderer. Task prompts say *what* to do; the skill supplies the path.

## Version reconciliation

**Read the installed version at the start of every run:**

```bash
python3 -c "import json;print(json.load(open('${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json'))['version'])"
```

**Stamp it into every task.** First line of each prompt:

> `Productivity v<VERSION> — prompt generated by onboarding. If this line names an older version than the installed plugin, re-run onboarding to refresh.`

And suffix each description with ` · v<VERSION>`.

**Refresh unconditionally.** Do not try to compare a stored prompt against the installed version, and do not ask the user what version they are on — an unconditional overwrite is cheaper than any comparison and is the only thing that leaves no task behind. For each **in-scope** task:

- **Absent** → `create_scheduled_task`. Report `created v<VERSION>`.
- **Present** → `update_scheduled_task` with the freshly generated `prompt`, `description` and `cronExpression`. **Always** — an unconditional overwrite is cheap and is the only thing that guarantees no task is left stale. Report `updated to v<VERSION>`.

Never report a task as "already scheduled" and move on; that is the stale-version bug.

Use the same three task IDs every time — `daily-brief`, `follow-ups`, `call-prep` — and **never invent versioned IDs** like `daily-brief-v2`, which would leave the old task running alongside the new one and double every email.

## Single-skill mode

Triggered when a target skill is named. Shared §10 is the common path: a manual run of one worker skill found no task for itself, offered to schedule it, the person said yes, and that skill invoked this one naming itself. A person asking directly — "schedule just the follow-ups" — is the same thing.

**Do exactly one skill's worth of work:**

- **Resolve the named skill** per *Resolving skill names*, so `daily brief`, `daily-brief` and `productivity:daily-brief` all land on the same target.
- **Create or update only its task**, with its own row from *The fixed schedule* — same cron, same task ID, same title, same stamped prompt as full mode would have written. **Nothing about the schedule changes because the mode did.**
- **Delete only its legacy IDs** from the *Migration* table — the row for that skill, not the whole table. A legacy task belonging to a skill that is out of scope keeps running, which is correct: that skill has not been migrated yet.
- **Report one row**, then the permissions block naming **only that skill**.
- **Never create the other two, and never mention them.** Not as a suggestion, not as a "you might also want", not as a note that they are unscheduled. Someone who scheduled one skill made a choice; listing the others turns a completed action into a sales pitch. If they want the rest, they will run those skills, or run `/productivity:onboarding`.

**If the named skill cannot be resolved to one of the three**, say so plainly and stop. Do not fall back to scheduling all three — that is the opposite of what was asked, and it creates two tasks nobody requested.

## Why the worker skills hand off here

A worker skill could technically create its own task. It must not, and the reason is specific: **the prompts written here are the only ones carrying the version stamp and the "unattended scheduled run" marker, and that marker is the sole thing that identifies a run as scheduled when it later fires** (shared §1).

A task written without it would fire, be treated as a manual run, skip the weekend guard, and — because shared §10 checks whether a task exists — quite possibly offer to schedule itself all over again. One writer avoids all of that. So a worker skill's yes arrives here, in single-skill mode, and this skill does the writing.

## Migration — remove legacy tasks before creating the new ones

This plugin ships under four names — Productivity, Haynes, AllNeurons and Roots — and earlier releases used others. A user who onboarded under any of them has scheduled tasks whose IDs this skill no longer writes to, so they would keep firing **alongside** the new ones and the user would get two of every email. **Productivity is this package; every other prefix is legacy here.**

**Delete any scheduled task whose ID matches a legacy ID for a skill in scope**, using the scheduled-tasks delete action, in the same parallel batch as the creates. Full mode covers every row below; single-skill mode covers only its own row:

| Legacy task ID | Replaced by |
|---|---|
| `haynes-daily-brief`, `allneurons-daily-brief`, `roots-daily-brief`, `an-daily-brief` | `daily-brief` |
| `haynes-follow-ups`, `haynes-follow-up`, `allneurons-follow-ups`, `allneurons-follow-up`, `roots-follow-ups`, `roots-follow-up`, `an-follow-ups`, `an-follow-up` | `follow-ups` |
| `haynes-call-prep`, `allneurons-call-prep`, `roots-call-prep`, `an-call-prep` | `call-prep` |

Only delete IDs that actually appeared in the task list from Step 3 — never attempt a delete for one that isn't there. Report each removal in the Step 7 table as `legacy <id> removed`. A delete that fails is reported and does not stop the run, but **say plainly that the old task may still be sending**, so the user can remove it by hand.

Deleting a legacy task loses that task's run history and stored tool approvals — unavoidable, since the ID changes. Mention it in one clause, not a paragraph.

## Resolving skill names

The three may be installed standalone (`daily-brief`) or inside a plugin (`<plugin>:<skill>`).

**The namespace is never matched against — it is discarded before comparison.** Whatever the plugin is called and however spelled or capitalized — `productivity`, the same name in any casing, a misspelling of it, `anthropic-skills`, anything at all — only the part after the final `:` is compared. Never hardcode, guess, or ask about the namespace.

**Comparison is normalized:** lowercase, then strip every non-alphanumeric character. So `daily-brief`, `daily_brief`, and that same name capitalised or punctuated any way at all, every one normalizes to `dailybrief`.

For each target, scan the available-skills list and take the first match:

1. Normalized post-colon name **equals** the normalized target.
2. Normalized post-colon name **ends with** the normalized target.
3. Same two checks after stripping a leading brand segment — this package's own `productivity-`, or any legacy prefix in the *Migrating from an earlier install* table above — from **both** sides before normalizing. This covers `productivity:daily-brief` and keeps earlier installs resolving to the same skill. Strip the hyphenated segment, never bare letters from the normalized string.
4. Normalized post-colon name **contains** the distinctive tokens — `dailybrief`, `followup`, `callprep` — and **exactly one** entry matches. Never guess between two candidates. Note `followup` also matches `follow-ups`, which is the correct skill.

Ties at the same tier: prefer a namespace normalizing to `productivity`; otherwise take the first. Record the resolved name verbatim.

No match → still create the task (the plugin may be installed later) and mark it `created — skill not currently visible`.

## What this skill cannot do — say it plainly, never pretend otherwise

**Permissions** on a scheduled task is **UI-only**. No parameter on the create or update action exposes it — they cover the task's id, title, description, prompt, schedule, completion notification and enabled flag — and nothing that touches permissions.

It defaults to *Manually approve*. Left there, every run halts waiting for a connector approval, and an unattended 6 AM run never completes.

So this skill **cannot** flip it, and must never claim it did or say "I've set them to automatic". It creates the tasks correctly and states the one thing the user must change — in a single line, per Step 7.

**Connector approvals cannot be pre-authorised from here either, and this skill must not pretend otherwise.** An approval prompt appears when a tool is first *called*, so the only way to trigger one is to make the call — which is exactly the data read Ground rule 2 forbids, and which would be doing the skills' work rather than scheduling it. The preflight above can tell you a connector *exists*; it cannot tell you the first unattended run will be allowed to use it.

**There are exactly two real remedies, and Step 7 gives the first:**

1. **Set Permissions to Automatically approve** on each task. This is the actual fix, and without it an unattended run stops on a prompt nobody is watching.
2. **Run each skill once by hand**, while you are watching, so any approval prompt surfaces where someone can clear it. This is a *confidence* step, not a fix: remedy 1 is what makes unattended runs work. Offer it in one clause, **only on a person-initiated full-mode run**, and never in place of remedy 1. On a §10 handoff, say nothing about it — the person is already doing exactly that.

## The only questions allowed

At most **two** cards in a whole run, and neither of them is about a connector:

- **Delivery email** — skip if the user's own address is known from session context. Use their own address, never anyone else's.
**Timezone is never a question.** It is resolved, always — see *Timezone* below.
**No card for a connector gap, ever.** A missing or unreachable connector is answered with a Connect / Enable / Reconnect **button** from the connector prerequisite, plus the status table. That includes a missing tracker. If the delivery address is still unknown after session context, it is asked in one small card of its own — that is about an address, not a connector.

- **The permissions confirmation** — one card at the very end of Step 5, asking whether Permissions has been set to Automatically approve. Never re-asked.

Nothing else. No day pickers, no time pickers, no "which of these three", no confirmation before creating, **and no card about any connector, mandatory or optional** — connectors get buttons. Never ask which plugin the skills came from — resolve it.

## Procedure

**Seven steps, in this order. Each one either produces something the next needs, or decides whether there is any point continuing.**

| # | Step | Produces | Skipped when |
|---|---|---|---|
| 1 | Establish mode and invocation | full vs single-skill; person vs handoff | never |
| 2 | Run the connector gate | the card and status table, if anything is missing | on a §10 handoff |
| 3 | Preflight | existing tasks, legacy tasks, version, timezone, dependencies, roles | preflight questions skipped on a handoff |
| 4 | Resolve skill names | the real name of each in-scope skill | never |
| 5 | Generate task prompts | one stamped prompt per in-scope skill | never |
| 6 | Write the tasks | the created/updated tasks, legacy ones deleted | never |
| 7 | Report and hand over permissions | the table, the gap block, the permissions block, one card | only on a Step 3 blocker stop |

**Step 1 — Establish the mode, and whether this is a handoff.** Was a target skill named? No → **full mode**, all three. Yes → **single-skill mode**, that skill only. Everything after this reads "in scope" accordingly.

Then note *how* you were invoked, because it changes what Step 1 does:

| Invoked by | Preflight |
|---|---|
| A person — `/productivity:onboarding`, "onboard me", "schedule my follow-ups" | **Run it in full**, per Steps 2 and 3. |
| **A worker skill's §10 handoff** | **Skip the preflight entirely.** Do the task list read, the version read, and nothing else. |

**Why the handoff skips it.** That worker is already mid-run: it sorted the connector roles at its own start (shared §7), it already called `list_scheduled_tasks` (shared §10), and it already took the single `date` reading that shared §2 says is taken **once** per run. Re-detecting the roles tells nobody anything new, a second `date` call breaks §2, and printing a gap block mid-run collides with the coverage gaps the worker is about to report itself.

**And ask nothing on a handoff.** The worker has already spent its one permitted question on the offer that sent you here (shared §10); a second card is exactly the "never make the person ask twice" failure that rule exists to prevent. No blocker card either — the worker is running, so its connectors evidently work. Create the task, report one line, print the permissions block, return.

**Step 2 — Run the connector gate.** `${CLAUDE_PLUGIN_ROOT}/references/connector-prerequisite.md` owns it and is the authority: **Calendar, Mail and Drive/SharePoint are mandatory**, Chat is optional, detection is by tool-name prefix, and each mandatory role gets one cheap probe because present is not the same as usable.

**Onboarding runs the gate like every other skill, and shows the same card — what differs is what happens next.** Its Part 1 table documents the variation: show the card, show the status table, then **carry on and create the tasks**, and say in one line that those scheduled runs will stay blocked until the missing role is connected. Scheduling for later is still useful while a connector is being connected now, and refusing would deadlock the very person trying to fix it.

**Skip this step on a §10 handoff.** The worker that sent you here is mid-run and already passed the gate at its own start; running it again costs three probes and tells nobody anything new.

**Step 3 — Preflight: list, version, timezone, dependencies, roles.** One parallel batch, and **nothing in it reads the user's data**:

- The scheduled-tasks list action — note which in-scope task IDs already exist (that decides create vs update) **and which of their legacy IDs from *Migration* are present** (that decides what to delete).
- The `plugin.json` version read above.
- `date`, for the timezone — **`date +%Z` and `date +%z` together**, so both the name and the offset are captured.
- **One dependency check**, reporting each package separately, because they fail differently:
  ```bash
  python3 -c "
  for m in ('reportlab','pypdf','pypdfium2'):
      try: __import__(m); print(m,'ok')
      except ImportError: print(m,'MISSING')"
  ```
  A combined `import reportlab, pypdf` cannot tell which one failed, and the two have very different consequences (see the table).

Then check the connector roles, **by tool name only**. A role is present if a tool for it is in this session; that is a look at the tool list, not a call to the tool. **One tool in a role is enough** — the point is that the role is covered, not which vendor covers it.

### Tier 0 — the one hard blocker

| Role | Any of | Missing means |
|---|---|---|
| **Scheduled tasks** | the session's scheduling tool | **Stop.** There is nothing to create a task with, so nothing this skill does is possible. State it plainly and end the run; no card, no partial setup. |

### Tier 1 — the mandatory set: calendar, mail, drive

**The connector gate enforces these at the start of every run: without all three, no skill produces output.** A gap here is answered with a **Connect / Enable / Reconnect button**, never a question. The impacts below are what to put in the report — they are not a menu of choices.

| Role | Any one of | If skipped, the real impact |
|---|---|---|
| **Mail** | **Gmail** · **Outlook / Microsoft 365 mail** | **The heaviest loss.** Mail is where the Daily Brief and Follow-Ups *deliver*, so with none connected neither arrives at all. It is also Follow-Ups' entire subject matter: no mailbox means **no drafts**, not merely no delivery. And it is half of the Daily Brief's already-handled check, so items you have answered by email will read as still open. Call Prep still delivers — it books calendar blocks — but loses the email history that gives an account its real status, and loses its failure report, which then shows up only as a calendar marker. |
| **Calendar** | **Google Calendar** · **Outlook / Microsoft 365 Calendar** | **Nothing runs without it.** Call Prep has no meetings to classify and nowhere to book; The Daily Brief loses every meeting, the timeline and all conflict detection, which is most of what a 6 AM brief is for. Follow-Ups still runs, without the meeting signal. |
| **Drive / SharePoint** | **Google Drive** · **OneDrive / SharePoint** · **Box** | Where every rendered document is stored and linked from. Call Prep's briefings have nowhere to live, so its prep blocks have nothing to link to, and the Daily Brief loses its fallback when the mail tool cannot attach. It is also Call Prep's research source for proposals, SOWs, security reviews and prior briefings. |

### Tier 2 — recommended, reported not asked

Each of these makes the output materially better. **None of them blocks anything** — unlike the mandatory three above — and a task created without one picks it up on a later run with no re-onboarding. **Where one is missing it still goes into the same `suggest_connectors` call, so the person gets a button rather than a sentence** — it simply does not stop the run.

| Role | Any one of | What you lose without it |
|---|---|---|
| **Tracking / tickets** | **Jira** · **GitHub** · **Linear** · **Asana** | The Daily Brief's *Due today & overdue* falls back to an email and chat keyword sweep, so **undated open work goes unreported entirely** — the commonest silent gap. Call Prep also loses ticket status as evidence for whether a commitment is genuinely still open. **This is the one Tier 2 role worth connecting before the first run**, because what it covers nothing else covers. |
| **Call intelligence / transcripts** | a meeting-recording or transcript connector | Call Prep's highest-value source. Briefs still render, noticeably thinner — no record of what was actually promised, no objections as they were really phrased, none of the words the other side used for their own problem. |
| **CRM** | **Salesforce** · **HubSpot** | No stage, amount, renewal date or last-activity signal, so Call Prep's call-at-a-glance strip is largely empty and Follow-Ups cannot rank by deal proximity. |
| **Chat** | **Slack** · **Microsoft Teams** · **Google Chat** | A large share of real asks live in chat, and none of them will be seen. The Daily Brief loses its chat sweep — the source of most *Needs attention* items. Follow-Ups' 10-day coverage floor drops from three sources to two, so a promise made in chat is invisible. Call Prep loses the internal chatter that usually holds an account's real status. **The most valuable of the optional roles.** |
| **Web search** | always available | No public signal — news, funding, leadership moves. The brief says "no recent public signal found" and leans on internal history, which is usually the better source anyway. |

### Tier 2 — the renderer's Python packages

| Package | Missing means |
|---|---|
| **`reportlab`** | **No PDF at all.** Daily Brief and Call Prep fall back to content inline in the email body — still delivered, just not as a document. |
| **`pypdf`** | PDFs still render; the renderer falls back to a weaker self-check. Worth fixing, not urgent. |

Install line: `pip install --break-system-packages reportlab pypdf pypdfium2` (`pypdfium2` is optional — it adds the near-empty-page check).

### Timezone — resolved, never asked

**Every task is scheduled in the person's own local timezone, and the schedule is always the same wall-clock time for them: 4 AM, 6 AM, 4 PM.** Cron is evaluated locally, so the times in *The fixed schedule* are written as-is and need no conversion.

**Never ask what timezone someone is in.** It is on the machine, and asking is both avoidable friction and a chance to get it wrong. Resolve it in this order and stop at the first that answers:

1. **`date +%Z` / `date +%z`** from the preflight batch. This is the machine's own timezone and is the answer in almost every case.
2. **The connected calendar's own timezone**, if `date` somehow returns nothing usable.
3. **Write the local times anyway.** Cron is already evaluated in local time, so an unresolved *name* does not change when the task fires — it only means the stamped `TIMEZONE` parameter is less specific. Stamp what you have (`local`), note it in one clause in the Step 7 report, and carry on.

**A task is never scheduled in UTC, never in the plugin author's timezone, and never at a converted time.** If someone's machine says `Asia/Kolkata`, their Daily Brief fires at 6 AM IST — not 6 AM UTC, and not 11:30 AM local.

### What to do with all that

**Tier 0 missing → stop.** State it and end. Nothing else applies.

**Any mandatory role missing → a button, never a question.** `${CLAUDE_PLUGIN_ROOT}/references/connector-prerequisite.md` owns this entirely, and it overrides anything here: work its ladder until a Connect / Enable / Reconnect card is on screen, show the status table, and **do not raise an `AskUserQuestion` about the gap.**

**There is no "continue anyway" choice to offer.** An earlier version asked one — *connected them just now / continue anyway / stop here* — and a real run showed that card instead of the buttons, because the two connectors involved were installed but not reachable in this chat and the search reported them as connected. The gate's state table now covers that case, and the question is gone. Deciding how to proceed is not the person's problem to solve in a dialog box: they need the connector, and the button is the connector.

**A missing tracker is also a button, not a question.** Include it in the same `suggest_connectors` call as any mandatory gap, so one card carries everything. Never ask "connect a tracker first?" — and never suggest or ask about the other Tier 2 roles, which are reported and nothing more.

**What onboarding does differently from the three worker skills** is only what happens *after* the card: it creates the tasks anyway (Part 1 of the gate file), and says in one line that those runs stay blocked until the connector is in. It does not ask permission to do that.

**Only if the gate's whole ladder failed** — no registry tool in the session, or the suggest call errored — fall back to words: name the role, the vendors that satisfy it, and where to connect them, and say which rung failed. **Never lead with the manual instruction.**

**Then report and proceed** per Step 7.

**Step 4 — Resolve.** Resolve every in-scope skill name — all three in full mode, the named one in single-skill mode. Email comes from session context. Ask only for what is still unknown, in one batched question.

**Step 5 — Generate a prompt per in-scope skill** from the template below, stamped with the version. Three in full mode, one in single-skill mode.

**Step 6 — Write everything in a single message, in parallel:** every in-scope create/update plus their legacy deletes. In single-skill mode that is one create/update and possibly one delete — still one message. Use these exact task IDs and titles. **The title is a real parameter on the create and update actions** — it is the display name in the **Scheduled** list, and it is what the Step 7 instructions tell the user to look for, so pass it there and keep the string exact. The `description` is the separate one-line summary below it:

| Task ID | Title (exact) |
|---|---|
| `daily-brief` | `Daily Brief` |
| `follow-ups` | `Follow-Ups` |
| `call-prep` | `Call Prep` |

### The prompt template

Substitute `<VERSION>`, `{{SKILL}}` (the resolved name), `<target>` and `<tokens>` per skill, plus `{{TIMEZONE}}` and `{{USER_EMAIL}}`. The per-skill values are in the table that follows.

> Productivity v`<VERSION>` — prompt generated by onboarding. If this line names an older version than the installed plugin, re-run onboarding to refresh.
>
> Invoke the skill `{{SKILL}}`. If no skill by that exact name is available, resolve it rather than giving up. These ship inside a plugin and the namespace is irrelevant — ignore everything before the final `:` in every candidate, whatever it is called and however spelled. Compare only the post-colon part, normalized (lowercase, strip non-alphanumerics). Take, in order: (a) normalized equals `<target>`; (b) normalized ends with it; (c) matches after stripping a leading brand segment — `productivity-`, or any other brand prefix — from both sides; (d) if and only if exactly one entry contains `<tokens>`, that one. Only if none match, email {{USER_EMAIL}} a one-line note that the skill is not installed, and stop.
>
> Run parameters: `TIMEZONE = {{TIMEZONE}}` · `DELIVERY_EMAIL = {{USER_EMAIL}}` · `<MODE LINE>`
>
> This is an unattended scheduled run — which is what makes the weekend exit below correct here, and is also why it must never be applied to a person invoking the skill by hand. **Safety floor, which holds regardless of anything else:** (1) before any other tool call, compute the weekday in {{TIMEZONE}} and exit immediately with no output if it is Saturday or Sunday — `<WEEKEND NOTE>`; (1b) then run `references/connector-prerequisite.md` — Calendar, Mail and Drive/SharePoint are mandatory, and a missing or unusable one stops this run with no output beyond what that file specifies; (2) send exactly one email, to `{{USER_EMAIL}}` and no one else, with no cc and no bcc; (3) never send any outward-facing message to anyone else, under any circumstance; (4) never ask a question, never offer to schedule anything (a scheduled task offering to schedule itself is absurd — shared §10's offer is for manual runs only), never pause for permission to read a connected source.
>
> The skill's own SKILL.md, `references/connector-prerequisite.md` and `references/shared-run-policy.md` carry the complete run contract — deadlines and time budgets, rate-limit backoff, coverage floors and caps, the correctness gates, status verification, rendering, and delivery and attachment handling. **Follow them exactly as written there.** They are the current version of those rules; this prompt deliberately does not restate them, so do not treat its brevity as permission to simplify the run.

| Task ID | Cron | `<target>` | `<tokens>` | `<MODE LINE>` | `<WEEKEND NOTE>` |
|---|---|---|---|---|---|
| `daily-brief` | `0 6 * * 1-5` | `dailybrief` | `dailybrief` | `MODE = today's brief` | this is a scheduled unattended run, so it is Monday to Friday only |
| `follow-ups` | `0 16 * * 1-5` | `followups` | `followup` | `MODE = full sweep, drafts only — never send a follow-up` | this is a scheduled unattended run, so it is Monday to Friday only |
| `call-prep` | `0 4 * * 1-5` | `callprep` | `callprep` | `MODE = prep TODAY's external calls; book a prep block per call, do not email unless the run fails` | this is a scheduled unattended run, so it is Monday to Friday only — **today's weekday is the only check**, because a 4 AM run preps today |

**Descriptions** (suffix each with ` · v<VERSION>`):

- `Daily Brief` — Weekday 6 AM briefing: today's meetings, conflicts, what's due, open asks, emailed as one PDF.
- `Follow-Ups` — Weekday 4 PM sweep: finds who needs a follow-up, drafts replies in your voice, never sends.
- `Call Prep` — Weekday 4 AM prep: a private prep block before each external call today, with the dossier linked.

**Step 7 — Report, then the permissions instructions. Nothing else.**

First print one compact table: skill, cadence, local time, status (`created v<VERSION>` / `updated to v<VERSION>` / `created — skill not currently visible`), plus a row per legacy task removed.

**Then, only if the preflight found anything missing**, one short block naming each gap and what it costs — one line each, in the words of the Step 3 tables. A clean preflight gets no block at all: a list of things that are fine is noise.

Order it by what it actually costs the client:

1. **Any Tier 1 gap first, in bold** — mail, calendar or chat — with the impact, and the fact that they chose to continue. This is the record of an informed decision, so it belongs in writing rather than only on a card that has been dismissed.
2. **No tracker**, if that is the case, in one line: undated open work will go unreported until one is connected.
3. **Everything else** in one line each, plainly. A missing renderer package belongs here, not at the top: it has a documented fallback.

End that block with one clause saying gaps close themselves — connect the tool and the next scheduled run picks it up, with no need to re-onboard.

Then print this block **verbatim**, substituting only `<VERSION>` — plus, in single-skill mode, the opening line and the skill list, exactly as described immediately after the block. Every name and label below is the exact string in the interface — do not paraphrase, retitle or "tidy" any of them:

> ## Enable automatic skill execution
>
> All three skills are installed and scheduled on the cadence above, running plugin v`<VERSION>`.
>
> To ensure they run automatically each day without requiring manual approval, update the schedule permissions for each one:
>
> 1. Go to **Scheduled** in the sidebar.
> 2. Locate the skill and click **Edit**.
> 3. Click **Edit** again to open the schedule settings.
> 4. Under **Permissions**, change **Manually approve** to **Automatically approve**.
> 5. Click **Save**.
>
> Repeat for all three skills:
>
> - **Daily Brief**
> - **Follow-Ups**
> - **Call Prep**
>
> Once **Automatically approve** is set, each skill runs on its schedule without asking you to approve anything.
>
> To re-run this setup at any time — after a plugin update, or to clear duplicate tasks — use `/productivity:onboarding`.

**In single-skill mode, two lines change and nothing else does.** The opening line becomes `**<Title>** is scheduled on the cadence above, running plugin v`<VERSION>`.`, and the "Repeat for all three skills" list collapses to the single bullet for that skill — drop the word "Repeat" and the other two bullets. **In full mode, if any skill was reported `created — skill not currently visible`, the opening line says "scheduled" rather than "installed and scheduled"** — the task exists, the skill does not yet, and claiming otherwise sends the person looking for something that is not there. The numbered steps, every interface string, and the closing line stay exactly as written. **Never list a skill that was not scheduled this run**, which would send the person hunting in Scheduled for a task that is not there.

**Exact strings — never alter these.** The three task titles are `Daily Brief`, `Follow-Ups` and `Call Prep` — that capitalisation exactly, including the hyphen and capital **U** in **Follow-Ups**. The sidebar section is **Scheduled**, not "Schedule" or "Schedules". The button is **Edit**, clicked **twice** — once on the task, once again to reach the schedule settings. The setting is **Permissions**, its values are **Manually approve** and **Automatically approve**, and the confirm button is **Save**. If you find yourself writing "Automatic Approval", "Auto-approve", "Settings" or "Productivity Follow-ups", you have got it wrong — go back to the strings above.

In full mode, list the three in schedule order — Call Prep (4 AM), Daily Brief (6 AM), Follow-Ups (4 PM). In single-skill mode there is one bullet.

**Then ask once whether it is done, and stop.** One `AskUserQuestion` card, the last thing in the run: *"Set Permissions to Automatically approve for each task?"* — **Done** / **I'll do it later**.

That card is the whole point of the block above. Left on *Manually approve*, every unattended run halts on a prompt nobody is there to click, and the person discovers it days later by noticing nothing ever arrived. **Asking closes the loop; printing instructions and hoping does not.**

- **Done** → acknowledge in one line and stop.
- **I'll do it later** → one line saying what that costs: the tasks exist but will not complete unattended until it is set. No lecture, no repetition.
- **No answer** → nothing further. Never re-ask, and never claim it was set.

**Then stop for real.** No second switch, no "Only on this computer" explanation, no Run-now fallback, no caveats, no recap of what the skills do, no offer to run one. The table, that block, and that one card **are** the entire ending. If you are about to add another paragraph, don't.

**"Stop" means stop adding to this output — it does not end the caller's run.** When a worker skill invoked this one via shared §10, control returns to that skill, which prints its own one line and then does the work the person actually asked for. Never treat the end of onboarding's report as the end of the session.

## Failure handling

- A failed create, update or delete → report that row as failed with the error, continue with the rest, and still finish with the table **and the Step 7 permissions block**. Never abandon the remaining work.
- An unresolved skill name → **not** a reason to skip. Create the task with the resolution preamble intact and flag it in the table.
- A failed version read → stamp `v(unknown)` and still write **every task in scope** — all three in full mode, the one target in single-skill mode. A failed version read never widens the scope.
- A **blocker stop** at Step 3 (no scheduling tool) legitimately ends without the Step 7 block — there is no task to permit. Every other run that ends without it is incomplete.
- A run that ends without the Step 7 permissions block is incomplete. A run that pads past it is also wrong. A run that leaves an **in-scope** task un-refreshed, or an in-scope legacy task in place, is a **failed** run even if it reports success.
- **A single-skill run that creates more than the one task it was asked for is a failed run**, even though every task it wrote is correct. Scope was the instruction.
