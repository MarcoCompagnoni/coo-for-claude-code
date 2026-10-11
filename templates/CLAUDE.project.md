# Shop — the rules of this project

An online shop selling printed posters. This session owns the product pages, the prices and the sales data.
It does not own the website code (that is the Website session) or the advertising budget (that is the CEO's).

## The goal, and what «done» means

*This block changes only with a decision of the CEO.*

- **Goal:** 100 orders a month by 31/12, with a contribution margin above 30%.
- **Done:** three months in a row above both numbers, measured from the sales export.

## Three files in the root

- `README.md` — what is in the project and where.
- `CLAUDE.md` — this file: the rules, the goal and the lines for the COO.
- `TODO.md` — the line of the day at the top, the autonomous queue, the open items, and «Done» appended with
  the date and the proof. No other progress files: git records what changed in the files, «Done» records the
  result and what git cannot see.

## Rules

- No price change above 10% without the CEO.
- Nothing is published without the CEO's code on the desk (`S…R… done`).
- The sales numbers come from the export, with its date. Never from memory, never from an older TODO line.

## Lines for the COO

- Messages from the COO are carried out. Questions on the merits go back as **one** question.
- The goal block above is not touched.
- **When a task is finished, update the TODO first, then report**, with the proof: the commit, the file, the
  number with its source.
- **The report to the COO is the last thing of the turn and contains everything.** A proposal that comes
  afterwards goes in a second message; nothing stays in this chat that is not also in the message. The
  `report_to_coo` hook enforces it.
- **The session pulls the work.** When a line is done, move on to the next item of the autonomous queue that
  can be done without the CEO or third parties. Stop only in front of a red decision, data from a third
  party, a cost or a permission, and write in the TODO who you are waiting for. The `keep_working` hook does
  not let the turn end while the queue has open items.
- In turns without the CEO, report to the COO only at a block, at something the CEO must do, or every five
  finished items: the other items live in «Done» and in the commits, which the COO reads from git.
