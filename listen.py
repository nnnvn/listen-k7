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
import zlib

import json
import os
import random
import shutil

DATA_NAMES = ("TITLE", "INTRO", "ITEMS", "TOOL_DUR", "LOCS", "WINDOWS", "WEATHER",
              "RECIPES", "SHOP", "PAGES", "EVENTS", "ACH", "SECRETS", "HELP",
              "BAG_MAX")


def load_content(d):
    """把一份数据字典挂到本模块的全局变量上。

    只接受 DATA_NAMES 里列出的名字，其余一律忽略——数据不能覆盖引擎函数。
    """
    globals().update({k: v for k, v in d.items() if k in DATA_NAMES})



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

    @staticmethod
    def _qty(arg):
        """buy/sell 的数量：省略时为 1；不是正整数时返回 None。"""
        if len(arg) < 2:
            return 1
        try:
            n = int(arg[1])
        except Exception:
            return None
        return n if n >= 1 else None

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
            L.append(PAGES["q_after_decode"])
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
                r = self.rng()
                L.append(r.choice(["（翻了半天，只找到一个你自己留下的脚印。）",
                                   "（今天这里什么都没有。）",
                                   "（空手而归。你坐着看了一会儿。）"]))
                self.save_rng(r)
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
        n = self._qty(arg)
        if n is None:
            return "数量要是正整数。"
        price = dict(SHOP).get(k)
        if price is None:
            return "备件柜里没有这个。"
        p = price * n
        if self.st["credits"] < p:
            return "配额不够（需要 %d，有 %d）。" % (p, self.st["credits"])
        if k not in TOOL_DUR and sum(self.st["bag"].values()) + n > BAG_MAX:
            return "🎒 背包装不下（还剩 %d 格）。" % (BAG_MAX - sum(self.st["bag"].values()))
        self.st["credits"] -= p
        self.add(k, n)
        return "买了 %s×%d，花 %d。" % (ITEMS[k][0], n, p)

    def sell(self, arg):
        if not arg:
            return "用法：sell <物品> [数量]"
        if arg[0] in ("junk", "零碎"):
            return self.sell_junk()
        k = arg[0]
        n = self._qty(arg)
        if n is None:
            return "数量要是正整数。"
        c = self.n(k)
        if c <= 0:
            return "背包里没有这个。"
        if ITEMS[k][1] == "story":
            return "这个不卖。"
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
            # 有几页才能读到第几页：一张纸不能读出三页内容
            idx = min(3, c, self.st["flags"].get("log_read", 0) + 1)
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
            self.j(PAGES["j_decoded"])
            return PAGES["signal"]
        return self.finale()

    # 结局相关的文字都在 PAGES 里（打包后在 _DATA 中），引擎只认 key
    def finale(self):
        self.say(PAGES["finale"])
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
        self.j(PAGES["j_end_" + key])
        self.ach("ending")
        return ""   # 存档和状态栏由 cmd() 统一处理

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
        # apply() 已经把文字写进 self.out，这里不再返回一遍，否则会打印两次
        self.apply(o.get("out") or {})
        return ""


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

)

# 把数据挂到引擎的全局变量上（纯数据，不执行任何代码）
load_content(json.loads(zlib.decompress(base64.b64decode(_DATA)).decode("utf-8")))
del _DATA
