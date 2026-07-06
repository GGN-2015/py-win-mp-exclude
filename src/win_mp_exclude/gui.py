from __future__ import annotations

import argparse
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Sequence

from . import __version__
from .api import (
    ELEVATION_FLAG,
    AdministratorRequiredError,
    PowerShellError,
    UnsupportedPlatformError,
    add_exclusion,
    is_admin,
    is_windows,
    list_exclusions,
    remove_exclusion,
    request_gui_elevation,
)


class DefenderExclusionsApp(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=12)
        self.master = master
        self.path_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self._build_widgets()
        self.refresh()

    def _build_widgets(self) -> None:
        self.master.title(f"py-win-mp-exclude {__version__}")
        self.master.minsize(720, 460)
        self.grid(row=0, column=0, sticky="nsew")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)

        entry = ttk.Entry(top, textvariable=self.path_var)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ttk.Button(top, text="File...", command=self.choose_file).grid(row=0, column=1, padx=(0, 4))
        ttk.Button(top, text="Folder...", command=self.choose_folder).grid(row=0, column=2)

        buttons = ttk.Frame(self)
        buttons.grid(row=1, column=0, sticky="ew", pady=(10, 10))

        ttk.Button(buttons, text="Add", command=self.add).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text="Remove", command=self.remove).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(buttons, text="Remove Selected", command=self.remove_selected).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(buttons, text="Refresh", command=self.refresh).grid(row=0, column=3)

        list_frame = ttk.Frame(self)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.exclusions = tk.Listbox(list_frame, activestyle="dotbox")
        self.exclusions.grid(row=0, column=0, sticky="nsew")
        self.exclusions.bind("<<ListboxSelect>>", self.use_selected)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.exclusions.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.exclusions.configure(yscrollcommand=scrollbar.set)

        status = ttk.Label(self, textvariable=self.status_var, anchor="w")
        status.grid(row=3, column=0, sticky="ew", pady=(10, 0))

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(title="Choose a file to exclude")
        if path:
            self.path_var.set(path)

    def choose_folder(self) -> None:
        path = filedialog.askdirectory(title="Choose a folder to exclude")
        if path:
            self.path_var.set(path)

    def selected_path(self) -> Optional[str]:
        selection = self.exclusions.curselection()
        if not selection:
            return None
        return self.exclusions.get(selection[0])

    def use_selected(self, _event: object = None) -> None:
        selected = self.selected_path()
        if selected:
            self.path_var.set(selected)

    def require_path(self) -> Optional[str]:
        path = self.path_var.get().strip()
        if path:
            return path
        messagebox.showwarning("Missing path", "Choose or enter a file or folder path first.")
        return None

    def run_operation(self, action: str, path: str) -> None:
        try:
            result = add_exclusion(path, elevate=False) if action == "add" else remove_exclusion(path, elevate=False)
        except (AdministratorRequiredError, PowerShellError, UnsupportedPlatformError) as exc:
            self.show_error(exc)
            return

        self.refresh()
        self.status_var.set(result.message)

    def add(self) -> None:
        path = self.require_path()
        if path:
            self.run_operation("add", path)

    def remove(self) -> None:
        path = self.require_path()
        if path:
            self.run_operation("remove", path)

    def remove_selected(self) -> None:
        selected = self.selected_path()
        if selected:
            self.path_var.set(selected)
            self.run_operation("remove", selected)
        else:
            messagebox.showwarning("No selection", "Select an exclusion to remove.")

    def refresh(self) -> None:
        try:
            result = list_exclusions()
        except (PowerShellError, UnsupportedPlatformError) as exc:
            self.show_error(exc)
            return

        self.exclusions.delete(0, tk.END)
        for path in result.exclusions:
            self.exclusions.insert(tk.END, path)

        count = len(result.exclusions)
        self.status_var.set(f"{count} Defender path exclusion{'s' if count != 1 else ''} configured.")

    def show_error(self, exc: Exception) -> None:
        self.status_var.set(str(exc))
        messagebox.showerror("py-win-mp-exclude", str(exc))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="win-mp-exclude-gui",
        description="Open the py-win-mp-exclude graphical interface.",
    )
    parser.add_argument(
        ELEVATION_FLAG,
        dest="elevation_attempted",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(list(argv))

    if not is_windows():
        print("This tool only supports Windows.", file=sys.stderr)
        return 1

    if not is_admin():
        if args.elevation_attempted:
            print(
                "The GUI is not running as administrator after one elevation attempt.",
                file=sys.stderr,
            )
            return 1
        try:
            request_gui_elevation(argv)
        except AdministratorRequiredError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("Administrator elevation was requested. Continue in the elevated window.")
        return 0

    root = tk.Tk()
    DefenderExclusionsApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
