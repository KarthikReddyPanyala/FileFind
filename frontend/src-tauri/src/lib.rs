use std::os::windows::process::CommandExt;
use std::process::Command;
use std::sync::Mutex;
use tauri::Manager;

struct BackendProcess(Mutex<Option<std::process::Child>>);

#[tauri::command]
fn open_file(path: String) {
    #[cfg(target_os = "windows")]
    Command::new("cmd")
        .args(["/C", "start", "", &path])
        .creation_flags(0x08000000)
        .spawn()
        .ok();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let backend_path = if cfg!(debug_assertions) {
                std::path::PathBuf::from("C:\\Users\\karth\\filefind\\backend\\dist\\filefind-backend.exe")
            } else {
                app.path().resource_dir()
                    .expect("Failed to get resource dir")
                    .join("filefind-backend.exe")
            };

            let backend = Command::new(backend_path)
                .creation_flags(0x08000000)
                .spawn()
                .expect("Failed to start backend");

            app.manage(BackendProcess(Mutex::new(Some(backend))));
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if let Some(state) = window.try_state::<BackendProcess>() {
                    if let Ok(mut child) = state.0.lock() {
                        if let Some(mut process) = child.take() {
                            process.kill().ok();
                        }
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![open_file])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}