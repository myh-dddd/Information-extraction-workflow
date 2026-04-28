import matplotlib.pyplot as plt
import numpy as np
import os

# 设置中文字体（解决中文显示问题）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Heiti SC']
plt.rcParams['axes.unicode_minus'] = False

# 数据准备：2017-2026年
years = np.array([2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026])

# CNKI数据（第一张图）
cnki_counts = np.array([1546, 2153, 2826, 3423, 3052, 3765, 4052, 4129, 3223, 827])

# Web of Science数据（第二张图）
wos_counts = np.array([3160, 4216, 5274, 5910, 7330, 8065, 8688, 9841, 11266, 3165])

# 计算每年总数（两个网站之和）
total_counts = cnki_counts + wos_counts

# 数据检查
print("数据检查（2017-2026年）：")
print(f"年份: {years}")
print(f"CNKI: {cnki_counts}")
print(f"WOS: {wos_counts}")
print(f"总数: {total_counts}")
print(f"总数最大值: {max(total_counts)} (2025年: {total_counts[8]})")

# 【修改1】增大画布尺寸（宽度12英寸，高度7英寸）
plt.figure(figsize=(12, 7))

# 绘制柱状图（总数）
bars = plt.bar(years, total_counts, color='#2E86AB', alpha=0.8, width=0.6, edgecolor='black')

# 【修改2】添加数值标签，使用动态偏移量避免被顶部框线压到
max_count = max(total_counts)
for bar in bars:
    height = bar.get_height()
    # 标签位置：柱子顶部 + 最大值的2%作为偏移量（确保所有标签都有足够空间）
    offset = max_count * 0.02  # 动态偏移量（最大值的2%）
    plt.text(bar.get_x() + bar.get_width()/2., height + offset,
             f'{int(height)}', ha='center', va='bottom', fontsize=10, fontweight='bold')

# 设置图表属性
plt.xlabel('年份', fontsize=12, fontweight='bold')
plt.ylabel('文献总数量 (CNKI + Web of Science)', fontsize=12, fontweight='bold')
plt.title('"析氢反应"相关文献年度总数量 (2017-2026年)', fontsize=14, fontweight='bold', pad=20)
plt.xticks(years, rotation=45)

# 添加网格线
plt.grid(axis='y', linestyle='--', alpha=0.3)

# 【修改3】设置y轴范围（顶部预留15%空间，避免标签被裁剪）
plt.ylim(0, max_count * 1.15)  # 原来是 max_count + 500，现在改为动态百分比

# 【修改4】设置x轴范围，避免边缘柱子被裁剪
plt.xlim(min(years)-0.5, max(years)+0.5)

# 调整布局
plt.tight_layout()

# 保存图片到指定路径
save_path = r"C:\Users\25757\PycharmProjects\2文献统计柱状图代码"
# 确保目录存在
os.makedirs(save_path, exist_ok=True)

# 保存为不同格式
png_file = os.path.join(save_path, "析氢反应文献年度总数_2017-2026.png")
pdf_file = os.path.join(save_path, "析氢反应文献年度总数_2017-2026.pdf")

# 【修改5】保存时使用高dpi和tight布局
plt.savefig(png_file, dpi=300, bbox_inches='tight')
plt.savefig(pdf_file, dpi=300, bbox_inches='tight')

print(f"\n柱状图已保存至：")
print(f"PNG格式: {png_file}")
print(f"PDF格式: {pdf_file}")

# 显示图表
plt.show()
