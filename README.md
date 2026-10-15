# CBSA BSF186A Customs Inventory Form Generator

[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

An automated generator for **Canada Border Services Agency (CBSA) Form BSF186A** (*Personal Effects Accounting Document (list of goods imported)*).

When relocating to Canada (as a permanent resident, work permit holder, returning citizen, or seasonal resident), the CBSA requires an itemized accounting of all personal effects accompanying you and goods to follow. Typing dozens or hundreds of items into static PDF forms by hand is tedious and difficult to paginate.

This tool reads a simple inventory spreadsheet (sample: `inventory.csv`), formats descriptions and serial numbers, calculates total declared values, and populates pixel-accurate vector SVG and printable multi-page PDF documents ready for CBSA border officials.

---

## ✨ Features

- **Standardized Pagination**: Automatically chunks inventory lists into official 26-item pages (`Page X of Y`), calculating required pages on the fly.
- **Pixel-Accurate SVG Vector Template**: Populates `templates/template.svg` with embedded font styles and official form dimensions without rasterization degradation.
- **Dynamic Text Scaling**: Automatically applies SVG `textLength` and `lengthAdjust` scaling for long descriptions (> 80 characters) to prevent text from overflowing table columns.
- **Serial Number & Value Formatting**:
  - Automatically merges serial numbers into the item description field: `Item (S/N: 12345678)`.
  - Normalizes duty values into standard currency strings (e.g., `$250.00`) and outputs the total sum of declared goods in CAD to the terminal.
- **Multi-Format Export (SVG & PDF)**:
  - Generates standalone `.svg` pages.
  - Automatically converts SVGs to PDFs using **Inkscape** (system binary or AppImage).
  - Automatically merges multi-page forms into a single unified document (`Canada_Inventory_All_Pages.pdf`) using `pdfunite`, `pdftk`, or Ghostscript (`gs`).
- **Zero Python Dependencies**: Written purely with Python's standard library (`xml.etree.ElementTree`, `csv`, `argparse`, `subprocess`). No `pip install` required!

---

## 📁 Repository Contents

| File / Folder | Description |
| :--- | :--- |
| `generate.py` | Main CLI script to parse inventory CSV and generate populated SVG/PDF forms. |
| `templates/template.svg` | Vector template of CBSA Form BSF186A containing predefined XML element IDs for form fields (isolated under Non-Commercial Reproduction terms). |
| `inventory.csv` | Sample inventory CSV containing item names, optional serial numbers, and declared duty values. |
| `LICENSE` | GNU General Public License v3.0 (GPL-3.0) with Section 7 Asset Exception & Non-Commercial Reproduction notice. |

---

## 🛠️ Prerequisites & Requirements

### 1. Python
- **Python 3.8+** (uses standard library only: `csv`, `xml.etree.ElementTree`, `argparse`, `math`, `shutil`, `subprocess`).

### 2. PDF Rendering (Optional, for PDF output)
To compile SVGs into printable PDFs, one of the following is required:
- **System Inkscape**: Installed and accessible in your system `PATH` (`which inkscape`):
  ```bash
  # Debian / Ubuntu
  sudo apt-get install inkscape

  # macOS (Homebrew)
  brew install inkscape

  # Fedora / RHEL
  sudo dnf install inkscape
  ```
- **Inkscape AppImage**: An executable AppImage located in the project directory (default: `./Inkscape-1.4.4.AppImage`) or specified via `--inkscape /path/to/inkscape`.

> **Note:** If Inkscape is not installed, pass `--no-pdf` to generate standard SVG files that can be viewed and printed directly from any modern web browser.

### 3. PDF Merging (Optional, for combined multi-page PDF)
To combine individual PDF pages into a single document, `generate.py` automatically detects and uses any one of:
- `pdfunite` (part of `poppler-utils`)
- `pdftk`
- `gs` (Ghostscript)

---

## 🚀 Quick Start

### 1. Edit Your Inventory
Update `inventory.csv` with your own belongings, serial numbers, and estimated replacement values (see [CSV Format](#-inventory-csv-format)).

### 2. Run the Generator
Run `generate.py`:
```bash
python3 generate.py
```
If you omit the `--importer` argument, the script will read your Git username (`git config user.name`) or prompt you interactively:
```text
Enter Name of Importer [Jane Doe]: Jane Doe
```

### 3. Check the Output
The generated forms will be saved to the `output/` directory:
```text
output/
├── page_01.svg
├── page_01.pdf
├── page_02.svg
├── page_02.pdf
└── Canada_Inventory_All_Pages.pdf    <-- Complete document to print
```

---

## 📊 Inventory CSV Format

The input CSV requires three columns (case-insensitive headers):

| Header Name | Accepted Aliases | Required? | Notes |
| :--- | :--- | :---: | :--- |
| `Item` | `item` | **Yes** | General description of the personal effect / household good. |
| `Serial Number(s)` | `serial number`, `serial` | No | Serial number(s) for electronics, appliances, or valuable items. |
| `Duty Value` | `duty`, `value` | **Yes** | Estimated value in Canadian Dollars (CAD). Can include `$` and commas. |

### Example `inventory.csv`:
```csv
Item,Serial Number(s),Duty Value
Books,,$150.00
"mattress/bedding (sheets, pillows, blankets)",,$200.00
outdoor patio furniture set,,$250.00
TV,43N31789UH03322,$100.00
Bath and kitchen rug/mats/towels,,$40.00
Electronics: MAC Apple Airbook,HUDH6QDKS3MA,$450.00
Furniture: Couch (large sectional with ottoman),,$600.00
Kitchen: Breville coffee maker and accessories,,$350.00
```

> **Tip:** If an item has multiple serial numbers or multi-line text in the CSV, newlines are automatically cleaned and separated with commas.

---

## ⚙️ Command-Line Options

Run `python3 generate.py --help` to view all available flags:

```text
usage: generate.py [-h] [--csv CSV] [--template TEMPLATE]
                   [--output-dir OUTPUT_DIR] [--importer IMPORTER]
                   [--doc-number DOC_NUMBER] [--goods-to-follow]
                   [--no-goods-to-follow] [--date DATE] [--no-pdf]
                   [--no-merge] [--inkscape INKSCAPE]
```

### Option Details

| Argument | Flag | Default | Description |
| :--- | :--- | :--- | :--- |
| `--csv` | `-i` | `inventory.csv` | Path to your input inventory CSV file. |
| `--template` | `-t` | `templates/template.svg` | Path to the base BSF186A SVG template. |
| `--output-dir` | `-o` | `output` | Directory where generated SVGs and PDFs will be written. |
| `--importer` | `-m` | Git user / Interactive | Full legal name of the importer as shown on your passport. |
| `--doc-number` | `-d` | *(blank)* | CBSA Document number. Leave blank unless you were already issued one. |
| `--goods-to-follow` | | `True` | Mark the checkbox for **"List of goods to follow"** (goods arriving separately). |
| `--no-goods-to-follow` | | | Uncheck **"List of goods to follow"** (e.g. for goods accompanying you at entry). |
| `--date` | | Today (`YYYY-MM-DD`) | Date stamped on the form. |
| `--no-pdf` | | `False` | Skip PDF rendering (produces only SVG pages). |
| `--no-merge` | | `False` | Render individual PDF pages but skip combining them into a single file. |
| `--inkscape` | | `./Inkscape-1.4.4.AppImage` | Custom path to Inkscape binary or AppImage. |

---

## 💡 Usage Examples

### 1. Fully Non-Interactive Generation (Goods to Follow)
```bash
python3 generate.py \
  --importer "Jane Doe" \
  --csv inventory.csv \
  --date 2026-10-15 \
  --output-dir ./output
```

### 2. Generating Form for "Goods Accompanying" (Carried with You)
By default, the script checks the "List of goods to follow" box. If you are preparing an inventory for goods currently in your vehicle or luggage accompanying you across the border, pass `--no-goods-to-follow`:
```bash
python3 generate.py \
  --importer "Jane Doe" \
  --csv accompanying_goods.csv \
  --no-goods-to-follow \
  --output-dir ./output_accompanying
```

### 3. SVG-Only Mode (No Inkscape Required)
If you do not have Inkscape installed or prefer printing directly from your browser:
```bash
python3 generate.py --no-pdf --importer "Jane Doe"
```
Open any generated `.svg` file in Google Chrome, Firefox, or Safari, and press `Ctrl+P` (or `Cmd+P`) to print to paper or save as PDF.

### 4. Custom Inkscape AppImage Path
```bash
python3 generate.py \
  --importer "Jane Doe" \
  --inkscape /opt/inkscape/inkscape-1.4.AppImage
```

---

## 🇨🇦 CBSA Border Crossing Tips

1. **Print Two Copies**: CBSA border officers will inspect your inventory, assign a file/document number, stamp both copies, retain one copy for CBSA records, and return the other stamped copy to you. Keep your stamped copy safe—you will need to present it to clear your "goods to follow" when shipments arrive.
2. **Valuation**: All declared values should represent **current fair market / replacement value** in **Canadian Dollars (CAD)**, not original purchase price.
3. **Serial Numbers**: Make sure serial numbers are listed for all major electronics (televisions, laptops, computers, high-end audio gear, power tools) and high-value appliances.
4. **Jewellery & High-Value Items**: Precious jewellery, heirloom collections, and artwork should ideally be photographed and accompanied by formal appraisals if values exceed standard settler exemptions.

> **NOTE:** This does not constitute legal or immigration advice. Please consult an immigration attorney, tax advisor, etc., for legal advice. This repository is not associated with the government of Canada, Canada Border Services Agency, or any immigration attorney or office. It is provided merely as a convenience to filling out the BSF186A form with an inventory list you have created. No guarantees or warranties are made.

---

## 📜 License & Legal Notices

This repository is distributed under a **split license**:

- **Software Code & Scripts** ([`generate.py`](generate.py)): Licensed under the [GNU General Public License v3.0](LICENSE).
- **Form Template Assets** ([`templates/template.svg`](templates/template.svg)): Derived from Canada Border Services Agency (CBSA) Form BSF186A (*Personal Effects Accounting Document - Continuation Sheet*), which is subject to Crown Copyright (Government of Canada). Pursuant to **Section 7 of the GNU GPL v3**, the template is provided under the **Government of Canada Non-Commercial Reproduction** terms:
  - Provided strictly for personal, public, and non-commercial administrative use.
  - Commercial reproduction, distribution, or re-sale of `templates/template.svg` is prohibited without prior written authorization from Public Services and Procurement Canada (PSPC).
  - Users must exercise due diligence in ensuring accuracy, acknowledge the CBSA as the source department, and not represent the materials as an official version or as having affiliation with or endorsement by the CBSA.
  - If using the software code (`generate.py`) under the GPL v3 in a commercial context, you must decouple and supply your own independent or properly authorized form templates.

For complete licensing terms and additional asset exceptions, please refer to the [LICENSE](LICENSE) file.
