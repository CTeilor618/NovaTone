import sys
import json

def handle_command(command, data):
    if command == "ping":
        return {"status": "ok", "message": "Python conectado"}
    elif command == "ocr_image":
        from ocr import convert_to_xml
        image_path = data.get("path", "")
        output_dir = data.get("output", "/tmp")
        return convert_to_xml(image_path, output_dir)
    elif command == "get_fingering":
        from fingering import analyze_xml
        instrument = data.get("instrument", "trompeta")
        xml = data.get("xml", "")
        return analyze_xml(xml, instrument)
    elif command == "export_pdf":
        from exporter import export_pdf
        return export_pdf(
            xml_content    = data.get("xml", ""),
            output_path    = data.get("path", "output.pdf"),
            fingerings     = data.get("fingerings", []),
            show_numbers   = data.get("showNumbers", True),
            show_note_names= data.get("showNoteNames", True),
            show_zeros     = data.get("showZeros", True),
            font_size      = data.get("diagramSize", 18),
        )
    return {"error": "Comando no reconocido"}

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "ping"
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        data = json.loads(open(sys.argv[idx+1]).read())
    elif len(sys.argv) > 2:
        data = json.loads(sys.argv[2])
    else:
        data = {}
    result = handle_command(command, data)
    print(json.dumps(result))