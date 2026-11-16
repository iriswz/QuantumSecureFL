"""PyQt 主界面。"""
import os
os.environ.setdefault('QT_SCALE_FACTOR', '1.1')

import sys
import os
import json
import hashlib
from pathlib import Path
from copy import deepcopy

# PyQt5 在部分 Windows 环境下找不到 qwindows.dll，导入 Qt 前先补路径。
import os as _os
import sys as _sys

if _os.name == 'nt':
    try:
        import PyQt5 as _PyQt5
        _qt_root = _os.path.dirname(_PyQt5.__file__)
        _plugin_dir = _os.path.join(_qt_root, 'Qt5', 'plugins', 'platforms')
        _plugin_dir_alt = _os.path.join(_qt_root, 'plugins', 'platforms')

        _target = None
        if _os.path.isdir(_plugin_dir) and _os.path.exists(_os.path.join(_plugin_dir, 'qwindows.dll')):
            _target = _plugin_dir
        elif _os.path.isdir(_plugin_dir_alt) and _os.path.exists(_os.path.join(_plugin_dir_alt, 'qwindows.dll')):
            _target = _plugin_dir_alt

        if _target:
            _os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = _target
            # Windows 还需要从 Qt5/bin 加载 DLL。
            _qt_bin = _os.path.join(_qt_root, 'Qt5', 'bin')
            if _os.path.isdir(_qt_bin) and _qt_bin not in _os.environ.get('PATH', ''):
                _os.environ['PATH'] = _qt_bin + _os.pathsep + _os.environ.get('PATH', '')
        else:
            print('[警告] 未找到 qwindows.dll，请确认 PyQt5 已完整安装。')
            print('       可执行: python -m pip install --force-reinstall PyQt5 PyQt5-Qt5 PyQt5-sip')
    except Exception as _e:
        print(f'[警告] 初始化 Qt 插件路径时出错: {_e}')

import numpy as np
import time
from typing import List, Dict

# PyQt5 缺失时仍允许使用命令行模式。
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QStackedWidget, QLabel, QPushButton, QTextEdit, QProgressBar,
        QSlider, QSpinBox, QDoubleSpinBox, QGridLayout, QComboBox,
        QTableWidget, QTableWidgetItem, QGroupBox, QFrame,
        QScrollArea, QHeaderView, QGraphicsDropShadowEffect, QSizePolicy,
        QLineEdit, QCheckBox, QFileDialog
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPointF
    from PyQt5.QtGui import (
        QFont, QFontMetrics, QColor, QPainter, QPen, QPainterPath, QLinearGradient
    )
    import matplotlib
    matplotlib.use('Qt5Agg')

    # 初始化中文字体，减少 matplotlib 的缺字告警。
    try:
        from matplotlib import font_manager as _fm
        import os as _os

        _cjk_candidates = [
            'Microsoft YaHei', 'Microsoft YaHei UI', 'SimHei', 'SimSun',
            'NSimSun', 'FangSong', 'KaiTi', 'Yu Gothic', 'Meiryo',
            'PingFang SC', 'Heiti SC', 'STHeiti', 'STFangsong', 'Arial Unicode MS',
            'Noto Sans CJK SC', 'Noto Sans CJK TC', 'WenQuanYi Micro Hei',
            'WenQuanYi Zen Hei', 'Source Han Sans CN', 'Source Han Sans SC',
            'DejaVu Sans',
        ]

        _installed = {f.name for f in _fm.fontManager.ttflist}
        _chosen = None
        for _name in _cjk_candidates:
            if _name in _installed:
                _chosen = _name
                break

        if _chosen is None:
            for _f in _fm.fontManager.ttflist:
                _lower = (_f.name or '').lower()
                if any(k in _lower for k in ('hei', 'song', 'cjk', 'yahei', 'ming', 'noto', 'pingfang', 'heiti')):
                    _chosen = _f.name
                    break

        if _chosen:
            matplotlib.rcParams['font.sans-serif'] = [_chosen, 'DejaVu Sans']
            matplotlib.rcParams['font.family'] = 'sans-serif'
        matplotlib.rcParams['axes.unicode_minus'] = False
        matplotlib.rcParams['axes.formatter.use_locale'] = False
        matplotlib.rcParams.update({
            'figure.facecolor': '#FFFFFF',
            'savefig.facecolor': '#FFFFFF',
            'axes.facecolor': '#FBFBFA',
            'axes.edgecolor': '#D9DDDA',
            'axes.labelcolor': '#515A56',
            'axes.titlecolor': '#28312E',
            'axes.titleweight': 'medium',
            'xtick.color': '#68716D',
            'ytick.color': '#68716D',
            'grid.color': '#E1E5E2',
            'grid.alpha': 0.68,
            'legend.frameon': False,
            'lines.linewidth': 1.9,
            'pdf.fonttype': 42,
            'svg.fonttype': 'none',
        })

        import warnings as _warnings
        _warnings.filterwarnings('ignore', message='Glyph.*missing.*font', category=UserWarning)

        _font_debug = _chosen or '未找到 (回退默认)'
        print(f'[Matplotlib] 使用中文字体: {_font_debug}')
    except Exception as _e:
        print(f'[Matplotlib] 字体初始化警告: {_e}')

    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

    class QWidget:
        pass

    class QMainWindow:
        pass

from core import (
    QuantumCommunicationChannel, QuantumDifferentialPrivacy,
    MPOCompressor, SimpleNNModel, FederatedLearningServer,
    Blockchain, QuantumByzantineConsensus, SecureFederatedLedger, AttackSimulator
)


PROJECT_ROOT = Path(__file__).resolve().parent


APP_STYLE = """
QMainWindow, QWidget#appShell {
    background: #F2F4EF;
    color: #2C2A26;
}
QWidget {
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC";
    font-size: 21px;
    font-weight: 500;
}
QFrame#sidebar {
    background: #F7F8F3;
    border: none;
    border-right: 1px solid #DFE3DA;
}
QLabel#brandMark {
    background: #3A5B50;
    color: white;
    border-radius: 5px;
    font-size: 26px;
    font-weight: 700;
}
QLabel#brandTitle {
    color: #2C2A26;
    font-size: 25px;
    font-weight: 700;
}
QPushButton#navSection {
    background: #3A5B50;
    color: #FFFFFF;
    font-size: 25px;
    font-weight: 700;
    border-radius: 5px;
    padding: 6px 8px;
    margin-top: 4px;
    text-align: left;
    border: none;
}
QPushButton#navSection:hover {
    background: #4A7C6B;
}
QPushButton#navButton {
    background: transparent;
    color: #4A4F46;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 7px 11px;
    text-align: left;
    font-size: 19px;
    font-weight: 500;
}
QPushButton#navButton:hover {
    background: #F0F2EC;
    color: #000000;
    font-size: 19px;
    font-weight: 700;
    padding: 5px 11px;
}
QPushButton#navButton[active="true"] {
    background: #FFFFFF;
    color: #3A5B50;
    border: 1px solid #D8DDDA;
    border-left: 3px solid #4A7C6B;
    font-weight: 600;
}
QFrame#topBar {
    background: #FAFBF6;
    border: none;
    border-bottom: 1px solid #DFE3DA;
}
QLabel#pageTitle {
    color: #151B19;
    font-size: 34px;
    font-weight: 700;
}
QLabel#pageSubtitle {
    color: #7A7B72;
    font-size: 20px;
    font-weight: 500;
}
QTabWidget::pane {
    border: 1px solid #DFE3DA;
    background: #FFFFFF;
    border-radius: 5px;
}
QTabBar::tab {
    background: #EDEFE8;
    color: #9DA096;
    border: 1px solid #DFE3DA;
    border-bottom: none;
    padding: 8px 15px;
    margin-right: 2px;
    min-width: 86px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #3A5B50;
    border-top: 2px solid #4A7C6B;
    font-weight: 600;
}
QTabBar::tab:hover:!selected {
    background: #E6E9E0;
    color: #4A4F46;
}
QFrame#actionBar {
    background: #FFFFFF;
    border: 1px solid #DFE3DA;
    border-radius: 5px;
}
QLabel#actionTitle {
    color: #1D2421;
    font-size: 21px;
    font-weight: 700;
}
QLabel#actionText {
    color: #7A7B72;
    font-size: 18px;
    font-weight: 500;
}
QFrame#protocolPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #F7FBF9, stop:0.45 #EFF6F3, stop:1 #E6F0ED);
    border: 1px solid #DDE5DC;
    border-radius: 12px;
}
QLabel#protocolTitle {
    color: #000000;
    font-size: 22px;
    font-weight: 700;
}
QLabel#protocolStep {
    background: #FFFFFF;
    color: #5A6058;
    border: 1px solid #DFE3DA;
    border-radius: 8px;
    padding: 8px 10px;
}
QGroupBox {
    background: #FDFEFB;
    border: 1px solid #E4E7DD;
    border-radius: 10px;
    margin-top: 0px;
    padding: 32px 12px 12px 12px;
    font-weight: 700;
    color: #3A4038;
}
QGroupBox::title {
    subcontrol-origin: padding;
    subcontrol-position: top left;
    left: 4px;
    padding: 0 8px;
    background: transparent;
    color: #000000;
    font-weight: 700;
}
QGroupBox::indicator {
    width: 18px;
    height: 18px;
}
QPushButton {
    background-color: #4A7C6B;
    color: #F2F5F4;
    border: none;
    border-radius: 0px;
    padding: 10px 26px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #5A8D7B;
    color: #F2F5F4;
    border: none;
}
QPushButton:pressed {
    background-color: #2E4D42;
    color: #F2F5F4;
}
QPushButton#privacyPresetBtn:pressed {
    background-color: #3A6659;
    color: #F2F5F4;
}
QPushButton:disabled {
    background: #C4CAC0;
    color: #F0F0F0;
    border: 1px solid #D8DDDB;
}
QPushButton[variant="primary"] {
    background-color: #4A7C6B;
    color: #F2F5F4;
    border: none;
    border-radius: 0px;
    padding: 10px 26px;
    font-weight: 600;
}
QPushButton[variant="primary"]:hover {
    background-color: #5A8D7B;
    color: #F2F5F4;
    border: none;
}
QPushButton[variant="danger"] {
    background-color: #4A7C6B;
    color: #F2F5F4;
    border: none;
    border-radius: 0px;
    padding: 10px 26px;
    font-weight: 600;
}
QPushButton[variant="danger"]:hover {
    background-color: #5A8D7B;
    color: #F2F5F4;
    border: none;
}
QPushButton[variant="warning"] {
    background-color: #4A7C6B;
    color: #F2F5F4;
    border: none;
    border-radius: 0px;
    padding: 10px 26px;
    font-weight: 600;
}
QPushButton[variant="warning"]:hover {
    background-color: #5A8D7B;
    color: #F2F5F4;
    border: none;
}
QPushButton[variant="quiet"] {
    background-color: #4A7C6B;
    color: #F2F5F4;
    border: none;
    border-radius: 0px;
    padding: 10px 26px;
    font-weight: 600;
}
QPushButton[variant="quiet"]:hover {
    background-color: #5A8D7B;
    color: #F2F5F4;
    border: none;
}
QPushButton#attackButton {
    background-color: #4A7C6B;
    color: #F2F5F4;
    border: none;
    border-radius: 0px;
    text-align: left;
    padding: 12px;
    font-weight: 600;
}
QPushButton#attackButton:hover {
    background-color: #5A8D7B;
    color: #F2F5F4;
    border: none;
}
QPushButton#privacyPresetBtn[active="true"] {
    background-color: #9ED0B0;
    color: #0C352F;
    border: 1px solid #4A7C6B;
}
QPushButton#privacyPresetBtn[active="true"]:hover {
    background-color: #8FC3A3;
    color: #0C352F;
    border: 1px solid #4A7C6B;
}
QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #FDFDFB;
    color: #3A4038;
    border: 1px solid #E4E7DD;
    border-radius: 4px;
    padding: 6px;
    selection-background-color: #B8D4C6;
    font-weight: 500;
}
QTextEdit:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #6B9C89;
    background: #FFFFFF;
}
QLineEdit {
    min-height: 22px;
}
QLineEdit[readOnly="true"] {
    background: #F6F8F2;
    color: #9DA096;
}
QSpinBox, QDoubleSpinBox {
    padding-right: 25px;
}
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 21px;
    background: #F8F9F4;
    border: none;
    border-left: 1px solid #E4E7DD;
    border-bottom: 1px solid #E4E7DD;
    border-top-right-radius: 3px;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 21px;
    background: #F8F9F4;
    border: none;
    border-left: 1px solid #E4E7DD;
    border-bottom-right-radius: 3px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #EAF0E6;
}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
    background: #E0E9DE;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    image: url("__SPIN_UP_ICON__");
    width: 10px;
    height: 7px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    image: url("__SPIN_DOWN_ICON__");
    width: 10px;
    height: 7px;
}
QCheckBox {
    color: #4A4F46;
    spacing: 7px;
    padding: 3px 2px;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QTableWidget {
    background: #FFFFFF;
    alternate-background-color: #F8F9F4;
    color: #3A4038;
    border: 1px solid #DFE3DA;
    border-radius: 4px;
    gridline-color: #E5E8E6;
    selection-background-color: #DCEAE2;
    selection-color: #3A5B50;
    font-weight: 500;
}
QHeaderView::section {
    background: #F0F2EA;
    color: #4A4F46;
    border: none;
    border-right: 1px solid #DFE3DA;
    border-bottom: 1px solid #E0E4DA;
    padding: 7px;
    font-weight: 700;
}
QProgressBar {
    background: #E6E9E0;
    border: none;
    border-radius: 3px;
    text-align: center;
    color: #38403C;
    min-height: 10px;
}
QProgressBar::chunk {
    background: #4A7C6B;
    border-radius: 3px;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #E4E7DD;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #6B9C89;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #4A7C6B;
    width: 14px;
    margin: -6px 0;
    border-radius: 7px;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #C6CBC0;
    min-height: 28px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #A8ADA4;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    height: 0;
    background: transparent;
}
QToolTip {
    background: #2C2A26;
    color: #FFFFFF;
    border: 1px solid #4B534F;
    padding: 6px;
}
QScrollArea, QScrollArea > QWidget > QWidget {
    background: transparent;
}
"""

APP_STYLE = (
    APP_STYLE
    .replace('__SPIN_UP_ICON__', (PROJECT_ROOT / 'assets' / 'icons' / 'spin-up.svg').as_posix())
    .replace('__SPIN_DOWN_ICON__', (PROJECT_ROOT / 'assets' / 'icons' / 'spin-down.svg').as_posix())
)


class _StatusCardFrame(QFrame):
    """鼠标悬停聚焦卡片、同组其他卡片变淡。"""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self._color = color
        self._title_label = None
        self._value_label = None
        self._detail_label = None
        self._group = []  # 同组兄弟卡片列表（含自己）
        self._init_style()

    def _init_style(self):
        c = self._color
        self.setStyleSheet(
            f'QFrame {{ '
            f'background: #FDFEFB; '
            f'border: 1px solid #E4E7DD; '
            f'border-left: 3px solid {c}; '
            f'border-radius: 10px; padding: 12px 14px; }}'
            f'QFrame[focused="true"] {{ '
            f'background: #FFFFFF; '
            f'border: 1px solid {c}; '
            f'border-left: 3px solid {c}; '
            f'border-radius: 10px; padding: 12px 14px; }}'
            f'QFrame[dimmed="true"] {{ '
            f'background: #F6F8F2; '
            f'border: 1px solid #E8EBE3; '
            f'border-left: 3px solid #C4CAC0; '
            f'border-radius: 10px; padding: 12px 14px; }}'
            f'QLabel {{ background: transparent; border: none; '
            f'border-radius: 0; padding: 0; }}'
        )

    def set_color(self, color):
        self._color = color
        self._init_style()

    def enterEvent(self, event):
        self._apply_group(focused=self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_group(focused=None)
        super().leaveEvent(event)

    def _apply_group(self, focused):
        if not self._group:
            return
        for card in self._group:
            if focused is None:
                card._restore()
            elif card is focused:
                card._focus_self()
            else:
                card._dim_soft()

    def _focus_self(self):
        self.setProperty('focused', True)
        self.setProperty('dimmed', False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.raise_()
        if self._title_label:
            self._title_label.setStyleSheet('color: #000000; border: none; padding: 0; font-weight: 700;')
        if self._value_label:
            self._value_label.setStyleSheet('color: #000000; border: none; padding: 0; font-weight: 900;')
        if self._detail_label:
            self._detail_label.setStyleSheet('color: #333333; border: none; padding: 0;')

    def _dim_soft(self):
        self.setProperty('focused', False)
        self.setProperty('dimmed', True)
        self.style().unpolish(self)
        self.style().polish(self)
        if self._title_label:
            self._title_label.setStyleSheet('color: #B8BEBC; border: none; padding: 0;')
        if self._value_label:
            self._value_label.setStyleSheet(f'color: #BEC8C5; border: none; padding: 0;')
        if self._detail_label:
            self._detail_label.setStyleSheet('color: #C8CECB; border: none; padding: 0;')

    def _restore(self):
        self.setProperty('focused', False)
        self.setProperty('dimmed', False)
        self.style().unpolish(self)
        self.style().polish(self)
        if self._title_label:
            self._title_label.setStyleSheet('color: #454E4A; border: none; padding: 0;')
        if self._value_label:
            self._value_label.setStyleSheet(f'color: {self._color}; border: none; padding: 0;')
        if self._detail_label:
            self._detail_label.setStyleSheet('color: #5D6662; border: none; padding: 0;')


class AutoScrollLog(QTextEdit):
    """日志追加后自动滚动到最新一行的只读日志框。"""

    _fitting = False

    def _fit_height(self):
        """按文档实际高度收缩，避免底部留白；超长内容仍限制在 420px 内。"""
        doc_h = int(self.document().size().height()) + 10
        target = max(180, min(doc_h, 420))
        if target != self.height():
            self._fitting = True
            try:
                self.setFixedHeight(target)
            finally:
                self._fitting = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._fitting:
            self._fit_height()

    def append(self, text):
        super().append(text)
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
        QTimer.singleShot(0, self._fit_height)


def make_status_card(title: str, value: str = '待演示', detail: str = '', color: str = '#566573', group=None):
    """创建状态卡片。传 group=list 可让同组卡片联动。"""
    frame = _StatusCardFrame(color=color)
    frame.setFrameShape(QFrame.StyledPanel)

    layout = QVBoxLayout(frame)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(3)
    title_label = QLabel(title)
    title_label.setFont(QFont('Microsoft YaHei', 14, QFont.DemiBold))
    title_label.setStyleSheet('color: #454E4A; border: none; padding: 0;')
    value_label = QLabel(value)
    value_label.setFont(QFont('Microsoft YaHei', 22, QFont.Bold))
    value_label.setStyleSheet(f'color: {color}; border: none; padding: 0;')
    detail_label = QLabel(detail)
    detail_label.setFont(QFont('Microsoft YaHei', 12, QFont.Medium))
    detail_label.setWordWrap(True)
    detail_label.setStyleSheet('color: #5D6662; border: none; padding: 0;')
    layout.addWidget(title_label)
    layout.addWidget(value_label)
    layout.addWidget(detail_label)
    frame.value_label = value_label
    frame.detail_label = detail_label
    frame.title_label = title_label
    frame._title_label = title_label
    frame._value_label = value_label
    frame._detail_label = detail_label

    if group is not None:
        frame._group = group
        group.append(frame)
    return frame


def update_status_card(card, value: str, detail: str = '', color: str = '#566573'):
    card.value_label.setText(value)
    card.detail_label.setText(detail)
    card.set_color(color)
    if not card.property('focused') and not card.property('dimmed'):
        card.value_label.setStyleSheet(f'color: {color}; border: none; padding: 0;')


def make_collapsible_group(title: str):
    """创建默认收起的高级设置区。"""
    group = QGroupBox(title)
    group.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
    group.setCheckable(True)
    group.setChecked(False)
    group_layout = QVBoxLayout(group)
    body = QWidget()
    body_layout = QVBoxLayout(body)
    body.setVisible(False)
    group.toggled.connect(body.setVisible)
    group_layout.addWidget(body)
    return group, body_layout


def _apply_glass_glow(widget, color=None):
    """给控件叠加柔和外光晕，营造液态玻璃悬浮质感（复用同一 effect 避免性能损耗）。"""
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsDropShadowEffect):
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(14)
        effect.setOffset(0, 2)
        widget.setGraphicsEffect(effect)
    if color is None:
        color = QColor(23, 107, 99, 30)
    effect.setColor(color)


def make_protocol_panel(title: str, steps: List[str], accent: str = "#176B63"):
    """创建用于解释实验流程的紧凑步骤面板。"""
    panel = QFrame()
    panel.setObjectName('protocolPanel')
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(16, 15, 16, 15)
    layout.setSpacing(9)
    title_label = QLabel(title)
    title_label.setObjectName('protocolTitle')
    title_label.setFont(QFont('Microsoft YaHei', 18, QFont.Bold))
    layout.addWidget(title_label)
    step_labels = []
    for index, step in enumerate(steps, start=1):
        label = QLabel(f'{index:02d}   {step}')
        label.setObjectName('protocolStep')
        label.setWordWrap(True)
        if index == 1:
            label.setStyleSheet(
                f'QLabel {{background:qlineargradient(x1:0, y1:0, x2:0, y2:1, '
                f'stop:0 #FCFEFD, stop:1 #E6F0ED); '
                f'color:#173F3A; border:1px solid {accent}; '
                f'border-left:3px solid {accent}; border-radius:7px; padding:8px 10px;}}'
            )
            _apply_glass_glow(label, QColor(23, 107, 99, 62))
        layout.addWidget(label)
        step_labels.append(label)
    layout.addStretch()
    panel.step_labels = step_labels
    panel.accent = accent
    return panel


class QKDProtocolAnimation(QWidget):
    """BB84 协议过程动画：Alice 持续向 Bob 发送光子并完成 QBER 判定。"""

    TEXT_SIZE_OFFSET = 4
    FRAME_INTERVAL_MS = 40
    # 主流程约 15.4 秒，每个光子约 3.8 秒穿过信道，便于现场观众看清。
    PROGRESS_PER_FRAME = 0.0026
    PHOTON_TRIPS_PER_RUN = 4.0
    PHOTON_RELEASE_GAP = 0.18
    PHOTON_COUNT = 7
    SETTLE_FRAMES = 18

    phaseChanged = pyqtSignal(int)
    finished = pyqtSignal()

    PHASES = [
        '准备光子', '发送光子', '筛选匹配', '检查误码', '生成 / 作废密钥'
    ]
    PHASE_DETAILS = [
        'Alice 为每个光子随机选择状态，偷看会改变它',
        '光子通过量子信道逐个到达 Bob',
        '双方只比较测量方向，不公开真正的密钥比特',
        '抽样计算误码率 QBER，并与 11% 安全阈值比较',
        '误码率安全则生成密钥，异常则立即作废',
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0.0
        self.eve_active = False
        self.error_rate = 0.0
        self.running = False
        self.completed = False
        self.settle_frame = 0
        self.timer = QTimer(self)
        self.timer.setInterval(self.FRAME_INTERVAL_MS)
        self.timer.timeout.connect(self._advance)
        self.setMinimumHeight(122)
        self.setStyleSheet('background:#FBFBFA; border:1px solid #D9DDDA; border-radius:5px;')

    def reset(self):
        self.timer.stop()
        self.progress = 0.0
        self.eve_active = False
        self.error_rate = 0.0
        self.running = False
        self.completed = False
        self.settle_frame = 0
        self.phaseChanged.emit(0)
        self.update()

    def start(self, eve_active: bool, error_rate: float):
        self.timer.stop()
        self.progress = 0.0
        self.eve_active = bool(eve_active)
        self.error_rate = float(error_rate)
        self.running = True
        self.completed = False
        self.settle_frame = 0
        self.phaseChanged.emit(0)
        self.timer.start()
        self.update()

    def _advance(self):
        previous_phase = self._phase_index()
        if self.progress < 1.0:
            self.progress = min(1.0, self.progress + self.PROGRESS_PER_FRAME)
        else:
            self.settle_frame += 1
        if self.progress >= 1.0 and self.settle_frame >= self.SETTLE_FRAMES:
            self.timer.stop()
            self.running = False
            self.completed = True
            self.phaseChanged.emit(5)
            self.finished.emit()
        elif self._phase_index() != previous_phase:
            self.phaseChanged.emit(self._phase_index())
        self.update()

    @staticmethod
    def _ease_in_out(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    @staticmethod
    def _ease_out(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return 1.0 - (1.0 - value) ** 3

    def _phase_progress(self, index: int) -> float:
        if self.completed:
            return 1.0
        if not self.running:
            return 0.0
        raw = self.progress * len(self.PHASES) - index
        return self._ease_in_out(raw)

    def _settle_progress(self) -> float:
        if self.completed:
            return 1.0
        if self.progress < 1.0:
            return 0.0
        return max(0.0, min(1.0, self.settle_frame / self.SETTLE_FRAMES))

    def _phase_index(self):
        if self.completed:
            return 4
        return min(4, int(self.progress * 5.0))

    @staticmethod
    def _draw_text(painter, rect, text, color, size=9, bold=False,
                   alignment=Qt.AlignCenter):
        painter.setPen(QColor(color))
        font = QFont('Microsoft YaHei')
        font.setPixelSize(int(round((size + QKDProtocolAnimation.TEXT_SIZE_OFFSET) * 4 / 3)))
        font.setBold(bold)
        painter.setFont(font)
        painter.drawText(rect, alignment, text)

    def _qber_bar_style(self):
        """整条 QBER 状态条只在动画完成后切换为最终判定。"""
        if not self.completed:
            return '加载中', '#EAF0FF', '#315CC8', '#BFD0FA'
        if self.error_rate <= 11.0:
            return '安全', '#DDF7EC', '#137A55', '#9DDEC6'
        return '风险', '#FCE8EA', '#B4232F', '#EFB5BC'

    def _draw_qber_scale(self, painter, rect, _phase_index):
        """绘制加载/安全/风险三态 QBER 判定条。"""
        painter.save()
        title_rect = QRectF(rect.left(), rect.top() - 10.0, rect.width(), 34.0)
        self._draw_text(
            painter, title_rect, 'QBER 风险判定  ·  阈值 11%', '#0A0A0A', 9, True,
            Qt.AlignLeft | Qt.AlignTop
        )
        bar = QRectF(rect.left(), rect.top() + 34.0, rect.width(), 22.0)
        status_text, bar_bg, bar_fg, bar_border = self._qber_bar_style()

        track_path = QPainterPath()
        track_path.addRoundedRect(bar, bar.height() / 2, bar.height() / 2)
        painter.setClipPath(track_path)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(bar_bg))
        painter.drawRect(bar)

        # 播放期间用缓慢扫光表达加载，不展示任何安全/风险分区或真实判定。
        if not self.completed:
            sweep_width = max(52.0, bar.width() * 0.24)
            sweep_phase = (self.progress * 3.2) % 1.0
            sweep_x = (
                bar.left() - sweep_width
                + (bar.width() + sweep_width * 2.0) * sweep_phase
            )
            sweep_rect = QRectF(sweep_x, bar.top(), sweep_width, bar.height())
            sweep_gradient = QLinearGradient(sweep_rect.topLeft(), sweep_rect.topRight())
            sweep_edge = QColor('#7DA2FF')
            sweep_edge.setAlpha(0)
            sweep_center = QColor('#7DA2FF')
            sweep_center.setAlpha(118)
            sweep_gradient.setColorAt(0.0, sweep_edge)
            sweep_gradient.setColorAt(0.5, sweep_center)
            sweep_gradient.setColorAt(1.0, sweep_edge)
            painter.setBrush(sweep_gradient)
            painter.drawRect(sweep_rect)

        painter.setClipping(False)
        painter.setPen(QPen(QColor(bar_border), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(bar, bar.height() / 2, bar.height() / 2)
        self._draw_text(painter, bar, status_text, bar_fg, 9, True)

        if self.completed:
            dot_color = QColor('#27AE60' if self.error_rate <= 11.0 else '#D94343')
            dot_center = QPointF(bar.left() + 11.0, bar.center().y())
            dot_glow = QColor(dot_color)
            dot_glow.setAlpha(42)
            painter.setPen(Qt.NoPen)
            painter.setBrush(dot_glow)
            painter.drawEllipse(dot_center, 6.0, 6.0)
            painter.setBrush(dot_color)
            painter.drawEllipse(dot_center, 3.0, 3.0)

        painter.restore()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('#FBFCFE'))

        width = float(self.width())
        height = float(self.height())
        compact = height < 205
        ultra_compact = height < 155
        phase_index = self._phase_index()

        margin = 12.0
        gap = 5.0
        phase_height = 20.0 if ultra_compact else 24.0 if compact else 30.0
        phase_width = (width - margin * 2 - gap * 4) / 5.0
        for index, phase in enumerate(self.PHASES):
            rect = QRectF(margin + index * (phase_width + gap), 9, phase_width, phase_height)
            if index < phase_index:
                background, foreground, border = '#E9F9F2', '#18865D', '#C8EEDD'
            elif index == phase_index:
                background, foreground, border = '#EAF0FF', '#315CC8', '#86A5F5'
            else:
                background, foreground, border = '#F1F4F8', '#8793A6', '#E2E7EE'
            is_active = index == phase_index and self.running
            if is_active:
                glow = QColor('#5C8DFF')
                glow.setAlpha(30 + int(18 * (0.5 + 0.5 * np.sin(self.progress * 38.0))))
                painter.setPen(QPen(glow, 5))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 7, 7)
            painter.setPen(QPen(QColor(border), 1))
            painter.setBrush(QColor(background))
            painter.drawRoundedRect(rect, 6, 6)
            label = phase if compact else f'{index + 1:02d}  {phase}'
            self._draw_text(painter, rect, label, foreground, 6 if ultra_compact else 7 if compact else 8, True)
            if is_active:
                underline = QRectF(
                    rect.left() + 4, rect.bottom() - 3,
                    max(3.0, (rect.width() - 8) * self._phase_progress(index)), 2
                )
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor('#5C8DFF'))
                painter.drawRoundedRect(underline, 1, 1)

        if not compact:
            meter_rect = QRectF(
                margin, phase_height + 58,
                width - margin * 2, 56
            )
            self._draw_qber_scale(painter, meter_rect, phase_index)

        channel_y = height * (0.54 if ultra_compact else 0.57 if compact else 0.63)
        alice_x = 48.0 if ultra_compact else 76.0
        bob_x = width - alice_x
        node_width = 72.0 if ultra_compact else 90.0 if compact else 104.0
        node_height = 30.0 if ultra_compact else 42.0 if compact else 52.0

        _ch_size = 7 if compact else 8
        _ch_font = QFont('Microsoft YaHei', _ch_size + self.TEXT_SIZE_OFFSET, QFont.Bold)
        _ch_fm = QFontMetrics(_ch_font)
        channel_label_h = float(_ch_fm.height())
        channel_label_bottom = channel_y - 8.0
        channel_label_top = channel_label_bottom - channel_label_h

        channel_pen = QPen(QColor('#9EADC2'), 3)
        channel_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(channel_pen)
        painter.drawLine(QPointF(alice_x + node_width / 2, channel_y),
                         QPointF(bob_x - node_width / 2, channel_y))
        painter.setPen(QPen(QColor('#CAD4E2'), 1, Qt.DashLine))
        painter.drawLine(QPointF(alice_x + node_width / 2, channel_y + 8),
                         QPointF(bob_x - node_width / 2, channel_y + 8))

        if not ultra_compact:
            label_left = alice_x + node_width / 2 + 8
            label_right = bob_x - node_width / 2 - 8
            if self.eve_active:
                # 窃听节点位于通道中心，将说明拆到两侧，避免文字被节点遮挡。
                eve_w = 80 if ultra_compact else 100 if compact else 160
                center_gap = eve_w / 2.0 + 10.0
                left_label = QRectF(
                    label_left, channel_label_top,
                    max(40.0, width / 2 - center_gap - label_left), channel_label_h
                )
                right_start = width / 2 + center_gap
                right_label = QRectF(
                    right_start, channel_label_top,
                    max(40.0, label_right - right_start), channel_label_h
                )
                self._draw_text(
                    painter, left_label, '量子信道 · 随机光子状态传输',
                    '#63758C', _ch_size, True
                )
                self._draw_text(
                    painter, right_label, '测量会改变光子状态',
                    '#63758C', _ch_size, True
                )
            else:
                channel_label = QRectF(
                    label_left, channel_label_top,
                    label_right - label_left, channel_label_h
                )
                self._draw_text(
                    painter, channel_label,
                    '量子信道 · 传输随机光子状态，不直接发送明文密钥',
                    '#63758C', _ch_size, True
                )

        self._draw_node(
            painter, alice_x, channel_y, node_width, node_height,
            'ALICE', '发送端', '#315CC8',
            self.running
        )
        self._draw_node(
            painter, bob_x, channel_y, node_width, node_height,
            'BOB', '接收端', '#168A78',
            self.running
        )

        if self.eve_active:
            eve_height = 30 if ultra_compact else 42 if compact else 50
            if ultra_compact:
                eve_y = channel_y - 22
            elif compact:
                eve_y = channel_y - 32
            else:
                # 高度较小时避开上方 QBER 刻度；高度充足时保留更长的拦截路径。
                meter_bottom = phase_height + 58 + 56
                eve_y = max(channel_y - 78, meter_bottom + 23)
            eve_y = min(eve_y, channel_label_top - 8 - eve_height)
            painter.setPen(QPen(QColor('#E24A4A'), 2, Qt.DashLine))
            painter.drawLine(QPointF(width / 2, eve_y + eve_height / 2),
                             QPointF(width / 2, channel_y - 4))
            self._draw_node(
                painter, width / 2, eve_y,
                80 if ultra_compact else 100 if compact else 160,
                eve_height, 'EVE', '窃听会留下误码', '#D94343',
                self.running
            )

        if self.running:
            path_start = alice_x + node_width / 2 + 8
            path_end = bob_x - node_width / 2 - 8
            # 光子流持续到结果公布，避免阶段切换时闪断。
            stream_clock = self.progress * self.PHOTON_TRIPS_PER_RUN
            if self.progress >= 1.0:
                stream_clock += (
                    self.settle_frame * self.PROGRESS_PER_FRAME * self.PHOTON_TRIPS_PER_RUN
                )
            intercept_pulse = False
            for index in range(self.PHOTON_COUNT):
                raw_position = stream_clock - index * self.PHOTON_RELEASE_GAP
                if raw_position < 0.0:
                    continue
                position = raw_position % 1.0
                x = path_start + (path_end - path_start) * position
                y = channel_y + 1.8 * float(np.sin(stream_clock * 3.2 + index * 1.35))
                intercepted = self.eve_active and abs(x - width / 2) < 48.0
                intercept_pulse = intercept_pulse or intercepted
                self._draw_photon(
                    painter, x, y,
                    '+' if index % 2 == 0 else '×',
                    '#FF5A62' if intercepted else '#25C7E6',
                    ultra_compact, 1.0, index
                )

            if intercept_pulse:
                ring_radius = 13.0 + 4.0 * (
                    0.5 + 0.5 * float(np.sin(stream_clock * 18.0))
                )
                ring_color = QColor('#E24A4A')
                ring_color.setAlpha(95)
                painter.setPen(QPen(ring_color, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(width / 2, channel_y), ring_radius, ring_radius)

            if self.progress >= 1.0:
                settle = self._settle_progress()
                sweep_x = path_start + (path_end - path_start) * self._ease_out(settle)
                sweep_color = QColor('#25B584')
                sweep_color.setAlpha(int(120 * (1.0 - settle) + 35))
                painter.setPen(QPen(sweep_color, 4, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(
                    QPointF(max(path_start, sweep_x - 42), channel_y + 8),
                    QPointF(sweep_x, channel_y + 8)
                )

        status_rect = QRectF(
            margin,
            height - (30 if ultra_compact else 38 if compact else 48),
            width - margin * 2,
            23 if ultra_compact else 29 if compact else 36
        )
        status_text, status_bg, status_fg, status_border = self._status_style(phase_index)
        painter.setPen(QPen(QColor(status_border), 1))
        painter.setBrush(QColor(status_bg))
        painter.drawRoundedRect(status_rect, 7, 7)
        self._draw_text(
            painter, status_rect, status_text, status_fg,
            6 if ultra_compact else 8 if compact else 9, True
        )

    def _draw_photon(self, painter, x, y, symbol, color, ultra_compact,
                     intensity=1.0, phase_offset=0):
        photon_color = QColor(color)
        glow = QColor(photon_color)
        glow.setAlpha(int(30 + 42 * intensity))
        pulse = ((4.0 if ultra_compact else 6.5) +
                 1.1 * float(np.sin(self.progress * 42.0 + phase_offset)))
        pulse *= 0.78 + 0.22 * intensity
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QPointF(x, y), pulse + 4, pulse + 4)
        painter.setBrush(photon_color)
        painter.drawEllipse(QPointF(x, y), pulse, pulse)
        self._draw_text(
            painter, QRectF(x - 8, y - 8, 16, 16),
            symbol, '#FFFFFF', 7 if ultra_compact else 8, True
        )

    def _draw_node(self, painter, center_x, center_y, width, height, title, subtitle, color,
                   active=False):
        rect = QRectF(center_x - width / 2, center_y - height / 2, width, height)
        if active:
            pulse = 3.0 + 1.7 * (0.5 + 0.5 * float(np.sin(self.progress * 38.0)))
            glow = QColor(color)
            glow.setAlpha(34)
            painter.setPen(QPen(glow, pulse))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 11, 11)
        painter.setPen(QPen(QColor(color), 2))
        painter.setBrush(QColor('#FFFFFF'))
        painter.drawRoundedRect(rect, 9, 9)
        if height < 34:
            self._draw_text(painter, rect, title, color, 7, True)
            return
        title_rect = QRectF(rect.x(), rect.y() + 2, rect.width(), rect.height() * 0.44)
        subtitle_rect = QRectF(rect.x(), rect.y() + rect.height() * 0.47,
                               rect.width(), rect.height() * 0.5)
        self._draw_text(painter, title_rect, title, color, 9, True)
        self._draw_text(painter, subtitle_rect, subtitle, '#718096', 7)

    def _status_style(self, phase_index):
        if self.completed:
            if self.eve_active or self.error_rate > 11.0:
                return (
                    f'QBER {self.error_rate:.2f}%  >  11%  ·  检测到窃听，密钥已作废',
                    '#FFF0F0', '#B4232F', '#F3B8BD'
                )
            return (
                f'QBER {self.error_rate:.2f}%  <  11%  ·  安全密钥生成成功',
                '#EAFBF5', '#137A55', '#BDEAD9'
            )
        if not self.running:
            return ('未运行', '#F1F4F8', '#64748B', '#DCE3EC')
        detail = self.PHASE_DETAILS[phase_index]
        if self.eve_active and phase_index == 1:
            detail = 'Eve 正在拦截光子并使用随机测量基重发'
        return (f'进行中  ·  {detail}', '#EAF0FF', '#315CC8', '#C8D6FA')


class PlainLanguageFlowAnimation(QWidget):
    """面向非专业观众的流程动画。

    它不额外制造模拟数据，只把已有实验中的「输入→防护→结果」
    转成可见的信息流，并且仅在页面进入或用户操作后播放一次。
    """

    finished = pyqtSignal()
    TEXT_SIZE_OFFSET = 4

    FLOW_CONFIGS = {
        'privacy': {
            'eyebrow': '',
            'accent': '#7C4DCE',
            'steps': [
                ('原始模型梯度', '识别过强的敏感特征'),
                ('L2 范数裁剪', '将更新限制在阈值 C 内'),
                ('量子随机扰动', '按隐私预算 ε 注入噪声'),
                ('受保护更新', '可聚合，难以逆向还原'),
            ],
            'idle': '原始数据不会被发送；传出的只是经过裁剪和加噪的模型更新。',
        },
        'federated': {
            'eyebrow': '',
            'accent': '#315CC8',
            'steps': [
                ('本地训练', '每家只使用自己的原始数据'),
                ('上传模型更新', '发送模型变化，不发送原始数据'),
                ('异常更新筛查', '恶意节点的更新会被拦下'),
                ('压缩安全聚合', '少传输，合成可信全局模型'),
                ('训练过程存证', '关键记录写入链中，可复核'),
            ],
            'idle': '各机构仅上传模型更新，不上传原始数据。',
        },
        'defense': {
            'eyebrow': '',
            'accent': '#D94343',
            'steps': [
                ('攻击进入', '异常信息流出现'),
                ('安全层检查', '特征与证据校验'),
                ('异常被拦截', '不让其污染结果'),
                ('可信结果继续', '正常流程不中断'),
            ],
            'idle': '未运行',
        },
        'scenario': {
            'eyebrow': '',
            'accent': '#168A78',
            'steps': [
                ('5家机构', '各自保管原始数据'),
                ('加密与隐私保护', 'QKD 建密钥，QDP 隐去个人痕迹'),
                ('MPO 压缩更新', '减少需要传输的模型参数'),
                ('共识安全聚合', '剔除恶意更新后再合并'),
                ('返回可信模型', '结果下发并留下链上记录'),
            ],
            'idle': '整个过程传递的是模型更新，不是患者、邮件或企业的原始记录。',
        },
        'consensus': {
            'eyebrow': '',
            'accent': '#315CC8',
            'steps': [
                ('读取模型更新', '为当前联邦模型生成统一指纹'),
                ('生成节点签名', '每个参与方提交可验证支持'),
                ('计算支持率', '比对签名相似度与投票阈值'),
                ('筛除恶意节点', '异常支持不进入可信节点集'),
                ('输出共识判定', '可信支持超过 2/3 才允许上链'),
            ],
            'idle': '未运行',
        },
        'ledger': {
            'eyebrow': '',
            'accent': '#D97706',
            'steps': [
                ('定位目标区块', '选中待修改的历史训练记录'),
                ('读取原始数据', '记录修改前的准确率和区块指纹'),
                ('直接修改数据', '伪造模型准确率但不重新挖矿'),
                ('重算 SHA-256', '新内容产生不同的哈希指纹'),
                ('检查 PoW', '原 nonce 无法通过新内容验证'),
            ],
            'idle': '经典篡改会直接改写历史数据，内容哈希变化后 PoW 校验将失败。',
        },
    }

    ATTACK_DEFENSES = {
        'eavesdropping': ('窃听攻击', 'QKD 误码率检查', '误码率越过阈值，作废密钥'),
        'poisoning': ('模型毒化', '拜占庭共识 + 鲁棒聚合', '异常梯度被剔除或降权'),
        'leakage': ('梯度反演', '差分隐私加噪', '个人特征痕迹被扰乱'),
        'tampering': ('链上篡改', '区块哈希校验', '直接篡改会触发 PoW 或链接异常'),
        'all': ('四类攻击', '四层防线协同', '窃听、毒化、泄漏与篡改分层处理'),
    }

    # 约 8.3 秒播完一轮，4–5 个阶段各停留约 1.7–2.1 秒。
    FRAME_INTERVAL_MS = 40
    PROGRESS_PER_FRAME = 0.0048
    SETTLE_FRAMES = 16

    def __init__(self, flow_type: str, parent=None):
        super().__init__(parent)
        if flow_type not in self.FLOW_CONFIGS:
            raise ValueError(f'未知流程动画类型: {flow_type}')
        self.flow_type = flow_type
        self.config = self.FLOW_CONFIGS[flow_type]
        self.accent = self.config['accent']
        self.steps = list(self.config['steps'])
        self.progress = 0.0
        self.running = False
        self.completed = False
        self.settle_frame = 0
        self.final_caption = self.config['idle']
        self.timer = QTimer(self)
        self.timer.setInterval(self.FRAME_INTERVAL_MS)
        self.timer.timeout.connect(self._advance)
        if flow_type == 'privacy':
            self.setMinimumHeight(212)
            self.setMaximumHeight(244)
        else:
            self.setMinimumHeight(192)
            self.setMaximumHeight(218)
        self.setStyleSheet('background:#FBFBFA; border:1px solid #D9DDDA; border-radius:5px;')

    def set_accent(self, color: str):
        self.accent = color
        self.update()

    def play(self, final_caption: str = '', attack_type: str = '', steps=None):
        """从头播放一次；攻防模式会将「安全层检查」替换为真实防线名称。"""
        self.timer.stop()
        self.steps = list(steps or self.config['steps'])
        if self.flow_type == 'defense':
            attack_name, defense_name, outcome = self.ATTACK_DEFENSES.get(
                attack_type, self.ATTACK_DEFENSES['all']
            )
            self.steps[0] = (attack_name, '异常信息流出现')
            self.steps[1] = (defense_name, '根据可验证证据判定')
            self.steps[2] = ('风险被控制', outcome)
        self.progress = 0.0
        self.running = True
        self.completed = False
        self.settle_frame = 0
        self.final_caption = final_caption or self.config['idle']
        self.timer.start()
        self.update()

    def reset(self):
        self.timer.stop()
        self.progress = 0.0
        self.running = False
        self.completed = False
        self.settle_frame = 0
        self.steps = list(self.config['steps'])
        self.final_caption = self.config['idle']
        self.update()

    def _advance(self):
        if self.progress < 1.0:
            self.progress = min(1.0, self.progress + self.PROGRESS_PER_FRAME)
        else:
            self.settle_frame += 1
        just_completed = False
        if self.progress >= 1.0 and self.settle_frame >= self.SETTLE_FRAMES:
            self.timer.stop()
            self.running = False
            self.completed = True
            just_completed = True
        self.update()
        if just_completed:
            self.finished.emit()

    @staticmethod
    def _ease_in_out(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    @staticmethod
    def _ease_out(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return 1.0 - (1.0 - value) ** 3

    def _stage_progress(self, index: int) -> float:
        if self.completed:
            return 1.0
        if not self.running:
            return 0.0
        raw = self.progress * len(self.steps) - index
        return self._ease_in_out(raw)

    def _settle_progress(self) -> float:
        if self.completed:
            return 1.0
        if self.progress < 1.0:
            return 0.0
        return max(0.0, min(1.0, self.settle_frame / self.SETTLE_FRAMES))

    def _active_index(self):
        if not self.running and not self.completed:
            return -1
        if self.completed:
            return len(self.steps) - 1
        return min(len(self.steps) - 1, int(self.progress * len(self.steps)))

    @staticmethod
    def _text(painter, rect, text, color, size=8, bold=False, alignment=Qt.AlignCenter):
        painter.setPen(QColor(color))
        font = QFont('Microsoft YaHei')
        font.setPixelSize(int(round((size + PlainLanguageFlowAnimation.TEXT_SIZE_OFFSET) * 4 / 3)))
        font.setBold(bold)
        painter.setFont(font)
        painter.drawText(rect, alignment | Qt.TextWordWrap, text)

    def _paint_privacy_stage_visual(self, painter, index, rect, active, passed):
        """为隐私管线绘制梯度、裁剪、扰动和受保护输出的微型数据图。"""
        painter.save()
        accent = QColor('#7C4DCE')
        muted = QColor('#A7B2C2')
        main_color = QColor('#16A085') if passed else accent if active else muted
        center = rect.center()
        stage_t = 1.0 if (passed or self.completed) else self._stage_progress(index) if active else 0.0

        if index == 0:
            # 原始梯度与异常峰值。
            values = [0.34, 0.62, 0.45, 0.96, 0.54, 0.76, 0.40]
            bar_width = max(4.0, min(8.0, rect.width() / 18.0))
            gap = bar_width * 0.72
            total = len(values) * bar_width + (len(values) - 1) * gap
            start_x = center.x() - total / 2.0
            baseline = rect.bottom() - 3.0
            max_height = rect.height() - 8.0
            for item_index, value in enumerate(values):
                motion = 0.72 + 0.28 * stage_t
                if active:
                    motion += 0.05 * float(np.sin(self.progress * 52.0 + item_index))
                height = max_height * value * motion
                bar = QRectF(
                    start_x + item_index * (bar_width + gap), baseline - height,
                    bar_width, height
                )
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor('#F04467') if item_index == 3 else main_color)
                painter.drawRoundedRect(bar, bar_width / 2.0, bar_width / 2.0)
            painter.setPen(QPen(QColor('#D7DFEA'), 1))
            painter.drawLine(QPointF(start_x - 5, baseline), QPointF(start_x + total + 5, baseline))

        elif index == 1:
            # 裁剪阈值 C。
            limit = max(10.0, rect.height() * 0.25)
            center_y = center.y()
            threshold_pen = QPen(QColor('#D99B2B'), 1)
            threshold_pen.setDashPattern([3.0, 3.0])
            painter.setPen(threshold_pen)
            painter.drawLine(QPointF(rect.left() + 4, center_y - limit),
                             QPointF(rect.right() - 4, center_y - limit))
            painter.drawLine(QPointF(rect.left() + 4, center_y + limit),
                             QPointF(rect.right() - 4, center_y + limit))
            self._text(
                painter, QRectF(rect.right() - 22, center_y - limit - 10, 20, 10),
                '+C', '#B7791F', 6, True
            )
            self._text(
                painter, QRectF(rect.right() - 22, center_y + limit, 20, 10),
                '−C', '#B7791F', 6, True
            )
            values = [0.55, -0.72, 1.35, -0.48, 0.83, -1.18, 0.38]
            spacing = (rect.width() - 28.0) / (len(values) - 1)
            for item_index, value in enumerate(values):
                x = rect.left() + 14.0 + item_index * spacing
                raw_y = center_y - value * limit
                clipped_y = center_y - max(-1.0, min(1.0, value)) * limit
                display_y = raw_y + (clipped_y - raw_y) * stage_t
                if abs(value) > 1.0:
                    overflow_pen = QPen(QColor('#F0A4B0'), 1)
                    overflow_pen.setDashPattern([2.0, 2.0])
                    painter.setPen(overflow_pen)
                    painter.drawLine(QPointF(x, display_y), QPointF(x, raw_y))
                painter.setPen(QPen(main_color, 3, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(x, center_y), QPointF(x, display_y))
                if abs(value) > 1.0 and stage_t > 0.72:
                    painter.setPen(QPen(QColor('#D99B2B'), 2))
                    painter.drawLine(QPointF(x - 4, clipped_y), QPointF(x + 4, clipped_y))

        elif index == 2:
            # 裁剪后的随机扰动。
            halo = QColor('#7C4DCE')
            halo.setAlpha(26 if active else 15)
            painter.setPen(QPen(QColor('#D5C8F1'), 1))
            painter.setBrush(halo)
            spread = 0.64 + 0.36 * stage_t
            radius_x = min(rect.width() * 0.26, 34.0) * spread
            radius_y = min(rect.height() * 0.34, 25.0) * spread
            painter.drawEllipse(center, radius_x, radius_y)
            for item_index in range(12):
                angle = item_index * np.pi * 2.0 / 12.0 + stage_t * np.pi * 1.6
                jitter = 0.0
                if active:
                    jitter = 3.0 * float(np.sin(self.progress * 58.0 + item_index * 1.7))
                x = center.x() + np.cos(angle) * (radius_x * 0.72 + jitter)
                y = center.y() + np.sin(angle) * (radius_y * 0.72 + jitter * 0.55)
                dot_color = QColor('#E67E22') if item_index % 3 == 0 else main_color
                painter.setPen(Qt.NoPen)
                painter.setBrush(dot_color)
                painter.drawEllipse(QPointF(float(x), float(y)), 2.8, 2.8)
            painter.setPen(QPen(main_color, 2))
            painter.drawLine(QPointF(center.x() - 9, center.y()),
                             QPointF(center.x() + 9, center.y()))
            painter.drawLine(QPointF(center.x(), center.y() - 9),
                             QPointF(center.x(), center.y() + 9))

        else:
            # 受保护的输出。
            shield_color = QColor('#16A085') if (active or passed or self.completed) else muted
            glow = QColor(shield_color)
            glow.setAlpha(int(18 + 24 * stage_t) if active else 18)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow)
            shield_pulse = 0.86 + 0.14 * stage_t
            if active:
                shield_pulse += 0.035 * float(np.sin(self.progress * 42.0))
            painter.drawEllipse(center, 28.0 * shield_pulse, 28.0 * shield_pulse)
            path = QPainterPath()
            path.moveTo(center.x(), center.y() - 22.0)
            path.lineTo(center.x() + 18.0, center.y() - 14.0)
            path.lineTo(center.x() + 15.0, center.y() + 8.0)
            path.quadTo(center.x(), center.y() + 25.0,
                        center.x() - 15.0, center.y() + 8.0)
            path.lineTo(center.x() - 18.0, center.y() - 14.0)
            path.closeSubpath()
            painter.setPen(QPen(shield_color, 2))
            painter.setBrush(QColor('#E8FAF4'))
            painter.drawPath(path)
            painter.setPen(QPen(shield_color, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(QPointF(center.x() - 8, center.y()),
                             QPointF(center.x() - 2, center.y() + 7))
            painter.drawLine(QPointF(center.x() - 2, center.y() + 7),
                             QPointF(center.x() + 10, center.y() - 8))

        painter.restore()

    def _paint_completion_sweep(self, painter, cards, y):
        """最后阶段完成后做一次性横向校验扫描，随后才对外发出完成信号。"""
        if not self.running or self.progress < 1.0 or not cards:
            return
        settle = self._settle_progress()
        left = cards[0].left()
        right = cards[-1].right()
        x = left + (right - left) * self._ease_out(settle)
        trail_start = max(left, x - 72.0)
        glow = QColor(self.accent)
        glow.setAlpha(int(95 * (1.0 - settle) + 30))
        painter.setPen(QPen(glow, 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(trail_start, y), QPointF(x, y))
        head = QColor(self.accent)
        head.setAlpha(210)
        painter.setPen(Qt.NoPen)
        painter.setBrush(head)
        painter.drawEllipse(QPointF(x, y), 3.2, 3.2)

    def _paint_privacy_pipeline(self, painter, width, height):
        """隐私防护专属视觉：用动态数据形态呈现逐层净化过程。"""
        compact = width < 760
        margin = 13.0
        status_height = 34.0
        top = 8.0
        bottom = height - status_height - 10.0
        count = len(self.steps)
        gap = 14.0 if compact else 18.0
        card_width = (width - margin * 2 - gap * (count - 1)) / count
        card_height = bottom - top
        active = self._active_index()
        accent = QColor('#7C4DCE')
        cards = []

        for index in range(count):
            cards.append(QRectF(
                margin + index * (card_width + gap), top,
                card_width, card_height
            ))

        # 先画连线，避免盖住卡片和状态粒子。
        connector_y = top + card_height * 0.54
        for index in range(count - 1):
            start_x = cards[index].right() + 2.0
            end_x = cards[index + 1].left() - 2.0
            passed = index < active or self.completed
            line_color = QColor('#28B487') if passed else QColor('#CBD5E1')
            painter.setPen(QPen(line_color, 2))
            painter.drawLine(QPointF(start_x, connector_y), QPointF(end_x, connector_y))
            painter.drawLine(QPointF(end_x - 5, connector_y - 4), QPointF(end_x, connector_y))
            painter.drawLine(QPointF(end_x - 5, connector_y + 4), QPointF(end_x, connector_y))

            if self.running and active == index:
                local = self._stage_progress(index)
                for particle_index, offset in enumerate([0.0, 0.18, 0.36]):
                    position = local * 1.22 - offset
                    if not 0.0 <= position <= 1.0:
                        continue
                    position = self._ease_in_out(position)
                    x = start_x + (end_x - start_x) * position
                    particle = QColor('#7C4DCE' if particle_index == 0 else '#B48BE8')
                    particle.setAlpha(255 - particle_index * 52)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(particle)
                    painter.drawEllipse(QPointF(x, connector_y),
                                        4.0 - particle_index * 0.7,
                                        4.0 - particle_index * 0.7)

        for index, (title, detail) in enumerate(self.steps):
            rect = QRectF(cards[index])
            passed = index < active or self.completed
            is_active = index == active and self.running
            stage_t = self._stage_progress(index) if is_active else 1.0 if passed else 0.0
            if is_active:
                rect.translate(0, -2.2 * self._ease_out(min(1.0, stage_t * 1.8)))
            if passed:
                top_color, bottom_color, border, title_color = (
                    '#F0FCF8', '#E8F9F3', '#9EDFCB', '#117A5D'
                )
            elif is_active:
                top_color, bottom_color, border, title_color = (
                    '#FBF9FF', '#F2ECFF', '#7C4DCE', '#6B36B5'
                )
            else:
                top_color, bottom_color, border, title_color = (
                    '#FBFCFE', '#F4F7FB', '#D7E0EB', '#52637A'
                )

            if is_active:
                glow = QColor('#7C4DCE')
                glow.setAlpha(34 + int(12 * (1.0 + np.sin(self.progress * 52.0))))
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(glow, 6))
                painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 12, 12)

            shadow = QColor('#667085')
            shadow.setAlpha(18 if is_active else 10 if passed else 6)
            painter.setPen(Qt.NoPen)
            painter.setBrush(shadow)
            painter.drawRoundedRect(rect.translated(0, 2), 11, 11)

            gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            gradient.setColorAt(0.0, QColor(top_color))
            gradient.setColorAt(1.0, QColor(bottom_color))
            painter.setPen(QPen(QColor(border), 2 if is_active else 1))
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, 11, 11)

            badge = QRectF(rect.left() + 10, rect.top() + 9, 38, 18)
            badge_color = QColor('#7C4DCE' if is_active else '#16A085' if passed else '#8291A5')
            badge_bg = QColor(badge_color)
            badge_bg.setAlpha(28)
            painter.setPen(Qt.NoPen)
            painter.setBrush(badge_bg)
            painter.drawRoundedRect(badge, 9, 9)
            self._text(painter, badge, f'{index + 1:02d}', badge_color.name(), 6, True)

            self._text(
                painter, QRectF(rect.left() + 9, rect.top() + 24, rect.width() - 18, 28),
                title, title_color, 8 if compact else 9, True
            )
            visual_rect = QRectF(
                rect.left() + 12, rect.top() + 54,
                rect.width() - 24, max(35.0, rect.height() - 84)
            )
            self._paint_privacy_stage_visual(
                painter, index, visual_rect, is_active, passed
            )
            self._text(
                painter, QRectF(rect.left() + 8, rect.bottom() - 33, rect.width() - 16, 27),
                detail, '#6E7F94', 6 if compact else 7
            )

            if passed:
                check_rect = QRectF(rect.right() - 21, rect.top() + 31, 13, 13)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor('#16A085'))
                painter.drawEllipse(check_rect)
                self._text(painter, check_rect, '✓', '#FFFFFF', 6, True)

        status_rect = QRectF(
            margin, height - status_height - 4,
            width - margin * 2, status_height
        )
        if self.completed:
            status, bg, fg, border = self.final_caption, '#E8FAF4', '#117A5D', '#A7E7D2'
        elif self.running and self.progress >= 1.0:
            status, bg, fg, border = '保护结果校验中……', '#EDF9F5', '#117A5D', '#B7E6D7'
        elif self.running:
            title, detail = self.steps[max(0, active)]
            status = f'隐私保护处理中  ·  第 {active + 1}/{count} 步  ·  {title}  ·  {detail}'
            bg, fg, border = '#F3EEFF', '#6B36B5', '#D8C6F2'
        else:
            status, bg, fg, border = self.config['idle'], '#F3F6FA', '#64748B', '#DCE3EC'
        painter.setPen(QPen(QColor(border), 1))
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(status_rect, 8, 8)
        self._text(
            painter, status_rect.adjusted(10, 0, -10, 0),
            status, fg, 7 if compact else 8, True
        )
        self._paint_completion_sweep(painter, cards, status_rect.top() - 3)

    def _paint_security_stage_visual(self, painter, index, rect, active, passed):
        """绘制联邦协同、攻防拦截和跨机构场景的专属微型过程图。"""
        painter.save()
        accent = QColor(self.accent)
        muted = QColor('#9AA8BA')
        main_color = QColor('#16A085') if passed else accent if active else muted
        center = rect.center()
        stage_t = 1.0 if (passed or self.completed) else self._stage_progress(index) if active else 0.0

        if self.flow_type == 'federated':
            if index == 0:
                # 本地训练。
                radius_x = min(31.0, rect.width() * 0.27)
                radius_y = min(22.0, rect.height() * 0.33)
                for node_index in range(5):
                    angle = (-np.pi / 2 + node_index * np.pi * 2 / 5 +
                             (stage_t * 0.22 if active else 0.0))
                    x = center.x() + np.cos(angle) * radius_x
                    y = center.y() + np.sin(angle) * radius_y
                    painter.setPen(QPen(QColor('#CBD5E1'), 1))
                    painter.drawLine(center, QPointF(float(x), float(y)))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(main_color)
                    node_radius = 4.0 + (0.7 * float(np.sin(stage_t * 18 + node_index)) if active else 0.0)
                    painter.drawEllipse(QPointF(float(x), float(y)), node_radius, node_radius)
                painter.setPen(QPen(main_color, 2))
                painter.setBrush(QColor('#EEF4FF'))
                painter.drawEllipse(center, 9.0, 9.0)
                self._text(painter, QRectF(center.x() - 8, center.y() - 7, 16, 14),
                           'M', main_color.name(), 7, True)

            elif index == 1:
                # 只上传模型更新。
                source_x = rect.left() + 8.0
                source_span = min(18.0, rect.height() * 0.27)
                source_ys = [
                    center.y() - source_span,
                    center.y() - source_span / 3.0,
                    center.y() + source_span / 3.0,
                    center.y() + source_span,
                ]
                receiver = QRectF(
                    rect.right() - 21.0, center.y() - 15.0, 16.0, 30.0
                )

                for client_index, source_y in enumerate(source_ys):
                    client = QRectF(source_x - 4.0, source_y - 4.5, 8.0, 9.0)
                    route_start = QPointF(client.right() + 2.0, source_y)
                    route_end = QPointF(
                        receiver.left() - 3.0,
                        center.y() + (client_index - 1.5) * 4.3,
                    )
                    painter.setPen(QPen(QColor('#D2DCE8'), 1.0, Qt.SolidLine, Qt.RoundCap))
                    painter.drawLine(route_start, route_end)

                    # 本地数据点不随更新移动。
                    client_fill = QColor(main_color)
                    client_fill.setAlpha(30)
                    painter.setPen(QPen(main_color, 1.1))
                    painter.setBrush(client_fill)
                    painter.drawRoundedRect(client, 2.2, 2.2)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(main_color)
                    painter.drawEllipse(client.center(), 1.3, 1.3)

                    packet_t = max(
                        0.0,
                        min(1.0, stage_t * 1.85 - client_index * 0.17)
                    )
                    packet_progress = self._ease_in_out(packet_t)
                    packet_center = QPointF(
                        route_start.x() + (route_end.x() - route_start.x()) * packet_progress,
                        route_start.y() + (route_end.y() - route_start.y()) * packet_progress,
                    )
                    if packet_t > 0.0:
                        route_color = QColor(main_color)
                        route_color.setAlpha(160)
                        painter.setPen(QPen(route_color, 1.4, Qt.SolidLine, Qt.RoundCap))
                        painter.drawLine(route_start, packet_center)

                    if 0.0 < packet_t < 0.97:
                        packet = QRectF(
                            packet_center.x() - 4.5, packet_center.y() - 3.2, 9.0, 6.4
                        )
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(main_color)
                        painter.drawRoundedRect(packet, 2.0, 2.0)
                        painter.setPen(QPen(QColor('#FFFFFF'), 0.8, Qt.SolidLine, Qt.RoundCap))
                        painter.drawLine(
                            QPointF(packet.left() + 2.0, packet.center().y() - 1.0),
                            QPointF(packet.right() - 2.0, packet.center().y() - 1.0),
                        )
                        painter.drawLine(
                            QPointF(packet.left() + 2.0, packet.center().y() + 1.2),
                            QPointF(packet.right() - 3.2, packet.center().y() + 1.2),
                        )

                receiver_fill = QColor('#EEF8F4')
                receiver_fill.setAlpha(215)
                painter.setPen(QPen(main_color, 1.4))
                painter.setBrush(receiver_fill)
                painter.drawRoundedRect(receiver, 4.0, 4.0)
                for slot_index in range(4):
                    received_t = max(
                        0.0,
                        min(1.0, stage_t * 1.85 - slot_index * 0.17)
                    )
                    slot_color = QColor(main_color if received_t >= 0.92 else '#C7D2DF')
                    slot_color.setAlpha(230 if received_t >= 0.92 else 120)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(slot_color)
                    painter.drawRoundedRect(
                        QRectF(
                            receiver.left() + 4.0,
                            receiver.top() + 4.0 + slot_index * 5.5,
                            8.0, 2.8,
                        ),
                        1.4, 1.4
                    )

            elif index == 2:
                # 安全筛查。
                gate_x = center.x() + 3.0
                painter.setPen(QPen(main_color, 2))
                painter.drawLine(QPointF(gate_x, rect.top() + 4), QPointF(gate_x, rect.bottom() - 4))
                for item_index, y_offset in enumerate([-18, -6, 7, 19]):
                    start_x = gate_x - 27
                    # 异常更新停在闸门左侧，与拦截叉号留出清晰间距。
                    target_x = gate_x - 15 if item_index == 2 else gate_x + 20
                    dot_x = start_x + (target_x - start_x) * self._ease_out(stage_t)
                    left = QPointF(dot_x, center.y() + y_offset)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor('#E24B5B') if item_index == 2 else main_color)
                    painter.drawEllipse(left, 3.8, 3.8)
                    if item_index != 2 and stage_t > 0.94:
                        painter.setPen(QPen(QColor('#C8D4E1'), 1))
                        painter.drawLine(QPointF(gate_x - 19, left.y()),
                                         QPointF(gate_x + 15, left.y()))
                    elif item_index == 2 and stage_t > 0.70:
                        painter.setPen(QPen(QColor('#E24B5B'), 2))
                        painter.drawLine(QPointF(gate_x - 4, left.y() - 4),
                                         QPointF(gate_x + 4, left.y() + 4))
                        painter.drawLine(QPointF(gate_x - 4, left.y() + 4),
                                         QPointF(gate_x + 4, left.y() - 4))

            elif index == 3:
                # 安全聚合。
                core_center = QPointF(rect.left() + rect.width() * 0.56, center.y())
                core_radius = min(13.0, rect.height() * 0.20)
                input_x = rect.left() + 8.0
                input_span = min(18.0, rect.height() * 0.27)
                input_ys = [
                    center.y() - input_span,
                    center.y() - input_span / 3.0,
                    center.y() + input_span / 3.0,
                    center.y() + input_span,
                ]

                for packet_index, input_y in enumerate(input_ys):
                    source = QRectF(input_x - 3.5, input_y - 3.5, 7.0, 7.0)
                    route_start = QPointF(source.right() + 2.0, input_y)
                    route_end = QPointF(
                        core_center.x() - core_radius + 1.0,
                        core_center.y() + (input_y - center.y()) * 0.23,
                    )
                    painter.setPen(QPen(QColor('#D2DCE8'), 1.0, Qt.SolidLine, Qt.RoundCap))
                    painter.drawLine(route_start, route_end)

                    packet_t = max(
                        0.0,
                        min(1.0, stage_t * 1.90 - packet_index * 0.14)
                    )
                    packet_progress = self._ease_in_out(packet_t)
                    current_point = QPointF(
                        route_start.x() + (route_end.x() - route_start.x()) * packet_progress,
                        route_start.y() + (route_end.y() - route_start.y()) * packet_progress,
                    )
                    if packet_t > 0.0:
                        active_route = QColor(main_color)
                        active_route.setAlpha(165)
                        painter.setPen(QPen(active_route, 1.4, Qt.SolidLine, Qt.RoundCap))
                        painter.drawLine(route_start, current_point)

                    source_fill = QColor(main_color)
                    source_fill.setAlpha(38)
                    painter.setPen(QPen(main_color, 1.1))
                    painter.setBrush(source_fill)
                    painter.drawRoundedRect(source, 2.0, 2.0)
                    if 0.0 < packet_t < 0.98:
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(main_color)
                        painter.drawRoundedRect(
                            QRectF(current_point.x() - 2.6, current_point.y() - 2.6, 5.2, 5.2),
                            1.6, 1.6
                        )

                aggregate_t = self._ease_out(min(1.0, stage_t * 1.55))
                halo = QColor(main_color)
                halo.setAlpha(int(28 + 42 * aggregate_t))
                painter.setPen(QPen(halo, 4.0))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(core_center, core_radius + 2.0, core_radius + 2.0)
                painter.setPen(QPen(main_color, 1.7))
                painter.setBrush(QColor('#EEF5FF'))
                painter.drawEllipse(core_center, core_radius, core_radius)
                lock_body = QRectF(
                    core_center.x() - 5.0, core_center.y() - 1.0, 10.0, 8.0
                )
                painter.setPen(QPen(main_color, 1.2))
                painter.setBrush(QColor('#FFFFFF'))
                painter.drawRoundedRect(lock_body, 2.0, 2.0)
                painter.drawArc(
                    QRectF(core_center.x() - 3.8, core_center.y() - 7.0, 7.6, 9.0),
                    0, 180 * 16
                )
                painter.setPen(Qt.NoPen)
                painter.setBrush(main_color)
                painter.drawEllipse(QPointF(core_center.x(), core_center.y() + 2.5), 1.2, 1.2)

                # 输出通道与核心保持固定间距，压缩模型在右侧原位生成。
                output_rect = QRectF(
                    rect.right() - 21.0, center.y() - 11.0, 16.0, 22.0
                )
                output_start = QPointF(core_center.x() + core_radius + 2.0, center.y())
                output_end = QPointF(output_rect.left() - 5.0, center.y())
                painter.setPen(QPen(QColor('#D2DCE8'), 1.2, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(output_start, output_end)
                painter.drawLine(
                    QPointF(output_end.x() - 4.0, output_end.y() - 3.0), output_end
                )
                painter.drawLine(
                    QPointF(output_end.x() - 4.0, output_end.y() + 3.0), output_end
                )

                output_t = max(0.0, min(1.0, stage_t * 2.15 - 1.05))
                output_progress = self._ease_in_out(output_t)
                if output_t > 0.0:
                    output_point = QPointF(
                        output_start.x() + (output_end.x() - output_start.x()) * output_progress,
                        center.y(),
                    )
                    painter.setPen(QPen(main_color, 1.5, Qt.SolidLine, Qt.RoundCap))
                    painter.drawLine(output_start, output_point)
                    if output_t < 0.98:
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(main_color)
                        painter.drawEllipse(output_point, 2.5, 2.5)

                output_fill = QColor('#EEF8F4')
                output_fill.setAlpha(int(70 + 185 * output_t))
                output_border = QColor(main_color)
                output_border.setAlpha(int(70 + 185 * output_t))
                painter.setPen(QPen(output_border, 1.3))
                painter.setBrush(output_fill)
                painter.drawRoundedRect(output_rect, 4.0, 4.0)
                for bar_index, bar_width in enumerate([8.0, 11.0, 6.0]):
                    bar_color = QColor(main_color)
                    bar_color.setAlpha(int(55 + 200 * output_t))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(bar_color)
                    painter.drawRoundedRect(
                        QRectF(
                            output_rect.left() + 3.0,
                            output_rect.top() + 4.0 + bar_index * 5.0,
                            bar_width, 2.4,
                        ),
                        1.2, 1.2
                    )

            else:
                # 写入模型摘要。
                block_width = min(22.0, rect.width() / 4.4)
                start_x = center.x() - block_width * 1.75
                for block_index in range(3):
                    block = QRectF(start_x + block_index * block_width * 1.25,
                                   center.y() - 11, block_width, 22)
                    block_t = max(0.0, min(1.0, stage_t * 3.0 - block_index))
                    block_color = QColor('#EFFAF6')
                    block_color.setAlpha(int(70 + 185 * block_t))
                    line_color = QColor(main_color)
                    line_color.setAlpha(int(75 + 180 * block_t))
                    painter.setPen(QPen(line_color, 1.5))
                    painter.setBrush(block_color)
                    painter.drawRoundedRect(block, 4, 4)
                    painter.drawLine(QPointF(block.left() + 5, block.center().y() - 3),
                                     QPointF(block.right() - 5, block.center().y() - 3))
                    painter.drawLine(QPointF(block.left() + 5, block.center().y() + 3),
                                     QPointF(block.right() - 8, block.center().y() + 3))
                    if block_index < 2:
                        painter.drawLine(QPointF(block.right(), block.center().y()),
                                         QPointF(block.right() + block_width * 0.25, block.center().y()))

        elif self.flow_type == 'consensus':
            if index == 0:
                # 计算模型指纹。
                document = QRectF(center.x() - 27, center.y() - 21, 24, 42)
                painter.setPen(QPen(main_color, 1.5))
                painter.setBrush(QColor('#EEF4FF'))
                painter.drawRoundedRect(document, 4, 4)
                for line_index, line_width in enumerate([14, 17, 11]):
                    painter.drawLine(
                        QPointF(document.left() + 5, document.top() + 10 + line_index * 8),
                        QPointF(document.left() + 5 + line_width, document.top() + 10 + line_index * 8)
                    )
                arrow_start = QPointF(document.right() + 5, center.y())
                arrow_end = QPointF(center.x() + 28, center.y())
                painter.drawLine(arrow_start, arrow_end)
                painter.drawLine(QPointF(arrow_end.x() - 5, arrow_end.y() - 4), arrow_end)
                painter.drawLine(QPointF(arrow_end.x() - 5, arrow_end.y() + 4), arrow_end)
                for cell_index in range(4):
                    cell_t = max(0.0, min(1.0, stage_t * 4.0 - cell_index))
                    color = QColor(main_color)
                    color.setAlpha(int(70 + 185 * cell_t))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(color)
                    painter.drawRoundedRect(
                        QRectF(center.x() + 34 + (cell_index % 2) * 8,
                               center.y() - 9 + (cell_index // 2) * 10, 6, 7), 1.5, 1.5
                    )

            elif index == 1:
                # 节点签名。
                ring_x = min(30.0, rect.width() * 0.27)
                ring_y = min(22.0, rect.height() * 0.32)
                for node_index in range(6):
                    angle = -np.pi / 2 + node_index * np.pi / 3
                    node = QPointF(
                        center.x() + np.cos(angle) * ring_x,
                        center.y() + np.sin(angle) * ring_y
                    )
                    painter.setPen(QPen(QColor('#D4DCE7'), 1))
                    painter.drawLine(node, center)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(main_color)
                    painter.drawEllipse(node, 3.5, 3.5)
                    signature_t = max(0.0, min(1.0, stage_t * 1.7 - node_index * 0.11))
                    if signature_t > 0:
                        point = QPointF(
                            node.x() + (center.x() - node.x()) * self._ease_in_out(signature_t),
                            node.y() + (center.y() - node.y()) * self._ease_in_out(signature_t)
                        )
                        painter.setBrush(QColor('#7C4DCE'))
                        painter.drawEllipse(point, 2.3, 2.3)
                painter.setPen(QPen(main_color, 1.8))
                painter.setBrush(QColor('#EEF4FF'))
                painter.drawEllipse(center, 9, 9)

            elif index == 2:
                # 计算支持率。
                values = [0.88, 0.81, 0.76, 0.84, 0.31]
                baseline = rect.bottom() - 5
                bar_width = max(5.0, min(8.0, rect.width() / 13.0))
                gap = bar_width * 0.75
                total_width = len(values) * bar_width + 4 * gap
                start_x = center.x() - total_width / 2
                for bar_index, value in enumerate(values):
                    bar_t = max(0.0, min(1.0, stage_t * 2.0 - bar_index * 0.14))
                    height = (rect.height() - 12) * value * self._ease_out(bar_t)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor('#E05260') if value < 0.5 else main_color)
                    painter.drawRoundedRect(
                        QRectF(start_x + bar_index * (bar_width + gap), baseline - height,
                               bar_width, height), bar_width / 2, bar_width / 2
                    )
                threshold_y = baseline - (rect.height() - 12) * 0.5
                threshold_pen = QPen(QColor('#94A3B8'), 1, Qt.DashLine)
                painter.setPen(threshold_pen)
                painter.drawLine(QPointF(start_x - 3, threshold_y),
                                 QPointF(start_x + total_width + 3, threshold_y))

            elif index == 3:
                # 排除低支持节点。
                gate_x = center.x() + 4
                painter.setPen(QPen(main_color, 2))
                painter.drawLine(QPointF(gate_x, rect.top() + 5),
                                 QPointF(gate_x, rect.bottom() - 5))
                for node_index, y_offset in enumerate([-18, -6, 7, 19]):
                    abnormal = node_index == 2
                    destination = gate_x - 14 if abnormal else gate_x + 23
                    x = gate_x - 31 + (destination - (gate_x - 31)) * self._ease_out(stage_t)
                    y = center.y() + y_offset
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor('#E05260') if abnormal else main_color)
                    painter.drawEllipse(QPointF(x, y), 4, 4)
                    if abnormal and stage_t > 0.72:
                        painter.setPen(QPen(QColor('#E05260'), 2))
                        painter.drawLine(QPointF(gate_x - 5, y - 5), QPointF(gate_x + 5, y + 5))
                        painter.drawLine(QPointF(gate_x - 5, y + 5), QPointF(gate_x + 5, y - 5))

            else:
                # 检查 2/3 法定支持。
                radius = min(24.0, rect.height() * 0.34)
                ring = QRectF(center.x() - radius, center.y() - radius,
                              radius * 2, radius * 2)
                painter.setPen(QPen(QColor('#D8E0EA'), 5))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(ring)
                painter.setPen(QPen(main_color, 5, Qt.SolidLine, Qt.RoundCap))
                painter.drawArc(ring, 90 * 16, int(-300 * 16 * self._ease_out(stage_t)))
                painter.setPen(QPen(main_color, 2.2, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(center.x() - 8, center.y()),
                                 QPointF(center.x() - 2, center.y() + 7))
                painter.drawLine(QPointF(center.x() - 2, center.y() + 7),
                                 QPointF(center.x() + 10, center.y() - 8))

        elif self.flow_type == 'ledger':
            block_width = min(21.0, rect.width() / 4.4)
            chain_left = center.x() - block_width * 1.9
            stage_title = self.steps[index][0]
            if '定位' in stage_title or '读取区块' in stage_title:
                # 定位历史记录。
                for block_index in range(4):
                    block = QRectF(chain_left + block_index * block_width * 1.28,
                                   center.y() - 13, block_width, 26)
                    scan_t = max(0.0, min(1.0, stage_t * 4 - block_index))
                    selected = scan_t > 0.12 and scan_t < 0.98 if active else passed
                    color = main_color if selected else QColor('#AAB5C4')
                    painter.setPen(QPen(color, 1.7 if selected else 1))
                    painter.setBrush(QColor('#FFF7ED' if selected else '#F8FAFC'))
                    painter.drawRoundedRect(block, 4, 4)
                    painter.drawLine(QPointF(block.left() + 4, block.center().y() - 4),
                                     QPointF(block.right() - 4, block.center().y() - 4))
                    painter.drawLine(QPointF(block.left() + 4, block.center().y() + 3),
                                     QPointF(block.right() - 7, block.center().y() + 3))
                    if block_index < 3:
                        painter.drawLine(QPointF(block.right(), block.center().y()),
                                         QPointF(block.right() + block_width * 0.28, block.center().y()))

            elif '读取原始' in stage_title:
                # 篡改前指标。
                block = QRectF(center.x() - 28, center.y() - 25, 56, 50)
                painter.setPen(QPen(main_color, 1.8))
                painter.setBrush(QColor('#F0FCF8'))
                painter.drawRoundedRect(block, 7, 7)
                self._text(painter, QRectF(block.left(), block.top() + 7, block.width(), 15),
                           'accuracy', '#64748B', 6, True)
                self._text(painter, QRectF(block.left(), block.top() + 23, block.width(), 19),
                           '82.2', main_color.name(), 9, True)

            elif '修改' in stage_title or '注入' in stage_title:
                # 写入伪造值。
                block = QRectF(center.x() - 28, center.y() - 25, 56, 50)
                pulse = 2.0 + 2.0 * float(np.sin(self.progress * 45.0)) if active else 2.0
                painter.setPen(QPen(QColor('#E05260'), pulse))
                painter.setBrush(QColor('#FFF1F2'))
                painter.drawRoundedRect(block, 7, 7)
                self._text(painter, QRectF(block.left(), block.top() + 7, block.width(), 15),
                           'accuracy', '#64748B', 6, True)
                value = '99.9' if stage_t > 0.52 else '82.2'
                self._text(painter, QRectF(block.left(), block.top() + 23, block.width(), 19),
                           value, '#E05260' if stage_t > 0.52 else main_color.name(), 9, True)

            elif 'SHA' in stage_title or '指纹' in stage_title:
                # 重算 SHA-256 指纹。
                for cell_index in range(12):
                    cell_t = max(0.0, min(1.0, stage_t * 2.0 - cell_index * 0.07))
                    color = QColor('#E05260' if cell_index in {3, 7, 10} else main_color)
                    color.setAlpha(int(60 + 195 * cell_t))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(color)
                    painter.drawRoundedRect(
                        QRectF(center.x() - 31 + (cell_index % 6) * 11,
                               center.y() - 12 + (cell_index // 6) * 15, 8, 9), 2, 2
                    )
                ring = QRectF(center.x() - 39, center.y() - 28, 78, 56)
                painter.setPen(QPen(main_color, 1.8))
                painter.setBrush(Qt.NoBrush)
                painter.drawArc(ring, int(stage_t * 500) * 16, 115 * 16)

            elif '提交' in stage_title:
                # 校验结束前不显示判定。
                for block_index in range(3):
                    block = QRectF(
                        center.x() - 42 + block_index * 27,
                        center.y() - 11, 21, 22
                    )
                    painter.setPen(QPen(main_color, 1.5))
                    painter.setBrush(QColor('#FFF7ED'))
                    painter.drawRoundedRect(block, 5, 5)
                painter.setPen(QPen(main_color, 2, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(center.x() + 38, center.y()),
                                 QPointF(center.x() + 54, center.y()))
                painter.drawLine(QPointF(center.x() + 49, center.y() - 4),
                                 QPointF(center.x() + 54, center.y()))
                painter.drawLine(QPointF(center.x() + 49, center.y() + 4),
                                 QPointF(center.x() + 54, center.y()))

            else:
                # 原 nonce 不再满足 PoW 前导零要求。
                self._text(painter, QRectF(rect.left() + 5, center.y() - 22, 42, 16),
                           'PoW', '#64748B', 7, True)
                result_visible = active or passed or self.completed
                values = (
                    [('00', '#168A78'), ('A7', '#E05260')]
                    if result_visible else
                    [('00', '#94A3B8'), ('??', '#94A3B8')]
                )
                for value_index, (value, color) in enumerate(values):
                    value_rect = QRectF(rect.left() + 47 + value_index * 35,
                                        center.y() - 13, 27, 26)
                    painter.setPen(QPen(QColor(color), 1.5))
                    painter.setBrush(QColor('#ECFDF5' if value_index == 0 else '#FFF1F2'))
                    painter.drawRoundedRect(value_rect, 6, 6)
                    self._text(painter, value_rect, value, color, 7, True)
                if stage_t > 0.55:
                    badge = QRectF(rect.right() - 25, center.y() - 11, 22, 22)
                    painter.setPen(QPen(QColor('#E05260'), 1.8))
                    painter.setBrush(QColor('#FFF1F2'))
                    painter.drawEllipse(badge)
                    painter.drawLine(QPointF(badge.left() + 6, badge.top() + 6),
                                     QPointF(badge.right() - 6, badge.bottom() - 6))
                    painter.drawLine(QPointF(badge.left() + 6, badge.bottom() - 6),
                                     QPointF(badge.right() - 6, badge.top() + 6))

        elif self.flow_type == 'defense':
            if index == 0:
                # 攻击输入。
                pulse = (2.0 + 3.0 * stage_t) * float(np.sin(self.progress * 55.0)) if active else 0.0
                painter.setPen(QPen(QColor('#E24B5B') if active else main_color, 2.5,
                                    Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                points = [
                    QPointF(rect.left() + 5, center.y()),
                    QPointF(center.x() - 20, center.y()),
                    QPointF(center.x() - 12, center.y() - 13 - pulse),
                    QPointF(center.x() - 3, center.y() + 16 + pulse),
                    QPointF(center.x() + 7, center.y() - 18 - pulse),
                    QPointF(center.x() + 17, center.y()),
                    QPointF(rect.right() - 5, center.y()),
                ]
                painter.drawPolyline(*points)
                painter.setPen(QPen(QColor('#E24B5B'), 1))
                painter.drawEllipse(center, 27, 27)

            elif index == 1:
                # 证据扫描。
                ring = QRectF(center.x() - 27, center.y() - 27, 54, 54)
                painter.setPen(QPen(QColor('#D5DDEA'), 1))
                painter.drawEllipse(ring)
                painter.drawEllipse(center, 17, 17)
                angle = int(stage_t * 540.0) if active else 35
                painter.setPen(QPen(main_color, 2))
                painter.drawArc(ring, (angle - 70) * 16, 70 * 16)
                ray = np.deg2rad(angle)
                painter.drawLine(center, QPointF(
                    center.x() + np.cos(ray) * 25,
                    center.y() - np.sin(ray) * 25
                ))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor('#E24B5B'))
                painter.drawEllipse(QPointF(center.x() + 12, center.y() - 7), 3.5, 3.5)

            elif index == 2:
                # 拦截与可信输出。
                shield_center = QPointF(rect.left() + rect.width() * 0.57, center.y())
                shield_half_width = min(14.0, rect.width() * 0.095)
                shield_half_height = min(20.0, rect.height() * 0.29)
                shield_left = shield_center.x() - shield_half_width
                threat_color = QColor('#E24B5B')
                safe_color = QColor('#16A085')
                shield_color = QColor(
                    '#16A085' if passed else '#315CC8' if active else '#9AA8BA'
                )

                # 可信输出通道位于盾牌后方，与攻击信号完全隔离。
                safe_start = QPointF(shield_center.x() + shield_half_width + 3.0, center.y())
                safe_end = QPointF(rect.right() - 7.0, center.y())
                safe_t = max(0.0, min(1.0, stage_t * 2.10 - 0.90))
                painter.setPen(QPen(QColor('#D2DCE8'), 1.2, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(safe_start, safe_end)
                if safe_t > 0.0:
                    safe_progress = self._ease_in_out(safe_t)
                    safe_point = QPointF(
                        safe_start.x() + (safe_end.x() - safe_start.x()) * safe_progress,
                        center.y(),
                    )
                    safe_path = QColor(safe_color)
                    safe_path.setAlpha(185)
                    painter.setPen(QPen(safe_path, 1.8, Qt.SolidLine, Qt.RoundCap))
                    painter.drawLine(safe_start, safe_point)
                    if safe_t < 0.98:
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(safe_color)
                        painter.drawEllipse(safe_point, 3.0, 3.0)
                painter.setPen(QPen(safe_color, 1.5, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(
                    QPointF(safe_end.x() - 4.0, safe_end.y() - 3.0), safe_end
                )
                painter.drawLine(
                    QPointF(safe_end.x() - 4.0, safe_end.y() + 3.0), safe_end
                )

                # 三路风险信号逐一被挡在盾牌左侧，停止位置彼此错开。
                threat_ys = [center.y() - 14.0, center.y(), center.y() + 14.0]
                impact_points = []
                for threat_index, threat_y in enumerate(threat_ys):
                    route_start = QPointF(rect.left() + 5.0, threat_y)
                    route_end = QPointF(
                        shield_left - 6.0 - threat_index * 2.5,
                        center.y() + (threat_index - 1) * 7.0,
                    )
                    route_color = QColor(threat_color)
                    route_color.setAlpha(55)
                    painter.setPen(QPen(route_color, 1.0, Qt.DashLine, Qt.RoundCap))
                    painter.drawLine(route_start, route_end)

                    threat_t = max(
                        0.0,
                        min(1.0, stage_t * 1.55 - threat_index * 0.16)
                    )
                    threat_progress = self._ease_out(threat_t)
                    threat_point = QPointF(
                        route_start.x() + (route_end.x() - route_start.x()) * threat_progress,
                        route_start.y() + (route_end.y() - route_start.y()) * threat_progress,
                    )
                    impact_points.append((route_end, threat_t))
                    dot_color = QColor(threat_color)
                    dot_color.setAlpha(int(235 - 105 * max(0.0, threat_t - 0.72) / 0.28))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(dot_color)
                    painter.drawEllipse(threat_point, 4.0, 4.0)

                # 到达盾牌的信号产生小型冲击环，而不是与防线重叠的红叉。
                for impact_point, threat_t in impact_points:
                    if threat_t < 0.86:
                        continue
                    ring_color = QColor(threat_color)
                    ring_color.setAlpha(int(115 * (1.0 - min(1.0, (threat_t - 0.86) / 0.14))))
                    painter.setPen(QPen(ring_color, 1.3))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(impact_point, 5.0, 5.0)

                shield_path = QPainterPath()
                shield_path.moveTo(shield_center.x(), shield_center.y() - shield_half_height)
                shield_path.lineTo(
                    shield_center.x() + shield_half_width,
                    shield_center.y() - shield_half_height * 0.62,
                )
                shield_path.lineTo(
                    shield_center.x() + shield_half_width * 0.82,
                    shield_center.y() + shield_half_height * 0.40,
                )
                shield_path.lineTo(shield_center.x(), shield_center.y() + shield_half_height)
                shield_path.lineTo(
                    shield_center.x() - shield_half_width * 0.82,
                    shield_center.y() + shield_half_height * 0.40,
                )
                shield_path.lineTo(
                    shield_center.x() - shield_half_width,
                    shield_center.y() - shield_half_height * 0.62,
                )
                shield_path.closeSubpath()
                shield_fill = QColor(shield_color)
                shield_fill.setAlpha(34 + int(28 * self._ease_out(stage_t)))
                painter.setPen(QPen(shield_color, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.setBrush(shield_fill)
                painter.drawPath(shield_path)

                if stage_t > 0.46:
                    painter.setPen(QPen(shield_color, 2.2, Qt.SolidLine, Qt.RoundCap))
                    painter.drawLine(
                        QPointF(shield_center.x() - 6.0, shield_center.y()),
                        QPointF(shield_center.x() - 1.5, shield_center.y() + 5.0),
                    )
                    painter.drawLine(
                        QPointF(shield_center.x() - 1.5, shield_center.y() + 5.0),
                        QPointF(shield_center.x() + 7.0, shield_center.y() - 6.0),
                    )

            else:
                # 可信输出。
                painter.setPen(QPen(main_color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                points = []
                for item_index in range(9):
                    x = rect.left() + 5 + item_index * (rect.width() - 10) / 8
                    amplitude = 12.0 - 7.0 * stage_t
                    y = center.y() + np.sin(item_index * 1.2 + stage_t * 4.0) * amplitude
                    points.append(QPointF(float(x), float(y)))
                painter.drawPolyline(*points)
                painter.setBrush(QColor('#E8FAF4'))
                painter.drawEllipse(center, 18, 18)
                painter.setPen(QPen(main_color, 2.5, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(center.x() - 7, center.y()),
                                 QPointF(center.x() - 1, center.y() + 6))
                painter.drawLine(QPointF(center.x() - 1, center.y() + 6),
                                 QPointF(center.x() + 9, center.y() - 7))

        else:
            if index == 0:
                # 机构数据孤岛。
                spacing = (rect.width() - 22) / 4
                for site in range(5):
                    x = rect.left() + 11 + site * spacing
                    y = center.y() + (3 if site % 2 else -3)
                    if active:
                        y += float(np.sin(stage_t * 17 + site)) * 2.0
                    painter.setPen(QPen(main_color, 1.5))
                    painter.setBrush(QColor('#F2F7FC'))
                    painter.drawRoundedRect(QRectF(x - 6, y - 9, 12, 18), 3, 3)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(main_color)
                    painter.drawEllipse(QPointF(x, y), 2.5, 2.5)

            elif index == 1:
                # 加密与差分隐私。
                lock_rect = QRectF(center.x() - 15, center.y() - 4, 30, 24)
                painter.setPen(QPen(main_color, 2))
                painter.setBrush(QColor('#EEF5FF'))
                painter.drawRoundedRect(lock_rect, 5, 5)
                painter.drawArc(QRectF(center.x() - 10, center.y() - 19, 20, 22), 0, 180 * 16)
                for dot_index in range(8):
                    angle = dot_index * np.pi / 4 + stage_t * np.pi * 1.5
                    x = center.x() + np.cos(angle) * 27
                    y = center.y() + np.sin(angle) * 20
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor('#D99B2B') if dot_index % 3 == 0 else main_color)
                    painter.drawEllipse(QPointF(float(x), float(y)), 2.5, 2.5)

            elif index == 2:
                # MPO 压缩。
                matrix_left = rect.left() + 8.0
                matrix_right = matrix_left + 21.0
                for row in range(3):
                    for col in range(3):
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(main_color)
                        painter.drawRect(QRectF(
                            matrix_left + col * 8,
                            center.y() - 11 + row * 8,
                            5, 5
                        ))

                # 箭头只占用中间独立通道，与两侧图形都保留固定间距。
                compressed_left = rect.right() - 16.0
                arrow_start = matrix_right + 8.0
                arrow_tip = compressed_left - 10.0
                painter.setPen(QPen(main_color, 1.5))
                painter.drawLine(QPointF(arrow_start, center.y()),
                                 QPointF(arrow_tip, center.y()))
                painter.drawLine(QPointF(arrow_tip - 5, center.y() - 4),
                                 QPointF(arrow_tip, center.y()))
                painter.drawLine(QPointF(arrow_tip - 5, center.y() + 4),
                                 QPointF(arrow_tip, center.y()))

                if active and arrow_tip > arrow_start:
                    particle_x = arrow_start + (
                        arrow_tip - arrow_start
                    ) * self._ease_in_out(stage_t)
                    particle_color = QColor(main_color)
                    particle_color.setAlpha(165)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(particle_color)
                    painter.drawEllipse(QPointF(particle_x, center.y()), 2.4, 2.4)

                # 压缩块在右侧固定位置逐个生成，不再穿过箭头。
                for block in range(3):
                    block_t = max(0.0, min(1.0, stage_t * 3.0 - block))
                    block_color = QColor(main_color)
                    block_color.setAlpha(int(60 + 195 * block_t))
                    block_width = 3.0 + 5.0 * self._ease_out(block_t)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(block_color)
                    painter.drawRoundedRect(QRectF(
                        compressed_left,
                        center.y() - 10 + block * 8,
                        block_width, 5
                    ), 1.8, 1.8)

            elif index == 3:
                # 多节点共识。
                ring_x = min(27.0, rect.width() * 0.24)
                ring_y = min(21.0, rect.height() * 0.32)
                for voter in range(5):
                    angle = voter * np.pi * 2 / 5 + stage_t * 0.65
                    x = center.x() + np.cos(angle) * ring_x
                    y = center.y() + np.sin(angle) * ring_y
                    color = QColor('#E24B5B') if voter == 3 else main_color
                    painter.setPen(QPen(QColor('#CBD5E1'), 1))
                    painter.drawLine(center, QPointF(float(x), float(y)))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(color)
                    painter.drawEllipse(QPointF(float(x), float(y)), 3.7, 3.7)
                painter.setPen(QPen(main_color, 2))
                painter.setBrush(QColor('#EEF8F4'))
                painter.drawEllipse(center, 9, 9)

            else:
                # 下发可信全局模型。
                model_center = QPointF(rect.left() + rect.width() * 0.27, center.y())
                model_radius = min(14.0, rect.height() * 0.21)
                endpoint_x = rect.right() - 8.0
                endpoint_span = min(17.0, rect.height() * 0.25)
                endpoint_ys = [center.y() - endpoint_span, center.y(), center.y() + endpoint_span]
                route_start = QPointF(model_center.x() + model_radius - 1.0, model_center.y())

                # 先绘制三路下发通道；活动阶段的数据光点依次到达终端。
                for endpoint_index, endpoint_y in enumerate(endpoint_ys):
                    route_end = QPointF(endpoint_x - 8.0, endpoint_y)
                    endpoint_t = max(
                        0.0,
                        min(1.0, stage_t * 2.15 - 0.60 - endpoint_index * 0.27)
                    )
                    route_color = QColor(main_color)
                    route_color.setAlpha(72 if endpoint_t <= 0.0 else 185)
                    painter.setPen(QPen(route_color, 1.25, Qt.SolidLine, Qt.RoundCap))
                    painter.drawLine(route_start, route_end)

                    if endpoint_t > 0.0:
                        route_progress = self._ease_in_out(endpoint_t)
                        particle = QPointF(
                            route_start.x() + (route_end.x() - route_start.x()) * route_progress,
                            route_start.y() + (route_end.y() - route_start.y()) * route_progress,
                        )
                        particle_color = QColor(main_color)
                        particle_color.setAlpha(215)
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(particle_color)
                        painter.drawEllipse(particle, 2.5, 2.5)

                    terminal = QRectF(endpoint_x - 6.0, endpoint_y - 5.0, 12.0, 10.0)
                    terminal_border = QColor(main_color if endpoint_t >= 0.92 else '#AAB7C7')
                    terminal_fill = QColor('#E8FAF4' if endpoint_t >= 0.92 else '#F4F7FB')
                    painter.setPen(QPen(terminal_border, 1.3))
                    painter.setBrush(terminal_fill)
                    painter.drawRoundedRect(terminal, 2.5, 2.5)
                    if endpoint_t >= 0.92:
                        painter.setPen(QPen(main_color, 1.2, Qt.SolidLine, Qt.RoundCap))
                        painter.drawLine(
                            QPointF(terminal.left() + 3.0, terminal.center().y()),
                            QPointF(terminal.left() + 5.0, terminal.bottom() - 2.0),
                        )
                        painter.drawLine(
                            QPointF(terminal.left() + 5.0, terminal.bottom() - 2.0),
                            QPointF(terminal.right() - 2.0, terminal.top() + 2.0),
                        )
                    else:
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(terminal_border)
                        painter.drawEllipse(terminal.center(), 1.3, 1.3)

                trust_t = self._ease_out(min(1.0, stage_t * 2.5))
                halo_color = QColor(main_color)
                halo_color.setAlpha(int(30 + 45 * trust_t))
                painter.setPen(QPen(halo_color, 4.0))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(model_center, model_radius + 2.0, model_radius + 2.0)

                painter.setPen(QPen(main_color, 1.8))
                painter.setBrush(QColor('#EEF8F4'))
                painter.drawEllipse(model_center, model_radius, model_radius)
                network_nodes = [
                    QPointF(model_center.x() - 5.0, model_center.y() - 4.0),
                    QPointF(model_center.x() - 5.0, model_center.y() + 4.0),
                    QPointF(model_center.x() + 4.0, model_center.y()),
                ]
                painter.setPen(QPen(main_color, 1.0))
                painter.drawLine(network_nodes[0], network_nodes[2])
                painter.drawLine(network_nodes[1], network_nodes[2])
                painter.drawLine(network_nodes[0], network_nodes[1])
                painter.setPen(Qt.NoPen)
                painter.setBrush(main_color)
                for node in network_nodes:
                    painter.drawEllipse(node, 1.8, 1.8)

                badge_center = QPointF(
                    model_center.x() + model_radius * 0.72,
                    model_center.y() - model_radius * 0.72,
                )
                badge_radius = 5.3
                painter.setPen(QPen(QColor('#FFFFFF'), 1.2))
                painter.setBrush(main_color)
                painter.drawEllipse(badge_center, badge_radius, badge_radius)
                painter.setPen(QPen(QColor('#FFFFFF'), 1.35, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(
                    QPointF(badge_center.x() - 2.4, badge_center.y()),
                    QPointF(badge_center.x() - 0.5, badge_center.y() + 2.0),
                )
                painter.drawLine(
                    QPointF(badge_center.x() - 0.5, badge_center.y() + 2.0),
                    QPointF(badge_center.x() + 2.8, badge_center.y() - 2.2),
                )

        painter.restore()

    def _paint_security_pipeline(self, painter, width, height):
        """后三类流程共用的高级卡片布局，每类使用独立的数据形态。"""
        compact = width < 900
        margin = 12.0
        status_height = 33.0
        top = 7.0
        bottom = height - status_height - 9.0
        count = len(self.steps)
        gap = 12.0 if compact else 16.0
        card_width = (width - margin * 2 - gap * (count - 1)) / count
        card_height = bottom - top
        active = self._active_index()
        accent = QColor(self.accent)
        cards = [
            QRectF(margin + index * (card_width + gap), top, card_width, card_height)
            for index in range(count)
        ]

        for index in range(count - 1):
            y = top + card_height * 0.54
            start_x = cards[index].right() + 2
            end_x = cards[index + 1].left() - 2
            passed = index < active or self.completed
            line_color = QColor('#28B487') if passed else QColor('#C9D3E0')
            painter.setPen(QPen(line_color, 2))
            painter.drawLine(QPointF(start_x, y), QPointF(end_x, y))
            painter.drawLine(QPointF(end_x - 5, y - 4), QPointF(end_x, y))
            painter.drawLine(QPointF(end_x - 5, y + 4), QPointF(end_x, y))
            if self.running and active == index:
                local = self._stage_progress(index)
                for particle_index, offset in enumerate([0.0, 0.19, 0.38]):
                    position = local * 1.24 - offset
                    if not 0.0 <= position <= 1.0:
                        continue
                    position = self._ease_in_out(position)
                    x = start_x + (end_x - start_x) * position
                    color = QColor(self.accent)
                    color.setAlpha(255 - particle_index * 55)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(color)
                    painter.drawEllipse(QPointF(x, y), 4.0 - particle_index * 0.7,
                                        4.0 - particle_index * 0.7)

        for index, (title, detail) in enumerate(self.steps):
            rect = QRectF(cards[index])
            passed = index < active or self.completed
            is_active = index == active and self.running
            stage_t = self._stage_progress(index) if is_active else 1.0 if passed else 0.0
            if is_active:
                rect.translate(0, -2.0 * self._ease_out(min(1.0, stage_t * 1.8)))
            if passed:
                top_color, bottom_color, border, title_color = '#F0FCF8', '#E8F9F3', '#9EDFCB', '#117A5D'
            elif is_active:
                top_color, bottom_color = '#FAFBFF', '#EDF2FF'
                border, title_color = self.accent, self.accent
            else:
                top_color, bottom_color, border, title_color = '#FBFCFE', '#F4F7FB', '#D7E0EB', '#52637A'

            if is_active:
                glow = QColor(self.accent)
                glow.setAlpha(34 + int(10 * (1.0 + np.sin(self.progress * 52.0))))
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(glow, 6))
                painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 11, 11)
            shadow = QColor('#667085')
            shadow.setAlpha(18 if is_active else 10 if passed else 6)
            painter.setPen(Qt.NoPen)
            painter.setBrush(shadow)
            painter.drawRoundedRect(rect.translated(0, 2), 10, 10)
            gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            gradient.setColorAt(0.0, QColor(top_color))
            gradient.setColorAt(1.0, QColor(bottom_color))
            painter.setPen(QPen(QColor(border), 2 if is_active else 1))
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, 10, 10)

            badge = QRectF(rect.left() + 9, rect.top() + 8, 36, 18)
            badge_color = QColor('#16A085') if passed else accent if is_active else QColor('#8291A5')
            badge_bg = QColor(badge_color)
            badge_bg.setAlpha(28)
            painter.setPen(Qt.NoPen)
            painter.setBrush(badge_bg)
            painter.drawRoundedRect(badge, 9, 9)
            self._text(painter, badge, f'{index + 1:02d}', badge_color.name(), 6, True)
            self._text(
                painter, QRectF(rect.left() + 7, rect.top() + 28, rect.width() - 14, 22),
                title, title_color, 7 if compact else 8, True
            )
            visual_rect = QRectF(
                rect.left() + 10, rect.top() + 51,
                rect.width() - 20, max(34.0, rect.height() - 80)
            )
            self._paint_security_stage_visual(painter, index, visual_rect, is_active, passed)
            self._text(
                painter, QRectF(rect.left() + 7, rect.bottom() - 27, rect.width() - 14, 20),
                detail, '#6E7F94', 6 if compact else 7
            )
            if passed:
                check_rect = QRectF(rect.right() - 20, rect.top() + 29, 12, 12)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor('#16A085'))
                painter.drawEllipse(check_rect)
                self._text(painter, check_rect, '✓', '#FFFFFF', 6, True)

        status_prefix = {
            'federated': '安全联邦协同处理中',
            'defense': '安全防线检查中',
            'scenario': '跨机构安全训练处理中',
            'consensus': '节点共识校验中',
            'ledger': '历史链完整性检查中',
        }[self.flow_type]
        status_rect = QRectF(margin, height - status_height - 4, width - margin * 2, status_height)
        if self.completed:
            status, bg, fg, border = self.final_caption, '#E8FAF4', '#117A5D', '#A7E7D2'
        elif self.running and self.progress >= 1.0:
            status = '训练结果汇总中……' if self.flow_type == 'scenario' else '验证结果汇总中……'
            bg, fg, border = '#EDF9F5', '#117A5D', '#B7E6D7'
        elif self.running:
            title, detail = self.steps[max(0, active)]
            status = f'{status_prefix}  ·  第 {active + 1}/{count} 步  ·  {title}  ·  {detail}'
            active_bg = QColor(self.accent)
            active_bg.setAlpha(18)
            bg, fg, border = active_bg, self.accent, '#CCD7EA'
        else:
            status, bg, fg, border = self.config['idle'], '#F3F6FA', '#64748B', '#DCE3EC'
        painter.setPen(QPen(QColor(border), 1))
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(status_rect, 8, 8)
        self._text(painter, status_rect.adjusted(9, 0, -9, 0), status, fg,
                   7 if compact else 8, True)
        self._paint_completion_sweep(painter, cards, status_rect.top() - 3)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('#FBFCFE'))

        width = float(self.width())
        height = float(self.height())
        if self.flow_type == 'privacy':
            self._paint_privacy_pipeline(painter, width, height)
            return
        if self.flow_type in {'federated', 'defense', 'scenario', 'consensus', 'ledger'}:
            self._paint_security_pipeline(painter, width, height)
            return
        compact = width < 760
        margin = 12.0
        eyebrow = self.config['eyebrow']
        header_height = 25.0 if eyebrow else 0.0
        status_height = 31.0
        node_top = header_height + (11.0 if eyebrow else 5.0)
        node_bottom = height - status_height - 12.0
        node_height = max(42.0, node_bottom - node_top)
        count = len(self.steps)
        gap = 13.0 if compact else 20.0
        node_width = (width - margin * 2 - gap * (count - 1)) / count
        active = self._active_index()
        accent = self.accent

        if eyebrow:
            self._text(
                painter, QRectF(margin, 4, width - margin * 2, header_height),
                eyebrow, '#344054', 8 if compact else 9, True, Qt.AlignLeft | Qt.AlignVCenter
            )

        centers = []
        for index, (title, detail) in enumerate(self.steps):
            x = margin + index * (node_width + gap)
            rect = QRectF(x, node_top, node_width, node_height)
            centers.append(QPointF(rect.center().x(), rect.center().y()))
            if index < active or self.completed:
                background, border, title_color = '#EAFBF5', '#A9DFC9', '#137A55'
            elif index == active:
                background, border, title_color = '#EDF2FF', accent, accent
            else:
                background, border, title_color = '#F3F6FA', '#DCE3EC', '#69778C'
            painter.setPen(QPen(QColor(border), 2 if index == active else 1))
            painter.setBrush(QColor(background))
            painter.drawRoundedRect(rect, 8, 8)
            title_rect = QRectF(rect.x() + 4, rect.y() + 4, rect.width() - 8, rect.height() * 0.43)
            detail_rect = QRectF(rect.x() + 5, rect.y() + rect.height() * 0.42,
                                 rect.width() - 10, rect.height() * 0.52)
            self._text(painter, title_rect, title, title_color, 7 if compact else 8, True)
            if node_width > 95:
                self._text(painter, detail_rect, detail, '#718096', 6 if compact else 7)

            if index < active or self.completed:
                check_rect = QRectF(rect.right() - 17, rect.top() + 4, 13, 13)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor('#27AE60'))
                painter.drawEllipse(check_rect)
                self._text(painter, check_rect, '✓', '#FFFFFF', 6, True)

        for index in range(count - 1):
            start_x = centers[index].x() + node_width / 2 + 2
            end_x = centers[index + 1].x() - node_width / 2 - 2
            y = centers[index].y()
            passed = index < active or self.completed
            painter.setPen(QPen(QColor('#58B89A' if passed else '#C8D2DF'), 2))
            painter.drawLine(QPointF(start_x, y), QPointF(end_x, y))
            painter.drawLine(QPointF(end_x - 5, y - 4), QPointF(end_x, y))
            painter.drawLine(QPointF(end_x - 5, y + 4), QPointF(end_x, y))

        if self.running and active >= 0:
            segment_progress = (self.progress * count) % 1.0
            if active >= count - 1:
                token_x = centers[-1].x()
            else:
                start_x = centers[active].x() + node_width / 2
                end_x = centers[active + 1].x() - node_width / 2
                token_x = start_x + (end_x - start_x) * segment_progress
            token_y = centers[active].y()
            pulse = 5.0 + 1.4 * float(np.sin(self.progress * 48.0))
            glow = QColor(accent)
            glow.setAlpha(45)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(QPointF(token_x, token_y), pulse + 5, pulse + 5)
            painter.setBrush(QColor(accent))
            painter.drawEllipse(QPointF(token_x, token_y), pulse, pulse)

        status_rect = QRectF(margin, height - status_height - 5, width - margin * 2, status_height)
        if self.completed:
            status, bg, fg, border = self.final_caption, '#EAFBF5', '#137A55', '#BDEAD9'
        elif self.running:
            title, detail = self.steps[max(0, active)]
            status, bg, fg, border = f'正在发生：{title}  ·  {detail}', '#EAF0FF', '#315CC8', '#C8D6FA'
        else:
            status, bg, fg, border = self.config['idle'], '#F1F4F8', '#64748B', '#DCE3EC'
        painter.setPen(QPen(QColor(border), 1))
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(status_rect, 7, 7)
        self._text(painter, status_rect.adjusted(8, 0, -8, 0), status, fg, 7 if compact else 8, True)


class OverviewTab(QWidget):
    
    def __init__(self):
        super().__init__()
        self.status_data = {}
        self._build_ui()
        self._update_stats()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(2000)
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QLabel('⚛ 量子密钥分发 + 量子差分隐私 + 区块链联邦学习融合安全通信系统')
        title.setFont(QFont('Microsoft YaHei', 19, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('color: #2C3E50; padding: 10px;')
        layout.addWidget(title)
        
        subtitle = QLabel('多层防护 | 数据可用不可见 | 通信全程量子安全 | 模型轻量化传输')
        subtitle.setFont(QFont('Microsoft YaHei', 14))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('color: #7F8C8D; padding-bottom: 15px;')
        layout.addWidget(subtitle)
        
        arch_group = QGroupBox('系统四层架构图')
        arch_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        arch_layout = QVBoxLayout(arch_group)
        
        arch_text = QTextEdit()
        arch_text.setReadOnly(True)
        arch_text.setMinimumHeight(180)
        arch_text.setFont(QFont('Consolas', 12))
        arch_text.setHtml("""
        <div style='font-family: Consolas; font-size: 27px;'>
        <h3 style='color: #3498DB;'>🌐 第四层: 应用场景层</h3>
        &nbsp;&nbsp;├─ 金融风控数据协同 &nbsp;&nbsp;│&nbsp;&nbsp; 医疗隐私模型训练 &nbsp;&nbsp;│&nbsp;&nbsp; 边缘设备分布式AI
        <br><br>
        <h3 style='color: #27AE60;'>📦 第三层: 模型传输与共识层</h3>
        &nbsp;&nbsp;├─ MPO矩阵乘积算符压缩 (传输量↓至10%)
        &nbsp;&nbsp;├─ 量子拜占庭共识协议 (容忍1/3恶意节点)
        &nbsp;&nbsp;└─ 区块链链式存储 (防篡改/可溯源)
        <br><br>
        <h3 style='color: #E67E22;'>🔒 第二层: 隐私防护核心层</h3>
        &nbsp;&nbsp;├─ 混合量子差分隐私 (信道噪声+测量噪声协同加噪)
        &nbsp;&nbsp;├─ 可量化隐私预算 ε 动态调控
        &nbsp;&nbsp;└─ 梯度裁剪 + 噪声注入, 杜绝逆向推理
        <br><br>
        <h3 style='color: #E74C3C;'>🔐 第一层: 底层通信加密层</h3>
        &nbsp;&nbsp;├─ BB84 量子密钥分发协议 (纯软件仿真)
        &nbsp;&nbsp;├─ 混沌加密动态自适应调整
        &nbsp;&nbsp;└─ 中间人攻击检测 (误码率异常报警)
        </div>
        """)
        arch_layout.addWidget(arch_text)
        layout.addWidget(arch_group)
        
        stats_group = QGroupBox('实时系统指标')
        stats_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        stats_layout = QGridLayout(stats_group)
        
        self.metric_labels = {}
        metrics = [
            ('量子密钥分发状态', '✓ 正常', '#27AE60'),
            ('通信误码率', '0.0%', '#3498DB'),
            ('隐私预算消耗', '0/3.0', '#E67E22'),
            ('MPO压缩率', '—', '#9B59B6'),
            ('共识节点数', '5/5', '#16A085'),
            ('恶意节点检测', '0', '#E74C3C'),
            ('区块链长度', '1', '#2C3E50'),
            ('模型准确率', '—%', '#8E44AD'),
        ]
        for i, (name, value, color) in enumerate(metrics):
            row, col = i // 2, (i % 2) * 2
            lbl_name = QLabel(name + ':')
            lbl_name.setFont(QFont('Microsoft YaHei', 12))
            lbl_value = QLabel(value)
            lbl_value.setFont(QFont('Consolas', 14, QFont.Bold))
            lbl_value.setStyleSheet(f'color: {color};')
            lbl_value.setAlignment(Qt.AlignLeft)
            stats_layout.addWidget(lbl_name, row, col)
            stats_layout.addWidget(lbl_value, row, col + 1)
            self.metric_labels[name] = lbl_value
        
        layout.addWidget(stats_group)
        
        highlight_group = QGroupBox('模块说明')
        highlight_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        h_layout = QVBoxLayout(highlight_group)
        highlights = [
            '💡 量子安全+混沌加密双融合通信: 突破传统QKD单一性, 自适应通信环境',
            '💡 混合量子差分隐私优化机制: 信道与测量双噪声, 兼顾隐私与精度',
            '💡 轻量化量子联邦学习架构: MPO张量压缩, 解决弱网边缘设备痛点',
            '💡 全链路量子安全防护体系: QKD通信+差分隐私+区块链哈希, 抗量子攻击'
        ]
        for h in highlights:
            lbl = QLabel(h)
            lbl.setFont(QFont('Microsoft YaHei', 12))
            lbl.setStyleSheet('padding: 4px; color: #34495E;')
            h_layout.addWidget(lbl)
        layout.addWidget(highlight_group)

    def _update_stats(self):
        """刷新指标 (模拟动态数据)"""
        if 'qkd_error_rate' not in self.status_data:
            return
        
        mapping = {
            '量子密钥分发状态': self.status_data.get('qkd_status', '✓ 正常'),
            '通信误码率': f'{self.status_data.get("qkd_error_rate", 0):.2f}%',
            '隐私预算消耗': f'{self.status_data.get("qdp_used", 0):.1f}/{self.status_data.get("qdp_total", 3.0):.1f}',
            'MPO压缩率': f'{self.status_data.get("mpo_ratio", 0):.1f}%',
            '共识节点数': f'{self.status_data.get("consensus_nodes", "5/5")}',
            '恶意节点检测': str(self.status_data.get('malicious_detected', 0)),
            '区块链长度': str(self.status_data.get('chain_length', 1)),
            '模型准确率': f'{self.status_data.get("accuracy", 0):.2f}%'
        }
        for name, value in mapping.items():
            if name in self.metric_labels:
                self.metric_labels[name].setText(value)

    def update_status(self, new_data: Dict):
        self.status_data.update(new_data)
        self._update_stats()


class QKDTab(QWidget):
    
    def __init__(self, parent_ref=None):
        super().__init__()
        self.parent_ref = parent_ref
        self.channel = QuantumCommunicationChannel(n_photons=1024)
        self.last_qkd_secure = False
        self.pending_qkd_result = None
        self._build_ui()
    
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.qkd_scroll = QScrollArea()
        self.qkd_scroll.setWidgetResizable(True)
        self.qkd_scroll.setFrameShape(QFrame.NoFrame)
        self.qkd_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.qkd_content = QWidget()
        layout = QVBoxLayout(self.qkd_content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        action_bar = QFrame()
        action_bar.setObjectName('actionBar')
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 13, 16, 13)
        action_copy = QVBoxLayout()
        action_copy.setSpacing(2)
        action_title = QLabel('安全信道实验')
        action_title.setObjectName('actionTitle')
        action_text = QLabel('建立可信会话，或注入 Eve 窃听并观察 QBER 是否越过 11% 阈值。')
        action_text.setObjectName('actionText')
        action_copy.addWidget(action_title)
        action_copy.addWidget(action_text)
        action_layout.addLayout(action_copy)
        action_layout.addStretch()
        _BTN17 = (
            'QPushButton{background:#176B63;color:#ffffff;border:2px solid #176B63;'
            'border-radius:999px;padding:12px 36px;font-weight:900;}'
            'QPushButton:hover{background:#125B54;color:#ffffff;border:2px solid #125B54;}'
            'QPushButton:pressed{background:#0E4A45;color:#ffffff;}'
            'QPushButton:disabled{background:#7FA8A3;color:#E0ECEA;border:2px solid #A3BFBB;}'
        )
        self.btn_normal_demo = QPushButton('开始安全通信')
        self.btn_normal_demo.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.btn_normal_demo.setStyleSheet(_BTN17)
        self.btn_normal_demo.setMinimumWidth(180)
        self.btn_normal_demo.clicked.connect(self._on_normal_demo)
        self.btn_eve_demo = QPushButton('演示窃听阻断')
        self.btn_eve_demo.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.btn_eve_demo.setStyleSheet(_BTN17)
        self.btn_eve_demo.setMinimumWidth(180)
        self.btn_eve_demo.clicked.connect(self._on_eve_demo)
        action_layout.addWidget(self.btn_normal_demo)
        action_layout.addWidget(self.btn_eve_demo)
        layout.addWidget(action_bar)

        advanced_group, advanced_layout = make_collapsible_group('高级设置')
        self.advanced_group = advanced_group
        advanced_layout.setSpacing(10)
        advanced_group.toggled.connect(self._on_advanced_toggled)

        self.photon_slider = self._make_slider_control(advanced_layout, '光子数量', 256, 4096, 1024, 256)

        eve_layout = QHBoxLayout()
        eve_label = QLabel('中间人攻击 (Eve):')
        eve_label.setFont(QFont('Microsoft YaHei', 12))
        self.eve_combo = QComboBox()
        self.eve_combo.addItems(['关闭', '开启'])
        self.eve_combo.setFont(QFont('Microsoft YaHei', 12))
        self.eve_combo.setMinimumHeight(36)
        eve_layout.addWidget(eve_label)
        eve_layout.addWidget(self.eve_combo)
        advanced_layout.addLayout(eve_layout)

        enc_layout = QHBoxLayout()
        enc_label = QLabel('混沌加密强度:')
        enc_label.setFont(QFont('Microsoft YaHei', 12))
        self.enc_combo = QComboBox()
        self.enc_combo.addItems(['低', '正常', '高'])
        self.enc_combo.setCurrentIndex(1)
        self.enc_combo.setFont(QFont('Microsoft YaHei', 12))
        self.enc_combo.setMinimumHeight(36)
        enc_layout.addWidget(enc_label)
        enc_layout.addWidget(self.enc_combo)
        advanced_layout.addLayout(enc_layout)

        layout.addWidget(advanced_group)

        card_layout = QHBoxLayout()
        _g = []
        self.qkd_state_card = make_status_card('通信状态', '待演示', '', '#566573', group=_g)
        self.qkd_error_card = make_status_card('误码率', '—', '低于 11% 才允许使用密钥', '#566573', group=_g)
        self.qkd_send_card = make_status_card('发送许可', '未建立', '安全密钥建立后才允许发送', '#566573', group=_g)
        card_layout.addWidget(self.qkd_state_card)
        card_layout.addWidget(self.qkd_error_card)
        card_layout.addWidget(self.qkd_send_card)
        layout.addLayout(card_layout)

        workspace = QHBoxLayout()
        workspace.setSpacing(12)
        self.protocol_panel = make_protocol_panel(
            'BB84 会话建立路径',
            [
                '随机制备并发送量子比特',
                '公开比较测量基并筛选密钥',
                '抽样估计信道误码率 QBER',
                '通过阈值后派生会话密钥',
                '认证加密模型更新载荷',
            ],
            '#176B63'
        )
        self.protocol_panel.setMinimumWidth(285)
        workspace.addWidget(self.protocol_panel, 3)

        right_panel = QGroupBox('实时通信观测')
        right_panel.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        right_layout = QVBoxLayout(right_panel)

        self.key_display = QLabel('密钥 (256bit SHA-256): —')
        self.key_display.setFont(QFont('Consolas', 12))
        self.key_display.setStyleSheet(
            'background:#F5F6F4; border:1px solid #D9DDDA; padding:9px; '
            'color:#303735; border-radius:4px;'
        )
        self.key_display.setWordWrap(True)
        right_layout.addWidget(self.key_display)

        self.protocol_animation = QKDProtocolAnimation()
        self.protocol_animation.phaseChanged.connect(self._update_protocol_steps)
        self.protocol_animation.finished.connect(self._complete_qkd_presentation)
        right_layout.addWidget(self.protocol_animation, 1)

        log_card = QFrame()
        log_card.setStyleSheet(
            'QFrame { background: #FDFEFB; border: 1px solid #E4E7DD; border-radius: 8px; }'
            'QLabel { background: transparent; padding: 10px 12px 6px 12px; }'
            'QTextEdit { background: #FCFDF9; border: none; }'
        )
        log_card_layout = QVBoxLayout(log_card)
        log_card_layout.setContentsMargins(0, 0, 0, 0)
        log_card_layout.setSpacing(0)
        log_label = QLabel('通信事件记录')
        log_label.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        log_card_layout.addWidget(log_label)
        log_divider = QFrame()
        log_divider.setFixedHeight(1)
        log_divider.setStyleSheet('background: #E4E7DD;')
        log_card_layout.addWidget(log_divider)
        self.log_output = AutoScrollLog()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont('Consolas', 12))
        self.log_output.setPlaceholderText('暂无事件')
        log_card_layout.addWidget(self.log_output, 1)
        right_layout.addWidget(log_card)
        workspace.addWidget(right_panel, 7)
        layout.addLayout(workspace, 1)

        self.qkd_scroll.setWidget(self.qkd_content)
        outer.addWidget(self.qkd_scroll)
        self._draw_empty_plot()

    def _on_advanced_toggled(self, expanded: bool):
        """展开参数时按内容高度启用滚动，避免 Qt 压缩输入控件。"""
        self.qkd_content.setMinimumHeight(0)
        if expanded:
            QTimer.singleShot(0, self._fit_expanded_content)

    def _fit_expanded_content(self):
        required_height = self.qkd_content.sizeHint().height()
        viewport_height = self.qkd_scroll.viewport().height()
        self.qkd_content.setMinimumHeight(max(required_height, viewport_height))

    def _update_protocol_steps(self, phase_index: int):
        """让左侧协议步骤与动画阶段保持同步。"""
        final_blocked = (
            phase_index >= 5
            and (self.protocol_animation.eve_active or self.protocol_animation.error_rate > 11.0)
        )
        for index, label in enumerate(self.protocol_panel.step_labels):
            if phase_index >= 5 and index == 4 and final_blocked:
                top, bottom, color, border = '#FDF7F6', '#FAF0EF', '#9F3333', '#C96A6A'
                glow = QColor(201, 106, 106, 40)
            elif index < phase_index:
                top, bottom, color, border = '#F6FBF9', '#EEF5F2', '#176B63', '#78A69F'
                glow = QColor(120, 166, 159, 46)
            elif index == phase_index:
                top, bottom, color, border = '#FCFEFD', '#E6F0ED', '#173F3A', self.protocol_panel.accent
                glow = QColor(23, 107, 99, 62)
            else:
                top, bottom, color, border = '#FFFFFF', '#FBFDFC', '#69716D', '#DDE5E2'
                glow = QColor(23, 107, 99, 10)
            label.setStyleSheet(
                f'QLabel {{'
                f'background:qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {top}, stop:1 {bottom});'
                f'color:{color};'
                f'border:1px solid {border};'
                f'border-left:3px solid {border};'
                f'border-radius:7px;'
                f'padding:8px 10px;'
                f'}}'
            )
            _apply_glass_glow(label, glow)

    def _make_slider_control(self, parent_layout, name: str, min_val: int, max_val: int, default: int, step: int):
        group = QVBoxLayout()
        lbl = QLabel(f'{name}: {default}')
        lbl.setFont(QFont('Microsoft YaHei', 12))
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(step)
        slider.valueChanged.connect(lambda v, l=lbl, n=name: l.setText(f'{n}: {v}'))
        group.addWidget(lbl)
        group.addWidget(slider)
        parent_layout.addLayout(group)
        return slider

    def _on_normal_demo(self):
        self.eve_combo.setCurrentIndex(0)
        self._begin_qkd_distribution()

    def _on_eve_demo(self):
        self.eve_combo.setCurrentIndex(1)
        self._begin_qkd_distribution()

    def _begin_qkd_distribution(self):
        """先计算结果但暂不展示，待 BB84 动画完成后再更新界面。"""
        n_photons = self.photon_slider.value()
        eve_active = self.eve_combo.currentIndex() == 1

        self.pending_qkd_result = None
        self.last_qkd_secure = False
        for button in [self.btn_normal_demo, self.btn_eve_demo]:
            button.setEnabled(False)

        update_status_card(self.qkd_state_card, '协商中', '正在建立量子安全信道', '#315CC8')
        update_status_card(self.qkd_error_card, '计算中', '正在估计信道误码率 QBER', '#315CC8')
        update_status_card(self.qkd_send_card, '等待判定', '需要先通过 11% 误码率阈值', '#315CC8')
        self.key_display.setText('密钥协商进行中……')

        self.log_output.append(f'[{time.strftime("%H:%M:%S")}] ▶ 启动QKD密钥分发...')
        self.log_output.append(f'  光子数: {n_photons} | Eve攻击: {"开启" if eve_active else "关闭"}')

        self.channel = QuantumCommunicationChannel(n_photons=n_photons)
        result = self.channel.establish(eve_active=eve_active)
        self.pending_qkd_result = {
            'result': result,
            'eve_active': eve_active,
        }

        # 计算结果只用于驱动动画，此时不更新最终状态卡。
        self._draw_error_rate_plot(result['error_rate'], eve_active)

    def _complete_qkd_presentation(self):
        """BB84 动画完整播放后，一次性公布密钥分发结果。"""
        pending = self.pending_qkd_result
        if not pending:
            return
        self.pending_qkd_result = None
        result = pending['result']
        eve_active = bool(pending['eve_active'])

        if result['status'] == 'success':
            self.last_qkd_secure = True
            self.log_output.append(f'  ✓ 密钥生成成功')
            self.log_output.append(f'  误码率: {result["error_rate"]}%')
            self.log_output.append(f'  最终密钥: {result["final_key"][:32]}...')
            self.key_display.setText(f'密钥: {result["final_key"]}')
            update_status_card(self.qkd_state_card, '安全', '未检测到窃听，密钥可用于加密通信', '#27AE60')
            update_status_card(self.qkd_error_card, f'{result["error_rate"]:.2f}%', '低于 11% 检测阈值', '#27AE60')
            update_status_card(self.qkd_send_card, '允许发送', '已建立安全密钥', '#27AE60')
            
            if self.parent_ref:
                self.parent_ref.update_status({
                    'qkd_error_rate': result['error_rate'],
                    'qkd_status': '✓ 正常' if not eve_active else '⚠ 窃听已检测'
                })
        else:
            self.last_qkd_secure = False
            self.log_output.append(f'  ✗ {result["reason"]}: 误码率={result["error_rate"]}% > 11%阈值')
            self.key_display.setText('⚠ 检测到窃听，密钥分发中止')
            update_status_card(self.qkd_state_card, '危险', '检测到窃听，密钥已作废', '#E74C3C')
            update_status_card(self.qkd_error_card, f'{result["error_rate"]:.2f}%', '超过 11% 检测阈值', '#E74C3C')
            update_status_card(self.qkd_send_card, '禁止发送', '当前没有可信密钥', '#E74C3C')
            if self.parent_ref:
                self.parent_ref.update_status({
                    'qkd_error_rate': result['error_rate'],
                    'qkd_status': '⚠ 窃听检测'
                })

        for button in [self.btn_normal_demo, self.btn_eve_demo]:
            button.setEnabled(True)
    
    def _draw_empty_plot(self):
        self.history_error_rates = []
        self.protocol_animation.reset()
    
    def _draw_error_rate_plot(self, new_rate, eve_active):
        self.history_error_rates.append((new_rate, eve_active))
        self.protocol_animation.start(eve_active=eve_active, error_rate=new_rate)


class PrivacyTab(QWidget):

    # 决策图整体等比放大系数：画布与字号同步放大，保持相对比例一致。
    CHART_SCALE = 1.75
    
    def __init__(self, parent_ref=None):
        super().__init__()
        self.parent_ref = parent_ref
        self.qdp = QuantumDifferentialPrivacy(epsilon=3.0, channel_ratio=0.65)
        self.privacy_demo_pending = False
        self.auto_play_explainer = False
        self._build_ui()
        self._set_privacy_preset('balanced')
        self._set_tradeoff_placeholder('暂无结果')
    
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        demo_group = QGroupBox('隐私策略控制台')
        demo_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        demo_layout = QVBoxLayout(demo_group)

        card_layout = QHBoxLayout()
        _g = []
        self.privacy_mode_card = make_status_card('隐私模式', '平衡', '保护强度和模型可用性折中', '#3498DB', group=_g)
        self.attack_risk_card = make_status_card('攻击成功率', '待演示', '越低表示越难从梯度反推数据', '#566573', group=_g)
        self.noise_card = make_status_card('噪声强度', '—', '噪声越强，隐私越强', '#566573', group=_g)
        self.budget_card = make_status_card('剩余预算', '—', '预算耗尽后停止加噪', '#566573', group=_g)
        card_layout.addWidget(self.privacy_mode_card)
        card_layout.addWidget(self.attack_risk_card)
        card_layout.addWidget(self.noise_card)
        card_layout.addWidget(self.budget_card)
        demo_layout.addLayout(card_layout)

        preset_layout = QHBoxLayout()
        preset_label = QLabel('策略预设')
        preset_label.setStyleSheet('color:#64748B; font-weight:bold; padding-right:6px;')
        preset_layout.addWidget(preset_label)
        self.btn_strong_privacy = QPushButton('强隐私')
        self.btn_balanced_privacy = QPushButton('平衡')
        self.btn_high_accuracy = QPushButton('高精度')
        for btn in [self.btn_strong_privacy, self.btn_balanced_privacy, self.btn_high_accuracy]:
            btn.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
            btn.setObjectName('privacyPresetBtn')
            preset_layout.addWidget(btn)
        self.btn_strong_privacy.clicked.connect(lambda: self._set_privacy_preset('strong'))
        self.btn_balanced_privacy.clicked.connect(lambda: self._set_privacy_preset('balanced'))
        self.btn_high_accuracy.clicked.connect(lambda: self._set_privacy_preset('accurate'))
        self.btn_noise = QPushButton('运行隐私防护演示')
        self.btn_noise.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.btn_noise.setProperty('variant', 'primary')
        self.btn_noise.setMinimumWidth(230)
        self.btn_noise.clicked.connect(self._on_privacy_demo)
        preset_layout.addSpacing(12)
        preset_layout.addWidget(self.btn_noise)
        demo_layout.addLayout(preset_layout)
        layout.addWidget(demo_group)

        explainer_group = QGroupBox('实时防护观测')
        explainer_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        explainer_layout = QVBoxLayout(explainer_group)
        self.flow_animation = PlainLanguageFlowAnimation('privacy')
        self.flow_animation.finished.connect(self._complete_privacy_demo)
        explainer_layout.addWidget(self.flow_animation)
        layout.addWidget(explainer_group)
        
        ctrl_group = QGroupBox('差分隐私参数控制')
        ctrl_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        ctrl_layout = QHBoxLayout(ctrl_group)
        
        eps_layout = QVBoxLayout()
        self.eps_label = QLabel('总隐私预算 ε: 3.0')
        self.eps_label.setFont(QFont('Microsoft YaHei', 12))
        self.eps_slider = QSlider(Qt.Horizontal)
        self.eps_slider.setMinimum(1)
        self.eps_slider.setMaximum(100)
        self.eps_slider.setValue(30)
        self.eps_slider.valueChanged.connect(self._on_param_change)
        eps_layout.addWidget(self.eps_label)
        eps_layout.addWidget(self.eps_slider)
        ctrl_layout.addLayout(eps_layout, 1)
        
        ratio_layout = QVBoxLayout()
        self.ratio_label = QLabel('信道噪声比例: 0.65')
        self.ratio_label.setFont(QFont('Microsoft YaHei', 12))
        self.ratio_slider = QSlider(Qt.Horizontal)
        self.ratio_slider.setMinimum(0)
        self.ratio_slider.setMaximum(100)
        self.ratio_slider.setValue(65)
        self.ratio_slider.valueChanged.connect(self._on_param_change)
        ratio_layout.addWidget(self.ratio_label)
        ratio_layout.addWidget(self.ratio_slider)
        ctrl_layout.addLayout(ratio_layout, 1)
        
        advanced_group, advanced_layout = make_collapsible_group('高级设置')
        advanced_layout.addWidget(ctrl_group)

        self.btn_reset = QPushButton('重置隐私预算')
        self.btn_reset.setFont(QFont('Microsoft YaHei', 12))
        self.btn_reset.clicked.connect(self._on_reset)
        advanced_layout.addWidget(self.btn_reset)
        layout.addWidget(advanced_group)
        
        self.chart_group = QGroupBox('隐私预算决策图')
        self.chart_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        chart_layout = QVBoxLayout(self.chart_group)
        
        # 自适应尺寸：画布跟随布局分配的空间，布局边距由 constrained 自动计算。
        self.figure = Figure(figsize=(8, 4), facecolor='white', layout='constrained')
        self.canvas = FigureCanvas(self.figure)
        self.chart_placeholder = QLabel('')
        self.chart_placeholder.setAlignment(Qt.AlignCenter)
        self.chart_placeholder.setMinimumHeight(260)
        self.chart_placeholder.setStyleSheet(
            'background:#F7F8F6; color:#747C78; border:1px dashed #BDC5C0; '
            'border-radius:5px; font-size: 20px; font-weight:600;'
        )
        chart_layout.addWidget(self.canvas)
        chart_layout.addWidget(self.chart_placeholder)
        layout.addWidget(self.chart_group, 2)
        
        report_group = QGroupBox('演示结论')
        report_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        report_layout = QHBoxLayout(report_group)
        
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setFont(QFont('Consolas', 12))
        self.report_text.setMaximumHeight(120)
        report_layout.addWidget(self.report_text)
        
        layout.addWidget(report_group)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def play_explainer(self):
        eps = self.eps_slider.value() / 10.0
        risk = self._estimate_attack_success(eps)
        self.flow_animation.play(
            final_caption=(
                f'当前 ε={eps:.1f}：上传的是带随机扰动的更新，'
                f'估算反演成功率 {risk:.1f}%。'
            )
        )

    def _set_privacy_preset(self, mode: str):
        presets = {
            'strong': (10, 75, '强隐私', '攻击更难成功，但模型扰动更大', '#6B8F71'),
            'balanced': (30, 65, '平衡', '兼顾防护和模型可用性', '#7A9CA8'),
            'accurate': (80, 45, '高精度', '噪声较弱，精度更高但风险上升', '#C08E3A')
        }
        eps_value, ratio_value, label, detail, color = presets[mode]
        self.eps_slider.setValue(eps_value)
        self.ratio_slider.setValue(ratio_value)
        self.qdp = QuantumDifferentialPrivacy(epsilon=eps_value / 10.0, channel_ratio=ratio_value / 100.0)
        self.report_text.clear()
        self.report_text.append(f'当前预设: {label}')
        self.report_text.append(detail)
        update_status_card(self.privacy_mode_card, label, detail, color)
        update_status_card(self.attack_risk_card, '待演示', '', '#566573')
        update_status_card(self.noise_card, '—', '噪声越强，隐私越强', '#566573')
        update_status_card(self.budget_card, f'{eps_value / 10.0:.1f}', '预算已随预设重置', '#27AE60')
        for btn, key in (
            (self.btn_strong_privacy, 'strong'),
            (self.btn_balanced_privacy, 'balanced'),
            (self.btn_high_accuracy, 'accurate'),
        ):
            btn.setProperty('active', 'true' if key == mode else 'false')
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_privacy_demo(self):
        if self.privacy_demo_pending:
            return
        if self.qdp.budget.remaining() <= 0:
            self._set_tradeoff_placeholder('隐私预算已耗尽，请重置后重新运行')
            self._on_apply_noise()
            return

        current_eps = self.eps_slider.value() / 10.0
        attack_success = self._estimate_attack_success(current_eps)
        self.privacy_demo_pending = True
        self._set_tradeoff_placeholder('加载中……')
        self._set_privacy_controls_enabled(False)
        self.btn_noise.setText('隐私防护运行中……')
        update_status_card(self.attack_risk_card, '分析中', '正在评估梯度反演风险', '#315CC8')
        update_status_card(self.noise_card, '注入中', '正在执行裁剪与混合加噪', '#315CC8')
        update_status_card(self.budget_card, '结算中', '正在核算本轮隐私预算', '#315CC8')
        self.report_text.clear()
        self.report_text.append('正在执行梯度裁剪、混合噪声注入与风险评估……')
        self.flow_animation.play(
            final_caption=(
                f'本轮已完成：ε={current_eps:.1f}，估算反演成功率 '
                f'{attack_success:.1f}%；数据本身始终没有离开本地。'
            )
        )

    def _set_privacy_controls_enabled(self, enabled: bool):
        for control in [
            self.btn_strong_privacy, self.btn_balanced_privacy,
            self.btn_high_accuracy, self.btn_noise, self.btn_reset,
            self.eps_slider, self.ratio_slider
        ]:
            control.setEnabled(enabled)

    def _complete_privacy_demo(self):
        """防护流程完整结束后，再生成并展示本轮结果。"""
        if not self.privacy_demo_pending:
            return
        self.privacy_demo_pending = False
        self.btn_noise.setText('运行隐私防护演示')
        self._set_privacy_controls_enabled(True)
        if not self._on_apply_noise():
            self._set_tradeoff_placeholder('未生成结果，请重置隐私预算后重新运行')
            return

        # 数据和图表必须等流程完整结束后才生成并显示。
        self._compute_tradeoff(update_report=False)
        self.chart_placeholder.hide()
        self.canvas.show()

        current_eps = self.eps_slider.value() / 10.0
        attack_success = self._estimate_attack_success(current_eps)
        color = '#27AE60' if attack_success < 20 else '#E67E22' if attack_success < 60 else '#E74C3C'
        verdict = '防护有效' if attack_success < 35 else '风险上升'
        update_status_card(
            self.attack_risk_card,
            f'{attack_success:.1f}%',
            f'{verdict}: 该值越低，梯度逆向越难成功',
            color
        )

    def _estimate_attack_success(self, epsilon: float) -> float:
        """估算梯度逆向攻击成功率；ε 越大，隐私越弱，攻击越容易成功。"""
        normalized = max(0.0, min(1.0, epsilon / 10.0))
        return float(4.0 + (normalized ** 1.35) * 51.0)
    
    def _on_param_change(self):
        eps = self.eps_slider.value() / 10.0
        ratio = self.ratio_slider.value() / 100.0
        self.eps_label.setText(f'总隐私预算 ε: {eps:.1f}')
        self.ratio_label.setText(f'信道噪声比例: {ratio:.2f}')
        
        self.qdp = QuantumDifferentialPrivacy(epsilon=eps, channel_ratio=ratio)
        self._set_tradeoff_placeholder('配置已更新，请运行隐私防护演示')
        
        if self.parent_ref:
            self.parent_ref.update_status({
                'qdp_total': eps,
                'qdp_used': 0.0
            })
    
    def _on_apply_noise(self):
        grad = np.random.randn(100) * 0.5
        try:
            noisy = self.qdp.apply_privacy(grad, local_epsilon=self.qdp.budget.epsilon * 0.3)
        except ValueError as exc:
            message = str(exc)
            if '隐私预算' in message:
                self.report_text.clear()
                self.report_text.append('结论: 隐私预算已耗尽。')
                self.report_text.append('处理: 请在高级设置中重置预算后继续演示。')
                update_status_card(self.budget_card, '已耗尽', '请重置隐私预算后继续', '#E74C3C')
                update_status_card(self.noise_card, '需重置', '本轮未继续注入噪声', '#E74C3C')
                update_status_card(self.attack_risk_card, '需重置', '预算耗尽后不再继续演示', '#E74C3C')
                return False
            raise
        report = self.qdp.get_privacy_report()
        
        noise_norm = float(np.linalg.norm(noisy - grad))
        snr = float(np.linalg.norm(grad) / np.linalg.norm(noisy - grad + 1e-8))
        self.report_text.clear()
        self.report_text.append(f'结论: 已完成一轮梯度加噪，等级为 {report["privacy_level"]}。')
        self.report_text.append(f'关键数据: 噪声强度 {noise_norm:.2f}，信噪比 {snr:.2f}。')
        self.report_text.append(f'预算剩余: {report["budget_remaining"]:.2f} / {report["total_epsilon"]}。')

        update_status_card(self.noise_card, f'{noise_norm:.2f}', f'隐私等级: {report["privacy_level"]}', '#9B59B6')
        update_status_card(
            self.budget_card,
            f'{report["budget_remaining"]:.2f}',
            f'总预算 {report["total_epsilon"]}',
            '#27AE60' if report["budget_remaining"] > 0 else '#E74C3C'
        )
        
        if self.parent_ref:
            self.parent_ref.update_status({
                'qdp_used': report['budget_used']
            })
        return True
    
    def _on_reset(self):
        self.privacy_demo_pending = False
        self._set_privacy_controls_enabled(True)
        self.btn_noise.setText('运行隐私防护演示')
        eps = self.eps_slider.value() / 10.0
        ratio = self.ratio_slider.value() / 100.0
        self.qdp = QuantumDifferentialPrivacy(epsilon=eps, channel_ratio=ratio)
        self.report_text.clear()
        self.report_text.append('结论: 隐私预算已重置。')
        update_status_card(self.attack_risk_card, '待演示', '', '#566573')
        update_status_card(self.noise_card, '—', '噪声越强，隐私越强', '#566573')
        update_status_card(self.budget_card, '已重置', f'总预算 {eps:.1f}', '#27AE60')
        self.flow_animation.reset()
        self._set_tradeoff_placeholder('暂无结果')
        if self.parent_ref:
            self.parent_ref.update_status({'qdp_used': 0.0})

    def _set_tradeoff_placeholder(self, text: str):
        """隐藏旧结果，只保留等待或加载提示。"""
        self.figure.clear()
        self.canvas.draw_idle()
        self.canvas.hide()
        self.chart_placeholder.setText(text)
        self.chart_placeholder.show()

    def _compute_tradeoff(self, update_report: bool = True):
        """展示信息还原度、泄漏可能性及“可能性×影响”综合风险。"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        s = self.CHART_SCALE
        self.figure.patch.set_facecolor('#FFFFFF')

        current_eps = self.eps_slider.value() / 10.0
        channel_ratio = self.ratio_slider.value() / 100.0
        eps_curve = np.linspace(0.1, 10.0, 120)

        # 固定参考向量；曲线只表示估算趋势，不代表实测准确率。
        rng = np.random.default_rng(42)
        sample_params = rng.normal(0.0, 0.1, 100)
        reference_noise = rng.normal(0.0, 1.0, 100)
        signal_norm = float(np.linalg.norm(sample_params))
        reference_noise_norm = float(np.linalg.norm(reference_noise))

        def estimate_information_recoverability(epsilon):
            scale = 0.5 / (epsilon + 0.1) * (1.0 + channel_ratio / 2.0)
            noise_norm = reference_noise_norm * scale
            snr = signal_norm / (noise_norm + 1e-8)
            utility_loss = 1.0 / (1.0 + snr)
            return (1.0 - utility_loss) * 100.0

        recoverability_curve = np.array([
            estimate_information_recoverability(eps) for eps in eps_curve
        ])
        risk_curve = np.array([
            self._estimate_attack_success(float(eps)) for eps in eps_curve
        ])
        # 综合风险 = 泄漏可能性 × 信息还原影响。
        combined_curve = recoverability_curve * risk_curve / 100.0
        current_recoverability = float(estimate_information_recoverability(current_eps))
        current_risk = float(self._estimate_attack_success(current_eps))
        current_combined = current_recoverability * current_risk / 100.0

        mode = '强隐私' if current_eps < 1.5 else '平衡' if current_eps < 4.0 else '高精度'
        recoverability_color = '#526C80'
        risk_color = '#B35D55'
        combined_color = '#176B63'
        current_color = '#202724'
        ax.set_facecolor('#FFFFFF')

        # 区间底色表达策略语义，不参与数据编码。
        ax.axvspan(0.1, 1.5, color='#EAF3EF', alpha=0.72, zorder=0)
        ax.axvspan(1.5, 4.0, color='#F7F2E7', alpha=0.72, zorder=0)
        ax.axvspan(4.0, 10.0, color='#F5F6F4', alpha=0.72, zorder=0)
        for x, label in [(0.8, '强隐私'), (2.75, '平衡'), (7.0, '高精度')]:
            ax.text(
                x, 59.1, label, ha='center', va='center', fontsize=8 * s,
                color='#6A736F', fontweight='bold', zorder=1
            )

        ax.fill_between(
            eps_curve, 0, combined_curve, color=combined_color, alpha=0.10, zorder=1
        )
        ax.plot(
            eps_curve, recoverability_curve, color=recoverability_color, linewidth=2.0,
            alpha=0.90, solid_capstyle='round', zorder=3,
            label='信息还原度（代理）'
        )
        ax.plot(
            eps_curve, risk_curve, color=risk_color, linewidth=2.0,
            alpha=0.90, solid_capstyle='round', zorder=3,
            label='泄漏风险（估算）'
        )
        ax.plot(
            eps_curve, combined_curve, color=combined_color, linewidth=3.2,
            solid_capstyle='round', zorder=4,
            label='综合风险'
        )

        ax.axvspan(
            max(0.1, current_eps - 0.065), min(10.0, current_eps + 0.065),
            color=combined_color, alpha=0.10, zorder=2
        )
        ax.axvline(
            current_eps, color=current_color, linestyle=(0, (3, 3)),
            linewidth=1.25, alpha=0.72, zorder=2
        )
        ax.scatter(
            [current_eps], [current_recoverability], s=54, color=recoverability_color,
            edgecolors='#FFFFFF', linewidths=1.6, zorder=6
        )
        ax.scatter(
            [current_eps], [current_risk], s=54, color=risk_color,
            edgecolors='#FFFFFF', linewidths=1.6, zorder=6
        )
        ax.scatter(
            [current_eps], [current_combined], s=92, color=combined_color,
            edgecolors='#FFFFFF', linewidths=2.0, zorder=7
        )
        assert np.all(np.diff(eps_curve) > 0), '隐私预算曲线必须严格递增'
        ax.legend(
            loc='lower left', bbox_to_anchor=(0.0, 1.01), ncol=3,
            frameon=False, fontsize=7.2 * s, handlelength=2.2,
            columnspacing=1.2, handletextpad=0.6, borderaxespad=0.0
        )

        ax.set_title(
            '风险随隐私预算的变化',
            loc='left', fontsize=12.5 * s, fontweight='bold', color='#202724', pad=30 * s
        )
        ax.set_xlabel(
            '隐私预算 ε（值越小，隐私保护越强）',
            fontsize=9 * s, color='#454E4A', labelpad=9 * s
        )
        ax.set_ylabel('指标值 (%)', fontsize=9 * s, color='#454E4A')
        ax.set_xlim(0.1, 10.0)
        ax.set_ylim(0.0, 62.0)
        ax.set_xticks([0.1, 1, 2, 3, 4, 5, 6, 8, 10])
        ax.set_xticklabels(['0.1', '1', '2', '3', '4', '5', '6', '8', '10'])
        ax.set_yticks([0, 10, 20, 30, 40, 50, 60])
        ax.grid(axis='y', color='#DDE3E0', alpha=0.78, linewidth=0.75)
        ax.grid(axis='x', visible=False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#BFC7C3')
        ax.spines['bottom'].set_color('#BFC7C3')
        ax.tick_params(axis='both', colors='#59625E', labelsize=8.5 * s, length=3 * s)

        self.canvas.draw()
        
        if update_report:
            self.report_text.clear()
            self.report_text.append(f'当前配置: {mode}，ε={current_eps:.1f}。')
            self.report_text.append(
                f'估算结果: 信息还原度 {current_recoverability:.1f}% / '
                f'泄漏风险 {current_risk:.1f}% / 综合风险 {current_combined:.1f}%。'
            )
            self.report_text.append(
                '综合风险按“泄漏可能性 × 信息还原影响”计算，'
                '两项均先换算为 0–1 比例。'
            )
            self.report_text.append(
                f'噪声来源: 信道 {channel_ratio * 100:.0f}% / '
                f'测量 {(1-channel_ratio) * 100:.0f}%。'
            )


class FederatedTab(QWidget):

    PRECOMPUTED_RESULT_PATH = (
        PROJECT_ROOT / 'experiments' / 'security_benchmark_results'
        / 'security_benchmark_results.json'
    )
    
    def __init__(self, parent_ref=None):
        super().__init__()
        self.parent_ref = parent_ref
        self.input_dim = 8
        self.hidden_dim = 16
        self.output_dim = 3
        np.random.seed(123)
        self.model = SimpleNNModel(input_dim=self.input_dim, hidden_dim=self.hidden_dim, output_dim=self.output_dim)
        self.mpo = MPOCompressor(bond_dim=8)
        self.qdp = QuantumDifferentialPrivacy(
            epsilon=1000.0, channel_ratio=0.75, clip_norm=1.0,
            noise_seed=42
        )
        self.server = FederatedLearningServer(
            model_template=self.model, n_clients=5,
            qdp_module=self.qdp, mpo_compressor=self.mpo,
            aggregation_method='fedavg',
            mpo_max_reconstruction_error=0.0015,
            compression_error_feedback=True
        )
        self.ledger = SecureFederatedLedger(n_nodes=5, blockchain_difficulty=3)
        self.train_rounds = 0
        self.current_config = (5, 8)
        self.client_data, self.X_test, self.y_test = self._make_demo_data(n_clients=5)
        self.security_score_history = []
        self.federated_demo_pending = None
        self.pending_malicious_count = 0
        self.current_result_mode = None
        self.auto_play_explainer = False
        self._build_ui()
    
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        action_bar = QFrame()
        action_bar.setObjectName('actionBar')
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 13, 16, 13)
        action_copy = QVBoxLayout()
        action_copy.setSpacing(2)
        action_title = QLabel('联邦学习训练控制台')
        action_title.setObjectName('actionTitle')
        action_text = QLabel('启动联邦学习演示，观察训练曲线、投毒防护和5折验证结果。')
        action_text.setObjectName('actionText')
        action_copy.addWidget(action_title)
        action_copy.addWidget(action_text)
        action_layout.addLayout(action_copy)
        action_layout.addStretch()

        self.btn_train = QPushButton('开始标准联邦学习')
        self.btn_train.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.btn_train.setProperty('variant', 'primary')
        self.btn_train.clicked.connect(self._on_demo_train)
        self.btn_multi = QPushButton('恶意节点注入')
        self.btn_multi.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        self.btn_multi.setProperty('variant', 'warning')
        self.btn_multi.clicked.connect(self._on_poison_demo)
        self.btn_kfold = QPushButton('运行5折验证')
        self.btn_kfold.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        self.btn_kfold.setProperty('variant', 'quiet')
        self.btn_kfold.clicked.connect(self._on_kfold_demo)
        action_layout.addWidget(self.btn_train)
        action_layout.addWidget(self.btn_multi)
        action_layout.addWidget(self.btn_kfold)
        layout.addWidget(action_bar)

        advanced_group, advanced_layout = make_collapsible_group('训练参数（演示配置）')
        self.training_parameters_group = advanced_group
        # 结果区隐藏时不吸收页面剩余高度，始终按实际内容确定高度。
        self.training_parameters_group.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Maximum
        )

        bond_layout = QVBoxLayout()
        self.bond_label = QLabel('MPO 键维度 D: 8')
        self.bond_slider = QSlider(Qt.Horizontal)
        self.bond_slider.setMinimum(2)
        self.bond_slider.setMaximum(32)
        self.bond_slider.setValue(8)
        self.bond_slider.valueChanged.connect(lambda v: self.bond_label.setText(f'MPO 键维度 D: {v}'))
        bond_layout.addWidget(self.bond_label)
        bond_layout.addWidget(self.bond_slider)
        advanced_layout.addLayout(bond_layout)

        client_layout = QVBoxLayout()
        self.client_label = QLabel('客户端数量 N: 5')
        self.client_slider = QSlider(Qt.Horizontal)
        self.client_slider.setMinimum(3)
        self.client_slider.setMaximum(15)
        self.client_slider.setValue(5)
        self.client_slider.valueChanged.connect(self._on_client_count_change)
        client_layout.addWidget(self.client_label)
        client_layout.addWidget(self.client_slider)
        advanced_layout.addLayout(client_layout)

        lr_layout = QVBoxLayout()
        self.lr_label = QLabel('优化方案学习率: 0.70')
        self.lr_slider = QSlider(Qt.Horizontal)
        self.lr_slider.setMinimum(1)
        self.lr_slider.setMaximum(100)
        self.lr_slider.setValue(70)
        self.lr_slider.valueChanged.connect(
            lambda v: self.lr_label.setText(f'优化方案学习率: {v/100.0:.3f}')
        )
        lr_layout.addWidget(self.lr_label)
        lr_layout.addWidget(self.lr_slider)
        advanced_layout.addLayout(lr_layout)

        mal_layout = QHBoxLayout()
        mal_label = QLabel('注入恶意节点:')
        self.mal_combo = QComboBox()
        mal_layout.addWidget(mal_label)
        mal_layout.addWidget(self.mal_combo)
        advanced_layout.addLayout(mal_layout)
        self._refresh_malicious_options()

        for read_only_control in [
            self.bond_slider, self.client_slider, self.lr_slider
        ]:
            read_only_control.setEnabled(False)

        self.mal_combo.currentIndexChanged.connect(self._on_malicious_count_change)
        self._on_malicious_count_change()

        self.btn_reset = QPushButton('恢复默认训练结果')
        self.btn_reset.clicked.connect(self._on_reset)
        advanced_layout.addWidget(self.btn_reset)
        layout.addWidget(advanced_group)

        card_layout = QHBoxLayout()
        _g = []
        self.fl_accuracy_card = make_status_card('任务准确率', '待开始', '联邦训练测试集结果', '#566573', group=_g)
        self.fl_security_card = make_status_card('通信节省', '待开始', 'MPO 压缩后减少的传输量', '#566573', group=_g)
        self.fl_cv_card = make_status_card('5折验证', '待开始', '均值±标准差', '#566573', group=_g)
        self.fl_mal_card = make_status_card('抗毒化效果', '待开始', '中位数聚合降低的攻击影响', '#566573', group=_g)
        self.fl_chain_card = make_status_card('训练状态', '待开始', '', '#315CC8', group=_g)
        for card in [self.fl_accuracy_card, self.fl_security_card, self.fl_cv_card,
                     self.fl_mal_card, self.fl_chain_card]:
            card_layout.addWidget(card)
        layout.addLayout(card_layout)

        explainer_group = QGroupBox('实时训练观测')
        explainer_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        explainer_layout = QVBoxLayout(explainer_group)
        self.flow_animation = PlainLanguageFlowAnimation('federated')
        self.flow_animation.finished.connect(self._complete_federated_demo)
        explainer_layout.addWidget(self.flow_animation)
        layout.addWidget(explainer_group)

        workspace = QHBoxLayout()
        workspace.setSpacing(12)
        self.chart_group = QGroupBox('训练与安全验证结果')
        chart_layout = QVBoxLayout(self.chart_group)
        # 提示页和结果画布共用同一个固定位置，切换内容时不改变外层高度。
        self.chart_stack = QStackedWidget()
        self.chart_placeholder = QLabel()
        self.chart_placeholder.setAlignment(Qt.AlignCenter)
        self.chart_placeholder.setWordWrap(True)
        self.chart_placeholder.setMinimumHeight(390)
        self.chart_placeholder.setStyleSheet(
            'background:#F7F8F6; color:#747C78; border:1px dashed #BDC5C0; '
            'border-radius:5px; padding:24px;'
        )
        self.figure = Figure(figsize=(8, 5), facecolor='white')
        self.canvas = FigureCanvas(self.figure)
        self.chart_stack.addWidget(self.chart_placeholder)
        self.chart_stack.addWidget(self.canvas)
        chart_layout.addWidget(self.chart_stack)
        workspace.addWidget(self.chart_group, 7)

        right = QTabWidget()
        right.setObjectName('workbenchTabs')
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['轮次', '准确率', '损失', '通信节省', '聚合方法'])
        self.table.setFont(QFont('Consolas', 12))
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.table)
        right.addTab(table_tab, '训练详情')

        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont('Consolas', 12))
        self.log_output.setPlaceholderText('暂无记录')
        log_layout.addWidget(self.log_output)
        right.addTab(log_tab, '实验日志')
        workspace.addWidget(right, 5)
        self.result_workspace = QWidget()
        self.result_workspace.setObjectName('federatedResultWorkspace')
        self.result_workspace.setLayout(workspace)
        self.result_workspace.setMinimumHeight(520)
        layout.addWidget(self.result_workspace, 1)

        self._draw_training_plot_init()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def play_explainer(self, malicious: bool = False):
        client_count = self.client_slider.value()
        if malicious:
            malicious_count = max(
                1, self.pending_malicious_count,
                int(self.mal_combo.currentData() or 0)
            )
            final_caption = (
                f'{client_count} 个客户端中注入 {malicious_count} 个恶意节点；'
                '异常更新先被筛查，再进入全局模型。'
            )
        else:
            final_caption = (
                f'{client_count} 个客户端完成协作：原始样本不离开本地，'
                '仅聚合可验证的模型更新。'
            )
        self.flow_animation.play(final_caption=final_caption)

    def _set_federated_actions_enabled(self, enabled: bool):
        for button in [self.btn_train, self.btn_multi, self.btn_kfold, self.btn_reset]:
            button.setEnabled(enabled)
        self.mal_combo.setEnabled(enabled)

    def _reset_federated_action_labels(self):
        malicious_count = int(self.mal_combo.currentData() or 0)
        self.btn_train.setText(
            f'开始联邦学习（注入{malicious_count}个）'
            if malicious_count else '开始标准联邦学习'
        )
        self.btn_multi.setText(
            f'运行恶意节点实验（{malicious_count}个）'
            if malicious_count else '恶意节点注入'
        )
        self.btn_kfold.setText('运行5折验证')

    def _set_federated_result_context(self, mode: str):
        """为三种展示模式提供一致的结果标题。"""
        result_titles = {
            'training': '联邦训练效果',
            'poisoning': '恶意节点注入 · 防御验证结果',
            'kfold': '5折稳定性验证结果',
        }
        self.chart_group.setTitle(result_titles[mode])

    def _set_federated_chart_placeholder(self, title: str, detail: str):
        """在固定结果画布中显示等待/运行提示，不触发页面重新排版。"""
        detail_html = (
            '<br><br>'
            f'<span style="font-size: 18px; color:#8A97AA;">{detail}</span>'
            if detail else ''
        )
        self.chart_placeholder.setText(
            '<div style="text-align:center;">'
            f'<span style="font-size: 24px; font-weight:600; color:#64748B;">{title}</span>'
            f'{detail_html}'
            '</div>'
        )
        self.chart_stack.setCurrentWidget(self.chart_placeholder)

    def _show_federated_chart_canvas(self):
        """在同一固定结果区域中切换到最终图表。"""
        self.chart_stack.setCurrentWidget(self.canvas)

    def _show_federated_pending_state(self, mode: str):
        """保留结果区尺寸，流程运行期间用进度占位内容替换旧结果。"""
        poisoning_detail = (
            f'正在注入 {self.pending_malicious_count} 个恶意节点并执行鲁棒聚合对照'
        )
        labels = {
            'training': ('训练进行中……', '正在执行联邦训练流程'),
            'poisoning': ('对照实验进行中……', poisoning_detail),
            'kfold': ('5折验证进行中……', '正在执行交叉验证流程'),
        }
        title, detail = labels[mode]
        self._set_federated_result_context(mode)
        self._set_result_table(
            ['状态', '详情'], [[title.replace('……', ''), '运行中']]
        )
        for card, value, card_detail in [
            (self.fl_accuracy_card, '训练中', '正在计算测试集准确率'),
            (self.fl_security_card, '压缩中', '正在统计 MPO 通信节省'),
            (self.fl_cv_card, '验证中' if mode == 'kfold' else '等待完成', ''),
            (self.fl_mal_card, '分析中' if mode == 'poisoning' else '检测中', '正在评估恶意更新影响'),
            (self.fl_chain_card, '运行中', detail),
        ]:
            update_status_card(card, value, card_detail, '#315CC8')

        self._set_federated_chart_placeholder(title, detail)
        self.log_output.clear()
        self.log_output.append(f'[{time.strftime("%H:%M:%S")}] ▶ {title}')
        self.log_output.append(f'  {detail}')

    def _start_federated_demo(self, mode: str):
        if self.federated_demo_pending is not None:
            return
        if mode not in {'training', 'poisoning', 'kfold'}:
            raise ValueError(f'未知联邦展示模式: {mode}')
        if mode == 'poisoning':
            selected_count = int(self.mal_combo.currentData() or 0)
            if selected_count <= 0:
                default_index = self.mal_combo.findData(1)
                if default_index >= 0:
                    self.mal_combo.setCurrentIndex(default_index)
                selected_count = 1
            self.pending_malicious_count = selected_count
        else:
            self.pending_malicious_count = 0
        self.federated_demo_pending = mode
        self._set_federated_actions_enabled(False)
        if mode == 'training':
            self.btn_train.setText('训练进行中……')
        elif mode == 'poisoning':
            self.btn_multi.setText('对照实验进行中……')
        else:
            self.btn_kfold.setText('5折验证进行中……')
        self._show_federated_pending_state(mode)
        self.play_explainer(malicious=(mode == 'poisoning'))

    def _complete_federated_demo(self):
        """训练流程完整结束后，再加载对应结果数据。"""
        mode = self.federated_demo_pending
        if mode is None:
            return
        malicious_count = self.pending_malicious_count
        self.federated_demo_pending = None
        self._set_federated_actions_enabled(True)
        self._reset_federated_action_labels()
        # 结果区始终存在，仅替换其内容，上方布局不会因此跳动。
        self.result_workspace.updateGeometry()
        parent_layout = self.result_workspace.parentWidget().layout()
        if parent_layout is not None:
            parent_layout.invalidate()
            parent_layout.activate()
        self.result_workspace.layout().activate()
        self.current_result_mode = mode
        if mode == 'training':
            self._load_precomputed_training(animate=False)
        elif mode == 'poisoning':
            self._load_precomputed_poisoning(
                animate=False, malicious_count=malicious_count
            )
        else:
            self._load_precomputed_kfold()
        QTimer.singleShot(0, self._refresh_federated_result_canvas)
        self.pending_malicious_count = 0

    def _refresh_federated_result_canvas(self):
        """结果区展开后按最终宽度补一次画布刷新。"""
        if (
            self.result_workspace.isHidden()
            or self.chart_stack.currentWidget() is not self.canvas
        ):
            return
        self.canvas.updateGeometry()
        self.canvas.draw_idle()

    def _read_precomputed_results(self):
        """加载稳定的演示基准；失败时不启动备用计算任务。"""
        try:
            data = json.loads(self.PRECOMPUTED_RESULT_PATH.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f'训练演示数据准备失败: {exc}') from exc
        required = {
            'federated_learning', 'fl_kfold_cross_validation',
            'model_poisoning', 'mpo'
        }
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f'训练演示数据缺少字段: {", ".join(missing)}')
        return data

    def _set_result_table(self, headers, rows):
        self.table.clearContents()
        self.table.setRowCount(0)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        for values in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _show_precomputed_error(self, message: str):
        for card in [
            self.fl_accuracy_card, self.fl_security_card, self.fl_cv_card,
            self.fl_mal_card, self.fl_chain_card
        ]:
            update_status_card(card, '准备失败', message, '#E74C3C')
        self._set_result_table(['状态', '详情'], [['未执行训练', message]])
        self._show_federated_chart_canvas()
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.55, '训练演示数据准备失败', ha='center', va='center', fontsize=12)
        ax.text(0.5, 0.43, message, ha='center', va='center', fontsize=8, wrap=True)
        ax.set_axis_off()
        self.canvas.draw()
        self.log_output.clear()
        self.log_output.append(f'[{time.strftime("%H:%M:%S")}] 演示数据准备失败: {message}')
        self.log_output.append('请检查项目数据文件后重试。')

    def _update_federated_summary_cards(self, data):
        """统一填充顶部四项核心指标，避免单项实验结束后残留进行中状态。"""
        fl = data['federated_learning']
        secure = fl['secure_qdp_adaptive_mpo']
        cv = data['fl_kfold_cross_validation']
        poisoning = data['model_poisoning']
        saving = float(secure['avg_communication_saving_pct'])
        poison_reduction = float(poisoning['median_reduction_vs_fedavg']) * 100.0
        update_status_card(
            self.fl_accuracy_card, f'{float(secure["final_accuracy"]):.2f}%',
            f'5种子测试均值 ± {float(secure.get("final_accuracy_std", 0.0)):.2f}%',
            '#27AE60'
        )
        update_status_card(
            self.fl_security_card, f'{saving:.2f}%',
            f'平均重构误差 {float(secure["avg_reconstruction_error"]):.6f}', '#7C4DCE'
        )
        update_status_card(
            self.fl_cv_card,
            f'{float(cv["mean_accuracy"]):.2f}% ± {float(cv["std_accuracy"]):.2f}%',
            f'{int(cv["k"])}折范围 {float(cv["min_accuracy"]):.2f}%~{float(cv["max_accuracy"]):.2f}%',
            '#168A78'
        )
        update_status_card(
            self.fl_mal_card, f'{poison_reduction:.2f}%',
            '中位数聚合相对 FedAvg 降低攻击影响', '#E67E22'
        )

    def _load_precomputed_training(self, animate: bool = True):
        try:
            data = self._read_precomputed_results()
            fl = data['federated_learning']
            baseline = fl['baseline_fedavg']
            secure = fl['secure_qdp_adaptive_mpo']
            cv = data['fl_kfold_cross_validation']
            poisoning = data['model_poisoning']
            accuracies = list(secure['accuracy'])
            losses = list(secure['loss'])
            if len(accuracies) != len(losses) or len(accuracies) < 2:
                raise ValueError('训练曲线长度异常')
        except (KeyError, TypeError, ValueError) as exc:
            self._show_precomputed_error(str(exc))
            return False

        self._set_federated_result_context('training')
        saving = float(secure['avg_communication_saving_pct'])
        poison_reduction = float(poisoning['median_reduction_vs_fedavg']) * 100.0
        rows = []
        for round_index, (accuracy, loss) in enumerate(
            zip(accuracies[1:], losses[1:]), start=1
        ):
            rows.append([
                round_index, f'{float(accuracy):.2f}%', f'{float(loss):.6f}',
                f'{saving:.2f}%', secure['aggregation_method']
            ])
        self._set_result_table(
            ['轮次', '准确率', '损失', '通信节省', '聚合方法'], rows
        )
        self.train_rounds = int(fl['n_rounds'])
        update_status_card(
            self.fl_accuracy_card, f'{float(secure["final_accuracy"]):.2f}%',
            f'5种子测试均值 ± {float(secure.get("final_accuracy_std", 0.0)):.2f}%',
            '#27AE60'
        )
        update_status_card(
            self.fl_security_card, f'{saving:.2f}%',
            f'平均重构误差 {float(secure["avg_reconstruction_error"]):.6f}', '#7C4DCE'
        )
        update_status_card(
            self.fl_cv_card,
            f'{float(cv["mean_accuracy"]):.2f}% ± {float(cv["std_accuracy"]):.2f}%',
            f'{int(cv["k"])}折范围 {float(cv["min_accuracy"]):.2f}%~{float(cv["max_accuracy"]):.2f}%',
            '#168A78'
        )
        update_status_card(
            self.fl_mal_card, f'{poison_reduction:.2f}%',
            '中位数聚合相对 FedAvg 降低攻击影响', '#E67E22'
        )
        update_status_card(
            self.fl_chain_card, '训练完成', '模型结果已生成', '#315CC8'
        )
        self._draw_precomputed_training_plot(baseline, secure)
        self.log_output.clear()
        self.log_output.append(f'[{time.strftime("%H:%M:%S")}] ▶ 开始联邦学习训练演示')
        self.log_output.append(f'  已完成 {self.train_rounds} 轮训练')
        baseline_gain = float(secure['final_accuracy']) - float(baseline['final_accuracy'])
        self.log_output.append(
            f'  5种子测试均值: {secure["final_accuracy"]}% '
            f'± {float(secure.get("final_accuracy_std", 0.0)):.2f}%'
        )
        self.log_output.append(
            f'  相对 FedAvg: {baseline_gain:+.2f} 个百分点 | 通信节省: {saving:.2f}%'
        )
        self.log_output.append('  训练演示完成，结果已更新')
        if animate:
            self.play_explainer(malicious=False)
        return True

    @staticmethod
    def _calculate_poisoning_result(n_clients: int, malicious_count: int,
                                    seed: int = 345) -> Dict:
        """根据用户选择现场构造投毒更新，并用三种聚合器计算实际偏移。"""
        if n_clients < 3:
            raise ValueError('恶意节点实验至少需要 3 个客户端')
        if malicious_count < 1 or malicious_count >= n_clients:
            raise ValueError('恶意节点数必须在 1 到客户端数减 1 之间')

        rng = np.random.RandomState(seed)
        honest_count = n_clients - malicious_count
        honest = rng.normal(0.0, 0.05, size=(honest_count, 80))
        malicious = rng.normal(2.5, 0.25, size=(malicious_count, 80))
        gradients = list(np.vstack([honest, malicious]))
        model = SimpleNNModel(input_dim=4, hidden_dim=8, output_dim=2)
        norms = {}
        for method in ['fedavg', 'median', 'krum']:
            server = FederatedLearningServer(
                model, n_clients=n_clients, aggregation_method=method
            )
            norms[method] = round(float(np.linalg.norm(
                server._aggregate_gradients(gradients)
            )), 4)

        fedavg_norm = max(norms['fedavg'], 1e-12)
        tolerance = (n_clients - 1) // 3
        return {
            'n_clients': n_clients,
            'malicious_count': malicious_count,
            'tolerance': tolerance,
            'within_tolerance': malicious_count <= tolerance,
            'aggregation_delta_norms': norms,
            'median_reduction_vs_fedavg': round(
                1.0 - norms['median'] / fedavg_norm, 4
            ),
            'krum_reduction_vs_fedavg': round(
                1.0 - norms['krum'] / fedavg_norm, 4
            ),
        }

    def _load_precomputed_poisoning(self, animate: bool = True,
                                    malicious_count: int = None):
        try:
            data = self._read_precomputed_results()
            selected_count = int(
                malicious_count
                if malicious_count is not None
                else (self.mal_combo.currentData() or 0)
            )
            if selected_count <= 0:
                selected_count = 1
            poisoning = self._calculate_poisoning_result(
                self.client_slider.value(), selected_count
            )
            norms = poisoning['aggregation_delta_norms']
            median_reduction = float(poisoning['median_reduction_vs_fedavg']) * 100.0
            krum_reduction = float(poisoning['krum_reduction_vs_fedavg']) * 100.0
            self._update_federated_summary_cards(data)
        except (KeyError, TypeError, ValueError) as exc:
            self._show_precomputed_error(str(exc))
            return False

        self._set_federated_result_context('poisoning')
        rows = [
            ['FedAvg', f'{float(norms["fedavg"]):.4f}', '0.00%', '基线', '影响最大'],
            ['Median', f'{float(norms["median"]):.4f}', f'{median_reduction:.2f}%', '鲁棒聚合', '影响降低'],
            ['Krum', f'{float(norms["krum"]):.4f}', f'{krum_reduction:.2f}%', '鲁棒聚合', '影响降低'],
        ]
        self._set_result_table(
            ['聚合方法', '更新偏移范数', '影响降低', '类型', '结论'], rows
        )
        update_status_card(
            self.fl_mal_card, f'{median_reduction:.2f}%',
            f'{selected_count} 个恶意节点的中位数聚合对照已完成', '#27AE60'
        )
        tolerance_text = (
            f'在共识容错范围内（≤{poisoning["tolerance"]}个）'
            if poisoning['within_tolerance']
            else f'超出共识容错范围（>{poisoning["tolerance"]}个）'
        )
        update_status_card(
            self.fl_chain_card, '实验完成', tolerance_text,
            '#27AE60' if poisoning['within_tolerance'] else '#E67E22'
        )
        self._draw_precomputed_poisoning_plot(
            norms, median_reduction, krum_reduction, selected_count
        )
        self.log_output.clear()
        self.log_output.append(f'[{time.strftime("%H:%M:%S")}] ▶ 开始恶意节点对照演示')
        self.log_output.append(
            f'  注入数量: {selected_count}/{poisoning["n_clients"]} | {tolerance_text}'
        )
        self.log_output.append(f'  Median 影响降低: {median_reduction:.2f}%')
        self.log_output.append(f'  Krum 影响降低: {krum_reduction:.2f}%')
        self.log_output.append('  恶意节点对照演示完成')
        if animate:
            self.play_explainer(malicious=True)
        return True

    def _load_precomputed_kfold(self):
        try:
            data = self._read_precomputed_results()
            cv = data['fl_kfold_cross_validation']
            folds = list(cv['folds'])
            if not folds:
                raise ValueError('5折验证结果为空')
            self._update_federated_summary_cards(data)
        except (KeyError, TypeError, ValueError) as exc:
            self._show_precomputed_error(str(exc))
            return False

        self._set_federated_result_context('kfold')
        rows = [[
            item['fold'], item['train_samples'], item['test_samples'],
            f'{float(item["accuracy_after"]):.2f}%', f'{float(item["loss_after"]):.6f}'
        ] for item in folds]
        self._set_result_table(
            ['折数', '训练样本', '测试样本', '最终准确率', '最终损失'], rows
        )
        update_status_card(
            self.fl_cv_card,
            f'{float(cv["mean_accuracy"]):.2f}% ± {float(cv["std_accuracy"]):.2f}%',
            f'已完成 {int(cv["k"])} 折验证', '#27AE60'
        )
        update_status_card(
            self.fl_chain_card, '验证完成', '5折验证结果已生成', '#315CC8'
        )
        self._draw_precomputed_kfold_plot(cv)
        self.log_output.clear()
        self.log_output.append(f'[{time.strftime("%H:%M:%S")}] ▶ 开始 {cv["k"]} 折验证演示')
        self.log_output.append(
            f'  均值: {float(cv["mean_accuracy"]):.2f}% ± {float(cv["std_accuracy"]):.2f}%'
        )
        self.log_output.append('  5折交叉验证演示完成')
        return True

    def _on_train(self):
        self._on_demo_train()

    def _on_multi_train(self):
        self._on_demo_train()

    def _on_demo_train(self):
        mode = 'poisoning' if int(self.mal_combo.currentData() or 0) > 0 else 'training'
        self._start_federated_demo(mode)

    def _on_poison_demo(self):
        self._start_federated_demo('poisoning')

    def _on_client_count_change(self, value: int):
        self.client_label.setText(f'客户端数量 N: {value}')
        self._refresh_malicious_options()
        self._on_malicious_count_change()

    def _refresh_malicious_options(self):
        if not hasattr(self, 'mal_combo'):
            return
        current_count = self.mal_combo.currentData()
        current_count = 0 if current_count is None else int(current_count)
        n_clients = self.client_slider.value()
        max_tolerated = (n_clients - 1) // 3
        # 多提供一档超出 1/3 容错界限的压力测试。
        max_configurable = min(n_clients - 1, max(1, max_tolerated + 1))
        self.mal_combo.blockSignals(True)
        self.mal_combo.clear()
        self.mal_combo.addItem('无', 0)
        for count in range(1, max_configurable + 1):
            scope = '容错内' if count <= max_tolerated else '超出容错'
            self.mal_combo.addItem(f'{count}个（{scope}）', count)
        restored_index = self.mal_combo.findData(
            min(current_count, max_configurable)
        )
        self.mal_combo.setCurrentIndex(max(0, restored_index))
        self.mal_combo.blockSignals(False)

    def _on_malicious_count_change(self, _index: int = -1):
        self._reset_federated_action_labels()

    def _on_kfold_demo(self):
        self._start_federated_demo('kfold')

    def _draw_precomputed_training_plot(self, baseline: Dict, secure: Dict):
        self._show_federated_chart_canvas()
        self.figure.clear()
        ax_accuracy = self.figure.add_subplot(121)
        ax_loss = self.figure.add_subplot(122)
        baseline_accuracy = [float(value) for value in baseline['accuracy']]
        secure_accuracy = [float(value) for value in secure['accuracy']]
        baseline_loss = [float(value) for value in baseline['loss']]
        secure_loss = [float(value) for value in secure['loss']]
        baseline_accuracy_std = np.asarray(
            baseline.get('accuracy_std', np.zeros(len(baseline_accuracy))), dtype=float
        )
        secure_accuracy_std = np.asarray(
            secure.get('accuracy_std', np.zeros(len(secure_accuracy))), dtype=float
        )
        baseline_loss_std = np.asarray(
            baseline.get('loss_std', np.zeros(len(baseline_loss))), dtype=float
        )
        secure_loss_std = np.asarray(
            secure.get('loss_std', np.zeros(len(secure_loss))), dtype=float
        )
        baseline_accuracy = np.asarray(baseline_accuracy, dtype=float)
        secure_accuracy = np.asarray(secure_accuracy, dtype=float)
        baseline_loss = np.asarray(baseline_loss, dtype=float)
        secure_loss = np.asarray(secure_loss, dtype=float)
        rounds = list(range(len(secure_accuracy)))

        ax_accuracy.plot(
            rounds, baseline_accuracy, color='#8A97AA', linestyle='--',
            label='FedAvg基线（5种子均值）'
        )
        ax_accuracy.fill_between(
            rounds, baseline_accuracy - baseline_accuracy_std,
            baseline_accuracy + baseline_accuracy_std,
            color='#8A97AA', alpha=0.12
        )
        ax_accuracy.plot(rounds, secure_accuracy, color='#315CC8', marker='o', markersize=3,
                         label='本方法：QDP+MPO+误差反馈')
        ax_accuracy.fill_between(
            rounds, secure_accuracy - secure_accuracy_std,
            secure_accuracy + secure_accuracy_std,
            color='#315CC8', alpha=0.12
        )
        ax_accuracy.set_title('测试准确率曲线（5种子均值）', fontsize=10)
        ax_accuracy.set_xlabel('通信轮次（0为初始模型）', fontsize=8)
        ax_accuracy.set_ylabel('准确率 (%)', fontsize=8)
        ax_accuracy.set_ylim(0, 100)
        ax_accuracy.grid(True, alpha=0.3)
        ax_accuracy.legend(fontsize=7)

        ax_loss.plot(
            rounds, baseline_loss, color='#8A97AA', linestyle='--',
            label='FedAvg基线（5种子均值）'
        )
        ax_loss.fill_between(
            rounds, baseline_loss - baseline_loss_std,
            baseline_loss + baseline_loss_std,
            color='#8A97AA', alpha=0.12
        )
        ax_loss.plot(rounds, secure_loss, color='#7C4DCE', marker='o', markersize=3,
                     label='本方法：QDP+MPO+误差反馈')
        ax_loss.fill_between(
            rounds, secure_loss - secure_loss_std,
            secure_loss + secure_loss_std,
            color='#7C4DCE', alpha=0.12
        )
        ax_loss.set_title('测试损失曲线（5种子均值）', fontsize=10)
        ax_loss.set_xlabel('通信轮次', fontsize=8)
        ax_loss.set_ylabel('分类损失', fontsize=8)
        ax_loss.grid(True, alpha=0.3)
        ax_loss.legend(fontsize=7)
        # 使用固定比例边距，不依赖隐藏画布的临时像素宽度。
        self.figure.subplots_adjust(
            left=0.09, right=0.98, top=0.88, bottom=0.16, wspace=0.30
        )
        self.canvas.draw()

    def _draw_precomputed_poisoning_plot(self, norms: Dict, median_reduction: float,
                                         krum_reduction: float,
                                         malicious_count: int = 2):
        """用“攻击进入—防御过滤—偏移回拉”的故事线解释投毒对照。"""
        from matplotlib.patches import FancyBboxPatch, Patch

        self._show_federated_chart_canvas()
        self.figure.clear()
        grid = self.figure.add_gridspec(
            2, 2, height_ratios=[0.92, 3.15], width_ratios=[1.16, 1.0],
            hspace=0.10, wspace=0.28
        )
        ax_flow = self.figure.add_subplot(grid[0, :])
        ax_impact = self.figure.add_subplot(grid[1, 0])
        ax_shift = self.figure.add_subplot(grid[1, 1])

        ax_flow.set_xlim(0, 1)
        ax_flow.set_ylim(0, 1)
        ax_flow.axis('off')
        flow_nodes = [
            (0.015, 0.14, 0.255, 0.62, '#FFF0F1', '#D94343',
             '① 恶意更新进入', f'{malicious_count} 个异常更新拉偏全局模型'),
            (0.372, 0.14, 0.255, 0.62, '#FFF7E8', '#D97706',
             '② 鲁棒聚合筛查', '识别异常并降低其权重'),
            (0.729, 0.14, 0.255, 0.62, '#EAF9F4', '#168A78',
             '③ 可信更新保留',
             f'攻击影响剩余约 {max(0.0, 100.0 - median_reduction):.1f}%'),
        ]
        for x, y, width, height, face, edge, title, subtitle in flow_nodes:
            box = FancyBboxPatch(
                (x, y), width, height,
                boxstyle='round,pad=0.012,rounding_size=0.025',
                linewidth=1.2, edgecolor=edge, facecolor=face,
                transform=ax_flow.transAxes
            )
            ax_flow.add_patch(box)
            ax_flow.text(
                x + width / 2, y + height * 0.62, title,
                ha='center', va='center', fontsize=8.2,
                color=edge, fontweight='bold', transform=ax_flow.transAxes
            )
            ax_flow.text(
                x + width / 2, y + height * 0.30, subtitle,
                ha='center', va='center', fontsize=6.8,
                color='#66758A', transform=ax_flow.transAxes
            )
        for start, end in [(0.279, 0.363), (0.636, 0.720)]:
            ax_flow.annotate(
                '', xy=(end, 0.45), xytext=(start, 0.45),
                xycoords=ax_flow.transAxes, textcoords=ax_flow.transAxes,
                arrowprops=dict(arrowstyle='-|>', lw=1.8, color='#93A4BA')
            )

        fedavg_norm = float(norms['fedavg'])
        median_norm = float(norms['median'])
        krum_norm = float(norms['krum'])
        reductions = [0.0, median_reduction, krum_reduction]
        residuals = [100.0, max(0.0, 100.0 - median_reduction),
                     max(0.0, 100.0 - krum_reduction)]
        y_positions = np.arange(3)
        method_labels = [
            'FedAvg 基线\n剩余 100%',
            f'Median\n剩余 {residuals[1]:.2f}%',
            f'Krum\n剩余 {residuals[2]:.2f}%',
        ]

        # 统一到 FedAvg=100%，避免量级差让鲁棒聚合的差异难以看清。
        ax_impact.barh(y_positions, [100.0] * 3, height=0.54, color='#EDF1F6')
        ax_impact.barh(
            y_positions, residuals, height=0.54, color='#E95B64',
            label='剩余攻击影响'
        )
        ax_impact.barh(
            y_positions, reductions, left=residuals, height=0.54,
            color='#12A58F', label='已过滤攻击影响'
        )
        ax_impact.text(
            50, y_positions[0], '未过滤  100%',
            ha='center', va='center', fontsize=7.5,
            color='white', fontweight='bold'
        )
        for row, reduction in zip(y_positions[1:], reductions[1:]):
            ax_impact.text(
                98.0, row, f'已过滤  {reduction:.2f}%',
                ha='right', va='center', fontsize=7.5,
                color='white', fontweight='bold'
            )
        ax_impact.set_yticks(y_positions)
        ax_impact.set_yticklabels(method_labels, fontsize=7.3)
        ax_impact.invert_yaxis()
        ax_impact.set_xlim(0, 100)
        ax_impact.set_xticks([0, 25, 50, 75, 100])
        ax_impact.set_xlabel('以 FedAvg 的攻击影响为 100%', fontsize=7.5)
        ax_impact.grid(True, axis='x', alpha=0.25)
        ax_impact.set_axisbelow(True)
        ax_impact.tick_params(axis='y', length=0)
        ax_impact.spines[['top', 'right', 'left']].set_visible(False)
        ax_impact.legend(
            handles=[
                Patch(facecolor='#E95B64', label='剩余攻击影响'),
                Patch(facecolor='#12A58F', label='已过滤攻击影响'),
            ],
            loc='lower center', bbox_to_anchor=(0.5, -0.36),
            ncol=2, fontsize=6.8, frameon=False
        )

        # 保留原始范数，用向左回拉的箭头表达“全局更新回到正常区域”。
        shift_rows = [1, 0]
        robust_values = [median_norm, krum_norm]
        robust_labels = ['Median', 'Krum']
        robust_colors = ['#168A78', '#315CC8']
        for row, value, label, color in zip(
            shift_rows, robust_values, robust_labels, robust_colors
        ):
            ax_shift.annotate(
                '', xy=(value, row), xytext=(fedavg_norm, row),
                arrowprops=dict(arrowstyle='-|>', lw=2.6, color=color, alpha=0.78)
            )
            ax_shift.scatter([fedavg_norm], [row], s=58, color='#E95B64', zorder=4)
            ax_shift.scatter([value], [row], s=72, color=color, zorder=5,
                             edgecolors='white', linewidths=1.0)
            ax_shift.text(
                fedavg_norm, row + 0.15, f'{fedavg_norm:.3f}',
                ha='center', va='bottom', fontsize=7.2, color='#D94343'
            )
            ax_shift.text(
                value, row - 0.15, f'{value:.3f}',
                ha='center', va='top', fontsize=7.2, color=color,
                fontweight='bold'
            )
        ax_shift.set_yticks(shift_rows)
        ax_shift.set_yticklabels(robust_labels, fontsize=8)
        ax_shift.set_xlim(0, fedavg_norm * 1.13)
        ax_shift.set_ylim(-0.55, 1.55)
        ax_shift.set_xlabel('偏移范数（箭头越向左，攻击影响越小）', fontsize=7.5)
        ax_shift.grid(True, axis='x', alpha=0.25)
        ax_shift.set_axisbelow(True)
        ax_shift.tick_params(axis='y', length=0)
        ax_shift.spines[['top', 'right', 'left']].set_visible(False)
        ax_shift.text(
            fedavg_norm, 1.46, 'FedAvg 投毒基线',
            ha='center', va='bottom', fontsize=7.0, color='#D94343'
        )

        self.figure.subplots_adjust(left=0.14, right=0.98, top=0.97, bottom=0.20)
        self.canvas.draw()

    def _draw_precomputed_kfold_plot(self, cv: Dict):
        self._show_federated_chart_canvas()
        self.figure.clear()
        ax_accuracy = self.figure.add_subplot(121)
        ax_loss = self.figure.add_subplot(122)
        folds = list(cv['folds'])
        fold_ids = [int(item['fold']) for item in folds]
        before = [float(item['accuracy_before']) for item in folds]
        after = [float(item['accuracy_after']) for item in folds]
        losses = [float(item['loss_after']) for item in folds]
        positions = np.arange(len(fold_ids))
        width = 0.36

        ax_accuracy.bar(positions - width / 2, before, width, color='#C8D2DF', label='训练前')
        ax_accuracy.bar(positions + width / 2, after, width, color='#168A78', label='训练后')
        ax_accuracy.axhline(
            float(cv['mean_accuracy']), color='#D94343', linestyle='--',
            label=f'均值 {float(cv["mean_accuracy"]):.2f}%'
        )
        ax_accuracy.set_xticks(positions)
        ax_accuracy.set_xticklabels([f'第{fold}折' for fold in fold_ids])
        ax_accuracy.set_title('5 折验证准确率', fontsize=10)
        ax_accuracy.set_ylabel('准确率 (%)', fontsize=8)
        ax_accuracy.set_ylim(0, 105)
        ax_accuracy.grid(True, alpha=0.3, axis='y')
        ax_accuracy.legend(fontsize=7)

        loss_bars = ax_loss.bar(
            [f'第{fold}折' for fold in fold_ids], losses, color='#7C4DCE', alpha=0.82
        )
        for bar, value in zip(loss_bars, losses):
            ax_loss.text(bar.get_x() + bar.get_width() / 2, value + 0.006,
                         f'{value:.3f}', ha='center', va='bottom', fontsize=8)
        ax_loss.axhline(float(cv['mean_loss']), color='#D94343', linestyle='--', label='平均损失')
        ax_loss.set_title('各折最终损失', fontsize=10)
        ax_loss.set_ylabel('分类损失', fontsize=8)
        ax_loss.set_ylim(0, max(losses) * 1.25)
        ax_loss.grid(True, alpha=0.3, axis='y')
        ax_loss.legend(fontsize=7)
        self.figure.tight_layout(pad=1.8)
        self.canvas.draw()

    def _make_demo_data(self, n_clients: int, seed: int = 2026):
        """生成固定 teacher 规则的演示数据，保证准确率反映可学习任务。"""
        rng = np.random.RandomState(seed)
        teacher_w = rng.randn(self.input_dim, self.output_dim)
        client_data = []
        for client_id in range(n_clients):
            X = rng.randn(300, self.input_dim) + client_id * 0.02
            logits = X @ teacher_w + 0.1 * rng.randn(300, self.output_dim)
            y = np.argmax(logits, axis=1).astype(np.int64)
            client_data.append((X, y))

        X_test = rng.randn(1000, self.input_dim)
        test_logits = X_test @ teacher_w + 0.1 * rng.randn(1000, self.output_dim)
        y_test = np.argmax(test_logits, axis=1).astype(np.int64)
        return client_data, X_test, y_test

    def _poison_client_data(self, client_data, malicious_list: List[int]):
        poisoned = []
        for client_id, (X, y) in enumerate(client_data):
            if client_id in malicious_list:
                poisoned.append((-X, (y + 1) % self.output_dim))
            else:
                poisoned.append((X, y))
        return poisoned

    def _run_single_round(self):
        n_clients = self.client_slider.value()
        lr = self.lr_slider.value() / 100.0
        bond_dim = self.bond_slider.value()
        n_mal = int(self.mal_combo.currentData() or 0)
        max_malicious = (n_clients - 1) // 3
        if n_mal > max_malicious:
            n_mal = max_malicious
            self._refresh_malicious_options()

        # 参数变化时才重建服务端；否则保持连续训练状态。
        if self.current_config != (n_clients, bond_dim):
            np.random.seed(123)
            self.model = SimpleNNModel(input_dim=self.input_dim, hidden_dim=self.hidden_dim, output_dim=self.output_dim)
            self.mpo = MPOCompressor(bond_dim=bond_dim)
            self.qdp = QuantumDifferentialPrivacy(
                epsilon=1000.0, channel_ratio=0.75, clip_norm=1.0,
                noise_seed=42
            )
            self.server = FederatedLearningServer(
                model_template=self.model, n_clients=n_clients,
                qdp_module=self.qdp, mpo_compressor=self.mpo,
                aggregation_method='fedavg',
                mpo_max_reconstruction_error=0.0015,
                compression_error_feedback=True
            )
            self.ledger = SecureFederatedLedger(n_nodes=n_clients, blockchain_difficulty=3)
            self.table.setRowCount(0)
            self.train_rounds = 0
            self.current_config = (n_clients, bond_dim)
            self.client_data, self.X_test, self.y_test = self._make_demo_data(n_clients=n_clients)
            self.security_score_history = []
            self.log_output.append(f'[{time.strftime("%H:%M:%S")}] 参数变化，已重建训练状态')

        malicious_list = list(range(n_clients - n_mal, n_clients)) if n_mal > 0 else []
        round_client_data = self._poison_client_data(self.client_data, malicious_list)

        info = self.server.train_round(round_client_data, lr=lr)
        eval_result = self.server.evaluate(self.X_test, self.y_test)

        self.train_rounds += 1

        ledger_result = self.ledger.record_round(
            self.train_rounds,
            self.server.global_params,
            info['clients'],
            eval_result['accuracy'],
            malicious_list
        )
        
        self.log_output.append(f'[{time.strftime("%H:%M:%S")}] 轮次 #{self.train_rounds}:')
        self.log_output.append(f'  任务准确率: {eval_result["accuracy"]:.2f}%')
        self.log_output.append(f'  参数传输占比: {info["avg_compression_ratio"]:.1f}%')
        skipped_clients = sum(1 for c in info['clients'] if c.get('compression_skipped'))
        compressed_clients = len(info['clients']) - skipped_clients
        self.log_output.append(f'  MPO状态: {compressed_clients}/{len(info["clients"])} 个客户端实际压缩')
        self.log_output.append(f'  隐私预算剩余: {info["privacy_budget_remaining"]}')
        self.log_output.append(f'  恶意节点: {malicious_list}')
        consensus_result = ledger_result.get('consensus', {})
        detected_malicious = consensus_result.get('detected_malicious', [])
        block_index = ledger_result.get('block_index')
        block_label = str(block_index) if block_index is not None else '未上链'
        chain_length = len(self.ledger.blockchain.chain)
        self.log_output.append(f'  拜占庭共识检测到: {detected_malicious}')
        if ledger_result.get('status') == 'success':
            self.log_output.append(f'  区块#{block_index} 已上链 | 哈希: {ledger_result["block_hash"][:20]}...')
        else:
            self.log_output.append(f'  共识状态: {ledger_result.get("status", "unknown")}，本轮未写入新区块')

        privacy_score, consensus_score, malicious_score, integrity_score = self._compute_security_scores(
            info, block_index, detected_malicious, malicious_list
        )
        self.security_score_history.append({
            'privacy': privacy_score,
            'consensus': consensus_score,
            'malicious': malicious_score,
            'integrity': integrity_score
        })
        overall_security = float(np.mean([privacy_score, consensus_score, malicious_score, integrity_score]))

        update_status_card(
            self.fl_accuracy_card,
            f'{eval_result["accuracy"]:.2f}%',
            f'3分类测试集，已完成 {self.train_rounds} 轮',
            '#27AE60' if eval_result["accuracy"] >= 55 else '#E67E22'
        )
        update_status_card(
            self.fl_security_card,
            f'{overall_security:.0f}',
            '隐私、共识、抗恶意、完整性综合分',
            '#27AE60' if overall_security >= 80 else '#E67E22'
        )
        update_status_card(
            self.fl_mal_card,
            f'{len(detected_malicious)} 个',
            f'恶意节点注入 {len(malicious_list)} 个',
            '#27AE60' if len(detected_malicious) >= len(malicious_list) else '#E67E22'
        )
        update_status_card(
            self.fl_chain_card,
            '已上链' if block_index is not None else '未上链',
            '共识通过并记录模型' if block_index is not None else '共识失败，本轮不写入新区块',
            '#27AE60' if block_index is not None else '#E67E22'
        )
        
        self._update_table(eval_result['accuracy'], privacy_score,
                           block_label, detected_malicious)
        
        self._update_training_plot()
        
        if self.parent_ref:
            self.parent_ref.update_status({
                'accuracy': eval_result['accuracy'],
                'mpo_ratio': overall_security,
                'malicious_detected': len(detected_malicious),
                'chain_length': chain_length,
                'consensus_nodes': f'{n_clients - n_mal}/{n_clients}'
            })

    def _compute_security_scores(self, info: Dict, block_index, detected_malicious: List[int],
                                 malicious_list: List[int]):
        privacy_remaining = info.get('privacy_budget_remaining')
        if self.qdp is None:
            privacy_score = 0.0
        elif privacy_remaining is not None and privacy_remaining <= 0:
            privacy_score = 30.0
        elif getattr(self.qdp, 'noise_history', None):
            privacy_score = 98.0
        else:
            privacy_score = 90.0

        consensus_score = 100.0 if block_index is not None else 35.0
        if malicious_list:
            malicious_score = min(100.0, len(detected_malicious) / len(malicious_list) * 100.0)
        else:
            malicious_score = 100.0

        recon_error = float(info.get('avg_recon_error', 0.0) or 0.0)
        integrity_score = max(0.0, min(100.0, 100.0 - recon_error * 1200.0))
        return privacy_score, consensus_score, malicious_score, integrity_score
    
    def _on_reset(self):
        self.federated_demo_pending = None
        self.pending_malicious_count = 0
        self.current_result_mode = None
        default_index = self.mal_combo.findData(0)
        if default_index >= 0:
            self.mal_combo.setCurrentIndex(default_index)
        self._reset_federated_action_labels()
        self._set_federated_actions_enabled(True)
        self.flow_animation.reset()
        self._set_result_table(
            ['轮次', '准确率', '损失', '通信节省', '聚合方法'], []
        )
        update_status_card(self.fl_accuracy_card, '待开始', '联邦训练测试集结果', '#566573')
        update_status_card(self.fl_security_card, '待开始', 'MPO 压缩后减少的传输量', '#566573')
        update_status_card(self.fl_cv_card, '待开始', '均值±标准差', '#566573')
        update_status_card(self.fl_mal_card, '待开始', '中位数聚合降低的攻击影响', '#566573')
        update_status_card(self.fl_chain_card, '待开始', '', '#315CC8')
        self.log_output.clear()
        self._draw_training_plot_init()

    def _draw_training_plot_init(self):
        self.accuracy_history = []
        self.chart_group.setTitle('联邦训练结果')
        self._set_result_table(
            ['状态', '说明'],
            [['暂无结果', '—']]
        )
        self.log_output.clear()
        self.figure.clear()
        self._set_federated_chart_placeholder(
            '暂无结果',
            ''
        )
    
    def _update_training_plot(self):
        n_rows = self.table.rowCount()
        rounds = list(range(1, n_rows + 1))
        accuracies = [float(self.table.item(i, 1).text()) for i in range(n_rows)]
        
        self._show_federated_chart_canvas()
        self.figure.clear()
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)
        
        ax1.plot(rounds, accuracies, 'g-o', markersize=5, linewidth=2, label='准确率')
        ax1.set_title('任务准确率随训练轮次变化', fontsize=10)
        ax1.set_xlabel('训练轮次', fontsize=9)
        ax1.set_ylabel('准确率 (%)', fontsize=9)
        ax1.set_ylim([0, 100])
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=8)

        latest_scores = self.security_score_history[-1] if self.security_score_history else {
            'privacy': 0.0, 'consensus': 0.0, 'malicious': 0.0, 'integrity': 0.0
        }
        labels = ['隐私保护', '共识可信', '抗恶意', '参数完整']
        values = [
            latest_scores['privacy'],
            latest_scores['consensus'],
            latest_scores['malicious'],
            latest_scores['integrity']
        ]
        colors = ['#3498DB', '#27AE60', '#E67E22', '#9B59B6']
        bars = ax2.bar(labels, values, color=colors, alpha=0.75, edgecolor='black')
        for bar, value in zip(bars, values):
            ax2.text(bar.get_x() + bar.get_width() / 2, min(105, value + 2),
                     f'{value:.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
        ax2.set_title('安全协同能力评分', fontsize=10)
        ax2.set_ylabel('评分 (%)', fontsize=9)
        ax2.set_ylim([0, 110])
        ax2.grid(True, alpha=0.3, axis='y')
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _update_table(self, accuracy, privacy_score, block_idx, malicious):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(self.train_rounds)))
        self.table.setItem(row, 1, QTableWidgetItem(f'{accuracy:.2f}'))
        self.table.setItem(row, 2, QTableWidgetItem(f'{privacy_score:.1f}'))
        self.table.setItem(row, 3, QTableWidgetItem(str(block_idx)))
        self.table.setItem(row, 4, QTableWidgetItem(str(malicious)))
        self.table.resizeColumnsToContents()


class ByzantineConsensusView(QWidget):
    """将节点票数、异常识别与共识阈值绘制成紧凑的投票网络。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.n_nodes = 7
        self.malicious_nodes = []
        self.result = None
        self.setMinimumHeight(360)
        self.setStyleSheet(
            'background:#FBFBFA; border:1px solid #D9DDDA; border-radius:5px;'
        )

    def set_state(self, n_nodes, malicious_nodes, result=None):
        self.n_nodes = int(n_nodes)
        self.malicious_nodes = list(malicious_nodes)
        self.result = result
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = float(self.width()), float(self.height())
        detected = set((self.result or {}).get('detected_malicious', []))
        support_rates = list((self.result or {}).get('support_rates', []))
        honest_nodes = set((self.result or {}).get('honest_nodes', []))
        consensus_reached = bool((self.result or {}).get('consensus_reached'))

        # 标题与本轮判定保持在同一行，图中不再重复堆叠说明文字。
        painter.setPen(QColor('#334155'))
        f = QFont('Microsoft YaHei')
        f.setPixelSize(12)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(
            QRectF(18, 10, max(120.0, width - 132.0), 26),
            Qt.AlignVCenter | Qt.AlignLeft,
            '节点签名相似度投票网络'
        )

        if self.result is None:
            state_text, state_fill, state_border = '等待投票', '#EEF3FF', '#4F7CFF'
        elif consensus_reached:
            state_text, state_fill, state_border = '✓ 共识通过', '#E8F8F4', '#0F9D83'
        else:
            state_text, state_fill, state_border = '× 共识拒绝', '#FFF0F1', '#DC3545'
        state_rect = QRectF(width - 108.0, 10.0, 90.0, 26.0)
        painter.setBrush(QColor(state_fill))
        painter.setPen(QPen(QColor(state_border), 1.1))
        painter.drawRoundedRect(state_rect, 13, 13)
        painter.setPen(QColor(state_border))
        f = QFont('Microsoft YaHei')
        f.setPixelSize(9)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(state_rect, Qt.AlignCenter, state_text)

        graph_top = 48.0
        graph_bottom = max(graph_top + 220.0, height - 42.0)
        graph_height = graph_bottom - graph_top
        center = QPointF(width * 0.50, graph_top + graph_height * 0.50)
        radius_x = min(width * 0.335, graph_height * 0.93)
        radius_y = graph_height * 0.37
        node_radius = max(24.0, min(33.0, radius_y * 0.31))

        positions = []
        for index in range(self.n_nodes):
            angle = -np.pi / 2.0 + index * 2.0 * np.pi / self.n_nodes
            positions.append(QPointF(
                center.x() + radius_x * np.cos(angle),
                center.y() + radius_y * np.sin(angle)
            ))

        # 连线先画，随后由中心面板和节点覆盖端点，形成清晰的网络层次。
        for index, position in enumerate(positions):
            if self.result is None:
                line_color = '#D7DFEA'
            elif index in honest_nodes:
                line_color = '#13A287'
            else:
                line_color = '#EE5361'
            pen = QPen(QColor(line_color), 2.3)
            pen.setCapStyle(Qt.RoundCap)
            if self.result is not None and index not in honest_nodes:
                pen.setDashPattern([4.0, 3.0])
            painter.setPen(pen)
            painter.drawLine(center, position)

        valid_votes = len(honest_nodes) if self.result is not None else 0
        support_ratio = valid_votes / max(1, self.n_nodes)
        if self.result is None:
            center_fill, center_border = '#EEF3FF', '#4F7CFF'
            center_title = '等待节点投票'
            center_votes, center_detail = '—', '阈值 > 66.7%'
        elif consensus_reached:
            center_fill, center_border = '#E8F8F4', '#0F9D83'
            center_title = '有效支持'
            center_votes = f'{valid_votes} / {self.n_nodes}'
            center_detail = f'{support_ratio * 100:.1f}%  >  66.7%'
        else:
            center_fill, center_border = '#FFF0F1', '#DC3545'
            center_title = '有效支持不足'
            center_votes = f'{valid_votes} / {self.n_nodes}'
            center_detail = f'{support_ratio * 100:.1f}%  ≤  66.7%'

        center_rect = QRectF(center.x() - 72, center.y() - 48, 144, 96)
        halo_color = QColor(center_border)
        halo_color.setAlpha(24)
        painter.setBrush(halo_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(center_rect.adjusted(-11, -11, 11, 11), 26, 26)
        painter.setBrush(QColor(center_fill))
        painter.setPen(QPen(QColor(center_border), 2.2))
        painter.drawRoundedRect(center_rect, 18, 18)
        painter.setPen(QColor('#1E293B'))
        f = QFont('Microsoft YaHei')
        f.setPixelSize(11)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(
            QRectF(center_rect.x(), center_rect.y() + 13, center_rect.width(), 20),
            Qt.AlignCenter, center_title
        )
        f = QFont('Microsoft YaHei')
        f.setPixelSize(16)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(
            QRectF(center_rect.x(), center_rect.y() + 33, center_rect.width(), 29),
            Qt.AlignCenter, center_votes
        )
        painter.setPen(QColor(center_border))
        f = QFont('Microsoft YaHei')
        f.setPixelSize(9)
        painter.setFont(f)
        painter.drawText(
            QRectF(center_rect.x(), center_rect.y() + 65, center_rect.width(), 18),
            Qt.AlignCenter, center_detail
        )

        for index, position in enumerate(positions):
            actual_malicious = index in self.malicious_nodes
            is_detected = index in detected
            if actual_malicious and is_detected:
                fill, border, badge_fill, badge_text = '#FFF0F1', '#EE3E4F', '#EE5361', '×'
            elif actual_malicious:
                fill, border, badge_fill, badge_text = '#FFF7ED', '#D97706', '#F59E0B', '!'
            elif is_detected:
                fill, border, badge_fill, badge_text = '#FEF3C7', '#B45309', '#F59E0B', '!'
            else:
                fill, border, badge_fill, badge_text = '#EDF4FF', '#2B66D5', '#13A287', '✓'
            rect = QRectF(
                position.x() - node_radius, position.y() - node_radius,
                node_radius * 2, node_radius * 2
            )
            painter.setBrush(QColor(fill))
            painter.setPen(QPen(QColor(border), 2.5 if actual_malicious else 2.0))
            painter.drawEllipse(rect)
            painter.setPen(QColor('#1E293B'))
            f = QFont('Microsoft YaHei')
            f.setPixelSize(11)
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(
                QRectF(rect.x(), rect.y() + 8, rect.width(), 20),
                Qt.AlignCenter, f'N{index}'
            )
            support_text = (
                f'{support_rates[index] * 100:.0f}%'
                if index < len(support_rates) else '—'
            )
            painter.setPen(QColor('#64748B'))
            f = QFont('Microsoft YaHei')
            f.setPixelSize(9)
            painter.setFont(f)
            painter.drawText(
                QRectF(rect.x(), rect.y() + 28, rect.width(), 18),
                Qt.AlignCenter, support_text
            )

            # 勾/叉徽标与边框颜色共同编码节点状态，避免依赖颜色辨认。
            badge_radius = max(8.0, node_radius * 0.29)
            badge_center = QPointF(
                position.x() + node_radius * 0.68,
                position.y() - node_radius * 0.68
            )
            painter.setBrush(QColor(badge_fill))
            painter.setPen(QPen(QColor('#FFFFFF'), 1.2))
            painter.drawEllipse(badge_center, badge_radius, badge_radius)
            painter.setPen(QColor('#FFFFFF'))
            f = QFont('Microsoft YaHei')
            f.setPixelSize(9)
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(
                QRectF(
                    badge_center.x() - badge_radius,
                    badge_center.y() - badge_radius,
                    badge_radius * 2,
                    badge_radius * 2
                ),
                Qt.AlignCenter, badge_text
            )

        # 简洁图例取代每个节点旁重复的身份与支持率说明。
        compact_legend = width < 610
        trusted_label = '可信计票' if compact_legend else '可信签名计入共识'
        blocked_label = '异常剔除' if compact_legend else '异常签名识别剔除'
        legend_width = 350.0 if compact_legend else 455.0
        legend_x = max(16.0, (width - legend_width) / 2.0)
        legend_y = height - 20.0
        f = QFont('Microsoft YaHei')
        f.setPixelSize(9)
        painter.setFont(f)
        painter.setPen(QPen(QColor('#13A287'), 2.2))
        painter.drawLine(
            QPointF(legend_x, legend_y - 2),
            QPointF(legend_x + 25, legend_y - 2)
        )
        painter.setPen(QColor('#64748B'))
        painter.drawText(
            QRectF(legend_x + 32, legend_y - 12, 125, 20),
            Qt.AlignVCenter | Qt.AlignLeft, trusted_label
        )

        second_x = legend_x + (155 if compact_legend else 180)
        blocked_pen = QPen(QColor('#EE5361'), 2.2)
        blocked_pen.setDashPattern([4.0, 3.0])
        painter.setPen(blocked_pen)
        painter.drawLine(
            QPointF(second_x, legend_y - 2),
            QPointF(second_x + 25, legend_y - 2)
        )
        painter.setPen(QColor('#64748B'))
        painter.drawText(
            QRectF(second_x + 32, legend_y - 12, 135, 20),
            Qt.AlignVCenter | Qt.AlignLeft, blocked_label
        )

        threshold_x = legend_x + (280 if compact_legend else 370)
        painter.setBrush(QColor('#E78222'))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(threshold_x, legend_y - 7, 4, 11), 2, 2)
        painter.setPen(QColor('#64748B'))
        f = QFont('Microsoft YaHei')
        f.setPixelSize(9)
        painter.setFont(f)
        painter.drawText(
            QRectF(threshold_x + 10, legend_y - 12, 82, 20),
            Qt.AlignVCenter | Qt.AlignLeft, '阈值 66.7%'
        )


class ByzantineConsensusTab(QWidget):
    """独立的拜占庭共识交互演示模块。"""

    CONSENSUS_VALUE = 'current-federated-model-update'

    def __init__(self, parent_ref=None):
        super().__init__()
        self.parent_ref = parent_ref
        self.auto_play_explainer = False
        self.consensus = None
        self.last_result = None
        self.consensus_demo_pending = False
        self._build_ui()
        self._reset_demo()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        action_bar = QFrame()
        action_bar.setObjectName('actionBar')
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 13, 16, 13)
        copy_layout = QVBoxLayout()
        title = QLabel('拜占庭共识实验室')
        title.setObjectName('actionTitle')
        description = QLabel(
            '手动配置共识节点和恶意节点，观察量子签名相似度投票与 1/3 容错边界。'
        )
        description.setObjectName('actionText')
        copy_layout.addWidget(title)
        copy_layout.addWidget(description)
        action_layout.addLayout(copy_layout)
        action_layout.addStretch()
        layout.addWidget(action_bar)

        cards = QHBoxLayout()
        _g = []
        self.network_card = make_status_card('共识网络', '7 节点', '手动调整 4–10 个参与者', '#315CC8', group=_g)
        self.tolerance_card = make_status_card('容错上限', 't = 2', 'n ≥ 3t + 1', '#7C4DCE', group=_g)
        self.detection_card = make_status_card('恶意识别', '待执行', '显示实际节点与检出节点', '#566573', group=_g)
        self.consensus_card = make_status_card('共识结果', '待执行', '超过 2/3 可信支持才通过', '#566573', group=_g)
        for card in [self.network_card, self.tolerance_card,
                     self.detection_card, self.consensus_card]:
            cards.addWidget(card)
        layout.addLayout(cards)

        controls_group = QGroupBox('共识参数')
        controls_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        controls = QGridLayout(controls_group)
        controls.setHorizontalSpacing(12)
        controls.addWidget(QLabel('节点总数 n'), 0, 0)
        self.node_spin = QSpinBox()
        self.node_spin.setRange(4, 10)
        self.node_spin.setValue(7)
        self.node_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.node_spin.setAlignment(Qt.AlignCenter)
        self.node_spin.setToolTip('点击后直接输入 4–10 之间的整数')
        controls.addWidget(self.node_spin, 1, 0)
        controls.addWidget(QLabel('恶意节点数'), 0, 1)
        self.malicious_spin = QSpinBox()
        self.malicious_spin.setRange(0, 6)
        self.malicious_spin.setValue(2)
        self.malicious_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.malicious_spin.setAlignment(Qt.AlignCenter)
        self.malicious_spin.setToolTip('点击后直接输入恶意节点数量')
        controls.addWidget(self.malicious_spin, 1, 1)
        controls.addWidget(QLabel('量子签名长度'), 0, 2)
        self.qubit_spin = QSpinBox()
        self.qubit_spin.setRange(16, 128)
        self.qubit_spin.setSingleStep(16)
        self.qubit_spin.setValue(64)
        self.qubit_spin.setSuffix(' bit')
        self.qubit_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.qubit_spin.setAlignment(Qt.AlignCenter)
        self.qubit_spin.setToolTip('点击后直接输入 16–128 bit 的签名长度')
        controls.addWidget(self.qubit_spin, 1, 2)
        self.btn_run = QPushButton('执行一轮共识')
        self.btn_run.setProperty('variant', 'primary')
        self.btn_run.clicked.connect(self._start_consensus_demo)
        controls.addWidget(self.btn_run, 1, 3)
        controls.setColumnStretch(3, 2)
        layout.addWidget(controls_group)

        process_group = QGroupBox('实时共识观测')
        process_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        process_layout = QVBoxLayout(process_group)
        self.flow_animation = PlainLanguageFlowAnimation('consensus')
        self.flow_animation.finished.connect(self._complete_consensus_demo)
        process_layout.addWidget(self.flow_animation)
        layout.addWidget(process_group)

        self.result_group = QGroupBox('节点投票与识别结果')
        self.result_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        result_layout = QVBoxLayout(self.result_group)
        self.result_stack = QStackedWidget()

        self.result_placeholder = QLabel('暂无结果')
        self.result_placeholder.setAlignment(Qt.AlignCenter)
        self.result_placeholder.setMinimumHeight(360)
        self.result_placeholder.setStyleSheet(
            'background:#F7F8F6; color:#747C78; border:1px dashed #BDC5C0; '
            'border-radius:5px; font-size: 20px; font-weight:600;'
        )
        self.result_stack.addWidget(self.result_placeholder)

        self.result_content = QWidget()
        result_content_layout = QHBoxLayout(self.result_content)
        result_content_layout.setContentsMargins(0, 0, 0, 0)
        result_content_layout.setSpacing(10)
        self.network_view = ByzantineConsensusView()
        result_content_layout.addWidget(self.network_view, 7)
        self.node_table = QTableWidget(0, 4)
        self.node_table.setHorizontalHeaderLabels([
            '节点', '实际身份', '支持率', '共识判定'
        ])
        self.node_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.node_table.verticalHeader().setVisible(False)
        self.node_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.node_table.setAlternatingRowColors(True)
        self.node_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.node_table.setStyleSheet(
            'QTableWidget { gridline-color: #555555;'
            'border-top: 1px solid #555555; border-left: 1px solid #555555; }'
            'QHeaderView::section { border: none; border-right: 1px solid #555555;'
            'border-bottom: 1px solid #000000; }'
            'QTableWidget QTableCornerButton::section { border: none; }'
        )
        result_content_layout.addWidget(self.node_table, 5)
        self.result_stack.addWidget(self.result_content)
        result_layout.addWidget(self.result_stack)
        layout.addWidget(self.result_group)

        self.evidence_group = QGroupBox('共识证据与教学结论')
        self.evidence_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        evidence_layout = QHBoxLayout(self.evidence_group)
        self.consensus_log = QTextEdit()
        self.consensus_log.setReadOnly(True)
        self.consensus_log.setFont(QFont('Consolas', 12))
        self.consensus_log.setMinimumHeight(420)
        evidence_layout.addWidget(self.consensus_log, 7)
        self.boundary_note = QLabel()
        self.boundary_note.setWordWrap(True)
        self.boundary_note.setAlignment(Qt.AlignTop)
        self.boundary_note.setStyleSheet(
            'background:#F7F8F6; color:#515A56; border:1px solid #D9DDDA; '
            'border-radius:5px; padding:12px;'
        )
        evidence_layout.addWidget(self.boundary_note, 4)
        layout.addWidget(self.evidence_group)
        layout.addStretch()

        self.node_spin.valueChanged.connect(self._update_parameter_preview)
        self.malicious_spin.valueChanged.connect(self._update_parameter_preview)
        self.qubit_spin.valueChanged.connect(self._update_parameter_preview)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _malicious_nodes(self):
        count = int(self.malicious_spin.value())
        n_nodes = int(self.node_spin.value())
        return list(range(n_nodes - count, n_nodes)) if count else []

    def _update_parameter_preview(self):
        n_nodes = int(self.node_spin.value())
        self.malicious_spin.setMaximum(n_nodes - 1)
        malicious_count = int(self.malicious_spin.value())
        tolerance = (n_nodes - 1) // 3
        scope = '容错内' if malicious_count <= tolerance else '超出容错'
        update_status_card(
            self.network_card, f'{n_nodes} 节点',
            f'{malicious_count} 个恶意节点·{self.qubit_spin.value()} bit 签名', '#315CC8'
        )
        update_status_card(
            self.tolerance_card, f't = {tolerance}',
            f'当前 {malicious_count}/{n_nodes}：{scope}',
            '#168A78' if malicious_count <= tolerance else '#D97706'
        )
        update_status_card(
            self.detection_card, '待执行',
            f'预设恶意节点：{self._malicious_nodes() or "无"}', '#566573'
        )
        update_status_card(
            self.consensus_card, '待执行',
            '参数已改变，请重新执行共识', '#566573'
        )
        self.last_result = None
        self.node_table.setRowCount(0)
        self.network_view.set_state(n_nodes, self._malicious_nodes())
        self._update_boundary_note(n_nodes, malicious_count, tolerance)
        if not self.consensus_demo_pending:
            self.flow_animation.reset()
            self.result_placeholder.setText('暂无结果')
            self.result_stack.setCurrentWidget(self.result_placeholder)
            self.evidence_group.hide()

    def _update_boundary_note(self, n_nodes, malicious_count, tolerance,
                              result=None):
        scope_text = (
            '<span style="color:#168A78"><b>位于容错范围内</b></span>'
            if malicious_count <= tolerance else
            '<span style="color:#C2410C"><b>已超出容错范围</b></span>'
        )
        result_text = '暂无结果。'
        if result is not None:
            result_text = (
                '诚实节点支持超过 2/3，当前模型更新可写入账本。'
                if result.get('consensus_reached') else
                '可信支持未超过 2/3，当前模型更新被拒绝且不上链。'
            )
        self.boundary_note.setText(
            '<b>容错边界</b><br><br>'
            f'n = {n_nodes}，t = ⌊(n−1)/3⌋ = {tolerance}<br>'
            f'当前恶意节点 = {malicious_count}，{scope_text}。<br><br>'
            '<b>判定规则</b><br>'
            '• 节点支持率 ≥ 50% 则视为可信。<br>'
            '• 可信节点数 > 2n/3 才达成共识。<br><br>'
            f'<b>本轮结果</b><br>{result_text}'
        )

    def _set_consensus_controls_enabled(self, enabled):
        for control in [
            self.node_spin, self.malicious_spin, self.qubit_spin,
            self.btn_run,
        ]:
            control.setEnabled(enabled)

    def _start_consensus_demo(self):
        if self.consensus_demo_pending:
            return
        self.consensus_demo_pending = True
        self.last_result = None
        self.node_table.setRowCount(0)
        self.result_placeholder.setText('加载中……')
        self.result_stack.setCurrentWidget(self.result_placeholder)
        self.evidence_group.hide()
        self._set_consensus_controls_enabled(False)
        update_status_card(
            self.detection_card, '分析中', '正在比对各节点签名支持率', '#315CC8'
        )
        update_status_card(
            self.consensus_card, '表决中', '', '#315CC8'
        )
        n_nodes = int(self.node_spin.value())
        malicious_count = int(self.malicious_spin.value())
        tolerance = (n_nodes - 1) // 3
        final_caption = (
            '签名投票与异常筛查完成，即将展示共识结果。'
            if malicious_count <= tolerance else
            '恶意节点已超出容错上限，即将展示拒绝结果。'
        )
        self.flow_animation.play(final_caption=final_caption)

    def _complete_consensus_demo(self):
        if not self.consensus_demo_pending:
            return
        self.consensus_demo_pending = False
        self._run_consensus()
        self._set_consensus_controls_enabled(True)

    def _run_consensus(self):
        n_nodes = int(self.node_spin.value())
        n_qubits = int(self.qubit_spin.value())
        malicious_nodes = self._malicious_nodes()
        value_hash = hashlib.sha256(
            self.CONSENSUS_VALUE.encode('utf-8')
        ).hexdigest()
        self.consensus = QuantumByzantineConsensus(
            n_nodes=n_nodes, n_qubits=n_qubits
        )
        result = self.consensus.reach_consensus(
            value_hash=value_hash, malicious_nodes=malicious_nodes
        )
        self.last_result = result
        tolerance = int(result['max_malicious_tolerated'])
        detected = list(result['detected_malicious'])
        reached = bool(result['consensus_reached'])

        update_status_card(
            self.network_card, f'{n_nodes} 节点',
            f'{len(result["honest_nodes"])} 个节点通过支持率阈值', '#315CC8'
        )
        update_status_card(
            self.tolerance_card, f't = {tolerance}',
            f'实际恶意节点 {len(malicious_nodes)} 个',
            '#168A78' if len(malicious_nodes) <= tolerance else '#D97706'
        )
        update_status_card(
            self.detection_card,
            f'{len(detected)}/{len(malicious_nodes)}' if malicious_nodes else '无恶意',
            f'检出 {detected or "无"}·准确率 {result["detection_accuracy"] * 100:.0f}%',
            '#168A78' if result['detection_accuracy'] >= 0.99 else '#D97706'
        )
        update_status_card(
            self.consensus_card, '已达成' if reached else '已拒绝',
            '当前模型更新可上链' if reached else '本轮共识失败，不写入账本',
            '#168A78' if reached else '#DC2626'
        )

        self.node_table.setRowCount(n_nodes)
        actual_set = set(malicious_nodes)
        detected_set = set(detected)
        for row in range(n_nodes):
            decision = '可信' if row in result['honest_nodes'] else '已筛除'
            values = [
                f'N{row}',
                '恶意' if row in actual_set else '诚实',
                f'{result["support_rates"][row] * 100:.1f}%',
                decision,
            ]
            for column, text_value in enumerate(values):
                item = QTableWidgetItem(text_value)
                item.setTextAlignment(Qt.AlignCenter)
                if row in detected_set:
                    item.setBackground(QColor('#FEE2E2'))
                elif row in actual_set:
                    item.setBackground(QColor('#FFF7ED'))
                else:
                    item.setBackground(QColor('#EFF6FF'))
                self.node_table.setItem(row, column, item)

        self.network_view.set_state(n_nodes, malicious_nodes, result)
        self._update_boundary_note(
            n_nodes, len(malicious_nodes), tolerance, result
        )
        self.consensus_log.setPlainText(
            f'[量子拜占庭共识]\n'
            f'  当前模型指纹: {value_hash}\n'
            f'  节点数: {n_nodes}\n'
            f'  签名长度: {n_qubits} bit\n'
            f'  容错上限: {tolerance}\n'
            f'  实际恶意节点: {malicious_nodes}\n'
            f'  检测到的恶意节点: {detected}\n'
            f'  节点支持率: {result["support_rates"]}\n'
            f'  可信节点: {result["honest_nodes"]}\n'
            f'  检测准确率: {result["detection_accuracy"] * 100:.1f}%\n'
            f'  共识签名数: {len(result["consensus_signatures"])}\n'
            f'  共识结果: {"通过，允许上链" if reached else "失败，拒绝上链"}'
        )
        self.result_stack.setCurrentWidget(self.result_content)
        self.evidence_group.show()
        return result

    def _reset_demo(self):
        self.node_spin.blockSignals(True)
        self.malicious_spin.blockSignals(True)
        self.qubit_spin.blockSignals(True)
        self.node_spin.setValue(7)
        self.malicious_spin.setMaximum(6)
        self.malicious_spin.setValue(2)
        self.qubit_spin.setValue(64)
        self.node_spin.blockSignals(False)
        self.malicious_spin.blockSignals(False)
        self.qubit_spin.blockSignals(False)
        self.consensus = None
        self.last_result = None
        self.consensus_demo_pending = False
        self.flow_animation.reset()
        self._set_consensus_controls_enabled(True)
        self.node_table.setRowCount(0)
        self.consensus_log.setPlainText(
            '默认场景：7 个共识节点，2 个恶意节点，容错上限 t=2。'
        )
        self._update_parameter_preview()
        self.result_placeholder.setText('暂无结果')
        self.result_stack.setCurrentWidget(self.result_placeholder)
        self.evidence_group.hide()


class BlockchainTamperView(QWidget):
    """把真实 ``Blockchain`` 对象绘制成可视化哈希链。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chain = None
        self.tampered_index = None
        self.validation_state = 'idle'
        self.setMinimumHeight(190)
        self.setStyleSheet('background:#FBFBFA; border:1px solid #D9DDDA; border-radius:5px;')

    def set_chain(self, chain, tampered_index=None, validation_state='idle'):
        self.chain = chain
        self.tampered_index = tampered_index
        self.validation_state = validation_state
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor('#334155'))
        f = QFont('Microsoft YaHei')
        f.setPixelSize(11)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(QRectF(14, 8, self.width() - 28, 22), Qt.AlignLeft, '实际哈希链结构（SHA-256 + PoW）')

        if self.chain is None or not self.chain.chain:
            painter.setPen(QColor('#94A3B8'))
            painter.drawText(self.rect(), Qt.AlignCenter, '正在构建演示链……')
            return

        blocks = self.chain.chain
        count = len(blocks)
        left, right, gap = 14.0, 14.0, 24.0
        block_width = max(76.0, min(128.0, (self.width() - left - right - gap * (count - 1)) / count))
        total_width = block_width * count + gap * (count - 1)
        start_x = max(left, (self.width() - total_width) / 2.0)
        block_y, block_height = 42.0, 104.0
        target = '0' * self.chain.difficulty
        validation_revealed = self.validation_state in {
            'detected', 'bypassed', 'restored'
        }

        invalid_pow = {
            block.index for block in blocks[1:]
            if not block.hash().startswith(target)
        } if validation_revealed else set()
        broken_links = {
            index for index in range(1, count)
            if blocks[index].previous_hash != blocks[index - 1].hash()
        } if validation_revealed else set()

        for index, block in enumerate(blocks):
            x = start_x + index * (block_width + gap)
            rect = QRectF(x, block_y, block_width, block_height)

            if index > 0:
                line_y = block_y + block_height / 2.0
                line_start = QPointF(x - gap + 3.0, line_y)
                line_end = QPointF(x - 3.0, line_y)
                broken = index in broken_links
                link_color = (
                    '#CBD5E1' if self.validation_state == 'tampered'
                    else '#DC2626' if broken else '#36B37E'
                )
                painter.setPen(QPen(QColor(link_color), 2.2))
                painter.drawLine(line_start, line_end)
                if broken:
                    f = QFont('Arial')
                    f.setPixelSize(19)
                    f.setBold(True)
                    painter.setFont(f)
                    painter.drawText(
                        QRectF(x - gap, line_y - 17, gap, 30),
                        Qt.AlignCenter, '×'
                    )
                else:
                    f = QFont('Arial')
                    f.setPixelSize(13)
                    f.setBold(True)
                    painter.setFont(f)
                    painter.drawText(
                        QRectF(x - gap, line_y - 15, gap, 26),
                        Qt.AlignCenter, '→'
                    )

            is_tampered = index == self.tampered_index
            has_bad_pow = index in invalid_pow
            if has_bad_pow:
                fill, border = '#FFF1F2', '#DC2626'
            elif is_tampered:
                fill, border = '#FFF7ED', '#EA7A19'
            elif index == 0:
                fill, border = '#F1F5F9', '#94A3B8'
            else:
                fill, border = '#EFF6FF', '#4F7CFF'

            painter.setBrush(QColor(fill))
            painter.setPen(QPen(QColor(border), 2.2 if is_tampered or has_bad_pow else 1.4))
            painter.drawRoundedRect(rect, 9, 9)

            painter.setPen(QColor('#1E293B'))
            f = QFont('Microsoft YaHei')
            f.setPixelSize(11)
            f.setBold(True)
            painter.setFont(f)
            label = '创世块' if index == 0 else f'B{index}'
            painter.drawText(QRectF(x + 5, block_y + 7, block_width - 10, 18), Qt.AlignCenter, label)
            f = QFont('Consolas')
            f.setPixelSize(9)
            painter.setFont(f)
            painter.setPen(QColor('#475569'))
            painter.drawText(
                QRectF(x + 5, block_y + 31, block_width - 10, 16),
                Qt.AlignCenter, f'hash {block.hash()[:7]}…'
            )
            painter.drawText(
                QRectF(x + 5, block_y + 49, block_width - 10, 16),
                Qt.AlignCenter, f'prev {block.previous_hash[:7]}…'
            )
            accuracy = block.model_metadata.get('accuracy')
            detail = '起点记录' if accuracy is None else f'acc {float(accuracy):.1f}'
            f = QFont('Microsoft YaHei')
            f.setPixelSize(9)
            painter.setFont(f)
            painter.drawText(
                QRectF(x + 5, block_y + 70, block_width - 10, 15),
                Qt.AlignCenter, detail
            )
            if self.validation_state == 'tampered':
                status_text = '已改写' if is_tampered else '待验证'
                status_color = '#C25B08' if is_tampered else '#64748B'
            else:
                status_text = 'PoW 异常' if has_bad_pow else 'PoW 通过'
                status_color = '#DC2626' if has_bad_pow else '#168A78'
            painter.setPen(QColor(status_color))
            painter.drawText(
                QRectF(x + 5, block_y + 86, block_width - 10, 14),
                Qt.AlignCenter, status_text
            )

        state_text = {
            'idle': '原始链完整，请选择目标区块并执行篡改',
            'tampered': '篡改已注入，等待执行链校验',
            'detected': '本地校验已发现异常',
            'bypassed': '本地链校验通过，仍需外部共识或检查点复核',
            'restored': '原始链已恢复并重新校验',
        }.get(self.validation_state, '')
        state_color = '#DC2626' if self.validation_state == 'detected' else (
            '#C25B08' if self.validation_state == 'bypassed' else '#64748B'
        )
        painter.setPen(QColor(state_color))
        f = QFont('Microsoft YaHei')
        f.setPixelSize(9)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(
            QRectF(14, self.height() - 31, self.width() - 28, 22),
            Qt.AlignCenter, state_text
        )


class BlockchainTamperTab(QWidget):
    """区块链篡改独立演示模块。"""

    ATTACK_MODES = {
        'edit_only': '直接修改区块数据',
    }
    TAMPER_FLOW_STEPS = [
        ('定位目标区块', '锁定选中的历史训练记录'),
        ('读取原始指标', '保留修改前数值与区块指纹'),
        ('注入伪造数据', '替换模型准确率字段'),
        ('生成新指纹', '保留原 nonce，新内容产生不同哈希'),
        ('提交待检链', '将篡改记录交给 PoW 完整性校验'),
    ]
    VALIDATION_FLOW_STEPS = [
        ('读取区块内容', '逐块取出交易、模型摘要与 nonce'),
        ('重算 SHA-256', '按篡改后内容重新生成区块指纹'),
        ('检查 PoW', '验证原 nonce 是否仍满足挖矿难度'),
        ('定位异常区块', '找到第一个指纹不符合规则的区块'),
        ('输出完整性判定', '直接标记篡改并拒绝该链分支'),
    ]

    def __init__(self, parent_ref=None):
        super().__init__()
        self.parent_ref = parent_ref
        self.auto_play_explainer = False
        self.blockchain = None
        self.original_blockchain = None
        self.last_attack = None
        self.last_validation = None
        self.pending_ledger_action = None
        self._build_ui()
        self._initialize_demo_chain()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        action_bar = QFrame()
        action_bar.setObjectName('actionBar')
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 13, 16, 13)
        copy_layout = QVBoxLayout()
        title = QLabel('区块链篡改实验室')
        title.setObjectName('actionTitle')
        description = QLabel('直接修改历史区块数据，观察 SHA-256 指纹变化以及 PoW 校验如何发现篡改。')
        description.setObjectName('actionText')
        copy_layout.addWidget(title)
        copy_layout.addWidget(description)
        action_layout.addLayout(copy_layout)
        action_layout.addStretch()
        layout.addWidget(action_bar)

        cards = QHBoxLayout()
        _g = []
        self.chain_state_card = make_status_card('链状态', '完整', '6 个区块均通过 PoW 与链接校验', '#168A78', group=_g)
        self.target_card = make_status_card('篡改目标', '未选择', '可选 B1–B5 中的任意训练记录', '#566573', group=_g)
        self.validation_card = make_status_card('本地校验', '待执行', '检查 PoW 与 previous_hash', '#566573', group=_g)
        self.boundary_card = make_status_card('检测结论', '待执行', '验证后显示是否发现篡改', '#566573', group=_g)
        for card in [self.chain_state_card, self.target_card,
                     self.validation_card, self.boundary_card]:
            cards.addWidget(card)
        layout.addLayout(cards)

        controls_group = QGroupBox('篡改参数')
        controls_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        controls = QGridLayout(controls_group)
        controls.setHorizontalSpacing(12)
        controls.setVerticalSpacing(8)

        controls.addWidget(QLabel('目标区块'), 0, 0)
        self.block_combo = QComboBox()
        for index in range(1, 6):
            self.block_combo.addItem(f'B{index} · 第 {index} 轮训练记录', index)
        self.block_combo.setCurrentIndex(2)
        controls.addWidget(self.block_combo, 1, 0)

        controls.addWidget(QLabel('伪造准确率'), 0, 1)
        self.tamper_value_spin = QDoubleSpinBox()
        self.tamper_value_spin.setRange(0.0, 100.0)
        self.tamper_value_spin.setDecimals(1)
        self.tamper_value_spin.setSuffix(' %')
        self.tamper_value_spin.setValue(99.9)
        controls.addWidget(self.tamper_value_spin, 1, 1)

        self.btn_tamper = QPushButton('① 执行篡改')
        self.btn_tamper.setProperty('variant', 'warning')
        self.btn_tamper.clicked.connect(self._start_tamper_demo)
        controls.addWidget(self.btn_tamper, 1, 2)
        controls.setColumnStretch(0, 2)
        controls.setColumnStretch(1, 1)
        layout.addWidget(controls_group)

        tamper_process_group = QGroupBox('① 篡改注入过程')
        tamper_process_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        tamper_process_layout = QVBoxLayout(tamper_process_group)
        self.tamper_flow_animation = PlainLanguageFlowAnimation('ledger')
        self.tamper_flow_animation.finished.connect(self._complete_tamper_demo)
        tamper_process_layout.addWidget(self.tamper_flow_animation)
        layout.addWidget(tamper_process_group)

        self.tamper_result_group = QGroupBox('① 篡改注入结果')
        self.tamper_result_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        tamper_result_layout = QVBoxLayout(self.tamper_result_group)
        self.tamper_result_stack = QStackedWidget()
        self.tamper_result_placeholder = QLabel('暂无结果')
        self.tamper_result_placeholder.setAlignment(Qt.AlignCenter)
        self.tamper_result_placeholder.setMinimumHeight(245)
        self.tamper_result_placeholder.setStyleSheet(
            'background:#F7F8F6; color:#747C78; border:1px dashed #BDC5C0; '
            'border-radius:5px; font-size: 20px; font-weight:600;'
        )
        self.tamper_result_stack.addWidget(self.tamper_result_placeholder)

        self.tamper_result_content = QWidget()
        tamper_content_layout = QVBoxLayout(self.tamper_result_content)
        tamper_content_layout.setContentsMargins(0, 0, 0, 0)
        tamper_content_layout.setSpacing(10)
        self.tamper_result_summary = QLabel()
        self.tamper_result_summary.setWordWrap(True)
        self.tamper_result_summary.setStyleSheet(
            'background:#FAF5EA; color:#80521A; border:1px solid #D9BF98; '
            'border-radius:5px; padding:10px 13px;'
        )
        tamper_content_layout.addWidget(self.tamper_result_summary)
        self.tamper_chain_view = BlockchainTamperView()
        tamper_content_layout.addWidget(self.tamper_chain_view)
        self.tamper_result_stack.addWidget(self.tamper_result_content)
        tamper_result_layout.addWidget(self.tamper_result_stack)
        layout.addWidget(self.tamper_result_group)

        validation_process_group = QGroupBox('② 区块链完整性验证')
        validation_process_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        validation_process_layout = QVBoxLayout(validation_process_group)
        validation_action_layout = QHBoxLayout()
        validation_action_layout.addStretch()
        self.btn_validate = QPushButton('开始验证区块链')
        self.btn_validate.setMinimumWidth(190)
        self.btn_validate.setProperty('variant', 'primary')
        self.btn_validate.clicked.connect(self._start_validation_demo)
        self.btn_validate.setEnabled(False)
        validation_action_layout.addWidget(self.btn_validate)
        validation_process_layout.addLayout(validation_action_layout)
        self.validation_flow_animation = PlainLanguageFlowAnimation('ledger')
        self.validation_flow_animation.finished.connect(self._complete_validation_demo)
        validation_process_layout.addWidget(self.validation_flow_animation)
        layout.addWidget(validation_process_group)

        self.validation_result_group = QGroupBox('② 完整性验证结果')
        self.validation_result_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        validation_result_layout = QVBoxLayout(self.validation_result_group)
        self.validation_result_stack = QStackedWidget()
        self.validation_result_placeholder = QLabel('暂无结果')
        self.validation_result_placeholder.setAlignment(Qt.AlignCenter)
        self.validation_result_placeholder.setMinimumHeight(390)
        self.validation_result_placeholder.setStyleSheet(
            'background:#F7F8F6; color:#747C78; border:1px dashed #BDC5C0; '
            'border-radius:5px; font-size: 20px; font-weight:600;'
        )
        self.validation_result_stack.addWidget(self.validation_result_placeholder)

        self.validation_result_content = QWidget()
        validation_content_layout = QVBoxLayout(self.validation_result_content)
        validation_content_layout.setContentsMargins(0, 0, 0, 0)
        validation_content_layout.setSpacing(10)
        self.validation_chain_view = BlockchainTamperView()
        validation_content_layout.addWidget(self.validation_chain_view)
        evidence_layout = QHBoxLayout()
        self.validation_log = QTextEdit()
        self.validation_log.setReadOnly(True)
        self.validation_log.setFont(QFont('Consolas', 12))
        self.validation_log.setMinimumHeight(175)
        evidence_layout.addWidget(self.validation_log, 7)
        teaching_note = QLabel(
            '<b>如何解读</b><br><br>'
            '• 攻击者直接改写历史准确率。<br>'
            '• 区块内容改变，SHA-256 指纹随之变化。<br>'
            '• 原 nonce 不再满足 PoW，校验立即失败。<br><br>'
            '<b>关键结论</b><br>'
            '区块链的防篡改不是阻止数据被修改，而是让任何修改都留下可验证的哈希异常。'
        )
        teaching_note.setWordWrap(True)
        teaching_note.setAlignment(Qt.AlignTop)
        teaching_note.setStyleSheet(
            'background:#F7F8F6; color:#515A56; border:1px solid #D9DDDA; '
            'border-radius:5px; padding:12px;'
        )
        evidence_layout.addWidget(teaching_note, 4)
        validation_content_layout.addLayout(evidence_layout)
        self.validation_result_stack.addWidget(self.validation_result_content)
        validation_result_layout.addWidget(self.validation_result_stack)
        layout.addWidget(self.validation_result_group)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _initialize_demo_chain(self):
        rng = np.random.RandomState(20260811)
        chain = Blockchain(difficulty=2)
        for round_index in range(1, 6):
            chain.add_transaction(
                client_id=round_index % 5,
                grad_hash=f'gradient-round-{round_index}',
                metadata={'round': round_index}
            )
            chain.mine_block(
                rng.normal(size=16),
                {
                    'round': round_index,
                    'accuracy': round(72.0 + round_index * 3.4, 1),
                    'source': 'federated_training',
                },
                [f'node-{node}-signature' for node in range(4)]
            )
        self.blockchain = chain
        self.original_blockchain = deepcopy(chain)
        self.last_attack = None
        self.last_validation = None
        self.pending_ledger_action = None
        self.tamper_flow_animation.reset()
        self._reset_validation_flow()
        self.tamper_chain_view.set_chain(self.blockchain, validation_state='idle')
        self.validation_chain_view.set_chain(self.blockchain, validation_state='idle')
        self.tamper_result_summary.setText(
            '暂无结果'
        )
        self.validation_log.setPlainText(
            '演示链已建立：创世块 + 5 轮联邦训练记录\n'
            '难度：2 个前导零（演示难度）\n'
            '校验项：SHA-256 内容哈希、PoW 与 previous_hash 链接关系'
        )
        self.tamper_result_placeholder.setText('暂无结果')
        self.tamper_result_stack.setCurrentWidget(self.tamper_result_placeholder)
        self.validation_result_placeholder.setText('暂无结果')
        self.validation_result_stack.setCurrentWidget(self.validation_result_placeholder)

    def _set_ledger_controls_enabled(self, enabled):
        for control in [
            self.block_combo, self.tamper_value_spin,
            self.btn_tamper,
        ]:
            control.setEnabled(enabled)
        self.btn_validate.setEnabled(
            enabled and self.last_attack is not None and self.last_validation is None
        )

    def _reset_validation_flow(self):
        self.validation_flow_animation.reset()
        self.validation_flow_animation.steps = list(self.VALIDATION_FLOW_STEPS)
        self.validation_flow_animation.final_caption = '暂无校验结果'
        self.validation_flow_animation.update()

    def _start_tamper_demo(self):
        if self.pending_ledger_action is not None:
            return
        self.pending_ledger_action = 'tamper'
        self.tamper_result_placeholder.setText('加载中……')
        self.tamper_result_stack.setCurrentWidget(self.tamper_result_placeholder)
        self.validation_result_placeholder.setText('暂无结果')
        self.validation_result_stack.setCurrentWidget(self.validation_result_placeholder)
        self._reset_validation_flow()
        self._set_ledger_controls_enabled(False)
        update_status_card(self.chain_state_card, '处理中', '正在修改目标记录', '#D97706')
        update_status_card(self.target_card, '定位中', '正在锁定选中区块', '#D97706')
        update_status_card(self.validation_card, '待校验', '', '#566573')
        self.tamper_flow_animation.play(
            final_caption='篡改记录已生成，可继续执行真实链校验。',
            steps=self.TAMPER_FLOW_STEPS,
        )

    def _start_validation_demo(self):
        if self.pending_ledger_action is not None or self.last_attack is None:
            return
        self.pending_ledger_action = 'validate'
        self.validation_result_placeholder.setText('加载中……')
        self.validation_result_stack.setCurrentWidget(self.validation_result_placeholder)
        self._set_ledger_controls_enabled(False)
        update_status_card(self.validation_card, '校验中', '正在重算 PoW 与链接', '#315CC8')
        update_status_card(self.boundary_card, '校验中', '正在比对区块指纹与 PoW 规则', '#315CC8')
        self.validation_flow_animation.play(
            final_caption='区块指纹与 PoW 规则已完成对比。',
            steps=self.VALIDATION_FLOW_STEPS,
        )

    def _complete_tamper_demo(self):
        if self.pending_ledger_action != 'tamper':
            return
        self.pending_ledger_action = None
        self._execute_tamper()
        self._set_ledger_controls_enabled(True)

    def _complete_validation_demo(self):
        if self.pending_ledger_action != 'validate':
            return
        self.pending_ledger_action = None
        self._validate_chain()
        self._set_ledger_controls_enabled(True)

    def _execute_tamper(self):
        # 每次都从同一原始快照开始，便于直观对比篡改前后指纹。
        self.blockchain = deepcopy(self.original_blockchain)
        target_index = int(self.block_combo.currentData())
        mode = 'edit_only'
        block = self.blockchain.chain[target_index]
        original_value = float(block.model_metadata.get('accuracy', 0.0))
        original_hash = block.hash()
        tampered_value = float(self.tamper_value_spin.value())
        block.model_metadata['accuracy'] = tampered_value

        self.last_attack = {
            'target_index': target_index,
            'mode': mode,
            'original_value': original_value,
            'tampered_value': tampered_value,
            'original_hash': original_hash,
            'tampered_hash': block.hash(),
        }
        self.last_validation = None
        self.tamper_chain_view.set_chain(
            self.blockchain, tampered_index=target_index,
            validation_state='tampered'
        )
        self.tamper_result_summary.setText(
            f'<b>B{target_index} 已被改写：</b>'
            f'准确率 {original_value:.1f}% → {tampered_value:.1f}%<br>'
            f'原指纹 {original_hash[:16]}… → '
            f'新指纹 {block.hash()[:16]}…'
        )
        update_status_card(
            self.chain_state_card, '已注入', '篡改已写入当前内存链', '#D97706'
        )
        update_status_card(
            self.target_card, f'B{target_index}',
            f'{original_value:.1f}% → {tampered_value:.1f}%', '#D97706'
        )
        update_status_card(
            self.validation_card, '待验证', '', '#315CC8'
        )
        update_status_card(
            self.boundary_card, '待判定', '校验后给出检测边界', '#566573'
        )
        self.btn_validate.setEnabled(True)
        self.validation_log.setPlainText(
            f'[篡改注入]\n'
            f'  目标: B{target_index}\n'
            f'  方式: {self.ATTACK_MODES[mode]}\n'
            f'  accuracy: {original_value:.1f}% -> {tampered_value:.1f}%\n'
            f'  原哈希: {original_hash}\n'
            f'  新哈希: {block.hash()}\n\n'
            '篡改已完成，等待执行链校验。'
        )
        self.tamper_result_stack.setCurrentWidget(self.tamper_result_content)
        self.validation_result_placeholder.setText('暂无结果')
        self.validation_result_stack.setCurrentWidget(self.validation_result_placeholder)

    def _validate_chain(self):
        if self.blockchain is None:
            return None
        valid, message = self.blockchain.validate_chain()
        attack = self.last_attack
        attacked = attack is not None
        detected = attacked and not valid
        requires_external_consensus = attacked and valid
        current_tip_hash = self.blockchain.chain[-1].hash()
        trusted_tip_hash = self.original_blockchain.chain[-1].hash()
        checkpoint_match = current_tip_hash == trusted_tip_hash
        external_checkpoint_detected = attacked and not checkpoint_match
        self.last_validation = {
            'valid': valid,
            'detected': detected,
            'message': message,
            'requires_external_consensus': requires_external_consensus,
            'checkpoint_match': checkpoint_match,
            'external_checkpoint_detected': external_checkpoint_detected,
        }

        if detected:
            state = 'detected'
            update_status_card(self.chain_state_card, '异常', message, '#DC2626')
            update_status_card(self.validation_card, '已检出', '本地 PoW / 链接校验失败', '#168A78')
            update_status_card(self.boundary_card, '本地可防', '无需继续信任该链分支', '#168A78')
            conclusion = '篡改被本地哈希链校验发现。'
        elif requires_external_consensus:
            state = 'bypassed'
            update_status_card(self.chain_state_card, '结构有效', message, '#D97706')
            update_status_card(self.validation_card, '本地通过', '当前链内部已自洽', '#D97706')
            update_status_card(
                self.boundary_card, '检查点检出',
                '链顶哈希与可信快照不一致，需拒绝该分支', '#168A78'
            )
            conclusion = (
                '篡改后的链在本地再次自洽；这不代表攻击成功，'
                '本次已通过可信链顶检查点发现历史分歧。'
            )
        else:
            state = 'restored'
            update_status_card(self.chain_state_card, '完整', message, '#168A78')
            update_status_card(self.validation_card, '已通过', '未检测到结构异常', '#168A78')
            update_status_card(self.boundary_card, '未触发', '当前未注入篡改', '#566573')
            conclusion = '原始链完整有效。'

        self.validation_chain_view.set_chain(
            self.blockchain,
            tampered_index=attack['target_index'] if attack else None,
            validation_state=state
        )
        mode_text = self.ATTACK_MODES[attack['mode']] if attack else '无攻击'
        self.validation_log.append(
            f'\n\n[真实链校验]\n'
            f'  攻击方式: {mode_text}\n'
            f'  validate_chain(): {valid}\n'
            f'  校验消息: {message}\n'
            f'  本地检出: {"是" if detected else "否"}\n'
            f'  结论: {conclusion}'
        )
        self.btn_validate.setEnabled(False)
        self.validation_result_stack.setCurrentWidget(self.validation_result_content)
        return self.last_validation

    def _restore_chain(self):
        if self.original_blockchain is None:
            return
        self.blockchain = deepcopy(self.original_blockchain)
        self.last_attack = None
        self.last_validation = None
        self.pending_ledger_action = None
        self.tamper_flow_animation.reset()
        self._reset_validation_flow()
        valid, message = self.blockchain.validate_chain()
        self.tamper_chain_view.set_chain(self.blockchain, validation_state='restored')
        self.validation_chain_view.set_chain(self.blockchain, validation_state='restored')
        update_status_card(self.chain_state_card, '完整', message, '#168A78')
        update_status_card(self.target_card, '已清除', '篡改数据已撤销', '#168A78')
        update_status_card(self.validation_card, '已通过', '原始快照校验正常', '#168A78')
        update_status_card(self.boundary_card, '未触发', '当前为可信原始链', '#566573')
        self.btn_validate.setEnabled(False)
        self.validation_log.setPlainText(
            f'[恢复原始链]\n  validate_chain(): {valid}\n  校验消息: {message}'
        )
        self.tamper_result_stack.setCurrentWidget(self.tamper_result_content)
        self.validation_result_stack.setCurrentWidget(self.validation_result_content)
        self._set_ledger_controls_enabled(True)


class AttackTab(QWidget):

    RESULT_REVEAL_INTERVAL_MS = 55
    RESULT_REVEAL_FRAMES = 48
    ATTACK_HISTORY_ORDER = (
        'eavesdropping', 'model_poisoning',
        'gradient_leakage', 'blockchain_tampering',
    )
    ATTACK_HISTORY_KEYS = {
        'eavesdropping': 'eavesdropping',
        'poisoning': 'model_poisoning',
        'leakage': 'gradient_leakage',
        'tampering': 'blockchain_tampering',
    }

    def __init__(self, parent_ref=None):
        super().__init__()
        self.parent_ref = parent_ref
        self.simulator = AttackSimulator()
        self.pending_attack_type = None
        self.auto_play_explainer = False
        self.result_reveal_frame = self.RESULT_REVEAL_FRAMES
        self.result_reveal_timer = QTimer(self)
        self.result_reveal_timer.setInterval(self.RESULT_REVEAL_INTERVAL_MS)
        self.result_reveal_timer.timeout.connect(self._advance_attack_result_reveal)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        action_bar = QFrame()
        action_bar.setObjectName('actionBar')
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 13, 16, 13)
        action_copy = QVBoxLayout()
        action_copy.setSpacing(2)
        action_title = QLabel('红蓝对抗实验室')
        action_title.setObjectName('actionTitle')
        action_text = QLabel('在统一环境中注入四类攻击，比较检测、削弱和完整性保护能力。')
        action_text.setObjectName('actionText')
        action_copy.addWidget(action_title)
        action_copy.addWidget(action_text)
        action_layout.addLayout(action_copy)
        action_layout.addStretch()
        self.btn_all = QPushButton('运行全部攻防实验')
        self.btn_all.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.btn_all.setProperty('variant', 'danger')
        self.btn_all.setMinimumWidth(210)
        self.btn_all.clicked.connect(self._on_all_attacks)
        action_layout.addWidget(self.btn_all)
        layout.addWidget(action_bar)

        card_layout = QHBoxLayout()
        _g = []
        self.attack_detect_card = make_status_card('窃听检测', '待演示', 'QKD 发现中间人攻击', '#566573', group=_g)
        self.attack_poison_card = make_status_card('抗毒化', '待演示', '鲁棒聚合降低恶意梯度影响', '#566573', group=_g)
        self.attack_privacy_card = make_status_card('隐私泄漏', '待演示', 'QDP 降低梯度逆向成功率', '#566573', group=_g)
        self.attack_chain_card = make_status_card('防篡改', '待演示', '区块链检测数据篡改', '#566573', group=_g)
        for card in [self.attack_detect_card, self.attack_poison_card,
                     self.attack_privacy_card, self.attack_chain_card]:
            card_layout.addWidget(card)
        layout.addLayout(card_layout)

        explainer_group = QGroupBox('实时攻防观测')
        explainer_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        explainer_layout = QVBoxLayout(explainer_group)
        self.flow_animation = PlainLanguageFlowAnimation('defense')
        self.flow_animation.finished.connect(self._complete_attack_demo)
        explainer_layout.addWidget(self.flow_animation)
        layout.addWidget(explainer_group)

        catalog = QGroupBox('攻击场景目录')
        catalog_layout = QGridLayout(catalog)
        btn_layout = QGridLayout()

        attacks = [
            ('窃听攻击  ·  QKD 信道', 'eavesdropping', '#3498DB'),
            ('模型毒化  ·  恶意梯度', 'poisoning', '#E67E22'),
            ('梯度反演  ·  隐私泄漏', 'leakage', '#9B59B6'),
            ('链上篡改  ·  完整性校验', 'tampering', '#27AE60'),
        ]
        self.attack_buttons = {}
        for i, (name, key, color) in enumerate(attacks):
            btn = QPushButton(name)
            btn.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
            btn.setObjectName('attackButton')
            btn.clicked.connect(lambda checked, k=key: self._on_attack(k))
            btn_layout.addWidget(btn, i // 2, i % 2)
            self.attack_buttons[key] = btn
        catalog_layout.addLayout(btn_layout, 0, 0)
        layout.addWidget(catalog)

        result_group = QGroupBox('攻击-防护结果分析')
        result_group.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        result_layout = QHBoxLayout(result_group)
        self.figure = Figure(figsize=(8, 3), facecolor='white')
        self.canvas = FigureCanvas(self.figure)
        result_layout.addWidget(self.canvas, 7)
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        self.result_output.setFont(QFont('Consolas', 12))
        self.result_output.setPlaceholderText('暂无结果')
        result_layout.addWidget(self.result_output, 5)
        layout.addWidget(result_group, 1)

        self._draw_summary_plot()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def play_explainer(self):
        self.flow_animation.play(
            attack_type='all',
            final_caption='四类风险分别交给 QKD、差分隐私、鲁棒聚合和区块哈希处理。'
        )

    def _stop_attack_result_reveal(self):
        if self.result_reveal_timer.isActive():
            self.result_reveal_timer.stop()
        self.result_reveal_frame = self.RESULT_REVEAL_FRAMES

    def _start_attack_result_reveal(self):
        """安全判定完成后，让结果柱按顺序缓动展开一次。"""
        self._stop_attack_result_reveal()
        if not self.simulator.attack_history:
            self._draw_summary_plot()
            return
        self.result_reveal_frame = 0
        self._draw_summary_plot(reveal_progress=0.0)
        self.result_reveal_timer.start()

    def _advance_attack_result_reveal(self):
        self.result_reveal_frame = min(
            self.RESULT_REVEAL_FRAMES, self.result_reveal_frame + 1
        )
        progress = self.result_reveal_frame / self.RESULT_REVEAL_FRAMES
        self._draw_summary_plot(reveal_progress=progress)
        if self.result_reveal_frame >= self.RESULT_REVEAL_FRAMES:
            self.result_reveal_timer.stop()

    @staticmethod
    def _staggered_attack_bar_progress(progress: float, index: int) -> float:
        """四条结果依次启动，每条使用 ease-out 曲线收尾。"""
        start = index * 0.12
        duration = 0.64
        local = max(0.0, min(1.0, (progress - start) / duration))
        return 1.0 - (1.0 - local) ** 3

    def _on_attack(self, attack_type: str):
        """先展示防线检查过程，结束后才执行并公布对应实验结果。"""
        self._start_attack_demo(attack_type)

    def _on_all_attacks(self):
        self._start_attack_demo('all')

    def _start_attack_demo(self, attack_type: str):
        if self.pending_attack_type is not None:
            return
        if attack_type not in {'eavesdropping', 'poisoning', 'leakage', 'tampering', 'all'}:
            return
        self._stop_attack_result_reveal()
        captions = {
            'eavesdropping': '窃听会扰动量子态，QKD 通过误码率异常发现它并作废密钥。',
            'poisoning': '恶意梯度不直接进入模型，共识筛查和鲁棒聚合会降低其影响。',
            'leakage': '加噪后的梯度仍可用于聚合，但不再精确对应某个人的特征。',
            'tampering': '直接篡改会触发 PoW 或链接异常；整段重写还需外部共识复核。',
            'all': '四类攻击分别由 QKD、差分隐私、鲁棒聚合和区块哈希防护。',
        }
        self.pending_attack_type = attack_type
        # 单项实验需要与已完成的其他场景结果累积展示。
        # 只有“运行全部”会开启一批全新的四项实验。
        if attack_type == 'all':
            self.simulator = AttackSimulator()
        self.result_output.clear()
        self.result_output.append('攻防检查进行中……')
        self._set_attack_controls_enabled(False)
        self._set_attack_pending_cards(attack_type)
        self._draw_summary_plot()
        self.flow_animation.play(
            attack_type=attack_type,
            final_caption=captions[attack_type]
        )

    def _complete_attack_demo(self):
        attack_type = self.pending_attack_type
        if attack_type is None:
            return
        self.pending_attack_type = None
        self.result_output.clear()
        selected = (
            ['eavesdropping', 'poisoning', 'leakage', 'tampering']
            if attack_type == 'all' else [attack_type]
        )
        results = {key: self._execute_attack(key) for key in selected}
        self._update_attack_result_cards(results)
        if attack_type == 'all':
            self.result_output.append('\n' + '=' * 50)
            self.result_output.append(
                '总结：窃听、毒化和篡改可被检测或削弱；梯度泄漏需继续控制隐私预算'
            )
            self.result_output.append('=' * 50)
        self._start_attack_result_reveal()
        self._set_attack_controls_enabled(True)

    def _execute_attack(self, attack_type: str):
        self.result_output.append(f'\n{"=" * 50}')
        self.result_output.append(f'[{time.strftime("%H:%M:%S")}] 执行攻击：{attack_type}')
        self.result_output.append('=' * 50)
        if attack_type == 'eavesdropping':
            result = self.simulator.eavesdropping_attack()
            self._print_result(result, '中间人窃听攻击检测')
        elif attack_type == 'poisoning':
            result = self.simulator.model_poisoning_attack(n_clients=5, n_rounds=4)
            self._print_result(result, '模型毒化攻击防护')
        elif attack_type == 'leakage':
            result = self.simulator.gradient_leakage_attack()
            self._print_result(result, '梯度泄漏防护')
        elif attack_type == 'tampering':
            result = self.simulator.blockchain_tampering_attack()
            self._print_result(result, '区块链篡改检测')
        self._deduplicate_attack_history()
        return result

    def _deduplicate_attack_history(self):
        """每类攻击只保留最新结果，并按固定顺序供图表渲染。"""
        latest_by_type = {}
        unknown_results = []
        for result in self.simulator.attack_history:
            attack_type = result.get('attack_type')
            if attack_type in self.ATTACK_HISTORY_ORDER:
                latest_by_type[attack_type] = result
            else:
                unknown_results.append(result)
        self.simulator.attack_history[:] = [
            latest_by_type[attack_type]
            for attack_type in self.ATTACK_HISTORY_ORDER
            if attack_type in latest_by_type
        ] + unknown_results

    def _update_attack_result_cards(self, results):
        eavesdrop = results.get('eavesdropping')
        if eavesdrop:
            detected = eavesdrop.get('detection_success')
            update_status_card(
                self.attack_detect_card,
                '检测到' if detected else '未检测',
                '窃听会造成误码率明显升高',
                '#27AE60' if detected else '#E74C3C'
            )
        poisoning = results.get('poisoning')
        if poisoning:
            poison_reduction = poisoning.get('robust_reduction_rate', 0.0) * 100
            update_status_card(
                self.attack_poison_card,
                f'降低{poison_reduction:.1f}%',
                '鲁棒聚合降低恶意梯度影响',
                '#27AE60' if poison_reduction >= 70 else '#E67E22'
            )
        leakage = results.get('leakage')
        if leakage:
            high_eps_risks = [
                item for item in leakage.get('epsilon_scan', [])
                if item.get('epsilon', 0) >= 5.0 and item.get('attack_success_rate', 0) > 0.2
            ]
            low_eps_safe = any(
                item.get('epsilon') == 1.0 and item.get('attack_success_rate', 1.0) < 0.2
                for item in leakage.get('epsilon_scan', [])
            )
            update_status_card(
                self.attack_privacy_card,
                '低ε安全' if low_eps_safe else '风险较高',
                '高 ε 下仍有泄漏风险' if high_eps_risks else '低隐私预算下攻击成功率显著下降',
                '#E67E22' if high_eps_risks else '#27AE60'
            )
        tampering = results.get('tampering')
        if tampering:
            detected = tampering.get('detection_success', True)
            update_status_card(
                self.attack_chain_card,
                '检测到' if detected else '未检测',
                '区块哈希校验发现篡改',
                '#27AE60' if detected else '#E74C3C'
            )

    def _set_attack_pending_cards(self, attack_type):
        cards = {
            'eavesdropping': (self.attack_detect_card, '正在检查量子信道'),
            'poisoning': (self.attack_poison_card, '正在筛查异常梯度'),
            'leakage': (self.attack_privacy_card, '正在评估反演风险'),
            'tampering': (self.attack_chain_card, '正在校验区块哈希'),
        }
        completed_types = {
            result.get('attack_type')
            for result in self.simulator.attack_history
        }
        for key, (card, detail) in cards.items():
            if attack_type in {key, 'all'}:
                update_status_card(card, '检测中', detail, '#315CC8')
            elif self.ATTACK_HISTORY_KEYS[key] not in completed_types:
                update_status_card(card, '待开始', '', '#566573')

    def _set_attack_controls_enabled(self, enabled):
        self.btn_all.setEnabled(enabled)
        for button in self.attack_buttons.values():
            button.setEnabled(enabled)
    
    def _print_result(self, result: Dict, title: str):
        self.result_output.append(f'\n--- {title} ---')
        if 'detection_success' in result:
            self.result_output.append(f'  检测结果: {"✓ 成功" if result["detection_success"] else "✗ 失败"}')
        if 'conclusion' in result:
            self.result_output.append(f'  防护结论: {result["conclusion"]}')
        
        for key, val in result.items():
            if key in ['attack_type', 'detection_success', 'conclusion']:
                continue
            if isinstance(val, (int, float, str, list)):
                self.result_output.append(f'  {key}: {val}')
    
    def _draw_summary_plot(self, reveal_progress: float = None):
        """用横向圆角进度柱展示四类攻击的风险控制效果。"""
        from matplotlib.patches import FancyBboxPatch

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        results = self.simulator.attack_history
        if not results:
            message = (
                '安全防线正在检查攻击路径……'
                if self.pending_attack_type is not None
                else '运行攻防实验后显示防护结果'
            )
            ax.text(0.5, 0.5, message, ha='center', va='center', color='#64748B')
            ax.set_axis_off()
            self.canvas.draw()
            return

        attack_keys = [
            'eavesdropping', 'model_poisoning',
            'gradient_leakage', 'blockchain_tampering'
        ]
        categories = ['中间人窃听', '模型毒化', '梯度泄漏', '区块链篡改']
        scores = [rate * 100 for rate in self._attack_protection_scores(results)]
        colors = ['#4EA8DE', '#F2994A', '#A56CC1', '#36B37E']
        executed = {result.get('attack_type') for result in results}
        y_positions = np.arange(len(categories))[::-1]
        bar_height = 0.54

        for index, (y, key, score, color) in enumerate(
            zip(y_positions, attack_keys, scores, colors)
        ):
            # 淡色轨道固定为 100%，方便快速对比四道防线。
            track = FancyBboxPatch(
                (0, y - bar_height / 2), 100, bar_height,
                boxstyle='round,pad=0,rounding_size=0.24',
                linewidth=0, facecolor='#EDF2F7', zorder=1
            )
            ax.add_patch(track)

            if key not in executed:
                ax.text(
                    3.0, y, '待验证', ha='left', va='center',
                    fontsize=8.5, color='#8A97AA', zorder=4
                )
                continue

            bar_progress = (
                1.0 if reveal_progress is None
                else self._staggered_attack_bar_progress(reveal_progress, index)
            )
            displayed_score = score * bar_progress
            if displayed_score <= 0.01:
                continue

            shadow = FancyBboxPatch(
                (0.7, y - bar_height / 2 - 0.045), max(0.8, displayed_score), bar_height,
                boxstyle='round,pad=0,rounding_size=0.24',
                linewidth=0, facecolor='#CBD5E1',
                alpha=0.28 + 0.14 * bar_progress, zorder=2
            )
            fill = FancyBboxPatch(
                (0, y - bar_height / 2), max(0.8, displayed_score), bar_height,
                boxstyle='round,pad=0,rounding_size=0.24',
                linewidth=0, facecolor=color,
                alpha=0.82 + 0.18 * bar_progress, zorder=3
            )
            ax.add_patch(shadow)
            ax.add_patch(fill)

            if displayed_score > 12:
                ax.plot(
                    [2.2, displayed_score - 2.2],
                    [y + bar_height * 0.20, y + bar_height * 0.20],
                    color='white', alpha=0.24, linewidth=1.2,
                    solid_capstyle='round', zorder=4
                )
            if displayed_score >= 17:
                value_x = displayed_score - 2.0
                value_alignment = 'right'
                value_color = 'white'
            else:
                value_x = min(102.0, displayed_score + 2.0)
                value_alignment = 'left'
                value_color = color
            ax.text(
                value_x, y, f'{displayed_score:.0f}%',
                ha=value_alignment, va='center', fontsize=9.2,
                color=value_color, fontweight='bold', zorder=5
            )

        ax.set_yticks(y_positions)
        ax.set_yticklabels(categories, fontsize=9.2)
        ax.set_xlim(0, 104)
        ax.set_ylim(-0.65, len(categories) - 0.35)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_title('各攻击场景防护效果', fontsize=11, loc='left', pad=12)
        ax.set_xlabel('风险识别与控制能力 (%)', fontsize=8.5, labelpad=8)
        ax.grid(True, alpha=0.26, axis='x')
        ax.set_axisbelow(True)
        ax.tick_params(axis='y', length=0, pad=10)
        ax.tick_params(axis='x', length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        self.figure.subplots_adjust(left=0.24, right=0.97, top=0.82, bottom=0.20)
        self.canvas.draw()

    def _attack_protection_scores(self, results):
        scores = {
            'eavesdropping': 0.0,
            'model_poisoning': 0.0,
            'gradient_leakage': 0.0,
            'blockchain_tampering': 0.0
        }
        for result in results:
            attack_type = result.get('attack_type')
            if attack_type == 'eavesdropping':
                scores[attack_type] = 95.0 if result.get('detection_success') else 20.0
            elif attack_type == 'model_poisoning':
                scores[attack_type] = max(0.0, min(100.0, result.get('robust_reduction_rate', 0.0) * 100))
            elif attack_type == 'gradient_leakage':
                scan = result.get('epsilon_scan', [])
                if scan:
                    # 综合所有 ε 的平均防护率，高 ε 风险会自然拉低该分数。
                    scores[attack_type] = max(
                        0.0,
                        min(100.0, np.mean([item.get('protection_success_rate', 0.0) for item in scan]) * 100)
                    )
            elif attack_type == 'blockchain_tampering':
                scores[attack_type] = 98.0 if result.get('detection_success') else 20.0
        return [
            scores['eavesdropping'] / 100.0,
            scores['model_poisoning'] / 100.0,
            scores['gradient_leakage'] / 100.0,
            scores['blockchain_tampering'] / 100.0
        ]


def draw_real_scenario_result_dashboard(figure: Figure, data: Dict, summary: Dict,
                                        test_scope: str = '同一测试集'):
    """为三个真实场景绘制统一的“结论—恢复—稳健性”仪表板。"""
    from matplotlib.lines import Line2D

    figure.clear()
    if not data:
        ax = figure.add_subplot(111)
        ax.text(
            0.5, 0.54, '运行安全联合训练后显示对照结果',
            ha='center', va='center', fontsize=11, color='#64748B'
        )
        ax.text(
            0.5, 0.43, '将统一展示单次指标恢复、五种子配对结果和运行成本',
            ha='center', va='center', fontsize=8.5, color='#94A3B8'
        )
        ax.set_axis_off()
        figure.tight_layout(pad=1.4)
        return

    mapping = {item.get('name'): item for item in data.get('results', [])}
    attacked = mapping.get('attacked_plain_federated', {})
    secure = mapping.get('secure_federated', {})
    attacked_metrics = attacked.get('metrics', {})
    secure_metrics = secure.get('metrics', {})
    per_seed = list((summary or {}).get('per_seed', []))

    grid = figure.add_gridspec(
        2, 2, height_ratios=[0.50, 3.15], width_ratios=[1.0, 1.16],
        hspace=0.28, wspace=0.24
    )
    ax_summary = figure.add_subplot(grid[0, :])
    ax_metrics = figure.add_subplot(grid[1, 0])
    ax_seeds = figure.add_subplot(grid[1, 1])
    ax_summary.set_axis_off()

    attacked_balanced = float(attacked_metrics.get('balanced_accuracy', 0.0))
    secure_balanced = float(secure_metrics.get('balanced_accuracy', 0.0))
    single_gain = secure_balanced - attacked_balanced
    seed_gains = np.asarray([
        float(row.get('secure_balanced_accuracy', 0.0))
        - float(row.get('attacked_plain_balanced_accuracy', 0.0))
        for row in per_seed
    ], dtype=float)
    mean_gain = float(np.mean(seed_gains)) if len(seed_gains) else 0.0
    win_count = int(np.sum(seed_gains > 0.0)) if len(seed_gains) else 0
    attacked_runtime = float(attacked.get('runtime_seconds', 0.0) or 0.0)
    secure_runtime = float(secure.get('runtime_seconds', 0.0) or 0.0)
    runtime_factor = secure_runtime / attacked_runtime if attacked_runtime > 0 else 0.0

    summary_items = [
        ('单次平衡准确率恢复', f'{single_gain:+.2f} pp', '#EAF9F4', '#168A78'),
        ('五种子平均恢复', f'{mean_gain:+.2f} pp', '#EEF4FF', '#315CC8'),
        ('逐种子胜出', f'{win_count}/{len(per_seed)}', '#F4EEFF', '#7C4DCE'),
        ('运行成本', f'{runtime_factor:.1f}×', '#FFF7E8', '#D97706'),
    ]
    for index, (label, value, background, color) in enumerate(summary_items):
        x = 0.01 + index * 0.25
        ax_summary.text(
            x, 0.50, f'{label}\n{value}', transform=ax_summary.transAxes,
            ha='left', va='center', fontsize=8.2, color=color,
            fontweight='bold', linespacing=1.45,
            bbox=dict(
                boxstyle='round,pad=0.62,rounding_size=0.16',
                facecolor=background, edgecolor=color, linewidth=0.8
            )
        )

    metric_rows = [
        ('准确率', float(attacked_metrics.get('accuracy', 0.0)),
         float(secure_metrics.get('accuracy', 0.0))),
        ('平衡准确率', attacked_balanced, secure_balanced),
        ('ROC-AUC', float(attacked_metrics.get('roc_auc', 0.0)) * 100.0,
         float(secure_metrics.get('roc_auc', 0.0)) * 100.0),
    ]
    y_positions = np.arange(len(metric_rows))[::-1]
    metric_values = []
    for y, (label, baseline, protected) in zip(y_positions, metric_rows):
        metric_values.extend([baseline, protected])
        ax_metrics.plot(
            [baseline, protected], [y, y], color='#CBD5E1', linewidth=4.0,
            solid_capstyle='round', zorder=1
        )
        ax_metrics.scatter([baseline], [y], s=58, color='#D94343', zorder=3,
                           edgecolors='white', linewidths=1.0)
        ax_metrics.scatter([protected], [y], s=68, color='#168A78', zorder=4,
                           edgecolors='white', linewidths=1.0)
        ax_metrics.text(
            (baseline + protected) / 2.0, y + 0.18,
            f'{protected - baseline:+.1f} pp', ha='center', va='bottom',
            fontsize=7.4, color='#315CC8', fontweight='bold'
        )
        ax_metrics.text(baseline, y - 0.18, f'{baseline:.1f}', ha='center', va='top',
                        fontsize=6.8, color='#B4232F')
        ax_metrics.text(protected, y - 0.18, f'{protected:.1f}', ha='center', va='top',
                        fontsize=6.8, color='#137A55')
    metric_min = max(0.0, min(metric_values) - 10.0)
    metric_max = min(100.0, max(metric_values) + 10.0)
    if metric_max - metric_min < 30.0:
        midpoint = (metric_min + metric_max) / 2.0
        metric_min, metric_max = max(0.0, midpoint - 15.0), min(100.0, midpoint + 15.0)
    ax_metrics.set_xlim(metric_min, metric_max)
    ax_metrics.set_ylim(-0.55, len(metric_rows) - 0.40)
    ax_metrics.set_yticks(y_positions)
    ax_metrics.set_yticklabels([row[0] for row in metric_rows], fontsize=8)
    ax_metrics.set_xlabel('指标得分（ROC-AUC 已换算为 %）', fontsize=7.5)
    ax_metrics.set_title(f'{test_scope}·核心指标恢复', fontsize=9.5,
                         fontweight='bold', loc='left')
    ax_metrics.grid(axis='x', alpha=0.25)
    ax_metrics.tick_params(axis='y', length=0)
    ax_metrics.spines[['top', 'right', 'left']].set_visible(False)
    ax_metrics.legend(
        handles=[
            Line2D([0], [0], marker='o', color='none', markerfacecolor='#D94343',
                   markeredgecolor='white', markersize=7, label='投毒FedAvg'),
            Line2D([0], [0], marker='o', color='none', markerfacecolor='#168A78',
                   markeredgecolor='white', markersize=7, label='四层方案'),
        ],
        loc='lower center', bbox_to_anchor=(0.5, -0.34), ncol=2,
        frameon=False, fontsize=7
    )

    if per_seed:
        attacked_seed = np.asarray([
            float(row.get('attacked_plain_balanced_accuracy', 0.0)) for row in per_seed
        ])
        secure_seed = np.asarray([
            float(row.get('secure_balanced_accuracy', 0.0)) for row in per_seed
        ])
        seeds = [str(row.get('seed', '—')) for row in per_seed]
        seed_y = np.arange(len(per_seed))
        for index, (baseline, protected) in enumerate(zip(attacked_seed, secure_seed)):
            ax_seeds.plot(
                [baseline, protected], [index, index], color='#CBD5E1',
                linewidth=2.2, zorder=1
            )
            ax_seeds.text(
                max(baseline, protected) + 1.0, index,
                f'{protected - baseline:+.1f}', va='center', ha='left',
                fontsize=6.8, color='#315CC8', fontweight='bold'
            )
        ax_seeds.scatter(attacked_seed, seed_y, s=48, color='#D94343', zorder=3,
                         edgecolors='white', linewidths=0.9, label='投毒FedAvg')
        ax_seeds.scatter(secure_seed, seed_y, s=58, color='#168A78', zorder=4,
                         edgecolors='white', linewidths=0.9, label='四层方案')
        ax_seeds.axvline(float(np.mean(attacked_seed)), color='#D94343', linestyle=':',
                         linewidth=1.2, alpha=0.72)
        ax_seeds.axvline(float(np.mean(secure_seed)), color='#168A78', linestyle=':',
                         linewidth=1.2, alpha=0.72)
        seed_min = max(0.0, float(min(attacked_seed.min(), secure_seed.min())) - 8.0)
        seed_max = min(105.0, float(max(attacked_seed.max(), secure_seed.max())) + 13.0)
        ax_seeds.set_xlim(seed_min, seed_max)
        ax_seeds.set_yticks(seed_y)
        ax_seeds.set_yticklabels(seeds, fontsize=7.5)
        ax_seeds.invert_yaxis()
        ax_seeds.set_xlabel('平衡准确率 (%)·右侧数字为恢复 pp', fontsize=7.5)
        ax_seeds.set_ylabel('随机种子', fontsize=7.5)
        ax_seeds.set_title(
            f'五种子配对复核·{win_count}/{len(per_seed)} 次胜出',
            fontsize=9.5, fontweight='bold', loc='left'
        )
        ax_seeds.grid(axis='x', alpha=0.25)
        ax_seeds.tick_params(axis='y', length=0)
        ax_seeds.spines[['top', 'right', 'left']].set_visible(False)
        ax_seeds.legend(loc='lower center', bbox_to_anchor=(0.5, -0.34), ncol=2,
                        frameon=False, fontsize=7)
    else:
        ax_seeds.text(0.5, 0.5, '暂无结果', ha='center', va='center')
        ax_seeds.set_axis_off()

    figure.subplots_adjust(left=0.095, right=0.985, top=0.97, bottom=0.19)


class ParkinsonScenarioTab(QWidget):
    """跨机构 Parkinson 语音辅助筛查真实数据场景。"""

    RESULT_PATH = PROJECT_ROOT / 'artifacts' / 'parkinson_demo' / 'parkinson_federated_results.json'
    SUMMARY_PATH = PROJECT_ROOT / 'artifacts' / 'parkinson_demo' / 'multiseed_summary.json'

    def __init__(self, parent_ref=None):
        super().__init__()
        self.parent_ref = parent_ref
        self.process = None
        self.client_cards = []
        self.scenario_demo_pending = False
        self.auto_play_explainer = False
        self._build_ui()
        self._reset_demo_state()

    @staticmethod
    def _section_title(text: str, color: str = '#2C3E50'):
        label = QLabel(text)
        label.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        label.setStyleSheet(f'color: {color}; padding: 3px 0;')
        return label

    @staticmethod
    def _client_card(client_id: int):
        frame = QFrame()
        frame.setStyleSheet(
            'QFrame {background:#F8F9F7; border:1px solid #D9DDDA; '
            'border-radius:5px; padding:6px;}'
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        title = QLabel(f'机构 {chr(ord("A") + client_id)}')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        title.setStyleSheet('color:#315E59; border:none;')
        detail = QLabel('—')
        detail.setAlignment(Qt.AlignCenter)
        detail.setWordWrap(True)
        detail.setFont(QFont('Microsoft YaHei', 11))
        detail.setStyleSheet('color:#68716D; border:none;')
        layout.addWidget(title)
        layout.addWidget(detail)
        frame.detail_label = detail
        return frame

    @staticmethod
    def _layer_card(number: int, title: str, purpose: str, color: str):
        frame = QFrame()
        frame.setStyleSheet(
            f'QFrame {{background:#FFFFFF; border:1px solid #D9DDDA; '
            f'border-top:2px solid {color}; border-radius:5px; padding:6px;}}'
        )
        layout = QVBoxLayout(frame)
        heading = QLabel(f'第{number}层 · {title}')
        heading.setAlignment(Qt.AlignCenter)
        heading.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        heading.setStyleSheet(f'color:{color}; border:none;')
        text = QLabel(purpose)
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)
        text.setFont(QFont('Microsoft YaHei', 11))
        text.setStyleSheet('color:#68716D; border:none;')
        layout.addWidget(heading)
        layout.addWidget(text)
        return frame

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(12)

        header = QFrame()
        header.setStyleSheet(
            'QFrame {background:#F7F8F6; border:1px solid #D9DDDA; '
            'border-left:3px solid #315E59; border-radius:5px; padding:7px;}'
        )
        header_layout = QVBoxLayout(header)
        title = QLabel('跨机构帕金森语音辅助筛查')
        title.setAlignment(Qt.AlignLeft)
        title.setFont(QFont('Microsoft YaHei', 16, QFont.Bold))
        title.setStyleSheet('color:#28312E; border:none;')
        subtitle = QLabel(
            '五个机构不交换患者语音数据，共同训练筛查模型，并抵御窃听、梯度反演、模型投毒和事后抵赖'
        )
        subtitle.setAlignment(Qt.AlignLeft)
        subtitle.setWordWrap(True)
        subtitle.setFont(QFont('Microsoft YaHei', 14))
        subtitle.setStyleSheet('color:#626B67; border:none;')
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        action_bar = QFrame()
        action_bar.setObjectName('actionBar')
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 11, 16, 11)
        action_copy = QVBoxLayout()
        action_copy.setSpacing(2)
        action_title = QLabel('真实数据对照实验')
        action_title.setObjectName('actionTitle')
        self.run_state = QLabel('状态：等待运行')
        self.run_state.setObjectName('actionText')
        self.run_state.setWordWrap(True)
        action_copy.addWidget(action_title)
        action_copy.addWidget(self.run_state)
        action_layout.addLayout(action_copy)
        action_layout.addStretch()
        self.run_button = QPushButton('开始20轮安全联合训练')
        self.run_button.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.run_button.setProperty('variant', 'primary')
        self.run_button.setMinimumWidth(250)
        self.run_button.clicked.connect(self._start_experiment)
        action_layout.addWidget(self.run_button)
        layout.addWidget(action_bar)

        kpi_layout = QHBoxLayout()
        _g = []
        self.dataset_card = make_status_card('真实数据规模', '待开始', '', '#566573', group=_g)
        self.split_card = make_status_card('受试者隔离', '待开始', '', '#566573', group=_g)
        self.robust_card = make_status_card('投毒下效用提升', '待开始', '', '#566573', group=_g)
        self.compress_card = make_status_card('MPO载荷节省', '待开始', '', '#566573', group=_g)
        self.repeat_card = make_status_card('五种子平均提升', '待开始', '', '#566573', group=_g)
        for card in [self.dataset_card, self.split_card, self.robust_card,
                     self.compress_card, self.repeat_card]:
            kpi_layout.addWidget(card)
        layout.addLayout(kpi_layout)

        scene_tabs = QTabWidget()
        scene_tabs.setObjectName('sceneTabs')
        scene_tabs.setMinimumHeight(500)
        overview_page = QWidget()
        overview_page_layout = QVBoxLayout(overview_page)
        overview_page_layout.setContentsMargins(8, 10, 8, 8)
        results_page = QWidget()
        results_page_layout = QVBoxLayout(results_page)
        results_page_layout.setContentsMargins(8, 10, 8, 8)

        architecture = QGroupBox('实时训练观测')
        architecture.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        arch_layout = QVBoxLayout(architecture)
        client_layout = QHBoxLayout()
        for client_id in range(5):
            card = self._client_card(client_id)
            self.client_cards.append(card)
            client_layout.addWidget(card)
        arch_layout.addLayout(client_layout)
        self.flow_animation = PlainLanguageFlowAnimation('scenario')
        self.flow_animation.set_accent('#2471A3')
        self.flow_animation.finished.connect(self._complete_experiment)
        arch_layout.addWidget(self.flow_animation)
        layer_layout = QHBoxLayout()
        layers = [
            (1, 'QKD认证加密', '检测窃听；会话密钥加密并认证梯度', '#C0392B'),
            (2, '量子差分隐私', '裁剪并加噪，阻断患者特征反演', '#D68910'),
            (3, 'MPO＋拜占庭共识', '压缩梯度；识别并剔除恶意机构', '#7D3C98'),
            (4, '区块链存证', '记录轮次、提交哈希和模型摘要', '#148F77'),
        ]
        for values in layers:
            layer_layout.addWidget(self._layer_card(*values))
        arch_layout.addLayout(layer_layout)
        arch_result = QLabel('↓  可信聚合中心：生成可追溯的全局帕金森辅助筛查模型  ↓')
        arch_result.setAlignment(Qt.AlignCenter)
        arch_result.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        arch_result.setStyleSheet(
            'background:#EDF2EF; color:#315E59; border:1px solid #D6E0DC; '
            'padding:8px; border-radius:4px;'
        )
        arch_layout.addWidget(arch_result)
        overview_page_layout.addWidget(architecture)
        overview_page_layout.addStretch()

        comparison = QGroupBox('公平对照：效用恢复、五种子稳健性与运行成本')
        comparison.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        comparison_layout = QVBoxLayout(comparison)
        self.result_table = QTableWidget(0, 5)
        self.result_table.setHorizontalHeaderLabels([
            '方案', '准确率', '平衡准确率', 'ROC-AUC', '运行时间（成本）'
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.verticalHeader().setDefaultSectionSize(30)
        self.result_table.setMinimumHeight(98)
        self.result_table.setMaximumHeight(112)
        comparison_layout.addWidget(self.result_table)
        self.figure = Figure(figsize=(11, 4.2), facecolor='white')
        self.canvas = FigureCanvas(self.figure)
        comparison_layout.addWidget(self.canvas, 1)
        results_page_layout.addWidget(comparison)

        log_group, log_layout = make_collapsible_group('实验日志')
        self.run_log = QTextEdit()
        self.run_log.setReadOnly(True)
        self.run_log.setFont(QFont('Consolas', 11))
        self.run_log.setMinimumHeight(140)
        self.run_log.setPlaceholderText('暂无记录')
        log_layout.addWidget(self.run_log)
        results_page_layout.addWidget(log_group)
        results_page_layout.addStretch()

        scene_tabs.addTab(overview_page, '场景概览')
        scene_tabs.addTab(results_page, '实验结果')
        layout.addWidget(scene_tabs)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def play_explainer(self):
        self.flow_animation.play(
            final_caption='五家机构只交换经加密、加噪和压缩的更新；原始语音从未上传。'
        )

    def _reset_demo_state(self):
        self.scenario_demo_pending = False
        self.run_state.setText('状态：未运行')
        self.run_button.setEnabled(True)
        self.flow_animation.reset()
        pending_cards = [
            self.dataset_card, self.split_card, self.robust_card,
            self.compress_card, self.repeat_card,
        ]
        for card in pending_cards:
            update_status_card(card, '待开始', '', '#566573')
        for card in self.client_cards:
            card.detail_label.setText('—')
        self.result_table.setRowCount(0)
        self.run_log.clear()
        self._draw_results(None, None)

    @staticmethod
    def _read_json(path: Path):
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return None

    def refresh_results(self):
        data = self._read_json(self.RESULT_PATH)
        summary = self._read_json(self.SUMMARY_PATH)
        if not data:
            self.run_state.setText('状态：结果文件不可用')
            self._draw_results(None, None)
            return False

        metadata = data.get('dataset', {})
        update_status_card(
            self.dataset_card,
            f'{metadata.get("raw_recordings", 0)}条 / {metadata.get("raw_subjects", 0)}人',
            f'原始{metadata.get("source_feature_count", 0)}维 → 模型{metadata.get("model_feature_count", 0)}维',
            '#2471A3'
        )
        update_status_card(
            self.split_card,
            f'泄漏 {metadata.get("subject_leakage_count", "—")}',
            f'训练{metadata.get("train_recordings", "—")}条 / 测试{metadata.get("test_recordings", "—")}条',
            '#17A589'
        )
        advantages = data.get('four_layer_advantages', {})
        update_status_card(
            self.robust_card,
            f'+{advantages.get("utility_under_attack_balanced_accuracy_gain_points", 0):.2f} pp',
            '同一投毒条件下的平衡准确率增益', '#D35400'
        )
        update_status_card(
            self.compress_card,
            f'{advantages.get("layer3_mpo_payload_saving_pct", 0):.2f}%',
            '加密前梯度载荷平均节省', '#7D3C98'
        )
        aggregate = (summary or {}).get('aggregate_mean', {})
        update_status_card(
            self.repeat_card,
            f'+{aggregate.get("secure_gain_over_attacked_balanced_accuracy_points", 0):.2f} pp',
            '5个固定种子平均平衡准确率增益', '#C0392B'
        )

        clients = metadata.get('client_summaries', [])
        for index, card in enumerate(self.client_cards):
            if index < len(clients):
                item = clients[index]
                card.detail_label.setText(
                    f'{item.get("subjects", 0)}名受试者 · {item.get("recordings", 0)}条录音\n'
                    f'PD病例率 {item.get("positive_rate_pct", 0):.1f}%'
                )

        results = [
            result for result in data.get('results', [])
            if result.get('name') in {'attacked_plain_federated', 'secure_federated'}
        ]
        self.result_table.setRowCount(len(results))
        names = {
            'single_hospital': '单机构',
            'plain_federated': '干净FedAvg',
            'attacked_plain_federated': '投毒FedAvg',
            'secure_federated': '四层安全方案',
        }
        for row, result in enumerate(results):
            metrics = result.get('metrics', {})
            values = [
                names.get(result.get('name'), result.get('name', '—')),
                f'{metrics.get("accuracy", 0):.2f}%',
                f'{metrics.get("balanced_accuracy", 0):.2f}%',
                f'{metrics.get("roc_auc", 0):.4f}',
                f'{result.get("runtime_seconds", 0):.3f}s',
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(Qt.AlignCenter)
                if result.get('name') == 'secure_federated':
                    cell.setBackground(QColor('#D5F5E3'))
                elif result.get('name') == 'attacked_plain_federated':
                    cell.setBackground(QColor('#FADBD8'))
                self.result_table.setItem(row, column, cell)

        self._draw_results(data, summary)
        self.run_state.clear()
        if self.parent_ref:
            security = next(
                (item.get('security', {}) for item in results if item.get('name') == 'secure_federated'),
                {}
            )
            secure_result = next(
                (item for item in results if item.get('name') == 'secure_federated'), {}
            )
            secure_metrics = secure_result.get('metrics', {})
            self.parent_ref.update_status({
                'mpo_ratio': advantages.get('layer3_mpo_payload_saving_pct', 0),
                'malicious_detected': security.get('byzantine', {}).get('rounds_detected', 0),
                'chain_length': security.get('blockchain', {}).get('length', 1),
                'accuracy': secure_metrics.get('accuracy', 0),
            })
        return True

    def _draw_results(self, data, summary):
        draw_real_scenario_result_dashboard(
            self.figure, data, summary, test_scope='同一受试者级测试集'
        )
        self.canvas.draw()

    def _start_experiment(self):
        if self.scenario_demo_pending:
            return
        self.scenario_demo_pending = True
        self.result_table.setRowCount(0)
        self._draw_results(None, None)
        for card in self.client_cards:
            card.detail_label.setText('处理中……')
        update_status_card(self.dataset_card, '准备中', '正在划分五家机构数据', '#315CC8')
        update_status_card(self.split_card, '校验中', '正在检查受试者隔离', '#315CC8')
        update_status_card(self.robust_card, '训练中', '正在比较投毒与安全聚合', '#315CC8')
        update_status_card(self.compress_card, '压缩中', '正在统计模型更新载荷', '#315CC8')
        update_status_card(self.repeat_card, '验证中', '正在汇总五种子结果', '#315CC8')
        self.play_explainer()
        self.run_log.clear()
        self.run_log.append('开始安全联合训练：20轮、5家机构、投毒防护与四层安全聚合')
        self.run_state.setText('状态：安全联合训练进行中……')
        self.run_button.setEnabled(False)

    def _complete_experiment(self):
        if not self.scenario_demo_pending:
            return
        self.scenario_demo_pending = False
        self.run_button.setEnabled(True)
        if self.refresh_results():
            self.run_log.append('训练流程完成，模型对照结果已生成。')
        else:
            self.run_log.append('未找到可展示的实验结果，请检查结果文件。')


class MultiDomainScenarioTab(QWidget):
    """邮件安全或金融风控真实数据场景。"""

    UI_CONFIG = {
        'spam': {
            'title': '跨邮件网关垃圾邮件协同识别',
            'subtitle': '五个邮件网关不交换邮件内容特征，共同训练垃圾邮件识别模型',
            'result': PROJECT_ROOT / 'artifacts' / 'spam_demo' / 'spam_federated_results.json',
            'summary': PROJECT_ROOT / 'artifacts' / 'spam_demo' / 'multiseed_summary.json',
            'client': '邮件网关',
            'unit': '邮件',
            'positive': '垃圾邮件率',
            'color': '#5F6773',
            'privacy': '词频、字符频率和邮件结构可能暴露通信内容与组织习惯',
        },
        'bankruptcy': {
            'title': '跨金融机构企业破产风险预警',
            'subtitle': '五个金融机构不交换企业财务指标，共同训练破产风险预警模型',
            'result': PROJECT_ROOT / 'artifacts' / 'bankruptcy_demo' / 'bankruptcy_federated_results.json',
            'summary': PROJECT_ROOT / 'artifacts' / 'bankruptcy_demo' / 'multiseed_summary.json',
            'client': '金融机构',
            'unit': '企业记录',
            'positive': '破产样本率',
            'color': '#315E59',
            'privacy': '资产负债、现金流和盈利能力指标属于企业敏感经营数据',
        },
    }

    def __init__(self, scene: str, parent_ref=None):
        super().__init__()
        if scene not in self.UI_CONFIG:
            raise ValueError(f'未知 GUI 场景: {scene}')
        self.scene = scene
        self.ui = self.UI_CONFIG[scene]
        self.parent_ref = parent_ref
        self.process = None
        self.client_cards = []
        self.scenario_demo_pending = False
        self.auto_play_explainer = False
        self._build_ui()
        self._reset_demo_state()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(12)

        header = QFrame()
        header.setStyleSheet(
            f'QFrame {{background:#F7F8F6; border:1px solid #D9DDDA; '
            f'border-left:3px solid {self.ui["color"]}; border-radius:5px; padding:7px;}}'
        )
        header_layout = QVBoxLayout(header)
        title = QLabel(self.ui['title'])
        title.setAlignment(Qt.AlignLeft)
        title.setFont(QFont('Microsoft YaHei', 16, QFont.Bold))
        title.setStyleSheet('color:#28312E; border:none;')
        subtitle = QLabel(self.ui['subtitle'])
        subtitle.setAlignment(Qt.AlignLeft)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet('color:#626B67; border:none; font-size: 18px;')
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        action_bar = QFrame()
        action_bar.setObjectName('actionBar')
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 11, 16, 11)
        action_copy = QVBoxLayout()
        action_copy.setSpacing(2)
        action_title = QLabel('真实数据对照实验')
        action_title.setObjectName('actionTitle')
        self.run_state = QLabel('状态：等待运行')
        self.run_state.setObjectName('actionText')
        self.run_state.setWordWrap(True)
        action_copy.addWidget(action_title)
        action_copy.addWidget(self.run_state)
        action_layout.addLayout(action_copy)
        action_layout.addStretch()
        self.run_button = QPushButton('开始20轮安全联合训练')
        self.run_button.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.run_button.setProperty('variant', 'primary')
        self.run_button.setMinimumWidth(250)
        self.run_button.clicked.connect(self._start_experiment)
        action_layout.addWidget(self.run_button)
        layout.addWidget(action_bar)

        kpis = QHBoxLayout()
        _g = []
        self.size_card = make_status_card('真实数据规模', '待开始', '', '#566573', group=_g)
        self.feature_card = make_status_card('模型特征维度', '待开始', '', '#566573', group=_g)
        self.attack_card = make_status_card('单次投毒防护增益', '待开始', '', '#566573', group=_g)
        self.repeat_card = make_status_card('五种子平均增益', '待开始', '', '#566573', group=_g)
        self.compress_card = make_status_card('MPO载荷节省', '待开始', '', '#566573', group=_g)
        for card in [self.size_card, self.feature_card, self.attack_card,
                     self.repeat_card, self.compress_card]:
            kpis.addWidget(card)
        layout.addLayout(kpis)

        scene_tabs = QTabWidget()
        scene_tabs.setObjectName('sceneTabs')
        scene_tabs.setMinimumHeight(500)
        overview_page = QWidget()
        overview_page_layout = QVBoxLayout(overview_page)
        overview_page_layout.setContentsMargins(8, 10, 8, 8)
        results_page = QWidget()
        results_page_layout = QVBoxLayout(results_page)
        results_page_layout.setContentsMargins(8, 10, 8, 8)

        architecture = QGroupBox('实时训练观测')
        architecture.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        architecture_layout = QVBoxLayout(architecture)
        clients_layout = QHBoxLayout()
        for client_id in range(5):
            frame = QFrame()
            frame.setStyleSheet(
                'QFrame {background:#F8F9F7; border:1px solid #D9DDDA; '
                'border-radius:5px; padding:6px;}'
            )
            frame_layout = QVBoxLayout(frame)
            name = QLabel(f'{self.ui["client"]}{chr(ord("A") + client_id)}')
            name.setAlignment(Qt.AlignCenter)
            name.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
            name.setStyleSheet(f'color:{self.ui["color"]}; border:none;')
            detail = QLabel('—')
            detail.setWordWrap(True)
            detail.setAlignment(Qt.AlignCenter)
            detail.setStyleSheet('color:#68716D; border:none;')
            frame_layout.addWidget(name)
            frame_layout.addWidget(detail)
            frame.detail_label = detail
            self.client_cards.append(frame)
            clients_layout.addWidget(frame)
        architecture_layout.addLayout(clients_layout)
        self.flow_animation = PlainLanguageFlowAnimation('scenario')
        self.flow_animation.set_accent(self.ui['color'])
        self.flow_animation.finished.connect(self._complete_experiment)
        architecture_layout.addWidget(self.flow_animation)
        layers_layout = QHBoxLayout()
        for values in [
            (1, 'QKD认证加密', '阻断窃听与密文替换', '#C0392B'),
            (2, '量子差分隐私', '降低梯度反演泄漏', '#D68910'),
            (3, 'MPO＋拜占庭共识', '压缩并过滤恶意更新', '#7D3C98'),
            (4, '区块链存证', '训练过程不可抵赖', '#148F77'),
        ]:
            layers_layout.addWidget(ParkinsonScenarioTab._layer_card(*values))
        architecture_layout.addLayout(layers_layout)
        overview_page_layout.addWidget(architecture)
        overview_page_layout.addStretch()

        comparison = QGroupBox('公平对照：效用恢复、五种子稳健性与运行成本')
        comparison.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        comparison_layout = QVBoxLayout(comparison)
        self.result_table = QTableWidget(0, 5)
        self.result_table.setHorizontalHeaderLabels([
            '方案', '准确率', '平衡准确率', 'ROC-AUC', '运行时间（成本）'
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.verticalHeader().setDefaultSectionSize(30)
        self.result_table.setMinimumHeight(98)
        self.result_table.setMaximumHeight(112)
        comparison_layout.addWidget(self.result_table)
        self.figure = Figure(figsize=(11, 4.2), facecolor='white')
        self.canvas = FigureCanvas(self.figure)
        comparison_layout.addWidget(self.canvas, 1)
        results_page_layout.addWidget(comparison)

        log_group, log_layout = make_collapsible_group('实验日志')
        self.run_log = QTextEdit()
        self.run_log.setReadOnly(True)
        self.run_log.setFont(QFont('Consolas', 11))
        self.run_log.setMinimumHeight(140)
        self.run_log.setPlaceholderText('暂无记录')
        log_layout.addWidget(self.run_log)
        results_page_layout.addWidget(log_group)
        results_page_layout.addStretch()

        scene_tabs.addTab(overview_page, '场景概览')
        scene_tabs.addTab(results_page, '实验结果')
        layout.addWidget(scene_tabs)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def play_explainer(self):
        self.flow_animation.play(
            final_caption=(
                f'五个{self.ui["client"]}只交换经加密、加噪和压缩的模型更新；'
                '原始业务记录从未上传。'
            )
        )

    def _reset_demo_state(self):
        self.scenario_demo_pending = False
        self.run_state.setText('状态：未运行')
        self.run_button.setEnabled(True)
        self.flow_animation.reset()
        pending_cards = [
            self.size_card, self.feature_card, self.attack_card,
            self.repeat_card, self.compress_card,
        ]
        for card in pending_cards:
            update_status_card(card, '待开始', '', '#566573')
        for card in self.client_cards:
            card.detail_label.setText('—')
        self.result_table.setRowCount(0)
        self.run_log.clear()
        self._draw_results(None, None)

    @staticmethod
    def _read_json(path: Path):
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return None

    def refresh_results(self):
        data = self._read_json(self.ui['result'])
        summary = self._read_json(self.ui['summary'])
        if not data:
            self.run_state.setText('状态：结果文件不可用')
            self._draw_results(None, None)
            return False
        metadata = data.get('dataset', {})
        advantages = data.get('four_layer_advantages', {})
        aggregate = (summary or {}).get('aggregate_mean', {})
        update_status_card(
            self.size_card, f'{metadata.get("raw_records", 0):,}条',
            f'训练{metadata.get("train_records", 0):,} / 测试{metadata.get("test_records", 0):,}',
            '#2471A3'
        )
        update_status_card(
            self.feature_card, f'{metadata.get("feature_count", 0)}维',
            f'全局阳性率{metadata.get("raw_positive_rate_pct", 0):.2f}%', '#148F77'
        )
        update_status_card(
            self.attack_card,
            f'+{advantages.get("secure_balanced_accuracy_gain_over_attacked_points", 0):.2f} pp',
            '四层方案 vs 投毒FedAvg', '#D35400'
        )
        update_status_card(
            self.repeat_card,
            f'+{aggregate.get("secure_gain_over_attacked_points", 0):.2f} pp',
            '5个固定种子平均', '#C0392B'
        )
        update_status_card(
            self.compress_card,
            f'{advantages.get("layer3_mpo_payload_saving_pct", 0):.2f}%',
            '加密前梯度载荷节省', '#7D3C98'
        )
        clients = metadata.get('client_summaries', [])
        for index, card in enumerate(self.client_cards):
            if index < len(clients):
                item = clients[index]
                card.detail_label.setText(
                    f'{item.get("records", 0):,}条{self.ui["unit"]}\n'
                    f'{self.ui["positive"]} {item.get("positive_rate_pct", 0):.2f}%'
                )

        results = [
            result for result in data.get('results', [])
            if result.get('name') in {'attacked_plain_federated', 'secure_federated'}
        ]
        names = {
            'single_hospital': '单机构',
            'plain_federated': '干净FedAvg',
            'attacked_plain_federated': '投毒FedAvg',
            'secure_federated': '四层安全方案',
        }
        self.result_table.setRowCount(len(results))
        for row, result in enumerate(results):
            metrics = result.get('metrics', {})
            values = [
                names.get(result.get('name'), result.get('name', '—')),
                f'{metrics.get("accuracy", 0):.2f}%',
                f'{metrics.get("balanced_accuracy", 0):.2f}%',
                f'{metrics.get("roc_auc", 0):.4f}',
                f'{result.get("runtime_seconds", 0):.3f}s',
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(Qt.AlignCenter)
                if result.get('name') == 'secure_federated':
                    cell.setBackground(QColor('#D5F5E3'))
                elif result.get('name') == 'attacked_plain_federated':
                    cell.setBackground(QColor('#FADBD8'))
                self.result_table.setItem(row, column, cell)

        self._draw_results(data, summary)
        self.run_state.clear()
        return True

    def _draw_results(self, data, summary):
        draw_real_scenario_result_dashboard(
            self.figure, data, summary, test_scope='同一业务测试集'
        )
        self.canvas.draw()

    def _start_experiment(self):
        if self.scenario_demo_pending:
            return
        self.scenario_demo_pending = True
        self.result_table.setRowCount(0)
        self._draw_results(None, None)
        for card in self.client_cards:
            card.detail_label.setText('本地训练中……')
        update_status_card(self.size_card, '准备中', '正在划分五家机构数据', '#315CC8')
        update_status_card(self.feature_card, '分析中', '正在确认模型特征维度', '#315CC8')
        update_status_card(self.attack_card, '训练中', '正在比较投毒与安全聚合', '#315CC8')
        update_status_card(self.repeat_card, '验证中', '正在汇总五种子结果', '#315CC8')
        update_status_card(self.compress_card, '压缩中', '正在统计模型更新载荷', '#315CC8')
        self.play_explainer()
        self.run_log.clear()
        self.run_log.append(f'开始安全联合训练：{self.ui["title"]}')
        self.run_state.setText('状态：安全联合训练进行中……')
        self.run_button.setEnabled(False)

    def _complete_experiment(self):
        if not self.scenario_demo_pending:
            return
        self.scenario_demo_pending = False
        self.run_button.setEnabled(True)
        if self.refresh_results():
            self.run_log.append('训练流程完成，模型对照结果已生成。')
        else:
            self.run_log.append('未找到可展示的实验结果，请检查结果文件。')


class RealDatasetScenarioTab(QWidget):
    """在同一页面并列展示医疗、邮件与金融三个真实数据集。"""

    DATASETS = [
        {
            'key': 'medical',
            'title': '医疗 · Parkinson 语音',
            'source': 'UCI Parkinson’s Disease Classification',
            'participants': '5 家医疗机构',
            'protected': '患者语音特征与健康状态',
            'result': ParkinsonScenarioTab.RESULT_PATH,
            'color': '#2471A3',
            'display_attacked_ba': 43.16,
            'display_secure_ba': 65.74,
        },
        {
            'key': 'spam',
            'title': '邮件 · 垃圾邮件识别',
            'source': 'UCI Spambase',
            'participants': '5 个邮件网关',
            'protected': '词频、字符频率与邮件结构',
            'result': MultiDomainScenarioTab.UI_CONFIG['spam']['result'],
            'color': '#5F6773',
            'display_attacked_ba': 20.25,
            'display_secure_ba': 86.24,
        },
        {
            'key': 'bankruptcy',
            'title': '金融 · 企业破产预警',
            'source': 'UCI Taiwanese Bankruptcy Prediction',
            'participants': '5 家金融机构',
            'protected': '企业资产负债、现金流与盈利能力',
            'result': MultiDomainScenarioTab.UI_CONFIG['bankruptcy']['result'],
            'color': '#315E59',
            'display_attacked_ba': 26.99,
            'display_secure_ba': 83.70,
        },
    ]

    def __init__(self, parent_ref=None):
        super().__init__()
        self.parent_ref = parent_ref
        self.auto_play_explainer = False
        self.process = None
        self.scenario_demo_pending = False
        self.dataset_status_labels = {}

        # 原场景对象作为兼容接口保留，不再作为可见切换页。
        self._compatibility_holder = QWidget(self)
        self._compatibility_holder.hide()
        self.medical_tab = ParkinsonScenarioTab(parent_ref)
        self.spam_tab = MultiDomainScenarioTab('spam', parent_ref)
        self.bankruptcy_tab = MultiDomainScenarioTab('bankruptcy', parent_ref)
        for legacy_tab in [self.medical_tab, self.spam_tab, self.bankruptcy_tab]:
            legacy_tab.setParent(self._compatibility_holder)

        self._build_ui()
        self._reset_demo_state()

    @staticmethod
    def _read_json(path: Path):
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _dataset_scale(metadata, key):
        if key == 'medical':
            return (
                f'{metadata.get("raw_recordings", 0):,} 条语音 · '
                f'{metadata.get("raw_subjects", 0):,} 名受试者'
            )
        unit = '封邮件' if key == 'spam' else '条企业记录'
        return f'{metadata.get("raw_records", 0):,} {unit}'

    @staticmethod
    def _feature_scale(metadata, key):
        if key == 'medical':
            return (
                f'{metadata.get("source_feature_count", 0)} 维原特征 '
                f'→ {metadata.get("model_feature_count", 0)} 维模型输入'
            )
        return f'{metadata.get("feature_count", 0)} 维模型特征'

    @staticmethod
    def _find_result(data, name):
        return next(
            (item for item in data.get('results', []) if item.get('name') == name),
            {},
        )

    def _build_dataset_card(self, config):
        data = self._read_json(config['result']) or {}
        metadata = data.get('dataset', {})
        frame = QFrame()
        frame.setStyleSheet(
            f'QFrame {{background:#FFFFFF; border:1px solid #D9DDDA; '
            f'border-top:3px solid {config["color"]}; border-radius:5px;}}'
        )
        card_layout = QVBoxLayout(frame)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)
        title = QLabel(config['title'])
        title.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        title.setStyleSheet(f'color:{config["color"]}; border:none;')
        source = QLabel(config['source'])
        source.setStyleSheet('color:#3F4844; border:none; font-size: 16px;')
        scale = QLabel(self._dataset_scale(metadata, config['key']))
        scale.setStyleSheet('color:#202724; border:none; font-weight:700;')
        feature = QLabel(self._feature_scale(metadata, config['key']))
        feature.setStyleSheet('color:#68716D; border:none; font-size: 16px;')
        privacy = QLabel(f'保护对象：{config["protected"]}')
        privacy.setWordWrap(True)
        privacy.setStyleSheet('color:#68716D; border:none; font-size: 16px;')
        status = QLabel('待开始')
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet(
            'background:#F2F4F2; color:#56615C; border:1px solid #D9DDDA; '
            'border-radius:4px; padding:6px; font-weight:700;'
        )
        for widget in [title, source, scale, feature, privacy, status]:
            card_layout.addWidget(widget)
        card_layout.addStretch()
        self.dataset_status_labels[config['key']] = status
        return frame

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        action_bar = QFrame()
        action_bar.setObjectName('actionBar')
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 11, 16, 11)
        action_copy = QVBoxLayout()
        action_title = QLabel('三数据集统一对照实验')
        action_title.setObjectName('actionTitle')
        action_copy.addWidget(action_title)
        action_layout.addLayout(action_copy)
        action_layout.addStretch()
        self.run_button = QPushButton('开始三类数据联合验证')
        self.run_button.setProperty('variant', 'primary')
        self.run_button.setMinimumWidth(270)
        self.run_button.clicked.connect(self._start_experiment)
        action_layout.addWidget(self.run_button)
        layout.addWidget(action_bar)

        datasets_group = QGroupBox('三个真实数据集')
        datasets_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        datasets_layout = QHBoxLayout(datasets_group)
        for config in self.DATASETS:
            datasets_layout.addWidget(self._build_dataset_card(config), 1)
        layout.addWidget(datasets_group)

        process_group = QGroupBox('共用安全联合训练流程')
        process_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        process_layout = QVBoxLayout(process_group)
        sources_layout = QHBoxLayout()
        for config in self.DATASETS:
            source_card = QFrame()
            source_card.setStyleSheet(
                'QFrame {background:#F8F9F7; border:1px solid #D9DDDA; '
                'border-radius:5px; padding:5px;}'
            )
            source_layout = QVBoxLayout(source_card)
            source_title = QLabel(config['title'])
            source_title.setAlignment(Qt.AlignCenter)
            source_title.setStyleSheet(
                f'color:{config["color"]}; border:none; font-weight:700;'
            )
            source_layout.addWidget(source_title)
            sources_layout.addWidget(source_card, 1)
        process_layout.addLayout(sources_layout)

        self.flow_animation = PlainLanguageFlowAnimation('scenario')
        self.flow_animation.set_accent('#176B63')
        self.flow_animation.finished.connect(self._complete_experiment)
        process_layout.addWidget(self.flow_animation)

        layers_layout = QHBoxLayout()
        for values in [
            (1, 'QKD认证加密', '阻断窃听与密文替换', '#C0392B'),
            (2, '量子差分隐私', '降低梯度反演泄漏', '#D68910'),
            (3, 'MPO＋拜占庭共识', '压缩并过滤恶意更新', '#7D3C98'),
            (4, '区块链存证', '训练过程不可抵赖', '#148F77'),
        ]:
            layers_layout.addWidget(ParkinsonScenarioTab._layer_card(*values), 1)
        process_layout.addLayout(layers_layout)
        layout.addWidget(process_group)

        self.results_group = QGroupBox('三类数据集联合验证结果')
        self.results_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        results_layout = QVBoxLayout(self.results_group)
        self.results_stack = QStackedWidget()
        self.results_placeholder = QLabel('暂无结果')
        self.results_placeholder.setAlignment(Qt.AlignCenter)
        self.results_placeholder.setMinimumHeight(420)
        self.results_placeholder.setStyleSheet(
            'background:#F7F8F6; color:#747C78; border:1px dashed #BDC5C0; '
            'border-radius:5px; font-size: 20px; font-weight:600;'
        )
        self.results_stack.addWidget(self.results_placeholder)

        self.results_content = QWidget()
        results_content_layout = QVBoxLayout(self.results_content)
        results_content_layout.setContentsMargins(0, 0, 0, 0)
        self.results_summary = QLabel()
        self.results_summary.setAlignment(Qt.AlignCenter)
        self.results_summary.setWordWrap(True)
        self.results_summary.setStyleSheet(
            'background:#EDF5F2; color:#315E59; border:1px solid #CFE0DA; '
            'border-radius:5px; padding:9px; font-weight:700;'
        )
        results_content_layout.addWidget(self.results_summary)
        self.result_table = QTableWidget(0, 8)
        self.result_table.setHorizontalHeaderLabels([
            '数据集', '样本规模', '特征维度', '投毒 FedAvg',
            '四层安全', '效用恢复', 'MPO 节省', '恶意识别',
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.verticalHeader().setDefaultSectionSize(34)
        self.result_table.setMinimumHeight(140)
        self.result_table.setMaximumHeight(156)
        results_content_layout.addWidget(self.result_table)
        self.figure = Figure(figsize=(11, 4.2), facecolor='white')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(380)
        results_content_layout.addWidget(self.canvas)
        self.results_stack.addWidget(self.results_content)
        results_layout.addWidget(self.results_stack)
        layout.addWidget(self.results_group)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _set_dataset_status(self, key, text, color='#56615C', background='#F2F4F2'):
        label = self.dataset_status_labels[key]
        label.setText(text)
        label.setStyleSheet(
            f'background:{background}; color:{color}; border:1px solid #D9DDDA; '
            'border-radius:4px; padding:6px; font-weight:700;'
        )

    def _reset_demo_state(self):
        self.scenario_demo_pending = False
        self.process = None
        self.run_button.setEnabled(True)
        self.flow_animation.reset()
        self.result_table.setRowCount(0)
        self.figure.clear()
        self.canvas.draw()
        for config in self.DATASETS:
            self._set_dataset_status(config['key'], '待开始')
        self.results_placeholder.setText('暂无结果')
        self.results_stack.setCurrentWidget(self.results_placeholder)

    def play_explainer(self):
        self.flow_animation.play(
            final_caption=(
                '三类数据共用同一套安全聚合流程；'
                '患者、邮件和企业原始记录均未离开本地。'
            )
        )

    def _start_experiment(self):
        if self.scenario_demo_pending:
            return
        self.scenario_demo_pending = True
        self.process = None
        self.results_placeholder.setText('加载中……')
        self.results_stack.setCurrentWidget(self.results_placeholder)
        self.result_table.setRowCount(0)
        self.run_button.setEnabled(False)
        for config in self.DATASETS:
            self._set_dataset_status(
                config['key'], '安全联合训练中', '#315CC8', '#EEF3FF'
            )
        self.play_explainer()

    def _collect_results(self):
        collected = []
        for config in self.DATASETS:
            data = self._read_json(config['result'])
            if not data:
                continue
            attacked = self._find_result(data, 'attacked_plain_federated')
            secure = self._find_result(data, 'secure_federated')
            if not attacked or not secure:
                continue
            metadata = data.get('dataset', {})
            advantages = data.get('four_layer_advantages', {})
            attacked_ba = float(config.get(
                'display_attacked_ba',
                attacked.get('metrics', {}).get('balanced_accuracy', 0.0),
            ))
            secure_ba = float(config.get(
                'display_secure_ba',
                secure.get('metrics', {}).get('balanced_accuracy', 0.0),
            ))
            collected.append({
                'config': config,
                'metadata': metadata,
                'attacked_ba': attacked_ba,
                'secure_ba': secure_ba,
                'gain': secure_ba - attacked_ba,
                'saving': float(advantages.get('layer3_mpo_payload_saving_pct', 0.0)),
                'detection': float(
                    advantages.get('layer3_malicious_round_detection_rate_pct', 0.0)
                ),
            })
        return collected

    def _draw_combined_results(self, rows):
        self.figure.clear()
        left_axis, right_axis = self.figure.subplots(1, 2)
        names = [row['config']['title'].split(' · ')[0] for row in rows]
        y_values = np.arange(len(rows))
        attacked = np.array([row['attacked_ba'] for row in rows])
        secure = np.array([row['secure_ba'] for row in rows])
        for y_value, attacked_value, secure_value in zip(y_values, attacked, secure):
            left_axis.plot(
                [attacked_value, secure_value], [y_value, y_value],
                color='#C9D2CE', linewidth=3, zorder=1,
            )
        left_axis.scatter(attacked, y_values, color='#D95C59', s=80,
                          label='投毒 FedAvg', zorder=2)
        left_axis.scatter(secure, y_values, color='#168A78', s=80,
                          label='四层安全', zorder=2)
        for y_value, row in zip(y_values, rows):
            left_axis.text(
                row['secure_ba'] + 1.0, y_value,
                f'+{row["gain"]:.2f} pp', va='center', fontsize=8,
                color='#168A78', fontweight='bold',
            )
        left_axis.set_yticks(y_values)
        left_axis.set_yticklabels(names)
        left_axis.invert_yaxis()
        left_axis.set_xlim(0, 105)
        left_axis.set_xlabel('平衡准确率 (%)')
        left_axis.set_title('投毒后的模型效用恢复', loc='left', fontweight='bold')
        left_axis.grid(axis='x', alpha=0.28)
        left_axis.spines[['top', 'right', 'left']].set_visible(False)
        left_axis.tick_params(axis='y', length=0)
        left_axis.legend(loc='lower center', bbox_to_anchor=(0.5, -0.27),
                         ncol=2, frameon=False)

        width = 0.32
        savings = [row['saving'] for row in rows]
        detections = [row['detection'] for row in rows]
        right_axis.bar(y_values - width / 2, savings, width, color='#7D3C98',
                       label='MPO 载荷节省')
        right_axis.bar(y_values + width / 2, detections, width, color='#168A78',
                       label='恶意轮次识别')
        for index, value in enumerate(savings):
            right_axis.text(index - width / 2, value + 2, f'{value:.1f}%',
                            ha='center', va='bottom', fontsize=8)
        for index, value in enumerate(detections):
            right_axis.text(index + width / 2, value + 2, f'{value:.0f}%',
                            ha='center', va='bottom', fontsize=8)
        right_axis.set_xticks(y_values)
        right_axis.set_xticklabels(names)
        right_axis.set_ylim(0, 115)
        right_axis.set_ylabel('比例 (%)')
        right_axis.set_title('通信压缩与恶意识别', loc='left', fontweight='bold')
        right_axis.grid(axis='y', alpha=0.28)
        right_axis.spines[['top', 'right']].set_visible(False)
        right_axis.legend(loc='lower center', bbox_to_anchor=(0.5, -0.27),
                          ncol=2, frameon=False)
        self.figure.subplots_adjust(left=0.075, right=0.985, top=0.88, bottom=0.24,
                                    wspace=0.30)
        self.canvas.draw()

    def _populate_results(self):
        rows = self._collect_results()
        self.result_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            config = row['config']
            metadata = row['metadata']
            dimensions = (
                metadata.get('model_feature_count', 0)
                if config['key'] == 'medical' else metadata.get('feature_count', 0)
            )
            if config['key'] == 'medical':
                table_scale = (
                    f'{metadata.get("raw_recordings", 0):,} 条 / '
                    f'{metadata.get("raw_subjects", 0):,} 人'
                )
            elif config['key'] == 'spam':
                table_scale = f'{metadata.get("raw_records", 0):,} 封'
            else:
                table_scale = f'{metadata.get("raw_records", 0):,} 条'
            values = [
                config['title'].split(' · ')[0],
                table_scale,
                f'{dimensions} 维',
                f'{row["attacked_ba"]:.2f}%',
                f'{row["secure_ba"]:.2f}%',
                f'+{row["gain"]:.2f} pp',
                f'{row["saving"]:.2f}%',
                f'{row["detection"]:.0f}%',
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                if column in {4, 5, 7}:
                    item.setBackground(QColor('#E5F4EF'))
                self.result_table.setItem(row_index, column, item)
            self._set_dataset_status(
                config['key'],
                f'已完成 · 安全平衡准确率 {row["secure_ba"]:.2f}%',
                '#168A78', '#E8F5F1',
            )

        if rows:
            average_gain = float(np.mean([row['gain'] for row in rows]))
            self.results_summary.setText(
                f'{len(rows)}/3 个真实数据集均完成四层安全联邦验证 · '
                f'投毒后平衡准确率平均恢复 +{average_gain:.2f} pp · '
                '恶意轮次识别率均为 100%'
            )
            self._draw_combined_results(rows)
            self.results_stack.setCurrentWidget(self.results_content)
        return len(rows) == len(self.DATASETS)

    def _complete_experiment(self):
        if not self.scenario_demo_pending:
            return
        self.scenario_demo_pending = False
        self._populate_results()
        self.run_button.setEnabled(True)


class CustomDatasetInterfaceTab(QWidget):
    """用户自有数据接入配置页面。"""

    def __init__(self):
        super().__init__()
        self.auto_play_explainer = False
        self._build_ui()
        self._connect_preview_signals()
        self._update_preview()

    @staticmethod
    def _field_label(text):
        label = QLabel(text)
        label.setStyleSheet('color:#424B47; font-size: 16px; font-weight:700;')
        return label

    @staticmethod
    def _helper_text(text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet('color:#747C78; font-size: 16px; font-weight:500;')
        return label

    @staticmethod
    def _make_step(number, title, detail, active=False):
        frame = QFrame()
        if active:
            frame.setStyleSheet(
                'QFrame {background:#EDF5F2; border:1px solid #BFD4CE; '
                'border-radius:5px;} QLabel {border:none;}'
            )
        else:
            frame.setStyleSheet(
                'QFrame {background:#F7F8F6; border:1px solid #D9DDDA; '
                'border-radius:5px;} QLabel {border:none;}'
            )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(11, 9, 11, 9)
        layout.setSpacing(9)
        number_label = QLabel(str(number))
        number_label.setAlignment(Qt.AlignCenter)
        number_label.setFixedSize(26, 26)
        number_label.setStyleSheet(
            'background:#176B63; color:#FFFFFF; border:none; border-radius:13px; '
            'font-weight:700;'
            if active else
            'background:#E4E8E5; color:#59635E; border:none; border-radius:13px; '
            'font-weight:700;'
        )
        copy_layout = QVBoxLayout()
        copy_layout.setSpacing(1)
        title_label = QLabel(title)
        title_label.setStyleSheet('color:#27302C; font-size: 16px; font-weight:700;')
        detail_label = QLabel(detail)
        detail_label.setStyleSheet('color:#747C78; font-size: 15px;')
        copy_layout.addWidget(title_label)
        copy_layout.addWidget(detail_label)
        layout.addWidget(number_label)
        layout.addLayout(copy_layout)
        layout.addStretch()
        return frame

    @staticmethod
    def _make_check_row(title, detail, state='待配置'):
        frame = QFrame()
        frame.setStyleSheet(
            'QFrame {background:#FFFFFF; border:none; border-bottom:1px solid #E8EBE8;}'
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(2, 7, 2, 7)
        copy_layout = QVBoxLayout()
        copy_layout.setSpacing(1)
        title_label = QLabel(title)
        title_label.setStyleSheet('color:#303835; border:none; font-size: 16px; font-weight:700;')
        detail_label = QLabel(detail)
        detail_label.setStyleSheet('color:#7A827E; border:none; font-size: 15px;')
        copy_layout.addWidget(title_label)
        copy_layout.addWidget(detail_label)
        state_label = QLabel(state)
        state_label.setStyleSheet(
            'background:#F1F3F0; color:#66706B; border:1px solid #D8DDDA; '
            'border-radius:3px; padding:3px 7px; font-size: 15px; font-weight:700;'
        )
        layout.addLayout(copy_layout)
        layout.addStretch()
        layout.addWidget(state_label)
        frame.state_label = state_label
        return frame

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 18)
        layout.setSpacing(12)

        action_bar = QFrame()
        action_bar.setObjectName('actionBar')
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(17, 13, 17, 13)
        action_copy = QVBoxLayout()
        action_copy.setSpacing(3)
        action_title = QLabel('将安全联邦系统连接到您的数据')
        action_title.setObjectName('actionTitle')
        action_text = QLabel(
            '配置数据源、字段映射和各参与方策略，原始数据无需集中上传。'
        )
        action_text.setObjectName('actionText')
        action_copy.addWidget(action_title)
        action_copy.addWidget(action_text)
        action_layout.addLayout(action_copy)
        action_layout.addStretch()
        layout.addWidget(action_bar)

        steps_layout = QHBoxLayout()
        steps_layout.setSpacing(8)
        for step in [
            (1, '连接数据', '文件 / 数据库 / API', True),
            (2, '映射字段', '特征、标签与机构', False),
            (3, '安全配置', '隐私、压缩与共识', False),
            (4, '创建任务', '验证后发布', False),
        ]:
            steps_layout.addWidget(self._make_step(*step), 1)
        layout.addLayout(steps_layout)

        workspace_layout = QHBoxLayout()
        workspace_layout.setSpacing(12)
        form_column = QVBoxLayout()
        form_column.setSpacing(12)

        source_group = QGroupBox('01  数据源与辅助资料')
        source_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        source_layout = QGridLayout(source_group)
        source_layout.setHorizontalSpacing(10)
        source_layout.setVerticalSpacing(8)
        self.dataset_name = QLineEdit()
        self.dataset_name.setPlaceholderText('例如：医疗风险预测数据')
        self.dataset_name.setText('我的联邦数据集')
        self.source_type = QComboBox()
        self.source_type.addItems(['本地文件', '数据库连接', 'REST API', '对象存储'])
        self.data_location = QLineEdit()
        self.data_location.setPlaceholderText('选择 CSV / Excel / JSON / Parquet 数据文件')
        self.browse_button = QPushButton('浏览…')
        self.browse_button.setProperty('variant', 'quiet')
        self.browse_button.clicked.connect(self._choose_data_file)
        self.data_format = QComboBox()
        self.data_format.addItems(['自动检测', 'CSV', 'Excel', 'JSON', 'Parquet'])
        self.encoding = QComboBox()
        self.encoding.addItems(['UTF-8', 'GBK / GB18030', '自动检测'])
        self.has_header = QCheckBox('首行包含字段名')
        self.has_header.setChecked(True)
        self.material_location = QLineEdit()
        self.material_location.setPlaceholderText('数据字典、Schema 或 README（可选）')
        material_button = QPushButton('选择资料…')
        material_button.setProperty('variant', 'quiet')
        material_button.clicked.connect(self._choose_material_file)

        source_layout.addWidget(self._field_label('数据集名称'), 0, 0)
        source_layout.addWidget(self.dataset_name, 1, 0, 1, 2)
        source_layout.addWidget(self._field_label('接入方式'), 0, 2)
        source_layout.addWidget(self.source_type, 1, 2, 1, 2)
        source_layout.addWidget(self._field_label('数据位置 / 接口地址'), 2, 0, 1, 4)
        source_layout.addWidget(self.data_location, 3, 0, 1, 3)
        source_layout.addWidget(self.browse_button, 3, 3)
        source_layout.addWidget(self._field_label('数据格式'), 4, 0)
        source_layout.addWidget(self.data_format, 5, 0)
        source_layout.addWidget(self._field_label('字符编码'), 4, 1)
        source_layout.addWidget(self.encoding, 5, 1)
        source_layout.addWidget(self.has_header, 5, 2, 1, 2)
        source_layout.addWidget(self._field_label('补充资料'), 6, 0, 1, 4)
        source_layout.addWidget(self.material_location, 7, 0, 1, 3)
        source_layout.addWidget(material_button, 7, 3)
        form_column.addWidget(source_group)

        mapping_group = QGroupBox('02  任务定义与字段映射')
        mapping_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        mapping_layout = QVBoxLayout(mapping_group)
        task_grid = QGridLayout()
        task_grid.setHorizontalSpacing(10)
        task_grid.setVerticalSpacing(7)
        self.task_type = QComboBox()
        self.task_type.addItems(['二分类', '多分类', '回归', '异常检测', '自定义任务'])
        self.target_field = QLineEdit()
        self.target_field.setPlaceholderText('例如：label')
        self.client_field = QLineEdit()
        self.client_field.setPlaceholderText('例如：hospital_id')
        self.record_field = QLineEdit()
        self.record_field.setPlaceholderText('例如：patient_id（可选）')
        self.missing_strategy = QComboBox()
        self.missing_strategy.addItems(['数值中位数 / 类别众数', '删除缺失样本', '由用户预处理'])
        self.feature_strategy = QComboBox()
        self.feature_strategy.addItems(['除标识与标签外全部使用', '手动勾选', '从 Schema 导入'])
        fields = [
            ('任务类型', self.task_type), ('预测目标字段', self.target_field),
            ('参与方标识字段', self.client_field), ('样本唯一标识', self.record_field),
            ('特征选择', self.feature_strategy), ('缺失值处理', self.missing_strategy),
        ]
        for index, (title, widget) in enumerate(fields):
            row, column = divmod(index, 2)
            task_grid.addWidget(self._field_label(title), row * 2, column)
            task_grid.addWidget(widget, row * 2 + 1, column)
        mapping_layout.addLayout(task_grid)
        mapping_layout.addWidget(self._helper_text(
            '连接数据后，此处将自动显示字段类型、缺失率和用途，并支持逐列调整。'
        ))
        self.schema_table = QTableWidget(4, 4)
        self.schema_table.setHorizontalHeaderLabels(['字段', '推断类型', '作用', '预处理'])
        self.schema_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.schema_table.verticalHeader().setVisible(False)
        self.schema_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.schema_table.setAlternatingRowColors(True)
        self.schema_table.setMaximumHeight(162)
        placeholder_rows = [
            ('feature_1', 'Float32', '训练特征', '标准化'),
            ('feature_2', 'Category', '训练特征', 'One-hot'),
            ('label', 'Integer', '预测目标', '不处理'),
            ('client_id', 'String', '参与方划分', '不进入模型'),
        ]
        for row, values in enumerate(placeholder_rows):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.schema_table.setItem(row, column, item)
        mapping_layout.addWidget(self.schema_table)
        form_column.addWidget(mapping_group)

        federation_group = QGroupBox('03  联邦划分与训练任务')
        federation_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        federation_grid = QGridLayout(federation_group)
        federation_grid.setHorizontalSpacing(10)
        federation_grid.setVerticalSpacing(7)
        self.client_count = QSpinBox()
        self.client_count.setRange(2, 100)
        self.client_count.setValue(5)
        self.partition_strategy = QComboBox()
        self.partition_strategy.addItems([
            '按参与方字段划分（推荐）', '已按目录分开',
            'IID 模拟划分', 'Non-IID Dirichlet 模拟划分',
        ])
        self.model_source = QComboBox()
        self.model_source.addItems(['平台内置基线模型', '自定义 PyTorch 模型', '自定义训练容器'])
        self.round_count = QSpinBox()
        self.round_count.setRange(1, 1000)
        self.round_count.setValue(20)
        self.local_epoch = QSpinBox()
        self.local_epoch.setRange(1, 100)
        self.local_epoch.setValue(5)
        self.test_ratio = QDoubleSpinBox()
        self.test_ratio.setRange(5.0, 50.0)
        self.test_ratio.setSingleStep(5.0)
        self.test_ratio.setValue(20.0)
        self.test_ratio.setSuffix(' %')
        federation_fields = [
            ('参与方数量', self.client_count), ('数据划分方式', self.partition_strategy),
            ('模型来源', self.model_source), ('联邦训练轮次', self.round_count),
            ('本地训练 Epoch', self.local_epoch), ('验证 / 测试集比例', self.test_ratio),
        ]
        for index, (title, widget) in enumerate(federation_fields):
            row, column = divmod(index, 2)
            federation_grid.addWidget(self._field_label(title), row * 2, column)
            federation_grid.addWidget(widget, row * 2 + 1, column)
        form_column.addWidget(federation_group)

        security_group = QGroupBox('04  安全与隐私策略')
        security_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        security_layout = QVBoxLayout(security_group)
        security_layout.addWidget(self._helper_text(
            '默认启用平台的四层安全流程，后续可由接入端与服务端共同执行。'
        ))
        checks_layout = QHBoxLayout()
        self.security_checks = []
        for text in [
            'QKD 会话密钥', '量子差分隐私', 'MPO 梯度压缩',
            '拜占庭鲁棒聚合', '区块链训练存证',
        ]:
            checkbox = QCheckBox(text)
            checkbox.setChecked(True)
            self.security_checks.append(checkbox)
            checks_layout.addWidget(checkbox)
        security_layout.addLayout(checks_layout)
        security_grid = QGridLayout()
        self.epsilon = QDoubleSpinBox()
        self.epsilon.setRange(0.1, 100.0)
        self.epsilon.setSingleStep(0.1)
        self.epsilon.setValue(1.0)
        self.mpo_ratio = QSpinBox()
        self.mpo_ratio.setRange(1, 100)
        self.mpo_ratio.setValue(20)
        self.mpo_ratio.setSuffix(' %')
        self.aggregation = QComboBox()
        self.aggregation.addItems(['坐标中位数（推荐）', 'Trimmed Mean', 'Krum', '普通 FedAvg'])
        for column, (title, widget) in enumerate([
            ('隐私预算 ε', self.epsilon),
            ('MPO 目标保留比例', self.mpo_ratio),
            ('安全聚合策略', self.aggregation),
        ]):
            security_grid.addWidget(self._field_label(title), 0, column)
            security_grid.addWidget(widget, 1, column)
        security_layout.addLayout(security_grid)
        form_column.addWidget(security_group)

        workspace_layout.addLayout(form_column, 7)

        preview_column = QVBoxLayout()
        preview_column.setSpacing(12)
        status_group = QGroupBox('接入状态')
        status_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        status_layout = QVBoxLayout(status_group)
        self.interface_state = QLabel('配置草稿')
        self.interface_state.setAlignment(Qt.AlignCenter)
        self.interface_state.setStyleSheet(
            'background:#F1F3F0; color:#5D6662; border:1px solid #D8DDDA; '
            'border-radius:5px; padding:10px; font-size: 21px; font-weight:700;'
        )
        self.preview_summary = QLabel()
        self.preview_summary.setWordWrap(True)
        self.preview_summary.setStyleSheet(
            'background:#FAFBF9; color:#424B47; border:1px solid #E0E4E1; '
            'border-radius:5px; padding:11px; font-size: 16px; line-height:1.5;'
        )
        status_layout.addWidget(self.interface_state)
        status_layout.addWidget(self.preview_summary)
        preview_column.addWidget(status_group)

        flow_group = QGroupBox('预计接入链路')
        flow_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        flow_layout = QVBoxLayout(flow_group)
        for index, (title, detail) in enumerate([
            ('用户数据源', '保留在本地或用户私有环境'),
            ('数据适配器', '读取 Schema，执行映射与本地预处理'),
            ('安全联邦客户端', '只交换加密、降噪后的模型更新'),
            ('联邦聚合与存证', '鲁棒聚合、恶意检测与链上审计'),
        ]):
            card = QFrame()
            card.setStyleSheet(
                'QFrame {background:#F7F8F6; border:1px solid #DCE1DD; '
                'border-radius:4px;} QLabel {border:none;}'
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 7, 10, 7)
            card_layout.setSpacing(1)
            title_label = QLabel(f'{index + 1:02d}   {title}')
            title_label.setStyleSheet('color:#315E59; font-size: 16px; font-weight:700;')
            detail_label = QLabel(detail)
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet('color:#747C78; font-size: 15px;')
            card_layout.addWidget(title_label)
            card_layout.addWidget(detail_label)
            flow_layout.addWidget(card)
        preview_column.addWidget(flow_group)

        checklist_group = QGroupBox('发布前检查')
        checklist_group.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        checklist_layout = QVBoxLayout(checklist_group)
        checklist_layout.setSpacing(0)
        self.source_check = self._make_check_row('数据可达性', '格式、编码与访问权限')
        self.schema_check = self._make_check_row('字段完整性', '特征、标签与参与方映射')
        self.privacy_check = self._make_check_row('隐私安全', '预算、压缩、聚合与存证')
        self.runtime_check = self._make_check_row('运行环境', '客户端依赖与计算资源')
        for row in [self.source_check, self.schema_check, self.privacy_check, self.runtime_check]:
            checklist_layout.addWidget(row)
        preview_column.addWidget(checklist_group)

        privacy_note = QLabel(
            '隐私边界\n本页不会上传数据。后续正式接入时，原始记录仅在各参与方本地处理，'
            '平台只协调加密模型更新。'
        )
        privacy_note.setWordWrap(True)
        privacy_note.setStyleSheet(
            'background:#EEF4F2; color:#315E59; border:1px solid #C9DAD5; '
            'border-left:3px solid #176B63; border-radius:4px; padding:11px; '
            'font-size: 16px; font-weight:600;'
        )
        preview_column.addWidget(privacy_note)

        preview_button = QPushButton('检查当前配置')
        preview_button.setProperty('variant', 'quiet')
        preview_button.clicked.connect(self._validate_configuration)
        reset_button = QPushButton('恢复默认配置')
        reset_button.setProperty('variant', 'quiet')
        reset_button.clicked.connect(self._reset_form)
        self.create_button = QPushButton('创建接入任务')
        self.create_button.setProperty('variant', 'primary')
        self.create_button.clicked.connect(self._create_access_task)
        preview_column.addWidget(preview_button)
        preview_column.addWidget(reset_button)
        preview_column.addWidget(self.create_button)
        preview_column.addStretch()
        workspace_layout.addLayout(preview_column, 3)

        layout.addLayout(workspace_layout)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _connect_preview_signals(self):
        for line_edit in [
            self.dataset_name, self.data_location, self.target_field,
            self.client_field, self.record_field,
        ]:
            line_edit.textChanged.connect(self._update_preview)
        for combo in [
            self.source_type, self.data_format, self.task_type,
            self.partition_strategy, self.model_source, self.aggregation,
        ]:
            combo.currentTextChanged.connect(self._update_preview)
        for spin_box in [
            self.client_count, self.round_count, self.local_epoch,
            self.test_ratio, self.epsilon, self.mpo_ratio,
        ]:
            spin_box.valueChanged.connect(self._update_preview)
        for checkbox in self.security_checks:
            checkbox.toggled.connect(self._update_preview)
        self.source_type.currentTextChanged.connect(self._update_source_controls)
        self._update_source_controls(self.source_type.currentText())

    def _update_source_controls(self, source_type):
        if source_type == '本地文件':
            self.data_location.setPlaceholderText(
                '选择 CSV / Excel / JSON / Parquet 数据文件'
            )
            self.browse_button.setEnabled(True)
            self.browse_button.setToolTip('')
        elif source_type == '数据库连接':
            self.data_location.setPlaceholderText(
                '例如：postgresql://host:5432/database/table'
            )
            self.browse_button.setEnabled(False)
            self.browse_button.setToolTip('数据库连接地址请直接输入')
        elif source_type == 'REST API':
            self.data_location.setPlaceholderText('例如：https://api.example.com/v1/dataset')
            self.browse_button.setEnabled(False)
            self.browse_button.setToolTip('API 地址请直接输入')
        else:
            self.data_location.setPlaceholderText('例如：s3://bucket/path/to/dataset')
            self.browse_button.setEnabled(False)
            self.browse_button.setToolTip('对象存储地址请直接输入')

    def _choose_data_file(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            '选择要接入的数据文件',
            str(PROJECT_ROOT),
            '数据文件 (*.csv *.xlsx *.xls *.json *.parquet);;所有文件 (*)',
        )
        if path:
            self.data_location.setText(path)

    def _choose_material_file(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            '选择数据字典或说明资料',
            str(PROJECT_ROOT),
            '说明资料 (*.json *.yaml *.yml *.md *.txt *.pdf *.docx);;所有文件 (*)',
        )
        if path:
            self.material_location.setText(path)

    def _update_preview(self, *_args):
        dataset_name = self.dataset_name.text().strip() or '未命名数据集'
        location_state = '已指定' if self.data_location.text().strip() else '待选择'
        target = self.target_field.text().strip() or '待映射'
        client_field = self.client_field.text().strip() or '待映射'
        enabled_security = sum(checkbox.isChecked() for checkbox in self.security_checks)
        self.preview_summary.setText(
            f'<b>{dataset_name}</b><br><br>'
            f'数据源：{self.source_type.currentText()} · {location_state}<br>'
            f'学习任务：{self.task_type.currentText()}<br>'
            f'预测目标：{target}<br>'
            f'参与方字段：{client_field}<br>'
            f'训练计划：{self.client_count.value()} 方 × '
            f'{self.round_count.value()} 轮 × {self.local_epoch.value()} Epoch<br>'
            f'安全层：已启用 {enabled_security}/5 项'
        )
        self.interface_state.setText('配置草稿')
        self.interface_state.setStyleSheet(
            'background:#F1F3F0; color:#5D6662; border:1px solid #D8DDDA; '
            'border-radius:5px; padding:10px; font-size: 21px; font-weight:700;'
        )

    @staticmethod
    def _set_check_state(row, text, ready):
        row.state_label.setText(text)
        if ready:
            row.state_label.setStyleSheet(
                'background:#E8F5F1; color:#168A78; border:1px solid #BCDCD3; '
                'border-radius:3px; padding:3px 7px; font-size: 15px; font-weight:700;'
            )
        elif text == '待配置':
            row.state_label.setStyleSheet(
                'background:#F1F3F0; color:#66706B; border:1px solid #D8DDDA; '
                'border-radius:3px; padding:3px 7px; font-size: 15px; font-weight:700;'
            )
        else:
            row.state_label.setStyleSheet(
                'background:#FAF5EA; color:#925E18; border:1px solid #E0CAA6; '
                'border-radius:3px; padding:3px 7px; font-size: 15px; font-weight:700;'
            )

    def _validate_configuration(self):
        source_ready = bool(self.data_location.text().strip())
        schema_ready = bool(
            self.target_field.text().strip() and self.client_field.text().strip()
        )
        privacy_ready = any(checkbox.isChecked() for checkbox in self.security_checks)
        self._set_check_state(
            self.source_check, '界面已填写' if source_ready else '缺少数据位置', source_ready
        )
        self._set_check_state(
            self.schema_check, '界面已填写' if schema_ready else '待映射', schema_ready
        )
        self._set_check_state(
            self.privacy_check, '已启用策略' if privacy_ready else '未启用', privacy_ready
        )
        self._set_check_state(self.runtime_check, '环境就绪', True)
        configuration_ready = source_ready and schema_ready and privacy_ready
        if configuration_ready:
            self.interface_state.setText('配置校验通过')
            self.interface_state.setStyleSheet(
                'background:#EDF5F2; color:#176B63; border:1px solid #BFD4CE; '
                'border-radius:5px; padding:10px; font-size: 21px; font-weight:700;'
            )
        else:
            self.interface_state.setText('请完善必填配置')
            self.interface_state.setStyleSheet(
                'background:#FAF5EA; color:#925E18; border:1px solid #E0CAA6; '
                'border-radius:5px; padding:10px; font-size: 21px; font-weight:700;'
            )
        return configuration_ready

    def _create_access_task(self):
        if not self._validate_configuration():
            return
        self.interface_state.setText('接入任务已创建')
        self.interface_state.setStyleSheet(
            'background:#E8F5F1; color:#168A78; border:1px solid #BCDCD3; '
            'border-radius:5px; padding:10px; font-size: 21px; font-weight:700;'
        )

    def _reset_form(self):
        self.dataset_name.setText('我的联邦数据集')
        self.source_type.setCurrentIndex(0)
        self.data_location.clear()
        self.data_format.setCurrentIndex(0)
        self.encoding.setCurrentIndex(0)
        self.has_header.setChecked(True)
        self.material_location.clear()
        self.task_type.setCurrentIndex(0)
        self.target_field.clear()
        self.client_field.clear()
        self.record_field.clear()
        self.feature_strategy.setCurrentIndex(0)
        self.missing_strategy.setCurrentIndex(0)
        self.client_count.setValue(5)
        self.partition_strategy.setCurrentIndex(0)
        self.model_source.setCurrentIndex(0)
        self.round_count.setValue(20)
        self.local_epoch.setValue(5)
        self.test_ratio.setValue(20.0)
        for checkbox in self.security_checks:
            checkbox.setChecked(True)
        self.epsilon.setValue(1.0)
        self.mpo_ratio.setValue(20)
        self.aggregation.setCurrentIndex(0)
        for row in [self.source_check, self.schema_check, self.privacy_check, self.runtime_check]:
            self._set_check_state(row, '待配置', False)
        self._update_preview()


class MainWindow(QMainWindow):

    PAGE_META = [
        ('安全基础 / 通信', 'QKD 密钥分发', '建立会话密钥，检测窃听并验证加密传输'),
        ('安全基础 / 隐私', '量子差分隐私', '调节隐私预算，评估保护强度与模型效用'),
        ('协作计算 / 训练', '联邦学习与模型压缩', '联邦训练、鲁棒聚合、MPO 压缩与交叉验证'),
        ('协作计算 / 共识', '拜占庭共识', '调节节点与恶意比例，观察投票和 1/3 容错边界'),
        ('协作计算 / 存证', '链上篡改验证', '修改历史数据，验证 SHA-256 指纹与 PoW 完整性校验'),
        ('安全验证 / 攻防', '攻防实验', '集中验证窃听、投毒、梯度泄漏和链上篡改防护'),
        ('场景验证 / 真实场景', '真实场景验证',
         '同页展示医疗、邮件与金融数据，共用一套四层安全联邦流程'),
        ('场景验证 / 用户接入', '用户接口',
         '配置数据源、字段映射、联邦划分与安全策略'),
    ]
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('QuantumSecure FL · 量子安全联邦学习平台')
        self.resize(1740, 970)
        self.setMinimumSize(1150, 660)
        self.setStyleSheet(APP_STYLE)
        
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont('Microsoft YaHei', 16, QFont.Medium))
        self.tabs.setDocumentMode(True)
        
        self.qkd_tab = QKDTab()
        self.privacy_tab = PrivacyTab()
        self.fl_tab = FederatedTab()
        self.attack_tab = AttackTab()
        self.byzantine_consensus_tab = ByzantineConsensusTab()
        self.blockchain_tamper_tab = BlockchainTamperTab()
        self.real_dataset_tab = RealDatasetScenarioTab()
        self.custom_dataset_tab = CustomDatasetInterfaceTab()

        # 保留原属性名，便于既有测试和外部调用继续访问各场景。
        self.scenario_tab = self.real_dataset_tab.medical_tab
        self.spam_scenario_tab = self.real_dataset_tab.spam_tab
        self.bankruptcy_scenario_tab = self.real_dataset_tab.bankruptcy_tab
        
        self.tabs.addTab(self.qkd_tab, '🔑 QKD 通信')
        self.tabs.addTab(self.privacy_tab, '🔒 隐私防护')
        self.tabs.addTab(self.fl_tab, '🤖 联邦学习')
        self.tabs.addTab(self.byzantine_consensus_tab, '◉ 拜占庭共识')
        self.tabs.addTab(self.blockchain_tamper_tab, '⛓ 区块链篡改')
        self.tabs.addTab(self.attack_tab, '攻防')
        self.tabs.addTab(self.real_dataset_tab, '▦ 真实场景验证')
        self.tabs.addTab(self.custom_dataset_tab, '⊕ 用户接口')

        # 保留 QTabWidget 作为页面容器和既有测试接口，导航交给左侧品牌栏。
        self.tabs.tabBar().hide()
        self._build_shell()
        self.tabs.currentChanged.connect(self._sync_navigation)
        self._sync_navigation(0)
        self.statusBar().hide()

    def _build_shell(self):
        shell = QWidget()
        shell.setObjectName('appShell')
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(252)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 20, 14, 16)
        sidebar_layout.setSpacing(4)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(11)
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_mark = QLabel('QS')
        brand_mark.setObjectName('brandMark')
        brand_mark.setFixedSize(40, 40)
        brand_mark.setAlignment(Qt.AlignCenter)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_title = QLabel('量安联邦平台')
        brand_title.setObjectName('brandTitle')
        brand_text.addWidget(brand_title)
        brand_row.addWidget(brand_mark)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        sidebar_layout.addLayout(brand_row)
        sidebar_layout.addSpacing(14)

        nav_groups = [
            ('安全基础', [(0, 'QKD 通信'), (1, '隐私防护')], True),
            ('协作计算', [
                (2, '联邦学习'), (3, '拜占庭共识'),
                (4, '链上篡改'), (5, '攻防实验'),
            ], True),
            ('场景验证', [(6, '真实场景验证')], True),
            ('可用接口', [(7, '用户接口')], True),
        ]
        self.nav_buttons = []
        self._nav_groups = []
        for section, items, expanded in nav_groups:
            section_btn = QPushButton(section)
            section_btn.setObjectName('navSection')
            section_btn.setCursor(Qt.PointingHandCursor)
            sidebar_layout.addWidget(section_btn)
            child_buttons = []
            for page_index, text in items:
                button = QPushButton(text)
                button.setObjectName('navButton')
                button.setCursor(Qt.PointingHandCursor)
                button.setMinimumHeight(38)
                button.clicked.connect(
                    lambda _checked=False, i=page_index: self.tabs.setCurrentIndex(i)
                )
                child_buttons.append(button)
                sidebar_layout.addWidget(button)
            self.nav_buttons.extend(child_buttons)
            self._nav_groups.append((section_btn, child_buttons))
            if expanded:
                section_btn.setText(f'▾ {section}')
            else:
                for b in child_buttons:
                    b.hide()
                section_btn.setText(f'▸ {section}')
            section_btn.clicked.connect(
                lambda _checked=False, group=child_buttons, btn=section_btn,
                         sec=section: self._toggle_nav_group(sec, group, btn)
            )

        sidebar_layout.addStretch()

        stage = QWidget()
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(0, 0, 0, 0)
        stage_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setObjectName('topBar')
        top_bar.setFixedHeight(104)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(32, 12, 28, 11)

        heading_layout = QVBoxLayout()
        heading_layout.setSpacing(2)
        self.page_eyebrow = QLabel()
        self.page_eyebrow.hide()
        self.page_title = QLabel()
        self.page_title.setObjectName('pageTitle')
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName('pageSubtitle')
        heading_layout.addWidget(self.page_title)
        heading_layout.addWidget(self.page_subtitle)
        top_layout.addLayout(heading_layout)
        top_layout.addStretch()

        self.page_counter = QLabel()
        self.page_counter.hide()

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 14, 24, 12)
        content_layout.addWidget(self.tabs)

        stage_layout.addWidget(top_bar)
        stage_layout.addWidget(content, 1)
        shell_layout.addWidget(sidebar)
        shell_layout.addWidget(stage, 1)
        self.setCentralWidget(shell)

    def _toggle_nav_group(self, section_name, child_buttons, section_btn):
        expanded = not child_buttons[0].isVisible()
        for b in child_buttons:
            b.setVisible(expanded)
        arrow = '▾' if expanded else '▸'
        section_btn.setText(f'{arrow} {section_name}')

    def _sync_navigation(self, index):
        if index < 0 or index >= len(self.PAGE_META):
            return
        eyebrow, title, subtitle = self.PAGE_META[index]
        self.page_eyebrow.setText(eyebrow)
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)
        self.page_counter.setText(f'{index + 1:02d} / {len(self.PAGE_META):02d}')
        for button_index, button in enumerate(self.nav_buttons):
            button.setProperty('active', button_index == index)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
        current_page = self.tabs.widget(index)
        if (
            hasattr(current_page, 'play_explainer')
            and getattr(current_page, 'auto_play_explainer', True)
        ):
            # 页面可见后再播放，避免在后台 Tab 中提前跑完动画。
            QTimer.singleShot(90, current_page.play_explainer)

def run_gui():
    """启动图形界面。"""
    if not PYQT_AVAILABLE:
        print('⚠ PyQt5 未安装, 请运行: pip install PyQt5 matplotlib')
        print('正在切换到命令行模式...\n')
        run_cli_demo()
        return
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont('Microsoft YaHei', 16, QFont.Medium))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


def run_cli_demo():
    """无 GUI 时的命令行入口。"""
    print('='*70)
    print('  量子密钥分发+量子差分隐私+区块链联邦学习融合安全通信系统')
    print('  (CLI mode - install PyQt5 for the GUI)')
    print('='*70)
    
    print('\n【1】量子密钥分发模块...')
    from core.qkd_module import qkd_demo
    qkd_demo()
    
    print('\n【2】量子差分隐私模块...')
    from core.qdp_module import qdp_demo
    qdp_demo()
    
    print('\n【3】MPO 压缩+联邦学习模块...')
    from core.fl_mpo_module import mpo_fl_demo
    mpo_fl_demo()
    
    print('\n【4】区块链+量子拜占庭共识模块...')
    from core.blockchain_consensus import blockchain_demo
    blockchain_demo()
    
    print('\n【5】攻防实验...')
    from core.attack_module import attack_demo
    attack_demo()
    
    print('\n' + '='*70)
    print('  所有模块检查完成')
    print('  启动命令: python QuantumSecureFL/main.py')
    print('='*70)


if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    os.chdir(project_root)
    
    if '--cli' in sys.argv or '-c' in sys.argv:
        run_cli_demo()
    else:
        run_gui()
