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

- ChT_eligible — eligible for chemotherapy
- ChT_ineligible — ineligible for chemotherapy
- ChT-ICI_eligible — eligible for chemotherapy plus immunotherapy
- ChT-ICI_ineligible — ineligible for chemotherapy plus immunotherapy
- Concurrent_CRT_eligible — eligible for concurrent chemoradiotherapy
- Concurrent_CRT_ineligible — ineligible for concurrent chemoradiotherapy
- N0 — node-negative
- R0 — R0 resection
- R1 — R1 resection
- R2 — R2 resection
- RT — radiotherapy alone pathway
- Sequential_CRT — sequential chemoradiotherapy

## mNSCLC

none

## MPM

- EBUS/EUS — endobronchial / endoscopic ultrasound staging
- PS — ECOG performance status (number)

## nomNSCLC

- Oligometastatic — oligometastatic disease
- pdl1_percent — PD-L1 expression percent (number)
- PS — ECOG performance status (number)

## SCLC

- cT1 , cT2 , cT3 , cT4 — TNM staging system
- M0 — no distant metastasis (limited-stage CRT conjunct)
- N0 — node-negative (reuse EBC; clinical or pathological N0)
- N1 — N1 (clinical CRT arm or after resection)
- N2 — N2 (clinical CRT arm or pathological after resection)
- N3 — N3 (clinical; limited-stage CRT arm)
- PS — ECOG performance status (number)
- PS_after_response — ECOG PS after treatment response (number); later timepoint than `PS`
- pT1 — pathological T1
- pT2 — pathological T2
- Response — response to first-line therapy (extensive-stage consolidation gate)
- Stage_I-II — limited-stage surgical pathway (with `cT1 or cT2` and `N0`)
- Stage_I-III — limited-stage CRT pathway (with `cT1 or cT2 or cT3 or cT4`, `N0 or N1 or N2 or N3`, and `M0`)
- TFI — treatment-free interval in months (number)

## TET

- Masaoka-Koga_I , Masaoka-Koga_IIA , Masaoka-Koga_IIB , Masaoka-Koga_III , Masaoka-Koga_IVA — Masaoka-Koga stages
- cTNM_IIIA , cTNM_IIIB , cTNM_IVA — clinical TNM stages
- R0 — R0 Complete Resection (reuse elaNSCLC)
- R1 — R1 Microscopic Incomplete Resection (reuse elaNSCLC)
- R2 — R2 resection (reuse elaNSCLC)
- WHO_A — WHO type A thymoma - Spindle cell / Medullary thymoma
- WHO_AB — WHO type AB thymoma - Mixed thymoma
- WHO_B1 — WHO type B1 thymoma - Lymphocyte-rich / Predominantly cortical thymoma
- WHO_B2 — WHO type B2 thymoma - Cortical thymoma
- WHO_B3 — WHO type B3 thymoma - Atypical / Epithelial thymoma

## MEL

- Adjuvant_anti-PD-1 — prior adjuvant anti-PD-1
- Adjuvant_BRAFi-MEKi — prior adjuvant BRAF plus MEK inhibitor
- Asymptomatic_MBMs — asymptomatic melanoma brain metastases
- BRAF_mutated — BRAF-mutated melanoma
- BRAF_WT — BRAF wild-type
- DFI_months — disease-free interval in months
- LMD — leptomeningeal disease
- Oligometastatic — oligometastatic disease (reuse nomNSCLC)
- prednisolone_mg_day — steroid dose in mg/day prednisolone equivalent (number)
- SLN- — sentinel lymph node negative (reuse EBC)
- SLN+ — sentinel lymph node positive (reuse EBC)
- Stage_I-IIA , Stage_IA, Stage_IB-IIA , Stage_IIB-IIC , Stage_IIB-IIIC , Stage_IIID , Stage_III , Stage_IV , Stage_IV_M1a-M1d_distant_metastases — different stages for Cutaneous Melanoma
- Stage_IV_NED_resected_CR — follow-up column stage IV NED after resection / complete response
- Symptomatic_MBMs — symptomatic melanoma brain metastases

## UM

- Alterations_in_chromosome_3 — copy-number alteration in chromosome 3
- Alterations_in_chromosome_8 — copy-number alteration in chromosome 8
- Extra-liver_metastases — extrahepatic metastases (with or without liver metastases)
- Eye-preservation_possible — localised primary amenable to eye-preserving therapy
- GEP_class_1 — gene-expression profile class 1 (low metastatic risk)
- GEP_class_2 — gene-expression profile class 2 (high metastatic risk)
- HLA-A*02:01_negative — HLA-A*02:01 negative
- HLA-A*02:01_positive — HLA-A*02:01 positive
- Liver_only_metastases — metastases confined to the liver
- No_alterations_in_chromosome_3 — no copy-number alteration in chromosome 3
- No_alterations_in_chromosome_8 — no copy-number alteration in chromosome 8
- Oligometastatic — oligometastatic disease (reuse nomNSCLC)
- PD — progressive disease
- T1a , T1b , T1c , T1d , T2a , T2b , T2c , T2d , T3, T4 
- tumours_with_extrascleral_extension — extrascleral extension of the primary

## NPC

- M0 — no distant metastasis (reuse SCLC)
- Metastatic_disease — metastatic NPC (reuse UM)
- N0 — node-negative (reuse EBC / SCLC)
- N1 — N1 (reuse SCLC)
- N2 — N2 (reuse SCLC)
- N3 — N3 (reuse SCLC)
- Stage_I — clinical stage I NPC
- Stage_II — clinical stage II NPC
- Stage_III — clinical stage III NPC
- Stage_IVA — clinical stage IVA NPC
- T0 — T0 NPC
- T1 — tumour stage T1 (reuse EBC)
- T2 — tumour stage T2 (reuse EBC)
- T3 — tumour stage T3 (reuse EBC)
- T4 — tumour stage T4 (reuse EBC)

## SGC

- AdCC_any_stage — adenoid cystic carcinoma, any stage (chest CT pathway)
- All_other — parotid primary that is not cT1/cT2 low-grade in the superficial lobe
- Clinical_findings_suggesting_malignancy — clinical findings suggest salivary malignancy
- cN+ — clinically node-positive (reuse EBC)
- cN0 — clinically node-negative (reuse EBC)
- cT1 — clinical T1 (reuse EBC)
- cT2 — clinical T2 (reuse EBC)
- cT3 — clinical T3 (reuse EBC)
- cT4 — clinical T4 (reuse EBC)
- extraglandular — submandibular primary extending outside the gland
- high_grade — high-grade histology (parotid cN0 neck; sublingual END indication)
- intraglandular — submandibular primary confined to the gland
- low_grade_in_superficial_lobe — low-grade parotid tumour in the superficial lobe
- low_intermediate_grade — low- or intermediate-grade parotid histology
- Lymph_node_metastasis — ultrasound-detected nodal metastasis
- M0 — no distant metastasis (unresectable SGC; reuse SCLC)
- M1 — distant metastasis (unresectable SGC)
- N+ — node-positive (reuse EBC)
- N0 — node-negative (reuse EBC)
- nVII_normal — facial nerve (CN VII) clinically normal
- nVII_paretic — facial nerve (CN VII) paresis
- pN+ — pathologically node-positive (reuse EBC)
- pN0 — pathologically node-negative (reuse EBC)
- T — tumour size in millimetres (number)

## SNM

- Amenable_to_reRT — locoregional recurrence suitable for re-irradiation (after not amenable to salvage therapy)
- Amenable_to_salvage_therapy — locoregional recurrence suitable for salvage surgery (not NPC’s combined salvage-or-reRT tag)
- CR — complete response
- High-grade_poorly_differentiated_stage_III-IV_resectable — high-grade / poorly differentiated resectable stage III–IV (NACT column)
- PD — progressive disease after NACT restaging
- PR — partial response after NACT or first-line systemic therapy
- SD — stable disease after NACT restaging
- Stage_I-II — clinical stage I–II SNM (surgery column; not SCLC limited-stage)
- Stage_III-IV_resectable — resectable clinical stage III–IV SNM
- Stage_IV_unresectable — unresectable clinical stage IV SNM

## SCCHN

- cM0 — clinically no distant metastasis
- cN0 — clinically node-negative (reuse EBC)
- cN1 — clinical N1
- cN2 — clinical N2
- cN3 — clinical N3
- cT1 — clinical T1 (reuse EBC)
- cT2 — clinical T2 (reuse EBC)
- cT3 — clinical T3 (reuse EBC)
- cT3b — clinical T3b larynx (larynx-preservation / CRT column)
- cT4 — clinical T4 oropharynx (reuse EBC)
- cT4a — clinical T4a (oral cavity, larynx, hypopharynx)
- cT4b — clinical T4b (oral cavity, larynx, hypopharynx)
- Immunotherapy_naive — no prior immunotherapy
- Larynx-preserving_surgery_feasible — conservation larynx surgery possible
- PD-L1_negative — PD-L1-negative tumour (reuse elaNSCLC)
- PD-L1_positive — PD-L1-positive tumour (reuse elaNSCLC)
- PD-L1_untested — PD-L1 not assessed
- TFI — platinum-free interval in months (number)

## CERV

- CIN2 — cervical intraepithelial neoplasia grade 2
- CIN3 — cervical intraepithelial neoplasia grade 3
- FIGO_IA1 , FIGO_IA2 ,FIGO_IB1 ,FIGO_IB2 , FIGO_IIA1 , FIGO_IIB , FIGO_IIIB , FIGO_IVA — FIGO stages
- Invasive_cervical_cancer — invasive cervical cancer after colposcopy / biopsy
- Locally_advanced_disease — locally advanced cervical cancer
- Metastatic_disease — metastatic cervical cancer (reuse UM)
- No_LVSI — no lymphovascular space invasion (same concept as EMC `no_LVSI`; current treatment DOT spelling)
- With_LVSI — lymphovascular space invasion present

## EMC

- dMMR — mismatch repair deficient
- EEC — endometrioid endometrial carcinoma
- focal_LVSI — focal lymphovascular space invasion
- G1 — histological grade 1
- G2 — histological grade 2
- G3 — histological grade 3
- MSI-H — microsatellite instability-high 
- MSS — microsatellite stable 
- no_LVSI — no lymphovascular space invasion (same concept as CERV `No_LVSI`)
- not_infiltrating_the_myometrium — p53-abn tumour not infiltrating the myometrium
- NSMP — no specific molecular profile
- p53-abn — p53-abnormal 
- p53-mut — p53-mutant 
- p53_wild_type — p53 wild-type 
- Patients_who_did_not_receive_RT — no prior radiotherapy
- Patients_who_received_only_VBT — vaginal brachytherapy only
- Patients_who_received_prior_RT — after prior radiotherapy
- pMMR — mismatch repair proficient
- pN0 — pathologically node-negative after lymph-node staging (reuse EBC)
- POLEmut — POLE-mutated molecular class (adjuvant)
- POLE_non-pathogenic — POLE non-pathogenic (molecular classification; with `POLE_wild_type`)
- POLE_pathogenic — pathogenic POLE mutation (molecular classification)
- POLE_wild_type — POLE wild-type (molecular classification)
- restricted_to_a_polyp — p53-abn tumour restricted to a polyp
- serous_EC — serous endometrial carcinoma
- Stage_I ,Stage_IA ,Stage_IB, Stage_II , Stage_III , Stage_IVA - stages of endometrial cancer
- substantial_LVSI — substantial lymphovascular space invasion

## EOC

- BRCA1/BRCA2_mutated — BRCA1 or BRCA2 mutation 
- BRCA1/BRCA2_wt — BRCA1 and BRCA2 wild-type
- CCC_FIGO_stage_IA-IC1 — clear cell carcinoma, FIGO IA–IC1 (optional adjuvant ChT)
- CCC_FIGO_stage_IC2-IC3 — clear cell carcinoma, FIGO IC2–IC3 (adjuvant ChT)
- Early_symptomatic_progression — early symptomatic progression (platinum not the best option)
- Expansile_MC_FIGO_stage_IA-IB — expansile mucinous carcinoma, FIGO IA–IB (observation)
- Expansile_MC_FIGO_stage_IC — expansile mucinous carcinoma, FIGO IC (optional adjuvant ChT)
- First_relapse — first relapse (with `Positive_AGO_score`: consider surgery)
- HGSC_any_FIGO_stage — high-grade serous carcinoma, any FIGO stage I–II (adjuvant ChT)
- HRD_negative — HRD-negative / homologous recombination proficient (with `BRCA1/BRCA2_wt`)
- HRD_positive — homologous recombination deficiency (with `BRCA1/BRCA2_wt`)
- Infiltrative_MC_FIGO_stage_IA — infiltrative mucinous carcinoma, FIGO IA (optional adjuvant ChT)
- Infiltrative_MC_FIGO_stage_IB-IC3 — infiltrative mucinous carcinoma, FIGO IB–IC3 (adjuvant ChT)

## NEOC

- Adjuvant_ChT — adjuvant chemotherapy
- HDCT_ASCT — high-dose chemotherapy plus autologous stem-cell transplant
- Pelvic_RT — pelvic radiotherapy
- Stage_IA_G1 — FIGO IA grade 1 (immature teratoma)
- Stage_IA_G2-G3 — FIGO IA grade 2–3 (immature teratoma)
