import os
import shutil
import threading
import traceback
import zipfile
from datetime import datetime

from backup.engines import iter_files_under, count_total_files, is_unchanged
from windows import win_longpath

class BackupWorker(threading.Thread):
    """
    Background backup worker:
      - zip_mode: write a single ZIP archive
      - else: mirror to a folder (optional incremental)
    Emits UI updates via ui_queue: ('log'| 'progress' | 'done' | 'failed' | 'cancelled', payload)
    """
    def __init__(self, sources, dest_root, ui_queue, zip_mode=False, incremental=True):
        super().__init__(daemon=True)
        self.sources = sources
        self.dest_root = dest_root
        self.ui_queue = ui_queue
        self.zip_mode = zip_mode
        self.incremental = incremental if not zip_mode else False
        self.stop_flag = False
        self.errors = []

    def log(self, msg): self.ui_queue.put(("log", msg))
    def set_progress(self, done, total): self.ui_queue.put(("progress", (done, total)))

    def _mk_backup_target(self):
        computer = os.environ.get("COMPUTERNAME", "UNKNOWNPC")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.zip_mode:
            return os.path.join(self.dest_root, f"EliteDangerousBackup_{computer}_{ts}.zip")
        else:
            dst = os.path.join(self.dest_root, f"EliteDangerousBackup_{computer}_{ts}")
            os.makedirs(dst, exist_ok=True)
            return dst

    def run(self):
        try:
            existing = [s for s in self.sources if s and os.path.isdir(s)]
            missing = [s for s in self.sources if not s or not os.path.isdir(s)]
            for m in missing: self.log(f"[WARN] Source not found or unset (skipping): {m}")

            total_files = count_total_files(existing)
            self.set_progress(0, max(total_files, 1))
            target = self._mk_backup_target()

            if self.zip_mode:
                self._run_zip(existing, target, total_files)
            else:
                self._run_mirror(existing, target, total_files)

            self.log("Backup completed successfully. No errors reported." if not self.errors
                     else f"Completed with {len(self.errors)} error(s). See log for details.")
            self.ui_queue.put(("done", target))

        except KeyboardInterrupt:
            self.log("Backup cancelled by user.")
            self.ui_queue.put(("cancelled", None))
        except Exception as e:
            tb = traceback.format_exc()
            self.log(f"Fatal error: {e}\n{tb}")
            self.ui_queue.put(("failed", str(e)))

    # ZIP
    def _run_zip(self, existing_sources, archive_path, total_files):
        self.log(f"ZIP mode: {archive_path}")
        log_lines = []; count = 0
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for src_root in existing_sources:
                parent = os.path.basename(os.path.dirname(src_root)); leaf = os.path.basename(src_root)
                tagged_base = f"{parent}__{leaf}" if parent else leaf
                self.log(f"Zipping: {src_root} -> /{tagged_base}/")
                for src_file, rel_path in iter_files_under(src_root):
                    if self.stop_flag: raise KeyboardInterrupt
                    arcname = os.path.join(tagged_base, rel_path).replace("\\", "/")
                    try:
                        zf.write(win_longpath(src_file), arcname)
                        log_lines.append(f"ZIP: {src_file} -> {arcname}")
                    except Exception as e:
                        err = f"[ERROR] ZIP {src_file} -> {arcname}: {e}"
                        self.errors.append(err); log_lines.append(err); self.log(err)
                    count += 1
                    if count % 5 == 0 or count == total_files: self.set_progress(count, max(total_files, 1))
            zf.writestr("backup_log.txt", "\n".join(log_lines))

    # MIRROR
    def _run_mirror(self, existing_sources, backup_dir, total_files):
        self.log(f"Mirror mode: {backup_dir}")
        log_path = os.path.join(backup_dir, "backup_log.txt")
        done = 0
        with open(log_path, "w", encoding="utf-8") as lf:
            lf.write(f"Elite Dangerous Backup Log (Mirror) - {datetime.now().isoformat()}\n")
            lf.write(f"Destination: {backup_dir}\n")
            lf.write(f"Incremental: {'ON' if self.incremental else 'OFF'}\n\n")
            for src_root in existing_sources:
                parent = os.path.basename(os.path.dirname(src_root)); leaf = os.path.basename(src_root)
                tagged_base = f"{parent}__{leaf}" if parent else leaf
                dest_base = os.path.join(backup_dir, tagged_base)
                self.log(f"Copying: {src_root} -> {dest_base}")
                os.makedirs(dest_base, exist_ok=True)

                for src_file, rel_path in iter_files_under(src_root):
                    if self.stop_flag: raise KeyboardInterrupt
                    dest_file = os.path.join(dest_base, rel_path)
                    dest_dir = os.path.dirname(dest_file)
                    try:
                        if self.incremental and os.path.exists(dest_file) and is_unchanged(src_file, dest_file):
                            lf.write(f"SKIP: {src_file}\n")
                        else:
                            os.makedirs(dest_dir, exist_ok=True)
                            shutil.copy2(win_longpath(src_file), win_longpath(dest_file))
                            lf.write(f"COPY: {src_file} -> {dest_file}\n")
                    except Exception as e:
                        err = f"[ERROR] {src_file} -> {dest_file}: {e}"
                        self.errors.append(err); lf.write(err + "\n"); self.log(err)
                    done += 1
                    if done % 5 == 0 or done == total_files: self.set_progress(done, max(total_files, 1))
