"""
Punto de entrada del pipeline de procesamiento de PDF.
Ejecuta todas las etapas desde carga hasta salida final.
"""

import json
import os
import argparse
import datetime

from pdf_pipeline import (
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



def main(save_to_file: bool=False) -> None:
    """Ejecuta el flujo completo de procesamiento."""
    file_path = "inputs/BUL_EM_TM_2024000007_001.json"

    data = load_json(file_path)

    textboxes = extract_all_textboxes(data)
    sorted_boxes = sort_textboxes(textboxes)

    threshold = detect_column_threshold(sorted_boxes)
    column_boxes = split_columns_per_page(sorted_boxes, threshold)

    lines = group_lines(column_boxes)

    records = build_records(lines)
    records = normalize_records(records)
    records = merge_records(records)

    final_records = transform_records(records)
    output = build_output(final_records)

    if save_to_file:
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        filename = (
            f"output_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(output, file, indent=2, ensure_ascii=False)

        print(f"Output guardado en: {output_path}")
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Procesa PDF convertido a JSON"
    )

    parser.add_argument(
        "--save",
        action="store_true",
        help="Guardar salida en archivo JSON en carpeta outputs",
    )

    args = parser.parse_args()

    main(save_to_file=args.save)
