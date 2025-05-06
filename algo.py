# algorithm to find peaks
import random
import numpy as np
from scipy.ndimage import maximum_filter
from PIL import Image
import time

def find_peaks(x, y, dem_data):
    #peaks = find_local_maxima(dem_data)
    #print(peaks)
    #print(f"Gefundene lokale Maxima: {len(peaks)}")
    return random.randint(0, x), random.randint(0, y)

def find_local_maxima(img_data):
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
    #Find coordinates of local maxima -> list of maxima
    local_max_list = np.argwhere(local_max == 1)
    return local_max_list

if __name__ == "__main__":
    # Beispiel-Test mit einem JPG-Bild
    image_path = "example_tifs/algo_test.png"  # Passe den Dateinamen an
    img = Image.open(image_path).convert("L")  # L = Graustufen
    dem_data = np.array(img)

    # find_local_maxima auf das eingelesene Array anwenden
    result = find_local_maxima(dem_data)
    print(f"Lokale Maxima im Bild: {result}")
    print(f"Anzahl gefundener lokaler Maxima: {len(result)}")

    # Test-Daten erstellen (z.B. 1000x1000)
    test_data = np.random.randint(0, 255, (1000, 1000), dtype=np.uint8)

    # Laufzeit von find_local_maxima
    start_time = time.time()
    _ = find_local_maxima(test_data)
    end_time = time.time()
    print(f"find_local_maxima: {end_time - start_time:.5f} Sekunden")