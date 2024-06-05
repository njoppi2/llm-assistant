import os
import fitz  # PyMuPDF
from difflib import SequenceMatcher

def similar(table, miner):
    return SequenceMatcher(None, table, miner).ratio()

def process_headers_footers(sorted_units, headers_footers, doc, type_to_process):
    for unit_tuple in zip(*sorted_units):
        for unitt in unit_tuple:
            similar_counter = sum(1 for rest in unit_tuple if similar(unitt['para'], rest['para']) > 0.8)
            if similar_counter > (len(sorted_units) - 5):
                a = " ".join(unitt['para'].split())
                for el in headers_footers:
                    if el['page'] == unitt['page']:
                        el[type_to_process].append(a)

def get_content_without_headers_and_footers(path):
    # Open the PDF file
    doc = fitz.open(path)
    sorted_footer_units = []
    sorted_header_units = []
    
    for page_nr in range(len(doc)):
        page = doc.load_page(page_nr)
        blocks = page.get_text("dict")["blocks"]
        p_height = page.rect.height
        units = []

        for block in blocks:
            if "lines" in block:
                for line_num in range(len(block["lines"])):
                    line = block["lines"][line_num]
                    line_content = []
                    for span in line["spans"]:
                        paragraph = span["text"]
                        if not paragraph.isspace():
                            line_content.append(paragraph)
                    if len(line_content) >= 0:
                        span = line['spans'][0]
                        units.append({'page': page_nr + 1, 'para': " ".join(line_content), 'x0': span["bbox"][0], 'y0': span["bbox"][1]})
        
        if not units:
            continue
        
        most_bottom_unit = sorted(units, key=lambda d: d['y0'], reverse=False)
        footer_area_units = []
        header_area_units = []

        for el in most_bottom_unit:
            if int(el['y0']) - p_height / 2 >= 0:
                header_area_units.append(el)
            if int(el['y0']) - p_height / 2 < 0:
                footer_area_units.append(el)

        header_area_units = sorted(header_area_units, key=lambda d: d['y0'], reverse=True)
        sorted_footer_units.append(footer_area_units)
        sorted_header_units.append(header_area_units)

    headers_footers = [{'page': i + 1, 'header': [], 'footer': []} for i in range(len(doc))]

    process_headers_footers(sorted_header_units, headers_footers, doc, 'header')
    process_headers_footers(sorted_footer_units, headers_footers, doc, 'footer')

    footers = []
    headers = []

    for el in headers_footers:
        counter_f = 0
        counter_h = 0
        if el['footer'] and el['header']:  # Check if the lists are not empty
            for rest in headers_footers:
                if rest['footer'] and similar(el['footer'], rest['footer']) > 0.7:  # Check if the list is not empty
                    counter_f += 1
                if rest['header'] and similar(el['header'], rest['header']) > 0.7:  # Check if the list is not empty
                    counter_h += 1
        if counter_f >= len(headers_footers) - 3:
            footers.append({'page': el['page'], 'footers': el['footer']})
        if counter_h >= len(headers_footers) - 3:
            headers.append({'page': el['page'], 'headers': el['header']})

    # Extract content excluding headers and footers
    content_without_headers_and_footers = []
    
    for page_nr in range(len(doc)):
        page = doc.load_page(page_nr)
        blocks = page.get_text("dict")["blocks"]
        units = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    line_content = []
                    for span in line["spans"]:
                        paragraph = span["text"]
                        if not paragraph.isspace():
                            is_header_or_footer = False
                            for hf in headers_footers:
                                if hf['page'] == page_nr + 1:
                                    for header in hf['header']:
                                        if similar(paragraph, header) > 0.8:
                                            is_header_or_footer = True
                                            break
                                    for footer in hf['footer']:
                                        if similar(paragraph, footer) > 0.8:
                                            is_header_or_footer = True
                                            break
                            if not is_header_or_footer:
                                line_content.append(paragraph)
                    if len(line_content) >= 0:
                        units.append(" ".join(line_content))
        if units:
            content_without_headers_and_footers.append({'page': page_nr + 1, 'content': units})

    return content_without_headers_and_footers

# Usage example
path_to_pdf = 'edital2.pdf'
output_file_name = path_to_pdf + '12.txt'
content = get_content_without_headers_and_footers(path_to_pdf)

if os.path.exists(output_file_name):
    # Delete the existing file
    os.remove(output_file_name)

with open(output_file_name, "a", encoding="utf-8") as file:
    # Loop through the data and append each item to the file
    for item_array in content:
        # Concatenate the elements in the sub-array with a space
        for item in item_array['content']:
            # Append the combined string to the file
            file.write(item + '\n')
