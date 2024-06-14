import numpy as np
from scipy.stats import gaussian_kde
from scipy.signal import find_peaks
import math
import matplotlib.pyplot as plt
import re


def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx

def find_optimal_bounds(cdf_values, peak_idx, target_percentage):
    lower_bound_idx = peak_idx
    upper_bound_idx = peak_idx

    total_data_percentage = 0

    while total_data_percentage < target_percentage and (lower_bound_idx > 0 or upper_bound_idx < len(cdf_values) - 1):
        if lower_bound_idx > 0:
            lower_bound_idx -= 1
        if upper_bound_idx < len(cdf_values) - 1:
            upper_bound_idx += 1

        total_data_percentage = cdf_values[upper_bound_idx] - cdf_values[lower_bound_idx]

    return lower_bound_idx, upper_bound_idx

def calculate_data_concentration_and_bounds(pages_organized_by_lines, target_percentage, num_peaks, bw_method, feature_list):
    # Calculate the KDE with a smaller bandwidth
    kde = gaussian_kde(feature_list, bw_method=bw_method)
    feature_range = np.linspace(min(feature_list), max(feature_list), 1000)
    kde_values = kde(feature_range)

    # Find all peaks of the KDE
    peaks, _ = find_peaks(kde_values, height=np.max(kde_values) * 0.1)  # You can adjust the 'height' parameter as needed
    peak_values = feature_range[peaks]

    # Sort the peaks by their KDE value in descending order and select the top num_peaks peaks
    sorted_peaks = sorted(peaks, key=lambda idx: kde_values[idx], reverse=True)[:num_peaks]
    selected_peak_features = feature_range[sorted_peaks]

    results = []

    # Calculate the CDF of the KDE
    cdf_values = np.cumsum(kde_values)
    cdf_values /= cdf_values[-1]  # Normalize to make it a proper CDF

    for peak_value in selected_peak_features:
        # Find the index of the peak in feature
        peak_idx = find_nearest(feature_range, peak_value)

        # Find the optimal bounds
        lower_bound_idx, upper_bound_idx = find_optimal_bounds(cdf_values, peak_idx, target_percentage)

        # Get the actual feature for these indices
        lower_bound = feature_range[lower_bound_idx]
        upper_bound = feature_range[upper_bound_idx]

        # Calculate the standard deviation of the filtered feature within this interval
        filtered_value = [v for v in feature_list if lower_bound <= v <= upper_bound]
        std_deviation = np.std(filtered_value)
        variance = math.sqrt(std_deviation)

        results.append({
            'std_deviation': std_deviation,
            'variance': variance,
            'lower_bound': lower_bound,
            'peak_value': peak_value,
            'upper_bound': upper_bound,
        })

    # # Plot histogram and KDE with the bounds
    # plt.figure(figsize=(10, 6))
    # plt.hist(feature_list, bins=50, color='blue', alpha=0.7, label='ends feature', density=True)
    # plt.plot(feature_range, kde_values, color='red', label='KDE')
    
    # for result in results:
    #     plt.axvline(result['peak_value'], color='green', linestyle='--', label=f'Peak: {result["peak_value"]:.2f}')
    #     plt.axvline(result['lower_bound'], color='purple', linestyle='--', label=f'Lower Bound: {result["lower_bound"]:.2f}')
    #     plt.axvline(result['upper_bound'], color='orange', linestyle='--', label=f'Upper Bound: {result["upper_bound"]:.2f}')
    
    # plt.xlabel('feature')
    # plt.ylabel('Density')
    # plt.title(f'Histogram and KDE of feature with {target_percentage*100:.0f}% Data Interval')
    # plt.legend()
    # plt.grid(True)
    # plt.show()

    for i, result in enumerate(results, 1):
        print(f"Peak {i} results:")
        print('std_deviation: ', result['std_deviation'])
        print('variance: ', result['variance'])
        print('lower_bound: ', result['lower_bound'])
        print('peak_value: ', result['peak_value'])
        print('upper_bound: ', result['upper_bound'])
        print('target_percentage: ', target_percentage)
        print()

    return results



def calculate_right_aligment(pages_organized_by_lines, target_percentage, avg_page_width):
    num_peaks, bw_method = 1, 0.03
    all_line_ends_x_coord = [line_unit[-1]['x1'] for line_unit in pages_organized_by_lines if line_unit[-1]['x1'] > avg_page_width * 0.6]
    results = calculate_data_concentration_and_bounds(pages_organized_by_lines, target_percentage, num_peaks, bw_method, all_line_ends_x_coord)
    return results[0]

def calculate_vertical_alignment(pages_organized_by_lines, target_percentage):
    num_peaks, bw_method = 2, 0.2
    all_line_vertical_distances = []

    for i in range(len(pages_organized_by_lines) - 1):
        prev_line = pages_organized_by_lines[i]
        curr_line = pages_organized_by_lines[i + 1]
        feature_diff = curr_line[-1]['origin_y0'] - prev_line[-1]['origin_y0']
        
        if feature_diff < 0 or curr_line[-1]['page'] != prev_line[-1]['page']:
            continue
        all_line_vertical_distances.append(feature_diff)
    
    results = calculate_data_concentration_and_bounds(pages_organized_by_lines, target_percentage, num_peaks, bw_method, all_line_vertical_distances
    )

    formatted_results = {
        'mid_paragraph_spacing': min(results, key=lambda x: x['peak_value']),
        'outer_paragraph_spacing': max(results, key=lambda x: x['peak_value']),
    }
    return formatted_results

def group_units_in_lines(pages_without_headers_and_footers, doc_length):
    # Organize the content into paragraphs
    pages_organized_by_lines = []
    line = []

    for page_nr in range(1, doc_length + 1):
        for unit_index, unit in enumerate(pages_without_headers_and_footers):
            if unit.get('page') > page_nr:
                break
            elif unit.get('page') < page_nr:
                continue
            elif unit_index == 0:
                line.append(unit)
                continue
            
            previous_unit = pages_without_headers_and_footers[unit_index - 1]
            smallest_y = min(previous_unit['y0'], unit['y0'])
            biggest_y = max(previous_unit['y1'], unit['y1'])
            previout_unit_height = previous_unit['y1'] - previous_unit['y0']
            unit_height = unit['y1'] - unit['y0']

            is_in_same_line = (biggest_y - smallest_y) < 1.5 * previout_unit_height and (biggest_y - smallest_y) < 1.5 * unit_height
            
            if not is_in_same_line:
                assert line[0]['page'] == line[-1]['page']
                pages_organized_by_lines.append(line)
                line = []
            line.append(unit)
    if line:
        pages_organized_by_lines.append(line)

    return pages_organized_by_lines

def ends_with_punctuation(s):
    # Remove trailing spaces
    stripped_string = s.rstrip()
    return stripped_string.endswith(';') or stripped_string.endswith('.') or stripped_string.endswith(':')

# def vertical_distance_diff(curr_line, prev_line, prev2_line):
#     """
#     Calculates how the vertical distance between the current and previous line compares to another vertical distance.
#     Positive values indicates higher probability of curr and prev being in the same paragraph
#     """
#     if curr_line[0]['page'] != prev_line[0]['page'] or prev_line[0]['page'] != prev2_line[0]['page']:
#         return 0
    
#     curr_prev_distance = curr_line[0]['origin_y0'] - prev_line[0]['origin_y0']
#     prev_prev2_distance = prev_line[0]['origin_y0'] - prev2_line[0]['origin_y0']
#     distance_difference = prev_prev2_distance - curr_prev_distance

#     return distance_difference

def is_roman_number(num):
    pattern = re.compile(r"""   
                                ^M{0,3}            # Thousands - 0 to 3000
                                (CM|CD|D?C{0,3})   # Hundreds - 900 (CM), 400 (CD), 0-300 (0-3 Cs), or 500-800 (D followed by 0-3 Cs)
                                (XC|XL|L?X{0,3})   # Tens - 90 (XC), 40 (XL), 0-30 (0-3 Xs), or 50-80 (L followed by 0-3 Xs)
                                (IX|IV|V?I{0,3})   # Units - 9 (IX), 4 (IV), 0-3 (0-3 Is), or 5-8 (V followed by 0-3 Is)
                                $""", re.VERBOSE | re.IGNORECASE)  # End of string, case insensitive
    return bool(re.match(pattern, num))

def get_items_and_separators(s):
    # Split the string by the first space and take the first group
    first_group = s.split(' ')[0]
    # Get the list of all separators in first_group
    separators = re.findall(r'[^0-9A-Za-z+*]', first_group)

    # Split the first group into segments using the specified separators
    segments = re.split(r'[^0-9A-Za-z+*]', first_group)
    item_level = 0

    for i, segment in enumerate(segments):
        if segment and (segment.isdigit() or (segment.isalpha() and len(segment) == 1) or is_roman_number(segment)):
            # Check if it's the last segment and if it's immediately followed by a separator
            if i + 1 < len(segments):
                item_level += 1
            elif i + 1 == len(segments) and len(first_group) > sum(map(len, segments)) + len(separators):
                item_level += 1
    
    return item_level, separators

def calculate_item_cost(s):
    item_level, separators = get_items_and_separators(s)
    if all([separator in ['.', '-', ')'] for separator in separators]):
        return - item_level * 4
    else:
        return - item_level * 2

# def calculate_right_aligment_cost(curr_line, prev_line, right_aligment_dict):
#     right_lower_bound = right_aligment_dict['lower_bound']
#     right_upper_bound = right_aligment_dict['upper_bound']
#     range_with_mid_paragraph_lines = right_upper_bound - right_lower_bound
#     variance = right_aligment_dict['variance']
#     prev_distance_to_upper_bound = right_upper_bound - prev_line[-1]['x1']
#     prev_distance_to_upper_bound_cost = - (prev_distance_to_upper_bound - range_with_mid_paragraph_lines) / (range_with_mid_paragraph_lines * variance)
    

#     return prev_distance_to_upper_bound_cost * 4 if prev_distance_to_upper_bound_cost > 0 else -(-prev_distance_to_upper_bound_cost) ** 2

def calculate_right_aligment_cost(curr_line, prev_line, right_aligment_dict):
    right_lower_bound = right_aligment_dict['lower_bound']
    right_upper_bound = right_aligment_dict['upper_bound']
    right_peak = right_aligment_dict['peak_value']
    range_with_mid_paragraph_lines = right_upper_bound - right_lower_bound
    variance = right_aligment_dict['variance']
    prev_distance_to_peak = right_peak - prev_line[-1]['x1']
    cost_to_peak = 2 / (max(abs(prev_distance_to_peak), 1) * variance)

    right_aligment_cost = cost_to_peak if prev_distance_to_peak < 0 else cost_to_peak - (prev_distance_to_peak / 10) ** 2
    

    return right_aligment_cost

def calculate_vertical_aligment_cost(curr_line, prev_line, vertical_aligment_dict):
    mid_paragraph_dict = vertical_aligment_dict['mid_paragraph_spacing']
    outer_paragraph_dict = vertical_aligment_dict['outer_paragraph_spacing']

    curr_vertical_distance = curr_line[0]['origin_y0'] - prev_line[0]['origin_y0']

    if curr_line[0]['page'] != prev_line[0]['page'] or curr_vertical_distance < 0 or mid_paragraph_dict['peak_value'] == outer_paragraph_dict['peak_value']:
        return 0

    bounded_curr_vertical_distance = max(mid_paragraph_dict['lower_bound'], min(curr_vertical_distance, outer_paragraph_dict['upper_bound']))
    
    mid_paragraph_spacing = mid_paragraph_dict['peak_value']
    outer_paragraph_spacing = outer_paragraph_dict['peak_value']
    range_with_mid_paragraph_lines = outer_paragraph_spacing - mid_paragraph_spacing

    neutral_mid_paragraph_spacing = (mid_paragraph_spacing + outer_paragraph_spacing*4) / 5

    vertical_aligment_cost = (neutral_mid_paragraph_spacing - bounded_curr_vertical_distance) * 6 / range_with_mid_paragraph_lines
    
    return vertical_aligment_cost

def is_current_and_previous_lines_in_same_paragraph(curr_line, prev_line, prev2_line, right_aligment_dict, vertical_aligment_dict):
    """
        Positive values indicates higher probability of curr and prev being in the same paragraph
    """

    prev_distance_to_upper_bound_cost = calculate_right_aligment_cost(curr_line, prev_line, right_aligment_dict)
    vertical_aligment_cost = calculate_vertical_aligment_cost(curr_line, prev_line, vertical_aligment_dict)
    # We multiply by variance because the more concentrated (smaller variance) line endings are to a specific point,
    # the higher the chance of the text being justify, so the distance from the upper_bound matters more
    is_prev_and_curr_perfectly_aligned = prev_line[0]['x0'] == curr_line[0]['x0']
    # is_prev_and_curr_partially_aligned = any([prev_unit['x0'] == curr_line[0]['x0'] for prev_unit in prev_line])
    did_prev_end_with_final_puctuation = ends_with_punctuation(prev_line[-1]['para'])
    is_font_size_equal = prev_line[0]['size'] == curr_line[0]['size']
    is_bold_state_equal = prev_line[0]['bold'] == curr_line[0]['bold']
    are_colors_equal = prev_line[0]['color'] == curr_line[0]['color']
    are_flags_equal = prev_line[0]['flags'] == curr_line[0]['flags']
    horizontal_distance = curr_line[0]['x0'] - prev_line[0]['x0']
    horizontal_distance_cost = 2 if horizontal_distance == 0 else min(horizontal_distance, 0) * (200 / right_aligment_dict['upper_bound'])
    item_level_cost = calculate_item_cost(curr_line[0]['para'])
    # these 2 should only get the value related to curr-prev, and then compare it to the average values of the document, not to only 1 other value
    # vertical_distance_cost = vertical_distance_diff(curr_line, prev_line, prev2_line) * 2
    # prev_number_of_characters = sum(len(unit['para']) for unit in prev_line)
    # todo: check if current line start with a similar string as the current paragraph

    prev_punctuation_cost = -5 if did_prev_end_with_final_puctuation else 5

    total_cost = prev_distance_to_upper_bound_cost + vertical_aligment_cost + prev_punctuation_cost + horizontal_distance_cost + item_level_cost
    is_same_paragraph = total_cost > 0
    return is_same_paragraph


def group_lines_into_paragraphs(pages_organized_by_lines, target_percentage, doc_length, avg_page_width):
    all_paragraphs = []
    paragraph = []
    right_aligment_dict = calculate_right_aligment(pages_organized_by_lines, target_percentage, avg_page_width)
    vertical_aligment_dict = calculate_vertical_alignment(pages_organized_by_lines, 0.1)

    for page_nr in range(1, doc_length + 1):
        for line_index, current_line in enumerate(pages_organized_by_lines):
            first_unit = current_line[0]
            last_unit = current_line[-1]
            if first_unit.get('page') > page_nr:
                break
            elif first_unit.get('page') < page_nr:
                continue
            elif line_index == 0:
                paragraph.append(current_line)
                continue

            previous_line = pages_organized_by_lines[line_index - 1]
            second_previous_line = pages_organized_by_lines[max(line_index - 2, 0)]
            paragraph_continuation = is_current_and_previous_lines_in_same_paragraph(current_line, previous_line, second_previous_line, right_aligment_dict, vertical_aligment_dict)
            if not paragraph_continuation:
                # assert line[0]['page'] == line[-1]['page']
                all_paragraphs.append(paragraph)
                paragraph = []
            paragraph.append(current_line)
    if paragraph:
        all_paragraphs.append(paragraph)

    return all_paragraphs