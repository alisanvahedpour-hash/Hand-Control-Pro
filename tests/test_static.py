"""بررسی ایستای کد: نام‌های تعریف‌نشده و ویژگی‌های self که هرگز مقدار نگرفته‌اند"""
import ast
import builtins
import unittest

from tests import stubs

FILES = ["hand_control_pro.py", "hcx/learn.py", "hcx/headtrack.py", "hcx/stats.py", "hcx/macro.py",
         "hcx/integrations.py", "hcx/remote.py", "hcx/updater.py", "hcx/plugins.py", "hcx/voice.py",
         "hcx/overlay.py", "hcx/i18n.py"]
QT_INHERITED = set("""setWindowTitle setMinimumWidth setMinimumSize resize show hide showNormal raise_
activateWindow setWindowFlag setWindowIcon setCentralWidget isVisible isMinimized accept reject exec style
update width height setProperty setObjectName close wait msleep start isRunning blockSignals setFont stop
setGeometry mapFromGlobal rect setAttribute adjustSize move setToolTip setText text setEnabled setVisible
findChildren windowTitle toolTip count""".split())


def undefined_names(tree):
    defined = set(dir(builtins))
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            defined.add(n.name)
        if isinstance(n, ast.arg):
            defined.add(n.arg)
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            defined.add(n.id)
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                defined.add((a.asname or a.name).split(".")[0])
        if isinstance(n, ast.ExceptHandler) and n.name:
            defined.add(n.name)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return sorted(used - defined)


class TestStatic(unittest.TestCase):
    def test_no_undefined_names(self):
        for f in FILES:
            tree = ast.parse((stubs.ROOT / f).read_text(encoding="utf-8"))
            self.assertEqual(undefined_names(tree), [], f)

    def test_self_attributes_exist(self):
        tree = ast.parse((stubs.ROOT / "hand_control_pro.py").read_text(encoding="utf-8"))
        classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        mixin = classes["ExtrasMixin"]

        def info(node):
            assigned = {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
                        and isinstance(n.ctx, ast.Store) and isinstance(n.value, ast.Name) and n.value.id == "self"}
            methods = {f.name for f in node.body if isinstance(f, ast.FunctionDef)}
            cvars = {t.id for b in node.body if isinstance(b, ast.Assign) for t in b.targets if isinstance(t, ast.Name)}
            loaded = {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
                      and isinstance(n.ctx, ast.Load) and isinstance(n.value, ast.Name) and n.value.id == "self"}
            return assigned, methods, cvars, loaded
        for name, node in classes.items():
            assigned, methods, cvars, loaded = info(node)
            if name == "MainWindow":                      # صفات میکسین هم در دسترس است
                a2, m2, c2, _ = info(mixin)
                assigned |= a2; methods |= m2; cvars |= c2
            if name == "ExtrasMixin":                     # متدهای MainWindow در دسترس است
                a2, m2, c2, _ = info(classes["MainWindow"])
                assigned |= a2; methods |= m2; cvars |= c2
            missing = sorted(loaded - assigned - methods - cvars - QT_INHERITED)
            self.assertEqual(missing, [], name)
