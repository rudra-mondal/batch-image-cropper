import sys
import os
from PIL import Image

# Add QPropertyAnimation for the color animation
from PySide6.QtCore import QPropertyAnimation, Property, QUrl 

# Add QDesktopServices for opening links
from PySide6.QtGui import QDesktopServices

# PySide6 components for GUI
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QGridLayout,
    QHBoxLayout, QVBoxLayout, QFrame, QFileDialog, QGroupBox,
    QComboBox, QStatusBar, QMessageBox, QSplitter,
    QGraphicsColorizeEffect
)
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QAction, QFont,
    QImageReader, QPainterPath
)
from PySide6.QtCore import Qt, QSize, QPointF, QRectF, QRect

# Set high DPI scaling for better visuals on modern displays
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)


class ImageCanvas(QWidget):
    """
    The main widget for displaying and interacting with the image.
    Handles constrained panning, zooming, and drawing the crop overlay.
    """
    def __init__(self):
        super().__init__()
        self.pixmap = None
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        self.last_mouse_pos = QPointF()
        
        # crop_box_rect is now a class member so it can be accessed by all methods
        self.crop_box_rect = QRectF()
        self.crop_aspect_ratio = 1.0

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

    def set_image(self, image_path):
        """Loads a new image into the canvas."""
        if image_path:
            reader = QImageReader(image_path)
            reader.setAutoTransform(True) # Auto-rotate based on EXIF
            img = reader.read()
            self.pixmap = QPixmap.fromImage(img) if not img.isNull() else None
        else:
            self.pixmap = None
        
        self.reset_view()
        self.update()

    def set_crop_aspect_ratio(self, width, height):
        """Sets the aspect ratio for the crop overlay."""
        if height > 0:
            self.crop_aspect_ratio = width / height
        else:
            self.crop_aspect_ratio = 1.0
        # When aspect ratio changes, we need to re-validate our constraints
        self._update_crop_box_rect()
        self._constrain_view()
        self.update()

    def reset_view(self):
        """Resets zoom and pan to fit the image in the view."""
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        if self.pixmap:
            self.fit_to_window()

    def fit_to_window(self):
        """Adjusts zoom to make the whole image visible."""
        if not self.pixmap: return
        self._update_crop_box_rect() # Ensure crop box is calculated
        
        # Start by fitting image to window
        w_ratio = self.width() / self.pixmap.width()
        h_ratio = self.height() / self.pixmap.height()
        self.zoom_factor = min(w_ratio, h_ratio) * 0.95
        
        # Center the image
        scaled_w = self.pixmap.width() * self.zoom_factor
        scaled_h = self.pixmap.height() * self.zoom_factor
        self.pan_offset.setX((self.width() - scaled_w) / 2)
        self.pan_offset.setY((self.height() - scaled_h) / 2)

        # Now, enforce constraints
        self._constrain_view()
        self.update()

    def _update_crop_box_rect(self):
        """Helper to calculate the crop box's geometry in the widget."""
        widget_w, widget_h = self.width(), self.height()
        
        box_w, box_h = 0, 0
        if widget_w / widget_h > self.crop_aspect_ratio:
            box_h = widget_h * 0.8
            box_w = box_h * self.crop_aspect_ratio
        else:
            box_w = widget_w * 0.8
            box_h = box_w / self.crop_aspect_ratio

        box_x = (widget_w - box_w) / 2
        box_y = (widget_h - box_h) / 2
        
        self.crop_box_rect = QRectF(box_x, box_y, box_w, box_h)

    def paintEvent(self, event):
        """Draws the image, the crop overlay, and the Rule of Thirds grid."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor(50, 50, 50)) # Background color

        if not self.pixmap:
            painter.setPen(QColor(180, 180, 180)) # Light gray text
            painter.setFont(QFont("Arial", 16))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Drag & Drop Images Here")
            return

        self._update_crop_box_rect()
        
        target_w = self.pixmap.width() * self.zoom_factor
        target_h = self.pixmap.height() * self.zoom_factor
        self.target_rect = QRectF(self.pan_offset.x(), self.pan_offset.y(), target_w, target_h)
        painter.drawPixmap(self.target_rect, self.pixmap, self.pixmap.rect())

        overlay_color = QColor(0, 0, 0, 150)
        path = QPainterPath()
        path.addRect(QRectF(self.rect()))
        path.addRect(self.crop_box_rect)
        painter.fillPath(path, QBrush(overlay_color))

        pen = QPen(Qt.GlobalColor.white, 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawRect(self.crop_box_rect)

        # --- NEW: Draw Rule of Thirds Grid ---
        grid_pen = QPen(QColor(255, 255, 255, 120), 1, Qt.PenStyle.DashLine) # Fainter, dashed white lines
        painter.setPen(grid_pen)
        
        one_third_w = self.crop_box_rect.width() / 3
        one_third_h = self.crop_box_rect.height() / 3

        # Vertical lines
        painter.drawLine(
            QPointF(self.crop_box_rect.left() + one_third_w, self.crop_box_rect.top()),
            QPointF(self.crop_box_rect.left() + one_third_w, self.crop_box_rect.bottom())
        )
        painter.drawLine(
            QPointF(self.crop_box_rect.left() + 2 * one_third_w, self.crop_box_rect.top()),
            QPointF(self.crop_box_rect.left() + 2 * one_third_w, self.crop_box_rect.bottom())
        )
        # Horizontal lines
        painter.drawLine(
            QPointF(self.crop_box_rect.left(), self.crop_box_rect.top() + one_third_h),
            QPointF(self.crop_box_rect.right(), self.crop_box_rect.top() + one_third_h)
        )
        painter.drawLine(
            QPointF(self.crop_box_rect.left(), self.crop_box_rect.top() + 2 * one_third_h),
            QPointF(self.crop_box_rect.right(), self.crop_box_rect.top() + 2 * one_third_h)
        )

    def _constrain_view(self):
        """NEW: Constrains zoom and pan to valid ranges."""
        if not self.pixmap or self.crop_box_rect.isNull():
            return
            
        # 1. Constrain Zoom: Image cannot be smaller than the crop box
        min_zoom_w = self.crop_box_rect.width() / self.pixmap.width()
        min_zoom_h = self.crop_box_rect.height() / self.pixmap.height()
        self.zoom_factor = max(self.zoom_factor, min_zoom_w, min_zoom_h)

        # 2. Constrain Pan: Image edges cannot go inside the crop box
        scaled_w = self.pixmap.width() * self.zoom_factor
        scaled_h = self.pixmap.height() * self.zoom_factor

        # Calculate valid top-left corner positions for the image
        min_pan_x = self.crop_box_rect.right() - scaled_w
        max_pan_x = self.crop_box_rect.left()
        min_pan_y = self.crop_box_rect.bottom() - scaled_h
        max_pan_y = self.crop_box_rect.top()

        current_pan = self.pan_offset
        constrained_x = max(min_pan_x, min(current_pan.x(), max_pan_x))
        constrained_y = max(min_pan_y, min(current_pan.y(), max_pan_y))
        
        self.pan_offset = QPointF(constrained_x, constrained_y)

    def wheelEvent(self, event):
        """Handles zooming with the mouse wheel."""
        if not self.pixmap: return
        
        # --- CHANGE 1: Reduced zoom sensitivity ---
        zoom_factor_change = 1.05 if event.angleDelta().y() > 0 else 1 / 1.05
        
        old_zoom = self.zoom_factor
        self.zoom_factor *= zoom_factor_change

        mouse_pos = event.position()
        pan_before_zoom = self.pan_offset
        pan_after_zoom = mouse_pos - (mouse_pos - pan_before_zoom) * (self.zoom_factor / old_zoom)
        self.pan_offset = pan_after_zoom
        
        # --- CHANGE 2: Apply constraints after every view change ---
        self._constrain_view()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.position()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.position() - self.last_mouse_pos
            self.pan_offset += delta
            self.last_mouse_pos = event.position()
            
            # --- CHANGE 3: Apply constraints after every view change ---
            self._constrain_view()
            self.update()

    def get_crop_parameters(self):
        """Calculates the crop rectangle in original image pixel coordinates."""
        if not self.pixmap: return None

        # Convert the crop box from widget coordinates to image coordinates
        img_x_in_widget = self.pan_offset.x()
        img_y_in_widget = self.pan_offset.y()

        # Calculate the top-left corner of the crop relative to the image
        crop_x_on_scaled_img = self.crop_box_rect.left() - img_x_in_widget
        crop_y_on_scaled_img = self.crop_box_rect.top() - img_y_in_widget

        # Convert these coordinates to original image pixels
        crop_x = int(crop_x_on_scaled_img / self.zoom_factor)
        crop_y = int(crop_y_on_scaled_img / self.zoom_factor)
        crop_w = int(self.crop_box_rect.width() / self.zoom_factor)
        crop_h = int(self.crop_box_rect.height() / self.zoom_factor)

        return QRect(crop_x, crop_y, crop_w, crop_h)


class ClickableLabel(QLabel):
    """A QLabel that is clickable and animates its color."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # ⚡ Bolt Optimization: Use QGraphicsColorizeEffect instead of setStyleSheet
        # Re-evaluating setStyleSheet many times a second triggers an expensive
        # style cascade across the widget tree, wasting CPU even when idle.
        # QGraphicsColorizeEffect operates cleanly at the paint level.
        self.effect = QGraphicsColorizeEffect(self)
        self.setGraphicsEffect(self.effect)

        # Color animation setup directly targeting the effect's color property
        self.animation = QPropertyAnimation(self.effect, b"color")
        self.animation.setDuration(3000) # 3 seconds per color transition
        self.animation.setLoopCount(-1) # Loop forever
        self.animation.setStartValue(QColor("#00A3FF")) # Bright Blue
        self.animation.setKeyValueAt(0.5, QColor("#4DFF8F")) # Bright Green
        self.animation.setEndValue(QColor("#00A3FF"))
        self.animation.start()
        
    def mousePressEvent(self, event):
        """Opens the link when the label is clicked."""
        QDesktopServices.openUrl(QUrl("https://github.com/rudra-mondal"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Precision Batch Cropper")
        self.setGeometry(100, 100, 1200, 800)

        # --- NEW: Dark Theme Stylesheet ---
        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E;
                color: #E0E0E0;
                font-family: Arial;
            }
            QMainWindow {
                background-color: #222222;
            }
            QFrame {
                border: 1px solid #444444;
                border-radius: 5px;
            }
            QListWidget {
                background-color: #3C3C3C;
                border: 1px solid #555555;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #007ACC;
                color: white;
            }
            QLineEdit, QComboBox {
                background-color: #3C3C3C;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 3px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png); /* For a custom arrow, otherwise uses system default */
            }
            QPushButton {
                border: 1px solid #555555;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QPushButton:pressed {
                background-color: #5A5A5A;
            }
            QGroupBox {
                border: 1px solid #555555;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QStatusBar {
                background-color: #222222;
                font-weight: bold;
            }
            QSplitter::handle {
                background-color: #444444;
            }
        """)

        self.uncropped_files = []
        self.ready_to_export = {}
        self.init_ui()
        self.connect_signals()
        self.setAcceptDrops(True)
        self.update_crop_overlay()
        self.update_ui_state()

    def init_ui(self):
        # ... (This method has ONE change at the very end for the status bar) ...
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_panel_layout = QVBoxLayout(left_panel)
        self.uncropped_list = QListWidget()
        self.ready_list = QListWidget()
        left_panel_layout.addWidget(QLabel("<b>Uncropped Images</b>"))
        left_panel_layout.addWidget(self.uncropped_list)
        left_panel_layout.addWidget(QLabel("<b>Ready to Export</b>"))
        left_panel_layout.addWidget(self.ready_list)
        splitter.addWidget(left_panel)
        self.canvas = ImageCanvas()
        splitter.addWidget(self.canvas)
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_panel_layout = QVBoxLayout(right_panel)
        settings_group = QGroupBox("Crop Settings")
        settings_layout = QGridLayout()
        settings_layout.addWidget(QLabel("Width:"), 0, 0)
        self.width_input = QLineEdit("236")
        settings_layout.addWidget(self.width_input, 0, 1)
        settings_layout.addWidget(QLabel("Height:"), 1, 0)
        self.height_input = QLineEdit("295")
        settings_layout.addWidget(self.height_input, 1, 1)
        settings_layout.addWidget(QLabel("Units:"), 2, 0)
        self.units_combo = QComboBox()
        self.units_combo.addItems(["Pixels", "Inches", "Centimeters"])
        self.units_combo.setCurrentText("Pixels")
        settings_layout.addWidget(self.units_combo, 2, 1)
        settings_layout.addWidget(QLabel("DPI:"), 3, 0)
        self.dpi_input = QLineEdit("300")
        settings_layout.addWidget(self.dpi_input, 3, 1)
        settings_group.setLayout(settings_layout)
        right_panel_layout.addWidget(settings_group)
        self.confirm_button = QPushButton("Confirm & Next →")
        self.confirm_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.save_all_button = QPushButton("Save All...")
        self.save_all_button.setStyleSheet("background-color: #008CBA; color: white;")
        right_panel_layout.addStretch()
        right_panel_layout.addWidget(self.confirm_button)
        right_panel_layout.addWidget(self.save_all_button)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 700, 250])
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # --- NEW: Animated, clickable status bar message ---
        self.status_label = ClickableLabel("Developed by RUDRA MONDAL")
        self.statusBar.addPermanentWidget(self.status_label)
        self.statusBar.showMessage("Ready")

    # All other methods in MainWindow remain unchanged.
    # No need to copy them again.
    # connect_signals(), dragEnterEvent(), dropEvent(), populate_list_widgets(),
    # display_selected_image(), update_crop_overlay(), get_target_pixel_size(),
    # confirm_and_next(), save_all_images(), update_ui_state() are all the same.
    # For completeness, I'll include them here, but they are identical to before.

    def connect_signals(self):
        self.width_input.textChanged.connect(self.update_crop_overlay)
        self.height_input.textChanged.connect(self.update_crop_overlay)
        self.units_combo.currentIndexChanged.connect(self.update_crop_overlay)
        self.dpi_input.textChanged.connect(self.update_crop_overlay)
        self.uncropped_list.currentItemChanged.connect(self.display_selected_image)
        self.ready_list.currentItemChanged.connect(self.display_selected_image)
        self.confirm_button.clicked.connect(self.confirm_and_next)
        self.save_all_button.clicked.connect(self.save_all_images)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        new_files = []
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.splitext(file_path)[1].lower() in valid_extensions:
                if file_path not in self.uncropped_files and file_path not in self.ready_to_export:
                    new_files.append(file_path)
        if new_files:
            self.uncropped_files.extend(new_files)
            self.populate_list_widgets()
            if self.uncropped_list.count() > 0 and self.uncropped_list.currentRow() == -1:
                self.uncropped_list.setCurrentRow(0)
        self.update_ui_state()

    def populate_list_widgets(self):
        self.uncropped_list.blockSignals(True)
        self.ready_list.blockSignals(True)
        self.uncropped_list.clear()
        self.ready_list.clear()
        for f in self.uncropped_files:
            item = QListWidgetItem(os.path.basename(f))
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.uncropped_list.addItem(item)
        for f in self.ready_to_export:
            item = QListWidgetItem(f"✓ {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setForeground(QColor("#4DFF8F")) # Use a bright green for dark theme
            self.ready_list.addItem(item)
        self.uncropped_list.blockSignals(False)
        self.ready_list.blockSignals(False)

    def display_selected_image(self, current_item, previous_item):
        if not current_item:
            self.canvas.set_image(None)
            return
        if self.sender() == self.uncropped_list:
            self.ready_list.setCurrentItem(None)
        else:
            self.uncropped_list.setCurrentItem(None)
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        self.canvas.set_image(file_path)
        self.statusBar.showMessage(f"Editing: {os.path.basename(file_path)}")

    def update_crop_overlay(self):
        try:
            width = float(self.width_input.text())
            height = float(self.height_input.text())
            self.canvas.set_crop_aspect_ratio(width, height)
        except ValueError:
            self.canvas.set_crop_aspect_ratio(1, 1)
        is_physical_unit = self.units_combo.currentText() in ["Inches", "Centimeters"]
        self.dpi_input.setEnabled(is_physical_unit)

    def get_target_pixel_size(self):
        try:
            width = float(self.width_input.text())
            height = float(self.height_input.text())
            dpi = int(self.dpi_input.text())
            units = self.units_combo.currentText()
            if units == "Pixels":
                return (int(width), int(height))
            elif units == "Inches":
                return (int(width * dpi), int(height * dpi))
            elif units == "Centimeters":
                cm_to_inch = 0.393701
                return (int(width * cm_to_inch * dpi), int(height * cm_to_inch * dpi))
        except (ValueError, ZeroDivisionError):
            return None

    def confirm_and_next(self):
        current_item = self.uncropped_list.currentItem()
        if not current_item: return
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        crop_rect = self.canvas.get_crop_parameters()
        target_size = self.get_target_pixel_size()
        if not crop_rect or crop_rect.width() == 0 or crop_rect.height() == 0:
            QMessageBox.warning(self, "Crop Error", "The crop area is invalid. Please adjust pan/zoom.")
            return
        if not target_size or target_size[0] == 0 or target_size[1] == 0:
            QMessageBox.warning(self, "Input Error", "The target dimensions are invalid. Please check your inputs.")
            return
        dpi = int(self.dpi_input.text()) if self.dpi_input.isEnabled() else 72
        self.ready_to_export[file_path] = {'crop_rect': crop_rect, 'dpi': dpi, 'target_size': target_size}
        current_row = self.uncropped_list.row(current_item)
        self.uncropped_files.pop(current_row)
        self.populate_list_widgets()
        if self.uncropped_list.count() > 0:
            next_row = min(current_row, self.uncropped_list.count() - 1)
            self.uncropped_list.setCurrentRow(next_row)
        else:
            self.canvas.set_image(None)
            self.statusBar.showMessage("All images cropped. Ready to save.")
        self.update_ui_state()

    def save_all_images(self):
        if not self.ready_to_export:
            QMessageBox.information(self, "No Images", "There are no cropped images to save.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if not folder: return
        self.statusBar.showMessage("Saving images...")
        processed_count = 0
        total_count = len(self.ready_to_export)
        for file_path, params in self.ready_to_export.items():
            try:
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)
                output_path = os.path.join(folder, f"{name}_cropped{ext}")
                img = Image.open(file_path)
                rect = params['crop_rect']
                box = (rect.left(), rect.top(), rect.right(), rect.bottom())
                cropped_img = img.crop(box)
                target_size = params['target_size']
                final_img = cropped_img.resize(target_size, Image.Resampling.LANCZOS)
                dpi_value = (params['dpi'], params['dpi'])
                if ext.lower() in ['.jpg', '.jpeg']:
                    final_img.save(output_path, 'jpeg', dpi=dpi_value, quality=95)
                else:
                    final_img.save(output_path, dpi=dpi_value)
                processed_count += 1
                self.statusBar.showMessage(f"Saving... {processed_count}/{total_count}")
                QApplication.processEvents()
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Could not save {base_name}.\nError: {e}")
                break
        QMessageBox.information(self, "Export Complete", f"Successfully saved {processed_count} images to:\n{folder}")
        self.statusBar.showMessage("Ready")
        
    def update_ui_state(self):
        self.confirm_button.setEnabled(self.uncropped_list.count() > 0 and self.uncropped_list.currentItem() is not None)
        self.save_all_button.setEnabled(len(self.ready_to_export) > 0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())