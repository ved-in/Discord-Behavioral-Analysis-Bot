import os
import math
import uuid
import tempfile
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


RADAR_DIMENSIONS = [
    ("Chaos", "chaos_score"),
    ("Eloquence", "eloquence_score"),
    ("Expressiveness", "expressiveness_score"),
    ("Social", "social_score"),
    ("Consistency", "consistency_score"),
    ("Toxicity", "toxicity_score"),
]

DIMENSION_COLORS = {
    "Chaos": "#FF4500",
    "Eloquence": "#4169E1",
    "Expressiveness": "#FFD700",
    "Social": "#FF69B4",
    "Consistency": "#32CD32",
    "Toxicity": "#8B0000",
}

LABELS = [d[0] for d in RADAR_DIMENSIONS]


def radar_values(metrics):
    """
    Extract and normalize scores from metrics dict. Divides by 100 to convert
    0-100 scale to 0-1 for polar plot (which expects unit values).
    """
    temp = []
    for _, attr in RADAR_DIMENSIONS:
        temp.append(metrics[attr] / 100)
    return temp


def draw_radar(ax, values, fill_color, dot_colors=None, alpha=0.65):
    """
    Draw a single radar chart on provided axis. Renders concentric gridlines,
    spoke lines, filled polygon, outline, and colored dots at each dimension.

    Key design: angles are evenly spaced around circle (2*pi / N).
    Values and angles are zipped to draw radial lines and fill the polygon.
    Final angle appended to close the shape (angle + value becomes angle + value[0]).
    """
    N = len(LABELS)
    angles = [n / float(N) * 2 * math.pi for n in range(N)] + [0]
    values = list(values)
    vals = values + values[:1]

    # Concentric gridlines (0.2, 0.4, 0.6, 0.8, 1.0 on unit scale)
    for level in [0.2, 0.4, 0.6, 0.8, 1.0]:
        ax.plot(angles, [level] * (N + 1), color="#ffffff", linewidth=0.3, alpha=0.15)

    # Spoke lines (radial from center to perimeter)
    for angle in angles[:-1]:
        ax.plot([angle, angle], [0, 1], color="#ffffff", linewidth=0.4, alpha=0.2)

    # Filled polygon and outline
    ax.fill(angles, vals, alpha=alpha * 0.3, color=fill_color)
    ax.plot(angles, vals, color=fill_color, linewidth=2.5, alpha=0.9)

    # Colored dots at each dimension endpoint
    dot_colors = dot_colors or [fill_color] * N
    for angle, val, color in zip(angles[:-1], values, dot_colors):
        ax.plot(angle, val, "o", color=color, markersize=7, zorder=5)

    # Axis labels and ticks
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(LABELS, fontsize=10, fontweight="bold", color="white")
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], color="#888888", fontsize=7)
    ax.set_ylim(0, 1)
    ax.spines["polar"].set_color("#333355")
    ax.grid(False)


def save_chart(fig, prefix, output_dir):
    """
    Save figure to disk with UUID suffix for uniqueness, close the figure
    to free memory (important in batch operations), and return the path.
    Uses Agg backend (non-interactive) to avoid display issues.
    """
    path = os.path.join(output_dir, f"{prefix}_{uuid.uuid4().hex}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def generate_chart(metrics, username, output_dir=None):
    """
    Generate and save a single behavioral profile radar chart.
    Footer displays all dimension scores in monospace for easy reading.
    """
    output_dir = output_dir or tempfile.gettempdir()
    fig = plt.figure(figsize=(8, 8), facecolor="#1a1a2e")
    ax = fig.add_subplot(111, polar=True, facecolor="#16213e")
    draw_radar(
        ax,
        radar_values(metrics),
        "#7B68EE",
        dot_colors=[DIMENSION_COLORS[l] for l in LABELS],
    )
    ax.set_title(
        f"Behavioral Profile — {username}",
        color="white",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    score_text = "  |  ".join(
        f"{label}: {metrics[attr]:.0f}" for label, attr in RADAR_DIMENSIONS
    )
    fig.text(
        0.5,
        0.02,
        score_text,
        ha="center",
        va="bottom",
        color="#aaaacc",
        fontsize=8,
        fontfamily="monospace",
    )
    return save_chart(fig, "radar", output_dir)


def generate_comparison_chart(metrics1, name1, metrics2, name2, output_dir=None):
    """
    Generate side-by-side radar comparison. Uses plt.subplots with polar=True
    to create a 1x2 grid of polar plots. Each subplot gets its own title and color.
    """
    output_dir = output_dir or tempfile.gettempdir()
    fig, axes = plt.subplots(
        1, 2, figsize=(16, 8), subplot_kw={"polar": True}, facecolor="#1a1a2e"
    )
    for ax, metrics, name, color in zip(
        axes, [metrics1, metrics2], [name1, name2], ["#7B68EE", "#FF6B6B"]
    ):
        ax.set_facecolor("#16213e")
        draw_radar(ax, radar_values(metrics), color)
        ax.set_title(name, color="white", fontsize=13, fontweight="bold", pad=16)
    fig.suptitle("Behavioral Comparison", color="white", fontsize=16, fontweight="bold")
    return save_chart(fig, "compare", output_dir)
