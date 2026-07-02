import matplotlib.pyplot as plt
import numpy as np
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Heiti SC']
plt.rcParams['axes.unicode_minus'] = False

# 数据准备：2017-2026年
years = np.array([2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026])

# 总数数据
total_counts = np.array([4706, 6369, 8100, 9333, 10382, 11830, 12740, 13970, 14489, 3992])

# 创建图形
fig, ax = plt.subplots(figsize=(12, 7))

# 绘制柱状图
bars = ax.bar(years, total_counts, color='#2E86AB', alpha=0.8, width=0.6, edgecolor='black')

# 添加数值标签
max_count = max(total_counts)
for bar in bars:
    height = bar.get_height()
    offset = max_count * 0.02
    ax.text(bar.get_x() + bar.get_width()/2., height + offset,
             f'{int(height)}', ha='center', va='bottom',
             fontsize=16, fontweight='bold')  # 字体从10调整到14

# 设置图表属性（字体大小全面调大）
ax.set_xlabel('年份', fontsize=16, fontweight='bold')  # 从12调整到16
ax.set_ylabel('文献总数量 (CNKI + Web of Science)', fontsize=16, fontweight='bold')  # 从12调整到16
ax.set_title('"析氢反应"相关文献年度总数量 (2017-2026年)',
             fontsize=18, fontweight='bold', pad=20)  # 从14调整到18

# x轴刻度标签字体调大
ax.set_xticks(years)
ax.set_xticklabels(years, rotation=45, fontsize=13)  # 增加fontsize参数

# y轴刻度标签字体调大
ax.tick_params(axis='y', labelsize=13)

# 添加图例（如果有的话）
# ax.legend(fontsize=14)

# 添加网格线
ax.grid(axis='y', linestyle='--', alpha=0.3)

# 设置y轴范围
ax.set_ylim(0, max_count * 1.15)

# 设置x轴范围
ax.set_xlim(min(years)-0.5, max(years)+0.5)

# 调整布局
plt.tight_layout()

# 保存图片
save_path = r"C:\Users\25757\PycharmProjects\2文献统计柱状图代码"
os.makedirs(save_path, exist_ok=True)

png_file = os.path.join(save_path, "析氢反应文献年度总数_2017-2026_大字体.png")
pdf_file = os.path.join(save_path, "析氢反应文献年度总数_2017-2026_大字体.pdf")

plt.savefig(png_file, dpi=300, bbox_inches='tight')
plt.savefig(pdf_file, dpi=300, bbox_inches='tight')

print(f"柱状图已保存至：")
print(f"PNG格式: {png_file}")
print(f"PDF格式: {pdf_file}")

plt.show()