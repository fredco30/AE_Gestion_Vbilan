#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_ledger_dump_plus.py — lecture seule
SITU dédoublonné par numéro enfant (child_doc). PDF scan pour mapper les enfants.

Sorties: data/_t/ledger_read.csv, data/_t/bilan_read.csv, data/_t/ledger_read.jsonl, data/_t/ledger_dump_plus.log
Options: --pause  --log <path>
"""
import os, sys, csv, re, logging, importlib.util, datetime as dt

DEF_DIR   = os.path.join("data","_t")
DEF_LEDGER= os.path.join(DEF_DIR, "ledger_read.csv")
DEF_BILAN = os.path.join(DEF_DIR, "bilan_read.csv")
DEF_JSONL = os.path.join(DEF_DIR, "ledger_read.jsonl")
DEF_LOG   = os.path.join(DEF_DIR, "ledger_dump_plus.log")

def _parse_args(argv):
    ledger=DEF_LEDGER; bilan=DEF_BILAN; jsonl=DEF_JSONL; logp=DEF_LOG; pause=False; dfrom=None; dto=None
    pos=[]; i=0
    while i<len(argv):
        a=argv[i]
        if a=="--log" and i+1<len(argv): logp=argv[i+1]; i+=2; continue
        if a=="--pause": pause=True; i+=1; continue
        if a=="--from" and i+1<len(argv): dfrom=argv[i+1]; i+=2; continue
        if a=="--to" and i+1<len(argv): dto=argv[i+1]; i+=2; continue
        pos.append(a); i+=1
    if len(pos)>=1: ledger=pos[0]
    if len(pos)>=2: bilan =pos[1]
    if len(pos)>=3: jsonl =pos[2]
    return ledger,bilan,jsonl,logp,pause,dfrom,dto

def _ensure_dirs(*paths):
    for p in paths:
        d=os.path.dirname(p)
        if d: os.makedirs(d, exist_ok=True)

def _setup_logging(log_path):
    _ensure_dirs(log_path)
    fmt="%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ])
    logging.info("log_path=%s", log_path)

def _load_app():
    here = os.path.abspath(os.path.dirname(__file__))
    for name in ["AE_Gestion_àgarder2010.py", "AE_Gestion_2010.py", "AE_Gestion.py"]:
        path = os.path.join(here, name)
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location("ae_gestion_app", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            logging.info("App loaded: %s", path)
            return mod
    raise FileNotFoundError("AE_Gestion module not found next to this script.")

def _to_float(x):
    if x is None: return 0.0
    if isinstance(x,(int,float)): return float(x)
    s=str(x).strip().replace('\xa0','').replace(' ','')
    if s.count(',')==1 and s.count('.')==0: s=s.replace(',','.')
    s=re.sub(r'[^0-9\.\-]','',s)
    try: return float(s) if s else 0.0
    except: return 0.0

def _to_bool(x):
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    s = str(x).strip().lower()
    if s in ("1","true","yes","on","oui","y"):
        return True
    if s in ("0","false","no","off","non",""):
        return False
    return False

RG_COLUMNS = [
    "rg_enabled", "rg_rate", "rg_total_operation", "rg_present_ttc",
    "rg_due_date_iso", "reception_date", "dgd_reminder_days",
    "rg_liberee", "rg_liberee_date", "show_rg_line", "rg_note",
    "rg_remaining_ttc",
]

def _fmt_float(val):
    try:
        f = float(val)
    except Exception:
        return ""
    return f"{f:.2f}"

def _first(doc, names, default=None):
    for n in names:
        for k in (n,n.lower(),n.upper(),n.title()):
            if isinstance(doc, dict) and k in doc and doc[k] not in (None,""):
                return doc[k]
    return default

def _maybe_iso(d):
    if not d: return ""
    s=str(d).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}",s): return s[:10]
    m=re.match(r"^(\d{1,2})[\/\.](\d{1,2})[\/\.](\d{4})$",s)
    if m:
        dd,mm,yyyy=m.groups()
        try: return dt.date(int(yyyy),int(mm),int(dd)).isoformat()
        except: return s
    m=re.match(r"^(\d{4})(\d{2})(\d{2})$",s)
    if m:
        y,m_,d=m.groups()
        try: return dt.date(int(y),int(m_),int(d)).isoformat()
        except: return s
    return s


def _in_range(d, dfrom, dto):
    if not dfrom and not dto: return True
    if not d: return False
    s = _maybe_iso(d)
    try:
        if dfrom and s < dfrom: return False
        if dto and s > dto: return False
        return True
    except Exception:
        return False


def _is_situation(doc, ctx):
    if isinstance(ctx, dict) and ctx.get("is_situation") is not None:
        return bool(ctx.get("is_situation"))
    t=(_first(doc,["type","doctype","doc_type"],"") or "").lower()
    if "situ" in t: return True
    label=(_first(doc,["label","intitule","titre"],"") or "").lower()
    if "situation" in label: return True
    return False

def _parse_payments_from_doc(doc):
    for key in ["journal_paiements","paiements","payments","encaissements","reglements","regl"]:
        v=doc.get(key)
        if isinstance(v,list) and v and isinstance(v[0],dict):
            return v
    return []

def _doc_date_for_payment(doc):
    return (_first(doc,["date_statut","date_status","date_paiement","date_reglement","date"]) or "")

def _extract_simple_invoice_payments(doc,total_ttc):
    rows=[]
    acompte_amt=_to_float(_first(doc,["acompte_montant","montant_acompte","deposit_amount","advance_amount","acompte"]))
    acompte_date=_first(doc,["acompte_date","date_acompte","deposit_date"])
    acompte_mode=_first(doc,["acompte_mode","mode_acompte","deposit_mode","mode_paiement_acompte","mode","mode_paiement","moyen_paiement"])
    final_amt=_to_float(_first(doc,["final_montant","montant_final","solde_montant","balance_amount","solde","balance"]))
    final_date=_first(doc,["final_date","date_finale","date_solde","balance_date"])
    final_mode=_first(doc,["final_mode","mode_final","mode_solde","balance_mode","mode_paiement_final","mode","mode_paiement","moyen_paiement"])
    fallback=acompte_date or final_date or _doc_date_for_payment(doc)
    if acompte_amt>0:
        label="final" if abs(acompte_amt-(total_ttc or 0.0))<0.01 else "acompte"
        rows.append({"date":_maybe_iso(acompte_date or fallback),"montant":acompte_amt,"mode":acompte_mode or "","label":label})
    if final_amt>0:
        rows.append({"date":_maybe_iso(final_date or fallback),"montant":final_amt,"mode":final_mode or "","label":"final"})
    for base in ["reglement","paiement","versement"]:
        for i in range(1,8):
            d=_first(doc,[f"{base}{i}_date",f"date_{base}{i}"])
            m=_to_float(_first(doc,[f"{base}{i}_montant",f"montant_{base}{i}"]))
            mo=_first(doc,[f"{base}{i}_mode",f"mode_{base}{i}"])
            if m>0: rows.append({"date":_maybe_iso(d or fallback),"montant":m,"mode":mo or "","label":"partiel"})
    return rows

def _normalize_label(label,is_situ):
    s=(label or "").strip().lower()
    if is_situ: return "situation"
    if s in ("final","solde","balance"): return "final"
    if "part" in s or "partial" in s or "partiel" in s: return "partiel"
    if "acompte" in s: return "acompte"
    if "situation" in s or "situ" in s: return "situation"
    return s or "partiel"

def _match_num(row):
    for k,v in row.items():
        kk=(k or "").lower()
        if kk in ("doc_numero","numero","numéro","facture","ref","facture_numero"):
            if v: return str(v).strip()
    return ""

def _csv_signals_is_situ(app, numero):
    reasons=[]
    facts_path=os.path.join(app.DATA_DIR, getattr(app,"CSV_FACTS","data_factures.csv"))
    try:
        if os.path.exists(facts_path):
            with open(facts_path,"r",encoding="utf-8",newline="") as f:
                r=csv.DictReader(f)
                for row in r:
                    if _match_num(row)==numero:
                        any_situ=any((k.lower().startswith("situation_") and str(v).strip()!="") for k,v in row.items())
                        if any_situ: reasons.append("facts:situation_*")
                        vcount=row.get("situation_total_count") or row.get("SITUATION_TOTAL_COUNT")
                        try:
                            if vcount and int(str(vcount).strip())>0: reasons.append("facts:situation_total_count>0")
                        except: pass
                        vindex=row.get("situation_index") or row.get("SITUATION_INDEX")
                        if vindex and str(vindex).strip()!="": reasons.append("facts:situation_index")
                        break
    except Exception as e:
        logging.warning("facts scan failed: %s", e)
    pays_path=os.path.join(app.DATA_DIR,"data_paiements.csv")
    try:
        if os.path.exists(pays_path):
            with open(pays_path,"r",encoding="utf-8",newline="") as f:
                r=csv.DictReader(f)
                for row in r:
                    if _match_num(row)==numero:
                        if (row.get("situation_index") and str(row.get("situation_index")).strip()!=""):
                            reasons.append("pays:situation_index")
                        if (row.get("parent_key") and str(row.get("parent_key")).strip()!=""):
                            reasons.append("pays:parent_key")
    except Exception as e:
        logging.warning("payments scan failed: %s", e)
    return (len(reasons)>0), reasons

def _build_child_maps(app):
    facts_path=os.path.join(app.DATA_DIR, getattr(app,"CSV_FACTS","data_factures.csv"))
    parent_to_children={}
    child_to_parent={}
    if os.path.exists(facts_path):
        with open(facts_path,"r",encoding="utf-8",newline="") as f:
            r=csv.DictReader(f)
            for row in r:
                num=_match_num(row)
                if not num: continue
                m=re.match(r"^(.*)-(\d{2,})$", num)
                if m:
                    parent=m.group(1); idx=int(m.group(2))
                    child_to_parent[num]=parent
                    parent_to_children.setdefault(parent, {})[idx]=num
    return parent_to_children, child_to_parent

def _scan_pdf_children(app):
    base = getattr(app, "DATA_DIR", ".")
    root = os.path.join(base, "ops")
    mapping = {}
    if not os.path.exists(root):
        return mapping
    pat = re.compile(r"^(F\d{4}-\d{3,})-(\d{2})_fx(?:_.+)?\.pdf$", re.IGNORECASE)
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith(".pdf"):
                continue
            m = pat.match(fn)
            if not m:
                continue
            parent = m.group(1)
            idx = int(m.group(2))
            child = f"{parent}-{idx:02d}"
            mapping.setdefault(parent, {})[idx] = child
    return mapping

def _infer_child_doc(parent_num, kv, parent_children):
    for k in ["child_doc","facture_situation","situation_numero","numero_situation","doc_child","child","numero_enfant"]:
        v=kv.get(k) if isinstance(kv, dict) else None
        if v and str(v).strip(): return str(v).strip()
    idx_str=None
    for k in ["situation_index","index","etape","phase","rang"]:
        v=kv.get(k) if isinstance(kv, dict) else None
        if v and str(v).strip():
            idx_str=str(v).strip()
            break
    if idx_str:
        try:
            i=int(re.sub(r"[^0-9]","", idx_str))
            if parent_num in parent_children and i in parent_children[parent_num]:
                return parent_children[parent_num][i]
            return f"{parent_num}-{i:02d}"
        except: pass
    return ""

def _load_external_payments_csv(app, parent_children):
    candidates=["payments.csv","data_paiements.csv","journal_paiements.csv"]
    rows=[]
    for name in candidates:
        p=os.path.join(app.DATA_DIR, name)
        if os.path.exists(p):
            logging.info("Reading external payments: %s", p)
            with open(p,"r",encoding="utf-8",newline="") as f:
                r=csv.DictReader(f)
                row_idx=0
                for row in r:
                    row_idx+=1
                    kv={ (k or "").strip().lower(): v for k,v in row.items() }
                    numero=kv.get("doc_numero") or kv.get("numero") or kv.get("facture") or kv.get("ref") or kv.get("facture_numero")
                    date =kv.get("date") or kv.get("jour") or kv.get("date_paiement")
                    montant=_to_float(kv.get("montant") or kv.get("amount") or kv.get("ttc"))
                    mode =kv.get("mode") or kv.get("moyen")
                    label=kv.get("label") or kv.get("type") or kv.get("libelle") or kv.get("libellé")
                    child=_infer_child_doc(str(numero).strip(), kv, parent_children) if numero else ""
                    if numero and montant>0:
                        rows.append({"doc_numero":str(numero).strip(),"date":_maybe_iso(date),"montant":montant,"mode":mode or "","label":label or "","child_doc":child,"src":f"ext:{os.path.basename(p)}:{row_idx}"})
    return rows

def main(argv=None):
    argv=argv or sys.argv[1:]
    ledger_csv,bilan_csv,jsonl_path,log_path,pause,dfrom,dto=_parse_args(argv)
    _ensure_dirs(ledger_csv,bilan_csv,jsonl_path,log_path)
    _setup_logging(log_path)
    os.environ["AE_SITU_TEST_LOG"]=jsonl_path

    app=_load_app()
    settings=app.ensure_settings()
    logging.info("DATA_DIR=%s", getattr(app,"DATA_DIR","?"))

    facts_path=os.path.join(app.DATA_DIR, app.CSV_FACTS)
    facts=app.load_csv(facts_path) if os.path.exists(facts_path) else []
    if not isinstance(facts,list):
        logging.warning("facts is not a list: %r", type(facts)); facts=[]
    logging.info("facts_count=%d", len(facts))

    parent_children, child_parent = _build_child_maps(app)
    # Augment with PDF scan
    pdf_map = _scan_pdf_children(app)
    for p, d in pdf_map.items():
        pc = parent_children.setdefault(p, {})
        for idx, child in d.items():
            if idx not in pc:
                pc[idx] = child
                try: app.log_action('childdoc_map_add', f'{p} idx={idx} child={child} source=pdfscan')
                except Exception: pass

    entries={}   # numero -> list of {date, montant, mode, label, child_doc, src}
    meta={}      # numero -> {type, client, ttc}
    is_situ_map={}
    flags_map={}

    def add(numero,is_situ,client,date,montant,mode,label,child_doc,src):
        entries.setdefault(numero,[]).append({
            "date":_maybe_iso(date),
            "montant":float(_to_float(montant)),
            "mode":mode or "",
            "label":_normalize_label(label,is_situ),
            "child_doc":child_doc or "",
            "src":src or "",
        })

    # Collect from facts
    for row in facts:
        numero=str(row.get("numero","") or row.get("numéro","") or row.get("doc_numero","") or row.get("facture","") or "").strip()
        if not numero: continue
        try: doc=app.assemble_doc("facture", numero)
        except Exception as e: logging.exception("assemble_doc %s", numero); continue
        try: ctx=app.build_situation_payment_context(doc, settings=settings)
        except Exception as e: logging.exception("context %s", numero); ctx={}

        is_situ=_is_situation(doc, ctx); is_situ_map[numero]=is_situ
        client=_first(doc,["client_nom","client","customer","client_name","raison_sociale"],"")
        total_ttc=_to_float(_first(doc,["total_ttc","montant_ttc","ttc_total","ttc"],0.0))
        meta[numero]={"type":"SITU" if is_situ else "SIMPLE","client":client,"ttc":total_ttc}

        rg_calc={}
        if hasattr(app, "compute_situation_amounts"):
            try:
                rg_calc = app.compute_situation_amounts(dict(doc))  # type: ignore
            except Exception:
                rg_calc={}

        rg_rate=_to_float(doc.get("rg_rate") or doc.get("retenue_garantie_pct"))
        rg_enabled=_to_bool(doc.get("rg_enabled")) or (rg_rate > 0.0)
        rg_total=_to_float(doc.get("rg_total_operation") or rg_calc.get("rg_total_operation"))
        rg_present=_to_float(doc.get("rg_present_ttc") or rg_calc.get("rg_present_ttc"))
        rg_remaining=_to_float(doc.get("rg_remaining_ttc") or rg_calc.get("rg_remaining_ttc"))
        rg_due=_maybe_iso(doc.get("rg_due_date_iso") or rg_calc.get("rg_due_date_iso"))
        reception=_maybe_iso(doc.get("reception_date") or doc.get("pv_reception_date_iso"))
        reminder_raw=doc.get("dgd_reminder_days")
        try:
            reminder_days=str(int(float(reminder_raw))) if reminder_raw not in (None,"") else ""
        except Exception:
            reminder_days=""
        rg_lib=_to_bool(doc.get("rg_liberee"))
        rg_lib_date=_maybe_iso(doc.get("rg_liberee_date"))
        show_line=_to_bool(doc.get("show_rg_line"))
        rg_note=str(doc.get("rg_note") or "").replace("\n"," ").strip()

        meta[numero].update({
            "rg_enabled": "1" if rg_enabled else "0",
            "rg_rate": _fmt_float(rg_rate) if rg_rate or rg_enabled else "",
            "rg_total_operation": _fmt_float(rg_total) if rg_total else ("0.00" if rg_enabled else ""),
            "rg_present_ttc": _fmt_float(rg_present) if rg_present else ("0.00" if rg_enabled else ""),
            "rg_due_date_iso": rg_due or "",
            "reception_date": reception or "",
            "dgd_reminder_days": reminder_days,
            "rg_liberee": "1" if rg_lib else "0",
            "rg_liberee_date": rg_lib_date or "",
            "show_rg_line": "1" if show_line else "0",
            "rg_note": rg_note,
            "rg_remaining_ttc": _fmt_float(rg_remaining) if rg_remaining else ("0.00" if rg_enabled else ""),
        })
        flags=[]

        # doc journal
        idx=0
        for p in _parse_payments_from_doc(doc):
            idx+=1
            date=p.get("date") or p.get("jour") or p.get("when")
            amt=_to_float(p.get("montant") or p.get("amount"))
            mode=p.get("mode") or p.get("moyen") or p.get("how")
            label=p.get("label") or p.get("type")
            if amt>0:
                child=_infer_child_doc(numero, {k.lower():p.get(k) for k in p.keys()}, parent_children) if is_situ else ""
                add(numero,is_situ,client,date,amt,mode,label,child,f"doc:{idx}")

        # simple fields
        if not is_situ:
            idx2=0
            for p in _extract_simple_invoice_payments(doc,total_ttc):
                idx2+=1
                amt=_to_float(p.get("montant",0))
                if amt>0: add(numero,is_situ,client,p.get("date"),amt,p.get("mode"),p.get("label"),"",f"docfld:{idx2}")

        # context
        if isinstance(ctx,dict):
            for key in ["payments","journal","payment_journal","encaissements"]:
                v=ctx.get(key)
                if isinstance(v,list):
                    for i,p in enumerate(v, start=1):
                        if not isinstance(p,dict): continue
                        date=p.get("date") or p.get("jour")
                        amt=_to_float(p.get("montant") or p.get("amount"))
                        mode=p.get("mode") or p.get("moyen")
                        label=p.get("label") or p.get("type")
                        if amt>0:
                            child=_infer_child_doc(numero, {k.lower():p.get(k) for k in p.keys()}, parent_children) if is_situ else ""
                            add(numero,is_situ,client,date,amt,mode,label,child,f"ctx:{key}:{i}")

        if is_situ and (_first(doc,["statut","status"],"").lower().find("acompte")>=0):
            flags.append("violation:no_acompte_in_situ")
        flags_map[numero]="|".join(flags) if flags else "ok"

    # external CSV
    ext=_load_external_payments_csv(app, parent_children)
    logging.info("external_rows=%d", len(ext))
    for e in ext:
        numero=str(e["doc_numero"]).strip()
        if not numero: continue
        is_situ=is_situ_map.get(numero, False)
        client =meta.get(numero, {}).get("client","")
        add(numero,is_situ,client,e["date"],e["montant"],e["mode"],e["label"],e.get("child_doc",""),e.get("src","ext"))

    # Post-fill child_doc by same (date, montant) within parent when one side known
    for numero, lst in list(entries.items()):
        if meta.get(numero, {}).get("type") != "SITU":
            continue
        by_key = {}
        for x in lst:
            key = (x.get("date",""), f'{float(x.get("montant",0.0)):.2f}')
            by_key.setdefault(key, []).append(x)
        for key, rows in by_key.items():
            if len(rows) < 2: 
                continue
            known = [r for r in rows if r.get("child_doc")]
            unknown = [r for r in rows if not r.get("child_doc")]
            if len(known) == 1 and len(unknown) >= 1:
                cd = known[0]["child_doc"]
                for r in unknown:
                    r["child_doc"] = cd

    # DEDUP
    for numero,lst in list(entries.items()):
        typ=meta.get(numero,{}).get("type","")
        seen=set(); out=[]
        if typ=="SITU":
            for x in lst:
                key=(x.get("child_doc",""), x["date"] or "", f'{float(x["montant"]):.2f}')
                if key in seen: 
                    continue
                seen.add(key); out.append(x)
        else:
            for x in lst:
                key=(x["date"] or "", f'{float(x["montant"]):.2f}')
                if key in seen: 
                    continue
                seen.add(key); out.append(x)
        entries[numero]=out

    # SIMPLE: ensure one 'final' if sum == TTC
    for numero,info in meta.items():
        if info["type"]!="SIMPLE": continue
        ttc=float(info["ttc"] or 0.0)
        lst=entries.get(numero,[])
        if not lst or ttc<=0: continue
        s=round(sum(x["montant"] for x in lst),2)
        if abs(s-ttc)<0.01 and not any(x["label"]=="final" for x in lst):
            lst_sorted=sorted(range(len(lst)), key=lambda i: (lst[i]["date"] or "", i))
            idxf=lst_sorted[-1]
            for i,x in enumerate(lst):
                x["label"]="final" if i==idxf else ("partiel" if x["label"]=="final" else x["label"])


    # Exports période si demandé
    if dfrom or dto:
        led_per = os.path.join(os.path.dirname(ledger_csv), "ledger_read_period.csv")
        bil_per = os.path.join(os.path.dirname(bilan_csv),  "bilan_read_period.csv")
        with open(led_per,"w",newline="",encoding="utf-8") as lf2, open(bil_per,"w",newline="",encoding="utf-8") as bf2:
            lw2=csv.writer(lf2); bw2=csv.writer(bf2)
            lw2.writerow(["doc_numero","type","client","date","montant","mode","label","child_doc"] + RG_COLUMNS)
            bw2.writerow(["doc_numero","type","client","ttc","encaissé_periode","encaissé_total_au_to","restant_au_to","flags"] + RG_COLUMNS)
            for numero,lst in entries.items():
                m=meta.get(numero,{"type":"", "client":"", "ttc":0.0})
                # lignes de la période
                per_rows=[x for x in lst if _in_range(x.get("date",""), dfrom, dto)]
                for x in sorted(per_rows, key=lambda x: (x["date"] or "", x["montant"])):
                    rg_values=[m.get(col, "") for col in RG_COLUMNS]
                    lw2.writerow([numero, m["type"], m["client"], x["date"], f"{x['montant']:.2f}", x["mode"], x["label"], x.get("child_doc","")] + rg_values)
                paid_per = round(sum(x["montant"] for x in per_rows),2)
                # total cumulé jusqu'à dto
                if dto:
                    cum_rows=[x for x in lst if _in_range(x.get("date",""), None, dto)]
                else:
                    cum_rows=list(lst)
                paid_cum = round(sum(x["montant"] for x in cum_rows),2)
                ttc=float(m["ttc"] or 0.0)
                restant_to = max(ttc - paid_cum, 0.0)
                flags = flags_map.get(numero, "ok")
                rg_values=[m.get(col, "") for col in RG_COLUMNS]
                bw2.writerow([numero, m["type"], m["client"], f"{ttc:.2f}", f"{paid_per:.2f}", f"{paid_cum:.2f}", f"{restant_to:.2f}", flags] + rg_values)

    # Write outputs + overpaid flag
    with open(ledger_csv,"w",newline="",encoding="utf-8") as lf, open(bilan_csv,"w",newline="",encoding="utf-8") as bf:
        lw=csv.writer(lf); bw=csv.writer(bf)
        lw.writerow(["doc_numero","type","client","date","montant","mode","label","child_doc"] + RG_COLUMNS)
        bw.writerow(["doc_numero","type","client","ttc","encaissé","restant_du","flags"] + RG_COLUMNS)

        for numero,lst in entries.items():
            m=meta.get(numero,{"type":"", "client":"", "ttc":0.0})
            for x in sorted(lst, key=lambda x: (x["date"] or "", x["montant"])):
                rg_values=[m.get(col, "") for col in RG_COLUMNS]
                lw.writerow([numero, m["type"], m["client"], x["date"], f"{x['montant']:.2f}", x["mode"], x["label"], x.get("child_doc","")] + rg_values)

        for numero,m in meta.items():
            paid=round(sum(x["montant"] for x in entries.get(numero,[])),2)
            ttc=float(m["ttc"] or 0.0)
            over=paid-ttc
            flags=[flags_map.get(numero,"ok")]
            if over>0.01:
                flags=[f for f in flags if f!="ok"]; flags.append("violation:paid_gt_ttc")
                try: app.log_action("overpaid_detected", f"{numero} paid={paid:.2f} ttc={ttc:.2f} delta={over:.2f}")
                except Exception: pass
            flags_str="ok" if not flags or flags==["ok"] else "|".join(flags)
            restant=max(ttc-paid,0.0)
            rg_values=[m.get(col, "") for col in RG_COLUMNS]
            bw.writerow([numero, m["type"], m["client"], f"{ttc:.2f}", f"{paid:.2f}", f"{restant:.2f}", flags_str] + rg_values)

    logging.info("[ledger_dump_plus] OK (SITU dedup by child_doc + PDF scan)")
    logging.info("ledger: %s", ledger_csv)
    logging.info("bilan : %s", bilan_csv)
    logging.info("jsonl : %s", jsonl_path)

    if ("--pause" in argv) or (os.environ.get("AE_PAUSE")=="1"):
        try: input("\nTerminé. Appuyez sur Entrée pour fermer...")
        except EOFError: pass

if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
