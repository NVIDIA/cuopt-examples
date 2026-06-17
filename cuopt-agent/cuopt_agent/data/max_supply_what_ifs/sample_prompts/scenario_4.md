## Scenario

Our max-supply model maximizes priority-weighted finished-goods inventory at the end of the
horizon — but it spends freely to do it. Procuring more raw material, running resources longer,
and carrying inventory all cost money (`item_costs.csv` has per-item `unit_cost` and `holding_cost`;
`resource_costs.csv` has `production_cost_per_hour`), and the base objective ignores all of it.

Finance now wants the cost side on the table. There is **no agreed exchange rate** between a unit of
finished-goods supply and a dollar of cost — pushing supply up raises cost, and the right balance is
a judgment call, not a number we can hand the solver up front. So the answer finance needs isn't a
single plan; it's the tradeoff laid out so they can choose where to sit.

## Request

1. Bring cost into the picture as a reporting quantity built from `item_costs.csv` and
   `resource_costs.csv` over the model's existing variables — no new decisions.

2. Give finance the **whole supply-vs-cost tradeoff**, not one plan and not a single blended
   objective: show how much finished-goods supply each budget level buys, from a tight budget up to
   where more money stops buying more supply.

3. Solve on the sample dataset (10 periods) and present it so finance can act: the tradeoff curve,
   the rate at which supply is bought as the budget loosens and where that rate falls off (the knee),
   what drives cost at the high-supply end, and two or three candidate operating points to choose
   between — without calling any one of them "best."

Watch two things about this model so the numbers mean what you claim: it's a **MILP**, and the
finished-goods priority weights span 10000:1 — so make sure your marginal rate is valid for the model
class and your supply figures are in terms finance can read, not just the weighted total.
