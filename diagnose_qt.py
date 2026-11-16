"""诊断 Windows 上的 Qt 平台插件路径。"""
import os
import sys

print('=' * 60)
print('  Qt 平台插件诊断')
print('=' * 60)
print(f'  系统平台: {os.name}')
print(f'  Python 版本: {sys.version.split()[0]}')
print(f'  当前目录: {os.getcwd()}')

try:
    import PyQt5
    qt_root = os.path.dirname(PyQt5.__file__)
    print(f'  PyQt5 安装目录: {qt_root}')

    # 兼容 PyPI、Conda 和旧版 PyQt5 的目录布局。
    paths_to_check = [
        os.path.join(qt_root, 'Qt5', 'plugins', 'platforms'),
        os.path.join(qt_root, 'plugins', 'platforms'),
        os.path.join(qt_root, 'Qt5', 'plugins'),
        os.path.join(qt_root, '..', 'PyQt5-Qt5', 'Qt5', 'plugins', 'platforms'),
    ]

    found = False
    for p in paths_to_check:
        p_norm = os.path.normpath(p)
        exists = os.path.isdir(p_norm)
        has_dll = False
        if exists:
            files = os.listdir(p_norm)
            has_dll = any(f.lower().startswith('qwindows') for f in files)
        print(f'    [{("✓" if exists and has_dll else "✗")}] {p_norm}')
        if exists and has_dll:
            found = True
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = p_norm
            qt_bin = os.path.join(qt_root, 'Qt5', 'bin')
            if os.path.isdir(qt_bin):
                os.environ['PATH'] = qt_bin + os.pathsep + os.environ.get('PATH', '')
            print(f'  → 设置为平台插件路径: {p_norm}')
            break

    if not found:
        print()
        print('  ⚠ 未找到 qwindows.dll，请执行完整重装:')
        print('  python -m pip uninstall -y PyQt5 PyQt5-Qt5 PyQt5-sip')
        print('  python -m pip install PyQt5 PyQt5-Qt5 PyQt5-sip')
        print()
        print('  或使用国内镜像加速:')
        print('  python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple PyQt5')
        sys.exit(1)

    print(f'  QT_QPA_PLATFORM_PLUGIN_PATH = {os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "(未设置)")}')

except ImportError as e:
    print(f'  ✗ PyQt5 未安装: {e}')
    print('  请执行: python -m pip install PyQt5')
    sys.exit(1)
except Exception as e:
    print(f'  ✗ 诊断过程出错: {e}')
    sys.exit(1)

print()
print('  正在测试 PyQt5.QtWidgets 导入 ...')
try:
    from PyQt5 import QtWidgets
    print('  ✓ PyQt5.QtWidgets 导入成功')
except Exception as e:
    print(f'  ✗ 导入失败: {e}')
    print('  请检查是否有杀毒软件隔离 Qt DLL 文件')
    sys.exit(1)

print()
print('=' * 60)
print('  ✅ 环境检查通过，可以正常启动 GUI')
print('=' * 60)
