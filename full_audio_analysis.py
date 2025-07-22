#!/usr/bin/env python3
"""
完全な音声解析 - ビープ音やクリック音の検出
"""
import numpy as np
from scipy.io import wavfile
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.family'] = 'Hiragino Sans'

# 音声を読み込み
audio_path = "test_crossfade_audio.wav"
sample_rate, data = wavfile.read(audio_path)

# ステレオの場合は左チャンネルのみ使用
if len(data.shape) > 1:
    data = data[:, 0]

# 正規化
data = data / 32768.0

print(f"音声ファイル情報:")
print(f"  サンプリングレート: {sample_rate} Hz")
print(f"  音声長: {len(data) / sample_rate:.2f} 秒")
print(f"  最大振幅: {np.max(np.abs(data)):.3f}")

# 急激な変化を検出（より敏感に）
diff = np.diff(data)
sudden_changes = np.where(np.abs(diff) > 0.05)[0]  # 閾値を下げる

print(f"\n急激な変化（0.05以上）の検出: {len(sudden_changes)}個")

if len(sudden_changes) > 0:
    # 時間別に整理
    change_times = sudden_changes / sample_rate
    
    # 10秒間隔でグループ化
    print("\n時間帯別の急激な変化:")
    for start_time in range(0, int(len(data) / sample_rate), 10):
        end_time = start_time + 10
        count = np.sum((change_times >= start_time) & (change_times < end_time))
        if count > 0:
            print(f"  {start_time:02d}-{end_time:02d}秒: {count}個")
    
    # 最初の20個の詳細位置
    print(f"\n最初の20個の詳細位置:")
    for i, idx in enumerate(sudden_changes[:20]):
        time_pos = idx / sample_rate
        amplitude = abs(diff[idx])
        print(f"  {i+1:2d}. {time_pos:7.3f}秒 (振幅変化: {amplitude:.3f})")

# 周波数スペクトル分析でビープ音検出
print(f"\n周波数解析中...")
fft = np.fft.fft(data)
freqs = np.fft.fftfreq(len(data), 1/sample_rate)
magnitude = np.abs(fft)

# 高周波成分（ビープ音に相当）の検出
high_freq_threshold = 8000  # 8kHz以上
high_freq_indices = np.where(np.abs(freqs) > high_freq_threshold)[0]
high_freq_energy = np.sum(magnitude[high_freq_indices])
total_energy = np.sum(magnitude)
high_freq_ratio = high_freq_energy / total_energy

print(f"高周波成分（8kHz以上）の比率: {high_freq_ratio:.4f}")
if high_freq_ratio > 0.01:
    print("⚠️  高周波ノイズ（ビープ音など）が検出されました")
else:
    print("✅ 高周波ノイズは正常範囲内です")

# 無音区間の検出
silence_threshold = 0.001
silence_mask = np.abs(data) < silence_threshold
silence_segments = []

in_silence = False
silence_start = 0

for i, is_silent in enumerate(silence_mask):
    if is_silent and not in_silence:
        silence_start = i
        in_silence = True
    elif not is_silent and in_silence:
        silence_end = i
        duration = (silence_end - silence_start) / sample_rate
        if duration > 0.1:  # 100ms以上の無音のみ記録
            silence_segments.append((silence_start / sample_rate, silence_end / sample_rate, duration))
        in_silence = False

print(f"\n無音区間（100ms以上）: {len(silence_segments)}個")
for i, (start, end, duration) in enumerate(silence_segments[:10]):
    print(f"  {i+1:2d}. {start:7.3f}-{end:7.3f}秒 (長さ: {duration:.3f}秒)")

# RMS分析によるレベル変動チェック
window_size = int(0.1 * sample_rate)  # 100msウィンドウ
rms_values = []
rms_times = []

for i in range(0, len(data) - window_size, window_size // 2):
    window = data[i:i + window_size]
    rms_value = np.sqrt(np.mean(window ** 2))
    rms_values.append(rms_value)
    rms_times.append(i / sample_rate)

rms_values = np.array(rms_values)
rms_mean = np.mean(rms_values)
rms_std = np.std(rms_values)

print(f"\nRMS統計:")
print(f"  平均RMS: {rms_mean:.4f}")
print(f"  標準偏差: {rms_std:.4f}")
print(f"  変動係数: {rms_std/rms_mean:.3f}")

# 異常に高いRMSレベルを検出
high_rms_threshold = rms_mean + 3 * rms_std
high_rms_indices = np.where(rms_values > high_rms_threshold)[0]

if len(high_rms_indices) > 0:
    print(f"\n異常に高いRMSレベル: {len(high_rms_indices)}個")
    for idx in high_rms_indices[:10]:
        time_pos = rms_times[idx]
        rms_val = rms_values[idx]
        print(f"  - {time_pos:7.3f}秒: RMS={rms_val:.4f}")
else:
    print(f"\n✅ RMSレベルは正常範囲内です")

print(f"\n=== 総合評価 ===")
issues = 0
if len(sudden_changes) > len(data) / sample_rate * 2:  # 1秒あたり2個以上
    print("❌ 急激な変化が多すぎます")
    issues += 1
else:
    print("✅ 急激な変化は許容範囲内")

if high_freq_ratio > 0.01:
    print("❌ 高周波ノイズが検出されました")
    issues += 1
else:
    print("✅ 高周波ノイズなし")

if len(high_rms_indices) > 0:
    print("❌ 異常なレベル変動があります")
    issues += 1
else:
    print("✅ レベル変動正常")

if issues == 0:
    print("\n🎉 音声品質は良好です！")
else:
    print(f"\n⚠️  {issues}個の問題が検出されました")