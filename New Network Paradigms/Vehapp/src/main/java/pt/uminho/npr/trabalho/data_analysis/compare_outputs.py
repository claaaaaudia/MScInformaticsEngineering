#!/usr/bin/env python3
"""Compare two MOSAIC RSU output CSVs.

The script compares a run with recommendations against a run without them and
reports:
- average and peak traffic density
- queue length statistics
- queue duration and longest queue episode
- per-zone car density

Expected CSV columns:
sim_time,avg_speed,z1,z2,z3,cars_z1,cars_z2,cars_z3,total_cars,q_len_m
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Sequence


@dataclass(frozen=True)
class Sample:
    sim_time: float
    avg_speed: float
    z1: float
    z2: float
    z3: float
    cars_z1: int
    cars_z2: int
    cars_z3: int
    total_cars: int
    q_len_m: float


@dataclass(frozen=True)
class ScenarioSummary:
    label: str
    samples: int
    start_time: float
    end_time: float
    duration_s: float
    average_total_cars: float
    peak_total_cars: int
    average_density_vpkm: float
    peak_density_vpkm: float
    average_queue_m: float
    peak_queue_m: float
    queue_duration_s: float
    longest_queue_episode_s: float
    queue_episodes: int
    average_z1_density_vpkm: float
    average_z2_density_vpkm: float
    average_z3_density_vpkm: float
    average_speed: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare MOSAIC output CSVs with and without recommendations."
    )
    parser.add_argument(
        "with_recommendations",
        type=Path,
        help="CSV generated with recommendations enabled.",
    )
    parser.add_argument(
        "without_recommendations",
        type=Path,
        help="CSV generated with recommendations disabled.",
    )
    parser.add_argument(
        "--road-length-m",
        type=float,
        default=280.0,
        help="Total monitored road length used to compute density (default: 280.0).",
    )
    parser.add_argument(
        "--queue-threshold-m",
        type=float,
        default=0.0,
        help="Queue length threshold used to count queue time (default: > 0.0 m).",
    )
    return parser.parse_args()


def read_samples(path: Path) -> list[Sample]:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "sim_time",
            "avg_speed",
            "z1",
            "z2",
            "z3",
            "cars_z1",
            "cars_z2",
            "cars_z3",
            "total_cars",
            "q_len_m",
        }
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            missing = sorted(required.difference(set(reader.fieldnames or [])))
            raise ValueError(f"{path} is missing expected columns: {', '.join(missing)}")

        samples: list[Sample] = []
        for row in reader:
            if not row:
                continue
            samples.append(
                Sample(
                    sim_time=float(row["sim_time"]),
                    avg_speed=float(row["avg_speed"]),
                    z1=float(row["z1"]),
                    z2=float(row["z2"]),
                    z3=float(row["z3"]),
                    cars_z1=int(row["cars_z1"]),
                    cars_z2=int(row["cars_z2"]),
                    cars_z3=int(row["cars_z3"]),
                    total_cars=int(row["total_cars"]),
                    q_len_m=float(row["q_len_m"]),
                )
            )

    if not samples:
        raise ValueError(f"{path} has no data rows")
    return samples


def sample_periods(samples: Sequence[Sample]) -> list[float]:
    if len(samples) < 2:
        return [1.0]

    periods: list[float] = []
    for left, right in zip(samples, samples[1:]):
        delta = right.sim_time - left.sim_time
        if delta > 0:
            periods.append(delta)
    return periods or [1.0]


def queue_duration(samples: Sequence[Sample], threshold_m: float) -> tuple[float, float, int]:
    durations: list[float] = []
    episode_length = 0.0
    queue_time = 0.0
    episodes = 0

    periods = sample_periods(samples)
    last_period = periods[-1]

    for index, sample in enumerate(samples):
        interval = periods[index] if index < len(periods) else last_period
        in_queue = sample.q_len_m > threshold_m
        if in_queue:
            queue_time += interval
            episode_length += interval
            if episode_length == interval:
                episodes += 1
        else:
            if episode_length > 0:
                durations.append(episode_length)
            episode_length = 0.0

    if episode_length > 0:
        durations.append(episode_length)

    longest = max(durations) if durations else 0.0
    return queue_time, longest, episodes


def summarize(label: str, samples: Sequence[Sample], road_length_m: float, queue_threshold_m: float) -> ScenarioSummary:
    total_cars = [sample.total_cars for sample in samples]
    queue_lengths = [sample.q_len_m for sample in samples]
    avg_speeds = [sample.avg_speed for sample in samples]
    z1_counts = [sample.cars_z1 for sample in samples]
    z2_counts = [sample.cars_z2 for sample in samples]
    z3_counts = [sample.cars_z3 for sample in samples]
    densities = [(cars / road_length_m) * 1000.0 for cars in total_cars]
    z1_densities = [(cars / 140.0) * 1000.0 for cars in z1_counts]
    z2_densities = [(cars / 60.0) * 1000.0 for cars in z2_counts]
    z3_densities = [(cars / 80.0) * 1000.0 for cars in z3_counts]

    queue_time, longest_queue, episodes = queue_duration(samples, queue_threshold_m)
    start_time = samples[0].sim_time
    end_time = samples[-1].sim_time
    duration_s = max(end_time - start_time, 0.0)

    return ScenarioSummary(
        label=label,
        samples=len(samples),
        start_time=start_time,
        end_time=end_time,
        duration_s=duration_s,
        average_total_cars=mean(total_cars),
        peak_total_cars=max(total_cars),
        average_density_vpkm=mean(densities),
        peak_density_vpkm=max(densities),
        average_queue_m=mean(queue_lengths),
        peak_queue_m=max(queue_lengths),
        queue_duration_s=queue_time,
        longest_queue_episode_s=longest_queue,
        queue_episodes=episodes,
        average_z1_density_vpkm=mean(z1_densities),
        average_z2_density_vpkm=mean(z2_densities),
        average_z3_density_vpkm=mean(z3_densities),
        average_speed=mean(avg_speeds),
    )


def print_summary(summary: ScenarioSummary) -> None:
    queue_share = (summary.queue_duration_s / summary.duration_s * 100.0) if summary.duration_s > 0 else 0.0

    print(f"\n=== {summary.label} ===")
    print(f"Samples: {summary.samples}")
    print(f"Time span: {summary.start_time:.3f}s -> {summary.end_time:.3f}s ({summary.duration_s:.3f}s)")
    print(f"Average speed: {summary.average_speed:.2f} m/s")
    print(f"Average cars: {summary.average_total_cars:.2f} | Peak cars: {summary.peak_total_cars}")
    print(f"Average density: {summary.average_density_vpkm:.2f} veh/km | Peak density: {summary.peak_density_vpkm:.2f} veh/km")
    print(f"Average queue length: {summary.average_queue_m:.2f} m | Peak queue length: {summary.peak_queue_m:.2f} m")
    print(f"Queue time: {summary.queue_duration_s:.2f}s ({queue_share:.1f}% of run)")
    print(f"Longest queue episode: {summary.longest_queue_episode_s:.2f}s | Queue episodes: {summary.queue_episodes}")
    print(
        "Per-zone average density: "
        f"Z1 {summary.average_z1_density_vpkm:.2f} veh/km, "
        f"Z2 {summary.average_z2_density_vpkm:.2f} veh/km, "
        f"Z3 {summary.average_z3_density_vpkm:.2f} veh/km"
    )


def print_comparison(with_rec: ScenarioSummary, without_rec: ScenarioSummary) -> None:
    def delta(left: float, right: float) -> float:
        return left - right

    print("\n=== Comparison (with - without) ===")
    print(f"Average density delta: {delta(with_rec.average_density_vpkm, without_rec.average_density_vpkm):.2f} veh/km")
    print(f"Peak density delta: {delta(with_rec.peak_density_vpkm, without_rec.peak_density_vpkm):.2f} veh/km")
    print(f"Average queue length delta: {delta(with_rec.average_queue_m, without_rec.average_queue_m):.2f} m")
    print(f"Peak queue length delta: {delta(with_rec.peak_queue_m, without_rec.peak_queue_m):.2f} m")
    print(f"Queue time delta: {delta(with_rec.queue_duration_s, without_rec.queue_duration_s):.2f}s")
    print(f"Longest queue episode delta: {delta(with_rec.longest_queue_episode_s, without_rec.longest_queue_episode_s):.2f}s")
    print(f"Average speed delta: {delta(with_rec.average_speed, without_rec.average_speed):.2f} m/s")


def main() -> int:
    args = parse_args()

    with_samples = read_samples(args.with_recommendations)
    without_samples = read_samples(args.without_recommendations)

    with_summary = summarize("With recommendations", with_samples, args.road_length_m, args.queue_threshold_m)
    without_summary = summarize("Without recommendations", without_samples, args.road_length_m, args.queue_threshold_m)

    print_summary(with_summary)
    print_summary(without_summary)
    print_comparison(with_summary, without_summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())