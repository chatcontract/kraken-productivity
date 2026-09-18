# The connector prerequisite — `checkRequiredConnectors()`

**This file is the gate every skill in this plugin passes through before it does anything else.** It is not advice and it is not per-skill. A skill that starts gathering, generating, rendering or emailing before this check has passed is broken, whatever its own SKILL.md says.

`references/shared-run-policy.md` owns how a run behaves. **This file owns whether a run happens at all.**

---

## Part 1 — The contract, in one line

**Calendar, Mail and Drive must all be present and usable, or no skill runs.** Chat is optional and its absence never blocks anything.

| Role | Requirement | What it is for |
|---|---|---|
| **Calendar** | **Mandatory** | Meetings, conflicts, and Call Prep's prep blocks |
| **Mail** | **Mandatory** | The delivery channel, and the largest single source |
| **Drive / SharePoint** | **Mandatory** | Where rendered documents are stored and linked from |
| **Chat** | *Optional* | Where a large share of real asks live |

**Every skill runs this gate — the three workers, onboarding, and any skill added later.** A new skill inherits it by calling it; that is its only integration step. There is no per-skill override and no flag that skips the *check*.

**What a block does has exactly one documented variation, and it is onboarding's.**

| Skill | On a block |
|---|---|
| The three workers | Show the card, **stop. No output of any kind** (Part 6). |
| `kraken-onboarding` | Show the card, **then carry on and create the scheduled tasks**, and say in one line that those runs will stay blocked until the missing role is connected. |

**Onboarding is not an exemption from the check — it still runs it and still shows the card.** It differs in what follows, for one reason: it produces no user-facing artefact and reads no user data, it writes only scheduled tasks, and it is the place a person lands when they are *setting the plugin up* — refusing to schedule anything until connectors exist would deadlock exactly the person trying to fix them. Its task-write is therefore permitted despite Part 6's "no writes"; nothing else about Part 6 is relaxed for it.

**This table is the authority.** Where a skill's own SKILL.md disagrees with it about blocking behaviour, this file wins — the usual "the skill's own file wins" rule at the top of the shared policy does not extend to the gate, because a gate a skill can locally override is not a gate.

---

## Part 2 — Where it sits in the run order

```
skill triggered
      |
      v
checkRequiredConnectors()      <- nothing above this line reads any data
      |
      |-- all three mandatory present and usable --> run the skill
      |
      `-- any one missing or unusable --> show the connection card, stop
```

**The gate's own calls sit OUTSIDE the run's call budget and OUTSIDE its clock** — the same treatment shared §10 gives the scheduling offer. Detection reads nothing, and the three probes are the cheapest call each provider offers; charging them to a gathering budget would make a skill cut real coverage to pay for a safety check.

**Nothing expensive happens before the gate returns.** No calendar read, no mailbox search, no chat sweep, no CRM lookup, no web search, no PDF render, no draft, no email, no calendar write. The gate costs a few tool-name comparisons and one probe per mandatory role; the run it prevents costs sixty to seventy tool calls.

**The full opening sequence of every run:**

1. The `date` call that starts the deadline clock.
2. The weekday guard (shared §1), on a scheduled run — a scheduled weekend run exits here, before the gate, so a missing connector can never produce a weekend email.
3. **The connector gate (this file).** Anything missing → render the Connect card and the status table, then **stop**.
4. **Only once the gate has passed:** the shared §10 schedule check, on a manual run.
5. Everything else.

**Nothing happens until the required connectors are connected. Nothing.** Not the run, and **not the scheduling either.**

**Why scheduling is included in that.** Creating a recurring task for a skill that cannot produce anything is a promise the plugin cannot keep: three tasks appear in the person's Scheduled list, fire every weekday, and produce nothing but blocked runs. Worse, it hides the real problem behind the appearance of a completed setup. **A schedule is only worth creating once the skill it schedules can actually run.**

**So a blocked run ends with exactly one thing: the Connect buttons.** No schedule card, no partial output, no "I set this up anyway". Once the connector is in, the person runs the skill again and *that* run — which passes the gate — offers the schedule.

---

## Part 3 — Detection: by role, never by vendor

Sort the available tools once, at run start, by tool-name prefix. **Never ask the user what they use, and never hardcode one vendor as "the" provider of a role.**

| Role | Prefixes that satisfy it |
|---|---|
| **Calendar** | `google_calendar_*`, `outlook_calendar_*`, `microsoft365_*`, any tool exposing list/create events |
| **Mail** | `gmail_*`, `outlook_*`, `microsoft365_*` |
| **Drive / SharePoint** | `drive_*`, `googledrive_*`, `onedrive_*`, `sharepoint_*`, `box_*` |
| **Chat** | `slack_*`, `teams_*`, `googlechat_*` |

**One tool in a role satisfies the role.** Two tools in one role is not better than one — pick deterministically (the one whose domain matches the signed-in identity) and never split a run's reads across two providers of the same role.

---

## Part 4 — Present is not the same as usable

**A connector is not valid because it was connected once.** Authorisations lapse, admins revoke scopes, tenants move. So the gate does not stop at "a tool with the right prefix exists" — it establishes that the role **answers right now.**

**One cheap read per mandatory role, in a single parallel batch** — the smallest call each provider offers, never a data-gathering call. Chunk to at most 3 Microsoft-backed calls per message (shared §3).

| Role | Probe |
|---|---|
| Calendar | list calendars, or a 1-event window |
| Mail | the signed-in profile, or a 1-message list |
| Drive | list the root, or "recent files" with a limit of 1 |

**Classify the answer into one of five states.** The first three block the run; the last two do not.

| State | How it shows | Blocks? | Button |
|---|---|---|---|
| **Not connected** | No tool with that role's prefix exists | **Yes** | **Connect** |
| **Installed but not reachable in this chat** | The connector exists on the account, but its tools are not available to this session — disabled for this chat, or not enabled for this plugin | **Yes** | **Enable** |
| **Expired / auth failed** | 401, `invalid_grant`, "reauthenticate", "token expired" | **Yes** | **Reconnect** |
| **Permission revoked** | 403, "insufficient scope", "access denied" | **Yes** | **Reconnect** |
| **Temporarily unavailable** | 429 (shared §3), 5xx, timeout | **No** — retry per shared §3, then treat as degraded for this run and say so | — |
| **Usable** | The probe returned | **No** | — |

**"Installed but not reachable in this chat" is the state that gets mishandled, so it is called out here.** A registry search will report that connector as *connected*, because on the account it is — and a rule that only suggests *unconnected* connectors then finds nothing to offer and falls through to prose or, worse, to a question. **`suggest_connectors` covers this case explicitly: its own contract names connectors "not yet connected **or whose tools are disabled in chat**."** So this state is a suggest call like any other, and it renders the Enable card. A real run hit exactly this with Gmail and Google Calendar and asked a text question instead — that is the bug this row exists to prevent.

**Never conflate a rate limit with a broken connection.** A 429 means the connector is working and busy, and shared §3 already owns the backoff; blocking the whole plugin on it would be wrong. A 401 means the connector is not working, and no amount of backoff fixes it.

**A probe failure is reported by its real cause, never by a shrug** (shared §12). "Calendar returned 401 invalid_grant" is actionable. "Calendar not available" is not.

---

## Part 5 — What a blocked run shows

**Never a bare error line.** `Calendar not connected.` gives the person nothing to act on. A blocked run shows the status of every role and a way to fix each gap.

### The connector card

**The card is not optional and not best-effort. A blocked run ALWAYS ends in Connect buttons.** Prose instructions are what you write when the session has no registry tool at all — never because a search came back thin.

### Never answer a connector gap with a question

**`AskUserQuestion` is not a substitute for a Connect button, and must never be used for a missing connector.** Not to ask whether the person has connected it, not to offer "continue anyway / stop here", not to ask how to proceed. A question card is text pretending to be an action: it costs the person a decision *and* still leaves them to go and find the connector themselves.

This applies to **every skill in the plugin, onboarding included.** Where a skill's own SKILL.md offers a choice about a connector gap, **this file overrides it.**

The only thing a connector gap produces is: **the status table, the Connect/Enable/Reconnect card, and a stop.** If the person connects the tool and wants to carry on, they re-run the skill — which is one click on a command, and needs no question card to arrange.

Two tools do it, in this order:

**1 · `search_mcp_registry` — search WIDE: brand names AND generic nouns, in one basket.**

**The two tools want different keywords, and conflating them is what breaks this.**

| Tool | What its keywords are for | So they should be |
|---|---|---|
| `search_mcp_registry` | **finding** connectors in the registry index | **brand names *and* nouns together** — its own documented examples are `["asana","tasks","todo"]` and `["gong","meet","zoom"]` |
| `suggest_connectors` | the **label** shown to the person, rendered as "For your {keyword}" | **one generic noun** — `calendar`, not `google calendar` |

A previous version told the search to strip brand names. That was wrong — it is the *display* keyword that must be generic — and it is exactly why a real run searched `email`, `mail`, `inbox`, `messages` and found nothing.

**Search every role in ONE call, with the widest basket that fits:**

| Missing role | Search keywords |
|---|---|
| **Calendar** | `["google calendar","outlook calendar","microsoft 365","calendar","events","scheduling"]` |
| **Mail** | `["gmail","outlook","microsoft 365","office 365","email","mail","inbox"]` |
| **Drive / SharePoint** | `["google drive","onedrive","sharepoint","box","files","documents","storage"]` |
| **Chat** | `["slack","microsoft teams","google chat","messages","chat"]` |

- **Name the real products.** Gmail, Google Calendar, Outlook, Microsoft 365, SharePoint, OneDrive, Google Drive, Box, Slack, Teams — these are what the registry indexes, and leaving them out is what produces an empty result on a role that plainly exists.
- **Searching more than one role at once is fine and preferred** — one call, all the gaps, then one suggest call.
- **A thin first result is not a conclusion.** Widen the basket and search again before you even consider prose.

**2 · `suggest_connectors` — one call, every missing role, with the UUIDs.**

Pass the `directoryUuid` of each match from step 1, plus one generic `keywords` noun per role. **One call for all the gaps**, so the person fixes them together instead of discovering the second after closing the first.

**Reconnecting skips step 1 entirely.** When the role is present but its probe failed on auth (expired, revoked — Part 4), there is nothing to search for: the connector already exists. Take the UUID straight out of the failing tool's own name — they are shaped `mcp__{uuid}__{toolName}` — and pass that UUID to `suggest_connectors`. That is the documented re-authentication path and it renders a **Reconnect** button.

## The ladder — work down it until something interactive is on screen

**A blocked run does not end in a paragraph. Work down this list and stop at the first rung that puts a clickable card in front of the person.**

| # | Try | When it applies |
|---|---|---|
| 1 | **`search_mcp_registry`** with the wide basket above, then **`suggest_connectors`** with the `directoryUuid`s it returned | The normal path. One search call, one suggest call, every gap in it. |
| 2 | **Search again, wider** — add the other providers for that role, and search the role's *category* words (`productivity`, `workspace`, `google`, `microsoft`) | The first basket came back empty or matched only some roles. |
| 3 | **`suggest_connectors` with the UUID from a failing tool name** — `mcp__{uuid}__{toolName}` | The role's tool exists but its probe failed on auth. No search needed; this renders **Reconnect**. |
| 4 | **`suggest_connectors` with whatever UUIDs you did get**, for the roles that matched | Some roles matched and some did not. **Never let an unmatched role suppress the buttons for the rest.** |
| 5 | **`list_connectors`** with that role's keywords | Nothing matched at all. It renders the person's own connectors as an interactive card — not a Connect button, but a live surface they can act on, which beats a sentence. |
| 6 | **Written instructions** | Only after 1–5 have all been tried. |

**Rung 6 is reached only when every rung above genuinely failed** — the session has no registry tool at all, or the calls errored. **A search that found nothing is not a reason to jump to rung 6**; it is a reason to go to rung 2, then 5.

**When you do land on rung 6, say which rung failed and why** — "the registry has no mail connector indexed for this session" — and name the products to add (Gmail, or Outlook / Microsoft 365) and where. **Never claim a card was shown when it was not**, and never describe rung 6 as though it were the normal outcome.

- **Pass every missing mandatory role in one call**, so they are seen and fixed together rather than one gap appearing after another is closed.
- **Include Chat in that same card when it is absent**, labelled optional. One card, four rows, requirements visibly distinct from nice-to-haves.
- **Never send the person to a generic settings page** when the tool can start the flow directly.
- **Never describe the steps in prose while the card is available.** Prose is the fallback, not the default.

### If the card cannot be rendered

Only then print the status table and name the connector to add, by role and by example provider — `a calendar connector (Google Calendar or Outlook Calendar)`. Say plainly that the card could not be shown, so the person knows why they are reading instructions instead of clicking.

### The status table — identical everywhere

**Same table, same order, same markers, in every skill and at setup.** A person should recognise it instantly and never have to work out which line is the problem.

**Your connections**

| Connector | Status |
|---|---|
| Calendar | 🟢 Connected |
| Email | 🟢 Connected |
| Drive / SharePoint | 🔴 Required |
| Chat | ⚪ Optional |

That is the literal output, markers included. Reproduce it exactly: do not substitute words for the markers, and do not reorder or omit rows.

| Marker | Meaning |
|---|---|
| 🟢 Connected | Present, and the probe answered |
| 🔴 Required | Mandatory and missing — the run is blocked on this |
| 🟠 Needs attention | Mandatory and present, but expired or revoked — blocked, and the button says **Reconnect** |
| ⚪ Optional | Chat, absent. Not a problem |

**Rows never reorder and are never omitted** — always all four, even when three are fine. A table that hides what is working makes the reader wonder what else went unchecked.

### The message above the table

Name the skill, name what it needs, stop. No apology, no explanation of why connectors exist.

> **Connect your accounts to continue**
>
> Call Prep needs Calendar, Email and Drive/SharePoint.
> Drive / SharePoint is not connected.

Then the card. Then nothing else.

---

## Part 6 — Blocked means blocked

**A blocked run produces no partial output.** This is the rule most likely to be quietly broken, because partial output feels helpful.

- **No PDF**, not even a thin one.
- **No email**, including a "here is what I could get" one. The block is communicated by the card in the reply, not by something in the inbox.
- **No drafts, no calendar blocks, no writes of any kind — including no scheduled task.** A schedule for a skill that cannot run is a task that fires every weekday and produces nothing (Part 2).
- **No schedule card either.** The shared §10 offer belongs to a run that passed the gate.
- **No "brief with gaps"**, and no offer to run in a reduced mode. A daily brief with no calendar is not a daily brief missing a section; it is not a daily brief.

**A blocked scheduled run does not email either — except once.** Sending the same "connect your Drive" mail at 4 AM every weekday is how someone learns to filter this plugin into the archive.

- **The first blocked scheduled run** sends one `[Blocked]` email naming the missing roles, carrying the status table and what the card would have said.
- **Later blocked runs of that skill send nothing** while the same role is still missing, and log `blocked — <role> unavailable`.
- **When the role returns**, the next run proceeds normally and says nothing about having been blocked.

**The "once" is established by a read, not by writing state.** An earlier draft stored a flag in Call Prep's settings record. That was wrong three times over: two of the three workers have no settings record and are forbidden from writing to the calendar (shared §6); the record is unreachable when Calendar is itself the missing role; and writing it would be exactly the write this Part forbids.

**So the dedupe is a search of the user's own sent mail** — a read, needing no state:

- **Mail usable** → search sent mail for a `[Blocked]` subject from this skill in the last 24 hours. Found → send nothing, log `blocked — <role> unavailable, already notified`. Not found → send the one email.
- **Mail is the missing role** → nothing can be sent at all. Log `blocked — mail unavailable` and exit. This is the one blocked path that reaches the person through no channel, and it is unavoidable: no channel is left.
- **Nothing to clear.** The next run that passes the gate just proceeds and says nothing about having been blocked — there is no flag to reset, which is the point.

---

## Part 7 — Chat is optional, and that is a real difference

**A missing Chat connector never blocks a run and never raises a card on its own.** When Chat is absent:

- The run proceeds on the three mandatory roles.
- The skill says what that costs, once, in its own designated place (shared §13) — the Daily Brief loses its chat sweep, Follow-Ups drops to two sources against its coverage floor, Call Prep loses the internal chatter that usually carries an account's real status.
- The status table shows it Optional, and the card offers **Connect Chat** beside the mandatory ones **only when the card is already up for a mandatory gap.**

**Never present an optional gap with the urgency of a required one.** If Chat is the only thing missing, the run happens and the person is told in one clause — not shown a connection screen.

---

## Part 8 — Reusable, so no skill re-implements it

**Every skill invokes the same procedure. No skill carries its own copy of the logic.**

```
runSkill()
    |
    v
checkRequiredConnectors()
    |
    |- roles  = detect_by_prefix()                 Part 3
    |- states = probe(calendar, mail, drive)       Part 4
    |
    |- all three usable?
    |     yes -> return PASS (plus chat present/absent, for Part 7)
    |     no  -> render_connector_card(missing)    Part 5
    |            render_status_table()             Part 5
    |            return BLOCK                      Part 6
    v
PASS -> continue the run
BLOCK -> stop, no output
```

A skill's own SKILL.md states **one line**: that it runs this gate first and stops on a block. It does not restate the roles, the probes, the states, the table or the card. That duplication is what this file exists to prevent, and a second copy is a copy that goes stale.

**When this file changes, every skill changes with it.** That is the point.

---

## Part 9 — What the gate must never do

- **Never ask the user which providers they use.** Detection is by prefix (shared §3).
- **Never treat its own probe failure as the user's fault.** A 5xx is the provider's problem: say so, and retry per shared §3.
- **Never block on Chat.**
- **Never pass a role because a different role's tool is present.** A mail connector that happens to carry calendar scopes still has to answer the calendar probe.
- **Never cache a pass across runs.** Every run re-checks (shared §13): a connector that worked at 4 AM can be revoked by 6 AM, and the 6 AM skill has to find that out itself rather than trusting what the 4 AM skill saw.
- **Never render a Connect button that does nothing.** If the flow cannot actually be started, print the fallback instructions — a dead button is worse than a sentence.
