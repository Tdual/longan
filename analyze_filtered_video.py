#!/usr/bin/env python3
"""
フィルタリング済み動画の音声分析
"""
import numpy as np
from scipy.io import wavfile
import matplotlib.pyplot as plt
import matplotlib
import subprocess
import os

matplotlib.rcParams['font.family'] = 'Hiragino Sans'

# 動画から音声を抽出
video_path = "noise_filtered_video_839228b7-f90a-4563-97eb-1449aea08062.mp4"
audio_path = "filtered_audio_analysis.wav"

print("フィルタリング済み動画から音声を抽出中...")
cmd = f"ffmpeg -i {video_path} -vn -acodec pcm_s16le -ar 44100 -ac 2 {audio_path} -y"
subprocess.run(cmd, shell=True, capture_output=True)

# 音声を読み込み
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

# 1.5秒から2.5秒の部分を詳細分析
start_idx = int(1.5 * sample_rate)
end_idx = int(2.5 * sample_rate)
segment = data[start_idx:end_idx]

# 時間軸（ミリ秒）
time_ms = np.linspace(1500, 2500, len(segment))

# 図を作成
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# 1. 波形
axes[0].plot(time_ms, segment, 'b-', linewidth=0.5)
axes[0].set_title('ノイズフィルタリング後: 2秒付近の音声波形', fontsize=14)
axes[0].set_xlabel('時間（ミリ秒）')
axes[0].set_ylabel('振幅')
axes[0].grid(True, alpha=0.3)
axes[0].axvline(x=2000, color='red', linestyle='--', alpha=0.7, label='2秒')
axes[0].legend()

# 2. スペクトログラム
from scipy import signal
f, t, Sxx = signal.spectrogram(segment, sample_rate, nperseg=1024, noverlap=512)
# 10000Hz以下の周波数のみ表示
freq_limit = 10000
freq_idx = np.where(f <= freq_limit)[0]
im = axes[1].pcolormesh(t * 1000 + 1500, f[freq_idx], 10 * np.log10(Sxx[freq_idx, :] + 1e-10), shading='gouraud', cmap='viridis')
axes[1].set_ylabel('周波数 (Hz)')
axes[1].set_xlabel('時間 (ミリ秒)')
axes[1].set_title('スペクトログラム（0-10000Hz）')
axes[1].axvline(x=2000, color='red', linestyle='--', alpha=0.7)
plt.colorbar(im, ax=axes[1], label='dB')

# 3. 差分（急激な変化）
diff = np.diff(segment)
diff_times = time_ms[:-1]
axes[2].plot(diff_times, diff, 'g-', linewidth=0.5)
axes[2].set_title('振幅の変化率', fontsize=14)
axes[2].set_xlabel('時間（ミリ秒）')
axes[2].set_ylabel('変化率')
axes[2].grid(True, alpha=0.3)
axes[2].axvline(x=2000, color='red', linestyle='--', alpha=0.7, label='2秒')
axes[2].axhline(y=0.1, color='orange', linestyle=':', alpha=0.7, label='問題レベル(0.1)')
axes[2].axhline(y=-0.1, color='orange', linestyle=':', alpha=0.7)
axes[2].legend()

plt.tight_layout()
plt.savefig('filtered_audio_2second_analysis.png', dpi=150, bbox_inches='tight')
print("フィルタリング後の分析結果を保存: filtered_audio_2second_analysis.png")

# 高周波成分の分析
fft = np.fft.fft(segment)
freqs = np.fft.fftfreq(len(segment), 1/sample_rate)
magnitude = np.abs(fft)

# 高周波成分（8kHz以上）の分析
high_freq_indices = np.where(np.abs(freqs) > 8000)[0]
high_freq_energy = np.sum(magnitude[high_freq_indices])
total_energy = np.sum(magnitude)
high_freq_ratio = high_freq_energy / total_energy

print(f"\n=== フィルタリング効果の評価 ===")
print(f"高周波成分（8kHz以上）の比率: {high_freq_ratio:.4f}")

# 急激な変化の検出
problem_threshold = 0.1
problem_indices = np.where(np.abs(diff) > problem_threshold)[0]

print(f"急激な変化（閾値: {problem_threshold}）: {len(problem_indices)}個")

if len(problem_indices) > 0:
    print("問題箇所:")
    for idx in problem_indices[:5]:  # 最初の5個
        time_pos = 1.5 + idx / sample_rate
        change_value = diff[idx]
        print(f"  - {time_pos:.3f}秒: 変化量 {change_value:.3f}")
else:
    print("✅ 問題となる急激な変化は検出されませんでした")

# 1928ms付近（元々問題があった場所）の確認
target_time = 1.928
target_idx = int((target_time - 1.5) * sample_rate)
if 0 <= target_idx < len(diff):
    target_change = diff[target_idx]
    print(f"\n1928ms付近の変化量: {target_change:.3f}")
    if abs(target_change) > 0.1:
        print("  ⚠️  まだ問題レベルです")
    else:
        print("  ✅ 改善されました")

# 総合評価
print(f"\n=== 総合評価 ===")
if high_freq_ratio < 0.02 and len(problem_indices) <= 5:
    print("🎉 ノイズフィルタリングが効果的に働いています！")
    print("   ビープ音問題は大幅に改善されました。")
elif high_freq_ratio < 0.05:
    print("✅ ノイズは改善されましたが、まだ軽微な問題があります。")
else:
    print("⚠️  さらなる改善が必要です。")

# クリーンアップ
os.remove(audio_path)