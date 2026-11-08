# -*- coding: utf-8 -*-
"""冒烟测试：把每个指令都打一遍，确认没有异常。用法：python tests/smoke.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
os.environ["LISTEN_SAVE"] = "smoke_save.json"
if os.path.exists("smoke_save.json"):
    os.remove("smoke_save.json")
import engine

engine.new_game(seed=3, force=True)
CMDS = ["help", "status", "map", "inv", "quests", "achievements", "secrets",
        "look", "look 值班舱", "look 铝板", "journal", "explore 2", "use 便条",
        "goto mast", "explore 2", "recipes", "shop", "buy cable 2", "sell junk",
        "wait 2", "rest", "goto hab", "craft rope", "repair rope", "sleep",
        "journal add 测试一行", "listen", "status"]

bad = 0
for c in CMDS:
    r = engine.cmd(c)
    if "出错了" in r or not r.strip():
        bad += 1
        print("!! %-16s -> %s" % (c, r[:120]))

# 多指令、上限、非法输入
for c in ["status; map; inv", "", "无这条指令", "explore 999", "choose 1"]:
    r = engine.cmd(c)
    if "出错了" in r:
        bad += 1
        print("!! %-16s -> %s" % (c, r[:120]))

print("SMOKE", "OK" if bad == 0 else ("FAIL %d" % bad))
