import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// Self-hosted serif (bundled same-origin by Vite -> safe under COOP/COEP); normal +
// true italic. See web/src/styles.css for how it's used (title, labels, status).
import "@fontsource-variable/eb-garamond/wght.css";
import "@fontsource-variable/eb-garamond/wght-italic.css";
import "./styles.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
