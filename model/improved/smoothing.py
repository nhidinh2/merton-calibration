"""
Equity Volatility Smoothing

Smooth noisy realized volatility using EWMA smoothing.
"""

import numpy as np
import pandas as pd


def smooth_equity_volatility(equity_vol_df, lambda_ewma=0.94):
    """
    Smooth equity volatility per firm using EWMA smoothing on variance.
    
    Apply EWMA smoothing on variance (lambda=0.94), then take sqrt.
    
    Parameters:
    -----------
    equity_vol_df : pd.DataFrame
        DataFrame with columns: date, firm_id, equity_vol
    lambda_ewma : float
        EWMA smoothing parameter (default: 0.94)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: date, firm_id, equity_vol (raw), equity_vol_smooth
    """
    result_list = []
    
    for firm_id in equity_vol_df['firm_id'].unique():
        firm_vol = equity_vol_df[equity_vol_df['firm_id'] == firm_id].copy()
        firm_vol = firm_vol.sort_values('date').reset_index(drop=True)
        
        # EWMA smoothing on variance, then take sqrt
        # EWMA: var_t = lambda * var_{t-1} + (1 - lambda) * var_t
        vol_smooth = np.zeros(len(firm_vol))
        var_smooth = None
        
        for i, vol in enumerate(firm_vol['equity_vol']):
            var = vol ** 2  # Convert to variance
            
            if var_smooth is None:
                # Initialize with first variance
                var_smooth = var
            else:
                # EWMA update
                var_smooth = lambda_ewma * var_smooth + (1 - lambda_ewma) * var
            
            vol_smooth[i] = np.sqrt(var_smooth)
        
        # Store results
        firm_result = firm_vol.copy()
        firm_result['equity_vol_raw'] = firm_vol['equity_vol'].values
        firm_result['equity_vol_smooth'] = vol_smooth
        # Replace equity_vol with smoothed for the main pipeline
        firm_result['equity_vol'] = vol_smooth
        
        result_list.append(firm_result)
    
    result_df = pd.concat(result_list, ignore_index=True)
    return result_df


def plot_smoothed_volatility(equity_vol_df, output_path=None):
    """
    Plot raw vs smoothed equity volatility for each firm.
    
    Parameters:
    -----------
    equity_vol_df : pd.DataFrame
        DataFrame with columns: date, firm_id, equity_vol_raw, equity_vol_smooth
    output_path : str, optional
        Path to save the plot
    """
    import matplotlib.pyplot as plt
    
    firms = equity_vol_df['firm_id'].unique()
    n_firms = len(firms)
    
    # Create subplots
    fig, axes = plt.subplots(n_firms, 1, figsize=(12, 3 * n_firms))
    if n_firms == 1:
        axes = [axes]
    
    for idx, firm_id in enumerate(firms):
        firm_data = equity_vol_df[equity_vol_df['firm_id'] == firm_id].sort_values('date')
        
        ax = axes[idx]
        ax.plot(firm_data['date'], firm_data['equity_vol_raw'], 
                label='Raw σ_E', alpha=0.6, linewidth=1, color='lightblue')
        ax.plot(firm_data['date'], firm_data['equity_vol_smooth'], 
                label='Smoothed σ_E', linewidth=2, color='darkblue')
        
        ax.set_xlabel('Date')
        ax.set_ylabel('Equity Volatility')
        ax.set_title(f'{firm_id}: Raw vs Smoothed Equity Volatility')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved volatility smoothing plot to {output_path}")
    else:
        plt.show()
    
    plt.close()

