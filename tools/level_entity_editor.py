"""Editeur de placements et de comportements pour les entites d'un niveau."""

import argparse
import json
import math
import os
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MAP = ROOT / "assets" / "maps" / "level_1_pyxel.json"
TILE_SIZE = 32
COLLISION_LAYERS = {"passages", "strict_collider"}
ZOOMS = (0.5, 1.0, 2.0)
ENTITY_CATEGORIES = ("enemy", "item", "special")
CATEGORY_LABELS = {
    "enemy": "Ennemi",
    "item": "Objet",
    "special": "Special",
}
ENTITY_COLORS = {
    "enemy": "#ef6461",
    "item": "#f2c14e",
    "special": "#59c3c3",
}
SEQUENCE_FLIP_CHOICES = {
    "Global": None,
    "Oui": True,
    "Non": False,
    "Si direction == droite": "direction_right",
    "Si direction == gauche": "direction_left",
}
SEQUENCE_FLIP_LABELS = {
    value: label for label, value in SEQUENCE_FLIP_CHOICES.items()
}


def default_entity(category, number, x=0, y=0):
    """Return a complete, editable entity with useful defaults."""
    return {
        "id": f"{category}-{number}",
        "name": f"{CATEGORY_LABELS[category]} {number}",
        "category": category,
        "x": x,
        "y": y,
        "width": TILE_SIZE,
        "height": TILE_SIZE,
        "layer": 0,
        "hitbox": {
            "x": 4,
            "y": 16,
            "width": 24,
            "height": 16,
        },
        "killable": False,
        "visible": True,
        "enabled": True,
        "collision": True,
        "tags": [],
        "sprite": "",
        "animation": {
            "frame_width": TILE_SIZE,
            "frame_height": TILE_SIZE,
            "columns": 1,
            "frame_count": 1,
            "row": 0,
            "fps": 8,
            "frame_delay_ms": 125,
            "sequences": {"left": [], "right": [], "death": []},
            "direction_settings": {
                "left": {"frame_delay_ms": None, "flip_x": None, "flip_y": None},
                "right": {"frame_delay_ms": None, "flip_x": None, "flip_y": None},
                "death": {"frame_delay_ms": None, "flip_x": None, "flip_y": None},
            },
            "loop": True,
            "offset_x": 0,
            "offset_y": 0,
            "flip_x": False,
            "flip_y": False,
        },
        "movement": {
            "type": "stationary",
            "axis": "x",
            "speed": 1.0,
            "range": 96,
            "waypoints": [],
            "steps": [],
            "gravity": False,
            "bounce": False,
            "facing": "right",
        },
        "effects": {
            "trigger": "contact",
            "action": "damage",
            "amount": 1,
            "duration": 0,
            "radius": 0,
            "cooldown": 0,
            "one_shot": False,
            "sound": "",
            "target": "player",
        },
        "custom_data": {},
    }


def normalize_entity(entity, index):
    """Fill newly introduced options without removing user-defined values."""
    category = entity.get("category", "enemy")
    if category not in ENTITY_CATEGORIES:
        category = "special"
    result = default_entity(category, index)
    result.update(entity)
    for section in ("animation", "movement", "effects", "hitbox"):
        if not isinstance(result.get(section), dict):
            result[section] = {}
        defaults = default_entity(category, index)[section]
        result[section] = {**defaults, **result[section]}
    if "frame_delay_ms" not in entity.get("animation", {}):
        result["animation"]["frame_delay_ms"] = (
            1000 / max(0.1, float(result["animation"]["fps"]))
        )
    direction_defaults = {
        direction: {"frame_delay_ms": None, "flip_x": None, "flip_y": None}
        for direction in ("left", "right", "death")
    }
    existing_direction_settings = result["animation"].get("direction_settings", {})
    if not isinstance(existing_direction_settings, dict):
        existing_direction_settings = {}
    result["animation"]["direction_settings"] = {
        direction: {
            **direction_defaults[direction],
            **(
                existing_direction_settings.get(direction, {})
                if isinstance(existing_direction_settings.get(direction, {}), dict)
                else {}
            ),
        }
        for direction in ("left", "right", "death")
    }
    for key in ("x", "y", "width", "height"):
        value = result["hitbox"].get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"'hitbox.{key}' doit etre un nombre.")
        if not math.isfinite(value):
            raise ValueError(f"'hitbox.{key}' doit etre fini.")
    if result["hitbox"]["width"] <= 0 or result["hitbox"]["height"] <= 0:
        raise ValueError("La largeur et la hauteur de la hitbox doivent etre positives.")
    if not isinstance(result.get("custom_data"), dict):
        result["custom_data"] = {}
    if not isinstance(result.get("tags"), list):
        result["tags"] = []
    return result


def entities_file_for(map_path):
    path = Path(map_path)
    return path.with_name(f"{path.stem}.entities.json")


def load_document(map_path, entities_path=None):
    map_path = Path(map_path).resolve()
    with map_path.open("r", encoding="utf-8") as source:
        map_data = json.load(source)
    width = map_data.get("width")
    height = map_data.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError("La carte doit definir une largeur et une hauteur entieres.")
    if width <= 0 or height <= 0:
        raise ValueError("Les dimensions de la carte doivent etre positives.")

    entities_path = Path(entities_path or entities_file_for(map_path)).resolve()
    if entities_path.exists():
        with entities_path.open("r", encoding="utf-8") as source:
            document = json.load(source)
        entities = document.get("entities")
        if not isinstance(entities, list):
            raise ValueError(f"La liste 'entities' est absente de {entities_path}.")
    else:
        entities = []
    normalized = [
        normalize_entity(entity, index + 1)
        for index, entity in enumerate(entities)
    ]
    ids = set()
    for entity in normalized:
        validate_entity(entity)
        if entity["id"] in ids:
            raise ValueError(f"Identifiant d'entite duplique : {entity['id']}")
        ids.add(entity["id"])
    return map_path, entities_path, map_data, normalized


def validate_entity(entity):
    if not str(entity.get("name", "")).strip():
        raise ValueError("Chaque entite doit avoir un nom.")
    if entity.get("category") not in ENTITY_CATEGORIES:
        raise ValueError("La categorie doit etre enemy, item ou special.")
    for key in ("x", "y", "width", "height", "layer"):
        value = entity.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"'{key}' doit etre un nombre.")
        if not math.isfinite(value):
            raise ValueError(f"'{key}' doit etre un nombre fini.")
    if entity["width"] <= 0 or entity["height"] <= 0:
        raise ValueError("La largeur et la hauteur doivent etre positives.")
    for section in ("animation", "movement", "effects"):
        if not isinstance(entity.get(section), dict):
            raise ValueError(f"'{section}' doit etre un objet JSON.")
    animation = entity["animation"]
    for key in ("frame_width", "frame_height", "columns", "frame_count"):
        if not isinstance(animation.get(key), int) or animation[key] <= 0:
            raise ValueError(f"'animation.{key}' doit etre un entier positif.")
    for key in ("row", "offset_x", "offset_y"):
        if not isinstance(animation.get(key), int):
            raise ValueError(f"'animation.{key}' doit etre un entier.")
    for key in ("fps",):
        value = animation.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"'animation.{key}' doit etre un nombre.")
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"'animation.{key}' doit etre positif et fini.")
    value = animation.get("frame_delay_ms")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("'animation.frame_delay_ms' doit etre un nombre.")
    if not math.isfinite(value) or value <= 0:
        raise ValueError("'animation.frame_delay_ms' doit etre positif et fini.")
    direction_settings = animation.get("direction_settings", {})
    if not isinstance(direction_settings, dict):
        raise ValueError("'animation.direction_settings' doit etre un objet JSON.")
    for direction in ("left", "right", "death"):
        settings = direction_settings.get(direction, {})
        if not isinstance(settings, dict):
            raise ValueError(f"'animation.direction_settings.{direction}' doit etre un objet JSON.")
        override_delay = settings.get("frame_delay_ms")
        if override_delay is not None:
            if (
                isinstance(override_delay, bool)
                or not isinstance(override_delay, (int, float))
                or not math.isfinite(override_delay)
                or override_delay <= 0
            ):
                raise ValueError(
                    f"'animation.direction_settings.{direction}.frame_delay_ms' "
                    "doit etre vide ou un nombre positif."
                )
        for flip_key in ("flip_x", "flip_y"):
            flip_value = settings.get(flip_key)
            valid_flip = (
                flip_value is None
                or isinstance(flip_value, bool)
                or (
                    direction == "death"
                    and flip_value in ("direction_right", "direction_left")
                )
            )
            if not valid_flip:
                raise ValueError(
                    f"'animation.direction_settings.{direction}.{flip_key}' "
                    "doit etre vide, true, false ou une condition de direction pour death."
                )
    sequences = animation.get("sequences", {})
    if not isinstance(sequences, dict):
        raise ValueError("'animation.sequences' doit etre un objet JSON.")
    for direction in ("left", "right", "death"):
        frames = sequences.get(direction, [])
        if not isinstance(frames, list):
            raise ValueError(f"'animation.sequences.{direction}' doit etre une liste.")
        for frame in frames:
            if (
                not isinstance(frame, dict)
                or any(
                    isinstance(frame.get(key), bool)
                    or not isinstance(frame.get(key), int)
                    or frame[key] < 0
                    for key in ("column", "row")
                )
            ):
                raise ValueError(
                    f"Chaque frame de '{direction}' doit definir une colonne "
                    "et une ligne positives ou nulles."
                )
    movement = entity["movement"]
    for key in ("speed", "range"):
        value = movement.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"'movement.{key}' doit etre un nombre.")
        if not math.isfinite(value):
            raise ValueError(f"'movement.{key}' doit etre fini.")
    waypoints = movement.get("waypoints")
    if not isinstance(waypoints, list):
        raise ValueError("'movement.waypoints' doit etre une liste JSON.")
    for point in waypoints:
        if (
            not isinstance(point, list)
            or len(point) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in point
            )
        ):
            raise ValueError("Chaque point de passage doit etre une paire de nombres.")
    steps = movement.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError("'movement.steps' doit etre une liste JSON.")
    for step in steps:
        if not isinstance(step, dict) or step.get("direction") not in (
            "left", "right", "up", "down"
        ):
            raise ValueError("Chaque pas doit definir une direction valide.")
        distance = step.get("steps")
        if (
            isinstance(distance, bool)
            or not isinstance(distance, (int, float))
            or not math.isfinite(distance)
            or distance <= 0
        ):
            raise ValueError("La distance de chaque pas doit etre positive.")
    for key in ("amount", "duration", "radius", "cooldown"):
        value = entity["effects"].get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"'effects.{key}' doit etre un nombre.")
        if not math.isfinite(value):
            raise ValueError(f"'effects.{key}' doit etre fini.")
    if not isinstance(entity.get("custom_data", {}), dict):
        raise ValueError("'custom_data' doit etre un objet JSON.")
    if not isinstance(entity.get("tags", []), list):
        raise ValueError("'tags' doit etre une liste JSON.")


def save_document(map_path, entities_path, entities):
    ids = set()
    for entity in entities:
        validate_entity(entity)
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or not entity_id:
            raise ValueError("Chaque entite doit avoir un identifiant.")
        if entity_id in ids:
            raise ValueError(f"Identifiant d'entite duplique : {entity_id}")
        ids.add(entity_id)

    destination = Path(entities_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "format_version": 1,
        "map": os.path.relpath(Path(map_path), destination.parent),
        "tile_size": TILE_SIZE,
        "entities": entities,
    }
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            suffix=".tmp",
            delete=False,
        ) as target:
            temp_path = Path(target.name)
            json.dump(document, target, ensure_ascii=False, indent=2)
            target.write("\n")
        temp_path.replace(destination)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


class LevelEntityEditor:
    def __init__(self, root, map_path):
        self.root = root
        self.root.title("Lost Cave - editeur d'entites")
        self.root.geometry("1600x950")
        self.root.minsize(1180, 720)
        self._configure_styles()
        self.map_path = None
        self.entities_path = None
        self.map_data = None
        self.entities = []
        self.selected_id = None
        self.placement_category = None
        self.dirty = False
        self.loading_form = False
        self.zoom = 1.0
        self.grid_visible = True
        self.snap_to_grid = True
        self.tile_sources = []
        self.tile_cache = {}
        self.sprite_cache = {}
        self.sprite_source_cache = {}
        self.image_refs = []
        self.frame_picker = None
        self.frame_picker_image = None
        self.frame_picker_canvas = None
        self.frame_picker_selected = None
        self.frame_picker_cell_size = (0, 0)
        self.frame_picker_columns = 0
        self.frame_picker_rows = 0
        self.variables = {}
        self.drag_id = None
        self.drag_offset = (0, 0)

        self._build_interface()
        self.open_map(map_path, confirm=False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._animate_sprites)

    def _configure_styles(self):
        """Apply a consistent, modern visual theme without changing editor behavior."""
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.colors = {
            "app": "#171b24",
            "panel": "#202633",
            "panel_alt": "#252d3b",
            "border": "#343e4e",
            "text": "#e8edf5",
            "muted": "#aab5c5",
            "accent": "#7c9cff",
            "accent_hover": "#9ab2ff",
            "input": "#171d27",
        }
        self.root.configure(background=self.colors["app"])
        style.configure(".", font=("Segoe UI", 10), background=self.colors["app"],
                        foreground=self.colors["text"])
        style.configure("TFrame", background=self.colors["app"])
        style.configure("Panel.TFrame", background=self.colors["panel"])
        style.configure("Toolbar.TFrame", background=self.colors["panel"], padding=(12, 10))
        style.configure("TLabel", background=self.colors["app"], foreground=self.colors["text"])
        style.configure("Heading.TLabel", font=("Segoe UI Semibold", 11),
                        foreground="#ffffff", background=self.colors["app"])
        style.configure("Muted.TLabel", foreground=self.colors["muted"])
        style.configure("TButton", padding=(10, 6), borderwidth=0,
                        background=self.colors["panel_alt"], foreground=self.colors["text"])
        style.map("TButton", background=[("active", self.colors["border"]),
                                        ("pressed", self.colors["accent"])],
                  foreground=[("disabled", self.colors["muted"])])
        style.configure("Accent.TButton", background=self.colors["accent"],
                        foreground="#101522", font=("Segoe UI Semibold", 10))
        style.map("Accent.TButton", background=[("active", self.colors["accent_hover"]),
                                                ("pressed", self.colors["accent"])])
        style.configure("TNotebook", background=self.colors["app"], borderwidth=0,
                        tabmargins=(2, 4, 2, 0))
        style.configure("TNotebook.Tab", padding=(10, 8), background=self.colors["panel"],
                        foreground=self.colors["muted"])
        style.map("TNotebook.Tab", background=[("selected", self.colors["panel_alt"])],
                  foreground=[("selected", "#ffffff")])
        style.configure("TEntry", padding=6, fieldbackground=self.colors["input"],
                        foreground=self.colors["text"], insertcolor=self.colors["text"])
        style.configure("TCombobox", padding=5, fieldbackground=self.colors["input"],
                        background=self.colors["panel_alt"], foreground=self.colors["text"])
        style.map("TCombobox", fieldbackground=[("readonly", self.colors["input"])],
                  foreground=[("readonly", self.colors["text"])])
        style.configure("TCheckbutton", background=self.colors["app"],
                        foreground=self.colors["text"], padding=(2, 4))
        style.map("TCheckbutton", background=[("active", self.colors["app"])])
        style.configure("TPanedwindow", background=self.colors["app"])
        style.configure("TSeparator", background=self.colors["border"])
        style.configure("TScrollbar", background=self.colors["panel_alt"],
                        troughcolor=self.colors["app"], borderwidth=0, arrowsize=12)

    def _build_interface(self):
        toolbar = ttk.Frame(self.root, style="Toolbar.TFrame")
        toolbar.pack(fill="x", padx=8, pady=(8, 10))
        ttk.Label(toolbar, text="LOST CAVE  /  ÉDITEUR D’ENTITÉS",
                  font=("Segoe UI Semibold", 11), background=self.colors["panel"],
                  foreground="#ffffff").pack(side="left", padx=(0, 18))
        ttk.Button(toolbar, text="Ouvrir une carte", command=self.choose_map).pack(
            side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Enregistrer  Ctrl+S", command=self.save,
                   style="Accent.TButton").pack(side="left", padx=(0, 12))
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        for label, command in (
            ("＋ Ennemi", lambda: self.start_placement("enemy")),
            ("＋ Objet", lambda: self.start_placement("item")),
            ("＋ Spécial", lambda: self.start_placement("special")),
            ("Supprimer", self.delete_selected),
        ):
            ttk.Button(toolbar, text=label, command=command).pack(
                side="left", padx=(0, 6))
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(toolbar, text="Grille", command=self.toggle_grid).pack(
            side="left", padx=5)
        ttk.Label(toolbar, text="Zoom", background=self.colors["panel"],
                  foreground=self.colors["muted"]).pack(side="left", padx=(12, 5))
        self.zoom_var = tk.StringVar(value="100 %")
        zoom_box = ttk.Combobox(
            toolbar,
            textvariable=self.zoom_var,
            values=("50 %", "100 %", "200 %"),
            width=8,
            state="readonly",
        )
        zoom_box.pack(side="left")
        zoom_box.bind("<<ComboboxSelected>>", self._zoom_changed)
        self.status_var = tk.StringVar(value="Pret")
        ttk.Label(toolbar, textvariable=self.status_var, background=self.colors["panel"],
                  foreground=self.colors["muted"]).pack(side="right", padx=8)

        panes = ttk.Panedwindow(self.root, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = ttk.Frame(panes, width=230, style="Panel.TFrame", padding=10)
        center = ttk.Frame(panes, padding=1)
        right = ttk.Frame(panes, width=430, style="Panel.TFrame", padding=10)
        panes.add(left, weight=0)
        panes.add(center, weight=1)
        panes.add(right, weight=0)
        left.pack_propagate(False)
        right.pack_propagate(False)

        self.entity_count_var = tk.StringVar(value="0 entité")
        ttk.Label(left, text="Entités du niveau", style="Heading.TLabel").pack(
            anchor="w", pady=(2, 2))
        ttk.Label(left, textvariable=self.entity_count_var, style="Muted.TLabel").pack(
            anchor="w", pady=(0, 10))
        self.entity_list = tk.Listbox(
            left, exportselection=False, relief="flat", borderwidth=0,
            background=self.colors["panel"], foreground=self.colors["text"],
            selectbackground=self.colors["accent"], selectforeground="#101522",
            activestyle="none", font=("Segoe UI", 10), highlightthickness=1,
            highlightbackground=self.colors["border"], highlightcolor=self.colors["accent"],
            selectborderwidth=0)
        list_scroll = ttk.Scrollbar(
            left, orient="vertical", command=self.entity_list.yview
        )
        self.entity_list.configure(yscrollcommand=list_scroll.set)
        self.entity_list.pack(side="left", fill="both", expand=True)
        list_scroll.pack(side="right", fill="y")
        self.entity_list.bind("<<ListboxSelect>>", self._list_selection_changed)

        self.canvas = tk.Canvas(
            center,
            background="#11151b",
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            scrollregion=(0, 0, 1, 1),
        )
        horizontal = ttk.Scrollbar(
            center, orient="horizontal", command=self.canvas.xview
        )
        vertical = ttk.Scrollbar(
            center, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(
            xscrollcommand=horizontal.set, yscrollcommand=vertical.set
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)
        self.canvas.bind("<Button-1>", self._canvas_down)
        self.canvas.bind("<B1-Motion>", self._canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._canvas_up)
        self.canvas.bind("<MouseWheel>", self._mouse_wheel)
        self.canvas.bind("<Button-4>", lambda event: self._mouse_wheel_linux(event, 1))
        self.canvas.bind("<Button-5>", lambda event: self._mouse_wheel_linux(event, -1))

        ttk.Label(right, text="Propriétés de l’entité", style="Heading.TLabel").pack(
            anchor="w", pady=(2, 10))
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self.forms = {}
        for key, title in (
            ("general", "Général"),
            ("hitbox", "Hitbox"),
            ("sprite", "Sprite"),
            ("movement", "Mouvement"),
            ("effects", "Effets"),
            ("advanced", "Avancé"),
        ):
            # A scrollable content area prevents long forms (sprite/movement/JSON)
            # from being clipped on smaller displays.
            tab = ttk.Frame(self.notebook)
            tab_canvas = tk.Canvas(
                tab, background=self.colors["app"], highlightthickness=0,
                borderwidth=0)
            tab_scroll = ttk.Scrollbar(tab, orient="vertical", command=tab_canvas.yview)
            tab_canvas.configure(yscrollcommand=tab_scroll.set)
            tab_canvas.pack(side="left", fill="both", expand=True)
            tab_scroll.pack(side="right", fill="y")
            frame = ttk.Frame(tab_canvas, padding=12)
            window_id = tab_canvas.create_window((0, 0), window=frame, anchor="nw")
            frame.bind(
                "<Configure>",
                lambda _event, canvas=tab_canvas: canvas.configure(
                    scrollregion=canvas.bbox("all")))
            tab_canvas.bind(
                "<Configure>",
                lambda event, canvas=tab_canvas, window=window_id:
                    canvas.itemconfigure(window, width=event.width))
            tab_canvas.bind("<MouseWheel>", lambda event, canvas=tab_canvas:
                            canvas.yview_scroll(int(-event.delta / 120), "units"))
            tab_canvas.bind("<Button-4>", lambda _event, canvas=tab_canvas:
                            canvas.yview_scroll(-1, "units"))
            tab_canvas.bind("<Button-5>", lambda _event, canvas=tab_canvas:
                            canvas.yview_scroll(1, "units"))
            self.notebook.add(tab, text=title)
            self.forms[key] = frame
        self._build_general_form()
        self._build_hitbox_form()
        self._build_sprite_form()
        self._build_movement_form()
        self._build_effects_form()
        self._build_advanced_form()

        self.root.bind("<Control-s>", lambda _event: self.save())
        self.root.bind("<Delete>", lambda _event: self.delete_selected())
        self.root.bind("<Escape>", self._cancel_placement)

    def _field(self, parent, row, key, label, value="", widget="entry", values=()):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", pady=3, padx=(0, 8)
        )
        variable = tk.BooleanVar(value=value) if widget == "check" else tk.StringVar(
            value=str(value)
        )
        self.variables[key] = variable
        variable.trace_add("write", self._property_modified)
        if widget == "check":
            control = ttk.Checkbutton(parent, variable=variable)
        elif widget == "combo":
            control = ttk.Combobox(
                parent,
                textvariable=variable,
                values=values,
                state="readonly",
            )
        else:
            control = ttk.Entry(parent, textvariable=variable)
        control.grid(row=row, column=1, sticky="ew", pady=3)
        parent.columnconfigure(1, weight=1)
        return control

    def _build_general_form(self):
        frame = self.forms["general"]
        for row, key, label, value in (
            (0, "name", "Nom", ""),
            (1, "category", "Categorie", "enemy"),
            (2, "x", "Position X (px)", "0"),
            (3, "y", "Position Y (px)", "0"),
            (4, "width", "Largeur (px)", "32"),
            (5, "height", "Hauteur (px)", "32"),
            (6, "layer", "Profondeur", "0"),
            (7, "tags", "Tags (JSON)", "[]"),
        ):
            widget = "combo" if key == "category" else "entry"
            values = ENTITY_CATEGORIES if key == "category" else ()
            self._field(frame, row, key, label, value, widget, values)
        for row, key, label in (
            (8, "visible", "Visible dans le niveau"),
            (9, "enabled", "Actif"),
            (10, "collision", "Collision active"),
            (11, "snap", "Aligner sur la grille"),
            (12, "killable", "Ennemi tuable par un saut"),
        ):
            self._field(frame, row, key, label, True, "check")
        self.variables["snap"].set(True)
        ttk.Label(
            frame,
            text="Cliquez sur la carte pour placer une entite. Faites-la glisser pour la deplacer.",
            wraplength=310,
        ).grid(row=13, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _build_hitbox_form(self):
        frame = self.forms["hitbox"]
        for row, key, label, value in (
            (0, "hitbox_x", "Decalage X (px)", "4"),
            (1, "hitbox_y", "Decalage Y (px)", "16"),
            (2, "hitbox_width", "Largeur (px)", "24"),
            (3, "hitbox_height", "Hauteur (px)", "16"),
        ):
            self._field(frame, row, key, label, value)
        ttk.Label(
            frame,
            text="La hitbox est relative au coin superieur gauche du sprite. "
            "Elle est affichee en cyan sur la carte.",
            wraplength=310,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _build_sprite_form(self):
        frame = self.forms["sprite"]
        self._field(frame, 0, "sprite", "Image / spritesheet")
        ttk.Button(frame, text="Choisir une image...", command=self.choose_sprite).grid(
            row=0, column=2, padx=(5, 0)
        )
        self._field(frame, 1, "frame_width", "Largeur de frame", "32")
        self._field(frame, 2, "frame_height", "Hauteur de frame", "32")
        self._field(frame, 3, "columns", "Colonnes", "1")
        self._field(frame, 4, "frame_count", "Nombre de frames", "1")
        self._field(frame, 5, "row", "Ligne de frames", "0")
        self._field(frame, 6, "frame_delay_ms", "Delai entre frames (ms)", "125")
        self._field(frame, 7, "offset_x", "Decalage X", "0")
        self._field(frame, 8, "offset_y", "Decalage Y", "0")
        self._field(frame, 9, "loop", "Boucler l'animation", True, "check")
        self._field(frame, 10, "flip_x", "Retourner horizontalement", False, "check")
        self._field(frame, 11, "flip_y", "Retourner verticalement", False, "check")
        ttk.Label(frame, text="Apercu anime").grid(
            row=12, column=0, columnspan=3, sticky="w", pady=(12, 3)
        )
        self.sprite_preview = tk.Canvas(
            frame, width=230, height=125, background=self.colors["input"],
            highlightthickness=1, highlightbackground=self.colors["border"]
        )
        self.sprite_preview.grid(row=13, column=0, columnspan=3, sticky="ew")
        ttk.Label(frame, text="Animations par direction").grid(
            row=14, column=0, columnspan=3, sticky="w", pady=(10, 3)
        )
        self.animation_sequence_var = tk.StringVar(value="right")
        self._loaded_animation_direction = "right"
        sequence_box = ttk.Combobox(
            frame,
            textvariable=self.animation_sequence_var,
            values=("left", "right", "death"),
            state="readonly",
        )
        sequence_box.grid(row=15, column=0, columnspan=3, sticky="ew")
        sequence_box.bind(
            "<<ComboboxSelected>>", self._animation_sequence_changed
        )
        self.animation_frames_list = tk.Listbox(
            frame, height=4, exportselection=False
        )
        self.animation_frames_list.grid(
            row=16, column=0, columnspan=3, sticky="ew", pady=(4, 4)
        )
        animation_controls = ttk.Frame(frame)
        animation_controls.grid(row=17, column=0, columnspan=3, sticky="ew")
        ttk.Button(
            animation_controls,
            text="Parcourir le spritesheet...",
            command=self.open_frame_picker,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(
            animation_controls, text="Ajouter frame", command=self.add_animation_frame
        ).grid(row=0, column=1, sticky="ew")
        ttk.Button(
            animation_controls,
            text="Supprimer",
            command=self.delete_animation_frame,
        ).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(4, 0))
        ttk.Button(
            animation_controls, text="Monter", command=lambda: self.move_animation_frame(-1)
        ).grid(row=1, column=1, sticky="ew", pady=(4, 0))
        ttk.Button(
            animation_controls, text="Descendre", command=lambda: self.move_animation_frame(1)
        ).grid(row=1, column=2, sticky="ew", pady=(4, 0))
        animation_controls.columnconfigure(0, weight=1)
        animation_controls.columnconfigure(1, weight=1)
        animation_controls.columnconfigure(2, weight=1)
        ttk.Label(
            frame,
            text="Choisissez une sequence, puis cliquez sur des cases du spritesheet "
            "pour ajouter ses frames dans l'ordre.",
            wraplength=310,
        ).grid(row=18, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Separator(frame, orient="horizontal").grid(
            row=19, column=0, columnspan=3, sticky="ew", pady=(12, 8)
        )
        ttk.Label(
            frame, text="Réglages propres à cette séquence",
            style="Heading.TLabel",
        ).grid(row=20, column=0, columnspan=3, sticky="w")
        ttk.Label(
            frame,
            text="Laissez le délai vide pour reprendre le délai global. Pour le retournement, "
            "« Global » reprend les cases Retourner X/Y ci-dessus ; Oui/Non force la valeur "
            "uniquement pour cette séquence. Pour « death », vous pouvez aussi conditionner "
            "le retournement à la direction de l’ennemi.",
            wraplength=310, justify="left",
        ).grid(row=21, column=0, columnspan=3, sticky="w", pady=(3, 8))
        ttk.Label(frame, text="Délai entre frames (ms), vide = global").grid(
            row=22, column=0, columnspan=2, sticky="w"
        )
        self.direction_delay_var = tk.StringVar(value="")
        self.direction_delay_entry = ttk.Entry(
            frame, textvariable=self.direction_delay_var, width=12
        )
        self.direction_delay_entry.grid(row=22, column=2, sticky="ew", padx=(4, 0))
        ttk.Label(frame, text="Retournement horizontal (X)").grid(
            row=23, column=0, columnspan=2, sticky="w", pady=(5, 0)
        )
        self.direction_flip_x_var = tk.StringVar(value="Global")
        self.direction_flip_x_combo = ttk.Combobox(
            frame, textvariable=self.direction_flip_x_var,
            values=("Global", "Oui", "Non"), state="readonly", width=12,
        )
        self.direction_flip_x_combo.grid(row=23, column=2, sticky="ew", padx=(4, 0), pady=(5, 0))
        ttk.Label(frame, text="Retournement vertical (Y)").grid(
            row=24, column=0, columnspan=2, sticky="w", pady=(5, 0)
        )
        self.direction_flip_y_var = tk.StringVar(value="Global")
        self.direction_flip_y_combo = ttk.Combobox(
            frame, textvariable=self.direction_flip_y_var,
            values=("Global", "Oui", "Non"), state="readonly", width=12,
        )
        self.direction_flip_y_combo.grid(row=24, column=2, sticky="ew", padx=(4, 0), pady=(5, 0))
        frame.columnconfigure(2, weight=1)

    def _build_movement_form(self):
        frame = self.forms["movement"]
        self._field(
            frame, 0, "movement_type", "Mode",
            "stationary", "combo",
            ("stationary", "patrol", "horizontal", "vertical", "loop", "steps", "follow", "path", "projectile", "custom"),
        )
        self._field(frame, 1, "axis", "Axe", "x", "combo", ("x", "y"))
        self._field(frame, 2, "speed", "Vitesse", "1.0")
        self._field(frame, 3, "range", "Portee / distance", "96")
        self._field(frame, 4, "waypoints", "Points (JSON)", "[]")
        self._field(frame, 5, "gravity", "Appliquer la gravite", False, "check")
        self._field(frame, 6, "bounce", "Rebondir aux limites", False, "check")
        self._field(
            frame, 7, "facing", "Orientation", "right",
            "combo", ("left", "right", "up", "down"),
        )
        ttk.Label(
            frame,
            text="Les points du chemin sont des positions en pixels, ex. [[320, 192], [480, 192]].",
            wraplength=310,
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Label(
            frame,
            text="Loop : avance depuis la position de depart puis revient au debut "
            "quand la distance indiquee est atteinte.",
            wraplength=310,
        ).grid(row=10, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Separator(frame, orient="horizontal").grid(
            row=11, column=0, columnspan=2, sticky="ew", pady=10
        )
        ttk.Label(frame, text="Sequence de pas (repetee en boucle)").grid(
            row=12, column=0, columnspan=2, sticky="w"
        )
        self.movement_steps_list = tk.Listbox(frame, height=5, exportselection=False)
        self.movement_steps_list.grid(
            row=13, column=0, columnspan=2, sticky="nsew", pady=(4, 6)
        )
        self.movement_steps_list.bind(
            "<<ListboxSelect>>", self._movement_step_selected
        )
        row_controls = ttk.Frame(frame)
        row_controls.grid(row=14, column=0, columnspan=2, sticky="ew")
        ttk.Label(row_controls, text="Direction").grid(row=0, column=0, sticky="w")
        self._field(
            row_controls, 0, "step_direction", "",
            "right", "combo", ("left", "right", "up", "down"),
        )
        ttk.Label(row_controls, text="Pas (px)").grid(row=1, column=0, sticky="w")
        self._field(row_controls, 1, "step_count", "", "32")
        for column, (label, command) in enumerate((
            ("Ajouter", self.add_movement_step),
            ("Modifier", self.update_movement_step),
            ("Supprimer", self.delete_movement_step),
        )):
            ttk.Button(row_controls, text=label, command=command).grid(
                row=2, column=column, sticky="ew", padx=(0, 4), pady=(5, 0)
            )
        for column, (label, offset) in enumerate((("Monter", -1), ("Descendre", 1))):
            ttk.Button(
                row_controls,
                text=label,
                command=lambda amount=offset: self.move_movement_step(amount),
            ).grid(row=3, column=column, sticky="ew", padx=(0, 4), pady=4)
        row_controls.columnconfigure(1, weight=1)
        ttk.Label(
            frame,
            text="Comme Scratch : 1 pas = 1 pixel. La vitesse indique le nombre "
            "de pixels parcourus par frame.",
            wraplength=310,
        ).grid(row=15, column=0, columnspan=2, sticky="w")

        ttk.Separator(frame, orient="horizontal").grid(
            row=16, column=0, columnspan=2, sticky="ew", pady=12
        )
        ttk.Label(
            frame, text="Animation pendant le déplacement",
            style="Heading.TLabel",
        ).grid(row=17, column=0, columnspan=2, sticky="w")
        ttk.Label(
            frame,
            text="Le mouvement règle le trajet. Les images animées se configurent "
            "dans l’onglet Sprite : une séquence pour la gauche et une pour la droite.",
            wraplength=310, justify="left",
        ).grid(row=18, column=0, columnspan=2, sticky="w", pady=(4, 8))
        self.movement_animation_status = tk.StringVar(
            value="Gauche : 0 image(s)   •   Droite : 0 image(s)"
        )
        ttk.Label(
            frame, textvariable=self.movement_animation_status,
        ).grid(row=19, column=0, columnspan=2, sticky="w", pady=(0, 6))
        animation_buttons = ttk.Frame(frame)
        animation_buttons.grid(row=20, column=0, columnspan=2, sticky="ew")
        ttk.Button(
            animation_buttons, text="Configurer l’animation gauche",
            command=lambda: self._open_animation_editor("left"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(
            animation_buttons, text="Configurer l’animation droite",
            command=lambda: self._open_animation_editor("right"),
        ).grid(row=0, column=1, sticky="ew")
        animation_buttons.columnconfigure(0, weight=1)
        animation_buttons.columnconfigure(1, weight=1)
        ttk.Label(
            frame,
            text="Étapes : 1) choisissez une image dans Sprite ; 2) ouvrez le "
            "spritesheet ; 3) cliquez les cases dans l’ordre ; 4) ajoutez-les à "
            "la séquence gauche ou droite. Une séquence vide n’a aucune frame dédiée.",
            wraplength=310, justify="left",
        ).grid(row=21, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _build_effects_form(self):
        frame = self.forms["effects"]
        self._field(
            frame, 0, "trigger", "Declencheur",
            "contact", "combo",
            ("contact", "collect", "proximity", "timer", "interact", "destroy"),
        )
        self._field(
            frame, 1, "action", "Effet",
            "damage", "combo",
            ("none", "damage", "heal", "slow", "poison", "knockback", "checkpoint", "teleport", "custom"),
        )
        self._field(frame, 2, "amount", "Valeur / degats", "1")
        self._field(frame, 3, "duration", "Duree (frames)", "0")
        self._field(frame, 4, "radius", "Rayon (px)", "0")
        self._field(frame, 5, "cooldown", "Recharge (frames)", "0")
        self._field(frame, 6, "one_shot", "Ne se declenche qu'une fois", False, "check")
        self._field(frame, 7, "sound", "Son (fichier)")
        self._field(frame, 8, "target", "Cible", "player", "combo", ("player", "enemy", "all", "self"))

    def _build_advanced_form(self):
        frame = self.forms["advanced"]
        ttk.Label(
            frame,
            text="Donnees additionnelles : un objet JSON libre conserve vos options personnalisees.",
            wraplength=310,
        ).pack(anchor="w", pady=(0, 6))
        self.custom_data_text = tk.Text(frame, height=8, wrap="none")
        self.custom_data_text.pack(fill="both", expand=True)
        self.custom_data_text.bind("<<Modified>>", self._text_modified)
        ttk.Label(frame, text="Entite JSON complete").pack(anchor="w", pady=(8, 3))
        self.advanced_text = tk.Text(frame, height=14, wrap="none")
        self.advanced_text.pack(fill="both", expand=True)
        self.advanced_text.bind("<<Modified>>", self._text_modified)
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(5, 0))
        ttk.Button(
            buttons,
            text="Appliquer le JSON complet",
            command=self.apply_advanced_json,
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Actualiser",
            command=self.refresh_advanced_json,
        ).pack(side="left", padx=5)

    def open_map(self, map_path, confirm=True):
        if confirm and not self._confirm_discard():
            return
        loaded = load_document(map_path)
        self.map_path, self.entities_path, self.map_data, self.entities = loaded
        self.selected_id = None
        self.placement_category = None
        self.tile_sources = []
        self.tile_cache.clear()
        self.sprite_cache.clear()
        self.sprite_source_cache.clear()
        self._load_tilesets()
        self._refresh_list()
        self._clear_form()
        self.dirty = False
        self._update_title()
        self._render_canvas()
        width, height = self.map_data["width"], self.map_data["height"]
        self.status_var.set(
            f"{self.map_path.name} - {width} x {height} cases - "
            f"{len(self.entities)} entite(s)"
        )

    def _load_tilesets(self):
        self.tile_sources = []
        for tile_set in self.map_data.get("tilesets", []):
            external_path = None
            if tile_set.get("source"):
                external_path = (self.map_path.parent / tile_set["source"]).resolve()
                xml = ET.parse(external_path).getroot()
                image_element = xml.find("image")
                if image_element is None:
                    raise ValueError(f"Aucune image de tuiles dans {external_path}.")
                image_path = (external_path.parent / image_element.get("source", "")).resolve()
                tile_set = {
                    **tile_set,
                    "tilewidth": int(xml.get("tilewidth", TILE_SIZE)),
                    "tileheight": int(xml.get("tileheight", TILE_SIZE)),
                    "columns": int(xml.get("columns", 1)),
                    "tilecount": int(xml.get("tilecount", 0)),
                    "margin": int(xml.get("margin", 0)),
                    "spacing": int(xml.get("spacing", 0)),
                    "image": os.path.relpath(image_path, self.map_path.parent),
                }
            else:
                image_path = (self.map_path.parent / tile_set["image"]).resolve()
            if not image_path.is_file():
                raise FileNotFoundError(f"Image de tuiles introuvable : {image_path}")
            source = tk.PhotoImage(master=self.root, file=str(image_path))
            tile_set = dict(tile_set)
            tile_set["_source"] = source
            tile_set["_tile_width"] = int(tile_set.get("tilewidth", TILE_SIZE))
            tile_set["_tile_height"] = int(tile_set.get("tileheight", TILE_SIZE))
            self.tile_sources.append(tile_set)

    def _image_at_zoom(self, image, zoom):
        if zoom == 2.0:
            return image.zoom(2)
        if zoom == 0.5:
            return image.subsample(2)
        return image

    def _tile_image(self, gid):
        key = (gid, self.zoom)
        if key in self.tile_cache:
            return self.tile_cache[key]
        for tile_set in self.tile_sources:
            firstgid = int(tile_set.get("firstgid", 1))
            count = int(tile_set.get("tilecount", 0))
            if not firstgid <= gid < firstgid + count:
                continue
            tile_width = tile_set["_tile_width"]
            tile_height = tile_set["_tile_height"]
            tile_id = gid - firstgid
            columns = int(tile_set.get("columns", 1))
            margin = int(tile_set.get("margin", 0))
            spacing = int(tile_set.get("spacing", 0))
            x = margin + (tile_id % columns) * (tile_width + spacing)
            y = margin + (tile_id // columns) * (tile_height + spacing)
            crop = tk.PhotoImage(
                master=self.root, width=tile_width, height=tile_height
            )
            crop.tk.call(
                str(crop),
                "copy",
                tile_set["_source"],
                "-from",
                x,
                y,
                x + tile_width,
                y + tile_height,
            )
            result = self._image_at_zoom(crop, self.zoom)
            self.tile_cache[key] = result
            return result
        raise ValueError(f"Identifiant de tuile {gid} absent des tilesets de la carte.")

    def _render_canvas(self):
        if not self.map_data:
            return
        self.canvas.delete("all")
        self.image_refs = []
        self.tile_cache.clear()
        tile_width = int(TILE_SIZE * self.zoom)
        map_width = self.map_data["width"]
        map_height = self.map_data["height"]
        for layer in self.map_data.get("layers", []):
            if layer.get("type") != "tilelayer" or not layer.get("visible", True):
                continue
            if layer.get("name", "").lower() in COLLISION_LAYERS:
                continue
            data = layer.get("data", [])
            if not isinstance(data, list):
                raise ValueError(
                    f"Le calque '{layer.get('name')}' doit contenir des GID en liste."
                )
            if len(data) != map_width * map_height:
                raise ValueError(
                    f"Le calque '{layer.get('name')}' ne correspond pas aux dimensions de la carte."
                )
            for index, gid in enumerate(data):
                gid = int(gid) & 0x1FFFFFFF
                if not gid:
                    continue
                image = self._tile_image(gid)
                x = (index % map_width) * tile_width
                y = (index // map_width) * tile_width
                self.canvas.create_image(x, y, image=image, anchor="nw", tags=("map",))
                self.image_refs.append(image)

        pixel_width = map_width * tile_width
        pixel_height = map_height * tile_width
        if self.grid_visible:
            grid_color = "#3c444e"
            for x in range(0, pixel_width + 1, tile_width):
                self.canvas.create_line(x, 0, x, pixel_height, fill=grid_color, tags=("grid",))
            for y in range(0, pixel_height + 1, tile_width):
                self.canvas.create_line(0, y, pixel_width, y, fill=grid_color, tags=("grid",))
        self._draw_entities()
        self.canvas.configure(scrollregion=(0, 0, pixel_width, pixel_height))

    def _draw_entities(self):
        self.canvas.delete("entity")
        self.image_refs = []
        for entity in sorted(self.entities, key=lambda item: item.get("layer", 0)):
            if not entity.get("visible", True):
                continue
            self._draw_entity(entity)

    def _draw_entity(self, entity):
        scale = self.zoom
        x = float(entity.get("x", 0)) * scale
        y = float(entity.get("y", 0)) * scale
        width = max(12, float(entity.get("width", TILE_SIZE)) * scale)
        height = max(12, float(entity.get("height", TILE_SIZE)) * scale)
        entity_id = entity["id"]
        tag = f"entity:{entity_id}"
        color = ENTITY_COLORS[entity.get("category", "special")]
        selected = entity_id == self.selected_id
        self._draw_movement(entity, x, y, width, height)
        image = self._entity_sprite(entity, 0)
        if image is not None:
            animation = entity.get("animation", {})
            self.canvas.create_image(
                x + width / 2 + float(animation.get("offset_x", 0)) * scale,
                y + height / 2 + float(animation.get("offset_y", 0)) * scale,
                image=image,
                anchor="center",
                tags=("entity", tag, f"entity-sprite:{entity_id}"),
            )
            self.image_refs.append(image)
        else:
            self.canvas.create_rectangle(
                x, y, x + width, y + height,
                fill=color,
                outline="#ffffff" if selected else "#20252d",
                width=2 if selected else 1,
                tags=("entity", tag),
            )
            self.canvas.create_text(
                x + width / 2,
                y + height / 2,
                text=CATEGORY_LABELS.get(entity.get("category"), "?")[0],
                fill="#172027",
                font=("TkDefaultFont", 10, "bold"),
                tags=("entity", tag),
            )
        if selected:
            hitbox = entity.get("hitbox", {})
            hitbox_x = x + float(hitbox.get("x", 0)) * scale
            hitbox_y = y + float(hitbox.get("y", 0)) * scale
            hitbox_width = float(hitbox.get("width", entity.get("width", TILE_SIZE))) * scale
            hitbox_height = float(hitbox.get("height", entity.get("height", TILE_SIZE))) * scale
            self.canvas.create_rectangle(
                hitbox_x,
                hitbox_y,
                hitbox_x + hitbox_width,
                hitbox_y + hitbox_height,
                outline="#47e5d1",
                width=2,
                dash=(4, 2),
                tags=("entity", tag),
            )
            self.canvas.create_rectangle(
                x - 2, y - 2, x + width + 2, y + height + 2,
                outline="#ffffff",
                width=2,
                dash=(4, 2),
                tags=("entity", tag),
            )
        self.canvas.create_text(
            x + width / 2,
            y - 5,
            text=entity.get("name", "Entite"),
            fill="#ffffff",
            anchor="s",
            font=("TkDefaultFont", 8, "bold"),
            tags=("entity", tag),
        )

    def _draw_movement(self, entity, x, y, width, height):
        movement = entity.get("movement", {})
        mode = movement.get("type", "stationary")
        color = ENTITY_COLORS.get(entity.get("category"), "#ffffff")
        center_x, center_y = x + width / 2, y + height / 2
        if mode in ("patrol", "horizontal", "vertical"):
            distance = max(0, float(movement.get("range", 0)) * self.zoom) / 2
            if movement.get("axis", "x") == "y" or mode == "vertical":
                self.canvas.create_line(
                    center_x, center_y - distance, center_x, center_y + distance,
                    fill=color, dash=(4, 3), arrow="both", tags=("entity",),
                )
            else:
                self.canvas.create_line(
                    center_x - distance, center_y, center_x + distance, center_y,
                    fill=color, dash=(4, 3), arrow="both", tags=("entity",),
                )
        points = movement.get("waypoints", [])
        if mode == "path" and isinstance(points, list) and len(points) > 1:
            scaled = [(float(point[0]) * self.zoom, float(point[1]) * self.zoom)
                      for point in points if isinstance(point, list) and len(point) == 2]
            if len(scaled) > 1:
                self.canvas.create_line(
                    *[coordinate for point in scaled for coordinate in point],
                    fill=color, dash=(3, 2), tags=("entity",),
                )
        radius = max(0, float(entity.get("effects", {}).get("radius", 0)) * self.zoom)
        if radius > 0:
            self.canvas.create_oval(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                outline=color, dash=(2, 3), tags=("entity",),
            )

    def _entity_sprite(self, entity, frame_number):
        sprite = entity.get("sprite", "")
        if not sprite:
            return None
        path = self._resolve_asset(sprite)
        if not path.is_file():
            return None
        animation = entity.get("animation", {})
        try:
            modified = path.stat().st_mtime_ns
            frame_width = int(animation.get("frame_width", TILE_SIZE))
            frame_height = int(animation.get("frame_height", TILE_SIZE))
            columns = max(1, int(animation.get("columns", 1)))
            count = max(1, int(animation.get("frame_count", 1)))
            if frame_width <= 0 or frame_height <= 0:
                return None
            sequences = animation.get("sequences", {})
            sequence_direction = "right" if sequences.get("right") else "left"
            sequence = sequences.get(sequence_direction) or []
            direction_settings = animation.get("direction_settings", {}).get(sequence_direction, {})
            flip_x = animation.get("flip_x", False)
            flip_y = animation.get("flip_y", False)
            if direction_settings.get("flip_x") is not None:
                flip_x = direction_settings["flip_x"]
            if direction_settings.get("flip_y") is not None:
                flip_y = direction_settings["flip_y"]
            if sequence:
                selected = sequence[frame_number % len(sequence)]
                column, row = selected["column"], selected["row"]
                frame = frame_number % len(sequence)
            else:
                frame = frame_number % count if animation.get("loop", True) else min(frame_number, count - 1)
                column = frame % columns
                row = int(animation.get("row", 0)) + frame // columns
            cache_key = (
                str(path),
                modified,
                frame_width,
                frame_height,
                columns,
                count,
                row,
                frame,
                tuple((item["column"], item["row"]) for item in sequence),
                self.zoom,
                bool(flip_x),
                bool(flip_y),
            )
            if cache_key in self.sprite_cache:
                return self.sprite_cache[cache_key]
            source_key = (str(path), modified)
            source = self.sprite_source_cache.get(source_key)
            if source is None:
                source = tk.PhotoImage(master=self.root, file=str(path))
                self.sprite_source_cache[source_key] = source
            crop = tk.PhotoImage(
                master=self.root, width=frame_width, height=frame_height
            )
            crop.tk.call(
                str(crop),
                "copy",
                source,
                "-from",
                column * frame_width,
                row * frame_height,
                (column + 1) * frame_width,
                (row + 1) * frame_height,
            )
            result = self._image_at_zoom(crop, self.zoom)
            if flip_x:
                result = self._flip_image(result, horizontal=True)
            if flip_y:
                result = self._flip_image(result, horizontal=False)
            self.sprite_cache[cache_key] = result
            return result
        except (tk.TclError, ValueError, OSError):
            return None

    def _flip_image(self, image, horizontal):
        width, height = image.width(), image.height()
        flipped = tk.PhotoImage(master=self.root, width=width, height=height)
        for y in range(height):
            for x in range(width):
                sx = width - x - 1 if horizontal else x
                sy = y if horizontal else height - y - 1
                if image.transparency_get(sx, sy):
                    flipped.transparency_set(x, y, True)
                    continue
                color = image.get(sx, sy)
                if isinstance(color, tuple):
                    color = "#%02x%02x%02x" % color[:3]
                flipped.put(str(color), (x, y))
        return flipped

    def _resolve_asset(self, value):
        path = Path(value)
        return path.resolve() if path.is_absolute() else (ROOT / path).resolve()

    def _animate_sprites(self):
        if not self.root.winfo_exists():
            return
        now = int(self.root.winfo_toplevel().tk.call("clock", "milliseconds"))
        for entity in self.entities:
            animation = entity.get("animation", {})
            sequences = animation.get("sequences", {})
            sequence_direction = "right" if sequences.get("right") else "left"
            frames = sequences.get(sequence_direction) or []
            if frames:
                direction_settings = animation.get("direction_settings", {}).get(sequence_direction, {})
                delay_value = direction_settings.get("frame_delay_ms")
                if delay_value is None:
                    delay_value = animation.get("frame_delay_ms", 125)
                delay = max(1, float(delay_value))
                frame = int(now / delay) % len(frames)
            else:
                count = max(1, int(animation.get("frame_count", 1)))
                fps = max(0.1, float(animation.get("fps", 8)))
                frame = int(now * fps / 1000) % count
            image = self._entity_sprite(entity, frame)
            if image is None:
                continue
            for item in self.canvas.find_withtag(f"entity-sprite:{entity['id']}"):
                self.canvas.itemconfigure(item, image=image)
        self.root.after(100, self._animate_sprites)

    def _refresh_list(self):
        self.entity_list.delete(0, "end")
        self.entity_count_var.set(
            f"{len(self.entities)} entité{'s' if len(self.entities) != 1 else ''}")
        for entity in self.entities:
            category = CATEGORY_LABELS.get(entity.get("category"), "Entité")
            label = (f"{category}  ·  {entity.get('name', 'Sans nom')}  "
                     f"({entity.get('x', 0)}, {entity.get('y', 0)})")
            self.entity_list.insert("end", label)
            self.entity_list.itemconfig(
                "end", foreground=ENTITY_COLORS.get(entity.get("category"), self.colors["text"]))
        if self.selected_id:
            for index, entity in enumerate(self.entities):
                if entity["id"] == self.selected_id:
                    self.entity_list.selection_set(index)
                    self.entity_list.see(index)
                    break

    def _clear_form(self):
        self.loading_form = True
        for key, variable in self.variables.items():
            if isinstance(variable, tk.BooleanVar):
                variable.set(key == "snap")
            else:
                variable.set("")
        self.custom_data_text.delete("1.0", "end")
        self.custom_data_text.insert("1.0", "{}")
        self.custom_data_text.edit_modified(False)
        self.advanced_text.delete("1.0", "end")
        self.advanced_text.edit_modified(False)
        self.loading_form = False
        self.sprite_preview.delete("all")
        self.animation_frames_list.delete(0, "end")

    def _select_entity(self, entity_id):
        if not self._save_current_form():
            return False
        self.selected_id = entity_id
        entity = self._entity_by_id(entity_id)
        if entity is None:
            self._clear_form()
            return True
        self.loading_form = True
        values = {
            "name": entity.get("name", ""),
            "category": entity.get("category", "enemy"),
            "x": entity.get("x", 0),
            "y": entity.get("y", 0),
            "width": entity.get("width", TILE_SIZE),
            "height": entity.get("height", TILE_SIZE),
            "layer": entity.get("layer", 0),
            "tags": json.dumps(entity.get("tags", []), ensure_ascii=False),
            "visible": entity.get("visible", True),
            "enabled": entity.get("enabled", True),
            "collision": entity.get("collision", True),
            "killable": entity.get("killable", False),
            "hitbox_x": entity["hitbox"]["x"],
            "hitbox_y": entity["hitbox"]["y"],
            "hitbox_width": entity["hitbox"]["width"],
            "hitbox_height": entity["hitbox"]["height"],
            "step_direction": "right",
            "step_count": 32,
            "snap": self.snap_to_grid,
            "sprite": entity.get("sprite", ""),
        }
        for section, fields in (
            ("animation", ("frame_width", "frame_height", "columns", "frame_count", "row", "frame_delay_ms", "loop", "offset_x", "offset_y", "flip_x", "flip_y")),
            ("movement", ("movement_type", "axis", "speed", "range", "waypoints", "gravity", "bounce", "facing")),
            ("effects", ("trigger", "action", "amount", "duration", "radius", "cooldown", "one_shot", "sound", "target")),
        ):
            source = entity[section] if section in entity else {}
            for field in fields:
                data_key = "type" if field == "movement_type" else field
                value = source.get(data_key, "")
                if field == "waypoints":
                    value = json.dumps(value, ensure_ascii=False)
                values[field] = value
        for key, value in values.items():
            if key in self.variables:
                self.variables[key].set(value)
        self.animation_sequence_var.set("right")
        self._loaded_animation_direction = "right"
        self._load_direction_settings(entity, "right")
        self._refresh_movement_steps(entity)
        self._refresh_animation_frames(entity)
        self._update_movement_animation_status(entity)
        self.custom_data_text.delete("1.0", "end")
        self.custom_data_text.insert(
            "1.0", json.dumps(entity.get("custom_data", {}), ensure_ascii=False, indent=2)
        )
        self.custom_data_text.edit_modified(False)
        self.loading_form = False
        self.refresh_advanced_json()
        self._refresh_list()
        self._draw_entities()
        self._refresh_sprite_preview()
        self._refresh_frame_picker()
        return True

    def _save_current_form(self):
        entity = self._entity_by_id(self.selected_id)
        if entity is None or self.loading_form:
            return True
        try:
            entity["name"] = self.variables["name"].get().strip()
            entity["category"] = self.variables["category"].get()
            for key in ("x", "y", "width", "height", "layer"):
                entity[key] = float(self.variables[key].get())
                if entity[key].is_integer():
                    entity[key] = int(entity[key])
            entity["hitbox"] = {
                "x": float(self.variables["hitbox_x"].get()),
                "y": float(self.variables["hitbox_y"].get()),
                "width": float(self.variables["hitbox_width"].get()),
                "height": float(self.variables["hitbox_height"].get()),
            }
            for key, value in tuple(entity["hitbox"].items()):
                if value.is_integer():
                    entity["hitbox"][key] = int(value)
            entity["killable"] = self.variables["killable"].get()
            entity["visible"] = self.variables["visible"].get()
            entity["enabled"] = self.variables["enabled"].get()
            entity["collision"] = self.variables["collision"].get()
            entity["tags"] = json.loads(self.variables["tags"].get() or "[]")
            entity["sprite"] = self.variables["sprite"].get().strip()
            for key in ("frame_width", "frame_height", "columns", "frame_count", "row", "offset_x", "offset_y"):
                entity["animation"][key] = int(self.variables[key].get() or 0)
            delay = float(self.variables["frame_delay_ms"].get() or 0)
            entity["animation"]["frame_delay_ms"] = delay
            entity["animation"]["fps"] = 1000 / delay if delay > 0 else 0
            for key in ("loop", "flip_x", "flip_y"):
                entity["animation"][key] = self.variables[key].get()
            self._save_direction_settings(entity, self._loaded_animation_direction)
            entity["movement"].update({
                "type": self.variables["movement_type"].get(),
                "axis": self.variables["axis"].get(),
                "speed": float(self.variables["speed"].get()),
                "range": float(self.variables["range"].get()),
                "waypoints": json.loads(self.variables["waypoints"].get() or "[]"),
                "gravity": self.variables["gravity"].get(),
                "bounce": self.variables["bounce"].get(),
                "facing": self.variables["facing"].get(),
            })
            self._save_movement_steps(entity)
            for key in ("amount", "duration", "radius", "cooldown"):
                entity["effects"][key] = float(self.variables[key].get() or 0)
            for key in ("trigger", "action", "sound", "target"):
                entity["effects"][key] = self.variables[key].get()
            entity["effects"]["one_shot"] = self.variables["one_shot"].get()
            entity["custom_data"] = json.loads(
                self.custom_data_text.get("1.0", "end-1c") or "{}"
            )
            self.snap_to_grid = self.variables["snap"].get()
            validate_entity(entity)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            messagebox.showerror("Proprietes invalides", str(error), parent=self.root)
            return False
        self._refresh_list()
        self.dirty = True
        self._update_title()
        self._draw_entities()
        self._refresh_sprite_preview()
        self._refresh_frame_picker()
        return True

    def _list_selection_changed(self, _event):
        selection = self.entity_list.curselection()
        if not selection:
            return
        index = selection[0]
        if index < len(self.entities):
            self._select_entity(self.entities[index]["id"])

    def _entity_by_id(self, entity_id):
        return next((entity for entity in self.entities if entity["id"] == entity_id), None)

    def _update_movement_animation_status(self, entity=None):
        entity = entity or self._entity_by_id(self.selected_id)
        if entity is None or not hasattr(self, "movement_animation_status"):
            return
        sequences = entity.get("animation", {}).get("sequences", {})
        left_count = len(sequences.get("left", []))
        right_count = len(sequences.get("right", []))
        self.movement_animation_status.set(
            f"Gauche : {left_count} image(s)   •   Droite : {right_count} image(s)"
        )

    def _open_animation_editor(self, direction):
        if not self._save_current_form():
            return
        if direction not in ("left", "right"):
            return
        sprite_tab = self.forms["sprite"].master.master
        self.notebook.select(sprite_tab)
        self.animation_sequence_var.set(direction)
        entity = self._entity_by_id(self.selected_id)
        if entity is not None:
            self._refresh_animation_frames(entity)
        if not self.variables["sprite"].get().strip():
            messagebox.showinfo(
                "Image manquante",
                "Commencez par choisir une image dans l’onglet Sprite.",
                parent=self.root,
            )

    def _selected_animation_frames(self, entity):
        sequences = entity["animation"].setdefault(
            "sequences", {"left": [], "right": [], "death": []}
        )
        return sequences.setdefault(self.animation_sequence_var.get(), [])

    def _refresh_animation_frames(self, entity):
        self.animation_frames_list.delete(0, "end")
        for index, frame in enumerate(
            self._selected_animation_frames(entity), 1
        ):
            self.animation_frames_list.insert(
                "end", f"{index}. Colonne {frame['column'] + 1}, ligne {frame['row'] + 1}"
            )
        self._update_movement_animation_status(entity)

    def _load_direction_settings(self, entity, direction):
        self._set_direction_flip_choices(direction)
        settings = entity.get("animation", {}).get("direction_settings", {}).get(direction, {})
        delay = settings.get("frame_delay_ms")
        self.direction_delay_var.set("" if delay is None else str(delay))
        self.direction_flip_x_var.set(
            SEQUENCE_FLIP_LABELS.get(settings.get("flip_x"), "Global")
        )
        self.direction_flip_y_var.set(
            SEQUENCE_FLIP_LABELS.get(settings.get("flip_y"), "Global")
        )

    def _set_direction_flip_choices(self, direction):
        choices = list(SEQUENCE_FLIP_CHOICES)
        if direction != "death":
            choices = choices[:3]
        for combo in (self.direction_flip_x_combo, self.direction_flip_y_combo):
            combo.configure(values=choices)

    def _save_direction_settings(self, entity, direction):
        if entity is None or direction not in ("left", "right", "death"):
            return
        animation = entity.setdefault("animation", {})
        settings_by_direction = animation.setdefault("direction_settings", {})
        settings = settings_by_direction.setdefault(
            direction, {"frame_delay_ms": None, "flip_x": None, "flip_y": None}
        )
        raw_delay = self.direction_delay_var.get().strip()
        if raw_delay:
            delay = float(raw_delay)
            if not math.isfinite(delay) or delay <= 0:
                raise ValueError(
                    f"Le délai de la séquence « {direction} » doit être vide "
                    "ou un nombre positif."
                )
            settings["frame_delay_ms"] = delay
        else:
            settings["frame_delay_ms"] = None
        for key, variable in (
            ("flip_x", self.direction_flip_x_var),
            ("flip_y", self.direction_flip_y_var),
        ):
            choice = variable.get()
            if choice not in SEQUENCE_FLIP_CHOICES:
                raise ValueError(f"Choix de retournement invalide pour « {direction} ».")
            if direction != "death" and choice not in ("Global", "Oui", "Non"):
                raise ValueError(
                    "Le retournement conditionnel est disponible uniquement pour « death »."
                )
            settings[key] = SEQUENCE_FLIP_CHOICES[choice]

    def _animation_sequence_changed(self, _event=None):
        entity = self._entity_by_id(self.selected_id)
        new_direction = self.animation_sequence_var.get()
        if entity is not None:
            try:
                self._save_direction_settings(entity, self._loaded_animation_direction)
            except (ValueError, TypeError) as error:
                messagebox.showerror("Réglage d’animation invalide", str(error), parent=self.root)
                self.animation_sequence_var.set(self._loaded_animation_direction)
                return
            self._loaded_animation_direction = new_direction
            self._load_direction_settings(entity, new_direction)
            self._refresh_animation_frames(entity)
            self._update_movement_animation_status(entity)
            self.dirty = True
            self._update_title()

    def add_animation_frame(self):
        if not self._save_current_form():
            return
        if self.frame_picker_selected is None:
            messagebox.showinfo(
                "Frame non selectionnee",
                "Ouvrez le spritesheet et selectionnez une case avant de l'ajouter.",
                parent=self.root,
            )
            return
        entity = self._entity_by_id(self.selected_id)
        if entity is None:
            return
        self._selected_animation_frames(entity).append(
            dict(self.frame_picker_selected)
        )
        self._refresh_animation_frames(entity)
        self.animation_frames_list.selection_set("end")
        self.dirty = True
        self._update_title()

    def delete_animation_frame(self):
        if not self._save_current_form():
            return
        entity = self._entity_by_id(self.selected_id)
        selection = self.animation_frames_list.curselection()
        if entity is None or not selection:
            return
        frames = self._selected_animation_frames(entity)
        del frames[selection[0]]
        self._refresh_animation_frames(entity)
        if frames:
            self.animation_frames_list.selection_set(min(selection[0], len(frames) - 1))
        self.dirty = True
        self._update_title()

    def move_animation_frame(self, offset):
        if not self._save_current_form():
            return
        entity = self._entity_by_id(self.selected_id)
        selection = self.animation_frames_list.curselection()
        if entity is None or not selection:
            return
        frames = self._selected_animation_frames(entity)
        selected = selection[0]
        target = selected + offset
        if not 0 <= target < len(frames):
            return
        frames[selected], frames[target] = frames[target], frames[selected]
        self._refresh_animation_frames(entity)
        self.animation_frames_list.selection_set(target)
        self.dirty = True
        self._update_title()

    def _refresh_movement_steps(self, entity):
        self.movement_steps_list.delete(0, "end")
        for index, step in enumerate(entity["movement"].get("steps", []), 1):
            self.movement_steps_list.insert(
                "end",
                f"{index}. {step['direction']} - {step['steps']:g} px",
            )

    def _save_movement_steps(self, entity):
        entity["movement"].setdefault("steps", [])

    def _selected_step_index(self):
        selection = self.movement_steps_list.curselection()
        return selection[0] if selection else None

    def _movement_step_selected(self, _event=None):
        entity = self._entity_by_id(self.selected_id)
        index = self._selected_step_index()
        if entity is None or index is None:
            return
        step = entity["movement"].get("steps", [])[index]
        self.variables["step_direction"].set(step["direction"])
        self.variables["step_count"].set(step["steps"])

    def _step_from_fields(self):
        direction = self.variables["step_direction"].get()
        distance = float(self.variables["step_count"].get())
        if direction not in ("left", "right", "up", "down"):
            raise ValueError("Choisissez une direction valide.")
        if not math.isfinite(distance) or distance <= 0:
            raise ValueError("Le nombre de pas doit etre positif.")
        return {"direction": direction, "steps": distance}

    def _edit_movement_step(self, operation):
        if not self._save_current_form():
            return
        entity = self._entity_by_id(self.selected_id)
        if entity is None:
            return
        try:
            step = self._step_from_fields()
        except ValueError as error:
            messagebox.showerror("Pas invalide", str(error), parent=self.root)
            return
        steps = entity["movement"].setdefault("steps", [])
        selected = self._selected_step_index()
        if operation == "add":
            index = len(steps)
            steps.append(step)
        elif operation == "update" and selected is not None:
            index = selected
            steps[index] = step
        elif operation == "delete" and selected is not None:
            del steps[selected]
            index = min(selected, len(steps) - 1)
        elif operation in ("up", "down") and selected is not None:
            index = selected + (-1 if operation == "up" else 1)
            if not 0 <= index < len(steps):
                return
            steps[selected], steps[index] = steps[index], steps[selected]
        else:
            return
        self._refresh_movement_steps(entity)
        if steps:
            self.movement_steps_list.selection_set(index)
            self.movement_steps_list.activate(index)
        self.variables["movement_type"].set("steps")
        self.dirty = True
        self._update_title()

    def add_movement_step(self):
        self._edit_movement_step("add")

    def update_movement_step(self):
        self._edit_movement_step("update")

    def delete_movement_step(self):
        self._edit_movement_step("delete")

    def move_movement_step(self, offset):
        self._edit_movement_step("up" if offset < 0 else "down")

    def _property_modified(self, *_args):
        if self.loading_form or not self.selected_id:
            return
        self.dirty = True
        self._update_title()

    def _text_modified(self, event):
        widget = event.widget
        if not widget.edit_modified():
            return
        if not self.loading_form and self.selected_id:
            self.dirty = True
            self._update_title()
        widget.edit_modified(False)

    def _create_entity(self, category, x, y):
        if not self._save_current_form():
            return
        number = 1
        used_ids = {entity["id"] for entity in self.entities}
        while f"{category}-{number}" in used_ids:
            number += 1
        if self.snap_to_grid:
            x = round(x / TILE_SIZE) * TILE_SIZE
            y = round(y / TILE_SIZE) * TILE_SIZE
        entity = default_entity(category, number, max(0, int(x)), max(0, int(y)))
        self.entities.append(entity)
        self.selected_id = None
        self.dirty = True
        self._refresh_list()
        self._select_entity(entity["id"])
        self._update_title()
        self._render_canvas()

    def start_placement(self, category):
        if not self._save_current_form():
            return
        self.placement_category = category
        self.status_var.set(
            f"Cliquez sur la carte pour placer : {CATEGORY_LABELS[category]} (Echap pour annuler)"
        )
        self.canvas.configure(cursor="crosshair")

    def _cancel_placement(self, _event=None):
        self.placement_category = None
        self.canvas.configure(cursor="")
        if self.map_data:
            self.status_var.set(f"{len(self.entities)} entite(s)")

    def _canvas_down(self, event):
        if self.placement_category:
            category = self.placement_category
            world_x = self.canvas.canvasx(event.x) / self.zoom
            world_y = self.canvas.canvasy(event.y) / self.zoom
            self._create_entity(category, world_x, world_y)
            self._cancel_placement()
            return "break"
        x = self.canvas.canvasx(event.x) / self.zoom
        y = self.canvas.canvasy(event.y) / self.zoom
        hit = next(
            (
                entity
                for entity in reversed(self.entities)
                if entity.get("visible", True)
                and entity.get("x", 0) <= x <= entity.get("x", 0) + entity.get("width", TILE_SIZE)
                and entity.get("y", 0) <= y <= entity.get("y", 0) + entity.get("height", TILE_SIZE)
            ),
            None,
        )
        if hit is None:
            self.drag_id = None
            return
        if not self._select_entity(hit["id"]):
            self.drag_id = None
            return "break"
        self.drag_id = hit["id"]
        self.drag_offset = (x - float(hit.get("x", 0)), y - float(hit.get("y", 0)))

    def _canvas_drag(self, event):
        if not self.drag_id:
            return
        entity = self._entity_by_id(self.drag_id)
        if entity is None:
            return
        x = self.canvas.canvasx(event.x) / self.zoom - self.drag_offset[0]
        y = self.canvas.canvasy(event.y) / self.zoom - self.drag_offset[1]
        if self.snap_to_grid:
            x = round(x / TILE_SIZE) * TILE_SIZE
            y = round(y / TILE_SIZE) * TILE_SIZE
        entity["x"] = max(0, round(x))
        entity["y"] = max(0, round(y))
        self.variables["x"].set(entity["x"])
        self.variables["y"].set(entity["y"])
        self.dirty = True
        self._update_title()
        self._render_canvas()

    def _canvas_up(self, _event):
        self.drag_id = None

    def delete_selected(self):
        if not self.selected_id:
            return
        if not self._save_current_form():
            return
        self.entities = [
            entity for entity in self.entities if entity["id"] != self.selected_id
        ]
        self.selected_id = None
        self.dirty = True
        self._refresh_list()
        self._clear_form()
        self._render_canvas()
        self._update_title()

    def toggle_grid(self):
        self.grid_visible = not self.grid_visible
        self._render_canvas()

    def _zoom_changed(self, _event=None):
        self.zoom = {"50 %": 0.5, "100 %": 1.0, "200 %": 2.0}.get(
            self.zoom_var.get(), 1.0
        )
        self.tile_cache.clear()
        self.sprite_cache.clear()
        self._render_canvas()

    def _mouse_wheel(self, event):
        if event.state & 0x0004:
            current = ZOOMS.index(self.zoom)
            zoom_index = max(0, min(2, current + (1 if event.delta > 0 else -1)))
            self.zoom_var.set(f"{int(ZOOMS[zoom_index] * 100)} %")
            self._zoom_changed()
        elif event.delta:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _mouse_wheel_linux(self, _event, direction):
        self.canvas.yview_scroll(-direction, "units")

    def choose_sprite(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Choisir un sprite ou une spritesheet",
            filetypes=(("Images PNG/GIF", "*.png *.gif"), ("Tous les fichiers", "*.*")),
        )
        if not path:
            return
        try:
            sprite_path = Path(path).resolve()
            try:
                relative = os.path.relpath(sprite_path, ROOT)
            except ValueError:
                relative = str(sprite_path)
            self.variables["sprite"].set(relative)
            self.sprite_cache.clear()
            self.frame_picker_selected = None
            self._refresh_sprite_preview()
            self._refresh_frame_picker()
            self._save_current_form()
            self._render_canvas()
        except (OSError, ValueError) as error:
            messagebox.showerror("Image invalide", str(error), parent=self.root)

    def open_frame_picker(self):
        if not self._save_current_form():
            return
        sprite = self.variables["sprite"].get().strip()
        if not sprite:
            messagebox.showinfo(
                "Spritesheet manquant",
                "Choisissez d'abord une image ou une spritesheet.",
                parent=self.root,
            )
            return
        path = self._resolve_asset(sprite)
        try:
            image = tk.PhotoImage(master=self.root, file=str(path))
            width, height = image.width(), image.height()
            frame_width = int(self.variables["frame_width"].get())
            frame_height = int(self.variables["frame_height"].get())
            if width > 256 or height > 256:
                raise ValueError("Pyxel limite les spritesheets a 256 x 256 pixels.")
            if frame_width <= 0 or frame_height <= 0:
                raise ValueError("La largeur et la hauteur de frame doivent etre positives.")
            if width % frame_width or height % frame_height:
                raise ValueError(
                    "Les dimensions du spritesheet doivent etre divisibles par "
                    "la largeur et la hauteur de frame."
                )
        except (OSError, tk.TclError, ValueError) as error:
            messagebox.showerror("Spritesheet invalide", str(error), parent=self.root)
            return
        if self.frame_picker is not None and self.frame_picker.winfo_exists():
            self.frame_picker.lift()
            self.frame_picker_image = image
            self._configure_frame_picker(image, frame_width, frame_height)
            return
        self.frame_picker = tk.Toplevel(self.root)
        self.frame_picker.title("Selection des frames")
        self.frame_picker.transient(self.root)
        ttk.Label(
            self.frame_picker,
            text="Cliquez une case, puis ajoutez-la a la sequence selectionnee.",
        ).pack(anchor="w", padx=8, pady=(8, 4))
        canvas_frame = ttk.Frame(self.frame_picker)
        canvas_frame.pack(fill="both", expand=True, padx=8, pady=4)
        self.frame_picker_canvas = tk.Canvas(
            canvas_frame, background="#20252d", highlightthickness=0,
            width=min(width, 512), height=min(height, 420),
        )
        horizontal = ttk.Scrollbar(
            canvas_frame, orient="horizontal", command=self.frame_picker_canvas.xview
        )
        vertical = ttk.Scrollbar(
            canvas_frame, orient="vertical", command=self.frame_picker_canvas.yview
        )
        self.frame_picker_canvas.configure(
            xscrollcommand=horizontal.set, yscrollcommand=vertical.set
        )
        self.frame_picker_canvas.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)
        self.frame_picker_canvas.bind("<Button-1>", self._frame_picker_click)
        self.frame_picker_status = tk.StringVar(value="Aucune case selectionnee")
        ttk.Label(
            self.frame_picker, textvariable=self.frame_picker_status
        ).pack(anchor="w", padx=8, pady=4)
        controls = ttk.Frame(self.frame_picker)
        controls.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(
            controls,
            text="Ajouter a la sequence",
            command=self.add_animation_frame,
        ).pack(side="left")
        ttk.Button(
            controls, text="Fermer", command=self.frame_picker.destroy
        ).pack(side="right")
        self.frame_picker.protocol(
            "WM_DELETE_WINDOW", self.frame_picker.destroy
        )
        self.frame_picker_image = image
        self._configure_frame_picker(image, frame_width, frame_height)

    def _configure_frame_picker(self, image, frame_width, frame_height):
        self.frame_picker_columns = image.width() // frame_width
        self.frame_picker_rows = image.height() // frame_height
        self.frame_picker_cell_size = (frame_width, frame_height)
        self.frame_picker_canvas.delete("all")
        self.frame_picker_canvas.create_image(0, 0, image=image, anchor="nw")
        self.frame_picker_canvas.image = image
        for row in range(self.frame_picker_rows):
            for column in range(self.frame_picker_columns):
                x1, y1 = column * frame_width, row * frame_height
                self.frame_picker_canvas.create_rectangle(
                    x1, y1, x1 + frame_width, y1 + frame_height,
                    outline="#667080", width=1,
                )
        self.frame_picker_canvas.configure(
            scrollregion=(0, 0, image.width(), image.height())
        )
        self._draw_frame_picker_selection()

    def _frame_picker_click(self, event):
        frame_width, frame_height = self.frame_picker_cell_size
        column = int(self.frame_picker_canvas.canvasx(event.x) // frame_width)
        row = int(self.frame_picker_canvas.canvasy(event.y) // frame_height)
        if not (
            0 <= column < self.frame_picker_columns
            and 0 <= row < self.frame_picker_rows
        ):
            return
        self.frame_picker_selected = {"column": column, "row": row}
        self.frame_picker_status.set(
            f"Colonne {column + 1}, ligne {row + 1}"
        )
        self._draw_frame_picker_selection()

    def _draw_frame_picker_selection(self):
        if self.frame_picker_canvas is None:
            return
        self.frame_picker_canvas.delete("selected-frame")
        if self.frame_picker_selected is None:
            return
        frame_width, frame_height = self.frame_picker_cell_size
        column = self.frame_picker_selected["column"]
        row = self.frame_picker_selected["row"]
        self.frame_picker_canvas.create_rectangle(
            column * frame_width + 1,
            row * frame_height + 1,
            (column + 1) * frame_width - 1,
            (row + 1) * frame_height - 1,
            outline="#ffd166",
            width=3,
            tags=("selected-frame",),
        )

    def _refresh_frame_picker(self):
        if self.frame_picker is None or not self.frame_picker.winfo_exists():
            return
        sprite = self.variables["sprite"].get().strip()
        if not sprite:
            self.frame_picker.destroy()
            self.frame_picker = None
            return
        try:
            image = tk.PhotoImage(
                master=self.root, file=str(self._resolve_asset(sprite))
            )
            frame_width = int(self.variables["frame_width"].get())
            frame_height = int(self.variables["frame_height"].get())
            if frame_width <= 0 or frame_height <= 0:
                self.frame_picker_status.set(
                    "Definissez une largeur et une hauteur de frame positives."
                )
                return
            if image.width() % frame_width or image.height() % frame_height:
                self.frame_picker_status.set(
                    "Les dimensions des frames ne correspondent plus au spritesheet."
                )
                return
        except (OSError, tk.TclError, ValueError) as error:
            self.frame_picker_status.set(f"Spritesheet invalide : {error}")
            return
        if (
            self.frame_picker_selected is not None
            and (
                self.frame_picker_selected["column"] >= image.width() // frame_width
                or self.frame_picker_selected["row"] >= image.height() // frame_height
            )
        ):
            self.frame_picker_selected = None
        if self.frame_picker_selected is None:
            self.frame_picker_status.set("Aucune case selectionnee")
        self.frame_picker_image = image
        self._configure_frame_picker(image, frame_width, frame_height)

    def _refresh_sprite_preview(self):
        self.sprite_preview.delete("all")
        entity = self._entity_by_id(self.selected_id)
        if entity is None:
            return
        image = self._entity_sprite(entity, 0)
        if image is None:
            sprite = entity.get("sprite", "")
            if not sprite:
                description = "Aucune image selectionnee"
            elif not self._resolve_asset(sprite).is_file():
                description = f"Fichier introuvable : {Path(sprite).name}"
            else:
                description = f"Image illisible ou frame invalide : {Path(sprite).name}"
            self.sprite_preview.create_text(
                115,
                62,
                text=description,
                fill="#d8dee9",
                width=210,
            )
            return
        self.sprite_preview.create_image(115, 62, image=image, anchor="center")
        self.image_refs.append(image)

    def refresh_advanced_json(self):
        entity = self._entity_by_id(self.selected_id)
        self.custom_data_text.delete("1.0", "end")
        self.advanced_text.delete("1.0", "end")
        if entity is None:
            self.custom_data_text.insert("1.0", "{}")
            return
        self.custom_data_text.insert(
            "1.0",
            json.dumps(entity.get("custom_data", {}), ensure_ascii=False, indent=2),
        )
        self.custom_data_text.edit_modified(False)
        self.advanced_text.insert(
            "1.0", json.dumps(entity, ensure_ascii=False, indent=2)
        )
        self.advanced_text.edit_modified(False)

    def apply_advanced_json(self):
        try:
            entity = json.loads(self.advanced_text.get("1.0", "end-1c"))
            if not isinstance(entity, dict):
                raise ValueError("Le JSON complet doit etre un objet.")
            if entity.get("id") != self.selected_id:
                raise ValueError("L'identifiant de l'entite ne peut pas etre modifie ici.")
            normalized = normalize_entity(entity, 1)
            validate_entity(normalized)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            messagebox.showerror("JSON invalide", str(error), parent=self.root)
            return
        entity_id = self.selected_id
        index = next(
            index for index, item in enumerate(self.entities)
            if item["id"] == entity_id
        )
        self.entities[index] = normalized
        self.selected_id = None
        self.dirty = True
        self._select_entity(entity_id)
        self._update_title()
        self._render_canvas()

    def choose_map(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Ouvrir une carte Tiled JSON",
            initialdir=str(self.map_path.parent if self.map_path else ROOT / "assets" / "maps"),
            filetypes=(("Cartes JSON", "*.json"), ("Tous les fichiers", "*.*")),
        )
        if path:
            try:
                self.open_map(path)
            except (OSError, ValueError, json.JSONDecodeError, ET.ParseError, tk.TclError) as error:
                messagebox.showerror("Ouverture impossible", str(error), parent=self.root)

    def save(self):
        if not self.map_path or not self._save_current_form():
            return
        try:
            save_document(self.map_path, self.entities_path, self.entities)
        except (OSError, ValueError) as error:
            messagebox.showerror("Enregistrement impossible", str(error), parent=self.root)
            return
        self.dirty = False
        self._update_title()
        self.status_var.set(f"Enregistre : {self.entities_path.name}")

    def _confirm_discard(self):
        if not self.dirty:
            return True
        result = messagebox.askyesnocancel(
            "Modifications non enregistrees",
            "Enregistrer les modifications avant de continuer ?",
            parent=self.root,
        )
        if result is None:
            return False
        if result:
            self.save()
            return not self.dirty
        return True

    def close(self):
        if self._confirm_discard():
            self.root.destroy()

    def _update_title(self):
        marker = " *" if self.dirty else ""
        map_name = self.map_path.name if self.map_path else "Nouveau niveau"
        self.root.title(f"Lost Cave - {map_name}{marker}")


def launch(map_path=None):
    root = tk.Tk()
    try:
        LevelEntityEditor(root, map_path or DEFAULT_MAP)
    except (OSError, ValueError, json.JSONDecodeError, ET.ParseError, tk.TclError) as error:
        messagebox.showerror("Impossible d'ouvrir l'editeur", str(error), parent=root)
        root.destroy()
        raise
    root.mainloop()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", default=str(DEFAULT_MAP), help="Carte Tiled JSON a ouvrir")
    arguments = parser.parse_args(argv)
    launch(arguments.map)


if __name__ == "__main__":
    main()
