from pyproj import CRS, Transformer, Geod

def convert_coordinates_to_wgs84(x, y, crs_system):
    source_crs = CRS.from_user_input(crs_system)
    target_crs = CRS.from_epsg(4326) # WGS84

    if source_crs == target_crs:
          return x, y
    
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    long, lat = transformer.transform(x, y)
    return long, lat

def calculate_pixels_per_meter(crs_system, pixel_scale, top_left_x, top_left_y):
    """
    Berechnet die Pixel pro Meter für ein gegebenes Koordinatensystem und Pixelmaßstab.
    :param crs_system: Koordinatensystem
    :param pixel_scale: Pixelmaßstab (x, y)
    :param top_left_x: X-Koordinate des linken oberen Punkts der Karte
    :param top_left_y: Y-Koordinate des linken oberen Punkts der Karte
    :return: Pixel pro Meter (x, y)
    """
    crs = CRS.from_user_input(crs_system)

    if crs.is_geographic: # Einheit ist Grad -> umrechnen über Geodäsie
        geod = Geod(ellps="WGS84")

        pixel_scale_x = pixel_scale[0]
        pixel_scale_y = pixel_scale[1]

        # Horizontal: 1 Pixel = pixel_scale_x Grad in Längengrad
        lon1 = top_left_x
        lon2 = top_left_x + pixel_scale_x
        lat = top_left_y
        _, _, dist_x = geod.inv(lon1, lat, lon2, lat)

        # Vertikal: 1 Pixel = pixel_scale_y Grad in Breitengrad
        lat1 = top_left_y
        lat2 = top_left_y + pixel_scale_y
        lon = top_left_x
        _, _, dist_y = geod.inv(lon, lat1, lon, lat2)

    elif crs.is_projected: # Einheit ist Meter -> Skala direkt interpretierbar
        dist_x = pixel_scale_x
        dist_y = pixel_scale_y

    else:
        raise ValueError("Unbekannter CRS-Typ – weder geographisch noch projiziert")

    # Ergebnis: Pixel pro Meter (also 1 / Meter pro Pixel)
    px_per_meter_x = 1 / dist_x if dist_x != 0 else 0
    px_per_meter_y = 1 / dist_y if dist_y != 0 else 0

    print(f"Auflösung [m]: {dist_x} x {dist_y}")
    return px_per_meter_x, px_per_meter_y

if __name__ == "__main__":
    print("--- Test für convert_coordinates_to_wgs84 ---")
    x, y = 500000, 4649776  # Beispielkoordinaten in UTM Zone 33N
    crs_system = "EPSG:32633"  # UTM Zone 33N
    long, lat = convert_coordinates_to_wgs84(x, y, crs_system)
    print(f"UTM-Koordinaten ({x}, {y}) in WGS84: Längengrad={long}, Breitengrad={lat}\n")

    print("--- Test für calculate_pixels_per_meter ---")
    crs_system = "EPSG:4326"  # WGS84
    pixel_scale = (0.0001, 0.0001)  # Beispiel-Pixelmaßstab in Grad
    top_left_x, top_left_y = 10.0, 50.0  # Beispiel-Mittelpunkt (Längengrad, Breitengrad)
    px_per_meter_x, px_per_meter_y = calculate_pixels_per_meter(crs_system, pixel_scale, top_left_x, top_left_y)
    print(f"Pixel pro Meter: X={px_per_meter_x}, Y={px_per_meter_y}")