# Every correction became a check

I run several Claude Code sessions. One of them, the COO, does no project work: it hands out tasks, checks the reports
and writes one file for me, the desk, with only what needs a human. Two weeks ago I published four numbers on how that
desk was doing. All four were over my thresholds. Here are the three lessons from the fixes since, ones you can
reuse tomorrow, and then the numbers that say whether they worked.

## 1. A correction that is only a sentence comes back

Twice in one week the COO handed me something wrong. A return calculation (IRR) on a business model had payments due
at 6 and 12 months sitting in yearly rows, so the IRR was overstated. And after midnight, items for the next day
appeared on the desk, because the checker used the calendar date while I still called the new day «tomorrow».

Both were fixed in the work. Neither fix stopped there: each became a check in the script that refuses to commit a
malformed desk. An item that quotes an IRR must carry a line «Cash-flow timing: …». The day changes at 05:00, not at
midnight. Each check has a test that was red before and green after. From 10 to 21 October that script took 47
commits and went from 18 tests to 86. Every one of them is an error with a date on it.

**Tomorrow:** after your next correction, ask «which script would have caught this?» Write the test, watch it fail,
then write the check. If the honest answer is «none», that is the finding.

## 2. Hand the agent what is reversible

A third of my answers, 30% in the first week, were a plain «ok»: a yes to something the agent could have decided and
told me about. The rule that came out of it: every item on the desk names why it is mine. Money, accounts, messages to
outside, production, the goal and the plan, a project of mine, something I said I would do, or an answer to my own
question. An item that cannot name one is yellow: the agent decides, writes one line with a code, and I can cancel
it. A yellow is reversible by definition; if it is not, it is red. The public desk checker does the same: it stops an
item without a «Red: …» reason.

Whether it worked is in the numbers below. The rule landed on 17 October, the last day of the window I first
measured.

**Tomorrow:** list what your agent asks you for this week. Mark each as reversible or not. Give it the reversible
ones, with a written line you can cancel, and keep the rest.

## 3. Green checks are not the goal

A call script passed every structure test. I rejected it: the COO had recommended it after checking its form and a
simulation, not who actually picks up the phone, a switchboard operator and not the manager. A proposal the COO recommended paid the other side less
than our previous one: it had been checked only from our side, and I caught it on reading. Tests green, structure
respected, goal missed. The agent did not check what only the human could see, so the check had to go into code.

Two more checks followed, in my private version of the checker: an item with a call script must say how it reads for
the person who answers, and a proposal must say what the other side gets compared with the previous one.

**Tomorrow:** whatever reviews your agent's work gets the goal and the recipient in its prompt, not only the text
to check, and every deliverable carries one line: «read as: …».

## The numbers

Week one, re-run on closed days with the same script, came out different from what I published: worse on rounds and
on late answers, slightly better on questions and on «ok». The transcripts the script reads had changed between the
two runs, so from now on I compare weeks only from one run made after both are closed.

| Week 1 (5–11 October) | Published on 12 October | Re-run |
|---|---|---|
| Rounds per day on desk items | 40 (278 in 7 days) | 45 (313 in 7 days) |
| Answers that are just «ok» | 31% | 30% |
| Answers that are a question | 37% | 35% |
| Rounds older than 24 hours | 13% | 15% |

| Measure | 5–11 October | 12–17 October | 18–24 October | Threshold |
|---|---|---|---|---|
| Rounds per day on desk items | 45 (313 in 7 days) | 30 (178 in 6 days) | 37 (257 in 7 days) | under 20 |
| Answers that are just «ok» | 30% | 39% | 30% | under 20% |
| Answers that are a question | 35% | 30% | 38% | under 15% |
| Rounds older than 24 hours | 15% | 32% | 31% | under 5% |
| Messages of frustration per day | 10.4 | 5.7 | 8.4 | — |

The rule that an item for the human must say why it is the human's landed on 17 October, the last day of the second
window, so the third column is its first real test. «ok» went from 39% back to 30%, where it started, and still over
the 20% threshold. I cannot say the rule did it: one week, one run. Nothing else improved. Rounds went from 30 to 37 a
day and questions from 30% to 38%. Answers over 24 hours barely moved, 32% to 31%, and 52 of those 78 were on items opened before
18 October, so the desk was still clearing its backlog. Without them it is 13%, against 16% the week before.

Still all four over threshold. Against week one only rounds are better (45 to 37); «ok» is the same, questions and
late answers are worse. Not better yet.

## A question

How do you decide what your agent may decide alone? Which of your last ten «ok» answers could have been a note you
read afterwards? I would like to hear where you draw the line.

The measuring script and the desk checker are in [coo-for-claude-code](../README.md).
