# algorithm to find peaks
import random
import numpy as np
from scipy.ndimage import maximum_filter
from PIL import Image
import time
from skimage.draw import line # Erforderlich für get_path_between_points
from joblib import Parallel, delayed
from multiprocessing import Pool


def find_local_maxima(img_data):
    """
    This is the numpy/scipy version of find local maxima.
    Its a bit faster, and more compact code.
    """
    #Filter data with maximum filter to find maximum filter response in each neighbourhood
    max_out = maximum_filter(img_data,size=5)
    #Find local maxima.
    local_max = np.zeros((img_data.shape))
    local_max[max_out == img_data] = 1
    local_max[img_data == np.min(img_data)] = 0 # Minima ausschließen
    #Find coordinates of local maxima -> list of maxima
    local_max_list = np.argwhere(local_max == 1) # Gibt [[y,x], [y,x], ...] zurück
    print(f"Anzahl gefundener lokaler Maxima: {len(local_max_list)}")
    return local_max_list

def get_path_between_points(p1, p2):
    """
    Bresenham-artige Approximation für den Pfad zwischen zwei Punkten
    p1, p2 sind (x, y) Tupel.
    """
    # skimage.draw.line erwartet (row0, col0, row1, col1)
    # Da p1 = (x,y) = (col,row), ist p1[1]=row und p1[0]=col
    rr, cc = line(p1[1], p1[0], p2[1], p2[0])
    return list(zip(cc, rr)) # Gibt eine Liste von (x,y) Tupeln zurück

def calculate_prominence(candidate_peaks_xy, height_map, prominence_threshold):
    """
    Optimierte Prominenzberechnung: 
    Für jeden Peak wird nur der Sattelpunkt zum jeweils nächsthöheren Peak berechnet.
    """
    if not candidate_peaks_xy:
        return []

    peak_heights = np.array([int(height_map[y, x]) for x, y in candidate_peaks_xy])
    sorted_peaks = sorted(zip(candidate_peaks_xy, peak_heights), key=lambda p: -p[1])
    prominent_peaks_output = []

    for i, (peak_xy, peak_h) in enumerate(sorted_peaks):
        # Suche den nächsthöheren Peak (direkt vor diesem in der sortierten Liste)
        higher_peaks = sorted_peaks[:i]
        if not higher_peaks:
            prominence = peak_h
            if prominence >= prominence_threshold:
                prominent_peaks_output.append((peak_xy, peak_h, prominence))
            continue

        # Nur zum höchsten höheren Peak den Sattel berechnen
        higher_peak_xy, _ = higher_peaks[0]
        path = get_path_between_points(peak_xy, higher_peak_xy)
        #print(path)
        saddle_height = min(height_map[y, x] for x, y in path)
        prominence = peak_h - saddle_height

        if prominence >= prominence_threshold:
            prominent_peaks_output.append((peak_xy, peak_h, prominence))

    return prominent_peaks_output

def calculate_prominence_joblib(candidate_peaks_xy, height_map, prominence_threshold):
    """
    Optimierte Prominenzberechnung mit Parallelisierung durch joblib.
    """
    if not candidate_peaks_xy:
        return []

    peak_heights = np.array([int(height_map[y, x]) for x, y in candidate_peaks_xy])
    sorted_peaks = sorted(zip(candidate_peaks_xy, peak_heights), key=lambda p: -p[1])

    def compute_prominence(peak_xy, peak_h, higher_peaks):
        if not higher_peaks:
            # Wenn es keine höheren Peaks gibt, ist die Prominenz gleich der Höhe
            return (peak_xy, peak_h, peak_h) if peak_h >= prominence_threshold else None

        # Nur zum höchsten höheren Peak den Sattel berechnen
        higher_peak_xy, _ = higher_peaks[0]
        path = get_path_between_points(peak_xy, higher_peak_xy)
        saddle_height = min(height_map[y, x] for x, y in path)
        prominence = peak_h - saddle_height

        if prominence >= prominence_threshold:
            return (peak_xy, peak_h, prominence)
        return None

    # Parallelisierte Berechnung der Prominenz
    results = Parallel(n_jobs=-1)(
        delayed(compute_prominence)(peak_xy, peak_h, sorted_peaks[:i])
        for i, (peak_xy, peak_h) in enumerate(sorted_peaks)
    )

    # Entferne None-Werte aus den Ergebnissen
    prominent_peaks_output = [res for res in results if res is not None]

    return prominent_peaks_output

def calc_dominance_distance(peak_xy, peak_h, higher_peaks):
    """
    Berechnet die Dominanz als euklidische Entfernung zum nächsthöheren Peak.
    peak_xy: (x, y) des aktuellen Peaks
    peak_h: Höhe des aktuellen Peaks
    higher_peaks: Liste von (peak_xy, peak_h) für höhere Peaks
    """
    if not higher_peaks:
        return np.inf  # Höchster Punkt: Dominanz unendlich
    # Finde den nächstgelegenen höheren Peak
    min_dist = np.inf
    for hp_xy, hp_h in higher_peaks:
        dist = np.linalg.norm(np.array(peak_xy) - np.array(hp_xy))
        if dist < min_dist:
            min_dist = dist
    return min_dist

def find_peaks(dem_data, prominence_threshold_val=500, dominance_threshold_val=100):
    """
    Findet lokale Maxima und filtert sie dann nach Prominenz und Dominanz.
    Gibt eine Liste aller prominenten Gipfel zurück: [(x, y), Höhe, Prominenz, Dominanz]
    """
    candidate_peaks_yx = find_local_maxima(dem_data) # Gibt [[y,x], ...] zurück

    if not candidate_peaks_yx.size:
        return []

    candidate_peaks_xy_list = [(c, r) for r, c in candidate_peaks_yx]
    prominent_peaks_info = calculate_prominence(candidate_peaks_xy_list, dem_data, prominence_threshold=prominence_threshold_val)

    filtered_peaks = []
    sorted_peaks = sorted([(peak_xy, peak_h, prominence) for peak_xy, peak_h, prominence in prominent_peaks_info], key=lambda p: -p[1])
    for i, (peak_xy, peak_h, prominence) in enumerate(sorted_peaks):
        higher_peaks = [(p[0], p[1]) for p in sorted_peaks[:i] if p[1] >= peak_h]
        dominance = calc_dominance_distance(peak_xy, peak_h, higher_peaks)
        if dominance >= dominance_threshold_val:
            filtered_peaks.append((peak_xy, peak_h, prominence, dominance))
            print(f"  Prominenter Gipfel: {peak_xy} (x,y) mit Höhe: {peak_h}, Prominenz: {prominence}, Dominanz: {dominance}")
    print(f"Anzahl prominenter Gipfel: {len(filtered_peaks)}")

    return filtered_peaks


if __name__ == "__main__":
    # Beispiel-Test mit einem künstlichen DEM-Array
    print("\n--- Test für find_peaks ---")
    test_dem = np.zeros((200, 200), dtype=np.uint8) # Erstelle ein 20x20 DEM-Array mit Nullen
    test_dem[5, 5] = 100    # Peak 1
    test_dem[10, 10] = 150  # Peak 2 (höher)
    test_dem[15, 15] = 80   # Peak 3

    # Teste find_peaks
    results = find_peaks(test_dem, prominence_threshold_val=100, dominance_threshold_val=10)
    if results is not None:
        for idx, (peak_xy, peak_h, prom, dom) in enumerate(results, start=1):
            x, y = peak_xy
            print(f"Gefundener prominenter Gipfel: (x={x}, y={y}), Höhe: {test_dem[y, x]}")
    else:
        print("Kein prominenter Gipfel gefunden.")

    # Geschwindigkeitstest für calculate_prominence
    print("\n--- Geschwindigkeitstest für calculate_prominence (1000x1000) ---")
    large_test_data = np.random.randint(0, 255, (500, 500), dtype=np.uint8)
    # Zuerst lokale Maxima bestimmen
    candidate_peaks_yx = find_local_maxima(large_test_data)
    candidate_peaks_xy = [(c, r) for r, c in candidate_peaks_yx]

    start_time = time.time()
    _ = calculate_prominence_joblib(candidate_peaks_xy, large_test_data, prominence_threshold=50)
    end_time = time.time()
    print(f"  Dauer: {end_time - start_time:.5f} Sekunden")