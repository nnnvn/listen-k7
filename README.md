# 守听 · 中继站 K-7

一个给 AI 玩的文字游戏。

你是这一班的值守员，被留下来维护一座深空中继站。上一班的人走了，没有交接，
只在桌上留了一张便条。站里每天有四个通讯窗口，接收机里有一段**十四秒**的信号，
一遍一遍地重复。

## 怎么开始

把 [`listen.py`](listen.py) 下载到工作目录，然后：

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

## 它安全吗

可以自己核。`listen.py` 里**没有 `exec`、没有 `eval`、没有联网、没有子进程**：

- **引擎逻辑是明文**，就在文件上半部分，随便读。
- **文字内容是一个数据块**：`_DATA` = JSON → zlib → base64，由 `json.loads`
  读成字典。它不是代码，不会被执行。

```bash
grep -nE "exec\(|eval\(|subprocess|socket|urllib|requests" listen.py   # 应当没有输出
```

`_DATA` 解出来是剧透（有哪些东西、藏在哪、概率多少、结局原文），所以请不要解。
但那是**为了游玩体验**，不是因为里面藏着代码。

## 给"另一个 AI"玩

把 [`PROMPT.md`](PROMPT.md) 里那段丢给它，或者直接给它 raw 链接：

```
https://raw.githubusercontent.com/nnnvn/listen-k7/main/listen.py
```

`PROMPT.md` 里有三种身份（维修工 / 守夜人 / 收藏者）和一份报告格式——
身份不同，走出来的故事就不一样；把几份报告放在一起看，是这个游戏更好玩的部分。

## 源码

在 `src` 分支：`content.py`（内容）、`engine.py`（引擎）、`build.py`（打包）、测试。
**想盲玩的话就别过去。**

## License

MIT
