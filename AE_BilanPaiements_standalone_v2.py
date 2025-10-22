
# -*- coding: utf-8 -*-
"""
AE_BilanPaiements_standalone_v2.py
- Ajoute une ligne TOTAL en bas des tableaux
- Exports propres: PDF (via Qt) et Excel (XML Spreadsheet 2003, sans dépendances)
"""
import os, sys, csv, subprocess
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import QTextDocument

def _data_dirs():
    base = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(base, "data")
    try:
        import AE_Gestion_àgarder2010 as ae  # type: ignore
        d = getattr(ae, "DATA_DIR", None)
        if d and os.path.isdir(d):
            data = d
    except Exception:
        pass
    tdir = os.path.join(data, "_t")
    os.makedirs(tdir, exist_ok=True)
    return base, data, tdir

def _log_bilan(line: str):
    try:
        _, data, _ = _data_dirs()
        with open(os.path.join(data, "bilan_export.log"), "a", encoding="utf-8") as f:
            ts = datetime.utcnow().isoformat()
            f.write("{} standalone {}\n".format(ts, line))
    except Exception:
        pass

def _read_csv_rows(path):
    rows = []
    if not os.path.exists(path):
        return rows
    try_enc = ["utf-8-sig", "utf-8", "cp1252"]
    last_err = None
    for enc in try_enc:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                r = csv.reader(f)
                rows = [row for row in r]
            return rows
        except Exception as e:
            last_err = e
    raise last_err or RuntimeError("CSV read error")

def _to_number(s):
    if s is None: return None
    if isinstance(s, (int, float)): return float(s)
    t = str(s).strip().replace("€","").replace("\u202f","").replace("\xa0","").replace(" ", "").replace(",", ".")
    try:
        return float(t)
    except Exception:
        return None

class BilanApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bilan paiements — autonome v2")
        self.resize(1100, 680)
        self.base, self.data, self.tdir = _data_dirs()

        # Header
        head = QHBoxLayout()
        head.addWidget(QLabel("Du"))
        self.de_from = QDateEdit(); self.de_from.setDisplayFormat("yyyy-MM-dd"); self.de_from.setCalendarPopup(True)
        self.de_from.setDate(QDate.currentDate().addMonths(-1))
        head.addWidget(self.de_from)
        head.addWidget(QLabel("au"))
        self.de_to = QDateEdit(); self.de_to.setDisplayFormat("yyyy-MM-dd"); self.de_to.setCalendarPopup(True)
        self.de_to.setDate(QDate.currentDate())
        head.addWidget(self.de_to)
        head.addStretch(1)

        self.btn_run = QPushButton("Générer")
        self.btn_reload = QPushButton("Recharger")
        self.btn_open_folder = QPushButton("Ouvrir dossier _t")
        self.btn_open_ledger = QPushButton("Ouvrir CSV ledger")
        self.btn_open_bilan = QPushButton("Ouvrir CSV bilan")
        self.btn_export_pdf = QPushButton("Exporter PDF")
        self.btn_export_xls = QPushButton("Exporter Excel")

        for b in (self.btn_run, self.btn_reload, self.btn_open_folder, self.btn_open_ledger, self.btn_open_bilan, self.btn_export_pdf, self.btn_export_xls):
            head.addWidget(b)

        # Tables
        self.tabs = QTabWidget()
        self.tbl_ledger = QTableWidget(); self.tbl_bilan = QTableWidget()
        self.tabs.addTab(self.tbl_ledger, "Ledger (period)")
        self.tabs.addTab(self.tbl_bilan, "Bilan (period)")

        root = QVBoxLayout(self)
        root.addLayout(head)
        root.addWidget(self.tabs, 1)

        # Signals
        self.btn_run.clicked.connect(self.on_run)
        self.btn_reload.clicked.connect(self.load_tables)
        self.btn_open_folder.clicked.connect(self.on_open_folder)
        self.btn_open_ledger.clicked.connect(lambda: self.on_open_file(os.path.join(self.tdir, "ledger_read_period.csv")))
        self.btn_open_bilan.clicked.connect(lambda: self.on_open_file(os.path.join(self.tdir, "bilan_read_period.csv")))
        self.btn_export_pdf.clicked.connect(self.on_export_pdf)
        self.btn_export_xls.clicked.connect(self.on_export_xls)

        # Initial
        self.load_tables()

    def on_open_folder(self):
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.tdir)
            elif sys.platform == "darwin":
                subprocess.call(["open", self.tdir])
            else:
                subprocess.call(["xdg-open", self.tdir])
        except Exception as e:
            QMessageBox.critical(self, "Dossier", str(e))

    def on_open_file(self, path):
        try:
            if not os.path.exists(path):
                QMessageBox.warning(self, "Fichier absent", path)
                return
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])
        except Exception as e:
            QMessageBox.critical(self, "Ouvrir fichier", str(e))

    def on_run(self):
        du = self.de_from.date().toString("yyyy-MM-dd")
        au = self.de_to.date().toString("yyyy-MM-dd")
        runner = os.path.join(self.base, "run_ledger_dump_plus.py")
        if not os.path.exists(runner):
            QMessageBox.critical(self, "Bilan paiements", "Script introuvable:\n" + runner)
            return
        args = [sys.executable, runner, "--from", du, "--to", au]
        env = dict(os.environ); env["AE_PAUSE"] = "0"
        _log_bilan("start runner={} du={} au={}".format(runner, du, au))
        try:
            p = subprocess.run(args, cwd=self.base, env=env, capture_output=True, text=True)
        except Exception as e:
            _log_bilan("exception {}".format(repr(e)))
            QMessageBox.critical(self, "Bilan paiements", str(e))
            return
        _log_bilan("rc={}".format(p.returncode))
        if p.stdout: _log_bilan("stdout " + p.stdout.strip().replace("\n", "\\n"))
        if p.stderr: _log_bilan("stderr " + p.stderr.strip().replace("\n", "\\n"))
        if p.returncode != 0:
            QMessageBox.critical(self, "Bilan paiements", p.stderr or p.stdout or "Erreur inconnue")
            return
        self.load_tables()
        QMessageBox.information(self, "Bilan paiements", "Export OK")

    def _fill_table_with_totals(self, tbl: QTableWidget, rows):
        tbl.clear()
        if not rows:
            tbl.setRowCount(0); tbl.setColumnCount(0); return
        headers = [str(h) for h in rows[0]]
        data_rows = rows[1:]
        tbl.setRowCount(len(data_rows) + 1)  # +1 for TOTAL
        tbl.setColumnCount(len(headers))
        for j, h in enumerate(headers):
            tbl.setHorizontalHeaderItem(j, QTableWidgetItem(h))

        # Write data
        for i, row in enumerate(data_rows):
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                # Right align numbers
                if _to_number(val) is not None:
                    item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
                tbl.setItem(i, j, item)

        # Totals
        sums = [None]*len(headers)
        # Decide which columns to total:
        # For ledger: sum column named "montant"
        # For bilan: sum columns that look numeric except identifier columns
        for j, h in enumerate(headers):
            col_vals = [_to_number(r[j]) for r in data_rows if j < len(r)]
            nums = [v for v in col_vals if v is not None]
            if not nums:
                sums[j] = ""
                continue
            # Heuristic: only total for columns with a numeric header or known names
            if h.lower() in ("montant", "ttc", "encaissé_periode", "encaissé_total_au_to", "restant_au_to", "reste", "total"):
                sums[j] = "{:.2f}".format(sum(nums))
            else:
                # If majority numeric, also sum
                if len(nums) >= max(1, int(0.6*len(data_rows))):
                    sums[j] = "{:.2f}".format(sum(nums))
                else:
                    sums[j] = ""

        total_font = QFont(); total_font.setBold(True)
        total_label = QTableWidgetItem("TOTAL")
        total_label.setFont(total_font)
        tbl.setItem(len(data_rows), 0, total_label)
        for j in range(1, len(headers)):
            it = QTableWidgetItem(str(sums[j] if sums[j] is not None else ""))
            it.setFont(total_font)
            if sums[j] not in ("", None):
                it.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
            tbl.setItem(len(data_rows), j, it)

        tbl.resizeColumnsToContents()

    def load_tables(self):
        try:
            ledger_p = os.path.join(self.tdir, "ledger_read_period.csv")
            bilan_p  = os.path.join(self.tdir, "bilan_read_period.csv")
            ledger = _read_csv_rows(ledger_p) if os.path.exists(ledger_p) else []
            bilan  = _read_csv_rows(bilan_p)  if os.path.exists(bilan_p) else []
            self._fill_table_with_totals(self.tbl_ledger, ledger)
            self._fill_table_with_totals(self.tbl_bilan,  bilan)
        except Exception as e:
            QMessageBox.critical(self, "Chargement", str(e))

    def _make_html_table(self, title, rows):
        if not rows:
            return "<h2>{}</h2><p>(vide)</p>".format(title)
        # Build simple HTML table
        ths = "".join("<th>{}</th>".format(str(h)) for h in rows[0])
        body = []
        # data rows
        for r in rows[1:]:
            tds = "".join("<td style='text-align:{}'>{}</td>".format("right" if _to_number(c) is not None else "left", str(c)) for c in r)
            body.append("<tr>{}</tr>".format(tds))
        # totals row
        # Compute sums like in table
        headers = [str(h) for h in rows[0]]
        sums = [""]*len(headers)
        for j, h in enumerate(headers):
            nums = [_to_number(r[j]) for r in rows[1:] if j < len(r) and _to_number(r[j]) is not None]
            if h.lower() in ("montant", "ttc", "encaissé_periode", "encaissé_total_au_to", "restant_au_to", "reste", "total") and nums:
                sums[j] = "{:.2f}".format(sum(nums))
            elif nums and len(nums) >= max(1, int(0.6*(len(rows)-1))):
                sums[j] = "{:.2f}".format(sum(nums))
        total_tds = ["<td><b>TOTAL</b></td>"] + ["<td style='text-align:right'><b>{}</b></td>".format(s if s else "") for s in sums[1:]]
        body.append("<tr>{}</tr>".format("".join(total_tds)))
        html = """
        <h2 style="margin:0 0 6px 0;">{title}</h2>
        <table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse; font-size:10pt;">
            <thead><tr style="background:#f0f0f0">{ths}</tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """.format(title=title, ths=ths, rows="".join(body))
        return html

    def on_export_pdf(self):
        # Gather rows from both CSVs
        ledger_p = os.path.join(self.tdir, "ledger_read_period.csv")
        bilan_p  = os.path.join(self.tdir, "bilan_read_period.csv")
        ledger = _read_csv_rows(ledger_p) if os.path.exists(ledger_p) else []
        bilan  = _read_csv_rows(bilan_p)  if os.path.exists(bilan_p) else []

        path, _ = QFileDialog.getSaveFileName(self, "Exporter en PDF", os.path.join(self.tdir, "bilan_paiements.pdf"), "PDF (*.pdf)")
        if not path:
            return
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)

            title = "<h1 style='margin:0 0 10px 0;'>Bilan des paiements</h1>"
            sub = "<div style='margin:0 0 12px 0; font-size:10pt;'>Période: {} → {}</div>".format(
                self.de_from.date().toString("yyyy-MM-dd"),
                self.de_to.date().toString("yyyy-MM-dd")
            )
            html = title + sub + self._make_html_table("Ledger (period)", ledger) + "<div style='height:12px'></div>" + self._make_html_table("Bilan (period)", bilan)
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)
        except Exception as e:
            QMessageBox.critical(self, "Export PDF", str(e))
            return
        QMessageBox.information(self, "Export PDF", "PDF créé.")

    def _xml_escape(self, s):
        return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    def _export_sheet_xml(self, name, rows):
        # Build SpreadsheetML (Excel 2003 XML)
        name = "".join(ch if ch.isalnum() or ch in " _-" else "_" for ch in name)[:31] or "Sheet1"
        xml = []
        xml.append('<Worksheet ss:Name="{}">'.format(self._xml_escape(name)))
        xml.append('<Table>')
        for r in rows:
            xml.append('<Row>')
            for c in r:
                n = _to_number(c)
                if n is not None:
                    xml.append('<Cell><Data ss:Type="Number">{}</Data></Cell>'.format("{:.2f}".format(n)))
                else:
                    xml.append('<Cell><Data ss:Type="String">{}</Data></Cell>'.format(self._xml_escape(c)))
            xml.append('</Row>')
        # Add a TOTAL row as in UI if rows non-empty
        if rows:
            headers = [str(h) for h in rows[0]]
            sums = [""]*len(headers)
            for j, h in enumerate(headers):
                nums = [_to_number(r[j]) for r in rows[1:] if j < len(r) and _to_number(r[j]) is not None]
                if h.lower() in ("montant", "ttc", "encaissé_periode", "encaissé_total_au_to", "restant_au_to", "reste", "total") and nums:
                    sums[j] = "{:.2f}".format(sum(nums))
                elif nums and len(nums) >= max(1, int(0.6*(len(rows)-1))):
                    sums[j] = "{:.2f}".format(sum(nums))
            xml.append('<Row>')
            xml.append('<Cell><Data ss:Type="String">TOTAL</Data></Cell>')
            for j in range(1, len(headers)):
                val = sums[j] if sums[j] else ""
                if val:
                    xml.append('<Cell><Data ss:Type="Number">{}</Data></Cell>'.format(val))
                else:
                    xml.append('<Cell><Data ss:Type="String"></Data></Cell>')
            xml.append('</Row>')
        xml.append('</Table>')
        xml.append('</Worksheet>')
        return "\n".join(xml)

    def on_export_xls(self):
        ledger_p = os.path.join(self.tdir, "ledger_read_period.csv")
        bilan_p  = os.path.join(self.tdir, "bilan_read_period.csv")
        ledger = _read_csv_rows(ledger_p) if os.path.exists(ledger_p) else []
        bilan  = _read_csv_rows(bilan_p)  if os.path.exists(bilan_p) else []

        path, _ = QFileDialog.getSaveFileName(self, "Exporter Excel", os.path.join(self.tdir, "bilan_paiements.xls"), "Excel (*.xls *.xml)")
        if not path:
            return
        try:
            wb = []
            wb.append('<?xml version="1.0"?>')
            wb.append('<?mso-application progid="Excel.Sheet"?>')
            wb.append('<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"')
            wb.append(' xmlns:o="urn:schemas-microsoft-com:office:office"')
            wb.append(' xmlns:x="urn:schemas-microsoft-com:office:excel"')
            wb.append(' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">')
            wb.append('<DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">')
            wb.append('<Title>Bilan paiements</Title>')
            wb.append('<Created>{}</Created>'.format(datetime.utcnow().isoformat()))
            wb.append('</DocumentProperties>')
            wb.append('<Styles>')
            wb.append('<Style ss:ID="sHeader"><Font ss:Bold="1"/></Style>')
            wb.append('</Styles>')
            # Sheets
            if ledger:
                wb.append(self._export_sheet_xml("Ledger period", ledger))
            if bilan:
                wb.append(self._export_sheet_xml("Bilan period", bilan))
            wb.append('</Workbook>')
            xml = "\n".join(wb)
            with open(path, "w", encoding="utf-8") as f:
                f.write(xml)
        except Exception as e:
            QMessageBox.critical(self, "Export Excel", str(e))
            return
        QMessageBox.information(self, "Export Excel", "Fichier Excel créé.")

def main():
    app = QApplication(sys.argv)
    w = BilanApp()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
