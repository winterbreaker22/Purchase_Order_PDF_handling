import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QMainWindow,
    QGraphicsRectItem, QToolBar, QAction
)
from PyQt5.QtGui import (
    QPixmap, QBrush, QPen, QImage, QColor, QCursor
)
from PyQt5.QtCore import (
    Qt, QRectF, QPointF
)


class ResizeHandleItem(QGraphicsRectItem):
    def __init__(self, parent, handle_pos):
        super().__init__(parent=parent)
        self.handle_pos = handle_pos

        # Een klein vierkantje (8x8 px), gecentreerd rond (0,0)
        self.setRect(-4, -4, 8, 8)

        self.setBrush(QBrush(QColor("white")))
        self.setPen(QPen(QColor("blue"), 1))

        self.setFlags(
            self.ItemIsMovable
            | self.ItemIsSelectable
            | self.ItemSendsGeometryChanges
        )

        # Cursor instellen afhankelijk van de handle-positie
        if self.handle_pos in ("top-left", "bottom-right"):
            self.setCursor(QCursor(Qt.SizeFDiagCursor))
        elif self.handle_pos in ("top-right", "bottom-left"):
            self.setCursor(QCursor(Qt.SizeBDiagCursor))
        elif "left" in self.handle_pos or "right" in self.handle_pos:
            self.setCursor(QCursor(Qt.SizeHorCursor))
        else:
            self.setCursor(QCursor(Qt.SizeVerCursor))

    def mousePressEvent(self, event):
        parent = self.parentItem()
        if not parent.isSelected():
            print(f"[DEBUG] Handle clicked on {self.handle_pos}, parent {parent} is NOT selected -> selecting parent.")
            parent.setSelected(True)
            event.accept()
            return
        else:
            print(f"[DEBUG] Handle clicked on {self.handle_pos}, parent {parent} is already selected. (Ready to resize)")
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        print(f"[DEBUG] Handle released on {self.handle_pos}.")
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == self.ItemPositionChange and self.scene():
            # Wordt aangeroepen bij bewegen (drag) van de handle
            new_pos = value
            self.updateParentRect(new_pos)
            return new_pos
        return super().itemChange(change, value)

    def updateParentRect(self, handle_local_pos):
        parent = self.parentItem()
        if not parent:
            return

        rect = parent.rect()
        px, py = handle_local_pos.x(), handle_local_pos.y()
        left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()

        if "left" in self.handle_pos:
            left = px
        if "right" in self.handle_pos:
            right = px
        if "top" in self.handle_pos:
            top = py
        if "bottom" in self.handle_pos:
            bottom = py

        new_rect = QRectF(QPointF(left, top), QPointF(right, bottom)).normalized()

        # Debug:
        print(f"[DEBUG] updateParentRect from handle '{self.handle_pos}' -> old rect: {rect}, new rect: {new_rect}")

        if new_rect.width() > 5 and new_rect.height() > 5:
            parent.setRect(new_rect)


class ResizableRectItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)

        self._defaultPen = QPen(QColor("black"), 1, Qt.DashLine)
        self._hoverPen = QPen(QColor("blue"), 1, Qt.DashLine)
        self.setPen(self._defaultPen)
        self.setBrush(QBrush(Qt.transparent))

        self.setFlags(
            self.ItemIsMovable
            | self.ItemIsSelectable
            | self.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.SizeAllCursor))

        self.handles = []
        self.initHandles()

        # Beginstatus: handles uit, tot het item geselecteerd is
        self.showHandles(False)

    def initHandles(self):
        handle_positions = [
            ("top-left",       0.0, 0.0),
            ("top-center",     0.5, 0.0),
            ("top-right",      1.0, 0.0),
            ("right-center",   1.0, 0.5),
            ("bottom-right",   1.0, 1.0),
            ("bottom-center",  0.5, 1.0),
            ("bottom-left",    0.0, 1.0),
            ("left-center",    0.0, 0.5),
        ]
        for (name, rx, ry) in handle_positions:
            h = ResizeHandleItem(self, name)
            self.handles.append((h, rx, ry))
        self.updateHandlesPos()

    def updateHandlesPos(self):
        r = self.rect()
        for (handle, rx, ry) in self.handles:
            hx = r.x() + rx * r.width()
            hy = r.y() + ry * r.height()
            handle.setPos(hx, hy)

    def setRect(self, newRect):
        print(f"[DEBUG] setRect called with {newRect}")
        super().setRect(newRect)
        self.updateHandlesPos()

    def mousePressEvent(self, event):
        if not self.isSelected() and event.button() == Qt.LeftButton:
            print("[DEBUG] Rect clicked and selected.")
            self.setSelected(True)
            print("[DEBUG] Rect selected.")
            event.accept()
            return
        else:
            print("[DEBUG] Rect mousePressEvent -> already selected or non-left click.")
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        print("[DEBUG] Rect mouseReleaseEvent.")
        super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event):
        print("[DEBUG] Rect hoverEnter.")
        self.setPen(self._hoverPen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        print("[DEBUG] Rect hoverLeave.")
        if not self.isSelected():
            self.setPen(self._defaultPen)
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == self.ItemSelectedChange:
            is_now_selected = bool(value)
            print(f"[DEBUG] Rect itemChange -> ItemSelectedChange = {is_now_selected}")
            self.showHandles(is_now_selected)
            if is_now_selected:
                print("[DEBUG] Rect is now selected -> setPen(hoverPen).")
                self.setPen(self._hoverPen)
            else:
                print("[DEBUG] Rect is now deselected -> setPen(defaultPen).")
                self.setPen(self._defaultPen)
        elif change == self.ItemPositionChange:
            # Wordt aangeroepen als de rect verschoven wordt
            print(f"[DEBUG] Rect itemChange -> ItemPositionChange: new pos = {value}")
        return super().itemChange(change, value)

    def showHandles(self, visible):
        for (handle, _, _) in self.handles:
            handle.setVisible(visible)


class PDFEditor(QMainWindow):
    def __init__(self, pdf_path):
        super().__init__()
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.page = self.doc[0]
        self.bounding_boxes = []

        self.initUI()

    def initUI(self):
        self.setWindowTitle("PDF Editor with Debug")
        self.setGeometry(100, 100, 1000, 700)

        self.view = QGraphicsView(self)
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)

        self.createToolbar()

        self.render_pdf()
        self.draw_bounding_boxes()

    def createToolbar(self):
        toolbar = QToolBar("Tools", self)
        self.addToolBar(toolbar)

        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.zoomIn)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoomOut)
        toolbar.addAction(zoom_out_action)

    def zoomIn(self):
        self.view.scale(1.2, 1.2)

    def zoomOut(self):
        self.view.scale(1/1.2, 1/1.2)

    def render_pdf(self):
        # Gewoon 72 dpi hier; pas aan naar wens
        pix = self.page.get_pixmap(dpi=72)
        image_data = pix.tobytes("png")
        qt_image = QImage.fromData(image_data)
        pixmap = QPixmap.fromImage(qt_image)

        pixmap_item = self.scene.addPixmap(pixmap)
        pixmap_item.setZValue(-100)

    def draw_bounding_boxes(self):
        words = self.page.get_text("words")
        # Dit stukje code merge “words” tot regels, niet super relevant voor debug
        merged_boxes = []
        horizontal_threshold = 5
        vertical_threshold = 2

        for word in words:
            x0, y0, x1, y1, text = word[:5]
            if not merged_boxes:
                merged_boxes.append([x0, y0, x1, y1])
            else:
                last_box = merged_boxes[-1]
                if (abs(last_box[1] - y0) <= vertical_threshold
                        and abs(last_box[3] - y1) <= vertical_threshold
                        and (x0 - last_box[2]) <= horizontal_threshold):
                    last_box[2] = max(last_box[2], x1)
                    last_box[3] = max(last_box[3], y1)
                else:
                    merged_boxes.append([x0, y0, x1, y1])

        for box in merged_boxes:
            x0, y0, x1, y1 = box
            w = x1 - x0
            h = y1 - y0
            rect_item = ResizableRectItem(x0, y0, w, h)
            rect_item.setZValue(10)
            self.scene.addItem(rect_item)
            self.bounding_boxes.append(rect_item)

    def save_pdf(self):
        # Voorbeeld
        for rect_item in self.bounding_boxes:
            x0 = rect_item.rect().x()
            y0 = rect_item.rect().y()
            x1 = x0 + rect_item.rect().width()
            y1 = y0 + rect_item.rect().height()

            rect = fitz.Rect(x0, y0, x1, y1)
            self.page.draw_rect(rect, color=(1, 0, 0), width=0.5)

        self.doc.save("edited_output.pdf")
        print("PDF saved as 'edited_output.pdf'")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = PDFEditor("496.pdf")  # <-- vervang door jouw eigen PDF
    editor.show()
    sys.exit(app.exec_())
