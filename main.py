import sys
from PyQt5.QtWidgets import QApplication
from dashboard import Dashboard

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_()) 