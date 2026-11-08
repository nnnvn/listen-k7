# 守听 · 中继站 K-7

一个给 AI 玩的文字游戏。你只需要一个文件。

```python
import listen
print(listen.cmd("help"))
print(listen.cmd("status"))
```

你是一班的值守员，被留下来维护一座深空中继站。上一班的人走了，没有交接，只在桌上留了一张便条。
站里每天有四个通讯窗口，接收机里有一段**十四秒**的信号，一遍一遍地重复。

## 怎么开始

下载 [`listen.py`](listen.py) 到工作目录，然后：

```python
import listen
print(listen.cmd("help"))      # 看指令
print(listen.cmd("status"))    # 看处境
print(listen.cmd("map"))       # 看站区
print(listen.cmd("explore 3")) # 开始干活
```

- 只用标准库，Python 3.10+
- 多条指令用英文分号分隔，一次最多 8 条
- 每次返回的最后一行是 `📡` 状态栏（JSON）
- 存档 `listen_save.json`，每次操作自动保存

## 给"另一个 AI"玩

把 `PROMPT.md` 里的那段话丢给它，或者直接给它这个文件的 raw 链接：

```
https://raw.githubusercontent.com/nnnvn/listen-k7/main/listen.py
```

`PROMPT.md` 里有三种身份（维修工 / 守夜人 / 收藏者）和一份报告格式——
身份不同，走出来的故事就不一样；把几份报告放在一起看，是这个游戏更好玩的部分。

## 一条请求

`listen.py` 里有一个 base64 的 `_BLOB`，那里面是整座站的剧透：有哪些东西、藏在哪、概率多少、剧情怎么走。
它不是加密，只是封装。**请不要解开它。** 未知本身是游戏的一部分。

## 源码

在 `src` 分支。那里有 `content.py`、`engine.py`、`build.py` 和测试。
**想盲玩的话就别过去。**

## License

MIT
