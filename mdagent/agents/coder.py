"""Coder — 把步骤写成可执行代码。带上次报错时会自愈重写。"""

from ..state import AgentState
from ..utils import strip_code_fence

_FALLBACK_BOOTSTRAP = '''import os
import duckdb

DATA = os.environ["MDA_DATA"]
con = duckdb.connect()
con.execute("CREATE VIEW sales AS SELECT * FROM read_csv_auto('" + DATA + "/sales.csv')")'''

TEMPLATE = '''你是数据分析团队的 Coder。把分析步骤写成一段可直接运行的 Python 代码。

必须严格按下面的结构写，只把最后那条 SQL 换成你自己的：

```python
{bootstrap}

print(con.execute("""
SELECT ...
""").fetchdf().to_string(index=False))
```

可用表：{tables}

硬性要求：
- bootstrap 那几行原样保留，一个字都不要改，表已经建好视图了
- 表名和字段名只能用「表结构」里列出的
- 最后一行必须是 print(...)，不 print 就等于没答，前面查了也白查
- 不要把 MDA_DATA / MDA_DB 或变量名当表名
- 只输出代码，用 ```python 包裹'''


def system_prompt(state: AgentState) -> str:
    tables = state.get("tables") or ["sales"]
    return TEMPLATE.format(
        bootstrap=state.get("bootstrap") or _FALLBACK_BOOTSTRAP,
        tables="、".join(tables),
    )


def coder(llm, state: AgentState) -> dict:
    schema = state.get("schema") or "（未提供表结构，字段名需要你自行推断）"
    parts = [
        f"问题：{state['question']}",
        f"分析步骤：\n{state.get('plan', '')}",
        f"表结构：\n{schema}",
    ]
    if state.get("error"):
        parts.append(f"上一次执行报错，请修正：\n{state['error']}")
    elif state.get("reason") and state.get("code"):
        parts.append(f"上一次被 Critic 打回，原因：{state['reason']}\n请重写得更严谨。")

    reply = llm.chat(system_prompt(state), "\n\n".join(parts), role="coder")
    code = strip_code_fence(reply.text)

    trace = list(state.get("trace", []))
    trace.append({"node": "coder", "round": state.get("rounds", 0) + 1, "code": code})
    return {
        "code": code,
        "rounds": state.get("rounds", 0) + 1,
        "error": "",
        "trace": trace,
        "prompt_tokens": state.get("prompt_tokens", 0) + reply.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + reply.completion_tokens,
    }
