<script lang="ts">
  import { save } from "@tauri-apps/plugin-dialog";
  import { open as openDialog } from "@tauri-apps/plugin-dialog";
  import { invoke } from "@tauri-apps/api/core";
  import ScoreRenderer from "../components/score/ScoreRenderer.svelte";

  let openCategory = $state("METALES");
  let showNumbers = $state(true);
  let showNoteNames = $state(true);
  let showZeros = $state(true);
  let showDiagrams = $state(false);
  let diagramSize = $state(28);
  let activeFile = $state("Sin archivo");
  let xmlContent = $state("");
  let instrument = $state("trompeta");
  let fingerings: {note: string, note_esp: string, fingering: string}[] = $state([]);
  let songTitle = $state("");

  async function importFile() {
    const path = await openDialog({
      filters: [{ name: "MusicXML", extensions: ["xml", "musicxml", "mxl"] }]
    });
    if (typeof path === "string") {
      activeFile = path.split("/").pop() ?? path;
      xmlContent = await invoke("read_file", { path });
      await analyzeFingering();
    }
  }

  async function importImage() {
    const path = await openDialog({
      filters: [{ name: "Imagen o PDF", extensions: ["jpg", "jpeg", "png", "pdf", "bmp", "tiff", "webp"] }]
    });
    if (typeof path === "string") {
      activeFile = path.split("/").pop() ?? path;
      const result = await invoke<string>("run_python", {
        command: "ocr_image",
        data: JSON.stringify({ path, output: "/home/cesar/resultado" })
      });
      const parsed = JSON.parse(result);
      if (parsed.status === "ok") {
        xmlContent = parsed.xml;
        await analyzeFingering();
      } else {
        alert("Error OCR: " + parsed.error);
      }
    }
  }

  async function analyzeFingering() {
    if (!xmlContent) return;
    try {
      const result = await invoke<string>("run_python", {
        command: "get_fingering",
        data: JSON.stringify({ instrument, xml: xmlContent })
      });
      const parsed = JSON.parse(result);
      if (parsed.notes) {
        fingerings = parsed.notes;
        songTitle = parsed.title || "";
      }
    } catch(e) {
      console.error("Error:", e);
    }
  }

  async function exportPDF() {
    if (!xmlContent) { alert("Primero importa una partitura"); return; }
    const path = await save({
      filters: [{ name: "PDF", extensions: ["pdf"] }],
      defaultPath: activeFile.replace(".xml", ".pdf")
    });
    if (path) {
      const result = await invoke<string>("run_python", {
        command: "export_pdf",
        data: JSON.stringify({ xml: xmlContent, path, fingerings, showNumbers, showNoteNames, showZeros, showDiagrams, diagramSize, instrument })
      });
      const parsed = JSON.parse(result);
      if (parsed.status === "ok") {
        alert("PDF exportado: " + parsed.path);
      } else {
        alert("Error: " + parsed.error);
      }
    }
  }
</script>

<div class="layout">
  <header class="topbar">
    <div class="topbar-left">
      <span class="logo-text">NovaTone</span>
      <span class="file-name">{activeFile}</span>
    </div>
    <div class="topbar-right">
      <button class="btn-ghost {showNumbers ? 'active' : ''}" onclick={() => showNumbers = !showNumbers}>
        🔢 {showNumbers ? "Ocultar números" : "Números"}
      </button>
      <button class="btn-ghost {showZeros ? 'active' : ''}" onclick={() => showZeros = !showZeros}>
        0️⃣ {showZeros ? "Ocultar ceros" : "Ceros"}
      </button>
      <button class="btn-ghost {showNoteNames ? 'active' : ''}" onclick={() => showNoteNames = !showNoteNames}>
        🎵 {showNoteNames ? "Ocultar notas" : "Notas"}
      </button>
      <button class="btn-ghost {showDiagrams ? 'active' : ''}" onclick={() => showDiagrams = !showDiagrams}>
        🖐 {showDiagrams ? "Ocultar dedos" : "Dedos"}
      </button>
      {#if showDiagrams}
        <div class="slider-wrap">
          <span>Tam.</span>
          <input type="range" min="18" max="60" bind:value={diagramSize} />
          <span>{diagramSize}px</span>
        </div>
      {/if}
      <button class="btn-ghost" onclick={importImage}>📷 Imagen/PDF</button>
      <button class="btn-ghost" onclick={importFile}>Importar</button>
      <button class="btn-primary" onclick={exportPDF}>Exportar</button>
    </div>
  </header>

  <div class="workspace">
    <aside class="sidebar">
      <p class="sidebar-label">Archivos</p>
      <p class="sidebar-label">Instrumentos</p>
      <p class="sidebar-label">IA</p>
    </aside>

    <main class="score-area">
      {#if songTitle}
        <div class="song-title-bar">{songTitle}</div>
      {/if}
      {#if xmlContent}
        <ScoreRenderer
          {xmlContent}
          fingerings={fingerings}
          {instrument}
          {showNumbers}
          {showNoteNames}
          {showDiagrams}
          {showZeros}
          {diagramSize}
        />
      {:else}
        <div class="score-empty">
          <p class="score-hint">Importa una partitura para comenzar</p>
          <button class="btn-primary" onclick={importFile}>+ Nuevo proyecto</button>
        </div>
      {/if}
    </main>

    <aside class="panel-right">
      <p class="sidebar-title">Instrumento</p>
      {#each Object.entries({
        "METALES": ["trompeta", "tuba", "baritono", "trombon", "bajo", "fliscorno", "bombardino", "corno_frances"],
        "MADERAS": ["flauta", "flauta_dulce", "clarinete", "saxofon_soprano", "saxofon_alto", "saxofon_tenor", "saxofon_baritono"],
        "ANDINOS": ["zampoña", "quena", "tarka", "pinkillo", "moseño"],
      }) as [categoria, instrumentos]}
        <button class="categoria-btn {openCategory === categoria ? 'open' : ''}"
          onclick={() => openCategory = openCategory === categoria ? '' : categoria}>
          <span>{openCategory === categoria ? '▼' : '►'} {categoria}</span>
        </button>
        {#if openCategory === categoria}
          <div class="instrument-list">
            {#each instrumentos as inst}
              <button class="instrument-btn {instrument === inst ? 'active' : ''}"
                onclick={() => { instrument = inst; analyzeFingering(); }}>
                {inst.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </button>
            {/each}
          </div>
        {/if}
      {/each}
      {#if fingerings.length > 0}
        <p class="sidebar-title">Digitaciones</p>
        {#each fingerings as f}
          <div class="fingering-item">
            <span class="note-name">{f.note_esp || f.note}</span>
            <span class="fingering-number">{f.fingering}</span>
          </div>
        {/each}
      {/if}
    </aside>
  </div>

  <footer class="statusbar">
    <span>NovaTone v0.1.0</span>
    <span>Motor IA: listo</span>
  </footer>
</div>

<style>
  .layout { display: flex; flex-direction: column; height: 100vh; background-color: var(--nt-bg); color: var(--nt-text); font-family: 'Inter', sans-serif; }
  .topbar { display: flex; justify-content: space-between; align-items: center; min-height: 48px; padding: 4px 20px; background-color: var(--nt-panel); border-bottom: 1px solid #1E2A45; flex-wrap: wrap; gap: 6px; }
  .topbar-left { display: flex; align-items: center; gap: 16px; }
  .logo-text { font-size: 15px; font-weight: 600; color: var(--nt-primary); letter-spacing: 0.05em; }
  .file-name { font-size: 13px; color: var(--nt-muted); }
  .topbar-right { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .slider-wrap { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--nt-muted); }
  .slider-wrap input { width: 80px; }
  .workspace { display: flex; flex: 1; min-height: 0; overflow: hidden; }
  .sidebar { width: 200px; background-color: var(--nt-panel); border-right: 1px solid #1E2A45; padding: 16px 12px; display: flex; flex-direction: column; gap: 8px; }
  .panel-right { width: 220px; background-color: var(--nt-panel); border-left: 1px solid #1E2A45; padding: 16px 12px; display: flex; flex-direction: column; gap: 8px; overflow-y: scroll; height: 100%; }
  .sidebar-label { font-size: 12px; color: var(--nt-muted); padding: 8px 10px; border-radius: 6px; cursor: pointer; }
  .sidebar-label:hover { background-color: #1E2A45; color: var(--nt-text); }
  .score-area { flex: 1; min-height: 0; background-color: white; overflow-y: auto; }
  .score-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 16px; }
  .score-hint { font-size: 14px; color: var(--nt-muted); }
  .statusbar { height: 28px; background-color: var(--nt-panel); border-top: 1px solid #1E2A45; display: flex; justify-content: space-between; align-items: center; padding: 0 16px; font-size: 11px; color: var(--nt-muted); }
  .btn-primary { background-color: var(--nt-primary); color: #0B1020; border: none; padding: 6px 16px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; }
  .btn-primary:hover { opacity: 0.85; }
  .btn-ghost { background-color: transparent; color: var(--nt-text); border: 1px solid #1E2A45; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; }
  .btn-ghost:hover { border-color: var(--nt-primary); color: var(--nt-primary); }
  .btn-ghost.active { border-color: var(--nt-primary); color: var(--nt-primary); }
  .sidebar-title { font-size: 11px; color: var(--nt-muted); text-transform: uppercase; letter-spacing: 0.08em; padding: 8px 10px 4px; }
  .instrument-list { display: flex; flex-direction: column; gap: 4px; }
  .instrument-btn { background-color: #1E2A45; color: var(--nt-muted); border: 1px solid #2A3A55; border-radius: 6px; padding: 8px 12px; font-size: 13px; text-align: left; cursor: pointer; transition: all 0.15s; }
  .instrument-btn:hover { border-color: var(--nt-primary); color: var(--nt-text); }
  .instrument-btn.active { background-color: var(--nt-primary); color: #0B1020; border-color: var(--nt-primary); font-weight: 500; }
  .fingering-item { display: flex; justify-content: space-between; align-items: center; padding: 4px 10px; border-radius: 4px; }
  .fingering-item:hover { background-color: #1E2A45; }
  .note-name { font-size: 12px; color: var(--nt-text); }
  .fingering-number { font-size: 14px; font-weight: 600; color: var(--nt-primary); font-family: 'JetBrains Mono', monospace; }
  .categoria-btn { background-color: #0B1020; color: var(--nt-primary); border: 1px solid #1E2A45; border-radius: 6px; padding: 8px 12px; font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-align: left; cursor: pointer; width: 100%; margin-top: 4px; }
  .categoria-btn:hover { border-color: var(--nt-primary); }
  .categoria-btn.open { border-color: var(--nt-primary); }
  .song-title-bar { text-align: center; font-size: 16px; font-weight: 600; color: #0B1020; padding: 12px; background-color: white; border-bottom: 1px solid #eee; }
</style>
