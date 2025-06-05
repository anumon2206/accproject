import sys
import sqlite3
import os
import shutil
from datetime import date, datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFormLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QMessageBox, QDialog, QListWidget, QInputDialog,
    QDateEdit, QHeaderView, QFrame, QGridLayout, QStyle,
    QFileDialog, QCheckBox, QStackedWidget, QSizePolicy, QCompleter, QGroupBox, QMenu, QGraphicsColorizeEffect,
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt6.QtGui import (
    QKeySequence, QShortcut, QFont, QTextDocument, QPageSize, QPageLayout, QIcon, QColor, QPixmap
)
from PyQt6.QtCore import Qt, QDate, QSizeF, QMarginsF, QPoint, pyqtSignal

DB_NAME = "accounting.db"

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
            vendor_transaction_id INTEGER,
            notes TEXT,
            FOREIGN KEY(category_id) REFERENCES expense_categories(id)
        )''', None),
        ('''CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            contact TEXT,
            opening_balance REAL DEFAULT 0
        )''', None),
        ('''CREATE TABLE IF NOT EXISTS vendor_transactions (
            id INTEGER PRIMARY KEY,
            vendor_id INTEGER,
            date TEXT,
            type TEXT,
            amount REAL,
            note TEXT,
            due_date TEXT,
            invoice_no TEXT,
            payment_mode TEXT,
            net_terms TEXT,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
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
            is_paid INTEGER DEFAULT 0,
            vendor_transaction_id INTEGER
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

def get_vendor_names():
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT name FROM vendors ORDER BY name COLLATE NOCASE ASC").fetchall()]

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

def get_all_descriptions():
    with get_conn() as conn:
        income_descs = [row[0] for row in conn.execute("SELECT DISTINCT description FROM daily_income WHERE description IS NOT NULL AND description <> ''")]
        expense_descs = [row[0] for row in conn.execute("SELECT DISTINCT description FROM daily_expense WHERE description IS NOT NULL AND description <> ''")]
    return list(set(income_descs + expense_descs))

def ensure_default_income_categories():
    conn = get_conn()
    c = conn.cursor()
    for name in ["Sales", "Services"]:
        c.execute("INSERT OR IGNORE INTO income_categories (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


DARK_STYLESHEET = """
QMainWindow, QWidget {
    background: #181A1B;
    color: #F1F3F4;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}
/* ... [rest of stylesheet as in your previous code, unchanged] ... */
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
    border-radius: 8px;
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
    border-radius: 8px;
    padding: 5px;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #232627;
    width: 12px;
    margin: 0px;
    border-radius: 6px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #35393A;
    border-radius: 6px;
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

"""

# ---------------- Dialog and Tab Classes ----------------

class EntryEditDialog(QDialog):
    def __init__(self, entry_type, entry_id, date, cat_id, amount, desc, notes='', parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Entry")
        self.entry_type = entry_type
        self.entry_id = entry_id
        self.setMinimumWidth(390)
        self.setStyleSheet("""
            QDialog { background: #222325; }
            QLineEdit, QComboBox { border-radius: 8px; padding: 8px; font-size: 15px; background: #232627; color: #F1F3F4;}
            QLabel { font-size: 15px; color: #F1F3F4; background: transparent;}
            QComboBox { background: #232627; }
            QPushButton { border-radius: 8px; padding: 10px 20px; font-size: 15px; background:#26292A; color:#F1F3F4;}
            QDialogButtonBox QPushButton { min-width: 90px; }
        """)
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
            float(self.amount_input.text()),
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
        self.setStyleSheet("""
            QDialog { background: #181A1B; }
            QLabel { font-size: 15px; font-weight: 600; color: #F1F3F4;}
            QLineEdit, QComboBox, QDateEdit {
                border-radius: 8px; padding: 8px; font-size: 14px;
                border: 1.3px solid #35393A; background: #232627; color: #F1F3F4;
            }
            QPushButton {
                border-radius: 8px; padding: 9px 18px; font-size: 14px;
                background: #26292A; color: #F1F3F4; font-weight: bold;
            }
            QPushButton:pressed {
                background: #35393A;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 2px solid #fb700e;
            }
        """)

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
        self.type_input.addItems(["Income", "Expense", "Capital"])
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
        if t == "Income":
            for cid, name in get_income_categories():
                self.category_input.addItem(name, cid)
        elif t == "Expense":
            for cid, name in get_expense_categories():
                if name.strip().lower() == "vendors":
                    continue
                self.category_input.addItem(name, cid)
        elif t == "Capital":
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
        self.setStyleSheet("""
            QComboBox, QLineEdit, QDateEdit {
                border-radius: 2px;
                background: #232627;
                padding: 7px;
                font-size: 14px;
                border: 1px solid #35393A;
                color: #F1F3F4;
            }
            QLabel {
                color: #F1F3F4;
                font-weight: 600;
            }
            QPushButton {
                border-radius: 5px;
                padding: 7px 16px;
                font-size: 14px;
                background: #232627;
                color: #F1F3F4;
                border: 1.5px solid #35393A;
                font-weight:bold;
            }
            QPushButton:hover {
            color: #fb700e;
            border: 1.5px solid #fb700e;
            }
            QPushButton:pressed {
                background: #35393A;
                color: #fff;
            }
        """)

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
        self.date_from.setMinimumWidth(140) 

        self.date_to = QDateEdit()
        self.date_to.setDisplayFormat("dd-MM-yyyy")
        self.date_to.setCalendarPopup(True)
        self.date_to.setMinimumWidth(140) 

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
        self.setStyleSheet("""
            QLabel#dashboardTitle {
                font-size: 36px;
                font-weight: 800;
                color: #fb700e;
                margin-bottom: 12px;
                letter-spacing: 1px;
            }
            QLabel#dashboardSubtitle {
                font-size: 19px;
                color: #bcbcbc;
                font-weight: 500;
                margin-bottom: 20px;
            }
        """)
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

    def set_month(self):
        self.selected_month = self.month_combo.currentData()
        self.selected_year = self.year_combo.currentData()
        self.refresh()

    def get_total_accounts_payable(self):
        conn = get_conn()
        c = conn.cursor()
        total_payable = 0.0
        c.execute("SELECT id, opening_balance FROM vendors")
        vendors = c.fetchall()
        for vid, opening_balance in vendors:
            c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='purchase'", (vid,))
            purchases = c.fetchone()[0] or 0
            c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='payment'", (vid,))
            payments = c.fetchone()[0] or 0
            c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='return'", (vid,))
            returns = c.fetchone()[0] or 0
            balance = opening_balance + purchases - payments - returns
            if balance > 0:
                total_payable += balance
        conn.close()
        return total_payable

    def kpi_card_rect(self, icon, title, amount, color, bg="#232627"):
        box = QFrame()
        box.setStyleSheet(
            f"""
                QFrame {{
                    background: {bg};
                    border-radius: 5px;
                    padding: 0px 0px;
                    /* Remove border for no outline */
                }}
            """
        )
        h = QHBoxLayout(box)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(4)
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size:38px; color:{color};")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size:16px;color:#bcbcbc; font-weight:700; margin-bottom:0px;")
        right.addWidget(title_label)
        amount_label = QLabel(amount)
        amount_label.setStyleSheet(
            f"font-size:24px;font-weight:700;color:{color};margin-top:2px;letter-spacing:1px;"
        )
        right.addWidget(amount_label)
        right.addStretch()
        h.addLayout(right)
        return box

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
        total_payable = self.get_total_accounts_payable()

        card_data = [
            ("\U0001F4B0", "Total Income", f"{income:.2f} AED", "#43a047"),
            ("\U0001F4B8", "Total Expenses", f"{expenses:.2f} AED", "#e53935"),
            ("\U0001F4B5", "Balance", f"{balance:.2f} AED", "#fbc02d" if balance >= 0 else "#e53935"),
            ("\U0001F4C8", "Profit %", f"{profit_percent:.2f} %", "#43a047" if profit_percent >= 0 else "#e53935"),
            ("\U0001F4B3", "A/P Vendors", f"{total_payable:.2f} AED", "#fb700e"),
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

        self.add_entry_btn = QPushButton("Add")
        self.add_entry_btn.setToolTip("Add Income/Expense Entry (F1)")
        self.add_entry_btn.setFixedSize(120, 40)
        self.add_entry_btn.setStyleSheet("background:#26292A; color:white; font-size: 16px; font-weight: bold; border-radius: 3px;")
        self.add_entry_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.add_entry_btn.setIconSize(QSizeF(22, 22).toSize())
        self.add_entry_btn.setText(" Add")
        self.add_entry_btn.clicked.connect(self.show_entry_dialog)
        btn_left_layout.addWidget(self.add_entry_btn)

        self.add_shortcut = QShortcut(QKeySequence("F1"), self)
        self.add_shortcut.activated.connect(self.show_entry_dialog)
        self.add_entry_btn.setToolTip("Add Income/Expense Entry (F1)")

        self.print_btn = QPushButton("Print")
        self.print_btn.setToolTip("Print Day Report (F10)")
        self.print_btn.setFixedSize(120, 40)
        self.print_btn.setStyleSheet("background:#26292A; color:white; font-size: 16px; font-weight: bold; border-radius: 3px;")
        self.print_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.print_btn.setIconSize(QSizeF(22, 22).toSize())
        self.print_btn.setText(" Print")
        self.print_btn.clicked.connect(self.print_day_report)
        btn_left_layout.addWidget(self.print_btn)

        btn_row.addWidget(btn_left_container)
        btn_row.addStretch()

        # --- Today section with calendar icon, orange box, styled text ---

        today_box = QFrame()
        today_box.setObjectName("TodayBox")
        today_box.setStyleSheet("""
            QFrame#TodayBox {
                background: transparent;
                border-radius: 5px;
                padding: 2px 10px 2px 10px;
                border: 1.5px solid #c9570b;
                min-width: 130px;
                max-width: 160px;
            }
        """)
        today_layout = QHBoxLayout(today_box)
        today_layout.setContentsMargins(7, 4, 7, 4)
        today_layout.setSpacing(7)

        cal_icon = QLabel()
        cal_icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView).pixmap(22, 22))
        cal_icon.setStyleSheet("margin-right: 8px;")
        today_layout.addWidget(cal_icon)

        today_label = QLabel(date.today().strftime('%d-%m-%Y'))
        today_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        today_label.setStyleSheet("""
            font-weight: bold;
            font-size: 18px;
            color: #f5540c;
            letter-spacing: 0.5px;
        """)
        today_layout.addWidget(today_label)

        today_layout.addStretch()
        btn_row.addWidget(today_box)

        layout.addLayout(btn_row)

        layout.addSpacing(14)  # Gap between button row and the label below

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
            try:
                amt = float(amount_text.strip() or 0)
            except Exception:
                amt = 0
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
                if cat_name in ("sales", "services"):
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
                # Store in a separate daily_capital table (create if doesn't exist)
                c.execute("""
                    CREATE TABLE IF NOT EXISTS daily_capital (
                        id INTEGER PRIMARY KEY,
                        date TEXT,
                        amount REAL,
                        category TEXT,
                        description TEXT,
                        notes TEXT
                    )
                """)
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
            income_query = '''SELECT di.date, di.amount, ic.name, 'Income', di.description, di.id, di.category_id, di.notes
                      FROM daily_income di
                      LEFT JOIN income_categories ic ON di.category_id = ic.id
                      WHERE di.date BETWEEN ? AND ?'''
            expense_query = '''SELECT de.date, de.amount, ec.name, 'Expense', de.description, de.id, de.category_id, de.notes
                               FROM daily_expense de
                               LEFT JOIN expense_categories ec ON de.category_id = ec.id
                               WHERE de.date BETWEEN ? AND ?'''
            final_query = f"{income_query} UNION ALL {expense_query} ORDER BY date DESC"
            params = [date_from, date_to, date_from, date_to]
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

        # Fetch capital records separately
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_capital (
                id INTEGER PRIMARY KEY,
                date TEXT,
                amount REAL,
                category TEXT,
                description TEXT,
                notes TEXT
            )
        """)
        c.execute(
            "SELECT date, amount, category, 'Capital', description, id, NULL, notes FROM daily_capital WHERE date BETWEEN ? AND ?",
            (date_from, date_to)
        )
        capital_rows = c.fetchall()
        rows.extend(capital_rows)

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

    def handle_table_double_click(self, idx):
        row = idx.row()
        typ = self.data_table.item(row, 2).text()
        cat = self.data_table.item(row, 3).text()
        # Block editing for Vendors expense
        if typ == "Expense" and cat.strip().lower() == "vendors":
            QMessageBox.information(
                self,
                "Edit in Vendor Tab",
                "Vendor transcations can only be edited from the Vendors tab."
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

    def print_day_report(self):
        selected_date = self.filter_widget.date_from.date().toString("yyyy-MM-dd")
        self._print_report_for_date(selected_date)

    def _print_report_for_date(self, date_iso):
        conn = get_conn()
        c = conn.cursor()

        c.execute("""
            SELECT SUM(amount) FROM daily_income di
            LEFT JOIN income_categories ic ON di.category_id=ic.id
            WHERE di.date=? AND ic.name='Sales'
        """, (date_iso,))
        sales = c.fetchone()[0] or 0

        c.execute("""
            SELECT SUM(amount) FROM daily_income di
            LEFT JOIN income_categories ic ON di.category_id=ic.id
            WHERE di.date=? AND ic.name='Services'
        """, (date_iso,))
        services = c.fetchone()[0] or 0

        total_income = sales + services

        c.execute("SELECT SUM(amount) FROM daily_expense WHERE date=?", (date_iso,))
        total_expense = c.fetchone()[0] or 0
        gross_income = total_income - total_expense

        c.execute("""
            SELECT description, amount FROM daily_expense
            WHERE date=?
            ORDER BY id ASC
        """, (date_iso,))
        expense_rows = c.fetchall()
        conn.close()

        date_ddmmyyyy = QDate.fromString(date_iso, "yyyy-MM-dd").toString("dd/MM/yyyy")

        # Final: Block layout, big font, wide tables, no inline-blocks
        html = f"""
        <div style="font-family:Arial,sans-serif; color:#000;">
        <div style="font-size:24px; font-weight:bold; text-align:center; text-decoration:underline; border-bottom:3px solid #000; margin-bottom:16px;">DAILY REPORT</div>
        <table style="width:100%; font-size:18px; border:2px solid #000; border-collapse:collapse; margin-bottom:14px;">
            <tr>
            <td style="font-weight:bold; border:1.5px solid #000; padding:12px 10px; width:35%;">DATE</td>
            <td style="border:1.5px solid #000; padding:12px 10px; text-align:right; font-weight:bold;">{date_ddmmyyyy}</td>
            </tr>
        </table>
        <table style="width:100%; font-size:19px; border:2.5px solid #000; border-collapse:collapse; margin-bottom:8px;">
            <tr>
            <td style="font-weight:bold; border:1.5px solid #000; padding:14px 10px; width:35%;">TOTAL</td>
            <td style="border:1.5px solid #000; padding:14px 10px; font-weight:bold; text-align:center; width:50px;">AED</td>
            <td style="border:1.5px solid #000; padding:14px 10px; text-align:right; font-weight:bold;">{total_income:,.2f}</td>
            </tr>
            <tr>
            <td style="font-weight:bold; border:1.5px solid #000; padding:14px 10px;">EXPENSE</td>
            <td style="border:1.5px solid #000; padding:14px 10px; font-weight:bold; text-align:center;">AED</td>
            <td style="border:1.5px solid #000; padding:14px 10px; text-align:right; font-weight:bold;">{total_expense:,.2f}</td>
            </tr>
            <tr>
            <td style="font-weight:bold; border:1.5px solid #000; padding:14px 10px;">G.TOTAL</td>
            <td style="border:1.5px solid #000; padding:14px 10px; font-weight:bold; text-align:center;">AED</td>
            <td style="border:1.5px solid #000; padding:14px 10px; text-align:right; font-weight:bold;">{gross_income:,.2f}</td>
            </tr>
        </table>
        <table style="width:100%; border:2.5px solid #2C3E50; border-radius:6px; margin:18px 0 18px 0; border-collapse:collapse;">
            <tr>
            <td style="font-size:32px; font-weight:bold; color:#222; background:#f6f6f6; text-align:center; padding:18px;">{gross_income:,.2f}</td>
            </tr>
        </table>
        <div style="font-weight:bold; font-size:19px; padding:10px 0 10px 0;">Expense Details</div>
        <table style="width:100%; font-size:18px; border-collapse:collapse; margin-bottom:0;">
        """

        if expense_rows:
            for desc, amt in expense_rows:
                html += f"""
                <tr>
                <td style="font-weight:bold; text-align:left; padding:10px 0; border-bottom:1.2px solid #bbb;">{desc or ''}</td>
                <td style="text-align:center; width:46px; font-weight:bold;">AED</td>
                <td style="text-align:right; padding:10px 0; border-bottom:1.2px solid #bbb;">{amt:,.2f}</td>
                </tr>
                """
        else:
            html += '<tr><td colspan="3" style="text-align:center; color:#888; padding:16px 0;">No Expenses</td></tr>'

        html += "</table>"
        html += '<div style="border-bottom:3px solid #000; margin-top:16px; min-height:28px;"></div>'
        html += "</div>"

        doc = QTextDocument()
        doc.setDefaultFont(QFont("Arial", 18))  # LARGEST readable
        doc.setHtml(html)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setResolution(300)
        page_width_mm = 80
        page_height_mm = 200
        pagesize = QPageSize(QSizeF(page_width_mm, page_height_mm), QPageSize.Unit.Millimeter)
        printer.setPageSize(pagesize)
        printer.setPageMargins(QMarginsF(1, 1, 1, 1), QPageLayout.Unit.Millimeter)
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Print Preview - Daily Report")
        preview.paintRequested.connect(doc.print)
        if preview.exec():
            dialog = QPrintDialog(printer, self)
            if dialog.exec():
                doc.print(printer)

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
        salary = float(self.salary_edit.text() or 0)
        joining = self.joining_edit.date().toString("yyyy-MM-dd")
        photo = getattr(self, "photo_path", "")
        loan = float(self.loan_edit.text() or 0)
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

        # Transaction Inputs
        tx_form = QFormLayout()
        self.tx_type = QComboBox()
        self.tx_type.addItems(["Salary Payment", "Advance", "Deduction"])
        self.tx_amount = QLineEdit()
        self.tx_notes = QLineEdit()
        self.tx_date = QDateEdit()
        self.tx_date.setCalendarPopup(True)
        self.tx_date.setDate(QDate.currentDate())
        tx_form.addRow("Type:", self.tx_type)
        tx_form.addRow("Amount:", self.tx_amount)
        tx_form.addRow("Date:", self.tx_date)
        tx_form.addRow("Notes:", self.tx_notes)
        tx_btn = QPushButton("Record Transaction")
        tx_btn.clicked.connect(self.record_transaction)
        tx_form.addRow(tx_btn)
        tx_box = QGroupBox("Record Payroll Transaction")
        tx_box.setLayout(tx_form)
        self.layout().addWidget(tx_box)

        # Transactions Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Date", "Type", "Debit", "Credit", "Balance", "Notes"])
        # Set custom column widths
        self.table.setColumnWidth(0, 120)   # Date
        self.table.setColumnWidth(1, 140)   # Type
        self.table.setColumnWidth(2, 120)   # Debit
        self.table.setColumnWidth(3, 120)   # Credit
        self.table.setColumnWidth(4, 120)   # Balance
        self.table.setColumnWidth(5, 220)   # Notes
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # 5 is the index of Notes column
        self.table.verticalHeader().setVisible(False)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.layout().addWidget(self.table)
        self.load_employees()

        self.table.doubleClicked.connect(self.handle_table_double_click)


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
        c.execute("SELECT designation, salary, joining_date, photo_path, loan_balance FROM employees WHERE id=?", (eid,))
        row = c.fetchone()
        if not row:
            return
        desig, salary, joining, photo, loan = row
        self.emp_info.setText(f"{name}\n{desig}\nSalary: {salary}\nJoined: {joining}")
        self.photo.setPixmap(QPixmap(photo) if photo and os.path.exists(photo) else QPixmap())
        conn.close()
        self.load_transactions(eid)
        self.outstanding_card.set_balance(loan)

    def record_transaction(self):
        name = self.employee_combo.currentText()
        eid = self.emp_map.get(name)
        ttype = self.tx_type.currentText()
        date = self.tx_date.date().toString("yyyy-MM-dd")
        try:
            amt = float(self.tx_amount.text())
        except Exception:
            QMessageBox.warning(self, "Invalid", "Amount is required.")
            return
        notes = self.tx_notes.text()
        debit = credit = 0
        if ttype == "Salary Payment":
            debit = amt
        elif ttype == "Advance":
            debit = amt
        elif ttype == "Deduction":
            credit = amt

        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT balance FROM employee_payroll WHERE employee_id=? ORDER BY date DESC, id DESC LIMIT 1", (eid,))
        prev = c.fetchone()
        prev_bal = prev[0] if prev else 0
        bal = prev_bal + debit - credit
        c.execute(
            "INSERT INTO employee_payroll (employee_id, date, type, amount, debit, credit, balance, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (eid, date, ttype, amt, debit, credit, bal, notes)
        )
        if ttype == "Advance":
            c.execute("UPDATE employees SET loan_balance = loan_balance + ? WHERE id=?", (amt, eid))
        elif ttype == "Deduction":
            c.execute("UPDATE employees SET loan_balance = loan_balance - ? WHERE id=?", (amt, eid))
        conn.commit()
        conn.close()

        if ttype in ("Salary Payment", "Advance"):
            self._record_salary_expense_in_cashflow(emp_name=name, amount=amt, date=date, tx_type=ttype)

        # Refresh cashflow/daily tab
        main_window = self.window()
        if hasattr(main_window, "daily") and hasattr(main_window.daily, "load_data"):
            main_window.daily.load_data()

        self.load_employee(self.employee_combo.currentIndex())
        self.tx_amount.clear()
        self.tx_notes.clear()
        QMessageBox.information(self, "Success", "Transaction recorded.")

    def load_transactions(self, eid):
        self.table.setRowCount(0)
        conn = get_conn()
        c = conn.cursor()
        # Fetch transactions oldest to newest for correct running balance
        c.execute("SELECT id, date, type, debit, credit, notes FROM employee_payroll WHERE employee_id=? ORDER BY date ASC, id ASC", (eid,))
        rows = c.fetchall()
        conn.close()

        prev_balance = 0
        for i, (payroll_id, date_str, typ, debit, credit, notes) in enumerate(rows):
            debit_str = ""
            credit_str = ""

            if typ == "Advance":
                advance = float(debit) if debit else 0
                deduction = 0
                debit_str = str(advance)
            elif typ == "Deduction":
                advance = 0
                deduction = float(credit) if credit else 0
                credit_str = str(deduction)
            elif typ == "Salary Payment":
                advance = 0
                deduction = 0
                # For Salary Payment, show value in Debit, leave Credit blank
                debit_str = str(debit) if debit else ""
            else:
                advance = 0
                deduction = 0

            # Only Advance and Deduction affect balance
            balance = prev_balance + advance - deduction

            self.table.insertRow(i)
            # Store payroll_id as Qt.UserRole for reference in editing
            id_item = QTableWidgetItem(str(payroll_id))
            id_item.setData(Qt.ItemDataRole.UserRole, payroll_id)
            self.table.setVerticalHeaderItem(i, id_item)

            self.table.setItem(i, 0, QTableWidgetItem(str(date_str)))
            self.table.setItem(i, 1, QTableWidgetItem(str(typ)))
            self.table.setItem(i, 2, QTableWidgetItem(debit_str))
            self.table.setItem(i, 3, QTableWidgetItem(credit_str))
            self.table.setItem(i, 4, QTableWidgetItem(str(balance)))
            self.table.setItem(i, 5, QTableWidgetItem(str(notes)))

            # Only update prev_balance for Advance/Deduction
            if typ == "Advance" or typ == "Deduction":
                prev_balance = balance

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

        # Compute status and sort order
        def status_and_sortkey(doc):
            status, color, sortnum = self.compute_status_sort(doc["expiry_date"])
            return (sortnum, doc["description"].lower(), status, color)
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

class VendorDialog(QDialog):
    def __init__(self, parent=None, title="Add Vendor", name="", contact="", opening_balance=0.0):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        layout = QFormLayout(self)
        self.name_input = QLineEdit(name)
        self.name_input.setPlaceholderText("Enter vendor name")
        self.contact_input = QLineEdit(contact)
        self.contact_input.setPlaceholderText("Enter contact (optional)")
        self.opening_input = QLineEdit(str(opening_balance))
        self.opening_input.setPlaceholderText("Opening balance in AED")
        layout.addRow("Vendor Name:", self.name_input)
        layout.addRow("Contact:", self.contact_input)
        layout.addRow("Opening Balance (AED):", self.opening_input)
        button_box = QHBoxLayout()
        self.save_btn = QPushButton(QIcon.fromTheme("dialog-ok"), "Save")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton(QIcon.fromTheme("dialog-cancel"), "Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(self.save_btn)
        button_box.addWidget(self.cancel_btn)
        layout.addRow(button_box)
        self.setLayout(layout)

    def get_values(self):
        name = self.name_input.text().strip()
        contact = self.contact_input.text().strip()
        try:
            opening_balance = float(self.opening_input.text())
        except ValueError:
            opening_balance = 0.0
        return name, contact, opening_balance
    

class TransactionEntryDialog(QDialog):
    def __init__(self, parent, vendor_id, vendor_name, ttype=None, edit_mode=False, trans_id=None, init_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add Transaction" if not edit_mode else "Edit Transaction")
        self.vendor_id = vendor_id
        self.edit_mode = edit_mode
        self.trans_id = trans_id
        self.ttype = ttype if ttype else "purchase"
        self.setMinimumWidth(520)
        self.setMinimumHeight(400)

        main_layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignHCenter)

        vendor_label = QLabel(f"<b>Vendor:</b> <span style='color:#e53935;'>{vendor_name}</span>")
        vendor_label.setTextFormat(Qt.TextFormat.RichText)
        vendor_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        vendor_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(vendor_label)

        self.trans_type = QLabel(self.ttype.capitalize())
        self.trans_type.setStyleSheet("font-size:16px; color:#fb700e; font-weight:600;")
        form.addRow("Transaction Type:", self.trans_type)

        self.trans_entry_date = QDateEdit()
        self.trans_entry_date.setDisplayFormat("dd-MM-yyyy")
        self.trans_entry_date.setCalendarPopup(True)
        self.trans_entry_date.setDate(QDate.currentDate())
        self.trans_entry_date.setMinimumWidth(140)

        self.trans_invoice_input = QLineEdit()
        self.trans_invoice_input.setPlaceholderText("Invoice number (optional)")

        self.trans_due_date = QDateEdit()
        self.trans_due_date.setDisplayFormat("dd-MM-yyyy")
        self.trans_due_date.setCalendarPopup(True)
        self.trans_due_date.setDate(QDate.currentDate())
        self.trans_due_date.setMinimumWidth(140)

        self.trans_note_input = QLineEdit()
        self.trans_note_input.setPlaceholderText("Enter note or remarks (optional)")

        self.trans_amount_input = QLineEdit()
        self.trans_amount_input.setPlaceholderText("Enter amount in AED")
        amount_font = QFont()
        amount_font.setPointSize(20)
        amount_font.setBold(True)
        self.trans_amount_input.setFont(amount_font)
        self.trans_amount_input.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Payment Mode (only for payment)
        self.trans_payment_mode = QComboBox()
        self.trans_payment_mode.addItems(['Cash', 'Credit Card', 'Bank Transfer', 'Other'])
        self.trans_payment_mode.setEditable(True)
        self.trans_payment_mode.setMinimumWidth(240)

        # Cheque Fields (only if purchase and paid by cheque)
        self.paid_by_cheque_checkbox = QCheckBox("Payment done by Cheque")
        self.paid_by_cheque_checkbox.setStyleSheet("color:#F1F3F4; font-size:14px;")
        self.cheque_bank_name = QLineEdit()
        self.cheque_bank_name.setPlaceholderText("Bank Name")
        self.cheque_due_date = QDateEdit()
        self.cheque_due_date.setDisplayFormat("dd-MM-yyyy")
        self.cheque_due_date.setCalendarPopup(True)
        self.cheque_due_date.setDate(QDate.currentDate())
        self.cheque_due_date.setMinimumWidth(140)
        self.trans_due_date.dateChanged.connect(self.sync_cheque_due_date)
        self.cheque_due_date.dateChanged.connect(self.sync_due_date_from_cheque)

        # Hide/show fields based on transaction type
        self.ttype = self.ttype.lower()
        if self.ttype == "purchase":
            form.addRow("Date:", self.trans_entry_date)
            form.addRow("Invoice No:", self.trans_invoice_input)
            form.addRow("Due Date:", self.trans_due_date)
            form.addRow("Notes:", self.trans_note_input)
            form.addRow(self.paid_by_cheque_checkbox)
            self.cheque_fields_row = QHBoxLayout()
            self.cheque_fields_row.addWidget(QLabel("Bank Name:"))
            self.cheque_fields_row.addWidget(self.cheque_bank_name)
            self.cheque_fields_row.addWidget(QLabel("Cheque Due Date:"))
            self.cheque_fields_row.addWidget(self.cheque_due_date)
            form.addRow(self.cheque_fields_row)
            self.cheque_bank_name.hide()
            self.cheque_due_date.hide()
            self.cheque_fields_row.itemAt(0).widget().hide()
            self.cheque_fields_row.itemAt(2).widget().hide()
            self.paid_by_cheque_checkbox.stateChanged.connect(self.toggle_cheque_fields)
        elif self.ttype == "payment":
            form.addRow("Date:", self.trans_entry_date)
            form.addRow("Mode of Payment:", self.trans_payment_mode)
            form.addRow("Invoice No:", self.trans_invoice_input)
            form.addRow("Notes:", self.trans_note_input)
        elif self.ttype == "return":
            form.addRow("Date:", self.trans_entry_date)
            form.addRow("Amount (AED):", self.trans_amount_input)
            form.addRow("Notes:", self.trans_note_input)

        if self.ttype in ("purchase", "payment"):
            form.addRow("Amount (AED):", self.trans_amount_input)

        main_layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_ok = QPushButton("Save" if edit_mode else "Add Transaction")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_ok)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        if self.edit_mode and init_data:
            (date_str, ttype, amt, due, note, invoice_no, payment_mode, net_terms, bank_name, cheque_due) = (
                *(init_data + (None, None)),  # add extra fields for backward comp.
            )[:10]
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                self.trans_entry_date.setDate(QDate(dt.year, dt.month, dt.day))
            except Exception:
                self.trans_entry_date.setDate(QDate.currentDate())
            self.trans_invoice_input.setText(invoice_no or "")
            self.trans_note_input.setText(note or "")
            if due:
                try:
                    dt = datetime.strptime(due, "%Y-%m-%d")
                    self.trans_due_date.setDate(QDate(dt.year, dt.month, dt.day))
                except Exception:
                    pass
            self.trans_payment_mode.setCurrentText(payment_mode or "")
            self.trans_amount_input.setText(str(amt))
            if bank_name:
                self.paid_by_cheque_checkbox.setChecked(True)
                self.cheque_bank_name.setText(bank_name)
                self.cheque_bank_name.show()
                self.cheque_fields_row.itemAt(0).widget().show()
                self.cheque_fields_row.itemAt(2).widget().show()
                self.cheque_due_date.show()
                if cheque_due:
                    try:
                        dt = datetime.strptime(cheque_due, "%Y-%m-%d")
                        self.cheque_due_date.setDate(QDate(dt.year, dt.month, dt.day))
                    except Exception:
                        pass
    def toggle_cheque_fields(self, state):
        show = state == Qt.CheckState.Checked.value
        self.cheque_bank_name.setVisible(show)
        self.cheque_due_date.setVisible(show)
        self.cheque_fields_row.itemAt(0).widget().setVisible(show)
        self.cheque_fields_row.itemAt(2).widget().setVisible(show)
        if show:
            self.trans_due_date.setDate(self.cheque_due_date.date())
        else:
            # Let user edit due date freely if cheque is not used
            pass

    def get_values(self):
        ttype = self.ttype
        date_iso = self.trans_entry_date.date().toString("yyyy-MM-dd")
        amt = self.trans_amount_input.text()
        invoice_no = self.trans_invoice_input.text()
        note = self.trans_note_input.text()
        due_iso = self.trans_due_date.date().toString("yyyy-MM-dd") if self.ttype == "purchase" else None
        payment_mode = self.trans_payment_mode.currentText() if self.ttype == "payment" else None
        bank_name = self.cheque_bank_name.text() if (self.ttype == "purchase" and self.paid_by_cheque_checkbox.isChecked()) else None
        cheque_due = self.cheque_due_date.date().toString("yyyy-MM-dd") if (self.ttype == "purchase" and self.paid_by_cheque_checkbox.isChecked()) else None
        return (
            ttype, date_iso, amt, invoice_no, due_iso, note, payment_mode, bank_name, cheque_due
        )

    def update_due_date_by_net_terms(self):
        today = QDate.currentDate()
        if self.net_30.isChecked():
            self.trans_due_date.setDate(today.addDays(30))
        elif self.net_60.isChecked():
            self.trans_due_date.setDate(today.addDays(60))
        elif self.net_90.isChecked():
            self.trans_due_date.setDate(today.addDays(90))

    def update_section_visibility(self):
        ttype = self.trans_type_combo.currentText().lower()
        def grayscale_effect():
            effect = QGraphicsColorizeEffect()
            effect.setColor(QColor("#888888"))
            effect.setStrength(0.75)
            return effect
        if ttype == "purchase":
            self.due_frame.setGraphicsEffect(None)
            self.payment_frame.setGraphicsEffect(grayscale_effect())
            self.enable_widgets_in_frame(self.due_frame, True)
            self.enable_widgets_in_frame(self.payment_frame, False)
        elif ttype == "payment":
            self.due_frame.setGraphicsEffect(grayscale_effect())
            self.payment_frame.setGraphicsEffect(None)
            self.enable_widgets_in_frame(self.due_frame, False)
            self.enable_widgets_in_frame(self.payment_frame, True)
        elif ttype == "return":
            self.due_frame.setGraphicsEffect(grayscale_effect())
            self.payment_frame.setGraphicsEffect(grayscale_effect())
            self.enable_widgets_in_frame(self.due_frame, False)
            self.enable_widgets_in_frame(self.payment_frame, False)
        else:
            self.due_frame.setGraphicsEffect(None)
            self.payment_frame.setGraphicsEffect(None)
            self.enable_widgets_in_frame(self.due_frame, True)
            self.enable_widgets_in_frame(self.payment_frame, True)

    def enable_widgets_in_frame(self, frame, enabled):
        for i in range(frame.layout().count()):
            item = frame.layout().itemAt(i)
            widget = item.widget()
            if isinstance(widget, (QLineEdit, QDateEdit, QComboBox, QCheckBox)):
                widget.setEnabled(enabled)

    def update_due_date_by_net_terms(self):
        today = QDate.currentDate()
        if self.net_30.isChecked():
            self.trans_due_date.setDate(today.addDays(30))
        elif self.net_60.isChecked():
            self.trans_due_date.setDate(today.addDays(60))
        elif self.net_90.isChecked():
            self.trans_due_date.setDate(today.addDays(90))
    
    def sync_due_date_from_cheque(self):
            if self.cheque_due_date.isVisible():
                # Always sync the purchase due date to cheque due date if cheque section is visible
                self.trans_due_date.setDate(self.cheque_due_date.date())

    def sync_cheque_due_date(self):
            if self.cheque_due_date.isVisible():
                # If the user tries to set purchase due date different from cheque due date, force it back
                if self.trans_due_date.date() != self.cheque_due_date.date():
                    self.trans_due_date.setDate(self.cheque_due_date.date())

    def save_transaction(self):
        ttype = self.trans_type_combo.currentText().lower()
        try:
            amount = float(self.trans_amount_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Amount must be a number.")
            return
        if amount < 0.01:
            QMessageBox.warning(self, "Invalid", "Amount must be greater than zero.")
            return

        note = self.trans_note_input.text()
        entry_date_iso = self.trans_entry_date.date().toString("yyyy-MM-dd")
        due_date_iso = self.trans_due_date.date().toString("yyyy-MM-dd")
        net_terms = ""
        if self.net_30.isChecked():
            net_terms = "NET 30"
        elif self.net_60.isChecked():
            net_terms = "NET 60"
        elif self.net_90.isChecked():
            net_terms = "NET 90"
        payment_mode = self.trans_payment_mode.currentText()
        invoice_no = self.trans_invoice_input.text().strip()
        conn = get_conn()
        c = conn.cursor()
        if self.edit_mode and self.trans_id:
            # UPDATE vendor_transactions
            c.execute('''UPDATE vendor_transactions SET date=?, type=?, amount=?, note=?, due_date=?, invoice_no=?, payment_mode=?, net_terms=?
                         WHERE id=?''',
                      (entry_date_iso, ttype, amount, note,
                       due_date_iso if ttype == "purchase" else None,
                       invoice_no,
                       payment_mode if ttype == "payment" else None,
                       net_terms if ttype == "purchase" else None,
                       self.trans_id))
            # --- Update daily_expense for "payment" ---
            if ttype == "payment":
                c.execute("SELECT id FROM expense_categories WHERE name='Vendors'")
                cat = c.fetchone()
                if cat:
                    cat_id = cat[0]
                    c.execute("SELECT name FROM vendors WHERE id=?", (self.vendor_id,))
                    vrow = c.fetchone()
                    vendor_name = vrow[0] if vrow else ""
                    old_descr = f"{vendor_name} Payment ({amount:.2f} AED)"
                    # Try to update an existing expense entry for this transaction (might not exist)
                    c.execute("""
                        UPDATE daily_expense SET date=?, amount=?, description=?
                        WHERE date=? AND amount=? AND category_id=? AND description=?
                    """, (entry_date_iso, amount, old_descr, entry_date_iso, amount, cat_id, old_descr))
        else:
            # INSERT vendor_transactions (your original logic)
            c.execute('''INSERT INTO vendor_transactions
                (vendor_id, date, type, amount, note, due_date, invoice_no, payment_mode, net_terms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (self.vendor_id, entry_date_iso, ttype, amount, note,
                    due_date_iso if ttype == "purchase" else None,
                    invoice_no,
                    payment_mode if ttype == "payment" else None,
                    net_terms if ttype == "purchase" else None)
            )
            if ttype == "payment":
                # Find or create "Vendors" expense category
                c.execute("SELECT id FROM expense_categories WHERE name='Vendors'")
                cat = c.fetchone()
                if cat:
                    cat_id = cat[0]
                else:
                    c.execute("INSERT INTO expense_categories (name) VALUES ('Vendors')")
                    cat_id = c.lastrowid
                c.execute("SELECT name FROM vendors WHERE id=?", (self.vendor_id,))
                vrow = c.fetchone()
                vendor_name = vrow[0] if vrow else ""
                descr = f"{vendor_name} Payment ({amount:.2f} AED)"
                c.execute("""
                    SELECT 1 FROM daily_expense WHERE date=? AND amount=? AND category_id=? AND description=?
                """, (entry_date_iso, amount, cat_id, descr))
                if not c.fetchone():
                    c.execute(
                        '''INSERT INTO daily_expense (date, amount, category_id, description)
                        VALUES (?, ?, ?, ?)''',
                        (entry_date_iso, amount, cat_id, descr)
                    )
        conn.commit()
        conn.close()
        self.accept()

class VendorsTab(QWidget):
    chequeCreated = pyqtSignal()
    def __init__(self, daily_tab=None):
        super().__init__()
        self.ensure_invoice_payment_columns()  # Ensure columns exist before any queries
        self.daily_tab = daily_tab
        self.vendors = []
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)
        

        # ---- DISTINCT TAB STYLING ----
        self.tabs.setStyleSheet("""
            QTabBar {
                background: transparent;
                min-height: 34px;
            }
            QTabBar::tab {
                background: #232627;
                color: #e0e0e0;
                border-radius: 0px;
                padding: 8px 18px;
                margin-right: 8px;
                min-width: 130px;
                font-size: 15px;
                font-weight: 500;
                border: none;
            }
            QTabBar::tab:selected {
                background: #35393A;
                color: #fb700e;
                font-weight: bold;
            }
            QTabBar::tab:!selected:hover {
                color: #fb700e;
                background: #292b2e;
            }
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
        """)

        # --- Transactions Tab ---
        self.trans_tab = QWidget()
        self.trans_layout = QVBoxLayout()
        self.trans_tab.setLayout(self.trans_layout)

        # --- FILTER + CURRENT BALANCE row ---
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(10)

        filter_row.addWidget(QLabel("Select Vendor:"))

        self.trans_vendor_combo = QComboBox()
        self.trans_vendor_combo.setMinimumWidth(220)
        self.trans_vendor_combo.setMaximumWidth(320)
        self.trans_vendor_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.trans_vendor_combo.currentIndexChanged.connect(self.refresh_transactions_table)
        filter_row.addWidget(self.trans_vendor_combo)

        self.trans_vendor_search = QLineEdit()
        self.trans_vendor_search.setPlaceholderText("Search vendor...")
        self.trans_vendor_search.setFixedWidth(220)
        self.trans_vendor_search.textChanged.connect(self.filter_trans_vendor_combo)
        filter_row.addWidget(self.trans_vendor_search)

        filter_row.addStretch(1)

        self.current_balance_label = QLabel("Current Balance: 0.00 AED")
        self.current_balance_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.current_balance_label.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#fdc59e; margin:8px 0px 0 0;"
        )
        filter_row.addWidget(self.current_balance_label)

        self.trans_layout.addLayout(filter_row)

        # --- BUTTONS row: Export PDF & Add Transaction ---
        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 10, 0, 0)
        buttons_row.setSpacing(12)

        self.show_add_entry_btn = QPushButton("Add Transaction")
        self.show_add_entry_btn.setFixedWidth(160)
        self.show_add_entry_btn.clicked.connect(self.show_transaction_dialog)
        self.show_add_entry_btn.setStyleSheet(
            "font-size:15px; font-weight:bold; background:#fb700e; color:white; border-radius:5px; padding:8px 18px;"
        )
        buttons_row.addWidget(self.show_add_entry_btn)
        self.add_transaction_shortcut = QShortcut(QKeySequence("F1"), self)
        self.add_transaction_shortcut.activated.connect(self.show_transaction_dialog)

        self.export_pdf_btn = QPushButton("Export to PDF")
        self.export_pdf_btn.setFixedWidth(160)
        self.export_pdf_btn.setStyleSheet(
            "background:#26292A; color:white; font-size: 16px; font-weight: bold; border-radius: 3px;"
        )
        self.export_pdf_btn.clicked.connect(self.export_transactions_pdf)
        buttons_row.addWidget(self.export_pdf_btn)

        buttons_row.addStretch(1)
        self.trans_layout.addLayout(buttons_row)

        # Vendor Transactions Table
        self.trans_layout.addSpacing(6)
        self.trans_layout.addWidget(QLabel("Vendor Transactions:"))
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(8)
        self.trans_table.setHorizontalHeaderLabels([
            'Date', 'Invoice No.', 'Type', 'Debit (AED)', 'Credit (AED)', 'Due Date',
            'Payment Mode', 'Note'
        ])
        self.trans_table.setColumnWidth(0, 110)     # Date
        self.trans_table.setColumnWidth(1, 90)      # Invoice No.
        self.trans_table.setColumnWidth(2, 100)     # Type
        self.trans_table.setColumnWidth(3, 100)     # Debit (AED)
        self.trans_table.setColumnWidth(4, 100)     # Credit (AED)
        self.trans_table.setColumnWidth(5, 115)     # Due Date
        self.trans_table.setColumnWidth(6, 130)     # Payment Mode
        self.trans_table.setColumnWidth(7, 200)     # Note
        header = self.trans_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Only let Note stretch
        self.trans_table.setAlternatingRowColors(True)
        self.trans_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.trans_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.trans_table.customContextMenuRequested.connect(self.show_transaction_context_menu)
        self.trans_table.doubleClicked.connect(self.handle_transaction_double_click)
        self.trans_layout.addWidget(self.trans_table)
        self.tabs.addTab(self.trans_tab, "Transactions")

        # --------- OVERVIEW TAB -------------
        self.overview_tab = QWidget()
        self.overview_layout = QVBoxLayout(self.overview_tab)
        # Filter row
        overview_filter_row = QHBoxLayout()
        overview_filter_row.setContentsMargins(0, 0, 0, 0)
        overview_filter_row.setSpacing(10)
        overview_filter_row.addWidget(QLabel("Vendor:"))
        self.overview_vendor_search = QLineEdit()
        self.overview_vendor_search.setPlaceholderText("Search vendor...")
        overview_filter_row.addWidget(self.overview_vendor_search)
        overview_filter_row.addWidget(QLabel("From:"))
        self.overview_date_from = QDateEdit()
        self.overview_date_from.setDisplayFormat("dd-MM-yyyy")
        self.overview_date_from.setCalendarPopup(True)
        today = QDate.currentDate()
        first_of_month = QDate(today.year(), today.month(), 1)
        self.overview_date_from.setDate(first_of_month)
        overview_filter_row.addWidget(self.overview_date_from)
        overview_filter_row.addWidget(QLabel("To:"))
        self.overview_date_to = QDateEdit()
        self.overview_date_to.setDisplayFormat("dd-MM-yyyy")
        self.overview_date_to.setCalendarPopup(True)
        self.overview_date_to.setDate(today)
        overview_filter_row.addWidget(self.overview_date_to)
        self.overview_cheque_only = QCheckBox("Cheque Only")
        overview_filter_row.addWidget(self.overview_cheque_only)
        overview_filter_row.addStretch()
        self.overview_layout.addLayout(overview_filter_row)

        self.overview_table = QTableWidget()
        self.overview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.overview_table.setColumnCount(9)
        self.overview_table.setHorizontalHeaderLabels([
            'Date', 'Invoice No.', 'Vendor', 'Type', 'Debit (AED)', 'Credit (AED)', 'Due Date', 'Payment Mode', 'Notes'
        ])
        self.overview_table.setShowGrid(True)
        self.overview_table.setGridStyle(Qt.PenStyle.SolidLine)
        self.overview_table.setAlternatingRowColors(False)
        self.overview_table.verticalHeader().setVisible(True)
        overview_header = self.overview_table.horizontalHeader()
        overview_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.overview_layout.addWidget(self.overview_table)

        overview_totals_row = QHBoxLayout()
        overview_totals_row.setContentsMargins(0, 0, 0, 0)
        overview_totals_row.setSpacing(24)
        self.lbl_total_purchases = QLabel("Total Purchases: 0.00 AED")
        self.lbl_total_purchases.setStyleSheet("font-weight:bold;color:#43a047;")
        self.lbl_total_payments = QLabel("Total Payments: 0.00 AED")
        self.lbl_total_payments.setStyleSheet("font-weight:bold;color:#e53935;")
        self.lbl_current_balance = QLabel("Current Balance: 0.00 AED")
        self.lbl_current_balance.setStyleSheet("font-weight:bold;color:#fbc02d;")
        overview_totals_row.addWidget(self.lbl_total_purchases)
        overview_totals_row.addWidget(self.lbl_total_payments)
        overview_totals_row.addWidget(self.lbl_current_balance)
        overview_totals_row.addStretch()
        self.overview_layout.addLayout(overview_totals_row)

        self.tabs.addTab(self.overview_tab, "Overview")

        # Connect filter events for Overview tab
        self.overview_vendor_search.textChanged.connect(self.refresh_overview_table)
        self.overview_date_from.dateChanged.connect(self.refresh_overview_table)
        self.overview_date_to.dateChanged.connect(self.refresh_overview_table)
        self.overview_cheque_only.stateChanged.connect(self.refresh_overview_table)

        # --- Manage Vendors Tab (unchanged) ---
        self.vendor_manage_tab = QWidget()
        self.vendor_manage_layout = QVBoxLayout()
        self.vendor_manage_tab.setLayout(self.vendor_manage_layout)
        filter_row2 = QHBoxLayout()
        filter_row2.addWidget(QLabel("Search Vendor:"))
        self.vendor_search_input = QLineEdit()
        self.vendor_search_input.setPlaceholderText("Type at least 2 letters of vendor name...")
        self.vendor_search_input.textChanged.connect(self.filter_vendor_table)
        filter_row2.addWidget(self.vendor_search_input)
        filter_row2.addStretch()
        self.vendor_manage_layout.addLayout(filter_row2)

        # Total Account Payable label
        self.total_payable_label = QLabel("Total Account Payable: 0.00 AED")
        self.total_payable_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_payable_label.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#43a047; margin:0 0px 0px 0;"
        )
        self.vendor_manage_layout.addWidget(self.total_payable_label)

        self.vendor_table = QTableWidget()
        self.vendor_table.setColumnCount(4)
        self.vendor_table.setHorizontalHeaderLabels([
            "Vendor Name", "Contact", "Opening Balance (AED)", "Current Balance (AED)"
        ])
        self.vendor_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.vendor_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.vendor_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.vendor_table.setAlternatingRowColors(True)
        self.vendor_manage_layout.addWidget(QLabel("Vendors:"))
        self.vendor_manage_layout.addWidget(self.vendor_table)
        button_row = QHBoxLayout()
        self.add_vendor_btn = QPushButton("Add Vendor")
        self.add_vendor_btn.clicked.connect(self.show_add_vendor_dialog)
        self.edit_vendor_btn = QPushButton("Edit Vendor")
        self.edit_vendor_btn.clicked.connect(self.show_edit_vendor_dialog)
        self.delete_vendor_btn = QPushButton("Delete Vendor")
        self.delete_vendor_btn.clicked.connect(self.delete_vendor)
        button_row.addWidget(self.add_vendor_btn)
        button_row.addWidget(self.edit_vendor_btn)
        button_row.addWidget(self.delete_vendor_btn)
        self.vendor_manage_layout.addLayout(button_row)
        style = self.style()
        transactions_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView)
        overview_icon = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        manage_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self.tabs.addTab(self.trans_tab, transactions_icon, "Transactions")
        self.tabs.addTab(self.overview_tab, overview_icon, "Overview")
        self.tabs.addTab(self.vendor_manage_tab, manage_icon, "Manage Vendors")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # --- Now, after all widgets are created, call refresh_vendor_combo ---
        self.refresh_vendor_combo()


    def _on_tab_changed(self, index):
        if self.tabs.tabText(index) == "Overview":
            self.refresh_overview_table()

        # Data Loading
        self.refresh_vendor_combo()
        self.refresh_vendor_table()
        self.refresh_transactions_table()

    def refresh_overview_vendor_combo(self):
        self.overview_vendor_combo.blockSignals(True)
        self.overview_vendor_combo.clear()
        self.overview_vendor_combo.addItem("All", None)
        for vid, name, *_ in self.vendors:
            self.overview_vendor_combo.addItem(name, vid)
        self.overview_vendor_combo.blockSignals(False)

    def refresh_overview_table(self):
        vendor_search = self.overview_vendor_search.text().strip().lower()
        date_from = self.overview_date_from.date().toString("yyyy-MM-dd")
        date_to = self.overview_date_to.date().toString("yyyy-MM-dd")
        cheque_only = self.overview_cheque_only.isChecked()
        conn = get_conn()
        c = conn.cursor()
        query = """
            SELECT vt.date, vt.invoice_no, v.name, vt.type, vt.amount, vt.due_date, vt.payment_mode, vt.note, vt.vendor_id
            FROM vendor_transactions vt
            LEFT JOIN vendors v ON vt.vendor_id = v.id
            WHERE vt.date BETWEEN ? AND ?
        """
        params = [date_from, date_to]
        if vendor_search:
            query += " AND lower(v.name) LIKE ?"
            params.append(f"%{vendor_search}%")
        if cheque_only:
            query += " AND vt.payment_mode = 'Cheque'"
        query += " ORDER BY vt.date DESC, vt.id DESC"
        c.execute(query, params)
        rows = c.fetchall()
        self.overview_table.setRowCount(len(rows))
        total_purchase = 0.0
        total_payment = 0.0
        for i, (date_str, invoice_no, vendor_name, ttype, amt, due, payment_mode, note, vendor_id) in enumerate(rows):
            ttype_display = ttype.capitalize() if ttype else ""
            debit = credit = ""
            if ttype == "purchase":
                debit = f"{amt:.2f}"
                total_purchase += amt
            elif ttype in ("payment", "return"):
                credit = f"{amt:.2f}"
                total_payment += amt
            row_values = [
                to_ddmmyyyy(date_str),
                invoice_no or "",
                vendor_name or "",
                ttype_display,
                debit,
                credit,
                to_ddmmyyyy(due) if due else "",
                payment_mode or "",
                note or ""
            ]
            for col, value in enumerate(row_values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 8:
                    item.setForeground(QColor("#aaa"))
                self.overview_table.setItem(i, col, item)
            self.overview_table.setRowHeight(i, 30)

        # --- Total Purchases & Payments
        self.lbl_total_purchases.setText(f"Total Purchases: {total_purchase:.2f} AED")
        self.lbl_total_payments.setText(f"Total Payments: {total_payment:.2f} AED")

        # --- Current Balance: TOTAL ACCOUNT PAYABLE (including opening balance) ---
        # Show sum of positive balances (payable) of all vendors that match the filter
        c.execute("SELECT id, name, opening_balance FROM vendors")
        vendor_rows = c.fetchall()
        total_account_payable = 0.0
        for vid, vname, opening_balance in vendor_rows:
            # Filter by search if any
            if vendor_search and vendor_search not in vname.lower():
                continue
            c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='purchase'", (vid,))
            purchases = c.fetchone()[0] or 0
            c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='payment'", (vid,))
            payments = c.fetchone()[0] or 0
            c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='return'", (vid,))
            returns = c.fetchone()[0] or 0
            current_balance = opening_balance + purchases - payments - returns
            if current_balance > 0:
                total_account_payable += current_balance
        conn.close()
        self.lbl_current_balance.setText(f"Current Balance: {total_account_payable:.2f} AED")

    def ensure_invoice_payment_columns(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("PRAGMA table_info(vendor_transactions)")
        cols = [row[1] for row in c.fetchall()]
        if "invoice_no" not in cols:
            c.execute("ALTER TABLE vendor_transactions ADD COLUMN invoice_no TEXT")
        if "payment_mode" not in cols:
            c.execute("ALTER TABLE vendor_transactions ADD COLUMN payment_mode TEXT")
        if "net_terms" not in cols:
            c.execute("ALTER TABLE vendor_transactions ADD COLUMN net_terms TEXT")
        conn.commit()
        conn.close()

    def filter_trans_vendor_combo(self):
        self.refresh_vendor_combo()

    def refresh_vendor_combo(self):
        filter_text = self.trans_vendor_search.text().strip().lower()
        self.trans_vendor_combo.blockSignals(True)
        self.trans_vendor_combo.clear()
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name FROM vendors ORDER BY name COLLATE NOCASE ASC")
        vendor_combo_data = c.fetchall()
        items = []
        for vid, name in vendor_combo_data:
            if not filter_text or filter_text in name.lower():
                items.append((vid, name))
        for vid, name in items:
            self.trans_vendor_combo.addItem(name, vid)
        conn.close()
        self.trans_vendor_combo.blockSignals(False)
        # Only call refresh_transactions_table if there is at least one vendor
        if self.trans_vendor_combo.count() > 0:
            self.refresh_transactions_table()
        else:
            self.trans_table.setRowCount(0)
            self.current_balance_label.setText("Current Balance: 0.00 AED")
            self.update_total_payable_label()

    def refresh_vendor_table(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name, contact, opening_balance FROM vendors ORDER BY name COLLATE NOCASE ASC")
        self.vendors = c.fetchall()
        conn.close()
        self.filter_vendor_table()
        self.update_total_payable_label()

    def filter_vendor_table(self):
        search = self.vendor_search_input.text().strip().lower()
        self.filtered_vendors = []
        for vendor in self.vendors:
            vid, name, contact, opening_balance = vendor
            if (len(search) < 2) or (search in name.lower()):
                self.filtered_vendors.append(vendor)
        self.vendor_table.setRowCount(len(self.filtered_vendors))
        for row, (vid, name, contact, opening_balance) in enumerate(self.filtered_vendors):
            current_balance = self.get_current_balance(vid, opening_balance)
            item_name = QTableWidgetItem(name)
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.vendor_table.setItem(row, 0, item_name)
            item_contact = QTableWidgetItem(contact)
            item_contact.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.vendor_table.setItem(row, 1, item_contact)
            item_opening = QTableWidgetItem(f"{opening_balance:.2f}")
            item_opening.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.vendor_table.setItem(row, 2, item_opening)
            item_current = QTableWidgetItem(f"{current_balance:.2f}")
            item_current.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.vendor_table.setItem(row, 3, item_current)
        self.update_total_payable_label()

    def update_total_payable_label(self):
        # Sum current balance of ALL vendors, not just filtered
        total_payable = 0.0
        for vid, name, contact, opening_balance in self.vendors:
            current_balance = self.get_current_balance(vid, opening_balance)
            if current_balance > 0:
                total_payable += current_balance
        self.total_payable_label.setText(f"Total Account Payable: {total_payable:.2f} AED")

    def get_current_balance(self, vendor_id, opening_balance):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='purchase'", (vendor_id,))
        purchases = c.fetchone()[0] or 0
        c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='payment'", (vendor_id,))
        payments = c.fetchone()[0] or 0
        c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='return'", (vendor_id,))
        returns = c.fetchone()[0] or 0
        conn.close()
        return opening_balance + purchases - payments - returns

    def refresh_transactions_table(self):
        idx = self.trans_vendor_combo.currentIndex()
        if idx == -1 or self.trans_vendor_combo.count() == 0:
            self.trans_table.setRowCount(0)
            self.current_balance_label.setText("Current Balance: 0.00 AED")
            self.update_total_payable_label()
            return
        vendor_id = self.trans_vendor_combo.itemData(idx)
        if vendor_id is None:
            self.trans_table.setRowCount(0)
            self.current_balance_label.setText("Current Balance: 0.00 AED")
            self.update_total_payable_label()
            return

        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT opening_balance FROM vendors WHERE id=?", (vendor_id,))
        opening_balance_row = c.fetchone()
        opening_balance = opening_balance_row[0] if opening_balance_row else 0.0
        c.execute('''
            SELECT date, invoice_no, type, amount, due_date, payment_mode, note
            FROM vendor_transactions
            WHERE vendor_id=?
            ORDER BY date ASC, id ASC
        ''', (vendor_id,))
        rows = c.fetchall()
        conn.close()
        self.trans_table.setRowCount(len(rows))
        balance = opening_balance
        for i, (date_str, invoice_no, ttype, amt, due, payment_mode, note) in enumerate(rows):
            ttype_display = ttype.capitalize() if ttype else ""
            debit = credit = ""
            if ttype == "purchase":
                debit = f"{amt:.2f}"
                balance += amt
            elif ttype in ("payment", "return"):
                credit = f"{amt:.2f}"
                balance -= amt

            purchase_date = date_str
            due_date = due
            # If purchase and due date are the same, hide due date in table
            due_date_display = ""
            if due and purchase_date != due:
                due_date_display = to_ddmmyyyy(due)

            row_values = [
                to_ddmmyyyy(date_str),            # 0 Date
                invoice_no or "",                 # 1 Invoice No.
                ttype_display,                    # 2 Type
                debit,                            # 3 Debit (AED)
                credit,                           # 4 Credit (AED)
                due_date_display,
                payment_mode or '',               # 6 Payment Mode
                note or ''                        # 7 Note
            ]
            for col, value in enumerate(row_values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Dim the Notes column (index 7)
                if col == 7:
                    item.setForeground(QColor("#aaa"))  # Dimmed/gray color for notes
                self.trans_table.setItem(i, col, item)

            self.trans_table.setRowHeight(i, 30)
        self.current_balance_label.setText(f"Current Balance: {balance:.2f} AED")
        self.update_total_payable_label()



    def show_transaction_dialog(self):
        idx = self.trans_vendor_combo.currentIndex()
        if idx == -1:
            QMessageBox.warning(self, "No vendor", "Please select a vendor.")
            return
        vendor_id = self.trans_vendor_combo.itemData(idx)
        vendor_name = self.trans_vendor_combo.currentText()

        # Step 1: Transaction type popup
        type_dialog = TransactionTypeDialog(self)
        if not type_dialog.exec():
            return
        ttype = type_dialog.selected_type
        if not ttype:
            return

        # Step 2: Show the context-aware dialog
        dlg = TransactionEntryDialog(self, vendor_id, vendor_name, ttype=ttype)
        if dlg.exec():
            ttype, date_iso, amt, invoice_no, due_iso, note, payment_mode, bank_name, cheque_due = dlg.get_values()
            try:
                amount = float(amt.strip())
            except Exception:
                amount = 0.0
            if amount <= 0:
                QMessageBox.warning(self, "Invalid", "Amount must be greater than zero.")
                return
            conn = get_conn()
            c = conn.cursor()
            if ttype == "purchase":
                c.execute('''INSERT INTO vendor_transactions
                    (vendor_id, date, type, amount, note, due_date, invoice_no)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (vendor_id, date_iso, ttype, amount, note, due_iso, invoice_no)
                )
                vendor_transaction_id = c.lastrowid  # <- get the new purchase's ID
                if bank_name:
                    # Prevent duplicate cheque for this purchase
                    c.execute('''SELECT 1 FROM cheques WHERE vendor_transaction_id=?''', (vendor_transaction_id,))
                    if not c.fetchone():
                        c.execute('''INSERT INTO cheques (cheque_date, company_name, bank_name, due_date, amount, is_paid, vendor_transaction_id)
                                    VALUES (?, ?, ?, ?, ?, 0, ?)''',
                                (date_iso, vendor_name, bank_name, cheque_due, amount, vendor_transaction_id))
                    self.chequeCreated.emit()   # <-- ensure Cheque tab refreshes
                    
            elif ttype == "payment":
                c.execute('''INSERT INTO vendor_transactions
                    (vendor_id, date, type, amount, note, invoice_no, payment_mode)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (vendor_id, date_iso, ttype, amount, note, invoice_no, payment_mode)
                )
                # --------- DAILY EXPENSE LOGIC (always record payment as expense) ----------
                # Compose notes: "Paid via (Mode of Payment)"
                mode_label = payment_mode.strip() if payment_mode else "Other"
                expense_note = f"Paid via {mode_label}"
                # Get or create Vendors category
                c.execute("SELECT id FROM expense_categories WHERE name='Vendors'")
                cat = c.fetchone()
                if cat:
                    cat_id = cat[0]
                else:
                    c.execute("INSERT INTO expense_categories (name) VALUES ('Vendors')")
                    cat_id = c.lastrowid
                # Avoid duplicates: check if similar expense already exists
                c.execute('''SELECT id FROM daily_expense
                            WHERE date=? AND amount=? AND category_id=? AND description=? AND notes=?''',
                        (date_iso, amount, cat_id, vendor_name, expense_note))
                if not c.fetchone():
                    c.execute(
                        '''INSERT INTO daily_expense (date, amount, category_id, description, notes)
                        VALUES (?, ?, ?, ?, ?)''',
                        (date_iso, amount, cat_id, vendor_name, expense_note)
                    )
            elif ttype == "return":
                c.execute('''INSERT INTO vendor_transactions
                    (vendor_id, date, type, amount, note)
                    VALUES (?, ?, ?, ?, ?)''',
                    (vendor_id, date_iso, ttype, amount, note)
                )
            conn.commit()
            conn.close()
            self.refresh_transactions_table()

            # Refresh the Daily Tab and Dashboard reliably
            if self.daily_tab is not None:
                self.daily_tab.load_data()
                if hasattr(self.daily_tab, "dashboard_tab") and self.daily_tab.dashboard_tab is not None:
                    self.daily_tab.dashboard_tab.refresh()

    def add_transaction_from_dialog(self, dlg, vendor_id):
        ttype = dlg.trans_type_combo.currentText().lower()
        try:
            amount = float(dlg.trans_amount_input.text().strip())
        except Exception:
            amount = 0.0
        note = dlg.trans_note_input.text()
        due_date_iso = dlg.trans_due_date.date().toString("yyyy-MM-dd")
        net_terms = ""
        if dlg.net_30.isChecked():
            net_terms = "NET 30"
        elif dlg.net_60.isChecked():
            net_terms = "NET 60"
        elif dlg.net_90.isChecked():
            net_terms = "NET 90"
        payment_mode = dlg.trans_payment_mode.currentText()
        invoice_no = dlg.trans_invoice_input.text().strip()
        entry_date_iso = dlg.trans_entry_date.date().toString("yyyy-MM-dd")
        conn = get_conn()
        c = conn.cursor()
        c.execute('''INSERT INTO vendor_transactions
            (vendor_id, date, type, amount, note, due_date, invoice_no, payment_mode, net_terms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (vendor_id, entry_date_iso, ttype, amount, note,
                due_date_iso if ttype == "purchase" else None,
                invoice_no,
                payment_mode if ttype == "payment" else None,
                net_terms if ttype == "purchase" else None)
        )
        vendor_trans_id = c.lastrowid
        if ttype == "payment":
            c.execute("SELECT id FROM expense_categories WHERE name='Vendors'")
            cat_row = c.fetchone()
            if cat_row:
                cat_id = cat_row[0]
                c.execute("SELECT name FROM vendors WHERE id=?", (vendor_id,))
                vrow = c.fetchone()
                vendor_name = vrow[0] if vrow else ""
                descr = vendor_name
                c.execute('''
                    INSERT INTO daily_expense (date, amount, category_id, description, vendor_transaction_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (entry_date_iso, amount, cat_id, descr, vendor_trans_id))
        conn.commit()
        conn.close()
    
    def export_transactions_pdf(self):
        idx = self.trans_vendor_combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "No Vendor Selected", "Please select a vendor to export transactions.")
            return
        vendor_id = self.trans_vendor_combo.itemData(idx)
        vendor_name = self.trans_vendor_combo.currentText()

        conn = get_conn()
        c = conn.cursor()
        # Get opening balance
        c.execute("SELECT opening_balance FROM vendors WHERE id=?", (vendor_id,))
        ob_row = c.fetchone()
        opening_balance = ob_row[0] if ob_row else 0.0

        # Get all transactions for this vendor
        c.execute('''
            SELECT date, type, amount, due_date, note, invoice_no, payment_mode, net_terms
            FROM vendor_transactions
            WHERE vendor_id=?
            ORDER BY date ASC, id ASC
        ''', (vendor_id,))
        rows = c.fetchall()
        conn.close()

        # Calculate current balance
        balance = opening_balance
        for date_str, ttype, amt, *_ in rows:
            if ttype == "purchase":
                balance += amt
            elif ttype in ("payment", "return"):
                balance -= amt

        # Build HTML for PDF
        html = f"""
        <div style="font-family: Arial, sans-serif;">
        <h2 style="text-align:center; color:#fb700e;">Vendor Transactions Report</h2>
        <h3 style="margin-bottom:10px;">Vendor: <span style="color:#e53935">{vendor_name}</span></h3>
        <p style="font-size:16px;">
            <b>Opening Balance:</b> {opening_balance:.2f} AED<br>
            <b>Current Balance:</b> {balance:.2f} AED
        </p>
        <table border="1" cellspacing="0" cellpadding="8" width="100%" style="font-size:15px; border-collapse:collapse; margin-top:15px;">
            <tr style="background:#232627; color:#fff;">
                <th>Date</th>
                <th>Type</th>
                <th>Debit (AED)</th>
                <th>Credit (AED)</th>
                <th>Due Date</th>
                <th>NET Terms</th>
                <th>Payment Mode</th>
                <th>Invoice No.</th>
                <th>Note</th>
            </tr>
        """
        for date_str, ttype, amt, due, note, invoice_no, payment_mode, net_terms in rows:
            debit = f"{amt:.2f}" if ttype == "purchase" else ""
            credit = f"{amt:.2f}" if ttype in ("payment", "return") else ""
            html += f"""
            <tr>
                <td>{to_ddmmyyyy(date_str)}</td>
                <td>{ttype.capitalize()}</td>
                <td>{debit}</td>
                <td>{credit}</td>
                <td>{to_ddmmyyyy(due) if due else ''}</td>
                <td>{net_terms or ''}</td>
                <td>{payment_mode or ''}</td>
                <td>{invoice_no or ''}</td>
                <td>{note or ''}</td>
            </tr>
            """
        html += "</table></div>"

        # Create document and show print preview dialog
        doc = QTextDocument()
        doc.setHtml(html)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Print Preview - Vendor Transactions PDF")
        preview.paintRequested.connect(doc.print)
        preview.exec()

        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self,
            "Save PDF",
            f"Vendor_{vendor_name.replace(' ', '_')}_Transactions.pdf",
            "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(file_path)
        doc.print(printer)
        QMessageBox.information(self, "Export Complete", f"PDF exported to:\n{file_path}")

    def show_transaction_context_menu(self, pos: QPoint):
        index = self.trans_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        idx = self.trans_vendor_combo.currentIndex()
        if idx == -1:
            return
        vendor_id = self.trans_vendor_combo.itemData(idx)
        trans_id = self.get_transaction_id_from_row(row, vendor_id)
        if trans_id is None:
            return
        menu = QMenu(self)
        edit_action = menu.addAction("Edit Transaction")
        delete_action = menu.addAction("Delete Transaction")
        action = menu.exec(self.trans_table.viewport().mapToGlobal(pos))
        if action == edit_action:
            self.edit_transaction(row, trans_id, vendor_id)
        elif action == delete_action:
            self.delete_transaction(trans_id)

    def handle_transaction_double_click(self, index):
        row = index.row()
        idx = self.trans_vendor_combo.currentIndex()
        if idx == -1:
            return
        vendor_id = self.trans_vendor_combo.itemData(idx)
        trans_id = self.get_transaction_id_from_row(row, vendor_id)
        if trans_id is not None:
            self.edit_transaction(row, trans_id, vendor_id)

    def get_transaction_id_from_row(self, row, vendor_id):
        date_str = self.trans_table.item(row, 0).text()         # Date
        invoice_no = self.trans_table.item(row, 1).text()       # Invoice No.
        ttype = self.trans_table.item(row, 2).text().lower()    # Type
        debit = self.trans_table.item(row, 3).text()            # Debit (AED)
        credit = self.trans_table.item(row, 4).text()           # Credit (AED)
        # No NET Terms column anymore
        amount = 0.0
        if debit:
            try:
                amount = float(debit)
            except Exception:
                amount = 0.0
        elif credit:
            try:
                amount = float(credit)
            except Exception:
                amount = 0.0
        try:
            dt = datetime.strptime(date_str, "%d-%m-%Y")
            date_iso = dt.strftime("%Y-%m-%d")
        except Exception:
            date_iso = date_str
        conn = get_conn()
        c = conn.cursor()
        c.execute('''SELECT id FROM vendor_transactions
                    WHERE vendor_id=? AND date=? AND type=? AND amount=? AND (invoice_no IS ? OR invoice_no=?)''',
                (vendor_id, date_iso, ttype, amount, invoice_no, invoice_no))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

    def edit_transaction(self, row, trans_id, vendor_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute('''SELECT date, type, amount, due_date, note, invoice_no, payment_mode, net_terms
                    FROM vendor_transactions WHERE id=?''', (trans_id,))
        tr = c.fetchone()
        if not tr:
            conn.close()
            return
        vendor_name = self.trans_vendor_combo.currentText()
        # --- Fetch cheque info ---
        c.execute("SELECT bank_name, due_date FROM cheques WHERE vendor_transaction_id=?", (trans_id,))
        cheque_info = c.fetchone()
        if cheque_info:
            bank_name, cheque_due = cheque_info
        else:
            bank_name, cheque_due = None, None
        tr_with_cheque = tr + (bank_name, cheque_due)
        dlg = TransactionEntryDialog(self, vendor_id, vendor_name, ttype=tr[1], edit_mode=True, trans_id=trans_id, init_data=tr_with_cheque)
        if dlg.exec():
            ttype, date_iso, amt, invoice_no, due_iso, note, payment_mode, bank_name, cheque_due = dlg.get_values()
            try:
                amount = float(amt.strip())
            except Exception:
                amount = 0.0
            if amount <= 0:
                QMessageBox.warning(self, "Invalid", "Amount must be greater than zero.")
                return
            # --------- PATCH STARTS HERE ---------
            old_date, old_type, old_amount, *_ = tr
            old_payment_mode = tr[6] if len(tr) > 6 else None
            # Update vendor_transactions as before
            if ttype == "purchase":
                c.execute('''UPDATE vendor_transactions
                    SET date=?, type=?, amount=?, note=?, due_date=?, invoice_no=?
                    WHERE id=?''',
                    (date_iso, ttype, amount, note, due_iso, invoice_no, trans_id)
                )
                # Cheque logic unchanged...
            elif ttype == "payment":
                c.execute('''UPDATE vendor_transactions
                    SET date=?, type=?, amount=?, note=?, invoice_no=?, payment_mode=?
                    WHERE id=?''',
                    (date_iso, ttype, amount, note, invoice_no, payment_mode, trans_id)
                )
                # --- PATCH: Update daily_expense entry ---
                c.execute("SELECT id FROM expense_categories WHERE name='Vendors'")
                cat_row = c.fetchone()
                if cat_row:
                    cat_id = cat_row[0]
                    # Find the old daily_expense record for this vendor transaction
                    c.execute(
                        '''SELECT id FROM daily_expense
                           WHERE category_id=? AND description=? AND notes=? AND date=? AND amount=?''',
                        (cat_id, vendor_name, f"Paid via {old_payment_mode}" if old_payment_mode else "", old_date, old_amount)
                    )
                    exp_row = c.fetchone()
                    if exp_row:
                        exp_id = exp_row[0]
                        new_notes = f"Paid via {payment_mode}" if payment_mode else ""
                        c.execute(
                            '''UPDATE daily_expense
                               SET date=?, amount=?, notes=?
                               WHERE id=?''',
                            (date_iso, amount, new_notes, exp_id)
                        )
            elif ttype == "return":
                c.execute('''UPDATE vendor_transactions
                    SET date=?, type=?, amount=?, note=?
                    WHERE id=?''',
                    (date_iso, ttype, amount, note, trans_id)
                )
            conn.commit()
            conn.close()
            self.refresh_transactions_table()
            self.refresh_overview_table()

            if self.daily_tab is not None:
                self.daily_tab.load_data()
                if hasattr(self.daily_tab, "dashboard_tab") and self.daily_tab.dashboard_tab is not None:
                    self.daily_tab.dashboard_tab.refresh()

    def delete_transaction(self, trans_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT type, vendor_id, date, amount, payment_mode FROM vendor_transactions WHERE id=?", (trans_id,))
        tr = c.fetchone()
        tr_type = tr[0] if tr else None
        vendor_id = tr[1] if tr else None
        date = tr[2] if tr else None
        amount = tr[3] if tr else None
        payment_mode = tr[4] if tr else None

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Delete this vendor transaction?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            conn.close()
            return

        # --- Cheque deletion for purchase ---
        if tr_type == "purchase":
            c.execute("DELETE FROM cheques WHERE vendor_transaction_id=?", (trans_id,))
            self.chequeCreated.emit()

        # --- Delete from daily_expense for payment ---
        if tr_type == "payment":
            # Get vendor name
            c.execute("SELECT name FROM vendors WHERE id=?", (vendor_id,))
            vrow = c.fetchone()
            vendor_name = vrow[0] if vrow else ""
            # Get Vendors expense category ID
            c.execute("SELECT id FROM expense_categories WHERE name='Vendors'")
            cat = c.fetchone()
            cat_id = cat[0] if cat else None
            if cat_id:
                # Compose notes as in your insert/update logic
                notes = f"Paid via {payment_mode}" if payment_mode else ""
                c.execute('''DELETE FROM daily_expense
                             WHERE date=? AND amount=? AND category_id=? AND description=? AND notes=?''',
                          (date, amount, cat_id, vendor_name, notes))

        c.execute('DELETE FROM vendor_transactions WHERE id=?', (trans_id,))
        conn.commit()
        conn.close()
        self.refresh_transactions_table()

        # Refresh daily cashflow and dashboard
        if self.daily_tab is not None:
            self.daily_tab.load_data()
            if hasattr(self.daily_tab, "dashboard_tab") and self.daily_tab.dashboard_tab is not None:
                self.daily_tab.dashboard_tab.refresh()

    # --- Vendor Management Tab Methods ---

    def ensure_opening_balance_column(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("PRAGMA table_info(vendors)")
        cols = [row[1] for row in c.fetchall()]
        if "opening_balance" not in cols:
            c.execute("ALTER TABLE vendors ADD COLUMN opening_balance REAL DEFAULT 0")
            conn.commit()
        conn.close()

    def ensure_due_date_column(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("PRAGMA table_info(vendor_transactions)")
        cols = [row[1] for row in c.fetchall()]
        if "due_date" not in cols:
            c.execute("ALTER TABLE vendor_transactions ADD COLUMN due_date TEXT")
            conn.commit()
        conn.close()

    def ensure_invoice_payment_columns(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("PRAGMA table_info(vendor_transactions)")
        cols = [row[1] for row in c.fetchall()]
        if "invoice_no" not in cols:
            c.execute("ALTER TABLE vendor_transactions ADD COLUMN invoice_no TEXT")
        if "payment_mode" not in cols:
            c.execute("ALTER TABLE vendor_transactions ADD COLUMN payment_mode TEXT")
        if "net_terms" not in cols:
            c.execute("ALTER TABLE vendor_transactions ADD COLUMN net_terms TEXT")
        conn.commit()
        conn.close()

    def refresh_vendor_table(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name, contact, opening_balance FROM vendors ORDER BY name COLLATE NOCASE ASC")
        self.vendors = c.fetchall()
        conn.close()
        self.filter_vendor_table()

    def filter_vendor_table(self):
        search = self.vendor_search_input.text().strip().lower()
        self.filtered_vendors = []
        for vendor in self.vendors:
            vid, name, contact, opening_balance = vendor
            if (len(search) < 2) or (search in name.lower()):
                self.filtered_vendors.append(vendor)
        self.vendor_table.setRowCount(len(self.filtered_vendors))
        for row, (vid, name, contact, opening_balance) in enumerate(self.filtered_vendors):
            current_balance = self.get_current_balance(vid, opening_balance)
            item_name = QTableWidgetItem(name)
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.vendor_table.setItem(row, 0, item_name)
            item_contact = QTableWidgetItem(contact)
            item_contact.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.vendor_table.setItem(row, 1, item_contact)
            item_opening = QTableWidgetItem(f"{opening_balance:.2f}")
            item_opening.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.vendor_table.setItem(row, 2, item_opening)
            item_current = QTableWidgetItem(f"{current_balance:.2f}")
            item_current.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.vendor_table.setItem(row, 3, item_current)

    def get_current_balance(self, vendor_id, opening_balance):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='purchase'", (vendor_id,))
        purchases = c.fetchone()[0] or 0
        c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='payment'", (vendor_id,))
        payments = c.fetchone()[0] or 0
        c.execute("SELECT COALESCE(SUM(amount),0) FROM vendor_transactions WHERE vendor_id=? AND type='return'", (vendor_id,))
        returns = c.fetchone()[0] or 0
        conn.close()
        return opening_balance + purchases - payments - returns

    def show_add_vendor_dialog(self):
        dialog = VendorDialog(self, "Add Vendor")
        if dialog.exec():
            name, contact, opening_balance = dialog.get_values()
            if not name:
                QMessageBox.warning(self, "Missing Name", "Vendor name is required.")
                return
            conn = get_conn()
            c = conn.cursor()
            try:
                c.execute("INSERT INTO vendors (name, contact, opening_balance) VALUES (?, ?, ?)", (name, contact, opening_balance))
                conn.commit()
            except Exception:
                QMessageBox.warning(self, "Exists", "Vendor already exists.")
            conn.close()
            self.refresh_vendor_table()
            self.refresh_vendor_combo()
            self.refresh_overview_table()

    def show_edit_vendor_dialog(self):
        selected = self.vendor_table.currentRow()
        if selected < 0 or selected >= len(self.filtered_vendors):
            QMessageBox.warning(self, "Select Vendor", "Please select a vendor to edit.")
            return
        vid, name, contact, opening_balance = self.filtered_vendors[selected]
        dialog = VendorDialog(self, "Edit Vendor", name, contact, opening_balance)
        if dialog.exec():
            new_name, new_contact, new_balance = dialog.get_values()
            if not new_name:
                QMessageBox.warning(self, "Missing Name", "Vendor name is required.")
                return
            conn = get_conn()
            c = conn.cursor()
            try:
                c.execute(
                    "UPDATE vendors SET name=?, contact=?, opening_balance=? WHERE id=?",
                    (new_name, new_contact, new_balance, vid)
                )
                conn.commit()
            except Exception:
                QMessageBox.warning(self, "Exists", "Vendor already exists.")
            conn.close()
            self.refresh_vendor_table()
            self.refresh_vendor_combo()

    def delete_vendor(self):
        selected = self.vendor_table.currentRow()
        if selected < 0 or selected >= len(self.filtered_vendors):
            return
        vid, name, *_ = self.filtered_vendors[selected]
        reply = QMessageBox.question(self, "Confirm", f"Delete vendor '{name}'? This will also remove associated transactions.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = get_conn()
            c = conn.cursor()
            c.execute("DELETE FROM vendor_transactions WHERE vendor_id=?", (vid,))
            c.execute("DELETE FROM vendors WHERE id=?", (vid,))
            conn.commit()
            conn.close()
            self.refresh_vendor_table()
            self.refresh_vendor_combo()
    
def days_remaining(due_iso):
    try:
        due = datetime.strptime(due_iso, "%Y-%m-%d")
        now = datetime.now()
        return (due.date() - now.date()).days
    except Exception:
        return None
        
  
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
        self.company_name.addItems(get_vendor_names())
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
            try:
                amt = float(amount)
                if not company or not bank:
                    raise ValueError
            except Exception:
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
            vendor_name, amount = row
            # Find vendor ID
            c.execute("SELECT id FROM vendors WHERE name = ?", (vendor_name,))
            vrow = c.fetchone()
            if vrow:
                vendor_id = vrow[0]
                today_iso = date.today().isoformat()
                # Insert payment into vendor_transactions
                c.execute(
                    '''INSERT INTO vendor_transactions
                    (vendor_id, date, type, amount, note, due_date, invoice_no, payment_mode, net_terms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (vendor_id, today_iso, "payment", float(amount), "Payment via Cheque", None, None, "Cheque", None)
                )
                vendor_trans_id = c.lastrowid
                # Insert into daily_expense as well
                c.execute("SELECT id FROM expense_categories WHERE name='Vendors'")
                cat_row = c.fetchone()
                if cat_row:
                    cat_id = cat_row[0]
                else:
                    c.execute("INSERT INTO expense_categories (name) VALUES ('Vendors')")
                    cat_id = c.lastrowid
                descr = vendor_name
                # Check if already exists to prevent duplicate (optional, but safe)
                c.execute("""
                    SELECT 1 FROM daily_expense WHERE date=? AND amount=? AND category_id=? AND description=? AND vendor_transaction_id=?
                """, (today_iso, amount, cat_id, descr, vendor_trans_id))
                if not c.fetchone():
                    c.execute(
                        '''INSERT INTO daily_expense (date, amount, category_id, description, vendor_transaction_id)
                        VALUES (?, ?, ?, ?, ?)''',
                        (today_iso, amount, cat_id, descr, vendor_trans_id)
                    )
        conn.commit()
        conn.close()
        self.refresh()
        self.chequePaid.emit()   # <-- EMIT THE SIGNAL HERE

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



        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background: #232627;
                border-radius: 11px;
                color: #f1f3f4;
                font-size: 16px;
                font-weight: bold;
                margin: 8px 0 8px 8px;
                padding: 10px 0;
            }
            QListWidget::item:selected {
                background: #fb700e;
                color: #fff;
                border-radius: 6px;
            }
        """)
        self.sidebar.addItem("Logo")
        self.sidebar.addItem("Backup & Import/Export")
        self.sidebar.addItem("Expense Categories")
        self.sidebar.addItem("Manage Payroll")
        self.layout.addWidget(self.sidebar)

        # Stacked content
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        # Logo Page
        logo_page = QWidget()
        logo_vbox = QVBoxLayout(logo_page)

        logo_title = QLabel("Application Logo")
        logo_title.setStyleSheet("font-size:22px; font-weight:600; margin-bottom:14px;")
        logo_vbox.addWidget(logo_title)

        logo_row = QHBoxLayout()
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(96, 96)
        self.logo_label.setScaledContents(True)
        self.logo_label.setStyleSheet("border:2px solid #35393A; border-radius:15px; background:#232627;")
        self.load_app_logo()
        logo_row.addWidget(self.logo_label)
        self.upload_logo_btn = QPushButton("Upload Logo")
        self.upload_logo_btn.setStyleSheet("font-size:16px;")
        self.upload_logo_btn.clicked.connect(self.upload_logo)
        logo_row.addWidget(self.upload_logo_btn)
        logo_row.addStretch()
        logo_vbox.addLayout(logo_row)
        logo_vbox.addStretch(1)
        self.stack.addWidget(logo_page)

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

        # Sidebar navigation
        self.sidebar.setCurrentRow(0)
        self.stack.setCurrentIndex(0)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.setLayout(self.layout)

        

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
        from datetime import datetime
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
        # Set window icon from logo, if exists
        logo_path = os.path.join(os.path.expanduser("~"), ".national_bicycles_logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self.dashboard = DashboardTab()
        self.daily = DailyTab(self.dashboard)
        self.vendors = VendorsTab(daily_tab=self.daily)
        self.cheques_tab = ChequesTab()
        self.payroll_tab = PayrollTab()
        self.documents_tab = DocumentsTab()
        self.settings_tab = SettingsTab()
        

        # 1. Cashflow (was 'Daily')
        self.tabs.addTab(self.daily, QIcon(), "  Cashflow  ")
        # 2. Vendors
        self.tabs.addTab(self.vendors, QIcon(), "  Vendors  ")
        # 3. Cheques
        self.tabs.addTab(self.cheques_tab, QIcon(), "  Cheques  ")
        self.tabs.addTab(self.payroll_tab, QIcon(), "  Payroll  ")
        self.tabs.addTab(self.documents_tab, QIcon(), "  Documents  ")
        # 4. Dashboard
        self.tabs.addTab(self.dashboard, QIcon(), "  Dashboard  ")
        # 5. Settings
        self.tabs.addTab(self.settings_tab, QIcon(), "  Settings  ")

        self.cheques_tab.chequePaid.connect(self.vendors.refresh_transactions_table)
        self.cheques_tab.chequePaid.connect(self.vendors.refresh_vendor_table)
        self.cheques_tab.chequePaid.connect(self.vendors.refresh_vendor_combo)
        self.cheques_tab.chequePaid.connect(self.daily.load_data)
        self.cheques_tab.chequePaid.connect(self.vendors.refresh_overview_table)
        self.vendors.chequeCreated.connect(self.cheques_tab.refresh)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.do_auto_backup("open")


    def do_auto_backup(self, event):
        from datetime import datetime
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