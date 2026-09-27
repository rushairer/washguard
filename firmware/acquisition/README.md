# WG-EXP-001 采集固件

本目录是 WashGuard 第一版振动数据采集固件。

## 环境

- XIAO ESP32S3
- PlatformIO
- Arduino Framework
- EVAL-ADXL355Z

## 编译

```bash
cd firmware/acquisition
pio run
```

## 烧录

```bash
pio run -t upload
```

## 串口观察

```bash
pio device monitor
```

串口看到以下内容才说明 ADXL355 基本通信正常：

```text
# adxl355_ids,AD,1D,ED
# config,odr_hz=500,range_g=2,spi_hz=1000000,lsb_per_g=256000
# ready
```

## 正式采集

主机端建议使用 Python 3.10+。

首次准备：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r tools/requirements.txt
```

macOS 可先查串口：

```bash
ls /dev/cu.*
```

执行 60 秒预检采集：

```bash
python3 tools/capture_serial.py \
  --port /dev/cu.usbmodem101 \
  --output data/raw/WG-PREFLIGHT-001/run-001.csv \
  --experiment WG-PREFLIGHT-001 \
  --mount "顶部靠后"
```

结束后运行：

```bash
python3 tools/validate_capture.py \
  data/raw/WG-PREFLIGHT-001/run-001.csv
```

只有预检通过后再开始完整 WG-EXP-001。

## 固件输出协议

数据行：

```text
D,timestamp_us,seq,x_raw,y_raw,z_raw
```

诊断行以 `#` 开头，例如：

```text
# adxl355_ids,AD,1D,ED
# config,odr_hz=500,range_g=2,spi_hz=1000000
# stats,missed_drdy=0,queue_drop=0
```

正式采集要求重点检查：

- `missed_drdy=0`
- `queue_drop=0`
- `seq` 连续
- 无明显削顶
- 估算 ODR 接近 500 Hz

采集脚本会同时保存：

- CSV 原始数据；
- `.meta.json` 实验元信息；
- `.device.log` 固件诊断日志；
- 第一帧设备时间戳与主机 UTC 的对齐锚点。
