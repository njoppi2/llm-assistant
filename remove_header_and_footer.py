import os
import fitz  # PyMuPDF
from difflib import SequenceMatcher
import re

def similar(a, b):
    return SequenceMatcher(None, replace_numbers_with_zero(a), replace_numbers_with_zero(b)).ratio()

def replace_numbers_with_zero(s):
    # Use regular expression to find all numerical substrings
    return re.sub(r'\d+', '0', s)

def process_headers_footers(sorted_units):
    doc_length = len(sorted_units)
    concatenated_units_from_0_to_n_all_per_page = []
    headers_footers = []
    biggest_similar_strings = None
    highest_similar_concatenated_units_number = 0
    
    # Create concatenated units for each page
    for page_units in sorted_units:
        concatenated_page_units = []
        for i in range(len(page_units)):
            concatenated_text = " ".join(page_units[j]['para'] for j in range(i + 1))
            indexes = [page_units[j]['index'] for j in range(i + 1)]
            concatenated_page_units.append({
                'page': page_units[0]['page'],
                'para': concatenated_text,
                'indexes': indexes
            })
        concatenated_units_from_0_to_n_all_per_page.append(concatenated_page_units)


    for index, concatenated_page_units_from_0_to_n_per_page in enumerate(zip(*concatenated_units_from_0_to_n_all_per_page)):
        
        # Calculate the similarity of the middle concatenated text with the rest
        similar_strings = []
        for concatenated_page_units_from_0_to_n in concatenated_page_units_from_0_to_n_per_page:
            for concatenated_page_units_from_0_to_n_2 in concatenated_page_units_from_0_to_n_per_page:
                similarity = similar(concatenated_page_units_from_0_to_n['para'], concatenated_page_units_from_0_to_n_2['para'])
                concatenated_page_units_from_0_to_n['similarity_sum'] = concatenated_page_units_from_0_to_n.get('similarity_sum', 0) + similarity
                concatenated_page_units_from_0_to_n['count'] = concatenated_page_units_from_0_to_n.get('count', 0) + 1

            if concatenated_page_units_from_0_to_n['similarity_sum'] / concatenated_page_units_from_0_to_n['count'] > 0.95:
                similar_strings.append(concatenated_page_units_from_0_to_n)

        minimum_page_number_threshold = doc_length - 5
        total_similar_strings = len(similar_strings)
        if index > 5 and total_similar_strings < minimum_page_number_threshold:
            break

        if total_similar_strings >= (minimum_page_number_threshold):
            total_concatenated_units = len(concatenated_page_units_from_0_to_n['indexes'])
            if total_concatenated_units > highest_similar_concatenated_units_number:
                highest_similar_concatenated_units_number = total_concatenated_units
                biggest_similar_strings = similar_strings

    if biggest_similar_strings:
        for bss_page_n in biggest_similar_strings:
            headers_footers.append({'page': bss_page_n['page'], 'header_footer_indexes': bss_page_n['indexes']})

    return headers_footers

def get_content_without_headers_and_footers(path):
    # Open the PDF file
    doc = fitz.open(path)
    doc_length = len(doc)
    sorted_header_units = []
    sorted_footer_units = []
    units = []
    unit_count = 0
    
    for page_nr in range(doc_length):
        page = doc.load_page(page_nr)
        blocks = page.get_text("dict")["blocks"]
        p_height = page.rect.height
        page_units = []

        for block in blocks:
            if "lines" in block:
                for line_num in range(len(block["lines"])):
                    line = block["lines"][line_num]
                    line_content = []
                    for first_span in line["spans"]:
                        paragraph = first_span["text"]
                        if not paragraph.isspace():
                            line_content.append(paragraph)
                    if len(line_content) >= 0:
                        first_span = line['spans'][0]
                        last_span = line['spans'][-1]
                        page_units.append({'page': page_nr + 1, 'index': unit_count, 'para': " ".join(line_content), 'x0': first_span["bbox"][0], 'y0': first_span["bbox"][1], 'x1': last_span["bbox"][2], 'y1': last_span["bbox"][3]})
                        unit_count += 1
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

    footers = process_headers_footers(sorted_footer_units)
    headers = process_headers_footers(sorted_header_units)

    # Remove headers and footers from units
    content_without_headers_and_footers = [] # SHOULD SIMPLY BE A NOT IN HEADERS_FOOTERS PER PAGE
    # just compare what units is to what headers_footers is
    for page_index in range(doc_length):
        page_nr = page_index + 1
        header_indexes_flattened = [index for d in headers if d.get('page') == page_nr for index in d['header_footer_indexes']]
        footer_indexes_flattened = [index for d in footers if d.get('page') == page_nr for index in d['header_footer_indexes']]
        header_footer_indexes = [*header_indexes_flattened, *footer_indexes_flattened]
        units_in_page_n = [u for u in units if u.get('page') == page_nr]
        content_without_headers_and_footers.extend([u for u in units_in_page_n if u.get('index') not in header_footer_indexes])

    # Organize the content into paragraphs
    organized_content = []
    paragraph = []
    for page_nr in range(1, doc_length + 1):
        for unit_index, unit in enumerate(content_without_headers_and_footers):
            if unit.get('page') > page_nr:
                break
            elif unit.get('page') < page_nr:
                continue
            
            previous_unit = content_without_headers_and_footers[unit_index - 1]
            smallest_y = min(previous_unit['y0'], unit['y0'])
            biggest_y = max(previous_unit['y1'], unit['y1'])
            previout_unit_height = previous_unit['y1'] - previous_unit['y0']
            unit_height = unit['y1'] - unit['y0']

            is_in_same_line = (biggest_y - smallest_y) < 1.5 * previout_unit_height and (biggest_y - smallest_y) < 1.5 * unit_height
            
            if previous_unit['x1'] < 555 and not is_in_same_line:
                organized_content.append("".join(paragraph))
                paragraph = []
            unit_text = unit['para']
            paragraph.append(unit_text)

    if paragraph:
        organized_content.append("".join(paragraph))
    return organized_content

for i in range(1, 2):
    print(f"starting {i}")
    path_to_pdf = f'edital{i}.pdf'
    output_file_name = path_to_pdf + '_preprocessed2.txt'
    content = get_content_without_headers_and_footers(path_to_pdf)

    if os.path.exists(output_file_name):
        # Delete the existing file
        os.remove(output_file_name)

    with open(output_file_name, "a", encoding="utf-8") as file:
        # Loop through the data and append each item to the file
        for item in content:
            # Append the combined string to the file
            file.write(item + '\n')