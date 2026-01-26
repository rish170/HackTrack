from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication


DARK = {
    "bg": "#0f1115",
    "panel": "#161a20",
    "accent": "#4cc9f0",
    "accent_hover": "#41b8dc",
    "accent_pressed": "#35a2c4",
    "text_primary": "#e8ecf1",
    "text_secondary": "#9aa6b2",
    "border": "#222733",
    "success": "#67e8a8",
    "warning": "#f6c177",
    "error": "#ef476f",
}

LIGHT = {
    "bg": "#f6f7fb",
    "panel": "#ffffff",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent_pressed": "#1e40af",
    "text_primary": "#0f172a",
    "text_secondary": "#475569",
    "border": "#e2e8f0",
    "success": "#16a34a",
    "warning": "#d97706",
    "error": "#dc2626",
}


def apply_palette(app: QApplication, theme: dict) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(theme["bg"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme["panel"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme["bg"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(theme["text_primary"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme["text_primary"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme["text_primary"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme["text_primary"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(theme["panel"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme["accent"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(theme["accent"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(theme["text_secondary"]).lighter())
    app.setPalette(palette)


def stylesheet(theme: dict) -> str:
    accent = theme["accent"]
    accent_hover = theme["accent_hover"]
    accent_pressed = theme["accent_pressed"]
    panel = theme["panel"]
    border = theme["border"]
    text = theme["text_primary"]
    text_secondary = theme["text_secondary"]
    success = theme["success"]
    warning = theme["warning"]
    error = theme["error"]

    return f"""
    QWidget {{
        background: {theme['bg']};
        color: {text};
        font-family: 'Segoe UI', 'Inter', system-ui;
    }}
    QGroupBox {{
        background: {panel};
        border: 1px solid {border};
        border-radius: 10px;
        margin-top: 10px;
        padding: 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px 4px 4px;
        color: {text_secondary};
        background: transparent;
    }}
    QPushButton {{
        background: {accent};
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {accent_hover}; }}
    QPushButton:pressed {{ background: {accent_pressed}; }}
    QPushButton:disabled {{ background: {border}; color: {text_secondary}; }}
    QLineEdit, QSpinBox, QDoubleSpinBox {{
        background: {panel};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 8px 10px;
        color: {text};
    }}
    QProgressBar {{
        background: {panel};
        border: 1px solid {border};
        border-radius: 10px;
        text-visible: true;
        color: {text_secondary};
        height: 16px;
    }}
    QProgressBar::chunk {{
        background: linear-gradient(45deg, {accent} 0%, {accent_hover} 100%);
        border-radius: 9px;
        margin: 1px;
    }}
    QLabel.status-success {{ color: {success}; }}
    QLabel.status-warning {{ color: {warning}; }}
    QLabel.status-error {{ color: {error}; }}
    QLabel {{ background: transparent; }}
    QToolTip {{
        background: {panel};
        color: {text};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 6px;
    }}
    """
