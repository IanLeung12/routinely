interface ImportMetaEnv {
  /** Pipeline API base URL. See .env.example. */
  readonly VITE_API_URL?: string
  /** Port the capture machine's local camera preview is on, when one was asked for
   * (`PREVIEW_PORT`, `scripts/camera.sh --preview`). See .env.example. */
  readonly VITE_PREVIEW_PORT?: string
}
