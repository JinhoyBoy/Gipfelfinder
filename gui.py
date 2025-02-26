import customtkinter as ctk
from tkinter import filedialog, Toplevel, ttk
import rasterio
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import matplotlib
import algo

# Agg-Backend erzwingen (verhindert das Öffnen von Fenstern durch Matplotlib)
matplotlib.use("Agg")

# Globale Variablen
canvas = None
vmin_value = None
vmax_value = None

def add_table():
    style = ttk.Style()
    style.configure("Treeview",
                    background="#2B2B2B",  # Hintergrundfarbe der Tabelle
                    foreground="white",    # Textfarbe
                    rowheight=25,          # Höhe der Zeilen
                    fieldbackground="#2B2B2B")  # Hintergrund für Eingabefelder

    style.map("Treeview", background=[("selected", "#1E90FF")])  # Farbe für ausgewählte Zeilen

    # Tabelle erstellen
    table = ttk.Treeview(right_frame_bottom, columns=("Spalte 0", "Spalte 1", "Spalte 2", "Spalte 3"), show="headings")
    
    # Spaltenüberschriften
    table.heading("Spalte 0", text="Nummer")
    table.heading("Spalte 1", text="Längengrad")
    table.heading("Spalte 2", text="Breitengrad")
    table.heading("Spalte 3", text="Höhe (m)")

    # Spaltenbreiten setzen
    table.column("Spalte 0", width=50, anchor="center")
    table.column("Spalte 1", width=100, anchor="center")
    table.column("Spalte 2", width=100, anchor="center")
    table.column("Spalte 3", width=80, anchor="center")

    # Beispielwerte einfügen
    example_data = [
        (1, 56, 37, 120),
        (2, 14, 65, 125),
        (3, 23, 64, 130),
        (4, 67, 40, 135)
    ]
    for row in example_data:
        table.insert("", "end", values=row)

    # Tabelle packen
    table.pack(fill="x", side="bottom")

def open_settings_window():
    """Öffnet ein neues Fenster, um vmin und vmax einzustellen."""
    settings_window = Toplevel(root)
    settings_window.title("Einstellungen")
    settings_window.geometry("300x250")
    
    # Lokale Variable für vmin-Eingabe
    vmin_label = ctk.CTkLabel(settings_window, text="vmin (Wert für \'Blau\'):")
    vmin_label.pack(pady=5)
    vmin_entry = ctk.CTkEntry(settings_window)
    vmin_entry.pack(pady=5)

    # Lokale Variable für vmax-Eingabe
    vmax_label = ctk.CTkLabel(settings_window, text="vmax (Wert für \'Weiß\'):")
    vmax_label.pack(pady=5)
    vmax_entry = ctk.CTkEntry(settings_window)
    vmax_entry.pack(pady=5)

    def save_settings():
        """Speichert die eingegebenen vmin- und vmax-Werte in den globalen Variablen."""
        global vmin_value, vmax_value
        try:
            vmin_value = float(vmin_entry.get())
        except ValueError:
            vmin_value = None  # Standardwert, falls Eingabe ungültig ist

        try:
            vmax_value = float(vmax_entry.get())
        except ValueError:
            vmax_value = None  # Standardwert, falls Eingabe ungültig ist

        print(f"Einstellungen gespeichert: vmin={vmin_value}, vmax={vmax_value}")
        settings_window.destroy()  # Fenster schließen

    # "Speichern"-Button hinzufügen
    save_button = ctk.CTkButton(settings_window, text="Speichern", command=save_settings)
    save_button.pack(pady=20)

def upload_image():
    """Lädt eine GeoTIFF-Datei hoch und zeigt sie mit den eingestellten vmin- und vmax-Werten an."""
    global canvas
    file_path = filedialog.askopenfilename(filetypes=[("TIF Files", "*.tif")])
    if file_path:
        print(f"Datei ausgewählt: {file_path}")
        
        try:
            with rasterio.open(file_path) as src:
                dem_data = src.read(1)
                print(dem_data)

                vmin = vmin_value if vmin_value is not None else dem_data.min()
                vmax = vmax_value if vmax_value is not None else dem_data.max()
                print(f"vmin: {vmin}, vmax: {vmax}")

                fig, ax = plt.subplots()
                cax = ax.imshow(dem_data, cmap="terrain", vmin=vmin, vmax=vmax)
                fig.colorbar(cax, ax=ax, label="Höhe (m)")

                if canvas:
                    canvas.get_tk_widget().destroy()

                canvas = FigureCanvasTkAgg(fig, master=right_frame)
                canvas.draw()
                canvas.get_tk_widget().pack()

                plt.close(fig)

        except Exception as e:
            print(f"Fehler beim Einlesen der GeoTIFF-Datei: {e}")

def show_peaks():
    """Findet die Gipfel in der hochgeladenen Karte und markiert (300, 100)."""
    global canvas
    if canvas is None:
        print("Keine Karte geladen. Bitte lade zuerst eine GeoTIFF-Datei hoch.")
        return  # Falls keine Karte geladen wurde, breche ab

    try:
        # Neues Figure-Objekt für das bestehende Bild erzeugen
        fig, ax = canvas.figure, canvas.figure.axes[0]

        # get the max x and min y values
        x_max = int(ax.get_xlim()[1])
        y_max = int(ax.get_ylim()[0])

        # Neuen Punkt als roten Marker hinzufügen
        peak_x, peak_y = algo.find_peaks(x_max, y_max)
        ax.plot(peak_x, peak_y, 'rv', markersize=10, label="Gipfel")

        # Aktualisieren der Anzeige im GUI
        canvas.draw()

        print("Gipfel wurde auf dem Bild markiert.")

    except Exception as e:
        print(f"Fehler beim Markieren des Gipfels: {e}")

def open_info_window():
    """Öffnet ein neues Fenster mit Info-Text."""
    info_window = Toplevel(root)
    info_window.title("Info")
    info_window.geometry("400x350")

    # Label mit Lorem Ipsum-Text
    info_text = ("0: Weltberg (Monte Etna, Barre des Ecrins, Corno Grande, Großglockner, Mont Blanc) \n"
                 "1: Hauptberg eines Kontinents (Gran Paradiso, Großvenediger, Hochgall, Zugspitze) \n"
                 "2: Hauptberg eines Gebirges (Dent Blanche, Dent d'Herens, Monte Cevedale, Weissmies) \n"
                 "3: Hauptberg einer Gebirgsgruppe (Allalinhorn, Castor, Liskamm, Schwarzenstein) \n"
                 "4: Hauptgipfel (im Mittelgebirge: -hügel) \n"
                 "5: Nebengipfel (im Mittelgebirge: -hügel) \n")
    
    info_label = ctk.CTkLabel(info_window, text=info_text, wraplength=350, justify="left")
    info_label.pack(pady=20, padx=20)

# Initialisiere CustomTkinter
ctk.set_appearance_mode("System")
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

# Dropdown-Liste (zur Auswahl einer Option, nur als Beispiel)
options = ["Klasse 0", "Klasse 1", "Klasse 2", "Klasse 3", "Klasse 4", "Klasse 5"]
dropdown = ctk.CTkOptionMenu(left_frame, values=options)
dropdown.pack(pady=20, padx=20)

# Button um die Gipfel zu finden
find_peaks_button = ctk.CTkButton(left_frame, text="Gipfel finden", fg_color="green", command=show_peaks)
find_peaks_button.pack(pady=10, padx=20)

# Klickbares Info-Label hinzufügen
info_label = ctk.CTkLabel(left_frame, text="Was ist eine Klasse?", text_color="gray", cursor="hand2")
info_label.pack(padx=20)
info_label.bind("<Button-1>", lambda e: open_info_window())

# "Einstellungen"-Button unten links platzieren
settings_button = ctk.CTkButton(left_frame, text="Einstellungen", command=open_settings_window)
settings_button.pack(side="bottom", pady=10, padx=10)

# Funktion nach dem Fensteraufbau aufrufen
add_table()

# Hauptloop starten
root.mainloop()
