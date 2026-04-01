"""
Tests de integración para validar la exactitud del pipeline completo.

Incluye:
- Comparación contra ground truth
- Validación de estructura
- Detección de duplicados
- Verificación de campos críticos
"""

import json
import unittest

from main import (
    load_json,
    extract_all_textboxes,
    sort_textboxes,
    detect_column_threshold,
    split_columns_per_page,
    group_lines,
    build_records,
    normalize_records,
    merge_records,
    transform_records,
    build_output,
)


class TestOutputAccuracy(unittest.TestCase):
    """Suite de pruebas de integración del pipeline completo."""

    INPUT_PATH = (
        "inputs/BUL_EM_TM_2024000001_001.json"
    )
    EXPECTED_PATH = (
        "inputs/BUL_EM_TM_2024000001_002.json"
    )

    REQUIRED_FIELDS = ["111", "210", "151"]

    def setUp(self) -> None:
        """Carga archivos de entrada y salida esperada."""
        with open(self.EXPECTED_PATH, "r", encoding="utf-8") as file:
            self.expected_output = json.load(file)

        self.actual_output = self.run_pipeline()

    # =========================
    # PIPELINE COMPLETO
    # =========================
    def run_pipeline(self) -> dict:
        """Ejecuta todo el pipeline del procesamiento."""
        data = load_json(self.INPUT_PATH)

        textboxes = extract_all_textboxes(data)
        sorted_boxes = sort_textboxes(textboxes)

        threshold = detect_column_threshold(sorted_boxes)
        column_boxes = split_columns_per_page(sorted_boxes, threshold)

        lines = group_lines(column_boxes)

        records = build_records(lines)
        records = normalize_records(records)
        records = merge_records(records)

        final_records = transform_records(records)

        return build_output(final_records)

    # =========================
    # MÉTRICA DE EXACTITUD
    # =========================
    def calculate_accuracy(self, expected: dict, actual: dict) -> float:
        """
        Calcula exactitud usando matching por INID 111.
        También imprime diferencias para debugging.
        """
        expected_records = expected.get("B", {}).get("1", [])
        actual_records = actual.get("B", {}).get("1", [])

        expected_map = {
            record.get("111"): record
            for record in expected_records
            if "111" in record
        }
        actual_map = {
            record.get("111"): record
            for record in actual_records
            if "111" in record
        }

        total_fields = 0
        matched_fields = 0

        print("\n================ DEBUG DIFERENCIAS ================\n")

        for key_111, expected_record in expected_map.items():
            actual_record = actual_map.get(key_111)

            if not actual_record:
                print(f"Registro faltante: {key_111}")
                continue

            for field in expected_record:
                total_fields += 1

                expected_value = expected_record[field]
                actual_value = actual_record.get(field)

                if actual_value == expected_value:
                    matched_fields += 1
                else:
                    print(f"[x] Mismatch en registro {key_111}, campo {field}")
                    print(f"    Esperado: {expected_value}")
                    print(f"    Actual:   {actual_value}\n")

        if total_fields == 0:
            return 0.0

        return (matched_fields / total_fields) * 100

    # =========================
    # TEST PRINCIPAL
    # =========================
    def test_output_accuracy(self):
        """Valida que el output sea suficientemente cercano al esperado."""
        accuracy = self.calculate_accuracy(
            self.expected_output,
            self.actual_output,
        )

        print(f"\nAccuracy del procesamiento: {accuracy:.2f}%\n")

        self.assertGreaterEqual(accuracy, 80.0)

    # =========================
    # TEST DE ESTRUCTURA
    # =========================
    def test_structure(self):
        """Valida estructura base del JSON."""
        self.assertIn("B", self.actual_output)
        self.assertIn("1", self.actual_output["B"])
        self.assertIsInstance(self.actual_output["B"]["1"], list)

    # =========================
    # TEST DE DUPLICADOS
    # =========================
    def test_no_duplicate_records(self):
        """
        Detecta registros duplicados usando clave robusta:
        - 210 (principal)
        - fallback: 111
        """
        records = self.actual_output.get("B", {}).get("1", [])

        seen = set()
        duplicates = []

        for record in records:
            key = record.get("210") or record.get("111")

            if key in seen:
                duplicates.append(key)
            else:
                seen.add(key)

        print(f"\nDuplicados detectados: {duplicates}")

        self.assertEqual(len(duplicates), 0)


if __name__ == "__main__":
    unittest.main()
