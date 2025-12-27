import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path

# Get project root directory
project_root = Path(__file__).parent.parent.parent
outputs_dir = project_root / 'outputs'

# Load data
results = pd.read_csv(outputs_dir / 'naive_results.csv', parse_dates=['date'])

# Create plot
fig, ax = plt.subplots(figsize=(12, 6))

# Plot sigma_V for each firm
for firm_id in sorted(results['firm_id'].unique()):
    firm_data = results[results['firm_id'] == firm_id].sort_values('date')
    ax.plot(firm_data['date'], firm_data['sigma_V'], label=firm_id, marker='o', markersize=2, linewidth=1.5)

ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Asset Volatility (σ_V)', fontsize=12)
ax.set_title('Asset Volatility (σ_V) Over Time - Naive Model', fontsize=14, fontweight='bold')
ax.legend(loc='best', frameon=True)
ax.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()

# Save plot
output_path = outputs_dir / 'naive_sigma_V.png'
output_path.parent.mkdir(exist_ok=True)
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f'Plot saved to {output_path}')
plt.close()
