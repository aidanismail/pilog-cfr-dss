from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
SCENARIO_FILE = OUTPUT_DIR / "scenario_comparison.json"
GATE_FILE = OUTPUT_DIR / "gate_evaluation.json"
QUALITY_FILE = OUTPUT_DIR / "case_quality_report.json"
CASE_FILE = OUTPUT_DIR / "case_bontang_eci_normalized.json"
MARKDOWN_OUTPUT = OUTPUT_DIR / "decision_brief.md"
JSON_OUTPUT = OUTPUT_DIR / "decision_brief.json"


def load_json(path: Path) -> dict[str, Any]:
      if not path.exists():
          return {}

      with path.open("r", encoding="utf-8") as file:
          return json.load(file)


def money(value: Any) -> str:
      if value is None:
          return "N/A"

      try:
          return f"USD {float(value):,.2f}/MT"
      except (TypeError, ValueError):
          return str(value)


def get_quality_status(quality: dict[str, Any]) -> str:
      return str(
          quality.get("overall_status")
          or quality.get("status")
          or quality.get("result")
          or "UNKNOWN"
      )


def scenario_reasons(
      scenario: dict[str, Any],
      gate_evaluation: dict[str, Any],
  ) -> list[str]:
      reasons: list[str] = []

      feasible = scenario.get("feasible")
      comparable = scenario.get("comparable")
      calculation_status = scenario.get("calculation_status")
      sales_term = scenario.get("sales_term")

      if feasible is True:
          reasons.append("Skenario ditandai feasible berdasarkan input simulasi.")
      else:
          reasons.append("Skenario tidak feasible atau memenuhi persyaratan operasional.")

      if comparable is True:
          reasons.append(
              "Basis perbandingan dinyatakan comparable: route, tanggal, unit, "
              "dan batas biaya dianggap konsisten."
          )
      else:
          reasons.append(
              "Skenario belum comparable, sehingga tidak boleh menjadi dasar keputusan final."
          )

      if calculation_status == "CALCULATED":
          reasons.append("Perhitungan harga berhasil dijalankan.")
      else:
          reasons.append(f"Perhitungan belum lengkap dengan status {calculation_status or'UNKNOWN'}."
          )

      block_reason = scenario.get("block_reason")
      if block_reason:
          reasons.append(f"Alasan pemblokiran: {block_reason}")

      if sales_term == "FOB":
          reasons.append(
              "FOB berfungsi sebagai baseline karena PILOG menyerahkan ocean freight "
              "kepada buyer."
          )

      if sales_term == "CFR":
          results = scenario.get("results", {})
          margin = results.get("freight_margin_usd_mt")

          if margin is not None:
              if float(margin) > 0:
                  reasons.append(
                      f"Freight margin positif sebesar {money(margin)}, "
                      "sehingga freight menghasilkan kontribusi kotor positif."
                  )
              elif float(margin) < 0:
                  reasons.append(
                      f"Freight margin negatif sebesar {money(margin)}, "
                      "sehingga komponen freight berpotensi merugikan."
                  )
              else:
                  reasons.append(
                      "Freight margin berada pada titik impas."
                  )

      # Batch 7 menyimpan hasil per-skenario di gate_2.scenario_results.
      # Fallback ke key lama dipertahankan agar brief tetap kompatibel.
      gate_scenarios = (
          gate_evaluation.get("gate_2", {}).get("scenario_results")
          or gate_evaluation.get("scenarios", [])
      )
      for gate in gate_scenarios:
          if gate.get("scenario_id") == scenario.get("scenario_id"):
              gate_result = (
                  gate.get("outcome")
                  or gate.get("result")
                  or gate.get("status")
              )
              if gate_result:
                  reasons.append(f"Hasil Gate 2: {gate_result}.")

              for reason in gate.get("reasons", []):
                  reasons.append(f"Gate 2: {reason}")

      return reasons


def calculation_lines(scenario: dict[str, Any]) -> list[str]:
      inputs = scenario.get("inputs", {})
      results = scenario.get("results", {})

      index_value = inputs.get("index_usd_mt")
      alpha_value = inputs.get("alpha_usd_mt")
      selling_freight = inputs.get("freight_selling_rate_usd_mt")
      freight_cost = inputs.get("freight_cost_usd_mt")
      adjustment = inputs.get("cfr_adjustment_usd_mt")

      fob_value = results.get("fob_usd_mt")
      cfr_value = results.get("cfr_usd_mt")
      freight_margin = results.get("freight_margin_usd_mt")

      lines = [
          f"- FOB = Index + Alpha = "
          f"{money(index_value)} + {money(alpha_value)} = {money(fob_value)}"
      ]

      if cfr_value is not None:
          lines.append(
              f"- CFR = FOB + Freight selling rate + Adjustment = "
              f"{money(fob_value)} + {money(selling_freight)} + "
              f"{money(adjustment or 0)} = {money(cfr_value)}"
          )

      if freight_margin is not None:
          lines.append(
              f"- Freight margin = Freight selling rate − Freight cost = "
              f"{money(selling_freight)} − {money(freight_cost)} = "
              f"{money(freight_margin)}"
          )

      return lines


def build_brief() -> tuple[dict[str, Any], str]:
      scenarios_data = load_json(SCENARIO_FILE)
      gate_data = load_json(GATE_FILE)
      quality_data = load_json(QUALITY_FILE)
      case_data = load_json(CASE_FILE)

      scenarios = scenarios_data.get("scenarios", [])

      case_id = (
          scenarios_data.get("case_id")
          or case_data.get("case_id")
          or "UNKNOWN-CASE"
      )

      gate_1 = (
          gate_data.get("gate_1", {}).get("outcome")
          or gate_data.get("gate_1", {}).get("result")
          or gate_data.get("gate_1", {}).get("status")
          or "BELUM DIEVALUASI"
      )

      overall_result = (
          gate_data.get("overall_outcome")
          or gate_data.get("overall_result")
          or gate_data.get("recommendation")
          or "BELUM ADA REKOMENDASI FINAL"
      )

      report: dict[str, Any] = {
          "case_id": case_id,
          "mode": "simulation",
          "status": "advisory-only",
          "choice_made": False,
          "human_approval_required": True,
          "quality_status": get_quality_status(quality_data),
          "gate_1_result": gate_1,
          "overall_simulation_recommendation": overall_result,
          "scenarios": [],
          "limitations": [
              "Laporan ini adalah hasil simulasi, bukan keputusan komersial final.",
              "Nilai demo harus diganti dengan data tervalidasi dari sumber resmi.",
              "Skenario comparable=false tidak boleh digunakan untuk keputusan final.",
              "Tidak ada kontrak, booking kapal, hedging, atau transaksi yang dieksekusi.",
          ],
          "generated_at_utc": datetime.now(timezone.utc).isoformat(),
      }

      markdown: list[str] = [
          "# Decision Brief — CFR DSS Simulation",
          "",
          "> Status: SIMULATION / ADVISORY-ONLY",
          "> ",
          "> Dokumen ini memberikan rekomendasi simulasi beserta alasan dan audit perhitungannya.",
          "> Belum ada keputusan komersial atau eksekusi otomatis.",
          "",
          "## 1. Identitas Kasus",
          "",
          f"- Case ID: `{case_id}`",
          f"- Mode: `{report['mode']}`",
          f"- Status data: `{report['quality_status']}`",
          f"- Gate 1: `{gate_1}`",
          f"- Rekomendasi simulasi keseluruhan: **{overall_result}**",
          "- Persetujuan manusia: **Wajib**",
          "",
          "## 2. Ringkasan Rekomendasi",
          "",
          f"Rekomendasi sistem pada tahap simulasi adalah: **{overall_result}**.",
          "",
          "Rekomendasi ini belum berarti transaksi harus langsung dilakukan. "
          "Business user tetap harus memvalidasi harga, freight, kapal, kontrak, "
          "risiko, dan persetujuan internal.",
          "",
          "## 3. Detail Setiap Skenario",
          "",
      ]

      for index, scenario in enumerate(scenarios, start=1):
          scenario_id = scenario.get("scenario_id", f"SCENARIO-{index}")
          scenario_name = scenario.get("scenario_name", scenario_id)
          results = scenario.get("results", {})
          inputs = scenario.get("inputs", {})

          reasons = scenario_reasons(scenario, gate_data)
          calculations = calculation_lines(scenario)

          report["scenarios"].append(
              {
                  "scenario_id": scenario_id,
                  "scenario_name": scenario_name,
                  "sales_term": scenario.get("sales_term"),
                  "vessel_option": scenario.get("vessel_option"),
                  "feasible": scenario.get("feasible"),
                  "comparable": scenario.get("comparable"),
                  "calculation_status": scenario.get("calculation_status"),
                  "inputs": inputs,
                  "results": results,
                  "reasons": reasons,
              }
          )

          markdown.extend(
              [
                  f"### 3.{index} {scenario_name}",
                  "",
                  f"- Scenario ID: `{scenario_id}`",
                  f"- Sales term: `{scenario.get('sales_term', 'N/A')}`",
                  f"- Vessel option: `{scenario.get('vessel_option') or 'N/A'}`",
                  f"- Feasible: `{scenario.get('feasible')}`",
                  f"- Comparable: `{scenario.get('comparable')}`",
                  f"- Status perhitungan: `{scenario.get('calculation_status', 'N/A')}`",
                  f"- Sumber/asumsi: {scenario.get('source', 'N/A')}",
                  "",
                  "**Input yang digunakan:**",
                  "",
                  f"- Index: {money(inputs.get('index_usd_mt'))}",
                  f"- Alpha: {money(inputs.get('alpha_usd_mt'))}",
                  f"- Freight selling rate: {money(inputs.get('freight_selling_rate_usd_mt'))}",
                  f"- Freight cost: {money(inputs.get('freight_cost_usd_mt'))}",
                  f"- Penyesuaian CFR: {money(inputs.get('cfr_adjustment_usd_mt'))}",
                  "",
                  "**Perhitungan:**",
                  "",
                  *calculations,
                  "",
                  "**Hasil:**",
                  "",
                  f"- FOB: {money(results.get('fob_usd_mt'))}",
                  f"- CFR: {money(results.get('cfr_usd_mt'))}",
                  f"- Freight margin: {money(results.get('freight_margin_usd_mt'))}",
                  "",
                  "**Mengapa skenario ini mendapat status tersebut:**",
                  "",
              ]
          )

          markdown.extend([f"- {reason}" for reason in reasons])
          markdown.extend(["", f"**Catatan skenario:** {scenario.get('note', 'N/A')}", ""])

      markdown.extend(
          [
              "## 4. Cara Membaca Rekomendasi",
              "",
              "Sistem tidak memilih skenario hanya karena harga CFR paling tinggi."
              "Skenario harus memenuhi urutan berikut:",
              "",
              "1. Data wajib tersedia dan lolos pemeriksaan kualitas.",
              "2. Skenario feasible secara operasional.",
              "3. Basis perbandingan comparable.",
              "4. FOB dan CFR dihitung dengan unit serta batas biaya yang sama.",
              "5. Freight margin dan risiko diperiksa.",
              "6. Gate 1 dan Gate 2 memberikan status yang dapat diterima.",
              "7. Business user memberikan persetujuan manusia.",
              "",
              "## 5. Batasan dan Asumsi",
              "",
          ]
      )

      markdown.extend([f"- {item}" for item in report["limitations"]])

      markdown.extend(
          [
              "",
              "## 6. Status Implementasi",
              "",
              "- Ini masih **simulation build**.",
              "- Script hanya menyusun analisis dan decision brief.",
              "- Belum ada koneksi otomatis ke Fleetra, Procurex, SAP, atau sistem eksternal.",
              "- Belum ada booking kapal, penerbitan kontrak, hedging, atau pengiriman instruksi transaksi.",
              "- Field `choice_made` tetap `false` sampai ada proses persetujuan manusia.",
              "",
          ]
      )

      return report, "\n".join(markdown)


if __name__ == "__main__":
      report, markdown = build_brief()

      with JSON_OUTPUT.open("w", encoding="utf-8") as file:
          json.dump(report, file, indent=2, ensure_ascii=False)

      MARKDOWN_OUTPUT.write_text(markdown, encoding="utf-8")

      print(f"Decision brief berhasil dibuat: {MARKDOWN_OUTPUT}")
      print(f"Audit JSON berhasil dibuat: {JSON_OUTPUT}")
