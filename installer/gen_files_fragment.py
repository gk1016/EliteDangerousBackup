import os, uuid, pathlib

SRC = pathlib.Path(r"..\dist\EliteDangerousBackup").resolve()
OUT = pathlib.Path("FilesFragment.wxs").resolve()

def wix_guid():
    return "{" + str(uuid.uuid4()).upper() + "}"

def main():
    items = []
    for root, _, files in os.walk(SRC):
        for f in files:
            p = pathlib.Path(root, f)
            # Skip main exe; Product.wxs already declares it as KeyPath
            if p.name.lower() == "elitedangerousbackup.exe":
                continue
            rel = p.relative_to(SRC)
            comp_id = "EDB_" + "_".join(rel.parts).replace(".", "_").replace("-", "_")
            file_id = comp_id + "_file"
            items.append((comp_id, file_id, str(p)))

    with open(OUT, "w", encoding="utf-8") as w:
        w.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        w.write('<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">\n')
        w.write('  <Fragment>\n')
        w.write('    <ComponentGroup Id="EDB_OtherFiles">\n')
        for comp_id, file_id, fullpath in items:
            w.write(f'      <Component Id="{comp_id}" Directory="INSTALLDIR" Guid="{wix_guid()}">\n')
            w.write(f'        <File Id="{file_id}" Source="$(var.SourceDir)\\{os.path.relpath(fullpath, SRC)}" />\n')
            w.write('      </Component>\n')
        w.write('    </ComponentGroup>\n')
        w.write('  </Fragment>\n')
        w.write('</Wix>\n')

if __name__ == "__main__":
    main()
