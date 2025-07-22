import numpy as np
from scipy.io import wavfile
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Hiragino Sans'

# 音声を読み込み
sample_rate, data = wavfile.read("test_fixed_audio.wav")

# ステレオの場合は左チャンネルのみ使用
if len(data.shape) > 1:
    data = data[:, 0]

# 正規化
data = data / 32768.0

# 1.5秒から2.5秒の部分を抽出
start_idx = int(1.5 * sample_rate)
end_idx = int(2.5 * sample_rate)
segment = data[start_idx:end_idx]

# 時間軸（ミリ秒）
time_ms = np.linspace(1500, 2500, len(segment))

# 図を作成
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# 1. 波形
axes[0].plot(time_ms, segment, 'b-', linewidth=0.5)
axes[0].set_title('音声波形（1.5-2.5秒）', fontsize=14)
axes[0].set_xlabel('時間（ミリ秒）')
axes[0].set_ylabel('振幅')
axes[0].grid(True, alpha=0.3)

# 2秒の位置に線を引く
axes[0].axvline(x=2000, color='red', linestyle='--', alpha=0.7, label='2秒')
axes[0].legend()

# 2. スペクトログラム
from scipy import signal
f, t, Sxx = signal.spectrogram(segment, sample_rate, nperseg=1024, noverlap=512)
# 5000Hz以下の周波数のみ表示
freq_limit = 5000
freq_idx = np.where(f <= freq_limit)[0]
im = axes[1].pcolormesh(t * 1000 + 1500, f[freq_idx], 10 * np.log10(Sxx[freq_idx, :] + 1e-10), shading='gouraud', cmap='viridis')
axes[1].set_ylabel('周波数 (Hz)')
axes[1].set_xlabel('時間 (ミリ秒)')
axes[1].set_title('スペクトログラム（0-5000Hz）')
axes[1].axvline(x=2000, color='red', linestyle='--', alpha=0.7)
plt.colorbar(im, ax=axes[1], label='dB')

# 3. RMS（実効値）エネルギー
window_size = int(0.01 * sample_rate)  # 10msウィンドウ
rms = []
rms_times = []

for i in range(0, len(segment) - window_size, window_size // 2):
    window = segment[i:i + window_size]
    rms_value = np.sqrt(np.mean(window ** 2))
    rms.append(rms_value)
    rms_times.append(1500 + (i + window_size/2) / sample_rate * 1000)

axes[2].plot(rms_times, rms, 'g-', linewidth=1)
axes[2].set_title('RMSエネルギー（10msウィンドウ）', fontsize=14)
axes[2].set_xlabel('時間（ミリ秒）')
axes[2].set_ylabel('RMS')
axes[2].grid(True, alpha=0.3)
axes[2].axvline(x=2000, color='red', linestyle='--', alpha=0.7, label='2秒')

plt.tight_layout()
plt.savefig('2_seconds_analysis.png', dpi=150, bbox_inches='tight')
print("2秒付近の詳細分析を保存しました: 2_seconds_analysis.png")

# 音声ファイルのメタデータを確認
print("\n=== 音声ファイル情報 ===")
print(f"サンプリングレート: {sample_rate} Hz")
print(f"チャンネル数: {2 if len(data.shape) > 1 else 1}")
print(f"音声長: {len(data) / sample_rate:.2f} 秒")

# 2秒付近のゼロクロッシングレートを計算
zero_crossings = np.where(np.diff(np.sign(segment)))[0]
zcr = len(zero_crossings) / (1.0 / sample_rate)  # ゼロクロッシング/秒
print(f"\n1.5-2.5秒のゼロクロッシングレート: {zcr:.0f} Hz")

# 無音検出
silence_threshold = 0.001
silence_samples = np.where(np.abs(segment) < silence_threshold)[0]
silence_ratio = len(silence_samples) / len(segment) * 100
print(f"無音の割合: {silence_ratio:.1f}%")

# 急激な変化を検出
diff = np.diff(segment)
sudden_changes = np.where(np.abs(diff) > 0.1)[0]
if len(sudden_changes) > 0:
    print(f"\n急激な変化が検出された位置:")
    for idx in sudden_changes[:5]:  # 最初の5つ
        time_pos = 1500 + idx / sample_rate * 1000
        print(f"  - {time_pos:.1f} ms")