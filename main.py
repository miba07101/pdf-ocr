import os
import sys
import argparse
import pandas as pd
import numpy as np
from pdf2image import convert_from_path
import cv2
from tqdm import tqdm
import time
import glob
from pathlib import Path
import pdfplumber


def get_docling():
    try:
        from docling.document_converter import DocumentConverter

        return DocumentConverter()
    except Exception:
        return None


def get_marker(page_range=None):
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        config = {}
        if page_range:
            config["page_range"] = page_range

        return PdfConverter(artifact_dict=create_model_dict(), config=config)
    except Exception:
        return None


def process_docling(pdf_path, output_base, pages):
    print(f"\n--- Docling: {os.path.basename(pdf_path)} ---")
    converter = get_docling()
    if not converter:
        print("ERROR: Docling is not installed.")
        return

    print("Processing document...")

    page_range = None
    if pages:
        page_range = (min(pages), max(pages))

    result = converter.convert(pdf_path, page_range=page_range)

    out_dir = Path(f"output_docling") / Path(pdf_path).stem
    out_dir.mkdir(parents=True, exist_ok=True)

    md_content = result.document.export_to_markdown()

    with open(out_dir / "document.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Results in: {out_dir}")


def process_marker(pdf_path, output_base, pages):
    print(f"\n--- Marker: {os.path.basename(pdf_path)} ---")

    page_range = None
    if pages:
        page_range = [p - 1 for p in pages]

    converter = get_marker(page_range)
    if not converter:
        print("ERROR: Marker is not installed.")
        return
    from marker.output import text_from_rendered

    print("Processing PDF with Marker...")
    rendered = converter(pdf_path)
    full_text, _, images = text_from_rendered(rendered)
    out_dir = Path(output_base) / Path(pdf_path).stem
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "document.md", "w", encoding="utf-8") as f:
        f.write(full_text)

    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    print("Saving images...")
    for name, img in tqdm(images.items(), desc="Saving images", unit="image"):
        img.save(img_dir / name)
    print(f"Results in: {out_dir}")


def process_docling_tables(pdf_path, pages=None):
    print(f"\n--- Docling Tables: {os.path.basename(pdf_path)} ---")
    from docling.document_converter import DocumentConverter

    print("Processing document with progress...")
    converter = DocumentConverter()

    page_range = None
    if pages:
        page_range = (min(pages), max(pages))

    conv_res = converter.convert(pdf_path, page_range=page_range)

    out_dir = Path("output_docling_tables") / Path(pdf_path).stem
    out_dir.mkdir(parents=True, exist_ok=True)

    all_tables = list(conv_res.document.tables)

    tables_to_process = [(i + 1, table) for i, table in enumerate(all_tables)]

    tables_found = 0
    for table_ix, table in tqdm(
        tables_to_process, desc="Extracting tables", unit="table"
    ):
        table_df: pd.DataFrame = table.export_to_dataframe(doc=conv_res.document)
        tables_found += 1

        csv_path = out_dir / f"table_{table_ix}.csv"
        table_df.to_csv(csv_path, index=False, sep=";")

        xlsx_path = out_dir / f"table_{table_ix}.xlsx"
        table_df.to_excel(xlsx_path, index=False)

    if tables_found == 0:
        print("No tables found in document.")
    else:
        print(f"Extracted {tables_found} table(s). Results in: {out_dir}")


def process_pdfplumber_tables(pdf_path, pages=None):
    print(f"\n--- PDFPlumber Advanced Tables: {os.path.basename(pdf_path)} ---")
    out_dir = Path("output_pdfplumber") / Path(pdf_path).stem
    out_dir.mkdir(parents=True, exist_ok=True)

    all_tables = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pdf_pages = pdf.pages
            if pages:
                pdf_pages = [pdf_pages[p - 1] for p in pages if p - 1 < len(pdf_pages)]

            print(f"Analyzing {len(pdf_pages)} page(s) for tables...")

            for page_idx, page in enumerate(
                tqdm(pdf_pages, desc="Analyzing pages", unit="page")
            ):
                try:
                    # Try multiple extraction strategies
                    tables_strategy_1 = page.extract_tables(
                        {
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "explicit_vertical_lines": True,
                            "explicit_horizontal_lines": True,
                        }
                    )

                    tables_strategy_2 = page.extract_tables(
                        {
                            "vertical_strategy": "lines",
                            "horizontal_strategy": "lines",
                            "snap_tolerance": 3,
                            "snap_x_tolerance": 3,
                            "snap_y_tolerance": 3,
                        }
                    )

                    # Combine results from both strategies
                    combined_tables = tables_strategy_1 + tables_strategy_2

                    # Remove duplicates
                    unique_tables = []
                    seen_tables = set()
                    for table in combined_tables:
                        table_tuple = (
                            tuple(tuple(row) for row in table) if table else None
                        )
                        if (
                            table_tuple
                            and table_tuple not in seen_tables
                            and len(table) > 1
                        ):
                            seen_tables.add(table_tuple)
                            unique_tables.append(table)

                    if unique_tables:
                        for table in unique_tables:
                            if (
                                table and len(table) > 1
                            ):  # Require at least header + 1 row
                                all_tables.append(
                                    {
                                        "page": page_idx + 1,
                                        "data": table,
                                        "method": "pdfplumber_advanced",
                                    }
                                )

                except Exception as pe:
                    print(
                        f"Warning: Error processing page {page_idx + 1}: {str(pe)[:50]}"
                    )
                    continue

        if not all_tables:
            print("No tables found with advanced pdfplumber settings.")
            print("Trying basic extraction as fallback...")

            # Fallback to simple extraction
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_idx, page in enumerate(pdf.pages):
                        if pages and (page_idx + 1) not in pages:
                            continue
                        simple_tables = page.extract_tables()
                        for table in simple_tables:
                            if table and len(table) > 1:
                                all_tables.append(
                                    {
                                        "page": page_idx + 1,
                                        "data": table,
                                        "method": "pdfplumber_basic",
                                    }
                                )
            except Exception as e:
                pass

        if not all_tables:
            print("No tables found with any pdfplumber method.")
            return

        print(f"Found {len(all_tables)} table(s). Processing...")

        # Post-processing: clean empty cells and normalize data
        for i, table_dict in enumerate(
            tqdm(all_tables, desc="Processing tables", unit="table")
        ):
            # Clean and normalize table data
            cleaned_data = []
            for row in table_dict["data"]:
                cleaned_row = []
                for cell in row:
                    if cell is None:
                        cleaned_row.append("")
                    else:
                        # Clean whitespace and normalize
                        cleaned_cell = str(cell).strip()
                        cleaned_cell = " ".join(
                            cleaned_cell.split()
                        )  # Normalize whitespace
                        cleaned_row.append(cleaned_cell)
                cleaned_data.append(cleaned_row)

            # Create DataFrame
            df = pd.DataFrame(cleaned_data)

            # Save results
            page_num = table_dict.get("page", i + 1)
            table_num = i + 1
            csv_path = out_dir / f"table_{page_num}_{table_num}.csv"
            xlsx_path = out_dir / f"table_{page_num}_{table_num}.xlsx"

            df.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
            df.to_excel(xlsx_path, index=False)

            # Also save raw text version for reference
            with open(
                out_dir / f"table_{page_num}_{table_num}_raw.txt", "w", encoding="utf-8"
            ) as f:
                for row in cleaned_data:
                    f.write("|".join(row) + "\n")

        print(f"✅ Successfully extracted {len(all_tables)} table(s)")
        print(f"📁 Results saved in: {out_dir}")
        print(f"📊 Formats: CSV (semicolon-separated), Excel, and raw text")

    except Exception as e:
        print(f"❌ pdfplumber failed: {str(e)[:100]}")
        print("Consider trying Docling for complex table layouts.")


def show_menu():
    print("\n" + "=" * 50)
    print("         PDF OCR MASTER - MENU")
    print("=" * 50)
    print("1. Docling (IBM - Good for layout)")
    print("2. Marker (VikT0R - Best for formulas and text)")
    print("3. Docling Tables Only")
    print("4. PDFPlumber Advanced Tables (Enhanced extraction)")
    print("5. Exit")
    print("=" * 50)
    return input("Choose option (1-5): ")


def get_page_selection():
    val = input("Process all pages? (y/n): ").lower()
    if val == "y":
        return None
    else:
        pages_input = input("Enter pages/range (e.g. 1,3,5-10): ")
        pages = []
        try:
            for part in pages_input.split(","):
                if "-" in part:
                    s, e = map(int, part.split("-"))
                    pages.extend(range(s, e + 1))
                else:
                    pages.append(int(part))
            return pages
        except:
            print("Invalid format, processing all pages.")
            return None


def main():
    while True:
        choice = show_menu()
        if choice == "5":
            print("Goodbye!")
            break

        pdf_files = glob.glob("input_pdf/*.pdf")
        if not pdf_files:
            print("\n!!! ERROR: No PDF files found in 'input_pdf/' directory.")
            input("Press Enter to return to menu...")
            continue

        pages = get_page_selection()

        for pdf in pdf_files:
            if choice == "1":
                process_docling(pdf, "output_docling", pages)
            elif choice == "2":
                process_marker(pdf, "output_marker", pages)
            elif choice == "3":
                process_docling_tables(pdf, pages)
            elif choice == "4":
                process_pdfplumber_tables(pdf, pages)
            elif choice == "5":
                print("Goodbye!")
                return
            else:
                print("Invalid option.")
                break

        print("\nProcessing completed.")
        input("Press Enter to return to menu...")


if __name__ == "__main__":
    main()
