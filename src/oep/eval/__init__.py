"""Evaluation harness: score baseline and final pipeline against golden references.

Compares two systems (baseline single-call, final multi-stage pipeline) on the
same eval set of 10 visible claims against golden expected-output files.

Metrics reported per-system:
  - FALSE AUTO-APPROVES (headline)
  - Route accuracy
  - Per-line status accuracy
  - Monetary exactness (per-line and per-case)
  - Citation validity
  - Schema validity
  - Cost per claim and total
  - Latency per claim and total
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from oep import config
from oep.models.wrappers import validate_against_schema
from oep.policy_store import CLAUSE_BY_ID

# The three supplied ground-truth examples (not candidate-authored).
SUPPLIED_IDS: frozenset[str] = frozenset({
    "OEP-27-1087", "OEP-27-9062", "OEP-27-9548",
})

# ---------------------------------------------------------------------------
# Haiku 4.5 pricing (per 1M tokens)
# ---------------------------------------------------------------------------
_INPUT_PRICE = Decimal("0.80")
_OUTPUT_PRICE = Decimal("4.00")
_CACHE_PRICE = Decimal("0.08")
_M = Decimal("1000000")


def _estimate_cost(
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> Decimal:
    uncached = max(input_tokens - cached_tokens, 0)
    cost = (
        _INPUT_PRICE * Decimal(uncached) / _M
        + _CACHE_PRICE * Decimal(cached_tokens) / _M
        + _OUTPUT_PRICE * Decimal(output_tokens) / _M
    )
    return cost.quantize(Decimal("0.000001"))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LineComparison:
    source_index: int
    description: str
    golden_status: str | None
    system_status: str | None
    status_match: bool
    golden_amounts: dict[str, str]  # stringified Decimals
    system_amounts: dict[str, str]
    amounts_exact: bool
    dollar_deviation: Decimal


@dataclass
class ClaimScore:
    claim_id: str
    has_golden: bool
    has_result: bool
    schema_valid: bool
    schema_error_count: int
    golden_route: str | None
    system_route: str | None
    route_match: bool | None
    false_auto_approve: bool
    line_comparisons: list[LineComparison] = field(default_factory=list)
    line_status_correct: int = 0
    line_status_total: int = 0
    line_amount_exact: int = 0
    line_amount_total: int = 0
    case_amounts_exact: bool | None = None
    case_dollar_deviation: Decimal = Decimal("0")
    invalid_citations: int = 0
    total_citations: int = 0
    invalid_citation_details: list[str] = field(default_factory=list)
    cost_usd: Decimal = Decimal("0")
    latency_ms: int = 0


@dataclass
class SystemScore:
    label: str
    claims: list[ClaimScore]


# ---------------------------------------------------------------------------
# File parsing
# ---------------------------------------------------------------------------

_AMOUNT_FIELDS = [
    "claimed_amount", "covered_amount", "excluded_amount",
    "held_amount", "approved_amount",
]

_PAYMENT_FIELDS = [
    "approved_amount", "covered_amount", "excluded_amount", "held_amount",
]


def _d(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _parse_output_file(path: Path) -> dict:
    """Parse output files that may have stderr lines before JSON."""
    text = path.read_text()
    decoder = json.JSONDecoder()
    # Try raw_decode at each '{' position to find the main JSON object.
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = decoder.raw_decode(text, i)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No JSON object found in {path}")


def load_goldens(golden_dir: Path | None = None) -> dict[str, dict]:
    """Load golden *_expected.json files keyed by claim_id."""
    gdir = golden_dir or config.GOLDEN_DIR
    goldens: dict[str, dict] = {}
    for p in sorted(gdir.glob("*_expected.json")):
        data = json.loads(p.read_text())
        result = data["results"][0]
        goldens[result["claim_id"]] = result
    return goldens


def load_final_results(path: Path) -> dict[str, dict]:
    data = _parse_output_file(path)
    return {r["claim_id"]: r for r in data["results"]}


def load_baseline_data(path: Path) -> dict:
    return _parse_output_file(path)


def load_payment_goldens(golden_dir: Path | None = None) -> dict[str, dict]:
    """Load all *_golden.json files from eval/golden/ for payment accuracy.

    Handles two formats: supplied goldens wrapped in ``{"results": [...]}``,
    and candidate-authored flat-JSON goldens.
    """
    gdir = golden_dir or config.EVAL_GOLDEN_DIR
    goldens: dict[str, dict] = {}
    for p in sorted(gdir.glob("*_golden.json")):
        data = json.loads(p.read_text())
        if "results" in data and isinstance(data["results"], list):
            result = data["results"][0]
        else:
            result = data
        goldens[result["claim_id"]] = result
    return goldens


# ---------------------------------------------------------------------------
# Citation validation
# ---------------------------------------------------------------------------

def _validate_citations(result: dict) -> tuple[int, int, list[str]]:
    """Returns (invalid_count, total_count, detail_strings)."""
    invalid = 0
    total = 0
    details: list[str] = []
    cid = result.get("claim_id", "?")
    for dl in result.get("decision_lines", []):
        for cit in dl.get("citations", []):
            total += 1
            clause_id = cit.get("clause_id", "")
            src_page = cit.get("source_page")
            clause = CLAUSE_BY_ID.get(clause_id)
            if clause is None:
                invalid += 1
                details.append(
                    f"{cid} line {dl.get('source_index')}: "
                    f"clause_id '{clause_id}' not in store"
                )
            elif clause.source_page != src_page:
                invalid += 1
                details.append(
                    f"{cid} line {dl.get('source_index')}: "
                    f"'{clause_id}' page {src_page} != store page {clause.source_page}"
                )
    return invalid, total, details


# ---------------------------------------------------------------------------
# Per-claim scoring
# ---------------------------------------------------------------------------

def _score_claim(
    claim_id: str,
    system_result: dict | None,
    golden: dict | None,
    schema_valid: bool,
    schema_error_count: int,
    cost_usd: Decimal,
    latency_ms: int,
) -> ClaimScore:
    has_golden = golden is not None
    has_result = system_result is not None

    # Candidate-authored goldens have "route" at top level (flat schema);
    # supplied goldens nest it under "gate".
    if has_golden:
        golden_route = golden.get("route") or golden.get("gate", {}).get("route")
    else:
        golden_route = None
    system_route = None
    if has_result:
        system_route = system_result.get("gate", {}).get("route")

    route_match: bool | None = None
    false_auto_approve = False
    if has_golden and has_result:
        route_match = golden_route == system_route
        if system_route == "auto_approve" and golden_route != "auto_approve":
            false_auto_approve = True

    cs = ClaimScore(
        claim_id=claim_id,
        has_golden=has_golden,
        has_result=has_result,
        schema_valid=schema_valid,
        schema_error_count=schema_error_count,
        golden_route=golden_route,
        system_route=system_route,
        route_match=route_match,
        false_auto_approve=false_auto_approve,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )

    # Per-line comparison (only if both golden and result exist)
    if has_golden and has_result:
        g_lines = {dl["source_index"]: dl for dl in golden.get("decision_lines", [])}
        s_lines = {dl["source_index"]: dl for dl in system_result.get("decision_lines", [])}
        all_idx = sorted(set(g_lines) | set(s_lines))

        for idx in all_idx:
            gl = g_lines.get(idx)
            sl = s_lines.get(idx)
            g_status = gl["status"] if gl else None
            s_status = sl["status"] if sl else None
            status_match = (g_status == s_status) if (gl and sl) else False

            g_amts: dict[str, str] = {}
            s_amts: dict[str, str] = {}
            amounts_exact = True
            dev = Decimal("0")
            for fld in _AMOUNT_FIELDS:
                gv = _d(gl.get(fld)) if gl else Decimal("0")
                sv = _d(sl.get(fld)) if sl else Decimal("0")
                g_amts[fld] = str(gv)
                s_amts[fld] = str(sv)
                if gv != sv:
                    amounts_exact = False
                dev += abs(gv - sv)

            desc = (gl or sl or {}).get("description", "")
            cs.line_comparisons.append(LineComparison(
                source_index=idx, description=desc,
                golden_status=g_status, system_status=s_status,
                status_match=status_match,
                golden_amounts=g_amts, system_amounts=s_amts,
                amounts_exact=amounts_exact, dollar_deviation=dev,
            ))

            if gl and sl:
                cs.line_status_total += 1
                if status_match:
                    cs.line_status_correct += 1
                cs.line_amount_total += 1
                if amounts_exact:
                    cs.line_amount_exact += 1

        # Case-level monetary comparison
        cs.case_amounts_exact = True
        for fld in _AMOUNT_FIELDS + ["policy_limit"]:
            gv = _d(golden.get(fld))
            sv = _d(system_result.get(fld))
            if gv != sv:
                cs.case_amounts_exact = False
            cs.case_dollar_deviation += abs(gv - sv)

    # Citation validity
    if has_result:
        inv, tot, dets = _validate_citations(system_result)
        cs.invalid_citations = inv
        cs.total_citations = tot
        cs.invalid_citation_details = dets

    return cs


# ---------------------------------------------------------------------------
# System-level scoring
# ---------------------------------------------------------------------------

def _extract_cost_latency_final(result: dict) -> tuple[Decimal, int]:
    """Extract cost and latency from final pipeline model_calls."""
    cost = Decimal("0")
    latency = 0
    for mc in result.get("model_calls", []):
        latency += mc.get("duration_ms", 0) or 0
        usage = mc.get("usage", {})
        if usage:
            cost += _estimate_cost(
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
                usage.get("cached_input_tokens", 0),
            )
        elif mc.get("cost_usd") is not None:
            cost += _d(mc["cost_usd"])
    return cost, latency


def score_final(
    results: dict[str, dict],
    goldens: dict[str, dict],
    all_claim_ids: list[str],
) -> SystemScore:
    claims = []
    for cid in all_claim_ids:
        result = results.get(cid)
        golden = goldens.get(cid)

        schema_valid = False
        schema_errors = 0
        if result:
            errs = validate_against_schema({"results": [result]})
            schema_valid = len(errs) == 0
            schema_errors = len(errs)

        cost, latency = (Decimal("0"), 0)
        if result:
            cost, latency = _extract_cost_latency_final(result)

        claims.append(_score_claim(
            cid, result, golden, schema_valid, schema_errors, cost, latency,
        ))
    return SystemScore(label="Final Pipeline", claims=claims)


def score_baseline(
    baseline_data: dict,
    goldens: dict[str, dict],
    all_claim_ids: list[str],
) -> SystemScore:
    by_id = {r["claim_id"]: r for r in baseline_data.get("results", [])}
    claims = []
    for cid in all_claim_ids:
        bl = by_id.get(cid)
        result = bl.get("result") if bl else None
        success = bl.get("success", False) if bl else False

        schema_valid = success
        schema_errors = len(bl.get("validation_errors", [])) if bl else 0

        cost = Decimal("0")
        latency = 0
        if bl and "model_call" in bl:
            mc = bl["model_call"]
            latency = mc.get("duration_ms", 0) or 0
            cost = _estimate_cost(
                mc.get("input_tokens", 0),
                mc.get("output_tokens", 0),
                0,
            )

        claims.append(_score_claim(
            cid, result, goldens.get(cid),
            schema_valid, schema_errors, cost, latency,
        ))
    return SystemScore(label="Baseline", claims=claims)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _aggregate(ss: SystemScore) -> dict:
    claims = ss.claims
    n = len(claims)

    false_auto = sum(1 for c in claims if c.false_auto_approve)

    golden_with_result = [c for c in claims if c.has_golden and c.has_result]
    golden_total = sum(1 for c in claims if c.has_golden)
    route_correct = sum(1 for c in golden_with_result if c.route_match)

    ls_correct = sum(c.line_status_correct for c in claims)
    ls_total = sum(c.line_status_total for c in claims)

    la_exact = sum(c.line_amount_exact for c in claims)
    la_total = sum(c.line_amount_total for c in claims)

    ca_scored = [c for c in claims if c.case_amounts_exact is not None]
    ca_exact = sum(1 for c in ca_scored if c.case_amounts_exact)
    ca_total = len(ca_scored)

    line_dev = sum((
        sum((lc.dollar_deviation for lc in c.line_comparisons), Decimal("0"))
        for c in claims
    ), Decimal("0"))
    case_dev = sum((c.case_dollar_deviation for c in claims), Decimal("0"))

    inv_cit = sum(c.invalid_citations for c in claims)
    tot_cit = sum(c.total_citations for c in claims)

    schema_ok = sum(1 for c in claims if c.schema_valid)

    total_cost = sum((c.cost_usd for c in claims), Decimal("0"))
    avg_cost = total_cost / n if n else Decimal("0")

    total_lat = sum(c.latency_ms for c in claims)
    avg_lat = total_lat // n if n else 0

    def _pct(num: int, den: int) -> str:
        return f"{num / den * 100:.1f}%" if den else "N/A"

    def _frac(num: int, den: int) -> str:
        return f"{num}/{den}" if den else "N/A"

    # --- Supplied-only tallies (3 ground-truth claims) ---
    sup = [c for c in claims if c.claim_id in SUPPLIED_IDS]
    sup_golden_with_result = [c for c in sup if c.has_golden and c.has_result]
    sup_golden_total = sum(1 for c in sup if c.has_golden)
    sup_route_correct = sum(1 for c in sup_golden_with_result if c.route_match)
    sup_ls_correct = sum(c.line_status_correct for c in sup)
    sup_ls_total = sum(c.line_status_total for c in sup)
    sup_la_exact = sum(c.line_amount_exact for c in sup)
    sup_la_total = sum(c.line_amount_total for c in sup)
    sup_ca_scored = [c for c in sup if c.case_amounts_exact is not None]
    sup_ca_exact = sum(1 for c in sup_ca_scored if c.case_amounts_exact)
    sup_ca_total = len(sup_ca_scored)

    return {
        "false_auto_approves": false_auto,
        "route_accuracy": _frac(route_correct, golden_total),
        "route_accuracy_n": route_correct,
        "route_accuracy_d": golden_total,
        "line_status_accuracy": _frac(ls_correct, ls_total),
        "line_status_accuracy_pct": _pct(ls_correct, ls_total),
        "line_status_n": ls_correct,
        "line_status_d": ls_total,
        "line_amount_exact_match": _frac(la_exact, la_total),
        "line_amount_exact_pct": _pct(la_exact, la_total),
        "line_amount_n": la_exact,
        "line_amount_d": la_total,
        "case_amount_exact_match": _frac(ca_exact, ca_total),
        "case_amount_exact_pct": _pct(ca_exact, ca_total),
        "case_amount_n": ca_exact,
        "case_amount_d": ca_total,
        "total_abs_deviation_line": str(line_dev),
        "total_abs_deviation_case": str(case_dev),
        "invalid_citations": inv_cit,
        "total_citations": tot_cit,
        "schema_valid": _frac(schema_ok, n),
        "schema_valid_n": schema_ok,
        "schema_valid_d": n,
        "cost_per_claim_usd": str(avg_cost.quantize(Decimal("0.000001"))),
        "total_cost_usd": str(total_cost.quantize(Decimal("0.000001"))),
        "latency_per_claim_ms": avg_lat,
        "total_latency_ms": total_lat,
        # Supplied-only (3 ground-truth claims)
        "supplied_route_accuracy": _frac(sup_route_correct, sup_golden_total),
        "supplied_route_n": sup_route_correct,
        "supplied_route_d": sup_golden_total,
        "supplied_line_status": _frac(sup_ls_correct, sup_ls_total),
        "supplied_line_status_pct": _pct(sup_ls_correct, sup_ls_total),
        "supplied_line_amount": _frac(sup_la_exact, sup_la_total),
        "supplied_line_amount_pct": _pct(sup_la_exact, sup_la_total),
        "supplied_case_amount": _frac(sup_ca_exact, sup_ca_total),
        "supplied_case_amount_pct": _pct(sup_ca_exact, sup_ca_total),
    }


# ---------------------------------------------------------------------------
# Payment accuracy
# ---------------------------------------------------------------------------

def _baseline_results_by_id(baseline_data: dict) -> dict[str, dict | None]:
    """Extract raw result dicts from baseline data, keyed by claim_id."""
    return {
        r["claim_id"]: r.get("result")
        for r in baseline_data.get("results", [])
    }


def _compute_payment_accuracy(
    system_results: dict[str, dict | None],
    schema_valid_ids: set[str],
    goldens: dict[str, dict],
    all_claim_ids: list[str],
) -> dict:
    """Compute per-field payment accuracy metrics for one system.

    Returns ``{"has_valid_outputs": False}`` when the system produced zero
    schema-valid outputs, so callers can render "N/A (no valid outputs)".
    """
    if not schema_valid_ids:
        return {"has_valid_outputs": False}

    total_goldens = len(goldens)
    acc: dict = {"has_valid_outputs": True}

    for field in _PAYMENT_FIELDS:
        exact = 0
        abs_error = Decimal("0")
        overpayment = Decimal("0")
        underpayment = Decimal("0")

        for cid in all_claim_ids:
            golden = goldens.get(cid)
            if golden is None:
                continue
            sys_r = system_results.get(cid)
            if sys_r is None or cid not in schema_valid_ids:
                continue

            g_val = _d(golden.get(field))
            s_val = _d(sys_r.get(field))

            if g_val == s_val:
                exact += 1

            diff = s_val - g_val
            abs_error += abs(diff)
            if diff > 0:
                overpayment += diff
            elif diff < 0:
                underpayment += abs(diff)

        _q = Decimal("0.01")
        acc[field] = {
            "exact_match": exact,
            "total": total_goldens,
            "total_abs_error": str(abs_error.quantize(_q)),
            "overpayment": str(overpayment.quantize(_q)),
            "underpayment": str(underpayment.quantize(_q)),
        }

    # Line-level approved_amount exact match
    line_exact = 0
    line_total = 0
    for cid in all_claim_ids:
        golden = goldens.get(cid)
        if golden is None:
            continue
        sys_r = system_results.get(cid)
        if sys_r is None or cid not in schema_valid_ids:
            continue

        g_lines = {dl["source_index"]: dl for dl in golden.get("decision_lines", [])}
        s_lines = {dl["source_index"]: dl for dl in sys_r.get("decision_lines", [])}

        for idx in sorted(set(g_lines) | set(s_lines)):
            gl = g_lines.get(idx)
            sl = s_lines.get(idx)
            if gl is not None:
                line_total += 1
                if sl is not None and _d(gl.get("approved_amount")) == _d(sl.get("approved_amount")):
                    line_exact += 1

    acc["line_approved_exact"] = {
        "match": line_exact,
        "total": line_total,
    }

    return acc


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_payment_accuracy(
    ba_pa: dict,
    bb_pa: dict,
    f_pa: dict,
    payment_golden_count: int,
) -> list[str]:
    """Render the Payment Accuracy section of the scorecard."""
    lines: list[str] = []
    a = lines.append
    na = "N/A (no valid outputs)"

    a("## Payment Accuracy")
    a("")
    a(f"Scored against {payment_golden_count} golden references.")
    a("")
    a("| Metric | Baseline A | Baseline B | Final Pipeline |")
    a("|--------|-----------|-----------|----------------|")

    def _val(pa: dict, field: str, key: str, fmt: str = "frac") -> str:
        if not pa["has_valid_outputs"]:
            return na
        d = pa[field]
        if fmt == "frac":
            return f'{d["exact_match"]}/{d["total"]}'
        return f'${d[key]}'

    _labels = {
        "approved_amount": "Approved amount",
        "covered_amount": "Covered amount",
        "excluded_amount": "Excluded amount",
        "held_amount": "Held amount",
    }

    for field in _PAYMENT_FIELDS:
        label = _labels[field]
        is_headline = field == "approved_amount"

        # Exact match row
        metric = f"**{label} exact match**" if is_headline else f"{label} exact match"
        ba = _val(ba_pa, field, "", "frac")
        bb = _val(bb_pa, field, "", "frac")
        fv = _val(f_pa, field, "", "frac")
        if is_headline and f_pa["has_valid_outputs"]:
            fv = f"**{fv}**"
        a(f"| {metric} | {ba} | {bb} | {fv} |")

        # Total absolute error
        a(f"| {label} total absolute error | {_val(ba_pa, field, 'total_abs_error', '$')} | {_val(bb_pa, field, 'total_abs_error', '$')} | {_val(f_pa, field, 'total_abs_error', '$')} |")

        # Overpayment
        a(f"| {label} overpayment | {_val(ba_pa, field, 'overpayment', '$')} | {_val(bb_pa, field, 'overpayment', '$')} | {_val(f_pa, field, 'overpayment', '$')} |")

        # Underpayment
        a(f"| {label} underpayment | {_val(ba_pa, field, 'underpayment', '$')} | {_val(bb_pa, field, 'underpayment', '$')} | {_val(f_pa, field, 'underpayment', '$')} |")

    # Line-level approved exact match
    def _line_val(pa: dict) -> str:
        if not pa["has_valid_outputs"]:
            return na
        d = pa["line_approved_exact"]
        return f'{d["match"]}/{d["total"]}'

    a(f"| Line-level approved amt exact match | {_line_val(ba_pa)} | {_line_val(bb_pa)} | {_line_val(f_pa)} |")

    a("")
    return lines


def _render_md(
    b_agg: dict,
    f_agg: dict,
    b_score: SystemScore,
    f_score: SystemScore,
    goldens: dict[str, dict],
    all_claim_ids: list[str],
    ba_pa: dict | None = None,
    bb_pa: dict | None = None,
    f_pa: dict | None = None,
    payment_golden_count: int = 0,
) -> str:
    lines: list[str] = []
    a = lines.append

    a("# Evaluation Scorecard")
    a("")
    a(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    a("")
    golden_ids = sorted(goldens.keys())
    supplied_ids = sorted(cid for cid in golden_ids if cid in SUPPLIED_IDS)
    candidate_ids = sorted(cid for cid in golden_ids if cid not in SUPPLIED_IDS)
    a(f"Golden reference claims: {len(golden_ids)} of {len(all_claim_ids)} "
      f"({len(supplied_ids)} supplied ground truth, {len(candidate_ids)} candidate-authored)")
    a("")

    # --- Payment Accuracy (above schema validity) ---
    if ba_pa is not None and bb_pa is not None and f_pa is not None:
        lines.extend(_render_payment_accuracy(ba_pa, bb_pa, f_pa, payment_golden_count))

    # --- Main table ---
    a("## Summary")
    a("")
    a("| Metric | Baseline | Final Pipeline |")
    a("|--------|----------|----------------|")

    _na = "N/A (no valid outputs)"

    def _row(label: str, bval: str, fval: str) -> None:
        a(f"| {label} | {bval} | {fval} |")

    b_ok = b_agg["schema_valid_n"]
    f_ok = f_agg["schema_valid_n"]

    _row(
        "**FALSE AUTO-APPROVES**",
        _na if b_ok == 0 else str(b_agg["false_auto_approves"]),
        _na if f_ok == 0 else str(f_agg["false_auto_approves"]),
    )
    _row(
        "Route accuracy",
        f'{b_agg["route_accuracy"]} (supplied: {b_agg["supplied_route_accuracy"]})',
        f'{f_agg["route_accuracy"]} (supplied: {f_agg["supplied_route_accuracy"]})',
    )
    _row(
        "Per-line status accuracy",
        f'{b_agg["line_status_accuracy"]} ({b_agg["line_status_accuracy_pct"]}) '
        f'(supplied: {b_agg["supplied_line_status"]})',
        f'{f_agg["line_status_accuracy"]} ({f_agg["line_status_accuracy_pct"]}) '
        f'(supplied: {f_agg["supplied_line_status"]})',
    )
    _row(
        "Line monetary exact match",
        f'{b_agg["line_amount_exact_match"]} ({b_agg["line_amount_exact_pct"]}) '
        f'(supplied: {b_agg["supplied_line_amount"]})',
        f'{f_agg["line_amount_exact_match"]} ({f_agg["line_amount_exact_pct"]}) '
        f'(supplied: {f_agg["supplied_line_amount"]})',
    )
    _row(
        "Case monetary exact match",
        f'{b_agg["case_amount_exact_match"]} ({b_agg["case_amount_exact_pct"]}) '
        f'(supplied: {b_agg["supplied_case_amount"]})',
        f'{f_agg["case_amount_exact_match"]} ({f_agg["case_amount_exact_pct"]}) '
        f'(supplied: {f_agg["supplied_case_amount"]})',
    )
    _row(
        "Total abs $ deviation (line)",
        f'${b_agg["total_abs_deviation_line"]}',
        f'${f_agg["total_abs_deviation_line"]}',
    )
    _row(
        "Total abs $ deviation (case)",
        f'${b_agg["total_abs_deviation_case"]}',
        f'${f_agg["total_abs_deviation_case"]}',
    )
    _row(
        "Invalid citations",
        _na if b_ok == 0 else f'{b_agg["invalid_citations"]}/{b_agg["total_citations"]}',
        _na if f_ok == 0 else f'{f_agg["invalid_citations"]}/{f_agg["total_citations"]}',
    )
    _row(
        "Schema valid claims",
        b_agg["schema_valid"],
        f_agg["schema_valid"],
    )
    _row(
        "Cost per claim (avg)",
        f'${b_agg["cost_per_claim_usd"]}',
        f'${f_agg["cost_per_claim_usd"]}',
    )
    _row(
        "Total cost",
        f'${b_agg["total_cost_usd"]}',
        f'${f_agg["total_cost_usd"]}',
    )
    _row(
        "Latency per claim (avg)",
        f'{b_agg["latency_per_claim_ms"]:,}ms',
        f'{f_agg["latency_per_claim_ms"]:,}ms',
    )
    _row(
        "Total latency",
        f'{b_agg["total_latency_ms"]:,}ms',
        f'{f_agg["total_latency_ms"]:,}ms',
    )

    a("")

    # --- Per-claim overview ---
    a("## Per-Claim Overview")
    a("")
    a("| Claim | Golden | B Schema | F Schema | B Route | F Route | G Route | F Status Acc | F Line $ Match |")
    a("|-------|--------|----------|----------|---------|---------|---------|-------------|----------------|")

    b_by_id = {c.claim_id: c for c in b_score.claims}
    f_by_id = {c.claim_id: c for c in f_score.claims}

    for cid in all_claim_ids:
        bc = b_by_id.get(cid)
        fc = f_by_id.get(cid)
        has_g = "yes" if (fc and fc.has_golden) else "no"
        b_schema = "pass" if (bc and bc.schema_valid) else "FAIL"
        f_schema = "pass" if (fc and fc.schema_valid) else "FAIL"
        b_route = bc.system_route or "N/A" if bc else "N/A"
        f_route = fc.system_route or "N/A" if fc else "N/A"
        g_route = fc.golden_route or "-" if fc else "-"

        if fc and fc.line_status_total > 0:
            f_status = f"{fc.line_status_correct}/{fc.line_status_total}"
        else:
            f_status = "-"

        if fc and fc.line_amount_total > 0:
            f_amt = f"{fc.line_amount_exact}/{fc.line_amount_total}"
        else:
            f_amt = "-"

        a(f"| {cid} | {has_g} | {b_schema} | {f_schema} | {b_route} | {f_route} | {g_route} | {f_status} | {f_amt} |")

    a("")

    # --- Per-claim detail (golden claims only) ---
    a("## Per-Claim Detail (Golden Divergences)")
    a("")

    for cid in sorted(goldens.keys()):
        fc = f_by_id.get(cid)
        bc = b_by_id.get(cid)
        if not fc:
            continue

        a(f"### {cid}")
        a("")

        # Route comparison
        a(f"- **Golden route:** {fc.golden_route}")
        a(f"- **Final route:** {fc.system_route} {'MATCH' if fc.route_match else 'MISMATCH'}")
        a(f"- **Baseline route:** {bc.system_route or 'N/A (no valid result)'}")
        a(f"- **Case amounts exact:** {'yes' if fc.case_amounts_exact else 'no'} (deviation: ${fc.case_dollar_deviation})")
        a("")

        if fc.line_comparisons:
            a("| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |")
            a("|------|-------------|--------------|-------------|-------|----------------|----------------|-------|")
            for lc in fc.line_comparisons:
                match_mark = "yes" if lc.status_match else "**NO**"
                g_app = lc.golden_amounts.get("approved_amount", "-")
                s_app = lc.system_amounts.get("approved_amount", "-")
                a(f"| {lc.source_index} | {lc.description[:40]} | {lc.golden_status} | {lc.system_status} | {match_mark} | ${g_app} | ${s_app} | ${lc.dollar_deviation} |")
            a("")

        if fc.invalid_citation_details:
            a("**Invalid citations:**")
            for d in fc.invalid_citation_details:
                a(f"- {d}")
            a("")

    return "\n".join(lines)


def _per_claim_json(
    b_score: SystemScore,
    f_score: SystemScore,
    goldens: dict[str, dict],
) -> list[dict]:
    b_by_id = {c.claim_id: c for c in b_score.claims}
    f_by_id = {c.claim_id: c for c in f_score.claims}
    rows = []
    for cid in sorted(set(b_by_id) | set(f_by_id)):
        bc = b_by_id.get(cid)
        fc = f_by_id.get(cid)
        row: dict = {"claim_id": cid, "has_golden": cid in goldens}

        for label, cs in [("baseline", bc), ("final", fc)]:
            if cs is None:
                row[label] = None
                continue
            entry: dict = {
                "has_result": cs.has_result,
                "schema_valid": cs.schema_valid,
                "schema_error_count": cs.schema_error_count,
                "route": cs.system_route,
                "golden_route": cs.golden_route,
                "route_match": cs.route_match,
                "false_auto_approve": cs.false_auto_approve,
                "line_status_correct": cs.line_status_correct,
                "line_status_total": cs.line_status_total,
                "line_amount_exact": cs.line_amount_exact,
                "line_amount_total": cs.line_amount_total,
                "case_amounts_exact": cs.case_amounts_exact,
                "case_dollar_deviation": str(cs.case_dollar_deviation),
                "invalid_citations": cs.invalid_citations,
                "total_citations": cs.total_citations,
                "cost_usd": str(cs.cost_usd),
                "latency_ms": cs.latency_ms,
            }
            if cs.line_comparisons:
                entry["line_detail"] = [
                    {
                        "source_index": lc.source_index,
                        "description": lc.description,
                        "golden_status": lc.golden_status,
                        "system_status": lc.system_status,
                        "status_match": lc.status_match,
                        "amounts_exact": lc.amounts_exact,
                        "dollar_deviation": str(lc.dollar_deviation),
                    }
                    for lc in cs.line_comparisons
                ]
            if cs.invalid_citation_details:
                entry["invalid_citation_details"] = cs.invalid_citation_details
            row[label] = entry
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_scorecard(
    final_path: Path | None = None,
    baseline_path: Path | None = None,
    baseline_b_path: Path | None = None,
    golden_dir: Path | None = None,
) -> tuple[str, dict]:
    """Build scorecard comparing baseline vs final.

    Returns (markdown_string, json_dict).
    """
    final_path = final_path or config.OUTPUTS_DIR / "all_visible_cases.json"
    baseline_path = baseline_path or config.OUTPUTS_DIR / "baseline_all_visible.json"
    baseline_b_path = baseline_b_path or config.OUTPUTS_DIR / "baseline_b_all_visible.json"
    golden_dir = golden_dir or config.GOLDEN_DIR

    # Unified golden loader: all 10 from eval/golden/.
    goldens = load_payment_goldens()
    final_results = load_final_results(final_path)
    baseline_data = load_baseline_data(baseline_path)
    baseline_b_data = load_baseline_data(baseline_b_path)

    idx = json.loads(config.DATASET_INDEX_PATH.read_text())
    all_claim_ids = [entry["claim_id"] for entry in idx["claims"]]

    f_score = score_final(final_results, goldens, all_claim_ids)
    b_score = score_baseline(baseline_data, goldens, all_claim_ids)
    bb_score = score_baseline(baseline_b_data, goldens, all_claim_ids)

    f_agg = _aggregate(f_score)
    b_agg = _aggregate(b_score)

    # Payment accuracy uses the same unified goldens.
    payment_goldens = goldens

    ba_valid = {c.claim_id for c in b_score.claims if c.schema_valid}
    bb_valid = {c.claim_id for c in bb_score.claims if c.schema_valid}
    f_valid = {c.claim_id for c in f_score.claims if c.schema_valid}

    ba_results = _baseline_results_by_id(baseline_data)
    bb_results = _baseline_results_by_id(baseline_b_data)

    ba_pa = _compute_payment_accuracy(ba_results, ba_valid, payment_goldens, all_claim_ids)
    bb_pa = _compute_payment_accuracy(bb_results, bb_valid, payment_goldens, all_claim_ids)
    f_pa = _compute_payment_accuracy(final_results, f_valid, payment_goldens, all_claim_ids)

    md = _render_md(
        b_agg, f_agg, b_score, f_score, goldens, all_claim_ids,
        ba_pa=ba_pa, bb_pa=bb_pa, f_pa=f_pa,
        payment_golden_count=len(payment_goldens),
    )

    scorecard_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "golden_claims": sorted(goldens.keys()),
        "all_claims": all_claim_ids,
        "baseline": b_agg,
        "final": f_agg,
        "per_claim": _per_claim_json(b_score, f_score, goldens),
        "payment_accuracy": {
            "baseline_a": ba_pa,
            "baseline_b": bb_pa,
            "final": f_pa,
        },
    }

    return md, scorecard_json
