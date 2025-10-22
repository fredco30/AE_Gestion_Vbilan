class BilanPaiementsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._missing_warned = set()
        self.base_dir = BASE_DIR
        self.data_dir = self._resolve_data_dir()
        self.tdir = os.path.join(self.data_dir, "_t")
        try:
            os.makedirs(self.tdir, exist_ok=True)
        except Exception:
            pass
        root = QVBoxLayout(self)
        try:
            root.setContentsMargins(12, 8, 12, 8)
            root.setSpacing(6)
        except Exception:
            pass
        header = QHBoxLayout()
        header.setSpacing(6)
        root.addLayout(header)
        header.addWidget(QLabel("Du"))
        self.de_from = QDateEdit()
        self.de_from.setCalendarPopup(True)
        self.de_from.setDisplayFormat("yyyy-MM-dd")
        header.addWidget(self.de_from)
        header.addWidget(QLabel("Au"))
        self.de_to = QDateEdit()
        self.de_to.setCalendarPopup(True)
        self.de_to.setDisplayFormat("yyyy-MM-dd")
        header.addWidget(self.de_to)
        try:
            from PyQt5.QtCore import QDate
        except Exception:
            QDate = None
        if QDate is not None:
            try:
                self.de_from.setDate(QDate.currentDate().addMonths(-1))
            except Exception:
                pass
            try:
                self.de_to.setDate(QDate.currentDate())
            except Exception:
                pass
        header.addStretch(1)
        self.btn_generate = QPushButton("Générer")
        header.addWidget(self.btn_generate)
        self.btn_reload = QPushButton("Recharger")
        header.addWidget(self.btn_reload)
        self.btn_open_folder = QPushButton("Ouvrir dossier _t")
        header.addWidget(self.btn_open_folder)
        self.btn_open_ledger = QPushButton("Ouvrir CSV ledger")
        header.addWidget(self.btn_open_ledger)
        self.btn_open_bilan = QPushButton("Ouvrir CSV bilan")
        header.addWidget(self.btn_open_bilan)
        self.btn_export_pdf = QPushButton("Exporter PDF")
        header.addWidget(self.btn_export_pdf)
        self.btn_export_excel = QPushButton("Exporter Excel")
        header.addWidget(self.btn_export_excel)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.tbl_ledger = QTableWidget()
        self.tbl_bilan = QTableWidget()
        self.tabs.addTab(self.tbl_ledger, "Ledger (period)")
        self.tabs.addTab(self.tbl_bilan, "Bilan (period)")
        self._prepare_table(self.tbl_ledger)
        self._prepare_table(self.tbl_bilan)
        self.btn_generate.clicked.connect(self.on_generate)
        self.btn_reload.clicked.connect(self.load_tables)
        self.btn_open_folder.clicked.connect(self.on_open_folder)
        self.btn_open_ledger.clicked.connect(lambda: self.on_open_csv(os.path.join(self.tdir, "ledger_read_period.csv"), "CSV ledger"))
        self.btn_open_bilan.clicked.connect(lambda: self.on_open_csv(os.path.join(self.tdir, "bilan_read_period.csv"), "CSV bilan"))
        self.btn_export_pdf.clicked.connect(self.on_export_pdf)
        self.btn_export_excel.clicked.connect(self.on_export_excel)
        self.load_tables()

    def _resolve_data_dir(self):
        try:
            data = globals().get("DATA_DIR")
            if data:
                return data
        except Exception:
            pass
        return os.path.join(BASE_DIR, "data")

    def _prepare_table(self, table):
        try:
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        except Exception:
            pass
        try:
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
        except Exception:
            pass
        try:
            table.setAlternatingRowColors(True)
        except Exception:
            pass
        try:
            table.verticalHeader().setVisible(False)
        except Exception:
            pass
        try:
            table.setSortingEnabled(False)
        except Exception:
            pass

    def load_tables(self):
        ledger_path = os.path.join(self.tdir, "ledger_read_period.csv")
        bilan_path = os.path.join(self.tdir, "bilan_read_period.csv")
        ledger_rows = self._rows_with_totals(self._load_rows(ledger_path, "Ledger (period)"))
        bilan_rows = self._rows_with_totals(self._load_rows(bilan_path, "Bilan (period)"))
        self._populate_table(self.tbl_ledger, ledger_rows)
        self._populate_table(self.tbl_bilan, bilan_rows)

    def _load_rows(self, path, title):
        if not os.path.exists(path):
            if path not in self._missing_warned:
                self._warn_missing(title, path)
                self._missing_warned.add(path)
            return []
        try:
            return self._read_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, title, str(exc))
            return []

    def _warn_missing(self, title, path):
        QMessageBox.warning(self, title, "Fichier introuvable:\n" + str(path))

    def _read_csv(self, path):
        encodings = ["utf-8-sig", "utf-8", "cp1252"]
        last_error = None
        import csv as _csv
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc, newline="") as handle:
                    reader = _csv.reader(handle)
                    return [row for row in reader]
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        return []

    def _rows_with_totals(self, rows):
        if not rows:
            return []
        headers, data_rows = self._split_rows(rows)
        if not headers:
            return []
        total_row = self._compute_total_row(headers, data_rows)
        result = [headers]
        result.extend(data_rows)
        if total_row:
            result.append(total_row)
        return result

    def _split_rows(self, rows):
        if not rows:
            return [], []
        headers = [str(h) for h in rows[0]]
        data_rows = []
        for row in rows[1:]:
            first = row[0] if row else ""
            if isinstance(first, str) and first.strip().upper() == "TOTAL":
                continue
            data_rows.append(row)
        return headers, data_rows

    def _compute_total_row(self, headers, data_rows):
        if not headers:
            return []
        total = ["TOTAL"] + [""] * max(0, len(headers) - 1)
        known = {"montant", "ttc", "encaissé_periode", "encaissé_total_au_to", "restant_au_to", "reste", "total"}
        for idx in range(1, len(headers)):
            values = []
            for row in data_rows:
                if idx < len(row):
                    num = self._to_number(row[idx])
                    if num is not None:
                        values.append(num)
            if not values:
                continue
            header_low = str(headers[idx]).strip().lower()
            if header_low in known or len(values) >= max(1, int(0.6 * len(data_rows))):
                try:
                    total[idx] = "{:.2f}".format(sum(values))
                except Exception:
                    total[idx] = ""
        return total

    def _to_number(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            try:
                return float(value)
            except Exception:
                return None
        text = str(value).strip()
        if not text:
            return None
        replacements = [("€", ""), ("\u202f", ""), ("\xa0", ""), (" ", "")]
        for old, new in replacements:
            text = text.replace(old, new)
        text = text.replace(",", ".")
        try:
            return float(text)
        except Exception:
            return None

    def _populate_table(self, table, rows):
        table.clear()
        if not rows:
            table.setRowCount(0)
            table.setColumnCount(0)
            return
        headers = rows[0]
        data_rows = rows[1:]
        table.setColumnCount(len(headers))
        table.setRowCount(len(data_rows))
        for col, header in enumerate(headers):
            table.setHorizontalHeaderItem(col, QTableWidgetItem(str(header)))
        total_index = None
        if data_rows:
            last = data_rows[-1][0] if data_rows[-1] else ""
            if isinstance(last, str) and last.strip().upper() == "TOTAL":
                total_index = len(data_rows) - 1
        for row_index, row in enumerate(data_rows):
            for col_index in range(len(headers)):
                value = row[col_index] if col_index < len(row) else ""
                item = QTableWidgetItem(str(value) if value is not None else "")
                if self._to_number(value) is not None:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if total_index is not None and row_index == total_index:
                    try:
                        from PyQt5.QtGui import QFont
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    except Exception:
                        pass
                table.setItem(row_index, col_index, item)
        try:
            table.resizeColumnsToContents()
        except Exception:
            pass

    def on_generate(self):
        du = self.de_from.date().toString("yyyy-MM-dd")
        au = self.de_to.date().toString("yyyy-MM-dd")
        runner = os.path.join(self.base_dir, "run_ledger_dump_plus.py")
        if not os.path.exists(runner):
            self._log_run("missing_script", "", "", du, au)
            QMessageBox.critical(self, "Bilan Paiements", "Script introuvable:\n" + str(runner))
            return
        env = os.environ.copy()
        env["AE_PAUSE"] = "0"
        import subprocess, sys
        try:
            proc = subprocess.run([sys.executable, runner, "--from", du, "--to", au], cwd=self.base_dir, env=env, capture_output=True, text=True)
        except Exception as exc:
            self._log_run("exception", "", str(exc), du, au)
            QMessageBox.critical(self, "Bilan Paiements", str(exc))
            return
        self._log_run(str(proc.returncode), proc.stdout, proc.stderr, du, au)
        if proc.returncode != 0:
            message = proc.stderr or proc.stdout or "Erreur inconnue"
            QMessageBox.critical(self, "Bilan Paiements", message)
            return
        self.load_tables()
        QMessageBox.information(self, "Bilan Paiements", "Génération terminée.")

    def _log_run(self, rc, stdout_text, stderr_text, du, au):
        try:
            from datetime import datetime
            os.makedirs(self.data_dir, exist_ok=True)
            log_path = os.path.join(self.data_dir, "bilan_export.log")
            stamp = datetime.utcnow().isoformat()
            rc_text = str(rc)
            out_text = "" if stdout_text is None else str(stdout_text).strip().replace("\n", "\\n")
            err_text = "" if stderr_text is None else str(stderr_text).strip().replace("\n", "\\n")
            line = "{} rc={} du={} au={} stdout={} stderr={}\n".format(stamp, rc_text, du, au, out_text, err_text)
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(line)
        except Exception:
            pass

    def on_open_folder(self):
        try:
            if not os.path.isdir(self.tdir):
                os.makedirs(self.tdir, exist_ok=True)
            _open_file_async(self.tdir)
        except Exception as exc:
            QMessageBox.critical(self, "Bilan Paiements", str(exc))

    def on_open_csv(self, path, title):
        if not os.path.exists(path):
            QMessageBox.warning(self, title, "Fichier introuvable:\n" + str(path))
            return
        try:
            _open_file_async(path)
        except Exception as exc:
            QMessageBox.critical(self, title, str(exc))

    def on_export_pdf(self):
        ledger_path = os.path.join(self.tdir, "ledger_read_period.csv")
        bilan_path = os.path.join(self.tdir, "bilan_read_period.csv")
        ledger_rows = self._rows_with_totals(self._load_rows(ledger_path, "Ledger (period)"))
        bilan_rows = self._rows_with_totals(self._load_rows(bilan_path, "Bilan (period)"))
        if not ledger_rows and not bilan_rows:
            QMessageBox.warning(self, "Export PDF", "Aucune donnée à exporter.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PDF", os.path.join(self.tdir, "bilan_paiements.pdf"), "PDF (*.pdf)")
        if not path:
            return
        try:
            from PyQt5.QtPrintSupport import QPrinter
            from PyQt5.QtGui import QTextDocument
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            html = self._build_pdf_html(ledger_rows, bilan_rows)
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)
        except Exception as exc:
            QMessageBox.critical(self, "Export PDF", str(exc))
            return
        QMessageBox.information(self, "Export PDF", "PDF créé.")

    def _build_pdf_html(self, ledger_rows, bilan_rows):
        parts = []
        parts.append("<h1 style=\"margin:0 0 10px 0;\">Bilan des paiements</h1>")
        periode = "<div style='margin:0 0 12px 0; font-size:10pt;'>Période: {} → {}</div>".format(
            self.de_from.date().toString("yyyy-MM-dd"),
            self.de_to.date().toString("yyyy-MM-dd")
        )
        parts.append(periode)
        parts.append(self._make_html_table("Ledger (period)", ledger_rows))
        parts.append("<div style='height:12px'></div>")
        parts.append(self._make_html_table("Bilan (period)", bilan_rows))
        return "".join(parts)

    def _make_html_table(self, title, rows):
        if not rows:
            return "<h2>{}</h2><p>(vide)</p>".format(self._escape_html(title))
        header_cells = "".join("<th>{}</th>".format(self._escape_html(h)) for h in rows[0])
        body_rows = []
        for row in rows[1:]:
            cells = []
            for cell in row:
                align = "right" if self._to_number(cell) is not None else "left"
                cells.append("<td style='text-align:{}'>{}</td>".format(align, self._escape_html(cell)))
            body_rows.append("<tr>{}</tr>".format("".join(cells)))
        table_html = "<h2 style=\"margin:0 0 6px 0;\">{}</h2><table border=\"1\" cellspacing=\"0\" cellpadding=\"4\" style=\"border-collapse:collapse; font-size:10pt;\"><thead><tr style=\"background:#f0f0f0\">{}</tr></thead><tbody>{}</tbody></table>".format(
            self._escape_html(title),
            header_cells,
            "".join(body_rows)
        )
        return table_html

    def _escape_html(self, value):
        text = str(value)
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def on_export_excel(self):
        ledger_path = os.path.join(self.tdir, "ledger_read_period.csv")
        bilan_path = os.path.join(self.tdir, "bilan_read_period.csv")
        ledger_rows = self._rows_with_totals(self._load_rows(ledger_path, "Ledger (period)"))
        bilan_rows = self._rows_with_totals(self._load_rows(bilan_path, "Bilan (period)"))
        if not ledger_rows and not bilan_rows:
            QMessageBox.warning(self, "Export Excel", "Aucune donnée à exporter.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter Excel", os.path.join(self.tdir, "bilan_paiements.xls"), "Excel (*.xls *.xml)")
        if not path:
            return
        try:
            workbook = []
            workbook.append("<?xml version=\"1.0\"?>")
            workbook.append("<?mso-application progid=\"Excel.Sheet\"?>")
            workbook.append('<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">')
            from datetime import datetime
            workbook.append('<DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">')
            workbook.append('<Title>Bilan paiements</Title>')
            workbook.append('<Created>{}</Created>'.format(datetime.utcnow().isoformat()))
            workbook.append('</DocumentProperties>')
            workbook.append('<Styles><Style ss:ID="sHeader"><Font ss:Bold="1"/></Style></Styles>')
            if ledger_rows:
                workbook.append(self._export_sheet_xml("Ledger period", ledger_rows))
            if bilan_rows:
                workbook.append(self._export_sheet_xml("Bilan period", bilan_rows))
            workbook.append('</Workbook>')
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(workbook))
        except Exception as exc:
            QMessageBox.critical(self, "Export Excel", str(exc))
            return
        QMessageBox.information(self, "Export Excel", "Fichier Excel créé.")

    def _export_sheet_xml(self, name, rows):
        safe = "".join(ch if ch.isalnum() or ch in " _-" else "_" for ch in str(name))
        safe = (safe[:31] or "Sheet1")
        xml = []
        xml.append('<Worksheet ss:Name="{}">'.format(self._xml_escape(safe)))
        xml.append('<Table>')
        for row in rows:
            xml.append('<Row>')
            for cell in row:
                num = self._to_number(cell)
                if num is not None:
                    xml.append('<Cell><Data ss:Type="Number">{}</Data></Cell>'.format("{:.2f}".format(num)))
                else:
                    xml.append('<Cell><Data ss:Type="String">{}</Data></Cell>'.format(self._xml_escape(cell)))
            xml.append('</Row>')
        xml.append('</Table>')
        xml.append('</Worksheet>')
        return "\n".join(xml)

    def _xml_escape(self, value):
        text = str(value)
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


        suivi_tab = SuiviFinancierTab(self.settings, self)
        tabs.addTab(suivi_tab, "Suivi financier")
        try:
            self.suivi_financier_tab = suivi_tab
        except Exception:
            pass
        bilan_tab = BilanPaiementsTab(parent=self)
        try:
            index_sf = tabs.indexOf(suivi_tab)
            if index_sf >= 0:
                tabs.insertTab(index_sf + 1, bilan_tab, "Bilan Paiements")
            else:
                tabs.addTab(bilan_tab, "Bilan Paiements")
        except Exception:
            tabs.addTab(bilan_tab, "Bilan Paiements")
        try:
            self.bilan_paiements_tab = bilan_tab
        except Exception:
            pass
        suivi_tab = SuiviFinancierTab(self.settings, self)
        tabs.addTab(suivi_tab, "Suivi financier")
        try:
            self.suivi_financier_tab = suivi_tab
        except Exception:
            pass
        bilan_tab = BilanPaiementsTab(parent=self)
        try:
            index_sf = tabs.indexOf(suivi_tab)
            if index_sf >= 0:
                tabs.insertTab(index_sf + 1, bilan_tab, "Bilan Paiements")
            else:
                tabs.addTab(bilan_tab, "Bilan Paiements")
        except Exception:
            tabs.addTab(bilan_tab, "Bilan Paiements")
        try:
            self.bilan_paiements_tab = bilan_tab
        except Exception:
            pass
