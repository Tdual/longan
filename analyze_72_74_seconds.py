import subprocess
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from scipy.io import wavfile
import os

# 日本語フォントの設定
matplotlib.rcParams['font.family'] = 'Hiragino Sans'
matplotlib.rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']

# 動画ファイルのパス
video_path = os.path.expanduser("~/Downloads/video_72b53251-544e-4d79-8366-baed75f2855f.mp4")
temp_audio_path = "/tmp/temp_audio_72_74.wav"

# FFmpegで72-74秒の音声を抽出
print("72-74秒の音声を抽出中...")
cmd = [
    'ffmpeg', '-i', video_path, 
    '-ss', '72',     # 72秒から開始
    '-t', '2',       # 2秒間
    '-vn',           # ビデオなし
    '-acodec', 'pcm_s16le',  # 16bit PCM
    '-ar', '44100',  # サンプリングレート
    '-ac', '2',      # ステレオ
    '-y',            # 上書き
    temp_audio_path
]
subprocess.run(cmd, capture_output=True)

# WAVファイルを読み込み
print("音声データを分析中...")
sample_rate, data = wavfile.read(temp_audio_path)

# ステレオの場合は左チャンネルのみ使用
if len(data.shape) > 1:
    data = data[:, 0]

# 正規化
data = data / 32768.0  # 16bit audio

# 時間軸（秒単位）
time_s = np.linspace(0, len(data)/sample_rate, len(data))

# 差分計算
diff = np.diff(data)
diff_time_s = time_s[:-1]

# 閾値を設定（標準偏差の3倍）
threshold = np.std(diff) * 3

# 異常値を検出
anomaly_indices = np.where(np.abs(diff) > threshold)[0]

print(f"\n=== 72-74秒の分析結果 ===")
print(f"検出された異常値: {len(anomaly_indices)}個")
print(f"閾値: ±{threshold:.6f}")

# 異常値の時間分布を分析
if len(anomaly_indices) > 0:
    anomaly_times = diff_time_s[anomaly_indices]
    
    # 0.1秒ごとのビンで集計
    bins = np.arange(0, 2.1, 0.1)
    hist, bin_edges = np.histogram(anomaly_times, bins=bins)
    
    print("\n時間帯別の異常値数（0.1秒ごと）:")
    for i, count in enumerate(hist):
        if count > 0:
            start_time = bin_edges[i]
            end_time = bin_edges[i+1]
            print(f"  {start_time:.1f}-{end_time:.1f}秒: {count}個")
    
    # クラスター検出（連続する異常値）
    clusters = []
    if len(anomaly_indices) > 1:
        cluster_start = anomaly_indices[0]
        cluster_indices = [anomaly_indices[0]]
        
        for i in range(1, len(anomaly_indices)):
            if anomaly_indices[i] - anomaly_indices[i-1] <= 10:  # 10サンプル以内
                cluster_indices.append(anomaly_indices[i])
            else:
                if len(cluster_indices) > 3:  # 3個以上
                    clusters.append((cluster_start, cluster_indices[-1], len(cluster_indices)))
                cluster_start = anomaly_indices[i]
                cluster_indices = [anomaly_indices[i]]
        
        if len(cluster_indices) > 3:
            clusters.append((cluster_start, cluster_indices[-1], len(cluster_indices)))
    
    if clusters:
        print(f"\n異常値のクラスター（3個以上が連続）: {len(clusters)}個")
        for start_idx, end_idx, count in clusters[:5]:
            start_time = diff_time_s[start_idx]
            end_time = diff_time_s[end_idx]
            duration = end_time - start_time
            print(f"  - {start_time:.2f}秒: 長さ {duration*1000:.1f}ms, 異常値数 {count}")

# 最初の部分（1-2秒）との比較
print("\n=== 1-2秒の部分との比較 ===")
print("1-2秒の異常値: 162個（前回の分析結果）")
print(f"72-74秒の異常値: {len(anomaly_indices)}個")

# 可視化
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# 1. 波形全体
axes[0].plot(time_s, data, 'b-', linewidth=0.5)
axes[0].set_title('音声波形（72-74秒）', fontsize=14)
axes[0].set_xlabel('時間（秒）')
axes[0].set_ylabel('振幅')
axes[0].grid(True, alpha=0.3)

# 2. 差分信号と異常値
axes[1].plot(diff_time_s, diff, 'g-', linewidth=0.5, alpha=0.7, label='差分信号')
axes[1].axhline(y=threshold, color='r', linestyle='--', alpha=0.5, label=f'閾値 (+{threshold:.4f})')
axes[1].axhline(y=-threshold, color='r', linestyle='--', alpha=0.5, label=f'閾値 (-{threshold:.4f})')

if anomaly_indices.size > 0:
    axes[1].scatter(diff_time_s[anomaly_indices], diff[anomaly_indices], 
                   color='red', s=20, zorder=5, label=f'異常値 ({len(anomaly_indices)}個)')

axes[1].set_title('差分信号と異常値検出', fontsize=14)
axes[1].set_xlabel('時間（秒）')
axes[1].set_ylabel('差分値')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

# 3. 異常値の時間分布
if anomaly_indices.size > 0:
    axes[2].hist(anomaly_times, bins=20, alpha=0.7, color='orange', edgecolor='black')
    axes[2].set_title('異常値の時間分布', fontsize=14)
    axes[2].set_xlabel('時間（秒）')
    axes[2].set_ylabel('異常値の数')
    axes[2].grid(True, alpha=0.3)

plt.tight_layout()

# 保存
output_path = "/Users/tdual/Workspace/longan/anomaly_72_74_seconds.png"
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n可視化を保存しました: {output_path}")

# クリーンアップ
os.remove(temp_audio_path)