import subprocess
import os
import zipfile

def convert_to_xml(image_path: str, output_dir: str) -> dict:
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        result = subprocess.run([
            "flatpak", "run", "org.audiveris.audiveris",
            "-batch", "-export",
            "-output", output_dir,
            image_path
        ], capture_output=True, text=True, timeout=120)
        
        base = os.path.splitext(os.path.basename(image_path))[0]
        mxl_path = os.path.join(output_dir, base + ".mxl")
        
        if not os.path.exists(mxl_path):
            return {"error": "Audiveris no generó archivo MXL. " + result.stderr}
        
        xml_dir = os.path.join(output_dir, base + "_xml")
        os.makedirs(xml_dir, exist_ok=True)
        
        with zipfile.ZipFile(mxl_path, 'r') as z:
            z.extractall(xml_dir)
        
        xml_path = os.path.join(xml_dir, base + ".xml")
        if not os.path.exists(xml_path):
            for f in os.listdir(xml_dir):
                if f.endswith(".xml") and not f.startswith("META"):
                    xml_path = os.path.join(xml_dir, f)
                    break
        
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        return {"status": "ok", "xml": xml_content}
        
    except Exception as e:
        return {"error": str(e)}