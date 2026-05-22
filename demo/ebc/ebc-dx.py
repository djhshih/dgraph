# Early breast cancer treatment overview
# Figure 1, Loibl et al., 2024, https://doi.org/10.1016/j.annonc.2023.11.016

import dgraph.graph as dg
from dgraph.graph import Data, chain, node

graph = chain(
    "Diagnosis and staging of EBC",
    "Bilateral mammogram and US of both breasts and regional LNs [I, A]\nMRI for special situations [I, A]",
    "Core biopsy",
    "Confirmed diagnosis",
    "Assess biomarkers: ER, PgR, HER2; Ki-67 [I, A]\nIn HR+/HER2- NO-1 (if relevant for therapy decision):\ngene expression assays, endocrine response assessment [I, B]\nTest for gBRCA1/2 mutation (if family history or therapeutic relevance) [I, A; ESCCAT I-A]",
    "Disease staging and final pathological assessment according to WHO and UICC TNM8,medical/family history, menopausal status, physical examination [V, A]",
    "Minimum blood work-up (a full blood count, liver and renal function tests, alkaline phosphatase and calcium levels) before surgery and systemic (neo)adjuvant therapy [V, A]",
    "CT scan of the chest, abdominal imaging (US, CT or MRI scan) and a bone scan for patients with:\nclinically positive axillary nodes; large tumours (e.g. 5 cm); aggressive biology; and clinical signs, symptoms or laboratory values suggesting the presence of metastases [III, A]",
    "Clip marking of the lesions if neoadjuvant treatment and BCS is planned",
)

schema = dg.infer_schema(graph)
print(schema)

x = Data(("HR+",))
print(dg.validate_data(schema, x))
print(dg.walk(graph, x))

