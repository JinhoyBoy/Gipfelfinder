# algorithm to find peaks
import random
import numpy as np
from scipy.ndimage import maximum_filter
from PIL import Image
import time
from skimage.draw import line # Erforderlich für get_path_between_points
from concurrent.futures import ProcessPoolExecutor
from numba import njit
from scipy.spatial import cKDTree


def find_local_maxima(img_data):
    """
    This is the numpy/scipy version of find local maxima.
    Its a bit faster, and more compact code.
    """
    #Filter data with maximum filter to find maximum filter response in each neighbourhood
    max_out = maximum_filter(img_data,size=7)
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

def calculate_prominence_old(candidate_peaks_xy, height_map, prominence_threshold):
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

    print(f"Anzahl prominenter Gipfel (alt): {len(prominent_peaks_output)}")
    return prominent_peaks_output

@njit
def compute_nearest_higher(coords, heights):
    """
    Für jeden Punkt i findet dieses Numba-jit die nächstgelegene, streng höhere Quelle.
    Gibt ein Array nearest mit dem Index des nächsthöheren Peaks (oder -1) zurück.
    """
    n = coords.shape[0]
    nearest = np.full(n, -1, np.int64)
    for i in range(n):
        xi, yi = coords[i, 0], coords[i, 1]
        hi = heights[i]
        min_d = 1e12
        best = -1
        for j in range(n):
            hj = heights[j]
            if hj > hi:
                dx = xi - coords[j, 0]
                dy = yi - coords[j, 1]
                d = np.hypot(dx, dy)
                if d < min_d:
                    min_d = d
                    best = j
        nearest[i] = best
    return nearest

def calculate_prominence_numba(candidate_peaks_xy, height_map, prominence_threshold):
    """
    Beschleunigte Version der Prominenz-Berechnung mit Numba für den Nearest-Higher-Teil.
    Ohne Parallelisierung, behält volle Genauigkeit bei.
    """
    if not candidate_peaks_xy:
        return []

    # Koordinaten- und Höhen-Arrays
    coords = np.array(candidate_peaks_xy, dtype=np.int64)  # shape (n, 2)
    heights = height_map[coords[:, 1], coords[:, 0]].astype(np.int64)

    # Absteigend nach Höhe sortieren
    order = np.argsort(-heights)
    coords = coords[order]
    heights = heights[order]

    # Nearest-Higher jitted finden
    nearest = compute_nearest_higher(coords, heights)

    prominent_peaks = []
    for i in range(len(coords)):
        x, y = coords[i]
        h = heights[i]
        j = nearest[i]

        if j == -1:
            # Höchster Peak
            if h >= prominence_threshold:
                prominent_peaks.append(((x, y), int(h), int(h)))
            continue

        # Pfad und Sattelpunkt
        path = get_path_between_points((x, y), tuple(coords[j]))
        saddle_h = min(height_map[yy, xx] for xx, yy in path)
        prom = h - saddle_h
        if prom >= prominence_threshold:
            prominent_peaks.append(((x, y), int(h), int(prom)))

    print(f"Anzahl prominenter Gipfel: {len(prominent_peaks)}")
    return prominent_peaks

def calculate_prominence(candidate_peaks_xy, height_map, prominence_threshold):
    """
    Berechnet die Prominenz für eine Liste von Gipfelkandidaten.
    Neu: für jeden Peak wird der räumlich nächstgelegene, aber höhere Peak verwendet.
    """
    if not candidate_peaks_xy:
        return []

    # Höhen der Kandidaten
    peak_heights = np.array([int(height_map[y, x]) for x, y in candidate_peaks_xy])
    # Liste von ((x,y), Höhe), absteigend nach Höhe sortiert
    sorted_peaks = sorted(zip(candidate_peaks_xy, peak_heights), key=lambda p: -p[1])
    prominent_peaks_output = []

    for peak_xy, peak_h in sorted_peaks:
        # Finde alle Peaks, die strikt höher sind
        higher = [(xy, h) for xy, h in sorted_peaks if h > peak_h]
        if not higher:
            # Höchster Peak -> Prominenz = Höhe
            if peak_h >= prominence_threshold:
                prominent_peaks_output.append((peak_xy, peak_h, peak_h))
            continue

        # Wähle den räumlich nächstgelegenen höheren Peak
        dists = [np.hypot(peak_xy[0] - xy[0], peak_xy[1] - xy[1]) for xy, _ in higher]
        idx_min = int(np.argmin(dists))
        nearest_xy, _ = higher[idx_min]

        # Pfad berechnen und Sattelpunkt finden
        path = get_path_between_points(peak_xy, nearest_xy)
        saddle_h = min(height_map[y, x] for x, y in path)

        prominence = peak_h - saddle_h
        if prominence >= prominence_threshold:
            prominent_peaks_output.append((peak_xy, peak_h, prominence))
    print(f"Anzahl prominenter Gipfel: {len(prominent_peaks_output)}")

    return prominent_peaks_output

def calculate_prominence_fast(candidate_peaks_xy, height_map, prominence_threshold):
    """
    1) build KD-Tree on all peak positions
    2) for each peak: query nearest neighbors, pick the first higher
    3) compute saddle + prominence only for diesen einen Partner
    """
    if not candidate_peaks_xy:
        return []

    # 1) Positionen und Höhen in Arrays
    coords = np.array(candidate_peaks_xy)       # shape (n,2)
    heights = np.array([height_map[y, x] for x,y in candidate_peaks_xy], dtype=int)

    # 2) sortieren nach Höhe (absteigend)
    order = np.argsort(-heights)
    coords_sorted = coords[order]
    heights_sorted = heights[order]

    # 3) KD-Tree einmal bauen
    tree = cKDTree(coords_sorted)

    output = []
    # k = z.B. 5 nächste Nachbarn suchen
    k = min(5, len(coords_sorted))
    for i, (xy, h) in enumerate(zip(coords_sorted, heights_sorted)):
        if h < prominence_threshold:
            break   # alle weiteren sind niedriger → raus
        # 4) nearest-neighbor query (inkl. sich selbst an Position 0)
        dists, inds = tree.query(xy, k=k)
        # find first neighbor with greater height
        partner_idx = None
        for dist, idx in zip(dists[1:], inds[1:]):
            if heights_sorted[idx] > h:
                partner_idx = idx
                break
        if partner_idx is None:
            # höchster verbleibender Peak → Prominenz = Höhe
            output.append((tuple(xy), h, h))
            continue
        # 5) Saddle-Berechnung nur für diesen einen Pfad
        path = get_path_between_points(tuple(xy), tuple(coords_sorted[partner_idx]))
        saddle_h = min(height_map[y, x] for x, y in path)
        prominence = h - saddle_h
        if prominence >= prominence_threshold:
            output.append((tuple(xy), h, prominence))

    print(f"Anzahl prominenter Gipfel (schnell): {len(output)}")
    return output

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
    prominent_peaks_info = calculate_prominence_numba(candidate_peaks_xy_list, dem_data, prominence_threshold=prominence_threshold_val)

    filtered_peaks = []
    sorted_peaks = sorted([(peak_xy, peak_h, prominence) for peak_xy, peak_h, prominence in prominent_peaks_info], key=lambda p: -p[1])
    for i, (peak_xy, peak_h, prominence) in enumerate(sorted_peaks):
        higher_peaks = [(p[0], p[1]) for p in sorted_peaks[:i] if p[1] >= peak_h]
        dominance = calc_dominance_distance(peak_xy, peak_h, higher_peaks)
        if dominance >= dominance_threshold_val:
            filtered_peaks.append((peak_xy, peak_h, prominence, dominance))
            #print(f"  Prominenter Gipfel: {peak_xy} (x,y) mit Höhe: {peak_h}, Prominenz: {prominence}, Dominanz: {dominance}")
    print(f"Anzahl Gipfel: {len(filtered_peaks)}")

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
    large_test_data = np.random.randint(0, 255, (10000, 10000), dtype=np.uint16)
    # Zuerst lokale Maxima bestimmen
    candidate_peaks_yx = find_local_maxima(large_test_data)
    candidate_peaks_xy = [(c, r) for r, c in candidate_peaks_yx]

    start_time = time.time()
    _ = calculate_prominence_numba(candidate_peaks_xy, large_test_data, prominence_threshold=100)
    end_time = time.time()
    print(f"  Dauer: {end_time - start_time:.5f} Sekunden")