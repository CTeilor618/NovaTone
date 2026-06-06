use std::process::Command;
use std::path::PathBuf;
use std::fs;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
async fn read_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(&path).map_err(|e| e.to_string())
}

#[tauri::command]
async fn run_python(command: String, data: String) -> Result<String, String> {
    let mut script_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    script_path.push("../python-backend/main.py");

    // Escribir data a archivo temporal para evitar limite de argumentos
    let tmp_path = std::env::temp_dir().join("novatone_data.json");
    fs::write(&tmp_path, &data).map_err(|e| e.to_string())?;

    let output = Command::new("python3")
        .arg(&script_path)
        .arg(&command)
        .arg("--file")
        .arg(&tmp_path)
        .output()
        .map_err(|e| e.to_string())?;

    let _ = fs::remove_file(&tmp_path);

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![greet, read_file, run_python])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
