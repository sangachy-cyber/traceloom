from pathlib import Path

from traceloom.domain.pathlet import Pathlet
from traceloom.domain.pattern import PatternParser
from traceloom.io import HoloWANTrace
from traceloom.models.state_gmm import StateGMM

import traceloom as tl


holowan_trace = HoloWANTrace.load("/Users/xiaotuanzi/Downloads/20260130_003915_UuL-playback.txt")

pathlets, stat = holowan_trace.get_filtered_extended_windows_with_stats(100, 10, 100)


stat_model = StateGMM(model_path=Path(__file__).parent.parent / "data" / "models" / "default" / "gmm_model.joblib")
input_data = []

for pathlet in pathlets:
    input_data.append(stat_model.predict(pathlet.body.observations).state_id)

print(input_data)
pattern = PatternParser.parse(input_data)
print(pattern.sequence)

cmd = 's2x2 -> s0x57 -> s2x1 -> s0x45 -> s2x1 -> s0x5 -> s2x1 -> s0x124 -> s2x1 -> s0x70 -> s2x1 -> s0x47 -> s2x1 -> s0x4'

pattern = PatternParser.parse('s2x2 -> s0x57 -> s2x1 -> s0x45 -> s2x1 -> s0x5 -> s2x1 -> s0x124 -> s2x1 -> s0x70 -> s2x1 -> s0x47 -> s2x1 -> s0x4')
# [('s2', 20), ('s0', 570), ('s2', 10), ('s0', 450), ('s2', 10), ('s0', 50), ('s2', 10), ('s0', 1240), ('s2', 10), ('s0', 700), ('s2', 10), ('s0', 470), ('s2', 10), ('s0', 2430)]
print(pattern.sequence)

# 20 + 570 + 10 + 450 + 10 + 50 + 10 + 1240 + 10 + 700 + 10 + 470 + 10 + 40

# s2x2 -> s0x57 -> s2x1 -> s0x45 -> s2x1 -> s0x5 -> s2x1 -> s0x124 -> s2x1 -> s0x70 -> s2x1 -> s0x47 -> s2x1 -> s0x4

# pattern = PatternParser.parse('s2x2 -> s0x57 -> s2x1 -> s0x45 -> s2x1 -> s0x5 -> s2x1 -> s0x124 -> s2x1 -> s0x70 -> s2x1 -> s0x47 -> s2x1 -> s0x4')

day = [cmd] * 48
print(' -> '.join(day))

# tl.reweave(input_file=' -> '.join(day), output="reweave_path.txt")