# Tag glossary

Patient tags and attributes used in decision graphs, by tumour type.

Format: `tag` — medical context

## EBC

- ACOSOG-Z0011+ — meets ACOSOG Z0011 criteria
- ACOSOG-Z0011- — does not meet ACOSOG Z0011 criteria
- AMAROS+ — meets AMAROS criteria
- cN+ — clinically node-positive
- cN0 — clinically node-negative
- cT1 — clinical T1
- cT1a — clinical T1a
- cT1b — clinical T1b
- cT1c — clinical T1c
- cT2 — clinical T2
- cT3 — clinical T3
- cT4 — clinical T4
- HER2+ — HER2-positive
- HER2- — HER2-negative
- HR+ — hormone receptor–positive
- HR- — hormone receptor–negative
- iN+ — imaging node-positive
- iN0 — imaging node-negative
- N+ — node-positive
- N0 — node-negative
- neoadjuvant — neoadjuvant therapy pathway
- pN+ — pathologically node-positive
- pN0 — pathologically node-negative
- pNX — pathological nodal status unknown / not assessed
- positive_nodes — number of positive axillary nodes (number)
- postmenopausal — postmenopausal
- premenopausal — premenopausal
- primary_surgery — primary surgery indicated
- receiving_ofs — receiving ovarian function suppression
- SLN+ — sentinel lymph node positive
- SLN- — sentinel lymph node negative
- T1 — tumour stage T1
- T1a — tumour stage T1a
- T1b — tumour stage T1b
- T1c — tumour stage T1c
- T2 — tumour stage T2
- T3 — tumour stage T3
- T4 — tumour stage T4
- TAD+ — targeted axillary dissection positive
- TAD- — targeted axillary dissection negative
- ycN+ — clinical node-positive after neoadjuvant therapy
- ycN0 — clinical node-negative after neoadjuvant therapy
- ypN+ — pathological node-positive after neoadjuvant therapy
- ypN0 — pathological node-negative after neoadjuvant therapy

## ELANSCLC

- ALK_rearrangement — ALK rearrangement
- ALK_WT — ALK wild-type
- ChT_eligible — eligible for chemotherapy
- ChT_ineligible — ineligible for chemotherapy
- ChT-ICI_eligible — eligible for chemotherapy plus immunotherapy
- ChT-ICI_ineligible — ineligible for chemotherapy plus immunotherapy
- Concurrent_CRT_eligible — eligible for concurrent chemoradiotherapy
- Concurrent_CRT_ineligible — ineligible for concurrent chemoradiotherapy
- EGFR_exon_19_deletion — EGFR exon 19 deletion
- EGFR_mutation — EGFR mutation
- EGFR_WT — EGFR wild-type
- Higher_stage — higher stage (beyond locoregional criteria shown)
- L858R — EGFR L858R mutation
- Medically_inoperable — medically inoperable
- Medically_operable — medically operable
- N0 — node-negative
- no_EGFR_exon_19_deletion — no EGFR exon 19 deletion
- no_L858R — no EGFR L858R
- PD-L1_negative — PD-L1 negative
- PD-L1_positive — PD-L1 positive
- pdl1_percent — PD-L1 expression percent (number)
- R0 — R0 resection
- R1 — R1 resection
- R2 — R2 resection
- RT — radiotherapy alone pathway
- Sequential_CRT — sequential chemoradiotherapy
- tumour_size_cm — tumour size in centimetres (number)

## mNSCLC

- after_ALK_TKI_not_crizotinib — after ALK TKI other than crizotinib
- after_crizotinib — after crizotinib
- ALK_translocation — ALK translocation
- BRAF_V600_mutation — BRAF V600 mutation
- EGFR_ex20ins_mutation — EGFR exon 20 insertion
- EGFR_mutation — EGFR mutation
- Exon_20_T790M_mutation_negative — T790M negative
- Exon_20_T790M_mutation_positive — T790M positive
- first_line_first_or_second_generation_TKI — first-line 1st/2nd-generation TKI
- first_line_osimertinib — first-line osimertinib
- HER2_mutation — HER2 mutation
- if_ICI_monotherapy_given_in_first_line — ICI monotherapy given in first line
- if_ICI_monotherapy_not_given_in_first_line — ICI monotherapy not given in first line
- KRAS_G12C_mutation — KRAS G12C mutation
- MET_ex14_skipping_mutation — MET exon 14 skipping mutation
- no_ROS1_TKI_received_in_first_line — no ROS1 TKI in first line
- no_smoking_history — no smoking history
- No_resistance_mechanism_identified — no resistance mechanism identified
- NTRK_translocation — NTRK translocation
- Oligoprogression — oligoprogression
- rebiopsy_indicated_but_not_feasible — rebiopsy indicated but not feasible
- Resistance_mechanism_identified — resistance mechanism identified
- RET_translocation — RET translocation
- ROS1_TKI_received_in_first_line — ROS1 TKI received in first line
- ROS1_translocation — ROS1 translocation
- smoking_history — smoking history
- Systemic_progression — systemic progression

## MPM

- EBUS/EUS — endobronchial / endoscopic ultrasound staging
- FDG-PET — FDG-PET staging
- PS — ECOG performance status (number)

## nomNSCLC

- age_under_50 — age under 50 years
- any_expression_of_PD-L1 — any PD-L1 expression (no threshold)
- ECOG_PS — ECOG PS pathway hub label (`always()` in curated)
- ECOG_PS_and_PD-L1_expression_level — ECOG/PD-L1 pathway hub (`always()` in curated)
- light_smoker — light smoker
- long_time_ex_smoker — long-time ex-smoker
- Molecular_test_negative — molecular test negative
- Molecular_test_positive — molecular test positive
- Never_smoked — never smoked
- Oligometastatic — oligometastatic disease
- pdl1_percent — PD-L1 expression percent (number)
- PS — ECOG performance status (number)
- smoked_under_15_packyears — smoking history under 15 pack-years

## SCLC

- Age — age in years (number); curated `le` / `gt`
- Contraindications_for_IO — contraindications for immuno-oncology
- cT1 — clinical T1 (reuse EBC)
- cT2 — clinical T2
- cT3 — clinical T3
- cT4 — clinical T4
- due_to_comorbidities — ECOG PS ≥2 attributable to comorbidities
- due_to_SCLC — ECOG PS ≥2 attributable to SCLC
- Frail — frail (PCI shared-decision arm); current limited-stage DOT spelling
- M0 — no distant metastasis (limited-stage CRT conjunct)
- N0 — node-negative (reuse EBC; clinical or pathological N0)
- N1 — N1 (clinical CRT arm or after resection)
- N2 — N2 (clinical CRT arm or pathological after resection)
- N3 — N3 (clinical; limited-stage CRT arm)
- No_contraindication_for_IO — no contraindication for immuno-oncology
- PS — ECOG performance status (number); same attribute as MPM / nomNSCLC; induction snapshot on each graph
- PS_after_response — ECOG PS after treatment response (number); later timepoint than `PS`
- pT1 — pathological T1
- pT2 — pathological T2
- Refractory — platinum-refractory relapse
- Response — response to first-line therapy (extensive-stage consolidation gate)
- Stage_I-II — limited-stage surgical pathway (with `cT1 or cT2` and `N0`)
- Stage_I-III — limited-stage CRT pathway (with `cT1 or cT2 or cT3 or cT4`, `N0 or N1 or N2 or N3`, and `M0`)
- TFI — treatment-free interval in months (number)
