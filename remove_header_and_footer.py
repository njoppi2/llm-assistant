import os
import fitz  # PyMuPDF
from difflib import SequenceMatcher
import re

def similar(a, b):
    return SequenceMatcher(None, replace_numbers_with_zero(a), replace_numbers_with_zero(b)).ratio()

def replace_numbers_with_zero(s):
    # Use regular expression to find all numerical substrings
    return re.sub(r'\d+', '0', s)

def process_headers_footers(sorted_units, headers_footers, type_to_process):
    concatenated_units_from_0_to_n_all_per_page = []
    
    # Create concatenated units for each page
    for page_units in sorted_units:
        concatenated_page_units = []
        for i in range(len(page_units)):
            concatenated_text = " ".join(page_units[j]['para'] for j in range(i + 1))
            concatenated_page_units.append({
                'page': page_units[0]['page'],
                'para': concatenated_text,
                'start_index': 0,
                'end_index': i
            })
        concatenated_units_from_0_to_n_all_per_page.append(concatenated_page_units)

    biggest_similar_strings = None
    highest_similar_concatenated_units_number = 0

    for index, concatenated_page_units_from_0_to_n_per_page in enumerate(zip(*concatenated_units_from_0_to_n_all_per_page)):
        middle_index = len(concatenated_page_units_from_0_to_n_per_page) // 2
        middle_para = concatenated_page_units_from_0_to_n_per_page[middle_index]['para']
        
        # Calculate the similarity of the middle concatenated text with the rest
        similar_strings = []
        for concatenated_page_units_from_0_to_n in concatenated_page_units_from_0_to_n_per_page:
            for concatenated_page_units_from_0_to_n_2 in concatenated_page_units_from_0_to_n_per_page:
                similarity = similar(concatenated_page_units_from_0_to_n['para'], concatenated_page_units_from_0_to_n_2['para'])
                concatenated_page_units_from_0_to_n['similarity_sum'] = concatenated_page_units_from_0_to_n.get('similarity_sum', 0) + similarity
                concatenated_page_units_from_0_to_n['count'] = concatenated_page_units_from_0_to_n.get('count', 0) + 1

            if concatenated_page_units_from_0_to_n['similarity_sum'] / concatenated_page_units_from_0_to_n['count'] > 0.95:
                similar_strings.append(concatenated_page_units_from_0_to_n)

        doc_length = len(sorted_units)
        minimum_page_number_threshold = doc_length - 5
        total_similar_strings = len(similar_strings)
        if index > 5 and total_similar_strings < minimum_page_number_threshold:
            break

        if total_similar_strings >= (minimum_page_number_threshold):
            total_concatenated_units = len(middle_para.split())
            if total_concatenated_units > highest_similar_concatenated_units_number:
                highest_similar_concatenated_units_number = total_concatenated_units
                biggest_similar_strings = similar_strings

    if biggest_similar_strings:
        for unit in biggest_similar_strings:
            for el in headers_footers:
                if el['page'] == unit['page']:
                    for page_unit in sorted_units[unit['page'] - 1][unit['start_index']: unit['end_index'] + 1]:
                        if page_unit['para'] not in el[type_to_process]:
                            el[type_to_process].append(page_unit['para'])

def get_content_without_headers_and_footers(path):
    # Open the PDF file
    doc = fitz.open(path)
    sorted_header_units = []
    sorted_footer_units = []
    units = []
    
    for page_nr in range(len(doc)):
        page = doc.load_page(page_nr)
        blocks = page.get_text("dict")["blocks"]
        p_height = page.rect.height
        page_units = []

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
                        page_units.append({'page': page_nr + 1, 'para': " ".join(line_content), 'x0': span["bbox"][0], 'y0': span["bbox"][1]})
        
        if not page_units:
            continue
        
        units.extend(page_units)
        most_bottom_unit = sorted(page_units, key=lambda d: d['y0'], reverse=False)
        header_area_units = []
        footer_area_units = []

        for el in most_bottom_unit:
            if int(el['y0']) - p_height / 2 >= 0:
                footer_area_units.append(el)
            else:
                header_area_units.append(el)

        footer_area_units = sorted(footer_area_units, key=lambda d: d['y0'], reverse=True)
        sorted_footer_units.append(footer_area_units)
        sorted_header_units.append(header_area_units)

    headers_footers = [{'page': i + 1, 'header': [], 'footer': []} for i in range(len(doc))]

    process_headers_footers(sorted_footer_units, headers_footers, 'footer')
    process_headers_footers(sorted_header_units, headers_footers, 'header')

    footers = []
    headers = []

    for el in headers_footers:
        counter_f = 0
        counter_h = 0
        if el['footer'] and el['header']:
            for rest in headers_footers:
                if rest['footer'] and similar(" ".join([f for f in el['footer']]), " ".join([f for f in rest['footer']])) > 0.7:
                    counter_f += 1
                if rest['header'] and similar(" ".join([f for f in el['header']]), " ".join([f for f in rest['header']])) > 0.7:
                    counter_h += 1
        if counter_f >= len(headers_footers) - 3:
            footers.append({'page': el['page'], 'footers': el['footer']})
        if counter_h >= len(headers_footers) - 3:
            headers.append({'page': el['page'], 'headers': el['header']})

    # Remove headers and footers from units
    content_without_headers_and_footers = []
    for unit in units:
        is_header_or_footer = False
        for hf in headers_footers:
            if hf['page'] == unit['page']:
                for header in hf['header']:
                    if similar(unit['para'], header) > 0.8:
                        is_header_or_footer = True
                        break
                for footer in hf['footer']:
                    if similar(unit['para'], footer) > 0.8:
                        is_header_or_footer = True
                        break
        if not is_header_or_footer:
            content_without_headers_and_footers.append(unit)

    # Organize the content back into pages
    organized_content = []
    for page_nr in range(1, len(doc) + 1):
        page_content = [unit['para'] for unit in content_without_headers_and_footers if unit['page'] == page_nr]
        if page_content:
            organized_content.append({'page': page_nr, 'content': page_content})

    return organized_content

for i in range(1, 26):
    print(f"starting {i}")
    path_to_pdf = f'edital{i}.pdf'
    output_file_name = path_to_pdf + '.txt'
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