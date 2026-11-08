import sys
sys.stdout.reconfigure(encoding="utf-8")
import engine

if "--new" in sys.argv:
    print(engine.new_game(seed=7, force=True))
    sys.argv = [a for a in sys.argv if a != "--new"]

for c in sys.argv[1:]:
    print(engine.cmd(c))
    print("-" * 56)
