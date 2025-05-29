import sys
import sqlite3
import os
import shutil
from datetime import date, datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFormLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QMessageBox, QDialog, QListWidget, QInputDialog,
    QDateEdit, QHeaderView, QAbstractItemView, QFrame, QGridLayout, QStyle, QFileDialog, QCheckBox, QButtonGroup, QMenu, QGraphicsColorizeEffect, QStackedWidget, QSizePolicy, QCompleter
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
    c.execute('''CREATE TABLE IF NOT EXISTS expense_categories (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_expense (
        id INTEGER PRIMARY KEY,
        date TEXT,
        amount REAL,
        category_id INTEGER,
        description TEXT,
        vendor_transaction_id INTEGER,
        notes TEXT,
        FOREIGN KEY(category_id) REFERENCES expense_categories(id)
    )''')
    if not column_exists(conn, "daily_expense", "notes"):
        try:
            c.execute("ALTER TABLE daily_expense ADD COLUMN notes TEXT")
        except Exception:
            pass
    c.execute('''CREATE TABLE IF NOT EXISTS daily_expense (
        id INTEGER PRIMARY KEY,
        date TEXT,
        amount REAL,
        category_id INTEGER,
        description TEXT,
        vendor_transaction_id INTEGER,
        FOREIGN KEY(category_id) REFERENCES expense_categories(id)
    )''')
    if not column_exists(conn, "daily_expense", "vendor_transaction_id"):
        try:
            c.execute("ALTER TABLE daily_expense ADD COLUMN vendor_transaction_id INTEGER")
        except Exception:
            pass
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        contact TEXT,
        opening_balance REAL DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendor_transactions (
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
    )''')
    c.execute("INSERT OR IGNORE INTO expense_categories (name) VALUES ('Vendors')")
    c.execute('''CREATE TABLE IF NOT EXISTS income_categories (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_income (
        id INTEGER PRIMARY KEY,
        date TEXT,
        amount REAL,
        category_id INTEGER,
        description TEXT,
        FOREIGN KEY(category_id) REFERENCES income_categories(id)
    )''')
    if not column_exists(conn, "daily_income", "notes"):
        try:
            c.execute("ALTER TABLE daily_income ADD COLUMN notes TEXT")
        except Exception:
            pass
    c.execute('''CREATE TABLE IF NOT EXISTS cheques (
        id INTEGER PRIMARY KEY,
        cheque_date TEXT,
        company_name TEXT,
        bank_name TEXT,
        due_date TEXT,
        amount REAL,
        is_paid INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def get_income_categories():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name FROM income_categories")
    cats = c.fetchall()
    conn.close()
    return cats

def get_expense_categories():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name FROM expense_categories")
    cats = c.fetchall()
    conn.close()
    return cats

def get_vendor_names():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT name FROM vendors ORDER BY name COLLATE NOCASE ASC")
    vendors = [row[0] for row in c.fetchall()]
    conn.close()
    return vendors

def to_ddmmyyyy(iso):
    try:
        dt = datetime.strptime(iso, "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return iso

def to_month(iso):
    try:
        dt = datetime.strptime(iso, "%Y-%m-%d")
        return dt.strftime("%B")
    except Exception:
        return ""

def to_iso_date(ddmmyyyy):
    try:
        dt = datetime.strptime(ddmmyyyy, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ddmmyyyy
    
def get_all_descriptions():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT description FROM daily_income WHERE description IS NOT NULL AND description <> ''")
    income_descs = [row[0] for row in c.fetchall()]
    c.execute("SELECT DISTINCT description FROM daily_expense WHERE description IS NOT NULL AND description <> ''")
    expense_descs = [row[0] for row in c.fetchall()]
    conn.close()
    # Combine and deduplicate
    all_descs = list(set(income_descs + expense_descs))
    return all_descs

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background: #181A1B;
    color: #F1F3F4;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}
/* ... [rest of stylesheet as in your previous code, unchanged] ... */
QLabel { color: #F1F3F4; font-size: 15px; }
QTabWidget::pane { border: none; background: #181A1B; }
QTabBar::tab {
    background: #232627;
    color: #cfcfcf;
    border-radius: 8px 8px 0 0;
    padding: 10px 18px;
    font-size: 15px;
    min-width: 100px;
}
QTabBar::tab:selected {
    background: #26292A;
    color: #fff;
    font-weight: bold;
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
    border-radius: 8px;
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
    background-color: #232627;
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
"""

# ---------------- Dialog and Tab Classes ----------------

class EntryEditDialog(QDialog):
    def __init__(self, entry_type, entry_id, date, cat_id, amount, desc, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Entry")
        self.entry_type = entry_type
        self.entry_id = entry_id
        self.setMinimumWidth(390)
        self.setStyleSheet("""
            QDialog { background: #222325; }
            QLineEdit, QComboBox { border-radius: 8px; padding: 8px; font-size: 15px; background: #232627; color: #F1F3F4;}
            QLabel { font-size: 15px; color: #F1F3F4;}
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
            self.desc_input.text()
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
        self.setMinimumWidth(440)
        self.setStyleSheet("""
            QDialog { background: #181A1B; }
            QLabel { font-size: 18px; font-weight: 600; color: #F1F3F4;}
            QLineEdit, QComboBox, QDateEdit {
                border-radius: 10px; padding: 10px; font-size: 16px;
                border: 1.7px solid #35393A; background: #232627; color: #F1F3F4;
            }
            QPushButton {
                border-radius: 9px; padding: 10px 20px; font-size: 16px;
                background: #26292A; color: #F1F3F4; font-weight: bold;
            }
            QPushButton:pressed {
                background: #35393A;
            }
        """)
        layout = QVBoxLayout(self)
        centering = QVBoxLayout()
        layout.addLayout(centering)
        centering.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("Add Income / Expense")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        centering.addWidget(title)

        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form.setFormAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.date_input = QDateEdit()
        self.date_input.setDisplayFormat("dd-MM-yyyy")
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.form.addRow("Date", self.date_input)

        self.type_input = QComboBox()
        self.type_input.addItems(["Income", "Expense"])
        self.form.addRow("Type", self.type_input)

        self.category_input = QComboBox()
        self.form.addRow("Category", self.category_input)

        self.description_label = QLabel("Description")
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Description")
        # Auto-complete for Description
        desc_completer = QCompleter(get_all_descriptions())
        desc_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.description_input.setCompleter(desc_completer)
        self.form.addRow(self.description_label, self.description_input)
        self.description_label.hide()
        self.description_input.hide()

        self.amount_input = QLineEdit()
        self.amount_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.amount_input.setPlaceholderText("Amount (AED)")
        afont = QFont()
        afont.setPointSize(24)
        afont.setBold(True)
        self.amount_input.setFont(afont)
        self.form.addRow(QLabel("Amount"), self.amount_input)

        # --- NEW: Notes Field ---
        self.notes_label = QLabel("Notes")
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Notes (optional)")
        self.form.addRow(self.notes_label, self.notes_input)

        centering.addLayout(self.form)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_entry)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_form)
        for b in [self.save_btn, self.delete_btn, self.clear_btn]:
            btn_row.addWidget(b)
        centering.addLayout(btn_row)
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
        else:
            for cid, name in get_expense_categories():
                if name.strip().lower() == "vendors":
                    continue
                self.category_input.addItem(name, cid)
        self.category_input.blockSignals(False)
        self.handle_category_change()

    def handle_category_change(self):
        self.description_label.show()
        self.description_input.show()

    def update_amount_placeholder_color(self, t):
        color = "#43a047" if t == "Income" else "#e53935"
        self.amount_input.setStyleSheet(
            f"""
            QLineEdit {{
                background: #232627;
                color: #F1F3F4;
                border-radius: 12px;
                border: 2px solid #35393A;
                font-size: 24px;
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
        self.handle_category_change()

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
                border-radius: 8px;
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
                border-radius: 8px;
                padding: 7px 16px;
                font-size: 14px;
                background: #232627;
                color: #F1F3F4;
                border: 1.5px solid #35393A;
                font-weight:bold;
            }
            QPushButton:pressed {
                background: #35393A;
                color: #fff;
            }
        """)

        self.date_from = QDateEdit()
        self.date_from.setDisplayFormat("dd-MM-yyyy")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))

        self.date_to = QDateEdit()
        self.date_to.setDisplayFormat("dd-MM-yyyy")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())

        self.category_input = QComboBox()
        self.category_input.addItem("All", None)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Description contains...")
        # Auto-complete for Description
        desc_completer = QCompleter(get_all_descriptions())
        desc_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.description_input.setCompleter(desc_completer)

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
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self.category_input.setCurrentIndex(0)
        self.description_input.clear()

    def refresh_categories(self):
        self.category_input.clear()
        self.category_input.addItem("All", None)
        for cid, name in get_income_categories():
            self.category_input.addItem(f"Income: {name}", f"inc:{cid}")
        for cid, name in get_expense_categories():
            self.category_input.addItem(f"Expense: {name}", f"exp:{cid}")

    def clear_all_filters(self):
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self.category_input.setCurrentIndex(0)
        self.description_input.clear()

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
                    border-radius: 18px;
                    padding: 0px 0px;
                    /* Remove border for no outline */
                }}
            """
        )
        h = QHBoxLayout(box)
        h.setContentsMargins(22, 8, 22, 8)
        h.setSpacing(16)
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size:38px; color:{color};")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size:16px;color:#bcbcbc; font-weight:700; margin-bottom:2px;")
        right.addWidget(title_label)
        amount_label = QLabel(amount)
        amount_label.setStyleSheet(
            f"font-size:27px;font-weight:700;color:{color};margin-top:2px;letter-spacing:1px;"
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
        layout.setSpacing(10)  # Good vertical gap between main blocks

        self.filter_widget = FilterWidget()
        layout.addWidget(self.filter_widget)
        self.filter_widget.date_from.dateChanged.connect(self.load_data)
        self.filter_widget.date_to.dateChanged.connect(self.load_data)
        self.filter_widget.category_input.currentIndexChanged.connect(self.load_data)
        self.filter_widget.description_input.textChanged.connect(self.load_data)
        self.filter_widget.clear_button.clicked.connect(self.load_data)

        layout.addSpacing(0)  # Gap between filter and button row

        # --- Button Row with left margin and Today label with right margin ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(0)  # No horizontal gap between widgets

        # Container widget for left margin for buttons
        btn_left_container = QWidget()
        btn_left_layout = QHBoxLayout()
        btn_left_layout.setContentsMargins(12, 0, 0, 0)  # 12px left margin
        btn_left_layout.setSpacing(12)
        btn_left_container.setLayout(btn_left_layout)
        

        self.add_entry_btn = QPushButton("Add")
        self.add_entry_btn.setToolTip("Add Income/Expense Entry (F1)")
        self.add_entry_btn.setFixedSize(120, 40)
        self.add_entry_btn.setStyleSheet("background:#26292A; color:white; font-size: 16px; font-weight: bold; border-radius: 3px;")
        self.add_entry_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))        
        self.add_entry_btn.setIconSize(QSizeF(22, 22).toSize())
        
        self.add_entry_btn.setText(" Add")  # Two spaces before 'Add'
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
        self.add_entry_btn.setText(" Add")  # Two spaces before 'Add'
        self.print_btn.clicked.connect(self.print_day_report)
        btn_left_layout.addWidget(self.print_btn)

        btn_row.addWidget(btn_left_container)
        btn_row.addStretch()

        # Today label: right margin, soft dimmed orange
        today_container = QWidget()
        today_layout = QHBoxLayout()
        today_layout.setContentsMargins(0, 0, 12, 0)  # 12px right margin
        today_layout.setSpacing(0)
        today_container.setLayout(today_layout)

        today_label = QLabel(f"Today: {date.today().strftime('%d-%m-%Y')}")
        today_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        today_label.setStyleSheet("""
            font-weight: bold;
            font-size: 15px;
            color: #fff3d1;
            padding: 7px 16px;
            border-radius: 5px;
            letter-spacing: 0.5px;
        """)
        today_layout.addWidget(today_label)
        btn_row.addWidget(today_container)

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

        # --- Totals frame ---
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
        totals_layout.addWidget(self.total_income_box)
        totals_layout.addWidget(self.total_expense_box)
        totals_layout.addWidget(self.balance_box)
        totals_layout.addWidget(self.profit_box)
        layout.addWidget(self.totals_frame)

        self.data_table.doubleClicked.connect(self.handle_table_double_click)
        self.setLayout(layout)
        self.load_data()

    # ... (rest of your methods unchanged) ...

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
            # --- Prevent duplicate Sales or Services on same date ---
            if type_str == "Income":
                # Get the selected category name
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
                # Proceed to insert, since not duplicate
                c.execute(
                    "INSERT INTO daily_income (date, amount, category_id, description, notes) VALUES (?, ?, ?, ?, ?)",
                    (date_iso, amt, cat_id, desc, notes),
                )
            else:
                c.execute(
                    "INSERT INTO daily_expense (date, amount, category_id, description, notes) VALUES (?, ?, ?, ?, ?)",
                    (date_iso, amt, cat_id, desc, notes),
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
        # If user picked "All"
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

        # Filter by description if needed
        if desc_filter:
            rows = [r for r in rows if desc_filter in (r[4] or "").lower()]

        self.data_table.setRowCount(len(rows))
        total_income = 0
        total_expense = 0
        for i, (d, amt, cat, typ, desc, eid, catid, notes) in enumerate(rows):
            desc_len = len(desc or "")
            notes_len = len(notes or "")
            self.data_table.setRowHeight(i, 56 if desc_len > 60 or notes_len > 60 else 36)
            for col, value in enumerate([
                to_ddmmyyyy(d), to_month(d), typ, cat or "", desc or "", f"{amt:.2f} AED", notes or ""
            ]):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 6:  # Notes column
                    item.setForeground(QColor("#aaa"))  # Dim/gray color
                self.data_table.setItem(i, col, item)
            item_id = QTableWidgetItem(str(eid))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.data_table.setItem(i, 7, item_id)
            self.data_table.setColumnHidden(7, True)
            if typ == "Income":
                total_income += amt
            elif typ == "Expense":
                total_expense += amt

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
        conn = get_conn()
        c = conn.cursor()
        if typ == "Income":
            c.execute("SELECT category_id FROM daily_income WHERE id=?", (eid,))
        else:
            c.execute("SELECT category_id FROM daily_expense WHERE id=?", (eid,))
        result = c.fetchone()
        catid = result[0] if result else None
        conn.close()
        dialog = EntryEditDialog(typ, eid, to_iso_date(date_str), catid, amt, desc, self)
        if dialog.exec():
            if dialog.deleted:
                self.delete_entry(typ, eid)
            else:
                new_date, new_catid, new_amt, new_desc = dialog.get_values()
                self.update_entry(typ, eid, new_date, new_catid, new_amt, new_desc)
            self.load_data()
            self.dashboard_tab.refresh()

    def update_entry(self, typ, eid, date, catid, amt, desc):
        conn = get_conn()
        c = conn.cursor()
        if typ == "Income":
            c.execute("UPDATE daily_income SET date=?, category_id=?, amount=?, description=? WHERE id=?",
                      (date, catid, amt, desc, eid))
        else:
            c.execute("UPDATE daily_expense SET date=?, category_id=?, amount=?, description=? WHERE id=?",
                      (date, catid, amt, desc, eid))
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
            SELECT ic.name, SUM(di.amount)
            FROM daily_income di
            LEFT JOIN income_categories ic ON di.category_id = ic.id
            WHERE di.date=?
            GROUP BY ic.name
        """, (date_iso,))
        income_rows = c.fetchall()
        c.execute("SELECT SUM(amount) FROM daily_income WHERE date=?", (date_iso,))
        total_income = c.fetchone()[0] or 0

        c.execute("""
            SELECT ec.name, SUM(de.amount)
            FROM daily_expense de
            LEFT JOIN expense_categories ec ON de.category_id = ec.id
            WHERE de.date=?
            GROUP BY ec.name
        """, (date_iso,))
        expense_rows = c.fetchall()
        c.execute("SELECT SUM(amount) FROM daily_expense WHERE date=?", (date_iso,))
        total_expense = c.fetchone()[0] or 0

        conn.close()
        balance = total_income - total_expense
        date_ddmmyyyy = QDate.fromString(date_iso, "yyyy-MM-dd").toString("dd/MM/yyyy")

        doc = QTextDocument()
        html = f"""
        <table width="100%" style="font-size:15px;">
        <tr><td colspan=2><b>DATE</b></td><td colspan=2 align="right">{date_ddmmyyyy}</td></tr>
        <tr><td colspan=4><hr></td></tr>
        <tr><td colspan=2><b>INCOME</b></td><td><b>AED</b></td><td align="right"><b>{total_income:.2f}</b></td></tr>
        """
        for name, amt in income_rows:
            html += f'<tr><td colspan=2>{name or ""}</td><td>AED</td><td align="right">{amt:.2f}</td></tr>'
        html += f"""
        <tr style="background:#35393A;">
            <td colspan=2><b>TOTAL</b></td><td><b>AED</b></td><td align="right"><b>{balance:.2f}</b></td>
        </tr>
        <tr><td colspan=4><hr></td></tr>
        <tr><td colspan=2><b>EXPENSES</b></td><td><b>AED</b></td><td align="right"><b>{total_expense:.2f}</b></td></tr>
        """
        for name, amt in expense_rows:
            html += f'<tr><td colspan=2>{name or ""}</td><td>AED</td><td align="right">{amt:.2f}</td></tr>'
        html += "</table>"

        doc.setHtml(html)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        pagesize = QPageSize(QSizeF(80, 200), QPageSize.Unit.Millimeter)
        printer.setPageSize(pagesize)
        printer.setPageMargins(QMarginsF(5, 5, 5, 5), QPageLayout.Unit.Millimeter)
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)

        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            doc.print(printer)

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
        self.trans_payment_mode.addItems(['Cash', 'Credit Card', 'Bank Transfer', 'UPI', 'Other'])
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
    def __init__(self, daily_tab=None):
        super().__init__()
        self.ensure_invoice_payment_columns()  # Ensure columns exist before any queries
        self.daily_tab = daily_tab
        self.vendors = []
        self.layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        # --- Transactions Tab ---
        self.trans_tab = QWidget()
        self.trans_layout = QVBoxLayout()
        self.trans_tab.setLayout(self.trans_layout)
        vendor_select_row = QHBoxLayout()
        vendor_select_row.addWidget(QLabel("Select Vendor:"))
        self.trans_vendor_combo = QComboBox()
        self.trans_vendor_combo.setMinimumWidth(320)
        self.trans_vendor_combo.setMaximumWidth(500)
        self.trans_vendor_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.trans_vendor_combo.currentIndexChanged.connect(self.refresh_transactions_table)
        vendor_select_row.addWidget(self.trans_vendor_combo)
        self.trans_vendor_search = QLineEdit()
        self.trans_vendor_search.setPlaceholderText("Search vendor...")
        self.trans_vendor_search.textChanged.connect(self.filter_trans_vendor_combo)
        vendor_select_row.addWidget(self.trans_vendor_search)
        vendor_select_row.addStretch()
        self.trans_layout.addLayout(vendor_select_row)
        self.current_balance_label = QLabel("Current Balance: 0.00 AED")
        self.current_balance_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.current_balance_label.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#fdc59e; margin:0 12px 8px 0;"
        )
        self.trans_layout.addWidget(self.current_balance_label)
        add_entry_btn_row = QHBoxLayout()
        add_entry_btn_row.addStretch()
        self.show_add_entry_btn = QPushButton("Add Transaction")
        self.show_add_entry_btn.setFixedWidth(180)
        self.show_add_entry_btn.clicked.connect(self.show_transaction_dialog)
        add_entry_btn_row.addWidget(self.show_add_entry_btn)
        self.trans_layout.addLayout(add_entry_btn_row)
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(9)
        self.trans_table.setHorizontalHeaderLabels([
            'Date', 'Type', 'Debit (AED)', 'Credit (AED)', 'Due Date',
            'NET Terms', 'Payment Mode', 'Invoice No.', 'Note'
        ])
        self.trans_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.trans_table.setAlternatingRowColors(True)
        self.trans_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.trans_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.trans_table.customContextMenuRequested.connect(self.show_transaction_context_menu)
        self.trans_table.doubleClicked.connect(self.handle_transaction_double_click)
        self.trans_layout.addWidget(QLabel("Vendor Transactions:"))
        self.trans_layout.addWidget(self.trans_table)
        self.tabs.addTab(self.trans_tab, "Transactions")

        # --- Manage Vendors Tab ---
        self.vendor_manage_tab = QWidget()
        self.vendor_manage_layout = QVBoxLayout()
        self.vendor_manage_tab.setLayout(self.vendor_manage_layout)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Search Vendor:"))
        self.vendor_search_input = QLineEdit()
        self.vendor_search_input.setPlaceholderText("Type at least 2 letters of vendor name...")
        self.vendor_search_input.textChanged.connect(self.filter_vendor_table)
        filter_row.addWidget(self.vendor_search_input)
        filter_row.addStretch()
        self.vendor_manage_layout.addLayout(filter_row)

        # Add Export PDF button to transactions tab
        export_row = QHBoxLayout()
        self.export_pdf_btn = QPushButton("Export Transactions to PDF")
        self.export_pdf_btn.setStyleSheet("font-size:15px; font-weight:bold; background:#fb700e; color:white; border-radius:10px; padding:8px 18px;")
        self.export_pdf_btn.clicked.connect(self.export_transactions_pdf)
        export_row.addWidget(self.export_pdf_btn)
        export_row.addStretch()
        self.trans_layout.insertLayout(2, export_row)  # Place after vendor select and balance

        # --- Total Account Payable label ---
        self.total_payable_label = QLabel("Total Account Payable: 0.00 AED")
        self.total_payable_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_payable_label.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#43a047; margin:0 12px 8px 0;"
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
        self.tabs.addTab(self.vendor_manage_tab, "Manage Vendors")

        self.refresh_vendor_combo()
        self.refresh_vendor_table()
        self.refresh_transactions_table()

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
        # ... rest of your code for querying and populating the transactions table ...
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT opening_balance FROM vendors WHERE id=?", (vendor_id,))
        opening_balance_row = c.fetchone()
        opening_balance = opening_balance_row[0] if opening_balance_row else 0.0
        c.execute('''
            SELECT date, type, amount, due_date, note, invoice_no, payment_mode, net_terms, id
            FROM vendor_transactions
            WHERE vendor_id=?
            ORDER BY date ASC, id ASC
        ''', (vendor_id,))
        rows = c.fetchall()
        conn.close()
        self.trans_table.setRowCount(len(rows))
        balance = opening_balance
        for i, (date_str, ttype, amt, due, note, invoice_no, payment_mode, net_terms, trans_id) in enumerate(rows):
            ttype_display = ttype.capitalize() if ttype else ""
            debit = credit = ""
            if ttype == "purchase":
                debit = f"{amt:.2f}"
                balance += amt
            elif ttype in ("payment", "return"):
                credit = f"{amt:.2f}"
                balance -= amt
            self.trans_table.setItem(i, 0, QTableWidgetItem(to_ddmmyyyy(date_str)))
            self.trans_table.setItem(i, 1, QTableWidgetItem(ttype_display))
            debit_item = QTableWidgetItem(debit)
            debit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.trans_table.setItem(i, 2, debit_item)
            credit_item = QTableWidgetItem(credit)
            credit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.trans_table.setItem(i, 3, credit_item)
            self.trans_table.setItem(i, 4, QTableWidgetItem(to_ddmmyyyy(due) if due else ''))
            self.trans_table.setItem(i, 5, QTableWidgetItem(net_terms or ''))
            self.trans_table.setItem(i, 6, QTableWidgetItem(payment_mode or ''))
            self.trans_table.setItem(i, 7, QTableWidgetItem(invoice_no or ''))
            self.trans_table.setItem(i, 8, QTableWidgetItem(note or ''))
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
                if bank_name:
                    # Also add to cheques table
                    c.execute('''INSERT INTO cheques (cheque_date, company_name, bank_name, due_date, amount, is_paid)
                                VALUES (?, ?, ?, ?, ?, 0)''',
                            (date_iso, vendor_name, bank_name, cheque_due, amount))
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
        date_str = self.trans_table.item(row, 0).text()
        ttype = self.trans_table.item(row, 1).text().lower()
        debit = self.trans_table.item(row, 2).text()
        credit = self.trans_table.item(row, 3).text()
        invoice_no = self.trans_table.item(row, 7).text()
        amount = 0.0
        if debit:
            amount = float(debit)
        elif credit:
            amount = float(credit)
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
        orig_date, orig_type, orig_amt, orig_due, orig_note, orig_invoice, orig_payment_mode, orig_net_terms = tr
        vendor_name = self.trans_vendor_combo.currentText()
        dlg = TransactionEntryDialog(self, vendor_id, vendor_name, ttype=orig_type)  # <-- fixed here
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
            # Insert logic based on ttype
            if ttype == "purchase":
                c.execute('''INSERT INTO vendor_transactions
                    (vendor_id, date, type, amount, note, due_date, invoice_no)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (vendor_id, date_iso, ttype, amount, note, due_iso, invoice_no)
                )
                if bank_name:
                    # Also add to cheques table
                    c.execute('''INSERT INTO cheques (cheque_date, company_name, bank_name, due_date, amount, is_paid)
                                VALUES (?, ?, ?, ?, ?, 0)''',
                            (date_iso, vendor_name, bank_name, cheque_due, amount))
            elif ttype == "payment":
                c.execute('''INSERT INTO vendor_transactions
                    (vendor_id, date, type, amount, note, invoice_no, payment_mode)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (vendor_id, date_iso, ttype, amount, note, invoice_no, payment_mode)
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

    def delete_transaction(self, trans_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT type FROM vendor_transactions WHERE id=?", (trans_id,))
        tr = c.fetchone()
        tr_type = tr[0] if tr else None
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Delete this vendor transaction?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            conn.close()
            return
        c.execute('DELETE FROM vendor_transactions WHERE id=?', (trans_id,))
        if tr_type == "payment":
            c.execute("DELETE FROM daily_expense WHERE vendor_transaction_id=?", (trans_id,))
        conn.commit()
        conn.close()
        self.refresh_transactions_table()

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
        layout.addRow("Cheque Date:", self.cheque_date)

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
            "Cheque Date", "Company", "Bank", "Due Date", "Amount (AED)", "Days Remaining", "ID"
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
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.dashboard, QIcon(), "  Dashboard  ")
        self.tabs.addTab(self.daily, QIcon(), "  Daily  ")
        self.tabs.addTab(self.vendors, QIcon(), "  Vendors  ")
        self.tabs.addTab(self.cheques_tab, QIcon(), "  Cheques  ")
        self.tabs.addTab(self.settings_tab, QIcon(), "  Settings  ")

        self.cheques_tab.chequePaid.connect(self.vendors.refresh_transactions_table)
        self.cheques_tab.chequePaid.connect(self.vendors.refresh_vendor_table)
        self.cheques_tab.chequePaid.connect(self.vendors.refresh_vendor_combo)
        self.cheques_tab.chequePaid.connect(self.daily.load_data)

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

def main():
    app = QApplication(sys.argv)
    init_db()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()