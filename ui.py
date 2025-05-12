import customtkinter as ctk
from tkinter import filedialog, Toplevel, ttk
import rasterio
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import matplotlib
import numpy as np
import rasterio.transform
#from mpl_toolkits.mplot3d import Axes3D # Uncomment if needed for future 3D enhancements
from algo import find_peaks # Assuming algo.py exists with find_peaks
from geo_utils import calculate_pixels_per_meter, convert_coordinates_to_wgs84 # Assuming geo_utils.py exists

# Agg-Backend erzwingen (verhindert das Öffnen von Fenstern durch Matplotlib)
matplotlib.use("Agg")
plt.style.use('dark_background')

# Initialisiere CustomTkinter - Global settings applied before class instantiation
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class PeakFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PeakFinder")
        self.root.geometry("1000x600")
        self._set_icon() # Set icon during initialization

        # --- Instance Variables ---
        self.canvas = None # Canvas-Referenz für draw()
        self.canvas_widget = None # Holds the Tkinter widget for the canvas
        self.canvas_figure = None # Holds the Matplotlib Figure object
        self.dem_data = None
        self.peaks_table = None
        self.pixel_per_meter = None
        self.geo_transform = None
        self.crs_system = None
        self.prominence_threshold = 500 # Default value
        self.dominance_threshold = 2000 # Default value

        # --- UI Element References ---
        self.left_frame = None
        self.right_frame = None
        self.right_frame_bottom = None
        self.dimension_switch = None
        self.prominence_entry = None
        self.dominance_entry = None
        self.preset_combobox = None

        # --- Setup UI ---
        self._create_frames()
        self._create_left_widgets()
        self._create_right_widgets() # Placeholder for canvas
        self._create_table() # Create table in the bottom right frame

    def _set_icon(self):
        """Loads and sets the application icon."""
        try:
            icon_img = Image.open("icon.png") # Ensure icon.png is in the same directory
            icon_photo = ImageTk.PhotoImage(icon_img)
            self.root.iconphoto(True, icon_photo)
        except FileNotFoundError:
            print("Warning: icon.png not found. Skipping icon setting.")
        except Exception as e:
            print(f"Error loading icon: {e}")

    def _create_frames(self):
        """Creates the main layout frames."""
        self.left_frame = ctk.CTkFrame(self.root, width=200, corner_radius=10)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.right_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.right_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        # Bottom frame within the right frame for the table
        self.right_frame_bottom = ctk.CTkScrollableFrame(self.right_frame, height=150, corner_radius=10) # Adjusted height slightly
        self.right_frame_bottom.pack(side="bottom", fill="x", padx=10, pady=10) # Fill x only

    def _create_left_widgets(self):
        """Creates widgets within the left frame."""
        title_label = ctk.CTkLabel(self.left_frame, text="PeakFinder", font=("Arial", 18, "bold"))
        title_label.pack(side="top", pady=10, padx=20)

        upload_button = ctk.CTkButton(self.left_frame, text="Karte hochladen", command=self.upload_image)
        upload_button.pack(pady=10, padx=20)

        find_peaks_button = ctk.CTkButton(self.left_frame, text="Gipfel finden", fg_color="green", command=self.show_peaks)
        find_peaks_button.pack(pady=10, padx=20)

        # --- Plot Mode Switch ---
        self.dimension_switch = ctk.CTkSwitch(self.left_frame, text="3D Modus")
        self.dimension_switch.pack(pady=10, padx=20)

        # --- Presets ComboBox ---
        self.preset_combobox = ctk.CTkOptionMenu(self.left_frame,
                                                 command=self.apply_preset,
                                                 fg_color="gray25",
                                                 button_color="gray20",
                                                 button_hover_color="gray15")
        self.preset_combobox.pack(pady=10, padx=20)
        self.preset_combobox.configure(values=["Jurgalski-Modus", "UIAA-Alpinismus", "Kartografischer Modus", "benutzerdefiniert"])
        self.preset_combobox.set("Voreinstellungen")

        # --- Prominence Entry ---
        prominence_label = ctk.CTkLabel(self.left_frame, text="Prominenz (m):")
        prominence_label.pack(pady=(10,0), padx=20) # Reduced padding below label
        self.prominence_entry = ctk.CTkEntry(self.left_frame, placeholder_text=str(self.prominence_threshold))
        self.prominence_entry.pack(pady=(0,10), padx=20) # Reduced padding above entry

        # --- Dominance Entry ---
        dominance_label = ctk.CTkLabel(self.left_frame, text="Dominanz (m):")
        dominance_label.pack(pady=(10,0), padx=20)
        self.dominance_entry = ctk.CTkEntry(self.left_frame, placeholder_text=str(self.dominance_threshold))
        self.dominance_entry.pack(pady=(0,10), padx=20)

        # --- Info Label (Bottom) ---
        info_label = ctk.CTkLabel(self.left_frame, text="Was ist Prominenz/ Dominanz?", text_color="gray", cursor="hand2")
        info_label.pack(side="bottom", pady=(0,5), padx=20) # Adjusted padding
        info_label.bind("<Button-1>", lambda e: self.open_info_window())

        # --- Settings Button (Bottom) ---
        settings_button = ctk.CTkButton(self.left_frame, text="⚙️ Einstellungen", command=self.open_settings_window)
        settings_button.pack(side="bottom", pady=5, padx=10) # Adjusted padding

    def _create_right_widgets(self):
        """Sets up the area for the Matplotlib canvas."""
        # The canvas itself is created/updated in upload_image
        pass

    def _create_table(self):
        """Creates the ttk.Treeview table for peak data."""
        style = ttk.Style()
        style.theme_use("default") # Use a theme compatible with ttk
        style.configure("Treeview",
                        background="#2B2B2B",
                        foreground="white",
                        rowheight=25,
                        fieldbackground="#2B2B2B")
        style.map("Treeview", background=[("selected", "#1E90FF")])
        style.configure("Treeview.Heading",
                        background="#2B2B2B",
                        foreground="white",
                        relief="flat")
        style.map("Treeview.Heading", background=[('active', '#3C3C3C')]) # Add hover effect for heading


        table = ttk.Treeview(self.right_frame_bottom,
                             columns=("Nummer", "Pixel-Koord", "Breitengrad", "Längengrad", "Höhe"),
                             show="headings")

        table.heading("Nummer", text="Nr.")
        table.heading("Pixel-Koord", text="Pixel (x, y)")
        table.heading("Breitengrad", text="Breitengrad")
        table.heading("Längengrad", text="Längengrad")
        table.heading("Höhe", text="Höhe (m)")

        table.column("Nummer", width=40, anchor="center", stretch=False)
        table.column("Pixel-Koord", width=120, anchor="center", stretch=True)
        table.column("Breitengrad", width=150, anchor="center", stretch=True)
        table.column("Längengrad", width=150, anchor="center", stretch=True)
        table.column("Höhe", width=80, anchor="center", stretch=True)

        self.peaks_table = table
        # Use pack instead of grid for simpler layout within the scrollable frame
        self.peaks_table.pack(expand=True, fill="both")


    def open_settings_window(self):
        """Öffnet ein neues Fenster, um vmin und vmax einzustellen (Placeholder)."""
        # Currently this window is empty as per original code
        settings_window = Toplevel(self.root)
        settings_window.title("Einstellungen")
        settings_window.geometry("300x250")
        # Add setting controls here in the future if needed
        # For now, it just opens an empty window
        label = ctk.CTkLabel(settings_window, text="Einstellungen (aktuell keine Funktion)")
        label.pack(pady=20)

    def upload_image(self):
        """Lädt eine GeoTIFF-Datei hoch und zeigt sie abhängig vom Switch als 2D- oder 3D-Plot an."""
        file_path = filedialog.askopenfilename(filetypes=[("TIF Files", "*.tif"), ("All Files", "*.*")])

        if not file_path:
            return # User cancelled

        # Clear existing table entries
        if self.peaks_table:
            for item in self.peaks_table.get_children():
                self.peaks_table.delete(item)

        print(f"Datei ausgewählt: {file_path}")

        try:
            with rasterio.open(file_path) as src:
                dem_data = src.read(1)
                self.dem_data = dem_data # Store DEM data

                self.crs_system = src.crs
                self.geo_transform = src.transform # Store transform
                xres, yres = src.res
                pixel_scale = xres, yres

                print(f"Koordinatensystem: {self.crs_system}")
                print(f"Auflösung: {xres} m/pixel, {yres} m/pixel")

                # Calculate pixels per meter (handle potential errors in the utility function)
                try:
                    self.pixel_per_meter = calculate_pixels_per_meter(src.crs, pixel_scale, src.transform.a, src.transform.e)
                    print(f"Pixel pro Meter (Breite, Höhe): {self.pixel_per_meter}")
                    # Example usage: Dominance in pixels (using height resolution)
                    dominance_pixels = self.dominance_threshold * self.pixel_per_meter[1] if self.pixel_per_meter else "Berechnung fehlgeschlagen"
                    print(f"Aktuelle Dominanz ({self.dominance_threshold}m) in Pixel: {dominance_pixels}")
                except Exception as calc_e:
                    print(f"Fehler bei der Berechnung von Pixel pro Meter: {calc_e}")
                    self.pixel_per_meter = None # Reset on error

                vmin = np.nanmin(dem_data) # Use nanmin/nanmax to handle potential NoData values
                vmax = np.nanmax(dem_data)

                # --- Create or Update Plot ---
                if self.canvas_widget:
                    self.canvas_widget.destroy() # Remove old canvas widget
                    plt.close(self.canvas_figure) # Close the old figure explicitly

                fig = plt.figure(facecolor="#2B2B2B") # Adjust figsize as needed
                #fig.patch.set_alpha(0.85) # Keep background semi-transparent if desired

                if self.dimension_switch.get() == 1:
                    # 3D Mode
                    ax = fig.add_subplot(111, projection='3d')
                    x = np.arange(dem_data.shape[1])
                    y = np.arange(dem_data.shape[0])
                    X, Y = np.meshgrid(x, y)
                    plt.gca().set_facecolor('#2B2B2B') # Set background color for 3D plot
                    # Handle potential NaN values for plotting if necessary
                    surf = ax.plot_surface(X, Y, dem_data, cmap="viridis", vmin=vmin, vmax=vmax)
                    fig.colorbar(surf, ax=ax, label="Höhe (m)", shrink=0.75)
                else:
                    # 2D Mode
                    ax = fig.add_subplot(111)
                    im = ax.imshow(dem_data, cmap="viridis", vmin=vmin, vmax=vmax)
                    fig.colorbar(im, ax=ax, label="Höhe (m)", shrink=0.75) # Adjust colorbar size


                self.canvas_figure = fig # Store the figure object
                canvas = FigureCanvasTkAgg(fig, master=self.right_frame)
                self.canvas = canvas
                # Canvas-Widget holen und packen
                if self.canvas_widget:
                    self.canvas_widget.destroy()

                self.canvas_widget = canvas.get_tk_widget()
                self.canvas_widget.pack(side="top", fill="both", expand=True, padx=(0,60), pady=(10,0))
                # direkt zeichnen
                self.canvas.draw()


        except rasterio.RasterioIOError as rio_e:
            print(f"Rasterio Fehler beim Lesen der Datei: {rio_e}")
            # Optionally show an error message to the user
        except ImportError as imp_e:
             print(f"Import Fehler: {imp_e}. Stellen Sie sicher, dass alle Bibliotheken installiert sind.")
        except Exception as e:
            print(f"Allgemeiner Fehler beim Laden/Anzeigen des Bildes: {e}")


    def show_peaks(self):
        """Markiert alle gefundenen prominenten Gipfel im Plot und trägt sie in die Tabelle ein."""
        if self.canvas_widget is None or self.dem_data is None:
            print("Keine Karte geladen oder DEM-Daten fehlen. Bitte lade zuerst eine GeoTIFF-Datei hoch.")
            return
        if self.pixel_per_meter is None:
             print("Pixel pro Meter konnte nicht berechnet werden. Dominanz wird evtl. nicht korrekt umgerechnet.")
             # Decide how to handle this - maybe use a default or skip dominance calculation?
             # For now, we'll proceed but the dominance threshold in pixels might be wrong.
             dominance_pixels = self.dominance_threshold # Fallback or default? Needs decision.
        else:
            dominance_pixels = self.dominance_threshold * self.pixel_per_meter[1] # Use calculated value


        self.update_thresholds_from_entries() # Get latest thresholds from UI

        try:
            fig = self.canvas_figure
            # Get the correct axes object (can be 2D or 3D)
            if not fig.axes:
                print("Fehler: Kein Axes-Objekt im Canvas gefunden.")
                return
            ax = fig.axes[0]

            # Clear previous peak markers (important for re-running peak detection)
            # Find existing scatter plots (potential peaks) and remove them
            elements_to_remove = [child for child in ax.get_children()
                                  if isinstance(child, matplotlib.collections.PathCollection)] # Scatter plots are PathCollections
            if isinstance(ax, matplotlib.axes._axes.Axes) and not isinstance(ax, plt.Axes): # Check if it's 3D Axes
                 elements_to_remove.extend([child for child in ax.collections if isinstance(child, matplotlib.collections.PathCollection)])


            for element in elements_to_remove:
                element.remove()


            # Clear existing table entries before adding new ones
            if self.peaks_table:
                 for item in self.peaks_table.get_children():
                    self.peaks_table.delete(item)


            print(f"Suche Gipfel mit Prominenz >= {self.prominence_threshold}m und Dominanz >= {self.dominance_threshold}m ({dominance_pixels:.2f} Pixel)")

            # Find peaks using the algorithm
            peaks = find_peaks(
                self.dem_data,
                prominence_threshold_val=self.prominence_threshold,
                dominance_threshold_val=dominance_pixels # Use pixel value
            )

            if not peaks:
                print("Keine prominenten Gipfel gefunden mit den aktuellen Kriterien.")
                self.canvas_widget.draw() # Redraw canvas to remove old markers if any
                return

            print(f"Gefundene Gipfel: {len(peaks)}")

            peak_coords_x = []
            peak_coords_y = []
            peak_coords_z = []# For 3D plot

            for idx, (peak_xy, peak_h, prom, dom_pix) in enumerate(peaks, start=1):
                x, y = peak_xy # Pixel coordinates
                z = self.dem_data[y, x] # Height from DEM data

                # Convert pixel coordinates to the file's CRS coordinates
                try:
                    world_x, world_y = rasterio.transform.xy(self.geo_transform, y, x)
                except Exception as trans_e:
                    print(f"Fehler bei der Koordinatentransformation für Gipfel {idx}: {trans_e}")
                    continue # Skip this peak if transformation fails

                # Convert file's CRS coordinates to WGS84 (Lat/Lon)
                try:
                    long, lat = convert_coordinates_to_wgs84(world_x, world_y, self.crs_system)
                    long_str = f"{long:.6f}" # Format for display
                    lat_str = f"{lat:.6f}"  # Format for display
                except Exception as wgs_e:
                    print(f"Fehler bei der Umwandlung zu WGS84 für Gipfel {idx}: {wgs_e}")
                    long_str, lat_str = "Fehler", "Fehler" # Indicate error in table

                # Prepare data for plotting
                peak_coords_x.append(x)
                peak_coords_y.append(y)
                if self.dimension_switch.get() == 1:
                    peak_coords_z.append(z + 10) # Offset slightly for visibility in 3D

                # Add to table
                dom_meters = dom_pix / self.pixel_per_meter[1] if self.pixel_per_meter else "N/A" # Convert dominance back to meters if possible
                # Use formatted strings for table
                new_entry = (idx, f"{x}, {y}", lat_str, long_str, f"{z:.2f}")
                self.peaks_table.insert("", "end", values=new_entry)

                print(f"({idx}) Gipfel: Pixel(x={x}, y={y}), Höhe={z:.2f}m, Lat={lat_str}, Lon={long_str}, Prom={prom:.2f}m, Dom={dom_meters}m")


            # Plot all peaks at once for better performance
            plot_label = "Gipfel" if peak_coords_x else "" # Add label only if peaks exist
            if self.dimension_switch.get() == 1 and peak_coords_x:
                 # 3D Mode - Ensure ax is 3D capable
                 if hasattr(ax, 'scatter'):
                    ax.scatter(peak_coords_x, peak_coords_y, peak_coords_z, c='r', marker='^', s=50, depthshade=True, label=plot_label)
                 else:
                     print("Warnung: Versuch, 3D-Scatter auf einem 2D-Axes zu zeichnen.")
            elif peak_coords_x:
                 # 2D Mode
                 ax.scatter(peak_coords_x, peak_coords_y, c='r', marker='^', s=40, label=plot_label)


            # Add legend if label was set
            if plot_label and not ax.get_legend(): # Add legend only once
                 ax.legend()

            # ganz am Ende, nach dem Scatter-Aufruf und Einfügen in die Tabelle,
            # nicht self.canvas_widget.draw(), sondern:
            if self.canvas:
                self.canvas.draw()

        except AttributeError as ae:
             print(f"AttributeError in show_peaks (möglicherweise fehlt canvas oder figure): {ae}")
        except IndexError as ie:
             print(f"IndexError in show_peaks (möglicherweise Problem mit DEM-Daten oder Koordinaten): {ie}")
        except Exception as e:
            import traceback
            print(f"Allgemeiner Fehler beim Markieren der Gipfel: {e}")
            print(traceback.format_exc()) # Print full traceback for debugging


    def open_info_window(self):
        """Öffnet ein neues Fenster mit Info-Text."""
        info_window = Toplevel(self.root)
        info_window.title("Info")
        info_window.geometry("400x200") # Adjusted size
        info_window.configure(bg=self.root.cget('bg')) # Match background color

        info_text = """
Prominenz:
Die Höhendifferenz zwischen einem Gipfel und der höchsten Einschartung (Sattel), über die man zu einem höheren Gipfel gelangen muss. Sie misst die "Eigenständigkeit" eines Gipfels.

Dominanz:
Die horizontale Entfernung (Luftlinie) vom Gipfel zum nächstgelegenen Punkt auf gleicher Höhe, der zu einem höheren Gipfel gehört. Sie gibt an, wie weit ein Gipfel seine Umgebung "überragt".
        """

        info_label = ctk.CTkLabel(info_window,
                                  text=info_text,
                                  wraplength=380, # Wrap text within window width
                                  justify="left",
                                  anchor="w")
        info_label.pack(pady=20, padx=20, fill="x")

    def update_thresholds_from_entries(self):
        """Liest die Schwellenwerte aus den Eingabefeldern und aktualisiert die Instanzvariablen."""
        try:
            prom_val_str = self.prominence_entry.get()
            if prom_val_str: # Only update if not empty
                prom_val = float(prom_val_str)
                if prom_val >= 0:
                    self.prominence_threshold = prom_val
                    print(f"Prominenzschwelle aktualisiert auf: {self.prominence_threshold} m")
                else:
                     print("Ungültige Prominenz (negativ). Behalte alten Wert.")
            # If empty, keep the existing value (or the default placeholder value if never set)
        except ValueError:
            print(f"Ungültige Eingabe für Prominenz: '{self.prominence_entry.get()}'. Muss eine Zahl sein. Behalte alten Wert: {self.prominence_threshold}")
            # Optionally reset the entry field or show an error message
            self.prominence_entry.delete(0, "end")
            self.prominence_entry.insert(0, str(self.prominence_threshold)) # Restore valid value


        try:
            dom_val_str = self.dominance_entry.get()
            if dom_val_str:
                dom_val = float(dom_val_str)
                if dom_val >= 0:
                    self.dominance_threshold = dom_val
                    print(f"Dominanzschwelle aktualisiert auf: {self.dominance_threshold} m")
                else:
                    print("Ungültige Dominanz (negativ). Behalte alten Wert.")
            # If empty, keep the existing value
        except ValueError:
             print(f"Ungültige Eingabe für Dominanz: '{self.dominance_entry.get()}'. Muss eine Zahl sein. Behalte alten Wert: {self.dominance_threshold}")
             self.dominance_entry.delete(0, "end")
             self.dominance_entry.insert(0, str(self.dominance_threshold))

    def apply_preset(self, preset: str):
        """
        Schreibt für bestimmte Voreinstellungen Prominenz- und Dominanz-Werte
        in die Entry-Felder und aktualisiert die internen Werte.
        """
        prom_val, dom_val = None, None
        prom_placeholder, dom_placeholder = "500", "2000" # Defaults

        if preset == "Jurgalski-Modus":
            prom_val, dom_val = 500, 2000
        elif preset == "UIAA-Alpinismus":
            prom_val, dom_val = 300, 1000
        elif preset == "Kartografischer Modus":
            prom_val, dom_val = 100, 500 # Adjusted example values
        # Handle "benutzerdefiniert" or unexpected values - just clear placeholders
        elif preset == "benutzerdefiniert":
             prom_placeholder = "500"
             dom_placeholder = "2000"
             # Don't change prom_val/dom_val, let user input
        else: # Includes "Voreinstellungen" placeholder
             pass # Keep defaults / current values

        # Update Entry fields
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


        # Directly update internal thresholds if a valid preset was selected
        if prom_val is not None:
            self.prominence_threshold = prom_val
        if dom_val is not None:
            self.dominance_threshold = dom_val

        print(f"Preset '{preset}' angewendet. Prominenz: {self.prominence_threshold}, Dominanz: {self.dominance_threshold}")


    def run(self):
        """Starts the Tkinter main loop."""
        self.root.mainloop()

# --- Main execution block ---
if __name__ == "__main__":
    root = ctk.CTk()
    app = PeakFinderApp(root)
    app.run()