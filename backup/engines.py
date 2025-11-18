import os

def iter_files_under(root_dir):
    for base, dirs, files in os.walk(root_dir):
        for f in files:
            src = os.path.join(base, f)
            rel = os.path.relpath(src, root_dir)
            yield src, rel

def count_total_files(existing_sources):
    total = 0
    for s in existing_sources:
        for _ in iter_files_under(s):
            total += 1
    return total

def is_unchanged(src_file, dst_file, mtime_slop=1.0):
    try:
        if not os.path.exists(dst_file):
            return False
        s_stat = os.stat(src_file)
        d_stat = os.stat(dst_file)
        if s_stat.st_size != d_stat.st_size:
            return False
        return abs(s_stat.st_mtime - d_stat.st_mtime) <= mtime_slop
    except Exception:
        return False
