#!/usr/bin/env python3
import numpy as np
import scipy.io.wavfile as wav
from scipy import signal
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # バックエンドを設定

# 日本語フォント設定
try:
    import japanize_matplotlib
    print("japanize_matplotlibを使用")
except ImportError:
    print("japanize_matplotlibがインストールされていません。インストールします...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "japanize-matplotlib"])
    import japanize_matplotlib
    print("japanize_matplotlibをインストール完了")

# フォント設定をさらに強化
plt.rcParams['font.family'] = ['DejaVu Sans', 'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']

def analyze_time_series(audio_file, duration=15):
    """
    時系列での周波数とdB値の変化を分析
    """
    sample_rate, audio_data = wav.read(audio_file)
    
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # 時間軸を作成（0.1秒間隔）
    time_points = np.arange(0, duration, 0.1)
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
        
        if len(segment) < 10:  # セグメントが短すぎる場合
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

def create_visualization():
    """
    視覚化グラフを作成
    """
    # データを取得
    time_points, beep_freqs, beep_dbs, overall_dbs = analyze_time_series("/tmp/audio_analysis.wav", 10)
    
    # 図を作成（3つのサブプロット）
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12))
    fig.suptitle('4秒付近のビープ音異常検出 - 視覚的分析', fontsize=16)
    
    # 1. ビープ音帯域（300-400Hz）のdB値の時系列変化
    ax1.plot(time_points, beep_dbs, linewidth=2, color='red', label='300-400Hz帯域のdB値')
    ax1.axhline(y=100, color='orange', linestyle='--', alpha=0.7, label='強いビープ音閾値(100dB)')
    ax1.axhline(y=80, color='gold', linestyle='--', alpha=0.7, label='ビープ音閾値(80dB)')
    
    # 4秒付近を強調
    ax1.axvspan(3, 5, alpha=0.2, color='red', label='4秒付近（異常範囲）')
    ax1.axvline(x=4, color='red', linestyle='-', alpha=0.8, linewidth=3, label='4秒（中心）')
    
    ax1.set_ylabel('dB値')
    ax1.set_title('1. ビープ音帯域（300-400Hz）の音圧レベル')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_ylim(0, 140)
    
    # 2. ビープ音の周波数の時系列変化
    ax2.plot(time_points, beep_freqs, linewidth=2, color='blue', marker='o', markersize=3)
    ax2.axhspan(300, 400, alpha=0.2, color='blue', label='ビープ音周波数帯域')
    ax2.axvspan(3, 5, alpha=0.2, color='red', label='4秒付近（異常範囲）')
    ax2.axvline(x=4, color='red', linestyle='-', alpha=0.8, linewidth=3)
    
    ax2.set_ylabel('周波数 (Hz)')
    ax2.set_title('2. ビープ音の主要周波数の変化')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_ylim(250, 450)
    
    # 3. 全体音圧 vs ビープ音帯域の比較
    ax3.plot(time_points, overall_dbs, linewidth=2, color='green', alpha=0.7, label='全体最大dB値')
    ax3.plot(time_points, beep_dbs, linewidth=2, color='red', label='ビープ音帯域dB値')
    ax3.axvspan(3, 5, alpha=0.2, color='red', label='4秒付近（異常範囲）')
    ax3.axvline(x=4, color='red', linestyle='-', alpha=0.8, linewidth=3)
    
    ax3.set_xlabel('時間 (秒)')
    ax3.set_ylabel('dB値')
    ax3.set_title('3. 全体音圧とビープ音帯域の比較')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    ax3.set_ylim(0, 140)
    
    plt.tight_layout()
    plt.savefig('/Users/tdual/Workspace/longan/beep_analysis_jp.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4秒付近の詳細グラフ
    fig2, (ax4, ax5) = plt.subplots(2, 1, figsize=(15, 8))
    fig2.suptitle('4秒付近の詳細分析（3-5秒）', fontsize=16)
    
    # 3-5秒の範囲でフィルタリング
    mask_3_5 = (np.array(time_points) >= 3) & (np.array(time_points) <= 5)
    time_3_5 = np.array(time_points)[mask_3_5]
    beep_dbs_3_5 = np.array(beep_dbs)[mask_3_5]
    beep_freqs_3_5 = np.array(beep_freqs)[mask_3_5]
    
    # 4. 3-5秒の詳細dB値
    ax4.plot(time_3_5, beep_dbs_3_5, linewidth=3, color='red', marker='o', markersize=5)
    ax4.axhline(y=100, color='orange', linestyle='--', alpha=0.7, label='強いビープ音閾値')
    ax4.axvline(x=4, color='red', linestyle='-', alpha=0.8, linewidth=3, label='4秒')
    
    # 最高値と最低値を表示
    max_db = np.max(beep_dbs_3_5)
    min_db = np.min(beep_dbs_3_5)
    max_time = time_3_5[np.argmax(beep_dbs_3_5)]
    min_time = time_3_5[np.argmin(beep_dbs_3_5)]
    
    ax4.annotate(f'最高: {max_db:.1f}dB', xy=(max_time, max_db), xytext=(max_time+0.2, max_db+5),
                arrowprops=dict(arrowstyle='->', color='red'))
    ax4.annotate(f'最低: {min_db:.1f}dB', xy=(min_time, min_db), xytext=(min_time+0.2, min_db-5),
                arrowprops=dict(arrowstyle='->', color='blue'))
    
    ax4.set_ylabel('dB値')
    ax4.set_title('4. 3-5秒の詳細dB値変化')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    # 5. 3-5秒の詳細周波数
    ax5.plot(time_3_5, beep_freqs_3_5, linewidth=3, color='blue', marker='s', markersize=5)
    ax5.axhline(y=350, color='purple', linestyle='--', alpha=0.7, label='ビープ音中心周波数')
    ax5.axvline(x=4, color='red', linestyle='-', alpha=0.8, linewidth=3, label='4秒')
    
    ax5.set_xlabel('時間 (秒)')
    ax5.set_ylabel('周波数 (Hz)')
    ax5.set_title('5. 3-5秒の詳細周波数変化')
    ax5.grid(True, alpha=0.3)
    ax5.legend()
    
    plt.tight_layout()
    plt.savefig('/Users/tdual/Workspace/longan/beep_detail_4sec_jp.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 統計情報を出力
    print("=" * 60)
    print("視覚的分析結果")
    print("=" * 60)
    
    # 4秒付近とその他の比較
    mask_4sec = (np.array(time_points) >= 3.5) & (np.array(time_points) <= 4.5)
    mask_others = (np.array(time_points) < 2) | (np.array(time_points) > 6)
    
    db_4sec = np.array(beep_dbs)[mask_4sec]
    db_others = np.array(beep_dbs)[mask_others]
    
    avg_4sec = np.mean(db_4sec[db_4sec > -50])  # 有効な値のみ
    avg_others = np.mean(db_others[db_others > -50])  # 有効な値のみ
    
    print(f"4秒付近(3.5-4.5秒)の平均dB値: {avg_4sec:.1f} dB")
    print(f"その他の時間の平均dB値: {avg_others:.1f} dB")
    print(f"差: {avg_4sec - avg_others:.1f} dB")
    
    # 4秒での具体的な値
    idx_4sec = np.argmin(np.abs(np.array(time_points) - 4.0))
    print(f"\n4.0秒での測定値:")
    print(f"  周波数: {beep_freqs[idx_4sec]:.0f} Hz")
    print(f"  dB値: {beep_dbs[idx_4sec]:.1f} dB")
    
    return avg_4sec, avg_others

# メイン実行
print("日本語対応の視覚的分析グラフを作成中...")
avg_4sec, avg_others = create_visualization()

print(f"\n✅ 日本語対応グラフを保存しました:")
print(f"📊 全体分析: /Users/tdual/Workspace/longan/beep_analysis_jp.png")
print(f"🔍 4秒詳細: /Users/tdual/Workspace/longan/beep_detail_4sec_jp.png")

print(f"\n🎯 結論: 4秒付近は他の時間帯より {avg_4sec - avg_others:.1f}dB 高いビープ音が検出されています。")

# 追加の分析: ビープ音の特徴
print(f"\n📈 ビープ音の特徴分析:")
print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# 時間帯別の詳細
time_analysis = [
    (0, 2, "開始部分"),
    (2, 3, "4秒前"),
    (3, 5, "4秒付近（異常エリア）"),
    (5, 7, "4秒後"),
    (7, 10, "終了部分")
]

time_points, beep_freqs, beep_dbs, overall_dbs = analyze_time_series("/tmp/audio_analysis.wav", 10)

for start, end, description in time_analysis:
    mask = (np.array(time_points) >= start) & (np.array(time_points) < end)
    if np.any(mask):
        section_dbs = np.array(beep_dbs)[mask]
        section_freqs = np.array(beep_freqs)[mask]
        
        valid_dbs = section_dbs[section_dbs > -50]
        valid_freqs = section_freqs[section_freqs > 0]
        
        if len(valid_dbs) > 0:
            avg_db = np.mean(valid_dbs)
            max_db = np.max(valid_dbs)
            avg_freq = np.mean(valid_freqs) if len(valid_freqs) > 0 else 0
            
            print(f"{description:20s} ({start}-{end}秒): 平均{avg_db:6.1f}dB, 最大{max_db:6.1f}dB, 周波数{avg_freq:5.0f}Hz")

print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")