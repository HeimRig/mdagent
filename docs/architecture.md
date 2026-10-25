# 架构与设计取舍

## 1. 为什么要做成多角色

单 agent 直接"问题 → 代码"在数据分析场景下有两个硬伤：

1. **错了不知道**。代码跑通了但没回答问题（比如问"最高"却把整张明细打出来），
   没有第二双眼睛，这个错误会一路带进最终报告。
2. **错了不会修**。缺少"执行结果 → 判断 → 重写"的回路，一次写不对就结束。

所以拆成四个职责单一的角色：Planner 负责拆解、Coder 负责实现、Critic 负责验收、
Reporter 负责表达。好处是每个角色只有一个失败模式，出问题能定位到具体环节，
也方便单独做消融（去掉 Critic 会掉多少准确率）。

## 2. 四个机制

### 执行即验证
代码不是"生成完就交"，而是在子进程沙箱里真跑一遍，报错原文回灌给 Coder。
这一步把 LLM 的"看起来对"变成了"确实跑得起来的"。

### Schema 注入
把表结构、字段类型、样例行先拼进 Prompt 给 Planner。
不注入的话模型经常编字段名（比如把 city 写成城市），这是这类项目最常见的失败源。

### 自愈预算
最多 `MAX_REPAIR_ROUNDS` 轮（默认 3）。超了不硬编答案，
而是让 Reporter 明确输出"未能得到可靠结果"。**宁可承认失败，不给假数据**。

### 全链路 trace
每一步（prompt 产物、代码、stdout/stderr、Critic 判定）都记在 state["trace"] 里，
落盘到 runs/。评测复现和 debug 全靠它。

## 3. 状态机

```
plan ──▶ code ──▶ execute ──▶ critique ──┬─(通过)──▶ report ──▶ END
                  ▲                      │
                  └──────(打回/报错)──────┘
```

- `_route()` 决定 critique 之后走 code 还是 report
- 轮数到上限时强制走 report，由 Reporter 说明失败原因
- 用 LangGraph 的 `StateGraph` + `add_conditional_edges` 表达，
  没装 langgraph 时自动退化成等价的 `_run_loop()` 普通循环

## 4. 沙箱的边界

两个后端，`run_code()` 签名一致，切换只靠 `config.SANDBOX_BACKEND`（或 `MDA_SANDBOX`）：

| 后端 | 隔离手段 | 定位 |
|------|----------|------|
| `subprocess` | 子进程 + 超时 + 独立临时目录 + 抹掉 API_KEY/TOKEN/SECRET 环境变量 | 本机开发、CI，够快 |
| `docker` | `--network=none --read-only --tmpfs /tmp --memory 512m --cpus 1 --pids-limit 128`，数据目录只读挂载，脚本只读挂载 | 真隔离，敢跑不可信代码 |

`auto`（默认）先探 `docker image inspect mdagent-sandbox`，镜像在就用 docker，不在就回退
subprocess 并在报告里标出来。子进程后端**不是安全边界**——它能读文件系统、能联网，
README 和报告里都明说了，不假装它是。

docker 后端的镜像只装 duckdb + pandas（约 200MB），`make docker-image` 构建。

## 5. 评测为什么是重点

功能人人能写，能报出"准确率 52%、平均 1.7 轮自愈、平均 2.6k token，并且说清这个数字
有多不稳"的项目不多。

benchmark 共 27 题，覆盖 9 类题型（top1 / count / aggregate / groupby / filter /
timeseries / ratio / multistep / join），其中 join 组必须跨两张表。四条设计约束值得说明：

1. **答案键不能手敲**。每题配一条 reference SQL，`expect` 由 SQL 在数据集上实算得到
   （`make key`）。改数据就重算，不会出现"题目换了数据没换"的静默错误。
2. **期望值必须够长**。生成器会拒绝长度小于 4、且绝对值小于 100 的期望值——太短的
   数字（比如 `13`）会被任意表格里的其他数字误命中，把准确率虚高。
3. **判分要容忍四舍五入**。先做子串匹配，数字再走一次相对容差比较，
   避免 `49120.80` 与 `49120.8` 被判成两个答案。
4. **按题型出准确率**。整体一个数看不出问题在哪，分题型才能定位到
   "聚合类总忘 SUM"这种具体缺陷。
