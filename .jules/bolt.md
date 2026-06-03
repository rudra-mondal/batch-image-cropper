## 2024-06-03 - PySide6 setStyleSheet Animation Overhead
**Learning:** Using `setStyleSheet()` inside a rapid event loop or animation (like `QPropertyAnimation` updating color) creates severe CPU bottlenecks because it forces style re-evaluation and layout updates across the widget tree, even when the app is idle.
**Action:** When animating visual properties like color or opacity in Qt, prefer specialized graphic effect classes (e.g., `QGraphicsColorizeEffect` or `QGraphicsOpacityEffect`) which apply changes purely at the painting layer without triggering style cascades.
