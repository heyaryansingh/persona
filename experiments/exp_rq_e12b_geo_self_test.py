"""RQ-E12b: zero-model-cost, replayable matched-donor GEO self-test.

This experiment is deliberately narrow. It tests a prespecified NRF2-associated transcript panel in
two preparations from the same Alzheimer donor cohort. It does not measure NRF2 activity, oxidative
damage, ferroptosis, or causality. Twenty pristine offline-container reruns test the executable seam;
thirty paired donor-bootstrap seeds quantify sampling variation in the frozen analysis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from persona import context
from persona.manager import manager
from persona.sessions import (ResearchSession, append_session_artifact, audit_session,
                              read_session, verify_session)
from persona.tools.sandbox import image_digest, run_python


ROOT = Path(__file__).resolve().parent.parent
PERSONA_ID = "curie-3c33"
PROJECT = (ROOT / "personas" / PERSONA_ID / "projects" /
           "the-converged-belief-oxidative-stress-lowers-neu")
DATA = PROJECT / "data"
RUNS = ROOT / "personas" / PERSONA_ID / "runs"
OUT_JSON = ROOT / "results" / "rq_e12b_geo_self_test.json"
OUT_PNG = ROOT / "results" / "rq_e12b_geo_self_test.png"
RERUNS = 20
BOOTSTRAP_SEEDS = 30
REQUIRED_CLAIMS = ("clm_f4c5e47c1470", "clm_cf8d869026bb")
INPUTS = {
    "GSE1297_series_matrix.txt.gz": "7fe93d1e78ea1567625a066a267e28a62de2d421d517f3dd7a12576628d89009",
    "GSE28146_series_matrix.txt.gz": "10416f47a2f531d344b07a366f11d5c1df83665e55b00c84588770caa4791a09",
    "GPL96.annot.gz": "88e0b22362bac779eb220b3b185c80faa6510a92b9358eaad159a561ab4351c4",
}

PREREGISTRATION = """# RQ-E12b preregistration — matched-donor GEO self-test

Question: does a prespecified seven-gene NRF2-associated transcript panel change monotonically with
Alzheimer severity in both fresh-frozen CA1 tissue blocks (GSE1297) and laser-captured CA1 gray
matter from the same donors (GSE28146)?

Panel: SLC7A11, GPX4, GCLC, HMOX1, FTH1, FTL, TFRC. These are NRF2-regulated or linked genes in the
pinned evidence; their equal-weight score is an expression proxy, not a direct NRF2-activity or
ferroptosis-defense measurement. HMOX1 and iron-handling genes can be context-dependent.

Frozen method: use the 30 matched donors; confirm raw MAS5-scale intensities before log2(x+1);
within each dataset z-score each probe across donors; median probes per gene; equal-weight mean of
the seven genes; fit OLS panel_score ~ severity + centered_age + male. Severity is Control=0,
Incipient=1, Moderate=2, Severe=3. Use the same donor resample in both datasets for 30 bootstrap
seeds. Report percentile 95% intervals and seven leave-one-gene-out fits per dataset.

Branches: negative intervals excluding zero in both plus at least 6/7 leave-one-gene-out signs in
both = symmetric decline; positive intervals excluding zero in both = compensatory activation;
opposite reliable signs = tissue/context divergence; anything else = inconclusive. Never force a
supportive result. No branch establishes oxidative damage, causal disease progression, NRF2
activity, or ferroptosis.

Executable gate: at least 18/20 pristine offline Docker reruns exit cleanly and reproduce the exact
summary/scores/bootstrap/leave-one-out hashes with zero numeric error. Preserve code, raw input
hashes, data, output tables, figure, logs, image digest, report, and verifier in one session. Cost=0.
"""


WORKER_SOURCE = r'''from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA = Path("/work/data")
OUT = Path("/work")
EXPECTED = {
    "GSE1297_series_matrix.txt.gz": "7fe93d1e78ea1567625a066a267e28a62de2d421d517f3dd7a12576628d89009",
    "GSE28146_series_matrix.txt.gz": "10416f47a2f531d344b07a366f11d5c1df83665e55b00c84588770caa4791a09",
    "GPL96.annot.gz": "88e0b22362bac779eb220b3b185c80faa6510a92b9358eaad159a561ab4351c4",
}
GENES = ("SLC7A11", "GPX4", "GCLC", "HMOX1", "FTH1", "FTL", "TFRC")
SEVERITY = {"Control": 0, "Incipient": 1, "Moderate": 2, "Severe": 3}
DATASETS = {
    "GSE1297": ("GSE1297_series_matrix.txt.gz", "fresh-frozen CA1 tissue block"),
    "GSE28146": ("GSE28146_series_matrix.txt.gz", "laser-captured CA1 gray matter"),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_float(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("non-finite result")
    return round(value, 12)


def parse_matrix(path):
    metadata = {}
    table = []
    inside = False
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("!Sample_"):
                parts = line.rstrip("\n").split("\t")
                metadata.setdefault(parts[0], []).append([x.strip('"') for x in parts[1:]])
            if line.startswith("!series_matrix_table_begin"):
                inside = True
                continue
            if line.startswith("!series_matrix_table_end"):
                break
            if inside:
                table.append(line)
    if not table:
        raise ValueError(f"matrix table missing: {path.name}")
    expr = pd.read_csv(io.StringIO("".join(table)), sep="\t", quotechar='"', index_col=0)
    expr.index = expr.index.astype(str)
    if not expr.index.is_unique:
        raise ValueError(f"duplicate probe IDs: {path.name}")
    expr = expr.apply(pd.to_numeric, errors="raise")
    accessions = metadata["!Sample_geo_accession"][0]
    titles = metadata["!Sample_title"][0]
    if list(expr.columns) != accessions or len(titles) != len(accessions):
        raise ValueError(f"sample metadata/matrix mismatch: {path.name}")
    characteristics = metadata.get("!Sample_characteristics_ch1", [])
    records = []
    for index, accession in enumerate(accessions):
        fields = {}
        for row in characteristics:
            value = row[index].strip()
            if ":" in value:
                key, item = value.split(":", 1)
                fields[key.strip().casefold()] = item.strip()
        title = titles[index].strip()
        donor_match = re.search(r"(\d+)\s*$", fields.get("ref #", title))
        if not donor_match:
            raise ValueError(f"donor missing for {accession}")
        group = fields.get("group") or fields.get("disease status") or title.split()[0]
        group = group.strip().title()
        if group not in SEVERITY:
            raise ValueError(f"unknown severity {group!r}")
        age_match = re.search(r"\d+(?:\.\d+)?", fields.get("age", ""))
        sex_text = fields.get("sex", "").casefold()
        if not age_match or sex_text not in {"m", "male", "f", "female"}:
            raise ValueError(f"age/sex missing for {accession}")
        records.append({
            "geo_accession": accession,
            "donor": donor_match.group(1),
            "severity_label": group,
            "severity": SEVERITY[group],
            "age": float(age_match.group()),
            "sex": "M" if sex_text in {"m", "male"} else "F",
        })
    meta = pd.DataFrame(records).set_index("donor", drop=False)
    if not meta.index.is_unique:
        raise ValueError(f"duplicate donors in {path.name}")
    return expr, meta


def annotation_map(path):
    rows = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        header = None
        for line in handle:
            if line.startswith("ID\t"):
                header = next(csv.reader([line.rstrip("\n")], delimiter="\t"))
                break
        if header is None:
            raise ValueError("GPL96 annotation header missing")
        for row in csv.DictReader(handle, fieldnames=header, delimiter="\t"):
            if (row.get("ID") or "").startswith("!platform_table_end"):
                break
            rows.append(row)
    mapping = {gene: [] for gene in GENES}
    for row in rows:
        symbols = {part.strip() for part in (row.get("Gene symbol") or "").split("///")}
        for gene in set(GENES) & symbols:
            mapping[gene].append(row["ID"])
    mapping = {gene: sorted(set(probes)) for gene, probes in mapping.items()}
    if any(not probes for probes in mapping.values()) or sum(map(len, mapping.values())) != 13:
        raise ValueError(f"unexpected target mapping: {mapping}")
    return mapping


def fit_ols(frame, score_column="panel_score"):
    y = frame[score_column].to_numpy(float)
    age = frame["age"].to_numpy(float)
    age = age - age.mean()
    male = (frame["sex"].to_numpy() == "M").astype(float)
    severity = frame["severity"].to_numpy(float)
    X = np.column_stack([np.ones(len(frame)), severity, age, male])
    rank = int(np.linalg.matrix_rank(X))
    if rank != X.shape[1]:
        raise ValueError(f"rank-deficient OLS design: {rank}/{X.shape[1]}")
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    residual = y - X @ beta
    dof = len(y) - X.shape[1]
    sigma2 = float(residual @ residual / dof)
    covariance = sigma2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(covariance))
    adjusted = y - beta[2] * age - beta[3] * male + beta[3] * male.mean()
    return {
        "beta": clean_float(beta[1]),
        "analytic_se": clean_float(se[1]),
        "analytic_normal95_low": clean_float(beta[1] - 1.96 * se[1]),
        "analytic_normal95_high": clean_float(beta[1] + 1.96 * se[1]),
        "intercept": clean_float(beta[0]),
        "age_beta": clean_float(beta[2]),
        "male_beta": clean_float(beta[3]),
        "n": int(len(y)),
        "rank": rank,
        "residual_df": int(dof),
        "residual_sd": clean_float(math.sqrt(sigma2)),
        "condition_number": clean_float(np.linalg.cond(X)),
        "adjusted_score": adjusted,
    }


def build_scores(expressions, metadata, mapping, matched):
    all_scores = []
    gene_frames = {}
    diagnostics = {}
    for dataset in DATASETS:
        expr, meta = expressions[dataset], metadata[dataset]
        columns = meta.loc[matched, "geo_accession"].tolist()
        target_probes = sorted({probe for probes in mapping.values() for probe in probes})
        raw = expr.loc[target_probes, columns]
        all_values = expr.to_numpy(float)
        raw_quantiles = np.nanpercentile(all_values, [0, 50, 95, 99, 100])
        if raw_quantiles[3] <= 100 or raw_quantiles[4] <= 1000 or raw_quantiles[0] < 0:
            raise ValueError(f"{dataset} does not meet preregistered raw-intensity log rule: {raw_quantiles}")
        logged = np.log2(raw + 1.0)
        std = logged.std(axis=1, ddof=1)
        if (std <= 0).any():
            raise ValueError(f"constant target probe in {dataset}")
        z = logged.sub(logged.mean(axis=1), axis=0).div(std, axis=0)
        genes = pd.DataFrame(index=columns)
        for gene, probes in mapping.items():
            genes[gene] = z.loc[probes].median(axis=0).reindex(columns)
        genes["panel_score"] = genes[list(GENES)].mean(axis=1)
        genes.index = matched
        gene_frames[dataset] = genes
        frame = meta.loc[matched, ["donor", "severity_label", "severity", "age", "sex"]].copy()
        frame["dataset"] = dataset
        frame["preparation"] = DATASETS[dataset][1]
        frame["panel_score"] = genes["panel_score"]
        model = fit_ols(frame)
        frame["covariate_adjusted_score"] = model.pop("adjusted_score")
        all_scores.append(frame.reset_index(drop=True))
        diagnostics[dataset] = {
            "raw_expression_quantiles": [clean_float(x) for x in raw_quantiles],
            "transform": "log2(x+1), then within-dataset probe z-score",
            "model": model,
        }
    return pd.concat(all_scores, ignore_index=True), gene_frames, diagnostics


def paired_bootstrap(scores, seeds=30):
    datasets = list(DATASETS)
    frames = {name: scores[scores.dataset == name].sort_values("donor").reset_index(drop=True)
              for name in datasets}
    donors = frames[datasets[0]].donor.tolist()
    if any(frame.donor.tolist() != donors for frame in frames.values()):
        raise ValueError("dataset donor order differs")
    rows = []
    for seed in range(seeds):
        indices = np.random.default_rng(seed).integers(0, len(donors), len(donors))
        for dataset, frame in frames.items():
            sampled = frame.iloc[indices].reset_index(drop=True)
            model = fit_ols(sampled)
            rows.append({"seed": seed, "dataset": dataset, "severity_beta": model["beta"],
                         "rank": model["rank"]})
    return pd.DataFrame(rows)


def leave_one_gene_out(scores, gene_frames):
    rows = []
    for dataset, genes in gene_frames.items():
        meta = scores[scores.dataset == dataset].sort_values("donor").reset_index(drop=True)
        genes = genes.loc[meta.donor.tolist()]
        main_sign = int(np.sign(fit_ols(meta)["beta"]))
        for omitted in GENES:
            frame = meta.copy()
            frame["loo_score"] = genes[[gene for gene in GENES if gene != omitted]].mean(axis=1).to_numpy()
            beta = fit_ols(frame, "loo_score")["beta"]
            rows.append({"dataset": dataset, "omitted_gene": omitted, "severity_beta": beta,
                         "same_sign_as_full": bool(int(np.sign(beta)) == main_sign)})
    return pd.DataFrame(rows)


def classify(summary):
    results = summary["datasets"]
    reliable_negative = all(results[d]["bootstrap_95_high"] < 0 and
                            results[d]["loo_same_sign"] >= 6 for d in DATASETS)
    # The preregistered positive branch depends only on both intervals excluding zero; the 6/7 LOO
    # requirement was specified for the negative branch and must not be added post hoc.
    reliable_positive = all(results[d]["bootstrap_95_low"] > 0 for d in DATASETS)
    reliable = {d: results[d]["bootstrap_95_high"] < 0 or results[d]["bootstrap_95_low"] > 0
                for d in DATASETS}
    signs = {d: int(np.sign(results[d]["severity_beta"])) for d in DATASETS}
    if reliable_negative:
        return "symmetric_decline"
    if reliable_positive:
        return "compensatory_activation"
    if all(reliable.values()) and len(set(signs.values())) == 2:
        return "tissue_context_divergence"
    return "inconclusive"


def make_figure(scores_path, summary, output):
    scores = pd.read_csv(scores_path)
    labels = ["Control", "Incipient", "Moderate", "Severe"]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), sharey=True)
    colors = {"GSE1297": "#4f79a7", "GSE28146": "#c65f4a"}
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
        result = summary["datasets"][dataset]
        axis.axhline(0, color="#9ca3af", linewidth=.8, linestyle="--")
        axis.set_xticks(range(4), labels, rotation=20)
        axis.set_title(f"{dataset}\n{DATASETS[dataset][1]}")
        axis.text(.03, .97, (f"adjusted severity β={result['severity_beta']:.3f}\n"
                            f"paired-bootstrap 95% [{result['bootstrap_95_low']:.3f}, "
                            f"{result['bootstrap_95_high']:.3f}]"),
                  transform=axis.transAxes, va="top", fontsize=9,
                  bbox={"facecolor": "white", "edgecolor": "#d1d5db", "alpha": .9})
        axis.grid(axis="y", alpha=.16)
    axes[0].set_ylabel("NRF2-associated seven-gene expression score\n(age/sex-adjusted display)")
    fig.suptitle("Matched-donor CA1 transcriptomic proxy across Alzheimer severity", fontweight="bold")
    fig.text(.5, .01, "Expression proxy, not NRF2 activity, oxidative damage, ferroptosis, or causality.",
             ha="center", color="#8b2f2f", fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, .93))
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white",
                metadata={"Software": "Persona RQ-E12b"})
    plt.close(fig)


def main():
    observed = {name: sha256(DATA / name) for name in EXPECTED}
    if observed != EXPECTED:
        raise ValueError(f"input hash mismatch: {observed}")
    expressions, metadata = {}, {}
    for dataset, (filename, _) in DATASETS.items():
        expressions[dataset], metadata[dataset] = parse_matrix(DATA / filename)
    mapping = annotation_map(DATA / "GPL96.annot.gz")
    shared_probes = sorted(set(expressions["GSE1297"].index) & set(expressions["GSE28146"].index))
    target_probes = sorted({probe for probes in mapping.values() for probe in probes})
    if len(expressions["GSE1297"]) != 22283 or len(expressions["GSE28146"]) != 54675:
        raise ValueError("unexpected expression row count")
    if len(shared_probes) != 22277 or not set(target_probes).issubset(shared_probes):
        raise ValueError("shared-probe contract failed")
    matched = sorted(set(metadata["GSE1297"].index) & set(metadata["GSE28146"].index), key=int)
    if len(metadata["GSE1297"]) != 31 or len(metadata["GSE28146"]) != 30 or len(matched) != 30:
        raise ValueError("sample/matched-donor contract failed")
    for donor in matched:
        left, right = metadata["GSE1297"].loc[donor], metadata["GSE28146"].loc[donor]
        if (left.severity_label, left.age, left.sex) != (right.severity_label, right.age, right.sex):
            raise ValueError(f"matched metadata disagreement for donor {donor}")

    scores, gene_frames, diagnostics = build_scores(expressions, metadata, mapping, matched)
    bootstrap = paired_bootstrap(scores, 30)
    loo = leave_one_gene_out(scores, gene_frames)
    summary = {
        "experiment": "RQ-E12b matched-donor GEO executable self-test",
        "input_sha256": observed,
        "sample_counts": {"GSE1297": 31, "GSE28146": 30, "matched_donors": 30},
        "probe_counts": {"GSE1297": 22283, "GSE28146": 54675, "shared": 22277,
                         "panel": len(target_probes)},
        "gene_probe_map": mapping,
        "bootstrap": {"paired_donor_seeds": 30, "seed_range": [0, 29]},
        "model": "OLS panel_score ~ severity + centered_age + male",
        "datasets": {},
        "limitations": [
            "The two datasets are different preparations from the same donor cohort, not independent cohorts.",
            "The score is a transcriptomic proxy and does not measure NRF2 activity, oxidative damage, ferroptosis, or causality.",
            "HMOX1 and iron-handling genes can be context-dependent; an equal-weight panel is deliberately simple.",
            "Thirty bootstrap seeds describe this small matched cohort and are not population validation.",
        ],
    }
    for dataset in DATASETS:
        model = dict(diagnostics[dataset]["model"])
        severity_beta = model.pop("beta")
        values = bootstrap.loc[bootstrap.dataset == dataset, "severity_beta"].to_numpy(float)
        loo_rows = loo[loo.dataset == dataset]
        summary["datasets"][dataset] = {
            **model,
            "severity_beta": severity_beta,
            "bootstrap_mean": clean_float(values.mean()),
            "bootstrap_95_low": clean_float(np.percentile(values, 2.5)),
            "bootstrap_95_high": clean_float(np.percentile(values, 97.5)),
            "bootstrap_valid": int(len(values)),
            "loo_same_sign": int(loo_rows.same_sign_as_full.sum()),
            "raw_expression_quantiles": diagnostics[dataset]["raw_expression_quantiles"],
            "transform": diagnostics[dataset]["transform"],
        }
    summary["branch"] = classify(summary)

    scores = scores.sort_values(["dataset", "donor"]).reset_index(drop=True)
    bootstrap = bootstrap.sort_values(["seed", "dataset"]).reset_index(drop=True)
    loo = loo.sort_values(["dataset", "omitted_gene"]).reset_index(drop=True)
    scores.to_csv(OUT / "scores.csv", index=False, lineterminator="\n", float_format="%.12g")
    bootstrap.to_csv(OUT / "bootstrap.csv", index=False, lineterminator="\n", float_format="%.12g")
    loo.to_csv(OUT / "leave_one_gene_out.csv", index=False, lineterminator="\n", float_format="%.12g")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True,
                                                   ensure_ascii=False) + "\n", encoding="utf-8")
    make_figure(OUT / "scores.csv", summary, OUT / "figure.png")
    report = [
        "# Matched-donor GEO self-test: NRF2-associated expression and Alzheimer severity",
        "",
        f"**Prespecified branch:** `{summary['branch']}`.",
        "",
    ]
    for dataset in DATASETS:
        result = summary["datasets"][dataset]
        report.append(f"- **{dataset}:** adjusted severity beta {result['severity_beta']:.4f}; "
                      f"paired-bootstrap 95% [{result['bootstrap_95_low']:.4f}, "
                      f"{result['bootstrap_95_high']:.4f}]; "
                      f"leave-one-gene-out sign retention {result['loo_same_sign']}/7.")
    report += [
        "",
        "## Scope",
        "",
        "Expression proxy, not causality. The two assays use different preparations from the same 30 donors, "
        "so agreement is cross-preparation robustness, not independent-cohort replication. The analysis does "
        "not directly measure NRF2 activity, oxidative damage, ferroptosis, or disease modification.",
        "",
        "## Next discriminating work",
        "",
        "Replicate the frozen panel and direction in an independent, cell-type-resolved AD cohort; then pair "
        "transcript scores with direct oxidative-damage and NRF2-activity readouts before making a mechanistic claim.",
    ]
    (OUT / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "branch": summary["branch"],
                      "betas": {d: summary["datasets"][d]["severity_beta"] for d in DATASETS}}))


if __name__ == "__main__":
    main()
'''


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _input_manifest() -> dict:
    items = []
    for name, expected in INPUTS.items():
        path = DATA / name
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = _sha(path.read_bytes())
        if observed != expected:
            raise RuntimeError(f"input hash mismatch for {name}: {observed}")
        items.append({"name": name, "bytes": path.stat().st_size, "sha256": observed})
    return {"files": items, "data_root": str(DATA.relative_to(ROOT)).replace("\\", "/")}


def _evidence_packets(persona) -> list[dict]:
    with context.use(persona):
        packets = [persona.kg.provenance(claim_id) for claim_id in REQUIRED_CLAIMS]
    missing = [claim_id for claim_id, packet in zip(REQUIRED_CLAIMS, packets) if not packet]
    if missing:
        raise RuntimeError(f"required canonical evidence missing: {missing}")
    return packets


def _media_type(name: str) -> str:
    return {".json": "application/json", ".csv": "text/csv", ".png": "image/png",
            ".md": "text/markdown"}.get(Path(name).suffix, "application/octet-stream")


def _branch_claim(summary: dict) -> str:
    results = summary["datasets"]
    numbers = "; ".join(
        f"{dataset} beta={values['severity_beta']:.4f}, bootstrap 95% "
        f"[{values['bootstrap_95_low']:.4f}, {values['bootstrap_95_high']:.4f}], "
        f"LOO={values['loo_same_sign']}/7"
        for dataset, values in results.items())
    return f"The prespecified matched-donor analysis returned branch {summary['branch']}: {numbers}."


def main() -> None:
    persona = manager().get(PERSONA_ID)
    if persona is None:
        raise RuntimeError(f"persona not found: {PERSONA_ID}")
    manifest = _input_manifest()
    evidence = _evidence_packets(persona)
    session = ResearchSession(
        RUNS,
        "Does a prespecified NRF2-associated transcript panel change with Alzheimer severity "
        "across matched fresh-frozen and laser-captured CA1 preparations?",
        model="deterministic-python/no-model",
        metadata={"experiment_id": "RQ-E12b", "cost_usd": 0.0,
                  "required_claim_ids": list(REQUIRED_CLAIMS),
                  "scientific_scope": "matched-donor transcriptomic association; expression proxy, not causality"},
    )
    finished = False
    try:
        prereg = session.store_text("preregistration.md", PREREGISTRATION, media_type="text/markdown",
                                    parent_event_id=session.root_event_id)
        source = session.store_text("exp_rq_e12b_geo_self_test.py", Path(__file__).read_text(encoding="utf-8"),
                                   media_type="text/x-python", parent_event_id=session.root_event_id)
        worker = session.store_text("geo_analysis.py", WORKER_SOURCE, media_type="text/x-python",
                                   parent_event_id=session.root_event_id)
        evidence_artifact = session.store_json("evidence_packet.json", evidence,
                                               parent_event_id=session.root_event_id)
        manifest_artifact = session.store_json("input_manifest.json", manifest,
                                               parent_event_id=session.root_event_id)
        data_artifacts = []
        for name in INPUTS:
            data_artifacts.append(session.store_bytes(f"data/{name}", (DATA / name).read_bytes(),
                                                       media_type="application/gzip",
                                                       parent_event_id=session.root_event_id))
        evidence_event = session.record(
            "evidence_retrieved",
            {"claims": len(evidence), "claim_ids": list(REQUIRED_CLAIMS),
             "artifact_id": evidence_artifact["id"]}, parent_event_id=session.root_event_id)
        data_event = session.record(
            "data_snapshot_pinned",
            {"manifest": manifest_artifact["id"], "files": [a["id"] for a in data_artifacts]},
            parent_event_id=evidence_event)

        expected_outputs = ("summary.json", "scores.csv", "bootstrap.csv",
                            "leave_one_gene_out.csv", "figure.png", "report.md")
        core_outputs = ("summary.json", "scores.csv", "bootstrap.csv", "leave_one_gene_out.csv")
        attempts, reference_hashes, reference_files, reference_summary = [], None, None, None
        execution_event = session.record(
            "execution_started",
            {"pristine_reruns": RERUNS, "bootstrap_seeds": BOOTSTRAP_SEEDS,
             "sandbox_image": image_digest(), "network": "disabled", "data_mount": "read-only"},
            parent_event_id=data_event)
        for run_number in range(RERUNS):
            with tempfile.TemporaryDirectory(prefix=f"persona-e12b-{run_number:02d}-") as temp:
                workdir = Path(temp)
                receipt = run_python(WORKER_SOURCE, workdir, data_dir=DATA, timeout=180,
                                     memory="1g")
                missing = [name for name in expected_outputs if not (workdir / name).is_file()]
                output_bytes = ({name: (workdir / name).read_bytes() for name in expected_outputs}
                                if receipt["exit_code"] == 0 and not missing else {})
                hashes = {name: _sha(data) for name, data in output_bytes.items()}
                if reference_hashes is None and output_bytes:
                    reference_hashes = {name: hashes[name] for name in core_outputs}
                    reference_files = output_bytes
                    reference_summary = json.loads(output_bytes["summary.json"])
                core_match = bool(reference_hashes) and all(hashes.get(name) == reference_hashes[name]
                                                            for name in core_outputs)
                numeric_error = None
                if output_bytes and reference_summary is not None:
                    current = json.loads(output_bytes["summary.json"])
                    numeric_error = max(
                        abs(float(current["datasets"][dataset]["severity_beta"]) -
                            float(reference_summary["datasets"][dataset]["severity_beta"]))
                        for dataset in reference_summary["datasets"])
                clean = receipt["exit_code"] == 0 and not missing and core_match and numeric_error == 0
                attempt = {"run": run_number, "clean": clean, "exit_code": receipt["exit_code"],
                           "timeout": receipt["timeout"], "missing_outputs": missing,
                           "core_hashes": {name: hashes.get(name) for name in core_outputs},
                           "numeric_max_abs_error": numeric_error,
                           "stdout": receipt["stdout"], "stderr": receipt["stderr"]}
                attempts.append(attempt)
                session.record("execution_result", {key: attempt[key] for key in (
                    "run", "clean", "exit_code", "timeout", "missing_outputs",
                    "numeric_max_abs_error")}, parent_event_id=execution_event)

        clean_count = sum(attempt["clean"] for attempt in attempts)
        gate_passed = clean_count >= 18 and reference_files is not None
        replay = {"runs": RERUNS, "clean_runs": clean_count, "gate": ">=18/20",
                  "gate_passed": gate_passed, "reference_core_hashes": reference_hashes,
                  "attempts": attempts, "sandbox": {"image": "persona-sandbox",
                  "image_digest": image_digest(), "network": "none", "memory": "1g",
                  "cpus": 1, "data_mount": "read-only"}}
        replay_artifact = session.store_json("replay_manifest.json", replay,
                                             parent_event_id=execution_event)
        if not gate_passed:
            raise RuntimeError(f"clean-rerun gate failed: {clean_count}/{RERUNS}")

        output_artifacts = {}
        for name, data in reference_files.items():
            output_artifacts[name] = session.store_bytes(name, data, media_type=_media_type(name),
                                                         parent_event_id=execution_event)
        summary = reference_summary
        method_checks = {
            "input_hashes_match": True,
            "sample_counts": summary["sample_counts"],
            "probe_counts": summary["probe_counts"],
            "panel_genes": sorted(summary["gene_probe_map"]),
            "panel_probe_count": sum(len(v) for v in summary["gene_probe_map"].values()),
            "paired_bootstrap_seeds": summary["bootstrap"]["paired_donor_seeds"],
            "clean_reruns": clean_count,
            "exact_core_hashes": reference_hashes,
            "numeric_max_abs_error": max(attempt["numeric_max_abs_error"] or 0 for attempt in attempts),
            "model_cost_usd": 0.0,
            "causal_claim_authorized": False,
        }
        method_ok = (method_checks["sample_counts"]["matched_donors"] == 30 and
                     method_checks["panel_probe_count"] == 13 and
                     method_checks["paired_bootstrap_seeds"] == 30 and clean_count >= 18 and
                     method_checks["numeric_max_abs_error"] == 0 and
                     sorted(method_checks["panel_genes"]) ==
                     sorted(["SLC7A11", "GPX4", "GCLC", "HMOX1", "FTH1", "FTL", "TFRC"]))
        method_checks["ok"] = method_ok
        verifier = session.store_json("method_verifier.json", method_checks,
                                      parent_event_id=execution_event)
        if not method_ok:
            raise RuntimeError("method verifier failed")

        evidence_ids = [f"claim:{claim_id}" for claim_id in REQUIRED_CLAIMS]
        numeric_ids = [output_artifacts[name]["id"] for name in
                       ("summary.json", "scores.csv", "bootstrap.csv",
                        "leave_one_gene_out.csv", "figure.png")]
        conclusions = [
            {"claim": _branch_claim(summary), "status": "TESTED", "confidence": 0.99,
             "evidence_ids": evidence_ids + numeric_ids + [replay_artifact["id"], verifier["id"]]},
            {"claim": "Expression proxy, not causality: these same-donor transcriptomic assays do not "
                      "establish NRF2 activity, oxidative damage, ferroptosis, or disease modification.",
             "status": "SUPPORTED", "confidence": 1.0,
             "evidence_ids": [manifest_artifact["id"], prereg["id"], output_artifacts["report.md"]["id"]]},
            {"claim": "The observed branch will replicate in an independent, cell-type-resolved AD cohort "
                      "and align with direct oxidative-damage and NRF2-activity assays.",
             "status": "UNSUPPORTED_HYPOTHESIS", "confidence": 0.0, "evidence_ids": []},
        ]
        session.update(primary_figure_artifact_id=output_artifacts["figure.png"]["id"],
                       branch=summary["branch"], clean_reruns=clean_count,
                       source_code_artifact_id=source["id"], worker_code_artifact_id=worker["id"])
        session.finalize("completed", title="Matched-donor GEO self-test · NRF2 panel and AD severity",
                         conclusions=conclusions, parent_event_id=execution_event)
        finished = True
        reason = (f"Verified only the prespecified computation and replay scope: {clean_count}/20 "
                  f"clean offline reruns, exact core hashes, zero numeric error, 30 paired bootstrap "
                  f"seeds, and branch {summary['branch']}. This is an expression proxy, not causality.")
        if not audit_session(RUNS, session.id, "verified", reason):
            raise RuntimeError("could not append verifier verdict")
        first_audit = verify_session(RUNS, session.id)
        if not first_audit["ok"] or first_audit["warnings"]:
            audit_session(RUNS, session.id, "invalidated",
                          f"session replay failed after method verification: {first_audit}")
            raise RuntimeError(f"session replay failed: {first_audit}")
        loaded = read_session(RUNS, session.id)
        parent = loaded["events"][-1]["event_id"]
        append_session_artifact(RUNS, session.id, "session_replay_audit.json",
                                json.dumps(first_audit, indent=2).encode(), media_type="application/json",
                                parent_event_id=parent)
        final_audit = verify_session(RUNS, session.id)
        if not final_audit["ok"] or final_audit["warnings"]:
            audit_session(RUNS, session.id, "invalidated",
                          f"final session replay failed: {final_audit}")
            raise RuntimeError(f"final session replay failed: {final_audit}")

        top_result = {"experiment": "RQ-E12b", "session_id": session.id,
                      "gate_passed": True, "clean_reruns": clean_count,
                      "branch": summary["branch"], "datasets": summary["datasets"],
                      "input_manifest": manifest, "method_checks": method_checks,
                      "session_audit": final_audit}
        OUT_JSON.write_text(json.dumps(top_result, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
        OUT_PNG.write_bytes(reference_files["figure.png"])
        print(json.dumps({"ok": True, "session_id": session.id, "clean_reruns": clean_count,
                          "branch": summary["branch"], "audit": final_audit}, indent=2))
    except Exception as exc:
        error = {"error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}
        try:
            session.store_json("failure.json", error, parent_event_id=session.root_event_id)
            if not finished:
                session.finalize("failed", title="RQ-E12b GEO self-test failed", reason=error["error"])
            audit_session(RUNS, session.id, "invalidated", error["error"])
        finally:
            print(json.dumps({"ok": False, "session_id": session.id, **error}, indent=2))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the zero-cost, 20-replay matched-donor GEO self-test."
    )
    parser.parse_args()
    main()
