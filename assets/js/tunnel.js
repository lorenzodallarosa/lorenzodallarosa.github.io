/* Easter egg: click the big last name in the footer more than once and it goes into a wind
   tunnel. Each click raises the angle of attack by 4 deg (pitching about the quarter chord),
   smoke streamlines bend over it and the readout gives the thin-aerofoil lift, C_L = 2 pi alpha.
   Past 12 deg the flow separates and the word stalls; one more click resets the tunnel. */
(() => {
  const word = document.querySelector(".contact-mega");
  const wrap = word && word.parentElement;
  if (!wrap) return;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const NS = "http://www.w3.org/2000/svg";
  const W = 1000, H = 300, LINES = 9, STALL = 16;

  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", "tunnel");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("aria-hidden", "true");
  const paths = Array.from({ length: LINES }, (_, i) => {
    const p = document.createElementNS(NS, "path");
    p.style.animationDelay = `${-i * 0.37}s`;
    svg.appendChild(p);
    return p;
  });
  const read = document.createElement("p");
  read.className = "tunnel-read t-label";
  read.setAttribute("aria-live", "polite");
  wrap.append(svg, read);

  let clicks = 0, alpha = 0, noise = null;

  // Streamline at height y0: upwash ahead of the word, deflection over it, downwash behind.
  function line(y0, a, turbulent) {
    const k = a / STALL;
    const near = Math.exp(-Math.pow((y0 - H * 0.45) / (H * 0.45), 2)); // lines close to the word bend most
    let d = "";
    for (let x = 0; x <= W; x += 20) {
      let y = y0 - 120 * k * near * Math.exp(-Math.pow((x - 380) / 260, 2)) + 60 * k * near / (1 + Math.exp(-(x - 760) / 70));
      if (turbulent && x > 330 && y0 < H * 0.75) y += (Math.random() - 0.5) * 46 * near * ((x - 330) / (W - 330));
      d += `${x ? "L" : "M"}${x},${y.toFixed(1)}`;
    }
    return d;
  }
  function draw() {
    const stalled = alpha >= STALL;
    paths.forEach((p, i) => p.setAttribute("d", line(20 + (i * (H - 40)) / (LINES - 1), stalled ? 10 : alpha, stalled)));
  }

  function set(n) {
    clicks = n;
    alpha = Math.min(STALL, Math.max(0, (clicks - 1) * 4));
    const on = clicks > 1, stalled = alpha >= STALL;
    wrap.classList.toggle("is-tunnel", on);
    wrap.classList.toggle("is-stall", stalled);
    // Flow runs left to right, so the nose (left) pitches up. The drawn tilt is damped so the
    // whole name stays on screen.
    word.style.setProperty("--aoa", `${stalled ? 0 : alpha * 0.6}deg`);
    clearInterval(noise);
    if (on) {
      draw();
      if (stalled && !reduce) noise = setInterval(draw, 140);
      const cl = (2 * Math.PI * alpha * Math.PI / 180).toFixed(2);
      const a = '<span class="a">α</span>'; // keep the Greek letter lowercase inside the uppercase label
      read.innerHTML = stalled ? `${a} = ${alpha}° · Stall · click to reset` : `Wind tunnel · ${a} = ${alpha}° · C<sub>L</sub> ≈ ${cl}`;
    } else {
      read.textContent = "";
    }
  }

  word.addEventListener("click", () => set(alpha >= STALL ? 0 : clicks + 1));
})();
