import sys
import sqlite3
import os
import shutil
import win32print
import base64
from datetime import date, datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFormLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QMessageBox, QDialog, QListWidget, QInputDialog,
    QDateEdit, QHeaderView, QFrame, QGridLayout, QStyle,
    QFileDialog, QCheckBox, QStackedWidget, QSizePolicy, QCompleter, QMenu, QGraphicsColorizeEffect, QListWidgetItem
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtGui import (
    QKeySequence, QShortcut, QFont, QTextDocument, QPageSize, QPageLayout, QIcon, QColor, QPixmap,
)
from PyQt6.QtCore import Qt, QDate, QSizeF, QMarginsF, QPoint, pyqtSignal, QEventLoop


DB_NAME = "nbs.db"
ENTRY_TYPES = ["Income", "Expense", "Capital"]
INCOME_CATEGORIES = ["Sales", "Services"]
PAYROLL_TYPES = ["Salary Payment", "Advance"]

def get_conn():
    return sqlite3.connect(DB_NAME)

def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols

def init_db():
    conn = get_conn()
    c = conn.cursor()
    # Define all required tables and their columns
    tables = [
        ('''CREATE TABLE IF NOT EXISTS expense_categories (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        )''', None),
        ('''CREATE TABLE IF NOT EXISTS daily_expense (
            id INTEGER PRIMARY KEY,
            date TEXT,
            amount REAL,
            category_id INTEGER,
            description TEXT,
            notes TEXT,
            FOREIGN KEY(category_id) REFERENCES expense_categories(id)
        )''', None),
        
        ('''CREATE TABLE IF NOT EXISTS income_categories (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        )''', None),
        ('''CREATE TABLE IF NOT EXISTS daily_income (
            id INTEGER PRIMARY KEY,
            date TEXT,
            amount REAL,
            category_id INTEGER,
            description TEXT,
            notes TEXT,
            FOREIGN KEY(category_id) REFERENCES income_categories(id)
        )''', None),
        ('''CREATE TABLE IF NOT EXISTS cheques (
            id INTEGER PRIMARY KEY,
            cheque_date TEXT,
            company_name TEXT,
            bank_name TEXT,
            due_date TEXT,
            amount REAL,
            is_paid INTEGER DEFAULT 0
        )''', None),
        ('''CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            designation TEXT,
            salary REAL DEFAULT 0,
            joining_date TEXT,
            loan_balance REAL DEFAULT 0,
            photo_path TEXT
         )''', None),
         ('''CREATE TABLE IF NOT EXISTS employee_payroll (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER,
            date TEXT,
            type TEXT,
            amount REAL,
            debit REAL,
            credit REAL,
            balance REAL,
            notes TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
          )''', None),
        ('''CREATE TABLE IF NOT EXISTS daily_capital (
            id INTEGER PRIMARY KEY,
            date TEXT,
            amount REAL,
            category TEXT,
            description TEXT,
            notes TEXT
        )''', None),


    ]

    for stmt, _ in tables:
        c.execute(stmt)
    ensure_default_income_categories()

# --- Helper functions ---
def get_income_categories():
    with get_conn() as conn:
        return conn.execute("SELECT id, name FROM income_categories").fetchall()

def get_expense_categories():
    with get_conn() as conn:
        return conn.execute("SELECT id, name FROM expense_categories").fetchall()

def to_ddmmyyyy(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return iso

def to_month(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%B")
    except Exception:
        return ""

def to_iso_date(ddmmyyyy):
    try:
        return datetime.strptime(ddmmyyyy, "%d-%m-%Y").strftime("%Y-%m-%d")
    except Exception:
        return ddmmyyyy

def days_remaining(due_date_str):
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        today = date.today()
        return (due_date - today).days
    except Exception:
        return None

def get_all_descriptions():
    with get_conn() as conn:
        income_descs = [row[0] for row in conn.execute("SELECT DISTINCT description FROM daily_income WHERE description IS NOT NULL AND description <> ''")]
        expense_descs = [row[0] for row in conn.execute("SELECT DISTINCT description FROM daily_expense WHERE description IS NOT NULL AND description <> ''")]
    return list(set(income_descs + expense_descs))

def parse_amount(text):
    """
    Attempts to parse a float amount from the given text.
    Returns 0 if the text is empty, invalid, or cannot be parsed.
    """
    try:
        return float(text.strip())
    except Exception:
        return 0

def ensure_default_income_categories():
    conn = get_conn()
    c = conn.cursor()
    for name in INCOME_CATEGORIES:
        c.execute("INSERT OR IGNORE INTO income_categories (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background: #181A1B;
    color: #F1F3F4;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}
QLabel { color: #F1F3F4; font-size: 15px; }
QTabWidget::pane {
    border: none;
    border-top: 2px solid #5a3a12;
    background: #181A1B;
    border-radius: 0px 0px 0 0;
    margin: 10px 6px 6px 6px; /* top right bottom left */
}
QTabBar::tab {
    background: #232627;
    color: #cfcfcf;
    border-radius: 5px 5px 0 0;
    padding: 8px 14px;
    margin-left: 10px;
    margin-top: 6px;
    font-size: 15px;
    min-width: 100px;
}
QTabBar::tab:selected {
    background: #26292A;
    color: #fff;
    font-weight: bold;
    border: 2px solid #fb700e;
    border-radius: 5px 5px 0 0;
}
QLineEdit, QComboBox, QDateEdit, QTextEdit {
    background: #232627;
    color: #F1F3F4;
    border: 1.3px solid #35393A;
    border-radius: 5px;
    padding: 8px;
    font-size: 15px;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {
    border: 1.7px solid #6C7A89;
}
QPushButton {
    background: #232627;
    color: #F1F3F4;
    border-radius: 5px;
    padding: 8px 20px;
    font-size: 15px;
    border: 1px solid #35393A;
}
QPushButton:pressed { background: #35393A; }
QPushButton:disabled { background: #232627; color: #555; }
QTableWidget {
    background: #181A1B;
    color: #F1F3F4;
    gridline-color: #232627;
    font-size: 15px;
}
QHeaderView::section {
    background-color: #2A2C2E;
    color: #F1F3F4;
    font-weight: bold;
    font-size: 15px;
    border: none;
    border-radius: 0;
    padding: 4px;
}
QTableWidget QTableCornerButton::section { background: #232627; }
QFrame#totalsbox { background: #232627; border-radius: 12px; color: #F1F3F4; }
QListWidget {
    background: #232627;
    color: #F1F3F4;
    border-radius: 5px;
    padding: 5px;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #232627;
    width: 12px;
    margin: 0px;
    border-radius: 5px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #35393A;
    border-radius: 5px;
}
QToolTip {
    background: #35393A;
    color: #F1F3F4;
    border: 1px solid #6C7A89;
}
QComboBox {
    background: #232627;
    padding: 8px 14px;
    min-width: 120px;
    border-radius: 1px;
}
QTabWidget#mainTabs QTabBar::tab:selected {
    color: #fb700e;
}

"""

DIALOG_STYLESHEET = """
QDialog { background: #181A1B; }
QLabel { font-size: 15px; font-weight: 600; color: #F1F3F4; }
QLineEdit, QComboBox, QDateEdit {
    border-radius: 5px; padding: 8px; font-size: 14px;
    border: 1.3px solid #35393A; background: #232627; color: #F1F3F4;
}
QPushButton {
    border-radius: 5px; padding: 9px 18px; font-size: 14px;
    background: #26292A; color: #F1F3F4; font-weight: bold;
}
QPushButton:pressed { background: #35393A; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border: 2px solid #fb700e; }
"""

# You may define more as needed, e.g.:
FORM_STYLESHEET = """
QFormLayout QLabel { color: #F1F3F4; }
"""

CHECKBOX_STYLESHEET = """
QCheckBox {
    background-color: #3A3A3C;
    color: #F1F3F4;
    font-size: 13px;
    padding: 0px 4px 0px 2px;   /* top, right, bottom, left */
    border: 1.3px solid #5F6368;
    border-radius: 4px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    margin: 1px 6px 1px 2px;    /* top, right, bottom, left (between box and label) */
}
QCheckBox:checked {
    background-color: #1E8E3E;
    color: white;
    border-color: #1E8E3E;
}
"""

# ---------------- Dialog and Tab Classes ----------------

class EntryEditDialog(QDialog):
    def __init__(self, entry_type, entry_id, date, cat_id, amount, desc, notes='', parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Entry")
        self.entry_type = entry_type
        self.entry_id = entry_id
        self.setMinimumWidth(390)
        self.setStyleSheet(DIALOG_STYLESHEET)
        self.layout = QVBoxLayout(self)
        form = QFormLayout()
        self.date_input = QDateEdit()
        self.date_input.setDisplayFormat("dd-MM-yyyy")
        self.date_input.setCalendarPopup(True)
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            self.date_input.setDate(QDate(dt.year, dt.month, dt.day))
        except Exception:
            self.date_input.setDate(QDate.currentDate())
        form.addRow("Date:", self.date_input)
        self.cat_combo = QComboBox()
        if entry_type == "Income":
            for cid, name in get_income_categories():
                self.cat_combo.addItem(name, cid)
        else:
            for cid, name in get_expense_categories():
                self.cat_combo.addItem(name, cid)
        idx = self.cat_combo.findData(cat_id)
        if idx != -1:
            self.cat_combo.setCurrentIndex(idx)
        form.addRow("Category:", self.cat_combo)
        self.desc_input = QLineEdit(desc or "")
        form.addRow("Description:", self.desc_input)
        self.amount_input = QLineEdit(str(amount))
        self.amount_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form.addRow("Amount (AED):", self.amount_input)
        self.notes_input = QLineEdit(notes or "")
        self.notes_input.setPlaceholderText("Notes (optional)")
        form.addRow("Notes:", self.notes_input)
        self.layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_entry)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_form)
        for b in [self.save_btn, self.delete_btn, self.clear_btn]:
            btn_row.addWidget(b)
        self.layout.addLayout(btn_row)
        self.deleted = False

    def get_values(self):
        date_iso = self.date_input.date().toString("yyyy-MM-dd")
        return (
            date_iso,
            self.cat_combo.currentData(),
            parse_amount(self.amount_input.text()),
            self.desc_input.text(),
            self.notes_input.text()
        )

    def delete_entry(self):
        self.deleted = True
        self.accept()

    def clear_form(self):
        self.date_input.setDate(QDate.currentDate())
        self.cat_combo.setCurrentIndex(0)
        self.desc_input.clear()
        self.amount_input.clear()

class IncomeExpenseEntryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Transaction")
        self.setMinimumWidth(450)
        self.setMaximumWidth(500)
        self.setStyleSheet(DIALOG_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Add Income / Expense / Capital")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet("font-size:17px; font-weight:600; margin-bottom:8px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # Date
        self.date_input = QDateEdit()
        self.date_input.setDisplayFormat("dd-MM-yyyy")
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        form.addRow("Date", self.date_input)

        # Type
        self.type_input = QComboBox()
        self.type_input.addItems(ENTRY_TYPES)
        form.addRow("Type", self.type_input)

        # Category
        self.category_input = QComboBox()
        form.addRow("Category", self.category_input)

        # Description
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Description")
        self.description_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        desc_completer = QCompleter(get_all_descriptions())
        desc_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.description_input.setCompleter(desc_completer)
        form.addRow("Description", self.description_input)

        # Notes
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Notes (optional)")
        self.notes_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        form.addRow("Notes", self.notes_input)

        layout.addLayout(form)

        # Amount (centered, bold, larger)
        amount_row = QHBoxLayout()
        amount_row.addStretch()
        self.amount_input = QLineEdit()
        self.amount_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.amount_input.setPlaceholderText("Amount (AED)")
        afont = QFont()
        afont.setPointSize(20)
        afont.setBold(True)
        self.amount_input.setFont(afont)
        self.amount_input.setFixedWidth(220)
        amount_row.addWidget(self.amount_input)
        amount_row.addStretch()
        layout.addLayout(amount_row)

        # Button row (centered)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(5)
        btn_row.addStretch()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_entry)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_form)
        for b in [self.save_btn, self.delete_btn, self.clear_btn]:
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        self.deleted = False

        self.type_input.currentTextChanged.connect(self.update_category_options)
        self.category_input.currentIndexChanged.connect(self.handle_category_change)
        self.type_input.currentTextChanged.connect(self.update_amount_placeholder_color)
        self.update_category_options()
        self.update_amount_placeholder_color(self.type_input.currentText())

    def update_category_options(self, *_):
        t = self.type_input.currentText()
        self.category_input.blockSignals(True)
        self.category_input.clear()
        if t == ENTRY_TYPES[0]:
            for cid, name in get_income_categories():
                self.category_input.addItem(name, cid)
        elif t == ENTRY_TYPES[1]:
            for cid, name in get_expense_categories():
                if name.strip().lower() == "vendors":
                    continue
                self.category_input.addItem(name, cid)
        elif t == ENTRY_TYPES[2]:
            self.category_input.addItem("Additional Capital", "additional_capital")
        self.category_input.blockSignals(False)

    def handle_category_change(self):
        pass

    def update_amount_placeholder_color(self, t):
        color = "#43a047" if t == "Income" else "#e53935"
        if t == "Capital":
            color = "#1976d2"
        self.amount_input.setStyleSheet(
            f"""
            QLineEdit {{
                background: #232627;
                color: #F1F3F4;
                border-radius: 10px;
                border: 1.3px solid #35393A;
                font-size: 20px;
                font-weight:bold;
            }}
            QLineEdit::placeholder {{
                color: {color};
                font-weight: bold;
                letter-spacing: 1px;
            }}
            """
        )

    def clear_form(self):
        self.date_input.setDate(QDate.currentDate())
        self.type_input.setCurrentIndex(0)
        self.category_input.setCurrentIndex(0)
        self.description_input.clear()
        self.amount_input.clear()
        self.notes_input.clear()

    def delete_entry(self):
        self.deleted = True
        self.accept()

    def get_values(self):
        date_iso = self.date_input.date().toString("yyyy-MM-dd")
        desc = self.description_input.text()
        notes = self.notes_input.text()
        return (
            date_iso,
            self.type_input.currentText(),
            self.category_input.currentData(),
            self.amount_input.text(),
            desc,
            notes
        )

class FilterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        vbox = QVBoxLayout(self)
        filter_layout = QHBoxLayout()
        self.setStyleSheet(DIALOG_STYLESHEET)

        # --- Month Combo ---
        self.month_combo = QComboBox()
        self.month_combo.addItem("All Months", None)
        for m in range(1, 13):
            self.month_combo.addItem(QDate(2000, m, 1).toString("MMMM"), m)
        current_month = QDate.currentDate().month()
        self.month_combo.setCurrentIndex(current_month)  # Default to current month
        self.month_combo.currentIndexChanged.connect(self.on_month_selected)
        

        self.date_from = QDateEdit()
        self.date_from.setDisplayFormat("dd-MM-yyyy")
        self.date_from.setCalendarPopup(True)
        self.date_from.setMinimumWidth(120) 

        self.date_to = QDateEdit()
        self.date_to.setDisplayFormat("dd-MM-yyyy")
        self.date_to.setCalendarPopup(True)
        self.date_to.setMinimumWidth(120) 

        today = QDate.currentDate()
        first_of_month = QDate(today.year(), today.month(), 1)
        self.date_from.setDate(first_of_month)
        self.date_to.setDate(today)

        self.category_input = QComboBox()
        self.category_input.addItem("All", None)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Description contains...")
        # Auto-complete for Description
        desc_completer = QCompleter(get_all_descriptions())
        desc_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.description_input.setCompleter(desc_completer)

        filter_layout.addWidget(QLabel("Month:"))
        filter_layout.addWidget(self.month_combo)

        filter_layout.addWidget(QLabel("From:"))
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(QLabel("To:"))
        filter_layout.addWidget(self.date_to)
        filter_layout.addWidget(QLabel("Category:"))
        filter_layout.addWidget(self.category_input)
        filter_layout.addWidget(self.description_input)

        self.clear_button = QPushButton("Clear All Filters")
        filter_layout.addWidget(self.clear_button)
        self.clear_button.clicked.connect(self.clear_all_filters)

        vbox.addLayout(filter_layout)
        self.refresh_categories()

    def refresh_categories(self):
        self.category_input.clear()
        self.category_input.addItem("All", None)
        for cid, name in get_income_categories():
            self.category_input.addItem(f"Income: {name}", f"inc:{cid}")
        for cid, name in get_expense_categories():
            self.category_input.addItem(f"Expense: {name}", f"exp:{cid}")
        self.category_input.addItem("Capital: Additional Capital", "capital:additional_capital")

    def clear_all_filters(self):
        today = QDate.currentDate()
        first_of_month = QDate(today.year(), today.month(), 1)
        self.date_from.setDate(first_of_month)
        self.date_to.setDate(today)
        self.month_combo.setCurrentIndex(QDate.currentDate().month())  # selects current month
        self.category_input.setCurrentIndex(0)
        self.description_input.clear()

    def on_month_selected(self):
        month = self.month_combo.currentData()
        today = QDate.currentDate()
        year = today.year()
        if month is None:
            first = QDate(year, 1, 1)
            last = QDate(year, 12, 31)
            self.date_from.setDate(first)
            self.date_to.setDate(last)
        else:
            first = QDate(year, month, 1)
            last = first.addMonths(1).addDays(-1)
            self.date_from.setDate(first)
            if month == today.month() and year == today.year():
                self.date_to.setDate(today)
            else:
                self.date_to.setDate(last)

class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_month = date.today().month
        self.selected_year = date.today().year
        self.setStyleSheet(DIALOG_STYLESHEET)
        self.layout = QVBoxLayout(self)

        # Header
        title = QLabel("Dashboard", self)
        title.setObjectName("dashboardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(title)
        subtitle = QLabel("Quick snapshot of your business finances", self)
        subtitle.setObjectName("dashboardSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(subtitle)

        # Month/Year Picker Row
        self.topRow = QHBoxLayout()
        self.month_combo = QComboBox()
        for m in range(1, 13):
            self.month_combo.addItem(QDate(2000, m, 1).toString("MMMM"), m)
        self.month_combo.setCurrentIndex(self.selected_month - 1)
        self.month_combo.currentIndexChanged.connect(self.set_month)

        self.year_combo = QComboBox()
        for y in range(date.today().year, 1999, -1):
            self.year_combo.addItem(str(y), y)
        self.year_combo.setCurrentText(str(self.selected_year))
        self.year_combo.currentIndexChanged.connect(self.set_month)

        self.export_pdf_btn = QPushButton("Export PDF")
        self.export_pdf_btn.setIcon(QIcon.fromTheme("document-save"))
        self.export_pdf_btn.setStyleSheet("""
            QPushButton {
                background: #fb700e;
                color: #fff;
                border-radius: 12px;
                font-weight: 600;
                padding: 8px 18px;
                font-size: 16px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: #ff9800;
            }
        """)
        self.export_pdf_btn.clicked.connect(self.export_monthly_report_pdf)

        self.topRow.addWidget(QLabel("Month:", self))
        self.topRow.addWidget(self.month_combo)
        self.topRow.addWidget(QLabel("Year:", self))
        self.topRow.addWidget(self.year_combo)
        self.topRow.addStretch()
        self.topRow.addWidget(self.export_pdf_btn)
        self.layout.addLayout(self.topRow)

        # Modern Rectangle KPI Cards Section in a grid
        self.kpiGrid = QGridLayout()
        self.kpiGrid.setSpacing(18)
        self.layout.addSpacing(18)
        self.layout.addLayout(self.kpiGrid)

        self.layout.addStretch(1)
        self.refresh()
    
    def kpi_card_rect(self, icon, title, value, color):
            card = QFrame()
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card.setStyleSheet(f"background: {color}; border-radius: 13px;")
            v = QVBoxLayout(card)
            v.setContentsMargins(12, 16, 12, 16)
            v.setSpacing(5)

            icon_label = QLabel(icon)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            icon_label.setStyleSheet("font-size: 32px; margin-bottom: 2px;")
            v.addWidget(icon_label)

            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            title_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #fff;")
            v.addWidget(title_label)

            value_label = QLabel(value)
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            value_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #fff;")
            v.addWidget(value_label)

            v.addStretch()
            return card

    def set_month(self):
        self.selected_month = self.month_combo.currentData()
        self.selected_year = self.year_combo.currentData()
        self.refresh()


    def refresh(self):
        # Remove old KPI cards
        for i in reversed(range(self.kpiGrid.count())):
            w = self.kpiGrid.itemAt(i).widget()
            if w:
                self.kpiGrid.removeWidget(w)
                w.deleteLater()

        conn = get_conn()
        c = conn.cursor()
        q_month = f"{self.selected_month:02}"
        q_year = str(self.selected_year)
        c.execute("SELECT SUM(amount) FROM daily_income WHERE strftime('%m', date)=? AND strftime('%Y', date)=?", (q_month, q_year))
        income = c.fetchone()[0] or 0
        c.execute("SELECT SUM(amount) FROM daily_expense WHERE strftime('%m', date)=? AND strftime('%Y', date)=?", (q_month, q_year))
        expenses = c.fetchone()[0] or 0
        balance = income - expenses
        profit_percent = (balance / income * 100) if income > 0 else 0

        card_data = [
            ("\U0001F4B0", "Total Income", f"{income:,.2f} AED", "#43a047"),
            ("\U0001F4B8", "Total Expenses", f"{expenses:,.2f} AED", "#e53935"),
            ("\U0001F4B5", "Balance", f"{balance:,.2f} AED", "#fbc02d" if balance >= 0 else "#e53935"),
            ("\U0001F4C8", "Profit %", f"{profit_percent:,.2f} %", "#43a047" if profit_percent >= 0 else "#e53935"),
            ]
        

        # Arrange cards in a grid: 3 in first row, 2 in second row
        num_columns = 3
        for idx, data in enumerate(card_data):
            row = idx // num_columns
            col = idx % num_columns
            self.kpiGrid.addWidget(self.kpi_card_rect(*data), row, col)

        conn.close()

    def export_monthly_report_pdf(self):
        month = self.selected_month
        year = self.selected_year
        q_month = f"{month:02}"
        q_year = str(year)
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT date FROM (
                SELECT date FROM daily_income
                UNION
                SELECT date FROM daily_expense
            ) WHERE strftime('%m', date)=? AND strftime('%Y', date)=?
            ORDER BY date
        """, (q_month, q_year))
        days = [row[0] for row in c.fetchall()]

        rows = []
        total_sales = 0
        total_services = 0
        total_income = 0
        total_expenses = 0
        total_balance = 0

        for day in days:
            c.execute("""
                SELECT SUM(amount) FROM daily_income di
                LEFT JOIN income_categories ic ON di.category_id=ic.id
                WHERE di.date=? AND ic.name='Sales'
            """, (day,))
            sales = c.fetchone()[0] or 0

            c.execute("""
                SELECT SUM(amount) FROM daily_income di
                LEFT JOIN income_categories ic ON di.category_id=ic.id
                WHERE di.date=? AND ic.name='Services'
            """, (day,))
            services = c.fetchone()[0] or 0

            daily_income = sales + services

            c.execute("SELECT SUM(amount) FROM daily_expense WHERE date=?", (day,))
            expenses = c.fetchone()[0] or 0

            balance = daily_income - expenses
            profit_percent = (balance / daily_income * 100) if daily_income > 0 else 0

            rows.append((to_ddmmyyyy(day), sales, services, daily_income, expenses, balance, profit_percent))

            total_sales += sales
            total_services += services
            total_income += daily_income
            total_expenses += expenses
            total_balance += balance

        total_profit_percent = (total_balance / total_income * 100) if total_income > 0 else 0

        

        html = f"""
        <div style='font-family: Arial, sans-serif;'>
        <h2 style='text-align:center; margin-bottom:20px; font-size:28px;'>Monthly Report - {QDate(year, month, 1).toString('MMMM yyyy')}</h2>
        <table border='1' cellspacing='0' cellpadding='12' width='100%' style='font-size:22px; border-collapse:collapse; text-align:center;'>
            <tr style='background:#232627; color:#fff; font-size:22px;'>
                <th>Date</th>
                <th>Income (Sales)</th>
                <th>Income (Services)</th>
                <th>Total Income</th>
                <th>Expenses</th>
                <th>Balance</th>
                <th>Profit %</th>
            </tr>
        """
        for d, sales, services, income, expenses, balance, profit in rows:
            html += f"""
            <tr>
                <td>{d}</td>
                <td>{sales:.2f}</td>
                <td>{services:.2f}</td>
                <td>{income:.2f}</td>
                <td>{expenses:.2f}</td>
                <td>{balance:.2f}</td>
                <td>{profit:.2f}</td>
            </tr>
            """
        html += f"""
            <tr style='font-weight:bold; background:#e0e0e0; color:#000; font-size:23px;'>
                <td>Totals</td>
                <td>{total_sales:.2f}</td>
                <td>{total_services:.2f}</td>
                <td>{total_income:.2f}</td>
                <td>{total_expenses:.2f}</td>
                <td>{total_balance:.2f}</td>
                <td>{total_profit_percent:.2f}</td>
            </tr>
        </table>
        </div>
        """

        doc = QTextDocument()
        doc.setHtml(html)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Print Preview - Monthly Report")
        preview.paintRequested.connect(doc.print)
        preview.exec()

        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, "Save PDF", f"MonthlyReport_{q_year}-{q_month}.pdf", "PDF Files (*.pdf)")
        if not file_path:
            return
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(file_path)
        doc.print(printer)

class DailyTab(QWidget):
    def __init__(self, dashboard_tab, parent=None):
        super().__init__(parent)
        self.dashboard_tab = dashboard_tab
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.filter_widget = FilterWidget()
        layout.addWidget(self.filter_widget)
        self.filter_widget.date_from.dateChanged.connect(self.load_data)
        self.filter_widget.date_to.dateChanged.connect(self.load_data)
        self.filter_widget.category_input.currentIndexChanged.connect(self.load_data)
        self.filter_widget.description_input.textChanged.connect(self.load_data)
        self.filter_widget.clear_button.clicked.connect(self.load_data)
        self.filter_widget.on_month_selected()

        layout.addSpacing(0)

        # --- Button Row with left margin and Today label with right margin ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(0)

        # Container widget for left margin for buttons
        btn_left_container = QWidget()
        btn_left_layout = QHBoxLayout()
        btn_left_layout.setContentsMargins(12, 0, 0, 0)
        btn_left_layout.setSpacing(12)
        btn_left_container.setLayout(btn_left_layout)

        self.add_entry_btn = QPushButton()
        self.add_entry_btn.setToolTip("Add Income/Expense Entry (F1)")
        self.add_entry_btn.setFixedSize(40, 40)
        self.add_entry_btn.setStyleSheet(
            "background:#26292A; color:white; border-radius: 3px;"
        )
        # Use standard Plus icon
        self.add_entry_btn = QPushButton()
        self.add_entry_btn.setToolTip("Add Income/Expense Entry (F1)")
        self.add_entry_btn.setFixedSize(40, 40)
        self.add_entry_btn.setStyleSheet("background:rgba(251,112,14,0.10); color:white; border: 2px solid #f27329;")

        # Use 'list-add' theme icon if available, fallback to unicode plus
        icon = QIcon.fromTheme("list-add")
        if not icon.isNull():
            self.add_entry_btn.setIcon(icon)
            self.add_entry_btn.setIconSize(QSizeF(24, 24).toSize())
            self.add_entry_btn.setText("")  # No text, icon-only
        else:
            self.add_entry_btn.setText("＋")
            self.add_entry_btn.setFont(QFont("Arial", 22, QFont.Weight.Bold))

        self.add_entry_btn.clicked.connect(self.show_entry_dialog)

        # --- Print Button: now icon-only with tooltip ---
        self.print_btn = QPushButton()
        self.print_btn.setToolTip("Print Day Report (F12)")
        self.print_btn.setFixedSize(40, 40)
        self.print_btn.setStyleSheet("background:rgba(251,112,14,0.10); color:white; border: 2px solid #f27329;")

        printer_icon = QIcon.fromTheme("printer")
        if not printer_icon.isNull():
            self.print_btn.setIcon(printer_icon)
            self.print_btn.setIconSize(QSizeF(24, 24).toSize())
            self.print_btn.setText("")
        else:
            self.print_btn.setText("\U0001F5A8")  # Unicode printer emoji

        self.print_btn.clicked.connect(self.print_day_report)
        self.print_shortcut = QShortcut(QKeySequence("F12"), self)
        self.print_shortcut.activated.connect(self.print_day_report)
        btn_left_layout.addWidget(self.add_entry_btn)
        btn_left_layout.addWidget(self.print_btn)

        btn_row.addWidget(btn_left_container)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addSpacing(4)

        # --- Income and Expense Records label ---
        label = QLabel("Income and Expense Records:")
        label.setContentsMargins(8, 0, 0, 0)  # Horizontal gap from left for label
        layout.addWidget(label)

        layout.addSpacing(2)  # Gap between label and table

        # --- Data Table ---
        self.data_table = QTableWidget()
        self.data_table.setWordWrap(True)
        self.data_table.setColumnCount(8)
        self.data_table.setHorizontalHeaderLabels([
            'Date', 'Month', 'Type', 'Category', 'Description', 'Amount (AED)', 'Notes', 'ID'
        ])
        header = self.data_table.horizontalHeader()
        self.data_table.setColumnWidth(0, 100)   # Date
        self.data_table.setColumnWidth(1, 120)   # Month
        self.data_table.setColumnWidth(2, 100)   # Type
        self.data_table.setColumnWidth(3, 170)   # Category
        self.data_table.setColumnWidth(4, 270)   # Description
        self.data_table.setColumnWidth(5, 150)   # Amount
        self.data_table.setColumnWidth(6, 200)   # Notes
        self.data_table.setColumnHidden(7, True) # Hide ID

        # Set column resize modes: fixed for all except Notes, which stretches
        for idx in range(7):
            if idx == 6:
                header.setSectionResizeMode(idx, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(idx, QHeaderView.ResizeMode.Fixed)

        self.data_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.data_table.verticalHeader().setDefaultSectionSize(36)

        layout.addWidget(self.data_table)

        layout.addSpacing(12)  # Gap before totals

        # --- Totals frame: now Add. Capital last ---
        self.totals_frame = QFrame()
        self.totals_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.totals_frame.setObjectName("totalsbox")
        totals_layout = QHBoxLayout(self.totals_frame)
        totals_layout.setSpacing(18)
        totals_layout.setContentsMargins(0, 7, 0, 7)
        def card(style, text):
            box = QFrame()
            box.setFrameShape(QFrame.Shape.StyledPanel)
            box.setStyleSheet(style)
            v = QVBoxLayout(box)
            v.setContentsMargins(14, 10, 14, 10)
            v.setSpacing(2)
            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(label)
            return box, label
        card_style = lambda c: (f"background: {c}; border-radius:15px;"
            "border: none; color:#F1F3F4; min-width:135px; font-weight:bold; font-size:17px;")
        self.total_income_box, self.total_income_label = card(card_style("#232627"), "Income")
        self.total_expense_box, self.total_expense_label = card(card_style("#232627"), "Expense")
        self.balance_box, self.balance_label = card(card_style("#232627"), "Balance")
        self.profit_box, self.profit_label = card(card_style("#232627"), "Profit %")
        self.capital_box, self.capital_label = card(card_style("#232627"), "Add. Capital")
        totals_layout.addWidget(self.total_income_box)
        totals_layout.addWidget(self.total_expense_box)
        totals_layout.addWidget(self.balance_box)
        totals_layout.addWidget(self.profit_box)
        totals_layout.addWidget(self.capital_box)
        self.totals_frame.setLayout(totals_layout)
        layout.addWidget(self.totals_frame)

        self.data_table.doubleClicked.connect(self.handle_table_double_click)
        self.setLayout(layout)
        self.load_data()
        self.data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.data_table.clearSelection()
        self.data_table.setCurrentCell(-1, -1)

    def show_entry_dialog(self):
        dialog = IncomeExpenseEntryDialog(self)
        if dialog.exec():
            (
                date_iso,
                type_str,
                cat_id,
                amount_text,
                desc,
                notes
            ) = dialog.get_values()
            amt = parse_amount(amount_text)
            if amt <= 0:
                QMessageBox.warning(self, "Amount Required", "Please enter a valid amount greater than zero.")
                return
            conn = get_conn()
            c = conn.cursor()
            if type_str == "Income":
                # Duplicate Sales/Services check, as before
                c.execute("SELECT name FROM income_categories WHERE id=?", (cat_id,))
                cat_row = c.fetchone()
                cat_name = cat_row[0].strip().lower() if cat_row else ""
                if cat_name in [name.lower() for name in INCOME_CATEGORIES]:
                    c.execute(
                        "SELECT COUNT(*) FROM daily_income WHERE date=? AND category_id=?",
                        (date_iso, cat_id)
                    )
                    if c.fetchone()[0] > 0:
                        QMessageBox.warning(
                            self,
                            "Duplicate Entry",
                            f"Only one '{cat_name.title()}' income entry is allowed per date."
                        )
                        conn.close()
                        return
                # Insert Income
                c.execute(
                    "INSERT INTO daily_income (date, amount, category_id, description, notes) VALUES (?, ?, ?, ?, ?)",
                    (date_iso, amt, cat_id, desc, notes),
                )
            elif type_str == "Expense":
                c.execute(
                    "INSERT INTO daily_expense (date, amount, category_id, description, notes) VALUES (?, ?, ?, ?, ?)",
                    (date_iso, amt, cat_id, desc, notes),
                )
            elif type_str == "Capital":
                
                c.execute(
                    "INSERT INTO daily_capital (date, amount, category, description, notes) VALUES (?, ?, ?, ?, ?)",
                    (date_iso, amt, "Additional Capital", desc, notes),
                )
            conn.commit()
            conn.close()
            self.load_data()
            self.dashboard_tab.refresh()

    def load_data(self):
        date_from = self.filter_widget.date_from.date().toString("yyyy-MM-dd")
        date_to = self.filter_widget.date_to.date().toString("yyyy-MM-dd")
        cat = self.filter_widget.category_input.currentData()
        desc_filter = self.filter_widget.description_input.text().strip().lower()

        conn = get_conn()
        c = conn.cursor()
        rows = []
        params = []

        # Fetch income and expense records
        if not cat or cat == "All":
            final_query = """
            SELECT di.date, di.amount, ic.name, 'Income', di.description, di.id, di.category_id, di.notes
            FROM daily_income di
            LEFT JOIN income_categories ic ON di.category_id = ic.id
            WHERE di.date BETWEEN ? AND ?
            UNION ALL
            SELECT de.date, de.amount, ec.name, 'Expense', de.description, de.id, de.category_id, de.notes
            FROM daily_expense de
            LEFT JOIN expense_categories ec ON de.category_id = ec.id
            WHERE de.date BETWEEN ? AND ?
            UNION ALL
            SELECT dc.date, dc.amount, dc.category, 'Capital', dc.description, dc.id, NULL, dc.notes
            FROM daily_capital dc
            WHERE dc.date BETWEEN ? AND ?
            ORDER BY date ASC
            """
            params = [date_from, date_to, date_from, date_to, date_from, date_to]
            c.execute(final_query, params)
            rows = c.fetchall()

        elif cat.startswith("inc:"):
            cat_id = int(cat.split(":")[1])
            income_query = '''SELECT di.date, di.amount, ic.name, 'Income', di.description, di.id, di.category_id, di.notes
                      FROM daily_income di
                      LEFT JOIN income_categories ic ON di.category_id = ic.id
                      WHERE di.date BETWEEN ? AND ? AND di.category_id = ?'''
            params = [date_from, date_to, cat_id]
            c.execute(income_query + " ORDER BY di.date DESC", params)
            rows = c.fetchall()
        elif cat.startswith("exp:"):
            cat_id = int(cat.split(":")[1])
            expense_query = '''SELECT de.date, de.amount, ec.name, 'Expense', de.description, de.id, de.category_id, de.notes
                               FROM daily_expense de
                               LEFT JOIN expense_categories ec ON de.category_id = ec.id
                               WHERE de.date BETWEEN ? AND ? AND de.category_id = ?'''
            params = [date_from, date_to, cat_id]
            c.execute(expense_query + " ORDER BY de.date DESC", params)
            rows = c.fetchall()
        
        elif cat.startswith("capital:"):
            c.execute(
                "SELECT date, amount, category, 'Capital', description, id, NULL, notes FROM daily_capital WHERE date BETWEEN ? AND ? AND category=?",
                (date_from, date_to, "Additional Capital")
            )
            rows = c.fetchall()
        else:
            rows = []

        # Apply description filter
        if desc_filter:
            rows = [r for r in rows if desc_filter in (r[4] or "").lower()]

        self.data_table.setRowCount(len(rows))
        total_income = 0
        total_expense = 0
        total_capital = 0
        for i, (d, amt, cat, typ, desc, eid, catid, notes) in enumerate(rows):
            desc_len = len(desc or "")
            notes_len = len(notes or "")
            self.data_table.setRowHeight(i, 56 if desc_len > 60 or notes_len > 60 else 36)
            for col, value in enumerate([
                to_ddmmyyyy(d), to_month(d), typ, cat or "", desc or "", f"{amt:.2f} AED", notes or ""
            ]):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 6:
                    item.setForeground(QColor("#aaa"))
                self.data_table.setItem(i, col, item)
            item_id = QTableWidgetItem(str(eid))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.data_table.setItem(i, 7, item_id)
            self.data_table.setColumnHidden(7, True)
            if typ == "Income":
                total_income += amt
            elif typ == "Expense":
                total_expense += amt
            elif typ == "Capital":
                total_capital += amt

        balance = total_income - total_expense
        profit_percent = (balance / total_income * 100) if total_income > 0 else 0
        color = "#43a047" if balance >= 0 else "#e53935"
        self.total_income_label.setText(f"Income<br><span style='font-size:21px; color:#43a047'>{total_income:.2f} AED</span>")
        self.total_expense_label.setText(f"Expense<br><span style='font-size:21px; color:#e53935'>{total_expense:.2f} AED</span>")
        self.balance_label.setText(
            f"Balance<br><span style='font-size:21px; color:{color}'>{balance:.2f} AED</span>"
        )
        self.profit_label.setText(
            f"Profit %<br><span style='font-size:21px; color:{color}'>{profit_percent:.2f}%</span>"
        )
        self.capital_label.setText(f"Add. Capital<br><span style='font-size:21px; color:#1e88e5'>{total_capital:.2f} AED</span>")
        conn.close()

        # Always scroll to the bottom (show latest date at the bottom)
        if self.data_table.rowCount() > 0:
            self.data_table.scrollToBottom()

    def handle_table_double_click(self, idx):
        row = idx.row()
        typ = self.data_table.item(row, 2).text()

        cat = self.data_table.item(row, 3).text()
        # Block editing for Payroll-related expense
        if typ == "Expense" and cat == "Salary":
            QMessageBox.information(
                self,
                "Edit in Payroll Tab",
                "Payroll entries can only be modified through Payroll tab."
            )
            return
        
        id_item = self.data_table.item(row, 7)
        if id_item is None or not id_item.text().strip().isdigit():
            QMessageBox.warning(self, "Error", "ID not found for this entry.")
            return
        eid = int(id_item.text())
        date_str = self.data_table.item(row, 0).text()
        desc = self.data_table.item(row, 4).text()
        amt = float(self.data_table.item(row, 5).text().replace("AED", "").strip())
        notes = self.data_table.item(row, 6).text()
        conn = get_conn()
        c = conn.cursor()
        if typ == "Income":
            c.execute("SELECT category_id FROM daily_income WHERE id=?", (eid,))
        else:
            c.execute("SELECT category_id FROM daily_expense WHERE id=?", (eid,))
        result = c.fetchone()
        catid = result[0] if result else None
        conn.close()
        dialog = EntryEditDialog(typ, eid, to_iso_date(date_str), catid, amt, desc, notes, self)
        if dialog.exec():
            if dialog.deleted:
                self.delete_entry(typ, eid)
            else:
                new_date, new_catid, new_amt, new_desc, new_notes = dialog.get_values()
                self.update_entry(typ, eid, new_date, new_catid, new_amt, new_desc, new_notes)
            self.load_data()
            self.dashboard_tab.refresh()

    def update_entry(self, typ, eid, date, catid, amt, desc, notes):
        conn = get_conn()
        c = conn.cursor()
        if typ == "Income":
            c.execute("UPDATE daily_income SET date=?, category_id=?, amount=?, description=?, notes=? WHERE id=?",
                      (date, catid, amt, desc, notes, eid))
        else:
            c.execute("UPDATE daily_expense SET date=?, category_id=?, amount=?, description=?, notes=? WHERE id=?",
                      (date, catid, amt, desc, notes, eid))
        conn.commit()
        conn.close()

    def delete_entry(self, typ, eid):
        conn = get_conn()
        c = conn.cursor()
        if typ == "Income":
            c.execute("DELETE FROM daily_income WHERE id=?", (eid,))
        else:
            c.execute("DELETE FROM daily_expense WHERE id=?", (eid,))
        conn.commit()
        conn.close()

    def preview_transactions(self, selected_date, transaction_rows):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Transactions for {QDate.fromString(selected_date, 'yyyy-MM-dd').toString('dd/MM/yyyy')}")
        layout = QVBoxLayout(dialog)
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(['Type', 'Category', 'Amount', 'Description', 'Notes', 'Date'])
        table.setRowCount(len(transaction_rows))
        for i, (d, cat, typ, amt, desc, notes) in enumerate(transaction_rows):
            table.setItem(i, 0, QTableWidgetItem(typ))
            table.setItem(i, 1, QTableWidgetItem(cat or ""))
            table.setItem(i, 2, QTableWidgetItem(f"{amt:,.2f} AED"))
            table.setItem(i, 3, QTableWidgetItem(desc or ""))
            table.setItem(i, 4, QTableWidgetItem(notes or ""))
            table.setItem(i, 5, QTableWidgetItem(QDate.fromString(d, "yyyy-MM-dd").toString("dd/MM/yyyy")))
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Print")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def print_day_report(self):
        # --- Step 1: Ask user for date to print ---
        date_dialog = QDialog(self)
        date_dialog.setWindowTitle("Select Date for Daily Report")
        layout = QVBoxLayout(date_dialog)
        date_edit = QDateEdit()
        date_edit.setDisplayFormat("dd-MM-yyyy")
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        layout.addWidget(QLabel("Select date to print:"))
        layout.addWidget(date_edit)
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)
        ok_btn.clicked.connect(date_dialog.accept)
        cancel_btn.clicked.connect(date_dialog.reject)
        if date_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_date = date_edit.date().toString("yyyy-MM-dd")
        date_ddmmyyyy = date_edit.date().toString("dd/MM/yyyy")

        # --- Step 2: Gather summary data ---
        conn = get_conn()
        c = conn.cursor()

        c.execute("""
            SELECT SUM(amount) FROM daily_income di
            LEFT JOIN income_categories ic ON di.category_id=ic.id
            WHERE di.date=? AND ic.name='Sales'
        """, (selected_date,))
        sales = c.fetchone()[0] or 0

        c.execute("""
            SELECT SUM(amount) FROM daily_income di
            LEFT JOIN income_categories ic ON di.category_id=ic.id
            WHERE di.date=? AND ic.name='Services'
        """, (selected_date,))
        services = c.fetchone()[0] or 0

        total_income = sales + services

        c.execute("SELECT SUM(amount) FROM daily_expense WHERE date=?", (selected_date,))
        total_expense = c.fetchone()[0] or 0
        gross_income = total_income - total_expense

        c.execute("SELECT description, amount FROM daily_expense WHERE date=? ORDER BY id ASC", (selected_date,))
        expense_rows = c.fetchall()
        conn.close()

        # --- Step 3: Show preview dialog ---
        preview = QDialog(self)
        preview.setWindowTitle(f"Daily Summary Preview - {date_ddmmyyyy}")
        preview.resize(421, 0)
        vbox = QVBoxLayout(preview)

        # Heading
        heading = QLabel("Daily Summary")
        heading_font = QFont()
        heading_font.setBold(True)
        heading_font.setPointSize(22)
        heading.setFont(heading_font)
        heading.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        vbox.addWidget(heading)

        # Date
        date_lbl = QLabel(f"Date: {date_ddmmyyyy}")
        date_font = QFont()
        date_font.setBold(True)
        date_font.setPointSize(20)
        date_lbl.setFont(date_font)
        date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        date_lbl.setStyleSheet("color: #fb700e;")
        vbox.addWidget(date_lbl)

        # 2px vertical gap (8px by default, you can adjust)
        vbox.addSpacing(8)

        # Sales, Service, Total Income, Expenses - vertically aligned
        amount_font = QFont("Courier New", 12)  # Monospaced for alignment

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(16)
        summary_labels = ["Sales:", "Service:", "Total Income:", "Expenses:"]
        summary_values = [sales, services, total_income, total_expense]
        for row, (lbl, val) in enumerate(zip(summary_labels, summary_values)):
            l = QLabel(lbl)
            l.setFont(QFont("Segoe UI", 11))
            l.setAlignment(Qt.AlignmentFlag.AlignLeft)
            summary_grid.addWidget(l, row, 0)
            v = QLabel(f"{val:>12,.2f} ")
            v.setFont(amount_font)
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            v.setMinimumWidth(120)
            summary_grid.addWidget(v, row, 1)
        vbox.addLayout(summary_grid)

        # Balance (center, bold, larger)
        vbox.addSpacing(8)
        balance_lbl = QLabel(f"BALANCE: {gross_income:,.2f} ")
        balance_font = QFont()
        balance_font.setBold(True)
        balance_font.setPointSize(16)
        balance_lbl.setFont(balance_font)
        balance_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        balance_lbl.setStyleSheet("""
            color: #fb700e;
            border: 2px solid #ffbe87;
            border-radius: 5px;
            padding: 6px 0 6px 0;
        """)
        vbox.addWidget(balance_lbl)

        # Expense Details section
        expense_heading = QLabel("Expense Details:")
        expense_heading.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        expense_heading.setAlignment(Qt.AlignmentFlag.AlignLeft)
        vbox.addWidget(expense_heading)

        # Expense details in grid with vertical alignment for amounts
        if expense_rows:
            expense_grid = QGridLayout()
            expense_grid.setHorizontalSpacing(16)
            desc_font = QFont("Segoe UI", 10)
            amt_font = QFont("Courier New", 11)
            for row, (desc, amt) in enumerate(expense_rows):
                desc_lbl = QLabel(desc or "")
                desc_lbl.setFont(desc_font)
                desc_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
                expense_grid.addWidget(desc_lbl, row, 0)
                amt_lbl = QLabel(f"{amt:>12,.2f} ")
                amt_lbl.setFont(amt_font)
                amt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                amt_lbl.setMinimumWidth(120)
                expense_grid.addWidget(amt_lbl, row, 1)
            vbox.addLayout(expense_grid)
        else:
            vbox.addWidget(QLabel("No Expenses"))

        vbox.addSpacing(10)

        # Buttons
        btn_row = QHBoxLayout()
        print_btn = QPushButton("Print")
        cancel_btn = QPushButton("Cancel")
        btn_row.addStretch()
        btn_row.addWidget(print_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        vbox.addLayout(btn_row)
        print_btn.clicked.connect(preview.accept)
        cancel_btn.clicked.connect(preview.reject)

        if preview.exec() != QDialog.DialogCode.Accepted:
            return

        # --- Step 4: Build print lines (same as before) ---
        LINE_WIDTH = 42
        label_width = 20

        def center_text(text, width=LINE_WIDTH):
            return text.center(width)

        LEFT_MARGIN_SPACES = " " * 0
        TOP_MARGIN_LINES = "\r\n" * 2
        BOTTOM_MARGIN_LINES = "\r\n" * 8

        lines = []
        lines.append(center_text("NATIONAL BICYCLES"))
        lines.append(center_text("DAILY REPORT"))
        lines.append("-" * LINE_WIDTH)
        lines.append(f"Date: {date_ddmmyyyy}")
        lines.append("-" * LINE_WIDTH)
        def lined_amount(label, amount):
            amt_str = f"{amount:,.2f}"
            return f"{label:<{label_width}}{amt_str:>{LINE_WIDTH - label_width}}"
        lines.append(lined_amount("Total Sales:", total_income))
        lines.append(lined_amount("Total Expenses:", total_expense))
        lines.append(lined_amount("Balance:", gross_income))
        lines.append("-" * LINE_WIDTH)
        lines.append(center_text(f"BALANCE: {gross_income:,.2f}"))
        lines.append("-" * LINE_WIDTH)
        lines.append("Expense Details:")
        lines.extend([""]) 
        if expense_rows:
            for desc, amt in expense_rows:
                desc_str = (desc or "")
                if len(desc_str) > 24:
                    desc_str = desc_str[:24] + "…"  # Shorten long descriptions
                amt_str = f"{amt:,.2f}"
                space = LINE_WIDTH - len(desc_str) - len(amt_str)
                lines.append(desc_str + " " * max(1, space) + amt_str)
        else:
            lines.append(center_text("No Expenses"))
        lines.append("-" * LINE_WIDTH)

        lines_with_margin = [LEFT_MARGIN_SPACES + line for line in lines]
        receipt_text = TOP_MARGIN_LINES + "\r\n".join(lines_with_margin) + BOTTOM_MARGIN_LINES

        CUT = b'\x1d\x56\x00'

        try:
            printer_name = win32print.GetDefaultPrinter()
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                hjob = win32print.StartDocPrinter(hprinter, 1, ("Day Report", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, receipt_text.encode('utf-8'))
                win32print.WritePrinter(hprinter, CUT)
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)
        except Exception as e:
            QMessageBox.warning(self, "Print Error", f"Failed to print:\n{e}")

            

class ManagePayrollTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())
        self.form = QFormLayout()
        self.name_edit = QLineEdit()
        self.desig_edit = QLineEdit()
        self.salary_edit = QLineEdit()
        self.joining_edit = QDateEdit()
        self.joining_edit.setCalendarPopup(True)
        self.joining_edit.setDate(QDate.currentDate())
        self.loan_edit = QLineEdit()
        self.loan_edit.setReadOnly(True)
        self.photo_label = QLabel()
        self.photo_label.setFixedSize(72, 72)
        self.photo_label.setScaledContents(True)
        self.upload_btn = QPushButton("Upload Photo")
        self.upload_btn.clicked.connect(self.upload_photo)
        photo_row = QHBoxLayout()
        photo_row.addWidget(self.photo_label)
        photo_row.addWidget(self.upload_btn)

        self.form.addRow("Name:", self.name_edit)
        self.form.addRow("Designation:", self.desig_edit)
        self.form.addRow("Salary:", self.salary_edit)
        self.form.addRow("Joining Date:", self.joining_edit)
        self.form.addRow("Loan Balance:", self.loan_edit)
        self.form.addRow("Photo:", photo_row)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_employee)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_form)
        btns = QHBoxLayout()
        btns.addWidget(self.save_btn)
        btns.addWidget(self.clear_btn)
        self.form.addRow(btns)

        left = QVBoxLayout()
        left.addLayout(self.form)
        left.addStretch()

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Designation", "Salary", "Joining Date", "Loan Balance"])
        self.table.cellClicked.connect(self.select_employee)
        self.load_employees()

        self.layout().addLayout(left, 1)
        self.layout().addWidget(self.table, 2)

    def upload_photo(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Photo", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file:
            dest_dir = os.path.join(os.path.expanduser("~"), "NBS_EmployeePhotos")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, os.path.basename(file))
            shutil.copyfile(file, dest_path)
            self.photo_label.setPixmap(QPixmap(dest_path))
            self.photo_path = dest_path

    def clear_form(self):
        self.name_edit.clear()
        self.desig_edit.clear()
        self.salary_edit.clear()
        self.loan_edit.clear()
        self.joining_edit.setDate(QDate.currentDate())
        self.photo_label.clear()
        self.photo_path = None
        self.selected_id = None

    def save_employee(self):
        name = self.name_edit.text().strip()
        desig = self.desig_edit.text().strip()
        salary = parse_amount(self.salary_edit.text())
        joining = self.joining_edit.date().toString("yyyy-MM-dd")
        photo = getattr(self, "photo_path", "")
        loan = parse_amount(self.loan_edit.text())
        if not name:
            QMessageBox.warning(self, "Validation", "Name required")
            return
        conn = get_conn()
        c = conn.cursor()
        if hasattr(self, "selected_id") and self.selected_id:
            c.execute("UPDATE employees SET name=?, designation=?, salary=?, joining_date=?, loan_balance=?, photo_path=? WHERE id=?",
                      (name, desig, salary, joining, loan, photo, self.selected_id))
        else:
            c.execute("INSERT INTO employees (name, designation, salary, joining_date, loan_balance, photo_path) VALUES (?, ?, ?, ?, ?, ?)",
                      (name, desig, salary, joining, loan, photo))
        conn.commit()
        conn.close()
        self.clear_form()
        self.load_employees()

    def load_employees(self):
        self.table.setRowCount(0)
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name, designation, salary, joining_date, loan_balance FROM employees")
        for i, row in enumerate(c.fetchall()):
            self.table.insertRow(i)
            for col, val in enumerate(row[1:]):
                self.table.setItem(i, col, QTableWidgetItem(str(val)))
        conn.close()

    def select_employee(self, row, _):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name, designation, salary, joining_date, loan_balance, photo_path FROM employees")
        data = c.fetchall()[row]
        self.selected_id, name, desig, salary, joining, loan, photo = data
        self.name_edit.setText(name)
        self.desig_edit.setText(desig)
        self.salary_edit.setText(str(salary))
        self.joining_edit.setDate(QDate.fromString(joining, "yyyy-MM-dd"))
        self.loan_edit.setText(str(loan))
        self.photo_label.setPixmap(QPixmap(photo) if photo and os.path.exists(photo) else QPixmap())
        self.photo_path = photo
        conn.close()

class OutstandingBalanceCard(QWidget):
        def __init__(self, balance=0.0, parent=None):
            super().__init__(parent)
            self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
            outer = QHBoxLayout(self)
            outer.setContentsMargins(0,0,0,0)
            outer.setSpacing(0)

            # Orange vertical bar
            bar = QLabel()
            bar.setFixedWidth(4)
            bar.setFixedHeight(40)
            bar.setStyleSheet("background:#fb700e; border-radius:2px;")
            bar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            outer.addWidget(bar)

            # Main content area
            content = QVBoxLayout()
            content.setContentsMargins(16,8,16,8)
            content.setSpacing(2)

            # Big, bold black currency label
            self.amount_label = QLabel()
            font = QFont()
            font.setPointSize(20)
            font.setBold(True)
            self.amount_label.setFont(font)
            self.amount_label.setStyleSheet("color:#fff;")
            self.amount_label.setText(self.format_balance(balance))
            self.amount_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

            # Muted sublabel
            sublabel = QLabel("Outstanding Balance")
            font.setBold(True)
            sublabel.setStyleSheet("color:#888;")
            sublabel.setAlignment(Qt.AlignmentFlag.AlignLeft)

            content.addWidget(self.amount_label)
            content.addWidget(sublabel)
            content.addStretch(1)
            outer.addLayout(content)

            # Card background and padding
            self.setStyleSheet("""
            QWidget {
                background: #181a1b;
                border-radius: 13px;
                padding: 0px;
            }
            """)
            self.setContentsMargins(0,0,0,0)

        def set_balance(self, balance):
            self.amount_label.setText(self.format_balance(balance))

        def format_balance(self, balance):
            return f"AED {balance:,.2f}"

class PayrollTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())
        top = QHBoxLayout()
        self.employee_combo = QComboBox()
        self.employee_combo.currentIndexChanged.connect(self.load_employee)
        top.addWidget(self.employee_combo)
        self.photo = QLabel()
        self.photo.setFixedSize(64, 64)
        self.photo.setScaledContents(True)
        self.emp_info = QLabel()
        top.addWidget(self.photo)
        top.addWidget(self.emp_info)
        top.addStretch()
        self.layout().addLayout(top)
        self.outstanding_card = OutstandingBalanceCard(balance=0.0)
        top.addWidget(self.outstanding_card)


        # --- Add "Add Transaction" Button ---
        self.add_transaction_btn = QPushButton("Add Transaction")
        self.add_transaction_btn.setFixedWidth(180)
        self.add_transaction_btn.setStyleSheet("font-size:15px; font-weight:bold; background:#fb700e; color:white; border-radius:5px; padding:8px 18px;")
        self.add_transaction_btn.setToolTip("Add Salary or Advance")
        self.layout().addWidget(self.add_transaction_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.add_transaction_btn.clicked.connect(self.choose_transaction_type)

        # Transactions Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Date", "Type", "Debit", "Credit", "Balance", "Notes"])
        self.table.setColumnWidth(0, 120)   # Date
        self.table.setColumnWidth(1, 140)   # Type
        self.table.setColumnWidth(2, 120)   # Debit
        self.table.setColumnWidth(3, 120)   # Credit
        self.table.setColumnWidth(4, 120)   # Balance
        self.table.setColumnWidth(5, 220)   # Notes
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.layout().addWidget(self.table)
        self.load_employees()

        self.table.doubleClicked.connect(self.handle_table_double_click)

    def choose_transaction_type(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Transaction Type")
        dialog.setMinimumWidth(280)
        vbox = QVBoxLayout(dialog)
        vbox.addWidget(QLabel("What type of payroll transaction?"))
        btn_row = QHBoxLayout()
        btn_salary = QPushButton("Salary")
        btn_advance = QPushButton("Advance")
        btn_row.addWidget(btn_salary)
        btn_row.addWidget(btn_advance)
        vbox.addLayout(btn_row)

        selected = {}

        def choose_salary():
            selected['type'] = 'Salary Payment'
            dialog.accept()
        def choose_advance():
            selected['type'] = 'Advance'
            dialog.accept()
        btn_salary.clicked.connect(choose_salary)
        btn_advance.clicked.connect(choose_advance)

        if dialog.exec() == QDialog.DialogCode.Accepted and 'type' in selected:
            self.show_transaction_dialog(selected['type'])

    def show_transaction_dialog(self, tx_type):
        class SalaryDialog(QDialog):
            def __init__(self, parent):
                super().__init__(parent)
                self.setWindowTitle("Record Salary Payment")
                self.setMinimumWidth(340)
                form = QFormLayout(self)
                self.date_edit = QDateEdit()
                self.date_edit.setCalendarPopup(True)
                self.date_edit.setDate(QDate.currentDate())
                self.date_edit.setDisplayFormat("dd-MM-yyyy")
                form.addRow("Date:", self.date_edit)

                self.salary_amount_edit = QLineEdit()
                self.salary_amount_edit.setPlaceholderText("Salary Paid (AED)")
                self.salary_amount_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
                afont = QFont()
                afont.setPointSize(16)
                afont.setBold(True)
                self.salary_amount_edit.setFont(afont)
                form.addRow("Salary Paid:", self.salary_amount_edit)

                self.deduction_amount_edit = QLineEdit()
                self.deduction_amount_edit.setPlaceholderText("Deduction Amount (AED)")
                self.deduction_amount_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.deduction_amount_edit.setFont(afont)
                form.addRow("Deductions:", self.deduction_amount_edit)

                self.notes_edit = QLineEdit()
                self.notes_edit.setPlaceholderText("Notes (optional)")
                form.addRow("Notes:", self.notes_edit)

                btn_row = QHBoxLayout()
                save_btn = QPushButton("Save")
                cancel_btn = QPushButton("Cancel")
                save_btn.clicked.connect(self.accept)
                cancel_btn.clicked.connect(self.reject)
                btn_row.addWidget(save_btn)
                btn_row.addWidget(cancel_btn)
                form.addRow(btn_row)
                self.setLayout(form)

            def get_values(self):
                return (
                    self.salary_amount_edit.text(),
                    self.deduction_amount_edit.text(),
                    self.date_edit.date().toString("yyyy-MM-dd"),
                    self.notes_edit.text(),
                )

        class AdvanceDialog(QDialog):
            def __init__(self, parent):
                super().__init__(parent)
                self.setWindowTitle("Record Advance")
                self.setMinimumWidth(340)
                form = QFormLayout(self)
                self.date_edit = QDateEdit()
                self.date_edit.setCalendarPopup(True)
                self.date_edit.setDate(QDate.currentDate())
                self.date_edit.setDisplayFormat("dd-MM-yyyy")
                form.addRow("Date:", self.date_edit)

                self.amount_edit = QLineEdit()
                self.amount_edit.setPlaceholderText("Advance Amount (AED)")
                self.amount_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
                afont = QFont()
                afont.setPointSize(16)
                afont.setBold(True)
                self.amount_edit.setFont(afont)
                form.addRow("Amount:", self.amount_edit)

                self.notes_edit = QLineEdit()
                self.notes_edit.setPlaceholderText("Notes (optional)")
                form.addRow("Notes:", self.notes_edit)

                btn_row = QHBoxLayout()
                save_btn = QPushButton("Save")
                cancel_btn = QPushButton("Cancel")
                save_btn.clicked.connect(self.accept)
                cancel_btn.clicked.connect(self.reject)
                btn_row.addWidget(save_btn)
                btn_row.addWidget(cancel_btn)
                form.addRow(btn_row)
                self.setLayout(form)

            def get_values(self):
                return (
                    self.amount_edit.text(),
                    self.date_edit.date().toString("yyyy-MM-dd"),
                    self.notes_edit.text(),
                )

        class DeductionDialog(QDialog):
            def __init__(self, parent):
                super().__init__(parent)
                self.setWindowTitle("Record Deduction")
                self.setMinimumWidth(340)
                form = QFormLayout(self)
                self.date_edit = QDateEdit()
                self.date_edit.setCalendarPopup(True)
                self.date_edit.setDate(QDate.currentDate())
                self.date_edit.setDisplayFormat("dd-MM-yyyy")
                form.addRow("Date:", self.date_edit)

                self.amount_edit = QLineEdit()
                self.amount_edit.setPlaceholderText("Deduction Amount (AED)")
                self.amount_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
                afont = QFont()
                afont.setPointSize(16)
                afont.setBold(True)
                self.amount_edit.setFont(afont)
                form.addRow("Amount:", self.amount_edit)

                self.notes_edit = QLineEdit()
                self.notes_edit.setPlaceholderText("Notes (optional)")
                form.addRow("Notes:", self.notes_edit)

                btn_row = QHBoxLayout()
                save_btn = QPushButton("Save")
                cancel_btn = QPushButton("Cancel")
                save_btn.clicked.connect(self.accept)
                cancel_btn.clicked.connect(self.reject)
                btn_row.addWidget(save_btn)
                btn_row.addWidget(cancel_btn)
                form.addRow(btn_row)
                self.setLayout(form)

            def get_values(self):
                return (
                    self.amount_edit.text(),
                    self.date_edit.date().toString("yyyy-MM-dd"),
                    self.notes_edit.text(),
                )

        if tx_type == "Salary Payment":
            dlg = SalaryDialog(self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                salary_text, deduction_text, date, notes = dlg.get_values()
                try:
                    salary_amt = float(salary_text)
                except Exception:
                    salary_amt = 0.0
                try:
                    deduction_amt = float(deduction_text)
                except Exception:
                    deduction_amt = 0.0
                if salary_amt < 0:
                    QMessageBox.warning(self, "Amount Required", "Salary amount must be zero or positive.")
                    return
                if deduction_amt < 0:
                    QMessageBox.warning(self, "Amount Required", "Deduction amount must be zero or positive.")
                    return
                name = self.employee_combo.currentText()
                eid = self.emp_map.get(name)
                if eid is None:
                    QMessageBox.warning(self, "Employee required", "Please select an employee.")
                    return
                # Get previous balance
                conn = get_conn()
                c = conn.cursor()
                c.execute("SELECT balance FROM employee_payroll WHERE employee_id=? ORDER BY date DESC, id DESC LIMIT 1", (eid,))
                prev = c.fetchone()
                prev_balance = prev[0] if prev else 0
                debit = salary_amt
                credit = deduction_amt
                # Only deduction affects balance
                if deduction_amt > 0:
                    new_balance = prev_balance - deduction_amt
                else:
                    new_balance = prev_balance
                c.execute(
                    "INSERT INTO employee_payroll (employee_id, date, type, amount, debit, credit, balance, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (eid, date, "Salary Payment", salary_amt, debit, credit, new_balance, notes)
                )
                conn.commit()
                conn.close()
                # Restore cashflow entry for Salary Payment
                self._record_salary_expense_in_cashflow(emp_name=name, amount=debit, date=date, tx_type="Salary Payment")
                if hasattr(self.window(), "daily") and hasattr(self.window().daily, "load_data"):
                    self.window().daily.load_data()
                self.load_employee(self.employee_combo.currentIndex())
                QMessageBox.information(self, "Success", "Transaction recorded.")

        elif tx_type == "Advance":
            dlg = AdvanceDialog(self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                amount_text, date, notes = dlg.get_values()
                try:
                    amt = float(amount_text)
                except Exception:
                    amt = 0.0
                if amt <= 0:
                    QMessageBox.warning(self, "Amount Required", "Advance amount must be greater than zero.")
                    return
                name = self.employee_combo.currentText()
                eid = self.emp_map.get(name)
                if eid is None:
                    QMessageBox.warning(self, "Employee required", "Please select an employee.")
                    return
                # Get previous balance
                conn = get_conn()
                c = conn.cursor()
                c.execute("SELECT balance FROM employee_payroll WHERE employee_id=? ORDER BY date DESC, id DESC LIMIT 1", (eid,))
                prev = c.fetchone()
                prev_balance = prev[0] if prev else 0
                debit = amt
                credit = 0
                new_balance = prev_balance + amt
                c.execute(
                    "INSERT INTO employee_payroll (employee_id, date, type, amount, debit, credit, balance, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (eid, date, "Advance", amt, debit, credit, new_balance, notes)
                )
                conn.commit()
                conn.close()
                # Restore cashflow entry for Advance
                self._record_salary_expense_in_cashflow(emp_name=name, amount=debit, date=date, tx_type="Advance")
                if hasattr(self.window(), "daily") and hasattr(self.window().daily, "load_data"):
                     self.window().daily.load_data()
                self.load_employee(self.employee_combo.currentIndex())
                QMessageBox.information(self, "Success", "Transaction recorded.")

        elif tx_type == "Deduction":
            dlg = DeductionDialog(self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                amount_text, date, notes = dlg.get_values()
                try:
                    amt = float(amount_text)
                except Exception:
                    amt = 0.0
                if amt <= 0:
                    QMessageBox.warning(self, "Amount Required", "Deduction amount must be greater than zero.")
                    return
                name = self.employee_combo.currentText()
                eid = self.emp_map.get(name)
                if eid is None:
                    QMessageBox.warning(self, "Employee required", "Please select an employee.")
                    return
                # Get previous balance
                conn = get_conn()
                c = conn.cursor()
                c.execute("SELECT balance FROM employee_payroll WHERE employee_id=? ORDER BY date DESC, id DESC LIMIT 1", (eid,))
                prev = c.fetchone()
                prev_balance = prev[0] if prev else 0
                debit = 0
                credit = amt
                new_balance = prev_balance - amt
                c.execute(
                    "INSERT INTO employee_payroll (employee_id, date, type, amount, debit, credit, balance, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (eid, date, "Deduction", amt, debit, credit, new_balance, notes)
                )
                conn.commit()
                conn.close()
                self.load_employee(self.employee_combo.currentIndex())
                QMessageBox.information(self, "Success", "Transaction recorded.")


    def load_employees(self):
        self.employee_combo.clear()
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name FROM employees")
        self.emp_map = {}
        for eid, name in c.fetchall():
            self.emp_map[name] = eid
            self.employee_combo.addItem(name)
        conn.close()
        if self.emp_map:
            self.load_employee(0)

    def load_employee(self, idx):
        if idx < 0 or not self.emp_map:
            return
        name = self.employee_combo.currentText()
        eid = self.emp_map[name]
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT designation, salary, joining_date, photo_path FROM employees WHERE id=?", (eid,))
        row = c.fetchone()
        if not row:
            return
        desig, salary, joining, photo = row
        self.emp_info.setText(f"{name}\n{desig}\nSalary: {salary}\nJoined: {joining}")
        self.photo.setPixmap(QPixmap(photo) if photo and os.path.exists(photo) else QPixmap())
        conn.close()
        # Only call load_transactions now; don't set card yet
        self.load_transactions(eid)

    def load_transactions(self, eid):
        self.table.setRowCount(0)
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, date, type, debit, credit, balance, notes FROM employee_payroll WHERE employee_id=? ORDER BY date ASC, id ASC", (eid,))
        rows = c.fetchall()
        conn.close()

        last_balance = 0.0
        for i, (payroll_id, date_str, typ, debit, credit, balance, notes) in enumerate(rows):
            debit_str = ""
            credit_str = ""
            if typ == "Salary Payment":
                debit_str = f"{debit:.2f}" if debit else ""
                credit_str = f"{credit:.2f}" if credit else ""
            elif typ == "Advance":
                debit_str = f"{debit:.2f}" if debit else ""
            elif typ == "Deduction":
                credit_str = f"{credit:.2f}" if credit else ""

            self.table.insertRow(i)
            id_item = QTableWidgetItem(str(payroll_id))
            id_item.setData(Qt.ItemDataRole.UserRole, payroll_id)
            self.table.setVerticalHeaderItem(i, id_item)
            self.table.setItem(i, 0, QTableWidgetItem(str(date_str)))
            self.table.setItem(i, 1, QTableWidgetItem(str(typ)))
            self.table.setItem(i, 2, QTableWidgetItem(debit_str))
            self.table.setItem(i, 3, QTableWidgetItem(credit_str))
            self.table.setItem(i, 4, QTableWidgetItem(f"{balance:.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(str(notes)))

            # Only update prev_balance for Advance/Deduction
            if typ == "Advance" or typ == "Deduction":
                prev_balance = balance

            last_balance = balance  # always the latest

        self.outstanding_card.set_balance(last_balance)

    def handle_table_double_click(self, index):
        row = index.row()
        eid = self.emp_map.get(self.employee_combo.currentText())
        id_item = self.table.verticalHeaderItem(row)
        if id_item is None:
            QMessageBox.warning(self, "Error", "Could not identify transaction ID.")
            return
        payroll_id = int(id_item.text())

        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT date, type, amount, notes FROM employee_payroll WHERE id=?", (payroll_id,))
        rec = c.fetchone()
        conn.close()
        if not rec:
            QMessageBox.warning(self, "Error", "Could not find transaction details.")
            return

        date_str, typ, amount, notes = rec
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit/Delete Transaction")
        dialog.setMinimumWidth(350)
        form = QFormLayout(dialog)
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
        form.addRow("Date:", date_edit)
        type_combo = QComboBox()
        type_combo.addItems(["Salary Payment", "Advance", "Deduction"])
        idx = type_combo.findText(typ)
        if idx != -1:
            type_combo.setCurrentIndex(idx)
        form.addRow("Type:", type_combo)
        amount_edit = QLineEdit(str(amount))
        form.addRow("Amount:", amount_edit)
        notes_edit = QLineEdit(notes or "")
        form.addRow("Notes:", notes_edit)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        delete_btn = QPushButton("Delete")
        cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(save_btn)
        btn_row.addWidget(delete_btn)
        btn_row.addWidget(cancel_btn)
        form.addRow(btn_row)

        def do_save():
            new_date = date_edit.date().toString("yyyy-MM-dd")
            new_type = type_combo.currentText()
            try:
                new_amt = float(amount_edit.text())
            except Exception:
                QMessageBox.warning(dialog, "Error", "Amount required.")
                return
            new_notes = notes_edit.text()
            debit = credit = 0
            if new_type == "Salary Payment":
                debit = new_amt
            elif new_type == "Advance":
                debit = new_amt
            elif new_type == "Deduction":
                credit = new_amt

            conn = get_conn()
            c = conn.cursor()
            c.execute(
                "UPDATE employee_payroll SET date=?, type=?, amount=?, debit=?, credit=?, notes=? WHERE id=?",
                (new_date, new_type, new_amt, debit, credit, new_notes, payroll_id)
            )
            conn.commit()
            conn.close()
            emp_name = self.employee_combo.currentText()
            self._update_or_delete_salary_expense_entry(
                old_date=date_str,
                old_type=typ,
                old_amount=amount,
                emp_name=emp_name,
                new_date=new_date,
                new_type=new_type,
                new_amount=new_amt,
            )
            self.update_employee_loan_balance(eid)
            # Refresh cashflow/daily tab
            main_window = self.window()
            if hasattr(main_window, "daily") and hasattr(main_window.daily, "load_data"):
                main_window.daily.load_data()
            dialog.accept()
            self.load_employee(self.employee_combo.currentIndex())

        def do_delete():
            reply = QMessageBox.question(dialog, "Confirm Delete", "Delete this transaction?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                conn = get_conn()
                c = conn.cursor()
                c.execute("DELETE FROM employee_payroll WHERE id=?", (payroll_id,))
                conn.commit()
                conn.close()
                emp_name = self.employee_combo.currentText()
                self._update_or_delete_salary_expense_entry(
                    old_date=date_str,
                    old_type=typ,
                    old_amount=amount,
                    emp_name=emp_name,
                    new_date=None,
                    new_type=None,
                    new_amount=None,
                )
                self.update_employee_loan_balance(eid)
                # Refresh cashflow/daily tab
                main_window = self.window()
                if hasattr(main_window, "daily") and hasattr(main_window.daily, "load_data"):
                    main_window.daily.load_data()
                dialog.accept()
                self.load_employee(self.employee_combo.currentIndex())

        save_btn.clicked.connect(do_save)
        delete_btn.clicked.connect(do_delete)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

        # (Optional) If you want newest first, call self.table.sortItems(0, Qt.SortOrder.DescendingOrder) here

    def update_employee_loan_balance(self, eid):
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN type='Advance' THEN debit ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN type='Deduction' THEN credit ELSE 0 END), 0)
            FROM employee_payroll
            WHERE employee_id=?
        """, (eid,))
        advance_sum, deduction_sum = c.fetchone()
        loan_balance = advance_sum - deduction_sum
        c.execute("UPDATE employees SET loan_balance=? WHERE id=?", (loan_balance, eid))
        conn.commit()
        conn.close()
        self.outstanding_card.set_balance(loan_balance)

    def _record_salary_expense_in_cashflow(self, emp_name, amount, date, tx_type):
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM expense_categories WHERE lower(name)=?", ("salary",))
            row = c.fetchone()
            if row:
                cat_id = row[0]
            else:
                c.execute("INSERT INTO expense_categories (name) VALUES ('Salary')")
                cat_id = c.lastrowid
                conn.commit()
            description = emp_name
            notes = f"Payroll - {tx_type}"
            c.execute(
                """SELECT id FROM daily_expense
                   WHERE date=? AND category_id=? AND amount=? AND description=? AND notes=?""",
                (date, cat_id, amount, description, notes)
            )
            already = c.fetchone()
            if not already:
                c.execute(
                    """INSERT INTO daily_expense
                       (date, amount, category_id, description, notes)
                       VALUES (?, ?, ?, ?, ?)""",
                    (date, amount, cat_id, description, notes)
                )
                conn.commit()

    def _update_or_delete_salary_expense_entry(self, old_date, old_type, old_amount, emp_name, new_date, new_type, new_amount):
        if old_type not in ("Salary Payment", "Advance"):
            return
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM expense_categories WHERE lower(name)=?", ("salary",))
            row = c.fetchone()
            if not row:
                return
            cat_id = row[0]
            description = emp_name
            notes = f"Payroll - {old_type}"
            c.execute(
                """SELECT id FROM daily_expense
                   WHERE date=? AND category_id=? AND amount=? AND description=? AND notes=?""",
                (old_date, cat_id, old_amount, description, notes)
            )
            exp_row = c.fetchone()
            if not exp_row:
                return
            exp_id = exp_row[0]
            if new_type in ("Salary Payment", "Advance") and new_date and new_amount is not None:
                new_notes = f"Payroll - {new_type}"
                c.execute(
                    "UPDATE daily_expense SET date=?, amount=?, notes=? WHERE id=?",
                    (new_date, new_amount, new_notes, exp_id)
                )
            else:
                c.execute("DELETE FROM daily_expense WHERE id=?", (exp_id,))
            conn.commit()

class DocumentsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        # --- Search filter row ---
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Search Description:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter by description...")
        self.filter_edit.textChanged.connect(self.load_documents)
        filter_row.addWidget(self.filter_edit)
        filter_row.addStretch()
        self.add_btn = QPushButton("Add Document")
        self.add_btn.clicked.connect(self.add_document)
        filter_row.addWidget(self.add_btn)
        layout.addLayout(filter_row)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Description", "Category", "Expiry Date", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        self.table.doubleClicked.connect(self.handle_table_double_click)
        self.load_documents()

    def load_documents(self):
        docs = load_documents_from_db()
        filter_text = self.filter_edit.text().strip().lower()
        filtered_docs = []
        for d in docs:
            if not filter_text or filter_text in d["description"].lower():
                filtered_docs.append(d)
                
        # Add status and color and sortnum for sorting and later use
        table_docs = []
        for doc in filtered_docs:
            status, color, sortnum = self.compute_status_sort(doc["expiry_date"])
            table_docs.append((sortnum, status, color, doc))
        # Sort: expired (0), expiring soon (1), valid (2)
        table_docs.sort(key=lambda x: (x[0], x[3]["description"].lower()))

        self.table.setRowCount(len(table_docs))
        for i, (sortnum, status, color, doc) in enumerate(table_docs):
            desc, cat, expiry = doc["description"], doc["category"], doc["expiry_date"]
            self.table.setItem(i, 0, QTableWidgetItem(desc))
            self.table.setItem(i, 1, QTableWidgetItem(cat))
            self.table.setItem(i, 2, QTableWidgetItem(expiry))
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor("white"))
            status_item.setBackground(QColor(color))
            self.table.setItem(i, 3, status_item)
            for j in range(4):
                self.table.item(i, j).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.documents = [doc for (_, _, _, doc) in table_docs]

    def compute_status_sort(self, expiry_str):
        expiry = QDate.fromString(expiry_str, "dd/MM/yyyy")
        today = QDate.currentDate()
        days = today.daysTo(expiry)
        if not expiry.isValid():
            return "Invalid Date", "#616161", 3
        if days > 30:
            return " ✅ Valid", "#43a047", 2
        elif 0 <= days <= 30:
            return "⚠️ Expiring Soon", "#fbc02d", 1
        else:
            stat = f"❌ Expired {abs(days)} days ago" if days < -1 else "Expired"
            return stat, "#e53935", 0

    def add_document(self):
        dlg = DocumentEntryDialog(parent=self)
        if dlg.exec():
            desc, cat, expiry = dlg.get_values()
            if desc and cat and expiry:
                save_document_to_db(desc, cat, expiry)
                self.load_documents()

    def handle_table_double_click(self, index):
        row = index.row()
        doc = self.documents[row]
        dialog = DocumentActionDialog(doc, self)
        result = dialog.exec()
        if dialog.renewed:
            new_expiry = dialog.get_new_expiry()
            if new_expiry:
                update_document_expiry(doc, new_expiry)
                self.load_documents()
        elif dialog.deleted:
            delete_document(doc)
            self.load_documents()

class DocumentActionDialog(QDialog):
    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Document Action")
        self.setMinimumWidth(350)
        self.renewed = False
        self.deleted = False
        self._new_expiry = None

        layout = QVBoxLayout(self)
        label = QLabel(
            f"Description: <b>{doc['description']}</b><br>"
            f"Category: <b>{doc['category']}</b><br>"
            f"Expiry Date: <b>{doc['expiry_date']}</b>"
        )
        label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label)

        btn_row = QHBoxLayout()
        renew_btn = QPushButton("Renew Document")
        delete_btn = QPushButton("Delete Document")
        cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(renew_btn)
        btn_row.addWidget(delete_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        renew_btn.clicked.connect(self.handle_renew)
        delete_btn.clicked.connect(self.handle_delete)
        cancel_btn.clicked.connect(self.reject)

    def handle_renew(self):
        date_dlg = QDialog(self)
        date_dlg.setWindowTitle("Renew Document - New Expiry Date")
        layout = QVBoxLayout(date_dlg)
        date_edit = QDateEdit()
        date_edit.setDisplayFormat("dd/MM/yyyy")
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        layout.addWidget(QLabel("New Expiry Date:"))
        layout.addWidget(date_edit)
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)
        ok_btn.clicked.connect(date_dlg.accept)
        cancel_btn.clicked.connect(date_dlg.reject)
        if date_dlg.exec():
            self._new_expiry = date_edit.date().toString("dd/MM/yyyy")
            self.renewed = True
            self.accept()

    def handle_delete(self):
        reply = QMessageBox.question(
            self, "Delete Document",
            "Are you sure you want to delete this document?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.deleted = True
            self.accept()

    def get_new_expiry(self):
        return self._new_expiry

class DocumentEntryDialog(QDialog):
    def __init__(self, parent=None, desc="", cat="", expiry=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Document")
        self.setMinimumWidth(340)
        form = QFormLayout(self)
        self.desc_edit = QLineEdit(desc)
        self.cat_edit = QLineEdit(cat)
        self.expiry_edit = QDateEdit()
        self.expiry_edit.setDisplayFormat("dd/MM/yyyy")
        self.expiry_edit.setCalendarPopup(True)
        if expiry:
            qdate = QDate.fromString(expiry, "dd/MM/yyyy")
            self.expiry_edit.setDate(qdate if qdate.isValid() else QDate.currentDate())
        else:
            self.expiry_edit.setDate(QDate.currentDate())
        form.addRow("Description:", self.desc_edit)
        form.addRow("Category:", self.cat_edit)
        form.addRow("Expiry Date:", self.expiry_edit)
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        form.addRow(btn_row)
        self.setLayout(form)

    def get_values(self):
        return (
            self.desc_edit.text().strip(),
            self.cat_edit.text().strip(),
            self.expiry_edit.date().toString("dd/MM/yyyy")
        )

# --- Persistent storage functions using CSV file (replace with DB for production) ---

def load_documents_from_db():
    docs = []
    try:
        with open("documents.csv", encoding="utf-8") as f:
            for line in f:
                row = line.strip().split(",")
                if len(row) >= 3:
                    docs.append({"description": row[0], "category": row[1], "expiry_date": row[2]})
    except Exception:
        pass
    return docs

def save_document_to_db(desc, cat, expiry):
    with open("documents.csv", "a", encoding="utf-8") as f:
        f.write(f"{desc},{cat},{expiry}\n")

def update_document_expiry(doc, new_expiry):
    docs = load_documents_from_db()
    updated = False
    for d in docs:
        if (d["description"] == doc["description"] and
            d["category"] == doc["category"] and
            d["expiry_date"] == doc["expiry_date"]):
            d["expiry_date"] = new_expiry
            updated = True
            break
    if updated:
        with open("documents.csv", "w", encoding="utf-8") as f:
            for d in docs:
                f.write(f"{d['description']},{d['category']},{d['expiry_date']}\n")

def delete_document(doc):
    docs = load_documents_from_db()
    docs = [
        d for d in docs
        if not (d["description"] == doc["description"] and
                d["category"] == doc["category"] and
                d["expiry_date"] == doc["expiry_date"])
    ]
    with open("documents.csv", "w", encoding="utf-8") as f:
        for d in docs:
            f.write(f"{d['description']},{d['category']},{d['expiry_date']}\n")

class ExpenseCategoryTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.refresh_list()
        layout.addWidget(QLabel("Expense Categories:"))
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_category)
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self.edit_category)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_category)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def refresh_list(self):
        self.list_widget.clear()
        cats = get_expense_categories()
        for cid, name in cats:
            self.list_widget.addItem(name)

    def add_category(self):
        text, ok = QInputDialog.getText(self, "Add Expense Category", "Category Name:")
        if ok and text.strip():
            conn = get_conn()
            c = conn.cursor()
            try:
                c.execute("INSERT INTO expense_categories (name) VALUES (?)", (text.strip(),))
                conn.commit()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Exists", "This category already exists.")
            conn.close()
            self.refresh_list()

    def edit_category(self):
        selected = self.list_widget.currentItem()
        if not selected:
            return
        old_name = selected.text()
        text, ok = QInputDialog.getText(self, "Edit Expense Category", "Category Name:", text=old_name)
        if ok and text.strip():
            conn = get_conn()
            c = conn.cursor()
            try:
                c.execute("UPDATE expense_categories SET name=? WHERE name=?", (text.strip(), old_name))
                conn.commit()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Exists", "This category already exists.")
            conn.close()
            self.refresh_list()

    def delete_category(self):
        selected = self.list_widget.currentItem()
        if not selected:
            return
        name = selected.text()
        reply = QMessageBox.question(self, "Confirm", f"Delete category '{name}'? This will also remove associated expense entries.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT id FROM expense_categories WHERE name=?", (name,))
            res = c.fetchone()
            if res:
                cat_id = res[0]
                c.execute("DELETE FROM daily_expense WHERE category_id=?", (cat_id,))
                c.execute("DELETE FROM expense_categories WHERE id=?", (cat_id,))
                conn.commit()
            conn.close()
            self.refresh_list()

CHECKBOX_STYLESHEET = """
QCheckBox {
    background-color: #3A3A3C;
    color: #F1F3F4;
    font-size: 15px;
    padding: 10px 20px;
    border: 2px solid #5F6368;
    border-radius: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QCheckBox:checked {
    background-color: #1E8E3E;
    color: white;
    border-color: #1E8E3E;
}
"""

class ChequeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Cheque")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)
        self.cheque_date = QDateEdit()
        self.cheque_date.setDisplayFormat("dd-MM-yyyy")
        self.cheque_date.setCalendarPopup(True)
        self.cheque_date.setDate(QDate.currentDate())
        layout.addRow("Issue Date:", self.cheque_date)

        # Vendor ComboBox for Company Name
        self.company_name = QComboBox()
        self.company_name.setEditable(True)
        self.company_name.setPlaceholderText("Select or type vendor name")
        layout.addRow("Company Name:", self.company_name)

        self.bank_name = QLineEdit()
        self.bank_name.setPlaceholderText("Bank Name")
        layout.addRow("Bank Name:", self.bank_name)

        self.due_date = QDateEdit()
        self.due_date.setDisplayFormat("dd-MM-yyyy")
        self.due_date.setCalendarPopup(True)
        self.due_date.setDate(QDate.currentDate())
        layout.addRow("Due Date:", self.due_date)

        self.amount = QLineEdit()
        self.amount.setPlaceholderText("Amount")
        layout.addRow("Amount (AED):", self.amount)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)
        layout.addRow(btn_row)

    def get_values(self):
        cheque_iso = self.cheque_date.date().toString("yyyy-MM-dd")
        due_iso = self.due_date.date().toString("yyyy-MM-dd")
        return (
            cheque_iso,
            self.company_name.currentText().strip(),
            self.bank_name.text().strip(),
            due_iso,
            self.amount.text().strip()
        )

class ChequesTab(QWidget):
    chequePaid = pyqtSignal()  # <--- Signal to notify when a cheque is paid

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        # ... rest of __init__ setup as before ...

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add Cheque")
        self.add_btn.clicked.connect(self.show_add_dialog)
        btn_row.addWidget(self.add_btn)
        btn_row.addStretch()
        self.layout.addLayout(btn_row)

        self.add_shortcut = QShortcut(QKeySequence("F1"), self)
        self.add_shortcut.activated.connect(self.show_add_dialog)
        self.add_btn.setToolTip("Shortcut: F1")

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Issue Date", "Company", "Bank", "Due Date", "Amount (AED)", "Days Remaining", "ID"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setColumnHidden(6, True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.table)

        self.remaining_label = QLabel("")
        remaining_font = QFont()
        remaining_font.setPointSize(15)
        remaining_font.setBold(True)
        self.remaining_label.setFont(remaining_font)
        self.remaining_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.remaining_label.setStyleSheet("color:#43a047; margin:8px 12px 0 0;")
        self.layout.addWidget(self.remaining_label)

        self.ensure_db()
        self.refresh()

    def ensure_db(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS cheques (
                id INTEGER PRIMARY KEY,
                cheque_date TEXT,
                company_name TEXT,
                bank_name TEXT,
                due_date TEXT,
                amount REAL,
                is_paid INTEGER DEFAULT 0
            )
        ''')
        try:
            c.execute("ALTER TABLE cheques ADD COLUMN is_paid INTEGER DEFAULT 0")
        except Exception:
            pass  # Already exists
        conn.commit()
        conn.close()

    def show_add_dialog(self):
        dialog = ChequeDialog(self)
        if dialog.exec():
            cheque_iso, company, bank, due_iso, amount = dialog.get_values()
            amt = parse_amount(amount)
            if amt <= 0 or not company or not bank:
                QMessageBox.warning(self, "Error", "Please enter valid data.")
                return
            conn = get_conn()
            c = conn.cursor()
            c.execute(
                "INSERT INTO cheques (cheque_date, company_name, bank_name, due_date, amount, is_paid) VALUES (?, ?, ?, ?, ?, 0)",
                (cheque_iso, company, bank, due_iso, amt)
            )
            conn.commit()
            conn.close()
            self.refresh()

    def refresh(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, cheque_date, company_name, bank_name, due_date, amount, is_paid FROM cheques ORDER BY due_date ASC")
        rows = c.fetchall()
        conn.close()

        total_due = 0.0
        self.table.setRowCount(len(rows))
        for i, (cid, cdate, company, bank, due, amt, is_paid) in enumerate(rows):
            self.table.setItem(i, 0, self._center_item(to_ddmmyyyy(cdate)))
            self.table.setItem(i, 1, self._center_item(company))
            self.table.setItem(i, 2, self._center_item(bank))
            self.table.setItem(i, 3, self._center_item(to_ddmmyyyy(due)))
            self.table.setItem(i, 4, self._center_item(f"{amt:.2f}"))

            days = days_remaining(due)
            days_item = QTableWidgetItem()
            days_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            days_item.setFont(self._bold_font())
            if is_paid:
                days_item.setText("Paid")
                days_item.setForeground(Qt.GlobalColor.green)
            else:
                if days is None:
                    days_item.setText("-")
                    days_item.setForeground(Qt.GlobalColor.gray)
                elif days > 10:
                    days_item.setText(f"{days} days")
                    days_item.setForeground(Qt.GlobalColor.green)
                elif 0 <= days <= 10:
                    days_item.setText(f"{days} days")
                    days_item.setForeground(Qt.GlobalColor.yellow)
                else:
                    days_item.setText(f"Overdue by {-days} days")
                    days_item.setForeground(Qt.GlobalColor.red)
                # Only sum up cheques that are not paid and not overdue
                if days is not None and days >= 0:
                    total_due += float(amt)
            self.table.setItem(i, 5, days_item)
            self.table.setItem(i, 6, QTableWidgetItem(str(cid)))
            self.table.setRowHeight(i, 34)
        self.table.setColumnHidden(6, True)

        self.remaining_label.setText(f"Total Remaining Cheques Due: {total_due:.2f} AED")

    def _bold_font(self):
        font = self.table.font()
        font.setBold(True)
        font.setPointSize(13)
        return font

    def _center_item(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def show_context_menu(self, pos: QPoint):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        cheque_id = int(self.table.item(row, 6).text())
        is_paid = self.table.item(row, 5).text().strip().lower() == "paid"

        menu = QMenu(self)
        if not is_paid:
            mark_paid_action = menu.addAction("Mark as Paid")
        delete_action = menu.addAction("Delete Cheque")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action:
            if not is_paid and action == mark_paid_action:
                self.mark_cheque_paid(cheque_id)
            elif action == delete_action:
                self.delete_cheque(cheque_id)

    def mark_cheque_paid(self, cheque_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE cheques SET is_paid=1 WHERE id=?", (cheque_id,))
        c.execute("SELECT company_name, amount FROM cheques WHERE id=?", (cheque_id,))
        row = c.fetchone()
        if row:
            company_name, amount = row
            today_iso = date.today().isoformat()
            # Make sure the "Vendors" expense category exists
            c.execute("SELECT id FROM expense_categories WHERE name='Vendors'")
            cat_row = c.fetchone()
            if cat_row:
                cat_id = cat_row[0]
            else:
                c.execute("INSERT INTO expense_categories (name) VALUES ('Vendors')")
                cat_id = c.lastrowid
            descr = company_name
            # Prevent duplicate entry
            c.execute("""
                SELECT 1 FROM daily_expense WHERE date=? AND amount=? AND category_id=? AND description=?
            """, (today_iso, amount, cat_id, descr))
            if not c.fetchone():
                c.execute(
                    '''INSERT INTO daily_expense (date, amount, category_id, description, notes)
                    VALUES (?, ?, ?, ?, ?)''',
                    (today_iso, amount, cat_id, descr, "Paid via Cheque")
                )
        conn.commit()
        conn.close()
        self.refresh()
        self.chequePaid.emit()
    def delete_cheque(self, cheque_id):
        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this cheque?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = get_conn()
            c = conn.cursor()
            c.execute("DELETE FROM cheques WHERE id=?", (cheque_id,))
            conn.commit()
            conn.close()
            self.refresh()

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(250)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: 2px solid rgba(251,112,14,0.35); /* Dimmed #fb700e */
                border-radius: 11px;
                color: #f1f3f4;
                font-size: 15px;
                font-weight: bold;
                margin: 8px 0 8px 8px;
                padding: 5px 0;
                outline: 0;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                border-radius: 5px;
                margin: 5px 8px 5px 8px;
                padding: 5px 10px 5px 10px;
                min-height: 38px;
                font-size: 15px;
                color: #b7b7b7;
                qproperty-icon: url(right-arrow.png); /* fallback; see below for dynamic icon */
                qproperty-iconSize: 20px 20px;
            }
            QListWidget::item:selected {
                background: rgba(251,112,14,0.10);
                color: #fb700e;
            }
            QListWidget::item:selected:!active {
                background: rgba(251,112,14,0.10);
                color: #fb700e;;
            }
            QListWidget::item:hover {
                background: rgba(251,112,14,0.10);
                color: #fb700e;
            }
        """)
        # Add items with right arrow icon
        arrow_icon = QIcon()
        arrow_icon.addPixmap(self.style().standardPixmap(QStyle.StandardPixmap.SP_ArrowForward))
        for label in ["Company Information", "Import/Export", "Expense Categories", "Manage Payroll", "Reports"]:
            item = QListWidgetItem(label)
            item.setIcon(arrow_icon)
            self.sidebar.addItem(item)
        self.layout.addWidget(self.sidebar)

        # Stacked content
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        # Comapany Information Page
        company_info_page = QWidget()
        company_layout = QVBoxLayout(company_info_page)

        title = QLabel("Company Information")
        title.setStyleSheet("font-size:22px; font-weight:600; margin-bottom:14px;")
        company_layout.addWidget(title)

        form = QFormLayout()
        self.company_name_edit = QLineEdit()
        self.business_type_edit = QLineEdit()
        self.incorp_date_edit = QDateEdit()
        self.incorp_date_edit.setCalendarPopup(True)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(50, 50)
        self.logo_label.setScaledContents(True)
        self.load_app_logo()
        self.upload_logo_btn = QPushButton("Upload Logo")
        self.upload_logo_btn.clicked.connect(self.upload_logo)
        self.reg_address_edit = QLineEdit()
        self.reg_address_edit.setFixedHeight(56)
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.website_edit = QLineEdit()
        self.taxid_edit = QLineEdit()

        form.addRow("Company Name", self.company_name_edit)
        form.addRow("Business Type", self.business_type_edit)
        form.addRow("Date of Incorporation", self.incorp_date_edit)
        logo_row = QHBoxLayout()
        logo_row.addWidget(self.logo_label)
        logo_row.addWidget(self.upload_logo_btn)
        form.addRow("Logo", logo_row)
        form.addRow("Registered Address", self.reg_address_edit)
        form.addRow("Phone Number", self.phone_edit)
        form.addRow("Email Address", self.email_edit)
        form.addRow("Website", self.website_edit)
        form.addRow("Tax ID", self.taxid_edit)

        company_layout.addLayout(form)
        company_layout.addStretch(1)
        self.stack.addWidget(company_info_page)

        # Backup/Import/Export Page
        backup_page = QWidget()
        backup_vbox = QVBoxLayout(backup_page)
        backup_title = QLabel("Backup, Import & Export")
        backup_title.setStyleSheet("font-size:22px; font-weight:600; margin-bottom:14px;")
        backup_vbox.addWidget(backup_title)

        backup_row = QHBoxLayout()
        self.backup_btn = QPushButton("Backup Now")
        self.backup_btn.clicked.connect(self.backup_database)
        backup_row.addWidget(self.backup_btn)
        self.export_btn = QPushButton("Export Data")
        self.export_btn.clicked.connect(self.export_database)
        backup_row.addWidget(self.export_btn)
        self.import_btn = QPushButton("Import Data")
        self.import_btn.clicked.connect(self.import_database)
        backup_row.addWidget(self.import_btn)
        backup_row.addStretch()
        backup_vbox.addLayout(backup_row)
        backup_vbox.addWidget(QLabel("Backups are created automatically on open and close.\nManual backup will create a timestamped copy in your Documents."))
        backup_vbox.addStretch(1)
        self.stack.addWidget(backup_page)

        # Expense Categories Page
        self.expense_categories_tab = ExpenseCategoryTab()
        self.stack.addWidget(self.expense_categories_tab)

        self.manage_payroll_tab = ManagePayrollTab()
        self.stack.addWidget(self.manage_payroll_tab)

        # Reports Page
        reports_page = QWidget()
        reports_layout = QVBoxLayout(reports_page)
        title = QLabel("Reports")
        title.setStyleSheet("font-size:22px; font-weight:600; margin-bottom:14px;")
        reports_layout.addWidget(title)

        self.monthly_report_btn = QPushButton("Monthly Financial Report")
        self.monthly_report_btn.setFixedWidth(250)
        self.monthly_report_btn.setStyleSheet("font-size:16px; font-weight:600; background:#fb700e; color:white; border-radius:7px; padding:12px 18px;")
        self.monthly_report_btn.clicked.connect(self._monthly_report_btn_clicked)
        reports_layout.addWidget(self.monthly_report_btn)
        reports_layout.addStretch()
        self.stack.addWidget(reports_page)

        # Sidebar navigation
        self.sidebar.setCurrentRow(0)
        self.stack.setCurrentIndex(0)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.setLayout(self.layout)

    def _monthly_report_btn_clicked(self):
        # Dialog to select month/year for export
        dialog = QDialog(self)
        dialog.setWindowTitle("Export Monthly Report PDF")
        layout = QFormLayout(dialog)
        month_combo = QComboBox()
        for m in range(1, 13):
            month_combo.addItem(QDate(2000, m, 1).toString("MMMM"), m)
        month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        year_combo = QComboBox()
        current_year = QDate.currentDate().year()
        for y in range(current_year, 1999, -1):
            year_combo.addItem(str(y), y)
        year_combo.setCurrentText(str(current_year))
        layout.addRow("Month:", month_combo)
        layout.addRow("Year:", year_combo)
        btn_box = QHBoxLayout()
        ok_btn = QPushButton("Export PDF")
        cancel_btn = QPushButton("Cancel")
        btn_box.addWidget(ok_btn)
        btn_box.addWidget(cancel_btn)
        layout.addRow(btn_box)
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            month = month_combo.currentData()
            year = year_combo.currentData()
            self.show_monthly_report_export_pdf(month, year)

    def show_monthly_report_export_pdf(self, month, year):
        q_month = f"{month:02}"
        q_year = str(year)
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT date FROM (
                SELECT date FROM daily_income
                UNION
                SELECT date FROM daily_expense
            ) WHERE strftime('%m', date)=? AND strftime('%Y', date)=?
            ORDER BY date
        """, (q_month, q_year))
        days = [row[0] for row in c.fetchall()]
        rows = []
        total_sales = 0
        total_services = 0
        total_income = 0
        total_expenses = 0
        total_balance = 0

        for day in days:
            c.execute("""
                SELECT SUM(amount) FROM daily_income di
                LEFT JOIN income_categories ic ON di.category_id=ic.id
                WHERE di.date=? AND ic.name='Sales'
            """, (day,))
            sales = c.fetchone()[0] or 0
            c.execute("""
                SELECT SUM(amount) FROM daily_income di
                LEFT JOIN income_categories ic ON di.category_id=ic.id
                WHERE di.date=? AND ic.name='Services'
            """, (day,))
            services = c.fetchone()[0] or 0
            daily_income = sales + services
            c.execute("SELECT SUM(amount) FROM daily_expense WHERE date=?", (day,))
            expenses = c.fetchone()[0] or 0
            balance = daily_income - expenses
            rows.append((to_ddmmyyyy(day), sales, services, daily_income, expenses, balance))
            total_sales += sales
            total_services += services
            total_income += daily_income
            total_expenses += expenses
            total_balance += balance

        c.execute("""
            SELECT COALESCE(SUM(amount),0) FROM daily_capital
            WHERE strftime('%m', date)=? AND strftime('%Y', date)=? AND category='Additional Capital'
        """, (q_month, q_year))
        additional_capital = c.fetchone()[0] or 0
        available_cash = total_income - total_expenses + additional_capital
        profit_percent = (total_balance / total_income * 100) if total_income else 0
        conn.close()

        # Prepare logo as base64 if available
        logo_path = os.path.join(os.path.expanduser("~"), ".national_bicycles_logo.png")
        logo_html = ""
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_data = base64.b64encode(f.read()).decode("utf-8")
                logo_html = f"<img class='logo' src='data:image/png;base64,{logo_data}'/>"
        month_title = QDate(year, month, 1).toString('MMMM yyyy')

        # --- Modern PDF Style HTML ---
        html = f"""
    <html>
    <head>
    <style>
    body {{
        font-family: 'Segoe UI', 'Arial', sans-serif;
        background: #f6f7fa;
        color: #232627;
        margin: 0;
        padding: 0;
    }}
    .wrapper {{
        max-width: 950px;
        margin: 28px auto;
        background: #fff;
        border-radius: 18px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.10);
        padding: 12px 36px 15px 36px;
    }}
    .header {{
        display: flex;
        align-items: center;
        border-bottom: 4px solid #fb700e;
        padding-bottom: 10px;
    }}
    .logo {{
        height: 78px;
        margin-right: 28px;
    }}
    .title-section {{
        flex: 1;
        text-align: right;
    }}
    h1 {{
        margin: 0;
        font-size: 22px;
        font-weight: 800;
        color: #fb700e;
        letter-spacing: 1px;
    }}
    h2 {{
        margin: 6px 0 0 0;
        font-size: 17px;
        color: #1e88e5;
        font-weight: 700;
    }}
    .report-table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin: 20px 0 20px 0;
        background: #fff;
        border-radius: 5px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(255,112,14,0.04);
    }}
    .report-table th {{
        background: #fb700e;
        color: #fff;
        font-size: 12px;
        font-weight: 700;
        padding: 6px 0;
        border: none;
    }}
    .report-table td {{
        font-size: 12px;
        padding: 4px 0;
        border: none;
        text-align: center;
        transition: background 0.2s;
    }}
    .report-table tr:nth-child(odd) td {{
        background: #faf8f4;
    }}
    .report-table tr.total-row td {{
        background: #ffe0b2;
        color: #1d2a3a;
        font-weight: 700;
        font-size: 14px;
        border-top: 3px solid #fb700e;
    }}
    .summary-box {{
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin: 20px 0 0 0;
    }}
    .summary-item {{
        flex: 1 1 0;
        background: #f7fafe;
        border-radius: 5px;
        padding: 10px 5px 5px 10px;
        box-shadow: 0 1px 6px rgba(30,136,229,0.04);
        text-align: center;
        border-left: 7px solid #fb700e;
    }}
    .summary-item.blue {{ border-left-color: #1976d2; }}
    .summary-item.green {{ border-left-color: #43a047; }}
    .summary-item.orange {{ border-left-color: #fb700e; }}
    .summary-title {{
        font-size: 15px;
        color: #777;
        font-weight: 700;
        margin-bottom: 4px;
        letter-spacing: 0.5px;
    }}
    .summary-value {{
        font-size: 17px;
        font-weight: bold;
        color: #232627;
    }}
    .summary-value.green {{ color: #43a047; }}
    .summary-value.orange {{ color: #fb700e; }}
    .summary-value.blue {{ color: #1976d2; }}
    .summary-value.red {{ color: #e53935; }}
    .footer {{
        margin-top: 20px;
        text-align: right;
        color: #888;
        font-size: 13px;
    }}
    @media print {{
        body, .wrapper {{ box-shadow:none; background: #fff; }}
    }}
    </style>
    </head>
    <body>
    <div class="wrapper">
        <div class="header">
            {logo_html if logo_html else ''}
            <div class="title-section">
                <h1>Monthly Financial Report</h1>
                <h2>{month_title}</h2>
            </div>
        </div>
        <table class="report-table">
            <tr>
                <th>Date</th>
                <th>Sales</th>
                <th>Service</th>
                <th>Total Income</th>
                <th>Expenses</th>
                <th>Balance</th>
            </tr>
        """

        for d, sales, services, income, expenses, balance in rows:
            bal_class = "red" if balance < 0 else "green"
            html += f"""
            <tr>
                <td>{d}</td>
                <td>{sales:,.2f}</td>
                <td>{services:,.2f}</td>
                <td>{income:,.2f}</td>
                <td>{expenses:,.2f}</td>
                <td class="summary-value {bal_class}">{balance:,.2f}</td>
            </tr>
            """
        total_bal_class = "red" if total_balance < 0 else "green"
        html += f"""
            <tr class="total-row">
                <td>TOTAL</td>
                <td>{total_sales:,.2f}</td>
                <td>{total_services:,.2f}</td>
                <td>{total_income:,.2f}</td>
                <td>{total_expenses:,.2f}</td>
                <td class="summary-value {total_bal_class}">{total_balance:,.2f}</td>
            </tr>
        </table>
        <div class="summary-box">
            <div class="summary-item green">
                <div class="summary-title">Available Cash in Hand</div>
                <div class="summary-value green">{available_cash:,.2f} AED</div>
            </div>
            <div class="summary-item blue">
                <div class="summary-title">Additional Capital</div>
                <div class="summary-value blue">{additional_capital:,.2f} AED</div>
            </div>
            <div class="summary-item orange">
                <div class="summary-title">Profit %</div>
                <div class="summary-value orange">{profit_percent:,.2f} %</div>
            </div>
        </div>
        <div class="footer">
            Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}
        </div>
    </div>
    </body>
    </html>
    """    

        # Go directly to export PDF dialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Monthly Report PDF", f"MonthlyReport_{year}-{month:02}.pdf", "PDF Files (*.pdf)")
        if not file_path:
            return
        view = QWebEngineView()
        loop = QEventLoop()

        view.setHtml(html)

        def on_html_loaded(ok):
            if ok:
                # Use the correct overload: just the file path!
                view.page().printToPdf(file_path)
                QMessageBox.information(self, "Export PDF", f"PDF exported:\n{file_path}")
                loop.quit()
            else:
                QMessageBox.critical(self, "Export PDF", "Failed to render HTML for PDF export.")
                loop.quit()

        view.loadFinished.connect(on_html_loaded)
        loop.exec()

    # Logo methods
    def upload_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Logo Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            logo_dest = os.path.join(os.path.expanduser("~"), ".national_bicycles_logo.png")
            shutil.copyfile(file_path, logo_dest)
            self.set_logo(logo_dest)
            mw = self.parent()
            while mw is not None and not isinstance(mw, QMainWindow):
                mw = mw.parent()
            if mw is not None and hasattr(mw, "setWindowIcon"):
                mw.setWindowIcon(QIcon(logo_dest))

    def load_app_logo(self):
        logo_path = os.path.join(os.path.expanduser("~"), ".national_bicycles_logo.png")
        if os.path.exists(logo_path):
            self.set_logo(logo_path)

    def set_logo(self, path):
        pixmap = QPixmap(path)
        self.logo_label.setPixmap(pixmap)

    # Backup/Export/Import methods
    def backup_database(self):
        src = DB_NAME
        backup_dir = os.path.join(os.path.expanduser("~"), "NationalBicyclesBackups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.db")
        shutil.copyfile(src, backup_file)
        QMessageBox.information(self, "Backup", f"Database backup created:\n{backup_file}")

    def export_database(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Export Database As", "NationalBicyclesExport.db", "Database Files (*.db)")
        if save_path:
            shutil.copyfile(DB_NAME, save_path)
            QMessageBox.information(self, "Export", f"Database exported to:\n{save_path}")

    def import_database(self):
        open_path, _ = QFileDialog.getOpenFileName(self, "Import Database", "", "Database Files (*.db)")
        if open_path:
            self.backup_database()
            shutil.copyfile(open_path, DB_NAME)
            QMessageBox.information(self, "Import", "Database imported and app will restart.")
            os.execl(sys.executable, sys.executable, *sys.argv)

class TransactionTypeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_type = None
        self.setWindowTitle("Select Transaction Type")
        self.setMinimumWidth(300)
        self.setStyleSheet("QDialog { background: #181A1B; } QLabel { color: #F1F3F4; font-size: 16px; font-weight: 600; }")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("What type of transaction is this?"))
        btn_row = QHBoxLayout()
        self.purchase_btn = QPushButton("Purchase")
        self.payment_btn = QPushButton("Payment")
        self.return_btn = QPushButton("Return")
        for b in [self.purchase_btn, self.payment_btn, self.return_btn]:
            b.setMinimumHeight(32)
            b.setStyleSheet(
                "QPushButton { background:#232627; color:#F1F3F4; border-radius:8px; font-size:14px; font-weight:600; padding:8px 18px; }"
                "QPushButton:hover { background:#35393A; color:#fb700e; }"
            )
            btn_row.addWidget(b)
        layout.addLayout(btn_row)
        self.purchase_btn.clicked.connect(lambda: self.select_type("purchase"))
        self.payment_btn.clicked.connect(lambda: self.select_type("payment"))
        self.return_btn.clicked.connect(lambda: self.select_type("return"))

    def select_type(self, t):
        self.selected_type = t
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("National Bicycles 1.0")
        self.setGeometry(200, 200, 1200, 760)
        self.setStyleSheet(DARK_STYLESHEET)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.setObjectName("mainTabs")  # Add this line!
        # Set window icon from logo, if exists
        logo_path = os.path.join(os.path.expanduser("~"), ".national_bicycles_logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self.dashboard = DashboardTab()
        self.daily = DailyTab(self.dashboard)
        self.cheques_tab = ChequesTab()
        self.payroll_tab = PayrollTab()
        self.documents_tab = DocumentsTab()
        self.settings_tab = SettingsTab()
        
        self.tabs.addTab(self.daily, QIcon(), "  Cashflow  ")
        self.tabs.addTab(self.cheques_tab, QIcon(), "  Cheques  ")
        self.tabs.addTab(self.payroll_tab, QIcon(), "  Payroll  ")
        self.tabs.addTab(self.documents_tab, QIcon(), "  Documents  ")
        self.tabs.addTab(self.dashboard, QIcon(), "  Dashboard  ")
        self.tabs.addTab(self.settings_tab, QIcon(), "  Settings  ")

        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.do_auto_backup("open")

    

    def do_auto_backup(self, event):
        src = DB_NAME
        backup_dir = os.path.join(os.path.expanduser("~"), "NationalBicyclesBackups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f"auto_{event}_{timestamp}.db")
        try:
            shutil.copyfile(src, backup_file)
        except Exception:
            pass

    def closeEvent(self, event):
        self.do_auto_backup("close")
        super().closeEvent(event)

    def on_tab_changed(self, idx):
        tab = self.tabs.widget(idx)
        if tab == self.cheques_tab:
            self.cheques_tab.refresh()

def main():
    app = QApplication(sys.argv)
    # Set global app icon EARLY
    icon_path = os.path.join(os.path.expanduser("~"), ".national_bicycles_logo.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    init_db()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()