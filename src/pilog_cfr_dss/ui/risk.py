"""Streamlit editor for the optional transaction and stress inputs."""
import streamlit as st

from pilog_cfr_dss.models.risk import AGREEMENTS, BASES, PARTIES, STATUSES, STRESSES, VERSION, risk_input, voyage_scope


def select(label, options, value, key):
    return st.selectbox(label, list(options), index=list(options).index(value), format_func=options.get, key=key)


def field(label, current, key, max_chars=300):
    return st.text_input(label, "" if current is None else str(current), max_chars=max_chars, key=key).strip()


def commitment(label, existing, key, unit=None):
    status = select(label, STATUSES, existing.get("status", "unknown"), key + "status")
    result = {"status": status}
    if status == "unknown":
        return result
    if status == "binding":
        left, right = st.columns(2)
        with left:
            result["basis"] = select("Dasar harga", BASES, existing.get("basis", "unknown"), key + "basis")
        with right:
            result["coverage_percent"] = field("Cakupan tetap untuk kasus ini (%)", existing.get("coverage_percent"), key + "coverage", 16)
    result["evidence"] = field("Rujukan atau catatan konfirmasi", existing.get("evidence"), key + "evidence")
    if unit and status in ("indicative", "binding", "open"):
        left, middle, right = st.columns(3)
        with left:
            result["rate"] = field(f"Tarif tercatat ({unit})", existing.get("rate"), key + "rate", 24)
        with middle:
            result["agreed_on"] = field("Tanggal tercatat (YYYY-MM-DD)", existing.get("agreed_on"), key + "agreed", 10)
        with right:
            result["valid_until"] = field("Berlaku sampai (YYYY-MM-DD)", existing.get("valid_until"), key + "valid", 10)
    return result


def transaction_inputs(case, key):
    key += "_risk_"
    existing = case.get("risk_assessment", {})
    with st.expander("Status transaksi", expanded=bool(existing)):
        if not st.checkbox("Analisis risiko dan mitigasi", value=bool(existing), key=key + "enabled"):
            case.pop("risk_assessment", None)
            return
        current_scope = voyage_scope(case)
        scope = existing.get("scope", current_scope)
        if scope != current_scope:
            st.warning("Rute, muatan, komoditas, atau jadwal berubah. Periksa kembali cakupan komitmen.")
            if st.button("Konfirmasi cakupan untuk kasus ini", key=key + "scope"):
                scope = current_scope
        result = {"version": VERSION, "scope": scope, "commitments": {}}
        facts = existing.get("commitments", {})
        columns = st.columns(3)
        for column, (kind, label) in zip(columns, AGREEMENTS.items()):
            with column:
                old = facts.get(kind, {})
                prefix = key + kind + "_"
                result["commitments"][kind] = commitment(label, old, prefix, "USD/hari" if kind == "charter" else "USD/MT")
                if kind == "charter":
                    result["commitments"][kind]["vessel_class"] = select("Kelas pada komitmen sewa",
                        {None: "Belum ditetapkan", **{name: name for name in case["profiles"]}}, old.get("vessel_class"), prefix + "class")
                    if result["commitments"][kind]["status"] == "open" and result["commitments"][kind].get("rate"):
                        result["commitments"][kind]["quote_comparable"] = st.checkbox(
                            "Quotation untuk rute, periode, dan cakupan biaya ini", value=old.get("quote_comparable", False),
                            key=prefix + "comparable")
                    result["vessel_nominated"] = select("Kapal sudah dinominasikan",
                        {None: "Belum diketahui", True: "Ya", False: "Belum"}, existing.get("vessel_nominated"), prefix + "nomination")
        with st.expander("Bunker, delay dan kontrak terkait"):
            for column, kind in zip(st.columns(3), ("VLSFO", "LSMGO", "port_delay")):
                with column:
                    old = existing.get(kind, {})
                    label = "Tambahan hari di pelabuhan" if kind == "port_delay" else kind
                    prefix = key + kind + "_"
                    result[kind] = commitment(label, old, prefix) if kind != "port_delay" else {
                        "evidence": field("Rujukan biaya tambahan hari", old.get("evidence"), prefix + "evidence")}
                    result[kind]["payer"] = select("Penanggung " + label, PARTIES, old.get("payer", "unknown"), prefix + "payer")
            old = existing.get("demurrage", {})
            result["demurrage"] = {name: field(label, old.get(name), key + name) for name, label in
                (("payable_usd", "Demurrage terutang (USD)"), ("recoverable_usd", "Demurrage yang bisa ditagih (USD)"),
                 ("basis", "Pihak pembayar, tarif, dan waktu yang memenuhi syarat"), ("evidence", "Rujukan klausul demurrage"))}
            result["recurring_program"] = st.checkbox("Program pengiriman berulang", value=existing.get("recurring_program", False), key=key + "recurring")
            result["fx_evidence"] = field("Arus kas beda mata uang dan rujukan", existing.get("fx_evidence"), key + "fx")
            result["liability_evidence"] = field("Potensi tanggung jawab maritim dan rujukan", existing.get("liability_evidence"), key + "liability")
        with st.expander("Uji perubahan biaya dan durasi"):
            st.caption("Harga diisi sebagai selisih (+/−). Muatan dan draft diisi sebagai nilai baru.")
            old = existing.get("stresses", {})
            result["stresses"] = {}
            columns = st.columns(3)
            for i, (name, (label, unit)) in enumerate(STRESSES.items()):
                with columns[i % len(columns)]:
                    value = field(f"{label} ({unit})", old.get(name), key + "stress_" + name, 24)
                    if value:
                        result["stresses"][name] = value
        case["risk_assessment"] = result
        try:
            risk_input(case)
        except ValueError as error:
            st.session_state["input_errors"].append(str(error))
