import numpy as np
from scipy.stats import gaussian_kde
import math
import matplotlib.pyplot as plt

def calculate(pages_organized_by_lines, target_percentage):
    # Replace this with your actual data
    all_line_ends_x_coord = [line_unit[-1]['x1'] for line_unit in pages_organized_by_lines]

    # Calculate the KDE with a smaller bandwidth
    kde = gaussian_kde(all_line_ends_x_coord, bw_method=0.03)
    x_range = np.linspace(min(all_line_ends_x_coord), max(all_line_ends_x_coord), 1000)
    kde_values = kde(x_range)

    # Find the peak of the KDE
    peak_x_coord = x_range[np.argmax(kde_values)]

    # Calculate the CDF of the KDE
    cdf_values = np.cumsum(kde_values)
    cdf_values /= cdf_values[-1]  # Normalize to make it a proper CDF

    # Function to find nearest value index in array
    def find_nearest(array, value):
        idx = (np.abs(array - value)).argmin()
        return idx

    # Find index of the peak in x_range
    peak_idx = find_nearest(x_range, peak_x_coord)

    # Initialize bounds
    lower_bound_idx = peak_idx
    upper_bound_idx = peak_idx


    # Expand bounds to include the target percentage of data
    def find_optimal_bounds(cdf, peak_idx, target_percentage):
        n = len(cdf)
        best_lower = best_upper = peak_idx
        best_width = float('inf')

        for lower in range(peak_idx, -1, -1):
            for upper in range(peak_idx, n):
                if cdf[upper] - cdf[lower] >= target_percentage:
                    width = upper - lower
                    if width < best_width:
                        best_lower, best_upper = lower, upper
                        best_width = width
                    break  # Move to the next lower bound

        return best_lower, best_upper

    # Find the optimal bounds
    lower_bound_idx, upper_bound_idx = find_optimal_bounds(cdf_values, peak_idx, target_percentage)

    # Get the actual X coordinates for these indices
    lower_bound = x_range[lower_bound_idx]
    upper_bound = x_range[upper_bound_idx]

    # Calculate the standard deviation of the filtered x_coords within this interval
    filtered_x_coords = [x for x in all_line_ends_x_coord if lower_bound <= x <= upper_bound]
    std_deviation = np.std(filtered_x_coords)
    variance = math.sqrt(std_deviation)

    # # Plot histogram and KDE with the bounds
    # plt.figure(figsize=(10, 6))
    # plt.hist(all_line_ends_x_coord, bins=50, color='blue', alpha=0.7, label='ends X Coord', density=True)
    # plt.plot(x_range, kde_values, color='red', label='KDE')
    # plt.axvline(peak_x_coord, color='green', linestyle='--', label=f'Peak: {peak_x_coord:.2f}')
    # plt.axvline(lower_bound, color='purple', linestyle='--', label=f'Lower Bound: {lower_bound:.2f}')
    # plt.axvline(upper_bound, color='orange', linestyle='--', label=f'Upper Bound: {upper_bound:.2f}')
    # plt.xlabel('X Coordinate')
    # plt.ylabel('Density')
    # plt.title(f'Histogram and KDE of X Coordinates with 10% Data Interval')
    # plt.legend()
    # plt.grid(True)
    # plt.show()

    print('std_deviation: ', std_deviation)
    print('variance: ', variance)
    print('lower_bound: ', lower_bound)
    print('peak_x_coord: ', peak_x_coord)
    print('upper_bound: ', upper_bound)
    print('target_percentage: ', target_percentage)

    return {
        'std_deviation': std_deviation,
        'variance': variance,
        'lower_bound': lower_bound,
        'peak_x_coord': peak_x_coord,
        'upper_bound': upper_bound,
    }