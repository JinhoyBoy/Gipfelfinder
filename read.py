import rasterio
import matplotlib.pyplot as plt

# Datei laden
file_path = "example_tifs/Dubai.tif"
with rasterio.open(file_path) as dataset:
    dem_array = dataset.read(1)  # Lese die erste Band (Höhenwerte)

print(dem_array)  # zeigt das Höhenmodell als NumPy-Array


plt.imshow(dem_array, cmap='terrain')
plt.colorbar(label="Höhe (m)")
plt.title("Digitales Höhenmodell (DEM)")
plt.show()