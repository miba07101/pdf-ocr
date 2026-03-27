import os
import glob
from pathlib import Path


# --- Dynamické Importy ---
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


# --- Spracovateľské funkcie ---


def process_docling(pdf_path, output_base, pages):
    print(f"\n--- Docling: {os.path.basename(pdf_path)} ---")
    converter = get_docling()
    if not converter:
        print("Chyba: Docling nie je nainštalovaný.")
        return

    result = converter.convert(pdf_path)
    pdf_name = Path(pdf_path).stem
    out_dir = Path(f"output_docling") / pdf_name
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "document.md", "w", encoding="utf-8") as f:
        f.write(result.document.export_to_markdown())

    table_count = 0
    if hasattr(result.document, "tables") and result.document.tables:
        table_dir = out_dir / "tables"
        table_dir.mkdir(parents=True, exist_ok=True)

        for table_ix, table in enumerate(result.document.tables):
            try:
                import pandas as pd

                table_df = table.export_to_dataframe(doc=result.document)

                table_file = table_dir / f"table_{table_ix + 1}.csv"
                table_df.to_csv(table_file, index=False, encoding="utf-8-sig")
                table_count += 1
                print(f"  Tabuľka {table_ix + 1}: {table_file.name}")
            except Exception as e:
                print(f"  Chyba pri exporte tabuľky {table_ix + 1}: {e}")

    print(f"Výsledok v: {out_dir}")
    if table_count > 0:
        print(f"  Exportované tabuľky: {table_count}x CSV")


def process_tables_only(pdf_path, output_base, pages):
    print(f"\n--- Tabuľky (Docling): {os.path.basename(pdf_path)} ---")
    converter = get_docling()
    if not converter:
        print("Chyba: Docling nie je nainštalovaný.")
        return

    result = converter.convert(pdf_path)
    pdf_name = Path(pdf_path).stem
    out_dir = Path(f"output_tables") / pdf_name
    out_dir.mkdir(parents=True, exist_ok=True)

    table_count = 0
    if hasattr(result.document, "tables") and result.document.tables:
        for table_ix, table in enumerate(result.document.tables):
            try:
                import pandas as pd

                table_df = table.export_to_dataframe(doc=result.document)

                table_file = out_dir / f"table_{table_ix + 1}.csv"
                table_df.to_csv(table_file, index=False, encoding="utf-8-sig")
                table_count += 1
                print(f"  Tabuľka {table_ix + 1}: {table_file.name}")
            except Exception as e:
                print(f"  Chyba pri exporte tabuľky {table_ix + 1}: {e}")
    else:
        print("  Žiadne tabuľky sa nenašli.")

    print(f"Výsledok v: {out_dir}")
    print(f"  Exportované tabuľky: {table_count}")


def process_marker(pdf_path, output_base, pages):
    print(f"\n--- Marker: {os.path.basename(pdf_path)} ---")
    converter = get_marker()
    if not converter:
        print("Chyba: Marker nie je nainštalovaný.")
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
    print(f"Výsledok v: {out_dir}")


def show_menu():
    print("\n" + "=" * 40)
    print("      PDF OCR MASTER - MENU")
    print("=" * 40)
    print("1. Docling (text + tabuľky do CSV)")
    print("2. Marker (najlepšie na LaTeX a text)")
    print("3. Len tabuľky (iba CSV export)")
    print("4. Exit")
    print("=" * 40)
    return input("Vyber si možnosť (1-4): ")


def get_page_selection():
    val = input("Spracovať všetky strany? (y/n): ").lower()
    if val == "y":
        return None
    else:
        pages_input = input("Zadaj strany/rozsah (napr. 1,3,5-10): ")
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
            print("Neplatný formát, spracujem všetky strany.")
            return None


def main():
    while True:
        choice = show_menu()
        if choice == "4":
            print("Maj sa!")
            break

        pdf_files = glob.glob("input_pdf/*.pdf")
        if not pdf_files:
            print("\n!!! Chyba: V priečinku 'input_pdf/' nie sú žiadne PDF súbory.")
            input("Stlač Enter pre návrat do menu...")
            continue

        pages = get_page_selection()

        for pdf in pdf_files:
            if choice == "1":
                process_docling(pdf, "output_docling", pages)
            elif choice == "2":
                process_marker(pdf, "output_marker", pages)
            elif choice == "3":
                process_tables_only(pdf, "output_tables", pages)
            else:
                print("Neplatná voľba.")
                break

        print("\nSpracovanie dokončené.")
        input("Stlač Enter pre návrat do menu...")


if __name__ == "__main__":
    main()
