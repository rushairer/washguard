#!/usr/bin/env python3

import argparse
import csv
import json
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

import serial

LSB_PER_G_2G = 256000.0


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_args():
    parser = argparse.ArgumentParser(
        description="采集 WashGuard ADXL355 串口数据并保存为 CSV。"
    )
    parser.add_argument("--port", required=True, help="串口，例如 /dev/cu.usbmodem101")
    parser.add_argument("--baud", type=int, default=921600)
    parser.add_argument("--output", required=True, help="输出 CSV 文件路径")
    parser.add_argument("--experiment", default="WG-EXP-001")
    parser.add_argument("--machine", default="")
    parser.add_argument("--program", default="")
    parser.add_argument("--load", default="")
    parser.add_argument("--mount", default="")
    parser.add_argument("--orientation", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    meta_path = output.with_suffix(".meta.json")
    log_path = output.with_suffix(".device.log")

    stop_requested = False

    def request_stop(_signum, _frame):
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    metadata = {
        "experiment": args.experiment,
        "capture_started_at_utc": utc_now_iso(),
        "serial_port": args.port,
        "baud": args.baud,
        "machine": args.machine,
        "program": args.program,
        "load": args.load,
        "mount": args.mount,
        "orientation": args.orientation,
        "range_g": 2,
        "lsb_per_g": LSB_PER_G_2G,
        "firmware_wire_format": "D,timestamp_us,seq,x_raw,y_raw,z_raw",
    }

    sample_count = 0
    first_seq = None
    last_seq = None
    sequence_gap_count = 0
    first_sample_device_timestamp_us = None
    first_sample_host_utc = None
    last_sample_device_timestamp_us = None

    print(f"打开串口: {args.port} @ {args.baud}")
    print(f"CSV: {output}")
    print("按 Ctrl-C 结束采集。")

    try:
        with (
            serial.Serial(args.port, args.baud, timeout=1) as ser,
            output.open("w", newline="", encoding="utf-8") as csv_file,
            log_path.open("w", encoding="utf-8") as log_file,
        ):
            writer = csv.writer(csv_file)
            writer.writerow(
                [
                    "timestamp_us",
                    "seq",
                    "x_raw",
                    "y_raw",
                    "z_raw",
                    "x_g",
                    "y_g",
                    "z_g",
                ]
            )

            while not stop_requested:
                raw_line = ser.readline()
                if not raw_line:
                    continue

                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                if line.startswith("#"):
                    print(line)
                    log_file.write(line + "\n")
                    log_file.flush()
                    continue

                parts = line.split(",")
                if len(parts) != 6 or parts[0] != "D":
                    log_file.write(f"# unparsed,{line}\n")
                    continue

                try:
                    timestamp_us = int(parts[1])
                    seq = int(parts[2])
                    x_raw = int(parts[3])
                    y_raw = int(parts[4])
                    z_raw = int(parts[5])
                except ValueError:
                    log_file.write(f"# invalid,{line}\n")
                    continue

                if first_seq is None:
                    first_seq = seq
                    first_sample_device_timestamp_us = timestamp_us
                    first_sample_host_utc = utc_now_iso()

                if last_seq is not None and seq != last_seq + 1:
                    sequence_gap_count += max(0, seq - last_seq - 1)
                    print(
                        f"警告: seq 不连续，上一帧={last_seq} 当前={seq}",
                        file=sys.stderr,
                    )

                last_seq = seq
                last_sample_device_timestamp_us = timestamp_us

                writer.writerow(
                    [
                        timestamp_us,
                        seq,
                        x_raw,
                        y_raw,
                        z_raw,
                        x_raw / LSB_PER_G_2G,
                        y_raw / LSB_PER_G_2G,
                        z_raw / LSB_PER_G_2G,
                    ]
                )

                sample_count += 1
                if sample_count % 500 == 0:
                    csv_file.flush()
                    print(f"已采集 {sample_count} 样本", end="\r", flush=True)

    finally:
        metadata.update(
            {
                "capture_ended_at_utc": utc_now_iso(),
                "sample_count": sample_count,
                "first_seq": first_seq,
                "last_seq": last_seq,
                "sequence_gap_count": sequence_gap_count,
                "first_sample_device_timestamp_us": first_sample_device_timestamp_us,
                "first_sample_host_utc": first_sample_host_utc,
                "last_sample_device_timestamp_us": last_sample_device_timestamp_us,
            }
        )
        meta_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print()
        print(f"采集结束，共 {sample_count} 样本")
        print(f"序号缺口: {sequence_gap_count}")
        if first_sample_host_utc is not None:
            print(
                "时间锚点: "
                f"device={first_sample_device_timestamp_us} us "
                f"<-> host={first_sample_host_utc}"
            )
        print(f"元信息: {meta_path}")
        print(f"设备日志: {log_path}")


if __name__ == "__main__":
    main()
