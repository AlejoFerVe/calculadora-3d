"""
Calculadora 3D - 3D Printing Calculator
Main GUI application for calculating print costs, time, and material usage
"""

import tkinter as tk
from tkinter import ttk, messagebox
from calculator_logic import PrintCalculator
from inventory import InventoryTab
from datetime import datetime
import json
import os


class CalculadoraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("3D Printing Calculator")
        self.root.geometry("1150x800")
        self.root.resizable(True, True)
        self.root.minsize(950, 600)

        self.colors = {
            'bg_general': '#F8FAFC',
            'panel_left': '#FFFFFF',
            'panel_right': "#1B2E58",
            'button_blue': '#3B82F6',
            'button_blue_hover': '#2563EB',
            'text_primary': '#0F172A',
            'text_secondary': '#64748B',
            'text_white': '#F5F5F5',
            'border': '#E2E8F0',
            'shadow': '#E2E8F0'
        }

        self.calculator = PrintCalculator()
        self.history_file = "historial_cotizaciones.json"

        self.material_densities = {
            "PLA": 1.24,
            "ABS": 1.04,
            "PETG": 1.27,
            "TPU": 1.21,
            "Nylon": 1.14
        }

        self.current_quote_pieces = []
        self.piece_extra_rows = []
        self.piece_counter = 0
        self.editing_piece_index = None

        self.history_data = []
        self.selected_history_index = None

        self.root.configure(bg=self.colors['bg_general'])

        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TNotebook', background=self.colors['bg_general'], borderwidth=0)
        style.configure('TNotebook.Tab',
                       background=self.colors['panel_left'],
                       foreground=self.colors['text_primary'],
                       padding=[20, 10],
                       font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['button_blue'])],
                 foreground=[('selected', self.colors['text_white'])])

        style.configure('Left.TFrame', background=self.colors['panel_left'], relief='flat')
        style.configure('Right.TFrame', background=self.colors['panel_right'], relief='flat')
        style.configure('TFrame', background=self.colors['bg_general'])

        style.configure('Modern.TEntry', fieldbackground='white',
                       foreground=self.colors['text_primary'],
                       borderwidth=1, relief='solid')

        style.configure('Blue.TButton',
                       background=self.colors['button_blue'],
                       foreground='white', borderwidth=0,
                       font=('Segoe UI', 10, 'bold'), padding=[20, 10])
        style.map('Blue.TButton',
                 background=[('active', self.colors['button_blue_hover'])])

        style.configure('White.TButton',
                       background='white', foreground=self.colors['text_primary'],
                       borderwidth=1, font=('Segoe UI', 10), padding=[20, 10])
        style.map('White.TButton',
                 background=[('active', self.colors['bg_general'])],
                 bordercolor=[('active', self.colors['button_blue'])])

        style.configure('Treeview', font=('Segoe UI', 9), rowheight=24)
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))

    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=20)

        self.create_quote_tab()
        self.create_material_tab()
        self.create_history_tab()
        self.inventory = InventoryTab(self, self.notebook)

    # ---------------------------------------------------------------
    # Generic helpers
    # ---------------------------------------------------------------
    def _make_scrollable(self, parent):
        outer = tk.Frame(parent, bg=self.colors['bg_general'])
        outer.pack(fill='both', expand=True)

        canvas = tk.Canvas(outer, bg=self.colors['bg_general'], highlightthickness=0)
        vscroll = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side='left', fill='both', expand=True)
        vscroll.pack(side='right', fill='y')

        inner = tk.Frame(canvas, bg=self.colors['bg_general'])
        inner_id = canvas.create_window((0, 0), window=inner, anchor='nw')

        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(inner_id, width=e.width))

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', _on_wheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

        return inner, canvas

    def _bind_mousewheel_recursive(self, widget, canvas):
        """Make the mouse wheel scroll the outer page from anywhere inside `widget`,
        except widgets that manage their own scrolling (like the pieces Treeview)."""
        if isinstance(widget, ttk.Treeview):
            return

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
            return "break"

        try:
            widget.bind('<MouseWheel>', _on_wheel)
        except tk.TclError:
            pass

        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child, canvas)

    def _create_input(self, parent, row, label_text, default_value="", state='normal'):
        tk.Label(parent, text=label_text, font=('Segoe UI', 9),
                bg=self.colors['panel_left'], fg=self.colors['text_secondary']).grid(
                    row=row, column=0, sticky='w', pady=8)

        entry = tk.Entry(parent, font=('Segoe UI', 10),
                       bg='white', fg=self.colors['text_primary'],
                       relief='solid', bd=1, highlightthickness=1,
                       highlightbackground=self.colors['border'],
                       highlightcolor=self.colors['button_blue'])
        entry.grid(row=row, column=1, sticky='ew', pady=8)
        if default_value:
            entry.insert(0, default_value)
        if state == 'disabled':
            entry.config(state='disabled')
        return entry

    def _create_lockable_input(self, parent, row, label_text, default_value=""):
        tk.Label(parent, text=label_text, font=('Segoe UI', 9),
                bg=self.colors['panel_left'], fg=self.colors['text_secondary']).grid(
                    row=row, column=0, sticky='w', pady=8)

        entry = tk.Entry(parent, font=('Segoe UI', 10),
                       bg='white', fg=self.colors['text_primary'],
                       relief='solid', bd=1, highlightthickness=1,
                       highlightbackground=self.colors['border'],
                       highlightcolor=self.colors['button_blue'])
        entry.grid(row=row, column=1, sticky='ew', pady=8)
        if default_value:
            entry.insert(0, default_value)
        entry.config(state='disabled')

        lock_var = tk.BooleanVar(value=False)

        def toggle():
            entry.config(state='normal' if lock_var.get() else 'disabled')

        tk.Checkbutton(parent, text="Editar", variable=lock_var, command=toggle,
                      bg=self.colors['panel_left'], fg=self.colors['text_secondary'],
                      activebackground=self.colors['panel_left'],
                      font=('Segoe UI', 8)).grid(row=row, column=2, sticky='w', padx=(8, 0), pady=8)

        return entry, lock_var

    def format_price_col(self, amount):
        return f"{int(round(amount)):,}".replace(',', '.')

    def parse_time_input(self, time_str):
        try:
            if ':' in time_str:
                parts = time_str.split(':')
                hours = int(parts[0])
                minutes = int(parts[1])
                return hours * 60 + minutes
            else:
                return float(time_str)
        except:
            raise ValueError("Formato de tiempo inválido. Use H:MM (ej: 1:30)")

    def load_history_data(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save_history_data(self, history):
        """Returns True on success, False on failure (and shows why)."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            return True
        except PermissionError:
            messagebox.showerror(
                "No se pudo guardar",
                "No se pudo escribir en 'historial_cotizaciones.json'.\n\n"
                "Esto suele pasar si el archivo está abierto en otro programa "
                "(Excel, Bloc de notas, etc.), está marcado como solo lectura, "
                "o la carpeta no tiene permisos de escritura.\n\n"
                "Cierra el archivo si lo tienes abierto e inténtalo de nuevo. "
                "Tus datos no se han perdido."
            )
            return False
        except OSError as e:
            messagebox.showerror("No se pudo guardar", f"Error al guardar el historial:\n{e}")
            return False

    def _write_section(self, widget, title):
        widget.insert(tk.END, f"{title}\n")
        widget.insert(tk.END, "─" * 36 + "\n")

    def _write_row(self, widget, label, value, indent=2):
        label_str = (" " * indent) + str(label)
        widget.insert(tk.END, f"{label_str:<28}{value:>10}\n")

    def _write_divider(self, widget):
        widget.insert(tk.END, "─" * 36 + "\n")

    def _write_total(self, widget, label, value):
        widget.insert(tk.END, "═" * 36 + "\n")
        widget.insert(tk.END, f"  {label:<24}{value:>10}\n")
        widget.insert(tk.END, "═" * 36 + "\n")

    def _reset_extras_and_package_form(self):
        for entry in (self.extra_envio, self.extra_cajas, self.extra_papeleria,
                    self.extra_bolsas, self.extra_otro):
            entry.delete(0, tk.END)
        self.clear_package_form()

    # ---------------------------------------------------------------
    # TAB 1: COTIZACIÓN
    # ---------------------------------------------------------------
    def create_quote_tab(self):
        tab = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(tab, text="Cotización")

        content, self.quote_canvas = self._make_scrollable(tab)
        main_container = ttk.Frame(content, style='TFrame')
        main_container.pack(fill='both', expand=True, padx=20, pady=20)

        # ===== LEFT PANEL =====
        left_panel = tk.Frame(main_container, bg=self.colors['panel_left'],
                             relief='flat', bd=0, highlightthickness=1,
                             highlightbackground=self.colors['border'])
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))

        tk.Label(left_panel, text="Agregar Pieza",
                font=('Segoe UI', 16, 'bold'),
                bg=self.colors['panel_left'],
                fg=self.colors['text_primary']).pack(anchor='w', padx=25, pady=(20, 10))

        form = tk.Frame(left_panel, bg=self.colors['panel_left'])
        form.pack(fill='x', padx=25)
        form.columnconfigure(1, weight=1)

        row = 0
        self.piece_name = self._create_input(form, row, "Nombre de la pieza"); row += 1
        self.price_per_gram = self._create_input(form, row, "Precio por gramo ($)", "80"); row += 1
        self.filament_weight = self._create_input(form, row, "Peso del filamento (g)"); row += 1
        self.print_time = self._create_input(form, row, "Tiempo de impresión (H:MM)"); row += 1
        self.electricity_cost, self.electricity_lock = self._create_lockable_input(
            form, row, "Precio kWh ($)", "700"); row += 1
        self.printer_power, self.printer_power_lock = self._create_lockable_input(
            form, row, "Consumo impresora (W)", "400"); row += 1
        self.cost_per_min = self._create_input(form, row, "Costo minuto máquina ($)", "20"); row += 1
        self.failure_percent = self._create_input(form, row, "Porcentaje de fallo (%)", "10"); row += 1
        self.profit_margin, self.profit_margin_lock = self._create_lockable_input(
            form, row, "Margen de ganancia (%)", "50"); row += 1
        self.piece_quantity = self._create_input(form, row, "Cantidad", "1"); row += 1

        self.piece_has_extras = tk.BooleanVar(value=False)
        extras_check = tk.Checkbutton(
            form, text="Costos extra para esta pieza (dije, resina, etc.)",
            variable=self.piece_has_extras, command=self.toggle_keychain_extras,
            bg=self.colors['panel_left'], fg=self.colors['text_primary'],
            font=('Segoe UI', 9, 'bold'), activebackground=self.colors['panel_left'],
            selectcolor='white', wraplength=380, justify='left')
        extras_check.grid(row=row, column=0, columnspan=2, sticky='w', pady=(10, 5))
        row += 1

        self.keychain_extras_frame = tk.Frame(form, bg=self.colors['panel_left'])
        self.keychain_extras_frame.grid(row=row, column=0, columnspan=2, sticky='ew')
        self.keychain_extras_frame.grid_remove()
        row += 1

        quick_buttons_frame = tk.Frame(self.keychain_extras_frame, bg=self.colors['panel_left'])
        quick_buttons_frame.pack(fill='x', pady=(0, 5))
        for label in ["Dije", "Resina", "Cordón", "Otro"]:
            tk.Button(quick_buttons_frame, text=f"+ {label}", font=('Segoe UI', 7),
                    bg='white', fg=self.colors['text_secondary'], relief='solid', bd=1,
                    padx=4, pady=2, cursor='hand2',
                    command=lambda l=label: self.add_keychain_extra_row(l, "0")
                    ).pack(side='left', padx=(0, 3), pady=2)

        self.keychain_rows_container = tk.Frame(self.keychain_extras_frame, bg=self.colors['panel_left'])
        self.keychain_rows_container.pack(fill='x')

        tk.Button(self.keychain_extras_frame, text="+ Agregar extra", font=('Segoe UI', 8),
                bg='white', fg=self.colors['text_primary'], relief='solid', bd=1,
                padx=8, pady=4, cursor='hand2',
                command=lambda: self.add_keychain_extra_row()).pack(anchor='w', pady=(2, 8))

        btn_frame = tk.Frame(left_panel, bg=self.colors['panel_left'])
        btn_frame.pack(fill='x', padx=25, pady=(15, 15))

        self.add_piece_btn = tk.Button(btn_frame, text="Agregar Pieza a la Cotización",
                                      font=('Segoe UI', 10, 'bold'),
                                      bg=self.colors['button_blue'], fg='white',
                                      bd=0, padx=20, pady=12, cursor='hand2',
                                      command=self.add_piece_to_quote)
        self.add_piece_btn.pack(fill='x')

        self.cancel_edit_btn = tk.Button(btn_frame, text="Cancelar Edición", font=('Segoe UI', 9),
                                        bg='white', fg=self.colors['text_primary'], relief='solid', bd=1,
                                        padx=10, pady=8, cursor='hand2',
                                        command=self.cancel_piece_edit)

        tk.Label(left_panel, text="Piezas en esta cotización", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['panel_left'], fg=self.colors['text_primary']).pack(anchor='w', padx=25)

        tk.Label(left_panel,
                text="Aquí se acumulan las piezas que agregas. Selecciona una fila para "
                     "editarla o quitarla. Cuando termines, guarda toda la cotización con "
                     "el botón azul de la derecha.",
                font=('Segoe UI', 8), bg=self.colors['panel_left'], fg=self.colors['text_secondary'],
                wraplength=400, justify='left').pack(anchor='w', padx=25, pady=(2, 8))

        tree_frame = tk.Frame(left_panel, bg=self.colors['panel_left'])
        tree_frame.pack(fill='both', expand=True, padx=25, pady=(0, 10))

        columns = ('pieza', 'cant', 'p_unit', 'subtotal')
        self.pieces_tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                       height=8, selectmode='browse')
        self.pieces_tree.heading('pieza', text='Pieza')
        self.pieces_tree.heading('cant', text='Cant.')
        self.pieces_tree.heading('p_unit', text='P. Unit')
        self.pieces_tree.heading('subtotal', text='Subtotal')
        self.pieces_tree.column('pieza', width=140)
        self.pieces_tree.column('cant', width=50, anchor='center')
        self.pieces_tree.column('p_unit', width=90, anchor='e')
        self.pieces_tree.column('subtotal', width=100, anchor='e')
        self.pieces_tree.pack(fill='both', expand=True, side='left')

        tree_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.pieces_tree.yview)
        self.pieces_tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side='right', fill='y')

        tk.Button(left_panel, text="Editar Pieza Seleccionada", font=('Segoe UI', 9),
                bg='white', fg=self.colors['text_primary'], relief='solid', bd=1,
                padx=10, pady=8, cursor='hand2',
                command=self.edit_selected_piece).pack(fill='x', padx=25, pady=(0, 8))

        piece_btn_frame = tk.Frame(left_panel, bg=self.colors['panel_left'])
        piece_btn_frame.pack(fill='x', padx=25, pady=(0, 20))

        tk.Button(piece_btn_frame, text="Quitar Seleccionada", font=('Segoe UI', 9),
                bg='white', fg=self.colors['text_primary'], relief='solid', bd=1,
                padx=10, pady=8, cursor='hand2',
                command=self.remove_selected_piece).pack(side='left', fill='x', expand=True, padx=(0, 5))

        tk.Button(piece_btn_frame, text="Vaciar Todo", font=('Segoe UI', 9),
                bg='white', fg=self.colors['text_primary'], relief='solid', bd=1,
                padx=10, pady=8, cursor='hand2',
                command=self.clear_quote).pack(side='left', fill='x', expand=True, padx=(5, 0))

        # ===== RIGHT PANEL =====
        right_panel = tk.Frame(main_container, bg=self.colors['bg_general'])
        right_panel.pack(side='right', fill='both', expand=False, padx=(10, 0))
        right_panel.configure(width=420)

        extras_section = tk.Frame(right_panel, bg=self.colors['panel_left'],
                                 highlightthickness=1, highlightbackground=self.colors['border'])
        extras_section.pack(fill='x', pady=(0, 10))

        tk.Label(extras_section, text="Costos Adicionales (por cotización)", font=('Segoe UI', 13, 'bold'),
                bg=self.colors['panel_left'], fg=self.colors['text_primary']).pack(
                    anchor='w', padx=20, pady=(15, 10))

        tk.Label(extras_section,
                text="Se reinician cada vez que agregas o editas una pieza — "
                     "ingrésalos justo antes de guardar la cotización.",
                font=('Segoe UI', 8), bg=self.colors['panel_left'], fg=self.colors['text_secondary'],
                wraplength=380, justify='left').pack(anchor='w', padx=20, pady=(0, 8))

        extras_form = tk.Frame(extras_section, bg=self.colors['panel_left'])
        extras_form.pack(fill='x', padx=20, pady=(0, 15))
        extras_form.columnconfigure(1, weight=1)

        erow = 0
        self.extra_envio = self._create_input(extras_form, erow, "Envío ($)"); erow += 1
        self.extra_cajas = self._create_input(extras_form, erow, "Cajas ($)"); erow += 1
        self.extra_papeleria = self._create_input(extras_form, erow, "Papelería ($)"); erow += 1
        self.extra_bolsas = self._create_input(extras_form, erow, "Bolsas ($)"); erow += 1
        self.extra_otro = self._create_input(extras_form, erow, "Otro ($)"); erow += 1
        self.client_name = self._create_input(extras_form, erow, "Cliente"); erow += 1

        tk.Button(extras_section, text="Actualizar Total", font=('Segoe UI', 9, 'bold'),
                bg='white', fg=self.colors['text_primary'], relief='solid', bd=1,
                padx=10, pady=8, cursor='hand2',
                command=self.update_quote_total).pack(fill='x', padx=20, pady=(0, 15))

        # ---- Paquete de la pieza actual ----
        package_section = tk.Frame(right_panel, bg=self.colors['panel_left'],
                                  highlightthickness=1, highlightbackground=self.colors['border'])
        package_section.pack(fill='x', pady=(0, 10))

        tk.Label(package_section, text="Paquete de esta pieza", font=('Segoe UI', 13, 'bold'),
                bg=self.colors['panel_left'], fg=self.colors['text_primary']).pack(
                    anchor='w', padx=20, pady=(15, 5))

        tk.Label(package_section,
                text="Si esta pieza (o este lote) va en su propio empaque, pon aquí su "
                     "envío, cajas, papelería, bolsas, post-procesado u otro. Se suma una "
                     "sola vez (no por unidad) y queda asociado a la pieza que agregues a "
                     "continuación. El cuadro se limpia después de agregarla.",
                font=('Segoe UI', 8), bg=self.colors['panel_left'], fg=self.colors['text_secondary'],
                wraplength=380, justify='left').pack(anchor='w', padx=20, pady=(0, 10))

        pkg_form = tk.Frame(package_section, bg=self.colors['panel_left'])
        pkg_form.pack(fill='x', padx=20, pady=(0, 15))
        pkg_form.columnconfigure(1, weight=1)

        prow = 0
        self.package_envio = self._create_input(pkg_form, prow, "Envío ($)"); prow += 1
        self.package_cajas = self._create_input(pkg_form, prow, "Cajas ($)"); prow += 1
        self.package_papeleria = self._create_input(pkg_form, prow, "Papelería ($)"); prow += 1
        self.package_bolsas = self._create_input(pkg_form, prow, "Bolsas ($)"); prow += 1
        self.package_posproceso = self._create_input(pkg_form, prow, "Post-procesado ($)"); prow += 1
        self.package_otro = self._create_input(pkg_form, prow, "Otro ($)"); prow += 1

        blue_section = tk.Frame(right_panel, bg=self.colors['panel_right'])
        blue_section.pack(fill='both', expand=True)

        result_title_frame = tk.Frame(blue_section, bg=self.colors['panel_right'])
        result_title_frame.pack(fill='x', padx=25, pady=(20, 5))
        tk.Label(result_title_frame, text="RESULTADOS", font=('Segoe UI', 13, 'bold'),
                bg=self.colors['panel_right'], fg=self.colors['text_white']).pack(anchor='w')

        view_mode_frame = tk.Frame(blue_section, bg=self.colors['panel_right'])
        view_mode_frame.pack(fill='x', padx=25, pady=(5, 5))

        self.results_view_mode = tk.StringVar(value='resumen')
        tk.Radiobutton(view_mode_frame, text="Resumen", variable=self.results_view_mode, value='resumen',
                     command=self.update_quote_total, bg=self.colors['panel_right'],
                     fg=self.colors['text_white'], selectcolor=self.colors['panel_right'],
                     activebackground=self.colors['panel_right'], activeforeground=self.colors['text_white'],
                     font=('Segoe UI', 9)).pack(side='left', padx=(0, 15))
        tk.Radiobutton(view_mode_frame, text="Detalle de costos", variable=self.results_view_mode, value='detalle',
                     command=self.update_quote_total, bg=self.colors['panel_right'],
                     fg=self.colors['text_white'], selectcolor=self.colors['panel_right'],
                     activebackground=self.colors['panel_right'], activeforeground=self.colors['text_white'],
                     font=('Segoe UI', 9)).pack(side='left')

        tk.Frame(blue_section, height=2, bg='#3A4A64').pack(fill='x', padx=25, pady=(5, 0))

        results_container = tk.Frame(blue_section, bg=self.colors['panel_right'])
        results_container.pack(fill='both', expand=True, padx=25, pady=(15, 15))

        self.quote_results = tk.Text(results_container, font=('Consolas', 10),
                                    bg=self.colors['panel_right'], fg=self.colors['text_white'],
                                    relief='flat', bd=0, padx=10, pady=10, wrap='word',
                                    state='disabled', height=18)
        self.quote_results.pack(fill='both', expand=True)

        save_btn_frame = tk.Frame(right_panel, bg=self.colors['bg_general'])
        save_btn_frame.pack(fill='x', pady=(10, 20))

        tk.Button(save_btn_frame, text="Guardar Cotización en Historial",
                font=('Segoe UI', 10, 'bold'), bg=self.colors['button_blue'], fg='white',
                bd=0, padx=20, pady=12, cursor='hand2',
                command=self.save_quote_to_history).pack(fill='x')

        self.update_quote_total()

        # Make the mouse wheel scroll the whole tab from anywhere inside it
        self._bind_mousewheel_recursive(main_container, self.quote_canvas)

    def toggle_keychain_extras(self):
        if self.piece_has_extras.get():
            self.keychain_extras_frame.grid()
        else:
            self.keychain_extras_frame.grid_remove()
            for _, _, row_frame in list(self.piece_extra_rows):
                row_frame.destroy()
            self.piece_extra_rows = []

    def add_keychain_extra_row(self, name="", cost="0"):
        row_frame = tk.Frame(self.keychain_rows_container, bg=self.colors['panel_left'])
        row_frame.pack(fill='x', pady=2)

        name_entry = tk.Entry(row_frame, font=('Segoe UI', 9), width=14, relief='solid', bd=1)
        name_entry.insert(0, name)
        name_entry.pack(side='left', padx=(0, 5))

        cost_entry = tk.Entry(row_frame, font=('Segoe UI', 9), width=8, relief='solid', bd=1)
        cost_entry.insert(0, cost)
        cost_entry.pack(side='left', padx=(0, 5))

        tk.Button(row_frame, text="X", font=('Segoe UI', 8, 'bold'), bg='white', fg='#DC2626',
                relief='flat', bd=0, cursor='hand2',
                command=lambda: self.remove_keychain_extra_row(row_frame)).pack(side='left')

        self.piece_extra_rows.append((name_entry, cost_entry, row_frame))
        self._bind_mousewheel_recursive(row_frame, self.quote_canvas)

    def remove_keychain_extra_row(self, row_frame):
        self.piece_extra_rows = [r for r in self.piece_extra_rows if r[2] != row_frame]
        row_frame.destroy()

    # ---- Paquete de la pieza actual ----
    def get_current_package(self):
        def safe_float(entry):
            try:
                return float(entry.get())
            except (ValueError, AttributeError):
                return 0.0
        costs = {
            'Envío': safe_float(self.package_envio),
            'Cajas': safe_float(self.package_cajas),
            'Papelería': safe_float(self.package_papeleria),
            'Bolsas': safe_float(self.package_bolsas),
            'Post-procesado': safe_float(self.package_posproceso),
            'Otro': safe_float(self.package_otro),
        }
        return {k: v for k, v in costs.items() if v}

    def clear_package_form(self):
        for entry in (self.package_envio, self.package_cajas, self.package_papeleria,
                    self.package_bolsas, self.package_posproceso, self.package_otro):
            entry.delete(0, tk.END)

    # ---- Formulario de pieza ----
    def _reset_piece_form(self):
        self.piece_name.delete(0, tk.END)
        self.filament_weight.delete(0, tk.END)
        self.print_time.delete(0, tk.END)
        self.piece_quantity.delete(0, tk.END)
        self.piece_quantity.insert(0, "1")
        self.piece_has_extras.set(False)
        self.toggle_keychain_extras()

        self.electricity_lock.set(False)
        self.electricity_cost.config(state='normal')
        self.electricity_cost.delete(0, tk.END)
        self.electricity_cost.insert(0, "700")
        self.electricity_cost.config(state='disabled')

        self.printer_power_lock.set(False)
        self.printer_power.config(state='normal')
        self.printer_power.delete(0, tk.END)
        self.printer_power.insert(0, "400")
        self.printer_power.config(state='disabled')

        self.profit_margin_lock.set(False)
        self.profit_margin.config(state='normal')
        self.profit_margin.delete(0, tk.END)
        self.profit_margin.insert(0, "50")
        self.profit_margin.config(state='disabled')

    def _load_piece_into_form(self, piece):
        inputs = piece.get('inputs', {})

        self.piece_name.delete(0, tk.END)
        self.piece_name.insert(0, piece['name'])

        self.price_per_gram.delete(0, tk.END)
        self.price_per_gram.insert(0, str(inputs.get('price_per_gram', '')))

        self.filament_weight.delete(0, tk.END)
        self.filament_weight.insert(0, str(piece['weight_g']))

        hours = int(piece['time_min'] // 60)
        minutes = int(piece['time_min'] % 60)
        self.print_time.delete(0, tk.END)
        self.print_time.insert(0, f"{hours}:{minutes:02d}")

        elec_editable = inputs.get('elec_editable', False)
        self.electricity_lock.set(elec_editable)
        self.electricity_cost.config(state='normal')
        self.electricity_cost.delete(0, tk.END)
        self.electricity_cost.insert(0, str(inputs.get('elec_cost', '')))
        self.electricity_cost.config(state='normal' if elec_editable else 'disabled')

        power_editable = inputs.get('power_editable', False)
        self.printer_power_lock.set(power_editable)
        self.printer_power.config(state='normal')
        self.printer_power.delete(0, tk.END)
        self.printer_power.insert(0, str(inputs.get('power_w', '')))
        self.printer_power.config(state='normal' if power_editable else 'disabled')

        self.cost_per_min.delete(0, tk.END)
        self.cost_per_min.insert(0, str(inputs.get('cost_min', '')))

        self.failure_percent.delete(0, tk.END)
        self.failure_percent.insert(0, str(inputs.get('failure_pct', '')))

        margin_editable = inputs.get('margin_editable', False)
        self.profit_margin_lock.set(margin_editable)
        self.profit_margin.config(state='normal')
        self.profit_margin.delete(0, tk.END)
        self.profit_margin.insert(0, str(inputs.get('margin', '')))
        self.profit_margin.config(state='normal' if margin_editable else 'disabled')

        self.piece_quantity.delete(0, tk.END)
        self.piece_quantity.insert(0, str(piece['quantity']))

        self.piece_has_extras.set(piece.get('has_extras', False))
        for _, _, row_frame in list(self.piece_extra_rows):
            row_frame.destroy()
        self.piece_extra_rows = []
        if self.piece_has_extras.get():
            self.keychain_extras_frame.grid()
            for ex in piece.get('piece_extras', []):
                self.add_keychain_extra_row(ex['name'], str(ex['cost']))
        else:
            self.keychain_extras_frame.grid_remove()

        pkg_fields = {
            'Envío': self.package_envio, 'Cajas': self.package_cajas,
            'Papelería': self.package_papeleria, 'Bolsas': self.package_bolsas,
            'Post-procesado': self.package_posproceso, 'Otro': self.package_otro,
        }
        self.clear_package_form()
        for label, entry in pkg_fields.items():
            val = piece.get('package_costs', {}).get(label)
            if val:
                entry.insert(0, str(val))

    def edit_selected_piece(self):
        selected = self.pieces_tree.selection()
        if not selected:
            messagebox.showwarning("Selección", "Por favor selecciona una pieza para editar")
            return
        item = selected[0]
        index = self.pieces_tree.index(item)
        piece = self.current_quote_pieces[index]

        self._load_piece_into_form(piece)

        self.editing_piece_index = index
        self.add_piece_btn.config(text="Guardar Cambios en la Pieza")
        self.cancel_edit_btn.pack(fill='x', pady=(8, 0))

    def cancel_piece_edit(self):
        self.editing_piece_index = None
        self.add_piece_btn.config(text="Agregar Pieza a la Cotización")
        self.cancel_edit_btn.pack_forget()
        self._reset_piece_form()
        self.clear_package_form()

    def add_piece_to_quote(self):
        try:
            price_gram = float(self.price_per_gram.get())
            time_str = self.print_time.get().strip()
            time_min = self.parse_time_input(time_str)
            weight_g = float(self.filament_weight.get())
            elec_cost = float(self.electricity_cost.get())
            power_w = float(self.printer_power.get())
            cost_min = float(self.cost_per_min.get())
            failure_pct = float(self.failure_percent.get())
            margin = float(self.profit_margin.get())
            quantity = int(float(self.piece_quantity.get()))
            if quantity < 1:
                raise ValueError("La cantidad debe ser al menos 1")

            results = self.calculator.calculate_piece_cost(
                price_gram, time_min, weight_g, elec_cost, power_w,
                cost_min, failure_pct, margin
            )

            piece_extras = []
            extras_total_unit = 0.0
            if self.piece_has_extras.get():
                for name_entry, cost_entry, _ in self.piece_extra_rows:
                    name = name_entry.get().strip()
                    if not name:
                        continue
                    cost_str = cost_entry.get().strip()
                    try:
                        cost_val = float(cost_str) if cost_str else 0.0
                    except ValueError:
                        cost_val = 0.0
                    piece_extras.append({'name': name, 'cost': cost_val})
                    extras_total_unit += cost_val

            package_costs = self.get_current_package()
            package_total = sum(package_costs.values())

            unit_final_price = results['net_price'] + extras_total_unit
            subtotal = (unit_final_price * quantity) + package_total

            if self.editing_piece_index is not None:
                piece_name = self.piece_name.get().strip() or \
                    self.current_quote_pieces[self.editing_piece_index]['name']
            else:
                self.piece_counter += 1
                piece_name = self.piece_name.get().strip() or f"Pieza {self.piece_counter}"

            piece = {
                'name': piece_name,
                'weight_g': weight_g,
                'time_min': time_min,
                'quantity': quantity,
                'has_extras': self.piece_has_extras.get(),
                'piece_extras': piece_extras,
                'package_costs': package_costs,
                'unit_base_price': results['net_price'],
                'unit_extras_total': extras_total_unit,
                'unit_final_price': unit_final_price,
                'subtotal': subtotal,
                'breakdown': results,
                'inputs': {
                    'price_per_gram': price_gram,
                    'elec_cost': elec_cost,
                    'elec_editable': self.electricity_lock.get(),
                    'power_w': power_w,
                    'power_editable': self.printer_power_lock.get(),
                    'cost_min': cost_min,
                    'failure_pct': failure_pct,
                    'margin': margin,
                    'margin_editable': self.profit_margin_lock.get(),
                }
            }

            if self.editing_piece_index is not None:
                index = self.editing_piece_index
                self.current_quote_pieces[index] = piece
                item_id = self.pieces_tree.get_children()[index]
                self.pieces_tree.item(item_id, values=(
                    piece_name, quantity,
                    f"${self.format_price_col(unit_final_price)}",
                    f"${self.format_price_col(subtotal)}"
                ))
                self.editing_piece_index = None
                self.add_piece_btn.config(text="Agregar Pieza a la Cotización")
                self.cancel_edit_btn.pack_forget()
            else:
                self.current_quote_pieces.append(piece)
                self.pieces_tree.insert('', 'end', values=(
                    piece_name, quantity,
                    f"${self.format_price_col(unit_final_price)}",
                    f"${self.format_price_col(subtotal)}"
                ))

            self._reset_piece_form()
            self._reset_extras_and_package_form()
            self.update_quote_total()

        except ValueError as e:
            messagebox.showerror("Error", f"Error en los datos ingresados:\n{str(e)}")

    def remove_selected_piece(self):
        selected = self.pieces_tree.selection()
        if not selected:
            messagebox.showwarning("Selección", "Por favor selecciona una pieza para quitar")
            return
        item = selected[0]
        index = self.pieces_tree.index(item)
        self.pieces_tree.delete(item)
        del self.current_quote_pieces[index]

        if self.editing_piece_index is not None:
            if self.editing_piece_index == index:
                self.cancel_piece_edit()
            elif self.editing_piece_index > index:
                self.editing_piece_index -= 1

        self.update_quote_total()

    def clear_quote(self):
        self.current_quote_pieces = []
        for item in self.pieces_tree.get_children():
            self.pieces_tree.delete(item)
        if self.editing_piece_index is not None:
            self.cancel_piece_edit()
        self.update_quote_total()

    def get_global_extras(self):
        def safe_float(entry):
            try:
                return float(entry.get())
            except (ValueError, AttributeError):
                return 0.0
        return {
            'Envío': safe_float(self.extra_envio),
            'Cajas': safe_float(self.extra_cajas),
            'Papelería': safe_float(self.extra_papeleria),
            'Bolsas': safe_float(self.extra_bolsas),
            'Otro': safe_float(self.extra_otro),
        }

    def update_quote_total(self):
        global_extras = self.get_global_extras()
        totals = self.calculator.calculate_quote_total(self.current_quote_pieces, global_extras)

        w = self.quote_results
        w.config(state='normal')
        w.delete(1.0, tk.END)

        if not self.current_quote_pieces:
            w.insert(tk.END, "Aún no has agregado piezas.\n\n")
            w.insert(tk.END, "Completa el formulario y usa\n'Agregar Pieza a la Cotización'.")
        elif self.results_view_mode.get() == 'detalle':
            self._render_cost_detail(totals)
        else:
            self._render_summary(totals, global_extras)

        w.config(state='disabled')

    def _render_summary(self, totals, global_extras):
        w = self.quote_results
        self._write_section(w, "PIEZAS")
        for p in self.current_quote_pieces:
            label = f"{p['name'][:16]} x{p['quantity']}"
            self._write_row(w, label, f"${self.format_price_col(p['subtotal'])}")
            for name, val in p.get('package_costs', {}).items():
                self._write_row(w, f"+ {name} (empaque):", f"${self.format_price_col(val)}", indent=4)
        self._write_divider(w)
        self._write_row(w, "Subtotal piezas:", f"${self.format_price_col(totals['pieces_subtotal'])}", indent=0)
        w.insert(tk.END, "\n")

        extras_nonzero = {k: v for k, v in global_extras.items() if v}
        if extras_nonzero:
            self._write_section(w, "EXTRAS")
            for name, val in extras_nonzero.items():
                self._write_row(w, name, f"${self.format_price_col(val)}")
            self._write_divider(w)
            self._write_row(w, "Subtotal extras:", f"${self.format_price_col(totals['extras_subtotal'])}", indent=0)
            w.insert(tk.END, "\n")

        self._write_total(w, "TOTAL:", f"${self.format_price_col(totals['total'])}")

    def _render_cost_detail(self, totals):
        w = self.quote_results
        for p in self.current_quote_pieces:
            b = p['breakdown']
            hours = int(p['time_min'] // 60)
            minutes = int(p['time_min'] % 60)
            self._write_section(w, f"{p['name']} (x{p['quantity']})")
            self._write_row(w, "Material:", f"${self.format_price_col(b['material_cost'])}")
            self._write_row(w, "Electricidad:", f"${self.format_price_col(b['electricity_cost'])}")
            self._write_row(w, "Máquina:", f"${self.format_price_col(b['machine_cost'])}")
            self._write_row(w, "Fallo:", f"${self.format_price_col(b['failure_cost'])}")
            self._write_row(w, "Ganancia:", f"${self.format_price_col(b['profit'])}")
            for ex in p['piece_extras']:
                self._write_row(w, f"+ {ex['name']}:", f"${self.format_price_col(ex['cost'])}")
            for name, val in p.get('package_costs', {}).items():
                self._write_row(w, f"+ {name} (empaque):", f"${self.format_price_col(val)}")
            self._write_divider(w)
            self._write_row(w, "Tiempo:", f"{hours}:{minutes:02d} ({int(p['time_min'])} min)")
            self._write_row(w, "Peso:", f"{p['weight_g']:.0f}g")
            self._write_row(w, "Precio unitario:", f"${self.format_price_col(p['unit_final_price'])}", indent=0)
            w.insert(tk.END, "\n")

        total_time_min = sum(p['time_min'] * p['quantity'] for p in self.current_quote_pieces)
        total_weight = sum(p['weight_g'] * p['quantity'] for p in self.current_quote_pieces)
        th, tm = int(total_time_min // 60), int(total_time_min % 60)

        self._write_divider(w)
        self._write_row(w, "Tiempo total:", f"{th}:{tm:02d} ({int(total_time_min)} min)", indent=0)
        self._write_row(w, "Peso total:", f"{total_weight:.0f}g", indent=0)
        w.insert(tk.END, "\n")
        self._write_total(w, "TOTAL:", f"${self.format_price_col(totals['total'])}")

    def save_quote_to_history(self):
        if not self.current_quote_pieces:
            messagebox.showwarning("Cotización vacía", "Agrega al menos una pieza antes de guardar")
            return

        client_name = self.client_name.get().strip()
        if not client_name:
            messagebox.showwarning("Nombre requerido", "Por favor ingresa el nombre del cliente antes de guardar")
            return

        global_extras = self.get_global_extras()
        totals = self.calculator.calculate_quote_total(self.current_quote_pieces, global_extras)

        quote = {
            'type': 'quote',
            'client': client_name,
            'timestamp': datetime.now().strftime("%Y-%m-%d"),
            'pieces': self.current_quote_pieces,
            'global_extras': {k: v for k, v in global_extras.items() if v},
            'pieces_subtotal': totals['pieces_subtotal'],
            'extras_subtotal': totals['extras_subtotal'],
            'total': totals['total']
        }

        history = self.load_history_data()
        history.append(quote)
        if not self.save_history_data(history):
            return

        messagebox.showinfo("Guardado", f"Cotización para '{client_name}' guardada correctamente")

        self.clear_quote()
        self.client_name.delete(0, tk.END)
        self._reset_extras_and_package_form()

        self.refresh_history_list()

    # ---------------------------------------------------------------
    # TAB 2: CONVERSIÓN DE MATERIAL
    # ---------------------------------------------------------------
    def create_material_tab(self):
        tab = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(tab, text="Material Conversion")

        main_container = ttk.Frame(tab, style='TFrame')
        main_container.pack(fill='both', expand=True, padx=30, pady=30)

        left_panel = tk.Frame(main_container, bg=self.colors['panel_left'],
                             relief='flat', bd=0, highlightthickness=1,
                             highlightbackground=self.colors['border'])
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 15))

        title_frame = tk.Frame(left_panel, bg=self.colors['panel_left'])
        title_frame.pack(fill='x', padx=30, pady=(25, 20))

        tk.Label(title_frame, text="Material Conversion",
                font=('Segoe UI', 18, 'bold'),
                bg=self.colors['panel_left'],
                fg=self.colors['text_primary']).pack(anchor='w')

        tk.Label(title_frame, text="Convert between weight, length, and volume",
                font=('Segoe UI', 9),
                bg=self.colors['panel_left'],
                fg=self.colors['text_secondary']).pack(anchor='w', pady=(5, 0))

        input_container = tk.Frame(left_panel, bg=self.colors['panel_left'])
        input_container.pack(fill='both', expand=True, padx=30, pady=(20, 20))

        def create_field_row(parent, row, label_text, widget_type='entry', values=None,
                            default_value="", state='normal'):
            tk.Label(parent, text=label_text, font=('Segoe UI', 9),
                   bg=self.colors['panel_left'], fg=self.colors['text_secondary'],
                   anchor='w').grid(row=row, column=0, sticky='w', pady=10)

            if widget_type in ('combobox', 'combobox_blue'):
                font = ('Segoe UI', 10, 'bold') if widget_type == 'combobox_blue' else ('Segoe UI', 10)
                widget = ttk.Combobox(parent, values=values, state='readonly', font=font, width=25)
                if default_value:
                    widget.set(default_value)
            else:
                widget = tk.Entry(parent, font=('Segoe UI', 10),
                               bg='white', fg=self.colors['text_primary'],
                               relief='solid', bd=1,
                               highlightthickness=1,
                               highlightbackground=self.colors['border'],
                               highlightcolor=self.colors['button_blue'],
                               state=state)
                if default_value and state == 'normal':
                    widget.insert(0, default_value)
                elif default_value and state == 'readonly':
                    widget.config(state='normal')
                    widget.insert(0, default_value)
                    widget.config(state='readonly')

            widget.grid(row=row, column=1, sticky='ew', pady=10)
            return widget

        row = 0
        self.material_type = create_field_row(input_container, row, "Type of Material",
                                             'combobox', ["PLA", "ABS", "PETG", "TPU", "Nylon"], "PLA")
        self.material_type.bind("<<ComboboxSelected>>", self.on_material_change)

        row += 1
        self.filament_diameter = create_field_row(input_container, row, "Material Diameter (mm)",
                                                 'entry', default_value="1.75")

        row += 1
        self.material_density = create_field_row(input_container, row, "Material Density (g/cm³)",
                                                'entry', default_value="1.24", state='readonly')

        row += 1
        self.conversion_type = create_field_row(input_container, row, "Convert From",
                                               'combobox_blue', ["Weight (g)", "Length (m)", "Volume (cm³)"],
                                               "Length (m)")

        row += 1
        self.conversion_value = create_field_row(input_container, row, "Value", 'entry', default_value="2")

        input_container.columnconfigure(1, weight=1)

        button_frame = tk.Frame(left_panel, bg=self.colors['panel_left'])
        button_frame.pack(fill='x', padx=30, pady=(10, 25))

        tk.Button(button_frame, text="Convert",
                font=('Segoe UI', 10, 'bold'), bg=self.colors['button_blue'], fg='white',
                bd=0, padx=35, pady=12, cursor='hand2',
                command=self.calculate_material).pack(fill='x', pady=(0, 8))

        tk.Button(button_frame, text="Save to History",
                font=('Segoe UI', 10), bg='white', fg=self.colors['text_primary'],
                relief='solid', bd=1, padx=30, pady=12, cursor='hand2',
                command=self.save_material_to_history).pack(fill='x')

        right_panel = tk.Frame(main_container, bg=self.colors['panel_right'],
                              relief='flat', bd=0, highlightthickness=1,
                              highlightbackground=self.colors['border'])
        right_panel.pack(side='right', fill='both', expand=True, padx=(15, 0))

        result_title_frame = tk.Frame(right_panel, bg=self.colors['panel_right'])
        result_title_frame.pack(fill='x', padx=30, pady=(25, 10))

        tk.Label(result_title_frame, text="CONVERSION RESULTS",
                font=('Segoe UI', 14, 'bold'),
                bg=self.colors['panel_right'],
                fg=self.colors['text_white']).pack(anchor='w')

        tk.Frame(result_title_frame, height=2, bg='#3A4A64').pack(fill='x', pady=(10, 0))

        results_container = tk.Frame(right_panel, bg=self.colors['panel_right'])
        results_container.pack(fill='both', expand=True, padx=30, pady=(20, 25))

        self.material_results = tk.Text(results_container,
                                       font=('Consolas', 10),
                                       bg=self.colors['panel_right'],
                                       fg=self.colors['text_white'],
                                       relief='flat', bd=0, padx=10, pady=10,
                                       wrap='word', state='disabled')
        self.material_results.pack(fill='both', expand=True)

        self.update_material_density()

    def on_material_change(self, event=None):
        self.update_material_density()

    def update_material_density(self):
        selected_material = self.material_type.get()
        density = self.material_densities.get(selected_material, 1.24)
        self.material_density.config(state='normal')
        self.material_density.delete(0, tk.END)
        self.material_density.insert(0, str(density))
        self.material_density.config(state='readonly')

    def calculate_material(self):
        try:
            diameter = float(self.filament_diameter.get())
            density = float(self.material_density.get())
            value = float(self.conversion_value.get())
            conv_type = self.conversion_type.get()

            type_mapping = {
                "Weight (g)": "Peso (g)",
                "Length (m)": "Longitud (m)",
                "Volume (cm³)": "Volumen (cm³)"
            }
            conv_type_spanish = type_mapping.get(conv_type, conv_type)
            results = self.calculator.convert_material(diameter, density, value, conv_type_spanish)
            material = self.material_type.get()

            w = self.material_results
            w.config(state='normal')
            w.delete(1.0, tk.END)

            self._write_section(w, "PROPIEDADES DEL MATERIAL")
            self._write_row(w, "Material:", material)
            self._write_row(w, "Diámetro:", f"{diameter:.2f} mm")
            self._write_row(w, "Densidad:", f"{density:.2f} g/cm³")
            w.insert(tk.END, "\n")

            self._write_section(w, "CONVERSIONES")
            self._write_row(w, "Peso:", f"{results['weight']:.2f} g")
            self._write_row(w, "Longitud:", f"{results['length']:.2f} m")
            self._write_row(w, "Volumen:", f"{results['volume']:.2f} cm³")

            w.config(state='disabled')

        except ValueError:
            messagebox.showerror("Error", "Por favor ingresa valores numéricos válidos")

    def save_material_to_history(self):
        try:
            diameter = float(self.filament_diameter.get())
            density = float(self.material_density.get())
            value = float(self.conversion_value.get())
            conv_type = self.conversion_type.get()

            type_mapping = {
                "Weight (g)": "Peso (g)",
                "Length (m)": "Longitud (m)",
                "Volume (cm³)": "Volumen (cm³)"
            }
            conv_type_spanish = type_mapping.get(conv_type, conv_type)
            results = self.calculator.convert_material(diameter, density, value, conv_type_spanish)
            material = self.material_type.get()

            entry = {
                'type': 'conversion',
                'timestamp': datetime.now().strftime("%Y-%m-%d"),
                'material': material,
                'diameter': diameter,
                'density': density,
                'conversion_type': conv_type,
                'value': value,
                'results': results
            }

            history = self.load_history_data()
            history.append(entry)
            if not self.save_history_data(history):
                return

            messagebox.showinfo("Guardado", "Conversión guardada en el historial correctamente")
            self.refresh_history_list()

        except ValueError:
            messagebox.showerror("Error", "Por favor calcule primero antes de guardar")

    # ---------------------------------------------------------------
    # TAB 3: HISTORIAL
    # ---------------------------------------------------------------
    def create_history_tab(self):
        tab = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(tab, text="Historial")

        main_container = ttk.Frame(tab, style='TFrame')
        main_container.pack(fill='both', expand=True, padx=20, pady=20)

        left_panel = tk.Frame(main_container, bg=self.colors['panel_left'],
                             relief='flat', bd=0, highlightthickness=1,
                             highlightbackground=self.colors['border'])
        left_panel.pack(side='left', fill='both', expand=False, padx=(0, 10))
        left_panel.configure(width=320)

        tk.Label(left_panel, text="Cotizaciones Guardadas", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['panel_left'], fg=self.colors['text_primary']).pack(
                    anchor='w', padx=20, pady=(20, 10))

        control_frame = tk.Frame(left_panel, bg=self.colors['panel_left'])
        control_frame.pack(fill='x', padx=20, pady=(0, 10))

        tk.Button(control_frame, text="Actualizar", font=('Segoe UI', 9), bg='white', relief='solid', bd=1,
                padx=8, pady=4, cursor='hand2', command=self.refresh_history_list).pack(side='left', padx=(0, 5))
        tk.Button(control_frame, text="Eliminar", font=('Segoe UI', 9), bg='white', relief='solid', bd=1,
                padx=8, pady=4, cursor='hand2', command=self.delete_selected_history).pack(side='left', padx=(0, 5))
        tk.Button(control_frame, text="Limpiar Todo", font=('Segoe UI', 9), bg='white', relief='solid', bd=1,
                padx=8, pady=4, cursor='hand2', command=self.clear_all_history).pack(side='left')

        list_frame = tk.Frame(left_panel, bg=self.colors['panel_left'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        self.history_listbox = tk.Listbox(list_frame, font=('Segoe UI', 9), relief='solid', bd=1,
                                         activestyle='none', selectbackground=self.colors['button_blue'],
                                         selectforeground='white')
        self.history_listbox.pack(side='left', fill='both', expand=True)
        self.history_listbox.bind('<<ListboxSelect>>', self.on_history_select)

        hist_scroll = ttk.Scrollbar(list_frame, orient='vertical', command=self.history_listbox.yview)
        self.history_listbox.configure(yscrollcommand=hist_scroll.set)
        hist_scroll.pack(side='right', fill='y')

        right_panel = tk.Frame(main_container, bg=self.colors['panel_right'],
                              relief='flat', bd=0, highlightthickness=1,
                              highlightbackground=self.colors['border'])
        right_panel.pack(side='right', fill='both', expand=True, padx=(10, 0))

        detail_title_frame = tk.Frame(right_panel, bg=self.colors['panel_right'])
        detail_title_frame.pack(fill='x', padx=25, pady=(20, 10))
        self.history_detail_title = tk.Label(detail_title_frame, text="Selecciona una cotización",
                                            font=('Segoe UI', 14, 'bold'), bg=self.colors['panel_right'],
                                            fg=self.colors['text_white'])
        self.history_detail_title.pack(anchor='w')
        tk.Frame(detail_title_frame, height=2, bg='#3A4A64').pack(fill='x', pady=(10, 0))

        detail_container = tk.Frame(right_panel, bg=self.colors['panel_right'])
        detail_container.pack(fill='both', expand=True, padx=25, pady=(10, 20))

        self.history_detail_text = tk.Text(detail_container, font=('Consolas', 10),
                                          bg=self.colors['panel_right'], fg=self.colors['text_white'],
                                          relief='flat', bd=0, padx=10, pady=10, wrap='word',
                                          state='disabled')
        self.history_detail_text.pack(fill='both', expand=True)

        self.refresh_history_list()

    def refresh_history_list(self):
        self.history_data = self.load_history_data()
        self.history_listbox.delete(0, tk.END)
        for entry in self.history_data:
            ts = entry.get('timestamp', '')
            if entry.get('type') == 'conversion':
                label = f"{ts}  Conversión ({entry.get('material', '')})"
            else:
                client = entry.get('client', 'Sin nombre')
                total = entry.get('total', 0)
                label = f"{ts}  {client} — ${self.format_price_col(total)}"
            self.history_listbox.insert(tk.END, label)

        self.selected_history_index = None
        self.history_detail_title.config(text="Selecciona una cotización")
        self.history_detail_text.config(state='normal')
        self.history_detail_text.delete(1.0, tk.END)
        if not self.history_data:
            self.history_detail_text.insert(tk.END, "Aún no hay cotizaciones guardadas.")
        self.history_detail_text.config(state='disabled')

    def on_history_select(self, event=None):
        selection = self.history_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.selected_history_index = index
        self.render_history_detail(self.history_data[index])

    def render_history_detail(self, entry):
        w = self.history_detail_text
        w.config(state='normal')
        w.delete(1.0, tk.END)

        if entry.get('type') == 'conversion':
            self.history_detail_title.config(text=f"Conversión — {entry.get('timestamp', '')}")
            self._write_section(w, "PROPIEDADES DEL MATERIAL")
            self._write_row(w, "Material:", entry.get('material', ''))
            self._write_row(w, "Diámetro:", f"{entry.get('diameter', 0):.2f} mm")
            self._write_row(w, "Densidad:", f"{entry.get('density', 0):.2f} g/cm³")
            self._write_row(w, "Convertido desde:",
                          f"{entry.get('conversion_type', '')} = {entry.get('value', 0)}")
            w.insert(tk.END, "\n")

            r = entry.get('results', {})
            self._write_section(w, "RESULTADO")
            self._write_row(w, "Peso:", f"{r.get('weight', 0):.2f} g")
            self._write_row(w, "Longitud:", f"{r.get('length', 0):.2f} m")
            self._write_row(w, "Volumen:", f"{r.get('volume', 0):.2f} cm³")
        else:
            client = entry.get('client', 'Sin nombre')
            self.history_detail_title.config(text=f"{client} — {entry.get('timestamp', '')}")

            self._write_section(w, "PIEZAS")
            for p in entry.get('pieces', []):
                label = f"{p['name'][:16]} x{p['quantity']}"
                self._write_row(w, label, f"${self.format_price_col(p['subtotal'])}")
                for ex in p.get('piece_extras', []):
                    self._write_row(w, f"+ {ex['name']}:", f"${self.format_price_col(ex['cost'])}", indent=4)
                for name, val in p.get('package_costs', {}).items():
                    self._write_row(w, f"+ {name} (empaque):", f"${self.format_price_col(val)}", indent=4)
            self._write_divider(w)
            self._write_row(w, "Subtotal piezas:", f"${self.format_price_col(entry.get('pieces_subtotal', 0))}",
                           indent=0)
            w.insert(tk.END, "\n")

            extras = entry.get('global_extras', {})
            if extras:
                self._write_section(w, "EXTRAS")
                for name, val in extras.items():
                    self._write_row(w, name, f"${self.format_price_col(val)}")
                self._write_divider(w)
                self._write_row(w, "Subtotal extras:",
                               f"${self.format_price_col(entry.get('extras_subtotal', 0))}", indent=0)
                w.insert(tk.END, "\n")

            self._write_section(w, "DETALLE DE COSTOS POR PIEZA")
            for p in entry.get('pieces', []):
                b = p.get('breakdown', {})
                time_min = p.get('time_min', 0)
                hours = int(time_min // 60)
                minutes = int(time_min % 60)
                w.insert(tk.END, f"\n{p['name']} (x{p['quantity']})\n")
                self._write_row(w, "Material:", f"${self.format_price_col(b.get('material_cost', 0))}")
                self._write_row(w, "Electricidad:", f"${self.format_price_col(b.get('electricity_cost', 0))}")
                self._write_row(w, "Máquina:", f"${self.format_price_col(b.get('machine_cost', 0))}")
                self._write_row(w, "Fallo:", f"${self.format_price_col(b.get('failure_cost', 0))}")
                self._write_row(w, "Ganancia:", f"${self.format_price_col(b.get('profit', 0))}")
                for ex in p.get('piece_extras', []):
                    self._write_row(w, f"+ {ex['name']}:", f"${self.format_price_col(ex['cost'])}")
                for name, val in p.get('package_costs', {}).items():
                    self._write_row(w, f"+ {name} (empaque):", f"${self.format_price_col(val)}")
                self._write_row(w, "Tiempo:", f"{hours}:{minutes:02d} ({int(time_min)} min)")
                self._write_row(w, "Peso:", f"{p.get('weight_g', 0):.0f}g")
            w.insert(tk.END, "\n")

            self._write_total(w, "TOTAL:", f"${self.format_price_col(entry.get('total', 0))}")

        w.config(state='disabled')

    def delete_selected_history(self):
        if self.selected_history_index is None:
            messagebox.showwarning("Selección", "Por favor selecciona una cotización para eliminar")
            return
        history = self.load_history_data()
        del history[self.selected_history_index]
        if not self.save_history_data(history):
            return
        messagebox.showinfo("Eliminado", "Entrada eliminada del historial")
        self.refresh_history_list()

    def clear_all_history(self):
        response = messagebox.askyesno(
            "Confirmar",
            "¿Estás seguro de que deseas eliminar todo el historial?\nEsta acción no se puede deshacer."
        )
        if response:
            if not self.save_history_data([]):
                return
            messagebox.showinfo("Limpiado", "Historial eliminado completamente")
            self.refresh_history_list()


def main():
    root = tk.Tk()
    app = CalculadoraApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()