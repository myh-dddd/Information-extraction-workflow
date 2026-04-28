import os
import re

# 配置部分
input_dir = r"C:\Users\25757\PycharmProjects\文献采集\spilt_input(17~26年)\Chinese"  # 输入文件夹路径
output_dir = r"C:\Users\25757\PycharmProjects\文献采集\spilt_output\chinese"  # 输出文件夹路径

# 创建输出文件夹
os.makedirs(output_dir, exist_ok=True)

# 全局文件计数器（用于连续命名）
global_file_counter = 1

# 统计信息
total_processed = 0
total_files_scanned = 0
files_with_doi = 0
files_without_doi = 0
files_with_title = 0
files_without_title = 0

print("=" * 60)
print("开始处理文献文件...")
print("=" * 60)

# 获取输入文件夹中的所有txt文件
txt_files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]

if not txt_files:
    print(f"错误：在 {input_dir} 中未找到任何txt文件！")
    exit()

print(f"找到 {len(txt_files)} 个txt文件\n")

# 处理每个txt文件
for txt_file in txt_files:
    input_file = os.path.join(input_dir, txt_file)
    total_files_scanned += 1
    
    print(f"正在处理: {txt_file}")
    print("-" * 60)
    
    # 读取原始txt文件
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        print(f"  错误：无法读取文件 {txt_file}: {e}")
        continue
    
    # 分割内容块（每篇文献）
    content_blocks = content.split('\n\n')
    file_processed_count = 0
    
    # 对每个内容块（每篇文献）进行处理
    for block_index, block in enumerate(content_blocks):
        block = block.strip()
        if not block or len(block) < 50:
            continue
        
        lines = block.split('\n')
        
        # 初始化变量
        doi_content = ""
        summary_content = ""
        title_content = ""
        capturing_doi = False
        capturing_summary = False
        capturing_title = False
        temp_doi_lines = []
        temp_summary_lines = []
        temp_title_lines = []

        # 检查是否有真正的内容
        has_valid_content = False
        for line in lines:
            line = line.strip()
            if line and ('Summary-摘要:' in line or '摘要:' in line or 'DOI-DOI:' in line or 'DOI:' in line or 'Title-题名:' in line or '题名:' in line):
                has_valid_content = True
                break
        
        if not has_valid_content:
            continue
        
        # 逐行检查并处理
        for line in lines:
            line = line.strip()
            if not line:
                if capturing_summary:
                    capturing_summary = False
                continue
            
            # 1. 检查标题字段
            if 'Title-题名:' in line:
                capturing_title = True
                capturing_doi = False
                capturing_summary = False
                if ':' in line:
                    title_part = line.split(':', 1)[1].strip()
                    if title_part:
                        title_content = title_part
                        capturing_title = True
            
            # 2. 检查其他标题格式
            elif not title_content and any(title_marker in line for title_marker in ['题名:', '标题:', 'Title:', '篇名:']):
                capturing_title = True
                capturing_doi = False
                capturing_summary = False
                if ':' in line:
                    title_part = line.split(':', 1)[1].strip()
                    if title_part:
                        title_content = title_part
                        capturing_title = True
            
            # 3. 检查DOI字段
            elif 'DOI-DOI:' in line:
                capturing_doi = True
                capturing_summary = False
                capturing_title = False
                if ':' in line:
                    doi_part = line.split(':', 1)[1].strip()
                    if doi_part:
                        doi_content = doi_part
                        capturing_doi = False
            
            # 4. 检查其他DOI格式
            elif not doi_content and ('DOI:' in line or 'doi:' in line):
                capturing_doi = True
                capturing_summary = False
                capturing_title = False
                if ':' in line:
                    doi_part = line.split(':', 1)[1].strip()
                    if doi_part:
                        doi_content = doi_part
                        capturing_doi = False
            
            # 5. 检查摘要字段
            elif 'Summary-摘要:' in line:
                capturing_summary = True
                capturing_doi = False
                capturing_title = False
                if ':' in line:
                    summary_part = line.split(':', 1)[1].strip()
                    if summary_part:
                        summary_content = summary_part
            
            # 6. 检查其他摘要格式
            elif not summary_content and '摘要:' in line:
                capturing_summary = True
                capturing_doi = False
                capturing_title = False
                if ':' in line:
                    summary_part = line.split(':', 1)[1].strip()
                    if summary_part:
                        summary_content = summary_part
            
            # 7-10. 捕获多行内容
            elif capturing_title:
                if ':' in line and any(field in line for field in ['Summary-摘要', '摘要', '关键词', 'DOI-DOI', 'DOI', 'doi', '作者', '机构']):
                    capturing_title = False
                else:
                    temp_title_lines.append(line.strip())
            
            elif capturing_doi:
                if ':' in line and any(field in line for field in ['Summary-摘要', '摘要', '关键词', '作者', '机构']):
                    capturing_doi = False
                else:
                    temp_doi_lines.append(line.strip())
            
            elif capturing_summary:
                if ':' in line and any(field in line for field in ['关键词', '关键字', 'Key words', 'Keywords', '作者', '机构', '中图分类号']):
                    capturing_summary = False
                else:
                    temp_summary_lines.append(line.strip())
            
            elif ':' in line and any(field in line for field in ['作者', 'Author', '机构', 'Organ', 'Source', '文献来源', '关键词']):
                capturing_doi = False
                capturing_summary = False
                capturing_title = False

        # 处理收集到的多行内容
        if temp_title_lines:
            if title_content:
                title_content += ' ' + ' '.join(temp_title_lines).strip()
            else:
                title_content = ' '.join(temp_title_lines).strip()
        
        if temp_doi_lines and not doi_content:
            doi_content = ' '.join(temp_doi_lines).strip()
        
        if temp_summary_lines:
            if summary_content:
                summary_content += ' ' + ' '.join(temp_summary_lines).strip()
            else:
                summary_content = ' '.join(temp_summary_lines).strip()
        
        # 清理内容
        if title_content:
            title_content = re.sub(r'\s+', ' ', title_content).strip()
            if len(title_content) > 100:
                title_content = title_content[:100]
        
        if summary_content:
            summary_content = re.sub(r'(关键词|关键字|Key words|Keywords).*$', '', summary_content)
            summary_content = re.sub(r'\s+', ' ', summary_content).strip()
        
        # 只有当确实提取到摘要内容时才保存
        if summary_content:
            # 使用连续数字命名
            file_name = f"{global_file_counter}.txt"  # 直接使用数字，如1.txt, 2.txt, 3.txt
            output_path = os.path.join(output_dir, file_name)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as file:
                if title_content:
                    file.write(f"标题: {title_content}\n\n")
                
                if doi_content:
                    file.write(f"DOI: {doi_content}\n\n")
                    files_with_doi += 1
                else:
                    file.write(f"DOI: 无\n\n")
                    files_without_doi += 1
                
                file.write(f"摘要: {summary_content}\n")
                
                if title_content:
                    files_with_title += 1
                else:
                    files_without_title += 1
            
            print(f"  ✓ 已保存: {file_name}")
            if title_content:
                print(f"    标题: {title_content[:40]}...")
            if doi_content:
                print(f"    DOI: {doi_content}")
            
            global_file_counter += 1
            file_processed_count += 1
            total_processed += 1
    
    print(f"  从 {txt_file} 中提取了 {file_processed_count} 篇文献\n")

# 最终统计
print("=" * 60)
print("处理完成！")
print("=" * 60)
print(f"扫描的txt文件数: {total_files_scanned}")
print(f"提取的文献总数: {total_processed}")
print(f"输出文件夹: {output_dir}")
print()
print("详细统计:")
print(f"  - 有DOI的文献: {files_with_doi}")
print(f"  - 无DOI的文献: {files_without_doi}")
print(f"  - 有标题的文献: {files_with_title}")
print(f"  - 无标题的文献: {files_without_title}")
print("=" * 60)
