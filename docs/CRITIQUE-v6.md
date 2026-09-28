# CRITIQUE v6 — adversarial review of the current claims

Research lead, 2026-09-28. The three claims a reviewer would attack,
and how. Ranked by how much each could change what we say.

## Claim 1: "Decision quality is an individual skill that shows up in results" (replicated on the holdout)

1a. It may be "where he usually plays", not "how he chooses". (Suspected)
The role fixed effects are coarse (7 groups). Inside a role, some
players habitually receive higher up or more centrally, and their
passes' next-10-events xG is higher for that reason. g controls the
pass's own starting spot, but only explains 4.5% of the outcome.
Test: add the passer's OTHER-match averages of starting x, starting y
and ev_chosen as controls; replace the 7 roles with the pass's exact
StatsBomb position label.

1b. Which roles carry it? (Unknown)
If the effect lives entirely in forwards and attacking midfielders, it
says nothing about registas. Test: the P-test within each role.

1c. Does it count the passer's own later shot? (Suspected, small)
Y includes shots in the next 10 events, including by the passer.
Test: exclude the passer's own shots; horizons of 5 and 15 events.

1d. Inference. SEs are clustered by passer only. Test: two-way
clustering (passer and match) and a passer-level bootstrap.

1e. Size in football terms. +0.075 xG per 100 passes per SD needs
translating: per match and per season for a typical deep midfielder
and a typical attacker.

1f. The deep-midfield null may again be power. Study CI upper bound
+0.047, holdout +0.070, against +0.075 for all players. Report what
effect sizes the DM tests can rule out.

## Claim 2: "Elite registas don't get free; they take the ball in traffic"

2a. "Elite" is chosen by eye. (Checked: it is)
Busquets, de Jong, Verratti and Vitinha were named after seeing the
tables. A reviewer will call that cherry-picking. Fix: use a list that
existed BEFORE any of these measures: plan v3 section 5's fixed list
(Kroos, Modric, Verratti, Busquets, De Bruyne, Xhaka, de Jong, Kimmich,
Rodri, Pedri, Gundogan, Grillitsch, Shaparenko), written months ago and
used only as output. Test, pre-declared: do fixed-list players sit
lower than role-peers on availability and on reception space?
Permutation p-value. Small n; reported as such.

2b. Availability is not adjusted for where the player stands.
(Checked: by design)
So "available" may partly mean "standing somewhere safe that no one
bothers to mark", which would explain both the negative results link
and why busy central 6s score low. Fix: a location-adjusted version
(the baseline also knows his position relative to ball and goal) and a
"progressive availability" version (open AND ahead of the ball, i.e. a
line-breaking option).

2c. Thresholds (3 m space, 2 m lane) are arbitrary. Test: 2/3/5 m and
1/2/3 m.

2d. Two findings pull opposite ways within deep midfielders: more space
AT RECEPTION goes with more xG after (p = 0.025), more AVAILABILITY
goes with less (p = 0.05). Test: both in one model.

## Claim 3: "Leads on what separates deep midfielders" (reception space, move-on speed)
3a. Neither can be confirmed out of sample: the holdout is spent.
3b. Both come from a family of several within-DM tests; the Holm
correction was applied within each task, not across tasks.
Mitigation: report a correction across all within-DM tests run in
Tasks 35-39 together, and label these as leads.

## Improvement ideas (for after the vetting)
I1. Press resistance: receive in tight space AND keep the ball or play
    forward. The pattern the top names show. Measurable in both
    StatsBomb 360 and PFF.
I2. Progressive availability (2b).
I3. Engine v7 (choices between teammates, ranked; decisive passes only;
    xG-based value labels). Exploratory: no holdout left.

## Proposed order
1. Freeze v6 (Task 40).
2. Vetting, measurement only: 1a-1f, 2a, 2c, 2d, 3b (Task 41).
3. Improvements, pre-registered: I1 and I2 (Task 42).
4. I3 only if time remains, labelled exploratory.
