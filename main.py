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


def get_docling():
    try:
        from docling.document_converter import DocumentConverter

        return DocumentConverter()
    except Exception:
        return None


def get_marker():
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        return PdfConverter(artifact_dict=create_model_dict())
    except Exception:
        return None


def process_docling(pdf_path, output_base, pages):
    print(f"\n--- Docling: {os.path.basename(pdf_path)} ---")
    converter = get_docling()
    if not converter:
        print("ERROR: Docling is not installed.")
        return
    result = converter.convert(pdf_path)
    out_dir = Path(f"output_docling") / Path(pdf_path).stem
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "document.md", "w", encoding="utf-8") as f:
        f.write(result.document.export_to_markdown())
    print(f"Results in: {out_dir}")


def process_marker(pdf_path, output_base, pages):
    print(f"\n--- Marker: {os.path.basename(pdf_path)} ---")
    converter = get_marker()
    if not converter:
        print("ERROR: Marker is not installed.")
        return
    from marker.output import text_from_rendered

    rendered = converter(pdf_path)
    full_text, _, images = text_from_rendered(rendered)
    out_dir = Path(output_base) / Path(pdf_path).stem
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "document.md", "w", encoding="utf-8") as f:
        f.write(full_text)

    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    for name, img in images.items():
        img.save(img_dir / name)
    print(f"Results in: {out_dir}")


def show_menu():
    print("\n" + "=" * 40)
    print("      PDF OCR MASTER - MENU")
    print("=" * 40)
    print("1. Docling (IBM - Good for layout)")
    print("2. Marker (VikT0R - Best for formulas and text)")
    print("3. Exit")
    print("=" * 40)
    return input("Choose option (1-3): ")


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
        if choice == "3":
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
            else:
                print("Invalid option.")
                break

        print("\nProcessing completed.")
        input("Press Enter to return to menu...")


if __name__ == "__main__":
    main()
