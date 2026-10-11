# TODO — Shop

> **Today's line** (from the COO, 11/10): rewrite the product pages of the three best sellers with the new
> photos. Proof: the pages live and the before/after conversion below. Limits: no price changes, no new
> listings, nothing published without `SR1 done` from the CEO.

## Autonomous queue

Items the session can do without the CEO or third parties, in order. The `keep_working` hook does not let
the session stop while one is open. `[waiting]` marks an item that waits for someone: the hook skips it.

- [ ] Rewrite the three product pages (drafts on a local page for the CEO).
- [ ] [waiting] Publish the three pages — waits for `SR1 done`.
- [ ] Compare conversion on the three pages, seven days before and after.
- [ ] Turn the weekly sales export into a script that writes `data/sales_<date>.csv` without the model.

## Open

- Shipping costs to Germany: the carrier has not answered yet (asked 09/10).

## Done

- 10/10 — Price test closed: the cheaper variant sold 2 of 41 visits against 0 of 38. Commit `4f1c2aa`.
- 08/10 — Photos for the three best sellers received and resized. Commit `2b7e019`.
