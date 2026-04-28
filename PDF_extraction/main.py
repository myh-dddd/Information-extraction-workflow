import PyPDF2
import re
import os
import pandas as pd
import tiktoken
import glob
from typing import List, Union, Dict, Any


# ==================== Token计数 ====================

def count_tokens(text: str) -> int:
    """计算token数"""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


# ==================== 文本清理 ====================

def clean_text(text: str) -> str:
    """基础清理：去除多余空格和换行"""
    # 分割成行，去除每行首尾空格，过滤空行
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    # 用空格重新连接
    return ' '.join(lines)


def split_sentences(text: str) -> List[str]:
    """分割句子（用于页间重叠）"""
    # 中英文句子分割
    sentences = re.split(r'([。！？.!?]+)', text)
    result = []
    for i in range(0, len(sentences), 2):
        if i < len(sentences):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            if sentence.strip():
                result.append(sentence.strip())
    return result


# ==================== 关键词定义（仅用于标记）====================

# 铂系催化剂相关关键词（只标记，不过滤）
PT_KEYWORDS = {
    'platinum_metals': [
        'Pt', 'platinum', '铂',
        'Pd', 'palladium', '钯',
        'Ru', 'ruthenium', '钌',
        'Ir', 'iridium', '铱',
        'Rh', 'rhodium', '铑'
    ],
    'platinum_precursors': [
        'H2PtCl6', 'chloroplatinic acid', '氯铂酸',
        'K2PtCl4', 'K2PtCl6',
        'Pt(acac)2', 'platinum acetylacetonate', '乙酰丙酮铂',
        'PtCl4', 'Pt(NH3)4Cl2'
    ],
    'her_parameters': [
        'HER', 'hydrogen evolution', '析氢',
        'overpotential', '过电位',
        'Tafel', '塔菲尔',
        'exchange current', '交换电流密度',
        'Faradaic efficiency', '法拉第效率',
        'stability', '稳定性',
        'durability', '耐久性',
        'CV', 'cyclic voltammetry', '循环伏安',
        'LSV', 'linear sweep voltammetry', '线性扫描伏安',
        'EIS', 'electrochemical impedance', '电化学阻抗',
        'TOF', 'turnover frequency', '转换频率'
    ],
    'synthesis_terms': [
        'synthesized', 'prepared', '合成', '制备',
        'impregnation', 'deposition', '浸渍', '沉积',
        'calcined', 'annealed', '煅烧', '退火',
        'loading', '载量',
        'mg', 'g', 'mL', 'L', 'M', 'mmol', 'mol',  # 用量单位
        '°C', '℃', 'K',  # 温度
        'h', 'min', 's', 'hour', 'minute',  # 时间
    ]
}


def check_keywords(text: str) -> Dict[str, bool]:
    """
    检查文本包含哪些关键词
    只标记，不过滤
    """
    text_lower = text.lower()
    result = {}

    for category, words in PT_KEYWORDS.items():
        for word in words:
            if word.lower() in text_lower or word in text:
                result[f'has_{category}'] = True
                break
        else:
            result[f'has_{category}'] = False

    # 计算综合相关性得分（用于排序）
    result['relevance_score'] = (
            result['has_platinum_metals'] * 3 +
            result['has_platinum_precursors'] * 2 +
            result['has_her_parameters'] * 2 +
            result['has_synthesis_terms'] * 1
    )

    return result


# ==================== PDF提取（核心功能）====================

def extract_from_pdf(pdf_path: str,
                     overlap_sentences: int = 2) -> List[Dict[str, Any]]:
    """
    从PDF提取文本，按页处理

    参数:
        pdf_path: PDF文件路径
        overlap_sentences: 与上一页重叠的句子数量（0表示不重叠）
    """
    data = []
    previous_page_end = ""  # 上一页的最后几句话

    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)

            print(f"  处理 {os.path.basename(pdf_path)}，共 {total_pages} 页")

            for page_num in range(total_pages):
                page = reader.pages[page_num]
                text = page.extract_text()

                if not text or len(text.strip()) < 50:  # 跳过太短的页
                    continue

                # 基础清理
                text = clean_text(text)

                # 分割当前页的句子（用于重叠）
                current_sentences = split_sentences(text)

                # 构建当前页的完整内容（包含上一页的重叠）
                if previous_page_end and current_sentences:
                    # 检查是否需要添加重叠（避免重复）
                    first_sentence = current_sentences[0] if current_sentences else ""
                    if first_sentence not in previous_page_end:
                        full_content = f"[接上页] {previous_page_end}\n\n{text}"
                    else:
                        full_content = text
                else:
                    full_content = text

                # 提取当前页的最后几句话，用于下一页的重叠
                if current_sentences and overlap_sentences > 0:
                    if len(current_sentences) > overlap_sentences:
                        previous_page_end = ' '.join(current_sentences[-overlap_sentences:])
                    else:
                        previous_page_end = ' '.join(current_sentences)
                else:
                    previous_page_end = ""

                # 检查关键词（只标记）
                keyword_check = check_keywords(full_content)

                # 添加到数据
                data.append({
                    'file_name': os.path.basename(pdf_path),
                    'page_number': page_num + 1,
                    'total_pages': total_pages,
                    'content': full_content,
                    'tokens': count_tokens(full_content),
                    'has_overlap': bool(previous_page_end),
                    **keyword_check  # 展开所有标记字段
                })

    except Exception as e:
        print(f"  错误: {str(e)}")

    return data


# ==================== 主转换函数 ====================

def pdf_to_dataframe(pdf_source: Union[str, List[str]],
                     overlap_sentences: int = 2,
                     recursive: bool = False) -> pd.DataFrame:
    """
    将PDF转换为DataFrame（保留所有页，不过滤）

    参数:
        pdf_source: PDF文件路径、文件夹路径或文件列表
        overlap_sentences: 与上一页重叠的句子数量（0表示不重叠）
        recursive: 是否递归搜索子文件夹
    """
    all_data = []

    # 获取PDF文件列表
    if isinstance(pdf_source, str):
        if os.path.isdir(pdf_source):
            pattern = os.path.join(pdf_source, "**/*.pdf") if recursive else os.path.join(pdf_source, "*.pdf")
            pdf_files = glob.glob(pattern, recursive=recursive)
            print(f"在文件夹中找到 {len(pdf_files)} 个PDF文件")
        else:
            pdf_files = [pdf_source]
    else:
        pdf_files = pdf_source

    # 处理每个PDF
    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            file_data = extract_from_pdf(
                pdf_path=pdf_file,
                overlap_sentences=overlap_sentences
            )
            all_data.extend(file_data)

    # 创建DataFrame
    df = pd.DataFrame(all_data)

    if not df.empty:
        print(f"\n{'=' * 50}")
        print(f"处理完成！")
        print(f"  文件数: {df['file_name'].nunique()}")
        print(f"  总页数: {len(df)}")
        print(f"  总tokens: {df['tokens'].sum():,}")
        print(f"  平均tokens/页: {df['tokens'].mean():.0f}")
        print(f"\n关键词统计（仅标记，未过滤）:")
        print(f"  含铂金属: {df['has_platinum_metals'].sum()} 页")
        print(f"  含铂前驱体: {df['has_platinum_precursors'].sum()} 页")
        print(f"  含HER参数: {df['has_her_parameters'].sum()} 页")
        print(f"  含合成术语: {df['has_synthesis_terms'].sum()} 页")
        print(f"{'=' * 50}")

    return df


# ==================== 使用示例 ====================

def main():
    """主程序 - 只提取，不过滤"""

    print("=" * 60)
    print("铂系析氢催化剂PDF提取工具")
    print("(提取所有页面，不过滤，只做关键词标记)")
    print("=" * 60)

    # 设置PDF文件夹路径
    pdf_folder = input("请输入PDF文件夹路径: ").strip()

    if not os.path.exists(pdf_folder):
        print("文件夹不存在")
        return

    # 设置重叠句子数
    overlap = input("与上一页重叠的句子数 (默认: 2，输入0取消重叠): ").strip()
    overlap = int(overlap) if overlap.isdigit() else 2

    # 提取PDF
    df = pdf_to_dataframe(
        pdf_source=pdf_folder,
        overlap_sentences=overlap,
        recursive=True
    )

    if not df.empty:
        # 保存全部数据
        output_file = "all_pages_with_keywords.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n所有数据已保存到: {output_file}")

        # 显示预览
        print("\n数据预览（前3行）:")
        preview_cols = ['file_name', 'page_number', 'tokens',
                        'has_platinum_metals', 'has_her_parameters']
        print(df[preview_cols].head(3))

        print(f"\n后续处理建议:")
        print(f"1. 直接使用全部{len(df)}页输入LLM进行参数提取")
        print(f"2. 或先筛选铂相关页：df[df['has_platinum_metals']==True]")
        print(f"3. 或按相关性排序：df.sort_values('relevance_score', ascending=False)")


def quick_extract(folder_path: str) -> pd.DataFrame:
    """
    快速提取 - 最简单的调用方式
    """
    return pdf_to_dataframe(
        pdf_source=folder_path,
        overlap_sentences=2,
        recursive=True
    )


if __name__ == "__main__":
    # 运行主程序
    main()

    # 或者一行代码搞定：
    # df = quick_extract("./my_papers/")
    # df.to_csv("my_data.csv", index=False)