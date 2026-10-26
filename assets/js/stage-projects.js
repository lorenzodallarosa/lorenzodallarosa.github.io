/* Mounts every 3D stage on the page (ET-18, Caelus ONE:1, Caelus Baff-1). */
import { mountStage } from "./stage-core.js";

document.querySelectorAll("[data-stage]").forEach((fig) => mountStage(fig));
