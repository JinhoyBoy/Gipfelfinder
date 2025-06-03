# Gipfelfinder

## Installation der Abhängigkeiten

Bevor man das Tool nutzen kann, benötigt man GDAL (für rasterio) und die in `requirements.txt` genannten Python-Pakete.

### GDAL installieren

#### Windows

1. Lade den OSGeo4W Network Installer herunter:  
   https://trac.osgeo.org/osgeo4w/ (`osgeo4w-setup.exe`)  
2. Starte den Installer und wähle **Express** oder **Advanced** Installation.  
3. Wähle das Paket **gdal** aus und führe die Installation durch.  

Alternativ mit Conda:

    conda install -c conda-forge gdal

#### macOS

Mit Homebrew:

    brew install gdal

Oder mit Conda:

    conda install -c conda-forge gdal

#### Linux

Beispiel für Ubuntu/Debian:

    sudo apt-get update
    sudo apt-get install gdal-bin libgdal-dev

Oder mit Conda:

    conda install -c conda-forge gdal

## Nutzung

1. Lade eine GeoTIFF-DEM-Datei über den Button **"Karte hochladen"** hoch.  
2. Gib Schwellenwerte für **Prominenz** und **Dominanz** ein oder wähle eine Voreinstellung.  
3. Klicke auf **"Gipfel finden"**, um alle prominenten Gipfel in 2D oder 3D zu ermitteln und darzustellen.  
4. Betrachte die Ergebnisse im interaktiven Plot und in der Tabelle mit Pixel- und WGS84-Koordinaten.  

## Funktionen

- Erkennung lokaler Maxima in digitalen Höhenmodellen (DEMs)  
- Berechnung der **Prominenz** (Höhendifferenz zum höchsten Sattel)  
- Berechnung der **Dominanz** (Luftlinien-Entfernung zum nächstgelegenen höheren Punkt)  
- Einstellbare Schwellwerte und voreingestellte Modi  
- 2D-Overlay und interaktive 3D-Visualisierung der Geländeoberfläche  
- Exportierbare Tabelle der Gipfelkoordinaten (Pixel und WGS84)  