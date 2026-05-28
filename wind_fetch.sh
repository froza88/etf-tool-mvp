#!/bin/bash
# Wind数据批量抓取 - Bash版本
# 循环调用Wind API，抓取风险指标

ETF_LIST="etfs_missing_wind.json"
CACHE_DIR="data/cache/wind"
WIND_CLI="/Users/apangduo/.agents/skills/wind-mcp-skill/scripts/cli.mjs"

echo "📋 开始Wind批量抓取..."
echo "ETF列表: $(cat $ETF_LIST | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))') 只"

# 创建缓存目录
mkdir -p "$CACHE_DIR"

# 读取ETF列表
ETFS=$(cat $ETF_LIST | python3 -c "
import json, sys
data = json.load(sys.stdin)
for etf in data:
    print(etf['code'] + '|' + etf.get('name', ''))
")

# 统计
SUCCESS=0
ERROR=0
SKIP=0
TOTAL=$(echo "$ETFS" | wc -l)

# 主循环
I=0
echo "$ETFS" | while IFS='|' read -r CODE NAME; do
    I=$((I + 1))
    
    # 检查是否已抓取
    CACHE_FILE="$CACHE_DIR/${CODE}_risk.json"
    if [ -f "$CACHE_FILE" ]; then
        SKIP=$((SKIP + 1))
        if [ $((I % 100)) -eq 0 ]; then
            echo "⏭️  [$I/$TOTAL] 跳过 $CODE (已存在)"
        fi
        continue
    fi
    
    echo "🔄 [$I/$TOTAL] 抓取 $CODE $NAME..."
    
    # 调用Wind API
    QUESTION="查询${CODE}${NAME}的夏普比率近1年、年化波动率近1年、最大回撤近1年"
    
    OUTPUT=$(node $WIND_CLI call analytics_data get_financial_data "{\"question\":\"$QUESTION\"}" 2>&1)
    
    # 检查是否成功
    if echo "$OUTPUT" | grep -q '"text"'; then
        # 提取text字段并保存
        echo "$OUTPUT" | python3 -c "
import json, sys
try:
    output = sys.stdin.read()
    response = json.loads(output)
    text_str = response['content'][0]['text']
    data_obj = json.loads(text_str)
    
    # 提取数据
    data_list = data_obj.get('data', {}).get('data', [])
    if data_list:
        columns = data_list[0].get('columns', [])
        rows = data_list[0].get('rows', [])
        if rows:
            col_map = {col['name']: idx for idx, col in enumerate(columns)}
            row = rows[0]
            
            risk_data = {
                'windcode': '$CODE.OF',
                'name': '$NAME',
                'fetched_at': '$(date -Iseconds)'
            }
            
            for col_name, idx in col_map.items():
                if idx >= len(row): continue
                val = row[idx]
                if not val: continue
                
                if '夏普' in col_name or 'SHARPE' in col_name.upper():
                    risk_data['sharpe_1y'] = float(val)
                elif '波动率' in col_name or 'VOLATILITY' in col_name.upper():
                    risk_data['volatility_1y'] = float(val)
                elif '回撤' in col_name or 'DRAWDOWN' in col_name.upper():
                    risk_data['max_drawdown_1y'] = float(val)
            
            print(json.dumps(risk_data, ensure_ascii=False))
        else:
            print('ERROR: rows为空')
    else:
        print('ERROR: data_list为空')
except Exception as e:
    print(f'ERROR: {e}')
" > "$CACHE_FILE.tmp" 2>&1
        
        if [ -s "$CACHE_FILE.tmp" ] && ! grep -q "ERROR" "$CACHE_FILE.tmp"; then
            mv "$CACHE_FILE.tmp" "$CACHE_FILE"
            SUCCESS=$((SUCCESS + 1))
            SHARPE=$(cat "$CACHE_FILE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sharpe_1y', 'N/A'))")
            echo "✅ 成功 sharpe=$SHARPE"
        else
            rm -f "$CACHE_FILE.tmp"
            ERROR=$((ERROR + 1))
            echo "❌ 解析失败"
        fi
    else
        ERROR=$((ERROR + 1))
        echo "❌ API调用失败: ${OUTPUT:0:80}"
    fi
    
    # 限速
    sleep 1
    
    # 每10只显示统计
    if [ $((I % 10)) -eq 0 ]; then
        echo "📊 进度: $I/$TOTAL | ✅$SUCCESS ❌$ERROR ⏭️$SKIP"
    fi
done

echo ""
echo "============================================================"
echo "✅ Wind抓取完成"
echo "📊 总计: $TOTAL 只ETF"
echo "   成功: $SUCCESS"
echo "   失败: $ERROR"
echo "   跳过: $SKIP"
echo "============================================================"
