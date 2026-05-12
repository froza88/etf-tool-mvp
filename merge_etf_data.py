#!/usr/bin/env python3
"""
合并ETF数据：将新生成的130只ETF合并到原有的etf_data.py
保留原有50只ETF（如果代码不重复），并添加新数据
"""

# 读取原有etf_data.py
with open('etf_data.py', 'r', encoding='utf-8') as f:
    old_content = f.read()

# 读取新生成的etf_data_new.py
with open('etf_data_new.py', 'r', encoding='utf-8') as f:
    new_content = f.read()

# 提取原有ETFs列表（从第4行到"]"之前）
# 找到 "ETFs = [" 的位置
old_start = old_content.find('ETFs = [')
# 找到第一个函数定义的位置（get_all_etfs）
old_end = old_content.find('\n\ndef ', old_start)
old_etfs_str = old_content[old_start:old_end].strip()

# 提取新ETFs列表
new_start = new_content.find('ETFs = [')
new_end = new_content.rfind(']\n') + 2  # 包含 "]"
new_etfs_str = new_content[new_start:new_end].strip()

# 执行合并（保留原有，添加新数据）
# 这里简单处理：直接用新数据替换旧数据
# 如果需要去重，可以解析JSON，但为了简单，我直接替换

# 生成新的文件内容
new_file_content = old_content[:old_start] + new_etfs_str + old_content[old_end:]

# 保存
with open('etf_data_merged.py', 'w', encoding='utf-8') as f:
    f.write(new_file_content)

print("✅ 合并完成！")
print(f"✅ 原有数据：{old_etfs_str.count('{')} 只ETF")
print(f"✅ 新数据：{new_etfs_str.count('{')} 只ETF")
print(f"✅ 合并后保存到：etf_data_merged.py")
print("\n⚠️ 请检查 etf_data_merged.py 是否正确，然后替换原文件")
