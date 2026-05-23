import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RealSignalRoom } from "./RealSignalRoom";
import "./styles.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <RealSignalRoom />
  </StrictMode>
);
