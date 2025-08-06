#!/usr/bin/env python3
import numpy as np
import scipy.io.wavfile as wav
from scipy import signal
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

try:
    import japanize_matplotlib
except:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "japanize-matplotlib"])
    import japanize_matplotlib

def analyze_all_seconds(audio_file, duration=20):
    """
    全秒数での詳細分析
    """
    sample_rate, audio_data = wav.read(audio_file)
    
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    results = []
    
    # 0.5秒刻みで分析
    for t in np.arange(0, min(duration, len(audio_data)/sample_rate), 0.5):
        # 指定時刻の音声を取得
        start_sample = int(t * sample_rate)
        end_sample = int((t + 0.1) * sample_rate)
        
        if end_sample >= len(audio_data):
            break
            
        segment = audio_data[start_sample:end_sample]
        
        # FFT
        fft = np.fft.rfft(segment)
        freqs = np.fft.rfftfreq(len(segment), 1/sample_rate)
        magnitude_db = 20 * np.log10(np.abs(fft) + 1e-10)
        
        # 各帯域の分析
        beep_mask = (freqs >= 300) & (freqs <= 400)
        voice_mask = (freqs >= 500) & (freqs <= 2000)
        high_mask = (freqs >= 2000) & (freqs <= 4000)
        
        beep_db = np.max(magnitude_db[beep_mask]) if np.any(beep_mask) else -100
        voice_db = np.max(magnitude_db[voice_mask]) if np.any(voice_mask) else -100
        high_db = np.max(magnitude_db[high_mask]) if np.any(high_mask) else -100
        
        # ビープ音の周波数
        if np.any(beep_mask):
            beep_freqs_band = freqs[beep_mask]
            beep_db_band = magnitude_db[beep_mask]
            max_idx = np.argmax(beep_db_band)
            beep_freq = beep_freqs_band[max_idx]
        else:
            beep_freq = 0
        
        # 比率計算
        if voice_db > 0:
            ratio = beep_db / voice_db * 100
        else:
            ratio = 0
            
        results.append({
            'time': t,
            'beep_db': beep_db,
            'voice_db': voice_db,
            'high_db': high_db,
            'beep_freq': beep_freq,
            'ratio': ratio
        })
    
    return results

def find_similar_patterns():
    """
    4秒と似たパターンを持つ時間帯を探索
    """
    results = analyze_all_seconds("/tmp/audio_analysis.wav", 20)
    
    # 4秒付近（3.5-4.5秒）の特徴を取得
    target_results = [r for r in results if 3.5 <= r['time'] <= 4.5]
    if not target_results:
        print("4秒付近のデータが見つかりません")
        return
    
    # 4秒の平均的な特徴
    target_beep_db = np.mean([r['beep_db'] for r in target_results])
    target_ratio = np.mean([r['ratio'] for r in target_results])
    target_freq = np.mean([r['beep_freq'] for r in target_results if r['beep_freq'] > 0])
    
    print("=" * 70)
    print("4秒と同じ傾向を持つ時間帯の探索")
    print("=" * 70)
    
    print(f"\n【4秒付近の特徴】")
    print(f"ビープ音強度: {target_beep_db:.1f}dB")
    print(f"ビープ音/音声比: {target_ratio:.1f}%")
    print(f"ビープ音周波数: {target_freq:.1f}Hz")
    
    # 類似度を計算
    similarities = []
    for r in results:
        # 4秒付近は除外
        if 3.5 <= r['time'] <= 4.5:
            continue
            
        # 類似度スコア計算（0-100）
        db_diff = abs(r['beep_db'] - target_beep_db)
        ratio_diff = abs(r['ratio'] - target_ratio)
        freq_diff = abs(r['beep_freq'] - target_freq) if r['beep_freq'] > 0 else 100
        
        # 重み付けスコア
        score = 100 - (db_diff * 0.5 + ratio_diff * 0.3 + freq_diff * 0.05)
        score = max(0, score)
        
        similarities.append({
            'time': r['time'],
            'score': score,
            'beep_db': r['beep_db'],
            'voice_db': r['voice_db'],
            'ratio': r['ratio'],
            'beep_freq': r['beep_freq']
        })
    
    # スコアでソート
    similarities.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n【4秒と最も似ている時間帯 TOP10】")
    print("順位 | 時間  | 類似度 | ビープdB | 音声dB | 比率(%) | 周波数")
    print("-" * 70)
    
    for i, sim in enumerate(similarities[:10], 1):
        print(f"{i:2d}位 | {sim['time']:4.1f}秒 | {sim['score']:5.1f}% | "
              f"{sim['beep_db']:7.1f} | {sim['voice_db']:6.1f} | "
              f"{sim['ratio']:6.1f} | {sim['beep_freq']:5.0f}Hz")
    
    # 可視化
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    fig.suptitle('4秒と似たパターンを持つ時間帯の分析', fontsize=16)
    
    # データを時系列順に戻す
    all_times = [r['time'] for r in results]
    all_beep_dbs = [r['beep_db'] for r in results]
    all_ratios = [r['ratio'] for r in results]
    all_scores = []
    
    for t in all_times:
        sim = next((s for s in similarities if s['time'] == t), None)
        if sim:
            all_scores.append(sim['score'])
        else:
            all_scores.append(100 if 3.5 <= t <= 4.5 else 0)  # 4秒付近は100
    
    # グラフ1: ビープ音強度
    ax1 = axes[0]
    ax1.plot(all_times, all_beep_dbs, linewidth=2, color='red', alpha=0.7)
    ax1.axhline(y=target_beep_db, color='blue', linestyle='--', label=f'4秒の平均({target_beep_db:.1f}dB)')
    ax1.axvspan(3.5, 4.5, alpha=0.3, color='yellow', label='4秒付近（基準）')
    
    # 似ている時間帯をマーク
    for sim in similarities[:5]:
        ax1.axvline(x=sim['time'], color='green', alpha=0.5, linestyle=':')
        ax1.text(sim['time'], 130, f"{sim['score']:.0f}%", rotation=90, fontsize=8)
    
    ax1.set_ylabel('ビープ音dB値')
    ax1.set_title('ビープ音強度の時系列変化')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 20)
    
    # グラフ2: ビープ音/音声比
    ax2 = axes[1]
    ax2.plot(all_times, all_ratios, linewidth=2, color='purple', alpha=0.7)
    ax2.axhline(y=target_ratio, color='blue', linestyle='--', label=f'4秒の平均({target_ratio:.1f}%)')
    ax2.axhline(y=100, color='red', linestyle=':', alpha=0.5, label='同じ強さ')
    ax2.axvspan(3.5, 4.5, alpha=0.3, color='yellow')
    
    for sim in similarities[:5]:
        ax2.axvline(x=sim['time'], color='green', alpha=0.5, linestyle=':')
    
    ax2.set_ylabel('ビープ音/音声比率(%)')
    ax2.set_title('ビープ音と音声の強度比')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 20)
    
    # グラフ3: 類似度スコア
    ax3 = axes[2]
    bars = ax3.bar(all_times, all_scores, width=0.4, 
                   color=['red' if s >= 80 else 'orange' if s >= 60 else 'yellow' if s >= 40 else 'lightblue' 
                          for s in all_scores])
    
    ax3.axhspan(80, 100, alpha=0.2, color='red', label='高類似度(80%以上)')
    ax3.axhspan(60, 80, alpha=0.2, color='orange', label='中類似度(60-80%)')
    
    ax3.set_xlabel('時間（秒）')
    ax3.set_ylabel('4秒との類似度(%)')
    ax3.set_title('4秒パターンとの類似度スコア')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.set_xlim(-0.5, 20)
    ax3.set_ylim(0, 110)
    
    plt.tight_layout()
    plt.savefig('/Users/tdual/Workspace/longan/similar_patterns_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # グループ分析
    print("\n【パターン別グループ分類】")
    
    # 高類似度グループ
    high_similar = [s for s in similarities if s['score'] >= 70]
    if high_similar:
        times = [s['time'] for s in high_similar]
        print(f"\n★ 4秒と非常に似ている（類似度70%以上）: {len(high_similar)}箇所")
        print(f"   時間帯: {', '.join([f'{t:.1f}秒' for t in sorted(times)[:10]])}")
    
    # 中類似度グループ
    mid_similar = [s for s in similarities if 50 <= s['score'] < 70]
    if mid_similar:
        times = [s['time'] for s in mid_similar]
        print(f"\n☆ やや似ている（類似度50-70%）: {len(mid_similar)}箇所")
        print(f"   時間帯: {', '.join([f'{t:.1f}秒' for t in sorted(times)[:10]])}")
    
    return similarities

# 実行
similarities = find_similar_patterns()

print(f"\n✅ 類似パターン分析グラフを保存しました:")
print(f"📊 /Users/tdual/Workspace/longan/similar_patterns_analysis.png")