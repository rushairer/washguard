# WashGuard 实验数据目录

## 原则

原始振动数据体积可能很大，当前**不直接提交大体积 CSV 到 Git 历史**。

推荐本地结构：

```text
data/
└── raw/
    └── WG-EXP-001/
        ├── run-001.csv
        ├── run-001.meta.json
        ├── run-001.device.log
        └── run-001-ground-truth.csv
```

仓库保留：

- 数据格式；
- 实验元信息；
- 分析脚本；
- 小型示例数据；
- 可复现的结果摘要。

后续如果需要集中保存完整数据集，再明确采用 Git LFS、对象存储或其他数据仓库方案。

## Ground Truth 模板

```csv
timestamp_local,elapsed_s,state,note
2026-09-27T10:00:00+08:00,0,start,按下启动键
2026-09-27T10:03:12+08:00,192,wash,观察到明显低速往复
2026-09-27T10:31:40+08:00,1900,spin,进入高速脱水
2026-09-27T10:39:08+08:00,2348,done,机器提示完成
```
