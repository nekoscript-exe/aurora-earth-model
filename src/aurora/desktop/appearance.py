"""Shared presentation colors for AURORA Desktop."""

from PySide6.QtCore import QSettings

PALETTES = {
    "dark": {
        "background": "#090f1b",
        "surface": "#152238",
        "border": "#30475e",
        "text": "#e4edf8",
        "muted": "#91a7bd",
        "accent": "#78cfe9",
        "success": "#80d9c7",
        "warning": "#efbd76",
        "purple": "#b99de8",
    },
    "light": {
        "background": "#edf2f8",
        "surface": "#ffffff",
        "border": "#c6d5e3",
        "text": "#23374a",
        "muted": "#52697f",
        "accent": "#167a9f",
        "success": "#16765d",
        "warning": "#98601b",
        "purple": "#7653b0",
    },
}


def colors():
    mode = QSettings("AURORA", "Desktop").value(
        "appearance", "dark"
    )
    return PALETTES.get(mode, PALETTES["dark"])


def color(name):
    return colors()[name]


def style_figure(figure):
    palette = colors()

    figure.set_facecolor(palette["background"])

    for ax in figure.axes:
        ax.set_facecolor(palette["surface"])
        ax.tick_params(colors=palette["muted"])
        ax.title.set_color(palette["text"])
        ax.xaxis.label.set_color(palette["text"])
        ax.yaxis.label.set_color(palette["text"])

        for spine in ax.spines.values():
            spine.set_edgecolor(palette["border"])

        for text in ax.texts:
            text.set_color(palette["text"])

        legend = ax.get_legend()
        if legend is not None:
            legend.get_frame().set_facecolor(palette["surface"])
            legend.get_frame().set_edgecolor(palette["border"])

            for text in legend.get_texts():
                text.set_color(palette["text"])

    for text in figure.texts:
        text.set_color(palette["text"])


def refresh_figures(root):
    from PySide6.QtWidgets import QWidget
    from matplotlib.figure import Figure

    for widget in root.findChildren(QWidget):
        figure = getattr(widget, "figure", None)

        if isinstance(figure, Figure):
            style_figure(figure)

            if figure.canvas is not None:
                figure.canvas.draw_idle()
