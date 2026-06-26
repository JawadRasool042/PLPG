"""Analytics chart generation for the advanced learning system."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _ensure_output_dir(output_dir: str) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_radar_chart(scores: Dict[str, float], user_name: str, output_dir: str) -> str:
    output_dir = _ensure_output_dir(output_dir)
    labels = list(scores.keys())
    values = list(scores.values())
    if not labels:
        raise ValueError("scores cannot be empty")

    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticklabels([])
    ax.set_title(f"{user_name} - Interest Radar", pad=20)

    path = os.path.join(output_dir, f"{user_name.replace(' ', '_')}_radar_chart.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def generate_growth_graph(history: List[Dict[str, float]], user_name: str, output_dir: str) -> str:
    output_dir = _ensure_output_dir(output_dir)
    fig, ax = plt.subplots(figsize=(10, 5))
    for domain in sorted({item["domain"] for item in history}):
        series = [(idx, item["score"]) for idx, item in enumerate(history) if item["domain"] == domain]
        if series:
            x = [point[0] for point in series]
            y = [point[1] for point in series]
            ax.plot(x, y, marker="o", label=domain)
    ax.set_title(f"{user_name} - Growth Graph")
    ax.set_xlabel("Assessment #")
    ax.set_ylabel("Score")
    ax.legend(loc="best", fontsize=8)
    path = os.path.join(output_dir, f"{user_name.replace(' ', '_')}_growth_graph.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def generate_skill_heatmap(matrix: List[List[float]], labels: List[str], user_name: str, output_dir: str) -> str:
    output_dir = _ensure_output_dir(output_dir)
    fig, ax = plt.subplots(figsize=(10, 7))
    im = ax.imshow(matrix, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    fig.colorbar(im, ax=ax)
    ax.set_title(f"{user_name} - Skill Heatmap")
    path = os.path.join(output_dir, f"{user_name.replace(' ', '_')}_skill_heatmap.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def generate_domain_comparison(comparison: Dict[str, float], user_name: str, output_dir: str) -> str:
    output_dir = _ensure_output_dir(output_dir)
    domains = list(comparison.keys())
    values = list(comparison.values())
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(domains, values, color="#4F46E5")
    ax.set_title(f"{user_name} - Domain Comparison")
    ax.set_ylabel("Score")
    ax.tick_params(axis="x", rotation=25)
    path = os.path.join(output_dir, f"{user_name.replace(' ', '_')}_domain_comparison.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
