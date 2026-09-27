#!/usr/bin/env python3

import argparse
import csv
import json
import math
from pathlib import Path

EXPECTED_ODR_HZ = 500.0
MIN_ACCEPTABLE_ODR_HZ = 480.0
MAX_ACCEPTABLE_ODR_HZ = 520.0
RAW_CLIP_THRESHOLD = 520000


class AxisStats:
    def __init__(self):
        self.count = 0
        self.total = 0.0
        self.total_sq = 0.0
        self.minimum = None
        self.maximum = None
        self.clip_count = 0

    def add(self, value):
        self.count += 1
        self.total += value
        self.total_sq += value * value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        if abs(value) >= RAW_CLIP_THRESHOLD:
            self.clip_count += 1

    def as_dict(self):
        if self.count == 0:
            return {}
        mean = self.total / self.count
        variance = max(0.0, self.total_sq / self.count - mean * mean)
        return {
            "min_raw": self.minimum,
            "max_raw": self.maximum,
            "mean_raw": mean,
            "dynamic_rms_raw": math.sqrt(variance),
            "clip_count": self.clip_count,
        }


def parse_args():
    parser = argparse.ArgumentParser(
        description="检查 WashGuard 振动采集文件是否满足基本质量要求。"
    )
    parser.add_argument("csv_file", help="capture_serial.py 生成的 CSV")
    parser.add_argument(
        "--min-seconds",
        type=float,
        default=30.0,
        help="最低有效时长，默认 30 秒",
    )
    parser.add_argument("--json", dest="json_output", help="可选 JSON 报告路径")
    return parser.parse_args()


def main():
    args = parse_args()
    path = Path(args.csv_file)

    sample_count = 0
    first_ts = None
    last_ts = None
    previous_ts = None
    previous_seq = None
    sequence_gap_count = 0
    non_monotonic_timestamp_count = 0
    dt_min = None
    dt_max = None
    large_interval_count = 0

    axes = {
        "x": AxisStats(),
        "y": AxisStats(),
        "z": AxisStats(),
    }

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"timestamp_us", "seq", "x_raw", "y_raw", "z_raw"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"CSV 缺少字段: {', '.join(sorted(missing))}")

        for row in reader:
            ts = int(row["timestamp_us"])
            seq = int(row["seq"])
            x = int(row["x_raw"])
            y = int(row["y_raw"])
            z = int(row["z_raw"])

            if first_ts is None:
                first_ts = ts
            last_ts = ts

            if previous_ts is not None:
                dt = ts - previous_ts
                if dt <= 0:
                    non_monotonic_timestamp_count += 1
                else:
                    dt_min = dt if dt_min is None else min(dt_min, dt)
                    dt_max = dt if dt_max is None else max(dt_max, dt)
                    if dt > 3000:
                        large_interval_count += 1

            if previous_seq is not None and seq != previous_seq + 1:
                sequence_gap_count += max(0, seq - previous_seq - 1)

            previous_ts = ts
            previous_seq = seq

            axes["x"].add(x)
            axes["y"].add(y)
            axes["z"].add(z)
            sample_count += 1

    if sample_count < 2 or first_ts is None or last_ts is None:
        raise SystemExit("样本数量不足，无法检查。")

    duration_s = (last_ts - first_ts) / 1000000.0
    estimated_odr_hz = (sample_count - 1) / duration_s if duration_s > 0 else 0.0

    axis_report = {name: stats.as_dict() for name, stats in axes.items()}
    total_clip_count = sum(item["clip_count"] for item in axis_report.values())

    checks = {
        "duration_ok": duration_s >= args.min_seconds,
        "sample_rate_ok": MIN_ACCEPTABLE_ODR_HZ
        <= estimated_odr_hz
        <= MAX_ACCEPTABLE_ODR_HZ,
        "sequence_ok": sequence_gap_count == 0,
        "timestamps_ok": non_monotonic_timestamp_count == 0,
        "no_clipping": total_clip_count == 0,
    }
    passed = all(checks.values())

    report = {
        "file": str(path),
        "passed": passed,
        "sample_count": sample_count,
        "duration_s": duration_s,
        "estimated_odr_hz": estimated_odr_hz,
        "expected_odr_hz": EXPECTED_ODR_HZ,
        "sequence_gap_count": sequence_gap_count,
        "non_monotonic_timestamp_count": non_monotonic_timestamp_count,
        "dt_min_us": dt_min,
        "dt_max_us": dt_max,
        "interval_over_3000us_count": large_interval_count,
        "axes": axis_report,
        "checks": checks,
    }

    print("WashGuard 采集质量检查")
    print("=" * 36)
    print(f"样本数: {sample_count}")
    print(f"时长: {duration_s:.3f} s")
    print(f"估算 ODR: {estimated_odr_hz:.3f} Hz")
    print(f"seq 缺口: {sequence_gap_count}")
    print(f"非单调时间戳: {non_monotonic_timestamp_count}")
    print(f">3000 us 间隔次数: {large_interval_count}")
    print(f"削顶样本数: {total_clip_count}")

    for name in ("x", "y", "z"):
        item = axis_report[name]
        print(
            f"{name.upper()}: min={item['min_raw']} max={item['max_raw']} "
            f"mean={item['mean_raw']:.2f} "
            f"dynamic_rms={item['dynamic_rms_raw']:.2f}"
        )

    print("-" * 36)
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print("=" * 36)
    print("结论: " + ("通过，可以进入后续分析。" if passed else "未通过，先修复采集链路。"))

    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    raise SystemExit(0 if passed else 2)


if __name__ == "__main__":
    main()
