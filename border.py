"""
border.py

This script adds a white border to your image while keeping the same format
it had before.

You can add the width and height you want your new image to have, plus the
white border of the longest side. The other one will be calculated with those three values.

Used tkinter for GUI and PIL for image processing
"""

import os
import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox, ttk
from PIL import Image, ImageOps
import json
import subprocess
from enum import Enum

"""
JSON that contains the last configuration used when editing an image
"""
last_json_data = "last_config"

"""
Enum class containing the items that can be saved
on json files and that will be used for editing the image
"""
class Entries(Enum):
    WIDTH_ENTRY = "output_width"
    HEIGHT_ENTRY = "output_height"
    BORDER_SIZE_HEIGHT_ENTRY = "height_border_size"
    POSTFIX_ENTRY = "postfix"


"""
Enum class to understand orientation of the image based on the exif data
of the original image
"""
class Orientation(Enum):
    NORMAL = 1
    CLOCKWISE_90 = 8
    CLOCKWISE_180 = 3
    CLOCKWISE_270 = 6

"""
Method for adding the white border to the image

Improvements
    finding divisors or closest divisor to avoid having to resize the image twice for precision
"""
def add_white_border(input_image_path, output_image_path, output_width, output_height, longest_side_border_size,
                     postfix):
    return_value = True
    with Image.open(input_image_path).copy() as img_copy:

        # Using exif data to properly rotate the image
        exif_data = img_copy.getexif()
        if exif_data:
            orientation = exif_data.get(0x0112)  # EXIF tag for orientation

            if orientation is Orientation.CLOCKWISE_90.value:
                img_copy = img_copy.rotate(90, expand=True)
            elif orientation is Orientation.CLOCKWISE_180.value:
                img_copy = img_copy.rotate(180, expand=True)
            elif orientation is Orientation.CLOCKWISE_270.value:
                img_copy = img_copy.rotate(270, expand=True)

        # Getting size of the original image
        original_width, original_height = img_copy.size

        # Getting the output path
        base, ext = os.path.splitext(output_image_path)
        new_output_image_path = f"{base}{postfix}{ext}"

        # Resizing of image depending on which original size is bigger
        if original_height > original_width:
            resize_height = output_height - (longest_side_border_size * 2)
            resize_width = (resize_height * original_width) / original_height
            calculated_border_size = (output_width - resize_width) / 2
        else:
            resize_width = output_width - (longest_side_border_size * 2)
            resize_height = (resize_width * original_height) / original_width
            calculated_border_size = (output_height - resize_height) / 2

        # If calculated border is lower than zero, that means the image might be cropped
        if calculated_border_size < 0:
            result = messagebox.askquestion("Proceed?",
                                            f"The current configuration will crop the image {base}. Do you want to "
                                            f"proceed?")
            if result == 'no':
                return_value = False
                return

        # Resizing the image using the lanczos algorithm
        resized_img = img_copy.resize((int(resize_width), int(resize_height)), Image.LANCZOS)

        # Expanding the image with the white border
        if original_height > original_width:
            bordered_img = ImageOps.expand(resized_img, border=(int(calculated_border_size), longest_side_border_size),
                                           fill='white')
        else:
            bordered_img = ImageOps.expand(resized_img, border=(longest_side_border_size, int(calculated_border_size)),
                                           fill='white')

        # This resizing (improvement needed to remove it) is done, because the previous calculations
        # might throw decimals and make the final result a pixel or two imprecise
        bordered_img = bordered_img.resize((output_width, output_height), Image.LANCZOS)

        # Saving the final image
        bordered_img.save(new_output_image_path, format=img_copy.format, quality=100, dpi=img_copy.info.get("dpi"))

    del img_copy
    return return_value

"""
Method for saving configurations
"""
def save_configuration(entries, source=None):
    config_name = None

    if source == "button":
        config_name = simpledialog.askstring("Save Configuration", "Enter configuration name:")
    else:
        config_name = last_json_data

    if config_name:
        config_filename = f"{config_name}.json"

        config_data = {
            Entries.WIDTH_ENTRY.value: entries[Entries.WIDTH_ENTRY].get(),
            Entries.HEIGHT_ENTRY.value: entries[Entries.HEIGHT_ENTRY].get(),
            Entries.BORDER_SIZE_HEIGHT_ENTRY.value: entries[Entries.BORDER_SIZE_HEIGHT_ENTRY].get(),
            Entries.POSTFIX_ENTRY.value: entries[Entries.POSTFIX_ENTRY].get()
        }

        try:
            with open(config_filename, "w") as f:
                json.dump(config_data, f)
            load_combo['values'] = get_all_config_files()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    else:
        messagebox.showwarning("Invalid Name", "Please enter a valid name for the configuration.")

"""
Small method for retrieving config files 
"""
def get_all_config_files():
    return [os.path.splitext(f)[0] for f in os.listdir() if f.endswith('.json') and f != f"{last_json_data}.json"]

"""
Method for loading configurations
"""
def load_selected_configuration(event):
    selected_file = None

    if event:
        selected_file = f"{load_combo.get()}.json"
    else:
        selected_file = f"{last_json_data}.json"

    if selected_file:
        try:
            with open(selected_file, "r") as f:
                config = json.load(f)
                print(config)
                width_entry.delete(0, tk.END)
                width_entry.insert(0, config.get(Entries.WIDTH_ENTRY.value, ""))
                height_entry.delete(0, tk.END)
                height_entry.insert(0, config.get(Entries.HEIGHT_ENTRY.value, ""))
                border_size_height_entry.delete(0, tk.END)
                border_size_height_entry.insert(0, config.get(Entries.BORDER_SIZE_HEIGHT_ENTRY.value, ""))
                postfix_entry.delete(0, tk.END)
                postfix_entry.insert(0, config.get(Entries.POSTFIX_ENTRY.value, ""))
        except FileNotFoundError:
            pass

"""
Main method that does the image processing and calls the rest of the methods 
"""
def process_images(entries, event=None):
    try:
        output_width = int(entries[Entries.WIDTH_ENTRY].get())
        output_height = int(entries[Entries.HEIGHT_ENTRY].get())
        height_border_size = int(entries[Entries.BORDER_SIZE_HEIGHT_ENTRY].get())
        postfix = entries[Entries.POSTFIX_ENTRY].get()

        if not postfix:
            raise TypeError("Add a postfix to avoid modifying the original photo.")

    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter valid values.")
        return
    except TypeError as e:
        messagebox.showerror("Invalid Input", f"{e}")
        return

    save_configuration(entries)

    input_file_paths = filedialog.askopenfilenames(title="Select Input Images",
                                                   filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.tiff;*.bmp;*.gif")])
    if not input_file_paths:
        return
    output_directory = filedialog.askdirectory(title="Select Output Directory")
    if not output_directory:
        return

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for input_image_path in input_file_paths:
        filename = os.path.basename(input_image_path)
        output_image_path = os.path.join(output_directory, filename)
        add_white_border(input_image_path, output_image_path, output_width, output_height, height_border_size, postfix)

    messagebox.showinfo("Process Complete", f"Process Complete")
    output_directory = output_directory.replace("/", "\\")
    subprocess.Popen(['explorer', output_directory])

"""
This needs some improvements for the global variables
But it's the code creating the GUI and gluing all together
"""
if __name__ == '__main__':
    # Create the main application window
    root = tk.Tk()
    root.title("Image Border and Resize Tool")

    # Create and place the widgets
    tk.Label(root, text="Width (pixels):").grid(row=0, column=0, padx=10, pady=10)
    width_entry = tk.Entry(root)
    width_entry.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(root, text="Height (pixels):").grid(row=1, column=0, padx=10, pady=10)
    height_entry = tk.Entry(root)
    height_entry.grid(row=1, column=1, padx=10, pady=10)

    tk.Label(root, text="Longest Side Border Size (pixels):").grid(row=2, column=0, padx=10, pady=10)
    border_size_height_entry = tk.Entry(root)
    border_size_height_entry.grid(row=2, column=1, padx=10, pady=10)

    tk.Label(root, text="Postfix for Edited Photos:").grid(row=3, column=0, padx=10, pady=10)
    postfix_entry = tk.Entry(root)
    postfix_entry.grid(row=3, column=1, padx=10, pady=10)

    load_selected_configuration(event=None)

    # Entries
    all_entries = {
        Entries.WIDTH_ENTRY: width_entry,
        Entries.HEIGHT_ENTRY: height_entry,
        Entries.BORDER_SIZE_HEIGHT_ENTRY: border_size_height_entry,
        Entries.POSTFIX_ENTRY: postfix_entry
    }

    process_button = tk.Button(root, text="Process Images", command=lambda: process_images(all_entries))
    process_button.grid(row=4, column=0, columnspan=2, pady=10)

    save_button = tk.Button(root, text="Save", command=lambda: save_configuration(all_entries, source="button"))
    save_button.grid(row=5, column=0, pady=0)

    # Create and place the dropdown for loading configurations
    tk.Label(root, text="Load Configuration:").grid(row=5, column=1, padx=10, pady=0)
    load_combo = ttk.Combobox(root, width=30, values=get_all_config_files())
    load_combo.grid(row=6, column=1, padx=10, pady=10)
    load_combo.bind("<<ComboboxSelected>>", load_selected_configuration)

    # Bind <Return> key to trigger process_images()
    root.bind('<Return>', lambda event: process_images(all_entries))

    # Run the application
    root.mainloop()
