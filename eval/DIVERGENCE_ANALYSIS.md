# Divergence Analysis — Golden vs. Pipeline

Three of ten claims diverge between the golden set and the pipeline output.
The remaining seven are exact matches on all scored fields.

---

## 1. OEP-27-4706

### Divergent fields

#### L4 `category`

| | Value |
|---|---|
| Golden | `standard_turnover` |
| Pipeline | `ordinary_upkeep` |

Both sides agree on every other field for L4: status=`excluded`,
claimed=$142, covered=$0, excluded=$142, held=$0, approved=$0.
The adjudication outcome is identical — full exclusion.

#### L0–L3 `description`

| Line | Golden | Pipeline (= source register) |
|------|--------|------------------------------|
| 0 | Floor finish restoration | Kitchen floor finish replacement |
| 1 | Window treatment replacement | Window blind rail and hardware |
| 2 | Electrical labor | Kitchen GFCI receptacle restoration |
| 3 | Countertop panel replacement | Countertop edge panel replacement |

All other fields (category, status, amounts) match on these lines.

### Policy clauses

**L4 category** — OEP-3.2: "Administrative charges, ordinary upkeep, standard
turnover, household-owned property, elective upgrades, duplicate entries, and
amounts outside a supported interval are excluded."

OEP-3.2 lists "ordinary upkeep" and "standard turnover" as separate exclusion
reasons. The source item is literally named "Standard turnover cleaning." The
pipeline's extraction layer maps the source category "routine turnover" to
`ordinary_upkeep`, losing the distinction. The golden maps it to
`standard_turnover`, which matches the item's own name and the specific
exclusion term in OEP-3.2.

**L0–L3 descriptions** — The golden schema defines `description` as "Item
label from the source register." The source register (Premises Condition Log)
uses the pipeline's descriptions verbatim. The golden uses editorial
paraphrases (e.g., "Electrical labor" for "Kitchen GFCI receptacle
restoration").

### Verdicts

**L4 category: GOLDEN CORRECT**

The item is named "Standard turnover cleaning." OEP-3.2 has a specific
exclusion category "standard turnover" that matches the item's own name.
The pipeline classifies it as `ordinary_upkeep` — a different exclusion
category in OEP-3.2 — because its CATEGORY_MAP lacks a `standard_turnover`
mapping. This is a pipeline bug: the normalization layer should map this
item to the matching policy term.

**L0–L3 descriptions: PIPELINE CORRECT**

The golden schema's field definition says "Item label from the source
register." The pipeline preserves the verbatim source labels. The golden
uses paraphrased labels that differ from the source register — in some
cases substantially (e.g., "Electrical labor" for "Kitchen GFCI receptacle
restoration," "Window treatment replacement" for "Window blind rail and
hardware"). The golden descriptions were miscopied or editorially shortened
during golden authoring.

---

## 2. OEP-27-6795

### Divergent fields

#### L0 `status`

| | Value |
|---|---|
| Golden | `covered` |
| Pipeline | `partially_covered` |

Amounts are identical on both sides: claimed=$1,944, covered=$1,261,
excluded=$683, held=$0, approved=$1,261. The $683 excluded amount is a
post-closeout recovery attributed to this line.

#### L2 `category`

| | Value |
|---|---|
| Golden | `unit_restoration` |
| Pipeline | `duplicate` |

Both sides agree L2 is fully excluded (status=`excluded`, excluded=$1,944).
The golden classifies by the line's original nature; the pipeline classifies
by the exclusion reason.

#### L2 `description`

| | Value |
|---|---|
| Golden | Primary wall and trim restoration |
| Pipeline | Primary wall and trim restoration [DUPLICATE OF LINE 1] |

The pipeline appends a duplicate annotation to the source label.

### Policy clauses

**L0 status** — OEP-2.1: "Part A includes a scheduled occupancy amount
remaining at possession return after attributable payments, concessions,
reversals, credits, and recoveries are applied once." OEP-4.1: "apply credits
and recoveries once."

The $683 recovery must be applied once (OEP-4.1). The policy does not
specify which line the recovery offsets. The golden follows a greedy-in-
source-order convention, applying the recovery to L0 and labeling the line
`covered` (because the restoration itself is fully eligible — the recovery
is a separate adjustment). The pipeline also applies the recovery to L0 but
labels it `partially_covered` (because covered_amount < claimed_amount after
the recovery offset).

The line's status is a function of its recovery attribution, which is
convention.

**L2 category** — OEP-3.1: "Each submitted source line must receive one
normalized classification." OEP-4.1: "classify lines, remove exclusions and
duplicates." OEP-3.2: "duplicate entries … are excluded."

OEP-4.1 presents classification and duplicate removal as separate ordered
steps ("classify lines" then "remove … duplicates"). This suggests a line
is first classified by its nature (unit_restoration), then excluded because
it is a duplicate. The golden preserves the nature classification. The
pipeline replaces it with `duplicate` — which is an exclusion reason, not
a nature classification — and annotates the description accordingly.

The policy does not prescribe whether the "one normalized classification"
(OEP-3.1) should reflect the line's original nature or its exclusion reason.

### Verdicts

**L0 status: POLICY SILENT**

The recovery attribution to L0 is convention, not policy-determined (the
golden README and reasoning file acknowledge this explicitly). Status
follows from how the recovery is expressed at the line level. Both
`covered` (recovery is a separate adjustment) and `partially_covered`
(net covered < claimed) are defensible readings. Case totals are firm:
covered=$2,556, excluded=$2,736.

**L2 category: POLICY SILENT**

OEP-3.1 requires "one normalized classification" but does not define
whether a duplicate line's classification is its original nature or
`duplicate`. OEP-4.1's ordering ("classify lines, remove … duplicates")
slightly favors the golden's approach (classify first, exclude second),
but does not prohibit treating `duplicate` as the classification itself.
Both reach the same adjudication outcome.

**L2 description: POLICY SILENT**

The pipeline appends "[DUPLICATE OF LINE 1]" as an annotation. The policy
does not govern description formatting. The annotation is informational and
does not affect adjudication.

---

## 3. OEP-27-8150

### Divergent fields

#### L0–L3 `description`

| Line | Golden | Pipeline (= source register) |
|------|--------|------------------------------|
| 0 | Carpet replacement | Bedroom carpet replacement |
| 1 | Window treatment replacement | Living-room blind track replacement |
| 2 | Life-safety work | Hard-wired smoke alarm restoration |
| 3 | Door closer replacement | Entry door closer replacement |

All other scored fields match exactly on every line: category, status, and
all five amount fields are identical. Case-level totals, route
(`auto_approve`), gate score (100), and disposition (`approved`) all match.

### Policy clauses

The golden schema defines the `description` field as "Item label from the
source register" (golden_schema.json). OEP-1.3 defines a source line as
"one separately presented charge." OEP-5.1 requires the determination to
"retain source-page provenance."

The source register (3_Premises_Condition_Log.docx) presents the items
with the pipeline's descriptions verbatim:

- "Bedroom carpet replacement" — $1,075
- "Living-room blind track replacement" — $438
- "Hard-wired smoke alarm restoration" — $606
- "Entry door closer replacement" — $528

The golden labels are editorial abbreviations. In some cases they
significantly alter meaning: "Life-safety work" is a different
characterization from "Hard-wired smoke alarm restoration"; "Window
treatment replacement" is a broader category than "Living-room blind track
replacement."

### Verdict

**L0–L3 descriptions: PIPELINE CORRECT**

The golden schema's own field definition says "Item label from the source
register." The pipeline preserves the verbatim source labels. The golden
uses paraphrased labels that do not match the source register. The
paraphrasing was an error during golden authoring — the descriptions
should be transcribed from the source, not editorially shortened.

---

## Summary

| Claim | Field(s) | Verdict |
|-------|----------|---------|
| OEP-27-4706 | L4 `category` | **GOLDEN CORRECT** — pipeline bug (missing `standard_turnover` mapping) |
| OEP-27-4706 | L0–L3 `description` | **PIPELINE CORRECT** — golden paraphrased source labels |
| OEP-27-6795 | L0 `status` | **POLICY SILENT** — recovery attribution is convention |
| OEP-27-6795 | L2 `category` | **POLICY SILENT** — duplicate classification convention |
| OEP-27-6795 | L2 `description` | **POLICY SILENT** — annotation formatting convention |
| OEP-27-8150 | L0–L3 `description` | **PIPELINE CORRECT** — golden paraphrased source labels |
