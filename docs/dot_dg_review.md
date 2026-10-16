# Reviewing DOT and DG files

The figure (`data/<tumour>/img/<graph>.jpg`) is ground truth.

1. Fix **DOT** so topology and labels are correct for the compiler.
2. Regenerate `.dg` (`bin/dot2dg.py` or `make` in `data/<tumour>/dg`).
3. Add `*_curated.dg` only when the compiler’s **conditions** are wrong. Keep it close to the generated file; comment each override.

---

# Part A — DOT

## How to check

**Topology.** 
- Every figure box and edge is present. 
- If the figure is several subgraphs with **no common root**, add a dummy structural root in DOT that points at each subgraph (do not invent a parent above an existing title).

**Conditional vs structural.** 

| Conditional siblings | Structural |
|----------------------|------------|
| Stage, biomarkers, eligibility (operable / inoperable, ChT eligible / ineligible, PD-L1 status, R0 / R1 / R2, progression) | Named regimens, surgery, RT, CRT, surveillance, MDT, testing, titles |
| Short criterion only | Drug names, doses, `[I, A]` |

If a box mixes a criterion with drugs or modalities, **split**: conditional parent → structural child. Eligibility pairs stay conditional. Named regimens are structural unless the box is only an eligibility question.

**Conditional labels** 
- Write explicit ` and ` / ` or `
- prefix comparisons (`<= 40 Age`)
- parentheses when `and` and `or` mix. 
- For known conditions, use the existing tag from `docs/glossary.md` (if the meaning matches: `PS`, `Age`, `TFI`, `Oligometastatic`). Do not invent a synonym (`ECOG_PS` vs `PS`). 
- Do not reuse a tag that already means something else (`PD` = progressive disease). 
- Add a glossary line only for abbreviations or non-obvious new names.

**Structural labels.** 
- Faithful regimen text and evidence brackets 
- ASCII hyphens; drop footnotes and bullets. 
- Keep a `See Figure N` stub if the figure points onward — splice the other graph in curated DG (below). `\n` only between list items.

---

## When to change DOT, and how

Change DOT when topology or a parseable criterion is wrong. Then regenerate `.dg`.

| What you see | Change how |
|--------------|------------|
| Missing / extra / wrong edges vs figure | Fix teh topology to match the figure |
| Several subgraphs, no common root | Dummy structural root in DOT with edges to each subgraph. |
| Criterion plus drug list in one box | Split: short parent for condition → structural child for treatment. |
| `Yes` / `No` under two questions | Distinct tags (`Properly-staged` / `Not_properly-staged`). |
| Spaces making false AND | `Properly staged` → `Properly-staged`. |
| Alternatives glued or slash-separated | `EGFR_mutation or ALK_rearrangement`; expand `/` to `or` (`BRCA1/2` → `BRCA1 or BRCA2`). Parser does not split `/`. |
| Set-union “and” or figure “and/or” | `or` (`premenopausal or postmenopausal`). |
| Infix / glued / unit thresholds | Prefix with spaces: `PS >2` → `> 2 PS`; `PS_0-2` → `>= 0 PS and <= 2 PS`; `T 3-4 cm` → `>= 3 T and <= 4 T`; drop `cm` `%` `months`. |
| Glued TNM | `cT1-2N0` → `(cT1 or cT2) and N0`. |
| Name plus parenthetical cutoff | Keep the cutoff: `Platinum-resistant_relapse (< 3 TFI)` → `< 3 TFI`. |
| Layout `\n` or a line that is only `or` | One criterion, one line; `or` beside the next phrase. Compiler error `expected PHRASE, got OR`. |
| Mix of `and` and `or` | Parentheses. |
| New synonym for a known condition | Use the existing `docs/glossary.md` tag (`PS`, not `ECOG_PS`). Invent a tag only if nothing matches; glossary if it is an abbreviation. |
| Tag collides with another tumour | Distinct name (`PD` = progressive disease; use `Pulmonary_disease`). |
| “See Figure N” stub | Leave the stub in DOT (`See Figure 2`). Do not paste the other figure into DOT. Replace it in **curated DG**. |
| Footnotes, bullets, en-dashes | Strip; ASCII hyphen (`ChT–ICI` → `ChT-ICI`). |

---

# Part B — DG

## How to check

Generated: one root matching the title; DOT fan-out → `branch`; linear/leaves → `node`/`chain`; labels match DOT; shared DOT nodes reused; no placeholders.

Curated, if it exists: same topology and labels; only conditions (or rare inlining) differ; each change comments the compiler line, then `# manual_fix:`; exclusive criteria take one arm; `always()` takes every sibling.

## When to override

Check if autogeneratyed .dg file is correct, and generates correct paths when walk() is executed.

Otherwise copy generated → `<graph>_curated.dg` and change **conditions** only:


| Case | Generated | Curated |
|------|-----------|---------|
| Prefix compare (`<= 40 Age`, `< 3 TFI`, `> 2 PS`, `>= 0 PS and <= 2 PS`) | tag soup `has('<=40')`, `has('Age')` | `le('Age', 40)`, `lt('TFI', 3)`, `gt('PS', 2)`, `all_of(ge('PS', 0), le('PS', 2))` |
| Parallel treatments vs decisions (see below) | `has('Surgery')`, `has('HDCT_ASCT')`, `has('ChT')` | `always()` on each sibling |
| “See Figure N” stub | `node('See Figure 2')` | Replace that node with the other figure’s DG (see below). Not a DOT paste. |

**Parallel treatment options.** For a sibling fan-out, read the **labels**. If a label states a patient condition (stage, biomarker, eligibility, R0/R1, CR vs no CR, operable, …), those siblings are **conditional** — keep `has` / `any_of`. If the labels are only treatments or procedures (Surgery vs RT, HDCT vs pelvic RT, Primary vs Neck, unlabelled ChT arm) and say nothing about the patient, they are **parallel options**: generated `has(label)` is wrong; curated `always()` on each. Same if the figure dashes the boxes.

### “See Figure N” — splice the other graph into curated DG

If generated DG has a stub such as `node('See Figure 2')`, curated DG must substitute **that node** with figure 2’s graph so `walk` continues. Leave the stub in DOT.

Prefer `load_dg` of the other figure’s curated file. If that would recurse (A loads B and B would load A), **inline** the other subgraph instead.

Melanoma: `mel_st3_or_st4` (Figure 2) and `mel_adv_st3_or_st4` (Figure 4) point at each other.

Generated `mel_st3_or_st4.dg` keeps the stub:

```python
branch(
    'Unresectable_disease',
    has('Unresectable_disease'),
    node('See Figure 4')
)
```

Curated `mel_st3_or_st4_curated.dg` loads Figure 4 and uses it in place of the stub:

```python
fig4 = load_dg(_dir / 'mel_adv_st3_or_st4_curated.dg')
# ...
branch(
    'Unresectable_disease',
    has('Unresectable_disease'),
    fig4
)
```

Generated `mel_adv_st3_or_st4.dg` has `node('See Figure 2')` under `Resectable_disease`. Curated `mel_adv_st3_or_st4_curated.dg` **inlines** Figure 2’s resectable Stage III/IV subgraph there. It must not `load_dg('mel_st3_or_st4_curated.dg')` — that file already loads this one as Figure 4.

---

## DOT edit vs DG override

| Problem | Fix |
|---------|-----|
| Wrong boxes/edges; glued criterion+treatment; Yes/No collision; unparseable label; glossary | DOT, regenerate DG |
| Prefix compare → tag soup | Update dg to use le()/ ge() operators |
| Sibling labels have no patient condition (regimens / procedures only) | Curated `always()` |
| Unlabelled treatment sibling | Same: curated `always()` |
| `node('See Figure N')` | Curated: `load_dg` the other graph, or inline if that would recurse (`mel_st3_or_st4` / `mel_adv_st3_or_st4`) |

