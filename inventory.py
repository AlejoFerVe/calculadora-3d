"""
Inventario - Inventory tab for Calculadora 3D.

Two sub-sections:
  * Filamento: filament stock (brand, material, color, spools/packages,
    current grams) with quick adjustments, plus a table of empty-spool weights.
  * Papelería: boxes, bags (size, price, where it was bought: link or address)
    and shipping platforms with estimated price.

Data is stored in 'inventario.json' next to the program.
"""

import json
import os
import sys
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox
from urllib.parse import quote_plus

FILAMENT_MATERIALS = ["PLA", "PLA+", "PLA Silk", "PLA Mate", "PETG", "ABS", "ASA", "TPU", "Nylon"]
PURCHASE_TYPES = ["Internet", "Presencial"]
PRESENTATIONS = ["Carrete", "Paquete"]
LOW_STOCK_PERCENT = 20


def _app_dir():
    """Folder of the .exe when packaged, or of this file when run with Python."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fmt_grams(value):
    return f"{_num(value):,.0f} g".replace(',', '.')


class CrudSection:
    """A titled card with a form on the left and a table on the right.

    fields:  list of dicts {key, label, kind ('text'|'number'|'int'|'combo'|'choice'),
             values, default, required}
    columns: list of (heading, width, anchor, formatter(item) -> str)
    """

    def __init__(self, inv, parent, title, subtitle, data_key, fields, columns,
                 item_name="elemento", on_change=None, row_tag=None):
        self.inv = inv
        self.colors = inv.colors
        self.data_key = data_key
        self.fields = fields
        self.columns = columns
        self.item_name = item_name
        self.on_change = on_change
        self.row_tag = row_tag
        self.editing_index = None
        self.widgets = {}

        card = tk.Frame(parent, bg=self.colors['panel_left'],
                        highlightthickness=1, highlightbackground=self.colors['border'])
        card.pack(fill='x', pady=(0, 15))
        self.card = card

        tk.Label(card, text=title, font=('Segoe UI', 14, 'bold'),
                 bg=self.colors['panel_left'], fg=self.colors['text_primary']).pack(
                     anchor='w', padx=20, pady=(15, 2))
        if subtitle:
            tk.Label(card, text=subtitle, font=('Segoe UI', 8),
                     bg=self.colors['panel_left'], fg=self.colors['text_secondary'],
                     wraplength=900, justify='left').pack(anchor='w', padx=20, pady=(0, 10))

        body = tk.Frame(card, bg=self.colors['panel_left'])
        body.pack(fill='both', expand=True, padx=20, pady=(0, 15))
        body.columnconfigure(1, weight=1)
        self.body = body

        # ---- Form ----
        form = tk.Frame(body, bg=self.colors['panel_left'])
        form.grid(row=0, column=0, sticky='nw', padx=(0, 20))
        form.columnconfigure(1, weight=1)
        for row, field in enumerate(fields):
            label = field['label'] + (" *" if field.get('required') else "")
            tk.Label(form, text=label, font=('Segoe UI', 9),
                     bg=self.colors['panel_left'], fg=self.colors['text_secondary']).grid(
                         row=row, column=0, sticky='w', pady=4, padx=(0, 10))
            kind = field.get('kind', 'text')
            if kind in ('combo', 'choice'):
                widget = ttk.Combobox(form, values=field.get('values', []), font=('Segoe UI', 10),
                                      width=24, state='readonly' if kind == 'choice' else 'normal')
            else:
                widget = tk.Entry(form, font=('Segoe UI', 10), width=26,
                                  bg='white', fg=self.colors['text_primary'],
                                  relief='solid', bd=1, highlightthickness=1,
                                  highlightbackground=self.colors['border'],
                                  highlightcolor=self.colors['button_blue'])
            widget.grid(row=row, column=1, sticky='ew', pady=4)
            self.widgets[field['key']] = widget
        self._set_defaults()

        btns = tk.Frame(form, bg=self.colors['panel_left'])
        btns.grid(row=len(fields), column=0, columnspan=2, sticky='ew', pady=(10, 0))
        self.save_btn = tk.Button(btns, text=f"Agregar {item_name}", font=('Segoe UI', 9, 'bold'),
                                  bg=self.colors['button_blue'], fg='white', bd=0,
                                  padx=12, pady=8, cursor='hand2', command=self.save_item)
        self.save_btn.pack(fill='x')
        tk.Button(btns, text="Limpiar formulario", font=('Segoe UI', 9), bg='white',
                  fg=self.colors['text_primary'], relief='solid', bd=1, padx=10, pady=6,
                  cursor='hand2', command=self.clear_form).pack(fill='x', pady=(6, 0))

        # ---- Table ----
        table = tk.Frame(body, bg=self.colors['panel_left'])
        table.grid(row=0, column=1, sticky='nsew')
        self.table = table

        tree_frame = tk.Frame(table, bg=self.colors['panel_left'])
        tree_frame.pack(fill='both', expand=True)
        col_ids = [f"c{i}" for i in range(len(columns))]
        self.tree = ttk.Treeview(tree_frame, columns=col_ids, show='headings',
                                 height=8, selectmode='browse')
        for cid, (heading, width, anchor, _) in zip(col_ids, columns):
            self.tree.heading(cid, text=heading)
            self.tree.column(cid, width=width, anchor=anchor, minwidth=50)
        self.tree.tag_configure('low', foreground='#DC2626')
        self.tree.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        self.table_btns = tk.Frame(table, bg=self.colors['panel_left'])
        self.table_btns.pack(fill='x', pady=(8, 0))
        tk.Button(self.table_btns, text="Eliminar seleccionado", font=('Segoe UI', 9), bg='white',
                  fg='#DC2626', relief='solid', bd=1, padx=10, pady=6, cursor='hand2',
                  command=self.delete_selected).pack(side='left')

        self.refresh()

    # ---- helpers ----
    @property
    def items(self):
        return self.inv.data.setdefault(self.data_key, [])

    def add_table_button(self, text, command):
        tk.Button(self.table_btns, text=text, font=('Segoe UI', 9), bg='white',
                  fg=self.colors['text_primary'], relief='solid', bd=1, padx=10, pady=6,
                  cursor='hand2', command=command).pack(side='left', padx=(8, 0))

    def selected_index(self):
        sel = self.tree.selection()
        return self.tree.index(sel[0]) if sel else None

    def _set_widget(self, key, value):
        widget = self.widgets[key]
        if isinstance(widget, ttk.Combobox):
            widget.set('' if value is None else str(value))
        else:
            widget.delete(0, tk.END)
            if value not in (None, ''):
                widget.insert(0, str(value))

    def _set_defaults(self):
        for f in self.fields:
            self._set_widget(f['key'], f.get('default', ''))

    def clear_form(self):
        self.editing_index = None
        self.save_btn.config(text=f"Agregar {self.item_name}")
        self._set_defaults()
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def _read_form(self):
        item = {}
        for f in self.fields:
            raw = self.widgets[f['key']].get().strip()
            kind = f.get('kind', 'text')
            if f.get('required') and not raw:
                raise ValueError(f"El campo '{f['label']}' es obligatorio.")
            if kind == 'number':
                if raw:
                    try:
                        item[f['key']] = float(raw.replace(',', '.'))
                    except ValueError:
                        raise ValueError(f"'{f['label']}' debe ser un número.")
                else:
                    item[f['key']] = None
            elif kind == 'int':
                if raw:
                    try:
                        item[f['key']] = int(float(raw.replace(',', '.')))
                    except ValueError:
                        raise ValueError(f"'{f['label']}' debe ser un número entero.")
                else:
                    item[f['key']] = None
            else:
                item[f['key']] = raw
        return item

    def prepare_item(self, item, previous):
        """Hook for subclasses/owners to fill computed values."""
        return item

    # ---- actions ----
    def save_item(self):
        try:
            item = self._read_form()
        except ValueError as e:
            messagebox.showerror("Datos inválidos", str(e))
            return
        previous = self.items[self.editing_index] if self.editing_index is not None else None
        try:
            item = self.prepare_item(item, previous)
        except ValueError as e:
            messagebox.showerror("Datos inválidos", str(e))
            return
        if self.editing_index is not None:
            self.items[self.editing_index] = item
        else:
            self.items.append(item)
        if not self.inv.save():
            return
        self.clear_form()
        self.refresh()

    def delete_selected(self):
        index = self.selected_index()
        if index is None:
            messagebox.showwarning("Selección", f"Selecciona un {self.item_name} en la tabla.")
            return
        if not messagebox.askyesno("Confirmar", f"¿Eliminar este {self.item_name}?"):
            return
        del self.items[index]
        if not self.inv.save():
            return
        self.clear_form()
        self.refresh()

    def _on_select(self, event=None):
        index = self.selected_index()
        if index is None:
            return
        item = self.items[index]
        for f in self.fields:
            self._set_widget(f['key'], item.get(f['key'], ''))
        self.editing_index = index
        self.save_btn.config(text="Guardar cambios")

    def refresh(self):
        selected = self.selected_index()
        self.tree.delete(*self.tree.get_children())
        for item in self.items:
            values = [fmt(item) for _, _, _, fmt in self.columns]
            tags = (self.row_tag(item),) if self.row_tag and self.row_tag(item) else ()
            self.tree.insert('', 'end', values=values, tags=tags)
        if selected is not None and selected < len(self.items):
            child = self.tree.get_children()[selected]
            self.tree.selection_set(child)
        if self.on_change:
            self.on_change()


class InventoryTab:
    def __init__(self, app, notebook):
        self.app = app
        self.colors = app.colors
        self.file = os.path.join(_app_dir(), "inventario.json")
        self.data = self.load()

        tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(tab, text="Inventario")

        sub = ttk.Notebook(tab)
        sub.pack(fill='both', expand=True, padx=10, pady=10)

        self._build_filament(sub)
        self._build_stationery(sub)

    # ---------------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------------
    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                messagebox.showwarning(
                    "Inventario",
                    "No se pudo leer 'inventario.json'. Se empezará con un inventario vacío "
                    "(el archivo no se borra hasta que guardes un cambio).")
        return {}

    def save(self):
        try:
            with open(self.file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except PermissionError:
            messagebox.showerror(
                "No se pudo guardar",
                "No se pudo escribir en 'inventario.json'.\n\n"
                "Cierra el archivo si lo tienes abierto en otro programa e inténtalo de nuevo.")
            return False
        except OSError as e:
            messagebox.showerror("No se pudo guardar", f"Error al guardar el inventario:\n{e}")
            return False

    def _page(self, notebook, title):
        tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(tab, text=title)
        content, canvas = self.app._make_scrollable(tab)
        page = tk.Frame(content, bg=self.colors['bg_general'])
        page.pack(fill='both', expand=True, padx=15, pady=15)
        return page, canvas

    # ---------------------------------------------------------------
    # FILAMENTO
    # ---------------------------------------------------------------
    def _build_filament(self, notebook):
        page, canvas = self._page(notebook, "Filamento")

        # Summary strip
        self.filament_summary = tk.Label(page, text="", font=('Segoe UI', 11, 'bold'),
                                         bg=self.colors['panel_right'], fg=self.colors['text_white'],
                                         anchor='w', padx=20, pady=12)
        self.filament_summary.pack(fill='x', pady=(0, 15))

        def capacity(item):
            return _num(item.get('peso_unidad_kg'), 1) * 1000 * max(1, int(_num(item.get('cantidad'), 1)))

        def percent(item):
            cap = capacity(item)
            return (_num(item.get('gramos')) / cap * 100) if cap else 0

        def presentation(item):
            qty = int(_num(item.get('cantidad'), 1))
            kind = item.get('presentacion') or 'Carrete'
            kg = _num(item.get('peso_unidad_kg'), 1)
            kg_txt = f"{kg:g} kg"
            plural = 's' if qty != 1 else ''
            return f"{qty} {kind.lower()}{plural} de {kg_txt}"

        def price(item):
            p = item.get('precio')
            return f"${self.app.format_price_col(p)}" if p not in (None, '') else "—"

        fields = [
            {'key': 'marca', 'label': 'Marca', 'required': True},
            {'key': 'material', 'label': 'Material', 'kind': 'combo',
             'values': FILAMENT_MATERIALS, 'default': 'PLA'},
            {'key': 'color', 'label': 'Color', 'required': True},
            {'key': 'presentacion', 'label': 'Presentación', 'kind': 'choice',
             'values': PRESENTATIONS, 'default': 'Carrete'},
            {'key': 'peso_unidad_kg', 'label': 'Kilos por carrete/paquete', 'kind': 'number', 'default': '1'},
            {'key': 'cantidad', 'label': 'Cantidad (carretes/paquetes)', 'kind': 'int', 'default': '1'},
            {'key': 'gramos', 'label': 'Gramos actuales', 'kind': 'number'},
            {'key': 'precio', 'label': 'Precio por unidad ($)', 'kind': 'number'},
            {'key': 'notas', 'label': 'Notas'},
        ]
        columns = [
            ('Marca', 110, 'w', lambda i: i.get('marca', '')),
            ('Material', 80, 'w', lambda i: i.get('material', '')),
            ('Color', 100, 'w', lambda i: i.get('color', '')),
            ('Presentación', 150, 'w', presentation),
            ('Gramos actuales', 110, 'e', lambda i: _fmt_grams(i.get('gramos'))),
            ('% restante', 80, 'center', lambda i: f"{percent(i):.0f} %"),
            ('Precio/u', 90, 'e', price),
        ]

        self.filament = CrudSection(
            self, page, "Stock de filamento",
            "Registra cada filamento con su marca, color y presentación. Si dejas 'Gramos actuales' "
            "vacío se calcula como lleno (kilos × cantidad). Selecciona una fila para editarla o para "
            "descontar lo que vas gastando. En rojo: queda menos del "
            f"{LOW_STOCK_PERCENT} %.",
            'filamentos', fields, columns, item_name="filamento",
            on_change=self._update_filament_summary,
            row_tag=lambda i: 'low' if percent(i) < LOW_STOCK_PERCENT else None)

        def prepare(item, previous):
            if item.get('peso_unidad_kg') is None:
                item['peso_unidad_kg'] = 1.0
            if item['peso_unidad_kg'] <= 0:
                raise ValueError("Los kilos por carrete/paquete deben ser mayores que 0.")
            if item.get('cantidad') is None or item['cantidad'] < 1:
                item['cantidad'] = 1
            if item.get('gramos') is None:
                item['gramos'] = capacity(item)
            if item['gramos'] < 0:
                raise ValueError("Los gramos no pueden ser negativos.")
            return item
        self.filament.prepare_item = prepare

        self._build_adjust_panel(self.filament)

        # ---- Empty spool weights ----
        spool_fields = [
            {'key': 'marca', 'label': 'Marca', 'required': True},
            {'key': 'tipo', 'label': 'Tipo de carrete (plástico, cartón…)'},
            {'key': 'peso_g', 'label': 'Peso del carrete vacío (g)', 'kind': 'number', 'required': True},
            {'key': 'notas', 'label': 'Notas'},
        ]
        spool_columns = [
            ('Marca', 150, 'w', lambda i: i.get('marca', '')),
            ('Tipo', 150, 'w', lambda i: i.get('tipo', '')),
            ('Peso vacío', 110, 'e', lambda i: _fmt_grams(i.get('peso_g'))),
            ('Notas', 220, 'w', lambda i: i.get('notas', '')),
        ]
        self.spools = CrudSection(
            self, page, "Peso de carretes vacíos",
            "Guarda cuánto pesa el carrete vacío de cada marca. Así, pesando el carrete en la "
            "báscula, puedes saber cuánto filamento le queda (ver 'Calcular con báscula' arriba).",
            'carretes_vacios', spool_fields, spool_columns, item_name="carrete",
            on_change=self._update_spool_choices)

        self.app._bind_mousewheel_recursive(page, canvas)

    def _build_adjust_panel(self, section):
        panel = tk.Frame(section.table, bg=self.colors['bg_general'],
                         highlightthickness=1, highlightbackground=self.colors['border'])
        panel.pack(fill='x', pady=(10, 0))

        tk.Label(panel, text="Ajustar el filamento seleccionado", font=('Segoe UI', 10, 'bold'),
                 bg=self.colors['bg_general'], fg=self.colors['text_primary']).grid(
                     row=0, column=0, columnspan=6, sticky='w', padx=10, pady=(8, 4))

        tk.Label(panel, text="Gramos:", font=('Segoe UI', 9), bg=self.colors['bg_general'],
                 fg=self.colors['text_secondary']).grid(row=1, column=0, sticky='w', padx=(10, 4), pady=4)
        self.adjust_entry = tk.Entry(panel, font=('Segoe UI', 10), width=10, relief='solid', bd=1)
        self.adjust_entry.grid(row=1, column=1, sticky='w', pady=4)

        def btn(text, cmd, col, primary=False):
            tk.Button(panel, text=text, font=('Segoe UI', 9, 'bold' if primary else 'normal'),
                      bg=self.colors['button_blue'] if primary else 'white',
                      fg='white' if primary else self.colors['text_primary'],
                      relief='flat' if primary else 'solid', bd=0 if primary else 1,
                      padx=10, pady=4, cursor='hand2', command=cmd).grid(
                          row=1, column=col, sticky='w', padx=(8, 0), pady=4)

        btn("− Gasté", lambda: self._adjust_grams('restar'), 2, primary=True)
        btn("+ Agregué", lambda: self._adjust_grams('sumar'), 3)
        btn("Fijar valor", lambda: self._adjust_grams('fijar'), 4)

        tk.Label(panel, text="Calcular con báscula:", font=('Segoe UI', 9),
                 bg=self.colors['bg_general'], fg=self.colors['text_secondary']).grid(
                     row=2, column=0, columnspan=2, sticky='w', padx=(10, 4), pady=(6, 4))
        self.scale_entry = tk.Entry(panel, font=('Segoe UI', 10), width=10, relief='solid', bd=1)
        self.scale_entry.grid(row=2, column=2, sticky='w', padx=(8, 0), pady=(6, 4))
        tk.Label(panel, text="g en báscula, carrete:", font=('Segoe UI', 9),
                 bg=self.colors['bg_general'], fg=self.colors['text_secondary']).grid(
                     row=2, column=3, sticky='w', padx=(4, 4), pady=(6, 4))
        self.spool_choice = ttk.Combobox(panel, state='readonly', width=28, font=('Segoe UI', 9))
        self.spool_choice.grid(row=2, column=4, columnspan=2, sticky='w', pady=(6, 4))
        btn("Calcular", self._calc_from_scale, 6)

        tk.Label(panel,
                 text="La báscula calcula el filamento de UN carrete (peso en báscula − carrete vacío) "
                      "y lo deja en 'Gramos' para que lo fijes o lo descuentes.",
                 font=('Segoe UI', 8), bg=self.colors['bg_general'], fg=self.colors['text_secondary'],
                 wraplength=700, justify='left').grid(row=3, column=0, columnspan=7, sticky='w',
                                                      padx=10, pady=(0, 8))

    def _adjust_grams(self, mode):
        index = self.filament.selected_index()
        if index is None:
            messagebox.showwarning("Selección", "Selecciona un filamento en la tabla.")
            return
        raw = self.adjust_entry.get().strip().replace(',', '.')
        try:
            grams = float(raw)
        except ValueError:
            messagebox.showerror("Dato inválido", "Escribe los gramos como un número (ej: 35).")
            return
        if grams < 0:
            messagebox.showerror("Dato inválido", "Los gramos no pueden ser negativos.")
            return
        item = self.filament.items[index]
        current = _num(item.get('gramos'))
        if mode == 'restar':
            new = current - grams
            if new < 0:
                if not messagebox.askyesno(
                        "Stock insuficiente",
                        f"Solo quedan {_fmt_grams(current)}. ¿Dejarlo en 0 g?"):
                    return
                new = 0
        elif mode == 'sumar':
            new = current + grams
        else:
            new = grams
        item['gramos'] = round(new, 1)
        if not self.save():
            item['gramos'] = current
            return
        self.adjust_entry.delete(0, tk.END)
        self.filament.refresh()
        self.filament._on_select()

    def _calc_from_scale(self):
        raw = self.scale_entry.get().strip().replace(',', '.')
        try:
            total = float(raw)
        except ValueError:
            messagebox.showerror("Dato inválido", "Escribe el peso de la báscula en gramos.")
            return
        idx = self.spool_choice.current()
        spools = self.data.get('carretes_vacios', [])
        if idx < 0 or idx >= len(spools):
            messagebox.showwarning("Carrete", "Elige el carrete vacío (regístralo abajo si no está).")
            return
        net = total - _num(spools[idx].get('peso_g'))
        if net < 0:
            messagebox.showerror("Revisa los datos", "El peso en báscula es menor que el carrete vacío.")
            return
        self.adjust_entry.delete(0, tk.END)
        self.adjust_entry.insert(0, f"{net:.0f}")

    def _update_spool_choices(self):
        if not hasattr(self, 'spool_choice'):
            return
        options = []
        for s in self.data.get('carretes_vacios', []):
            tipo = f" ({s['tipo']})" if s.get('tipo') else ""
            options.append(f"{s.get('marca', '')}{tipo} — {_fmt_grams(s.get('peso_g'))}")
        self.spool_choice.config(values=options)
        if self.spool_choice.current() >= len(options):
            self.spool_choice.set('')

    def _update_filament_summary(self):
        items = self.data.get('filamentos', [])
        total = sum(_num(i.get('gramos')) for i in items)
        low = 0
        for i in items:
            cap = _num(i.get('peso_unidad_kg'), 1) * 1000 * max(1, int(_num(i.get('cantidad'), 1)))
            if cap and _num(i.get('gramos')) / cap * 100 < LOW_STOCK_PERCENT:
                low += 1
        text = (f"Total en stock: {_fmt_grams(total)}  ({total / 1000:.2f} kg)   ·   "
                f"{len(items)} filamento(s)")
        if low:
            text += f"   ·   ⚠ {low} con poco stock"
        self.filament_summary.config(text=text)

    # ---------------------------------------------------------------
    # PAPELERÍA
    # ---------------------------------------------------------------
    def _build_stationery(self, notebook):
        page, canvas = self._page(notebook, "Papelería")

        def money(key):
            def f(item):
                v = item.get(key)
                return f"${self.app.format_price_col(v)}" if v not in (None, '') else "—"
            return f

        def stock(item):
            v = item.get('cantidad')
            return str(v) if v not in (None, '') else "—"

        def supply_fields(name_label):
            return [
                {'key': 'nombre', 'label': name_label, 'required': True},
                {'key': 'medidas', 'label': 'Medidas (ej: 20x15x10 cm)'},
                {'key': 'cantidad', 'label': 'Cantidad en stock', 'kind': 'int'},
                {'key': 'precio', 'label': 'Precio por unidad ($)', 'kind': 'number'},
                {'key': 'compra', 'label': 'Dónde lo compré', 'kind': 'choice',
                 'values': PURCHASE_TYPES, 'default': 'Internet'},
                {'key': 'lugar', 'label': 'Link (internet) o dirección'},
                {'key': 'notas', 'label': 'Notas'},
            ]

        supply_columns = [
            ('Descripción', 150, 'w', lambda i: i.get('nombre', '')),
            ('Medidas', 110, 'w', lambda i: i.get('medidas', '')),
            ('Stock', 60, 'center', stock),
            ('Precio/u', 90, 'e', money('precio')),
            ('Compra', 80, 'center', lambda i: i.get('compra', '')),
            ('Link / Dirección', 260, 'w', lambda i: i.get('lugar', '')),
        ]

        self.boxes = CrudSection(
            self, page, "Cajas",
            "Cajas para empacar: medidas, precio y dónde las compraste. Si fue por internet pega el "
            "link; si fue presencial, escribe la dirección.",
            'cajas', supply_fields("Descripción de la caja"), supply_columns, item_name="caja")
        self.boxes.add_table_button("Abrir link / dirección", lambda: self._open_place(self.boxes))

        self.bags = CrudSection(
            self, page, "Bolsas",
            "Bolsas (zip, celofán, de regalo…): medidas, precio y dónde las compraste.",
            'bolsas', supply_fields("Descripción de la bolsa"), supply_columns, item_name="bolsa")
        self.bags.add_table_button("Abrir link / dirección", lambda: self._open_place(self.bags))

        ship_fields = [
            {'key': 'plataforma', 'label': 'Plataforma / empresa', 'required': True},
            {'key': 'destino', 'label': 'Destino o cobertura'},
            {'key': 'tiempo', 'label': 'Tiempo de entrega'},
            {'key': 'precio', 'label': 'Precio estimado ($)', 'kind': 'number'},
            {'key': 'lugar', 'label': 'Link de la plataforma'},
            {'key': 'notas', 'label': 'Notas'},
        ]
        ship_columns = [
            ('Plataforma', 150, 'w', lambda i: i.get('plataforma', '')),
            ('Destino', 140, 'w', lambda i: i.get('destino', '')),
            ('Tiempo', 100, 'w', lambda i: i.get('tiempo', '')),
            ('Precio est.', 100, 'e', money('precio')),
            ('Link', 220, 'w', lambda i: i.get('lugar', '')),
        ]
        self.shipping = CrudSection(
            self, page, "Plataformas de envío",
            "Empresas o apps de envío que usas y cuánto cuesta aproximadamente cada envío.",
            'envios', ship_fields, ship_columns, item_name="envío")
        self.shipping.add_table_button("Abrir link", lambda: self._open_place(self.shipping))

        self.app._bind_mousewheel_recursive(page, canvas)

    def _open_place(self, section):
        index = section.selected_index()
        if index is None:
            messagebox.showwarning("Selección", "Selecciona una fila en la tabla.")
            return
        place = (section.items[index].get('lugar') or '').strip()
        if not place:
            messagebox.showinfo("Sin datos", "Esta fila no tiene link ni dirección.")
            return
        if place.lower().startswith(('http://', 'https://', 'www.')):
            url = place if not place.lower().startswith('www.') else 'https://' + place
        else:
            url = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(place)
        webbrowser.open(url)
