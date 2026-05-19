#!/bin/bash
# 自动运行所有批次的吸收任务
# 用法: bash run_all_batches.sh

cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp

echo "=== 开始批量吸收任务 ==="
echo "开始时间: $(date)"

# 650只ETF，每批50只，共13批次
for i in {0..12}; do
    start=$((i * 50))
    end=$((start + 50))
    echo ""
    echo "=== 批次 $((i+1))/13: $start - $end ==="
    python3 absorb_batch.py --incremental --start $start --end $end 2>&1 | tee "absorb_batch_${i}.log"
    echo "批次 $((i+1)) 完成: $(date)"
    sleep 5
done

echo ""
echo "=== 所有批次完成 ==="
echo "结束时间: $(date)"

# 最终统计
python3 -c "
import json
with open('etf_standard_data.json', 'r') as f:
    data = json.load(f)
total = len(data)
has = sum(1 for etf in data if etf.get('year_3_return') and etf.get('year_3_return') != 0)
print(f'最终覆盖率: {has}/{total} = {has/total*100:.1f}%')
" 2>&1 | tee final_stats.txt
