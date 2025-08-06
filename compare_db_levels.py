#!/usr/bin/env python3
import numpy as np
import scipy.io.wavfile as wav
from scipy import signal

def analyze_db_at_time(audio_file, target_time, window_ms=50):
    """
    特定時刻の周波数別dB値を分析
    """
    sample_rate, audio_data = wav.read(audio_file)
    
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # 指定時刻の前後を取得
    window_sec = window_ms / 1000.0
    start_time = max(0, target_time - window_sec/2)
    end_time = target_time + window_sec/2
    
    start_sample = int(start_time * sample_rate)
    end_sample = int(end_time * sample_rate)
    segment = audio_data[start_sample:end_sample]
    
    # FFT分析
    fft = np.fft.rfft(segment)
    freqs = np.fft.rfftfreq(len(segment), 1/sample_rate)
    magnitude = np.abs(fft)
    magnitude_db = 20 * np.log10(magnitude + 1e-10)
    
    # 300-400Hz帯域の最大値を取得
    beep_band_mask = (freqs >= 300) & (freqs <= 400)
    beep_band_db = magnitude_db[beep_band_mask]
    beep_band_freqs = freqs[beep_band_mask]
    
    if len(beep_band_db) > 0:
        max_idx = np.argmax(beep_band_db)
        max_freq = beep_band_freqs[max_idx]
        max_db = beep_band_db[max_idx]
    else:
        max_freq = 0
        max_db = -100
    
    # 全体の最大値も取得
    overall_max_idx = np.argmax(magnitude_db)
    overall_max_freq = freqs[overall_max_idx]
    overall_max_db = magnitude_db[overall_max_idx]
    
    return max_freq, max_db, overall_max_freq, overall_max_db

# メイン処理
print("=" * 70)
print("3-4秒前後の各時間帯における300-400Hz帯域のdB値比較")
print("=" * 70)
print("\n時刻     | 300-400Hz帯域        | 全体最大値           | 判定")
print("-" * 70)

audio_file = "/tmp/audio_analysis.wav"

# 分析する時間範囲を拡大（0秒から20秒まで、0.5秒刻み）
time_points = []

# より細かく3-5秒を分析
for t in np.arange(3.0, 5.1, 0.2):
    time_points.append(t)

# その前後も含める
for t in [0.5, 1.0, 1.5, 2.0, 2.5, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0]:
    if t not in time_points:
        time_points.append(t)

time_points.sort()

results = []
for t in time_points:
    beep_freq, beep_db, overall_freq, overall_db = analyze_db_at_time(audio_file, t)
    results.append((t, beep_freq, beep_db, overall_freq, overall_db))

# 結果を表示
for t, beep_freq, beep_db, overall_freq, overall_db in results:
    # ビープ音の判定
    if beep_db > 100:
        judgment = "★★★ 強いビープ音"
    elif beep_db > 80:
        judgment = "★★ ビープ音あり"
    elif beep_db > 60:
        judgment = "★ 弱いビープ音"
    else:
        judgment = "ビープ音なし"
    
    # 3-5秒の範囲は強調表示
    if 3.0 <= t <= 5.0:
        print(f"{t:5.1f}秒 | {beep_freq:4.0f}Hz: {beep_db:6.1f}dB | {overall_freq:5.0f}Hz: {overall_db:6.1f}dB | {judgment} ◀")
    else:
        print(f"{t:5.1f}秒 | {beep_freq:4.0f}Hz: {beep_db:6.1f}dB | {overall_freq:5.0f}Hz: {overall_db:6.1f}dB | {judgment}")

print("-" * 70)

# 統計情報
beep_dbs = [db for _, _, db, _, _ in results]
beep_dbs_3_5 = [db for t, _, db, _, _ in results if 3.0 <= t <= 5.0]
beep_dbs_other = [db for t, _, db, _, _ in results if t < 3.0 or t > 5.0]

print("\n【統計情報】")
print(f"3-5秒の300-400Hz平均dB値: {np.mean(beep_dbs_3_5):.1f} dB")
print(f"その他の時間の300-400Hz平均dB値: {np.mean(beep_dbs_other):.1f} dB")
print(f"差: {np.mean(beep_dbs_3_5) - np.mean(beep_dbs_other):.1f} dB")

# より詳細な比較（前後2秒と4秒付近）
print("\n" + "=" * 70)
print("詳細比較: 4秒付近 vs その前後")
print("=" * 70)

comparison_times = [
    (2.0, "2秒（4秒の2秒前）"),
    (3.0, "3秒（4秒の1秒前）"),
    (3.5, "3.5秒"),
    (4.0, "★4秒（中心）"),
    (4.5, "4.5秒"),
    (5.0, "5秒（4秒の1秒後）"),
    (6.0, "6秒（4秒の2秒後）"),
]

print("\n時刻と説明                | 300-400Hz帯 | 全体最大  | 相対差(4秒比)")
print("-" * 70)

# 4秒のdB値を基準とする
ref_db = None
for t, desc in comparison_times:
    beep_freq, beep_db, overall_freq, overall_db = analyze_db_at_time(audio_file, t)
    
    if t == 4.0:
        ref_db = beep_db
        diff_str = "基準"
    else:
        diff = beep_db - ref_db if ref_db else 0
        diff_str = f"{diff:+6.1f}dB"
    
    print(f"{desc:25s} | {beep_db:7.1f}dB | {overall_db:7.1f}dB | {diff_str}")

print("-" * 70)

# 周波数の分布も確認
print("\n【300-400Hz帯域で検出された主要周波数の分布】")
freq_counts = {}
for t, beep_freq, beep_db, _, _ in results:
    if beep_db > 80 and 300 <= beep_freq <= 400:
        freq_bin = round(beep_freq / 10) * 10  # 10Hz単位にビニング
        if freq_bin not in freq_counts:
            freq_counts[freq_bin] = 0
        freq_counts[freq_bin] += 1

for freq in sorted(freq_counts.keys()):
    count = freq_counts[freq]
    bar = "█" * count
    print(f"{freq:3.0f}Hz: {bar} ({count}回)")