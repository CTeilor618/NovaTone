import sys
import json
import re
import verovio
try:
    import cairosvg
    CAIRO_OK = True
except Exception:
    CAIRO_OK = False



def get_instrument_type(instrument: str) -> str:
    andinos = ["zampoña","quena","tarka","pinkillo","moseño"]
    maderas = ["flauta","flauta_dulce","clarinete","saxofon_soprano",
               "saxofon_alto","saxofon_tenor","saxofon_baritono"]
    if instrument in andinos: return "andino"
    if instrument in maderas: return "madera"
    if instrument == "trombon": return "trombon"
    return "metal"

def svg_diagram(fingering: str, instrument: str, size: float) -> str:
    """Genera SVG de diagrama de digitacion en unidades viewBox"""
    if not fingering or fingering == "?": return ""
    itype = get_instrument_type(instrument)
    
    if itype == "trombon":
        pos = fingering.replace("Pos.", "")
        w, h = size, size
        return (f'<rect x="0" y="0" width="{w:.0f}" height="{h:.0f}" rx="{h*0.15:.0f}" fill="#000"/>' 
                f'<text x="{w/2:.0f}" y="{h*0.7:.0f}" text-anchor="middle" ' 
                f'font-size="{h*0.5:.0f}" fill="#fff" font-family="sans-serif" ' 
                f'font-weight="bold">{pos}</text>')
    
    elif itype == "metal":
        parts = fingering.split("-")
        r = size * 0.38
        cx = size / 2
        gap = size * 1.15
        total_h = gap * 3 + size * 0.4
        result = []
        for idx, label in enumerate(["1","2","3"]):
            cy = size * 0.5 + gap * idx
            pressed = label in parts
            fill = "#000" if pressed else "#fff"
            stroke = "#000"
            result.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" ' 
                          f'fill="{fill}" stroke="{stroke}" stroke-width="{size*0.06:.0f}"/>')
            if pressed:
                result.append(f'<text x="{cx:.0f}" y="{cy+r*0.4:.0f}" ' 
                              f'text-anchor="middle" font-size="{r*0.9:.0f}" ' 
                              f'fill="#fff" font-family="sans-serif" font-weight="bold">{label}</text>')
        return "".join(result), total_h
    
    else:  # madera o andino
        parts = fingering.split("-")
        num_holes = 7 if itype in ["madera","andino"] else 6
        r = size * 0.36
        cx = size / 2
        gap = size * 1.1
        total_h = gap * num_holes + size * 0.4
        result = []
        for idx in range(num_holes):
            val = parts[idx] if idx < len(parts) else "ab"
            cy = size * 0.5 + gap * idx
            filled = val not in ["ab","0","o",""]
            fill = "#000" if filled else "#fff"
            result.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" ' 
                          f'fill="{fill}" stroke="#000" stroke-width="{size*0.06:.0f}"/>')
        return "".join(result), total_h

def inject_fingerings_svg(svg_str, fingerings, show_numbers=True, show_note_names=True, show_zeros=False, font_size=18, show_diagrams=False, instrument="trompeta", diag_size=200):
    try:
        vb_match = re.search(r'viewBox="([^"]+)"', svg_str)
        if not vb_match:
            return svg_str
        vb = [float(v) for v in vb_match.group(1).split()]
        vb_w = vb[2]
        vb_h = vb[3]
        fn      = vb_w * 0.014
        fn2     = vb_w * 0.012
        off_top = vb_h * 0.0005
        off_bot = vb_h * 0.032
        box_h   = vb_h * 0.012
        box_pad = vb_w * 0.003
        sw      = vb_w * 0.001
        pattern = re.compile(r'class="notehead">\s*<use[^>]+transform="translate\(([0-9.\-]+),\s*([0-9.\-]+)\)')
        all_positions = [(float(m.group(1)), float(m.group(2))) for m in pattern.finditer(svg_str)]
        if not all_positions:
            return svg_str
        all_ys = sorted(set(p[1] for p in all_positions))
        # Extraer notas directamente de los staffs superiores (indices pares)
        # Los staffs en el SVG alternan: 0=superior, 1=inferior, 2=superior...
        staff_blocks = list(re.finditer(r'<g id="[^"]+" class="staff">', svg_str))
        pattern_nh_block = re.compile(
            r'class="notehead">\s*<use[^>]+transform="translate\(([0-9.\-]+),\s*([0-9.\-]+)\)'
        )

        # Detectar si hay 1 o 2 pentagramas por sistema
        # Obtener Y unico de cada staff
        staff_ys = []
        for m in staff_blocks:
            start = m.start()
            end = len(svg_str)
            block = svg_str[start:start+500]
            sy = re.search(r'path d="M\d+ (\d+)', block)
            staff_ys.append(int(sy.group(1)) if sy else 0)

        # Si todos los Y son iguales o muy parecidos = 1 pentagrama por sistema
        # Si hay 2 Y distintos alternando = 2 pentagramas (piano right+left)
        ys_unicos = sorted(set(staff_ys))
        # Detectar si es partitura de 1 pentagrama (trompeta) o 2 (piano)
        # En piano: los 2 Y se REPITEN alternando en cada sistema
        # En trompeta: cada sistema tiene UN solo Y distinto
        # Si el numero de Y unicos == numero de sistemas = mono
        # Si hay exactamente 2 Y que se alternan = piano
        if len(ys_unicos) == 1:
            es_mono = True
        elif len(ys_unicos) == 2:
            # Ver si alternan (piano) o son sistemas distintos (mono multi-sistema)
            patron_alternado = all(
                staff_ys[i] != staff_ys[i+1]
                for i in range(min(4, len(staff_ys)-1))
            )
            es_mono = not patron_alternado
        else:
            es_mono = True

        positions_ordered = []
        for i, m in enumerate(staff_blocks):
            # Si es monofónico (1 pentagrama), tomar todos los staffs
            # Si es piano (2 pentagramas), tomar solo los pares (superiores)
            if not es_mono and i % 2 != 0:
                continue
            start = m.start()
            end = staff_blocks[i+1].start() if i+1 < len(staff_blocks) else len(svg_str)
            block = svg_str[start:end]
            for nh in pattern_nh_block.finditer(block):
                positions_ordered.append((float(nh.group(1)), float(nh.group(2))))
        positions = [p for p in positions_ordered if p[0] > 400]
        positions.sort(key=lambda p: (round(p[1] / 200), p[0]))
        unique = []
        for p in positions:
            if not unique or abs(p[0] - unique[-1][0]) > 50 or abs(p[1] - unique[-1][1]) > 50:
                unique.append(p)
        texts = []
        for i, (x, y) in enumerate(unique):
            if i >= len(fingerings):
                break
            f = fingerings[i]
            if not f:
                continue
            fing = f.get("fingering", "")
            note_esp = f.get("note_esp", "")
            if show_numbers and fing and fing != "?":
                if not (fing == "0" and not show_zeros):
                    nchars = len(fing)
                    fn_use = fn if nchars <= 3 else fn*0.75 if nchars <= 5 else fn*0.55 if nchars <= 7 else fn*0.42
                    char_w = fn_use * 0.65
                    bw = len(fing) * char_w + box_pad * 2
                    bx = x - bw / 2
                    by = y - off_top - box_h
                    texts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{box_h:.1f}" rx="{box_h*0.25:.1f}" fill="white" stroke="#000" stroke-width="{sw:.1f}"/>')
                    texts.append(f'<text x="{x:.1f}" y="{by+box_h*0.82:.1f}" text-anchor="middle" font-size="{fn_use:.1f}" font-weight="bold" font-family="monospace" fill="#000">{fing}</text>')
            if show_note_names and note_esp:
                ty = y + off_bot + fn2
                texts.append(f'<text x="{x:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="{fn2:.1f}" font-weight="bold" font-family="sans-serif" fill="#000">{note_esp}</text>')

            # Diagrama de digitacion debajo de la nota
            if show_diagrams and fing and fing != "?":
                try:
                    diag_result = svg_diagram(fing, instrument, diag_size)
                    if diag_result and isinstance(diag_result, tuple):
                        diag_svg, diag_h = diag_result
                        diag_y = y + off_bot + fn2 + (fn2 * 4.0 if show_note_names and note_esp else fn2 * 2.0)
                        diag_x = x - diag_size / 2
                        texts.append(f'<g transform="translate({diag_x:.0f},{diag_y:.0f})">{diag_svg}</g>')
                except:
                    pass
        if texts:
            svg_str = svg_str.replace("</svg>", '<g class="fingerings">' + "\n".join(texts) + "</g></svg>")
        return svg_str
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return svg_str



def _svg_to_pdf_fallback(svg_bytes: bytes, output_path: str):
    """Fallback para Windows usando svglib + reportlab"""
    import tempfile, os
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    tmp = tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
    tmp.write(svg_bytes)
    tmp.close()
    drawing = svg2rlg(tmp.name)
    os.unlink(tmp.name)
    if drawing:
        renderPDF.drawToFile(drawing, output_path)

def export_pdf(xml_content, output_path, fingerings=[], show_numbers=True, show_note_names=True, show_zeros=False, font_size=18, show_diagrams=False, instrument="trompeta"):
    try:
        tk = verovio.toolkit()
        tk.setOptions({"pageWidth": 2159, "pageHeight": 2794, "scale": 30, "adjustPageHeight": False, "spacingSystem": 12, "spacingStaff": 8})
        tk.loadData(xml_content)
        page_count = tk.getPageCount()
        def process_page(page_num):
            svg = tk.renderToSVG(page_num)
            if fingerings and (show_numbers or show_note_names):
                svg = inject_fingerings_svg(svg, fingerings, show_numbers, show_note_names, show_zeros, font_size, show_diagrams, instrument)
            return svg
        if page_count == 1:
            svg_data = process_page(1).encode("utf-8")
        if CAIRO_OK:
            cairosvg.svg2pdf(bytestring=svg_data, write_to=output_path)
        else:
            _svg_to_pdf_fallback(svg_data, output_path)
        else:
            import tempfile, os
            from pypdf import PdfWriter
            tmp_files = []
            for page in range(1, page_count + 1):
                tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                svg_data = process_page(page).encode("utf-8")
                if CAIRO_OK:
                    cairosvg.svg2pdf(bytestring=svg_data, write_to=tmp.name)
                else:
                    _svg_to_pdf_fallback(svg_data, tmp.name)
                tmp.close()
                tmp_files.append(tmp.name)
            writer = PdfWriter()
            for p in tmp_files:
                writer.append(p)
            with open(output_path, "wb") as f:
                writer.write(f)
            for p in tmp_files:
                os.unlink(p)
        return {"status": "ok", "path": output_path}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    print(json.dumps(export_pdf(data.get("xml",""), data.get("path","output.pdf"), data.get("fingerings",[]), data.get("showNumbers",True), data.get("showNoteNames",True), data.get("showZeros",False), data.get("diagramSize",18), data.get("showDiagrams",False), data.get("instrument","trompeta"))))
