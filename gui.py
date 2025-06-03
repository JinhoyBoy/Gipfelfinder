import customtkinter as ctk
from tkinter import filedialog, Toplevel, ttk
import rasterio.transform
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import numpy as np
import csv 

from peak_analysis import find_peaks
from geo_utils import calculate_pixels_per_meter, convert_coordinates_to_wgs84
from reader import read_dem

# --- Matplotlib Einstellungen ---
matplotlib.use("Agg") # Agg-Backend erzwingen (verhindert das Öffnen von Fenstern durch Matplotlib)
plt.style.use('dark_background')

# --- CustomTkinter Einstellungen ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class PeakFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PeakFinder")
        self.root.geometry("1200x800")
        self._set_icon() # Icon Setzen

        # --- Instanz Variablen ---
        self.canvas = None # Canvas-Referenz für draw()
        self.canvas_widget = None
        self.canvas_figure = None
        self.dem_data = None
        self.peaks_table = None
        self.peaks_csv = []
        self.pixel_per_meter = None
        self.geo_transform = None
        self.crs_system = None
        self.prominence_threshold = 500  # Default Wert (Himalaya-Modus)
        self.dominance_threshold = 2000  # Default Wert (Himalaya-Modus)
        self.orographic_threshold = 0  # Default Orographische Dominanz in %
        self.min_height_threshold = 0    # Default wert
        self.border_width = 50

         # --- Setup UI ---
        self._create_frames()
        self._create_left_widgets()
        self._create_table()


    def _set_icon(self):
        """Loads and sets the application icon."""
        try:
            icon_img = Image.open("./images/_icon.ico")
            icon_photo = ImageTk.PhotoImage(icon_img)
            self.root.iconphoto(True, icon_photo)
        except Exception as e:
            print(f"Error loading icon: {e}")


    def _create_frames(self):
        """Creates the main layout frames."""
        self.left_frame = ctk.CTkFrame(self.root, width=200, corner_radius=10)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.right_frame_top = ctk.CTkFrame(self.root, corner_radius=10)
        self.right_frame_top.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        self.right_frame_bottom = ctk.CTkScrollableFrame(self.right_frame_top, height=150, corner_radius=10)
        self.right_frame_bottom.pack(side="bottom", fill="x", padx=10, pady=10)


    def _create_left_widgets(self):
        """Erstellt alle Widgets im linken Frame."""
        title_label = ctk.CTkLabel(self.left_frame, text="PeakFinder", font=("Arial", 18, "bold"))
        title_label.pack(side="top", pady=10, padx=20)

        # --- Upload Button ---
        upload_button = ctk.CTkButton(self.left_frame, text="Karte hochladen", command=self.upload_image)
        upload_button.pack(pady=10, padx=20)

        # --- Gipfel Finden Button ---
        find_peaks_button = ctk.CTkButton(self.left_frame, text="Gipfel finden", fg_color="green", command=self.show_peaks)
        find_peaks_button.pack(pady=10, padx=20)

        # --- 3D Plot Mode Switch ---
        self.dimension_switch = ctk.CTkSwitch(self.left_frame, text="3D Modus")
        self.dimension_switch.pack(pady=10, padx=20)

        # --- Voreinstellungen ComboBox ---
        self.preset_combobox = ctk.CTkOptionMenu(self.left_frame,
                                                 command=self.apply_preset,
                                                 fg_color="gray25",
                                                 button_color="gray20",
                                                 button_hover_color="gray15")
        self.preset_combobox.pack(pady=10, padx=20)
        self.preset_combobox.configure(values=["Himalaya-Modus", "UIAA-Alpinismus", "Kartografischer Modus", "benutzerdefiniert"])
        self.preset_combobox.set("Voreinstellungen")

        # --- Prominenz Eintrag ---
        prominence_label = ctk.CTkLabel(self.left_frame, text="Prominenz (m):")
        prominence_label.pack(pady=(10,0), padx=20)
        self.prominence_entry = ctk.CTkEntry(self.left_frame, placeholder_text=str(self.prominence_threshold))
        self.prominence_entry.pack(pady=(0,10), padx=20)

        # --- Dominanz Eintrag ---
        dominance_label = ctk.CTkLabel(self.left_frame, text="Dominanz (m):")
        dominance_label.pack(pady=(10,0), padx=20)
        self.dominance_entry = ctk.CTkEntry(self.left_frame, placeholder_text=str(self.dominance_threshold))
        self.dominance_entry.pack(pady=(0,10), padx=20)

        # --- orographische Dominanz Eintrag ---
        orographic_label = ctk.CTkLabel(self.left_frame, text="Orograph. Dominanz (%):")
        orographic_label.pack(pady=(10,0), padx=20)
        self.orographic_entry = ctk.CTkEntry(self.left_frame, placeholder_text="0")  # Standardwert 0
        self.orographic_entry.pack(pady=(0,10), padx=20)

        # --- Mindesthöhe Eintrag ---
        min_height_label = ctk.CTkLabel(self.left_frame, text="Mindesthöhe (m):")
        min_height_label.pack(pady=(10, 0), padx=20)
        self.min_height_entry = ctk.CTkEntry(self.left_frame, placeholder_text="0")  # Standardwert 0
        self.min_height_entry.pack(pady=(0, 10), padx=20)
        
        # --- Info Label (Unten) ---
        info_label = ctk.CTkLabel(self.left_frame, text="(ℹ) Was ist Prominenz/ Dominanz?", text_color="gray", cursor="hand2")
        info_label.pack(side="bottom", pady=(0,5), padx=20)
        info_label.bind("<Button-1>", lambda e: self.open_info_window())

        # --- Settings Button (Bottom) ---
        settings_button = ctk.CTkButton(self.left_frame, text="⚙️ Einstellungen", command=self.open_settings_window)
        settings_button.pack(side="bottom", pady=5, padx=10)
        
        # --- Export CSV Button (Bottom) ---
        export_button = ctk.CTkButton(self.left_frame, text="Tabelle exportieren", fg_color="gray25", hover_color="gray15", command=self.export_csv_table)
        export_button.pack(side="bottom", pady=10, padx=10)


    def _create_table(self):
        """Creates the ttk.Treeview table for peak data."""
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2B2B2B", foreground="white", rowheight=25, fieldbackground="#2B2B2B")
        style.map("Treeview", background=[("selected", "#1E90FF")])
        style.configure("Treeview.Heading", background="#2B2B2B", foreground="white", relief="flat")
        style.map("Treeview.Heading", background=[('active', '#3C3C3C')])

        # --- Tabelle erstellen ---
        table = ttk.Treeview(self.right_frame_bottom,
                             columns=("Nummer", "Pixel-Koord", "Breitengrad", "Längengrad", "Höhe"),
                             show="headings")
        
        # Setzen der Headings
        table.heading("Nummer", text="Nr.")
        table.heading("Pixel-Koord", text="Pixel (x, y)")
        table.heading("Breitengrad", text="Breitengrad")
        table.heading("Längengrad", text="Längengrad")
        table.heading("Höhe", text="Höhe (m)")

        # Setzen der Spaltenbreiten und Ausrichtung
        table.column("Nummer", width=40, anchor="center", stretch=False)
        table.column("Pixel-Koord", width=120, anchor="center", stretch=True)
        table.column("Breitengrad", width=150, anchor="center", stretch=True)
        table.column("Längengrad", width=150, anchor="center", stretch=True)
        table.column("Höhe", width=80, anchor="center", stretch=True)

        self.peaks_table = table
        self.peaks_table.pack(expand=True, fill="both")


    def _draw_plot(self, dem_data, vmin, vmax):
        """Erstellt oder aktualisiert den 2D/3D-Plot im rechten Frame."""
        # altes Canvas/Figure entfernen
        if self.canvas_widget:
            self.canvas_widget.destroy()
            plt.close(self.canvas_figure)

        # neue Figure mit Hintergrund
        fig = plt.figure(facecolor="#2B2B2B")
        if self.dimension_switch.get() == 1:
            # 3D-Plot
            ax = fig.add_subplot(111, projection='3d')
            x = np.arange(dem_data.shape[1])
            y = np.arange(dem_data.shape[0])
            X, Y = np.meshgrid(x, y)
            plt.gca().set_facecolor('#2B2B2B')
            surf = ax.plot_surface(X, Y, dem_data, cmap="viridis", vmin=vmin, vmax=vmax)
            fig.colorbar(surf, ax=ax, label="Höhe (m)", shrink=0.75)
        else:
            # 2D-Plot
            ax = fig.add_subplot(111)
            im = ax.imshow(dem_data, cmap="viridis", vmin=vmin, vmax=vmax)
            fig.colorbar(im, ax=ax, label="Höhe (m)", shrink=0.75)

        # Canvas einrichten
        self.canvas_figure = fig
        canvas = FigureCanvasTkAgg(fig, master=self.right_frame_top)
        self.canvas = canvas
        self.canvas_widget = canvas.get_tk_widget()
        self.canvas_widget.pack(side="top", fill="both", expand=True, padx=(0,60), pady=(10,0))
        self.canvas.draw()


    def upload_image(self):
        """Lädt eine GeoTIFF-Datei und aktualisiert Plot + Metadaten."""
        file_path = filedialog.askopenfilename(filetypes=[("TIF Files", "*.tif"), ("All Files", "*.*")])
        if not file_path:
            return

        # Tabelle leeren
        if self.peaks_table:
            for item in self.peaks_table.get_children():
                self.peaks_table.delete(item)

        try:
            # --- Ausgelagertes DEM-Lesen ---
            dem_data, crs, transform, (xres, yres) = read_dem(file_path)
            self.dem_data = dem_data
            self.crs_system = crs
            self.geo_transform = transform

            print(f"Datei geladen: {file_path}")
            print(f"Koordinatensystem: {self.crs_system}")
            print(f"Auflösung: {xres:.2f} m × {yres:.2f} m pro Pixel")

            # Meter↔Pixel-Umrechnung
            try:
                self.pixel_per_meter = calculate_pixels_per_meter(
                    self.crs_system, (xres, yres),
                    transform.a, transform.e
                )
                dom_px = self.dominance_threshold * self.pixel_per_meter[1]
                print(f"Dominanz-Schwelle {self.dominance_threshold}m ≙ {dom_px:.2f} px")
            except Exception as e:
                print(f"Fehler Meter↔Pixel: {e}")
                self.pixel_per_meter = None

            vmin = np.nanmin(dem_data)
            vmax = np.nanmax(dem_data)
            # Plot erstellen/aktualisieren
            self._draw_plot(dem_data, vmin, vmax)

        except Exception as e:
            print(f"Fehler beim Laden/Anzeigen des Bildes: {e}")


    def show_peaks(self):
        """Markiert alle gefundenen prominenten Gipfel im Plot und trägt sie in die Tabelle ein."""

        self.update_thresholds_from_entries() # neueste thresholds aus UI

        if self.canvas_widget is None or self.dem_data is None:
            print("Keine Karte geladen oder DEM-Daten fehlen. Bitte lade zuerst eine GeoTIFF-Datei hoch.")
            return
        if self.pixel_per_meter is None:
             print("Pixel pro Meter konnte nicht berechnet werden. Dominanz wird evtl. nicht korrekt umgerechnet.")
             # Entscheidung: Dominanz in Pixel verwenden, wenn Berechnung nicht möglich ist
             dominance_pixels = self.dominance_threshold # Meter-Wert nehmen
        else:
            dominance_pixels = self.dominance_threshold * self.pixel_per_meter[1] # Dominanz [m] in Pixel umrechnen

        try:
            fig = self.canvas_figure

            if not fig.axes:
                print("Fehler: Kein Axes-Objekt im Canvas gefunden.")
                return
            ax = fig.axes[0]

            # Lösche alle alten Marker (Scatter-Elemente) aus dem Axes
            elements_to_remove = [child for child in ax.get_children()
                                  if isinstance(child, matplotlib.collections.PathCollection)]
            if isinstance(ax, matplotlib.axes._axes.Axes) and not isinstance(ax, plt.Axes): # Checken ob 3D Axes
                 elements_to_remove.extend([child for child in ax.collections if isinstance(child, matplotlib.collections.PathCollection)])

            for element in elements_to_remove:
                element.remove()

            # Alte Einträge in der Tabelle löschen
            if self.peaks_table:
                 for item in self.peaks_table.get_children():
                    self.peaks_table.delete(item)

            print(f"Suche Gipfel mit Prominenz >= {self.prominence_threshold}m und Dominanz >= {self.dominance_threshold}m ({dominance_pixels:.2f} Pixel)")

            # finde Gipfel
            peaks = find_peaks(
                self.dem_data,
                prominence_threshold_val=self.prominence_threshold,
                dominance_threshold_val=dominance_pixels,
                orographic_dominence_threshold_val=self.orographic_threshold,
                border_width=self.border_width,
                min_height=self.min_height_threshold,
            )

            if not peaks:
                print("Keine prominenten Gipfel gefunden mit den aktuellen Kriterien.")
                return

            print(f"Gefundene Gipfel: {len(peaks)}")

            peak_coords_x = []
            peak_coords_y = []
            peak_coords_z = []# Für 3D plot

            for idx, (peak_xy, peak_h, prom, dom_pix) in enumerate(peaks, start=1):
                x, y = peak_xy
                z = self.dem_data[y, x] # Höhe aus DEM daten

                # Konvertiere Pixel-Koordinaten in CRS-Welt-Koordinaten (Rasterio)
                try:
                    world_x, world_y = rasterio.transform.xy(self.geo_transform, y, x)
                except Exception as trans_e:
                    print(f"Fehler bei der Koordinatentransformation für Gipfel {idx}: {trans_e}")
                    continue # Skip bei Fehler

                # Konvertiere CRS-Koordinaten aus der Datei zu WGS84 (Lat/Lon)
                try:
                    long, lat = convert_coordinates_to_wgs84(world_x, world_y, self.crs_system)
                    long_str = f"{long:.8f}" # Formatieren
                    lat_str = f"{lat:.8f}"  # Formatieren
                except Exception as wgs_e:
                    print(f"Fehler bei der Umwandlung zu WGS84 für Gipfel {idx}: {wgs_e}")
                    long_str, lat_str = "Fehler", "Fehler" # Bei Fehler setzen

                # vorbereiten der Koordinaten für den Plot
                peak_coords_x.append(x)
                peak_coords_y.append(y)
                if self.dimension_switch.get() == 1:
                    peak_coords_z.append(z + 10) # Offset für mehr Sichtbarkeit in 3D

                # Tabelleintrag erstellen
                dom_meters = dom_pix / self.pixel_per_meter[1] if self.pixel_per_meter else "N/A"
                new_entry = (idx, f"{x}, {y}", lat_str, long_str, f"{z}")
                self.peaks_table.insert("", "end", values=new_entry)

                # Speichern der Peaks in einer CSV-Datei
                csv_new_entry = (idx, f"{x}, {y}", lat_str, long_str, z, prom, f"{dom_meters:.2f}", f"{(prom/z)*100:.2f}")
                self.peaks_csv.append(csv_new_entry)
                print(f"({idx}) Gipfel: Pixel(x={x}, y={y}), Höhe={z}m, Lat={lat_str}, Lon={long_str}, Prom={prom}m, Dom={dom_meters:.2f}m, Oro. Dom={(prom/z)*100:.2f}%")


            # Plot der Gipfel
            plot_label = "Gipfel" if peak_coords_x else "" # Label
            if self.dimension_switch.get() == 1 and peak_coords_x:
                 # 3D Mode
                 if hasattr(ax, 'scatter'):
                    ax.scatter(peak_coords_x, peak_coords_y, peak_coords_z, c='r', marker='^', s=50, depthshade=True, label=plot_label)
                 else:
                     print("Warnung: Versuch, 3D-Scatter auf einem 2D-Axes zu zeichnen.")
            elif peak_coords_x:
                 # 2D Mode
                 ax.scatter(peak_coords_x, peak_coords_y, c='r', marker='^', s=40, label=plot_label)


            # Legende hinzufügen
            if plot_label and not ax.get_legend(): # Nur eine Legende
                 ax.legend()

            # canvas aktualisieren
            if self.canvas:
                self.canvas.draw()

        except AttributeError as ae:
             print(f"AttributeError in show_peaks (möglicherweise fehlt canvas oder figure): {ae}")
        except IndexError as ie:
             print(f"IndexError in show_peaks (möglicherweise Problem mit DEM-Daten oder Koordinaten): {ie}")
        except Exception as e:
            import traceback
            print(f"Allgemeiner Fehler beim Markieren der Gipfel: {e}")
            print(traceback.format_exc()) # full traceback für debugging


    def open_settings_window(self):
        """Öffnet ein neues Fenster (Placeholder)."""
        settings_window = Toplevel(self.root)
        settings_window.title("Einstellungen")
        settings_window.geometry("300x200")
        settings_window.configure(bg=self.root.cget('bg')) 

        # Border-Width einstellen
        bw_label = ctk.CTkLabel(settings_window, text="Randbreite (px):")
        bw_label.pack(pady=(20,5), padx=20, anchor="w")
        bw_var = ctk.StringVar(value=str(self.border_width))
        bw_entry = ctk.CTkEntry(settings_window, textvariable=bw_var)
        bw_entry.pack(pady=(0,10), padx=20, fill="x")

        def save_and_close():
            try:
                val = int(bw_var.get())
                if val >= 0:
                    self.border_width = val
                    print(f"Border-Width aktualisiert auf: {self.border_width} px")
            except ValueError:
                print(f"Ungültige Eingabe für Randbreite: '{bw_var.get()}'. Behalte alten Wert.")
            settings_window.destroy()

        save_btn = ctk.CTkButton(settings_window, text="Speichern", command=save_and_close)
        save_btn.pack(pady=10, padx=20, fill="x")


    def open_info_window(self):
        """Öffnet ein neues Fenster mit Info-Text."""
        info_window = Toplevel(self.root)
        info_window.title("Info")
        info_window.geometry("450x350")
        info_window.configure(bg=self.root.cget('bg')) # Hintergrundfarbe anpassen

        info_text = """
Prominenz:
Die Höhendifferenz zwischen einem Gipfel und der höchsten Einschartung (Sattel), über die man zu einem höheren Gipfel gelangen muss. Sie misst die "Eigenständigkeit" eines Gipfels.

Dominanz:
Die horizontale Entfernung (Luftlinie) vom Gipfel zum nächstgelegenen Punkt auf gleicher Höhe, der zu einem höheren Gipfel gehört. Sie gibt an, wie weit ein Gipfel seine Umgebung "überragt".
        
Orographische Dominanz:
Die relative Höhe eines Gipfels im Verhältnis zu seiner Prominenz. Sie wird in Prozent angegeben und beschreibt, wie stark ein Gipfel aus dem Gelände herausragt.      
        """

        info_label = ctk.CTkLabel(info_window,
                                  text=info_text,
                                  wraplength=380,
                                  justify="left",
                                  anchor="w")
        info_label.pack(pady=20, padx=20, fill="x")


    def update_thresholds_from_entries(self):
        """Liest die Schwellenwerte aus den Eingabefeldern und aktualisiert die Instanzvariablen."""
        # Prominenz
        try:
            prom_val_str = self.prominence_entry.get()
            if prom_val_str:  # Nur wenn nicht leer
                prom_val = float(prom_val_str)
                if prom_val >= 0:
                    self.prominence_threshold = prom_val
                    print(f"Prominenzschwelle aktualisiert auf: {self.prominence_threshold} m")
                else:
                    print("Ungültige Prominenz (negativ). Behalte alten Wert.")
        except ValueError:
            print(f"Ungültige Eingabe für Prominenz: '{self.prominence_entry.get()}'. Behalte alten Wert: {self.prominence_threshold}")

        # Dominanz
        try:
            dom_val_str = self.dominance_entry.get()
            if dom_val_str:
                dom_val = float(dom_val_str)
                if dom_val >= 0:
                    self.dominance_threshold = dom_val
                    print(f"Dominanzschwelle aktualisiert auf: {self.dominance_threshold} m")
                else:
                    print("Ungültige Dominanz (negativ). Behalte alten Wert.")
        except ValueError:
            print(f"Ungültige Eingabe für Dominanz: '{self.dominance_entry.get()}'. Behalte alten Wert: {self.dominance_threshold}")

        # Mindesthöhe
        try:
            min_height_val_str = self.min_height_entry.get()
            if min_height_val_str:
                min_height_val = float(min_height_val_str)
                if min_height_val >= 0:
                    self.min_height_threshold = min_height_val
                    print(f"Mindesthöhe aktualisiert auf: {self.min_height_threshold} m")
                else:
                    print("Ungültige Mindesthöhe (negativ). Behalte alten Wert.")
        except ValueError:
            print(f"Ungültige Eingabe für Mindesthöhe: '{self.min_height_entry.get()}'. Behalte alten Wert: 0")

        # Orographische Dominanz
        try:
            oro_str = self.orographic_entry.get()
            if oro_str:
                oro_val = float(oro_str)
                if oro_val >= 0:
                    self.orographic_threshold = oro_val
                    print(f"Orographische Dominanz-Schwelle aktualisiert auf: {self.orographic_threshold} %")
                else:
                    print("Ungültige Orographische Dominanz (negativ). Behalte alten Wert.")
        except ValueError:
            print(f"Ungültige Eingabe für Orographische Dominanz: '{self.orographic_entry.get()}'. Behalte alten Wert: {self.orographic_threshold}")
 

    def apply_preset(self, preset: str):
        """
        Schreibt für bestimmte Voreinstellungen Prominenz- und Dominanz-Werte
        in die Entry-Felder und aktualisiert die internen Werte.
        """
        prom_val, dom_val = None, None
        prom_placeholder, dom_placeholder = "500", "2000" # Defaults

        if preset == "Himalaya-Modus":
            prom_val, dom_val = 500, 2000
        elif preset == "UIAA-Alpinismus":
            prom_val, dom_val = 30, 100
        elif preset == "Kartografischer Modus":
            prom_val, dom_val = 200, 1000
        elif preset == "benutzerdefiniert":
            prom_placeholder = "500"
            dom_placeholder = "2000"
        else:
             pass

        # Update der UI-Einträge
        self.prominence_entry.delete(0, "end")
        if prom_val is not None:
            self.prominence_entry.insert(0, str(prom_val))
        else:
            self.prominence_entry.configure(placeholder_text=prom_placeholder)

        self.dominance_entry.delete(0, "end")
        if dom_val is not None:
            self.dominance_entry.insert(0, str(dom_val))
        else:
             self.dominance_entry.configure(placeholder_text=dom_placeholder)
        
        # Update der internen Variablen
        if prom_val is not None:
            self.prominence_threshold = prom_val
        if dom_val is not None:
            self.dominance_threshold = dom_val

        print(f"Preset '{preset}' angewendet. Prominenz: {self.prominence_threshold}, Dominanz: {self.dominance_threshold}")


    def export_csv_table(self):
        """Exportiert die aktuelle Peaks-Tabelle als CSV."""
        # Dateiauswahl-Dialog für Speicherort
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")],
            title="Tabelle als CSV speichern"
        )
        if not path:
            return  # Abgebrochen

        # Spaltenüberschriften aus Treeview
        cols = [ "Nr.", "Pixel-Koord", "Breitengrad", "Längengrad", "Höhe (m)", "Prominenz (m)", "Dominanz (m)", "Oro. Dominanz (%)" ]

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(cols)
                for item in self.peaks_csv:
                    #row = [item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7]]
                    writer.writerow(item)
            print(f"Tabelle erfolgreich exportiert nach: {path}")
        except Exception as e:
            print(f"Fehler beim Export der Tabelle: {e}")


    def run(self):
        """Starts the Tkinter main loop."""
        self.root.mainloop()

# --- Starten der GUI ---
if __name__ == "__main__":
    root = ctk.CTk()
    app = PeakFinderApp(root)
    app.run()