import numpy as np
from scipy.io import wavfile
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Hiragino Sans'

# 修正後の音声を読み込み
sample_rate, data = wavfile.read("test_fixed_audio.wav")

# ステレオの場合は左チャンネルのみ使用
if len(data.shape) > 1:
    data = data[:, 0]

# 正規化
data = data / 32768.0

# 時間軸（秒）
time_s = np.linspace(0, len(data)/sample_rate, len(data))

# 差分計算
diff = np.diff(data)
diff_time_s = time_s[:-1]

# 閾値を設定
threshold = np.std(diff) * 3

# 異常値を検出
anomaly_indices = np.where(np.abs(diff) > threshold)[0]

print(f"=== 修正後の音声分析結果 ===")
print(f"音声長: {len(data)/sample_rate:.2f}秒")
print(f"検出された異常値: {len(anomaly_indices)}個")
print(f"閾値: ±{threshold:.6f}")

# 時間帯別の異常値数（1秒ごと）
for i in range(10):
    start_idx = int(i * sample_rate)
    end_idx = int((i + 1) * sample_rate)
    anomalies_in_second = np.sum((anomaly_indices >= start_idx) & (anomaly_indices < end_idx))
    print(f"  {i}-{i+1}秒: {anomalies_in_second}個")

# 可視化
fig, axes = plt.subplots(2, 1, figsize=(14, 8))

# 波形
axes[0].plot(time_s, data, 'b-', linewidth=0.5)
axes[0].set_title('修正後の音声波形（最初の10秒）', fontsize=14)
axes[0].set_xlabel('時間（秒）')
axes[0].set_ylabel('振幅')
axes[0].grid(True, alpha=0.3)

# 差分信号と異常値
axes[1].plot(diff_time_s, diff, 'g-', linewidth=0.5, alpha=0.7)
axes[1].axhline(y=threshold, color='r', linestyle='--', alpha=0.5)
axes[1].axhline(y=-threshold, color='r', linestyle='--', alpha=0.5)

if anomaly_indices.size > 0:
    axes[1].scatter(diff_time_s[anomaly_indices], diff[anomaly_indices], 
                   color='red', s=20, zorder=5, label=f'異常値 ({len(anomaly_indices)}個)')

axes[1].set_title('差分信号と異常値検出', fontsize=14)
axes[1].set_xlabel('時間（秒）')
axes[1].set_ylabel('差分値')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('fixed_audio_analysis.png', dpi=150, bbox_inches='tight')
print(f"\n可視化を保存しました: fixed_audio_analysis.png")