# -*- coding: utf-8 -*-
"""
SketchUp Automation Engine
Detects SketchUp installations, installs runner bridge, executes pipeline, monitors progress.
"""

import os
import sys
import json
import time
import subprocess
import winreg
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class SketchUpDetector:
    @staticmethod
    def get_installed_versions() -> List[Dict[str, str]]:
        """Find all installed SketchUp versions on the system."""
        found = []
        
        # 1. Check Program Files directories
        program_files = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        ]
        
        years = ["2026", "2025", "2024", "2023", "2022", "2021", "2020"]
        
        for pf in program_files:
            if not pf:
                continue
            su_base = Path(pf) / "SketchUp"
            if su_base.exists():
                for year in years:
                    candidate_dirs = [
                        su_base / f"SketchUp {year}" / "SketchUp" / "SketchUp.exe",
                        su_base / f"SketchUp {year}" / "SketchUp.exe",
                    ]
                    for exe in candidate_dirs:
                        if exe.exists():
                            appdata_plugins = Path(os.environ.get("APPDATA", "")) / "SketchUp" / f"SketchUp {year}" / "SketchUp" / "Plugins"
                            localappdata = Path(os.environ.get("LOCALAPPDATA", "")) / "SketchUp" / f"SketchUp {year}" / "SketchUp"
                            found.append({
                                "year": year,
                                "name": f"SketchUp {year}",
                                "exe": str(exe),
                                "plugins": str(appdata_plugins),
                                "localappdata": str(localappdata)
                            })
                            break

        # 2. Check Windows Registry if not found yet
        if not found:
            for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    with winreg.OpenKey(root_key, r"SOFTWARE\Trimble\SketchUp") as key:
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                i += 1
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        install_dir, _ = winreg.QueryValueEx(subkey, "InstallDir")
                                        exe_path = Path(install_dir) / "SketchUp.exe"
                                        if not exe_path.exists():
                                            exe_path = Path(install_dir) / "SketchUp" / "SketchUp.exe"
                                        if exe_path.exists():
                                            found.append({
                                                "year": subkey_name,
                                                "name": f"SketchUp {subkey_name}",
                                                "exe": str(exe_path),
                                                "plugins": str(Path(os.environ.get("APPDATA", "")) / "SketchUp" / f"SketchUp {subkey_name}" / "SketchUp" / "Plugins"),
                                                "localappdata": str(Path(os.environ.get("LOCALAPPDATA", "")) / "SketchUp" / f"SketchUp {subkey_name}" / "SketchUp")
                                            })
                                    except WindowsError:
                                        pass
                            except WindowsError:
                                break
                except WindowsError:
                    pass

        # Deduplicate by exe path
        seen = set()
        unique = []
        for item in found:
            if item["exe"] not in seen:
                seen.add(item["exe"])
                unique.append(item)
                
        return unique

class PipelineRunner:
    def __init__(self, sketchup_info: Dict[str, str], work_dir: str):
        self.su_info = sketchup_info
        self.work_dir = Path(work_dir)
        self.config_file = self.work_dir / "pipeline_config.json"
        self.status_file = self.work_dir / "pipeline_status.json"
        self.log_file = self.work_dir / "pipeline_ruby.log"
        self.plugin_path = Path(self.su_info["plugins"]) / "skp_pipeline_bridge.rb"
        self.process = None

    def create_ruby_script(self):
        """Generates the Ruby bridge script to run inside SketchUp."""
        from ruby_template import RUBY_BRIDGE_CODE
        
        cfg_path_esc = str(self.config_file).replace("\\", "/")
        status_path_esc = str(self.status_file).replace("\\", "/")
        log_path_esc = str(self.log_file).replace("\\", "/")
        
        code = RUBY_BRIDGE_CODE.replace("{{CONFIG_PATH}}", cfg_path_esc)
        code = code.replace("{{STATUS_PATH}}", status_path_esc)
        code = code.replace("{{LOG_PATH}}", log_path_esc)
        
        # Ensure plugins dir exists
        self.plugin_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.plugin_path, "w", encoding="utf-8") as f:
            f.write(code)

    def write_config(self, source_skp: str, do_optimize: bool, do_architecture: bool, do_furniture: bool):
        config_data = {
            "source_skp": str(Path(source_skp).resolve()).replace("\\", "/"),
            "do_optimize": do_optimize,
            "do_architecture": do_architecture,
            "do_furniture": do_furniture,
            "status_file": str(self.status_file).replace("\\", "/"),
            "log_file": str(self.log_file).replace("\\", "/")
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        # Initialize status file
        initial_status = {
            "status": "starting",
            "progress": 5,
            "message": "Inicializando SketchUp...",
            "log": ["[00:00:00] Pipeline iniciado pela ferramenta."]
        }
        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(initial_status, f, indent=2)

    def launch(self, source_skp: str):
        """Spawns SketchUp with the target file."""
        self.create_ruby_script()
        
        cmd = [self.su_info["exe"], str(Path(source_skp).resolve())]
        self.process = subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )
        return self.process

    def get_status(self) -> Dict:
        """Reads the latest status written by the Ruby script."""
        if self.status_file.exists():
            try:
                with open(self.status_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"status": "running", "progress": 10, "message": "Carregando modelo no SketchUp...", "log": []}

    def stop(self):
        """Force terminates the SketchUp process if still active."""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        self.cleanup()

    def cleanup(self):
        """Removes the temporary plugin and config files."""
        try:
            if self.plugin_path.exists():
                self.plugin_path.unlink()
        except Exception:
            pass
        try:
            if self.config_file.exists():
                self.config_file.unlink()
        except Exception:
            pass
        try:
            if self.status_file.exists():
                self.status_file.unlink()
        except Exception:
            pass
