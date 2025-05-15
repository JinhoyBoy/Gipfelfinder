import rasterio

def read_dem(file_path):
    """
    Liest ein GeoTIFF und gibt zurück:
      - dem_data (2D-Array)
      - crs (CRS-Objekt)
      - transform (Affine-Transform)
      - resolution (xres, yres) in Daten-Einheiten (z.B. Meter)
    """
    with rasterio.open(file_path) as src:
        dem_data = src.read(1)
        crs = src.crs
        transform = src.transform
        xres, yres = src.res
    return dem_data, crs, transform, (xres, yres)