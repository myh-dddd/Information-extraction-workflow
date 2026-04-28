import os


# 配置部分
input_dir = r"C:\Users\25757\PycharmProjects\文献采集\input(17~26年)\English"  # 输入文件夹路径
output_dir = r"C:\Users\25757\PycharmProjects\文献采集\output\english"  # 输出文件夹路径

# 创建输出文件夹
os.makedirs(output_dir, exist_ok=True)

# 全局文件计数器（用于连续命名）
global_file_counter = 1

# 统计信息
total_processed = 0
total_files_scanned = 0

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
    
    # 分割内容块（每篇文献） - 使用ER作为分隔符
    # ER表示End of Record，是Web of Science每篇文献的结束标记
    content_blocks = content.split('ER\n')
    file_processed_count = 0
    
    # 对每个内容块（每篇文献）进行处理
    for block_index, block in enumerate(content_blocks):
        # 更严格地检查空块
        if not block or not block.strip() or len(block.strip()) < 10:
            continue
        
        lines = block.strip().split('\n')
        title_content = []
        doi_content = []
        ab_content = []
        capturing_title = False
        capturing_doi = False
        capturing_ab = False

        # 检查是否有真正的内容（至少有一个有效字段）
        has_valid_content = False
        for line in lines:
            line = line.strip()
            if line and line.startswith(('PT ', 'AU ', 'TI ', 'AB ', 'DI ', 'DO ', 'DOI ')):
                has_valid_content = True
                break
        
        if not has_valid_content:
            continue
        
        # 逐行检查并处理
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查标题字段 TI
            if line.startswith('TI '):
                capturing_title = True
                capturing_doi = False
                capturing_ab = False
                title_line = line.split(' ', 1)[1] if len(line.split(' ', 1)) > 1 else ''
                if title_line:
                    title_content.append(title_line.strip())
            
            # 检查DOI字段
            elif line.startswith('DI ') or line.startswith('DO ') or line.startswith('DOI '):
                capturing_doi = True
                capturing_ab = False
                capturing_title = False
                doi_line = line.split(' ', 1)[1] if len(line.split(' ', 1)) > 1 else ''
                if doi_line:
                    doi_content.append(doi_line.strip())
            
            # 检查摘要字段
            elif line.startswith('AB '):
                capturing_ab = True
                capturing_doi = False
                capturing_title = False
                ab_line = line.split(' ', 1)[1] if len(line.split(' ', 1)) > 1 else ''
                if ab_line:
                    ab_content.append(ab_line.strip())
            
            # 如果是其他主要字段开始，停止所有捕获
            elif line.startswith(('PT ', 'AU ', 'SO ', 'VL ', 'IS ', 'BP ', 'EP ', 'DT ', 
                                 'PD ', 'PY ', 'DA ', 'UT ', 'PM ', 'TC ', 'ZB ', 'Z8 ', 
                                 'ZR ', 'ZS ', 'ZA ', 'Z9 ', 'D2 ', 'BE ', 'SE ')):
                capturing_doi = False
                capturing_ab = False
                capturing_title = False
            
            # 捕获多行的标题内容（标题可能跨多行）
            elif capturing_title:
                title_content.append(line.strip())
            
            # 捕获多行的DOI内容（理论上DOI应该在一行内，但以防万一）
            elif capturing_doi:
                doi_content.append(line.strip())
            
            # 捕获多行的摘要内容
            elif capturing_ab:
                ab_content.append(line.strip())

        # 只有当确实提取到内容时才保存
        if title_content or doi_content or ab_content:
            # 合并标题内容
            title_full = ' '.join(title_content).strip()
            # 合并DOI内容
            doi_full = ' '.join(doi_content).strip()
            # 合并摘要内容
            ab_full = ' '.join(ab_content).strip()
            
            # 确保至少有摘要内容才保存
            if ab_full:
                # 使用连续数字命名
                file_name = f"{global_file_counter}.txt"
                output_path = os.path.join(output_dir, file_name)
                
                # 写入文件
                with open(output_path, 'w', encoding='utf-8') as file:
                    # 写入标题
                    if title_full:
                        file.write(f"标题: {title_full}\n\n")
                    else:
                        file.write(f"标题: 无\n\n")
                    
                    # 写入DOI
                    if doi_full:
                        file.write(f"DOI: {doi_full}\n\n")
                    else:
                        file.write(f"DOI: 无\n\n")
                    
                    # 写入摘要
                    file.write(f"摘要: {ab_full}\n")
                
                print(f"  ✓ 已保存: {file_name}")
                if title_full:
                    print(f"    标题: {title_full[:50]}..." if len(title_full) > 50 else f"    标题: {title_full}")
                if doi_full:
                    print(f"    DOI: {doi_full}")
                
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
print(f"实际保存文件数: {len([f for f in os.listdir(output_dir) if f.endswith('.txt')])}")
print("=" * 60)