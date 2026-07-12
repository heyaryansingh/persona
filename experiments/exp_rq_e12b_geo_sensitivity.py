"""Append-only robustness audit for the completed RQ-E12b GEO session.

This does not rewrite the preregistered 30-draw result. It responds to independent review with a
10,000-draw paired bootstrap, HC3 intervals, influence diagnostics, FTL-excluded sensitivity, and
an age/sex-adjusted figure, then appends a scoped contested verdict to the original session.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.exp_rq_e12b_geo_self_test import DATA, WORKER_SOURCE
from persona.sessions import (append_session_artifact, audit_session, read_session,
                              verify_session)
from persona.tools.sandbox import image_digest, run_python


ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "personas" / "curie-3c33" / "runs"
SESSION_ID = "20260711T194501Z-does-a-prespecified-nrf2-associated-tran-08c6fd9b"
OUT_JSON = ROOT / "results" / "rq_e12b_geo_sensitivity.json"
OUT_PNG = ROOT / "results" / "rq_e12b_geo_sensitivity.png"

_GUARD = '\n\nif __name__ == "__main__":\n    main()\n'
if _GUARD not in WORKER_SOURCE:
    raise RuntimeError("primary worker guard changed; sensitivity library extraction is unsafe")
PRIMARY_LIBRARY = WORKER_SOURCE.rsplit(_GUARD, 1)[0]

SENSITIVITY_BODY = r'''

BOOTSTRAP_DRAWS = 10_000
T95_DF26 = 2.055529438642871


def design(frame, score_column):
    y = frame[score_column].to_numpy(float)
    age = frame["age"].to_numpy(float)
    age = age - age.mean()
    male = (frame["sex"].to_numpy() == "M").astype(float)
    X = np.column_stack([np.ones(len(frame)), frame["severity"].to_numpy(float), age, male])
    if np.linalg.matrix_rank(X) != 4:
        raise ValueError("rank-deficient sensitivity design")
    return X, y


def beta_only(X, y, indices):
    sampled_x, sampled_y = X[indices], y[indices]
    if np.linalg.matrix_rank(sampled_x) != 4:
        return None
    return float(np.linalg.lstsq(sampled_x, sampled_y, rcond=None)[0][1])


def robust_diagnostics(frame, score_column):
    X, y = design(frame, score_column)
    inverse = np.linalg.inv(X.T @ X)
    beta = inverse @ X.T @ y
    fitted = X @ beta
    residual = y - fitted
    leverage = np.sum((X @ inverse) * X, axis=1)
    adjusted_sq = residual ** 2 / np.maximum((1 - leverage) ** 2, 1e-12)
    meat = X.T @ (X * adjusted_sq[:, None])
    covariance = inverse @ meat @ inverse
    hc3_se = float(np.sqrt(covariance[1, 1]))
    dof = len(y) - X.shape[1]
    mse = float(residual @ residual / dof)
    studentized = residual / np.sqrt(np.maximum(mse * (1 - leverage), 1e-12))
    cook = (residual ** 2 / (X.shape[1] * mse)) * leverage / np.maximum((1 - leverage) ** 2, 1e-12)
    sd = float(residual.std(ddof=0))
    standardized = residual / sd if sd else residual
    fitted_corr = float(np.corrcoef(fitted, residual)[0, 1]) if fitted.std() and residual.std() else 0.0
    return {
        "severity_beta": clean_float(beta[1]),
        "hc3_se": clean_float(hc3_se),
        "hc3_t95_low": clean_float(beta[1] - T95_DF26 * hc3_se),
        "hc3_t95_high": clean_float(beta[1] + T95_DF26 * hc3_se),
        "max_abs_studentized_residual": clean_float(np.max(np.abs(studentized))),
        "max_leverage": clean_float(np.max(leverage)),
        "leverage_over_2p_over_n": int(np.sum(leverage > 2 * X.shape[1] / len(y))),
        "max_cooks_distance": clean_float(np.max(cook)),
        "cooks_over_4_over_n": int(np.sum(cook > 4 / len(y))),
        "residual_skew": clean_float(np.mean(standardized ** 3)),
        "residual_excess_kurtosis": clean_float(np.mean(standardized ** 4) - 3),
        "fitted_residual_correlation": clean_float(fitted_corr),
        "n": len(y),
        "rank": int(np.linalg.matrix_rank(X)),
        "condition_number": clean_float(np.linalg.cond(X)),
    }


def corrected_branch(results, loo):
    negative = all(results[d]["bootstrap_95_high"] < 0 and loo[d] >= 6 for d in DATASETS)
    positive = all(results[d]["bootstrap_95_low"] > 0 for d in DATASETS)
    reliable = {d: results[d]["bootstrap_95_high"] < 0 or results[d]["bootstrap_95_low"] > 0
                for d in DATASETS}
    signs = {d: int(np.sign(results[d]["severity_beta"])) for d in DATASETS}
    if negative:
        return "symmetric_decline"
    if positive:
        return "compensatory_activation"
    if all(reliable.values()) and len(set(signs.values())) == 2:
        return "tissue_context_divergence"
    return "inconclusive"


def adjusted_figure(scores, summary, output):
    labels = ["Control", "Incipient", "Moderate", "Severe"]
    colors = {"GSE1297": "#4f79a7", "GSE28146": "#c65f4a"}
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), sharey=True)
    for axis, dataset in zip(axes, DATASETS):
        frame = scores[scores.dataset == dataset]
        for _, row in frame.iterrows():
            digest = hashlib.sha256(f"{dataset}|{row.donor}".encode()).digest()[0]
            jitter = (digest / 255 - .5) * .24
            axis.scatter(row.severity + jitter, row.covariate_adjusted_score, s=27, alpha=.78,
                         color=colors[dataset], edgecolor="white", linewidth=.45)
        for severity in range(4):
            values = frame.loc[frame.severity == severity, "covariate_adjusted_score"].to_numpy(float)
            mean = float(values.mean())
            half = 1.96 * float(values.std(ddof=1)) / math.sqrt(len(values)) if len(values) > 1 else 0
            axis.errorbar(severity, mean, yerr=half, fmt="D", color="#111827", capsize=3,
                          markersize=5, linewidth=1.2)
        result = summary["datasets"][dataset]["full_panel"]
        axis.axhline(0, color="#9ca3af", linewidth=.8, linestyle="--")
        axis.set_xticks(range(4), labels, rotation=20)
        axis.set_title(f"{dataset}\n{DATASETS[dataset][1]}")
        axis.text(.03, .97, (f"adjusted severity beta={result['severity_beta']:.3f}\n"
                            f"10,000-draw bootstrap 95% [{result['bootstrap_95_low']:.3f}, "
                            f"{result['bootstrap_95_high']:.3f}]\n"
                            f"HC3 t 95% [{result['hc3_t95_low']:.3f}, {result['hc3_t95_high']:.3f}]"),
                  transform=axis.transAxes, va="top", fontsize=8.5,
                  bbox={"facecolor": "white", "edgecolor": "#d1d5db", "alpha": .92})
        axis.grid(axis="y", alpha=.16)
    axes[0].set_ylabel("NRF2-associated seven-gene expression score\n(age/sex-adjusted display)")
    fig.suptitle("Matched-donor GEO sensitivity: robust uncertainty and adjusted display",
                 fontweight="bold")
    fig.text(.5, .01, "All robust intervals include zero. Expression proxy, not causality.",
             ha="center", color="#8b2f2f", fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, .93))
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white",
                metadata={"Software": "Persona RQ-E12b sensitivity"})
    plt.close(fig)


def sensitivity_main():
    observed = {name: sha256(DATA / name) for name in EXPECTED}
    if observed != EXPECTED:
        raise ValueError("input hash mismatch")
    expressions, metadata = {}, {}
    for dataset, (filename, _) in DATASETS.items():
        expressions[dataset], metadata[dataset] = parse_matrix(DATA / filename)
    mapping = annotation_map(DATA / "GPL96.annot.gz")
    matched = sorted(set(metadata["GSE1297"].index) & set(metadata["GSE28146"].index), key=int)
    scores, gene_frames, _ = build_scores(expressions, metadata, mapping, matched)
    loo_table = leave_one_gene_out(scores, gene_frames)
    loo = {dataset: int(loo_table[loo_table.dataset == dataset].same_sign_as_full.sum())
           for dataset in DATASETS}

    frames, arrays, gene_rows = {}, {}, []
    for dataset in DATASETS:
        frame = scores[scores.dataset == dataset].sort_values("donor").reset_index(drop=True).copy()
        genes = gene_frames[dataset].loc[frame.donor.tolist()]
        frame["no_ftl_score"] = genes[[gene for gene in GENES if gene != "FTL"]].mean(axis=1).to_numpy()
        frames[dataset] = frame
        arrays[dataset] = {
            "full_panel": design(frame, "panel_score"),
            "without_ftl": design(frame, "no_ftl_score"),
        }
        for index, row in frame.iterrows():
            item = {"dataset": dataset, "donor": row.donor, "severity": int(row.severity),
                    "age": row.age, "sex": row.sex, "panel_score": row.panel_score,
                    "no_ftl_score": row.no_ftl_score}
            item.update({gene: float(genes.iloc[index][gene]) for gene in GENES})
            gene_rows.append(item)

    bootstrap_rows = []
    values = {dataset: {panel: [] for panel in ("full_panel", "without_ftl")}
              for dataset in DATASETS}
    for seed in range(BOOTSTRAP_DRAWS):
        indices = np.random.default_rng(seed).integers(0, len(matched), len(matched))
        for dataset in DATASETS:
            for panel in ("full_panel", "without_ftl"):
                X, y = arrays[dataset][panel]
                beta = beta_only(X, y, indices)
                if beta is None:
                    raise ValueError(f"rank-deficient draw {seed} {dataset} {panel}")
                values[dataset][panel].append(beta)
                bootstrap_rows.append({"seed": seed, "dataset": dataset,
                                       "panel": panel, "severity_beta": beta})

    summary = {"experiment": "RQ-E12b append-only sensitivity audit",
               "status": "post_preregistration_sensitivity", "input_sha256": observed,
               "bootstrap_draws": BOOTSTRAP_DRAWS, "paired_donor_resampling": True,
               "datasets": {}, "limitations": [
                   "The two preparations use the same donors and are not independent cohorts.",
                   "Both FTL probes are cross-hybridizing _x_at probes.",
                   "Sensitivity analyses were added after independent review and do not rewrite the preregistered result.",
                   "Expression is a proxy, not NRF2 activity, oxidative damage, ferroptosis, or causality.",
               ]}
    residual_rows = []
    for dataset in DATASETS:
        summary["datasets"][dataset] = {}
        for panel, score_column in (("full_panel", "panel_score"),
                                    ("without_ftl", "no_ftl_score")):
            diagnostics = robust_diagnostics(frames[dataset], score_column)
            draws = np.asarray(values[dataset][panel])
            result = {**diagnostics,
                      "bootstrap_mean": clean_float(draws.mean()),
                      "bootstrap_95_low": clean_float(np.percentile(draws, 2.5)),
                      "bootstrap_95_high": clean_float(np.percentile(draws, 97.5)),
                      "bootstrap_valid": int(len(draws))}
            summary["datasets"][dataset][panel] = result
            residual_rows.append({"dataset": dataset, "panel": panel, **diagnostics})
        full = summary["datasets"][dataset]["full_panel"]["severity_beta"]
        no_ftl = summary["datasets"][dataset]["without_ftl"]["severity_beta"]
        summary["datasets"][dataset]["ftl_magnitude_reduction_percent"] = clean_float(
            100 * (full - no_ftl) / full)
    full_results = {dataset: summary["datasets"][dataset]["full_panel"] for dataset in DATASETS}
    summary["corrected_preregistered_branch"] = corrected_branch(full_results, loo)
    summary["original_30_draw_branch"] = "inconclusive"
    summary["verdict"] = "contested_scientific_interpretation_computation_reproduced"

    gene_table = pd.DataFrame(gene_rows).sort_values(["dataset", "donor"])
    bootstrap_table = pd.DataFrame(bootstrap_rows).sort_values(["seed", "dataset", "panel"])
    residual_table = pd.DataFrame(residual_rows).sort_values(["dataset", "panel"])
    gene_table.to_csv(OUT / "gene_scores.csv", index=False, lineterminator="\n", float_format="%.12g")
    bootstrap_table.to_csv(OUT / "sensitivity_bootstrap.csv", index=False, lineterminator="\n",
                           float_format="%.12g")
    residual_table.to_csv(OUT / "residual_diagnostics.csv", index=False, lineterminator="\n",
                          float_format="%.12g")
    (OUT / "sensitivity.json").write_text(json.dumps(summary, indent=2, sort_keys=True,
                                                       ensure_ascii=False) + "\n", encoding="utf-8")
    adjusted_figure(scores, summary, OUT / "adjusted_figure.png")
    lines = ["# RQ-E12b append-only sensitivity review", "",
             "Independent review reproduced every core number but contested the scientific presentation.", ""]
    for dataset in DATASETS:
        full = summary["datasets"][dataset]["full_panel"]
        no_ftl = summary["datasets"][dataset]["without_ftl"]
        lines += [f"## {dataset}", "",
                  f"- Full panel beta {full['severity_beta']:.4f}; 10,000-draw bootstrap 95% "
                  f"[{full['bootstrap_95_low']:.4f}, {full['bootstrap_95_high']:.4f}]; HC3 t 95% "
                  f"[{full['hc3_t95_low']:.4f}, {full['hc3_t95_high']:.4f}].",
                  f"- Without FTL beta {no_ftl['severity_beta']:.4f}; bootstrap 95% "
                  f"[{no_ftl['bootstrap_95_low']:.4f}, {no_ftl['bootstrap_95_high']:.4f}].",
                  f"- Removing FTL reduced coefficient magnitude by "
                  f"{summary['datasets'][dataset]['ftl_magnitude_reduction_percent']:.1f}%.", ""]
    lines += ["## Corrected interpretation", "",
              "All robust full-panel and FTL-excluded intervals include zero. The original and corrected "
              "branches remain `inconclusive`; no positive/compensatory inference is supported.", "",
              "The original 30-draw output remains preserved as the preregistered computation. This sensitivity "
              "is append-only and changes the scientific-review verdict to contested, not the trace-integrity verdict.", ""]
    (OUT / "sensitivity_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"ok": True, "branch": summary["corrected_preregistered_branch"],
                      "verdict": summary["verdict"]}))


if __name__ == "__main__":
    sensitivity_main()
'''

SENSITIVITY_SOURCE = PRIMARY_LIBRARY + SENSITIVITY_BODY


def _latest_event_id() -> int:
    loaded = read_session(RUNS, SESSION_ID)
    if loaded is None:
        raise RuntimeError("RQ-E12b session missing")
    return max(event["event_id"] for event in loaded["events"])


def main(*, allow_repeat: bool = False) -> None:
    loaded = read_session(RUNS, SESSION_ID)
    if loaded is None:
        raise RuntimeError("RQ-E12b session missing")
    prior = [artifact for artifact in loaded["session"].get("artifacts", [])
             if artifact.get("name") == "sensitivity_session_audit.json"]
    if prior and not allow_repeat:
        raise RuntimeError(
            "sensitivity is already appended; refusing to mutate the canonical session again. "
            "Use --allow-repeat only for an intentional append-only replication."
        )
    before = verify_session(RUNS, SESSION_ID)
    if not before["ok"] or before["warnings"]:
        raise RuntimeError(f"original session integrity failed: {before}")
    with tempfile.TemporaryDirectory(prefix="persona-e12b-sensitivity-") as temp:
        workdir = Path(temp)
        receipt = run_python(SENSITIVITY_SOURCE, workdir, data_dir=DATA, timeout=180,
                             memory="1g")
        expected = ("sensitivity.json", "gene_scores.csv", "sensitivity_bootstrap.csv",
                    "residual_diagnostics.csv", "adjusted_figure.png", "sensitivity_report.md")
        missing = [name for name in expected if not (workdir / name).is_file()]
        if receipt["exit_code"] != 0 or missing:
            raise RuntimeError(f"sensitivity execution failed: {receipt}; missing={missing}")
        outputs = {name: (workdir / name).read_bytes() for name in expected}
    summary = json.loads(outputs["sensitivity.json"])
    checks = {
        "original_integrity": before,
        "bootstrap_draws": summary["bootstrap_draws"],
        "corrected_branch": summary["corrected_preregistered_branch"],
        "all_full_panel_intervals_include_zero": all(
            result["full_panel"]["bootstrap_95_low"] <= 0 <=
            result["full_panel"]["bootstrap_95_high"]
            for result in summary["datasets"].values()),
        "all_no_ftl_intervals_include_zero": all(
            result["without_ftl"]["bootstrap_95_low"] <= 0 <=
            result["without_ftl"]["bootstrap_95_high"]
            for result in summary["datasets"].values()),
        "sandbox_image_digest": image_digest(),
        "model_cost_usd": 0.0,
    }
    checks["ok"] = (checks["bootstrap_draws"] == 10_000 and
                    checks["corrected_branch"] == "inconclusive" and
                    checks["all_full_panel_intervals_include_zero"] and
                    checks["all_no_ftl_intervals_include_zero"])
    if not checks["ok"]:
        raise RuntimeError(f"sensitivity verifier failed: {checks}")

    parent = _latest_event_id()
    append_session_artifact(RUNS, SESSION_ID, "exp_rq_e12b_geo_sensitivity.py",
                            Path(__file__).read_bytes(), media_type="text/x-python",
                            parent_event_id=parent)
    append_session_artifact(RUNS, SESSION_ID, "geo_sensitivity_worker.py",
                            SENSITIVITY_SOURCE.encode(), media_type="text/x-python",
                            parent_event_id=parent)
    append_session_artifact(RUNS, SESSION_ID, "sensitivity_execution_receipt.json",
                            json.dumps({**receipt, "image_digest": image_digest()}, indent=2).encode(),
                            media_type="application/json", parent_event_id=parent)
    media = {".json": "application/json", ".csv": "text/csv",
             ".png": "image/png", ".md": "text/markdown"}
    for name, data in outputs.items():
        append_session_artifact(RUNS, SESSION_ID, name, data,
                                media_type=media[Path(name).suffix], parent_event_id=parent)
    append_session_artifact(RUNS, SESSION_ID, "sensitivity_verifier.json",
                            json.dumps(checks, indent=2).encode(), media_type="application/json",
                            parent_event_id=parent)

    reason = ("Computation and bundle integrity reproduce, but scientific interpretation is contested: "
              "10,000-draw paired bootstrap and HC3 intervals include zero in both preparations; "
              "cross-hybridizing FTL probes materially affect magnitude; the original 30-draw interval "
              "is unstable. The branch remains inconclusive and no causal/compensatory inference is supported.")
    if not audit_session(RUNS, SESSION_ID, "contested", reason):
        raise RuntimeError("could not append contested verdict")
    audit = verify_session(RUNS, SESSION_ID)
    if not audit["ok"] or audit["warnings"]:
        raise RuntimeError(f"post-sensitivity session audit failed: {audit}")
    append_session_artifact(RUNS, SESSION_ID, "sensitivity_session_audit.json",
                            json.dumps(audit, indent=2).encode(), media_type="application/json",
                            parent_event_id=_latest_event_id())
    final_audit = verify_session(RUNS, SESSION_ID)
    if not final_audit["ok"] or final_audit["warnings"]:
        raise RuntimeError(f"final sensitivity audit failed: {final_audit}")

    top = {"experiment": "RQ-E12b sensitivity", "session_id": SESSION_ID,
           "summary": summary, "checks": checks, "session_audit": final_audit}
    OUT_JSON.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_PNG.write_bytes(outputs["adjusted_figure.png"])
    print(json.dumps({"ok": True, "session_id": SESSION_ID,
                      "verdict": "contested", "audit": final_audit}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Append robustness sensitivity to the canonical RQ-E12b session once."
    )
    parser.add_argument(
        "--allow-repeat", action="store_true",
        help="explicitly append another replication to the canonical session",
    )
    args = parser.parse_args()
    main(allow_repeat=args.allow_repeat)
