import PyPDF2
import re
import os
import pandas as pd
import tiktoken
import glob
from typing import List, Union, Dict, Any
from datetime import datetime


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


def clean_surrogate_chars(text: str) -> str:
    """清理文本中的无效代理字符"""
    if not isinstance(text, str):
        return text
    # 方法1：正则表达式移除所有代理字符（U+D800到U+DFFF）
    text = re.sub(r'[\ud800-\udfff]', '', text)
    # 方法2：额外的安全措施，确保没有残留的无效字符
    try:
        # 尝试编码为UTF-8，忽略错误，再解码回来
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # 如果还是失败，移除所有非基本字符
        text = ''.join(c for c in text if ord(c) < 0xd800 or ord(c) > 0xdfff)
    return text


def clean_dataframe_for_save(df: pd.DataFrame) -> pd.DataFrame:
    """
    清理DataFrame中所有字符串列的无效代理字符
    """
    df_clean = df.copy()

    # 清理所有object类型（字符串）的列
    for col in df_clean.select_dtypes(include=['object']).columns:
        df_clean[col] = df_clean[col].apply(
            lambda x: clean_surrogate_chars(x) if pd.notna(x) else x
        )

    return df_clean


def safe_save_csv(df: pd.DataFrame, output_file: str):
    """
    安全保存CSV文件，自动处理编码问题
    """
    # 清理数据
    df_clean = clean_dataframe_for_save(df)

    # 尝试多种编码方式保存
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']

    for encoding in encodings:
        try:
            df_clean.to_csv(output_file, index=False, encoding=encoding)
            print(f"  ✓ 成功保存，使用编码: {encoding}")
            return True
        except (UnicodeEncodeError, UnicodeError):
            continue

    # 最后的手段：使用errors='ignore'
    try:
        df_clean.to_csv(output_file, index=False, encoding='utf-8', errors='ignore')
        print(f"  ⚠ 保存成功，但部分字符被忽略")
        return True
    except Exception as e:
        print(f"  ✗ 保存失败: {e}")
        return False


def generate_output_filename(base_name: str, suffix: str = "", include_timestamp: bool = True) -> str:
    """
    生成带时间戳的文件名，避免覆盖

    参数:
        base_name: 基础文件名（不含扩展名）
        suffix: 额外的后缀（如 "high_quality"）
        include_timestamp: 是否包含时间戳

    返回:
        完整的文件名（含扩展名）
    """
    if include_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if suffix:
            filename = f"{base_name}_{suffix}_{timestamp}.csv"
        else:
            filename = f"{base_name}_{timestamp}.csv"
    else:
        if suffix:
            filename = f"{base_name}_{suffix}.csv"
        else:
            filename = f"{base_name}.csv"

    return filename


def save_with_version(df: pd.DataFrame, base_name: str, suffix: str = "",
                      also_save_latest: bool = True) -> str:
    """
    保存文件，同时保留最新版本和历史版本

    参数:
        df: 要保存的DataFrame
        base_name: 基础文件名
        suffix: 额外后缀
        also_save_latest: 是否同时保存一份为 latest 版本（方便快速访问）

    返回:
        保存的文件路径
    """
    # 生成带时间戳的文件名
    timestamped_file = generate_output_filename(base_name, suffix, include_timestamp=True)

    # 保存带时间戳的版本
    print(f"\n  保存版本: {timestamped_file}")
    success = safe_save_csv(df, timestamped_file)

    # 同时保存一份为 latest（每次覆盖，方便快速访问最新结果）
    if also_save_latest and success:
        latest_file = generate_output_filename(base_name, suffix, include_timestamp=False)
        latest_file = latest_file.replace('.csv', '_latest.csv')
        print(f"  保存最新版: {latest_file}")
        safe_save_csv(df, latest_file)

    return timestamped_file if success else None


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
    # 先清理文本中的无效字符
    text = clean_surrogate_chars(text)
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


# ==================== PDF提取（核心功能 - 整篇文献模式）====================

def extract_full_document(pdf_path: str) -> Dict[str, Any]:
    """
    从PDF提取整篇文献的文本（不按页分割）

    参数:
        pdf_path: PDF文件路径

    返回:
        包含整篇文献信息的字典
    """
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)

            print(f"  处理 {os.path.basename(pdf_path)}，共 {total_pages} 页")

            pages_content = []
            page_tokens = []

            for page_num in range(total_pages):
                page = reader.pages[page_num]
                text = page.extract_text()

                if not text or len(text.strip()) < 50:  # 跳过太短的页
                    continue

                # 基础清理
                text = clean_text(text)
                # 清理无效字符
                text = clean_surrogate_chars(text)

                pages_content.append({
                    'page_num': page_num + 1,
                    'text': text
                })
                page_tokens.append(count_tokens(text))

            if not pages_content:
                return None

            # 合并所有页，保留页码标记
            full_text_parts = []
            for page in pages_content:
                full_text_parts.append(
                    f"\n{'=' * 60}\n[Page {page['page_num']}/{total_pages}]\n{'=' * 60}\n{page['text']}")

            full_text = "".join(full_text_parts)

            # 检查关键词
            keyword_check = check_keywords(full_text)

            return {
                'file_name': os.path.basename(pdf_path),
                'total_pages': len(pages_content),
                'original_pages': total_pages,
                'content': full_text,
                'tokens': sum(page_tokens),
                'pages_count': len(pages_content),
                'pages_skipped': total_pages - len(pages_content),
                **keyword_check
            }

    except Exception as e:
        print(f"  错误: {str(e)}")
        return None


# ==================== 主转换函数（整篇文献模式）====================

def pdf_to_dataframe(pdf_source: Union[str, List[str]],
                     recursive: bool = False,
                     skip_non_platinum: bool = True,
                     max_files: int = None) -> pd.DataFrame:
    """
    将PDF转换为DataFrame（按整篇文献，不按页分割）

    参数:
        pdf_source: PDF文件路径、文件夹路径或文件列表
        recursive: 是否递归搜索子文件夹
        skip_non_platinum: 是否跳过不含铂金属的文献（快速筛选）
        max_files: 最大处理文件数（用于测试）
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

    # 限制文件数量（用于测试）
    if max_files and max_files > 0:
        pdf_files = pdf_files[:max_files]
        print(f"限制处理前 {max_files} 个文件")

    total_files = len(pdf_files)
    processed = 0
    skipped = 0
    errors = 0

    # 处理每个PDF
    for idx, pdf_file in enumerate(pdf_files, 1):
        if os.path.exists(pdf_file):
            print(f"\n[{idx}/{total_files}] ", end="")
            doc_data = extract_full_document(pdf_file)

            if doc_data is None:
                errors += 1
                continue

            # 快速筛选：跳过不含铂的文献（节省后续处理时间）
            if skip_non_platinum and not doc_data.get('has_platinum_metals', False):
                skipped += 1
                print(f"  跳过 {os.path.basename(pdf_file)}（不含铂金属）")
                continue

            all_data.append(doc_data)
            processed += 1

    # 创建DataFrame
    df = pd.DataFrame(all_data)

    # 重新排列列的顺序
    if not df.empty:
        # 定义列顺序
        base_cols = ['file_name', 'total_pages', 'original_pages', 'pages_count', 'pages_skipped',
                     'tokens', 'has_platinum_metals', 'has_platinum_precursors',
                     'has_her_parameters', 'has_synthesis_terms', 'relevance_score']

        # 确保所有列都存在
        existing_cols = [col for col in base_cols if col in df.columns]
        other_cols = [col for col in df.columns if col not in base_cols and col != 'content']

        # content 放在最后
        if 'content' in df.columns:
            other_cols.append('content')

        df = df[existing_cols + other_cols]

        print(f"\n{'=' * 50}")
        print(f"处理完成！")
        print(f"  总PDF文件数: {total_files}")
        print(f"  跳过（不含铂）: {skipped}")
        print(f"  处理错误: {errors}")
        print(f"  有效处理: {processed}")
        print(f"  总tokens: {df['tokens'].sum():,}")
        print(f"  平均tokens/篇: {df['tokens'].mean():.0f}")
        print(f"  最大tokens/篇: {df['tokens'].max():,}")
        print(f"  最小tokens/篇: {df['tokens'].min():,}")
        print(f"\n关键词统计:")
        print(f"  含铂金属: {df['has_platinum_metals'].sum()} 篇")
        print(f"  含铂前驱体: {df['has_platinum_precursors'].sum()} 篇")
        print(f"  含HER参数: {df['has_her_parameters'].sum()} 篇")
        print(f"  含合成术语: {df['has_synthesis_terms'].sum()} 篇")

        # 检查是否有超过128K的文献
        over_limit = df[df['tokens'] > 128000]
        if not over_limit.empty:
            print(f"\n⚠ 警告: {len(over_limit)} 篇文献超过128K tokens限制")
            print("  这些文献需要分段处理")

        print(f"{'=' * 50}")

    return df


# ==================== 辅助函数 ====================

def filter_by_relevance(df: pd.DataFrame, min_score: int = 4) -> pd.DataFrame:
    """
    按相关性得分筛选文献

    参数:
        df: 数据框
        min_score: 最低相关性得分（默认4，表示至少包含铂金属+HER参数）
    """
    return df[df['relevance_score'] >= min_score].copy()


def get_high_quality_docs(df: pd.DataFrame) -> pd.DataFrame:
    """
    获取高质量文献（含铂金属且含HER参数）
    """
    return df[(df['has_platinum_metals'] == True) &
              (df['has_her_parameters'] == True)].copy()


def load_latest_extraction(base_name: str = "all_documents") -> pd.DataFrame:
    """
    加载最新的提取结果

    参数:
        base_name: 基础文件名

    返回:
        最新的DataFrame，如果不存在则返回空DataFrame
    """
    latest_file = f"{base_name}_latest.csv"
    if os.path.exists(latest_file):
        print(f"加载最新结果: {latest_file}")
        return pd.read_csv(latest_file)
    else:
        print(f"未找到最新结果文件: {latest_file}")
        return pd.DataFrame()


def list_saved_files(base_name: str = "all_documents"):
    """
    列出所有已保存的结果文件
    """
    import glob
    pattern = f"{base_name}_*.csv"
    files = glob.glob(pattern)

    if not files:
        print(f"未找到 {base_name} 相关的文件")
        return

    print(f"\n找到 {len(files)} 个文件:")
    for f in sorted(files, reverse=True):
        size = os.path.getsize(f) / 1024  # KB
        print(f"  {f} ({size:.1f} KB)")


# ==================== 快速提取函数 ====================

def quick_extract(folder_path: str, skip_non_platinum: bool = True,
                  max_files: int = None) -> pd.DataFrame:
    """
    快速提取 - 最简单的调用方式

    参数:
        folder_path: PDF文件夹路径
        skip_non_platinum: 是否跳过不含铂的文献
        max_files: 最大处理文件数（用于测试）
    """
    return pdf_to_dataframe(
        pdf_source=folder_path,
        recursive=True,
        skip_non_platinum=skip_non_platinum,
        max_files=max_files
    )


# ==================== 主函数 ====================

def main():
    """主程序 - 整篇文献提取模式"""

    print("=" * 60)
    print("铂系析氢催化剂PDF提取工具")
    print("(整篇文献模式 - 不按页分割)")
    print("=" * 60)

    # 设置PDF文件夹路径
    pdf_folder = input("请输入PDF文件夹路径: ").strip()

    if not os.path.exists(pdf_folder):
        print("文件夹不存在")
        return

    # 是否跳过不含铂的文献
    skip = input("是否跳过不含铂金属的文献？(y/n，默认y): ").strip().lower()
    skip_non_platinum = skip != 'n'

    # 是否限制处理数量（用于测试）
    limit_input = input("是否限制处理文件数？(输入数字，0或回车表示不限制): ").strip()
    max_files = int(limit_input) if limit_input.isdigit() and int(limit_input) > 0 else None

    # 提取PDF
    print("\n开始提取PDF...")
    df = pdf_to_dataframe(
        pdf_source=pdf_folder,
        recursive=True,
        skip_non_platinum=skip_non_platinum,
        max_files=max_files
    )

    if not df.empty:
        # 保存全部数据（带版本管理）
        print(f"\n正在保存文件...")
        saved_file = save_with_version(df, "all_documents", also_save_latest=True)

        # 保存高质量文献（含铂+HER）
        high_quality = get_high_quality_docs(df)
        if not high_quality.empty:
            save_with_version(high_quality, "documents", "high_quality", also_save_latest=True)
            print(f"\n高质量文献（含铂+HER）: {len(high_quality)} 篇")

        # 保存高相关性文献（得分≥4）
        high_relevance = filter_by_relevance(df, min_score=4)
        if not high_relevance.empty and len(high_relevance) != len(high_quality):
            save_with_version(high_relevance, "documents", "high_relevance", also_save_latest=True)
            print(f"高相关性文献（得分≥4）: {len(high_relevance)} 篇")

        # 显示预览
        print("\n数据预览（前3行）:")
        preview_cols = ['file_name', 'total_pages', 'tokens',
                        'has_platinum_metals', 'has_her_parameters', 'relevance_score']
        print(df[preview_cols].head(3))

        # 统计信息
        print(f"\n统计信息:")
        print(f"  总文献数: {len(df)}")
        print(f"  总页数: {df['total_pages'].sum()}")
        print(f"  总tokens: {df['tokens'].sum():,}")
        print(f"  平均每篇tokens: {df['tokens'].mean():.0f}")
        print(f"  最大tokens/篇: {df['tokens'].max():,}")
        print(f"  最小tokens/篇: {df['tokens'].min():,}")

        # 检查是否有超过128K的文献
        over_limit = df[df['tokens'] > 128000]
        if not over_limit.empty:
            print(f"\n⚠ 警告: {len(over_limit)} 篇文献超过128K tokens限制")
            over_limit[['file_name', 'tokens']].to_csv("over_limit_docs.csv", index=False)
            print("  超限文献列表已保存到 over_limit_docs.csv")

        print(f"\n文件保存说明:")
        print(f"  - 每次运行都会生成带时间戳的新文件，不会覆盖")
        print(f"  - 同时保存 *_latest.csv 文件，方便快速访问最新结果")
        print(f"  - 建议定期清理旧文件或移动到备份文件夹")

        print(f"\n后续处理建议:")
        print(f"1. 使用高质量文献进行参数提取: documents_high_quality_latest.csv")
        print(f"2. 或按相关性排序: df.sort_values('relevance_score', ascending=False)")
        print(f"3. 筛选特定关键词: df[df['has_platinum_precursors']==True]")


# ==================== 程序入口 ====================

if __name__ == "__main__":
    # 运行主程序（交互式）
    main()

    # 如果想直接运行快速提取，取消下面的注释，并注释掉上面的 main()
    # df = quick_extract("./my_papers/", max_files=10)
    # save_with_version(df, "test_result")
    # print(f"提取完成，共 {len(df)} 篇文献")