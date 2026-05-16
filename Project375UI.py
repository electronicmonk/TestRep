import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import datetime
import os

# Try to import tkinterdnd2 for drag and drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAS_DND = True
except ImportError:
    HAS_DND = False

# Import functions from your existing files
from photoexperiment import (
    check_llm_status,
    generic_image_request,
    generic_image_request2,
    get_photo_details,
    make_square,
    reveal_in_file_manager,
    calculate_days_passed,
    add_row_to_excel
)

# --- Configuration for easy modification (Requirement 2 & 3) ---
LLM_SERVERS = {
    "Ollama": {
        "default_ip": "localhost",
        "port": 11434,
        "model": "gemma4"
    },
    "LM Studio": {
        "default_ip": "localhost",
        "port": 1234,
        "model": "gemma4"
    },
    "llama.cpp": {
        "default_ip": "localhost",
        "port": 8080,
        "model": "gemma4"
    }
}


class PhotoUploadGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Project 365 - Photo Uploader")
        self.root.geometry("700x850")

        # Variables
        self.selected_image = tk.StringVar()
        self.selected_xlsx = tk.StringVar()
        self.selected_server = tk.StringVar(value=list(LLM_SERVERS.keys())[0])
        self.server_ip = tk.StringVar(value=LLM_SERVERS[list(LLM_SERVERS.keys())[0]]["default_ip"])
        self.sheet_name = tk.StringVar(value="Photos")
        # the default row is set to the number of days passed since 2026-04-11 plus 2,
        # which is the starting point for the project
        self.row_val = tk.StringVar(value=str(calculate_days_passed(2026, 4, 11) + 2))
        self.col_val = tk.StringVar(value="3")

        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- LLM Server Section ---
        server_frame = ttk.LabelFrame(main_frame, text="LLM Server Settings", padding="10")
        server_frame.pack(fill=tk.X, pady=10)

        ttk.Label(server_frame, text="Server:").grid(row=0, column=0, sticky=tk.W)
        self.server_menu = ttk.Combobox(server_frame, textvariable=self.selected_server,
                                        values=list(LLM_SERVERS.keys()), state="readonly")
        self.server_menu.grid(row=0, column=1, padx=5, pady=5)
        self.server_menu.bind("<<ComboboxSelected>>", self._on_server_change)

        ttk.Label(server_frame, text="IP Address:").grid(row=0, column=2, sticky=tk.W, padx=10)
        self.ip_entry = ttk.Entry(server_frame, textvariable=self.server_ip)
        self.ip_entry.grid(row=0, column=3, padx=5, pady=5)

        self.status_label = ttk.Label(server_frame, text="Checking status...", foreground="gray")
        self.status_label.grid(row=0, column=4, padx=10)

        # --- File Selection Section ---
        files_frame = ttk.LabelFrame(main_frame, text="Files (Drag & Drop or Browse)", padding="10")
        files_frame.pack(fill=tk.X, pady=10)

        # Image File
        ttk.Label(files_frame, text="Image:").grid(row=0, column=0, sticky=tk.W)
        self.img_entry = ttk.Entry(files_frame, textvariable=self.selected_image, width=50)
        self.img_entry.grid(row=0, column=1, padx=5, pady=5)
        self._make_droppable(self.img_entry)
        ttk.Button(files_frame, text="Browse", command=self._browse_image).grid(row=0, column=2, padx=5)

        # Excel File
        ttk.Label(files_frame, text="Excel:").grid(row=1, column=0, sticky=tk.W)
        self.xlsx_entry = ttk.Entry(files_frame, textvariable=self.selected_xlsx, width=50)
        self.xlsx_entry.grid(row=1, column=1, padx=5, pady=5)
        self._make_droppable(self.xlsx_entry)
        ttk.Button(files_frame, text="Browse", command=self._browse_xlsx).grid(row=1, column=2, padx=5)

        # --- Excel Details Section ---
        detail_frame = ttk.LabelFrame(main_frame, text="Excel Positioning", padding="10")
        detail_frame.pack(fill=tk.X, pady=10)

        ttk.Label(detail_frame, text="Sheet Name:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(detail_frame, textvariable=self.sheet_name).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(detail_frame, text="Row (Optional):").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(detail_frame, textvariable=self.row_val).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(detail_frame, text="Col (Optional):").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(detail_frame, textvariable=self.col_val).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # --- Control Button ---
        self.start_btn = ttk.Button(main_frame, text="START UPLOAD PROCESS", command=self._start_thread)
        self.start_btn.pack(pady=20)

        # --- Output Log ---
        ttk.Label(main_frame, text="Process Log:").pack(anchor=tk.W)
        self.log_area = tk.Text(main_frame, height=20, width=80, state="disabled", font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Initial status check
        self._update_connection_status()

    def _make_droppable(self, widget):
        if HAS_DND:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind('<<Drop>>', lambda e: self._handle_drop(e, widget))

    def _handle_drop(self, event, widget):
        # Remove curly braces that Windows sometimes adds to paths with spaces
        path = event.data.strip('{}')
        if widget == self.img_entry:
            self.selected_image.set(path)
        else:
            self.selected_xlsx.set(path)

    def _browse_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if path: self.selected_image.set(path)

    def _browse_xlsx(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if path: self.selected_xlsx.set(path)

    def _on_server_change(self, event):
        server_name = self.selected_server.get()
        self.server_ip.set(LLM_SERVERS[server_name]["default_ip"])
        self._update_connection_status()

    def _update_connection_status(self):
        server_name = self.selected_server.get()
        ip = self.server_ip.get()

        # Run check in a small thread to avoid GUI freeze
        def check():
            res = check_llm_status(server_name, ip)
            color = "green" if res["online"] else "red"
            text = "● Online" if res["online"] else "● Offline"
            self.root.after(0, lambda: self.status_label.config(text=text, foreground=color))

        threading.Thread(target=check, daemon=True).start()

    def log(self, message):
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")

    def _start_thread(self):
        # Validate basic inputs
        if not self.selected_image.get() or not self.selected_xlsx.get():
            messagebox.showerror("Error", "Please select both image and excel files.")
            return

        self.start_btn.config(state="disabled")
        threading.Thread(target=self._run_process, daemon=True).start()

    def _run_process(self):
        start_time = time.perf_counter()
        try:
            img_path = self.selected_image.get()
            xlsx_path = self.selected_xlsx.get()
            sheet = self.sheet_name.get()

            # Parse optional row/col
            try:
                row = int(self.row_val.get()) if self.row_val.get() else None
                col = int(self.col_val.get()) if self.col_val.get() else None
            except ValueError:
                self.log("Error: Row/Col must be integers.")
                self.root.after(0, lambda: self.start_btn.config(state="normal"))
                return

            # 1. Connectivity Check
            server_name = self.selected_server.get()
            ip = self.server_ip.get()
            status = check_llm_status(server_name, ip)

            if not status["online"]:
                self.log(f"FAIL: LLM Server {server_name} at {ip} is offline.")
                self.root.after(0, lambda: messagebox.showerror("Connection Error", "LLM Server is offline."))
                self.root.after(0, lambda: self.start_btn.config(state="normal"))
                return

            # 2. Image Processing (The "what full_upload_process_output does" part)
            self.log("Starting upload process...")

            # EXIF Data
            self.log("Extracting EXIF details...")
            exif_data = get_photo_details(img_path)

            # Image Formatting
            self.log("Creating square version of image...")
            padded_name = make_square(img_path)
            reveal_in_file_manager(img_path)

            # LLM Requests
            model = LLM_SERVERS[server_name]["model"]

            prompts = {
                "Genre": "You are an expert photography critic and genre classifier. Analyze the provided image and determine the primary genre of photography. Your output must be concise and contain only the name of the genre. No preamble.",
                "Description": "You a professional photography critique. Describe what you see in this image, in one paragraph. It should be no more than one short sentence. Don't use superlatives",
                "Keywords": "You are an expert computer vision assistant. Analyze this image and list every distinct, primary object you can see. Respond ONLY with a comma-separated list of object names.",
                "Location": "Analyse the image and determine the location. The output should be strictly formated as country, location, site. If any of the items cannot be determined, replace it with 'undetermined'."
            }

            results = {}
            server_name = self.selected_server.get()
            ip = self.server_ip.get()
            port = LLM_SERVERS[server_name]["port"]
            if server_name == "Ollama":
                target_url = f"http://{ip}:{port}/api/generate"
            else:
                target_url = f"http://{ip}:{port}/v1/chat/completions"

            for key, prompt in prompts.items():
                self.log(f"Requesting {key} from LLM...")
                # We override the URL in photoexperiment.py's generic_image_request by
                # dynamically updating the globals if needed, but since generic_image_request
                # uses a hardcoded URL, we rely on the server being at that expected IP
                # OR you would need to modify that function.
                # Since you said "do not change current code", I will assume the
                # user updates their local environment/hosts or the utility function
                # is updated to accept a URL.
                # FOR NOW, I call the function as is.
                res = generic_image_request2(img_path, model, prompt, url=target_url)
                results[key] = res
                if res:
                    self.log(f"  -> {key}: {res}")

            # 3. Prepare Data for Excel
            self.log("Preparing data for Excel...")

            # Convert keywords to list
            keywords_list = []
            if results["Keywords"]:
                keywords_list = [k.strip() for k in results["Keywords"].split(',') if k.strip()]

            values_list = [
                exif_data.get("Camera", ""),
                exif_data.get("Lens", ""),
                float(exif_data.get("FL", 0)),
                float(exif_data.get("EFL", 0)),
                results["Genre"] if results["Genre"] else " ",
                datetime.datetime.strptime(exif_data.get("Date Taken", "2000-01-01"), "%Y-%m-%d"),
                datetime.datetime.strptime(exif_data.get("Date Posted", "2000-01-01"), "%Y-%m-%d"),
                exif_data.get("Day Of Week", ""),
                datetime.datetime.strptime(exif_data.get("Time Posted", "00:00:00"), "%H:%M:%S"),
                results["Location"] if results["Location"] else "undetermined",
                img_path
            ]

            values_list.append(results["Description"] if results["Description"] else " ")
            if keywords_list:
                values_list.extend(keywords_list)
            else:
                values_list.append(" ")

            # 4. Write to Excel
            self.log("Updating XLSX file...")
            excel_res = add_row_to_excel(
                file_name=xlsx_path,
                sheet_name=sheet,
                values=values_list,
                row_number=row,
                col_number=col
            )

            if excel_res["status"] == "success":
                self.log(f"SUCCESS: {excel_res['message']}")
                # Display readable info to user (Requirement 6)
                summary = (f"\n--- Added Information ---\n"
                           f"Genre: {results['Genre']}\n"
                           f"Desc: {results['Description']}\n"
                           f"Loc: {results['Location']}\n"
                           f"Keywords: {', '.join(keywords_list)}")
                self.log(summary)
                self.root.after(0, lambda: messagebox.showinfo("Success", "Excel updated successfully!"))
            else:
                self.log(f"FAIL: {excel_res['message']}")
                self.root.after(0, lambda: messagebox.showerror("Excel Error", excel_res['message']))

        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred: {e}"))

        finally:
            end_time = time.perf_counter()
            self.log(f"Total process time: {end_time - start_time:.2f} seconds")
            self.root.after(0, lambda: self.start_btn.config(state="normal"))


if __name__ == "__main__":
    # Use TkinterDnD if available, otherwise standard Tk
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
        print("tkinterdnd2 not found. Drag-and-drop disabled. Use Browse buttons.")

    app = PhotoUploadGUI(root)
    root.mainloop()
