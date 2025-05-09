from pyproj import CRS, Transformer, Geod

def transform_to_wgs84(x, y, crs_system):
    source_crs = CRS.from_user_input(crs_system)
    target_crs = CRS.from_epsg(4326) # WGS84

    if source_crs == target_crs:
          return x, y
    
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    long, lat = transformer.transform(x, y)
    return long, lat

def pixel_per_meter_from_scale(crs_system, pixel_scale, center_x, center_y):
    crs = CRS.from_user_input(crs_system)

    if crs.is_geographic:
        # Einheit ist Grad → umrechnen über Geodäsie
        geod = Geod(ellps="WGS84")

        pixel_scale_x = pixel_scale[0]
        pixel_scale_y = pixel_scale[1]

        # Horizontal: 1 Pixel = pixel_scale_x Grad in Längengrad
        lon1 = center_x
        lon2 = center_x + pixel_scale_x
        lat = center_y
        _, _, dist_x = geod.inv(lon1, lat, lon2, lat)

        # Vertikal: 1 Pixel = pixel_scale_y Grad in Breitengrad
        lat1 = center_y
        lat2 = center_y + pixel_scale_y
        lon = center_x
        _, _, dist_y = geod.inv(lon, lat1, lon, lat2)

    elif crs.is_projected:
        # Einheit ist Meter → Skala direkt interpretierbar
        dist_x = pixel_scale_x
        dist_y = pixel_scale_y

    else:
        raise ValueError("Unbekannter CRS-Typ – weder geographisch noch projiziert")

    # Ergebnis: Pixel pro Meter (also 1 / Meter pro Pixel)
    px_per_meter_x = 1 / dist_x if dist_x != 0 else 0
    px_per_meter_y = 1 / dist_y if dist_y != 0 else 0

    print(f"Auflösung [m]: {dist_x} x {dist_y}")
    return px_per_meter_x, px_per_meter_y