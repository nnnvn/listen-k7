# -*- coding: utf-8 -*-
"""打包脚本：把 engine.py（明文）+ content.py（数据，压缩）合成单文件 listen.py。

安全模型：
  - 引擎逻辑全部明文，任何人都能读，能看出它只读写本地存档、不联网。
  - 只有文字内容（物品/地点/事件/结局）被 zlib 压缩 + base64 编码，用
    json.loads 读回来。**没有任何 exec / eval / 动态导入。**

用法：python build.py
"""
import base64
import json
import os
import textwrap
import zlib

import content

HERE = os.path.dirname(os.path.abspath(__file__))
from engine import DATA_NAMES  # 与引擎共用同一份白名单

HEADER = '''# -*- coding: utf-8 -*-
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

'''

FOOTER = '''
# 文字内容（纯数据：JSON → zlib → base64），在文件末尾读入。
_DATA = (
'''

TAIL = '''
)

# 把数据挂到引擎的全局变量上（纯数据，不执行任何代码）
load_content(json.loads(zlib.decompress(base64.b64decode(_DATA)).decode("utf-8")))
del _DATA
'''


def engine_source():
    src = open(os.path.join(HERE, "engine.py"), encoding="utf-8").read()
    # 去掉引擎自己的 coding 行与模块 docstring（单文件里只保留一个）
    if src.startswith("# -*- coding"):
        src = src.split("\n", 1)[1]
    s = src.lstrip()
    if s.startswith('"""'):
        end = s.find('"""', 3)
        if end != -1:
            s = s[end + 3:].lstrip("\n")
    src = s
    a = src.find("# --- dev content import")
    if a != -1:
        b = src.find("# --- end dev content import ---")
        b = src.find("\n", b)
        src = src[:a] + src[b + 1:]
    return src


def build():
    data = {k: getattr(content, k) for k in DATA_NAMES if hasattr(content, k)}
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    blob = base64.b64encode(zlib.compress(raw, 9)).decode("ascii")

    body = "\n".join('    "%s"' % x for x in textwrap.wrap(blob, 76))
    out = HEADER + engine_source() + FOOTER + body + "\n" + TAIL

    path = os.path.join(HERE, "listen.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote %s (%d bytes; data %d bytes -> blob %d chars)" %
          (path, len(out), len(raw), len(blob)))


if __name__ == "__main__":
    build()
