# WG-EXP-001 原型硬件与接线

## 1. 目标

使用 **EVAL-ADXL355Z + XIAO ESP32S3** 建立第一版稳定采集链路，连续记录 500 Hz 三轴振动数据，为 WG-EXP-001 提供真实原始数据。

## 2. 官方资料确认

ADXL355：

- 支持 SPI / I²C；
- SPI 使用 Mode 0：CPOL=0、CPHA=0；
- SPI 时钟范围 100 kHz～10 MHz；
- 20 bit 三轴数字输出；
- ±2 g / ±4 g / ±8 g 可配置；
- ±2 g 典型灵敏度：256000 LSB/g；
- `FILTER(0x28)=0x03` 时，ODR=500 Hz、LPF=125 Hz；
- 数据寄存器从 `XDATA3(0x08)` 连续排列到 `ZDATA1(0x10)`；
- DRDY 在新加速度数据可用时拉高，读取 X/Y/Z 数据后清除。

XIAO ESP32S3：

- D8 / GPIO7：SPI SCK
- D9 / GPIO8：SPI MISO
- D10 / GPIO9：SPI MOSI
- D3 / GPIO4：本项目用作 CS
- D2 / GPIO3：本项目用作 DRDY

## 3. EVAL-ADXL355Z 接线

### 电源与 DRDY

| EVAL-ADXL355Z | 功能 | XIAO ESP32S3 |
| --- | --- | --- |
| P1-1 | VDD / VSUPPLY | 3V3 |
| P1-3 | VDDIO | 3V3 |
| P1-5 | VSS / GND | GND |
| P1-6 | DRDY | D2 / GPIO3 |

### SPI

| EVAL-ADXL355Z | 功能 | XIAO ESP32S3 |
| --- | --- | --- |
| P2-2 | CS/SCL | D3 / GPIO4 |
| P2-4 | SCLK/VSSIO | D8 / GPIO7 |
| P2-5 | MISO/ASEL | D9 / GPIO8 |
| P2-6 | MOSI/SDA | D10 / GPIO9 |

### 不要连接

EVAL-ADXL355Z 的：

- P2-1：V1P8ANA
- P2-3：V1P8DIG

在当前使用板载 LDO 的方案里不需要接到 XIAO 的 3.3 V。

> EVAL-ADXL355Z 不具备反接保护。首次上电前必须再次核对 3V3、GND 和 P1/P2 针脚方向。

## 4. 第一版采集参数

| 参数 | 值 |
| --- | --- |
| ODR | 500 Hz |
| LPF | 125 Hz |
| HPF | 关闭 |
| 量程 | ±2 g |
| SPI | 5 MHz / Mode 0 |
| 数据 | 20 bit X/Y/Z |
| 时间戳 | ESP32-S3 单调微秒时间 |
| 主机输出 | USB Serial |
| 目标格式 | CSV |

选择 5 MHz SPI 的原因是它位于 ADXL355 官方允许范围内，并且能够在 2 ms 的 500 Hz 采样周期内非常快地完成 9 字节 X/Y/Z 连续读取。

## 5. 为什么使用 DRDY，而不是固定 delay(2)

WG-EXP-001 必须尽量忠实记录传感器真正产生的新样本。

使用：

```text
ADXL355 500 Hz ODR
       ↓
     DRDY ↑
       ↓
ESP32 立即连续读取 0x08～0x10
       ↓
      Queue
       ↓
USB Serial → Mac → CSV
```

这样采样时刻由传感器数据就绪事件驱动，而不是依赖 MCU 的软件延时。

如果采集任务一次收到多个尚未处理的 DRDY 通知，固件会累计 `missed_drdy`；如果输出队列满，则累计 `queue_drop`。WG-EXP-001 正式数据要求这两个值最好始终为 0。

## 6. 上电自检

固件启动后会读取：

- `DEVID_AD(0x00)`，预期 `0xAD`
- `DEVID_MST(0x01)`，预期 `0x1D`
- `PARTID(0x02)`，预期 `0xED`

任一不匹配时，不进入正式采集。

## 7. 安装建议

WG-EXP-001 第一次实验：

1. 先选择洗衣机顶部靠后、相对刚性的机身位置；
2. 固定 EVAL-ADXL355Z，整个周期不能移动；
3. 拍照记录板子方向；
4. 线缆固定在机身附近，避免线缆摆动直接拉扯传感器；
5. XIAO ESP32S3 可与传感器保持短线连接，但不要让开发板悬空撞击机身；
6. USB 线尽量固定，避免自身运动成为振动干扰源。

## 8. 参考资料

- Analog Devices ADXL354/ADXL355 Data Sheet Rev. D  
  https://www.analog.com/media/en/technical-documentation/data-sheets/adxl354_adxl355.pdf
- Analog Devices EVAL-ADXL354/EVAL-ADXL355 User Guide UG-1030  
  https://www.analog.com/media/en/technical-documentation/user-guides/eval-adxl354-355-ug-1030.pdf
- Seeed Studio XIAO ESP32S3 Pin Multiplexing  
  https://wiki.seeedstudio.com/xiao_esp32s3_pin_multiplexing/
