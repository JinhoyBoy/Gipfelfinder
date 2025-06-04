import heapq  # neu ergänzen
import numpy as np
from scipy.ndimage import maximum_filter
from scipy.ndimage import distance_transform_edt
import time
from skimage.draw import line
from numba import njit


def set_image_borders_to_zero(img, width):
    """
    Setzt die Werte an den Rändern des Bildes auf 0, um sie von der Analyse auszuschließen.
    :param img: Eingabebild (2D-Array)
    :param width: Breite des Randes, der auf 0 gesetzt wird
    :return: Bild mit gepaddeten Rändern
    """
    img[:width, :] = 0
    img[-width:, :] = 0
    img[:, :width] = 0
    img[:, -width:] = 0
    return img


def find_local_maxima(img_data, border_width=2):
    """
    Findet lokale Maxima in einem Bildarray und schließt Punkte am Rand aus.
    Gibt eine Liste von Koordinaten zurück, die die Positionen der lokalen Maxima darstellen.
    :param img_data: 2D-Array der Höhenwerte
    :param border_width: Breite des Randes, der ausgeschlossen wird
    """
    # Ränder des Bildes ausschließen
    img_data = set_image_borders_to_zero(img_data, width=border_width)

    # Filter data with maximum filter to find maximum filter response in each neighbourhood
    max_out = maximum_filter(img_data, size=7)

    # Find local maxima
    local_max = np.zeros((img_data.shape))
    local_max[max_out == img_data] = 1
    local_max[img_data == np.min(img_data)] = 0  # Minima ausschließen

    # Find coordinates of local maxima -> list of maxima
    local_max_list = np.argwhere(local_max == 1)  # Gibt [[y,x], [y,x], ...] zurück
    print(f"Anzahl gefundener lokaler Maxima (und nach Randfilter): {len(local_max_list)}")
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

@njit
def get_maxmin_saddle(height_map, start, end):
    """
    Findet den Pfad von start->end, dessen niedrigster Punkt (Sattel) maximal ist.
    Gibt die Höhe dieses Sattelpunktes zurück (Maximin- bzw. Bottleneck-Pfad). 
    Ist ein modifizierter Dijkstra-Algorithmus.
    start,end: (x,y)-Tupel in Pixelkoordinaten.
    """
    rows, cols = height_map.shape
    sx, sy = start
    ex, ey = end

    # best[y,x] = höchster erreichbarer minimaler Wert bis zu (x,y)
    best = np.full((rows, cols), -np.inf, dtype=np.float64)
    best[sy, sx] = float(height_map[sy, sx])

    # PriorityQueue speichert (-Sattelhöhe, x, y)
    pq = [(-best[sy, sx], sx, sy)]

    while pq:
        cur_min_neg, x, y = heapq.heappop(pq)
        cur_min = -float(cur_min_neg)

        # Wenn wir am Ziel sind, geben wir den Wert zurück
        if (x, y) == (ex, ey):
            return cur_min

        # 4‐Nachbarn
        for dx, dy in ((1,0), (-1,0), (0,1), (0,-1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < cols and 0 <= ny < rows:
                neigh_h = float(height_map[ny, nx])
                saddle = min(cur_min, neigh_h)
                if saddle > best[ny, nx]:
                    best[ny, nx] = saddle
                    heapq.heappush(pq, (-saddle, nx, ny))

    return best[ey, ex]  # Falls Ziel nie erreicht wurde


def calculate_prominent_peaks(candidate_peaks_xy, height_map, prominence_threshold, use_dijkstra=True):
    """
    Beschleunigte Version der Prominenz-Berechnung mit Numba für den Nearest-Higher-Teil.
    Ohne Parallelisierung, behält volle Genauigkeit bei.
    :param use_dijkstra: Wenn False, nutzt nur Bresenham-Approximation und überspringt Maximin-Dijkstra
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

        # Pfad und Sattelpunkt erst mit Bresenham-Approximation
        path = get_path_between_points((x, y), tuple(coords[j]))
        saddle_h = min(height_map[yy, xx] for xx, yy in path)
        prom = h - saddle_h
        if prom >= prominence_threshold:
            if use_dijkstra:
                # Feine Berechnung des Sattels mit Maximin-Dijkstra
                saddle_h = get_maxmin_saddle(height_map, (x, y), tuple(coords[j]))
                prom = h - saddle_h
                if prom >= prominence_threshold:
                    prominent_peaks.append(((x, y), int(h), int(prom)))
            else:
                # Nur Bresenham-Pfad nutzen
                prominent_peaks.append(((x, y), int(h), int(prom)))

    print(f"Anzahl prominenter Gipfel: {len(prominent_peaks)}")
    return prominent_peaks


def calculate_dominance_distance(peak_xy, height_map):
    """
    Berechnet die Dominanz: Distanz zum nähesten Pixel mit größerem Höhenwert auf der Karte
    peak_xy: (x, y) des aktuellen Gipfels
    height_map: 2D-Array mit Höhenwerten
    """
    x, y = peak_xy
    h0 = height_map[y, x]

    # Maske aller Pixel < h0 → distance_transform_edt liefert Abstand
    # zum nächsten False-Pixel (also ≥ h0)
    mask = (height_map < h0)
    mask[y, x] = True   # mich selbst aus der False-Fläche entfernen
    dist_map = distance_transform_edt(mask)
    return dist_map[y, x]

def calculate_orographic_dominance(peak_height, prominence):
    """
    Berechnet die orographische Dominanz eines Gipfels. (Relative Prominenz)
    """
    if peak_height == 0:
        return 0
    return (prominence / peak_height) * 100

def find_peaks(dem_data, prominence_threshold_val=500, dominance_threshold_val=100, orographic_dominence_threshold_val=0, border_width=50, min_height=0):
    """
    Findet lokale Maxima und filtert sie dann nach Prominenz, Dominanz und Mindesthöhe.
    Gibt eine Liste aller prominenten Gipfel zurück: [(x, y), Höhe, Prominenz, Dominanz]
    :param dem_data: 2D-Array der Höhenwerte (DEM-Daten)
    :param prominence_threshold_val: Mindestwert für die Prominenz
    :param dominance_threshold_val: Mindestwert für die Dominanz
    :param orographic_dominence_threshold_val: Mindestwert für die orographische Dominanz
    :param border_width: Breite des Randes, der ausgeschlossen wird
    :param min_height: Mindesthöhe, die ein Gipfel haben muss, um berücksichtigt zu werden
    """
    candidate_peaks_yx = find_local_maxima(dem_data, border_width)  # Gibt [[y,x], ...] zurück

    if not candidate_peaks_yx.size:
        return []

    candidate_peaks_xy_list = [(c, r) for r, c in candidate_peaks_yx]  # Konvertiere in eine Liste von (x, y)-Koordinaten
    prominent_peaks_info = calculate_prominent_peaks(candidate_peaks_xy_list, dem_data, prominence_threshold_val)  # Berechne die Prominenz und filtere danach -> Liste

    filtered_peaks = []
    sorted_peaks = sorted([(peak_xy, peak_h, prominence) for peak_xy, peak_h, prominence in prominent_peaks_info], key=lambda p: -p[1])
    for i, (peak_xy, peak_h, prominence) in enumerate(sorted_peaks):
        # Mindesthöhe
        if peak_h < min_height:
            continue  # Gipfel ausschließen, wenn die Höhe unter der Mindesthöhe liegt
        
        # orografische Dominanz
        orographic_dominance = calculate_orographic_dominance(peak_h, prominence)
        if orographic_dominance < orographic_dominence_threshold_val:
            continue  # Gipfel ausschließen, wenn die orographische Dominanz unter dem Schwellenwert liegt
        
        # Dominanz
        higher_peaks = [(p[0], p[1]) for p in sorted_peaks[:i] if p[1] >= peak_h]
        if not higher_peaks: # Wenn es keine höheren Gipfel gibt, ist die Dominanz unendlich
            dominance = np.inf
        else: 
            dominance = calculate_dominance_distance(peak_xy, dem_data)            
        if dominance >= dominance_threshold_val:
            filtered_peaks.append((peak_xy, peak_h, prominence, dominance))
            # print(f"  Prominenter Gipfel: {peak_xy} (x,y) mit Höhe: {peak_h}, Prominenz: {prominence}, Dominanz: {dominance}")
    print(f"Anzahl Gipfel: {len(filtered_peaks)}")

    return filtered_peaks


if __name__ == "__main__":
    # Beispiel-Test mit einem künstlichen DEM-Array
    print("\n--- Test für find_peaks ---")
    test_dem = np.zeros((2000, 2000), dtype=np.uint8) # Erstelle ein 2000x2000 DEM-Array mit Nullen
    test_dem[50, 50] = 100    # Peak 1
    test_dem[100, 100] = 150  # Peak 2 (höher)
    test_dem[150, 150] = 80   # Peak 3

    # Teste find_peaks
    results = find_peaks(test_dem, prominence_threshold_val=100, dominance_threshold_val=10)
    if results is not None:
        for idx, (peak_xy, peak_h, prom, dom) in enumerate(results, start=1):
            x, y = peak_xy
            print(f"Gefundener prominenter Gipfel: (x={x}, y={y}), Höhe: {test_dem[y, x]}")
    else:
        print("Kein prominenter Gipfel gefunden.")

    # Geschwindigkeitstest für calculate_prominence
    data_size = 500
    print(f"\n--- Geschwindigkeitstest für Prominenzberechnung ({data_size}x{data_size}) ---")
    large_test_data = np.random.randint(0, 255, (data_size, data_size), dtype=np.uint16)
    # Zuerst lokale Maxima bestimmen
    candidate_peaks_yx = find_local_maxima(large_test_data)
    candidate_peaks_xy = [(c, r) for r, c in candidate_peaks_yx]

    print(f"\nGeschwindigkeitstest für calculate_prominent_peaks:")
    start_time = time.time()
    _ = calculate_prominent_peaks(candidate_peaks_xy, large_test_data, prominence_threshold=100, use_dijkstra=False)
    end_time = time.time()
    print(f"  Dauer: {end_time - start_time:.5f} Sekunden")
    
    """
    print(f"\nGeschwindigkeitstest für calculate_prominent_peaks normal (ohne Beschleunigung):")
    start_time = time.time()
    _ = calculate_prominent_peaks_old(candidate_peaks_xy, large_test_data, prominence_threshold=100)
    end_time = time.time()
    print(f"  Dauer: {end_time - start_time:.5f} Sekunden")
    """
