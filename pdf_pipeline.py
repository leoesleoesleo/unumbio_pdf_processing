"""
Procesamiento de textboxes desde PDF convertido a JSON.
Incluye extracción, limpieza, agrupación y transformación final.
"""

import json
import re
from typing import List, Dict, Any


# =========================
# CARGA DE DATOS
# =========================
def load_json(file_path: str) -> List[Dict[str, Any]]:
    """Carga un archivo JSON en memoria."""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# =========================
# EXTRACCIÓN Y NORMALIZACIÓN
# =========================
def extract_all_textboxes(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extrae todos los textboxes de todas las páginas."""
    all_boxes: List[Dict[str, Any]] = []

    for page in data:
        page_number = page.get("page")
        textboxes = page.get("textboxhorizontal", [])

        for box in textboxes:
            text = box.get("text", "").strip()

            if not text:
                continue

            all_boxes.append(
                {
                    "text": text,
                    "top": box.get("top"),
                    "x0": box.get("x0"),
                    "page": page_number,
                }
            )

    return all_boxes


# =========================
# ORDENAMIENTO
# =========================
def sort_textboxes(textboxes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ordena por página, posición vertical y horizontal."""
    return sorted(
        textboxes,
        key=lambda box: (box["page"], box["top"], box["x0"]),
    )


# =========================
# DETECCIÓN DE COLUMNAS
# =========================
def detect_column_threshold(textboxes: List[Dict[str, Any]]) -> float:
    """Detecta el umbral de separación entre columnas."""
    x_positions = sorted(box["x0"] for box in textboxes)

    max_gap = 0.0
    threshold = 0.0

    for index in range(len(x_positions) - 1):
        gap = x_positions[index + 1] - x_positions[index]

        if gap > max_gap:
            max_gap = gap
            threshold = (x_positions[index] + x_positions[index + 1]) / 2

    return threshold


def split_columns_per_page(
    textboxes: List[Dict[str, Any]],
    threshold: float,
) -> List[Dict[str, Any]]:
    """
    Separa columnas respetando páginas.
    Evita mezclar columnas de distintas páginas.
    """
    pages: Dict[Any, List[Dict[str, Any]]] = {}

    for box in textboxes:
        pages.setdefault(box["page"], []).append(box)

    ordered: List[Dict[str, Any]] = []

    for page in sorted(pages.keys()):
        boxes = pages[page]

        left_column = [b for b in boxes if b["x0"] < threshold]
        right_column = [b for b in boxes if b["x0"] >= threshold]

        left_column = sorted(left_column, key=lambda b: b["top"])
        right_column = sorted(right_column, key=lambda b: b["top"])

        ordered.extend(left_column)
        ordered.extend(right_column)

    return ordered


# =========================
# AGRUPACIÓN DE LÍNEAS
# =========================
def group_lines(
    textboxes: List[Dict[str, Any]],
    tolerance: float = 3.0,
) -> List[List[Dict[str, Any]]]:
    """Agrupa bloques en líneas lógicas según proximidad vertical."""
    lines: List[List[Dict[str, Any]]] = []
    current_line: List[Dict[str, Any]] = []
    current_top = None

    for box in textboxes:
        if current_top is None:
            current_line = [box]
            current_top = box["top"]
            continue

        if abs(box["top"] - current_top) <= tolerance:
            current_line.append(box)
        else:
            lines.append(current_line)
            current_line = [box]
            current_top = box["top"]

    if current_line:
        lines.append(current_line)

    return lines


def build_line_text(line: List[Dict[str, Any]]) -> str:
    """Reconstruye el texto de una línea."""
    sorted_line = sorted(line, key=lambda b: b["x0"])
    return " ".join(box["text"] for box in sorted_line)


# =========================
# LIMPIEZA DE TEXTO
# =========================
def clean_text(text: str) -> str:
    """
    Limpia ruido estructural del PDF.

    Reglas:
    - Elimina cualquier contenido después de 'EUTM XXXXX'
    - Elimina headers de sección SOLO si están al inicio de línea
    """

    # 1. Cortar después de EUTM
    text = re.sub(r"\s*EUTM\s+\d+.*", "", text)

    # 2. Eliminar headers SOLO al inicio de línea
    header_patterns = [
        r"^2024/\d{3}\s+PART\s+B\s+B\.1\.?",
        r"^2024/\d{3}\s+Part\s+B\.1\.?",
        r"^Part\s+B\.1\.?",
    ]

    for pattern in header_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

    return text.strip()


def is_noise_line(text: str) -> bool:
    """Detecta líneas completamente irrelevantes."""
    patterns = [r"PART\s+B", r"B\.1", r"2024/\d{3}"]

    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


# =========================
# DETECCIÓN DE INID
# =========================
def is_inid(token: str) -> bool:
    """Valida si un token es un INID."""
    return token.isdigit() and 2 <= len(token) <= 4


# =========================
# CONSTRUCCIÓN DE REGISTROS
# =========================
def build_records(lines: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Construye registros a partir de líneas.

    - 111 inicia registro
    - Maneja multilinealidad
    - Limpia ruido
    """
    records: List[Dict[str, Any]] = []
    current_record: Dict[str, Any] = None
    current_field: str = None

    for line in lines:
        raw_text = build_line_text(line)

        if is_noise_line(raw_text):
            continue

        line_text = clean_text(raw_text)
        if not line_text:
            continue

        tokens = line_text.split()
        if not tokens:
            continue

        first_token = tokens[0]

        if first_token == "111":
            if current_record:
                records.append(current_record)

            current_record = {"_PAGE": line[0]["page"]}
            current_field = "111"
            current_record[current_field] = " ".join(tokens[1:])
            continue

        if is_inid(first_token):
            if current_record is None:
                continue

            current_field = first_token
            value = clean_text(" ".join(tokens[1:]))

            if current_field == "210":
                matches = re.findall(r"\b\d{6,}\b", value)
                if matches:
                    current_record[current_field] = max(matches, key=len)
                continue

            if current_field == "400":
                if value:
                    current_record.setdefault("400", [])
                    if value not in current_record["400"]:
                        current_record["400"].append(value)
                continue

            current_record[current_field] = value
            continue

        if current_record is None or not current_field:
            continue

        if current_field == "400":
            if current_record.get("400"):
                current_record["400"][-1] += f" {line_text}"
            continue

        current_record[current_field] += f" {line_text}"

    if current_record:
        records.append(current_record)

    return records


# =========================
# NORMALIZACIÓN PRE-MERGE
# =========================
def normalize_records(
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Limpia todos los valores antes del merge."""
    for record in records:
        for key, value in record.items():
            if isinstance(value, str):
                record[key] = clean_text(value)
            elif isinstance(value, list):
                record[key] = [clean_text(item) for item in value]

    return records


# =========================
# MERGE DE REGISTROS
# =========================
def merge_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fusiona registros duplicados.

    Prioridad:
    - 210 (ID único real)
    - fallback: 111
    """
    merged: Dict[str, Dict[str, Any]] = {}

    for record in records:
        key = record.get("210") or record.get("111")

        if not key:
            continue

        if key not in merged:
            merged[key] = record
            continue

        existing = merged[key]

        for field, value in record.items():
            if field == "_PAGE":
                continue

            if isinstance(value, str):
                value = clean_text(value)

            if field not in existing:
                existing[field] = value

            elif field == "400":
                existing.setdefault("400", [])

                for item in value:
                    item = clean_text(item)
                    if item not in existing["400"]:
                        existing["400"].append(item)

            else:
                existing_val = existing.get(field, "")

                if len(str(value)) > len(str(existing_val)):
                    existing[field] = value

    return list(merged.values())


# =========================
# TRANSFORMACIÓN FINAL
# =========================
def transform_records(
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Limpieza final de formato."""
    cleaned_records: List[Dict[str, Any]] = []

    for record in records:
        new_record: Dict[str, Any] = {}

        for key, value in record.items():
            if key == "_PAGE":
                new_record[key] = value
            elif key == "400":
                new_record[key] = [item.strip() for item in value]
            else:
                new_record[key] = value.strip()

        cleaned_records.append(new_record)

    return cleaned_records


def build_output(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Construye la estructura final requerida."""
    return {"B": {"1": records}}
