import pandas as pd
import re
from collections import Counter
import itertools
import string

# ============================================
# 自定义停用词（不依赖NLTK）
# ============================================
STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and',
    'any', 'are', 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below',
    'between', 'both', 'but', 'by', 'could', 'did', 'do', 'does', 'doing', 'down',
    'during', 'each', 'few', 'for', 'from', 'further', 'had', 'has', 'have', 'having',
    'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'i',
    'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'me', 'more', 'my', 'myself',
    'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought',
    'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'she', 'should', 'so',
    'some', 'such', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves',
    'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under',
    'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where', 'which',
    'while', 'who', 'whom', 'why', 'will', 'with', 'would', 'you', 'your', 'yours',
    'yourself', 'yourselves',
    # 学术类停用词
    'study', 'research', 'investigation', 'analysis', 'using', 'novel', 'new',
    'efficient', 'high', 'low', 'great', 'enhanced', 'improved', 'superior',
    'toward', 'towards', 'via', 'through', 'based', 'approach', 'method',
    'strategy', 'design', 'development', 'fabrication', 'synthesis',
    'application', 'performance', 'activity', 'efficiency'
}

# 词形还原的简单映射（手动处理常见变化）
LEMMA_MAP = {
    'nanosheets': 'nanosheet',
    'nanowires': 'nanowire',
    'nanoparticles': 'nanoparticle',
    'catalysts': 'catalyst',
    'electrocatalysts': 'electrocatalyst',
    'materials': 'material',
    'structures': 'structure',
    'properties': 'property',
    'activities': 'activity',
    'mechanisms': 'mechanism',
    'reactions': 'reaction',
    'studies': 'study',
    'methods': 'method',
    'approaches': 'approach',
    'strategies': 'strategy',
    'designs': 'design',
    'syntheses': 'synthesis',
    'fabrications': 'fabrication',
    'applications': 'application',
    'performances': 'performance',
    'efficiencies': 'efficiency'
}


def simple_lemmatize(word):
    """简单的词形还原"""
    return LEMMA_MAP.get(word, word)


# ============================================
# 关键词提取器（不依赖NLTK）
# ============================================
class KeywordExtractor:
    def __init__(self):
        # 领域关键词库（电催化/析氢）
        self.technical_terms = {
            # 贵金属催化剂
            'pt', 'platinum', 'pt-based', 'pt-based alloys', 'pt-alloy',
            'pd', 'palladium', 'ru', 'ruthenium', 'rh', 'rhodium',
            'ir', 'iridium', 'au', 'gold', 'ag', 'silver',
            'ptni', 'ptco', 'ptfe', 'ptcu', 'ptru', 'ptpd',
            # 非贵金属催化剂
            'ni', 'nickel', 'co', 'cobalt', 'fe', 'iron', 'cu', 'copper',
            'mo', 'molybdenum', 'w', 'tungsten', 'v', 'vanadium',
            'mn', 'manganese', 'cr', 'chromium', 'zn', 'zinc',
            'nife', 'nico', 'nimo', 'como', 'feco', 'nimn',
            # 过渡金属化合物
            'mos2', 'molybdenum disulfide', 'ws2', 'tungsten disulfide',
            'mose2', 'wse2', 'nise2', 'cose2', 'fes2',
            'mop', 'wp', 'nip', 'cop', 'fep', 'nipo',
            'mo2c', 'wc', 'nic', 'coc', 'mon', 'wn', 'nin', 'con',
            'mxene', 'mof', 'metal-organic framework', 'cof',
            # 碳材料
            'graphene', 'carbon nanotube', 'cnt', 'carbon nanofiber',
            'carbon cloth', 'carbon paper', 'carbon fiber', 'rgo',
            # 结构/形貌
            'single atom', 'single-atom', 'single atom catalyst',
            'core-shell', 'heterostructure', 'nanowire', 'nanosheet',
            'nanoparticle', 'nanorod', 'nanotube', 'nanoarray',
            # 性能
            'hydrogen evolution', 'her', 'electrocatalysis', 'water splitting',
            'overpotential', 'tafel slope', 'stability', 'durability',
            'activity', 'efficiency', 'mass activity',
            'turnover frequency', 'tof', 'faradaic efficiency',
            # 方法
            'dft', 'density functional theory', 'first-principles',
            'mechanism', 'kinetics', 'in-situ', 'operando',
            'volmer', 'heyrovsky', 'tafel',
            # 特性
            'defect', 'vacancy', 'edge', 'phase', '1t', '2h',
            'doping', 'alloy', 'composite', 'hybrid',
            'alkaline', 'acidic', 'neutral', 'ph-universal',
            'bifunctional', 'trifunctional'
        }
        self.stop_words = STOP_WORDS
        self.punctuation = string.punctuation

    def extract_keywords(self, title):
        """从标题中提取关键词"""
        title_lower = title.lower()
        extracted = []

        # 1. 匹配预定义的领域术语（支持多词短语）
        for term in self.technical_terms:
            if term in title_lower:
                extracted.append(term)

        # 2. 提取有意义的单词
        clean_title = title_lower.translate(str.maketrans('', '', self.punctuation))
        clean_title = clean_title.replace('-', ' ').replace('/', ' ')

        for word in clean_title.split():
            if len(word) <= 2:
                continue
            if word in self.stop_words:
                continue
            if not word.isalpha():
                continue
            lemma = simple_lemmatize(word)
            extracted.append(lemma)

        return list(set(extracted))


# ============================================
# 生成VOSviewer Corpus文件（XML格式，官方推荐）
# ============================================
def generate_vosviewer_corpus(keywords_list, output_file='vosviewer.corpus', min_freq=5):
    """生成VOSviewer官方Corpus文件（XML格式）"""
    all_keywords = [kw for sublist in keywords_list for kw in sublist]
    freq = Counter(all_keywords)

    # 筛选高频关键词
    high_freq = {kw for kw, count in freq.items() if count >= min_freq}

    print(f"总关键词出现次数: {len(all_keywords)}")
    print(f"唯一关键词数: {len(freq)}")
    print(f"高频关键词数（≥{min_freq}次）: {len(high_freq)}")
    print("\n高频关键词TOP30:")
    for kw, count in freq.most_common(30):
        print(f"  {kw}: {count}")

    # 生成VOSviewer Corpus XML文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<VOSviewer>\n')
        f.write('  <corpus>\n')

        doc_id = 0
        for keywords in keywords_list:
            filtered = [kw for kw in keywords if kw in high_freq]
            if filtered:
                doc_id += 1
                f.write(f'    <document id="{doc_id}">\n')
                f.write('      <title>Document ' + str(doc_id) + '</title>\n')
                f.write('      <text>\n')
                f.write('        ' + ' '.join(filtered) + '\n')
                f.write('      </text>\n')
                f.write('    </document>\n')

        f.write('  </corpus>\n')
        f.write('</VOSviewer>\n')

    print(f"\n已生成VOSviewer Corpus文件: {output_file} (包含 {doc_id} 篇文献)")
    return high_freq, freq


# ============================================
# 生成共现矩阵（可选，用于网络分析）
# ============================================
def generate_cooccurrence_matrix(keywords_list, high_freq_keywords, output_file='cooccurrence_matrix.csv'):
    """生成关键词共现矩阵"""
    # 过滤只保留高频关键词
    keywords_list_filtered = [
        [kw for kw in kw_list if kw in high_freq_keywords]
        for kw_list in keywords_list
    ]
    keywords_list_filtered = [kw_list for kw_list in keywords_list_filtered if kw_list]

    # 创建索引
    kw_list = sorted(list(high_freq_keywords))
    kw_index = {kw: i for i, kw in enumerate(kw_list)}

    # 初始化矩阵
    matrix = [[0] * len(kw_list) for _ in range(len(kw_list))]

    # 计算共现
    for keywords in keywords_list_filtered:
        for kw1, kw2 in itertools.combinations(keywords, 2):
            if kw1 != kw2:
                i, j = kw_index[kw1], kw_index[kw2]
                matrix[i][j] += 1
                matrix[j][i] += 1

    # 转换为DataFrame并保存
    df_matrix = pd.DataFrame(matrix, index=kw_list, columns=kw_list)
    df_matrix.to_csv(output_file)
    print(f"已生成共现矩阵: {output_file}")
    return df_matrix


# ============================================
# 主程序
# ============================================
def main():
    print("=" * 60)
    print("Pt基HER催化剂文献关键词共现分析")
    print("=" * 60)

    # 文件路径
    file_chinese = r'C:\Users\25757\PycharmProjects\3关键词共现分析\Chinese_需要下载_Pt基HER催化剂.xlsx'
    file_english = r'C:\Users\25757\PycharmProjects\3关键词共现分析\English_需要下载_Pt基HER催化剂.xlsx'

    print("\n步骤1: 加载文献数据")
    print("-" * 40)

    try:
        df_cn = pd.read_excel(file_chinese)
        df_en = pd.read_excel(file_english)
        df = pd.concat([df_cn, df_en], ignore_index=True)
        print(f"中文文献: {len(df_cn)} 篇")
        print(f"英文文献: {len(df_en)} 篇")
        print(f"共加载 {len(df)} 篇文献")
    except FileNotFoundError as e:
        print(f"文件未找到: {e}")
        print("请确认以下文件路径是否正确：")
        print(f"  1. {file_chinese}")
        print(f"  2. {file_english}")
        return
    except Exception as e:
        print(f"读取文件出错: {e}")
        return

    print("\n步骤2: 从标题提取关键词")
    print("-" * 40)

    extractor = KeywordExtractor()
    keywords_list = []

    for idx, row in df.iterrows():
        title = row['title']
        if pd.notna(title):
            keywords = extractor.extract_keywords(title)
            keywords_list.append(keywords)

        # 进度提示
        if (idx + 1) % 500 == 0:
            print(f"  已处理 {idx + 1} 篇文献...")

    print(f"成功处理 {len(keywords_list)} 篇文献")

    print("\n步骤3: 生成VOSviewer Corpus文件")
    print("-" * 40)

    high_freq_kw, freq = generate_vosviewer_corpus(
        keywords_list,
        output_file='vosviewer.corpus',
        min_freq=5  # 可调整此值，文献量大时建议5-10
    )

    print("\n步骤4: 生成共现矩阵（可选）")
    print("-" * 40)

    generate_cooccurrence_matrix(
        keywords_list,
        high_freq_kw,
        output_file='cooccurrence_matrix.csv'
    )

    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)
    print("\n生成的文件:")
    print("  1. vosviewer.corpus - VOSviewer Corpus文件（XML格式，推荐）")
    print("  2. cooccurrence_matrix.csv - 关键词共现矩阵（备用）")
    print("\n" + "=" * 60)
    print("VOSviewer 导入步骤:")
    print("=" * 60)
    print("  1. 打开VOSviewer")
    print("  2. 点击左侧 Create")
    print("  3. 选择 Create a map based on text data")
    print("  4. 选择 Read data from VOSviewer files")  # 注意：是VOSviewer files！
    print("  5. 在 VOSviewer corpus file 中，点击 Browse 选择 vosviewer.corpus")
    print("  6. 点击 Next -> 设置阈值 -> Finish")
    print("=" * 60)


if __name__ == "__main__":
    main()