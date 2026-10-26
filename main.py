# -*- coding: utf-8 -*-
"""
rhTools SKP Optimizer
Standalone desktop tool to automate SketchUp model optimization, purging, and element separation.
Supports batch queue processing of multiple .skp files.
Part of the rhTools suite.
"""

import os
import sys
import time
import json
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from engine import SketchUpDetector, PipelineRunner
from logo_asset import LOGO_HEADER_BASE64, ICON_ICO_BASE64

APP_VERSION = "v1.0.2"

DERIVED_SUFFIXES = [
    "_otimizado.skp",
    "_arquitetura.skp",
    "_assets.skp",
    "_mobiliario_vegetacao.skp"
]

def is_derived_file(filepath: str) -> bool:
    lower = filepath.lower()
    return any(lower.endswith(suf) for suf in DERIVED_SUFFIXES)

def format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.2f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024**2):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} B"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title(f"rhTools SKP Optimizer - {APP_VERSION}")
        self.geometry("880x760")
        self.minsize(780, 640)
        
        # Color Palette (Modern Dark Slate / rhTools Theme)
        self.bg_main = "#181825"
        self.bg_card = "#1e1e2e"
        self.bg_input = "#313244"
        self.fg_text = "#cdd6f4"
        self.fg_sub = "#a6adc8"
        self.accent = "#89b4fa"
        self.accent_hover = "#b4befe"
        self.success = "#a6e3a1"
        self.warning = "#f9e2af"
        self.danger = "#f38ba8"
        
        self.configure(bg=self.bg_main)
        
        # Set Window Icon
        try:
            self.icon_img = tk.PhotoImage(data=LOGO_HEADER_BASE64)
            self.iconphoto(True, self.icon_img)
        except Exception:
            pass
        
        self.su_versions = SketchUpDetector.get_installed_versions()
        self.selected_su = tk.StringVar()
        
        self.opt_optimize = tk.BooleanVar(value=True)
        self.opt_architecture = tk.BooleanVar(value=True)
        self.opt_furniture = tk.BooleanVar(value=True)
        
        # Queue Data
        self.queue_items = []  # list of dicts: {"tree_id", "path", "name", "size_bytes", "folder", "status"}
        self.is_running = False
        self.cancel_requested = False
        self.runner = None
        
        self._init_styles()
        self._build_ui()
        
        # Select first detected SketchUp
        if self.su_versions:
            self.selected_su.set(self.su_versions[0]["name"])
        else:
            self.selected_su.set("Nenhum SketchUp detectado automaticamente")

    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        
        # Progressbars
        style.configure("Queue.Horizontal.TProgressbar", thickness=14, troughcolor=self.bg_input, background=self.accent)
        style.configure("File.Horizontal.TProgressbar", thickness=10, troughcolor=self.bg_input, background=self.success)
        
        style.configure("Card.TFrame", background=self.bg_card)
        style.configure("TCombobox", fieldbackground=self.bg_input, background=self.bg_card, foreground=self.fg_text)
        style.map("TCombobox", fieldbackground=[("readonly", self.bg_input)])
        
        # Treeview styling
        style.configure(
            "Treeview",
            background=self.bg_card,
            foreground=self.fg_text,
            fieldbackground=self.bg_card,
            rowheight=26,
            font=("Segoe UI", 9)
        )
        style.configure(
            "Treeview.Heading",
            background=self.bg_input,
            foreground=self.accent,
            font=("Segoe UI", 9, "bold"),
            relief="flat"
        )
        style.map(
            "Treeview",
            background=[("selected", "#45475a")],
            foreground=[("selected", "#ffffff")]
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#45475a")]
        )

    def _build_ui(self):
        # 0. Header with Logo
        header = tk.Frame(self, bg=self.bg_main, padx=24, pady=14)
        header.pack(fill="x")
        
        try:
            self.logo_photo = tk.PhotoImage(data=LOGO_HEADER_BASE64)
            logo_lbl = tk.Label(header, image=self.logo_photo, bg=self.bg_main)
            logo_lbl.pack(side="left", padx=(0, 14))
        except Exception:
            pass
        
        title_box = tk.Frame(header, bg=self.bg_main)
        title_box.pack(side="left", fill="x", expand=True)
        
        title_row = tk.Frame(title_box, bg=self.bg_main)
        title_row.pack(anchor="w")
        
        title_lbl = tk.Label(
            title_row,
            text="rhTools SKP Optimizer",
            font=("Segoe UI", 18, "bold"),
            fg=self.accent,
            bg=self.bg_main
        )
        title_lbl.pack(side="left")
        
        ver_badge = tk.Label(
            title_row,
            text=APP_VERSION,
            font=("Segoe UI", 9, "bold"),
            fg="#11111b",
            bg=self.accent,
            padx=6,
            pady=1
        )
        ver_badge.pack(side="left", padx=(10, 0), pady=(3, 0))
        
        subtitle_lbl = tk.Label(
            title_box,
            text="Otimização, Limpeza e Separação em Fila (Batch Processing) para SketchUp",
            font=("Segoe UI", 9),
            fg=self.fg_sub,
            bg=self.bg_main
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))
        
        # Main Container
        content = tk.Frame(self, bg=self.bg_main, padx=24)
        content.pack(fill="both", expand=True)

        # 1. SketchUp Version Selector Card
        su_card = tk.LabelFrame(
            content,
            text=" 1. Versão do SketchUp ",
            font=("Segoe UI", 10, "bold"),
            fg=self.accent,
            bg=self.bg_card,
            padx=12,
            pady=8
        )
        su_card.pack(fill="x", pady=(0, 8))
        
        su_names = [v["name"] for v in self.su_versions] if self.su_versions else ["Buscar manualmente..."]
        su_combo = ttk.Combobox(su_card, values=su_names, textvariable=self.selected_su, state="readonly", width=40)
        su_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        btn_browse_su = tk.Button(
            su_card,
            text="Procurar .exe...",
            font=("Segoe UI", 9),
            bg=self.bg_input,
            fg=self.fg_text,
            relief="flat",
            padx=10,
            command=self._browse_custom_su
        )
        btn_browse_su.pack(side="right")

        # 2. Queue Section (File Selection)
        queue_card = tk.LabelFrame(
            content,
            text=" 2. Fila de Modelos SketchUp (.SKP) ",
            font=("Segoe UI", 10, "bold"),
            fg=self.accent,
            bg=self.bg_card,
            padx=12,
            pady=8
        )
        queue_card.pack(fill="both", expand=True, pady=(0, 8))
        
        # Toolbar above Treeview
        tb_frame = tk.Frame(queue_card, bg=self.bg_card)
        tb_frame.pack(fill="x", pady=(0, 8))
        
        self.btn_add_files = tk.Button(
            tb_frame,
            text="+ Adicionar Arquivo(s)...",
            font=("Segoe UI", 9, "bold"),
            bg=self.accent,
            fg="#11111b",
            relief="flat",
            padx=12,
            pady=4,
            command=self._add_files
        )
        self.btn_add_files.pack(side="left", padx=(0, 6))
        
        self.btn_add_folder = tk.Button(
            tb_frame,
            text="+ Adicionar Pasta...",
            font=("Segoe UI", 9),
            bg=self.bg_input,
            fg=self.fg_text,
            relief="flat",
            padx=10,
            pady=4,
            command=self._add_folder
        )
        self.btn_add_folder.pack(side="left", padx=(0, 6))
        
        self.btn_remove = tk.Button(
            tb_frame,
            text="- Remover Selecionado(s)",
            font=("Segoe UI", 9),
            bg=self.bg_input,
            fg=self.fg_text,
            relief="flat",
            padx=10,
            pady=4,
            command=self._remove_selected
        )
        self.btn_remove.pack(side="left", padx=(0, 6))
        
        self.btn_clear = tk.Button(
            tb_frame,
            text="🗑 Limpar Fila",
            font=("Segoe UI", 9),
            bg=self.bg_input,
            fg=self.danger,
            relief="flat",
            padx=10,
            pady=4,
            command=self._clear_queue
        )
        self.btn_clear.pack(side="left")
        
        hint_lbl = tk.Label(
            tb_frame,
            text="Dica: duplo-clique no item abre a pasta.",
            font=("Segoe UI", 8),
            fg=self.fg_sub,
            bg=self.bg_card
        )
        hint_lbl.pack(side="right")
        
        # Treeview Container
        tree_frame = tk.Frame(queue_card, bg=self.bg_card)
        tree_frame.pack(fill="both", expand=True)
        
        columns = ("idx", "status", "name", "size", "folder")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=6
        )
        
        self.tree.heading("idx", text="#")
        self.tree.heading("status", text="Status")
        self.tree.heading("name", text="Modelo (.SKP)")
        self.tree.heading("size", text="Tamanho")
        self.tree.heading("folder", text="Pasta / Diretório")
        
        self.tree.column("idx", width=36, anchor="center")
        self.tree.column("status", width=125, anchor="center")
        self.tree.column("name", width=250, anchor="w")
        self.tree.column("size", width=85, anchor="e")
        self.tree.column("folder", width=280, anchor="w")
        
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
        # Tags for status colors
        self.tree.tag_configure("pending", foreground=self.fg_text)
        self.tree.tag_configure("processing", foreground=self.warning)
        self.tree.tag_configure("completed", foreground=self.success)
        self.tree.tag_configure("error", foreground=self.danger)
        self.tree.tag_configure("canceled", foreground="#6c7086")
        
        # Tree Events
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Delete>", lambda e: self._remove_selected())
        
        # Queue Stats Label
        self.lbl_queue_stats = tk.Label(
            queue_card,
            text="Fila vazia. Adicione um ou mais arquivos .skp para iniciar.",
            font=("Segoe UI", 9),
            fg=self.fg_sub,
            bg=self.bg_card
        )
        self.lbl_queue_stats.pack(anchor="w", pady=(6, 0))

        # 3. Pipeline Options Card
        opt_card = tk.LabelFrame(
            content,
            text=" 3. Opções da Pipeline ",
            font=("Segoe UI", 10, "bold"),
            fg=self.accent,
            bg=self.bg_card,
            padx=12,
            pady=6
        )
        opt_card.pack(fill="x", pady=(0, 8))
        
        opts_box = tk.Frame(opt_card, bg=self.bg_card)
        opts_box.pack(fill="x")
        
        chk1 = tk.Checkbutton(
            opts_box,
            text="Gerar Otimizado (_Otimizado.skp)",
            variable=self.opt_optimize,
            font=("Segoe UI", 9),
            fg=self.fg_text,
            bg=self.bg_card,
            selectcolor=self.bg_input,
            activebackground=self.bg_card,
            activeforeground=self.accent
        )
        chk1.pack(side="left", padx=(0, 16))
        
        chk2 = tk.Checkbutton(
            opts_box,
            text="Separar Arquitetura (_Arquitetura.skp)",
            variable=self.opt_architecture,
            font=("Segoe UI", 9),
            fg=self.fg_text,
            bg=self.bg_card,
            selectcolor=self.bg_input,
            activebackground=self.bg_card,
            activeforeground=self.accent
        )
        chk2.pack(side="left", padx=(0, 16))
        
        chk3 = tk.Checkbutton(
            opts_box,
            text="Separar Mobiliário / Vegetação (_Assets.skp)",
            variable=self.opt_furniture,
            font=("Segoe UI", 9),
            fg=self.fg_text,
            bg=self.bg_card,
            selectcolor=self.bg_input,
            activebackground=self.bg_card,
            activeforeground=self.accent
        )
        chk3.pack(side="left")

        # 4. Progress and Log Card
        prog_card = tk.LabelFrame(
            content,
            text=" 4. Progresso & Status da Execução ",
            font=("Segoe UI", 10, "bold"),
            fg=self.accent,
            bg=self.bg_card,
            padx=12,
            pady=8
        )
        prog_card.pack(fill="both", expand=True, pady=(0, 8))
        
        # Overall Queue Progress
        self.lbl_queue_prog = tk.Label(
            prog_card,
            text="Progresso Geral da Fila: Aguardando...",
            font=("Segoe UI", 9, "bold"),
            fg=self.fg_text,
            bg=self.bg_card
        )
        self.lbl_queue_prog.pack(anchor="w", pady=(0, 2))
        
        self.prog_queue = ttk.Progressbar(prog_card, orient="horizontal", mode="determinate", style="Queue.Horizontal.TProgressbar")
        self.prog_queue.pack(fill="x", pady=(0, 6))
        
        # Current File Progress
        self.lbl_file_prog = tk.Label(
            prog_card,
            text="Arquivo Atual: Nenhum arquivo em processamento.",
            font=("Segoe UI", 8),
            fg=self.fg_sub,
            bg=self.bg_card
        )
        self.lbl_file_prog.pack(anchor="w", pady=(0, 2))
        
        self.prog_file = ttk.Progressbar(prog_card, orient="horizontal", mode="determinate", style="File.Horizontal.TProgressbar")
        self.prog_file.pack(fill="x", pady=(0, 6))
        
        # Log Box with scrollbar
        log_frame = tk.Frame(prog_card, bg=self.bg_card)
        log_frame.pack(fill="both", expand=True)
        
        self.txt_log = tk.Text(
            log_frame,
            height=5,
            font=("Consolas", 8),
            bg=self.bg_input,
            fg="#bac2de",
            relief="flat",
            wrap="word"
        )
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=log_scroll.set)
        
        self.txt_log.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        # 5. Bottom Action Buttons Bar
        actions_bar = tk.Frame(self, bg=self.bg_main, padx=24, pady=10)
        actions_bar.pack(fill="x", side="bottom")
        
        self.btn_run = tk.Button(
            actions_bar,
            text="▶ EXECUTAR FILA",
            font=("Segoe UI", 11, "bold"),
            bg=self.success,
            fg="#11111b",
            relief="flat",
            padx=20,
            pady=6,
            command=self._start_pipeline
        )
        self.btn_run.pack(side="left")
        
        self.btn_cancel = tk.Button(
            actions_bar,
            text="⏹ Cancelar Fila",
            font=("Segoe UI", 9, "bold"),
            bg=self.bg_input,
            fg=self.danger,
            relief="flat",
            padx=14,
            pady=6,
            state="disabled",
            command=self._cancel_pipeline
        )
        self.btn_cancel.pack(side="left", padx=10)
        
        self.btn_open_folder = tk.Button(
            actions_bar,
            text="📁 Abrir Pasta no Explorer",
            font=("Segoe UI", 9),
            bg=self.bg_input,
            fg=self.fg_text,
            relief="flat",
            padx=14,
            pady=6,
            command=self._open_output_folder
        )
        self.btn_open_folder.pack(side="right")

    # --- Queue Management ---

    def _insert_queue_item(self, full_path: str):
        size_bytes = os.path.getsize(full_path) if os.path.exists(full_path) else 0
        name = os.path.basename(full_path)
        folder = os.path.dirname(full_path)
        idx = len(self.queue_items) + 1
        
        tree_id = self.tree.insert(
            "",
            "end",
            values=(str(idx), "⏳ Pendente", name, format_size(size_bytes), folder),
            tags=("pending",)
        )
        
        self.queue_items.append({
            "tree_id": tree_id,
            "path": full_path,
            "name": name,
            "size_bytes": size_bytes,
            "folder": folder,
            "status": "Pendente"
        })

    def _reindex_queue(self):
        for idx, it in enumerate(self.queue_items):
            current_vals = list(self.tree.item(it["tree_id"], "values"))
            current_vals[0] = str(idx + 1)
            self.tree.item(it["tree_id"], values=current_vals)

    def _update_queue_stats(self):
        total = len(self.queue_items)
        if total == 0:
            self.lbl_queue_stats.config(
                text="Fila vazia. Adicione um ou mais arquivos .skp para iniciar.",
                fg=self.fg_sub
            )
            return
            
        total_bytes = sum(it["size_bytes"] for it in self.queue_items)
        pending = sum(1 for it in self.queue_items if it["status"] in ["Pendente", "⏳ Pendente"])
        completed = sum(1 for it in self.queue_items if it["status"] in ["Concluído", "✅ Concluído"])
        errors = sum(1 for it in self.queue_items if "Erro" in it["status"])
        
        text = f"Total na fila: {total} arquivo(s) ({format_size(total_bytes)})  |  {pending} pendente(s)  |  {completed} concluído(s)"
        if errors > 0:
            text += f"  |  {errors} com erro"
            
        self.lbl_queue_stats.config(text=text, fg=self.fg_text)

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="Selecione um ou mais arquivos SketchUp (.skp)",
            filetypes=[("Modelos SketchUp (*.skp)", "*.skp"), ("Todos os Arquivos", "*.*")]
        )
        if not files:
            return
            
        added = 0
        skipped_derived = 0
        for f in files:
            norm = str(Path(f).resolve())
            if is_derived_file(norm):
                skipped_derived += 1
                self._append_log(f"[{time.strftime('%H:%M:%S')}] Ignorado (já derivado): {os.path.basename(norm)}")
                continue
            if any(it["path"] == norm for it in self.queue_items):
                continue
            self._insert_queue_item(norm)
            added += 1
            
        self._update_queue_stats()
        if added > 0:
            self._append_log(f"[{time.strftime('%H:%M:%S')}] +{added} arquivo(s) adicionado(s) à fila.")
        if skipped_derived > 0 and added == 0:
            messagebox.showinfo(
                "Aviso",
                f"{skipped_derived} arquivo(s) selecionado(s) já são arquivos de saída (_Otimizado, _Arquitetura ou _Assets) e foram ignorados."
            )

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Selecione uma pasta com arquivos SketchUp (.skp)")
        if not folder:
            return
            
        folder_path = Path(folder)
        skp_files = sorted(list(folder_path.glob("*.skp")), key=lambda p: p.name.lower())
        if not skp_files:
            messagebox.showinfo("Informação", "Nenhum arquivo .skp encontrado na pasta.")
            return
            
        added = 0
        skipped_derived = 0
        for f in skp_files:
            norm = str(f.resolve())
            if is_derived_file(norm):
                skipped_derived += 1
                continue
            if any(it["path"] == norm for it in self.queue_items):
                continue
            self._insert_queue_item(norm)
            added += 1
            
        self._update_queue_stats()
        msg = f"{added} modelo(s) .skp adicionado(s) à fila."
        if skipped_derived > 0:
            msg += f"\n({skipped_derived} arquivos derivados já gerados foram ignorados)."
        messagebox.showinfo("Fila Atualizada", msg)
        self._append_log(f"[{time.strftime('%H:%M:%S')}] Pasta adicionada: {folder} (+{added} arquivos)")

    def _remove_selected(self):
        if self.is_running:
            messagebox.showwarning("Aviso", "Não é possível remover itens com a fila em andamento.")
            return
        selected = self.tree.selection()
        if not selected:
            return
        for item_id in selected:
            self.tree.delete(item_id)
            self.queue_items = [it for it in self.queue_items if it["tree_id"] != item_id]
        self._reindex_queue()
        self._update_queue_stats()

    def _clear_queue(self):
        if self.is_running:
            messagebox.showwarning("Aviso", "Não é possível limpar a fila durante a execução.")
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.queue_items.clear()
        self._update_queue_stats()
        self._append_log(f"[{time.strftime('%H:%M:%S')}] Fila limpa.")

    def _on_tree_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        for it in self.queue_items:
            if it["tree_id"] == item_id:
                if os.path.exists(it["folder"]):
                    subprocess.Popen(f'explorer "{it["folder"]}"')
                break

    def _open_output_folder(self):
        selected = self.tree.selection()
        target_folder = None
        if selected:
            for it in self.queue_items:
                if it["tree_id"] == selected[0]:
                    target_folder = it["folder"]
                    break
        if not target_folder and self.queue_items:
            target_folder = self.queue_items[0]["folder"]
            
        if target_folder and os.path.exists(target_folder):
            subprocess.Popen(f'explorer "{target_folder}"')
        else:
            messagebox.showinfo("Aviso", "Nenhuma pasta selecionada ou disponível na fila.")

    def _browse_custom_su(self):
        filename = filedialog.askopenfilename(
            title="Localize o executável do SketchUp (SketchUp.exe)",
            filetypes=[("Executável SketchUp", "SketchUp.exe"), ("Todos os Arquivos", "*.*")]
        )
        if filename:
            exe_path = Path(filename)
            year = "Custom"
            for part in exe_path.parts:
                if "SketchUp" in part and any(y in part for y in ["2026", "2025", "2024", "2023", "2022", "2021", "2020"]):
                    year = [y for y in ["2026", "2025", "2024", "2023", "2022", "2021", "2020"] if y in part][0]
                    break
            
            custom_info = {
                "year": year,
                "name": f"SketchUp {year} (Personalizado)",
                "exe": str(exe_path),
                "plugins": str(Path(os.environ.get("APPDATA", "")) / "SketchUp" / f"SketchUp {year}" / "SketchUp" / "Plugins"),
                "localappdata": str(Path(os.environ.get("LOCALAPPDATA", "")) / "SketchUp" / f"SketchUp {year}" / "SketchUp")
            }
            self.su_versions.append(custom_info)
            self.selected_su.set(custom_info["name"])

    def _append_log(self, text: str):
        self.after(0, lambda: self._do_append_log(text))

    def _do_append_log(self, text: str):
        self.txt_log.insert("end", text + "\n")
        self.txt_log.see("end")

    def _update_tree_item(self, item_id: str, status: str, tag: str):
        def _do():
            if self.tree.exists(item_id):
                vals = list(self.tree.item(item_id, "values"))
                vals[1] = status
                self.tree.item(item_id, values=vals, tags=(tag,))
        self.after(0, _do)

    # --- Pipeline Execution ---

    def _start_pipeline(self):
        if self.is_running:
            return
            
        if not self.queue_items:
            messagebox.showerror("Erro", "A fila está vazia! Adicione arquivos .SKP para processar.")
            return
            
        if not any([self.opt_optimize.get(), self.opt_architecture.get(), self.opt_furniture.get()]):
            messagebox.showwarning("Aviso", "Selecione ao menos uma opção na etapa 3!")
            return
            
        su_name = self.selected_su.get()
        target_su = next((v for v in self.su_versions if v["name"] == su_name), None)
        if not target_su or not os.path.exists(target_su["exe"]):
            messagebox.showerror("Erro", "Executável do SketchUp não encontrado!")
            return
            
        self.is_running = True
        self.cancel_requested = False
        
        self.btn_run.config(state="disabled", bg=self.bg_input, text="Processando Fila...")
        self.btn_cancel.config(state="normal", bg=self.danger)
        self.btn_add_files.config(state="disabled")
        self.btn_add_folder.config(state="disabled")
        self.btn_remove.config(state="disabled")
        self.btn_clear.config(state="disabled")
        
        self.prog_queue["value"] = 0
        self.prog_file["value"] = 0
        
        threading.Thread(target=self._worker_thread, args=(target_su,), daemon=True).start()

    def _cancel_pipeline(self):
        if not self.is_running:
            return
        if messagebox.askyesno("Confirmar Cancelamento", "Deseja interromper o processamento da fila?"):
            self.cancel_requested = True
            self.lbl_file_prog.config(text="Cancelando fila... aguarde...", fg=self.warning)
            self.btn_cancel.config(state="disabled", text="Cancelando...")
            if self.runner:
                self.runner.stop()

    def _worker_thread(self, target_su: dict):
        total_files = len(self.queue_items)
        completed_count = 0
        error_count = 0
        
        self._append_log("=" * 60)
        self._append_log(f"[{time.strftime('%H:%M:%S')}] rhTools SKP Optimizer {APP_VERSION}")
        self._append_log(f"[{time.strftime('%H:%M:%S')}] Iniciando Fila de Processamento ({total_files} arquivo(s))...")
        self._append_log(f"[{time.strftime('%H:%M:%S')}] SketchUp: {target_su['name']}")
        self._append_log("=" * 60)
        
        for idx, item in enumerate(self.queue_items):
            if self.cancel_requested:
                self._append_log(f"[{time.strftime('%H:%M:%S')}] Processamento interrompido pelo usuário.")
                break
                
            if item["status"] == "Concluído":
                completed_count += 1
                continue
                
            item_id = item["tree_id"]
            skp_path = item["path"]
            file_name = item["name"]
            
            # UI Updates
            item["status"] = "Processando"
            self._update_tree_item(item_id, "⚙️ Processando", "processing")
            self.after(0, self._update_queue_stats)
            
            queue_pct = int((idx / total_files) * 100)
            self.after(0, lambda qp=queue_pct, i=idx: (
                self.prog_queue.configure(value=qp),
                self.lbl_queue_prog.configure(
                    text=f"Progresso Geral: Arquivo {i + 1} de {total_files} ({qp}%)",
                    fg=self.accent
                ),
                self.prog_file.configure(value=5),
                self.lbl_file_prog.configure(
                    text=f"[{i + 1}/{total_files}] Inicializando {file_name}...",
                    fg=self.warning
                )
            ))
            
            self._append_log(f"\n--- [{idx + 1}/{total_files}] {file_name} ---")
            
            if not os.path.exists(skp_path):
                item["status"] = "Erro"
                error_count += 1
                self._update_tree_item(item_id, "❌ Não encontrado", "error")
                self._append_log(f"[{time.strftime('%H:%M:%S')}] Arquivo não encontrado: {skp_path}")
                continue
                
            work_dir = os.path.dirname(skp_path)
            self.runner = PipelineRunner(target_su, work_dir)
            self.runner.write_config(
                skp_path,
                self.opt_optimize.get(),
                self.opt_architecture.get(),
                self.opt_furniture.get()
            )
            
            proc = self.runner.launch(skp_path)
            last_message = ""
            success = False
            error_msg = ""
            
            while True:
                time.sleep(1.0)
                
                if self.cancel_requested:
                    self._append_log(f"[{time.strftime('%H:%M:%S')}] Encerrando SketchUp para cancelamento...")
                    self.runner.stop()
                    item["status"] = "Cancelado"
                    self._update_tree_item(item_id, "⏹ Cancelado", "canceled")
                    break
                    
                status = self.runner.get_status()
                prog = status.get("progress", 10)
                msg = status.get("message", "Processando...")
                st = status.get("status", "running")
                
                self.after(0, lambda p=prog, m=msg, i=idx: (
                    self.prog_file.configure(value=p),
                    self.lbl_file_prog.configure(text=f"[{i + 1}/{total_files}] {m} ({p}%)", fg=self.fg_text)
                ))
                
                if msg != last_message:
                    self._append_log(f"[{time.strftime('%H:%M:%S')}] {msg}")
                    last_message = msg
                    
                if st == "completed":
                    success = True
                    break
                    
                if st == "error":
                    error_msg = msg
                    break
                    
                # If process died unexpectedly
                if proc.poll() is not None and st not in ["completed", "error"]:
                    time.sleep(2.0)
                    final_status = self.runner.get_status()
                    if final_status.get("status") == "completed":
                        success = True
                    else:
                        error_msg = final_status.get("message", "SketchUp encerrou antes da confirmação.")
                    break
                    
            # Wait for process to fully exit
            if proc.poll() is None:
                try:
                    proc.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    self.runner.stop()
                    
            if self.runner:
                self.runner.cleanup()
                
            if self.cancel_requested:
                break
                
            if success:
                item["status"] = "Concluído"
                completed_count += 1
                self._update_tree_item(item_id, "✅ Concluído", "completed")
                self.after(0, lambda i=idx, fn=file_name: (
                    self.prog_file.configure(value=100),
                    self.lbl_file_prog.configure(text=f"[{i + 1}/{total_files}] {fn} finalizado com sucesso!", fg=self.success)
                ))
                self._append_log(f"[{time.strftime('%H:%M:%S')}] Concluído com sucesso!")
            else:
                item["status"] = "Erro"
                error_count += 1
                self._update_tree_item(item_id, "❌ Erro", "error")
                self.after(0, lambda i=idx, em=error_msg: (
                    self.lbl_file_prog.configure(text=f"[{i + 1}/{total_files}] Falha: {em}", fg=self.danger)
                ))
                self._append_log(f"[{time.strftime('%H:%M:%S')}] Falha no arquivo: {error_msg}")
                
            self.after(0, self._update_queue_stats)
            # Short cooldown between files so SketchUp instances don't collide
            time.sleep(1.5)
            
        # Finalization
        self.after(0, lambda: self._on_worker_finished(completed_count, error_count, total_files))

    def _on_worker_finished(self, completed_count: int, error_count: int, total_files: int):
        self.is_running = False
        self.cancel_requested = False
        
        self.btn_run.config(state="normal", bg=self.success, text="▶ EXECUTAR FILA")
        self.btn_cancel.config(state="disabled", text="⏹ Cancelar Fila")
        self.btn_add_files.config(state="normal")
        self.btn_add_folder.config(state="normal")
        self.btn_remove.config(state="normal")
        self.btn_clear.config(state="normal")
        
        if self.cancel_requested:
            self.lbl_queue_prog.config(text="Fila cancelada pelo usuário.", fg=self.warning)
            self._append_log(f"\n[{time.strftime('%H:%M:%S')}] Fila interrompida.")
        else:
            self.prog_queue["value"] = 100
            self.lbl_queue_prog.config(
                text=f"Fila finalizada! {completed_count} concluído(s), {error_count} erro(s).",
                fg=self.success if error_count == 0 else self.warning
            )
            self._append_log("=" * 60)
            self._append_log(f"[{time.strftime('%H:%M:%S')}] Fila concluída: {completed_count}/{total_files} arquivo(s) processados com sucesso.")
            self._append_log("=" * 60)
            
        self._update_queue_stats()


if __name__ == "__main__":
    app = App()
    app.mainloop()
