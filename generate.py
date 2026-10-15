#!/usr/bin/env python3
"""
Customs Form Generator for Canada Border Services Agency (CBSA) BSF186A
Generates filled SVG and PDF pages from an input inventory CSV.
"""

import os
import sys
import csv
import math
import shutil
import datetime
import argparse
import subprocess
import xml.etree.ElementTree as ET

# Default paths and settings
DEFAULT_INKSCAPE_PATH = "./Inkscape-1.4.4.AppImage"
DEFAULT_TEMPLATE_SVG = "templates/template.svg"
DEFAULT_INVENTORY_CSV = "inventory.csv"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_PDF_SOURCE = "https://www.cbsa-asfc.gc.ca/publications/forms-formulaires/bsf186a.pdf"
ROWS_PER_PAGE = 26


def find_inkscape(preferred_path: str = DEFAULT_INKSCAPE_PATH) -> str | None:
    """Find a usable Inkscape executable or AppImage."""
    if preferred_path and os.path.exists(preferred_path):
        return preferred_path
    path = shutil.which("inkscape")
    if path:
        return path
    return None


def get_default_importer_name() -> str:
    """Attempt to get a default importer name from git config or environment."""
    try:
        res = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=False,
        )
        name = res.stdout.strip()
        if name:
            return name
    except Exception:
        pass
    return "No Name"


def load_inventory(csv_path: str) -> tuple[list[dict], float]:
    """
    Read inventory CSV and return list of formatted items and total declared duty value.
    Each item dict has keys: 'description', 'duty', 'item', 'serial'.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Inventory CSV not found at '{csv_path}'")

    items = []
    total_duty = 0.0

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Normalize header map (strip whitespace and lower-case)
        header_map = {col.strip().lower(): col for col in (reader.fieldnames or [])}

        item_col = header_map.get("item")
        sn_col = header_map.get("serial number(s)") or header_map.get("serial number") or header_map.get("serial")
        duty_col = header_map.get("duty value") or header_map.get("duty") or header_map.get("value")

        if not item_col or not duty_col:
            raise ValueError(
                f"CSV must contain 'Item' and 'Duty Value' columns. Found columns: {reader.fieldnames}"
            )

        for row in reader:
            raw_item = row.get(item_col, "").strip()
            if not raw_item:
                continue

            raw_sn = row.get(sn_col, "").strip() if sn_col else ""
            raw_duty = row.get(duty_col, "").strip()

            # Format serial numbers: replace newlines with comma-space
            sn_clean = ", ".join(line.strip() for line in raw_sn.splitlines() if line.strip())

            # Combine Item and Serial Number for Description column
            if sn_clean:
                description = f"{raw_item} (S/N: {sn_clean})"
            else:
                description = raw_item

            # Format duty value: ensure currency formatting if numeric
            duty_clean = raw_duty
            duty_num_str = raw_duty.replace("$", "").replace(",", "").strip()
            try:
                duty_num = float(duty_num_str)
                total_duty += duty_num
                if not duty_clean.startswith("$"):
                    duty_clean = f"${duty_num:,.2f}"
            except ValueError:
                pass

            items.append({
                "item": raw_item,
                "serial": sn_clean,
                "description": description,
                "duty": duty_clean,
            })

    return items, total_duty


def populate_page_xml(
    tree_root: ET.Element,
    page_num: int,
    total_pages: int,
    importer_name: str,
    doc_number: str,
    goods_to_follow: bool,
    date_str: str,
    page_items: list[dict],
) -> None:
    """Populate SVG XML tree in-place for a specific page."""
    # Mapping for direct element ID updates
    field_updates = {
        "field_page_num": str(page_num),
        "field_page_total": str(total_pages),
        "field_importer_name": importer_name,
        "field_doc_num": doc_number,
        "field_goods_to_follow": "X" if goods_to_follow else "",
        "field_date": date_str,
    }

    # Update item rows (1 to ROWS_PER_PAGE)
    for i in range(1, ROWS_PER_PAGE + 1):
        idx = i - 1
        if idx < len(page_items):
            desc = page_items[idx]["description"]
            duty = page_items[idx]["duty"]
        else:
            desc = ""
            duty = ""

        field_updates[f"field_desc_{i}"] = desc
        field_updates[f"field_duty_{i}"] = duty

    # Find and update each element in the XML tree
    for elem_id, value in field_updates.items():
        elem = tree_root.find(f".//*[@id='{elem_id}']")
        if elem is not None:
            elem.text = value
            # Handle long item descriptions to prevent overlapping columns
            if elem_id.startswith("field_desc_") and len(value) > 80:
                elem.set("textLength", "530")
                elem.set("lengthAdjust", "spacingAndGlyphs")
            elif elem_id.startswith("field_desc_") and "textLength" in elem.attrib:
                del elem.attrib["textLength"]
                if "lengthAdjust" in elem.attrib:
                    del elem.attrib["lengthAdjust"]


def merge_pdfs(pdf_paths: list[str], output_pdf: str) -> bool:
    """Merge multiple PDFs into a single file using pdfunite, pdftk, or gs."""
    if not pdf_paths:
        return False

    # Try pdfunite first
    if shutil.which("pdfunite"):
        try:
            subprocess.run(
                ["pdfunite", *pdf_paths, output_pdf],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except subprocess.SubprocessError:
            pass

    # Try pdftk
    if shutil.which("pdftk"):
        try:
            subprocess.run(
                ["pdftk", *pdf_paths, "cat", "output", output_pdf],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except subprocess.SubprocessError:
            pass

    # Try ghostscript
    if shutil.which("gs"):
        try:
            subprocess.run([
                "gs",
                "-q",
                "-dNOPAUSE",
                "-dBATCH",
                "-sDEVICE=pdfwrite",
                f"-sOutputFile={output_pdf}",
                *pdf_paths,
            ], check=True)
            return True
        except subprocess.SubprocessError:
            pass

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate filled Canadian customs forms (BSF186A) from an inventory CSV."
    )
    parser.add_argument(
        "--csv", "-i",
        default=DEFAULT_INVENTORY_CSV,
        help=f"Path to input inventory CSV (default: '{DEFAULT_INVENTORY_CSV}')",
    )
    parser.add_argument(
        "--template", "-t",
        default=DEFAULT_TEMPLATE_SVG,
        help=f"Path to SVG template (default: '{DEFAULT_TEMPLATE_SVG}')",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: '{DEFAULT_OUTPUT_DIR}')",
    )
    parser.add_argument(
        "--importer", "-m",
        help="Name of importer (prompted interactively if omitted)",
    )
    parser.add_argument(
        "--doc-number", "-d",
        default="",
        help="Document number (default: blank, CBSA assigns at border)",
    )
    parser.add_argument(
        "--goods-to-follow",
        action="store_true",
        default=True,
        help="Check 'List of goods to follow' (default: True)",
    )
    parser.add_argument(
        "--no-goods-to-follow",
        action="store_false",
        dest="goods_to_follow",
        help="Uncheck 'List of goods to follow'",
    )
    parser.add_argument(
        "--date",
        help="Date on form in YYYY-MM-DD or preferred format (default: today's date)",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Skip PDF rendering (generate SVGs only)",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Skip merging individual PDFs into a combined multi-page PDF",
    )
    parser.add_argument(
        "--inkscape",
        default=DEFAULT_INKSCAPE_PATH,
        help="Path to Inkscape AppImage or executable",
    )

    args = parser.parse_args()

    # Determine importer name
    importer_name = args.importer
    if not importer_name:
        default_name = get_default_importer_name()
        if sys.stdin.isatty():
            entered = input(f"Enter Name of Importer [{default_name}]: ").strip()
            importer_name = entered if entered else default_name
        else:
            importer_name = default_name

    # Determine date
    date_str = args.date or datetime.date.today().strftime("%Y-%m-%d")

    # Locate template and verify
    template_path = args.template
    if not os.path.exists(template_path):
        if template_path == DEFAULT_TEMPLATE_SVG and os.path.exists("template.svg"):
            template_path = "template.svg"
        elif template_path == "template.svg" and os.path.exists(DEFAULT_TEMPLATE_SVG):
            template_path = DEFAULT_TEMPLATE_SVG
        else:
            print(f"❌ Error: Template SVG not found at '{template_path}'")
            sys.exit(1)

    # Load inventory data
    try:
        items, total_duty = load_inventory(args.csv)
    except Exception as e:
        print(f"❌ Error loading inventory CSV: {e}")
        sys.exit(1)

    total_items = len(items)
    if total_items == 0:
        print("⚠️ Warning: Inventory is empty, no items found.")
        total_pages = 1
    else:
        total_pages = math.ceil(total_items / ROWS_PER_PAGE)

    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 60)
    print("📋 CBSA Form BSF186A Generator")
    print("=" * 60)
    print(f"• Input CSV:       {args.csv} ({total_items} items)")
    print(f"• Importer Name:   {importer_name}")
    print(f"• Document Number: {args.doc_number or '(None / Blank)'}")
    print(f"• Goods to Follow: {'Checked [X]' if args.goods_to_follow else 'Unchecked [ ]'}")
    print(f"• Date:            {date_str}")
    print(f"• Total Pages:     {total_pages} pages ({ROWS_PER_PAGE} items/page)")
    print(f"• Total Duty Sum:  ${total_duty:,.2f} CAD")
    print(f"• Output Dir:      {os.path.abspath(args.output_dir)}")
    print("=" * 60)

    # Parse template SVG
    # Register namespaces to preserve Inkscape/sodipodi formatting
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("sodipodi", "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd")
    ET.register_namespace("inkscape", "http://www.inkscape.org/namespaces/inkscape")

    template_tree = ET.parse(template_path)

    svg_paths = []
    print("\n[1/3] Generating SVG pages...")
    for p in range(1, total_pages + 1):
        start_idx = (p - 1) * ROWS_PER_PAGE
        end_idx = min(start_idx + ROWS_PER_PAGE, total_items)
        page_items = items[start_idx:end_idx]

        # Make a deep copy of the template tree
        page_root = ET.fromstring(ET.tostring(template_tree.getroot(), encoding="utf-8"))
        populate_page_xml(
            page_root,
            page_num=p,
            total_pages=total_pages,
            importer_name=importer_name,
            doc_number=args.doc_number,
            goods_to_follow=args.goods_to_follow,
            date_str=date_str,
            page_items=page_items,
        )

        svg_out_path = os.path.join(args.output_dir, f"page_{p:02d}.svg")
        tree_out = ET.ElementTree(page_root)
        tree_out.write(svg_out_path, encoding="utf-8", xml_declaration=True)
        svg_paths.append(svg_out_path)
        print(f"   ✓ Generated {svg_out_path} ({len(page_items)} items)")

    # Convert to PDF if requested
    pdf_paths = []
    inkscape_bin = find_inkscape(args.inkscape)
    if not args.no_pdf and inkscape_bin:
        print("\n[2/3] Exporting SVGs to PDF via Inkscape...")
        try:
            # Batch export all SVGs to PDF in one run
            cmd = [
                inkscape_bin,
                "--export-type=pdf",
                *svg_paths,
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for svg_path in svg_paths:
                pdf_path = os.path.splitext(svg_path)[0] + ".pdf"
                if os.path.exists(pdf_path):
                    pdf_paths.append(pdf_path)
            print(f"   ✓ Successfully compiled {len(pdf_paths)} PDF pages.")
        except Exception as e:
            print(f"   ❌ Inkscape export failed: {e}")
    elif not args.no_pdf and not inkscape_bin:
        print("\n[2/3] ⚠️ Inkscape binary not found. Skipped PDF generation.")
        print(f"      To enable PDF export, specify --inkscape /path/to/inkscape")
    else:
        print("\n[2/3] PDF generation skipped (--no-pdf).")

    # Merge PDFs if requested
    if pdf_paths and not args.no_merge:
        print("\n[3/3] Merging pages into complete document...")
        merged_pdf = os.path.join(args.output_dir, "Canada_Inventory_All_Pages.pdf")
        if merge_pdfs(pdf_paths, merged_pdf):
            print(f"   ✓ Created complete printable document: {merged_pdf}")
        else:
            print("   ⚠️ Could not merge PDFs (pdfunite/pdftk/gs not available).")
    else:
        print("\n[3/3] PDF merge skipped.")

    print("\n✨ Done! All pages ready.")


if __name__ == "__main__":
    main()
