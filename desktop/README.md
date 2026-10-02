# microtranslate desktop

Tauri 2 wrapper around the same UI the web version uses. Tauri was chosen over
Electron because it can target iOS and Android from this same project later;
Electron cannot.

## Build (Windows)

Needs Rust and the MSVC toolchain, plus WebView2 (present on Windows 11).

    cargo install tauri-cli --version "^2" --locked
    cd src-tauri
    cargo tauri icon icons/icon.png
    cargo tauri build

Produces an .msi and an NSIS .exe installer in
`src-tauri/target/release/bundle/`.

## Mobile, later

The app entry point lives in `src-tauri/src/lib.rs` rather than `main.rs`,
which is what the iOS and Android targets link against:

    cargo tauri android init
    cargo tauri ios init

## What this does and does not change

It packages the app: own window, own icon, no browser, no service worker, and
the models are fetched once on first run rather than per visit.

It does NOT make inference faster. The webview still runs the models in
WebAssembly, exactly as the browser does. Native speed would mean moving
inference into Rust (the `ort` crate) instead of Transformers.js, which is a
separate piece of work.
