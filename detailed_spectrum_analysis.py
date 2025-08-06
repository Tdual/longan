#!/usr/bin/env python3
import numpy as np
import scipy.io.wavfile as wav
from scipy import signal
import matplotlib.pyplot as plt
from scipy.signal import spectrogram

def create_spectrogram(audio_file, start_time=0, duration=10):
    """
    スペクトログラムを作成して詳細な周波数分析
    """
    sample_rate, audio_data = wav.read(audio_file)
    
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # 正規化
    audio_data = audio_data.astype(np.float32)
    if np.max(np.abs(audio_data)) > 0:
        audio_data = audio_data / np.max(np.abs(audio_data))
    
    # 指定範囲を抽出
    start_sample = int(start_time * sample_rate)
    end_sample = int((start_time + duration) * sample_rate)
    segment = audio_data[start_sample:end_sample]
    
    # スペクトログラム作成
    f, t, Sxx = spectrogram(segment, sample_rate, nperseg=1024, noverlap=512)
    
    # dBスケールに変換
    Sxx_db = 10 * np.log10(Sxx + 1e-10)
    
    # ビープ音の特徴的な周波数を検出
    print(f"\n=== {start_time}秒から{start_time+duration}秒のスペクトル分析 ===")
    
    # 各時間フレームで強い周波数を検出
    beep_candidates = []
    for i, time_point in enumerate(t):
        if i % 10 == 0:  # 10フレームごとにサンプリング
            spectrum_slice = Sxx_db[:, i]
            
            # 300-500Hz帯域の平均パワー
            freq_mask_low = (f >= 300) & (f <= 500)
            power_low = np.mean(spectrum_slice[freq_mask_low])
            
            # 1000-2000Hz帯域の平均パワー（倍音）
            freq_mask_high = (f >= 1000) & (f <= 2000)
            power_high = np.mean(spectrum_slice[freq_mask_high])
            
            # 全体の平均パワー
            power_total = np.mean(spectrum_slice)
            
            # ビープ音の可能性を判定
            if power_low > power_total + 10:  # 低周波が強い
                actual_time = start_time + time_point
                beep_candidates.append((actual_time, power_low, "低周波ビープ"))
                
    return beep_candidates

def analyze_specific_moment(audio_file, target_time, window_ms=100):
    """
    特定の瞬間の詳細な周波数分析
    """
    sample_rate, audio_data = wav.read(audio_file)
    
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # 指定時刻の前後を取得
    window_sec = window_ms / 1000.0
    start_time = max(0, target_time - window_sec/2)
    end_time = target_time + window_sec/2
    
    start_sample = int(start_time * sample_rate)
    end_sample = int(end_time * sample_rate)
    segment = audio_data[start_sample:end_sample]
    
    # FFT分析
    fft = np.fft.rfft(segment)
    freqs = np.fft.rfftfreq(len(segment), 1/sample_rate)
    magnitude = np.abs(fft)
    magnitude_db = 20 * np.log10(magnitude + 1e-10)
    
    # ピーク検出
    peaks, properties = signal.find_peaks(magnitude_db, height=-20, distance=20)
    
    print(f"\n{target_time:.2f}秒の瞬間的な周波数成分:")
    
    # 主要な周波数成分を表示
    if len(peaks) > 0:
        sorted_peaks = sorted(zip(freqs[peaks], magnitude_db[peaks]), key=lambda x: x[1], reverse=True)
        
        for freq, mag in sorted_peaks[:10]:
            if mag > -30:  # 十分な強度がある成分のみ
                print(f"  {freq:7.1f} Hz: {mag:6.1f} dB")
    
    # ビープ音の特徴を判定
    beep_freqs = [(f, m) for f, m in sorted_peaks if 250 <= f <= 550]
    if beep_freqs and beep_freqs[0][1] > -20:
        print(f"  → ビープ音の可能性: 高 (主要周波数 {beep_freqs[0][0]:.1f} Hz)")
        return True
    else:
        print(f"  → ビープ音の可能性: 低")
        return False

# メイン処理
print("=== 詳細なスペクトル分析 ===")
print("特に4秒付近を重点的に分析します\n")

audio_file = "/tmp/audio_analysis.wav"

# 3.5秒から4.5秒を詳細分析
print("=" * 50)
print("3.5秒 - 4.5秒の1秒間を0.1秒刻みで分析:")
print("=" * 50)

beep_detected = []
for t in np.arange(3.5, 4.6, 0.1):
    is_beep = analyze_specific_moment(audio_file, t, window_ms=50)
    if is_beep:
        beep_detected.append(t)

if beep_detected:
    print(f"\n【結果】4秒付近でビープ音を検出: {beep_detected[0]:.2f}秒から{beep_detected[-1]:.2f}秒")
else:
    print("\n【結果】4秒付近では明確なビープ音は検出されませんでした")

# 0-10秒のスペクトログラム分析
print("\n" + "=" * 50)
print("0-10秒全体のスペクトログラム分析:")
print("=" * 50)

candidates = create_spectrogram(audio_file, 0, 10)

# より精密な分析：エネルギー比較
print("\n" + "=" * 50)
print("エネルギー比較による精密分析（0-10秒）:")
print("=" * 50)

sample_rate, audio_data = wav.read(audio_file)
if len(audio_data.shape) > 1:
    audio_data = np.mean(audio_data, axis=1)

# 0.5秒ごとにエネルギーを計算
for t in np.arange(0, 10, 0.5):
    start_idx = int(t * sample_rate)
    end_idx = int((t + 0.5) * sample_rate)
    
    if end_idx > len(audio_data):
        break
        
    segment = audio_data[start_idx:end_idx]
    
    # 周波数帯域ごとのエネルギー
    fft = np.fft.rfft(segment)
    freqs = np.fft.rfftfreq(len(segment), 1/sample_rate)
    
    # 各帯域のエネルギー
    energy_300_500 = np.sum(np.abs(fft[(freqs >= 300) & (freqs <= 500)])**2)
    energy_total = np.sum(np.abs(fft)**2)
    
    if energy_total > 0:
        ratio = energy_300_500 / energy_total * 100
        
        if ratio > 5:  # 5%以上が300-500Hz帯域
            print(f"{t:4.1f}秒: ビープ音帯域が全体の {ratio:5.1f}% を占める ★")
        else:
            print(f"{t:4.1f}秒: ビープ音帯域は {ratio:5.1f}% のみ")