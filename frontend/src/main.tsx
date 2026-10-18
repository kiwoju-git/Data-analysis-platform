import React from "react";
import ReactDOM from "react-dom/client";

import "./App.css";
import { ApplicationContent, ApplicationErrorBoundary } from "./ApplicationBoundary";
import { LocaleProvider } from "./i18n/LocaleProvider";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ApplicationErrorBoundary>
      <LocaleProvider>
        <ApplicationContent />
      </LocaleProvider>
    </ApplicationErrorBoundary>
  </React.StrictMode>,
);
