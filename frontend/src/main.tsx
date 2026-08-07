import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { statisticalTwinProfile } from "./productProfile";

document.body.dataset.statisticalTwinProfile = statisticalTwinProfile;

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
