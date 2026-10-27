/* Shared 3D stage (DESIGN.md sections 0 and 9): lazy three.js viewer for the project models.
   - Initialises when the stage is within one viewport. On phones it loads directly when the
     device and connection look capable, otherwise on tap.
   - Models are fetched as XOR-obfuscated .bin files and decoded here (basic anti-scraping).
   - Carbon-fibre materials are re-tuned as a dielectric weave under a glossy clear coat.
   - Renders only while on screen. Pixel ratio capped at 2.
   - "Product on black" (dark) or "product on paper" (paper) lighting; the models keep
     their own materials.
   - Orbit with damping, limited polar angle and zoom, idle rotation <= 2 deg/s that
     stops on interaction and respects reduced motion.
   - Keyboard-accessible camera presets and 1px callout leaders anchored to named nodes;
     a model can keep its callouts hidden until the stage is hovered.
   - While the model loads, the poster turns into a dimmed ghost with a progress bar. */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { toCreasedNormals } from "three/addons/utils/BufferGeometryUtils.js";

const MODEL_KEY = new TextEncoder().encode("ldr-stage-7f3a91"); // matches tools/build_site.py

const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
const small = matchMedia("(max-width: 767px)");
const ease = (t) => 1 - Math.pow(1 - t, 3);

// Camera directions; every model is exported nose towards -X, +Y up. The top view looks
// straight down (the tiny offset only fixes which way is up on screen).
const VIEWS = {
  three: new THREE.Vector3(-1, 0.5, 1.05),
  side: new THREE.Vector3(0, 0.12, 1),
  front: new THREE.Vector3(-1, 0.18, 0),
  top: new THREE.Vector3(0, 1, 0.002),
};

let loader;
function getLoader() {
  if (loader) return loader;
  const draco = new DRACOLoader();
  draco.setDecoderPath(import.meta.resolve("three/addons/libs/draco/gltf/"));
  loader = new GLTFLoader();
  loader.setDRACOLoader(draco);
  loader.setMeshoptDecoder(MeshoptDecoder);
  return loader;
}

// Fetch an obfuscated model, reporting progress, and undo the XOR.
async function fetchModel(url, onProgress) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  const total = +res.headers.get("content-length") || 0;
  const reader = res.body.getReader();
  const chunks = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    got += value.length;
    if (total) onProgress(got / total);
  }
  const buf = new Uint8Array(got);
  let o = 0;
  for (const c of chunks) { buf.set(c, o); o += c.length; }
  const k = MODEL_KEY, n = k.length;
  for (let i = 0; i < got; i++) buf[i] ^= k[i % n];
  return buf.buffer;
}

// Phones: load straight away only on a capable device and connection.
function canAutoLoad() {
  const c = navigator.connection;
  if (c && (c.saveData || /(^|-)2g|3g/.test(c.effectiveType || ""))) return false;
  if (navigator.deviceMemory && navigator.deviceMemory < 4) return false;
  if (navigator.hardwareConcurrency && navigator.hardwareConcurrency < 4) return false;
  return true;
}

// Carbon fibre: a woven dielectric under a clear coat, not a metal. The exported
// metal/roughness maps flag the weave as metallic, so metalness is forced to zero and the
// weave reads through the roughness map and the normal map under the coat. `look` lets a
// model override the defaults, e.g. a more matte finish.
const CARBON = { roughness: 0.75, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.8 };
function tuneMaterial(mat, maxAniso, look = {}) {
  if (!mat) return;
  // Sharp tiled textures at grazing angles (the ET-18 weave repeats 18 times per UV tile).
  ["map", "normalMap", "roughnessMap", "metalnessMap"].forEach((k) => {
    if (mat[k]) { mat[k].anisotropy = maxAniso; mat[k].needsUpdate = true; }
  });
  if (!mat.isMeshPhysicalMaterial || !(mat.clearcoat > 0) || !mat.normalMap) return;
  const c = { ...CARBON, ...look };
  mat.metalness = 0;
  mat.metalnessMap = null;
  mat.roughness = c.roughness; // scales the weave's roughness map (~0.3) to a satin fibre
  mat.color.multiplyScalar(0.6);
  mat.normalScale.set(0.6, 0.6);
  mat.clearcoat = c.clearcoat;
  mat.clearcoatRoughness = c.clearcoatRoughness;
  mat.envMapIntensity = c.envMapIntensity; // a glossy coat needs clear reflections to read as lacquer
  mat.needsUpdate = true;
}

function webglOK() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

function poolTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const g = c.getContext("2d");
  const grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  grad.addColorStop(0, "rgba(237,231,214,0.07)");
  grad.addColorStop(0.5, "rgba(237,231,214,0.025)");
  grad.addColorStop(1, "rgba(237,231,214,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// Anchor point for a callout: centre of every mesh whose (sanitised) name contains `token`,
// optionally moved by `bias` (fractions of the half-size per axis), e.g. out along a wing.
function anchorFor(root, token, bias = [0, 0, 0]) {
  const key = token.replace(/[\s.]/g, "_");
  const box = new THREE.Box3();
  root.traverse((o) => {
    if (o.isMesh && o.name.replace(/[\s.]/g, "_").includes(key)) box.union(new THREE.Box3().setFromObject(o));
  });
  if (box.isEmpty()) return null;
  const half = box.getSize(new THREE.Vector3()).multiplyScalar(0.5);
  return box.getCenter(new THREE.Vector3()).add(half.multiply(new THREE.Vector3(...bias)));
}

export function mountStage(fig) {
  const cfg = JSON.parse(fig.querySelector(".stage-cfg").textContent);
  const box = fig.querySelector(".stage-box");
  const host = fig.querySelector(".stage-gl");
  const coLayer = fig.querySelector(".stage-callouts");
  const poster = fig.querySelector(".stage-poster");
  const presetBtns = [...fig.querySelectorAll("[data-view]")];
  const dark = cfg.theme === "dark";
  const byKey = Object.fromEntries(cfg.models.map((m) => [m.key, m]));

  const api = { current: cfg.models[0].key, show };
  const loaded = {};
  let three = null; // renderer, scene, camera, controls once initialised

  const status = document.createElement("p");
  status.className = "stage-status t-label";
  status.setAttribute("aria-live", "polite");
  const bar = document.createElement("span");
  bar.className = "stage-progress";
  bar.setAttribute("aria-hidden", "true");
  box.append(status, bar);
  const progress = (f) => {
    status.textContent = f == null ? "Loading 3D model" : `Loading 3D model · ${Math.round(f * 100)}%`;
    bar.style.setProperty("--p", f == null ? 0.08 : f);
  };
  if (cfg.models.some((m) => m.hoverCallouts)) fig.classList.add("co-hover");

  function show(key) {
    api.current = key;
    const m = byKey[key];
    if (loaded[key]) {
      Object.entries(loaded).forEach(([k, o]) => { o.root.visible = k === key; });
      fig.classList.add("is-live");
      buildCallouts();
    } else {
      fig.classList.remove("is-live");
      poster.src = m.poster;
      poster.alt = m.alt;
      poster.removeAttribute("width");
      poster.removeAttribute("height");
      buildCallouts();
    }
  }

  if (!webglOK()) {
    fig.classList.add("no-gl");
    return api;
  }

  let started = false;
  const start = () => {
    if (started) return;
    started = true;
    fig.classList.add("is-loading");
    progress(null);
    init().catch((err) => {
      console.error(err);
      status.textContent = "3D unavailable · photo shown";
    }).finally(() => fig.classList.remove("is-loading"));
  };
  fig.querySelector(".stage-tap").addEventListener("click", start);
  fig.addEventListener("contextmenu", (e) => e.preventDefault());
  if (!small.matches || canAutoLoad()) {
    const near = new IntersectionObserver((es) => {
      if (es.some((e) => e.isIntersecting)) { near.disconnect(); start(); }
    }, { rootMargin: "100% 0px" });
    near.observe(fig);
  }

  // ---- callouts
  let callouts = [];
  function buildCallouts() {
    coLayer.innerHTML = "";
    callouts = [];
    const m = byKey[api.current];
    const entry = loaded[api.current];
    if (!entry || !m.callouts) return;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    coLayer.appendChild(svg);
    m.callouts.forEach((c, i) => {
      if (!entry.anchors[i]) return;
      const path = document.createElementNS(svg.namespaceURI, "polyline");
      path.setAttribute("class", `co-line tone-${c.tone}`);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke-width", "1");
      path.setAttribute("pathLength", "1"); // lets CSS draw the leader in
      const dot = document.createElementNS(svg.namespaceURI, "circle");
      dot.setAttribute("r", "2.5");
      dot.setAttribute("class", `co-dot tone-${c.tone}`);
      [path, dot].forEach((el) => el.style.setProperty("--i", i));
      svg.append(path, dot);
      const label = document.createElement("span");
      label.className = `co-label tone-${c.tone}`;
      label.style.setProperty("--i", i);
      label.textContent = c.label;
      coLayer.appendChild(label);
      callouts.push({ c, anchor: entry.anchors[i], path, dot, label, dy: c.dy ?? (i % 2 ? 64 : -64) });
    });
  }

  const v = new THREE.Vector3();
  function placeCallouts(camera, w, h) {
    // 1. Project anchors and pick a side and a label height for each visible callout.
    const shown = [];
    callouts.forEach((k) => {
      v.copy(k.anchor).project(camera);
      const vis = v.z < 1 && Math.abs(v.x) < 1.1 && Math.abs(v.y) < 1.1;
      k.path.style.display = k.dot.style.display = k.label.style.display = vis ? "" : "none";
      if (!vis) return;
      k.x = (v.x * 0.5 + 0.5) * w;
      k.y = (-v.y * 0.5 + 0.5) * h;
      k.dir = k.x > w * 0.5 ? 1 : -1;
      k.ey = Math.min(h - 70, Math.max(40, k.y + k.dy));
      shown.push(k);
    });
    // 2. Labels on the same side keep at least one line between them.
    const GAP = 24;
    [-1, 1].forEach((side) => {
      const col = shown.filter((k) => k.dir === side).sort((a, b) => a.ey - b.ey);
      for (let i = 1; i < col.length; i++) col[i].ey = Math.max(col[i].ey, col[i - 1].ey + GAP);
    });
    // 3. Draw: leader from the anchor to an elbow, then out to the stage margin.
    shown.forEach((k) => {
      const { x, y, dir, ey } = k;
      const ex = x + dir * 28;
      const lw = k.lw || (k.lw = k.label.offsetWidth) || 220;
      const lx = dir > 0
        ? Math.min(Math.max(ex + 24, w - 32 - lw), w - 16 - lw) // never past the stage edge
        : Math.max(Math.min(ex - 24, 32 + lw), 16 + lw);
      k.path.setAttribute("points", `${x},${y} ${ex},${ey} ${lx},${ey}`);
      k.dot.setAttribute("cx", x);
      k.dot.setAttribute("cy", y);
      k.label.classList.toggle("right", dir > 0);
      k.label.classList.toggle("left", dir < 0);
      k.label.style.left = `${lx}px`;
      k.label.style.top = `${ey}px`;
    });
  }

  // ---- three.js
  async function init() {
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    host.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environmentIntensity = dark ? 0.35 : 0.55;

    const camera = new THREE.PerspectiveCamera(28, 1, 0.01, 500);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.minPolarAngle = 0;
    controls.maxPolarAngle = Math.PI * 0.49;
    controls.autoRotate = !reduceMotion.matches;
    controls.autoRotateSpeed = 0.3; // 0.3 * 6 = 1.8 deg/s
    renderer.domElement.style.touchAction = "pan-y"; // never trap vertical page scroll
    host.addEventListener("wheel", (e) => {
      if (!e.ctrlKey && !e.metaKey) e.stopPropagation(); // plain wheel scrolls the page
      else e.preventDefault();
    }, { capture: true, passive: false });
    controls.addEventListener("start", () => {
      controls.autoRotate = false;
      tween = null;
      fig.classList.add("is-touched");
      presetBtns.forEach((b) => b.classList.remove("is-on"));
    });

    three = { renderer, scene, camera, controls };

    // Load the first model, then the rest in the background.
    const order = [api.current, ...cfg.models.map((m) => m.key).filter((k) => k !== api.current)];
    for (const key of order) {
      await loadModel(key);
      if (key === order[0]) {
        frame();
        setLights();
        setView("three", true);
        resize();
        startLoop();
      } else {
        frame();
      }
      show(api.current);
    }
    status.textContent = "";
  }

  let R = 1, center = new THREE.Vector3(), fitDist = 5;

  async function loadModel(key) {
    const m = byKey[key];
    const { scene } = three;
    progress(null);
    const data = await fetchModel(m.src, progress);
    const gltf = await getLoader().parseAsync(data, "");
    const root = gltf.scene;
    if (m.rotateY) root.rotation.y = THREE.MathUtils.degToRad(m.rotateY);
    root.updateMatrixWorld(true);
    const b = new THREE.Box3().setFromObject(root);
    const c = b.getCenter(new THREE.Vector3());
    root.position.set(-c.x, -b.min.y, -c.z);
    root.updateMatrixWorld(true);
    const maxAniso = three.renderer.capabilities.getMaxAnisotropy();
    const crease = m.smooth ? THREE.MathUtils.degToRad(m.smooth) : 0;
    root.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      o.receiveShadow = true;
      (Array.isArray(o.material) ? o.material : [o.material]).forEach((mt) => tuneMaterial(mt, maxAniso, m.carbon));
      // Smooth faceted exports: average normals across faces closer than the crease angle.
      if (crease && !o.material.normalMap) o.geometry = toCreasedNormals(o.geometry, crease);
    });
    root.visible = key === api.current;
    scene.add(root);
    const anchors = (m.callouts || []).map((co) => anchorFor(root, co.node, co.bias));
    loaded[key] = { root, box: new THREE.Box3().setFromObject(root), anchors };
  }

  // Frame the union of all loaded models, so swapping keeps the same camera.
  function frame() {
    const u = new THREE.Box3();
    Object.values(loaded).forEach((o) => u.union(o.box));
    const s = u.getBoundingSphere(new THREE.Sphere());
    R = s.radius;
    center.copy(u.getCenter(new THREE.Vector3()));
    center.y = u.max.y * 0.42;
    three.controls.target.copy(center);
    fitDistance();
  }

  function fitDistance() {
    const { camera, controls } = three;
    const vf = THREE.MathUtils.degToRad(camera.fov);
    const hf = 2 * Math.atan(Math.tan(vf / 2) * camera.aspect);
    const prev = fitDist;
    fitDist = (R * (cfg.fit || cfg.models[0].fit || 0.66) * (camera.aspect < 1 ? 1.4 : 1)) / Math.sin(Math.min(vf, hf) / 2);
    controls.minDistance = fitDist * 0.4;
    controls.maxDistance = fitDist * 1.5;
    camera.near = fitDist / 100;
    camera.far = fitDist * 10;
    camera.updateProjectionMatrix();
    if (prev && camera.position.lengthSq() > 0) {
      const off = camera.position.clone().sub(controls.target).multiplyScalar(fitDist / prev);
      camera.position.copy(controls.target).add(off);
    }
  }

  let lightsSet = false;
  function setLights() {
    if (lightsSet) return;
    lightsSet = true;
    const { scene } = three;
    const size = R * 10;
    if (dark) {
      scene.add(new THREE.HemisphereLight(0xede7d6, 0x1b1b19, 0.35));
      const spot = new THREE.SpotLight(0xfff3e0, 4, 0, Math.PI / 6, 1, 0);
      spot.position.set(R * 0.2, R * 3.2, R * 0.9);
      spot.target.position.copy(center);
      spot.castShadow = true;
      spot.shadow.mapSize.set(2048, 2048);
      spot.shadow.bias = -0.0004;
      spot.shadow.radius = 6;
      scene.add(spot, spot.target);
      const pool = new THREE.Mesh(
        new THREE.PlaneGeometry(R * 4.2, R * 4.2),
        new THREE.MeshBasicMaterial({ map: poolTexture(), transparent: true, depthWrite: false }),
      );
      pool.rotation.x = -Math.PI / 2;
      pool.position.y = -0.002;
      scene.add(pool);
    } else {
      scene.add(new THREE.HemisphereLight(0xfffbf2, 0xd8cfb8, 0.7));
      const key = new THREE.DirectionalLight(0xfff6e8, 2.2);
      key.position.set(-R * 1.4, R * 3, R * 1.8);
      key.castShadow = true;
      key.shadow.mapSize.set(2048, 2048);
      const sc = key.shadow.camera;
      sc.left = sc.bottom = -R * 1.4;
      sc.right = sc.top = R * 1.4;
      sc.near = R * 0.5;
      sc.far = R * 8;
      key.shadow.bias = -0.0004;
      key.shadow.radius = 4;
      scene.add(key);
      const fill = new THREE.DirectionalLight(0xffffff, 0.6);
      fill.position.set(R * 2, R, -R * 2);
      scene.add(fill);
    }
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.ShadowMaterial({ opacity: dark ? 0.4 : 0.2 }));
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);
  }

  // ---- views
  let tween = null;
  function setView(name, instant) {
    const { camera, controls } = three;
    // A model can override a preset, e.g. the aircraft's top view looks along the span.
    const custom = byKey[api.current].views?.[name];
    const dir = (custom ? new THREE.Vector3(...custom.slice(0, 3)) : VIEWS[name].clone()).normalize();
    const to = center.clone().add(dir.multiplyScalar(fitDist * ((custom && custom[3]) || 1)));
    presetBtns.forEach((b) => b.classList.toggle("is-on", b.dataset.view === name));
    if (instant || reduceMotion.matches) {
      camera.position.copy(to);
      controls.update();
      return;
    }
    // Tween in spherical coordinates around the target: azimuth takes the short way round and
    // the polar angle moves on its own, so swinging over the pole never flips the camera.
    const a = new THREE.Spherical().setFromVector3(camera.position.clone().sub(center));
    const b = new THREE.Spherical().setFromVector3(to.clone().sub(center));
    let dTheta = b.theta - a.theta;
    dTheta = Math.atan2(Math.sin(dTheta), Math.cos(dTheta));
    tween = { a, b, dTheta, t0: performance.now(), dur: 800 };
  }
  presetBtns.forEach((b) => b.addEventListener("click", () => {
    if (!three) return;
    three.controls.autoRotate = false;
    fig.classList.add("is-touched");
    setView(b.dataset.view);
  }));

  // ---- loop
  let w = 1, h = 1;
  function resize() {
    if (!three) return;
    w = box.clientWidth;
    h = box.clientHeight;
    three.renderer.setSize(w, h, false);
    three.camera.aspect = w / h;
    three.camera.updateProjectionMatrix();
    fitDistance();
  }
  new ResizeObserver(resize).observe(box);

  const sph = new THREE.Spherical();
  function tick(now) {
    const { renderer, scene, camera, controls } = three;
    if (tween) {
      const t = Math.min(1, (now - tween.t0) / tween.dur);
      const k = ease(t), { a, b } = tween;
      sph.set(
        THREE.MathUtils.lerp(a.radius, b.radius, k),
        Math.max(1e-4, THREE.MathUtils.lerp(a.phi, b.phi, k)),
        a.theta + tween.dTheta * k,
      );
      camera.position.setFromSpherical(sph).add(center);
      if (t >= 1) tween = null;
    }
    controls.update();
    renderer.render(scene, camera);
    placeCallouts(camera, w, h);
  }

  let running = false;
  function startLoop() {
    const vis = new IntersectionObserver((es) => {
      const on = es.some((e) => e.isIntersecting);
      if (on === running) return;
      running = on;
      three.renderer.setAnimationLoop(on ? tick : null);
    });
    vis.observe(fig);
  }

  return api;
}

