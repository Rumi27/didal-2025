import csv

def generate_debias_table():
    input_csv = "processed_data/stable_ground_debiasing/pairwise_stable_ground_stats.csv"
    output_tex = "processed_data/stable_ground_debiasing/final_debias_table.tex"

    with open(input_csv, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Format the columns for display
    def format_num(x, decimals=1):
        if not x or x == "NaN" or x == "":
            return "NaN"
        try:
            return f"{float(x):.{decimals}f}"
        except (TypeError, ValueError):
            return "NaN"

    lines = []
    lines.append("\\begin{tabular}{lrrrrrrr}")
    lines.append("\\toprule")
    lines.append(
        "Pair & Bias$_E$ & Bias$_N$ & NMAD$_E$ & NMAD$_N$ & Valid & PCR & $\\sigma_V$ \\\\"
    )
    lines.append(
        "& (m) & (m) & (m) & (m) & frac. & (median) & (m d$^{-1}$) \\\\"
    )
    lines.append("\\midrule")

    for row in rows:
        pair = row["date1"] + "--" + row["date2"]

        stable_sat_frac = float(row.get("stable_saturated_fraction", 0) or 0)
        n_stable_valid = int(row.get("n_stable_valid", 0) or 0)

        if stable_sat_frac == 1.0 or n_stable_valid == 0:
            bias_e = "NaN"
            bias_n = "NaN"
            nmad_e = "NaN"
            nmad_n = "NaN"
            valid_frac = format_num(row.get("valid_fraction"), 2)
            corr = format_num(row.get("stable_corr_median"), 3)
            sig_v = "NaN"
        else:
            # bias_*_m and resid_nmad_*_m are total map-plane displacement (m) over the pair
            # interval — not ice velocity; see table note in manuscript.
            bias_e = format_num(row.get("bias_E_at_glacier_m"), 1)
            bias_n = format_num(row.get("bias_N_at_glacier_m"), 1)
            nmad_e = format_num(row.get("resid_nmad_E_m"), 1)
            nmad_n = format_num(row.get("resid_nmad_N_m"), 1)
            valid_frac = format_num(row.get("valid_fraction"), 2)
            corr = format_num(row.get("stable_corr_median"), 3)
            sig_v = format_num(row.get("vindex_sigma_m_per_day"), 1)

        lines.append(
            f"{pair} & {bias_e} & {bias_n} & {nmad_e} & {nmad_n} & {valid_frac} & {corr} & {sig_v} \\\\"
        )

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")

    with open(output_tex, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Saved {output_tex}")


if __name__ == "__main__":
    generate_debias_table()
