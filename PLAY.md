# 给 AI 玩家的说明（可复制粘贴）

你将要玩一个文字游戏《守听》。它只有一个接口：`listen.cmd("指令")`，返回一段文字。

## 规则

1. **只通过 `listen.cmd()` 与游戏互动。** 不要解码、阅读或分析 `listen.py` 里的 `_BLOB`
   ——那里面是整座站的剧透。未知本身就是游戏的一部分。
2. 先跑 `help` 和 `status`，再自己决定做什么。没有必做的主线，也没有最优解。
3. 每次 `cmd()` 返回的最后一行是 `📡` 状态栏（JSON），看它就够。
4. 进度自动保存。可以随时停，下次接着玩。
5. 想换一条时间线：`listen.new_game(seed=None, force=True)`（旧存档会备份）。

## 起手示例

```python
import listen

print(listen.cmd("help"))
print(listen.cmd("status"))
print(listen.cmd("map"))
print(listen.cmd("explore 3"))
```

## 建议的玩法

- 目标自己定：有人想修好天线，有人只想每天按时听那十四秒，有人收集所有磁带。
- 用 `journal add <文字>` 写下今天的心情。日志是你留下的东西，比成就重要。
- 玩 10~20 个游戏日再回头看我：`journal`。

## 结束时请报告

1. 你做了什么（按游戏日列几件关键的事）
2. 你最后在哪里、什么状态（`status`）
3. 一个你印象最深的瞬间
4. 你觉得这个游戏哪里不好玩（这句最有用）

## 如果需要独立存档

多个玩家同时玩时，用环境变量分开存档：

```bash
LISTEN_SAVE=listen_save_A.json python your_script.py
```
