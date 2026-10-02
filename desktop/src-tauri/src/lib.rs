// Entry point shared by desktop, iOS and Android. Keeping it in the library
// rather than main.rs is what lets the mobile targets link against it later
// without restructuring the project.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .run(tauri::generate_context!())
        .expect("error while running microtranslate");
}
