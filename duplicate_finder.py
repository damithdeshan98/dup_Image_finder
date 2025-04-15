import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import imagehash
import os
import threading
from send2trash import send2trash

# Main Application Class
class DuplicateImageFinderAppFinal:
    def __init__(self, root):
        self.root = root
        self.root.title("Duplicate Image Finder v1.0")
        self.root.geometry("1100x650")

        # --- GUI Frames ---
        top_frame = ttk.Frame(root, padding="10")
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        top_frame.columnconfigure(1, weight=1)

        tree_frame = ttk.Frame(root, padding="10")
        tree_frame.grid(row=1, column=0, sticky="nsew")

        preview_frame = ttk.Frame(root, padding="10")
        preview_frame.grid(row=1, column=1, sticky="nsew")

        bottom_frame = ttk.Frame(root, padding="10")
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

        # --- Widgets ---
        ttk.Label(top_frame, text="Image Folder:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky='w')
        self.folder_path_var = tk.StringVar()
        self.folder_entry = ttk.Entry(top_frame, textvariable=self.folder_path_var, width=70)
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.browse_button = ttk.Button(top_frame, text="Browse...", command=self.browse_folder)
        self.browse_button.grid(row=0, column=2, padx=(5, 0), pady=5)
        self.scan_button = ttk.Button(top_frame, text="Find Duplicates", command=self.start_scan_thread)
        self.scan_button.grid(row=1, column=0, columnspan=3, pady=10)

        ttk.Label(tree_frame, text="Detected Duplicates (Select to preview/delete):").pack(anchor='w', pady=(0, 5))
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        self.tree = ttk.Treeview(tree_frame, columns=("fullpath",), displaycolumns=(), height=18,
                                 yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_y.pack(side="right", fill="y")
        tree_scroll_x.config(command=self.tree.xview)
        tree_scroll_x.pack(side="bottom", fill="x")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        self.preview_type_label = ttk.Label(preview_frame, text="Image Preview", font=('Segoe UI', 10, 'italic'), anchor="center")
        self.preview_type_label.pack(pady=(0, 5), fill="x")

        self.image_preview_label = ttk.Label(preview_frame, text="Select an image from the list", relief="groove", anchor="center", background="lightgrey")
        self.image_preview_label.pack(fill="both", expand=True, pady=5)
        self.image_preview_label.image = None

        self.delete_button = ttk.Button(bottom_frame, text="Delete Selected Duplicates", command=self.delete_selected_duplicates_from_tree, state=tk.DISABLED)
        self.delete_button.pack(pady=5)

        self.status_var = tk.StringVar()
        self.status_var.set("Ready.")
        self.status_label = ttk.Label(bottom_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill="x", pady=(5, 0))

        self.image_hashes = {}
        self.tree_item_to_path = {}

        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=2)
        preview_frame.rowconfigure(1, weight=1)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path_var.set(folder_selected)
            self.status_var.set(f"Selected folder: {folder_selected}")
        else:
            self.status_var.set("No folder selected.")

    def start_scan_thread(self):
        folder_path = self.folder_path_var.get()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showerror("Error", "Please select a valid image folder.")
            return

        self.clear_results()
        self.scan_button.config(state=tk.DISABLED)
        self.browse_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)
        self.status_var.set("Scanning images...")
        self.root.update_idletasks()

        scan_thread = threading.Thread(target=self.find_duplicates, args=(folder_path,), daemon=True)
        scan_thread.start()
        self.check_scan_thread(scan_thread)

    def clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_to_path = {}
        self.image_preview_label.config(image='', text='Select an image from the list')
        self.image_preview_label.image = None
        self.preview_type_label.config(text='Image Preview')
        self.image_hashes = {}

    def check_scan_thread(self, thread):
        if thread.is_alive():
            self.root.after(100, lambda: self.check_scan_thread(thread))
        else:
            self.root.after(0, self.populate_treeview)

    def find_duplicates(self, folder_path):
        self.image_hashes = {}
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')
        files_to_process = [
            os.path.normpath(os.path.join(folder_path, f)) for f in os.listdir(folder_path)
            if f.lower().endswith(image_extensions) and os.path.isfile(os.path.join(folder_path, f))
        ]

        for i, filepath in enumerate(files_to_process, start=1):
            try:
                img = Image.open(filepath)
                img_hash = imagehash.phash(img, hash_size=8)
                self.image_hashes.setdefault(img_hash, []).append(filepath)
                status_text = f"Processing: {i}/{len(files_to_process)} - {os.path.basename(filepath)}"
                self.root.after(0, self.update_status, status_text)
            except Exception as e:
                print(f"Warning: Could not process file {filepath}: {e}")
                self.root.after(0, self.update_status, f"Skipped (Error): {os.path.basename(filepath)}")

    def populate_treeview(self):
        self.status_var.set("Populating results...")
        self.tree.delete(*self.tree.get_children())
        self.tree_item_to_path = {}
        duplicate_count = 0
        set_count = 0

        for img_hash, paths in self.image_hashes.items():
            if len(paths) > 1:
                paths.sort(key=lambda x: os.path.getsize(x), reverse=True)
                original_path = paths[0]
                duplicate_paths = paths[1:]
                set_count += 1

                original_filename = os.path.basename(original_path)
                parent_item = self.tree.insert("", tk.END, text=f"⭐ Original: {original_filename}", open=True, values=(original_path,))
                self.tree_item_to_path[parent_item] = original_path

                for dup_path in duplicate_paths:
                    duplicate_count += 1
                    dup_filename = os.path.basename(dup_path)
                    child_item = self.tree.insert(parent_item, tk.END, text=f"   └─ Duplicate: {dup_filename}", values=(dup_path,))
                    self.tree_item_to_path[child_item] = dup_path

        if duplicate_count > 0:
            self.status_var.set(f"Scan Complete! Found {duplicate_count} duplicates in {set_count} sets.")
            self.delete_button.config(state=tk.NORMAL)
        else:
            self.status_var.set("Scan Complete! No duplicates found.")
            self.delete_button.config(state=tk.DISABLED)

        self.scan_button.config(state=tk.NORMAL)
        self.browse_button.config(state=tk.NORMAL)

    def update_status(self, message):
        self.status_var.set(message)

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            self.image_preview_label.config(image='', text='Select an image from the list')
            self.image_preview_label.image = None
            self.preview_type_label.config(text='Image Preview')
            return

        selected_item = selected_items[0]
        filepath = self.tree_item_to_path.get(selected_item)

        if not filepath or not os.path.exists(filepath):
            self.image_preview_label.config(image='', text=f'Error: File not found\n{filepath}')
            self.image_preview_label.image = None
            self.preview_type_label.config(text='Error')
            return

        if self.tree.parent(selected_item) == "":
            self.preview_type_label.config(text="Showing: Original Image")
        else:
            self.preview_type_label.config(text="Showing: Selected Duplicate Image")

        self.show_image_preview(filepath, self.image_preview_label)

    def show_image_preview(self, filepath, label_widget):
        try:
            label_widget.update_idletasks()
            label_width = label_widget.winfo_width() or 350
            label_height = label_widget.winfo_height() or 300

            img = Image.open(filepath)
            img.thumbnail((label_width - 10, label_height - 10), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            label_widget.config(image=photo, text="")
            label_widget.image = photo
        except Exception as e:
            filename = os.path.basename(filepath)
            label_widget.config(image='', text=f"Preview Error:\n{filename}\n({e})")
            label_widget.image = None
            print(f"Error creating preview for {filepath}: {e}")

    def delete_selected_duplicates_from_tree(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select duplicate files to delete.")
            return

        files_to_delete = []
        items_to_remove_from_tree = []
        for item_id in selected_items:
            if self.tree.parent(item_id) != "":
                filepath = self.tree_item_to_path.get(item_id)
                if filepath:
                    files_to_delete.append(os.path.normpath(filepath))
                    items_to_remove_from_tree.append(item_id)

        if not files_to_delete:
            messagebox.showinfo("Info", "Selected items are not duplicates. Original files will not be deleted.")
            return

        confirm = messagebox.askyesno("Confirm Deletion",
                                      f"Are you sure you want to delete {len(files_to_delete)} duplicate files?\n"
                                      f"(Original files will not be affected)\nThis action cannot be undone.")
        if confirm:
            deleted_count = 0
            error_count = 0
            self.status_var.set("Deleting selected duplicates...")
            self.root.update_idletasks()

            for filepath, item_id in zip(files_to_delete, items_to_remove_from_tree):
                try:
                    if os.path.exists(filepath):
                        send2trash(filepath)
                        deleted_count += 1
                        if item_id in self.tree_item_to_path:
                            self.tree.delete(item_id)
                            del self.tree_item_to_path[item_id]
                    else:
                        if item_id in self.tree_item_to_path:
                            self.tree.delete(item_id)
                            del self.tree_item_to_path[item_id]
                except Exception as e:
                    print(f"Error deleting {filepath}: {e}")
                    error_count += 1
                self.root.update_idletasks()

            self.status_var.set(f"Deletion Complete. Deleted: {deleted_count}, Errors: {error_count}")
            messagebox.showinfo("Deletion Complete", f"{deleted_count} files deleted.\n{error_count} errors occurred.")

            self.image_preview_label.config(image='', text='Select an image from the list')
            self.image_preview_label.image = None
            self.preview_type_label.config(text='Image Preview')

            if not any(self.tree.parent(item) != "" for item in self.tree.get_children("")):
                self.delete_button.config(state=tk.DISABLED)
        else:
            self.status_var.set("Deletion cancelled.")

# --- Main Program ---
if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    try:
        style.theme_use('vista')
    except tk.TclError:
        print("Vista theme not available, using default.")
    app = DuplicateImageFinderAppFinal(root)
    root.mainloop()
