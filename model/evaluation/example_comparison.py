"""
Example comparison script between naive and improved models.

This is a template - modify as needed for your evaluation.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Get project root directory
project_root = Path(__file__).parent.parent.parent
outputs_dir = project_root / 'outputs'
outputs_dir.mkdir(exist_ok=True)


def load_results():
    """Load results from both models."""
    naive = pd.read_csv(outputs_dir / 'naive_results.csv', parse_dates=['date'])
    improved = pd.read_csv(outputs_dir / 'improved_results.csv', parse_dates=['date'])
    return naive, improved


def compare_time_series_stability(naive, improved):
    """
    Compare time-series stability of risk measures.
    
    Lower standard deviation = more stable = better (usually)
    """
    print("\n" + "="*60)
    print("Time-Series Stability Comparison")
    print("="*60)
    
    # Group by firm and compute standard deviation of PD
    naive_stability = naive.groupby('firm_id')['PD'].std()
    improved_stability = improved.groupby('firm_id')['PD'].std()
    
    print("\nPD Standard Deviation (lower is more stable):")
    print(f"\nNaive Model:")
    print(naive_stability)
    print(f"\nImproved Model:")
    print(improved_stability)
    
    print(f"\nAverage PD Std Dev:")
    print(f"  Naive:    {naive_stability.mean():.4f}")
    print(f"  Improved: {improved_stability.mean():.4f}")
    print(f"  Change:   {improved_stability.mean() - naive_stability.mean():.4f}")
    
    return naive_stability, improved_stability


def compare_cross_sectional_ranking(naive, improved):
    """
    Compare cross-sectional risk ranking.
    
    Do firms with higher leverage have higher PD? (They should!)
    """
    print("\n" + "="*60)
    print("Cross-Sectional Risk Ranking")
    print("="*60)
    
    # Get average PD per firm
    naive_avg_pd = naive.groupby('firm_id')['PD'].mean().sort_values(ascending=False)
    improved_avg_pd = improved.groupby('firm_id')['PD'].mean().sort_values(ascending=False)
    
    print("\nAverage PD by Firm (sorted, highest to lowest):")
    print(f"\nNaive Model:")
    print(naive_avg_pd)
    print(f"\nImproved Model:")
    print(improved_avg_pd)
    
    # TODO: Compare with actual leverage if you have that data
    # Higher leverage firms should generally have higher PD


def plot_comparison(naive, improved, firm_id='FIRM_C'):
    """
    Plot time series comparison for a specific firm.
    """
    naive_firm = naive[naive['firm_id'] == firm_id].sort_values('date')
    improved_firm = improved[improved['firm_id'] == firm_id].sort_values('date')
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # PD comparison
    axes[0, 0].plot(naive_firm['date'], naive_firm['PD'], label='Naive', alpha=0.7)
    axes[0, 0].plot(improved_firm['date'], improved_firm['PD'], label='Improved', alpha=0.7)
    axes[0, 0].set_title(f'Default Probability: {firm_id}')
    axes[0, 0].set_ylabel('PD')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # DD comparison
    axes[0, 1].plot(naive_firm['date'], naive_firm['DD'], label='Naive', alpha=0.7)
    axes[0, 1].plot(improved_firm['date'], improved_firm['DD'], label='Improved', alpha=0.7)
    axes[0, 1].set_title(f'Distance-to-Default: {firm_id}')
    axes[0, 1].set_ylabel('DD')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Asset volatility comparison
    axes[1, 0].plot(naive_firm['date'], naive_firm['sigma_V'], label='Naive', alpha=0.7)
    axes[1, 0].plot(improved_firm['date'], improved_firm['sigma_V'], label='Improved', alpha=0.7)
    axes[1, 0].set_title(f'Asset Volatility: {firm_id}')
    axes[1, 0].set_ylabel('σ_V')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Asset value comparison
    axes[1, 1].plot(naive_firm['date'], naive_firm['V'], label='Naive', alpha=0.7)
    axes[1, 1].plot(improved_firm['date'], improved_firm['V'], label='Improved', alpha=0.7)
    axes[1, 1].set_title(f'Asset Value: {firm_id}')
    axes[1, 1].set_ylabel('V')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = outputs_dir / f'comparison_{firm_id}.png'
    plt.savefig(output_path, dpi=150)
    print(f"\nSaved plot to {output_path}")


def main():
    """Main comparison function."""
    print("Model Comparison")
    print("="*60)
    
    # Load results
    try:
        naive, improved = load_results()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure you've run both models and saved results to outputs/")
        return
    
    # Compare metrics
    compare_time_series_stability(naive, improved)
    compare_cross_sectional_ranking(naive, improved)
    
    # Plot comparison for one firm
    if len(naive['firm_id'].unique()) > 0:
        plot_comparison(naive, improved, firm_id=naive['firm_id'].unique()[0])
    
    print("\n" + "="*60)
    print("Comparison complete!")
    print("="*60)


if __name__ == "__main__":
    main()

