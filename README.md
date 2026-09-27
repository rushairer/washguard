# WashGuard

WashGuard is a non-invasive washing-machine vibration sensing project.

The first prototype uses **EVAL-ADXL355Z + XIAO ESP32S3** to collect real vibration data from the washing-machine chassis. The project goal is not to memorize one machine's fixed wash program, but to build a sensing and inference stack that can gradually adapt to different machines, programs, loads, and mounting positions.

## Current phase

**Phase 0 / Prototype data acquisition**

The immediate objective is to prove that useful washing-machine operating states are observable from external vibration.

Do not optimize the enclosure, PCB, mobile app, cloud service, or ML model before this is demonstrated with real data.

### First milestone

Complete `WG-EXP-001`:

- EVAL-ADXL355Z connected to XIAO ESP32S3
- stable three-axis acquisition
- target initial sampling rate: 500 Hz
- initial range: +/-2 g, increase if clipping is observed
- retain raw XYZ samples and monotonic timestamps
- record one complete washing cycle
- record human ground-truth timestamps for visible/audible state changes

## Core engineering principles

1. **Raw data first.** Preserve raw XYZ samples; derived features must not replace source data.
2. **Do not overfit the first washing machine.** Initial data is an exploratory dataset, not the final training set.
3. **Prefer orientation-independent features.** Mounting direction and position must not be assumed fixed.
4. **Per-machine calibration is a first-class concept.** Each installation may build a Machine Profile.
5. **Recognize motion primitives before semantic wash stages.** Physical motion is more transferable than vendor-specific program names.
6. **Use a hybrid architecture.** DSP + normalization + calibration + rules/state machine first; ML is introduced only when the dataset justifies it.
7. **Completion detection has higher product priority than perfect stage naming.** The first useful product can reliably distinguish Idle / Running / Finished before it distinguishes every wash/rinse sub-stage.
8. **Every important conclusion should be reproducible.** Decisions should point back to experiments and recorded evidence.

## Planned signal architecture

```text
ADXL355 raw XYZ
      |
      v
Signal conditioning / gravity removal / filtering
      |
      +----> orientation-independent features
      |
      v
Machine calibration / Machine Profile
      |
      v
Feature vector
      |
      +----> Rules / thresholds
      |
      +----> ML classifier (later, if justified)
      |
      v
Motion primitive
      |
      v
Sequence / state model
      |
      v
User-facing state
Idle / Running / Washing / Spinning / Finished / Abnormal
```

## Documentation

- [Project decisions](docs/PROJECT_DECISIONS.md)
- [Experiment plan](docs/EXPERIMENTS.md)
- [Development plan](docs/DEVELOPMENT_PLAN.md)
- [Repository working rules](AGENTS.md)

## Immediate next action

Build the prototype acquisition path and run `WG-EXP-001`. The result should be a complete raw dataset plus ground-truth annotations from one real washing cycle.
