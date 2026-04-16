from __future__ import annotations

from PySide6.QtGui import QColor

from app.ui.form100_v2.bodymap_assets import load_bodymap_template_pixmap, split_bodymap_template
from app.ui.form100_v2.wizard_widgets.icon_select_widget import IconSelectWidget


def _dark_bbox(pixmap) -> tuple[int, int, int, int] | None:
    image = pixmap.toImage()
    min_x = image.width()
    min_y = image.height()
    max_x = -1
    max_y = -1
    for y in range(image.height()):
        for x in range(image.width()):
            color = QColor(image.pixelColor(x, y))
            if color.alpha() == 0:
                continue
            luminance = (color.red() + color.green() + color.blue()) // 3
            if luminance >= 235:
                continue
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
    if max_x < 0 or max_y < 0:
        return None
    return min_x, min_y, max_x, max_y


def test_icon_select_widget_marks_active_button_property(qapp) -> None:
    widget = IconSelectWidget((("lying", "Лёжа"), ("sitting", "Сидя")))
    widget.set_value("sitting")
    qapp.processEvents()

    assert widget.value() == "sitting"
    assert widget._buttons["sitting"].property("active") is True
    assert widget._buttons["lying"].property("active") is False


def test_bodymap_split_keeps_gap_between_front_and_back_silhouettes(qapp) -> None:
    del qapp
    template = load_bodymap_template_pixmap()
    assert template is not None

    silhouettes = split_bodymap_template(template, lambda pixmap: pixmap)
    front_bbox = _dark_bbox(silhouettes["male_front"])
    back_bbox = _dark_bbox(silhouettes["male_back"])

    assert front_bbox is not None
    assert back_bbox is not None
    assert front_bbox[2] <= silhouettes["male_front"].width() - 6
    assert back_bbox[0] >= 6
