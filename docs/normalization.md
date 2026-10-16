## ebc
tag expansion: graph condition or patient data?
    - graph condition
        - >=cT2 -> (cT2, cT3, cT4)
        - cT1c-4 -> (cT1c, cT2, cT3, cT4)
        - HR+ -> ER+ or HR+
    - patient data
        - ER+ -> (ER+, HR+)
        - PR+ -> (PR+, HR+)
        - cT3 -> (>=cT2, cT1c-4)
    - common abbreviations?
        - (BRCA1/2 -> BRCA1/BRCA2)

## elansclc
tag normalization:
locoregional_staging.jpg
    Original: T <3 cm N0
    Curated: < 3 tumour_size_cm  and N0

    Original: T 3-4 cm N0
    Curated: >= 3 tumour_size_cm and <= 4 tumour_size_cm and N0

systemic_treatment.jpg:
    Original: EGFR mutation or < PD-L1 < 1%
    Curated: EGFR_mutation or < 1 pdl1_percent

    Original: EGFR WT and PD-L1 >= 1%
    Curated: EGFR_WT and > 1 pdl1_percent

## mpm
staging.jpg:
Excluded the top 3 staging description boxes in the graph.

inoperable.jpg:
Removed the root → disease progression → PS ≥ 3 path, since a root → PS ≥ 3 path already exists.
Optional sibling regimens: curated `always()` (see [`docs/dot_dg_review.md`](dot_dg_review.md)).

## sclc
limited_stage T/N split — DOT writes atomic OR lists so the compiler emits `has('cT1')` (no curated T expansion):
    Original: Stage I-II (cT1-2N0)
    DOT: Stage_I-II and (cT1 or cT2) and N0

    Original: Stage I-III (cT1-4N0-3M0)
    DOT: Stage_I-III and (cT1 or cT2 or cT3 or cT4) and (N0 or N1 or N2 or N3) and M0

    Original: pT1-2N0-1, R0
    DOT: (pT1 or pT2) and (N0 or N1) and R0

recurrent — named TFI boxes drop to prefix comparisons; `and/or` is `or`; hyphenated PS expands. Curated uses numeric `TFI` / `PS` (compiler still emits tag soup):
    Original: Platinum-resistant relapse (<3 months TFI)
    DOT: < 3 TFI
    Curated: lt('TFI', 3)

    Original: Platinum-sensitive relapse (≥3 months TFI)
    DOT: >= 3 TFI
    Curated: ge('TFI', 3)

    Original: Refractory and/or PS >2
    DOT: Refractory or > 2 PS
    Curated: any_of(has('Refractory'), gt('PS', 2))

    Original: PS 0-2
    DOT: >= 0 PS and <= 2 PS
    Curated: all_of(ge('PS', 0), le('PS', 2))

    Horizontal arrow from the platinum-sensitive treatment box to the resistant PS 0-2 list is a shared downstream node (`h -> g`).

## tet
metastatic — thymoma Surgery vs Definitive_radiotherapy are treatment options (dashed siblings), not patient tags. Curated uses `always()` on both so walk takes every path; Follow-up is one shared node.
    DOT: Surgery / Definitive_radiotherapy compile as has('Surgery') / has('Definitive_radiotherapy')
    Curated: always()

unresectable — first-line Primary_chemotherapy vs Chemoradiotherapy, and unresectable CRT vs Definitive_radiotherapy, are treatment options. Curated uses `always()`; Follow-up / PORT / postop chemo are shared nodes. Restaging (Unresectable / Resectable + Masaoka-Koga + cTNM) and R0/R1/R2 stay as tags.
    DOT: has('Primary_chemotherapy') / has('Chemoradiotherapy') / has('Definitive_radiotherapy')
    Curated: always()

## mel
itm — left arm stays `Resectable_disease`. Right arm is unresectable or resectable with short DFI:
    DOT: Unresectable_disease or (Resectable_disease and < 6 DFI_months)
    Curated: any_of(has('Unresectable_disease'), all_of(has('Resectable_disease'), lt('DFI_months', 6)))

mbm — steroid dose is prefix comparison; SRS vs neurosurgery/systemic are treatment options:
    DOT: Symptomatic_MBMs and > 10 prednisolone_mg_day and Local_treatment_not_an_option
    Curated: all_of(has('Symptomatic_MBMs'), gt('prednisolone_mg_day', 10), has('Local_treatment_not_an_option'))
    DOT sibling treatment boxes compile as has(); curated always()

st3 — curated loads `mel_adv_st3_or_st4_curated.dg` in place of `See Figure 4`.
adv — curated inlines Figure 2's resectable Stage III/IV subgraph in place of `See Figure 2` (do not load_dg st3_curated; that file loads this one as Figure 4).
itm — right arm continues into Figure 4 (`mel_adv_st3_or_st4_curated.dg`) after the local-therapy box.
