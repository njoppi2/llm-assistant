import os
import fitz  # PyMuPDF
from difflib import SequenceMatcher
import re
from pre_processing.functions import group_lines_into_paragraphs, group_units_in_lines

# Target percentage of data
target_percentage = 0.4

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
    all_page_widths = []
    units = []
    unit_count = 0
    
    for page_nr in range(doc_length):
        page = doc.load_page(page_nr)
        blocks = page.get_text("dict")["blocks"]
        p_height = page.rect.height
        all_page_widths.append(page.rect.width)
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
                        page_units.append(
                            {
                                'page': page_nr + 1,
                                'index': unit_count,
                                'para': " ".join(line_content),
                                'x0': first_span["bbox"][0],
                                'y0': first_span["bbox"][1],
                                'x1': last_span["bbox"][2],
                                'y1': last_span["bbox"][3],
                                'origin_x0': first_span['origin'][0],
                                'origin_y0': first_span['origin'][1],
                                'flags': first_span['flags'],
                                'bold': first_span['flags'] & 2**4,
                                'size': first_span['size'],
                                'color': first_span['color']
                            }
                        )
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
    pages_without_headers_and_footers = [] # SHOULD SIMPLY BE A NOT IN HEADERS_FOOTERS PER PAGE
    # just compare what units is to what headers_footers is
    for page_index in range(doc_length):
        page_nr = page_index + 1
        header_indexes_flattened = [index for d in headers if d.get('page') == page_nr for index in d['header_footer_indexes']]
        footer_indexes_flattened = [index for d in footers if d.get('page') == page_nr for index in d['header_footer_indexes']]
        header_footer_indexes = [*header_indexes_flattened, *footer_indexes_flattened]
        units_in_page_n = [u for u in units if u.get('page') == page_nr]
        pages_without_headers_and_footers.extend([u for u in units_in_page_n if u.get('index') not in header_footer_indexes])

    avg_page_width = sum(all_page_widths) / len(all_page_widths)
    pages_organized_by_lines = group_units_in_lines(pages_without_headers_and_footers, doc_length)
    all_paragraphs = group_lines_into_paragraphs(pages_organized_by_lines, target_percentage, doc_length, avg_page_width)


    # Initialize an empty list to hold all the content
    final_content = []

    # Loop through the data and build the final content string
    for paragraph in all_paragraphs:
        for line in paragraph:
            for unit in line:
                # Append the combined string to the list
                final_content.append(unit['para'])
        # Only break lines after a paragraph ending
        final_content.append('\n')

    # Join the final content list into a single string
    final_string = ''.join(final_content)

    return final_string

for i in range(1, 26):
    print(f"starting {i}")
    path_to_pdf = f'pdfs/edital{i}.pdf'
    output_file_name = f'pdfs/edital{i}_preprocessed{str(target_percentage)}.txt'
    final_string = get_content_without_headers_and_footers(path_to_pdf)

    if os.path.exists(output_file_name):
        # Delete the existing file
        os.remove(output_file_name)

    # Write the final string to the file once
    with open(output_file_name, "w", encoding="utf-8") as file:
        file.write(final_string)