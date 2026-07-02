import matplotlib.pyplot as plt
import numpy as np
import os

# 设置中文字体（解决中文显示问题）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Heiti SC']
plt.rcParams['axes.unicode_minus'] = False

# 数据准备：2017-2026年
years = np.array([2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026])

# CNKI数据
cnki_counts = np.array([429, 256, 293, 380, 462, 693, 866, 983, 1132, 185])

# Web of Science数据
wos_counts = np.array([3160, 4216, 5274, 5910, 7330, 8065, 8688, 9841, 11266, 3165])

# 计算每年总数（用于验证）
total_counts = cnki_counts + wos_counts

# 设置柱状图参数
x = np.arange(len(years))  # 标签位置
width = 0.35  # 柱子的宽度

# 创建图形
fig, ax = plt.subplots(figsize=(14, 8))

# 绘制双柱状图
bars1 = ax.bar(x - width/2, cnki_counts, width, label='CNKI (知网)',
                color='#2E86AB', alpha=0.85, edgecolor='black', linewidth=0.8)
bars2 = ax.bar(x + width/2, wos_counts, width, label='Web of Science',
                color='#7E3D76', alpha=0.85, edgecolor='black', linewidth=0.8)

# 添加数值标签
max_count = max(wos_counts)

# CNKI标签
for bar in bars1:
    height = bar.get_height()
    if height > 0:  # 只为有数据的柱子添加标签
        offset = max_count * 0.01
        ax.text(bar.get_x() + bar.get_width()/2., height + offset,
                f'{int(height)}', ha='center', va='bottom', fontsize=9, fontweight='bold')

# WOS标签
for bar in bars2:
    height = bar.get_height()
    offset = max_count * 0.01
    ax.text(bar.get_x() + bar.get_width()/2., height + offset,
            f'{int(height)}', ha='center', va='bottom', fontsize=9, fontweight='bold')



# 设置图表属性
ax.set_xlabel('年份', fontsize=13, fontweight='bold')
ax.set_ylabel('文献数量（篇）', fontsize=13, fontweight='bold')
ax.set_title('"析氢反应"相关文献年度分布 (2017-2026年)',
             fontsize=15, fontweight='bold', pad=20)

# 设置x轴刻度
ax.set_xticks(x)
ax.set_xticklabels(years, rotation=45, ha='right')

# 添加图例
ax.legend(loc='upper left', fontsize=11, framealpha=0.9, edgecolor='black')

# 添加网格线
ax.grid(axis='y', linestyle='--', alpha=0.3, linewidth=0.5)

# 设置y轴范围（顶部预留15%空间）
ax.set_ylim(0, max_count * 1.2)

# 设置x轴范围
ax.set_xlim(-0.5, len(years) - 0.5)

# 添加背景色（浅灰色）
ax.set_facecolor('#F8F9FA')
fig.patch.set_facecolor('white')

# 调整布局
plt.tight_layout()

# 保存图片
save_path = r"C:\Users\25757\PycharmProjects\2文献统计柱状图代码"
os.makedirs(save_path, exist_ok=True)

# 保存为不同格式
png_file = os.path.join(save_path, "析氢反应文献年度对比_2017-2026.png")
pdf_file = os.path.join(save_path, "析氢反应文献年度对比_2017-2026.pdf")
svg_file = os.path.join(save_path, "析氢反应文献年度对比_2017-2026.svg")

plt.savefig(png_file, dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig(pdf_file, dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig(svg_file, dpi=300, bbox_inches='tight', facecolor='white')

print(f"数据统计：")
print(f"CNKI总数: {sum(cnki_counts)}")
print(f"WOS总数: {sum(wos_counts)}")
print(f"总文献数: {sum(total_counts)}")
print(f"\n图片已保存至：")
print(f"PNG格式: {png_file}")
print(f"PDF格式: {pdf_file}")
print(f"SVG格式: {svg_file}")

# 显示图表
plt.show()