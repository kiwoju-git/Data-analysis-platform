import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the DataLab Studio shell", () => {
    const html = renderToString(<App />);

    expect(html).toContain("DataLab Studio");
    expect(html).toContain("로컬 분석 작업대");
    expect(html).toContain("업로드");
  });
});
