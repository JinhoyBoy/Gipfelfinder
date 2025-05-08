import customtkinter as ctk
from tkinter import filedialog, Toplevel, ttk
import rasterio
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import matplotlib
import algo
import numpy as np
#from mpl_toolkits.mplot3d import Axes3D  # Am Anfang hinzufügen

# Agg-Backend erzwingen (verhindert das Öffnen von Fenstern durch Matplotlib)
matplotlib.use("Agg")
plt.style.use('dark_background')

# Globale Variablen
canvas = None
dem_data_global = None  # Neuer globaler Speicher für DEM-Daten
plot_mode_switch = None  # Globaler Switch-Zustand
points_table = None  # Globale Referenz auf die Tabelle
prominence_threshold_global = 500
dominance_threshold_global = 100

def add_table():
    global points_table
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview",
                    background="#2B2B2B",  # Hintergrundfarbe der Tabelle
                    foreground="white",    # Textfarbe
                    rowheight=25,          # Höhe der Zeilen
                    fieldbackground="#2B2B2B") # Hintergrund für Eingabefelder

    style.map("Treeview", background=[("selected", "#1E90FF")])  # Farbe für ausgewählte Zeilen

    # Style für die Kopfzeile (Header) festlegen
    style.configure("Treeview.Heading",
                    background="#2B2B2B",  # Hintergrundfarbe der Kopfzeile
                    foreground="white",
                    relief="flat") 
    
    # Tabelle erstellen
    table = ttk.Treeview(right_frame_bottom, columns=("Spalte 0", "Spalte 1", "Spalte 2", "Spalte 3"), show="headings")

    # Spaltenüberschriften
    table.heading("Spalte 0", text="Nummer")
    table.heading("Spalte 1", text="X-Koordinate")
    table.heading("Spalte 2", text="Y-Koordinate")
    table.heading("Spalte 3", text="Höhe (m)")

    # Spaltenbreiten setzen
    table.column("Spalte 0", width=50, anchor="center")
    table.column("Spalte 1", width=100, anchor="center")
    table.column("Spalte 2", width=100, anchor="center")
    table.column("Spalte 3", width=80, anchor="center")

    # Tabelle als globale points_table speichern
    points_table = table
    table.pack(fill="x", side="bottom")


def open_settings_window():
    """Öffnet ein neues Fenster, um vmin und vmax einzustellen."""
    settings_window = Toplevel(root)
    settings_window.title("Einstellungen")
    settings_window.geometry("300x250")


def upload_image():
    """Lädt eine GeoTIFF-Datei hoch und zeigt sie abhängig vom Switch als 2D- oder 3D-Plot an."""
    global canvas, dem_data_global, plot_mode_switch, points_table
    file_path = filedialog.askopenfilename(filetypes=[("TIF Files", "*.tif")])
    
    # Tabelle zurücksetzen
    if points_table is not None:
        for item in points_table.get_children():
            points_table.delete(item)

    if file_path:
        print(f"Datei ausgewählt: {file_path}")
        
        try:
            with rasterio.open(file_path) as src:
                dem_data = src.read(1)
                geodata = src.transform
                dem_data_global = dem_data

                # DEM-Daten in eine CSV-Datei speichern
                #np.savetxt("dem_data.csv", dem_data, delimiter=",")

                vmin = dem_data.min()
                vmax = dem_data.max()

                fig = plt.figure(figsize=(10, 6))
                fig.patch.set_alpha(0.85)

                # Abhängig von der Stellung des Switch zwischen 2D und 3D wechseln
                if plot_mode_switch and plot_mode_switch.get() == 1:
                    # 3D-Modus
                    ax = fig.add_subplot(111, projection='3d')
                    x = np.arange(dem_data.shape[1])
                    y = np.arange(dem_data.shape[0])
                    X, Y = np.meshgrid(x, y)
                    surf = ax.plot_surface(X, Y, dem_data, cmap="viridis", vmin=vmin, vmax=vmax)
                    fig.colorbar(surf, ax=ax, label="Höhe (m)")
                else:
                    # 2D-Modus
                    ax = fig.add_subplot(111)
                    ax.imshow(dem_data, cmap="viridis", vmin=vmin, vmax=vmax)
                    fig.colorbar(ax.imshow(dem_data, cmap="viridis", vmin=vmin, vmax=vmax), ax=ax, label="Höhe (m)")

                if canvas:
                    canvas.get_tk_widget().destroy()

                canvas = FigureCanvasTkAgg(fig, master=right_frame)
                canvas.draw()
                canvas.get_tk_widget().pack()

                plt.close(fig)

        except Exception as e:
            print(f"Fehler beim Einlesen der GeoTIFF-Datei: {e}")


def show_peaks():
    """Markiert alle gefundenen prominenten Gipfel im Plot und trägt sie in die Tabelle ein."""
    global canvas, dem_data_global, plot_mode_switch, points_table
    update_thresholds_from_entries()  # <-- Werte aus Entry-Feldern übernehmen

    if canvas is None:
        print("Keine Karte geladen. Bitte lade zuerst eine GeoTIFF-Datei hoch.")
        return

    try:
        fig, ax = canvas.figure, canvas.figure.axes[0]

        # Alle gefundenen Gipfel holen
        peaks = algo.find_peaks(
            dem_data_global,
            prominence_threshold_val=prominence_threshold_global,
            dominance_threshold_val=dominance_threshold_global
        )
        if not peaks:
            print("Keine prominenten Gipfel gefunden.")
            return

        for idx, (peak_xy, peak_h, prom, dom) in enumerate(peaks, start=1):
            x, y = peak_xy
            z = dem_data_global[y, x]
            if plot_mode_switch and plot_mode_switch.get() == 1:
                # 3D-Modus
                ax.scatter(x, y, z, c='r', marker='o', s=50, label="Gipfel" if idx == 1 else "")
                print(f"3D-Gipfel: X={x}, Y={y}, Z={z}, Prominenz={prom}, Dominanz={dom}")
            else:
                # 2D-Modus
                ax.scatter(x, y, c='r', marker='o', s=50, label="Gipfel" if idx == 1 else "")
                print(f"2D-Gipfel: X={x}, Y={y}, Prominenz={prom}, Dominanz={dom}")
            # In die Tabelle eintragen
            new_entry = (len(points_table.get_children()) + 1, x, y, z)
            points_table.insert("", "end", values=new_entry)

        canvas.draw()
    except Exception as e:
        print(f"Fehler beim Markieren der Gipfel: {e}")


def open_info_window():
    """Öffnet ein neues Fenster mit Info-Text."""
    info_window = Toplevel(root)
    info_window.title("Info")
    info_window.geometry("400x350")

    # Label mit Lorem Ipsum-Text
    info_text = ("""Prominenz und Dominanz sind Maße zur Beschreibung der Bedeutung eines Berggipfels in einem Höhenmodell:
    
    Prominenz:
    - Die Höhendifferenz zwischen dem Gipfel und dem tiefsten Punkt (Sattel), über den man zu einem höheren Gipfel gelangt.
    
    Dominanz:
    - Die horizontale Entfernung (Luftlinie) vom Gipfel zum nächsthöheren Gipfel.""")
    
    info_label = ctk.CTkLabel(info_window, text=info_text, wraplength=350, justify="left")
    info_label.pack(pady=20, padx=20)


def create_plot_mode_switch():
    """Erzeugt einen Switch, um zwischen 2D- und 3D-Plot zu wechseln."""
    global plot_mode_switch
    plot_mode_switch = ctk.CTkSwitch(left_frame, text="3D Modus")
    plot_mode_switch.pack(pady=10)


def update_thresholds_from_entries():
    global prominence_threshold_global, dominance_threshold_global
    try:
        prom_val = float(prominence_entry.get())
        prominence_threshold_global = prom_val
    except ValueError:
        prominence_threshold_global = 500  # Fallback

    try:
        dom_val = float(dominance_entry.get())
        dominance_threshold_global = dom_val
    except ValueError:
        dominance_threshold_global = 100  # Fallback


# Initialisiere CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Hauptfenster erstellen
root = ctk.CTk()
root.title("PeakFinder")
root.geometry("1000x600")

# Icon setzen
icon_img = Image.open("icon.png")
icon_photo = ImageTk.PhotoImage(icon_img)
root.iconphoto(True, icon_photo)

# Linken Frame erstellen (für UI-Elemente)
left_frame = ctk.CTkFrame(root, width=200, corner_radius=10)
left_frame.pack(side="left", fill="y", padx=10, pady=10)

# Rechten Frame erstellen (für die Matplotlib-Anzeige)
right_frame = ctk.CTkFrame(root, corner_radius=10)
right_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

# Recter Frame unten rechts erstellen scrollbar (für die Tabelle)
right_frame_bottom = ctk.CTkScrollableFrame(right_frame, height=200, corner_radius=10)
right_frame_bottom.pack(side="bottom", fill="both", padx=10, pady=10)

# Überschrift in den rechten Frame hinzufügen
title_label = ctk.CTkLabel(left_frame, text="Gipfel finden", font=("Arial", 18, "bold"))
title_label.pack(side="top", pady=10, padx=20)

# "Bild hochladen"-Button hinzufügen
upload_button = ctk.CTkButton(left_frame, text="Karte hochladen", command=upload_image)
upload_button.pack(pady=10, padx=20)

# Button um die Gipfel zu finden
find_peaks_button = ctk.CTkButton(left_frame, text="Gipfel finden", fg_color="green", command=show_peaks)
find_peaks_button.pack(pady=10, padx=20)

# Erstelle den Switch im left_frame
create_plot_mode_switch()

# Eintrag für die Prominenz
prominence_label = ctk.CTkLabel(left_frame, text="Prominenz (m):")
prominence_label.pack(pady=10, padx=20)
prominence_entry = ctk.CTkEntry(left_frame, placeholder_text="500")
prominence_entry.pack(padx=20)

# Eintrag für die Dominanz
dominance_label = ctk.CTkLabel(left_frame, text="Dominanz (pixel):")
dominance_label.pack(pady=10, padx=20)
dominance_entry = ctk.CTkEntry(left_frame, placeholder_text="100")
dominance_entry.pack(padx=20)

# "Einstellungen"-Button unten links platzieren
settings_button = ctk.CTkButton(left_frame, text="⚙️ Einstellungen", command=open_settings_window)
settings_button.pack(side="bottom", pady=10, padx=10)

# Klickbares Info-Label hinzufügen
info_label = ctk.CTkLabel(left_frame, text="Was ist Prominenz/ Dominanz?", text_color="gray", cursor="hand2")
info_label.pack(side="bottom", padx=20)
info_label.bind("<Button-1>", lambda e: open_info_window())

# Funktion nach dem Fensteraufbau aufrufen
add_table()

# Hauptloop starten
root.mainloop()
