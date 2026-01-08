"""
Comprehensive Model Comparison: Naive, Improved, and Bounded

Compares all three Merton model implementations:
1) PD Stability: max |Δlog(PD)| per firm
2) Asset Value Plausibility: V/E ratio statistics
3) Risk Ranking Consistency: Spearman correlation, wrong sign %, top-1 in top-2 PD
4) Sensitivity: median and p95 elasticities for all parameters
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from model.evaluation.compare_model import (
    diagnose_unstable_signals,
    diagnose_implausible_outputs,
    diagnose_risk_ranking,
    diagnose_sensitivity
)


def load_bounded_results_and_inputs():
    """Load bounded model results and merge with input data."""
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / 'data' / 'real'
    out_dir = project_root / 'outputs'
    
    try:
        results = pd.read_csv(out_dir / 'bounded_results.csv', parse_dates=['date'])
    except FileNotFoundError:
        return None
    
    equity_prices = pd.read_csv(data_dir / 'equity_prices.csv', parse_dates=['date'])
    equity_vol = pd.read_csv(data_dir / 'equity_vol.csv', parse_dates=['date'])
    debt = pd.read_csv(data_dir / 'debt_quarterly.csv', parse_dates=['date'])
    risk_free = pd.read_csv(data_dir / 'risk_free.csv', parse_dates=['date'])

    # Align debt to daily
    debt_daily_list = []
    for firm_id in debt['firm_id'].unique():
        firm_debt = debt[debt['firm_id'] == firm_id].set_index('date')
        firm_equity_dates = equity_prices[equity_prices['firm_id'] == firm_id]['date'].unique()
        
        if len(firm_debt) == 0 or len(firm_equity_dates) == 0:
            continue
        
        all_dates = sorted(set(list(firm_equity_dates) + list(firm_debt.index)))
        firm_debt_daily = firm_debt.reindex(all_dates).bfill().ffill().reset_index()
        firm_debt_daily = firm_debt_daily[firm_debt_daily['date'].isin(firm_equity_dates)]
        firm_debt_daily['firm_id'] = firm_id
        firm_debt_daily = firm_debt_daily[['date', 'firm_id', 'debt']]
        debt_daily_list.append(firm_debt_daily)
    
    if debt_daily_list:
        debt_daily = pd.concat(debt_daily_list, ignore_index=True)
    else:
        debt_daily = pd.DataFrame(columns=['date', 'firm_id', 'debt'])

    shares_outstanding = {
        'AAPL': 16.93,
        'JPM': 3.09,
        'TSLA': 3.325,
        'XOM': 4.25,
        'F': 3.97
    }

    # Bounded model uses smoothed volatility (same as improved)
    from improved.smoothing import smooth_equity_volatility
    equity_vol_smooth = smooth_equity_volatility(equity_vol.copy())

    # Merge inputs
    results = results.merge(
        equity_prices.rename(columns={'equity_price': 'E_per_share'})[['date', 'firm_id', 'E_per_share']],
        on=['date', 'firm_id'], how='left'
    )
    results = results.merge(
        equity_vol_smooth.rename(columns={'equity_vol': 'sigma_E'})[['date', 'firm_id', 'sigma_E']],
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

    results['shares_billions'] = results['firm_id'].map(shares_outstanding)
    results['E'] = results['E_per_share'] * results['shares_billions'] * 1000.0
    results = results.drop(columns=['E_per_share', 'shares_billions'])

    required = ['date', 'firm_id', 'E', 'sigma_E', 'D', 'r', 'V', 'sigma_V', 'PD', 'DD']
    missing = [c for c in required if c not in results.columns]
    if missing:
        return None

    return results


def calculate_all_metrics(naive_results, improved_results, bounded_results):
    """Calculate all diagnostic metrics for all three models."""
    metrics = {}
    
    if naive_results is not None:
        metrics['naive'] = {
            'pd_stability': diagnose_unstable_signals(naive_results),
            'asset_plausibility': diagnose_implausible_outputs(naive_results),
            'risk_ranking': diagnose_risk_ranking(naive_results),
            'sensitivity': diagnose_sensitivity(naive_results, use_naive=True)
        }
    
    if improved_results is not None:
        metrics['improved'] = {
            'pd_stability': diagnose_unstable_signals(improved_results),
            'asset_plausibility': diagnose_implausible_outputs(improved_results),
            'risk_ranking': diagnose_risk_ranking(improved_results),
            'sensitivity': diagnose_sensitivity(improved_results, use_naive=False)
        }
    
    if bounded_results is not None:
        metrics['bounded'] = {
            'pd_stability': diagnose_unstable_signals(bounded_results),
            'asset_plausibility': diagnose_implausible_outputs(bounded_results),
            'risk_ranking': diagnose_risk_ranking(bounded_results),
            'sensitivity': diagnose_sensitivity(bounded_results, use_naive=False)
        }
    
    return metrics


def print_comparison_summary(metrics):
    """Print comprehensive comparison summary."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE MODEL COMPARISON: NAIVE vs IMPROVED vs BOUNDED")
    print("=" * 80)
    
    # 1. PD Stability
    print("\n1. PD STABILITY: Max |Δlog(PD)| per firm")
    print("-" * 80)
    print(f"{'Firm':<8} {'Naive':<15} {'Improved':<15} {'Bounded':<15}")
    print("-" * 80)
    
    # Get all firms from all models
    all_firms = set()
    for model_name in metrics.keys():
        if 'pd_stability' in metrics[model_name]:
            for firm_data in metrics[model_name]['pd_stability'].get('max_abs_dlogPD_per_firm', []):
                all_firms.add(firm_data['firm_id'])
    
    for firm in sorted(all_firms):
        naive_val = None
        improved_val = None
        bounded_val = None
        
        if 'naive' in metrics and 'pd_stability' in metrics['naive']:
            for firm_data in metrics['naive']['pd_stability'].get('max_abs_dlogPD_per_firm', []):
                if firm_data['firm_id'] == firm:
                    naive_val = firm_data['max_abs_dlogPD']
                    break
        
        if 'improved' in metrics and 'pd_stability' in metrics['improved']:
            for firm_data in metrics['improved']['pd_stability'].get('max_abs_dlogPD_per_firm', []):
                if firm_data['firm_id'] == firm:
                    improved_val = firm_data['max_abs_dlogPD']
                    break
        
        if 'bounded' in metrics and 'pd_stability' in metrics['bounded']:
            for firm_data in metrics['bounded']['pd_stability'].get('max_abs_dlogPD_per_firm', []):
                if firm_data['firm_id'] == firm:
                    bounded_val = firm_data['max_abs_dlogPD']
                    break
        
        naive_str = f"{naive_val:.4f}" if naive_val is not None else "N/A"
        improved_str = f"{improved_val:.4f}" if improved_val is not None else "N/A"
        bounded_str = f"{bounded_val:.4f}" if bounded_val is not None else "N/A"
        print(f"{firm:<8} {naive_str:<15} {improved_str:<15} {bounded_str:<15}")
    
    # 2. Asset Plausibility
    print("\n2. ASSET VALUE PLAUSIBILITY: V/E Ratio Statistics")
    print("-" * 80)
    print(f"{'Metric':<20} {'Naive':<15} {'Improved':<15} {'Bounded':<15}")
    print("-" * 80)
    
    for metric_name in ['mean_V_E', 'median_V_E', 'max_V_E', 'n_V_invalid']:
        naive_val = None
        improved_val = None
        bounded_val = None
        
        if 'naive' in metrics and 'asset_plausibility' in metrics['naive']:
            naive_val = metrics['naive']['asset_plausibility'].get(metric_name)
        
        if 'improved' in metrics and 'asset_plausibility' in metrics['improved']:
            improved_val = metrics['improved']['asset_plausibility'].get(metric_name)
        
        if 'bounded' in metrics and 'asset_plausibility' in metrics['bounded']:
            bounded_val = metrics['bounded']['asset_plausibility'].get(metric_name)
        
        naive_str = f"{naive_val:.4f}" if naive_val is not None and metric_name != 'n_V_invalid' else (f"{naive_val}" if naive_val is not None else "N/A")
        improved_str = f"{improved_val:.4f}" if improved_val is not None and metric_name != 'n_V_invalid' else (f"{improved_val}" if improved_val is not None else "N/A")
        bounded_str = f"{bounded_val:.4f}" if bounded_val is not None and metric_name != 'n_V_invalid' else (f"{bounded_val}" if bounded_val is not None else "N/A")
        print(f"{metric_name:<20} {naive_str:<15} {improved_str:<15} {bounded_str:<15}")
    
    # 3. Risk Ranking
    print("\n3. RISK RANKING CONSISTENCY")
    print("-" * 80)
    print(f"{'Metric':<30} {'Naive':<15} {'Improved':<15} {'Bounded':<15}")
    print("-" * 80)
    
    for metric_name in ['spearman_rho_median', 'wrong_sign_pct', 'top1_not_in_top2_PD_pct']:
        naive_val = None
        improved_val = None
        bounded_val = None
        
        if 'naive' in metrics and 'risk_ranking' in metrics['naive']:
            naive_val = metrics['naive']['risk_ranking'].get(metric_name)
        
        if 'improved' in metrics and 'risk_ranking' in metrics['improved']:
            improved_val = metrics['improved']['risk_ranking'].get(metric_name)
        
        if 'bounded' in metrics and 'risk_ranking' in metrics['bounded']:
            bounded_val = metrics['bounded']['risk_ranking'].get(metric_name)
        
        naive_str = f"{naive_val:.3f}" if naive_val is not None else "N/A"
        improved_str = f"{improved_val:.3f}" if improved_val is not None else "N/A"
        bounded_str = f"{bounded_val:.3f}" if bounded_val is not None else "N/A"
        print(f"{metric_name:<30} {naive_str:<15} {improved_str:<15} {bounded_str:<15}")
    
    # 4. Sensitivity
    print("\n4. SENSITIVITY: Median and p95 Elasticities")
    print("-" * 80)
    
    # Get all parameters
    all_params = set()
    for model_name in metrics.keys():
        if 'sensitivity' in metrics[model_name] and 'stats' in metrics[model_name]['sensitivity']:
            all_params.update(metrics[model_name]['sensitivity']['stats'].keys())
    
    print(f"\n{'Parameter':<12} {'Metric':<10} {'Naive':<15} {'Improved':<15} {'Bounded':<15}")
    print("-" * 80)
    
    for param in sorted(all_params):
        for metric in ['median_abs', 'p95_abs']:
            naive_val = None
            improved_val = None
            bounded_val = None
            
            if 'naive' in metrics and 'sensitivity' in metrics['naive']:
                if 'stats' in metrics['naive']['sensitivity'] and param in metrics['naive']['sensitivity']['stats']:
                    naive_val = metrics['naive']['sensitivity']['stats'][param].get(metric)
            
            if 'improved' in metrics and 'sensitivity' in metrics['improved']:
                if 'stats' in metrics['improved']['sensitivity'] and param in metrics['improved']['sensitivity']['stats']:
                    improved_val = metrics['improved']['sensitivity']['stats'][param].get(metric)
            
            if 'bounded' in metrics and 'sensitivity' in metrics['bounded']:
                if 'stats' in metrics['bounded']['sensitivity'] and param in metrics['bounded']['sensitivity']['stats']:
                    bounded_val = metrics['bounded']['sensitivity']['stats'][param].get(metric)
            
            naive_str = f"{naive_val:.3f}" if naive_val is not None else "N/A"
            improved_str = f"{improved_val:.3f}" if improved_val is not None else "N/A"
            bounded_str = f"{bounded_val:.3f}" if bounded_val is not None else "N/A"
            print(f"{param:<12} {metric:<10} {naive_str:<15} {improved_str:<15} {bounded_str:<15}")
    
    print("\n" + "=" * 80)


def main():
    """Run comprehensive comparison."""
    from model.evaluation.compare_model import load_naive_results_and_inputs, load_results_and_inputs
    
    print("Loading model results...")
    
    naive_results = load_naive_results_and_inputs()
    if naive_results is not None:
        print(f"  Naive: {len(naive_results):,} rows")
    else:
        print("  Naive: Not found")
    
    improved_results = load_results_and_inputs()
    if improved_results is not None:
        print(f"  Improved: {len(improved_results):,} rows")
    else:
        print("  Improved: Not found")
    
    bounded_results = load_bounded_results_and_inputs()
    if bounded_results is not None:
        print(f"  Bounded: {len(bounded_results):,} rows")
    else:
        print("  Bounded: Not found")
    
    if improved_results is None and bounded_results is None:
        print("Error: Need at least improved or bounded results")
        return
    
    print("\nCalculating diagnostics...")
    metrics = calculate_all_metrics(naive_results, improved_results, bounded_results)
    
    print_comparison_summary(metrics)
    
    return metrics


if __name__ == "__main__":
    main()

