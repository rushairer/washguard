# WashGuard ADXL355 V0.1 CAD

这是 EVAL-ADXL355Z 第一版 3D 打印绝缘底座的参数化 CadQuery 源码。

## 当前尺寸

- EVAL-ADXL355Z PCB：20.32 × 20.32 mm
- PCB 厚度：1.575 mm
- 安装孔：Ø3.048 mm
- 安装孔中心距：15.24 × 15.24 mm
- 安装孔中心距相邻板边：2.54 mm
- 底座：38 × 32 × 2.4 mm
- PCB 支撑柱：Ø5.5 mm，高 2.5 mm
- PCB 固定：Ø1.7 mm M2 自攻导孔
- 压线片：10 × 14 × 3 mm
- 压线片 M2 孔距：10 mm

## 重要说明

安装孔中心位置来自 ADI 官方机械图几何读取。正式打印前，必须使用游标卡尺复核用户手中 EVAL-ADXL355Z 实物，尤其是四孔中心距、孔径以及排针/元件与底座的干涉。

V0.1 的目标是绝缘、刚性固定和应力释放，不代表最终量产结构。

## 生成

需要 Python + CadQuery：

```bash
python cad/generate_adxl355_base.py
```

生成 STEP 和 STL 到 `generated/`。
