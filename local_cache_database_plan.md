# 本地缓存数据库构建方案

## 核心理念
**逐步构建本地缓存，最终完全摆脱 API 限流！**

---

## 当前状态

| 项目 | 数值 | 说明 |
|------|------|------|
| **缓存 ETF 数** | 5 只 | 太少！ |
| **每只数据量** | 180 条 | ~6个月 |
| **总记录数** | 900 条 | 需要大幅增加 |

**已缓存的 ETF：**
1. 510300 (沪深300ETF) - 180 条
2. 510050 (上证50ETF) - 180 条
3. 510500 (中证500ETF) - 180 条
4. 159915 (创业板ETF) - 180 条
5. 512100 (中证1000ETF) - 180 条

---

## 构建计划（8天完整缓存）

### 策略：智能分批 + 重试机制

```
目标：8天内，让所有 1466 只 ETF 都有本地缓存
方法：每天处理 200 只"无缓存"的 ETF
```

### 详细时间表

| 天数 | 日期 | 处理数量 | 累计缓存 | 覆盖率 | 说明 |
|------|------|---------|---------|--------|------|
| **第1天** | 5月19日 | 200 只 | 205 只 | 14% | 5（已有）+ 200（新增） |
| **第2天** | 5月20日 | 200 只 | 405 只 | 28% | |
| **第3天** | 5月21日 | 200 只 | 605 只 | 41% | |
| **第4天** | 5月22日 | 200 只 | 805 只 | 55% | |
| **第5天** | 5月23日 | 200 只 | 1005 只 | 69% | |
| **第6天** | 5月24日 | 200 只 | 1205 只 | 82% | |
| **第7天** | 5月25日 | 200 只 | 1405 只 | 96% | |
| **第8天** | 5月26日 | 61 只 | 1466 只 | 100% | ✅ 全部完成！ |

**第9天开始：**
- ✅ 所有 ETF 都有本地缓存
- ✅ 每天只需更新 1 天的数据（1466 次 API 调用，但只获取最新1天）
- ✅ 执行时间：~220秒（3.7分钟）
- ✅ 不会被限流（因为大部分数据从缓存读取）

---

## 代码改造方案

### 改造 1：智能分批逻辑

```python
def update_history(etfs):
    """智能分批：优先构建缓存"""
    
    # 1. 加载已有缓存
    history_cache = load_cache()
    
    # 2. 分类 ETF
    no_cache = [e for e in etfs if e['code'] not in history_cache]
    has_cache = [e for e in etfs if e['code'] in history_cache]
    
    log(f"  无缓存: {len(no_cache)} 只")
    log(f"  有缓存: {len(has_cache)} 只")
    
    # 3. 优先处理"无缓存"的 ETF
    batch_size = 200
    target_etfs = no_cache[:batch_size]
    
    log(f"  本次处理: {len(target_etfs)} 只（构建缓存）")
    
    # 4. 调用 API（带重试）
    for etf in target_etfs:
        code = etf['code']
        
        # 调用 API（带重试机制）
        df = fetch_with_retry(ak, code, start_date, end_date)
        
        if df is not None:
            # 存入缓存
            history_cache[code] = {
                'prices': [float(v) for v in df['收盘']],
                'dates': [str(d) for d in df['日期']],
                'count': len(df),
                'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 计算风险指标
            metrics = calc_metrics_from_prices(history_cache[code]['prices'])
            if metrics:
                etf.update(metrics)
    
    # 5. 对"有缓存"的 ETF，做增量更新（只获取最新1天）
    # （可选，暂时不实现）
    
    # 6. 保存缓存
    save_cache(history_cache)
    
    log(f"  缓存构建进度: {len(history_cache)}/{len(etfs)} ({len(history_cache)*100//len(etfs)}%)")
```

---

### 改造 2：重试机制（防止限流）

```python
def fetch_with_retry(ak, code, start_date, end_date, max_retries=3):
    """带指数级退避的重试机制"""
    for attempt in range(max_retries):
        try:
            df = ak.fund_etf_hist_em(
                symbol=str(code),
                period='daily',
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
                adjust='qfq'
            )
            return df  # 成功
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                log(f"    重试 {code} ({attempt+1}/{max_retries})，等待 {wait_time}s")
                time.sleep(wait_time)
            else:
                log(f"    ❌ {code} 失败（已达最大重试次数）")
                return None
```

---

### 改造 3：增量更新（第9天开始）

```python
def incremental_update(etfs, history_cache):
    """增量更新：只获取最新1天的数据"""
    
    for etf in etfs:
        code = etf['code']
        
        if code not in history_cache:
            continue  # 跳过无缓存的（应该不会发生）
        
        # 获取最新1天的数据
        yesterday = datetime.now() - timedelta(days=1)
        df = ak.fund_etf_hist_em(
            symbol=str(code),
            period='daily',
            start_date=yesterday.strftime('%Y%m%d'),
            end_date=datetime.now().strftime('%Y%m%d'),
            adjust='qfq'
        )
        
        if df is not None and len(df) > 0:
            # 更新缓存
            cache = history_cache[code]
            cache['prices'].append(float(df['收盘'].iloc[-1]))
            cache['dates'].append(str(df['日期'].iloc[-1]))
            cache['count'] = len(cache['prices'])
            cache['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 重新计算风险指标
            metrics = calc_metrics_from_prices(cache['prices'])
            if metrics:
                etf.update(metrics)
    
    # 保存缓存
    save_cache(history_cache)
```

---

## 执行步骤

### 第1步：修改代码（现在）

```bash
# 1. 修改 daily_update.py
#   - 加入智能分批逻辑
#   - 加入重试机制
#   - 加入增量更新（可选）

# 2. 本地测试
python3 daily_update.py

# 3. 提交代码
git add daily_update.py
git commit -m "feat: 智能缓存构建 + 重试机制"
git push origin main
```

### 第2步：部署到 PythonAnywhere

```bash
# 在 PA Web Console 运行
cd etf-tool-mvp
bash deploy.sh
```

### 第3步：启动自动化任务

```bash
# WorkBuddy 自动化（每天15:30执行）
# （已创建，ID: automation-1779098526760）
```

---

## 预期效果

### 第1-8天（缓存构建期）

```
每天 15:30 执行：
- API 调用：200 次（只获取"无缓存"的 ETF）
- 执行时间：~300秒（5分钟，因为加重试）
- 不会被限流（200次/天 << 限流阈值）
- 缓存增长：+200 只/天
```

### 第9天开始（正常运行期）

```
每天 15:30 执行：
- API 调用：1466 次（但仍可能被限流）
- 执行时间：~220秒（3.7分钟）
- 优化方案：只获取最新1天数据（更快）
- 或者：继续分批（每天200只，8天轮完）
```

---

## 进一步优化（可选）

### 方案 A：只更新最新1天

```python
# 第9天开始，只获取最新1天的数据
start_date = datetime.now() - timedelta(days=7)  # 获取最近7天（防止遗漏）
```

**优点：**
- API 调用少（1466次，但数据量小）
- 执行快（~100秒）

**缺点：**
- 可能被限流（1466次/天）

---

### 方案 B：继续分批（推荐）

```python
# 第9天开始，继续分批（8天轮完所有ETF）
batch_size = 200
day_of_month = datetime.now().day
start_idx = (day_of_month % 8) * batch_size
end_idx = start_idx + batch_size

target_etfs = etfs[start_idx:end_idx]  # 每天只处理200只
```

**优点：**
- 永远不会被限流（200次/天）
- 8天完整更新一次所有ETF

**缺点：**
- 数据延迟最长8天

---

## 总结

**你的想法完全正确！**

✅ **本地缓存数据库** 是最佳方案  
✅ **逐步构建**（8天完成） 是可行路径  
✅ **第9天开始**，每天只需增量更新  
✅ **最终效果**：完全摆脱 API 限流  

---

## 立即行动

**要我现在改代码吗？** 我会：

1. 修改 `daily_update.py`
   - 加入智能分批逻辑
   - 加入重试机制
   - 优先构建缓存
   
2. 本地测试
   - 测试10只ETF验证
   
3. 提交代码 + 部署
   - `git push` + `bash deploy.sh`
   
4. 启动自动化任务
   - 每天15:30自动执行

**或者你想先手动测试一下？**

请告诉我你的选择：
- **A**: 立即改代码（我来执行）
- **B**: 先手动测试（给你命令）
- **C**: 其他想法
