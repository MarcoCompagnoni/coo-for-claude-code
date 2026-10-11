# I run 15 Claude Code sessions as a team. One of them is the COO.

Here is the org chart, the rules, and the numbers, including the ones that are not where they should be.

## The problem

I work on several projects at once: a real-estate pipeline, a couple of small online businesses, some data
tools, research. Each one has its own Claude Code session, and each session does real work: it writes code,
fills spreadsheets, prepares pages for me to review, runs analyses.

Agents that work still need direction. Someone has to decide what each session does today, check that what
it says is done is actually done, and bring me only what needs me. With fourteen project sessions, reading
fourteen chats is not a plan. For the first weeks that is what I did, and the chats were where proposals,
half-finished work and questions went to die.

So I gave the sessions a COO. It is another Claude Code session, with one job: run the others.

## The shape

There are four kinds of things in the system.

- **The CEO, me.** I read one file, the desk, and answer by code. `RR1 pay` is a complete answer.
- **The COO session.** It delegates, verifies and reports. It never does project work: every task goes to the
  session that owns it. It writes the board (one row per project, state only) and the desk.
- **The project sessions.** Each one lives in its own folder with three files: `README.md` (what is where),
  `CLAUDE.md` (the rules, the goal and what «done» means, how to deal with the COO) and `TODO.md` (the line of
  the day, a queue of work it can do alone, and «Done» with a proof for every item).
- **Messages between sessions.** The COO sends each session its line for the day: the goal, the proof it
  expects, the limits. The session reports back with the proof: a commit, a file, a number with its source.

The desk has four sections, in this order: **Decide** (only what needs my decision, each with a recommendation,
the consequence of not answering and a link to a page with the details), **Do** (manual actions, each with the
minutes it takes and what it unblocks), **Decided by COO** (one line each, cancellable) and **What's running**
(one generated line per project, which I do not need to read to act).

## Who decides what

Every decision has a colour.

- **Red, only me:** money, accounts and credentials, messages to people outside, writes to production,
  deploys, deletions, goals and thresholds, opening or closing a project.
- **Yellow, the COO decides, writes it down, I can cancel it:** parameters inside a project, the order of the
  work, test plans, formats, closing a line that is superseded.
- **Green, never on the desk:** fixes, tests, runs. They live in the board and in the TODOs.

The rule that makes yellow work is that **a yellow is reversible by definition**. If it cannot be undone, it
is red. If a yellow turns out to have been red, it goes back up and becomes a rule. This is what lets the COO
take decisions without asking: the cost of a wrong yellow is one line on my side, `WY1 no`.

## The model only where judgement is needed

The sessions are expensive in the only currency that matters here: attention, theirs and mine. So everything
mechanical runs without a model.

- **Hooks.** Claude Code runs a script when a session is about to end its turn. Two of mine decide whether it
  may: one makes sure the report to the COO contains everything, the other keeps the session working while its
  queue has items. Neither calls a model.
- **Checks.** The board and the desk have a shape, and a script checks it at every commit: cell caps, who we
  are waiting for, the four parts of a red item, the minutes of an action, yellows that should have expired.
- **Scripts instead of sessions.** If something comes back twice with the same steps (reading numbers,
  counting rows, checking a status), the owning session writes it once as a script that writes its result to
  a dated file. From then on it runs from the system scheduler and the COO reads the file. The session comes
  back only when a number looks wrong or a source changes.

## Five things that broke, and the fix

The system is three weeks old. Most of its rules exist because something went wrong.

**1. Proposals died in the chat.** A session would send its report to the COO, then keep writing: «also, I
noticed that…». The COO never saw it; I never read that chat. The fix is the `report_to_coo` hook: in a turn
the COO started, if there is more than a closing line after the report, the turn is blocked until that text
goes to the COO too. The report is the last thing of the turn and contains everything.

**2. Sessions sat idle.** A session would finish its task, or hit something that needed me, and stop. It would
wait for hours with a TODO full of work it could have done alone. Two fixes. First, a rule: **the session pulls
the work, the COO does not push it**. When a line is done, it takes the next one it can do without me, and it
stops only in front of a red decision, data from someone else, a cost or a permission. Second, the
`keep_working` hook: while the «Autonomous queue» in the TODO has open items, the turn does not end. Items
waiting for someone are marked and skipped; after three re-runs without a new commit the hook lets go, so a
stuck session cannot spin in place.

**3. The browser was 26% of a day's usage.** I measured where usage went on one day: a single session driving a
browser had made over twelve hundred calls, and that was about a quarter of the whole day across all
sessions. Every browser step is a model call carrying the whole context; the same step through an API or a
script is one call. The rule now: if an API, a command-line tool or a script can do it, that is how it is done.
The browser stays for sites that offer nothing else and for visual checks.

**4. The desk filled up with half-finished work.** Pages that had not been checked, numbers not re-read
against their source, items I could not close without asking three questions. One afternoon I spent more
time asking for fixes than deciding. The rule now: **only finished, checked work reaches the desk**. The COO
opens the page and re-reads the numbers before writing the item; if the work is not done, it goes back to the
session and I never see it. Every item stands on its own. And at my second question on the same item, it
leaves the desk and moves to the chat of the session that owns it.

**5. Messages between sessions stopped arriving.** In my setup, after about ten messages between sessions with
no message from me, Claude Code stopped delivering them until I wrote something. A COO that hears about every
finished item burns through that in an hour. The fix: in turns without me, a session reports to the COO only
at a block, at something I must do, or every five finished items. The rest is in «Done» and in the commits,
which the COO reads from git.

## The numbers: first week, all over threshold

A desk is doing its job when I answer little and answer fast. Every desk item has a code, and my answers
mention the code, so the COO's transcript is enough to measure it. The script pairs each code with my answers
and classifies them.

| Measure | 5–11 October | Threshold |
|---|---|---|
| Rounds per day on desk items | 40 (278 in 7 days) | under 20 |
| Answers that are just «ok» | 31% | under 20% |
| Answers that are a question | 37% | under 15% |
| Rounds older than 24 hours | 13% | under 5% |

Every one is over. What they say:

- **37% questions** is the loudest number, and it says the same thing as point 4: items reached me unfinished
  or not self-contained. The «only finished work» rule has been in force since 10 October, so this week's
  number barely includes it.
- **31% «ok»** means almost a third of what I was asked could have been decided by the COO. Those should have
  been yellows.
- **40 rounds a day** is the sum of the two. One item alone took 35 rounds.
- **13% over 24 hours** is items sitting on the desk while I answered others.

I measure again on Saturday 17 October, same script, same thresholds. If the questions do not come down, the
next change is in how the COO writes an item, not in how many it writes.

## Using the repository

[coo-for-claude-code](../README.md) has the generic version: the two hooks, the board and desk checker, the
generator for the «What's running» section, the measurement script, and templates for every file, with fake
but realistic content. Standard-library Python, no model calls, MIT licence. The README explains the setup in
five steps.

What it is not: an agent framework. The model and the agent loop are Anthropic's, and Claude Code does the
work. What is here is the organisation around it: who decides what, which file says what, and the checks that
catch it when the organisation drifts.

## If you run something similar

I would like to compare numbers. How often does your setup ask you something, and how often is the answer
just «ok»?
