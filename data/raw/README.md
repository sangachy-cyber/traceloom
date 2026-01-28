# Raw Data Organization

This directory contains raw network traces in text format.

## Directory Structure

```
raw/
├── weak/                  # Weak network raw traces (.txt)
│   ├── xiceng_20260120.txt
│   ├── basement_wifi_20260122.txt
│   └── ...
└── README.md              # This file
```

## File Format

Each .txt file contains raw network trace data with the following columns:

- `timestamp`: Timestamp of the sample
- `delay_up`: Upload delay in milliseconds
- `delay_down`: Download delay in milliseconds
- `loss_up`: Upload loss rate (0-1)
- `loss_down`: Download loss rate (0-1)
- `bandwidth_up`: Upload bandwidth in Mbps
- `bandwidth_down`: Download bandwidth in Mbps

## Data Source

The raw traces are collected from various network environments to capture different network conditions.
