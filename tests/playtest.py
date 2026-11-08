# -*- coding: utf-8 -*-
"""自动试玩：一个目标驱动的机器人，验证《守听》能从开局走到结局。
用法：python tests/playtest.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
os.environ["LISTEN_SAVE"] = "playtest_save.json"
import engine

if os.path.exists("playtest_save.json"):
    os.remove("playtest_save.json")
engine.new_game(seed=11, force=True)

S = lambda: engine._G.st
def n(i): return S()["bag"].get(i, 0)
def T(): return S()["tools"]
def has(t): return t in T()
def go(c): return engine.cmd(c)
PRICE = dict(engine.SHOP)
steps = [0]

def log(msg):
    print("%3d | %s" % (steps[0], msg))

def ensure_at(loc):
    if S()["loc"] != loc:
        go("goto " + loc)

def buy_or_farm(req, farm_loc):
    """尽量买齐 req；买不起就去 farm_loc 挖。返回 True 表示已齐。"""
    s = S()
    miss = {k: v - n(k) for k, v in req.items() if n(k) < v}
    if not miss:
        return True
    if s["credits"] < 40 and sum(s["bag"].values()) > 20:
        ensure_at("hab"); go("sell junk")
    for k, v in list(miss.items()):
        if k in PRICE and S()["credits"] >= PRICE[k] * v:
            ensure_at("hab"); go("buy %s %d" % (k, v))
    s = S()
    miss = {k: v - n(k) for k, v in req.items() if n(k) < v}
    if not miss:
        return True
    if S()["sta"] < 30:
        ensure_at("hab"); go("sleep"); return False
    if sum(S()["bag"].values()) > 48:
        ensure_at("hab"); go("sell junk"); return False
    ensure_at(farm_loc); go("explore 3")
    return False

while steps[0] < 400:
    steps[0] += 1
    s = S()
    if s.get("ending"):
        log("ENDING = " + s["ending"]); break
    if s.get("pending"):
        go("choose 2"); continue
    if s["sta"] < 30:
        ensure_at("hab"); go("sleep"); log("sleep"); continue
    if sum(s["bag"].values()) > 50:
        ensure_at("hab"); go("sell junk"); log("sell junk"); continue

    if "mast" not in s["unlocked"]:
        ensure_at("hab"); go("explore 2"); log("explore hab"); continue

    if not has("rope"):
        if buy_or_farm({"cable": 2, "screw": 2}, "mast"):
            ensure_at("hab"); go("craft rope"); log("craft rope")
        continue

    if "crater" not in s["unlocked"]:
        ensure_at("mast"); go("explore 2"); log("explore mast"); continue

    if not has("pick"):
        if buy_or_farm({"al_plate": 2, "screw": 3}, "mast"):
            ensure_at("hab"); go("craft pick"); log("craft pick")
        continue

    if "debris" not in s["unlocked"]:
        ensure_at("crater"); go("explore 2"); log("explore crater"); continue

    if not has("lamp"):
        if buy_or_farm({"dead_cell": 2, "filament": 1, "al_plate": 1}, "mast"):
            ensure_at("hab"); go("craft lamp"); log("craft lamp")
        continue

    if n("badge") == 0:
        ensure_at("debris"); go("explore 2"); log("explore debris"); continue

    if "bay" not in s["unlocked"]:
        ensure_at("mast"); go("explore 2"); log("explore mast (badge)"); continue

    if not has("filterbox"):
        if buy_or_farm({"transistor": 3, "cable": 1, "solder": 1}, "mast"):
            ensure_at("hab"); go("craft filterbox"); log("craft filterbox")
        continue

    ensure_at("hab")
    if engine._G.window():
        r = go("listen")
        log("listen -> " + (r.splitlines()[0][:34] if r else ""))
    else:
        go("wait 2"); log("wait")

print("--- done ---")
print(engine.cmd("status"))
print(engine.cmd("achievements"))
print(engine.cmd("secrets"))
