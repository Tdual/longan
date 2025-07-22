#!/usr/bin/env python3
"""
2秒付近の改善を確認
"""
import numpy as np
from scipy.io import wavfile
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.family'] = 'Hiragino Sans'

# 修正後の音声を読み込み
sample_rate, data = wavfile.read("test_crossfade_audio.wav")

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
fig, axes = plt.subplots(2, 1, figsize=(14, 8))

# 1. 波形
axes[0].plot(time_ms, segment, 'b-', linewidth=0.5)
axes[0].set_title('クロスフェード適用後: 2秒付近の音声波形', fontsize=14)
axes[0].set_xlabel('時間（ミリ秒）')
axes[0].set_ylabel('振幅')
axes[0].grid(True, alpha=0.3)
axes[0].axvline(x=2000, color='red', linestyle='--', alpha=0.7, label='2秒')
axes[0].legend()

# 2. 差分（急激な変化）
diff = np.diff(segment)
diff_times = time_ms[:-1]
axes[1].plot(diff_times, diff, 'g-', linewidth=0.5)
axes[1].set_title('振幅の変化率', fontsize=14)
axes[1].set_xlabel('時間（ミリ秒）')
axes[1].set_ylabel('変化率')
axes[1].grid(True, alpha=0.3)
axes[1].axvline(x=2000, color='red', linestyle='--', alpha=0.7, label='2秒')
axes[1].axhline(y=0.1, color='orange', linestyle=':', alpha=0.7, label='問題レベル(0.1)')
axes[1].axhline(y=-0.1, color='orange', linestyle=':', alpha=0.7)
axes[1].legend()

plt.tight_layout()
plt.savefig('2_second_improvement_check.png', dpi=150, bbox_inches='tight')
print("2秒付近の改善チェック結果を保存しました: 2_second_improvement_check.png")

# 2秒付近の問題箇所を特定
problem_threshold = 0.1
problem_indices = np.where(np.abs(diff) > problem_threshold)[0]

print(f"\n2秒付近（1.5-2.5秒）の急激な変化（閾値: {problem_threshold}）:")
if len(problem_indices) > 0:
    for idx in problem_indices:
        time_pos = 1.5 + idx / sample_rate
        change_value = diff[idx]
        print(f"  - {time_pos:.3f}秒: 変化量 {change_value:.3f}")
else:
    print("  ✅ 問題となるレベルの急激な変化は検出されませんでした")

# 1928ms付近（元々問題があった場所）を特定チェック
target_time = 1.928  # 秒
target_idx = int((target_time - 1.5) * sample_rate)
if 0 <= target_idx < len(diff):
    target_change = diff[target_idx]
    print(f"\n1928ms付近の変化量: {target_change:.3f}")
    if abs(target_change) > 0.1:
        print("  ⚠️  まだ問題のレベルです")
    else:
        print("  ✅ 改善されています")
else:
    print(f"\n1928ms は範囲外です")

# 2000ms（2秒ちょうど）付近をチェック
target_time = 2.0  # 秒
target_idx = int((target_time - 1.5) * sample_rate)
if 0 <= target_idx < len(diff):
    target_change = diff[target_idx]
    print(f"\n2000ms付近の変化量: {target_change:.3f}")
    if abs(target_change) > 0.1:
        print("  ⚠️  まだ問題のレベルです")
    else:
        print("  ✅ 改善されています")

# 最大変化量を確認
max_change_idx = np.argmax(np.abs(diff))
max_change_time = 1.5 + max_change_idx / sample_rate
max_change_value = diff[max_change_idx]

print(f"\n最大変化:")
print(f"  時間: {max_change_time:.3f}秒")
print(f"  変化量: {max_change_value:.3f}")

print(f"\n=== 改善状況の評価 ===")
severe_problems = len(np.where(np.abs(diff) > 0.2)[0])
moderate_problems = len(np.where((np.abs(diff) > 0.1) & (np.abs(diff) <= 0.2))[0])

print(f"深刻な変化（0.2以上）: {severe_problems}個")
print(f"中程度の変化（0.1-0.2）: {moderate_problems}個")

if severe_problems == 0 and moderate_problems <= 5:
    print("✅ 2秒付近の音声品質は大幅に改善されました！")
elif severe_problems == 0:
    print("⚠️  改善されましたが、まだ軽微な問題があります")
else:
    print("❌ さらなる改善が必要です")