# Legacy Comparison Results (new pipeline; original mockdown fails)

The original mockdown fails on these legacy datasets (non-isomorphic examples not supported), so only the new pipeline metrics are shown. `hn` timed out; `conference` timed out in this run.

Dataset | RMSD (px) | ACC | Constraints | Total (s) | Inst (s) | Learn (s) | Prune (s)
--- | --- | --- | --- | --- | --- | --- | ---
ace | 0.3017 | 1.0000 | 1223 | 26.8536 | 4.4571 | 20.2692 | 2.1273
author | 24.4573 | 0.0000 | 669 | 181.3447 | 1.0135 | 8.0805 | 172.2507
conference | timeout | — | — | — | — | — | —
ddg | 0.2168 | 1.0000 | 627 | 14.4277 | 1.0847 | 7.8392 | 5.5038
fwt-main | 0.2951 | 1.0000 | 1827 | 49.3395 | 10.0502 | 27.9030 | 11.3863
fwt-running | 0.2006 | 1.0000 | 543 | 12.6874 | 0.8116 | 7.4801 | 4.3957
fwt-space | 0.1932 | 1.0000 | 793 | 12.9713 | 1.3258 | 9.6933 | 1.9522
hn | timeout | — | — | — | — | — | —
ieeexplore | 0.4661 | 0.9509 | 3032 | 84.7303 | 27.8482 | 49.0201 | 7.8619

