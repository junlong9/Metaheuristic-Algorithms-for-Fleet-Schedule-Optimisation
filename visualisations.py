import matplotlib.pyplot as plt
# ============================================================
# PLOT RESULTS IN PYTHON
# ============================================================

def plot_comparison(original_table, best_table):
    """
    Plots original and optimised availability in Python.
    """

    plt.figure(figsize=(16, 6))

    plt.plot(
        original_table["Date"],
        original_table["Available"],
        label="Original Availability",
        linewidth=1
    )

    plt.plot(
        best_table["Date"],
        best_table["Available"],
        label="Optimised Availability",
        linewidth=1
    )

    plt.title("Original vs Optimised Fleet Availability")
    plt.xlabel("Date")
    plt.ylabel("Available Aircraft")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
