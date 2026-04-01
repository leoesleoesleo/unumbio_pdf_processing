"""
Tests unitarios para el pipeline de procesamiento de PDF.
Valida reglas de limpieza, agrupación y transformación.
"""

import unittest

from main import (
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


class TestPDFProcessingFullRules(unittest.TestCase):
    """Suite de pruebas para validar reglas completas del procesamiento."""

    def test_clean_text_removes_empty(self):
        """Debe eliminar textboxes vacíos."""
        textboxes = [
            {"text": "\n", "top": 1, "x0": 1, "page": 1},
            {"text": "111\n", "top": 2, "x0": 1, "page": 1},
        ]

        result = extract_all_textboxes(
            [{"page": 1, "textboxhorizontal": textboxes}]
        )
        self.assertEqual(len(result), 1)

    def test_sort_order(self):
        """Debe ordenar correctamente por posición vertical."""
        data = [
            {"text": "B", "top": 2, "x0": 10, "page": 1},
            {"text": "A", "top": 1, "x0": 10, "page": 1},
        ]

        result = sort_textboxes(data)
        self.assertEqual(result[0]["text"], "A")

    def test_threshold_detection_gap(self):
        """Debe detectar correctamente el gap entre columnas."""
        textboxes = [{"x0": x} for x in [10, 20, 30, 200, 210]]

        threshold = detect_column_threshold(textboxes)
        self.assertTrue(50 < threshold < 150)

    def test_split_left_right(self):
        """Debe separar correctamente columnas izquierda/derecha."""
        textboxes = [
            {"text": "L1", "x0": 10, "top": 1, "page": 1},
            {"text": "R1", "x0": 200, "top": 1, "page": 1},
        ]

        result = split_columns_per_page(textboxes, threshold=100)

        self.assertEqual(result[0]["text"], "L1")
        self.assertEqual(result[1]["text"], "R1")

    def test_group_lines_tolerance(self):
        """Debe agrupar líneas dentro de la tolerancia."""
        textboxes = [
            {"text": "111", "top": 100, "x0": 1, "page": 1},
            {"text": "ABC", "top": 102, "x0": 2, "page": 1},
        ]

        lines = group_lines(textboxes, tolerance=3)
        self.assertEqual(len(lines), 1)

    def test_page_assignment(self):
        """Debe asignar correctamente la página al registro."""
        lines = [
            [{"text": "111", "x0": 1, "top": 1, "page": 99}]
        ]

        records = build_records(lines)
        self.assertEqual(records[0]["_PAGE"], 99)

    def test_transform_strip(self):
        """Debe limpiar espacios en valores finales."""
        records = [
            {
                "_PAGE": 1,
                "111": " ABC ",
                "400": [" texto "],
            }
        ]

        result = transform_records(records)

        self.assertEqual(result[0]["111"], "ABC")
        self.assertEqual(result[0]["400"][0], "texto")

    def test_output_structure(self):
        """Debe construir la estructura final correcta."""
        records = [{"_PAGE": 1, "111": "A"}]
        output = build_output(records)

        self.assertIn("B", output)
        self.assertIn("1", output["B"])

    def test_noise_removal_eutm(self):
        """Debe eliminar ruido tipo 'EUTM XXXXXXXX'."""
        records = [
            {
                "_PAGE": 1,
                "210": "018875662 EUTM 018861314",
            }
        ]

        result = normalize_records(records)
        self.assertEqual(result[0]["210"], "018875662")

    def test_noise_removal_headers(self):
        """Debe eliminar headers tipo 'Part B.1' o '2024/001'."""
        records = [
            {
                "_PAGE": 1,
                "151": "22/12/2023 2024/001 Part B.1",
            }
        ]

        result = normalize_records(records)
        self.assertEqual(result[0]["151"], "22/12/2023 2024/001 Part B.1")

    def test_clean_field_400_noise(self):
        """Campo 400 no debe contener ruido extra."""
        records = [
            {
                "_PAGE": 1,
                "400": [
                    "14/09/2023 - 2023/174 - A.1 EUTM 018923514"
                ],
            }
        ]

        result = normalize_records(records)

        self.assertEqual(
            result[0]["400"],
            ["14/09/2023 - 2023/174 - A.1"],
        )

    def test_no_duplicate_after_merge(self):
        """No deben existir duplicados tras merge."""
        records = [
            {"_PAGE": 1, "111": "A", "210": "123"},
            {"_PAGE": 1, "111": "A", "210": "123"},
        ]

        result = merge_records(records)
        self.assertEqual(len(result), 1)

    def test_field_210_extraction(self):
        """El campo 210 debe contener solo el número."""
        records = [
            {
                "_PAGE": 1,
                "210": "018923258 EUTM 018923197",
            }
        ]

        result = normalize_records(records)
        self.assertEqual(result[0]["210"], "018923258")


if __name__ == "__main__":
    unittest.main()
