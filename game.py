import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="OrbitDrift", page_icon="🪐", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
.stApp {
    background: radial-gradient(circle at 20% 20%, #1b1140 0%, #0a0620 55%, #04030d 100%);
}
#MainMenu, footer, header { visibility: hidden; }
.od-title {
    text-align: center;
    font-weight: 800;
    font-size: 2.6rem;
    background: linear-gradient(90deg, #7cf7ff, #a78bfa, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
}
.od-sub {
    text-align: center;
    color: #a9a4d0;
    font-weight: 300;
    margin-top: 0;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="od-title">🪐 OrbitDrift</p>', unsafe_allow_html=True)
st.markdown('<p class="od-sub">A sprawling archipelago of floating islands, race gates, and orbs to collect. Press F to fly, C to switch camera.</p>', unsafe_allow_html=True)

GAME_HTML = r"""
<div id="od-wrap" style="width:100%; height:78vh; position:relative; border-radius:20px; overflow:hidden;
    background:linear-gradient(180deg,#0a0620,#04030d); box-shadow:0 0 40px rgba(124,247,255,0.08);">
  <canvas id="od-canvas" style="display:block; width:100%; height:100%;"></canvas>

  <div id="od-hud" style="position:absolute; top:14px; left:14px; z-index:5; color:#e8e6ff;
      font-family:'Outfit',sans-serif; pointer-events:none;">
    <div id="od-mode" style="font-size:0.95rem; font-weight:600; letter-spacing:0.06em;
        background:rgba(20,14,50,0.55); backdrop-filter: blur(8px); padding:8px 14px; border-radius:12px;
        border:1px solid rgba(124,247,255,0.25);">EXPLORE MODE</div>
    <div id="od-timer" style="display:none; margin-top:8px; font-size:1.3rem; font-weight:800; color:#7cf7ff;
        background:rgba(20,14,50,0.55); backdrop-filter: blur(8px); padding:6px 14px; border-radius:12px;
        border:1px solid rgba(124,247,255,0.25);">00.00</div>
    <div id="od-orbs" style="margin-top:8px; font-size:0.85rem; color:#c9c4ff;
        background:rgba(20,14,50,0.55); backdrop-filter: blur(8px); padding:6px 14px; border-radius:12px;
        border:1px solid rgba(167,139,250,0.25);">✨ Orbs: loading…</div>
  </div>

  <div id="od-best" style="position:absolute; top:14px; right:14px; z-index:5; color:#c9c4ff;
      font-family:'Outfit',sans-serif; font-size:0.85rem; background:rgba(20,14,50,0.55);
      backdrop-filter: blur(8px); padding:8px 14px; border-radius:12px; border:1px solid rgba(244,114,182,0.25);
      text-align:right;">Best Race: --</div>

  <div id="od-msg" style="position:absolute; bottom:16px; left:50%; transform:translateX(-50%); z-index:5;
      color:#e8e6ff; font-family:'Outfit',sans-serif; font-size:0.9rem; text-align:center;
      background:rgba(20,14,50,0.55); backdrop-filter: blur(8px); padding:8px 18px; border-radius:14px;
      border:1px solid rgba(124,247,255,0.2); pointer-events:none;">
      WASD or arrow keys move · SPACE jump · F toggle flying · C toggle camera · drag mouse to look · fly into pink gate to start race
  </div>

  <div id="od-startscreen" style="position:absolute; inset:0; z-index:10; display:flex; flex-direction:column;
      align-items:center; justify-content:center; background:rgba(4,3,13,0.85); backdrop-filter: blur(6px);
      font-family:'Outfit',sans-serif; color:#e8e6ff; text-align:center;">
    <div style="font-size:2rem; font-weight:800; background:linear-gradient(90deg,#7cf7ff,#a78bfa,#f472b6);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:8px;">OrbitDrift</div>
    <div style="max-width:420px; color:#a9a4d0; font-weight:300; margin-bottom:22px; line-height:1.5;">
      Drift between floating islands collecting orbs, then dive through a pink gate for a timed race
      against three checkpoints. Switch camera anytime with C.
    </div>
    <button id="od-startbtn" style="padding:14px 34px; border-radius:14px; border:none; cursor:pointer;
        font-family:'Outfit',sans-serif; font-weight:600; font-size:1.05rem; color:#04030d;
        background:linear-gradient(90deg,#7cf7ff,#a78bfa); box-shadow:0 0 25px rgba(124,247,255,0.35);">
        Launch ▸
    </button>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
(function() {
  const wrap = document.getElementById('od-wrap');
  const canvas = document.getElementById('od-canvas');
  const modeEl = document.getElementById('od-mode');
  const timerEl = document.getElementById('od-timer');
  const orbsEl = document.getElementById('od-orbs');
  const bestEl = document.getElementById('od-best');
  const msgEl = document.getElementById('od-msg');
  const startScreen = document.getElementById('od-startscreen');
  const startBtn = document.getElementById('od-startbtn');

  let scene, camera, renderer, clock;
  let player, playerVel = new THREE.Vector3();
  let onGround = false;
  let thirdPerson = true;
  let started = false;
  let keys = {};

  let islands = [], orbs = [], collected = 0;
  let raceGates = [], raceActive = false, raceStart = 0, raceCheckpoint = 0, bestTime = null;
  let yaw = 0, pitch = 0.28;
  let dragging = false, lastMouseX = 0, lastMouseY = 0;
  let flying = false;

  const GRAVITY = -24;
  const MOVE_SPEED = 20;
  const JUMP_SPEED = 13;
  const FLY_SPEED_MULT = 2.4;

  function loadBest() {
    try {
      const v = localStorage.getItem('orbitdrift_best');
      if (v) { bestTime = parseFloat(v); bestEl.textContent = 'Best Race: ' + bestTime.toFixed(2) + 's'; }
    } catch(e) {}
  }
  function saveBest(t) {
    bestTime = t;
    try { localStorage.setItem('orbitdrift_best', t.toString()); } catch(e) {}
    bestEl.textContent = 'Best Race: ' + t.toFixed(2) + 's';
  }

  function init() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0620);
    scene.fog = new THREE.FogExp2(0x0a0620, 0.0035);

    const w0 = wrap.clientWidth || wrap.getBoundingClientRect().width || 800;
    const h0 = wrap.clientHeight || wrap.getBoundingClientRect().height || 500;

    camera = new THREE.PerspectiveCamera(65, w0 / h0, 0.1, 4000);
    camera.position.set(0, 9, 12);
    camera.lookAt(0, 6, 0);
    yaw = 0; pitch = 0.28;

    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setSize(w0, h0, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    scene.add(new THREE.AmbientLight(0x8888ff, 0.6));
    const sun = new THREE.DirectionalLight(0xfff0e0, 1.1);
    sun.position.set(30, 50, 20);
    scene.add(sun);
    const rim = new THREE.PointLight(0xff66cc, 1.2, 200);
    rim.position.set(-30, 20, -30);
    scene.add(rim);

    // starfield
    const starGeo = new THREE.BufferGeometry();
    const starCount = 3000;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      starPos[i*3] = (Math.random()-0.5) * 1400;
      starPos[i*3+1] = (Math.random()-0.5) * 1400;
      starPos[i*3+2] = (Math.random()-0.5) * 1400;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.6, transparent: true, opacity: 0.7 });
    scene.add(new THREE.Points(starGeo, starMat));

    // player
    const hasCapsule = typeof THREE.CapsuleGeometry === 'function';
    const pGeo = hasCapsule ? new THREE.CapsuleGeometry(0.5, 1, 4, 8) : new THREE.CylinderGeometry(0.5, 0.5, 2, 8);
    const pMat = new THREE.MeshStandardMaterial({ color: 0x7cf7ff, emissive: 0x1a4a55, metalness: 0.3, roughness: 0.4 });
    player = new THREE.Mesh(pGeo, pMat);
    player.position.set(0, 6, 0);
    scene.add(player);

    buildIslands();
    buildOrbs();
    buildRace();

    clock = new THREE.Clock();

    window.addEventListener('keydown', e => {
      const k = e.key.toLowerCase();
      if (!keys[k]) {
        if (k === 'c') thirdPerson = !thirdPerson;
        if (k === 'f') { flying = !flying; playerVel.set(0,0,0); msgEl.textContent = flying ? 'Flying enabled — W/S move along your view, SPACE/SHIFT for extra up/down.' : 'Flying disabled — gravity is back on.'; }
      }
      keys[k] = true;
      if (e.key.startsWith('Arrow')) e.preventDefault();
    });
    window.addEventListener('keyup', e => keys[e.key.toLowerCase()] = false);
    window.addEventListener('resize', onResize);

    canvas.style.cursor = 'grab';
    canvas.addEventListener('mousedown', e => {
      if (!started) return;
      dragging = true;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
      canvas.style.cursor = 'grabbing';
    });
    window.addEventListener('mouseup', () => { dragging = false; canvas.style.cursor = 'grab'; });
    window.addEventListener('mousemove', e => {
      if (!dragging) return;
      const dx = e.clientX - lastMouseX;
      const dy = e.clientY - lastMouseY;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
      const sens = 0.0035;
      yaw -= dx * sens;
      pitch -= dy * sens;
      pitch = Math.max(-1.3, Math.min(1.3, pitch));
    });
    canvas.addEventListener('touchstart', e => {
      if (!started || e.touches.length === 0) return;
      dragging = true;
      lastMouseX = e.touches[0].clientX;
      lastMouseY = e.touches[0].clientY;
    }, { passive: true });
    window.addEventListener('touchmove', e => {
      if (!dragging || e.touches.length === 0) return;
      const dx = e.touches[0].clientX - lastMouseX;
      const dy = e.touches[0].clientY - lastMouseY;
      lastMouseX = e.touches[0].clientX;
      lastMouseY = e.touches[0].clientY;
      const sens = 0.0035;
      yaw -= dx * sens;
      pitch -= dy * sens;
      pitch = Math.max(-1.3, Math.min(1.3, pitch));
    }, { passive: true });
    window.addEventListener('touchend', () => { dragging = false; });

    loadBest();
    animate();

    // Re-measure a few times after mount in case the iframe finished
    // laying out after our initial (possibly premature) size read.
    [50, 200, 600].forEach(t => setTimeout(onResize, t));
    window.addEventListener('load', onResize);
  }

  function onResize() {
    const w = wrap.clientWidth || wrap.getBoundingClientRect().width;
    const h = wrap.clientHeight || wrap.getBoundingClientRect().height;
    if (!w || !h) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }

  function islandMesh(x, y, z, r, color) {
    const geo = new THREE.CylinderGeometry(r, r * 1.15, 1.2, 10);
    const mat = new THREE.MeshStandardMaterial({ color: color, roughness: 0.7, metalness: 0.1 });
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    scene.add(m);
    islands.push({ mesh: m, x, y: y + 0.6, z, r });
    return m;
  }

  function buildIslands() {
    islandMesh(0, 5, 0, 7, 0x4c3d8f);
    const colors = [0x3d5a8f, 0x8f3d6a, 0x3d8f6a, 0x8f7a3d, 0x5a3d8f, 0x3d8f8f, 0x8f3d3d, 0x6a3d8f, 0x3d6a8f, 0x8f6a3d];
    const ring = (count, radius, yBase, yVar, rMin, rMax) => {
      for (let i = 0; i < count; i++) {
        const angle = (i / count) * Math.PI * 2 + (Math.random() - 0.5) * 0.4;
        const rad = radius + (Math.random() - 0.5) * radius * 0.3;
        const x = Math.cos(angle) * rad;
        const z = Math.sin(angle) * rad;
        const y = yBase + (Math.random() - 0.5) * yVar;
        const r = rMin + Math.random() * (rMax - rMin);
        islandMesh(x, y, z, r, colors[i % colors.length]);
      }
    };
    ring(14, 70, 8, 6, 3.2, 5);
    ring(20, 140, 14, 10, 3, 5.5);
    ring(26, 220, 20, 14, 2.8, 6);
    ring(20, 300, 26, 16, 3, 5.5);
    ring(16, 380, 32, 20, 3.2, 6.5);
  }

  let ORB_TOTAL = 0;
  function buildOrbs() {
    const orbGeo = new THREE.OctahedronGeometry(0.4, 0);
    const orbMat = new THREE.MeshStandardMaterial({ color: 0xffe066, emissive: 0x996600, emissiveIntensity: 0.6 });
    islands.forEach(isl => {
      const m = new THREE.Mesh(orbGeo, orbMat.clone());
      m.position.set(isl.x + (Math.random()-0.5)*2, isl.y + 2.2 + Math.random()*1.5, isl.z + (Math.random()-0.5)*2);
      scene.add(m);
      orbs.push(m);
    });
    // extra sky orbs scattered between islands
    for (let i = 0; i < 45; i++) {
      const angle = Math.random() * Math.PI * 2;
      const rad = 20 + Math.random() * 370;
      const m = new THREE.Mesh(orbGeo, orbMat.clone());
      m.position.set(Math.cos(angle) * rad, 8 + Math.random() * 35, Math.sin(angle) * rad);
      scene.add(m);
      orbs.push(m);
    }
    ORB_TOTAL = orbs.length;
    orbsEl.textContent = '✨ Orbs: 0 / ' + ORB_TOTAL;
  }

  function buildRace() {
    // pink start gate near spawn island
    const gateMat = new THREE.MeshStandardMaterial({ color: 0xf472b6, emissive: 0x8a1f55, emissiveIntensity: 0.7, transparent: true, opacity: 0.85 });
    function makeGate(x, y, z) {
      const torus = new THREE.Mesh(new THREE.TorusGeometry(2.2, 0.25, 8, 24), gateMat.clone());
      torus.position.set(x, y, z);
      scene.add(torus);
      return { mesh: torus, x, y, z, hit: false };
    }
    raceGates.push(makeGate(0, 8, -8));        // start gate
    raceGates.push(makeGate(90, 14, -90));     // checkpoint 1
    raceGates.push(makeGate(200, 24, 60));     // checkpoint 2
    raceGates.push(makeGate(320, 34, -140));   // finish
  }

  function updatePlayer(dt) {
    const flatForward = new THREE.Vector3(Math.sin(yaw), 0, Math.cos(yaw));
    const flatRight = new THREE.Vector3(-Math.cos(yaw), 0, Math.sin(yaw));

    let move = new THREE.Vector3();

    if (flying) {
      const lookForward = new THREE.Vector3(
        Math.sin(yaw) * Math.cos(pitch),
        Math.sin(pitch),
        Math.cos(yaw) * Math.cos(pitch)
      );
      if (keys['w'] || keys['arrowup']) move.add(lookForward);
      if (keys['s'] || keys['arrowdown']) move.sub(lookForward);
      if (keys['d'] || keys['arrowright']) move.add(flatRight);
      if (keys['a'] || keys['arrowleft']) move.sub(flatRight);
      if (move.lengthSq() > 0) move.normalize().multiplyScalar(MOVE_SPEED * FLY_SPEED_MULT);
      if (keys[' ']) move.y += MOVE_SPEED * 1.6;
      if (keys['shift']) move.y -= MOVE_SPEED * 1.6;

      player.position.addScaledVector(move, dt);
      playerVel.set(0, 0, 0);
      onGround = false;

      if (move.lengthSq() > 0.001) {
        const targetAngle = Math.atan2(move.x, move.z);
        player.rotation.y += (targetAngle - player.rotation.y) * Math.min(1, dt * 10);
      }
      if (player.position.y < -20) {
        player.position.set(0, 8, 0);
      }
      return;
    }

    if (keys['w'] || keys['arrowup']) move.add(flatForward);
    if (keys['s'] || keys['arrowdown']) move.sub(flatForward);
    if (keys['d'] || keys['arrowright']) move.add(flatRight);
    if (keys['a'] || keys['arrowleft']) move.sub(flatRight);
    if (move.lengthSq() > 0) {
      move.normalize().multiplyScalar(MOVE_SPEED);
      player.position.x += move.x * dt;
      player.position.z += move.z * dt;
      const targetAngle = Math.atan2(move.x, move.z);
      player.rotation.y += (targetAngle - player.rotation.y) * Math.min(1, dt*10);
    }

    playerVel.y += GRAVITY * dt;
    player.position.y += playerVel.y * dt;

    onGround = false;
    islands.forEach(isl => {
      const dx = player.position.x - isl.x, dz = player.position.z - isl.z;
      const dist = Math.sqrt(dx*dx + dz*dz);
      if (dist < isl.r + 0.6 && player.position.y <= isl.y + 0.9 && player.position.y >= isl.y - 2 && playerVel.y <= 0) {
        player.position.y = isl.y + 0.9;
        playerVel.y = 0;
        onGround = true;
      }
    });

    if (onGround && keys[' ']) {
      playerVel.y = JUMP_SPEED;
      onGround = false;
    }

    if (player.position.y < -20) {
      player.position.set(0, 8, 0);
      playerVel.set(0,0,0);
    }
  }

  function updateCamera() {
    const lookDir = new THREE.Vector3(
      Math.sin(yaw) * Math.cos(pitch),
      Math.sin(pitch),
      Math.cos(yaw) * Math.cos(pitch)
    );
    if (thirdPerson) {
      const dist = 7.5, height = 3.2;
      const back = lookDir.clone().multiplyScalar(-dist);
      const desired = player.position.clone().add(new THREE.Vector3(0, height, 0)).add(back);
      camera.position.lerp(desired, 0.18);
      camera.lookAt(player.position.clone().add(new THREE.Vector3(0, 1, 0)).add(lookDir.clone().multiplyScalar(3)));
      modeEl.textContent = raceActive ? 'RACE MODE · 3RD PERSON' : 'EXPLORE MODE · 3RD PERSON';
    } else {
      const headPos = player.position.clone().add(new THREE.Vector3(0, 0.8, 0));
      camera.position.lerp(headPos, 0.4);
      camera.lookAt(headPos.clone().add(lookDir));
      modeEl.textContent = raceActive ? 'RACE MODE · 1ST PERSON' : 'EXPLORE MODE · 1ST PERSON';
    }
  }

  function checkOrbs() {
    for (let i = orbs.length - 1; i >= 0; i--) {
      const o = orbs[i];
      if (player.position.distanceTo(o.position) < 1.3) {
        scene.remove(o);
        orbs.splice(i, 1);
        collected++;
        orbsEl.textContent = '✨ Orbs: ' + collected + ' / ' + ORB_TOTAL;
      }
    }
  }

  function checkRace(dt) {
    orbs.forEach(o => o.rotation.y += dt * 2);
    raceGates.forEach(g => { g.mesh.rotation.z += dt * 0.6; });

    if (!raceActive) {
      const g0 = raceGates[0];
      if (player.position.distanceTo(new THREE.Vector3(g0.x, g0.y, g0.z)) < 2.6) {
        raceActive = true;
        raceStart = performance.now();
        raceCheckpoint = 1;
        timerEl.style.display = 'block';
        msgEl.textContent = 'Race started! Fly through the glowing gates in order.';
      }
    } else {
      const elapsed = (performance.now() - raceStart) / 1000;
      timerEl.textContent = elapsed.toFixed(2);
      const g = raceGates[raceCheckpoint];
      if (g && player.position.distanceTo(new THREE.Vector3(g.x, g.y, g.z)) < 2.6) {
        raceCheckpoint++;
        if (raceCheckpoint >= raceGates.length) {
          raceActive = false;
          timerEl.style.display = 'none';
          if (!bestTime || elapsed < bestTime) {
            saveBest(elapsed);
            msgEl.textContent = 'New best time: ' + elapsed.toFixed(2) + 's! Fly back through the pink gate to race again.';
          } else {
            msgEl.textContent = 'Finished in ' + elapsed.toFixed(2) + 's. Best stays ' + bestTime.toFixed(2) + 's.';
          }
        } else {
          msgEl.textContent = 'Checkpoint ' + raceCheckpoint + ' of ' + (raceGates.length - 1) + '!';
        }
      }
    }
  }

  function animate() {
    requestAnimationFrame(animate);
    onResize();
    if (!started) { renderer.render(scene, camera); return; }
    const dt = Math.min(clock.getDelta(), 0.05);
    updatePlayer(dt);
    updateCamera();
    checkOrbs();
    checkRace(dt);
    renderer.render(scene, camera);
  }

  startBtn.addEventListener('click', () => {
    startScreen.style.display = 'none';
    started = true;
    canvas.focus();
  });

  init();
})();
</script>
"""

components.html(GAME_HTML, height=640, scrolling=False)

st.markdown("""
<div style="max-width:900px; margin:1.5rem auto 0 auto; color:#a9a4d0; font-family:'Outfit',sans-serif;
    font-size:0.9rem; text-align:center;">
    Best race time is saved locally in your browser. Reload the page for a fresh explore run any time.
</div>
""", unsafe_allow_html=True)
