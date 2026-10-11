# COO board

> **What this is.** The COO's register: for each active project, what it does today, where it stands and
> who we are waiting for. The CEO does not read it: the CEO reads `CEO_DESK.md`.
>
> **State, not history.** Every cell stays under 400 characters and says how things are now: an update
> *replaces* the text, it is never appended. The history lives in the «Done» section of each project's TODO
> and in the `git log` of this file. Before every commit: `python scripts/check_board.py`.
>
> **Desk codes** (`<project letter><R|Y><n>`). R = red or «Do» (waits for the CEO), Y = yellow («Decided by
> COO»: the CEO can cancel it). An open item keeps its code until the CEO answers; a new one takes the lowest
> free number of its project. Fixed letters: C COO (proposals about the process itself) · S Shop · R Research
> · W Website · P Property.
>
> **Session addresses.** Always the session id, never the display name: two sessions can share a name.
> COO `local_…` · Shop `local_…` · Research `local_…` · Website `local_…` · Property `local_…`.

| Project | Today | Done | Status |
|---|---|---|---|
| Shop | Rewrite the product pages of the three best sellers with the new photos; proof: the pages live and the before/after conversion in the TODO. | 10/10: price test closed, the cheaper variant sold 2 of 41 visits against 0 of 38 (commit `4f1c2aa`). | waiting session: product pages · msg 11/10 09:12 |
| Research | Weekly scan of the listings, same filters as last week; proof: the CSV and the three best matches with the reasons. | 09/10: filters moved to a config file, the scan runs without the model (commit `91be07d`). | waiting CEO: RR1, budget for the paid data source · msg 10/10 18:40 |
| Website | — | 08/10: contact form fixed, test message received. | nothing in flight |
| Property | Valuation of the two listings from the agent, with the comparables; proof: the filled template and the range. | 11/10: first listing done, price range from 6 comparables in the template. | waiting session: second valuation · msg 11/10 10:05 |
