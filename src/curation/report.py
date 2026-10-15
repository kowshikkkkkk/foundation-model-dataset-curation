from __future__ import annotations

from pathlib import Path

from curation.result import StageResult

_METRICS = [
    ("n_records", "Records"),
    ("total_chars", "Total characters"),
    ("mean_chars", "Mean characters"),
    ("median_chars", "Median characters"),
    ("p95_chars", "P95 characters"),
    ("n_tokens", "Tokens"),
    ("vocab_size", "Vocabulary size"),
    ("distinct_1", "distinct-1"),
    ("distinct_2", "distinct-2"),
]


def _pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}%" if d else "-"


def _table(headers: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return lines


def _fmt_dist(d: dict) -> str:
    if not d:
        return "-"
    return ", ".join(f"{k}: {v}" for k, v in sorted(d.items(), key=lambda kv: (-kv[1], kv[0])))


def build_report(stages: list[StageResult], before: dict, after: dict, manifest: dict) -> str:
    raw_in = stages[0].n_in
    final_n = stages[-1].n_out
    total_removed = sum(len(s.removed) for s in stages)
    code = manifest["code"]

    L: list[str] = ["# Dataset Quality Report", ""]

    L += ["## Summary", ""]
    L += [
        f"- **Dataset version:** `{manifest['dataset_version']}`",
        f"- **Created (UTC):** {manifest['created_at_utc']}",
        f"- **Config hash:** `{manifest['config_hash'][:12]}`",
        f"- **Git commit:** `{code['git_commit']}` (uncommitted changes: {code['git_dirty']})",
        f"- **Input lines parsed:** {raw_in}",
        f"- **Records in curated dataset:** {final_n} ({_pct(final_n, raw_in)} retained)",
        f"- **Records removed:** {total_removed}",
        "",
    ]

    L += ["## Funnel", ""]
    rows = [
        [s.stage, s.n_in, s.n_out, len(s.removed), _pct(s.n_out, raw_in)] for s in stages
    ]
    L += _table(["Stage", "In", "Out", "Removed", "Retained vs raw"], rows)
    L.append("")

    L += ["## Removal reasons", ""]
    reason_rows = [
        (s.stage, reason, count)
        for s in stages
        for reason, count in s.reason_counts().items()
    ]
    reason_rows.sort(key=lambda r: (-r[2], r[0], r[1]))
    if reason_rows:
        L += _table(
            ["Stage", "Reason", "Count", "Share of raw input"],
            [[st, rs, c, _pct(c, raw_in)] for st, rs, c in reason_rows],
        )
    else:
        L.append("No records were removed.")
    L.append("")

    samples: list[str] = []
    for s in stages:
        seen: dict[str, list] = {}
        for r in s.removed:
            if r.detail and len(seen.setdefault(r.reason, [])) < 3:
                seen[r.reason].append(r)
        for reason, items in seen.items():
            for r in items:
                samples.append(f"- `{s.stage}` / `{reason}`: record `{r.record_id}`: {r.detail}")
    if samples:
        L += ["## Sample removals", ""] + samples + [""]

    counters = [s for s in stages if s.stats]
    if counters:
        L += ["## Stage counters", ""]
        for s in counters:
            L.append(f"- **{s.stage}**: " + _fmt_dist(s.stats))
        L.append("")

    L += ["## Before and after", ""]
    L += _table(
        ["Metric", "Before", "After"],
        [[label, before[key], after[key]] for key, label in _METRICS],
    )
    L.append("")
    L += _table(
        ["Distribution", "Before", "After"],
        [
            ["Record kinds", _fmt_dist(before["kinds"]), _fmt_dist(after["kinds"])],
            ["Sources", _fmt_dist(before["sources"]), _fmt_dist(after["sources"])],
            ["Languages", _fmt_dist(before["languages"]), _fmt_dist(after["languages"])],
        ],
    )
    L.append("")

    L += [
        "## Notes",
        "",
        "- *Before* is the set of records that parsed and validated at ingest; malformed lines never became records.",
        "- Language is detected after normalization, so *before* has no language counts. See the language stage counters for the distribution of records entering that stage.",
        "- distinct-n is unique n-grams divided by total n-grams. It depends on corpus size and rises mechanically when duplicates are removed, so read it as a description of the data, not a quality score.",
        "- Quality and language thresholds are untuned defaults until they are checked against hand-labeled samples.",
        "",
    ]

    L += ["## Outputs", ""]
    out_rows = [
        [name, info["path"], info["bytes"], f"`{info['sha256']}`"]
        for name, info in manifest["outputs"].items()
    ]
    L += _table(["Format", "Path", "Bytes", "SHA-256"], out_rows)
    L.append("")

    L += ["## Reproducibility", ""]
    L.append(f"- Python {code['python']}")
    for pkg, ver in code["packages"].items():
        L.append(f"- {pkg} {ver}")
    for b in manifest.get("benchmarks", []):
        L.append(f"- Benchmark {b['path']} sha256 `{b['sha256'][:12]}`")
    L.append("- Full configuration and input hashes are in `manifest.json`.")
    L.append("")

    return "\n".join(L)


def write_report(
    stages: list[StageResult], before: dict, after: dict, manifest: dict, out_dir: str | Path
) -> Path:
    path = Path(out_dir) / "quality_report.md"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(build_report(stages, before, after, manifest))
    return path