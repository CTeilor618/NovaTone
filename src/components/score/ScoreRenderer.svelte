<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { OpenSheetMusicDisplay } from "opensheetmusicdisplay";

  let { xmlContent, fingerings = [], instrument = "trompeta", showNumbers = true, showNoteNames = true, showZeros = true, showDiagrams = false, diagramSize = 28 } = $props<{ 
    xmlContent: string,
    fingerings: {note: string, note_esp: string, fingering: string}[],
    instrument: string,
    showNumbers: boolean,
    showNoteNames: boolean,
    showZeros: boolean,
    showDiagrams: boolean,
    diagramSize: number
  }>();

  let container: HTMLDivElement;
  let osmd: any;
  let ready = $state(false);
  let rendered = $state(false);

  function getInstrumentType(inst: string): string {
    const andinos = ["zampoña","quena","tarka","pinkillo","moseño"];
    const maderas = ["flauta","flauta_dulce","clarinete","saxofon_soprano","saxofon_alto","saxofon_tenor","saxofon_baritono"];
    if (andinos.includes(inst)) return "andino";
    if (maderas.includes(inst)) return "madera";
    if (inst === "trombon") return "trombon";
    return "metal";
  }

  function svgPistones(fingering: string, size: number): string {
    const pressed = fingering.split("-").map(s => s.trim());
    const r = size * 0.38;
    const cx = size / 2;
    const gap = size * 1.15;
    const totalH = gap * 3 + size * 0.4;
    const positions = [
      { label: "1", cy: size * 0.5 },
      { label: "2", cy: size * 0.5 + gap },
      { label: "3", cy: size * 0.5 + gap * 2 },
    ];
    let circles = positions.map(p => {
      const isPressed = pressed.includes(p.label);
      const fill = isPressed ? "#000" : "#fff";
      return `<circle cx="${cx}" cy="${p.cy}" r="${r}" fill="${fill}" stroke="#000" stroke-width="1.5"/>
              <text x="${cx}" y="${p.cy + r * 0.4}" text-anchor="middle" font-size="${r * 0.9}" fill="${isPressed ? '#fff' : 'transparent'}" font-family="sans-serif" font-weight="bold">${isPressed ? p.label : ""}</text>`;
    }).join("");
    return `<svg width="${size}" height="${totalH}" xmlns="http://www.w3.org/2000/svg">${circles}</svg>`;
  }

  function svgAgujeros(fingering: string, size: number, numHoles: number): string {
    const parts = fingering.split("-");
    const r = size * 0.36;
    const cx = size / 2;
    const gap = size * 1.1;
    const totalH = gap * numHoles + size * 0.4;
    let circles = "";
    for (let i = 0; i < numHoles; i++) {
      const val = parts[i] || "0";
      const cy = size * 0.5 + gap * i;
      const fill = val === "0" ? "#fff" : "#000";
      circles += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${fill}" stroke="#000" stroke-width="1.5"/>`;
    }
    return `<svg width="${size}" height="${totalH}" xmlns="http://www.w3.org/2000/svg">${circles}</svg>`;
  }

  function svgTrombon(fingering: string, size: number): string {
    const pos = fingering.replace("Pos.", "");
    return `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="4" width="${size-8}" height="${size-8}" rx="4" fill="#000"/>
      <text x="${size/2}" y="${size/2 + size*0.15}" text-anchor="middle" font-size="${size*0.38}" fill="#fff" font-family="sans-serif" font-weight="bold">${pos}</text>
    </svg>`;
  }

  function getDiagram(fingering: string, inst: string, size: number): string {
    if (!fingering || fingering === "?") return "";
    const type = getInstrumentType(inst);
    if (type === "trombon") return svgTrombon(fingering, size);
    if (type === "andino" || type === "madera") return svgAgujeros(fingering, size, 7);
    return svgPistones(fingering, size);
  }

  onMount(() => {
    setTimeout(() => {
      osmd = new OpenSheetMusicDisplay(container, {
        autoResize: true,
        darkMode: false,
        drawingParameters: "default",
        backend: "svg",
      });
      ready = true;
    }, 200);
  });

  $effect(() => {
    if (ready && osmd && xmlContent) {
      osmd.clear();
      container.scrollTop = 0;
      rendered = false;
      osmd.load(xmlContent).then(() => {
        osmd.render();
        rendered = true;
        setTimeout(() => addFingeringLabels(), 900);
      }).catch((e: Error) => console.error("OSMD error:", e));
    }
  });

  $effect(() => {
    if (rendered) {
      const _ = showNumbers + showNoteNames + String(showZeros) + String(showDiagrams) + diagramSize + instrument + fingerings.length;
      setTimeout(() => addFingeringLabels(), 100);
    }
  });

  function addFingeringLabels() {
    container.querySelectorAll(".fingering-label,.note-name-label,.diagram-label,.system-diagram").forEach(el => el.remove());
    if (!fingerings.length) return;
    const svg = container.querySelector("svg");
    if (!svg) return;

    // Usar posición relativa al contenedor con scroll
    const cRect = container.getBoundingClientRect();
    const scrollTop = 0; // posiciones calculadas sin scroll

    const allPaths = Array.from(svg.querySelectorAll("path[fill='#000000'], path[fill='black'], path[fill='#000']"));
    const noteHeads = allPaths.filter(path => {
      const r = path.getBoundingClientRect();
      return r.width >= 6 && r.width <= 18 && r.height >= 6 && r.height <= 18;
    });

    noteHeads.sort((a, b) => {
      const ra = a.getBoundingClientRect();
      const rb = b.getBoundingClientRect();
      const rowDiff = Math.round((ra.top - rb.top) / 30);
      if (rowDiff !== 0) return rowDiff;
      return ra.left - rb.left;
    });

    const unique: Element[] = [];
    for (const path of noteHeads) {
      const r = path.getBoundingClientRect();
      const isDuplicate = unique.some(u => {
        const ur = u.getBoundingClientRect();
        return Math.abs(ur.left - r.left) < 4 && Math.abs(ur.top - r.top) < 4;
      });
      if (!isDuplicate) unique.push(path);
    }

    // Grupos por sistema (fila del pentagrama)
    const systems: {bottom: number, notes: {x: number, index: number}[]}[] = [];

    unique.forEach((notehead, index) => {
      if (index >= fingerings.length) return;
      const f = fingerings[index];
      if (!f) return;

      const r = notehead.getBoundingClientRect();
      // Posición absoluta dentro del contenedor (incluyendo scroll)
      const x = r.left - cRect.left + r.width / 2;
      const yAbs = r.top - cRect.top + scrollTop;
      const yTop = yAbs - 20;
      const yBottom = yAbs + r.height + 5;
      const noteBottom = yAbs + r.height;

      // Agrupar en sistema
      let system = systems.find(s => Math.abs(s.bottom - noteBottom) < 150);
      if (!system) {
        system = { bottom: noteBottom, notes: [] };
        systems.push(system);
      }
      if (noteBottom > system.bottom) system.bottom = noteBottom;
      system.notes.push({ x, index });

      // Digitación arriba
      if (showNumbers && f.fingering && f.fingering !== "?" && (f.fingering !== "0" || showZeros) ) {
        const label = document.createElement("div");
        label.className = "fingering-label";
        label.textContent = f.fingering;
        label.style.cssText = `position:absolute;left:${x}px;top:${yTop}px;transform:translateX(-50%);font-size:10px;font-weight:800;color:#000;font-family:monospace;pointer-events:none;z-index:999;background:white;padding:1px 2px;border-radius:2px;border:1px solid #000;white-space:nowrap;line-height:1.2;`;
        container.appendChild(label);
      }

      // Nombre de nota
      if (showNoteNames && f.note_esp) {
        const noteLabel = document.createElement("div");
        noteLabel.className = "note-name-label";
        noteLabel.textContent = f.note_esp;
        noteLabel.style.cssText = `position:absolute;left:${x}px;top:${yBottom}px;transform:translateX(-50%);font-size:10px;font-weight:900;color:#000;font-family:sans-serif;pointer-events:none;z-index:999;white-space:nowrap;line-height:1.2;`;
        container.appendChild(noteLabel);
      }
      // Diagrama debajo de la nota
      if (showDiagrams && f.fingering && f.fingering !== "?") {
        const svgStr = getDiagram(f.fingering, instrument, diagramSize);
        if (svgStr) {
          const diagLabel = document.createElement("div");
          diagLabel.className = "system-diagram";
          const diagTop = yBottom + (showNoteNames ? 14 : 0);
          diagLabel.style.cssText = `position:absolute;left:${x}px;top:${diagTop}px;transform:translateX(-50%);pointer-events:none;z-index:998;`;
          diagLabel.innerHTML = svgStr;
          container.appendChild(diagLabel);
        }
      }
    });
  }

  onDestroy(() => {
    if (osmd) osmd.clear();
  });
</script>

<div class="score-wrapper">
  <div bind:this={container} class="renderer"></div>
</div>

<style>
  .score-wrapper { width: 100%; height: 100%; background-color: white; overflow-y: auto; overflow-x: hidden; position: relative; }
  .renderer { width: 100%; min-height: 600px; padding: 24px; background-color: white; position: relative; overflow: visible; }
</style>
