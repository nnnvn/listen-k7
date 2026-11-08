# -*- coding: utf-8 -*-
"""回归测试：2026-11 修掉的几个 bug。跑法：python tests/regress.py"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["LISTEN_SAVE"] = os.path.join(tempfile.mkdtemp(), "save.json")

import engine as E  # noqa: E402

E.new_game(seed=1, force=True)
G = E._G
S = G.st


def bars(out):
    return out.count("📡")


# 1. 事件选项的结果只打印一次
E.EVENTS.append({"id": "__t", "w": 0,
                 "opts": [{"t": "x", "out": {"text": "【唯一的结果文本】"}}]})
S["pending"], S["pending_ev"] = "choose", "__t"
out = E.cmd("choose 1")
assert out.count("【唯一的结果文本】") == 1, out
assert bars(out) == 1, out
E.EVENTS.pop()

# 2. 结局：正文一次，状态栏一个
S["pending"], S["pending_ev"] = "choose", "_finale"
out = E.cmd("choose 2")
assert out.count(E.PAGES["end_keep"].splitlines()[0]) == 1, out
assert bars(out) == 1, out
assert S["ending"] == "keep"
S["ending"] = None

# 3. 数量必须是正整数
c0, b0 = S["credits"], dict(S["bag"])
for bad in ("buy ration -5", "buy ration 0", "sell water -3", "buy ration x"):
    assert "正整数" in E.cmd(bad), bad
assert S["credits"] == c0 and S["bag"] == b0

# 4. 背包满了不扣钱
S["bag"] = {"iron": E.BAG_MAX}
S["credits"] = 999
out = E.cmd("buy water 1")
assert "装不下" in out and S["credits"] == 999, out

# 5. 剧情物品不能卖
S["bag"] = {"photo": 1}
assert "不卖" in E.cmd("sell photo")
assert S["bag"].get("photo") == 1

# 6. 一张日志页只能读到第一页
S["bag"] = {"logpage": 1}
S["flags"].pop("log_read", None)
for _ in range(3):
    E.cmd("use logpage")
assert S["flags"]["log_read"] == 1
S["bag"]["logpage"] = 3
for _ in range(3):
    E.cmd("use logpage")
assert S["flags"]["log_read"] == 3

# 7. 数据不能覆盖引擎函数
E.load_content({"Game": "nope", "cmd": 1})
assert callable(E.cmd) and isinstance(E.Game, type)

print("REGRESS OK")
