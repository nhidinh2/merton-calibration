# Progress Report: Toward Bounded and Regularized Merton Model Calibration

## Executive Summary

This report documents progress toward extending the Merton (1974) structural credit model with bounded and regularized calibration to address ill-posed inverse estimation of asset value and volatility. The current implementation establishes the foundation, diagnostic framework, and empirical evaluation necessary for the final constrained optimization approach.

### Current Status: Bounded Calibration Implemented and Evaluated

**Progress Completed:**
- Implemented baseline Merton model with unconstrained root-finding (`fsolve`)
- Identified systematic weaknesses: excessive sensitivity, PD instability, calibration degeneracy
- Established comprehensive diagnostic framework for model evaluation
- Conducted perturbation analysis to quantify PD sensitivity across parameters
- Developed improved model with input-level smoothing (EWMA) as intermediate step
- **Implemented bounded and regularized calibration with constrained nonlinear least squares**
- **Conducted comprehensive comparison of all three models (baseline, improved, bounded)**
- Validated evaluation methodology on real firm data (AAPL, JPM, TSLA, XOM, F)

**Key Findings:**
- Baseline model exhibits extreme sensitivity to equity volatility (median elasticity = 9.211, p95 = 90.445)
- PD instability driven by noise amplification: max daily changes in log(PD) range from 4.60 to 31.55
- EWMA smoothing reduces PD instability by 80-95% while maintaining risk sensitivity
- **Bounded calibration successfully enforces parameter bounds but introduces risk ranking issues**
- **Improved model (EWMA) provides best overall performance: best risk ranking (1.2% wrong sign vs 44% for bounded) and balanced sensitivity**

**Next Milestones:**
- Extend stress-testing framework to market regime analysis
- Benchmark structural default probabilities against reduced-form models
- Explore hybrid approaches combining EWMA smoothing with selective bounded constraints

---

## Part I: Current Implementation Status

### 1. What Has Been Built

This section describes the current implementation, which serves as the foundation for the final bounded and regularized calibration approach.

#### 1.1 Baseline Merton Model

The baseline Merton model treats a firm's equity as a European call option on its assets. The model is applied to real firm data representing five publicly traded companies (AAPL, JPM, TSLA, XOM, F) over a one-year period (2020), with the goal of calibrating unobservable asset values and volatilities from observable equity market data, and computing credit risk measures including distance-to-default and default probability.

**Key Assumptions:**

1. **Asset Value Process**: Firm asset value $V_t$ follows a geometric Brownian motion under the risk-neutral measure:
   $$dV_t = r V_t dt + \sigma_V V_t dW_t$$
   where $r$ is the risk-free rate (assumed constant), $\sigma_V$ is asset volatility (assumed constant), and $dW_t$ is a Wiener process.

2. **Default Condition**: Default occurs only at maturity $T$ if the asset value falls below the debt face value $D$:
   - Default if: $V_T < D$
   - No default if: $V_T \geq D$

3. **Equity as European Call Option**: Equity is valued as a European call option on firm assets with strike price equal to the debt face value:
   $$E_t = V_t \Phi(d_1) - D e^{-r(T-t)} \Phi(d_2)$$
   where:
   - $d_1 = \frac{\ln(V_t/D) + (r + \sigma_V^2/2)(T-t)}{\sigma_V \sqrt{T-t}}$
   - $d_2 = d_1 - \sigma_V \sqrt{T-t}$
   - $\Phi(\cdot)$ is the standard normal cumulative distribution function

4. **Equity Volatility Relationship**: The relationship between equity volatility $\sigma_E$ and asset volatility $\sigma_V$ is given by:
   $$\sigma_E E_t = \Delta \sigma_V V_t$$
   where $\Delta = \Phi(d_1)$ is the option delta (sensitivity of equity value to asset value).

#### 1.2 Improved Model with EWMA Smoothing

The improved model applies EWMA (Exponential Weighted Moving Average) smoothing to $\sigma_E$:
   - **EWMA Smoothing**: Apply exponential weighted moving average to the variance, then take the square root:
     $$\text{var}_t^{\text{smooth}} = \lambda \cdot \text{var}_{t-1}^{\text{smooth}} + (1-\lambda) \cdot \sigma_{E,t}^2$$
     $$\sigma_{E,t}^{\text{smooth}} = \sqrt{\text{var}_t^{\text{smooth}}}$$
     where $\lambda = 0.94$ is the smoothing parameter.

**Justification**: The improved model differs from the baseline model **only** in the application of volatility smoothing. Both models use the same calibration methodology (`fsolve` root-finding) and initialization strategy (warm-start using previous period's solution). The volatility smoothing directly addresses the identified weakness by reducing measurement noise in inputs, mitigating—but not eliminating—structural sensitivity that drives PD instability.

#### 1.3 Diagnostic Framework

A comprehensive diagnostic framework has been established to evaluate model performance across four dimensions:

1. **PD Stability**: Maximum daily change in log(PD) per firm
2. **Asset Value Plausibility**: V/E ratio distributions and invalid value counts
3. **Risk Ranking Consistency**: Spearman correlation between PD and leverage, wrong-sign days, top-k containment
4. **Sensitivity Analysis**: Median and p95 elasticities of log(PD) with respect to all input parameters

This framework provides the evaluation metrics needed to validate the bounded and regularized calibration approach.

### 2. Empirical Setup

#### 2.1 Data Sources and Processing

**Firms Analyzed**: AAPL, JPM, TSLA, XOM, F (2020 data)

**Data Alignment: Quarterly Debt to Daily Equity**
- Debt data is available at quarterly frequency, while equity data is available daily
- Quarterly debt values are reindexed using `pandas.reindex()` with `bfill().ffill()` to align to daily frequency

**Equity Market Cap Calculation**
- Equity prices are per-share while debt is in total millions
- Convert equity to total market cap: $E_{\text{total}} = E_{\text{per-share}} \times N \times 1000$ (in millions)
- Shares outstanding: AAPL (16.93B), JPM (3.09B), TSLA (3.325B), XOM (4.25B), F (3.97B)

#### 2.2 Implementation Assumptions

1. **Time to Maturity (T)**: Constant T = 1.0 year for all firms and dates (one-year PD horizon)
2. **Single Debt Proxy**: Each firm's capital structure represented by a single debt face value
3. **Constant Risk-Free Rate**: Daily rates used, but assumed constant over the one-year horizon T
4. **No Dividends**: Dividend payments not accounted for
5. **European Option Assumption**: Default can only occur at maturity T, not before
6. **Geometric Brownian Motion**: Asset values follow GBM with constant drift and volatility
7. **Perfect Market Assumptions**: Frictionless markets, no transaction costs

These assumptions are necessary for analytical tractability but represent limitations that should be considered when interpreting results.

---

## Part II: Empirical Findings

### 3. Baseline Model Diagnosis

After implementing and evaluating the baseline model, we identify systematic weaknesses in its behavior that motivate the need for bounded and regularized calibration.

#### 3.1 Identified Weaknesses

##### (1) Unstable PD Values

The estimated default probabilities exhibit large, discontinuous jumps over time that are inconsistent with smooth changes in underlying inputs.

**Evidence.** Figure 3.1 plots $\log(\text{PD})$ over time for each firm. All firms exhibit abrupt regime shifts and flatlining behavior. The magnitude of instability is quantified by the maximum daily change in $\log(\text{PD})$:

- AAPL: $\max |\Delta\log(\text{PD})| = 23.90$
- F: $4.60$
- JPM: $28.50$
- TSLA: $9.94$
- XOM: $31.55$

![Figure 3.1: log(PD) time-series](outputs/diagnosis_timeseries.png)

##### (2) Asset-Value Plausibility

The inferred asset values themselves are not the primary source of failure. We do not observe widespread implausible or invalid asset values ($V < 0$) in this sample.

**Evidence.** Figure 3.2 shows histograms of the asset-to-equity ratio ($V/E$). For AAPL, TSLA, XOM, and JPM, $V/E$ remains within plausible ranges (typically below 3), consistent with the Merton framework where $V \approx E + D$. Ford (F) exhibits higher $V/E$ ratios, but the calibration also yields very small asset volatility. This pattern is indicative of degeneracy.

![Figure 3.2: V/E histograms](outputs/diagnosis_v_e_ratio.png)

##### (3) Risk Ranking Consistency

The model's ability to rank firms by distress is imperfect and occasionally unreliable.

**Evidence.** While the median daily Spearman rank correlation is $\rho_t = 0.700$, indicating moderate average alignment, failures occur:

- 17.1% of days exhibit the wrong sign between PD and leverage.
- PD ranks change abruptly even when leverage ranks remain constant.

![Figure 3.3: PD rank vs leverage rank over time](outputs/diagnosis_ranking.png)

##### (4) Excessive Sensitivity to Inputs

The dominant weakness of the baseline model is extreme sensitivity to equity volatility, which motivates the need for bounded and regularized calibration.

**Evidence.** We report median absolute elasticities of $\log(\text{PD})$ with respect to model inputs. Equity volatility $\sigma_E$ is the most influential parameter by a wide margin:

- $\text{median } |\text{sens}(\sigma_E)| = 9.211$
- $95^{\text{th}}$ percentile $|\text{sens}(\sigma_E)| = 90.445$
- Extreme cases exceed 150 (e.g., AAPL in June 2020)

In contrast, sensitivities to equity value ($\text{median } |\text{sens}| = 2.922$), debt ($\text{median } |\text{sens}| = 2.987$), interest rate ($\text{median } |\text{sens}| = 2.777$), and maturity ($\text{median } |\text{sens}| = 6.843$) are much smaller.

**Interpretation.** Small changes or estimation noise in $\sigma_E$ can induce large swings in PD, directly explaining the observed instability and ranking inconsistencies. This perturbation analysis establishes the foundation for stress-testing across market regimes and validates the need for constrained optimization that bounds parameter sensitivity.

**Progress Note**: This sensitivity analysis provides the empirical foundation for designing appropriate bounds in the constrained calibration approach. The extreme sensitivities observed here will inform the selection of $\sigma_{\min}$ and $\sigma_{\max}$ bounds.

![Figure 3.4: Sensitivity bar chart](outputs/diagnosis_sensitivity.png)

#### 3.2 Illustrative Examples

##### Example 1: PD Instability Driven by Volatility Sensitivity (AAPL)

In early June 2020, AAPL's $\log(\text{PD})$ exhibits sharp jumps exceeding 20 log-units despite relatively smooth equity dynamics. This period coincides with extreme $\sigma_E$ sensitivity ($|\text{sens}| > 150$), illustrating how volatility amplification drives PD instability.

**Plots:** $\log(\text{PD})$ time-series (Figure 3.1), sensitivity extremes (Figure 3.4)

##### Example 2: Ranking Instability Under Stable Leverage (TSLA)

In the Merton calibration, $$\sigma_E \approx \Phi(d_1) \sigma_V \frac{V}{E}.$$ With low leverage, equity is deep in-the-money so $\Phi(d_1) \approx 1$, and since $V/E \approx 1$, we get TSLA's high inferred asset volatility.

When $\sigma_V$ is large, PD becomes highly sensitive to day-to-day noise in $\sigma_E$. With strong volatility sensitivity (median $|\text{sens}(\sigma_E)| = 9.211$), small fluctuations in estimated equity volatility translate into large PD swings, breaking the link between PD rank and leverage-based distress.

![Figure 3.5: Asset volatility time-series](outputs/naive_sigma_V.png)

**Plot:** PD rank vs leverage rank (Figure 3.3)

##### Example 3: Cross-Firm Instability Despite Plausible Asset Values (XOM, JPM)

XOM and JPM exhibit large PD jumps ($\max |\Delta\log(\text{PD})| > 28$) even though their $V/E$ ratios remain within plausible ranges. This demonstrates that PD instability is not caused by implausible asset levels but by sensitivity amplification.

**Plots:** $\log(\text{PD})$ time-series (Figure 3.1), $V/E$ histograms (Figure 3.2)

#### 3.3 Summary

The baseline model's main weakness is its excessive sensitivity (especially to equity volatility) produces unstable PD dynamics and occasional firm-specific calibration pathologies (most notably Ford), which can trigger episodic breakdowns in risk ranking and reduce reliability for credit risk assessment.

**Progress Toward Final Goal**: The diagnostic framework established here (PD stability, asset plausibility, risk ranking, sensitivity analysis) provides the evaluation metrics needed to validate the bounded and regularized calibration approach. The identified failures—particularly calibration degeneracy (e.g., Ford's extreme $V/E$ ratios with near-zero $\sigma_V$)—directly motivate the need for constrained optimization with economically meaningful bounds.

### 4. Improved Model Results

#### 4.1 Quantitative Comparison

The improved model addresses the primary weakness identified in the baseline model (excessive sensitivity to noisy equity volatility) through volatility smoothing. We evaluate improvements using the same diagnostic framework applied to the baseline model.

##### (1) PD Stability

**Improvement**: EWMA smoothing reduces volatility measurement noise, mitigating—but not eliminating—structural sensitivity, which reduces PD instability.

**Evidence**: The maximum daily change in $\log(\text{PD})$ for all firms:

| Firm | Baseline max \|Δlog(PD)\| | Improved max \|Δlog(PD)\| |
|------|----------------|----------------------|
| AAPL | 23.90 | 2.311 |
| F | 4.60 | 0.2854 |
| JPM | 28.50 | 1.087 |
| TSLA | 9.94 | 1.757 |
| XOM | 31.55 | 1.077 |

![Figure 4.1: Improved log(PD) time-series](outputs/diagnosis_timeseries_improved.png)

The improved model exhibits smoother PD trajectories with fewer abrupt jumps compared to the baseline.

##### (2) Asset Value Plausibility

**Maintained**: The improved model maintains plausible asset values, similar to the baseline model.

**Evidence**: V/E ratios remain within economically reasonable ranges, similar to the baseline model.

![Figure 4.2: Improved V/E histograms](outputs/diagnosis_v_e_ratio_improved.png)

##### (3) Risk Ranking Consistency

**Improvement**: The improved model shows better alignment between PD ranks and leverage ranks.

**Evidence**: 
- Percentage of days with wrong sign: Improved: 1.2%, Baseline: 17.1%
- Top-1 distress in top-2 PD failure rate: Improved: 0.4%, Baseline: 0.8%

Both models show strong top-k containment, with the improved model showing better alignment between PD ranks and leverage-based distress ranks.

![Figure 4.3: Improved PD rank vs leverage rank](outputs/diagnosis_ranking_improved.png)

##### (4) Sensitivity to Inputs

**Improvement**: EWMA smoothing reduces volatility measurement noise, mitigating—but not eliminating—structural sensitivity to equity volatility.

**Evidence**: The median absolute elasticity of $\log(\text{PD})$ with respect to model inputs:

| Parameter | Baseline median $\lvert\text{sens}\rvert$ | Baseline p95 $\lvert\text{sens}\rvert$ | Improved median $\lvert\text{sens}\rvert$ | Improved p95 $\lvert\text{sens}\rvert$ |
|-----------|--------------------------|----------------------|-------------------------|----------------------|
| $\sigma_E$ | 9.211 | 90.445 | 6.790 | 58.394 |
| $E$ | 2.922 | 22.781 | 2.893 | 15.917 |
| $D$ | 2.987 | 24.606 | 2.874 | 15.817 |
| $r$ | 2.777 | 31.993 | 2.747 | 18.527 |
| $T$ | 6.843 | 45.529 | 6.002 | 29.182 |

![Figure 4.4: Improved sensitivity bar chart](outputs/diagnosis_sensitivity_improved.png)

The improved model shows reduced sensitivity to equity volatility, with more balanced sensitivity across all parameters.

#### 4.2 Why It's Better

EWMA smoothing improves the model because the baseline Merton calibration amplifies short-horizon volatility noise into large swings in implied asset volatility, distance-to-default, and ultimately PD. 

By smoothing $\sigma_E$, we reduce measurement noise in the key input driving instability, producing:
- more stable PD paths (large reductions in $\max|\Delta\log(\text{PD})|$),
- more consistent risk ordering over time (wrong-sign days drop sharply from 17.1% to 1.2%), and
- lower effective sensitivity to $\sigma_E$ (median sensitivity drops from 9.211 to 6.790) while leaving other inputs largely unchanged.

**Economic Interpretation**: This approach can be viewed as signal extraction: observed daily equity volatility contains substantial transitory noise, while credit risk should respond primarily to persistent changes in firm risk. Volatility smoothing filters out short-term noise, producing more stable credit risk measures that better reflect underlying firm fundamentals.

### 5. Bounded Model Implementation and Results

#### 5.1 Implementation

The bounded and regularized calibration has been implemented using `scipy.optimize.least_squares` with the Trust Region Reflective algorithm. The optimization problem is:

$$\min_{V, \sigma_V} \left\| \begin{bmatrix}
E - \text{BlackScholes}(V, D, T, r, \sigma_V) \\
\sigma_E - \frac{\Delta \sigma_V V}{E}
\end{bmatrix} \right\|^2 + \lambda_1 (\sigma_V - \sigma_{V,0})^2 + \lambda_2 (V/V_0 - 1)^2$$

subject to:
- $\sigma_{\min} \leq \sigma_V \leq \sigma_{\max}$ (tuned: [0.03, 1.2])
- $L_{\min} \leq D/V \leq L_{\max}$ (tuned: [0.05, 0.98])
- $V > 0$

**Parameter Tuning Process:**
- Initial configuration: $\sigma_V \in [0.05, 0.80]$, leverage $\in [0.10, 0.95]$, $\lambda_1 = \lambda_2 = 0.1$
- Result: 36.6% of $\sigma_V$ values hitting upper bound, indicating constraints too restrictive
- Final tuned configuration: $\sigma_V \in [0.03, 1.2]$, leverage $\in [0.05, 0.98]$, $\lambda_1 = \lambda_2 = 0.2$
- Rationale: Increased $\sigma_V$ upper bound to reduce constraint binding; increased regularization to improve stability

#### 5.2 Quantitative Comparison

##### (1) PD Stability

**Mixed Results**: The bounded model shows improvement for some firms but degradation for others compared to the improved model.

| Firm | Baseline max \|Δlog(PD)\| | Improved max \|Δlog(PD)\| | Bounded max \|Δlog(PD)\| |
|------|--------------------------|---------------------------|--------------------------|
| AAPL | 23.90 | 2.311 | **1.957** ✓ |
| F | 4.60 | **0.285** ✓ | 0.460 |
| JPM | 28.50 | **1.087** ✓ | 5.138 |
| TSLA | 9.94 | 1.757 | 2.583 |
| XOM | 31.55 | **1.077** ✓ | 3.390 |

**Interpretation**: Bounded model achieves better stability for AAPL but worse stability for JPM and XOM. The improved model provides the most consistent stability across all firms.

##### (2) Asset Value Plausibility

**Maintained**: All three models maintain economically plausible asset values with no invalid $V$ values ($n_V^{\text{invalid}} = 0$ for all models).

##### (3) Risk Ranking Consistency

**Critical Weakness**: The bounded model exhibits poor risk ranking performance, representing a significant regression from the improved model.

| Metric | Baseline | Improved | Bounded |
|--------|----------|----------|---------|
| Median Spearman $\rho_t$ | 0.700 | **0.700** ✓ | 0.300 ✗ |
| Wrong sign % | 17.1% | **1.2%** ✓ | 44.0% ✗ |
| Top-1 not in top-2 PD % | 0.8% | **0.4%** ✓ | 29.8% ✗ |

**Interpretation**: The bounded model's risk ranking correlation drops to 0.300 (vs 0.700 for improved), and 44% of days exhibit wrong sign between PD and leverage (vs 1.2% for improved). This suggests that hard constraints may be forcing solutions that don't accurately reflect firm risk differences.

##### (4) Sensitivity to Inputs

**Mixed Results**: The bounded model achieves the best median sensitivity to $\sigma_E$ but shows much worse sensitivity to other parameters.

| Parameter | Baseline median \|sens\| | Improved median \|sens\| | Bounded median \|sens\| |
|-----------|--------------------------|--------------------------|--------------------------|
| $\sigma_E$ | 9.211 | 6.790 | **6.235** ✓ |
| $E$ | 2.922 | 2.893 | 32.523 ✗ |
| $D$ | 2.987 | 2.874 | 33.575 ✗ |
| $r$ | 2.777 | 2.747 | 2605.396 ✗ |
| $T$ | 6.843 | 6.002 | 29.890 ✗ |

**Note**: Sensitivity calculation uses unconstrained calibration for all models, which may not accurately reflect bounded model behavior when constraints are binding. The extreme sensitivity to $r$ (median = 2605) likely reflects constraint binding effects.

#### 5.3 Root Cause Analysis

The bounded model's poor risk ranking performance suggests several issues:

1. **Constraint Binding**: When optimization hits bounds, solutions may not fit the data well, leading to poor risk discrimination. Approximately 36.6% of $\sigma_V$ values hit the upper bound even after tuning.

2. **Regularization Trade-Off**: Increased regularization ($\lambda = 0.2$) may be penalizing economically meaningful differences between firms, reducing the model's ability to distinguish risk levels.

3. **Optimization Issues**: The constrained optimization may be finding local minima that satisfy bounds but don't accurately reflect firm risk, particularly when constraints are active.

4. **Sensitivity Calculation Limitation**: The sensitivity test uses unconstrained calibration, which doesn't reflect how the bounded model responds to perturbations when constraints are binding.

#### 5.4 Summary and Recommendations

**Strengths of Bounded Model:**
- ✓ Successfully enforces parameter bounds ($\sigma_V \in [0.03, 1.2]$)
- ✓ Maintains plausible asset values (no invalid $V$)
- ✓ Best median sensitivity to $\sigma_E$ (6.235 vs 6.790 for improved)
- ✓ Better PD stability for AAPL compared to improved model

**Weaknesses of Bounded Model:**
- ✗ Poor risk ranking consistency (44% wrong sign days vs 1.2% for improved)
- ✗ High sensitivity to $r$ and other parameters (likely due to constraint binding)
- ✗ Mixed PD stability results across firms
- ✗ Risk ranking correlation drops to 0.300 (vs 0.700 for improved)

**Conclusion**: The bounded calibration successfully enforces parameter bounds and reduces sensitivity to equity volatility. However, it introduces significant issues with risk ranking consistency, suggesting that hard constraints may be too restrictive for accurate credit risk assessment.

**Recommendation**: The improved model (EWMA smoothing with unconstrained calibration) provides superior overall performance, achieving:
- Better risk ranking (1.2% wrong sign vs 44% for bounded)
- More balanced sensitivity across parameters
- Better PD stability for most firms

The bounded calibration should be considered as a fallback option when unconstrained solutions produce implausible parameters, but the improved model remains the preferred approach for production use.

**Future Directions**: 
- Explore hybrid approaches: use bounded calibration only when unconstrained solution violates bounds
- Implement two-stage optimization: unconstrained first, then bounded if needed
- Consider soft bounds with penalty functions instead of hard constraints
- Fix sensitivity calculation to use bounded calibration for accurate assessment

---

## Part III: Roadmap to Final Goal

### 6. Target Implementation: Bounded and Regularized Calibration

**Status: COMPLETED** ✓

The bounded and regularized calibration has been implemented using constrained nonlinear least squares optimization. See Section 5 for detailed implementation and results.

#### 6.1 Implementation Summary

**Implementation**: Replaced `scipy.optimize.fsolve` with `scipy.optimize.least_squares` using Trust Region Reflective algorithm with bounds and regularization:

$$\min_{V, \sigma_V} \left\| \begin{bmatrix}
E - \text{BlackScholes}(V, D, T, r, \sigma_V) \\
\sigma_E - \frac{\Delta \sigma_V V}{E}
\end{bmatrix} \right\|^2 + \lambda_1 (\sigma_V - \sigma_{V,0})^2 + \lambda_2 (V/V_0 - 1)^2$$

subject to:
- $\sigma_{\min} \leq \sigma_V \leq \sigma_{\max}$ (tuned: [0.03, 1.2])
- $L_{\min} \leq D/V \leq L_{\max}$ (tuned: [0.05, 0.98])
- $V > 0$

#### 6.2 Actual Results vs. Expected Improvements

**Expected vs. Actual:**

1. **Elimination of Calibration Degeneracy**: ✓ **ACHIEVED** - Bounds prevent extreme $V/E$ ratios; all models maintain valid asset values
2. **Reduced PD Instability**: ⚠️ **PARTIAL** - Bounded model shows mixed results; improved model performs better overall
3. **Improved Risk Ranking**: ✗ **NOT ACHIEVED** - Bounded model shows worse risk ranking (44% wrong sign vs 1.2% for improved)
4. **Better Economic Consistency**: ⚠️ **PARTIAL** - Bounds enforce parameter ranges but sacrifice risk discrimination accuracy

**Key Finding**: Hard constraints successfully enforce parameter bounds but introduce significant risk ranking issues, suggesting that the improved model (EWMA smoothing) provides a better balance between stability and accuracy.

### 7. Next Steps

#### 7.1 Immediate Tasks (Priority Order)

1. **Extend Stress-Testing Framework**
   - Conduct perturbation analysis across market regimes (bull, bear, crisis)
   - Test sensitivity to equity shocks, volatility spikes, leverage changes
   - Quantify failure modes and boundary conditions
   - Validate that bounds prevent degeneracy under stress scenarios

2. **Hybrid Calibration Approaches**
   - Implement two-stage optimization: unconstrained first, then bounded if needed
   - Explore soft bounds with penalty functions instead of hard constraints
   - Test adaptive bounds based on firm characteristics
   - Fix sensitivity calculation to use bounded calibration for accurate assessment

3. **Benchmark Against Reduced-Form Models**
   - Compare structural default probabilities with reduced-form credit models
   - Evaluate against market-implied risk signals (CDS spreads, credit ratings)
   - Assess empirical reliability and economic consistency
   - Document where structural model adds value vs. reduced-form approaches

#### 7.2 Validation Strategy

The diagnostic framework established in Part II has been used to validate all three models (baseline, improved, bounded). Results show:

- **PD Stability**: Improved model achieves best overall stability; bounded model shows mixed results
- **Asset Plausibility**: All models maintain valid asset values
- **Risk Ranking**: Improved model achieves best ranking (1.2% wrong sign); bounded model shows poor ranking (44% wrong sign)
- **Sensitivity**: Improved model shows most balanced sensitivity; bounded model best for $\sigma_E$ but worse for other parameters

#### 7.3 Longer-Term Extensions

Future work could address remaining limitations by incorporating:
- Maturity-aware debt measures (rather than single debt proxy)
- Forward-looking (implied) volatility estimates
- Alternative structural frameworks that allow for early default and liquidity risk
- Multi-factor models that capture additional risk dimensions

The bounded calibration approach established here provides a foundation for these extensions.

---

## Part IV: Technical Appendix

### A. Calibration Methodology Details

#### A.1 Numerical Methods

**Baseline and Improved Models**: We use `scipy.optimize.fsolve` to solve the system of equations:

$$\begin{cases}
E - \text{BlackScholes}(V, D, T, r, \sigma_V) = 0 \\
\sigma_E - \frac{\Delta \sigma_V V}{E} = 0
\end{cases}$$

where $\Delta = \Phi(d_1)$ is the option delta. For the improved model, $\sigma_E$ in the second equation is replaced with $\sigma_E^{\text{smooth}}$.

**Bounded Model**: We use `scipy.optimize.least_squares` with Trust Region Reflective algorithm to solve the constrained optimization problem with bounds and regularization terms. See Section 5.1 for details.

#### A.2 Initial Guesses and Warm-Start Strategy

The calibration uses a warm-start approach that reflects the persistence of firm value and asset volatility:

- **Initial observation**: For the first observation for each firm, use standard approximations:
  - **Asset Value**: $V_0 = E + D$ (assuming assets equal equity plus debt)
  - **Asset Volatility**: $\sigma_{V0} = \frac{\sigma_E \cdot E}{E + D}$ (leverage-adjusted volatility estimate), where $\sigma_E$ is either raw (baseline) or smoothed (improved)

- **Subsequent observations**: For each subsequent date, use the solution from the previous period as the initial guess:
  - $V_0 = V_{t-1}$ (previous period's asset value)
  - $\sigma_{V0} = \sigma_{V,t-1}$ (previous period's asset volatility)

This warm-start approach improves convergence by leveraging the temporal persistence of firm fundamentals, as asset values and volatilities typically change smoothly over time rather than jumping discontinuously.

#### A.3 Edge Case Handling

1. **Non-negative constraints**: Both $V$ and $\sigma_V$ are constrained to be at least $10^{-6}$ to prevent negative or zero values.

2. **Calibration failures**: If the numerical solver fails to converge or raises an exception, the function returns the standard approximation ($V = E + D$, $\sigma_V = \frac{\sigma_E \cdot E}{E + D}$).

3. **Solver parameters**: 
   - Tolerance: `xtol=1e-6` (solution tolerance)
   - Maximum iterations: `maxfev=5000` (maximum function evaluations)

### B. Risk Measures Computation

#### B.1 Distance-to-Default (DD)

In the Merton model, **DD = -d₂**, where d₂ is the standard Black-Scholes parameter:

$$\text{DD} = -\frac{\ln(V/D) + (r - 0.5\sigma_V^2)T}{\sigma_V \sqrt{T}}$$

**Relationship to PD**: $\text{PD} = \Phi(-\text{DD}) = \Phi(d_2)$

#### B.2 Default Probability (PD)

The risk-neutral default probability is:

$$\text{PD} = \Phi(-d_2) = \Phi\left(-\frac{\ln(V/D) + (r - \sigma_V^2/2)T}{\sigma_V \sqrt{T}}\right)$$

**Edge cases**:
- If $T \leq 0$, $\sigma_V \leq 0$, $V \leq 0$, or $D \leq 0$: Returns `1.0` if $V < D$ else `0.0`
- Result is clamped to $[0, 1]$ to ensure valid probability

### C. Limitations

#### C.1 What the Model Still Does Not Capture

The model cannot capture early default or liquidity/refinancing-driven distress because equity is modeled as a European option and default is only assessed at maturity $T$. Debt is represented by a single proxy $D$ (total book debt from annual Yahoo Finance balance sheets, forward-filled daily), which ignores maturity structure, covenants, seniority, and near-term funding pressure. Corporate actions (dividends, buybacks, issuance) are not modeled, though they affect equity and inferred asset values.

#### C.2 What Assumptions Remain

We retain core Merton assumptions: asset value follows GBM with constant drift/volatility over the horizon, markets are frictionless, and default occurs only at $T$. We fix $T=1$ as a one-year PD horizon, since $D$ is an annual balance-sheet proxy rather than a maturity-matched promised payment. EWMA smoothing changes only the $\sigma_E$ input and does not alter the calibration equations, so ill-conditioning can still occur for some firms/dates.

#### C.3 When the Improvement May Not Work

EWMA smoothing can lag sudden regime shifts (earnings shocks, crises), temporarily understating risk, and may dampen genuine distress-related volatility spikes. If instability mainly comes from calibration ill-conditioning (e.g., high leverage or mismatched debt proxy), smoothing may improve PD smoothness but not fully prevent implausible implied parameters.

---

## References

- **Merton (1974)**: "On the Pricing of Corporate Debt: The Risk Structure of Interest Rates"
- **Merton Model Credit Risk Calculator**: [Credit Risk Calculator](https://www.creditrisk.nathangs.ca/)
- **EWMA Volatility Smoothing**: Common practice in financial modeling to reduce noise in realized volatility estimates
