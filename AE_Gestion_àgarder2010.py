    "rg_enabled":"rg_enabled",
    "rg_rate":"rg_rate",
    "rg_total_operation":"rg_total_operation",
    "reception_date":"reception_date",
    "dgd_reminder_days":"dgd_reminder_days",
    "rg_liberee":"rg_liberee",
    "rg_liberee_date":"rg_liberee_date",
    "show_rg_line":"show_rg_line",
    "rg_note":"rg_note",
    "rg_remaining_ttc":"rg_remaining_ttc",
        try:
            entry["rg_present_ttc"] = _safe_float(row.get("rg_present_ttc", 0.0), 0.0)
        except Exception:
            entry["rg_present_ttc"] = 0.0
        try:
            entry["rg_rate"] = _safe_float(row.get("rg_rate", row.get("retenue_garantie_pct", 0.0)), 0.0)
        except Exception:
            entry["rg_rate"] = 0.0
        try:
            entry["rg_total_operation"] = _safe_float(row.get("rg_total_operation", 0.0), 0.0)
        except Exception:
            entry["rg_total_operation"] = 0.0
        entry["rg_enabled"] = _p_bool(row.get("rg_enabled"), default=entry.get("rg_rate", 0.0) > 0.0)
        entry["rg_liberee"] = _p_bool(row.get("rg_liberee"), default=False)
            if is_situ:
                contrat_total = _safe_float(r.get("contrat_total_ttc", ttc))
                net_cumul = _safe_float(r.get("situation_cumul_ttc", present))
                rg_total = _safe_float(r.get("rg_total_operation", 0.0))
                rg_enabled = _p_bool(r.get("rg_enabled"), default=_safe_float(r.get("rg_rate", r.get("retenue_garantie_pct", 0.0)), 0.0) > 0.0)
                net_total = max(contrat_total - (rg_total if rg_enabled else 0.0), 0.0)
                restant = max(net_total - net_cumul, 0.0)
            else:
                restant = max(ttc - pay_sum, 0.0)
    "rg_enabled", "rg_rate", "rg_total_operation", "reception_date",
    "dgd_reminder_days", "rg_liberee", "rg_liberee_date",
    "show_rg_line", "rg_note", "rg_remaining_ttc",
def _p_bool(value, default=False):
    try:
        if isinstance(value, bool):
            return value
        if value is None:
            return bool(default)
        s = str(value).strip().lower()
        if s in {"1", "true", "yes", "on", "oui", "y"}:
            return True
        if s in {"0", "false", "no", "off", "non", ""}:
            return False
    except Exception:
        pass
    return bool(default)

def _p_add_days(iso: str, days: int) -> str:
    try:
        from datetime import datetime, timedelta
        if not iso:
            return ""
        dt = datetime.strptime(str(iso), "%Y-%m-%d")
        return (dt + timedelta(days=int(days))).strftime("%Y-%m-%d")
    except Exception:
        return ""

    raw_prev = _p_safe_float(doc.get("situation_prev_ttc"), 0.0)
    raw_cumul = _p_safe_float(doc.get("situation_cumul_ttc"), 0.0)

    legacy_pct = _p_safe_float(doc.get("retenue_garantie_pct"), 0.0)
    rate = _p_safe_float(doc.get("rg_rate"), legacy_pct)
    rg_enabled = _p_bool(doc.get("rg_enabled"), default=rate > 0.0)

    reception_iso = _p_date_iso(doc.get("reception_date") or doc.get("pv_reception_date_iso") or "")
    pv_iso = _p_date_iso(doc.get("pv_reception_date_iso") or doc.get("reception_date") or "")
    reminder_days = int(_p_safe_float(doc.get("dgd_reminder_days"), 0))
    release_flag = _p_bool(doc.get("rg_liberee"), default=False)
    release_iso = _p_date_iso(doc.get("rg_liberee_date") or "")
    deja_hist = 0.0
    hist_withheld = 0.0
    hist_released = 0.0
        deja_hist += _p_safe_float(e.get("amount"), 0.0)
        amt_rg = _p_safe_float(e.get("rg_present_ttc"), 0.0)
        if amt_rg >= 0.0:
            hist_withheld += amt_rg
        else:
            hist_released += abs(amt_rg)

    deja = max(deja_hist, raw_prev)
    cumul = max(deja + current, raw_cumul if raw_cumul > 0.0 else 0.0)
    if base_total <= 0 and cumul > 0:
        base_total = cumul

    rg_total = _p_safe_float(doc.get("rg_total_operation"), None)
    if rg_total is None or rg_total < 0:
        if rg_enabled and rate > 0 and base_total > 0:
            rg_total = base_total * (rate / 100.0)
        else:
            rg_total = 0.0
    if base_total > 0:
        rg_total = max(0.0, min(rg_total, base_total))
    else:
        rg_total = max(rg_total, 0.0)

    net_before = max(hist_withheld - hist_released, 0.0)

    rg_present = 0.0
    if rg_enabled:
        if release_flag:
            rg_present = -min(net_before, rg_total)
        else:
            raw_rg = max(current, 0.0) * (rate / 100.0)
            rg_present = min(max(raw_rg, 0.0), max(rg_total - net_before, 0.0))
    net_after = max(net_before + rg_present, 0.0)
    net_total = max(base_total - (rg_total if rg_enabled else 0.0), 0.0)
    reste = max(0.0, net_total - cumul)
    if net_total > 0:
        pct = 100.0 * (cumul / net_total)

    if release_flag:
        rg_due = release_iso or pv_iso or reception_iso
    else:
        if reminder_days > 0 and reception_iso:
            rg_due = _p_add_days(reception_iso, reminder_days)
        elif pv_months > 0 and reception_iso:
            rg_due = _p_add_months(reception_iso, pv_months)
        elif pv_months > 0 and pv_iso:
            rg_due = _p_add_months(pv_iso, pv_months)
        else:
            rg_due = pv_iso or reception_iso
        "op_net_total_ttc": net_total,
        "rg_total_operation": rg_total,
        "rg_remaining_ttc": max(rg_total - net_after, 0.0),
        initial = getattr(self, "initial_values", {}) or {}

        self.chk_rg_enabled = QCheckBox("Activer la retenue de garantie")
        default_rate = _p_safe_float(initial.get("rg_rate", initial.get("retenue_garantie_pct", 0.0)), 0.0)
        self.chk_rg_enabled.setChecked(_p_bool(initial.get("rg_enabled"), default=default_rate > 0.0))

        if default_rate <= 0.0:
            default_rate = 5.0 if self.chk_rg_enabled.isChecked() else 0.0
        self.sp_rg_pct.setValue(default_rate)

        self.lbl_rg_total = QLabel("RG totale opération : 0,00 €")
        self.lbl_rg_amt = QLabel("RG retenue : 0,00 €")
        self.de_reception = QDateEdit(); self.de_reception.setCalendarPopup(True)
        rec_iso = _p_date_iso(initial.get("reception_date") or initial.get("pv_reception_date_iso") or "")
        if rec_iso:
            try:
                y,m,d = [int(x) for x in rec_iso.split("-")]
                self.de_reception.setDate(QDate(y,m,d))
            except Exception:
                self.de_reception.setDate(QDate.currentDate())
        else:
            self.de_reception.setDate(QDate.currentDate())

        self.sp_dgd_days = QDoubleSpinBox(); self.sp_dgd_days.setSuffix(" j"); self.sp_dgd_days.setRange(0.0, 720.0); self.sp_dgd_days.setDecimals(0)
        default_days = int(_p_safe_float(initial.get("dgd_reminder_days"), 0))
        if default_days <= 0:
            legacy_months = int(_p_safe_float(initial.get("pv_rg_months"), 0))
            if legacy_months > 0:
                default_days = legacy_months * 30
        self.sp_dgd_days.setValue(default_days)
        self.lbl_rg_due = QLabel("Échéance / rappel RG : —")

        self.chk_rg_release = QCheckBox("Libérer la retenue (DGD)")
        self.chk_rg_release.setChecked(_p_bool(initial.get("rg_liberee"), default=False))
        self.de_rg_release = QDateEdit(); self.de_rg_release.setCalendarPopup(True)
        release_iso = _p_date_iso(initial.get("rg_liberee_date") or "")
        if release_iso:
            try:
                y,m,d = [int(x) for x in release_iso.split("-")]
                self.de_rg_release.setDate(QDate(y,m,d))
            except Exception:
                self.de_rg_release.setDate(QDate.currentDate())
            self.de_rg_release.setDate(QDate.currentDate())

        self.chk_show_line = QCheckBox("Afficher la ligne RG sur la facture")
        self.chk_show_line.setChecked(_p_bool(initial.get("show_rg_line"), default=True))

        self.ed_rg_note = QLineEdit(str(initial.get("rg_note") or ""))
        self.chk_reverse.setChecked(_p_bool(initial.get("situ_reverse_charge"), default=False))
        self.ed_reverse_mention = QLineEdit(initial.get(
        grid.addWidget(self.chk_rg_enabled, r,0,1,2); r += 1
        grid.addWidget(QLabel("Taux RG"), r,0); grid.addWidget(self.sp_rg_pct, r,1); r += 1
        grid.addWidget(self.lbl_rg_total, r,0,1,2); r += 1
        grid.addWidget(QLabel("Date de réception"), r,0); grid.addWidget(self.de_reception, r,1); r += 1
        grid.addWidget(QLabel("Rappel DGD (jours)"), r,0); grid.addWidget(self.sp_dgd_days, r,1); r += 1
        grid.addWidget(self.chk_rg_release, r,0,1,2); r += 1
        grid.addWidget(QLabel("Date libération RG"), r,0); grid.addWidget(self.de_rg_release, r,1); r += 1
        grid.addWidget(self.chk_show_line, r,0,1,2); r += 1
        grid.addWidget(QLabel("Note RG"), r,0); grid.addWidget(self.ed_rg_note, r,1); r += 1
        def _collect_preview_doc():
                current = _p_safe_float((getattr(self, "doc", {}) or {}).get("situation_current_ttc"), 0.0)
            try:
                base = float(self.sp_base.value()) if hasattr(self, "sp_base") else _p_safe_float(initial.get("contrat_total_ttc"), 0.0)
            except Exception:
                base = _p_safe_float(initial.get("contrat_total_ttc"), 0.0)
            try:
                prev = float(self.sp_prev.value()) if hasattr(self, "sp_prev") else _p_safe_float(initial.get("situation_prev_ttc"), 0.0)
            except Exception:
                prev = _p_safe_float(initial.get("situation_prev_ttc"), 0.0)
            try:
                cumul = float(self.sp_cumul.value()) if hasattr(self, "sp_cumul") else _p_safe_float(initial.get("situation_cumul_ttc"), 0.0)
            except Exception:
                cumul = _p_safe_float(initial.get("situation_cumul_ttc"), 0.0)

            try:
                qd = self.de_reception.date()
                rec_iso = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"
            except Exception:
                rec_iso = ""
            try:
                qr = self.de_rg_release.date()
                rel_iso = f"{qr.year():04d}-{qr.month():02d}-{qr.day():02d}"
            except Exception:
                rel_iso = ""

            preview = dict(getattr(self, "doc", {}) or {})
            preview.update({
                "contrat_total_ttc": base,
                "situation_current_ttc": current,
                "situation_prev_ttc": prev,
                "situation_cumul_ttc": cumul,
                "rg_rate": self.sp_rg_pct.value(),
                "rg_enabled": self.chk_rg_enabled.isChecked(),
                "rg_liberee": self.chk_rg_release.isChecked(),
                "rg_liberee_date": rel_iso if self.chk_rg_release.isChecked() else "",
                "reception_date": rec_iso,
                "pv_reception_date_iso": rec_iso,
                "dgd_reminder_days": int(self.sp_dgd_days.value()),
                "pv_rg_months": int(_p_safe_float(initial.get("pv_rg_months"), 0)),
                "show_rg_line": self.chk_show_line.isChecked(),
                "rg_note": self.ed_rg_note.text().strip(),
            })
            return preview

        def _sync_release_state():
            rel_enabled = self.chk_rg_enabled.isChecked() and self.chk_rg_release.isChecked()
            try:
                self.de_rg_release.setEnabled(rel_enabled)
            except Exception:
                pass

        def _sync_rg_enabled():
            enabled = self.chk_rg_enabled.isChecked()
            for widget in (
                self.sp_rg_pct,
                self.de_reception,
                self.sp_dgd_days,
                self.chk_rg_release,
                self.de_rg_release,
                self.chk_show_line,
                self.ed_rg_note,
            ):
                try:
                    widget.setEnabled(enabled)
                except Exception:
                    pass
            if not enabled:
                try: self.chk_rg_release.setChecked(False)
                except Exception: pass
            _sync_release_state()
        def _recalc_labels():
            preview = _collect_preview_doc()
            res = {}
            try:
                res = compute_situation_amounts(preview)
            except Exception:
                res = {}
            total_rg = _p_safe_float(res.get("rg_total_operation"), _p_safe_float(preview.get("rg_total_operation"), 0.0))
            self.lbl_rg_total.setText("RG totale opération : " + _p_fmt_eur(total_rg))
            amt = _p_safe_float(res.get("rg_present_ttc"), 0.0)
            lbl_prefix = "RG libérée : " if amt < 0 else "RG retenue : "
            self.lbl_rg_amt.setText(lbl_prefix + _p_fmt_eur(abs(amt)))
            a_reg = _p_safe_float(res.get("a_regler_ttc"), preview.get("a_regler_ttc", 0.0))
            due = res.get("rg_due_date_iso") or ""
            self.lbl_rg_due.setText("Échéance / rappel RG : " + (due or "—"))
            remaining = res.get("rg_remaining_ttc")
            if remaining is not None:
                self.lbl_rg_total.setToolTip("RG restante : " + _p_fmt_eur(remaining))
            else:
                self.lbl_rg_total.setToolTip("")
        except Exception:
            pass
        try:
            self.sp_prev.valueChanged.connect(_recalc_labels)
        except Exception:
            pass
        try:
            self.sp_base.valueChanged.connect(_recalc_labels)
        except Exception:
            pass
        try:
            self.sp_cumul.valueChanged.connect(_recalc_labels)
        except Exception:
            pass
        except Exception:
            pass
            self.de_reception.dateChanged.connect(_recalc_labels)
        except Exception:
            pass
            self.sp_dgd_days.valueChanged.connect(_recalc_labels)
        except Exception:
            pass
        try:
            self.chk_rg_enabled.toggled.connect(lambda *_: (_sync_rg_enabled(), _recalc_labels()))
        except Exception:
            pass
        try:
            self.chk_rg_release.toggled.connect(lambda *_: (_sync_release_state(), _recalc_labels()))
        except Exception:
            pass
        try:
            self.de_rg_release.dateChanged.connect(_recalc_labels)
        except Exception:
            pass

        _sync_rg_enabled()
            qd = self.de_reception.date() if hasattr(self, "de_reception") else QDate.currentDate()
            rec_iso = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"
        except Exception:
            rec_iso = _p_date_iso(data.get("reception_date") or data.get("pv_reception_date_iso") or "")
        try:
            from PyQt5.QtCore import QDate
            qr = self.de_rg_release.date() if hasattr(self, "de_rg_release") else QDate.currentDate()
            rel_iso = f"{qr.year():04d}-{qr.month():02d}-{qr.day():02d}"
        except Exception:
            rel_iso = _p_date_iso(data.get("rg_liberee_date") or "")

        pct_rg = _p_safe_float(getattr(self, "sp_rg_pct", None).value() if hasattr(self,"sp_rg_pct") else data.get("rg_rate", data.get("retenue_garantie_pct", 0.0)), 0.0)
        enabled = _p_bool(getattr(self, "chk_rg_enabled", None).isChecked() if hasattr(self,"chk_rg_enabled") else data.get("rg_enabled"), default=pct_rg > 0.0)
        release_flag = _p_bool(getattr(self, "chk_rg_release", None).isChecked() if hasattr(self,"chk_rg_release") else data.get("rg_liberee"), default=False)
        days = int(_p_safe_float(getattr(self, "sp_dgd_days", None).value() if hasattr(self,"sp_dgd_days") else data.get("dgd_reminder_days", 0), 0))
        months = int(_p_safe_float(data.get("pv_rg_months"), 0))
        if days > 0:
            try:
                months = max(0, int(round(float(days) / 30.0)))
            except Exception:
                pass

        try:
            base = float(self.sp_base.value()) if hasattr(self, "sp_base") else _p_safe_float(data.get("contrat_total_ttc"), 0.0)
        except Exception:
            base = _p_safe_float(data.get("contrat_total_ttc"), 0.0)
        try:
            current = float(self.sp_current.value()) if hasattr(self, "sp_current") else _p_safe_float(data.get("situation_current_ttc"), 0.0)
        except Exception:
            current = _p_safe_float(data.get("situation_current_ttc"), 0.0)
        try:
            prev = float(self.sp_prev.value()) if hasattr(self, "sp_prev") else _p_safe_float(data.get("situation_prev_ttc"), 0.0)
        except Exception:
            prev = _p_safe_float(data.get("situation_prev_ttc"), 0.0)
        try:
            cumul = float(self.sp_cumul.value()) if hasattr(self, "sp_cumul") else _p_safe_float(data.get("situation_cumul_ttc"), 0.0)
            cumul = _p_safe_float(data.get("situation_cumul_ttc"), 0.0)

        tmp.update({
            "contrat_total_ttc": base,
            "situation_current_ttc": current,
            "situation_prev_ttc": prev,
            "situation_cumul_ttc": cumul,
            "rg_rate": pct_rg,
            "rg_enabled": enabled,
            "rg_liberee": release_flag,
            "rg_liberee_date": rel_iso if release_flag else "",
            "reception_date": rec_iso,
            "pv_reception_date_iso": rec_iso,
            "dgd_reminder_days": days,
            "pv_rg_months": months,
            "show_rg_line": _p_bool(getattr(self, "chk_show_line", None).isChecked() if hasattr(self,"chk_show_line") else data.get("show_rg_line"), default=True),
            "rg_note": getattr(self, "ed_rg_note", None).text().strip() if hasattr(self,"ed_rg_note") else data.get("rg_note", ""),
        })
            "rg_rate": pct_rg,
            "rg_enabled": enabled,
            "rg_total_operation": res.get("rg_total_operation", 0.0),
            "rg_remaining_ttc": res.get("rg_remaining_ttc", 0.0),
            "reception_date": rec_iso,
            "pv_reception_date_iso": rec_iso,
            "dgd_reminder_days": days,
            "rg_liberee": release_flag,
            "rg_liberee_date": rel_iso if release_flag else "",
            "rg_note": getattr(self, "ed_rg_note", None).text().strip() if hasattr(self,"ed_rg_note") else data.get("rg_note", ""),
            "show_rg_line": _p_bool(getattr(self, "chk_show_line", None).isChecked() if hasattr(self,"chk_show_line") else data.get("show_rg_line"), default=True),
            _fsd_init_patched(self, *a, **kw)
            if _orig_FSD_init:
                _orig_FSD_init(self, *a, **kw)
        if callable(_orig_FSD_get_payload):
            FactureSituationDialog.get_payload = _fsd_payload_patched
