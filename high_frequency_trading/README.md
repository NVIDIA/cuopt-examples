# High-Frequency Trading Market-Making Optimization

This example demonstrates **why GPU acceleration is required** for realistic high-frequency trading (HFT) market-making optimization, not just "faster" but essential for practical deployment.

## Problem Overview

A cryptocurrency market maker continuously posts bid and ask quotes across 50+ trading pairs. The system must:

- **Update quotes 10 times per second** (100ms cycle time)
- **Optimize across 50+ pairs** considering fill probability, transaction costs, slippage, and inventory risk
- **Solve within ~50ms** to leave time for data fetching and order placement

### The Challenge

**CPU Performance (scipy):**
- 50 pairs: ~200-300ms solve time ❌
- **Result:** 5-6x over budget, cannot maintain real-time operation

**GPU Performance (NVIDIA cuOpt):**
- 50 pairs: ~7ms solve time ✅
- **Result:** ~35x speedup, enables real-time trading

This is not an optimization — **CPU cannot do this in real-time; GPU makes it possible.**

## Problem Formulation

### Decision Variables

For each trading pair *i*:
- **spread<sub>i</sub>**: Bid-ask spread (basis points)
- **skew<sub>i</sub>**: Quote asymmetry (-1 to +1, controls bid/ask positioning)
- **notional<sub>i</sub>**: Quote size (dollars)

### Objective Function

Maximize expected profit minus inventory risk:

```
max Σ [P_fill(spread_i) × spread_i × notional_i] - λ × Σ |inventory_i| × volatility_i × |skew_i|
```

Where:
- **P_fill(spread)** = exp(-α × spread) = fill probability (exponential decay)
- **λ** = risk aversion parameter
- **volatility<sub>i</sub>** = recent price volatility
- **inventory<sub>i</sub>** = current position

### Realistic Features

1. **Non-linear fill probability**: Wider spreads → exponentially lower fill rates
2. **Transaction costs**: Trading fees + slippage (quadratic in size)
3. **Adverse selection**: Larger quotes incur higher adverse selection costs
4. **Inventory risk**: Volatility-weighted position penalty

### Constraints

- Minimum spread ≥ 2 × fee_rate (must cover trading costs)
- Total capital: Σ notional<sub>i</sub> ≤ Capital
- Position limits: 0 ≤ notional<sub>i</sub> ≤ 0.05 × Capital
- Skew bounds: -1 ≤ skew<sub>i</sub> ≤ 1

## Why This Example Matters

### Real-World Use Case

This demonstrates a practical scenario where **GPU acceleration is required**, not optional:

- **CPU result**: System cannot maintain 10Hz quote updates
- **GPU result**: System operates comfortably within real-time constraints
- **Impact**: Enables strategies that are impossible on CPU

### Educational Value

Useful for:
- Financial engineers and quantitative developers
- Operations research practitioners
- Students learning optimization in finance
- Developers evaluating cuOpt for real-time systems

Shows:
- Realistic financial optimization workflow
- Non-linear optimization concepts
- Performance benchmarking methodology
- Real-time decision constraints
- When GPU acceleration becomes necessary

## Running the Example

### Prerequisites

- NVIDIA GPU with appropriate drivers
- NVIDIA Container Toolkit (for Docker) or GPU-enabled environment
- Python 3.8+

### Option 1: Docker (Recommended)

```bash
# Pull cuOpt Docker image
docker pull nvidia/cuopt:25.12.0a-cuda12.9-py3.13

# Run Jupyter
docker run -it --rm --gpus all --network=host \
  -v $(pwd):/workspace -w /workspace \
  nvidia/cuopt:25.12.0a-cuda12.9-py3.13 \
  /bin/bash -c "pip install -r requirements.txt; jupyter-notebook"
```

Open the provided URL in your browser and navigate to `hft_market_making.ipynb`.

### Option 2: Local Installation

```bash
# Install cuOpt
pip install --extra-index-url=https://pypi.nvidia.com cuopt-cu12

# Install dependencies
pip install -r requirements.txt

# Launch Jupyter
jupyter notebook hft_market_making.ipynb
```

### Option 3: Google Colab

1. Upload `hft_market_making.ipynb` to Colab
2. Enable GPU: Runtime → Change runtime type → GPU
3. Run all cells (cuOpt will be installed automatically)

## Expected Results

### Benchmark Summary

| Pairs | Variables | CPU Time | GPU Time | Speedup | CPU Status |
|-------|-----------|----------|----------|---------|------------|
| 10    | 30        | ~30ms    | ~3ms     | 10x     | ✅ OK      |
| 20    | 60        | ~80ms    | ~4ms     | 20x     | ⚠️ Tight   |
| 30    | 90        | ~130ms   | ~5ms     | 26x     | ❌ Over    |
| 40    | 120       | ~180ms   | ~6ms     | 30x     | ❌ Over    |
| 50    | 150       | ~250ms   | ~7ms     | 35x     | ❌ Over    |

**Key Insight:** At 50 pairs (realistic workload), CPU is 5x over budget while GPU completes comfortably within the 50ms constraint.

### Visualization

The notebook generates comparison charts showing:
- CPU vs GPU solve times across problem sizes (log scale)
- Speedup factors (10-35x)
- Budget violation analysis
- Real-time feasibility assessment

## Problem Complexity

### Why Non-Linear Matters

A simplified linear model (ignoring fill probability dynamics) can solve in ~5ms on CPU. However:

- **Unrealistic**: Linear models don't capture market behavior
- **Dangerous**: Ignores adverse selection and fill probability
- **Unprofitable**: Real market-making requires realistic models

The non-linear realistic model:
- CPU: 200-300ms (50-60x slower than linear)
- GPU: 7ms (remains fast despite complexity)
- **Conclusion**: Only GPU can handle realistic models in real-time

### Scaling Considerations

| Pairs | Frequency | CPU Viable? | GPU Required? |
|-------|-----------|-------------|---------------|
| 10    | 10 Hz     | ✅ Yes      | No            |
| 20    | 10 Hz     | ⚠️ Tight    | Recommended   |
| 50    | 10 Hz     | ❌ No       | **Yes**       |
| 100   | 10 Hz     | ❌ No       | **Yes**       |

## Files

- `hft_market_making.ipynb` - Main demonstration notebook
- `README.md` - This file
- `requirements.txt` - Python dependencies
- `data/` - Output directory for results

## References

- **cuOpt Documentation**: https://docs.nvidia.com/cuopt/
- **Market Making Theory**: Avellaneda, M., & Stoikov, S. (2008). "High-frequency trading in a limit order book". Quantitative Finance, 8(3), 217-224.
- **Portfolio Optimization**: For related financial optimization examples, see `../portfolio_optimization/`

## Next Steps

After running this example:

1. **Scale up**: Test with 100+ pairs to see GPU advantage grow
2. **Add complexity**: Include order book dynamics, correlation models
3. **Real data**: Integrate with live market data feeds
4. **Deploy**: Run on production GPU infrastructure

## Contributing

This example is part of the [NVIDIA cuOpt Examples](https://github.com/NVIDIA/cuopt-examples) repository. Contributions are welcome! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

This project is licensed under Apache 2.0. See [LICENSE.md](../LICENSE.md) for details.
