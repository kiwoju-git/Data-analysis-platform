"""Small spawn target which does not import the statistical stack."""

import time


def running_child(output, root, *unused):
    (root.parent / "child-started.txt").write_text(str(root), encoding="utf-8")
    while True:
        time.sleep(0.1)
