#!/usr/bin/env python3
"""
Tangram Solution Data Annotator

This tool helps annotate tangram solutions by asking whether each piece
needs to be slid (0) or lifted (1) into place.

Usage:
    python tangram_annotator.py

Controls:
    0 - Slide (record 0)
    1 - Lift (record 1)
    n - Next image (skip current)
    p - Previous image
    q - Quit and save
"""

import os
import csv
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import glob

# Configuration
IMAGE_DIR = "tangram-imgs"
CSV_FILE = "tangram_annotations.csv"
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800

# The 7 tangram shapes in order
SHAPES = [
    "Red triangle (small)",
    "Purple triangle (small)",
    "Pink triangle (medium)",
    "Orange triangle (large)",
    "Blue triangle (large)",
    "Yellow parallelogram",
    "Green square"
]

class TangramAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("Tangram Solution Annotator")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # Data
        self.image_files = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.*")))
        self.image_files = [f for f in self.image_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
        self.current_index = 0
        self.current_shape_index = 0
        self.current_annotations = []
        self.all_annotations = {}

        # Load existing annotations
        self.load_annotations()

        # Skip to first unannotated image
        self.skip_to_unannotated()

        # UI Setup
        self.setup_ui()

        # Bind keyboard events
        self.root.bind('0', lambda e: self.record_answer(0))
        self.root.bind('1', lambda e: self.record_answer(1))
        self.root.bind('n', lambda e: self.next_image())
        self.root.bind('p', lambda e: self.prev_image())
        self.root.bind('q', lambda e: self.quit_app())

        # Load first image
        if self.image_files:
            self.load_image()
        else:
            messagebox.showerror("Error", f"No images found in {IMAGE_DIR}")
            self.root.quit()

    def setup_ui(self):
        """Setup the user interface"""
        # Top frame for image
        self.image_frame = tk.Frame(self.root, bg='gray')
        self.image_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.image_label = tk.Label(self.image_frame, bg='gray')
        self.image_label.pack(expand=True)

        # Bottom frame for questions and controls
        self.control_frame = tk.Frame(self.root, bg='white')
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        # Progress label
        self.progress_label = tk.Label(
            self.control_frame,
            text="",
            font=("Arial", 12),
            bg='white'
        )
        self.progress_label.pack(pady=5)

        # Question label
        self.question_label = tk.Label(
            self.control_frame,
            text="",
            font=("Arial", 16, "bold"),
            bg='white',
            fg='blue',
            wraplength=900
        )
        self.question_label.pack(pady=10)

        # Current answers display
        self.answers_label = tk.Label(
            self.control_frame,
            text="",
            font=("Arial", 12),
            bg='white'
        )
        self.answers_label.pack(pady=5)

        # Instructions
        instructions = (
            "Press 0 for SLIDE | Press 1 for LIFT\n"
            "n = Next | p = Previous | q = Quit & Save"
        )
        self.instructions_label = tk.Label(
            self.control_frame,
            text=instructions,
            font=("Arial", 10),
            bg='white',
            fg='gray'
        )
        self.instructions_label.pack(pady=5)

    def load_annotations(self):
        """Load existing annotations from CSV file"""
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'r') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 8:  # filename + 7 annotations
                        filename = row[0]
                        annotations = [int(x) for x in row[1:8]]
                        self.all_annotations[filename] = annotations
            print(f"Loaded {len(self.all_annotations)} existing annotations")

    def skip_to_unannotated(self):
        """Skip to the first unannotated image"""
        for i, img_file in enumerate(self.image_files):
            filename = os.path.basename(img_file)
            if filename not in self.all_annotations:
                self.current_index = i
                return
        # All images annotated
        if self.image_files:
            self.current_index = len(self.image_files) - 1

    def load_image(self):
        """Load and display the current image"""
        if not self.image_files:
            return

        img_path = self.image_files[self.current_index]
        filename = os.path.basename(img_path)

        # Load existing annotations for this image
        if filename in self.all_annotations:
            self.current_annotations = self.all_annotations[filename].copy()
            self.current_shape_index = len(SHAPES)  # Mark as complete
        else:
            self.current_annotations = []
            self.current_shape_index = 0

        # Load and resize image
        img = Image.open(img_path)

        # Calculate scaling to fit window while maintaining aspect ratio
        img_width, img_height = img.size
        max_width = WINDOW_WIDTH - 100
        max_height = WINDOW_HEIGHT - 300

        scale = min(max_width / img_width, max_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        self.image_label.config(image=photo)
        self.image_label.image = photo  # Keep a reference

        self.update_display()

    def update_display(self):
        """Update the question and progress displays"""
        if not self.image_files:
            return

        filename = os.path.basename(self.image_files[self.current_index])

        # Update progress
        annotated_count = len(self.all_annotations)
        total = len(self.image_files)
        progress_text = f"Image {self.current_index + 1}/{total} | Annotated: {annotated_count}/{total} | File: {filename}"
        self.progress_label.config(text=progress_text)

        # Update question
        if self.current_shape_index < len(SHAPES):
            shape = SHAPES[self.current_shape_index]
            question = f"Can the robot SLIDE the {shape} into place or does it need to LIFT it?\nPress 0 for SLIDE | Press 1 for LIFT"
            self.question_label.config(text=question, fg='blue')
        else:
            if filename in self.all_annotations:
                self.question_label.config(
                    text="✓ This image is already annotated. Press 'n' for next or 'p' for previous.",
                    fg='green'
                )
            else:
                self.question_label.config(
                    text="✓ All shapes annotated for this image! Press 'n' to continue to next image.",
                    fg='green'
                )

        # Update current answers
        answers_text = "Current annotations: "
        for i, shape in enumerate(SHAPES):
            if i < len(self.current_annotations):
                answer = "SLIDE" if self.current_annotations[i] == 0 else "LIFT"
                answers_text += f"\n{i+1}. {shape}: {answer}"
            elif i == self.current_shape_index:
                answers_text += f"\n{i+1}. {shape}: ?"
            else:
                answers_text += f"\n{i+1}. {shape}: -"

        self.answers_label.config(text=answers_text)

    def record_answer(self, answer):
        """Record an answer (0 or 1) for the current shape"""
        if self.current_shape_index >= len(SHAPES):
            messagebox.showinfo("Info", "All shapes annotated for this image. Press 'n' for next image.")
            return

        # Record the answer
        self.current_annotations.append(answer)
        self.current_shape_index += 1

        # If all shapes are annotated, save to CSV
        if self.current_shape_index >= len(SHAPES):
            self.save_current_annotation()

        self.update_display()

    def save_current_annotation(self):
        """Save the current annotation to the CSV file"""
        if len(self.current_annotations) != len(SHAPES):
            return

        filename = os.path.basename(self.image_files[self.current_index])
        self.all_annotations[filename] = self.current_annotations.copy()

        # Write all annotations to CSV
        self.save_all_annotations()

        print(f"Saved annotation for {filename}")

    def save_all_annotations(self):
        """Save all annotations to CSV file"""
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)

            # Write header
            header = ['filename'] + [f'shape_{i+1}' for i in range(len(SHAPES))]
            writer.writerow(header)

            # Write annotations
            for filename, annotations in sorted(self.all_annotations.items()):
                row = [filename] + annotations
                writer.writerow(row)

        print(f"Saved {len(self.all_annotations)} annotations to {CSV_FILE}")

    def next_image(self):
        """Move to the next image"""
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_image()
        else:
            messagebox.showinfo("Info", "This is the last image!")

    def prev_image(self):
        """Move to the previous image"""
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image()
        else:
            messagebox.showinfo("Info", "This is the first image!")

    def quit_app(self):
        """Save and quit the application"""
        self.save_all_annotations()

        annotated = len(self.all_annotations)
        total = len(self.image_files)
        messagebox.showinfo(
            "Goodbye",
            f"Annotations saved!\n{annotated}/{total} images annotated.\nSaved to {CSV_FILE}"
        )
        self.root.quit()

def main():
    # Check if image directory exists
    if not os.path.exists(IMAGE_DIR):
        print(f"Error: Image directory '{IMAGE_DIR}' not found!")
        print(f"Please make sure the directory exists and contains tangram solution images.")
        return

    root = tk.Tk()
    app = TangramAnnotator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
