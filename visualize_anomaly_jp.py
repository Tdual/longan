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
temp_audio_path = "/tmp/temp_audio_anomaly.wav"

# FFmpegで0.3-0.4秒の音声を抽出（異常が検出された範囲）
print("異常部分の音声を抽出中...")
cmd = [
    'ffmpeg', '-i', video_path, 
    '-ss', '1.3',   # 1.3秒から開始（動画全体の1秒目 + 0.3秒）
    '-t', '0.2',    # 0.2秒間
    '-vn',          # ビデオなし
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

# 時間軸（ミリ秒単位）
time_ms = np.linspace(0, len(data)/sample_rate*1000, len(data))

# 図を作成
fig, axes = plt.subplots(4, 1, figsize=(14, 12))

# 1. 波形全体
axes[0].plot(time_ms, data, 'b-', linewidth=0.5)
axes[0].set_title('音声波形（0.3-0.5秒の範囲）', fontsize=14)
axes[0].set_xlabel('時間（ミリ秒）')
axes[0].set_ylabel('振幅')
axes[0].grid(True, alpha=0.3)

# 異常検出のための差分計算
diff = np.diff(data)
diff_time_ms = time_ms[:-1]

# 閾値を設定（標準偏差の3倍）
threshold = np.std(diff) * 3

# 2. 差分信号と異常値
axes[1].plot(diff_time_ms, diff, 'g-', linewidth=0.5, alpha=0.7, label='差分信号')
axes[1].axhline(y=threshold, color='r', linestyle='--', alpha=0.5, label=f'閾値 (+{threshold:.4f})')
axes[1].axhline(y=-threshold, color='r', linestyle='--', alpha=0.5, label=f'閾値 (-{threshold:.4f})')

# 異常値をハイライト
anomaly_indices = np.where(np.abs(diff) > threshold)[0]
if anomaly_indices.size > 0:
    axes[1].scatter(diff_time_ms[anomaly_indices], diff[anomaly_indices], 
                   color='red', s=50, zorder=5, label=f'異常値 ({len(anomaly_indices)}個)')

axes[1].set_title('差分信号と異常値検出', fontsize=14)
axes[1].set_xlabel('時間（ミリ秒）')
axes[1].set_ylabel('差分値')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

# 3. 異常値の詳細（最初の5つ）
if anomaly_indices.size > 0:
    # 最初の異常値周辺を拡大表示
    first_anomaly_idx = anomaly_indices[0]
    window_size = int(0.005 * sample_rate)  # 5ms window
    
    start_idx = max(0, first_anomaly_idx - window_size)
    end_idx = min(len(data)-1, first_anomaly_idx + window_size)
    
    window_data = data[start_idx:end_idx]
    window_time = time_ms[start_idx:end_idx]
    
    axes[2].plot(window_time, window_data, 'b-', linewidth=1)
    axes[2].axvline(x=time_ms[first_anomaly_idx], color='red', linestyle='--', 
                   alpha=0.7, label='異常発生位置')
    axes[2].set_title(f'最初の異常値周辺の拡大図（±5ms）', fontsize=14)
    axes[2].set_xlabel('時間（ミリ秒）')
    axes[2].set_ylabel('振幅')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

# 4. 異常値の統計情報
if anomaly_indices.size > 0:
    # 異常値の時間分布をヒストグラム表示
    anomaly_times = diff_time_ms[anomaly_indices]
    
    axes[3].hist(anomaly_times, bins=20, alpha=0.7, color='orange', edgecolor='black')
    axes[3].set_title('異常値の時間分布', fontsize=14)
    axes[3].set_xlabel('時間（ミリ秒）')
    axes[3].set_ylabel('異常値の数')
    axes[3].grid(True, alpha=0.3)
    
    # 統計情報をテキストで追加
    stats_text = f'総異常値数: {len(anomaly_indices)}\n'
    stats_text += f'平均間隔: {np.mean(np.diff(anomaly_times)):.2f} ms\n' if len(anomaly_times) > 1 else ''
    stats_text += f'最大差分値: {np.max(np.abs(diff[anomaly_indices])):.4f}'
    
    axes[3].text(0.02, 0.95, stats_text, transform=axes[3].transAxes, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                verticalalignment='top', fontsize=10)

plt.tight_layout()

# 保存
output_path = "/Users/tdual/Workspace/longan/anomaly_visualization_jp.png"
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"異常値の可視化を保存しました: {output_path}")

# 詳細な異常値情報を出力
print("\n=== 異常値の詳細情報 ===")
if anomaly_indices.size > 0:
    print(f"検出された異常値: {len(anomaly_indices)}個")
    print(f"閾値: ±{threshold:.6f}")
    print("\n最初の10個の異常値:")
    for i, idx in enumerate(anomaly_indices[:10]):
        time_pos = diff_time_ms[idx]
        diff_value = diff[idx]
        print(f"  {i+1}. 時刻: {time_pos:.2f} ms, 差分値: {diff_value:.6f}")
    
    # 連続する異常値のクラスターを検出
    clusters = []
    if len(anomaly_indices) > 1:
        cluster_start = anomaly_indices[0]
        cluster_indices = [anomaly_indices[0]]
        
        for i in range(1, len(anomaly_indices)):
            if anomaly_indices[i] - anomaly_indices[i-1] <= 10:  # 10サンプル以内なら同じクラスター
                cluster_indices.append(anomaly_indices[i])
            else:
                if len(cluster_indices) > 3:  # 3個以上の異常値が集まっている場合
                    clusters.append((cluster_start, cluster_indices[-1], len(cluster_indices)))
                cluster_start = anomaly_indices[i]
                cluster_indices = [anomaly_indices[i]]
        
        # 最後のクラスターを追加
        if len(cluster_indices) > 3:
            clusters.append((cluster_start, cluster_indices[-1], len(cluster_indices)))
    
    if clusters:
        print(f"\n異常値のクラスター（3個以上が連続）:")
        for start_idx, end_idx, count in clusters[:5]:
            start_time = diff_time_ms[start_idx]
            end_time = diff_time_ms[end_idx]
            duration = end_time - start_time
            print(f"  - {start_time:.2f} - {end_time:.2f} ms (長さ: {duration:.2f} ms, 異常値数: {count})")

# クリーンアップ
os.remove(temp_audio_path)

print("\n異常値の可視化完了！")

# グラフを表示
plt.show()