# Quant Strategy Development Plan

> **For Hermes:** 先按本计划冻结需求与范围，不提前写实现代码。待用户确认后，再按 P0 -> P1 -> P2 逐阶段开发。

**Goal:** 在 `/root/project/quant_strategy` 中建设一个长期可维护的量化研究与回测项目，第一阶段先完成规则型最小闭环；第二阶段纳入 Alpha158 因子子集与因子评估；当前阶段不引入 LightGBM。

**Architecture:** 采用五层结构：`data -> factors -> strategy -> backtest -> reports`。第一阶段主线只依赖标准化行情数据和少量基础因子，保证可解释、可调试、可回测。Alpha158 不作为第一阶段主链路依赖，而是在规则闭环稳定后，以独立因子扩展与评估模块接入。

**Tech Stack:** Python 3.11, pandas, pyarrow, pyyaml, requests/httpx, loguru, unittest/pytest（二选一统一）, parquet 年分片存储。

---

## 0. 当前状态与范围冻结

### 当前状态

- `/root/project/quant_strategy` 已按用户要求清空，目前只保留空目录。
- 之前尝试过的 `Qlib + Alpha158 + LightGBM` 路线已不再保留为当前项目实现基础。
- 当前目标不是恢复旧项目，而是基于新需求重新制定开发计划。

### 本轮范围冻结

本轮只做 **需求与开发计划文档**，不做任何功能实现代码。

本计划确认后，再进入开发。

### 一阶段不做

- LightGBM
- Qlib 运行时依赖
- Alpha158 全量 158 因子实现
- 自动调参
- 多策略并行框架
- 复杂前端
- 生产级调度与部署系统

---

## 1. 项目目标

### 核心目标

构建一个可长期维护的 A 股量化项目，优先满足：

1. 可稳定拉取并标准化真实行情数据
2. 可基于基础因子生成规则型选股信号
3. 可进行低复杂度、可审计的历史回测
4. 可导出可读的回测与信号报告
5. 具备后续纳入 Alpha158 因子评估的清晰扩展点

### 设计原则

1. **先闭环，再扩展**：先做最小可解释策略，不先上 ML。
2. **分层清晰**：数据、因子、信号、执行、报告职责严格分离。
3. **真实数据优先**：所有回测与评估基于真实行情，不引入模拟数据作为正式结论。
4. **标准化契约**：所有下游模块统一消费标准 OHLCV 表。
5. **先验证，再判断**：策略有效性结论必须建立在完整回测和可检查输出之上。

---

## 2. 总体架构

### 项目结构

```text
/root/project/quant_strategy/
├── README.md
├── .gitignore
├── docs/
│   └── plans/
│       └── 2026-05-30-quant-strategy-development-plan.md
├── config/
│   ├── base.yaml
│   ├── local_windows.yaml
│   └── server_ubuntu.yaml
├── data/
│   ├── raw/
│   │   └── tushare/
│   ├── processed/
│   │   ├── daily/
│   │   └── factors/
│   └── reports/
├── scripts/
│   ├── fetch_data.py
│   ├── build_features.py
│   ├── build_alpha158.py
│   ├── evaluate_factors.py
│   ├── run_signal.py
│   └── run_backtest.py
├── src/
│   ├── __init__.py
│   ├── settings.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── tushare_client.py
│   │   ├── normalize.py
│   │   └── loader.py
│   ├── factors/
│   │   ├── __init__.py
│   │   ├── momentum.py
│   │   ├── trend.py
│   │   ├── liquidity.py
│   │   └── alpha158.py
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── factor_metrics.py
│   │   └── factor_selection.py
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── rules.py
│   │   └── portfolio.py
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── ledger.py
│   │   └── metrics.py
│   └── reports/
│       ├── __init__.py
│       └── export.py
└── tests/
    ├── test_settings.py
    ├── test_normalize.py
    ├── test_loader.py
    ├── test_factors.py
    ├── test_alpha158.py
    ├── test_rules.py
    ├── test_backtest.py
    └── test_factor_metrics.py
```

### 五层职责

#### 1. `data/`

只做真实行情获取与标准化，不做策略逻辑。

标准表固定为：

```text
date, ticker, open, high, low, close, volume, amount, is_tradable(optional; best-effort only)
```

说明：当前第三方 Tushare HTTP 代理已验证支持 `daily`、`trade_cal`、`index_weight`，但未验证到 `daily` 透传 `suspend_type`，且 `suspend` 接口不可用。因此 `is_tradable` 目前不能视为真实完整覆盖；当上游缺失停牌元数据时，系统仅以保守的 contract 占位方式写出该列。

#### 2. `factors/`

只做基础指标与 Alpha158 子集特征生成，不做买卖决策。

基础因子表与 Alpha158 因子表分文件独立存储、独立版本管理，不合并落盘，避免字段互相污染和回测复现歧义。

#### 3. `strategy/`

把因子转成规则信号，只输出“某日应持有什么”。

#### 4. `backtest/`

只负责执行和记账，不负责决定买什么。

#### 5. `reports/`

将策略结果导出成用户可读文件。

---

## 3. 配置设计

### `config/base.yaml`

```yaml
project:
  name: quant_strategy
  version: "0.1.0"

data_source:
  provider: tushare_http
  http_url: "http://api.tushare.pro"
  token: ${TUSHARE_TOKEN}
  component_index: "000300.SH"
  start_date: "2018-01-01"
  end_date: null

strategy:
  name: top_momentum_monthly
  universe: "csi300"
  benchmark_index: "000300.SH"
  rebalance: "monthly"
  signal_on: "last_trading_day"
  topk: 20
  min_amount_ma20: 50000000
  require_close_above_ma20: true

backtest:
  initial_capital: 1000000
  commission_bps: 3
  slippage_bps: 5
  benchmark: "000300.SH"

paths:
  raw_data: "data/raw"
  processed_data: "data/processed"
  report_output: "data/reports"

factors:
  momentum:
    periods: [5, 20, 60]
  trend:
    ma_periods: [20, 60]
  liquidity:
    ma_period: 20

alpha158:
  enabled: false
  mode: subset
  factor_subset:
    - ret_5
    - ret_10
    - ret_20
    - ret_60
    - ma_bias_20
    - ma_bias_60
    - std_20
    - amount_ratio_20
    - volume_ratio_20
    - corr_close_volume_20

evaluation:
  ic_window: 20
  rankic_window: 20
  group_count: 10
```

### 配置原则

1. `token` 支持 `${ENV_VAR}` 替换，由 `settings.py` 显式解析。
2. `data_source.component_index` 与 `strategy.universe` / `strategy.benchmark_index` 分离，避免“原始数据成分来源”和“策略股票池定义”混淆。
3. `alpha158.enabled` 默认关闭。
4. 第一阶段只用 `strategy` 下的基础规则字段。

---

## 4. 第一阶段策略定义

### 策略名称

`top_momentum_monthly`

### 策略规则

- 股票池：沪深300
- 调仓频率：月频
- 信号生成时点：每月最后一个交易日，使用 `T-1` 数据
- 排序因子：`ret_20`
- 过滤条件：
  - `close > ma_20`
  - `amount_ma_20 >= 50000000`
- 按 `ret_20` 降序取 `top 20`
- 权重：等权
- 持有到下个调仓日

### 为什么第一阶段选这个策略

1. 简单
2. 可解释
3. 易于排查未来函数与执行错误
4. 不依赖 ML
5. 可以作为后续 Alpha158 增强的基线策略

---

## 5. Alpha158 纳入方式与可行性评估

### 结论

Alpha158 **可以纳入开发计划**，但不应作为第一阶段主链路依赖。

### 推荐定位

Alpha158 在本项目中的角色是：

1. **第二阶段因子扩展模块**
2. **因子评估工具**
3. **规则增强候选因子来源**

而不是第一阶段的训练主引擎。

### 为什么不在第一阶段主线接入 Alpha158

1. 完整 Alpha158 工程复杂度高
2. 数据缺失与窗口问题更多
3. 第一阶段优先目标是把回测闭环做稳
4. 先做规则型基线，后续更容易判断 Alpha158 是否真的带来增益

### Alpha158 可行性评估

#### 数据可行性

当前标准表：

```text
date, ticker, open, high, low, close, volume, amount, is_tradable(optional)
```

这已经足以支持一批 Alpha158 风格的价量因子子集。

#### 计算可行性

如果股票池先限制在 `csi300`，日频下计算成本可控。

#### 工程可行性

建议第一批只实现 **Alpha158-compatible subset**，不追求完整 158 因子。

### Alpha158 第一批子集建议

#### 动量类

- `ret_5`
- `ret_10`
- `ret_20`
- `ret_60`
- `ma_bias_20`
- `ma_bias_60`

#### 波动类

- `std_20`
- `range_20`
- `atr_like_20`

#### 流动性类

- `amount_ratio_20`
- `volume_ratio_20`

#### 价量交互类

- `corr_close_volume_20`
- `corr_ret_volume_20`

### Alpha158 接入顺序

1. 先完成规则型回测基线
2. 再实现 `src/factors/alpha158.py`
3. 再做 `scripts/build_alpha158.py`
4. 再做 `scripts/evaluate_factors.py`
5. 根据 IC / RankIC / 分组收益结果，决定是否把个别因子并入规则策略

---

## 6. 文件清单与职责

### 数据层

#### `src/data/tushare_client.py`

职责：封装第三方 Tushare HTTP 请求。

最小功能：
- 初始化 token / base url
- `get_index_weight(index_code, start_date, end_date)`
- `get_daily(ts_code, start_date, end_date)`
- 重试与基础报错

#### `src/data/normalize.py`

职责：把原始返回统一成标准 OHLCV schema。

最小函数：
- `normalize_ohlcv(df)`

要求：
- 输出字段：`date, ticker, open, high, low, close, volume, amount`
- 可选字段：`is_tradable`，用于标记当日是否可交易；缺失时默认按 `True` 处理
- 日期转 `datetime64[ns]`
- `ts_code` 标准化为小写交易所前缀格式，例如 `000001.SZ -> sz000001`
- 按 `ticker, date` 排序


职责：读写 parquet 分片。

最小函数：
- `save_daily_partitions(df, output_root)`
- `load_daily(start_date, end_date, universe=None)`
- `load_factors(start_date, end_date, factor_set="base", universe=None)`

存储结构：

```text
data/processed/daily/year=2018/daily.parquet
```

因子表接口契约：
- `build_features.py` 输出的基础因子表至少包含：`date, ticker, close, ret_20, ma_20, close_above_ma20, amount_ma_20`
- 若上游 daily 表含 `is_tradable`，基础因子表应透传该列；若缺失则默认补 `True`
- `load_factors()` 的调用模式与 `load_daily()` 保持一致，策略层通过因子表读取信号所需字段，不直接回退到 daily 表自行拼接

### 基础因子层

#### `src/factors/momentum.py`

- `calc_ret(df, period)` -> `ret_{period}`

#### `src/factors/trend.py`

- `calc_ma(df, period)` -> `ma_{period}`
- `close_above_ma(df, period)` -> `close_above_ma{period}`

#### `src/factors/liquidity.py`

- `calc_amount_ma(df, period=20)` -> `amount_ma_20`
- `calc_volume_ma(df, period=20)` -> `volume_ma_20`

### Alpha158 因子层

#### `src/factors/alpha158.py`

职责：实现 Alpha158 子集，不依赖 Qlib。

最小函数：
- `build_alpha158_subset(df, config)`

要求：
- 输入标准 OHLCV 表
- 输出在原表上追加 Alpha158 子集列
- 每个因子按 `ticker` 分组滚动计算
- 严禁跨股票滚动
- Alpha158 结果单独落盘到独立因子文件，不与基础因子表混写

### 策略层

#### `src/strategy/portfolio.py`

- `equal_weight(tickers)` -> `{ticker: weight}`

#### `src/strategy/rules.py`

- `TopMomentumRule(config)`
- `generate_signals(signal_date, factor_data)`

逻辑：
- 过滤 `close_above_ma20`
- 过滤 `amount_ma_20`
- 按 `ret_20` 排序取 `topk`
- 等权输出

### 回测层

#### `src/backtest/ledger.py`

职责：记录现金、持仓、市值、交易。

#### `src/backtest/engine.py`

职责：日频推进回测。

关键要求：
- 调仓日使用 `T-1` 信号
- 先卖后买
- 扣除佣金与滑点
- 记录净值序列
- 当可用现金不足以按目标权重买入每个目标股票至少一手（100 股）时，按比例降低所有目标股票的买入数量，优先保持组合结构接近目标权重，禁止按买入顺序逐个耗尽现金

#### `src/backtest/metrics.py`

- 年化收益
- 最大回撤
- Sharpe
- 换手率

### 报告层

#### `src/reports/export.py`

输出：
- `summary.json`
- `equity_curve.csv`
- `trades.csv`
- `positions.csv`

---

## 7. 测试策略

### 核心原则

测试只验证**机械正确性与数据契约**，不在测试里固化“策略收益应该是多少”。

### 第一批测试文件

#### `tests/test_settings.py`

验证：
- `${ENV_VAR}` 替换正确
- 相对路径解析正确

#### `tests/test_normalize.py`

验证：
- 标准化后列名正确
- 日期类型正确
- 排序正确

#### `tests/test_loader.py`

验证：
- 分片保存路径正确
- 指定年份/区间加载正确

#### `tests/test_factors.py`

验证：
- `ret_20`
- `ma_20`
- `amount_ma_20`
- 严禁跨 ticker 污染

#### `tests/test_alpha158.py`

验证：
- Alpha158 子集列可生成
- 多 ticker 下滚动正确
- 窗口不足时按预期为 NaN

#### `tests/test_rules.py`

验证：
- 过滤正确
- 排序正确
- `topk` 正确
- 权重和为 1

#### `tests/test_backtest.py`

验证：
- 调仓日触发正确
- 信号使用 `T-1`
- 成本正确扣减
- 净值闭合
- 交易记录与持仓一致

#### `tests/test_factor_metrics.py`

验证：
- IC / RankIC 计算逻辑正确
- 分组收益分桶正确
- 未来收益标签至少从 `T+1` 起算，严禁使用 `T` 日收盘后不可得收益

---

## 8. 阶段开发顺序

### P0: 数据层闭环

目标：拉真实数据并标准化存储。

交付：
- `config/base.yaml`
- `src/settings.py`
- `src/data/tushare_client.py`
- `src/data/normalize.py`
- `src/data/loader.py`
- `scripts/fetch_data.py`
- 对应测试

验收：
- 能稳定拉取沪深300成分股日线
- 能按年分片保存 parquet

### P1: 基础因子闭环

目标：生成第一批基础规则因子。

交付：
- `ret_20`
- `ma_20`
- `amount_ma_20`
- `scripts/build_features.py`

验收：
- 因子表可抽样验证
- 无跨 ticker 计算错误

### P2: 规则策略 + 最小回测闭环

目标：第一条规则型策略跑通历史回测。

交付：
- `TopMomentumRule`
- `BacktestEngine`
- `Ledger`
- `metrics`
- `run_backtest.py`
- `run_signal.py`
- 报告导出

验收：
- 产出净值曲线
- 产出交易记录
- 产出 summary.json
- 回测结果附带已知偏差声明：第一版未处理停牌/涨跌停约束，可交易性假设偏乐观，收益可能略高估；第二阶段优先引入停牌过滤修正该偏差

### P2.5: Alpha158 子集接入与可行性评估

目标：在不引入 LightGBM 的前提下，验证 Alpha158 子集是否值得纳入策略增强。

交付：
- `src/factors/alpha158.py`
- `src/evaluation/factor_metrics.py`
- `src/evaluation/factor_selection.py`
- `scripts/build_alpha158.py`
- `scripts/evaluate_factors.py`

验收：
- 能产出 Alpha158 子集因子表
- 能计算 IC / RankIC / 分组收益
- 能输出因子评估报告

评估约束：
- 所有未来收益标签默认以 `T+1` 起算，至少滞后 1 个交易日
- 严禁把 `T` 日收盘后才可得的信息用于 `T` 日因子评估标签

### P3: 规则增强

目标：从 Alpha158 子集里选择少量有效因子，增强规则策略。

可能形式：
- 增加过滤条件
- 增加二级排序
- 做简单线性组合评分

验收：
- 与基线策略进行真实回测对比
- 给出是否值得保留的判断

### P4: 日报与信号输出

目标：支持日常使用。

交付：
- 当日候选池输出
- 当日目标持仓输出
- 策略日报文件

---

## 9. 风险与约束

### 风险 1：Tushare 数据口径

需明确：
- 是否前复权
- 股票池成分按哪个日期口径取

### 风险 2：未来函数

必须保证：
- 调仓信号使用 `T-1` 数据
- 回测执行与信号生成分离

### 风险 3：Alpha158 复杂度膨胀

必须控制：
- 第一批只做子集
- 不追求完整 158 因子

### 风险 4：回测引擎过早复杂化

第一版先不做：
- 停牌精细执行
- 涨跌停限制
- 复杂订单撮合

---

## 10. 本计划确认后的直接执行顺序

确认后按下面顺序进入开发：

1. 新建基础目录与空文件
2. 写 `config/base.yaml` 与 `src/settings.py` 测试
3. 实现数据层并跑通 `fetch_data.py`
4. 实现基础因子层并跑通 `build_features.py`
5. 实现最小规则策略与回测
6. 回测基线稳定后，再接 Alpha158 子集评估

---

## 11. 一句话结论

本项目第一阶段应做成：

> **Tushare 数据 + 标准化 parquet + 少量基础因子 + 规则型选股 + 简单回测 + 报告输出**

Alpha158 应该：

> **纳入开发计划，但作为第二阶段因子扩展与评估模块，不作为当前主链路依赖。**
