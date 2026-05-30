# quant_strategy

一个面向 A 股规则型研究与回测的最小可用项目。当前主线是：

- 真实数据抓取
- 历史指数成分落盘
- 基础因子生成
- 规则型选股信号
- 最小可审计回测

当前默认策略是 `top_momentum_monthly`：

- 股票池：沪深 300 历史成分
- universe 过滤：主板在市股票，额外去掉 `ST/*ST`
- 排序因子：`ret_20`
- 过滤条件：`close > ma_20` 且 `amount_ma_20 >= 50,000,000`
- 调仓：月频，`T-1` 信号，`T` 日执行

## 当前能力

- `fetch_data.py`
  - 支持单票抓取：`--ts-code`
  - 支持指数成分批量抓取：`--component-index`
  - 会同时落盘：
    - 日线数据
    - 历史成分表
    - 停牌表
- `build_features.py`
  - 从标准化日线生成基础因子表
- `run_signal.py`
  - 在指定日期生成目标权重
- `run_backtest.py`
  - 使用历史成分约束后的 universe 跑最小回测并导出报告

## 数据目录

当前落盘结构：

```text
data/
├── raw/
│   ├── year=YYYY/daily.parquet
│   └── tushare/
│       ├── csi300_components/year=YYYY/components.parquet
│       └── suspends/year=YYYY/suspend.parquet
├── processed/
│   └── factors/
│       └── base/year=YYYY/factors.parquet
└── reports/
```

## 环境准备

建议使用项目虚拟环境：

```bash
cd /root/project/quant_strategy
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

当前配置默认从环境变量读取 token。`load_settings()` 会优先使用进程环境变量；如果项目根目录存在 `.env`，会在解析 `${TUSHARE_TOKEN}` 前自动加载，且不会覆盖已导出的同名环境变量。

```bash
# 方式一：写入项目根目录 .env（推荐，本地使用，不入 Git）
echo 'TUSHARE_TOKEN=your-real-token' > .env

# 方式二：直接导出到 shell
export TUSHARE_TOKEN='your-real-token'
```

### 排障

如果你已经修改了 `.env`，但请求仍然报 `token invalid`，优先检查当前 shell 是否残留旧的 `TUSHARE_TOKEN`。进程环境变量的优先级高于 `.env`，会覆盖文件里的新值。

```bash
# 查看当前 shell 是否已有旧值
echo "$TUSHARE_TOKEN"

# 清掉旧值后，让项目回退到读取 .env
unset TUSHARE_TOKEN
```

## 运行方式

### 1. 单票抓取

```bash
.venv/bin/python scripts/fetch_data.py \
  --config config/server_ubuntu.yaml \
  --ts-code 000001.SZ
```

### 2. 沪深 300 成分批量抓取

```bash
.venv/bin/python scripts/fetch_data.py \
  --config config/server_ubuntu.yaml \
  --component-index 000300.SH
```

### 3. 生成基础因子

```bash
.venv/bin/python scripts/build_features.py \
  --config config/server_ubuntu.yaml \
  --start-date 2024-01-01 \
  --end-date 2024-03-31
```

### 4. 生成某日信号

```bash
.venv/bin/python scripts/run_signal.py \
  --config config/server_ubuntu.yaml \
  --date 2024-01-31
```

### 5. 运行回测

```bash
.venv/bin/python scripts/run_backtest.py \
  --config config/server_ubuntu.yaml \
  --start-date 2024-01-31 \
  --end-date 2024-03-31
```

## 真实约束与已知限制

### `is_tradable`

当前第三方 Tushare HTTP 代理：

- `daily` 不稳定透传 `suspend_type`
- `suspend_d` 可用，已单独拉取并用于生成停牌表

因此当前 `is_tradable` 的真实来源是：

- 优先使用日线自带 `suspend_type`（若代理提供）
- 否则使用独立的 `suspend_d` 停牌表按 `date+ticker` 关联生成

### 回测执行层

当前回测已经支持：

- `T-1` 信号
- `100` 股整手
- 成本扣减
- 先卖后买
- 历史成分过滤后的 universe
- 停牌表支撑下的最小不可交易约束

但仍未覆盖：

- 涨停不能买
- 跌停不能卖
- 部分成交
- 更细粒度的成交撮合

## 测试

运行全量测试：

```bash
.venv/bin/python -m unittest
```

当前项目测试覆盖数据层、因子层、规则层、回测层和脚本入口。