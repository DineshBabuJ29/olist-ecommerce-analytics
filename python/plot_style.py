"""Shared chart style so every figure in /outputs/figures looks consistent."""
import matplotlib
matplotlib.use("Agg")  # render to files, no window needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

PRIMARY = "#2563EB"   # blue - main series
ACCENT = "#F97316"    # orange - highlight / comparison
NEGATIVE = "#DC2626"  # red - bad outcome (late, negative review)
NEUTRAL = "#94A3B8"   # grey - context

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 13, "axes.titlelocation": "left",
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 10,
})


def money(ax, axis="y"):
    """Format an axis as R$ thousands / millions."""
    def fmt(x, _):
        if abs(x) >= 1e6:
            return f"R${x / 1e6:.1f}M"
        if abs(x) >= 1e3:
            return f"R${x / 1e3:.0f}K"
        return f"R${x:.0f}"
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(mticker.FuncFormatter(fmt))


def pct(ax, axis="y"):
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(mticker.PercentFormatter(decimals=0))


def save(fig, path):
    fig.savefig(path)
    plt.close(fig)
    print(f"  saved {path.name}")
