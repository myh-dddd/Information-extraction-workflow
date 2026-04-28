import os
import pandas as pd
from openai import OpenAI, AsyncOpenAI
import time
import json
import re
import asyncio
from typing import List, Dict, Optional, Tuple


class DeepSeekClassifier:
    def __init__(self, max_concurrent=3):
        """
        初始化分类器

        Args:
            max_concurrent: 最大并发数（同时调用API的次数）
        """
        # 在这里直接设置您的DeepSeek API密钥
        api_key = "sk-e331bd28d28c4335a67cd0008903cd5b"  # 请替换为您的真实密钥

        if not api_key:
            raise ValueError("请在代码中设置正确的DeepSeek API密钥")

        # 初始化同步和异步客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        # 最大并发数
        self.max_concurrent = max_concurrent

        # 定义相关性的判断prompt - 要求JSON输出
        self.prompt_template = """{topic}

Abstract:
{abstract}

Please output JSON format: {{"result": "include"}} or {{"result": "exclude"}}"""

        # 存储结果（使用字典保证顺序）
        self.results = {}

    def get_all_txt_files(self, directory):
        """
        递归获取目录下所有txt文件
        """
        txt_files = []

        if not os.path.exists(directory):
            print(f"❌ 目录不存在: {directory}")
            return txt_files

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.txt'):
                    rel_path = os.path.relpath(os.path.join(root, file), directory)
                    txt_files.append({
                        'path': os.path.join(root, file),
                        'filename': file,
                        'relative_path': rel_path,
                        'folder': os.path.basename(root) if root != directory else '根目录'
                    })

        # 按数字排序
        def extract_number(file_info):
            try:
                return int(os.path.splitext(file_info['filename'])[0])
            except ValueError:
                return 999999999

        txt_files.sort(key=extract_number)

        return txt_files

    def extract_title_doi_and_abstract(self, file_path):
        """从txt文件中提取标题、DOI和摘要（兼容中英文格式）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            title = None
            doi = None
            abstract = None

            lines = content.split('\n')

            # 提取标题（支持多种格式）
            for line in lines:
                line_stripped = line.strip()
                # 中文格式：标题: xxx 或 Title-题名: xxx 或 题名: xxx
                if line_stripped.startswith('标题:') or line_stripped.startswith('标题：'):
                    title = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else \
                    line_stripped.split('：', 1)[1].strip()
                    break
                elif 'Title-题名:' in line_stripped or 'Title-题名：' in line_stripped:
                    title = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else \
                    line_stripped.split('：', 1)[1].strip()
                    break
                elif line_stripped.startswith('题名:') or line_stripped.startswith('题名：'):
                    title = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else \
                    line_stripped.split('：', 1)[1].strip()
                    break
                # 英文格式：TI xxx（Web of Science格式）
                elif line_stripped.startswith('TI '):
                    title = line_stripped.split(' ', 1)[1].strip() if len(line_stripped.split(' ', 1)) > 1 else ''
                    break
                # 其他可能的标题格式
                elif line_stripped.startswith('Title:') or line_stripped.startswith('Title：'):
                    title = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else \
                    line_stripped.split('：', 1)[1].strip()
                    break

            # 查找DOI
            for line in lines:
                line_stripped = line.strip()
                if line_stripped.startswith('DOI:') or line_stripped.startswith('DOI：'):
                    doi = line_stripped.replace('DOI:', '').replace('DOI：', '').strip()
                    break
                # Web of Science格式：DI xxx 或 DO xxx
                elif line_stripped.startswith('DI ') or line_stripped.startswith('DO '):
                    doi = line_stripped.split(' ', 1)[1].strip() if len(line_stripped.split(' ', 1)) > 1 else ''
                    break

            # 查找摘要
            abstract_section = None
            # 中文格式
            if '摘要:' in content or '摘要：' in content:
                if '摘要:' in content:
                    abstract_section = content.split('摘要:', 1)[1].strip()
                else:
                    abstract_section = content.split('摘要：', 1)[1].strip()
            # 英文格式（Web of Science）
            elif 'AB ' in content:
                for line in lines:
                    if line.strip().startswith('AB '):
                        abstract_section = line.strip().split(' ', 1)[1] if len(line.strip().split(' ', 1)) > 1 else ''
                        # 继续读取多行摘要
                        idx = lines.index(line)
                        for next_line in lines[idx + 1:]:
                            next_stripped = next_line.strip()
                            if next_stripped and not next_stripped.startswith(
                                    ('PT ', 'AU ', 'TI ', 'DI ', 'DO ', 'SO ', 'PY ', 'ER ')):
                                abstract_section += ' ' + next_stripped
                            elif next_stripped.startswith(('PT ', 'AU ', 'TI ', 'DI ', 'DO ', 'SO ', 'PY ', 'ER ')):
                                break
                        break
            # 其他可能的摘要格式
            elif 'abstract:' in content.lower():
                for line in lines:
                    if 'abstract:' in line.lower():
                        abstract_section = line.split(':', 1)[1].strip() if ':' in line else ''
                        break

            abstract = abstract_section if abstract_section else content

            # 如果没有提取到标题，尝试使用文件名或设置为"无标题"
            if not title or title == "":
                title = os.path.basename(file_path).replace('.txt', '')

            # 如果DOI为空或只是"无"，设置为None
            if doi and (doi == "无" or doi.strip() == ""):
                doi = None

            return title, doi, abstract

        except Exception as e:
            print(f"读取文件失败 {file_path}: {str(e)}")
            return None, None, None

    def clean_json_response(self, text):
        """清洗JSON响应，提取JSON内容"""
        # 尝试提取markdown代码块中的JSON
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 尝试提取普通代码块中的JSON
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 如果没有代码块，直接返回清理后的文本
        return text.strip()

    async def is_related_async(self, abstract: str, topic: str, file_index: int, max_retries: int = 3) -> Tuple[
        int, Optional[bool], str]:
        """
        异步判断摘要是否相关

        Args:
            abstract: 摘要内容
            topic: 主题
            file_index: 文件索引（用于保证顺序）
            max_retries: 最大重试次数

        Returns:
            (file_index, is_related, error_message)
        """
        for attempt in range(max_retries):
            try:
                # 构建完整的prompt
                prompt = self.prompt_template.format(topic=topic, abstract=abstract[:2000])

                response = await self.async_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a literature screening assistant. Output JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=50,
                    temperature=0.1
                )

                result_text = response.choices[0].message.content.strip()

                # 清洗JSON
                cleaned_json = self.clean_json_response(result_text)

                # 解析JSON
                result_dict = json.loads(cleaned_json)

                # 检查JSON是否有效
                if 'result' not in result_dict or not result_dict['result']:
                    print(f"    [文件{file_index}] ⚠ JSON格式不完整，尝试重试 ({attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    else:
                        return (file_index, None, "JSON格式不完整")

                # 判断结果
                result_value = result_dict['result'].strip().lower()
                if result_value == "include":
                    return (file_index, True, "")
                elif result_value == "exclude":
                    return (file_index, False, "")
                else:
                    print(f"    [文件{file_index}] ⚠ 无法识别的结果值: {result_value}")
                    if attempt < max_retries - 1:
                        print(f"    [文件{file_index}] 尝试重试 ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(2)
                        continue
                    else:
                        return (file_index, None, f"无法识别的结果值: {result_value}")

            except json.JSONDecodeError as e:
                print(f"    [文件{file_index}] ⚠ JSON解析失败: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"    [文件{file_index}] 尝试重试 ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(2)
                    continue
                else:
                    return (file_index, None, f"JSON解析失败: {str(e)}")
            except Exception as e:
                print(f"    [文件{file_index}] ⚠ API调用失败: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"    [文件{file_index}] 尝试重试 ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(2)
                    continue
                else:
                    return (file_index, None, f"API调用失败: {str(e)}")

        return (file_index, None, "达到最大重试次数")

    async def process_file_async(self, file_info: Dict, topic: str, semaphore: asyncio.Semaphore):
        """
        异步处理单个文件

        Args:
            file_info: 文件信息字典 {'path': ..., 'filename': ..., 'index': ...}
            topic: 判断主题
            semaphore: 信号量，用于控制并发数
        """
        async with semaphore:  # 限制并发数
            file_index = file_info['index']
            filename = file_info['filename']
            file_path = file_info['path']
            folder = file_info.get('folder', '')

            print(f"\n[文件{file_index}] 开始处理: {folder}/{filename}")

            # 提取标题、DOI和摘要（同步操作）
            title, doi, abstract = await asyncio.to_thread(self.extract_title_doi_and_abstract, file_path)

            if not abstract:
                print(f"  [文件{file_index}] ⚠ 无法提取摘要，跳过")
                self.results[file_index] = {
                    'status': 'failed',
                    'filename': f"{folder}/{filename}" if folder else filename,
                    'file_index': file_index,
                    'doi': doi if doi else '无',
                    'title': title if title else '无',
                    'error': '提取失败'
                }
                return

            # 使用API判断相关性
            _, is_related, error_msg = await self.is_related_async(abstract, topic, file_index)

            if is_related is None:
                print(f"  [文件{file_index}] ❌ 判断失败: {error_msg}")
                self.results[file_index] = {
                    'status': 'failed',
                    'filename': f"{folder}/{filename}" if folder else filename,
                    'file_index': file_index,
                    'doi': doi if doi else '无',
                    'title': title if title else '无',
                    'error': error_msg
                }
            elif is_related:
                print(f"  ✅ 包含 (Pt基HER催化剂)")
                self.results[file_index] = {
                    'status': 'include',
                    'filename': f"{folder}/{filename}" if folder else filename,
                    'file_index': file_index,
                    'doi': doi if doi else '无',
                    'title': title if title else '无'
                }
            else:
                print(f"  ❌ 排除 (非Pt基或其他)")
                self.results[file_index] = {
                    'status': 'exclude',
                    'filename': f"{folder}/{filename}" if folder else filename,
                    'file_index': file_index,
                    'doi': doi if doi else '无',
                    'title': title if title else '无'
                }

    async def process_files_async(self, directory: str, topic: str, start_index: Optional[int] = None,
                                  end_index: Optional[int] = None):
        """
        异步处理多个文件

        Args:
            directory: 文件目录
            topic: 判断主题
            start_index: 起始文件编号（从1开始）
            end_index: 结束文件编号（包含）
        """
        print(f"开始处理目录: {directory}")
        print(f"判断主题: {topic[:200]}...")  # 只显示前200字符
        print(f"最大并发数: {self.max_concurrent}")

        # 递归获取所有txt文件
        all_txt_files = self.get_all_txt_files(directory)

        if not all_txt_files:
            print("⚠️ 未找到任何txt文件！")
            return

        print(f"\n找到 {len(all_txt_files)} 个txt文件")

        # 显示文件夹分布
        folder_counts = {}
        for f in all_txt_files:
            folder = f.get('folder', '根目录')
            folder_counts[folder] = folder_counts.get(folder, 0) + 1
        print("文件分布:")
        for folder, count in folder_counts.items():
            print(f"  - {folder}: {count} 个文件")

        # 应用范围过滤
        if start_index is not None and end_index is not None:
            print(f"处理范围: {start_index}-{end_index}")
            all_txt_files = all_txt_files[start_index - 1:end_index]
            file_indices = list(range(start_index, end_index + 1))
        elif start_index is not None:
            print(f"处理范围: 从{start_index}到末尾")
            all_txt_files = all_txt_files[start_index - 1:]
            file_indices = list(range(start_index, start_index + len(all_txt_files)))
        elif end_index is not None:
            print(f"处理范围: 从开始到{end_index}")
            all_txt_files = all_txt_files[:end_index]
            file_indices = list(range(1, end_index + 1))
        else:
            file_indices = list(range(1, len(all_txt_files) + 1))

        print(f"将处理 {len(all_txt_files)} 个文件")
        print("-" * 50)

        # 准备文件信息列表
        file_infos = []
        for file_info, file_index in zip(all_txt_files, file_indices):
            file_info['index'] = file_index
            file_infos.append(file_info)

        # 创建信号量来控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # 创建所有任务
        tasks = [
            self.process_file_async(file_info, topic, semaphore)
            for file_info in file_infos
        ]

        # 并发执行所有任务
        print(f"\n开始并发处理（最多同时处理 {self.max_concurrent} 个文件）...\n")
        await asyncio.gather(*tasks)

        print("\n" + "=" * 50)
        print("所有文件处理完成！")
        print("=" * 50)

    def process_files(self, directory: str, topic: str, start_index: Optional[int] = None,
                      end_index: Optional[int] = None):
        """
        同步入口，处理文件
        """
        # 运行异步任务
        asyncio.run(self.process_files_async(directory, topic, start_index, end_index))

    def save_to_excel(self, output_dir: str = ".", append_mode: bool = True):
        """
        将结果保存到Excel文件，输出 filename、doi、title 三列，支持追加模式
        """
        os.makedirs(output_dir, exist_ok=True)

        # 按照文件索引排序结果
        sorted_indices = sorted(self.results.keys())

        # 分类结果
        include_list = []
        exclude_list = []
        failed_list = []

        for idx in sorted_indices:
            result = self.results[idx]
            # 提取三列
            record = {
                'filename': result.get('filename', ''),
                'doi': result.get('doi', ''),
                'title': result.get('title', '')
            }

            if result['status'] == 'include':
                include_list.append(record)
            elif result['status'] == 'exclude':
                exclude_list.append(record)
            elif result['status'] == 'failed':
                failed_list.append(record)

        # 保存包含的文献（需要下载的）
        if include_list:
            include_path = os.path.join(output_dir, "需要下载_Pt基HER催化剂.xlsx")
            df_new = pd.DataFrame(include_list)

            if append_mode and os.path.exists(include_path):
                try:
                    df_existing = pd.read_excel(include_path)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    df_combined = df_combined.drop_duplicates(subset=['doi', 'filename'], keep='last')
                    df_combined.to_excel(include_path, index=False)
                    print(f"\n✅ 需要下载的文献已追加到: {include_path} (总数: {len(df_combined)})")
                except Exception as e:
                    print(f"⚠ 追加失败，将覆盖保存: {str(e)}")
                    df_new.to_excel(include_path, index=False)
                    print(f"✅ 需要下载的文献已保存到: {include_path} (数量: {len(df_new)})")
            else:
                df_new.to_excel(include_path, index=False)
                print(f"\n✅ 需要下载的文献已保存到: {include_path} (数量: {len(df_new)})")

        # 保存排除的文献（不需要下载的）
        if exclude_list:
            exclude_path = os.path.join(output_dir, "跳过下载_非Pt基或其他.xlsx")
            df_new = pd.DataFrame(exclude_list)

            if append_mode and os.path.exists(exclude_path):
                try:
                    df_existing = pd.read_excel(exclude_path)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    df_combined = df_combined.drop_duplicates(subset=['doi', 'filename'], keep='last')
                    df_combined.to_excel(exclude_path, index=False)
                    print(f"✅ 跳过的文献已追加到: {exclude_path} (总数: {len(df_combined)})")
                except Exception as e:
                    print(f"⚠ 追加失败，将覆盖保存: {str(e)}")
                    df_new.to_excel(exclude_path, index=False)
                    print(f"✅ 跳过的文献已保存到: {exclude_path} (数量: {len(df_new)})")
            else:
                df_new.to_excel(exclude_path, index=False)
                print(f"✅ 跳过的文献已保存到: {exclude_path} (数量: {len(df_new)})")

        # 保存失败文件
        if failed_list:
            failed_path = os.path.join(output_dir, "处理失败文件.xlsx")
            df_new = pd.DataFrame(failed_list)

            if append_mode and os.path.exists(failed_path):
                try:
                    df_existing = pd.read_excel(failed_path)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    df_combined = df_combined.drop_duplicates(subset=['filename'], keep='last')
                    df_combined.to_excel(failed_path, index=False)
                    print(f"⚠ 处理失败文件已追加到: {failed_path} (总数: {len(df_combined)})")
                except Exception as e:
                    print(f"⚠ 追加失败，将覆盖保存: {str(e)}")
                    df_new.to_excel(failed_path, index=False)
                    print(f"⚠ 处理失败文件已保存到: {failed_path} (数量: {len(df_new)})")
            else:
                df_new.to_excel(failed_path, index=False)
                print(f"⚠ 处理失败文件已保存到: {failed_path} (数量: {len(df_new)})")

        # 打印统计信息
        print("\n" + "=" * 50)
        print("本次处理统计:")
        print(f"需要下载 (Pt基HER催化剂): {len(include_list)}")
        print(f"跳过下载 (非Pt基或其他): {len(exclude_list)}")
        print(f"处理失败: {len(failed_list)}")
        print(f"总计: {len(include_list) + len(exclude_list) + len(failed_list)}")


def main():
    # 配置参数
    TXT_DIRECTORY = r"C:\Users\25757\PycharmProjects\文献采集\DOI筛选_input_chinese" # 包含文献txt的文件夹的位置目录
    OUTPUT_DIR = r"C:\Users\25757\PycharmProjects\文献采集\DOI筛选_output_chinese"  # 输出Excel文件夹的位置目录

    TOPIC = """筛选必须含有铂(Pt)的HER电催化剂文章。

    【硬性要求 - 必须同时满足】：
    1. 文献必须明确涉及铂（Pt）或铂基材料
       - 关键词：Pt、铂、platinum、铂基、Pt基、Pt-based
       - 包含：Pt单质、Pt合金、Pt纳米颗粒、Pt/C、Pt化合物

    2. 文献必须涉及HER（析氢反应）
       - 关键词：HER、析氢、析氢反应、氢析出、hydrogen evolution

    【标记为"include"的条件】：
    - 摘要中明确提到"Pt"或"铂" AND 提到"HER"或"析氢"
    - 即使主要研究其他金属，但包含Pt作为对比或参比

    【标记为"exclude"的条件】：
    - 完全不提及Pt或铂（即使提到HER也排除）
    - 完全不提及HER或析氢（即使提到Pt也排除）
    - 只提到其他金属如：Fe、Co、Ni、Mo、Ru、Ir、Pd等（不含Pt）
    - 只提到非金属催化剂、碳材料、MOF等（不含Pt）

    【重要】：
    - 只有同时包含Pt和HER才保留
    - 不确定时选择"exclude"

    输出JSON格式：{"result": "include"} 或 {"result": "exclude"}"""

    # 设置处理范围（None表示不限制）
    START_INDEX = 1  # 起始文件编号（从1开始）
    END_INDEX = None  # 结束文件编号（包含此文件）

    # 是否使用追加模式（True=追加，False=覆盖）
    APPEND_MODE = True

    # 设置最大并发数（同时调用API的次数）
    MAX_CONCURRENT = 3  # 建议设置为 3-5

    # 创建分类器实例
    print("初始化DeepSeek分类器...")
    print(f"最大并发数: {MAX_CONCURRENT}")

    try:
        classifier = DeepSeekClassifier(max_concurrent=MAX_CONCURRENT)
        print("✅ 分类器初始化成功")

        # 处理文件（使用TOPIC_SIMPLE或TOPIC）
        classifier.process_files(
            TXT_DIRECTORY,
            TOPIC,  # 使用简洁版提示词
            start_index=START_INDEX,
            end_index=END_INDEX
        )

        # 保存结果到Excel（追加模式）
        classifier.save_to_excel(OUTPUT_DIR, append_mode=APPEND_MODE)

    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
