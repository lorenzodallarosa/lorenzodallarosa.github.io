/* Caelus stage: Baff-1 (newer) and ONE:1 (earlier) on one spotlit stage.
   The toggle is a hard swap that keeps the camera (DESIGN.md section 0). */
import { mountStage } from "./stage-core.js";

const fig = document.querySelector("#caelus-baff-1 [data-stage]");
if (fig) {
  const stage = mountStage(fig);
  const buttons = [...fig.querySelectorAll(".toggle button")];
  buttons.forEach((b) => b.addEventListener("click", () => {
    buttons.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    stage.show(b.dataset.model);
  }));
}
