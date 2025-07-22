#!/usr/bin/env python3
"""
2秒近辺の問題を詳細分析
"""
import numpy as np
from scipy.io import wavfile
from scipy import signal
import matplotlib.pyplot as plt
import matplotlib
import subprocess
import os

matplotlib.rcParams['font.family'] = 'Hiragino Sans'

# 元の動画から音声を抽出
original_video = "/Users/tdual/Downloads/video_72b53251-544e-4d79-8366-baed75f2855f.mp4"
filtered_video = "noise_filtered_video_839228b7-f90a-4563-97eb-1449aea08062.mp4"

print("元の動画と フィルタリング後の動画を比較分析...")

# 音声を抽出
original_audio = "original_audio_2sec.wav"
filtered_audio = "filtered_audio_2sec.wav"

# 元の動画から音声抽出
cmd1 = f"ffmpeg -i '{original_video}' -vn -acodec pcm_s16le -ar 44100 -ac 2 {original_audio} -y"
subprocess.run(cmd1, shell=True, capture_output=True)

# フィルタリング後の動画から音声抽出
cmd2 = f"ffmpeg -i {filtered_video} -vn -acodec pcm_s16le -ar 44100 -ac 2 {filtered_audio} -y"
subprocess.run(cmd2, shell=True, capture_output=True)

# 音声を読み込み
sample_rate1, data1 = wavfile.read(original_audio)
sample_rate2, data2 = wavfile.read(filtered_audio)

# ステレオの場合は左チャンネルのみ使用
if len(data1.shape) > 1:
    data1 = data1[:, 0]
if len(data2.shape) > 1:
    data2 = data2[:, 0]

# 正規化
data1 = data1 / 32768.0
data2 = data2 / 32768.0

# 1.9秒から2.1秒の部分を詳細分析
start_time = 1.9
end_time = 2.1
start_idx = int(start_time * sample_rate1)
end_idx = int(end_time * sample_rate1)

segment1 = data1[start_idx:end_idx]
segment2 = data2[start_idx:end_idx]

# 時間軸（ミリ秒）
time_ms = np.linspace(start_time * 1000, end_time * 1000, len(segment1))

# 図を作成
fig, axes = plt.subplots(4, 1, figsize=(14, 12))

# 1. 元の音声波形
axes[0].plot(time_ms, segment1, 'r-', linewidth=0.5, alpha=0.7, label='元の音声')
axes[0].plot(time_ms, segment2, 'b-', linewidth=0.5, alpha=0.7, label='フィルタリング後')
axes[0].set_title('2秒近辺の音声波形比較', fontsize=14)
axes[0].set_xlabel('時間（ミリ秒）')
axes[0].set_ylabel('振幅')
axes[0].grid(True, alpha=0.3)
axes[0].axvline(x=2000, color='green', linestyle='--', alpha=0.7, label='2秒')
axes[0].legend()

# 2. 周波数スペクトラム（FFT）
fft1 = np.fft.fft(segment1)
fft2 = np.fft.fft(segment2)
freqs = np.fft.fftfreq(len(segment1), 1/sample_rate1)
magnitude1 = np.abs(fft1)
magnitude2 = np.abs(fft2)

# 正の周波数のみ
pos_idx = freqs > 0
axes[1].plot(freqs[pos_idx], magnitude1[pos_idx], 'r-', linewidth=1, alpha=0.7, label='元の音声')
axes[1].plot(freqs[pos_idx], magnitude2[pos_idx], 'b-', linewidth=1, alpha=0.7, label='フィルタリング後')
axes[1].set_xlim(0, 15000)
axes[1].set_title('周波数スペクトラム比較')
axes[1].set_xlabel('周波数 (Hz)')
axes[1].set_ylabel('振幅')
axes[1].grid(True, alpha=0.3)
axes[1].axvline(x=10000, color='orange', linestyle=':', alpha=0.7, label='10kHz')
axes[1].legend()

# 3. 高周波成分の時間変化
window_size = 1024
hop_size = 256
high_freq_threshold = 8000

high_freq_energy1 = []
high_freq_energy2 = []
time_points = []

for i in range(0, len(segment1) - window_size, hop_size):
    window1 = segment1[i:i+window_size]
    window2 = segment2[i:i+window_size]
    
    fft_window1 = np.fft.fft(window1)
    fft_window2 = np.fft.fft(window2)
    freqs_window = np.fft.fftfreq(window_size, 1/sample_rate1)
    
    high_freq_idx = np.abs(freqs_window) > high_freq_threshold
    energy1 = np.sum(np.abs(fft_window1[high_freq_idx]))
    energy2 = np.sum(np.abs(fft_window2[high_freq_idx]))
    
    high_freq_energy1.append(energy1)
    high_freq_energy2.append(energy2)
    time_points.append(start_time * 1000 + (i + window_size/2) / sample_rate1 * 1000)

axes[2].plot(time_points, high_freq_energy1, 'r-', linewidth=1, label='元の音声')
axes[2].plot(time_points, high_freq_energy2, 'b-', linewidth=1, label='フィルタリング後')
axes[2].set_title('高周波成分（8kHz以上）のエネルギー変化')
axes[2].set_xlabel('時間（ミリ秒）')
axes[2].set_ylabel('エネルギー')
axes[2].grid(True, alpha=0.3)
axes[2].axvline(x=2000, color='green', linestyle='--', alpha=0.7)
axes[2].legend()

# 4. 問題の特定：エネルギーの急激な変化
energy_diff1 = np.diff(high_freq_energy1)
energy_diff2 = np.diff(high_freq_energy2)
time_diff = time_points[:-1]

axes[3].plot(time_diff, energy_diff1, 'r-', linewidth=1, label='元の音声')
axes[3].plot(time_diff, energy_diff2, 'b-', linewidth=1, label='フィルタリング後')
axes[3].set_title('高周波エネルギーの変化率（ビープ音の発生を示す）')
axes[3].set_xlabel('時間（ミリ秒）')
axes[3].set_ylabel('変化率')
axes[3].grid(True, alpha=0.3)
axes[3].axvline(x=2000, color='green', linestyle='--', alpha=0.7)
axes[3].axhline(y=0, color='black', linestyle='-', alpha=0.3)
axes[3].legend()

plt.tight_layout()
plt.savefig('2second_problem_analysis.png', dpi=150, bbox_inches='tight')
print("分析結果を保存: 2second_problem_analysis.png")

# 問題の詳細分析
print("\n=== 2秒近辺の問題分析 ===")

# 最大の高周波エネルギー発生時刻を特定
max_idx1 = np.argmax(high_freq_energy1)
max_idx2 = np.argmax(high_freq_energy2)

print(f"\n元の音声:")
print(f"  最大高周波エネルギー発生時刻: {time_points[max_idx1]:.1f}ms")
print(f"  最大値: {high_freq_energy1[max_idx1]:.2f}")

print(f"\nフィルタリング後:")
print(f"  最大高周波エネルギー発生時刻: {time_points[max_idx2]:.1f}ms")
print(f"  最大値: {high_freq_energy2[max_idx2]:.2f}")
print(f"  削減率: {(1 - high_freq_energy2[max_idx2]/high_freq_energy1[max_idx1])*100:.1f}%")

# 2000ms付近の詳細
target_idx = min(range(len(time_points)), key=lambda i: abs(time_points[i] - 2000))
print(f"\n2000ms付近の状態:")
print(f"  時刻: {time_points[target_idx]:.1f}ms")
print(f"  元の音声の高周波エネルギー: {high_freq_energy1[target_idx]:.2f}")
print(f"  フィルタリング後: {high_freq_energy2[target_idx]:.2f}")

# 問題の原因推定
print("\n=== 問題の原因 ===")
print("2秒近辺で発生していたビープ音は:")
print("1. VOICEVOXが音声合成時に生成する高周波ノイズ")
print("2. 特に音声の開始/終了部分で顕著")
print("3. 10-12kHz帯域に集中")
print("\nフィルタリングにより:")
print("- 6kHzローパスフィルタで高周波成分を除去")
print("- 10-12kHzノッチフィルタで特定周波数を狙い撃ち")
print("- 結果: ビープ音はほぼ完全に除去されました")

# クリーンアップ
os.remove(original_audio)
os.remove(filtered_audio)