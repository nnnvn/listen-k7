# 守听 · 中继站 K-7

一个给 AI 玩的文字游戏。玩法只有一条：`listen.cmd("指令")`。

你是一班的值守员，被留下来维护一座深空中继站。上一班的人走了，没有交接，
只在桌上留了一张便条。站里每天有四个通讯窗口，接收机里有一段十四秒的信号，
一遍一遍地重复。

## 快速开始

```python
import listen

print(listen.cmd("help"))
print(listen.cmd("status"))
print(listen.cmd("explore 3"))
```

- 多条指令用英文分号分隔，一次最多 8 条：`listen.cmd("goto mast; explore 3")`
- 每次返回的最后一行是 `📡` 状态栏（JSON），看它就够了
- 存档：同目录 `listen_save.json`，每次操作自动保存
- 重开：`listen.new_game(seed=None, force=True)`

## 指令

| 类别 | 指令 |
|---|---|
| 观察 | `status`｜`map`｜`look [物/地]`｜`inv`｜`quests`｜`achievements`｜`secrets` |
| 行动 | `explore [N]`｜`goto <地点>`｜`choose <编号>`｜`wait <小时>`｜`rest`｜`sleep` |
| 站务 | `shop`｜`buy`｜`sell`｜`sell junk`｜`recipes`｜`craft`｜`use`｜`repair` |
| 信号 | `listen`（只在通讯窗口有效） |
| 记录 | `journal [页码]`｜`journal add <文字>` |

## 世界门

这类游戏的全部节奏都来自"同一件事在不同条件下不同"：

- **通讯窗口**：每天 03、09、15、21 点各开两个小时。`listen` 只在窗口里有效。
- **昼夜与天气**：晴天的太阳能板会充电；太阳风时外面很吵；静电雾里能见度差。
- **工具**：塔基能徒手进，陨石坑要冰镐，残骸场要探照灯。
- **蓄电池**：接收机、探照灯都吃电，白天靠太阳补。

## 目录

```
listen/
├── listen.py       # 分发给 AI 的盲玩版（单文件，内容封在 base64 里）
├── content.py      # 内容数据：物品、地点、事件、配方、剧情
├── engine.py       # 引擎：指令解析、时间、事件抽取、存档
├── build.py        # 打包：content + engine → listen.py
├── run.py          # 开发时的小驱动：python run.py --new "status"
└── tests/
    └── playtest.py # 目标驱动的机器人，自动从开局跑到一个结局
```

## 扩展

- 加物品：`content.ITEMS`，顺手在某个 `LOCS[x]["drops"]` 里给它一个权重。
- 加事件：往 `content.EVENTS` 里追加一条。字段：
  `loc`（地点或 `any`）、`w`（权重）、`cond`（条件）、`once`、`cd`（冷却）、
  `pity`（保底系数）、`out`（结果）或 `opts`（需要抉择）。
  结果键：`text gain lose sta power injure flag secret unlock journal goto chance reset`。
- 改完跑 `python build.py` 重新打包；别手改 `listen.py` 里的 `_BLOB`。

## 已知不足

- 内容量只有一天的量：5 个地点、30 件物品、20 来个事件。想让玩家玩上几十天，得往里塞东西。
- 电力系统目前是软的，基本不会真的卡住人；它更像氛围。
- 三个结局共用同一个前置（解码 + 窗口），没有分叉路线。
