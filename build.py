# -*- coding: utf-8 -*-
"""打包脚本：把 content.py + engine.py 封进单文件 listen.py（盲玩版）。
用法：python build.py
"""
import base64
import os
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))

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

⚠️ 请不要解码 / 查看下面的 _BLOB：那里面是整座站的剧透（有哪些东西、
藏在哪、概率多少、剧情怎么走）。这只是方便盲玩的 base64 封装，不是加密。
想维护这个游戏的人类，请看同目录的 content.py / engine.py。
"""
import base64

'''

FOOTER = '''

exec(compile(base64.b64decode(_BLOB).decode("utf-8"), "<listen>", "exec"), globals())
del _BLOB
'''


def build():
    content = open(os.path.join(HERE, "content.py"), encoding="utf-8").read()
    engine = open(os.path.join(HERE, "engine.py"), encoding="utf-8").read()

    # 去掉引擎里那段为了开发方便写的 import
    cut = engine.find("SAVE = os.environ")
    head = engine[:cut]
    head = head.split("try:")[0]
    engine = head + engine[cut:]

    src = content + "\n\n# " + "=" * 60 + "\n#  引擎\n# " + "=" * 60 + "\n\n" + engine
    blob = base64.b64encode(src.encode("utf-8")).decode("ascii")
    body = "_BLOB = (\n" + "\n".join('    "%s"' % x for x in textwrap.wrap(blob, 76)) + "\n)\n"
    out = HEADER + body + FOOTER
    path = os.path.join(HERE, "listen.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote %s (%d bytes, blob %d chars)" % (path, len(out), len(blob)))


if __name__ == "__main__":
    build()
