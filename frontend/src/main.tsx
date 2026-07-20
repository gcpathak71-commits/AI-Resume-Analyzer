/**
 * main.tsx
 * --------
 * The actual DOM entry point, referenced by index.html
 * (<script type="module" src="/src/main.tsx">). Mounts the root <App />
 * component into #root in React 18's StrictMode, and is the single place
 * globals.css is imported so Tailwind's generated styles apply app-wide.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import App from "@/App";
import "@/styles/globals.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Could not find #root element to mount the app into. Check index.html.");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
