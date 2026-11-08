# -*- coding: utf-8 -*-
"""《守听》—— 中继站 K-7，一个给 AI 玩的文字游戏。

用法：
    import listen
    print(listen.cmd("help"))
    print(listen.cmd("status"))
    print(listen.cmd("explore 3"))

多条指令用英文分号分隔，一次最多 8 条；每次返回最后一行是 📡 状态栏。
存档：同目录 listen_save.json（每次操作自动保存，重新 import 会接着玩）。
重开：listen.new_game(seed=None, force=True)

关于下面的 _DATA：它是这个游戏的全部文字内容（物品、地点、事件、结局），
JSON → zlib → base64。这个文件里没有任何 exec / eval，_DATA 只是被
json.loads 读进来的一个字典。解压它就能看到剧透——所以请不要解。

引擎逻辑在本文件下方，明文，可以直接读。
"""
import base64
import json
import zlib

import json
import os
import random
import shutil

DATA_NAMES = ("TITLE", "INTRO", "ITEMS", "TOOL_DUR", "LOCS", "WINDOWS", "WEATHER",
              "RECIPES", "SHOP", "PAGES", "EVENTS", "ACH", "SECRETS", "HELP",
              "BAG_MAX")


def load_content(d):
    """把一份数据字典挂到本模块的全局变量上。"""
    globals().update(d)



SAVE = os.environ.get("LISTEN_SAVE", "listen_save.json")
BAG_MAX = globals().get("BAG_MAX", 60)


def _new_state(seed=None):
    r = random.Random(seed)
    return {
        "day": 1, "hour": 8, "loc": "hab",
        "sta": 100, "sta_max": 100, "pwr": 55, "credits": 30,
        "bag": {}, "tools": {}, "flags": {"note_read": False},
        "seen": {}, "cd": {}, "pity": {},
        "log": [], "ach": [], "secrets": [], "ending": None,
        "pending": None, "pending_ev": None,
        "explore": 0, "crafts": 0,
        "wx": "clear", "unlocked": ["hab"],
        "rng": [r.getstate()[0], list(r.getstate()[1]), r.getstate()[2]],
    }


class Game:
    def __init__(self, save=SAVE, seed=None, force=False):
        self.save_path = save
        self.out = []
        if force or not os.path.exists(save):
            self.st = _new_state(seed)
            self.st["bag"]["note"] = 1
            self.st["bag"]["ration"] = 2
            self.st["bag"]["water"] = 2
            self.j("你醒在值班舱。舱里很稳，只有空气循环在响。")
            self.j("桌上有一张便条，被杯子压着。")
        else:
            try:
                with open(save, encoding="utf-8") as f:
                    self.st = json.load(f)
            except Exception:
                self.st = _new_state(seed)

    # ── RNG ─────────────────────────────────────
    def rng(self):
        r = random.Random()
        s = self.st["rng"]
        r.setstate((s[0], tuple(s[1]), s[2]))
        return r

    def save_rng(self, r):
        s = r.getstate()
        self.st["rng"] = [s[0], list(s[1]), s[2]]

    def say(self, x=""):
        self.out.append(x)

    def save(self):
        tmp = self.save_path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.st, f, ensure_ascii=False)
            if os.path.exists(self.save_path):
                shutil.copyfile(self.save_path, self.save_path + ".bak")
            os.replace(tmp, self.save_path)
        except Exception as e:
            self.say("（存档失败：%s）" % e)

    # ── 物品 ────────────────────────────────────
    def n(self, i):
        return self.st["bag"].get(i, 0)

    def has(self, i):
        return self.n(i) > 0 or i in self.st["tools"]

    def add(self, i, k=1):
        if i in TOOL_DUR:
            self.st["tools"][i] = TOOL_DUR[i]
            self.say("获得工具：%s" % ITEMS[i][0])
            return True
        if i not in ITEMS:
            return False
        if sum(self.st["bag"].values()) + k > BAG_MAX:
            self.say("🎒 背包满了，%s×%d 没装下。" % (ITEMS[i][0], k))
            return False
        self.st["bag"][i] = self.st["bag"].get(i, 0) + k
        return True

    def take(self, i, k=1):
        if i in self.st["tools"] and i not in self.st["bag"]:
            self.st["tools"].pop(i, None)
            return True
        c = self.st["bag"].get(i, 0)
        if c < k:
            return False
        if c == k:
            self.st["bag"].pop(i, None)
        else:
            self.st["bag"][i] = c - k
        return True

    # ── 时间 ────────────────────────────────────
    def window(self):
        return self.st["hour"] in WINDOWS

    def dark(self):
        return self.st["hour"] < 6 or self.st["hour"] >= 19

    def advance(self, h):
        r = self.rng()
        for _ in range(h):
            self.st["hour"] += 1
            if self.st["hour"] >= 24:
                self.st["hour"] = 0
                self.st["day"] += 1
                self.st["wx"] = r.choices(["clear", "wind", "fog"], [6, 3, 3])[0]
            if 6 <= self.st["hour"] < 18 and self.st["wx"] == "clear":
                self.st["pwr"] = min(100, self.st["pwr"] + 6)
        self.save_rng(r)

    def j(self, text, mine=False):
        self.st["log"].append({"d": self.st["day"], "h": self.st["hour"], "t": text, "mine": mine})

    def ach(self, key):
        if key in ACH and key not in self.st["ach"]:
            self.st["ach"].append(key)
            self.say("🏅 成就：%s" % ACH[key])

    def secret(self, key):
        if key in SECRETS and key not in self.st["secrets"]:
            self.st["secrets"].append(key)
            self.say("✨ 你发现了一个秘密。（secrets）")

    def bar(self):
        b = {"day": self.st["day"], "h": self.st["hour"], "loc": self.st["loc"],
             "sta": "%d/%d" % (self.st["sta"], self.st["sta_max"]),
             "pwr": self.st["pwr"], "bag": "%d/%d" % (sum(self.st["bag"].values()), BAG_MAX),
             "win": self.window(), "wx": WEATHER[self.st["wx"]][0]}
        return "📡 " + json.dumps(b, ensure_ascii=False, separators=(",", ":"))

    # ── 事件 ────────────────────────────────────
    def ev_by_id(self, eid):
        for ev in EVENTS:
            if ev["id"] == eid:
                return ev
        return None

    def ok_cond(self, ev):
        c = ev.get("cond") or {}
        if "window" in c and c["window"] != self.window():
            return False
        if "time" in c:
            t = "night" if self.dark() else "day"
            if t not in c["time"]:
                return False
        if "weather" in c and self.st["wx"] not in c["weather"]:
            return False
        if "have" in c and not self.has(c["have"]):
            return False
        if "flag" in c and not self.st["flags"].get(c["flag"]):
            return False
        if "notflag" in c and self.st["flags"].get(c["notflag"]):
            return False
        return True

    def roll_event(self, loc):
        r = self.rng()
        cands = []
        for ev in EVENTS:
            if ev.get("w", 0) <= 0:
                continue
            if ev.get("once") and ev["id"] in self.st["seen"]:
                continue
            if ev["loc"] not in (loc, "any"):
                continue
            if self.st["cd"].get(ev["id"], 0) > self.st["explore"]:
                continue
            if not self.ok_cond(ev):
                continue
            cands.append((ev, ev["w"] * self.st["pity"].get(ev["id"], 1.0)))
        if not cands:
            return None
        total = sum(w for _, w in cands)
        x = r.random() * total
        for ev, w in cands:
            x -= w
            if x <= 0:
                for e2, _ in cands:
                    if e2 is not ev:
                        self.st["pity"][e2["id"]] = min(4.0, self.st["pity"].get(e2["id"], 1.0) * 1.25)
                self.st["pity"][ev["id"]] = 1.0
                self.st["seen"][ev["id"]] = self.st["day"]
                if ev.get("cd"):
                    self.st["cd"][ev["id"]] = self.st["explore"] + ev["cd"]
                self.save_rng(r)
                return ev
        self.save_rng(r)
        return None

    def apply(self, out):
        if not out:
            return
        if out.get("reset"):
            pass
        if "chance" in out:
            r = self.rng()
            pick = out["chance"]["ok"] if r.random() < out["chance"]["p"] else out["chance"]["fail"]
            self.save_rng(r)
            return self.apply(pick)
        if out.get("text"):
            self.say(out["text"])
        gained = []
        for k, v in (out.get("gain") or {}).items():
            if self.add(k, v):
                gained.append("%s×%d" % (ITEMS[k][0], v))
        if gained:
            self.say("获得：" + "、".join(gained))
        for k, v in (out.get("lose") or {}).items():
            self.take(k, v)
        if out.get("sta"):
            self.st["sta"] = max(0, min(self.st["sta_max"], self.st["sta"] + out["sta"]))
        if out.get("power"):
            self.st["pwr"] = max(0, min(100, self.st["pwr"] + out["power"]))
        if out.get("injure"):
            self.st["flags"]["injured"] = True
            self.say("🩹 你受伤了：探索更费体力，睡觉也恢复得少。")
        if out.get("flag"):
            self.st["flags"][out["flag"]] = True
        if out.get("secret"):
            self.secret(out["secret"])
        if out.get("unlock"):
            u = out["unlock"]
            if u not in self.st["unlocked"]:
                self.st["unlocked"].append(u)
                self.say("🗺️ 新地点：【%s %s】（goto %s）" % (LOCS[u]["name"], u, u))
        if out.get("journal"):
            self.j(out["journal"])
        if out.get("goto"):
            self.st["loc"] = out["goto"]

    def fire(self, ev):
        if ev.get("opts"):
            self.say("❗【事件】" + (ev.get("text") or ""))
            for i, o in enumerate(ev["opts"], 1):
                self.say("  %d. %s" % (i, o["t"]))
            self.say("（用 choose <编号> 做决定；决定之前不能继续探索）")
            self.st["pending"] = "choose"
            self.st["pending_ev"] = ev["id"]
        else:
            self.apply(ev.get("out"))

    def use_tool(self, tid):
        if tid not in self.st["tools"]:
            return False
        self.st["tools"][tid] -= 1
        if self.st["tools"][tid] <= 0:
            self.st["tools"].pop(tid, None)
            self.say("🔧 %s 坏掉了。" % ITEMS[tid][0])
        return True

    # ── 指令分发 ────────────────────────────────
    def cmd(self, line):
        self.out = []
        lines = [x.strip() for x in str(line).split(";") if x.strip()][:8]
        multi = len(lines) > 1
        for ln in lines:
            if multi:
                self.say("▶ " + ln)
            try:
                res = self.one(ln)
                if res:
                    self.say(res)
            except Exception as e:
                self.say("（出错了：%s）" % e)
            if self.st.get("pending"):
                break
        self.ach_check()
        self.save()
        self.out.append(self.bar())
        return "\n".join([x for x in self.out if x != ""])

    def one(self, s):
        a = s.split()
        if not a:
            return ""
        c, arg = a[0], a[1:]
        if self.st.get("pending") and c not in ("choose", "status", "help", "inv", "inventory",
                                                "journal", "look", "map", "quests",
                                                "achievements", "secrets"):
            return "先做决定：choose <编号>"
        table = {
            "help": lambda: HELP, "status": self.status, "map": self.map,
            "inv": self.inv, "inventory": self.inv, "quests": self.quests,
            "achievements": self.ach_list, "secrets": self.secrets_cmd,
            "look": lambda: self.look(" ".join(arg)),
            "journal": lambda: self.journal(arg),
            "explore": lambda: self.explore(arg),
            "goto": lambda: self.goto(" ".join(arg)),
            "go": lambda: self.goto(" ".join(arg)),
            "choose": lambda: self.choose(arg),
            "wait": lambda: self.wait(arg),
            "rest": self.rest, "sleep": self.sleep, "shop": self.shop,
            "recipes": self.recipes,
            "buy": lambda: self.buy(arg), "sell": lambda: self.sell(arg),
            "craft": lambda: self.craft(arg),
            "use": lambda: self.use(" ".join(arg)),
            "repair": lambda: self.repair(arg),
            "listen": self.listen,
        }
        if c in table:
            return table[c]()
        return "不认识的指令。用 help 看看。"

    # ── 观察 ────────────────────────────────────
    def next_window(self):
        h = self.st["hour"]
        for d in range(0, 25):
            if (h + d) % 24 in WINDOWS:
                return d
        return 0

    def win_text(self):
        if self.window():
            return "窗口开着"
        d = self.next_window()
        return "窗口 %d 小时后" % d if d else "窗口关着"

    def status(self):
        L = LOCS[self.st["loc"]]
        return ("【状态】第 %d 天 %02d:00 · %s · %s\n"
                "位置：%s　体力 %d/%d　电力 %d　配额 %d　背包 %d/%d\n"
                "工具：%s") % (
            self.st["day"], self.st["hour"], WEATHER[self.st["wx"]][0], self.win_text(),
            L["name"], self.st["sta"], self.st["sta_max"], self.st["pwr"],
            self.st["credits"], sum(self.st["bag"].values()), BAG_MAX,
            "、".join("%s(%d)" % (ITEMS[k][0], v) for k, v in self.st["tools"].items()) or "无")

    def map(self):
        L = ["【站区图】%s · %s" % (WEATHER[self.st["wx"]][0], self.win_text())]
        for k in ("hab", "mast", "crater", "debris", "bay"):
            if k not in self.st["unlocked"]:
                continue
            d = LOCS[k]
            need = ""
            if d.get("need") and d["need"] not in self.st["tools"]:
                need = "（需要%s）" % ITEMS[d["need"]][0]
            L.append(" %s %s　%s　%d小时·体力%d%s" % ("✦" if k == self.st["loc"] else "·",
                                                     d["name"], k, d["hours"], d["sta"], need))
        if "bay" not in self.st["unlocked"]:
            L.append("  塔基下面还有一扇没有编号的门。")
        return "\n".join(L)

    def inv(self):
        if not self.st["bag"] and not self.st["tools"]:
            return "【背包】空的。"
        L = ["【背包】%d/%d　配额 %d" % (sum(self.st["bag"].values()), BAG_MAX, self.st["credits"])]
        if self.st["tools"]:
            L.append(" 工具：%s" % "、".join("%s(%d)" % (ITEMS[k][0], v) for k, v in self.st["tools"].items()))
        for cat, label in (("food", "补给"), ("part", "零件"), ("mat", "材料"), ("story", "记录")):
            items = [(k, v) for k, v in self.st["bag"].items() if ITEMS[k][1] == cat]
            if items:
                L.append(" %s：%s" % (label, "、".join("%s×%d" % (ITEMS[k][0], v) for k, v in items)))
        return "\n".join(L)

    def look(self, name):
        if not name:
            d = LOCS[self.st["loc"]]
            return "【%s %s】%s" % (d["name"], self.st["loc"], d["desc"])
        for k, v in ITEMS.items():
            if name in (k, v[0]):
                return "【%s】%s" % (v[0], v[3])
        for k, v in LOCS.items():
            if name in (k, v["name"]):
                return "【%s %s】%s" % (v["name"], k, v["desc"])
        return "？？？——你还没见过它。"

    def quests(self):
        L = ["【线索】"]
        if not self.st["flags"].get("note_read"):
            L.append(" · 桌上那张便条，可以 use 便条 看看。")
        if not self.st["flags"].get("heard"):
            L.append(" · 每天有四个通讯窗口（03、09、15、21 点）。到点 listen。")
        elif not self.st["flags"].get("decoded"):
            L.append(" · 十四秒里有人说话，静电太厚。需要一个滤波器（craft filterbox）。")
        elif not self.st["ending"]:
            L.append(" · 你听清了。要回答吗？（再 listen 一次）")
        if "bay" in self.st["unlocked"]:
            L.append(" · 塔基下面那扇门开着。")
        if len(self.st["secrets"]) < len(SECRETS):
            L.append(" · 站里还藏着些东西——要在对的时候做对的事。")
        return "\n".join(L)

    def ach_list(self):
        L = ["【成就】%d/%d" % (len(self.st["ach"]), len(ACH))]
        for k, v in ACH.items():
            L.append(" %s %s" % ("✔" if k in self.st["ach"] else "·", v))
        return "\n".join(L)

    def secrets_cmd(self):
        L = ["【秘密】%d/%d" % (len(self.st["secrets"]), len(SECRETS))]
        if self.st["secrets"]:
            L.append("　" + "、".join(SECRETS[k] for k in self.st["secrets"]))
        else:
            L.append("　还没有。")
        return "\n".join(L)

    def ach_check(self):
        s = self.st
        if s["explore"] >= 1:
            self.ach("wake")
        if s["flags"].get("heard"):
            self.ach("first_echo")
        if s["flags"].get("decoded"):
            self.ach("decode")
        if s["crafts"] >= 4:
            self.ach("maker")
        if s["flags"].get("tape_a_read") and s["flags"].get("tape_b_read"):
            self.ach("tapes")
        if all(k in s["unlocked"] for k in ("mast", "crater", "debris", "bay")):
            self.ach("far")
        if s.get("ending"):
            self.ach("ending")

    # ── 行动 ────────────────────────────────────
    def explore(self, arg):
        try:
            n = int(arg[0]) if arg else 1
        except Exception:
            n = 1
        n = max(1, min(20, n))
        loc = self.st["loc"]
        d = LOCS[loc]
        if d.get("need") and d["need"] not in self.st["tools"]:
            return "⛔ 这里需要：%s。" % ITEMS[d["need"]][0]
        total, L, ran, sta0 = {}, [], 0, self.st["sta"]
        for i in range(1, n + 1):
            cost = d["sta"] + (6 if self.st["flags"].get("injured") else 0)
            if self.st["sta"] < cost:
                L.append("⛔ 体力不够了（需要 %d，现有 %d）。吃点东西，或者回值班舱 sleep。" %
                         (cost, self.st["sta"]))
                break
            self.st["sta"] -= cost
            self.st["pwr"] = max(0, self.st["pwr"] - 1)
            self.advance(d["hours"])
            self.st["explore"] += 1
            ran += 1
            if d.get("need"):
                self.use_tool(d["need"])
            got = self.drop(loc)
            for k, v in got.items():
                total[k] = total.get(k, 0) + v
            L.append("— 第%d次 —" % i)
            if not got:
                L.append(random.choice(["（翻了半天，只找到一个你自己留下的脚印。）",
                                        "（今天这里什么都没有。）",
                                        "（空手而归。你坐着看了一会儿。）"]))
            ev = self.roll_event(loc)
            if ev:
                mark = len(self.out)
                self.fire(ev)
                new = self.out[mark:]
                del self.out[mark:]
                L.extend(new)
                if self.st["pending"]:
                    break
        if total:
            L.append("合计拾获：" + "、".join("%s×%d" % (ITEMS[k][0], v) for k, v in total.items()))
        if ran:
            L.append("体力 %d→%d　时间 第%d天%02d:00" % (sta0, self.st["sta"], self.st["day"], self.st["hour"]))
        return "\n".join(L)

    def drop(self, loc):
        r = self.rng()
        out = {}
        for _ in range(r.randint(1, 2)):
            ks, ws = zip(*LOCS[loc]["drops"])
            k = r.choices(ks, ws)[0]
            out[k] = out.get(k, 0) + 1
        self.save_rng(r)
        got = {}
        for k, v in out.items():
            if self.add(k, v):
                got[k] = v
        return got

    def goto(self, name):
        key = None
        for k, v in LOCS.items():
            if name in (k, v["name"]):
                key = k
        if not key or key not in self.st["unlocked"]:
            return "你不知道去那里的路。用 map 看。"
        if key == self.st["loc"]:
            return "你已经在%s了。" % LOCS[key]["name"]
        self.advance(1)
        self.st["sta"] = max(0, self.st["sta"] - 3)
        self.st["loc"] = key
        return "来到【%s】。%s" % (LOCS[key]["name"], LOCS[key]["desc"])

    def wait(self, arg):
        try:
            h = max(1, min(24, int(arg[0])))
        except Exception:
            return "用法：wait <小时>"
        self.advance(h)
        self.st["sta"] = min(self.st["sta_max"], self.st["sta"] + h // 2)
        return "你等了 %d 小时。现在 %02d:00，%s，%s。" % (
            h, self.st["hour"], WEATHER[self.st["wx"]][0],
            "窗口开着" if self.window() else "窗口关着")

    def rest(self):
        self.advance(2)
        self.st["sta"] = min(self.st["sta_max"], self.st["sta"] + 12)
        return "你靠在舱壁上歇了两个小时。体力 +12。"

    def sleep(self):
        if self.st["loc"] != "hab":
            return "睡觉要回值班舱（goto hab）。"
        h = (6 - self.st["hour"]) % 24 or 24
        self.advance(h)
        heal = 45 if self.st["flags"].get("injured") else 85
        self.st["sta"] = min(self.st["sta_max"], self.st["sta"] + heal)
        self.st["pwr"] = min(100, self.st["pwr"] + 25)
        if self.st["flags"].get("injured"):
            self.st["flags"].pop("injured", None)
        return "你在休眠舱里睡到第 %d 天 06:00。体力 +%d。" % (self.st["day"], heal)

    def shop(self):
        L = ["【备件柜】配额 %d" % self.st["credits"]]
        for k, p in SHOP:
            L.append("  %-10s %-6s %d" % (k, ITEMS[k][0], p))
        return "\n".join(L)

    def buy(self, arg):
        if not arg:
            return "用法：buy <物品> [数量]"
        k = arg[0]
        try:
            n = int(arg[1]) if len(arg) > 1 else 1
        except Exception:
            n = 1
        price = dict(SHOP).get(k)
        if price is None:
            return "备件柜里没有这个。"
        p = price * n
        if self.st["credits"] < p:
            return "配额不够（需要 %d，有 %d）。" % (p, self.st["credits"])
        self.st["credits"] -= p
        self.add(k, n)
        return "买了 %s×%d，花 %d。" % (ITEMS[k][0], n, p)

    def sell(self, arg):
        if not arg:
            return "用法：sell <物品> [数量]"
        if arg[0] in ("junk", "零碎"):
            return self.sell_junk()
        k = arg[0]
        try:
            n = int(arg[1]) if len(arg) > 1 else 1
        except Exception:
            n = 1
        c = self.n(k)
        if c <= 0:
            return "背包里没有这个。"
        n = min(n, c)
        self.take(k, n)
        self.st["credits"] += ITEMS[k][2] * n
        return "卖掉 %s×%d，得 %d。" % (ITEMS[k][0], n, ITEMS[k][2] * n)

    def journal(self, arg):
        if arg and arg[0] in ("add", "加"):
            txt = " ".join(arg[1:]).strip()
            if not txt:
                return "用法：journal add <文字>"
            self.st["log"].append({"d": self.st["day"], "h": self.st["hour"],
                                   "t": txt, "mine": True})
            return "📝 记下了。"
        n = len(self.st["log"])
        if not n:
            return "【日志】还没有。"
        per, page = 12, 1
        if arg:
            try:
                page = max(1, int(arg[0]))
            except Exception:
                page = 1
        total = (n + per - 1) // per
        page = min(page, total)
        chunk = self.st["log"][(page - 1) * per: page * per]
        L = ["【日志】第 %d/%d 页" % (page, total)]
        for e in chunk:
            L.append("  第%d天%02d时 %s%s" % (e["d"], e["h"],
                                             "✍ " if e.get("mine") else "", e["t"]))
        return "\n".join(L)

    def sell_junk(self):
        keep, got = 2, 0
        for k in list(self.st["bag"]):
            if ITEMS[k][1] not in ("mat", "part", "food"):
                continue
            c = self.st["bag"][k]
            if c > keep:
                x = c - keep
                self.take(k, x)
                got += ITEMS[k][2] * x
        self.st["credits"] += got
        return ("卖掉零碎材料，得 %d 配额。" % got) if got else "没有可卖的零碎。"

    def recipes(self):
        L = ["【工作台】craft <配方>"]
        for k, r in RECIPES.items():
            need = "、".join("%s×%d" % (ITEMS[i][0], c) for i, c in r["need"].items())
            L.append("  %-11s %s　← %s" % (k, r["name"], need))
        return "\n".join(L)

    def craft(self, arg):
        if self.st["loc"] != "hab":
            return "做东西要回值班舱（goto hab）。"
        if not arg:
            return "用法：craft <配方>"
        k = arg[0]
        if k not in RECIPES:
            return "没有这个配方。"
        r = RECIPES[k]
        lack = [(i, c) for i, c in r["need"].items() if self.n(i) < c]
        if lack:
            return "材料不够：" + "、".join("%s×%d(有%d)" % (ITEMS[i][0], c, self.n(i)) for i, c in lack)
        for i, c in r["need"].items():
            self.take(i, c)
        self.st["crafts"] += 1
        self.add(r["out"])
        return "做好了 %s。" % r["name"]

    def use(self, name):
        if name in ("note", "便条"):
            if not self.has("note"):
                return "你没有便条。"
            self.st["flags"]["note_read"] = True
            return PAGES["note"]
        if name in ("tape_a", "磁带·甲"):
            if not self.has("tape_a"):
                return "你没有这卷磁带。"
            self.st["flags"]["tape_a_read"] = True
            return PAGES["tape_a"]
        if name in ("tape_b", "磁带·乙"):
            if not self.has("tape_b"):
                return "你没有这卷磁带。"
            self.st["flags"]["tape_b_read"] = True
            return PAGES["tape_b"]
        if name in ("photo", "照片"):
            return PAGES["photo"] if self.has("photo") else "你没有照片。"
        if name in ("badge", "工牌"):
            return PAGES["badge"] if self.has("badge") else "你没有工牌。"
        if name in ("logpage", "日志", "值班日志页"):
            c = self.n("logpage")
            if c <= 0:
                return "你还没有日志页。"
            idx = min(3, self.st["flags"].get("log_read", 0) + 1)
            self.st["flags"]["log_read"] = idx
            return PAGES["log%d" % idx]
        for f, t in (("ration", 20), ("water", 12)):
            if name in (f, ITEMS[f][0]):
                if self.n(f) <= 0:
                    return "没有%s了。" % ITEMS[f][0]
                self.take(f, 1)
                self.st["sta"] = min(self.st["sta_max"], self.st["sta"] + t)
                return "你吃了%s，体力 +%d。" % (ITEMS[f][0], t)
        return "这个没什么可以直接用的。"

    def repair(self, arg):
        if self.st["loc"] != "hab":
            return "修理要回值班舱。"
        if not self.has("wrench"):
            return "需要扳手。"
        if not arg or arg[0] not in self.st["tools"]:
            return "用法：repair <工具>"
        if self.st["credits"] < 6:
            return "配件不够（需要 6 配额）。"
        self.st["credits"] -= 6
        self.st["tools"][arg[0]] = TOOL_DUR.get(arg[0], 5)
        return "%s 修好了。" % ITEMS[arg[0]][0]

    # ── 信号 ────────────────────────────────────
    def listen(self):
        if self.st["ending"]:
            return "信号已经不需要你了。"
        if not self.window():
            return "没有窗口。接收机只有静电。（窗口：03、09、15、21 点前后）"
        if self.st["pwr"] < 6:
            return "电力不够，接收机带不动。"
        self.st["pwr"] -= 6
        self.advance(1)
        if not self.st["flags"].get("heard"):
            self.st["flags"]["heard"] = True
            self.j("在窗口里听到十四秒，全是静电。")
            return ("十四秒。\n"
                    "开头是静电，中间好像有人说话，但被噪声盖住了。\n"
                    "结尾是三声很轻的“嗒、嗒、嗒”，像有人在敲麦克风。")
        if not self.st["flags"].get("decoded"):
            if not self.has("filterbox"):
                return ("还是十四秒。这一次你听出了起伏——是人的说话声。\n"
                        "但静电太厚，一个字也抓不住。也许需要一个滤波器（craft filterbox）。")
            self.st["flags"]["decoded"] = True
            self.secret("signal_full")
            self.j("用滤波器听清了十四秒。是林郁的声音。")
            return PAGES["signal"]
        return self.finale()

    def finale(self):
        self.say("❗【事件】十四秒又来了。这一次你听得很清楚，清楚到能听见她换气。")
        self.say("　　　发射键就在手边。")
        self.say("  1. 把这段话发回去")
        self.say("  2. 让它继续循环，什么也不改")
        self.say("  3. 关掉它")
        self.say("（用 choose <编号> 做决定）")
        self.st["pending"] = "choose"
        self.st["pending_ev"] = "_finale"
        return ""

    def final_choose(self, k):
        key = {1: "send", 2: "keep", 3: "off"}[k]
        self.st["ending"] = key
        self.st["pending"] = None
        self.st["pending_ev"] = None
        self.say(PAGES["end_" + key])
        self.j({"send": "我把那十四秒发了回去。第三个窗口，回波多了三秒。",
                "keep": "我什么也没改。灯亮着，没有人回答，也很好。",
                "off": "我关掉了它。任务结束。"}[key])
        self.ach("ending")
        self.save()
        self.out.append(self.bar())
        return "\n".join([x for x in self.out if x != ""])

    def choose(self, arg):
        if self.st.get("pending_ev") == "_finale":
            try:
                k = int(arg[0])
            except Exception:
                return "用法：choose <编号>"
            if k not in (1, 2, 3):
                return "没有这个选项。"
            return self.final_choose(k)
        eid = self.st.get("pending_ev")
        ev = self.ev_by_id(eid) if eid else None
        if not ev:
            return "现在没有需要决定的事。"
        try:
            k = int(arg[0])
        except Exception:
            return "用法：choose <编号>"
        opts = ev["opts"]
        if k < 1 or k > len(opts):
            return "没有这个选项。"
        o = opts[k - 1]
        for it, c in (o.get("need") or {}).items():
            if self.n(it) < c:
                return "做不到：需要 %s×%d。换一个选项吧。" % (ITEMS[it][0], c)
        for it, c in (o.get("need") or {}).items():
            self.take(it, c)
        if o.get("tool"):
            self.use_tool(o["tool"])
        self.st["pending"] = None
        self.st["pending_ev"] = None
        out = o.get("out") or {}
        mark = len(self.out)
        self.apply(out)
        return "\n".join([x for x in self.out[mark:] if x])


_G = None


def game(seed=None, force=False):
    global _G
    _G = Game(seed=seed, force=force)
    return _G


def new_game(seed=None, force=False):
    global _G
    _G = Game(seed=seed, force=force)
    return INTRO + "\n" + _G.cmd("status")


def cmd(line):
    global _G
    if _G is None:
        _G = Game()
    return _G.cmd(line)

# 文字内容（纯数据：JSON → zlib → base64），在文件末尾读入。
_DATA = (
    "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"
    "qLyhRw63KYxiu80GXnZbkQjs/wBmT2lI"

)

# 把数据挂到引擎的全局变量上（纯数据，不执行任何代码）
load_content(json.loads(zlib.decompress(base64.b64decode(_DATA)).decode("utf-8")))
del _DATA
