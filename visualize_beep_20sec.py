#!/usr/bin/env python3
import numpy as np
import scipy.io.wavfile as wav
from scipy import signal
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

# 日本語フォント設定
try:
    import japanize_matplotlib
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "japanize-matplotlib"])
    import japanize_matplotlib

def analyze_time_series_extended(audio_file, duration=20):
    """
    時系列での周波数とdB値の変化を分析（20秒版）
    """
    sample_rate, audio_data = wav.read(audio_file)
    
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # 時間軸を作成（0.1秒間隔）
    time_points = np.arange(0, min(duration, len(audio_data)/sample_rate), 0.1)
    beep_freqs = []
    beep_dbs = []
    overall_dbs = []
    
    for t in time_points:
        # 各時刻でのFFT分析
        window_sec = 0.05  # 50ms窓
        start_sample = int((t - window_sec/2) * sample_rate)
        end_sample = int((t + window_sec/2) * sample_rate)
        
        if start_sample < 0:
            start_sample = 0
        if end_sample >= len(audio_data):
            end_sample = len(audio_data) - 1
            
        segment = audio_data[start_sample:end_sample]
        
        if len(segment) < 10:
            beep_freqs.append(0)
            beep_dbs.append(-100)
            overall_dbs.append(-100)
            continue
        
        # FFT
        fft = np.fft.rfft(segment)
        freqs = np.fft.rfftfreq(len(segment), 1/sample_rate)
        magnitude = np.abs(fft)
        magnitude_db = 20 * np.log10(magnitude + 1e-10)
        
        # ビープ音帯域（300-400Hz）の最大値
        beep_mask = (freqs >= 300) & (freqs <= 400)
        if np.any(beep_mask):
            beep_band_db = magnitude_db[beep_mask]
            beep_band_freqs = freqs[beep_mask]
            max_idx = np.argmax(beep_band_db)
            beep_freqs.append(beep_band_freqs[max_idx])
            beep_dbs.append(beep_band_db[max_idx])
        else:
            beep_freqs.append(300)
            beep_dbs.append(-100)
        
        # 全体の最大dB値
        overall_dbs.append(np.max(magnitude_db))
    
    return time_points, beep_freqs, beep_dbs, overall_dbs

def create_extended_visualization():
    """
    20秒間の視覚化グラフを作成
    """
    # データを取得（20秒）
    time_points, beep_freqs, beep_dbs, overall_dbs = analyze_time_series_extended("/tmp/audio_analysis.wav", 20)
    
    # 大きい図を作成（20秒用）
    fig, axes = plt.subplots(4, 1, figsize=(20, 16))
    fig.suptitle('0-20秒のビープ音詳細分析', fontsize=18)
    
    # 1. ビープ音帯域（300-400Hz）のdB値の時系列変化
    ax1 = axes[0]
    ax1.plot(time_points, beep_dbs, linewidth=2, color='red', label='300-400Hz帯域のdB値')
    ax1.axhline(y=100, color='orange', linestyle='--', alpha=0.7, label='強いビープ音閾値(100dB)')
    ax1.axhline(y=80, color='gold', linestyle='--', alpha=0.7, label='ビープ音閾値(80dB)')
    
    # 4秒付近を強調
    ax1.axvspan(3, 5, alpha=0.3, color='yellow', label='4秒付近')
    ax1.axvline(x=4, color='red', linestyle='-', alpha=0.8, linewidth=2)
    
    # 各秒にグリッド線を追加
    for i in range(0, 21):
        ax1.axvline(x=i, color='gray', linestyle=':', alpha=0.3)
    
    ax1.set_ylabel('dB値', fontsize=12)
    ax1.set_title('1. ビープ音帯域（300-400Hz）の音圧レベル', fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right')
    ax1.set_xlim(0, 20)
    ax1.set_ylim(0, 140)
    
    # 2. ビープ音の周波数の時系列変化
    ax2 = axes[1]
    ax2.plot(time_points, beep_freqs, linewidth=2, color='blue', marker='o', markersize=2)
    ax2.axhspan(300, 400, alpha=0.2, color='blue', label='ビープ音周波数帯域')
    ax2.axvspan(3, 5, alpha=0.3, color='yellow')
    ax2.axvline(x=4, color='red', linestyle='-', alpha=0.8, linewidth=2)
    
    for i in range(0, 21):
        ax2.axvline(x=i, color='gray', linestyle=':', alpha=0.3)
    
    ax2.set_ylabel('周波数 (Hz)', fontsize=12)
    ax2.set_title('2. ビープ音の主要周波数の変化', fontsize=14)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    ax2.set_xlim(0, 20)
    ax2.set_ylim(250, 450)
    
    # 3. 全体音圧 vs ビープ音帯域の比較
    ax3 = axes[2]
    ax3.plot(time_points, overall_dbs, linewidth=1.5, color='green', alpha=0.7, label='全体最大dB値')
    ax3.plot(time_points, beep_dbs, linewidth=2, color='red', label='ビープ音帯域dB値')
    ax3.axvspan(3, 5, alpha=0.3, color='yellow')
    ax3.axvline(x=4, color='red', linestyle='-', alpha=0.8, linewidth=2)
    
    for i in range(0, 21):
        ax3.axvline(x=i, color='gray', linestyle=':', alpha=0.3)
    
    ax3.set_ylabel('dB値', fontsize=12)
    ax3.set_title('3. 全体音圧とビープ音帯域の比較', fontsize=14)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='upper right')
    ax3.set_xlim(0, 20)
    ax3.set_ylim(0, 140)
    
    # 4. ビープ音強度のヒートマップ風表示
    ax4 = axes[3]
    
    # 1秒ごとの平均dB値を計算
    second_dbs = []
    for sec in range(20):
        mask = (np.array(time_points) >= sec) & (np.array(time_points) < sec + 1)
        if np.any(mask):
            sec_dbs = np.array(beep_dbs)[mask]
            valid_dbs = sec_dbs[sec_dbs > -50]
            if len(valid_dbs) > 0:
                avg_db = np.mean(valid_dbs)
            else:
                avg_db = 0
        else:
            avg_db = 0
        second_dbs.append(avg_db)
    
    # バーグラフで表示
    colors = []
    for db in second_dbs:
        if db > 110:
            colors.append('red')
        elif db > 100:
            colors.append('orange')
        elif db > 90:
            colors.append('yellow')
        elif db > 80:
            colors.append('lightgreen')
        else:
            colors.append('lightblue')
    
    bars = ax4.bar(range(20), second_dbs, color=colors, edgecolor='black', linewidth=1)
    
    # 4秒を強調
    bars[4].set_edgecolor('red')
    bars[4].set_linewidth(3)
    
    ax4.set_xlabel('時間 (秒)', fontsize=12)
    ax4.set_ylabel('平均dB値', fontsize=12)
    ax4.set_title('4. 各秒の平均ビープ音強度（赤=最強、橙=強、黄=中、緑=弱、青=極弱）', fontsize=14)
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.set_xlim(-0.5, 19.5)
    ax4.set_ylim(0, 130)
    
    # X軸の秒数表示
    ax4.set_xticks(range(20))
    ax4.set_xticklabels(range(20))
    
    plt.tight_layout()
    plt.savefig('/Users/tdual/Workspace/longan/beep_20sec_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 統計情報を出力
    print("=" * 70)
    print("0-20秒の詳細分析結果")
    print("=" * 70)
    
    # 各秒の詳細情報
    print("\n【秒ごとのビープ音強度】")
    print("秒  | 平均dB  | 判定")
    print("-" * 40)
    
    for sec, avg_db in enumerate(second_dbs):
        if avg_db > 110:
            judgment = "★★★ 非常に強い"
        elif avg_db > 100:
            judgment = "★★ 強い"
        elif avg_db > 90:
            judgment = "★ 中程度"
        elif avg_db > 80:
            judgment = "弱い"
        else:
            judgment = "極弱/なし"
        
        # 4秒を強調
        if sec == 4:
            print(f"{sec:2d}秒 | {avg_db:6.1f}dB | {judgment} ← ★注目★")
        else:
            print(f"{sec:2d}秒 | {avg_db:6.1f}dB | {judgment}")
    
    # 上位5秒を表示
    top_5 = sorted(enumerate(second_dbs), key=lambda x: x[1], reverse=True)[:5]
    print("\n【ビープ音が最も強い上位5秒】")
    print("順位 | 時間 | 平均dB値")
    print("-" * 30)
    for rank, (sec, db) in enumerate(top_5, 1):
        print(f"{rank}位  | {sec:2d}秒 | {db:6.1f}dB")
    
    return second_dbs

# メイン実行
print("20秒間の詳細分析グラフを作成中...")
second_dbs = create_extended_visualization()

print(f"\n✅ 20秒分析グラフを保存しました:")
print(f"📊 /Users/tdual/Workspace/longan/beep_20sec_analysis.png")

# 4秒の順位を確認
sorted_dbs = sorted(enumerate(second_dbs), key=lambda x: x[1], reverse=True)
rank_4sec = next(i for i, (sec, _) in enumerate(sorted_dbs, 1) if sec == 4)
print(f"\n🎯 4秒は全20秒中 第{rank_4sec}位 の強さです。")