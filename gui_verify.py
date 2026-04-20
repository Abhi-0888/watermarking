import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from verification.verify import verify_document


class VerifyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure Document Verifier")
        self.root.geometry("860x640")

        self.file_var = tk.StringVar()
        self.manifest_var = tk.StringVar()
        self.registry_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="offline")

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Secure Digital Document Verification", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Upload a protected document and manifest, then run offline or online verification.",
        ).pack(anchor="w", pady=(4, 16))

        self._file_row(frame, "Protected File", self.file_var, [("Images", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")])
        self._file_row(frame, "Manifest File", self.manifest_var, [("JSON files", "*.json"), ("All files", "*.*")])
        self._file_row(frame, "Registry File", self.registry_var, [("JSON files", "*.json"), ("All files", "*.*")], optional=True)

        mode_row = ttk.Frame(frame)
        mode_row.pack(fill="x", pady=(8, 12))
        ttk.Label(mode_row, text="Mode", width=18).pack(side="left")
        ttk.Radiobutton(mode_row, text="Offline", variable=self.mode_var, value="offline").pack(side="left", padx=(0, 12))
        ttk.Radiobutton(mode_row, text="Online", variable=self.mode_var, value="online").pack(side="left")

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(8, 12))
        ttk.Button(button_row, text="Verify Document", command=self.verify).pack(side="left")
        ttk.Button(button_row, text="Clear", command=self.clear).pack(side="left", padx=(8, 0))

        ttk.Label(frame, text="Verification Output", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 6))
        self.output = tk.Text(frame, wrap="word", font=("Consolas", 10))
        self.output.pack(fill="both", expand=True)

    def _file_row(self, parent, label, variable, filetypes, optional=False):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, width=18).pack(side="left")
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)
        ttk.Button(
            row,
            text="Browse",
            command=lambda: self._browse(variable, filetypes),
        ).pack(side="left", padx=(8, 0))
        if optional:
            ttk.Label(parent, text="Registry is needed only for online verification.", foreground="#666666").pack(anchor="w", padx=(145, 0))

    def _browse(self, variable, filetypes):
        selected = filedialog.askopenfilename(filetypes=filetypes)
        if selected:
            variable.set(selected)

    def clear(self):
        self.file_var.set("")
        self.manifest_var.set("")
        self.registry_var.set("")
        self.mode_var.set("offline")
        self.output.delete("1.0", tk.END)

    def verify(self):
        file_path = self.file_var.get().strip()
        manifest_path = self.manifest_var.get().strip()
        registry_path = self.registry_var.get().strip() or None
        mode = self.mode_var.get()

        if not file_path or not manifest_path:
            messagebox.showerror("Missing Input", "Please select both a protected file and a manifest file.")
            return
        if mode == "online" and not registry_path:
            messagebox.showerror("Missing Registry", "Online mode requires a registry JSON file.")
            return

        try:
            report = verify_document(file_path, manifest_path, mode=mode, registry_path=registry_path)
        except Exception as exc:
            messagebox.showerror("Verification Failed", str(exc))
            return

        self.output.delete("1.0", tk.END)
        self.output.insert(
            tk.END,
            "\n".join(
                [
                    f"Mode: {report['mode']}",
                    f"Document ID: {report['document_id']}",
                    f"Authentic: {report['authentic']}",
                    f"Hash Valid: {report['hash_valid']}",
                    f"Signature Valid: {report['signature_valid']}",
                    f"Watermark Valid: {report['watermark_valid']}",
                    f"Registry Valid: {report['registry_valid']}",
                    f"Receiver: {report['receiver_identity']}",
                    f"Watermark Confidence: {report['watermark_confidence']}",
                    f"Watermark Text: {report['watermark_text'] or 'Not recovered'}",
                    f"Issues: {', '.join(report['issues']) if report['issues'] else 'None'}",
                ]
            ),
        )


def main():
    root = tk.Tk()
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    app = VerifyApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
