"""
发行人提取模块 - 从 ETF 名称中自动分离 ETF 名称和基金公司
可配置化，其他工具可传入自己的映射表
"""
from modules.data_cleaner import dedup_by_code

# 默认兜底发行人列表（按长度降序，长的先匹配）
DEFAULT_ISSUERS = sorted([
    "基金管理有限公司", "基金", "证券", "资产管理有限公司", "资产管理",
    "华泰柏瑞基金", "华泰柏瑞", "易方达", "华夏基金", "华夏", "华宝基金", "华宝",
    "天弘基金", "国泰基金", "国泰", "南方基金", "博时基金", "银华基金",
    "广发基金", "广发", "嘉实基金", "嘉实", "招商基金", "招商", "富国基金", "富国",
    "汇添富", "汇添富基金", "景顺长城", "景顺长城基金",
    "中欧基金", "鹏华基金", "鹏华", "万家基金", "建信基金", "工银瑞信", "工银",
    "交银施罗德", "兴证全球", "前海开源", "中银基金", "上投摩根",
    "国投瑞银", "长信基金", "长城基金", "财通基金", "创金合信",
    "金鹰基金", "大成基金", "融通基金", "西部利得", "新华基金",
    "华商基金", "诺安基金", "方正富邦", "东吴基金", "浙商基金",
    "中信保诚", "光大保德", "摩根士丹利", "农银汇理", "中海基金",
    "中加基金", "中信建投", "鑫元基金", "国联基金", "信达澳亚",
    "宏利基金", "太平基金", "永赢基金", "恒生前海", "汇安基金",
    "山西证券", "格林基金", "贝莱德", "路博迈", "国金基金",
    "英大基金", "兴银基金", "中泰资管", "申万菱信", "银河基金",
    "长盛基金", "红塔红土", "大摩基金", "德邦基金", "南华基金",
    "尚正基金", "瑞达基金", "富敦基金", "中科沃土", "华宸未来",
    "明亚基金", "华融基金", "红土创新", "华泰资管", "太平洋证券",
    "中原证券", "国海证券", "第一创业", "东方证券", "长江资管",
    "浙商资管", "财通资管",
], key=lambda x: -len(x))


def build_known_names(generated_data, name_key='name', issuer_key='issuer'):
    """
    从已有数据（如 etf_data_generated.json）构建已知 name→issuer 映射
    返回按 name 长度降序的字典
    """
    known = {}
    for item in generated_data:
        n = str(item.get(name_key, '')).strip()
        i = str(item.get(issuer_key, '')).strip()
        if n and i and n not in known:
            known[n] = i
    return dict(sorted(known.items(), key=lambda x: -len(x[0])))


def extract_name_issuer(raw_name, known_names=None, issuers=None):
    """
    从原始名称（如"沪深300ETF易方达"）中分离 ETF 名称和发行人
    优先级：已知映射 > 兜底列表后缀匹配
    返回 (name, issuer)
    """
    if known_names:
        for known_name, known_issuer in known_names.items():
            if known_name in raw_name:
                rest = raw_name.replace(known_name, '', 1).strip()
                if rest and len(rest) <= 12:
                    return known_name, known_issuer

    issuer_list = issuers or DEFAULT_ISSUERS
    for issuer in issuer_list:
        if raw_name.endswith(issuer):
            name = raw_name[:-len(issuer)].strip().rstrip('-')
            if name:
                return name, issuer

    return raw_name, ""
