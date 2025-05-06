# algorithm to find peaks
import random
import numpy as np
from scipy.ndimage import maximum_filter
from PIL import Image

def find_peaks(x, y, dem_data):
    peaks = find_local_maxima(dem_data)
    print(peaks)
    print(f"Gefundene lokale Maxima: {len(peaks)}")
    return random.randint(0, x), random.randint(0, y)

def find_local_maxima(dem_data):
    """
    1. Für jedes (i, j) wird in einem 3x3-Fenster der größte Wert gesucht 
       und in ein neues 2D-Array eingetragen.
    2. An den Stellen, wo das neue Array denselben Wert wie dem_data hat, 
       wird (j, i) als lokales Maximum betrachtet.
    Quelle: https://www.youtube.com/watch?v=f9vXOMKOlaY
    """
    rows, cols = dem_data.shape
    # Array anlegen, um das Maximum aus dem 3×3-Fenster zu speichern
    local_max_map = np.zeros_like(dem_data)

    # 3×3-Fenster für alle "inneren" Pixel durchlaufen
    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            region = dem_data[i-1:i+2, j-1:j+2]
            max_val = region.max()
            local_max_map[i, j] = max_val

    # Liste für True-Peaks
    peaks = []
    # Dort, wo lokales Maximum == dem_data, haben wir einen Peak
    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            if dem_data[i, j] == local_max_map[i, j]:
                peaks.append((j, i))  # (x, y)
    return peaks

def find_local_maxima_np(img_data):
    """
    This is the numpy/scipy version of the above function (find local maxima).
    Its a bit faster, and more compact code.
    """
    
    #Filter data with maximum filter to find maximum filter response in each neighbourhood
    max_out = maximum_filter(img_data,size=3)
    #Find local maxima.
    local_max = np.zeros((img_data.shape))
    local_max[max_out == img_data] = 1
    local_max[img_data == np.min(img_data)] = 0
    return local_max

if __name__ == "__main__":
    # Beispiel-Test mit einem JPG-Bild
    image_path = "example_tifs/algo_test.png"  # Passe den Dateinamen an
    img = Image.open(image_path).convert("L")  # L = Graustufen
    dem_data = np.array(img)

    # find_local_maxima auf das eingelesene Array anwenden
    result = find_local_maxima(dem_data)
    result_np = find_local_maxima_np(dem_data)
    print(f"Lokale Maxima (numpy/scipy): {result_np}")
    print(f"Lokale Maxima im Bild: {result}")
    print(f"Anzahl gefundener lokaler Maxima: {len(result)}")
