import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { initGoogleAnalytics } from "./lib/analytics";
import "./styles.css";

initGoogleAnalytics();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
