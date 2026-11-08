# 守听 · 中继站 K-7（开发版）

一个给 AI 玩的文字游戏。玩法只有一条：`listen.cmd("指令")`。

> 玩家看 [`main`](../../tree/main) 分支的 README；这份是给改代码的人看的。

你是一班的值守员，被留下来维护一座深空中继站。上一班的人走了，没有交接，
只在桌上留了一张便条。站里每天有四个通讯窗口，接收机里有一段十四秒的信号，
一遍一遍地重复。

## 快速开始

```python
import listen          # 打包后的单文件
print(listen.cmd("help"))
print(listen.cmd("explore 3"))
```

开发时也可以直接跑引擎：`python run.py --new "status"`。

## 目录

```
listen/
├── listen.py       # 分发给 AI 的单文件：明文引擎 + 压缩的数据块
├── content.py      # 内容数据（只在这一支）：物品、地点、事件、配方、剧情
├── engine.py       # 引擎（只在这一支）：指令解析、时间、事件抽取、存档
├── build.py        # 打包：engine.py + content.py → listen.py
├── run.py          # 小驱动：python run.py --new "status"
├── README.md       # 这份
├── PROMPT.md       # 给 AI 玩家的说明（main 上也有同一份）
└── tests/
    ├── smoke.py    # 冒烟测试
    └── playtest.py # 目标驱动的机器人，自动跑到一个结局
```

## 打包做什么

`python build.py` 生成 `listen.py`：

1. **引擎明文**放在文件上半部分（`engine.py` 去掉 coding 行、docstring 和 dev import）。
2. 内容是 `content.py` 里的数据 → `json.dumps` → `zlib` → `base64`，写成 `_DATA`。
3. 文件末尾一句 `load_content(json.loads(zlib.decompress(...)))`。

**没有 exec / eval**。这是硬约束：AI 玩家会被安全策略拦在执行隐藏代码上，
所以引擎必须可读、数据必须只是数据。

## 测试

```bash
python tests/smoke.py                        # 每个指令打一遍
python tests/playtest.py                     # 机器人跑开发版到结局
LISTEN_MOD=listen python tests/playtest.py   # 同样跑一遍打包版
```

两个 playtest 应该输出完全一致的结果（固定 seed=11）。

## 扩展

- 加物品：`content.ITEMS`，顺手在某个 `LOCS[x]["drops"]` 里给它一个权重。
- 加事件：往 `content.EVENTS` 里追加一条。字段：
  `loc`（地点或 `any`）、`w`（权重）、`cond`（条件）、`once`、`cd`（冷却）、
  `pity`（保底系数）、`out`（结果）或 `opts`（需要抉择）。
  结果键：`text gain lose sta power injure flag secret unlock journal goto chance reset`。
- 改完跑 `python build.py` 重新打包；不要手改 `listen.py`。

## 已知不足

- 内容量只有一天的量：5 个地点、30 件物品、20 来个事件。
- 电力系统目前是软的，基本卡不住人，更像氛围。
- 三个结局共用同一个前置（解码 + 窗口），没有分叉路线。
