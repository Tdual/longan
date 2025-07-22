#!/usr/bin/env python3
import numpy as np
from scipy.io import wavfile
import matplotlib.pyplot as plt
import matplotlib
import subprocess
import os

matplotlib.rcParams['font.family'] = 'Hiragino Sans'

# 動画から音声を抽出
video_path = "test_crossfade_video.mp4"
audio_path = "test_crossfade_audio.wav"

print("動画から音声を抽出中...")
cmd = f"ffmpeg -i {video_path} -vn -acodec pcm_s16le -ar 44100 -ac 2 {audio_path} -y"
subprocess.run(cmd, shell=True, capture_output=True)

# 音声を読み込み
sample_rate, data = wavfile.read(audio_path)

# ステレオの場合は左チャンネルのみ使用
if len(data.shape) > 1:
    data = data[:, 0]

# 正規化
data = data / 32768.0

# 最初の10秒を分析
end_idx = min(len(data), int(10 * sample_rate))
segment = data[:end_idx]

# 図を作成
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# 1. 波形
time_s = np.linspace(0, len(segment)/sample_rate, len(segment))
axes[0].plot(time_s, segment, 'b-', linewidth=0.5)
axes[0].set_title('クロスフェード適用後の音声波形（最初の10秒）', fontsize=14)
axes[0].set_xlabel('時間（秒）')
axes[0].set_ylabel('振幅')
axes[0].grid(True, alpha=0.3)

# 2秒の位置に線を引く
axes[0].axvline(x=2, color='red', linestyle='--', alpha=0.7, label='2秒')
axes[0].legend()

# 2. スペクトログラム
from scipy import signal
f, t, Sxx = signal.spectrogram(segment, sample_rate, nperseg=1024, noverlap=512)
freq_limit = 5000
freq_idx = np.where(f <= freq_limit)[0]
im = axes[1].pcolormesh(t, f[freq_idx], 10 * np.log10(Sxx[freq_idx, :] + 1e-10), shading='gouraud', cmap='viridis')
axes[1].set_ylabel('周波数 (Hz)')
axes[1].set_xlabel('時間 (秒)')
axes[1].set_title('スペクトログラム（0-5000Hz）')
axes[1].axvline(x=2, color='red', linestyle='--', alpha=0.7)
plt.colorbar(im, ax=axes[1], label='dB')

# 3. RMSエネルギー
window_size = int(0.01 * sample_rate)  # 10msウィンドウ
rms = []
rms_times = []

for i in range(0, len(segment) - window_size, window_size // 2):
    window = segment[i:i + window_size]
    rms_value = np.sqrt(np.mean(window ** 2))
    rms.append(rms_value)
    rms_times.append(i / sample_rate)

axes[2].plot(rms_times, rms, 'g-', linewidth=1)
axes[2].set_title('RMSエネルギー（10msウィンドウ）', fontsize=14)
axes[2].set_xlabel('時間（秒）')
axes[2].set_ylabel('RMS')
axes[2].grid(True, alpha=0.3)
axes[2].axvline(x=2, color='red', linestyle='--', alpha=0.7, label='2秒')

plt.tight_layout()
plt.savefig('crossfade_result_analysis.png', dpi=150, bbox_inches='tight')
print("分析結果を保存しました: crossfade_result_analysis.png")

# 急激な変化を検出
diff = np.diff(segment)
sudden_changes = np.where(np.abs(diff) > 0.1)[0]
if len(sudden_changes) > 0:
    print(f"\n急激な変化が検出された位置:")
    for idx in sudden_changes[:10]:  # 最初の10個
        time_pos = idx / sample_rate
        print(f"  - {time_pos:.3f} 秒")
else:
    print("\n急激な変化は検出されませんでした")

# 2秒付近を詳細分析
start_idx = int(1.5 * sample_rate)
end_idx = int(2.5 * sample_rate)
segment_2s = segment[start_idx:end_idx]

# 2秒付近の突然の変化
diff_2s = np.diff(segment_2s)
sudden_changes_2s = np.where(np.abs(diff_2s) > 0.05)[0]
if len(sudden_changes_2s) > 0:
    print(f"\n2秒付近（1.5-2.5秒）の変化:")
    for idx in sudden_changes_2s[:5]:
        time_pos = 1.5 + idx / sample_rate
        print(f"  - {time_pos:.3f} 秒")

# クリーンアップ
os.remove(audio_path)