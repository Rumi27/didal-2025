import os
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np

# Editable text in vector PDF (journal-friendly)
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42

# English month abbreviations (locale-independent)
MONTH_ABBR_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def fmt_day_mon_en(x, pos=None):
    """Format date as 'DD Mon' in English."""
    d = mdates.num2date(x)
    return f"{d.day:02d} {MONTH_ABBR_EN[d.month-1]}"

def main():
    data_dir = "processed_data/same_track_12day_comparison"
    orbit1_file = os.path.join(data_dir, "orbit1_12day_debiased.csv")
    orbit2_file = os.path.join(data_dir, "orbit2_12day_debiased.csv")
    output_csv = os.path.join(data_dir, "backbone_12day.csv")
    plot_dir = "figures"
    os.makedirs(plot_dir, exist_ok=True)
    output_plot_png = os.path.join(plot_dir, "backbone_12day_plot.png")
    output_plot_pdf = os.path.join(plot_dir, "backbone_12day_plot.pdf")

    columns_to_keep = [
        "date1", "date2", "orbit_track",
        "glacier_speed_m_per_day_debiased", "glacier_speed_sigma_m_per_day",
        "glacier_corr", "stable_ground_status", "valid_fraction",
        "stable_corr_median", "stable_saturated_fraction"
    ]

    # Read data
    df1 = pd.read_csv(orbit1_file, parse_dates=["date1", "date2"]) if os.path.exists(orbit1_file) else pd.DataFrame()
    df2 = pd.read_csv(orbit2_file, parse_dates=["date1", "date2"]) if os.path.exists(orbit2_file) else pd.DataFrame()

    if df1.empty and df2.empty:
        print("Error: Both input CSVs are missing or empty.")
        return

    # Combine data and keep only requisite columns
    df_combined = pd.concat([df1, df2], ignore_index=True)
    # Check if all needed columns exist, if a column is missing, warn and continue with available ones
    available_cols = [c for c in columns_to_keep if c in df_combined.columns]
    
    # Check if orbit track is missing from concatenation if it wasn't in CSV but passed in name
    if "orbit_track" not in df_combined.columns:
        if not df1.empty: df1['orbit_track'] = 'Orbit1'
        if not df2.empty: df2['orbit_track'] = 'Orbit2'
        df_combined = pd.concat([df1, df2], ignore_index=True)
        available_cols.append('orbit_track')
        
    df_combined = df_combined[available_cols]

    # Sort by date for plotting
    if 'date1' in df_combined.columns:
        df_combined = df_combined.sort_values(by="date1").reset_index(drop=True)

    # Save Backbone Table
    df_combined.to_csv(output_csv, index=False)
    print(f"Saved Backbone Table to: {output_csv}")

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Add mid-date for plotting
    df_combined['mid_date'] = df_combined['date1'] + (df_combined['date2'] - df_combined['date1']) / 2

    # Plot each orbit
    orbits = df_combined['orbit_track'].unique()
    colors = ['tab:blue', 'tab:orange', 'tab:green']

    for i, orbit in enumerate(orbits):
        orbit_data = df_combined[df_combined['orbit_track'] == orbit]
        
        # Valid points (ok)
        valid_mask = orbit_data['stable_ground_status'] == 'ok'
        valid_data = orbit_data[valid_mask]
        
        ax.errorbar(valid_data['mid_date'], valid_data['glacier_speed_m_per_day_debiased'],
                    yerr=valid_data['glacier_speed_sigma_m_per_day'], fmt='o-', 
                    label=f'{orbit} (Valid)', color=colors[i % len(colors)], capsize=4, alpha=0.9, markersize=6)
        
        # Invalid points (!= ok)
        invalid_mask = orbit_data['stable_ground_status'] != 'ok'
        invalid_data = orbit_data[invalid_mask]
        if not invalid_data.empty:
            ax.errorbar(invalid_data['mid_date'], invalid_data['glacier_speed_m_per_day_debiased'],
                        yerr=invalid_data['glacier_speed_sigma_m_per_day'], fmt='x', 
                        label=f'{orbit} (Excluded)', color=colors[i % len(colors)], capsize=4, alpha=0.5, markersize=8)

    ax.set_xlabel("Date", fontsize=18)
    ax.set_ylabel("Debiased Glacier Speed (m/day)", fontsize=18)
    ax.set_title("Same-track 12-day Backbone + Uncertainty", fontsize=20, fontweight='normal')
    ax.legend(fontsize=16, frameon=True, framealpha=0.95)
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Format x-axis dates with English locale-independent formatting
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_day_mon_en))
    ax.tick_params(axis='both', which='major', labelsize=16)
    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig(output_plot_png, dpi=300)
    print(f"Saved plot to: {output_plot_png}")
    plt.savefig(output_plot_pdf, bbox_inches="tight", format="pdf")
    print(f"Saved vector plot to: {output_plot_pdf}")

if __name__ == "__main__":
    main()
