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

正式实验建议不要直接复制终端文本，而使用仓库根目录下的：

```bash
python3 tools/capture_serial.py ...
```

它会把固件的原始整数输出转换为包含原始值与 g 值的 CSV，同时生成实验元信息 JSON。

## 固件输出协议

数据行：

```text
D,timestamp_us,seq,x_raw,y_raw,z_raw
```

诊断行以 `#` 开头，例如：

```text
# adxl355_ids,AD,1D,ED
# config,odr_hz=500,range_g=2,spi_hz=5000000
# stats,missed_drdy=0,queue_drop=0
```

正式 WG-EXP-001 要求重点检查：

- `missed_drdy=0`
- `queue_drop=0`
- seq 连续
