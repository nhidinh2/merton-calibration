"""
Naive Merton Model Diagnostics

Checks:
1) Unstable risk signals: large jumps in log(PD)
2) Implausible implied outputs: V/E blowups, sigma_V collapse, sigma_V/sigma_E anomalies
3) Risk ranking sanity: PD vs leverage correlation + bin summary (latest date)
4) Sensitivity: rerun calibration under small perturbations (E, sigma_E, D, r, T)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from naive_model.calibration import calibrate_asset_parameters
from naive_model.risk_measures import compute_risk_measures


# ----------------------------- Load + merge ----------------------------- #

def load_results_and_inputs():
    """
    Load model results and merge with input data.
    
    Uses the same data loading and alignment logic as naive_model/__main__.py
    to ensure consistency with the results being diagnosed.
    """
    # Load all data
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / 'data' / 'real'
    out_dir = project_root / 'outputs'
    
    results = pd.read_csv(out_dir / 'naive_results.csv', parse_dates=['date'])
    equity_prices = pd.read_csv(data_dir / 'equity_prices.csv', parse_dates=['date'])
    equity_vol = pd.read_csv(data_dir / 'equity_vol.csv', parse_dates=['date'])
    debt = pd.read_csv(data_dir / 'debt_quarterly.csv', parse_dates=['date'])
    risk_free = pd.read_csv(data_dir / 'risk_free.csv', parse_dates=['date'])

    # Align debt to daily (forward-fill quarterly values)
    debt_daily_list = []
    for firm_id in debt['firm_id'].unique():
        firm_debt = debt[debt['firm_id'] == firm_id].set_index('date')
        firm_equity_dates = equity_prices[equity_prices['firm_id'] == firm_id]['date'].unique()
        
        if len(firm_debt) == 0 or len(firm_equity_dates) == 0:
            continue
        
        # Reindex to daily, using backward-fill then forward-fill to handle quarterly debt data
        all_dates = sorted(set(list(firm_equity_dates) + list(firm_debt.index)))
        firm_debt_daily = firm_debt.reindex(all_dates).bfill().ffill().reset_index()
        # Filter to only equity dates
        firm_debt_daily = firm_debt_daily[firm_debt_daily['date'].isin(firm_equity_dates)]
        firm_debt_daily['firm_id'] = firm_id
        firm_debt_daily = firm_debt_daily[['date', 'firm_id', 'debt']]
        debt_daily_list.append(firm_debt_daily)
    
    if debt_daily_list:
        debt_daily = pd.concat(debt_daily_list, ignore_index=True)
    else:
        debt_daily = pd.DataFrame(columns=['date', 'firm_id', 'debt'])

    # Shares outstanding (in billions) as of Dec 31, 2020
    shares_outstanding = {
        'AAPL': 16.93,  # ~16.93 billion shares
        'JPM': 3.09,    # ~3.09 billion shares
        'TSLA': 3.325,  # ~3.325 billion shares (est.)
        'XOM': 4.25,    # ~4.2-4.3 billion shares
        'F': 3.97       # ~3.97 billion shares
    }

    # Merge inputs with results
    results = results.merge(
        equity_prices.rename(columns={'equity_price': 'E_per_share'})[['date', 'firm_id', 'E_per_share']],
        on=['date', 'firm_id'], how='left'
    )
    results = results.merge(
        equity_vol.rename(columns={'equity_vol': 'sigma_E'})[['date', 'firm_id', 'sigma_E']],
        on=['date', 'firm_id'], how='left'
    )
    results = results.merge(
        debt_daily.rename(columns={'debt': 'D'})[['date', 'firm_id', 'D']],
        on=['date', 'firm_id'], how='left'
    )
    results = results.merge(
        risk_free.rename(columns={'risk_free_rate': 'r'})[['date', 'r']],
        on=['date'], how='left'
    )

    # Convert equity from per-share to total market cap (in millions)
    results['shares_billions'] = results['firm_id'].map(shares_outstanding)
    results['E'] = results['E_per_share'] * results['shares_billions'] * 1000.0
    results = results.drop(columns=['E_per_share', 'shares_billions'])

    # Validate required columns
    required = ['date', 'firm_id', 'E', 'sigma_E', 'D', 'r', 'V', 'sigma_V', 'PD', 'DD']
    missing = [c for c in required if c not in results.columns]
    if missing:
        raise ValueError(f'Missing required columns: {missing}')

    return results


# ----------------------------- Diagnosis 1 ----------------------------- #

def diagnose_unstable_signals(results):
    """Calculate max |Δlog(PD)| per firm."""
    eps = 1e-18
    df = results.sort_values(["firm_id", "date"]).copy()
    df["PD_clip"] = df["PD"].clip(eps, 1 - eps)
    df["logPD"] = np.log(df["PD_clip"])

    # Compute changes per firm
    df["dlogPD"] = df.groupby("firm_id")["logPD"].diff()
    df["abs_dlogPD"] = df["dlogPD"].abs()

    # Calculate max |Δlog(PD)| per firm
    max_abs_dlogPD_per_firm = df.groupby("firm_id")["abs_dlogPD"].max().reset_index()
    max_abs_dlogPD_per_firm.columns = ["firm_id", "max_abs_dlogPD"]

    return {
        "max_abs_dlogPD_per_firm": max_abs_dlogPD_per_firm.to_dict("records"),
    }


# ----------------------------- Diagnosis 2 ----------------------------- #

def diagnose_implausible_outputs(results):
    """Check for economically implausible V"""
    df = results.copy()
    n_V_invalid = ((df["V"] <= 0) | (~np.isfinite(df["V"]))).sum()

    return {
        "n_V_invalid": int(n_V_invalid)
    }


# ----------------------------- Diagnosis 3 ----------------------------- #

def diagnose_risk_ranking(results):
    """
    Minimal risk-ranking diagnosis.
    
    Distress proxy: leverage (D / (E + D))
    
    Two numbers:
    1. Daily Spearman rank correlation ρ_t = Spearman(PD_t, leverage_t)
       - Report: Median ρ_t and % of days with wrong sign
    2. Top-1 distress in top-2 PD: Is the most distressed firm in the top-2 PD firms?
       - Report: % of days where this fails
    """
    df = results.copy()
    df["leverage"] = df["D"] / (df["E"] + df["D"]).replace(0, np.nan)

    # Process each day
    daily_results = []
    dates = sorted(df["date"].unique())
    
    for date in dates:
        x = df[df["date"] == date].dropna(subset=["PD", "leverage"]).copy()
        if len(x) < 2:
            continue
        
        # Spearman rank correlation
        spear = float(spearmanr(x["PD"], x["leverage"], nan_policy="omit").correlation)
        
        # Top-1 distress in top-2 PD: Is the most distressed (highest leverage) firm in the top-2 PD firms?
        most_distressed_firm = x.loc[x["leverage"].idxmax(), "firm_id"]
        top2_PD_firms = set(x.nlargest(2, "PD")["firm_id"].values)
        top1_in_top2_PD = most_distressed_firm in top2_PD_firms
        
        daily_results.append({
            "date": str(date),
            "n_firms": int(len(x)),
            "spearman_rho": spear,
            "top1_in_top2_PD": bool(top1_in_top2_PD),
            "most_distressed_firm": most_distressed_firm,
            "top2_PD_firms": list(top2_PD_firms),
        })
    
    if not daily_results:
        return {"note": "No dates with enough firms", "n_dates": 0}
    
    # Aggregate across all days
    daily_df = pd.DataFrame(daily_results)
    
    # Wrong sign: if PD ranks risk correctly, ρ_t should be positive (higher leverage → higher PD)
    wrong_sign_pct = (daily_df["spearman_rho"] <= 0).mean() * 100
    
    # Top-1 distress in top-2 PD failure rate
    top1_not_in_top2_PD_pct = (~daily_df["top1_in_top2_PD"]).mean() * 100
    
    return {
        "n_dates": int(len(daily_df)),
        "distress_proxy": "leverage",
        "spearman_rho_median": float(daily_df["spearman_rho"].median()),
        "wrong_sign_pct": float(wrong_sign_pct),
        "top1_not_in_top2_PD_pct": float(top1_not_in_top2_PD_pct),
        "daily_results": daily_df.to_dict("records"),
    }


# ----------------------------- Diagnosis 4 ----------------------------- #

def diagnose_sensitivity(results, seed=42):
    """Test sensitivity by rerunning calibration with small input perturbations."""
    df = results.dropna(subset=["E", "sigma_E", "D", "r"]).copy()
    if len(df) == 0:
        return {"note": "No rows with complete inputs"}

    samp = df.sample(n=len(df), random_state=seed)

    T0 = 1.0
    pert = {
        "E": ("mult", 0.01),      # +1%
        "sigma_E": ("mult", 0.01),  # +1%
        "D": ("mult", 0.01),      # +1%
        "r": ("add", 1e-4),       # +1bp
        "T": ("add", 0.01),       # +0.01 year
    }

    elasticities = {k: [] for k in pert.keys()}

    for _, row in samp.iterrows():
        E0, sE0, D0, r0 = float(row["E"]), float(row["sigma_E"]), float(row["D"]), float(row["r"])
        
        if pd.isna(row.get("PD")) or pd.isna(row.get("V")) or pd.isna(row.get("sigma_V")):
            continue
        logPDb = np.log(float(row["PD"]))
        
        # Use baseline solution as initial guess (warm start)
        V0 = float(row["V"])
        sigma_V0 = float(row["sigma_V"])

        for name, (_, size) in pert.items():
            E1, sE1, D1, r1, T1 = E0, sE0, D0, r0, T0
            if name == "E":
                E1 = E0 * (1 + size)
            elif name == "sigma_E":
                sE1 = sE0 * (1 + size)
            elif name == "D":
                D1 = D0 * (1 + size)
            elif name == "r":
                r1 = r0 + size
            elif name == "T":
                T1 = T0 + size
            else:
                continue

            try:
                # Use baseline solution as initial guess for perturbed calibration
                V1, sV1 = calibrate_asset_parameters(E1, sE1, D1, T1, r1, V0=V0, sigma_V0=sigma_V0)
                out = compute_risk_measures(V1, D1, T1, r1, sV1)
                logPD1 = np.log(float(out["PD"]))
                sens = (logPD1 - logPDb) / size
                elasticities[name].append(float(sens))
            except:
                continue

    stats = {}
    for k, vals in elasticities.items():
        if vals:
            arr = np.array(vals, dtype=float)
            stats[k] = {
                "median_abs": float(np.median(np.abs(arr))),
                "p95_abs": float(np.quantile(np.abs(arr), 0.95)),
            }

    return {
        "stats": stats
    }


# ----------------------------- Plotting ----------------------------- #

def plot_diagnostics(results, diagnostics, output_dir=None):
    """Generate diagnostic plots for the report."""
    if output_dir is None:
        project_root = Path(__file__).parent.parent.parent
        output_dir = project_root / 'outputs'
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Prepare data
    results = results.copy()
    results['V_E'] = results['V'] / results['E']
    results['leverage'] = results['D'] / (results['E'] + results['D'])
    results['log_PD'] = np.log(results['PD'].clip(lower=1e-18, upper=1-1e-18))
    
    # 1. Diagnosis 1: Time series of PD for selected firms (showing instability)
    # Sort firms to ensure consistent ordering and include all firms
    unique_firms = sorted(results['firm_id'].unique())
    n_firms = len(unique_firms)
    n_cols = 2
    n_rows = (n_firms + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 5*n_rows))
    if n_firms == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    firms_to_plot = unique_firms  # Plot all firms
    
    for idx, firm_id in enumerate(firms_to_plot):
        firm_data = results[results['firm_id'] == firm_id].sort_values('date')
        
        ax = axes[idx]
        
        ax.plot(firm_data['date'], firm_data['log_PD'], 'b-', alpha=0.7, label='log(PD)', linewidth=1.5)
        ax.set_ylabel('log(PD)')
        ax.set_title(f'{firm_id}: log(PD) Over Time')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
    
    # Hide unused subplots
    for idx in range(len(firms_to_plot), len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'diagnosis_timeseries.png', dpi=150, bbox_inches='tight')
    print(f"Saved PD time series plot to {output_dir / 'diagnosis_timeseries.png'}")
    plt.close()
    
    # 2. Diagnosis 2: V/E ratio per firm
    n_firms = len(unique_firms)
    
    # Create subplots (arrange in grid)
    n_cols = min(3, n_firms)
    n_rows = (n_firms + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5*n_rows))
    if n_firms == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    for idx, firm_id in enumerate(unique_firms):
        ax = axes[idx]
        firm_data = results[results['firm_id'] == firm_id].copy()
        v_e_firm = firm_data['V_E'][(firm_data['V_E'] > 0) & np.isfinite(firm_data['V_E'])]
        
        if len(v_e_firm) > 0:
            # Plot histogram
            ax.hist(v_e_firm, bins=30, edgecolor='black', alpha=0.7)
            ax.set_xlabel('V/E Ratio')
            ax.set_ylabel('Frequency')
            ax.set_title(f'{firm_id}')
            ax.set_xscale('log')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, f'No valid data\nfor {firm_id}', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{firm_id}')
    
    # Hide extra subplots
    for idx in range(n_firms, len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'diagnosis_v_e_ratio.png', dpi=150, bbox_inches='tight')
    print(f"Saved V/E ratio plot to {output_dir / 'diagnosis_v_e_ratio.png'}")
    plt.close()
    
    # 3. Rank trajectory plot: PD rank vs distress (leverage) rank over time
    if 'ranking' in diagnostics and 'daily_results' in diagnostics['ranking']:
        daily_results = diagnostics['ranking']['daily_results']
        
        # Collect firm rank trajectories
        firm_rank_trajectories = {}
        dates_list = []
        
        for daily_result in daily_results:
            date = pd.to_datetime(daily_result['date'])
            dates_list.append(date)
            
            # Get data for this date
            date_data = results[results['date'] == date].dropna(subset=['PD', 'leverage']).copy()
            if len(date_data) < 2:
                continue
            
            # Rank firms: 1 = highest PD, 1 = highest leverage (most distressed)
            date_data_pd = date_data.sort_values('PD', ascending=False).reset_index(drop=True)
            date_data_pd['rank_PD'] = range(1, len(date_data_pd) + 1)
            rank_pd_map = dict(zip(date_data_pd['firm_id'], date_data_pd['rank_PD']))
            
            date_data_lev = date_data.sort_values('leverage', ascending=False).reset_index(drop=True)
            date_data_lev['rank_leverage'] = range(1, len(date_data_lev) + 1)
            rank_lev_map = dict(zip(date_data_lev['firm_id'], date_data_lev['rank_leverage']))
            
            # Store ranks for each firm
            for firm_id in date_data['firm_id']:
                if firm_id not in firm_rank_trajectories:
                    firm_rank_trajectories[firm_id] = {'dates': [], 'rank_PD': [], 'rank_leverage': []}
                firm_rank_trajectories[firm_id]['dates'].append(date)
                firm_rank_trajectories[firm_id]['rank_PD'].append(rank_pd_map.get(firm_id))
                firm_rank_trajectories[firm_id]['rank_leverage'].append(rank_lev_map.get(firm_id))
        
        if firm_rank_trajectories:
            n_firms = len(firm_rank_trajectories)
            
            fig, axes = plt.subplots(n_firms, 1, figsize=(12, 3*n_firms))
            if n_firms == 1:
                axes = [axes]
            
            for idx, (firm_id, trajectories) in enumerate(sorted(firm_rank_trajectories.items())):
                ax = axes[idx]
                dates_firm = trajectories['dates']
                rank_PD = trajectories['rank_PD']
                rank_leverage = trajectories['rank_leverage']
                
                # Sort by date
                sorted_idx = sorted(range(len(dates_firm)), key=lambda i: dates_firm[i])
                dates_firm_sorted = [dates_firm[i] for i in sorted_idx]
                rank_PD_sorted = [rank_PD[i] for i in sorted_idx]
                rank_leverage_sorted = [rank_leverage[i] for i in sorted_idx]
                
                # Calculate average PD rank (sum of ranks / number of days)
                avg_PD_rank = sum(rank_PD) / len(rank_PD) if len(rank_PD) > 0 else 0
                
                ax.plot(dates_firm_sorted, rank_PD_sorted, 'b-', alpha=0.7, linewidth=1.5, 
                       label='PD Rank', marker='o', markersize=3)
                ax.plot(dates_firm_sorted, rank_leverage_sorted, 'r--', alpha=0.7, linewidth=1.5, 
                       label='Leverage Rank (Distress)', marker='s', markersize=3)
                
                # Add horizontal line for average PD rank
                if len(dates_firm_sorted) > 0:
                    ax.axhline(y=avg_PD_rank, color='green', linestyle=':', linewidth=2, 
                             alpha=0.8, label=f'Avg PD Rank ({avg_PD_rank:.2f})')
                
                ax.set_ylabel('Rank')
                ax.set_title(f'{firm_id}: PD Rank vs Leverage Rank Over Time')
                ax.set_ylim(0.5, n_firms + 0.5)
                ax.invert_yaxis()  # Rank 1 at top
                ax.legend(loc='best')
                ax.grid(True, alpha=0.3)
            
            axes[-1].set_xlabel('Date')
            plt.tight_layout()
            plt.savefig(output_dir / 'diagnosis_ranking.png', dpi=150, bbox_inches='tight')
            print(f"Saved ranking plot to {output_dir / 'diagnosis_ranking.png'}")
            plt.close()
    
    # 4. Sensitivity elasticity distribution 
    if 'sensitivity' in diagnostics and 'stats' in diagnostics['sensitivity']:
        sens_stats = diagnostics['sensitivity']['stats']
        if sens_stats:
            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            
            params = []
            median_abs_values = []
            for param, stats in sens_stats.items():
                params.append(param)
                median_abs_values.append(stats['median_abs'])
            
            colors = ['red' if m > 1 else 'blue' for m in median_abs_values]
            ax.barh(params, median_abs_values, color=colors, alpha=0.7, edgecolor='black')
            ax.set_xlabel('Median |Elasticity| of log(PD)')
            ax.set_title('Sensitivity to Input Parameters\n(median |sens|: typical sensitivity)')
            ax.grid(True, alpha=0.3, axis='x')
            
            # Add value labels
            for i, (param, median_abs) in enumerate(zip(params, median_abs_values)):
                ax.text(median_abs, i, f' {median_abs:.3f}', va='center', fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(output_dir / 'diagnosis_sensitivity.png', dpi=150, bbox_inches='tight')
            print(f"Saved sensitivity plot to {output_dir / 'diagnosis_sensitivity.png'}")
            plt.close()


# ----------------------------- Runner ----------------------------- #

def main():
    """Run all diagnostic checks."""
    print("=" * 72)
    print("NAIVE MERTON MODEL DIAGNOSTICS")
    print("=" * 72)

    results = load_results_and_inputs()
    print(f"Loaded {len(results):,} rows")

    d1 = diagnose_unstable_signals(results)
    d2 = diagnose_implausible_outputs(results)
    d3 = diagnose_risk_ranking(results)
    d4 = diagnose_sensitivity(results)
    
    diagnostics = {"unstable": d1, "implausible": d2, "ranking": d3, "sensitivity": d4}
    
    # Generate plots
    print("\n--- Generating Plots ---")
    plot_diagnostics(results, diagnostics)

    print("\n--- Summary ---")

    if "max_abs_dlogPD_per_firm" in d1:
        print("Unstable signals: max |Δlog(PD)| per firm:")
        for firm_data in d1["max_abs_dlogPD_per_firm"]:
            print(f"  {firm_data['firm_id']}: max |Δlog(PD)| = {firm_data['max_abs_dlogPD']:.4f}")
    else:
        print(f"Unstable signals: {d1.get('note', 'N/A')}")

    print(f"\nImplausible outputs: invalid V={d2['n_V_invalid']}")

    if "spearman_rho_median" in d3:
        print(f"\nRanking (distress proxy: {d3.get('distress_proxy', 'leverage')}, across {d3['n_dates']} days):")
        print(f"  Median Spearman ρ_t = {d3['spearman_rho_median']:.3f}")
        print(f"  % of days with wrong sign = {d3['wrong_sign_pct']:.1f}%")
        print(f"  Top-1 distress not in top-2 PD = {d3['top1_not_in_top2_PD_pct']:.1f}%")
    else:
        print(f"\nRanking: {d3.get('note', 'N/A')} (n_dates={d3.get('n_dates', 'N/A')})")

    if "stats" in d4:
        print(f"\nSensitivity Issues:")
        print("  Elasticity statistics (median |sens|, p95 |sens|):")
        for param, stat in d4["stats"].items():
            print(f"    {param}: median |sens|={stat['median_abs']:.3f}, p95 |sens|={stat['p95_abs']:.3f}")
    else:
        print(f"\nSensitivity: {d4.get('note', 'N/A')}")

    return diagnostics


if __name__ == "__main__":
    main()
