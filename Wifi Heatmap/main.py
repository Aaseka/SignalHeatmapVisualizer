import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from tkinter import filedialog, messagebox
from PIL import Image
import csv
import subprocess
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# wifi signal utilzing netsh
def get_signal_strength():
    try:
        result = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout
            for line in output.splitlines():
                if "Signal" in line:
                    signal_line = line.strip()
                    signal_strength = signal_line.split(":")[1].strip().replace('%', '')
                    return int(signal_strength)
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# Function to collect data on click and ensure minimum distance
def collect_data_on_click(event, positions, extent, fig, ax, min_distance=50):
    signal_strength = get_signal_strength()
    if signal_strength is not None:
        x_mapped = event.xdata
        y_mapped = event.ydata

        if x_mapped is not None and y_mapped is not None:
            is_valid = True
            for px, py, _ in positions:
                distance = np.sqrt((x_mapped - px)**2 + (y_mapped - py)**2)
                if distance < min_distance:
                    is_valid = False
                    break

            if is_valid:
                positions.append((x_mapped, y_mapped, signal_strength))
                print(f"Collected Position: ({x_mapped}, {y_mapped}), Signal Strength: {signal_strength}%")

                ax.plot(x_mapped, y_mapped, 'ro') 
                fig.canvas.draw()
            else:
                messagebox.showwarning("Invalid Click", "The selected point is too close to an existing point. Please choose a different location.")
        else:
            print("Click was outside the image boundaries!")

# Function to generate heatmap
def generate_heatmap(positions, floor_plan_path):
    if len(positions) < 4:
        messagebox.showerror("Error", "Please collect data from at least 4 points before generating a heatmap!")
        return

    img = mpimg.imread(floor_plan_path)
    img_extent = [0, img.shape[1], 0, img.shape[0]]

    x = [pos[0] for pos in positions]
    y = [pos[1] for pos in positions]
    signal = [pos[2] for pos in positions]

    grid_size = 300
    grid_x, grid_y = np.meshgrid(
        np.linspace(img_extent[0], img_extent[1], grid_size),
        np.linspace(img_extent[2], img_extent[3], grid_size)
    )
    heatmap_data = np.zeros_like(grid_x)

    for px, py, ps in zip(x, y, signal):
        distance = np.sqrt((grid_x - px)**2 + (grid_y - py)**2)
        wave_effect = ps * np.exp(-distance / 50)
        heatmap_data += wave_effect

    heatmap_data = np.clip(heatmap_data, 0, 100)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(img, extent=img_extent, aspect='auto', alpha=0.5)
    heatmap = ax.contourf(grid_x, grid_y, heatmap_data, levels=20, cmap='coolwarm', alpha=0.7)
    cbar = plt.colorbar(heatmap, ax=ax)
    cbar.set_label("Signal Strength (%)")
    ax.set_title("Wi-Fi Coverage Heatmap")
    plt.show()

# Function to save data to a CSV file
def save_to_csv(positions):
    if not positions:
        messagebox.showerror("Error", "No data to save!")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")],
        title="Save Collected Data"
    )
    if file_path:
        with open(file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["X", "Y", "SignalStrength"])
            writer.writerows(positions)
        messagebox.showinfo("Info", f"Data saved to {file_path}")

# Function to load data from a CSV file
def load_from_csv():
    file_path = filedialog.askopenfilename(
        title="Select a CSV File",
        filetypes=[("CSV Files", "*.csv")]
    )
    if file_path:
        try:
            with open(file_path, mode='r') as file:
                reader = csv.reader(file)
                next(reader)  # Skip the header row
                return [(float(row[0]), float(row[1]), int(row[2])) for row in reader]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data from CSV: {e}")
    return []

# Main GUI function
def start_gui():
    positions = []
    floor_plan_path = None

    def load_floor_plan():
        nonlocal floor_plan_path, positions  # Ensure positions is updated in the outer scope
        positions = []  # Reset positions whenever a new floor plan is loaded
        floor_plan_path = filedialog.askopenfilename(title="Select a Floor Plan Image", filetypes=[("Image Files", "*.png;*.jpg")])
        if not floor_plan_path:
            messagebox.showerror("Error", "No floor plan selected!")
            return
        
        img = Image.open(floor_plan_path)
        fig, ax = plt.subplots(figsize=(10, 8))
        extent = [0, img.width, 0, img.height]
        ax.imshow(img, aspect='auto', extent=extent)
        ax.set_title("Click to collect signal strength")
        fig.canvas.mpl_connect('button_press_event', lambda event: collect_data_on_click(event, positions, extent, fig, ax))
        plt.show()

    def complete_data_collection():
        if len(positions) < 4:
            messagebox.showerror("Error", "Please collect data from at least 4 points!")
        else:
            messagebox.showinfo("Info", "Data collection complete! You can now generate the heatmap.")

    def generate_heatmap_button():
        generate_heatmap(positions, floor_plan_path)

    def save_data_button():
        save_to_csv(positions)

    def load_data_button():
        nonlocal positions
        loaded_positions = load_from_csv()
        if loaded_positions:
            positions = loaded_positions
            generate_heatmap(positions, floor_plan_path)

    root = ttk.Window(themename="superhero")  # Use a modern theme
    root.title("Wi-Fi Coverage Heatmap Generator")
    root.geometry("400x400")

    title_label = ttk.Label(root, text="Wi-Fi Coverage Heatmap", font=("Helvetica", 16, "bold"))
    title_label.pack(pady=20)

    frame = ttk.Frame(root)
    frame.pack(pady=20)

    load_button = ttk.Button(frame, text="Load Floor Plan", command=load_floor_plan, width=20, bootstyle=SUCCESS)
    load_button.grid(row=0, column=0, padx=10, pady=5)

    complete_button = ttk.Button(frame, text="Complete", command=complete_data_collection, width=20, bootstyle=INFO)
    complete_button.grid(row=1, column=0, padx=10, pady=5)

    generate_button = ttk.Button(frame, text="Generate Heatmap", command=generate_heatmap_button, width=20, bootstyle=PRIMARY)
    generate_button.grid(row=2, column=0, padx=10, pady=5)

    save_button = ttk.Button(frame, text="Save to CSV", command=save_data_button, width=20, bootstyle=WARNING)
    save_button.grid(row=3, column=0, padx=10, pady=5)

    load_csv_button = ttk.Button(frame, text="Load in CSV", command=load_data_button, width=20, bootstyle=DANGER)
    load_csv_button.grid(row=4, column=0, padx=10, pady=5)

    root.mainloop()

# start
start_gui()
