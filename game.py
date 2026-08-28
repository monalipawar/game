import streamlit as st
import streamlit.components.v1 as components
import json
import os
import time
import uuid
import random

st.set_page_config(page_title="OrbitDrift", page_icon="🪐", layout="wide")

STATE_DIR = "/tmp/orbitdrift_rooms"
os.makedirs(STATE_DIR, exist_ok=True)

def room_state_path(room):
    return os.path.join(STATE_DIR, f"{room}_state.json")

def room_chat_path(room):
    return os.path.join(STATE_DIR, f"{room}_chat.json")

def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except Exception:
        pass

def default_boss(slot):
    return {"slot": slot, "hp": 900, "max_hp": 900, "tier": 1, "alive": True, "respawn_at": 0}

def default_bosses():
    return [default_boss(0), default_boss(1), default_boss(2)]

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
div[data-testid="stTextArea"]:has(textarea[aria-label="od_sync_data"]) { display: none; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="od-title">🪐 OrbitDrift</p>', unsafe_allow_html=True)
st.markdown('<p class="od-sub">A sprawling archipelago with 3 roaming bosses that shoot back, room-code multiplayer, and live chat. Press F to fly, C to switch camera, E to attack.</p>', unsafe_allow_html=True)

if "od_player_id" not in st.session_state:
    st.session_state.od_player_id = uuid.uuid4().hex[:8]
if "od_room" not in st.session_state:
    st.session_state.od_room = ""
if "od_name" not in st.session_state:
    st.session_state.od_name = "Drifter" + st.session_state.od_player_id[:3]
if "od_color" not in st.session_state:
    st.session_state.od_color = random.choice(["#7cf7ff", "#f472b6", "#a78bfa", "#facc15", "#4ade80", "#fb7185"])
if "od_hp" not in st.session_state:
    st.session_state.od_hp = 100

if "od_mode" not in st.session_state:
    st.session_state.od_mode = "multiplayer"

# --- Room / identity setup ---
if not st.session_state.od_room:
    st.markdown("#### Choose how to play")
    mode_choice = st.radio(
        "Mode", ["Multiplayer (room code)", "Singleplayer"],
        horizontal=True, label_visibility="collapsed"
    )
    is_solo = mode_choice.startswith("Singleplayer")

    if is_solo:
        c1, c2 = st.columns([3, 1])
        with c1:
            name_in = st.text_input("Callsign", value=st.session_state.od_name)
        with c2:
            st.write("")
            st.write("")
            if st.button("Launch ▸", use_container_width=True):
                st.session_state.od_name = name_in.strip()[:16] or st.session_state.od_name
                st.session_state.od_mode = "singleplayer"
                st.session_state.od_room = "SOLO-" + st.session_state.od_player_id
                st.rerun()
    else:
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            name_in = st.text_input("Callsign", value=st.session_state.od_name)
        with c2:
            room_in = st.text_input("Room code", value="MAIN", help="Share this code with friends to land in the same world.")
        with c3:
            st.write("")
            st.write("")
            if st.button("Launch ▸", use_container_width=True):
                st.session_state.od_name = name_in.strip()[:16] or st.session_state.od_name
                st.session_state.od_mode = "multiplayer"
                st.session_state.od_room = room_in.strip().upper()[:12] or "MAIN"
                st.rerun()
    st.stop()

is_solo = st.session_state.od_mode == "singleplayer"

room = st.session_state.od_room
my_id = st.session_state.od_player_id

mode_label = "Solo flight" if is_solo else f"Room <b>{room}</b>"
st.markdown(
    f'<div style="text-align:center; color:#7cf7ff; font-size:0.85rem; margin-bottom:0.5rem;">'
    f'{mode_label} · playing as <b>{st.session_state.od_name}</b> '
    f'<a href="?" style="color:#a9a4d0; margin-left:12px;">leave</a></div>',
    unsafe_allow_html=True
)

# --- Handle incoming sync payload from the client (position, chat, boss damage) ---
sync_raw = st.session_state.get("od_sync_data", "")
state = load_json(room_state_path(room), {"players": {}, "bosses": default_bosses()})
if "bosses" not in state:
    state["bosses"] = default_bosses()

if sync_raw:
    try:
        payload = json.loads(sync_raw)
        p = payload.get("player", {})
        state["players"][my_id] = {
            "name": st.session_state.od_name,
            "color": st.session_state.od_color,
            "x": p.get("x", 0), "y": p.get("y", 8), "z": p.get("z", 0),
            "yaw": p.get("yaw", 0),
            "hp": p.get("hp", st.session_state.od_hp),
            "pvp": bool(p.get("pvp", False)),
            "last_seen": time.time(),
        }
        st.session_state.od_hp = p.get("hp", st.session_state.od_hp)

        boss_dmg = payload.get("boss_damage", {}) or {}
        for slot_str, dmg in boss_dmg.items():
            try:
                slot = int(slot_str)
            except Exception:
                continue
            if slot < 0 or slot >= len(state["bosses"]) or not dmg:
                continue
            b = state["bosses"][slot]
            if b.get("alive", True):
                b["hp"] = max(0, b["hp"] - dmg)
                if b["hp"] <= 0:
                    b["alive"] = False
                    b["respawn_at"] = time.time() + 12

        pvp_dmg = payload.get("pvp_damage", {}) or {}
        if pvp_dmg:
            state.setdefault("pvp_incoming", {})
            for target_id, dmg in pvp_dmg.items():
                if not dmg or target_id == my_id:
                    continue
                state["pvp_incoming"][target_id] = state["pvp_incoming"].get(target_id, 0) + dmg

    except Exception:
        pass

# apply any PvP damage other players have dealt to me since my last request, then clear it
incoming_pvp = state.get("pvp_incoming", {}).pop(my_id, 0)
if incoming_pvp:
    st.session_state.od_hp = max(0, st.session_state.od_hp - incoming_pvp)
    if st.session_state.od_hp <= 0:
        st.session_state.od_hp = 100

# respawn any boss whose timer elapsed
for b in state["bosses"]:
    if not b.get("alive", True) and time.time() > b.get("respawn_at", 0):
        tier = b.get("tier", 1) + 1
        b["tier"] = tier
        b["hp"] = b["max_hp"] = 900 + (tier - 1) * 350
        b["alive"] = True
        b["respawn_at"] = 0

# prune stale players (not synced in 10s)
now = time.time()
state["players"] = {pid: pl for pid, pl in state["players"].items() if now - pl.get("last_seen", 0) < 10}
save_json(room_state_path(room), state)

other_players = [
    {"id": pid, **pl} for pid, pl in state["players"].items() if pid != my_id
]
bosses_state = state["bosses"]
chat_log = load_json(room_chat_path(room), [])[-20:]

# internal widgets the JS heartbeat uses to push position/damage/chat back into Streamlit.
# the text area is hidden via CSS above; the sync button is kept tiny and tucked to the side
# rather than fully hidden, since reliably hiding it with CSS alone isn't feasible.
st.text_area("od_sync_data", key="od_sync_data", label_visibility="collapsed")
sync_col, _ = st.columns([1, 30])
with sync_col:
    if st.button("⛭", key="od_sync_btn", help="internal room sync — safe to ignore"):
        st.rerun()

INIT_DATA = json.dumps({
    "myId": my_id,
    "myName": st.session_state.od_name,
    "myColor": st.session_state.od_color,
    "myHp": st.session_state.od_hp,
    "otherPlayers": other_players,
    "bosses": bosses_state,
    "isSolo": is_solo,
})

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
    <div id="od-hp" style="margin-top:8px; font-size:0.85rem; color:#fb7185;
        background:rgba(20,14,50,0.55); backdrop-filter: blur(8px); padding:6px 14px; border-radius:12px;
        border:1px solid rgba(251,113,133,0.3);">❤ HP: 100</div>
    <div id="od-safezone" style="display:none; margin-top:8px; font-size:0.85rem; color:#4ade80;
        background:rgba(20,14,50,0.55); backdrop-filter: blur(8px); padding:6px 14px; border-radius:12px;
        border:1px solid rgba(74,222,128,0.4);">🏝 Safe Zone — no damage</div>
    <div id="od-shield" style="margin-top:8px; font-size:0.85rem; color:#7cf7ff;
        background:rgba(20,14,50,0.55); backdrop-filter: blur(8px); padding:6px 14px; border-radius:12px;
        border:1px solid rgba(124,247,255,0.3);">🛡 Shield: ready (Q)</div>
    <div id="od-weapon" style="margin-top:8px; font-size:0.85rem; color:#facc15;
        background:rgba(20,14,50,0.55); backdrop-filter: blur(8px); padding:6px 14px; border-radius:12px;
        border:1px solid rgba(250,204,21,0.3);">🎯 Weapon: Target Missiles (2)</div>
    <div id="od-pvp" style="margin-top:8px; font-size:0.85rem; color:#94a3b8;
        background:rgba(20,14,50,0.55); backdrop-filter: blur(8px); padding:6px 14px; border-radius:12px;
        border:1px solid rgba(148,163,184,0.3);">⚔ PvP: OFF (P)</div>
  </div>

  <div id="od-boss-hud" style="position:absolute; top:14px; left:50%; transform:translateX(-50%); z-index:5;
      width:min(66%,520px); font-family:'Outfit',sans-serif; color:#e8e6ff; text-align:center;
      display:flex; gap:10px; justify-content:center;">
    <div class="od-boss-slot" id="od-boss-slot-0" style="flex:1; min-width:0;">
      <div class="od-boss-name" id="od-boss-name-0" style="font-size:0.78rem; font-weight:700; letter-spacing:0.04em; margin-bottom:4px;
          text-shadow:0 0 8px rgba(244,114,182,0.6); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">VOID WYRM · T1</div>
      <div style="height:11px; border-radius:8px; background:rgba(20,14,50,0.6); border:1px solid rgba(244,114,182,0.35); overflow:hidden;">
        <div class="od-boss-bar" id="od-boss-bar-0" style="height:100%; width:100%; background:linear-gradient(90deg,#f472b6,#a78bfa);"></div>
      </div>
    </div>
    <div class="od-boss-slot" id="od-boss-slot-1" style="flex:1; min-width:0;">
      <div class="od-boss-name" id="od-boss-name-1" style="font-size:0.78rem; font-weight:700; letter-spacing:0.04em; margin-bottom:4px;
          text-shadow:0 0 8px rgba(96,165,250,0.6); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">NOVA SENTINEL · T1</div>
      <div style="height:11px; border-radius:8px; background:rgba(20,14,50,0.6); border:1px solid rgba(96,165,250,0.35); overflow:hidden;">
        <div class="od-boss-bar" id="od-boss-bar-1" style="height:100%; width:100%; background:linear-gradient(90deg,#60a5fa,#a78bfa);"></div>
      </div>
    </div>
    <div class="od-boss-slot" id="od-boss-slot-2" style="flex:1; min-width:0;">
      <div class="od-boss-name" id="od-boss-name-2" style="font-size:0.78rem; font-weight:700; letter-spacing:0.04em; margin-bottom:4px;
          text-shadow:0 0 8px rgba(251,146,60,0.6); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">CRIMSON WARDEN · T1</div>
      <div style="height:11px; border-radius:8px; background:rgba(20,14,50,0.6); border:1px solid rgba(251,146,60,0.35); overflow:hidden;">
        <div class="od-boss-bar" id="od-boss-bar-2" style="height:100%; width:100%; background:linear-gradient(90deg,#fb923c,#a78bfa);"></div>
      </div>
    </div>
  </div>

  <div id="od-players-hud" style="position:absolute; top:14px; right:14px; z-index:5; color:#c9c4ff;
      font-family:'Outfit',sans-serif; font-size:0.78rem; background:rgba(20,14,50,0.55);
      backdrop-filter: blur(8px); padding:8px 14px; border-radius:12px; border:1px solid rgba(124,247,255,0.2);
      text-align:right; max-width:200px;">
    <div style="font-weight:600; margin-bottom:4px;">Best Race: <span id="od-best">--</span></div>
    <div id="od-roster">Players online: 1</div>
  </div>

  <div id="od-minimap-wrap" style="position:absolute; top:76px; right:14px; z-index:5;
      background:rgba(10,7,26,0.6); backdrop-filter: blur(8px); border-radius:50%;
      border:1px solid rgba(124,247,255,0.25); padding:4px; box-shadow:0 0 18px rgba(124,247,255,0.08);">
    <canvas id="od-minimap" width="160" height="160" style="display:block; border-radius:50%;"></canvas>
  </div>

  <div id="od-shop-btn" style="position:absolute; top:76px; right:190px; z-index:5; cursor:pointer;
      color:#facc15; font-family:'Outfit',sans-serif; font-size:0.8rem; background:rgba(20,14,50,0.55);
      backdrop-filter: blur(8px); padding:8px 14px; border-radius:12px; border:1px solid rgba(250,204,21,0.35);
      user-select:none;">🛒 Shop (B)</div>

  <div id="od-shop-panel" style="display:none; position:absolute; inset:0; z-index:9;
      align-items:center; justify-content:center; background:rgba(4,3,13,0.8); backdrop-filter: blur(6px);
      font-family:'Outfit',sans-serif; color:#e8e6ff;">
    <div style="width:min(90%,480px); background:rgba(20,14,50,0.9); border:1px solid rgba(250,204,21,0.3);
        border-radius:18px; padding:22px; box-shadow:0 0 40px rgba(0,0,0,0.5);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <div style="font-size:1.3rem; font-weight:800; color:#facc15;">🛒 Drifter's Shop</div>
        <div style="font-size:0.9rem; color:#c9c4ff;">✨ Currency: <span id="od-shop-currency">0</span></div>
      </div>
      <div id="od-shop-items" style="display:flex; flex-direction:column; gap:10px; max-height:50vh; overflow-y:auto;"></div>
      <div style="text-align:center; margin-top:16px;">
        <button id="od-shop-close" style="padding:10px 26px; border-radius:12px; border:none; cursor:pointer;
            font-family:'Outfit',sans-serif; font-weight:600; color:#04030d;
            background:linear-gradient(90deg,#7cf7ff,#a78bfa);">Close</button>
      </div>
    </div>
  </div>

  <div id="od-scope" style="position:absolute; inset:0; z-index:8; display:none; pointer-events:none;">
    <svg width="100%" height="100%" style="position:absolute; inset:0;">
      <defs>
        <mask id="od-scope-mask">
          <rect x="0" y="0" width="100%" height="100%" fill="white"/>
          <circle cx="50%" cy="50%" r="28%" fill="black"/>
        </mask>
      </defs>
      <rect x="0" y="0" width="100%" height="100%" fill="black" mask="url(#od-scope-mask)"/>
      <circle cx="50%" cy="50%" r="28%" fill="none" stroke="#0a0a0a" stroke-width="6"/>
      <line x1="50%" y1="8%" x2="50%" y2="38%" stroke="#0a0a0a" stroke-width="2"/>
      <line x1="50%" y1="62%" x2="50%" y2="92%" stroke="#0a0a0a" stroke-width="2"/>
      <line x1="8%" y1="50%" x2="38%" y2="50%" stroke="#0a0a0a" stroke-width="2"/>
      <line x1="62%" y1="50%" x2="92%" y2="50%" stroke="#0a0a0a" stroke-width="2"/>
      <circle cx="50%" cy="50%" r="2.5" fill="#f472b6"/>
    </svg>
  </div>

  <div id="od-msg" style="position:absolute; bottom:16px; left:50%; transform:translateX(-50%); z-index:5;
      color:#e8e6ff; font-family:'Outfit',sans-serif; font-size:0.85rem; text-align:center;
      background:rgba(20,14,50,0.55); backdrop-filter: blur(8px); padding:8px 18px; border-radius:14px;
      border:1px solid rgba(124,247,255,0.2); pointer-events:none; max-width:80%;">
      WASD/arrows move · SPACE jump · F fly · C camera · drag to look · E to fire (hold for rapid fire) · 1 bullets · 2 target missiles · 3 blast missiles · 4 toggles rapid fire · right-click toggles scope · P toggles PvP · B opens shop · green crosses heal you · islands are a safe zone
  </div>

  <div id="od-startscreen" style="position:absolute; inset:0; z-index:10; display:flex; flex-direction:column;
      align-items:center; justify-content:center; background:rgba(4,3,13,0.85); backdrop-filter: blur(6px);
      font-family:'Outfit',sans-serif; color:#e8e6ff; text-align:center;">
    <div style="font-size:2rem; font-weight:800; background:linear-gradient(90deg,#7cf7ff,#a78bfa,#f472b6);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:8px;">OrbitDrift</div>
    <div style="max-width:440px; color:#a9a4d0; font-weight:300; margin-bottom:22px; line-height:1.5;">
      Explore a huge archipelago with other drifters. Walk the islands as your character, or
      press F to hop into your ship and fly. Switch between rapid-fire bullets, auto-aiming
      target missiles, and area-damage blast missiles (keys 1/2/3) — press 4 to toggle rapid
      fire on any of them and hold E to unload, and take on 3 bosses at once who roam the map
      and shoot back. Right-click toggles a scope for precise aim. Race checkpoint gates, and
      chat below the scene. Everyone in this room shares the same boss fights.
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
  const INIT = __INIT_DATA__;

  const wrap = document.getElementById('od-wrap');
  const canvas = document.getElementById('od-canvas');
  const modeEl = document.getElementById('od-mode');
  const timerEl = document.getElementById('od-timer');
  const orbsEl = document.getElementById('od-orbs');
  const hpEl = document.getElementById('od-hp');
  const safeZoneEl = document.getElementById('od-safezone');
  const shieldEl = document.getElementById('od-shield');
  const weaponEl = document.getElementById('od-weapon');
  const pvpEl = document.getElementById('od-pvp');
  const minimapCanvas = document.getElementById('od-minimap');
  const minimapCtx = minimapCanvas.getContext('2d');
  const shopBtn = document.getElementById('od-shop-btn');
  const shopPanel = document.getElementById('od-shop-panel');
  const shopItemsEl = document.getElementById('od-shop-items');
  const shopCurrencyEl = document.getElementById('od-shop-currency');
  const shopCloseBtn = document.getElementById('od-shop-close');
  const bestEl = document.getElementById('od-best');
  const rosterEl = document.getElementById('od-roster');
  const bossBarEls = [document.getElementById('od-boss-bar-0'), document.getElementById('od-boss-bar-1'), document.getElementById('od-boss-bar-2')];
  const bossNameEls = [document.getElementById('od-boss-name-0'), document.getElementById('od-boss-name-1'), document.getElementById('od-boss-name-2')];
  const msgEl = document.getElementById('od-msg');
  const scopeEl = document.getElementById('od-scope');
  const startScreen = document.getElementById('od-startscreen');
  const startBtn = document.getElementById('od-startbtn');

  let scene, camera, renderer, clock;
  let player, playerVel = new THREE.Vector3();
  let humanVisual = null, shipVisual = null;
  let onGround = false;
  let onIsland = false;
  let thirdPerson = true;
  let started = false;
  let keys = {};

  let islands = [], orbs = [], collected = 0, ORB_TOTAL = 0;
  let healthPacks = [];
  let raceGates = [], raceActive = false, raceStart = 0, raceCheckpoint = 0, bestTime = null;
  let yaw = 0, pitch = 0.28;
  let dragging = false, lastMouseX = 0, lastMouseY = 0;
  let flying = false;
  let scoping = false;
  let pvpEnabled = false;
  let currency = 150;
  let upgrades = { maxHpBoost: 0, dmgBoost: 0, speedBoost: 0, shieldBoost: 0 };
  const SHOP_ITEMS = [
    { key: 'maxHpBoost', name: '+20 Max HP', desc: 'Permanently raises your maximum health.', cost: 15, max: 5 },
    { key: 'dmgBoost', name: '+10% Weapon Damage', desc: 'All weapons hit harder.', cost: 20, max: 5 },
    { key: 'speedBoost', name: '+8% Move Speed', desc: 'Move and fly a bit faster.', cost: 18, max: 5 },
    { key: 'shieldBoost', name: '+1s Shield Duration', desc: 'Your shield blocks damage longer.', cost: 15, max: 5 }
  ];
  const BASE_FOV = 65;
  const SCOPE_FOV = 22;

  let myHp = INIT.myHp || 100;
  let shieldActive = false, shieldReadyAt = 0, shieldEndsAt = 0, shieldMesh = null;
  const SHIELD_DURATION = 4;
  const SHIELD_COOLDOWN = 10;
  let ghosts = {};       // id -> {mesh, label, target: {x,y,z,yaw}}
  const BOSS_TYPES = [
    { name: 'VOID WYRM', color: 0x8a1f55, emissive: 0xf472b6, boltColor: 0xf472b6 },
    { name: 'NOVA SENTINEL', color: 0x1f3a6b, emissive: 0x60a5fa, boltColor: 0x60a5fa },
    { name: 'CRIMSON WARDEN', color: 0x7a2f10, emissive: 0xfb923c, boltColor: 0xfb923c }
  ];
  let bossMeshes = [null, null, null];
  let bossHp = [INIT.bosses[0].hp, INIT.bosses[1].hp, INIT.bosses[2].hp];
  let bossMaxHp = [INIT.bosses[0].max_hp, INIT.bosses[1].max_hp, INIT.bosses[2].max_hp];
  let bossAlive = [INIT.bosses[0].alive, INIT.bosses[1].alive, INIT.bosses[2].alive];
  let bossTier = [INIT.bosses[0].tier || 1, INIT.bosses[1].tier || 1, INIT.bosses[2].tier || 1];
  function bossTypeOf(i) { return BOSS_TYPES[(bossTier[i] - 1) % BOSS_TYPES.length]; }
  let bossAnchors = [
    { x: 130, z: 0 }, { x: -110, z: 100 }, { x: -60, z: -150 }
  ];
  let bossLastShot = [0, 0, 0];
  let pendingBossDamage = {};
  let pendingPvpDamage = {};
  let lastAttack = 0;
  const ATTACK_COOLDOWN = 0.5;
  const ATTACK_RANGE = 60;

  const ENEMY_TYPES = {
    sentinel: { label: 'Sentinel Orb', color: 0x2dd4bf, emissive: 0x0f766e, hp: 35, aggressive: false, chases: false },
    turret:   { label: 'Turret', color: 0xef4444, emissive: 0x7f1d1d, hp: 50, aggressive: true, chases: false },
    chaser:   { label: 'Chaser', color: 0xa855f7, emissive: 0x581c87, hp: 45, aggressive: true, chases: true }
  };
  let enemies = [];
  let enemyBolts = [];
  let bossBolts = [];

  let raycaster = new THREE.Raycaster();
  let lockedTarget = null; // { kind: 'boss' } or { kind: 'enemy', ref: enemyObj }
  let lockRing = null;
  let activeBolts = [];
  let mouseDownPos = null, mouseDownTime = 0;
  let lastHitFlash = 0;
  let gunGroup = null, gunMuzzle = null, gunBasePos = null, gunKick = 0;
  let freeBolts = [];
  let trailPuffs = [];
  let explosions = [];
  let bullets = [];
  let currentWeapon = 'bullet';
let rapidFire = false;

const RAPID_MULT = 0.32;

const WEAPON_LABELS = {
  bullet: 'Bullets',
  missile: 'Target Missiles',
  blast: 'Blast Missiles',
  plasma: 'Plasma Cannon',
  rapid: 'Rapid Cannon',
  heavy: 'Heavy Cannon'
};

const WEAPON_PRICES = {
  bullet: 0,
  missile: 20,
  blast: 35,
  plasma: 50,
  rapid: 65,
  heavy: 80
};

let unlockedWeapons = {
  bullet: true,
  missile: false,
  blast: false,
  plasma: false,
  rapid: false,
  heavy: false
};

  const BULLET_COOLDOWN = 0.18;
  const BULLET_SPEED = 220;
  const BULLET_LIFETIME = 1.4;
  const BULLET_BOSS_RADIUS = 2.6;
  const BULLET_ENEMY_RADIUS = 1.5;
  const BLAST_COOLDOWN = 1.4;
  const BLAST_RADIUS = 7;
  const FREE_BOLT_SPEED = 70;
  const FREE_BOLT_LIFETIME = 8;
  const FREE_BOLT_BOSS_RADIUS = 2.6;
  const FREE_BOLT_ENEMY_RADIUS = 1.5;

  const GRAVITY = -24;
  const MOVE_SPEED = 20;
  const JUMP_SPEED = 13;
  const FLY_SPEED_MULT = 2.4;

  function loadBest() {
    try {
      const v = localStorage.getItem('orbitdrift_best');
      if (v) { bestTime = parseFloat(v); bestEl.textContent = bestTime.toFixed(2) + 's'; }
    } catch(e) {}
  }
  function saveBest(t) {
    bestTime = t;
    try { localStorage.setItem('orbitdrift_best', t.toString()); } catch(e) {}
    bestEl.textContent = t.toFixed(2) + 's';
  }

  function loadShopData() {
    try {
      const c = localStorage.getItem('orbitdrift_currency');
      currency = c ? parseInt(c, 10) : 0;
      const u = localStorage.getItem('orbitdrift_upgrades');
      if (u) upgrades = Object.assign(upgrades, JSON.parse(u));
    } catch(e) {}
  }
  function saveShopData() {
  const saved = localStorage.getItem('orbitdrift_shop');

if (saved) {
  try {
    const data = JSON.parse(saved);

    currency = Number(data.currency ?? 150);

    if (data.upgrades) {
      upgrades = {
        ...upgrades,
        ...data.upgrades
      };
    }

    if (data.unlockedWeapons) {
      unlockedWeapons = {
        ...unlockedWeapons,
        ...data.unlockedWeapons
      };
    }
  } catch (e) {
    console.warn('Could not load shop data:', e);
    currency = 150;
  }
} else {
  // First time playing
  currency = 150;
  saveShopData();
}

  function currentMaxHp() { return 100 + upgrades.maxHpBoost * 20; }
  function dmgMultiplier() { return 1 + upgrades.dmgBoost * 0.1; }
  function speedMultiplier() { return 1 + upgrades.speedBoost * 0.08; }
  function shieldDurationBonus() { return upgrades.shieldBoost * 1; }

  function renderShop() {
  shopCurrencyEl.textContent = currency;
  shopItemsEl.innerHTML = '';

  // =========================
  // WEAPONS
  // =========================

  Object.keys(WEAPON_PRICES).forEach(weapon => {
    const owned = unlockedWeapons[weapon];
    const price = WEAPON_PRICES[weapon];

    const row = document.createElement('div');

    row.style.cssText =
      'display:flex; justify-content:space-between; align-items:center; gap:12px;' +
      'background:rgba(255,255,255,0.04); border-radius:12px; padding:10px 14px;';

    const info = document.createElement('div');

    const weaponIcons = {
      bullet: '🔫',
      missile: '🚀',
      blast: '💥'
    };

    info.innerHTML =
      '<div style="font-weight:600;">' +
      weaponIcons[weapon] + ' ' + WEAPON_LABELS[weapon] +
      '</div>' +
      '<div style="font-size:0.78rem; color:#a9a4d0;">' +
      (weapon === 'bullet'
        ? 'Basic weapon. Fires straight.'
        : weapon === 'missile'
        ? 'Locks onto enemies and follows them.'
        : 'Explodes and damages enemies nearby.') +
      '</div>';

    row.appendChild(info);

    const btn = document.createElement('button');

    if (owned) {
      btn.textContent = 'OWNED';
      btn.disabled = true;
    } else {
      btn.textContent = 'Buy · ✨' + price;
      btn.disabled = currency < price;
    }

    btn.style.cssText =
      'padding:8px 16px; border-radius:10px; border:none;' +
      'cursor:pointer; font-family:Outfit,sans-serif; font-weight:600;' +
      'white-space:nowrap; color:#04030d; background:' +
      (owned || currency < price
        ? '#555'
        : 'linear-gradient(90deg,#7cf7ff,#a78bfa)');

    btn.addEventListener('click', () => {
      if (owned || currency < price) return;

      currency -= price;
      unlockedWeapons[weapon] = true;

      saveShopData();
      renderShop();

      msgEl.textContent =
        'Purchased ' + WEAPON_LABELS[weapon] + '!';
    });

    row.appendChild(btn);
    shopItemsEl.appendChild(row);
  });

  // =========================
  // UPGRADES
  // =========================

  SHOP_ITEMS.forEach(item => {
    const level = upgrades[item.key] || 0;
    const maxed = level >= item.max;
    const cost = item.cost + level * 6;

    const row = document.createElement('div');

    row.style.cssText =
      'display:flex; justify-content:space-between; align-items:center; gap:12px;' +
      'background:rgba(255,255,255,0.04); border-radius:12px; padding:10px 14px;';

    const info = document.createElement('div');

    info.innerHTML =
      '<div style="font-weight:600;">' +
      item.name +
      ' <span style="color:#94a3b8; font-weight:400;">(Lv ' +
      level + '/' + item.max + ')</span></div>' +
      '<div style="font-size:0.78rem; color:#a9a4d0;">' +
      item.desc +
      '</div>';

    row.appendChild(info);

    const btn = document.createElement('button');

    btn.textContent =
      maxed ? 'MAXED' : ('Buy · ✨' + cost);

    btn.disabled =
      maxed || currency < cost;

    btn.style.cssText =
      'padding:8px 16px; border-radius:10px; border:none;' +
      'cursor:pointer; font-family:Outfit,sans-serif; font-weight:600;' +
      'white-space:nowrap; color:#04030d; background:' +
      (maxed
        ? '#555'
        : (currency < cost
          ? '#555'
          : 'linear-gradient(90deg,#7cf7ff,#a78bfa)'));

    btn.addEventListener('click', () => {
      if (maxed || currency < cost) return;

      currency -= cost;
      upgrades[item.key] = level + 1;

      saveShopData();
      applyUpgrades();
      renderShop();

      msgEl.textContent =
        'Purchased ' + item.name + '!';
    });

    row.appendChild(btn);
    shopItemsEl.appendChild(row);
  });
}

  function applyUpgrades() {
    const newMax = currentMaxHp();
    if (myHp > newMax) myHp = newMax;
    hpEl.textContent = '❤ HP: ' + Math.round(myHp) + ' / ' + newMax;
  }

  function updateMinimap() {
    const ctx = minimapCtx;
    const W = 160, H = 160, cx = W / 2, cy = H / 2;
    const R = 260; // world units shown to the edge of the minimap
    const scale = (W / 2 - 6) / R;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(10,7,26,0.85)';
    ctx.beginPath();
    ctx.arc(cx, cy, W / 2, 0, Math.PI * 2);
    ctx.fill();

    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, W / 2 - 2, 0, Math.PI * 2);
    ctx.clip();

    const px = player.position.x, pz = player.position.z;

    // Islands (faint)
    ctx.fillStyle = 'rgba(124,247,255,0.18)';
    islands.forEach(isl => {
      const dx = isl.x - px, dz = isl.z - pz;
      if (dx * dx + dz * dz > R * R * 1.3) return;
      const mx = cx + dx * scale, my = cy + dz * scale;
      ctx.beginPath();
      ctx.arc(mx, my, Math.max(1.5, isl.r * scale), 0, Math.PI * 2);
      ctx.fill();
    });

    // Bosses
    for (let i = 0; i < 3; i++) {
      if (!bossAlive[i] || !bossMeshes[i]) continue;
      const dx = bossMeshes[i].position.x - px, dz = bossMeshes[i].position.z - pz;
      const dist = Math.sqrt(dx * dx + dz * dz);
      const clampedScale = dist > R ? (R / dist) * scale : scale;
      const mx = cx + dx * clampedScale, my = cy + dz * clampedScale;
      ctx.fillStyle = ['#f472b6', '#60a5fa', '#fb923c'][i];
      ctx.beginPath();
      ctx.arc(mx, my, 4, 0, Math.PI * 2);
      ctx.fill();
    }

    // Other players
    Object.values(ghosts).forEach(g => {
      const dx = g.mesh.position.x - px, dz = g.mesh.position.z - pz;
      const dist = Math.sqrt(dx * dx + dz * dz);
      if (dist > R * 1.4) return;
      const clampedScale = dist > R ? (R / dist) * scale : scale;
      const mx = cx + dx * clampedScale, my = cy + dz * clampedScale;
      ctx.fillStyle = g.color || '#a78bfa';
      ctx.beginPath();
      ctx.arc(mx, my, 3.5, 0, Math.PI * 2);
      ctx.fill();
      if (g.pvp) {
        ctx.strokeStyle = '#fb7185';
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.arc(mx, my, 5.5, 0, Math.PI * 2);
        ctx.stroke();
      }
    });

    ctx.restore();

    // Player arrow (always centered, rotated to facing)
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(yaw);
    ctx.fillStyle = '#7cf7ff';
    ctx.beginPath();
    ctx.moveTo(0, -6);
    ctx.lineTo(4, 5);
    ctx.lineTo(-4, 5);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    ctx.strokeStyle = 'rgba(124,247,255,0.3)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, W / 2 - 1, 0, Math.PI * 2);
    ctx.stroke();
  }

  function toggleShop() {
    const open = shopPanel.style.display !== 'flex';
    shopPanel.style.display = open ? 'flex' : 'none';
    if (open) renderShop();
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
    scene.add(camera);
    buildGunViewmodel();

    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setSize(w0, h0, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    scene.add(new THREE.AmbientLight(0x8888ff, 0.6));
    const sun = new THREE.DirectionalLight(0xfff0e0, 1.1);
    sun.position.set(30, 50, 20);
    scene.add(sun);
    const rim = new THREE.PointLight(0xff66cc, 1.2, 300);
    rim.position.set(-30, 20, -30);
    scene.add(rim);

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

    player = new THREE.Group();
    player.position.set(0, 6, 0);
    scene.add(player);
    humanVisual = buildHumanCharacter();
    shipVisual = buildSpaceship();
    player.add(humanVisual);
    player.add(shipVisual);
    updatePlayerAppearance();

    const shieldGeo = new THREE.SphereGeometry(1.4, 16, 16);
    const shieldMat = new THREE.MeshStandardMaterial({
      color: 0x7cf7ff, emissive: 0x2dd4bf, emissiveIntensity: 0.6,
      transparent: true, opacity: 0.28, side: THREE.DoubleSide
    });
    shieldMesh = new THREE.Mesh(shieldGeo, shieldMat);
    shieldMesh.visible = false;
    player.add(shieldMesh);

    buildIslands();
    buildOrbs();
    buildRace();
    buildBosses();
    buildEnemies();
    buildHealthPacks();
    syncGhosts(INIT.otherPlayers);

    clock = new THREE.Clock();

    window.addEventListener('keydown', e => {
      const k = e.key.toLowerCase();
      if (!keys[k]) {
        if (k === 'c') thirdPerson = !thirdPerson;
        if (k === 'f') { flying = !flying; playerVel.set(0,0,0); updatePlayerAppearance(); msgEl.textContent = flying ? 'Flying enabled — piloting your ship. W/S move along your view, SPACE/SHIFT for extra up/down.' : 'Flying disabled — back on foot, gravity is back on.'; }
        if (k === 'e') fireBolt();
        if (k === 'q') activateShield();
        if (k === '1') switchWeapon('bullet');
        if (k === '2') switchWeapon('missile');
        if (k === '3') switchWeapon('blast');
        if (k === '4') switchWeapon('plasma');
        if (k === '5') switchWeapon('rapid');
        if (k === '6') switchWeapon('heavy');
        if (k === '4') toggleRapidFire();
        if (k === 'p') togglePvp();
        if (k === 'b') toggleShop();
      }
      keys[k] = true;
      if (e.key.startsWith('Arrow')) e.preventDefault();
    });
    window.addEventListener('keyup', e => keys[e.key.toLowerCase()] = false);
    window.addEventListener('resize', onResize);
    window.addEventListener('blur', () => { scoping = false; scopeEl.style.display = 'none'; dragging = false; });

    canvas.style.cursor = 'grab';
    canvas.addEventListener('contextmenu', e => e.preventDefault());
    canvas.addEventListener('mousedown', e => {
      if (!started) return;
      if (e.button === 2) {
        toggleScope();
        return;
      }
      dragging = true;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
      mouseDownPos = { x: e.clientX, y: e.clientY };
      mouseDownTime = performance.now();
      canvas.style.cursor = 'grabbing';
    });
    window.addEventListener('mouseup', e => {
      if (e.button === 2) return;
      dragging = false;
      canvas.style.cursor = 'grab';
      if (mouseDownPos && started) {
        const moved = Math.hypot(e.clientX - mouseDownPos.x, e.clientY - mouseDownPos.y);
        const elapsed = performance.now() - mouseDownTime;
        if (moved < 6 && elapsed < 350) tryLockTarget(e.clientX, e.clientY);
      }
      mouseDownPos = null;
    });
    window.addEventListener('mousemove', e => {
      if (!dragging) return;
      const dx = e.clientX - lastMouseX;
      const dy = e.clientY - lastMouseY;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
      const sens = scoping ? 0.0013 : 0.0035;
      yaw -= dx * sens;
      pitch -= dy * sens;
      pitch = Math.max(-1.3, Math.min(1.3, pitch));
    });

    loadBest();
    loadShopData();
    applyUpgrades();
    updateHudStatic();
    animate();

    [50, 200, 600].forEach(t => setTimeout(onResize, t));
    window.addEventListener('load', onResize);

    setInterval(heartbeat, 1500);
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

  function buildHumanCharacter() {
    const group = new THREE.Group();
    const suitMat = new THREE.MeshStandardMaterial({ color: 0x2a3a55, metalness: 0.3, roughness: 0.6 });
    const accentMat = new THREE.MeshStandardMaterial({ color: 0x7cf7ff, emissive: 0x2dd4bf, emissiveIntensity: 0.6 });
    const skinMat = new THREE.MeshStandardMaterial({ color: 0xe8b892, roughness: 0.7 });
    const visorMat = new THREE.MeshStandardMaterial({ color: 0x0a2a33, emissive: 0x2dd4bf, emissiveIntensity: 0.8, metalness: 0.6, roughness: 0.2 });

    const hasCapsule = typeof THREE.CapsuleGeometry === 'function';
    const torso = new THREE.Mesh(hasCapsule ? new THREE.CapsuleGeometry(0.32, 0.7, 4, 8) : new THREE.CylinderGeometry(0.32, 0.28, 1, 8), suitMat);
    torso.position.set(0, 0.15, 0);
    group.add(torso);

    const belt = new THREE.Mesh(new THREE.TorusGeometry(0.33, 0.05, 6, 12), accentMat);
    belt.position.set(0, -0.18, 0);
    belt.rotation.x = Math.PI / 2;
    group.add(belt);

    const head = new THREE.Mesh(new THREE.SphereGeometry(0.24, 12, 12), skinMat);
    head.position.set(0, 0.68, 0);
    group.add(head);

    const visor = new THREE.Mesh(new THREE.SphereGeometry(0.15, 10, 10), visorMat);
    visor.position.set(0, 0.68, 0.15);
    visor.scale.set(1, 0.7, 0.6);
    group.add(visor);

    const armGeo = hasCapsule ? new THREE.CapsuleGeometry(0.09, 0.55, 4, 6) : new THREE.CylinderGeometry(0.09, 0.09, 0.7, 6);
    const armL = new THREE.Mesh(armGeo, suitMat);
    armL.position.set(-0.42, 0.1, 0);
    armL.rotation.z = 0.18;
    group.add(armL);
    const armR = new THREE.Mesh(armGeo, suitMat);
    armR.position.set(0.42, 0.1, 0);
    armR.rotation.z = -0.18;
    group.add(armR);

    const legGeo = hasCapsule ? new THREE.CapsuleGeometry(0.11, 0.6, 4, 6) : new THREE.CylinderGeometry(0.11, 0.11, 0.75, 6);
    const legL = new THREE.Mesh(legGeo, suitMat);
    legL.position.set(-0.15, -0.6, 0);
    group.add(legL);
    const legR = new THREE.Mesh(legGeo, suitMat);
    legR.position.set(0.15, -0.6, 0);
    group.add(legR);

    const packGeo = new THREE.BoxGeometry(0.32, 0.4, 0.16);
    const pack = new THREE.Mesh(packGeo, accentMat);
    pack.position.set(0, 0.15, -0.24);
    group.add(pack);

    // Handheld weapon, attached to the right arm so it moves and rotates with it.
    const handWeapon = new THREE.Group();
    const gunMetal = new THREE.MeshStandardMaterial({ color: 0x2a2f45, metalness: 0.7, roughness: 0.35 });
    const gunAccent = new THREE.MeshStandardMaterial({ color: 0x7cf7ff, emissive: 0x2dd4bf, emissiveIntensity: 0.9 });
    const gunBody = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.08, 0.34), gunMetal);
    handWeapon.add(gunBody);
    const gunBarrel = new THREE.Mesh(new THREE.CylinderGeometry(0.028, 0.032, 0.22, 8), gunMetal);
    gunBarrel.rotation.x = Math.PI / 2;
    gunBarrel.position.set(0, 0.005, -0.28);
    handWeapon.add(gunBarrel);
    const gunTip = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.028, 0.05, 8), gunAccent);
    gunTip.rotation.x = Math.PI / 2;
    gunTip.position.set(0, 0.005, -0.39);
    handWeapon.add(gunTip);
    const gunGrip = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.16, 0.06), gunMetal);
    gunGrip.position.set(0, -0.1, 0.1);
    gunGrip.rotation.x = 0.3;
    handWeapon.add(gunGrip);
    handWeapon.position.set(0, -0.32, -0.1);
    handWeapon.rotation.x = -0.15;
    armR.add(handWeapon);
    group.userData.handWeapon = handWeapon;
    group.userData.handWeaponAccent = gunAccent;

    group.position.y = 0.75;
    return group;
  }

  function buildSpaceship() {
    const group = new THREE.Group();
    const hullMat = new THREE.MeshStandardMaterial({ color: 0xd8dbe6, metalness: 0.65, roughness: 0.3 });
    const accentMat = new THREE.MeshStandardMaterial({ color: 0x7cf7ff, emissive: 0x2dd4bf, emissiveIntensity: 0.7 });
    const cockpitMat = new THREE.MeshStandardMaterial({ color: 0x1a2a44, emissive: 0x3388ff, emissiveIntensity: 0.5, metalness: 0.4, roughness: 0.15, transparent: true, opacity: 0.85 });
    const engineMat = new THREE.MeshStandardMaterial({ color: 0xff8844, emissive: 0xff5511, emissiveIntensity: 1.4, transparent: true, opacity: 0.85 });

    const fuselage = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.42, 1.7, 10), hullMat);
    fuselage.rotation.x = Math.PI / 2;
    group.add(fuselage);

    const nose = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.6, 10), hullMat);
    nose.rotation.x = Math.PI / 2;
    nose.position.set(0, 0, -1.15);
    group.add(nose);

    const cockpit = new THREE.Mesh(new THREE.SphereGeometry(0.24, 12, 12), cockpitMat);
    cockpit.position.set(0, 0.18, -0.45);
    cockpit.scale.set(1, 0.85, 1.3);
    group.add(cockpit);

    const wingGeo = new THREE.BoxGeometry(1.3, 0.06, 0.55);
    const wingL = new THREE.Mesh(wingGeo, hullMat);
    wingL.position.set(-0.75, -0.02, 0.25);
    wingL.rotation.z = 0.06;
    group.add(wingL);
    const wingR = new THREE.Mesh(wingGeo, hullMat);
    wingR.position.set(0.75, -0.02, 0.25);
    wingR.rotation.z = -0.06;
    group.add(wingR);

    const finL = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.32, 0.24), accentMat);
    finL.position.set(-1.25, 0.14, 0.32);
    group.add(finL);
    const finR = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.32, 0.24), accentMat);
    finR.position.set(1.25, 0.14, 0.32);
    group.add(finR);

    const engineL = new THREE.Mesh(new THREE.ConeGeometry(0.14, 0.4, 8), engineMat);
    engineL.rotation.x = -Math.PI / 2;
    engineL.position.set(-0.3, -0.05, 0.95);
    group.add(engineL);
    const engineR = new THREE.Mesh(new THREE.ConeGeometry(0.14, 0.4, 8), engineMat);
    engineR.rotation.x = -Math.PI / 2;
    engineR.position.set(0.3, -0.05, 0.95);
    group.add(engineR);

    const stripe = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 1.4), accentMat);
    stripe.position.set(0, 0.28, -0.1);
    group.add(stripe);

    group.visible = false;
    return group;
  }

  function updatePlayerAppearance() {
    if (!humanVisual || !shipVisual) return;
    humanVisual.visible = !flying;
    shipVisual.visible = flying;
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
    ring(16, 90, 8, 6, 3.2, 5);
    ring(22, 180, 14, 10, 3, 5.5);
    ring(28, 290, 20, 14, 2.8, 6);
    ring(26, 400, 26, 16, 3, 5.5);
    ring(24, 520, 32, 20, 3.2, 6.5);
    ring(20, 650, 40, 24, 3.5, 7);
    ring(16, 780, 46, 26, 4, 7.5);
  }

  function buildOrbs() {
    const orbGeo = new THREE.OctahedronGeometry(0.8, 0);
    const orbMat = new THREE.MeshStandardMaterial({ color: 0xffe066, emissive: 0x996600, emissiveIntensity: 0.6 });
    islands.forEach(isl => {
      const m = new THREE.Mesh(orbGeo, orbMat.clone());
      m.position.set(isl.x + (Math.random()-0.5)*2, isl.y + 2.2 + Math.random()*1.5, isl.z + (Math.random()-0.5)*2);
      scene.add(m);
      orbs.push(m);
    });
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
    const gateMat = new THREE.MeshStandardMaterial({ color: 0xf472b6, emissive: 0x8a1f55, emissiveIntensity: 0.7, transparent: true, opacity: 0.85 });
    function makeGate(x, y, z) {
      const torus = new THREE.Mesh(new THREE.TorusGeometry(2.2, 0.25, 8, 24), gateMat.clone());
      torus.position.set(x, y, z);
      scene.add(torus);
      return { mesh: torus, x, y, z, hit: false };
    }
    raceGates.push(makeGate(0, 8, -8));
    raceGates.push(makeGate(90, 14, -90));
    raceGates.push(makeGate(200, 24, 60));
    raceGates.push(makeGate(320, 34, -140));
  }

  function buildEnemy(type, x, y, z) {
    const def = ENEMY_TYPES[type];
    const mat = new THREE.MeshStandardMaterial({ color: def.color, emissive: def.emissive, emissiveIntensity: 0.5, roughness: 0.5 });
    let mesh;
    if (type === 'sentinel') mesh = new THREE.Mesh(new THREE.OctahedronGeometry(1.1, 0), mat);
    else if (type === 'turret') mesh = new THREE.Mesh(new THREE.ConeGeometry(1, 1.8, 6), mat);
    else mesh = new THREE.Mesh(new THREE.IcosahedronGeometry(1, 0), mat);
    mesh.position.set(x, y, z);
    scene.add(mesh);
    return {
      mesh, type, def, hp: def.hp, maxHp: def.hp, alive: true,
      spawn: { x, y, z }, lastShot: 0, deadAt: 0
    };
  }

  function buildEnemies() {
    const types = ['sentinel', 'turret', 'chaser'];
    let i = 0;
    islands.forEach(isl => {
      if (isl.r < 3.5) return; // skip tiny islands
      if (Math.random() > 0.55) return; // not every island gets one
      const type = types[i % types.length];
      i++;
      const angle = Math.random() * Math.PI * 2;
      const dist = isl.r * 0.6;
      buildEnemyToScene(type, isl.x + Math.cos(angle) * dist, isl.y + 2, isl.z + Math.sin(angle) * dist);
    });
  }
  function buildEnemyToScene(type, x, y, z) {
    enemies.push(buildEnemy(type, x, y, z));
  }

  function respawnEnemy(e) {
    scene.remove(e.mesh);
    const fresh = buildEnemy(e.type, e.spawn.x, e.spawn.y, e.spawn.z);
    Object.assign(e, fresh);
  }

  function buildHealthPacks() {
    const crossMat = new THREE.MeshStandardMaterial({ color: 0x4ade80, emissive: 0x166534, emissiveIntensity: 0.7 });
    const spots = [];
    islands.forEach((isl, i) => { if (i % 6 === 0) spots.push(isl); }); // sparse coverage
    spots.forEach(isl => {
      const group = new THREE.Group();
      const bar1 = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.32, 0.32), crossMat);
      const bar2 = new THREE.Mesh(new THREE.BoxGeometry(0.32, 1.1, 0.32), crossMat);
      group.add(bar1, bar2);
      group.position.set(isl.x, isl.y + 2, isl.z);
      scene.add(group);
      healthPacks.push({ mesh: group, alive: true, deadAt: 0, spawn: { x: isl.x, y: isl.y + 2, z: isl.z } });
    });
  }

  function updateHealthPacks(dt) {
    const now = performance.now() / 1000;
    healthPacks.forEach(hp => {
      if (!hp.alive) {
        if (now - hp.deadAt > 14) {
          hp.alive = true;
          hp.mesh.visible = true;
        }
        return;
      }
      hp.mesh.rotation.y += dt * 1.8;
      hp.mesh.position.y = hp.spawn.y + Math.sin(now * 2 + hp.spawn.x) * 0.3;
      if (player.position.distanceTo(hp.mesh.position) < 1.6 && myHp < currentMaxHp()) {
        myHp = Math.min(currentMaxHp(), myHp + 35);
        hpEl.textContent = '❤ HP: ' + Math.round(myHp) + ' / ' + currentMaxHp();
        hp.alive = false;
        hp.deadAt = now;
        hp.mesh.visible = false;
        msgEl.textContent = 'Picked up a health pack — +35 HP.';
      }
    });
  }

  function updateEnemies(dt) {
    const now = performance.now() / 1000;
    enemies.forEach(e => {
      if (!e.alive) {
        if (now - e.deadAt > 9) respawnEnemy(e);
        return;
      }
      e.mesh.rotation.y += dt * 1.2;
      e.mesh.position.y = e.spawn.y + Math.sin(now * 1.5 + e.spawn.x) * 0.4;

      const distToPlayer = e.mesh.position.distanceTo(player.position);

      if (e.def.chases && distToPlayer < 55 && distToPlayer > 2) {
        const dir = new THREE.Vector3().subVectors(player.position, e.mesh.position);
        dir.y = 0;
        dir.normalize();
        e.mesh.position.addScaledVector(dir, 6.5 * dt);
        if (distToPlayer < 2.4 && now - e.lastShot > 1) {
          e.lastShot = now;
          damagePlayer(8 + Math.floor(Math.random() * 6));
        }
      }

      if (e.type === 'turret' && distToPlayer < 45 && now - e.lastShot > 2.2) {
        e.lastShot = now;
        const mat = new THREE.MeshStandardMaterial({ color: e.def.color, emissive: e.def.color, emissiveIntensity: 1.3 });
        const bolt = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 8), mat);
        bolt.position.copy(e.mesh.position);
        scene.add(bolt);
        enemyBolts.push({ mesh: bolt, dmg: 10 + Math.floor(Math.random() * 8) });
      }
    });
  }

  function activateShield() {
    const now = performance.now() / 1000;
    if (shieldActive || now < shieldReadyAt) return;
    const dur = SHIELD_DURATION + shieldDurationBonus();
    shieldActive = true;
    shieldEndsAt = now + dur;
    shieldReadyAt = now + dur + SHIELD_COOLDOWN;
    shieldMesh.visible = true;
    msgEl.textContent = 'Shield up! Incoming damage is blocked for ' + dur + 's.';
  }

  function updateShield(dt) {
    const now = performance.now() / 1000;
    if (shieldActive) {
      shieldMesh.rotation.y += dt * 1.5;
      const pulse = 1 + Math.sin(now * 8) * 0.04;
      shieldMesh.scale.set(pulse, pulse, pulse);
      const remaining = shieldEndsAt - now;
      if (remaining <= 0) {
        shieldActive = false;
        shieldMesh.visible = false;
        shieldEl.textContent = '🛡 Shield: cooling down…';
      } else {
        shieldEl.textContent = '🛡 Shield: active (' + remaining.toFixed(1) + 's)';
      }
    } else if (now < shieldReadyAt) {
      shieldEl.textContent = '🛡 Shield: cooling down (' + (shieldReadyAt - now).toFixed(1) + 's)';
    } else {
      shieldEl.textContent = '🛡 Shield: ready (Q)';
    }
  }

  function damagePlayer(dmg) {
    if (onIsland) return; // islands are a safe zone — no damage while standing on one
    if (shieldActive) {
      shieldMesh.scale.set(1.25, 1.25, 1.25);
      setTimeout(() => { if (shieldMesh) shieldMesh.scale.set(1,1,1); }, 120);
      return;
    }
    myHp = Math.max(0, myHp - dmg);
    hpEl.textContent = '❤ HP: ' + Math.round(myHp) + ' / ' + currentMaxHp();
    hpEl.style.borderColor = 'rgba(251,113,133,0.9)';
    setTimeout(() => { hpEl.style.borderColor = 'rgba(251,113,133,0.3)'; }, 150);
    if (myHp <= 0) {
      myHp = currentMaxHp();
      player.position.set(0, 8, 0);
      playerVel.set(0, 0, 0);
      msgEl.textContent = 'You went down! Back on your feet at the spawn island.';
      hpEl.textContent = '❤ HP: ' + myHp + ' / ' + currentMaxHp();
    }
  }

  function updateEnemyBolts(dt) {
    for (let i = enemyBolts.length - 1; i >= 0; i--) {
      const b = enemyBolts[i];
      const dir = new THREE.Vector3().subVectors(player.position, b.mesh.position);
      const dist = dir.length();
      if (dist < 1.4) {
        damagePlayer(b.dmg);
        scene.remove(b.mesh);
        enemyBolts.splice(i, 1);
        continue;
      }
      dir.normalize();
      b.mesh.position.addScaledVector(dir, 28 * dt);
    }
  }
  function buildGunViewmodel() {
  const group = new THREE.Group();

  const metal = new THREE.MeshStandardMaterial({
    color: 0x2a2f45,
    metalness: 0.7,
    roughness: 0.35
  });

  const accent = new THREE.MeshStandardMaterial({
    color: 0x7cf7ff,
    emissive: 0x2dd4bf,
    emissiveIntensity: 0.9,
    metalness: 0.4,
    roughness: 0.3
  });

  const dark = new THREE.MeshStandardMaterial({
    color: 0x111525,
    metalness: 0.8,
    roughness: 0.25
  });
function rebuildGunViewmodel() {
  if (gunGroup) {
    camera.remove(gunGroup);
  }

  gunGroup = null;
  gunMuzzle = null;

  buildGunViewmodel();
}
  // =========================
  // 1 — BASIC BULLET GUN
  // =========================
  function buildBulletGun() {
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.16, 0.14, 0.55), metal
    );
    body.position.set(0, 0, -0.1);
    group.add(body);

    const barrel = new THREE.Mesh(
      new THREE.CylinderGeometry(0.045, 0.055, 0.4, 10), metal
    );
    barrel.rotation.x = Math.PI / 2;
    barrel.position.set(0, 0.01, -0.55);
    group.add(barrel);

    const tip = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.045, 0.08, 10), accent
    );
    tip.rotation.x = Math.PI / 2;
    tip.position.set(0, 0.01, -0.76);
    group.add(tip);

    const grip = new THREE.Mesh(
      new THREE.BoxGeometry(0.11, 0.28, 0.12), metal
    );
    grip.position.set(0, -0.18, 0.12);
    grip.rotation.x = 0.25;
    group.add(grip);

    const stripe = new THREE.Mesh(
      new THREE.BoxGeometry(0.17, 0.03, 0.2), accent
    );
    stripe.position.set(0, 0.06, -0.05);
    group.add(stripe);
  }

  // =========================
  // 2 — RAPID FIRE GUN
  // =========================
  function buildRapidGun() {
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.22, 0.18, 0.5), dark
    );
    body.position.z = -0.1;
    group.add(body);

    // Three barrels
    [-0.07, 0, 0.07].forEach(x => {
      const barrel = new THREE.Mesh(
        new THREE.CylinderGeometry(0.035, 0.045, 0.55, 8),
        metal
      );
      barrel.rotation.x = Math.PI / 2;
      barrel.position.set(x, 0, -0.55);
      group.add(barrel);
    });

    const grip = new THREE.Mesh(
      new THREE.BoxGeometry(0.13, 0.3, 0.14), dark
    );
    grip.position.set(0, -0.2, 0.1);
    grip.rotation.x = 0.25;
    group.add(grip);
  }

  // =========================
  // 3 — MISSILE LAUNCHER
  // =========================
  function buildMissileGun() {
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.28, 0.22, 0.6), dark
    );
    body.position.z = -0.05;
    group.add(body);

    // Missile tube
    const tube = new THREE.Mesh(
      new THREE.CylinderGeometry(0.12, 0.12, 0.7, 12),
      metal
    );
    tube.rotation.x = Math.PI / 2;
    tube.position.z = -0.55;
    group.add(tube);

    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.12, 0.025, 8, 16),
      accent
    );
    ring.position.z = -0.9;
    group.add(ring);

    const grip = new THREE.Mesh(
      new THREE.BoxGeometry(0.15, 0.3, 0.15), dark
    );
    grip.position.set(0, -0.2, 0.1);
    grip.rotation.x = 0.25;
    group.add(grip);
  }

  // =========================
  // 4 — BLAST CANNON
  // =========================
  function buildBlastGun() {
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.3, 0.25, 0.55), dark
    );
    body.position.z = -0.05;
    group.add(body);

    const barrel = new THREE.Mesh(
      new THREE.CylinderGeometry(0.16, 0.12, 0.55, 12),
      accent
    );
    barrel.rotation.x = Math.PI / 2;
    barrel.position.z = -0.55;
    group.add(barrel);

    const muzzle = new THREE.Mesh(
      new THREE.CylinderGeometry(0.2, 0.15, 0.12, 12),
      metal
    );
    muzzle.rotation.x = Math.PI / 2;
    muzzle.position.z = -0.86;
    group.add(muzzle);

    const grip = new THREE.Mesh(
      new THREE.BoxGeometry(0.16, 0.32, 0.16), dark
    );
    grip.position.set(0, -0.2, 0.1);
    grip.rotation.x = 0.25;
    group.add(grip);
  }

  // =========================
  // 5 — PLASMA CANNON
  // =========================
  function buildPlasmaGun() {
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.25, 0.22, 0.65), metal
    );
    body.position.z = -0.05;
    group.add(body);

    const barrel = new THREE.Mesh(
      new THREE.CylinderGeometry(0.09, 0.11, 0.75, 12),
      accent
    );
    barrel.rotation.x = Math.PI / 2;
    barrel.position.z = -0.65;
    group.add(barrel);

    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.1, 12, 12),
      accent
    );
    core.position.z = -1.02;
    group.add(core);

    const grip = new THREE.Mesh(
      new THREE.BoxGeometry(0.14, 0.3, 0.15), dark
    );
    grip.position.set(0, -0.2, 0.12);
    grip.rotation.x = 0.25;
    group.add(grip);
  }
  
function buildRapidGun() {
  const body = new THREE.Mesh(
    new THREE.BoxGeometry(0.3, 0.22, 0.6),
    dark
  );
  body.position.z = -0.05;
  group.add(body);

  // Four rapid-fire barrels
  [-0.12, -0.04, 0.04, 0.12].forEach(x => {
    const barrel = new THREE.Mesh(
      new THREE.CylinderGeometry(0.035, 0.045, 0.65, 8),
      accent
    );
    barrel.rotation.x = Math.PI / 2;
    barrel.position.set(x, 0, -0.62);
    group.add(barrel);
  });

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(0.08, 12, 12),
    accent
  );
  core.position.set(0, 0.02, -0.98);
  group.add(core);

  const grip = new THREE.Mesh(
    new THREE.BoxGeometry(0.16, 0.3, 0.15),
    dark
  );
  grip.position.set(0, -0.2, 0.1);
  grip.rotation.x = 0.25;
  group.add(grip);
}

  // =========================
  // 6 — HEAVY CANNON
  // =========================
  function buildHeavyGun() {
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.34, 0.3, 0.7), dark
    );
    body.position.z = -0.02;
    group.add(body);

    const barrel = new THREE.Mesh(
      new THREE.CylinderGeometry(0.18, 0.16, 0.8, 12),
      metal
    );
    barrel.rotation.x = Math.PI / 2;
    barrel.position.z = -0.7;
    group.add(barrel);

    const muzzle = new THREE.Mesh(
      new THREE.CylinderGeometry(0.23, 0.19, 0.14, 12),
      accent
    );
    muzzle.rotation.x = Math.PI / 2;
    muzzle.position.z = -1.12;
    group.add(muzzle);

    const grip = new THREE.Mesh(
      new THREE.BoxGeometry(0.18, 0.35, 0.18), dark
    );
    grip.position.set(0, -0.23, 0.15);
    grip.rotation.x = 0.25;
    group.add(grip);
  }

 if (currentWeapon === 'bullet') {
  buildBulletGun();
}

if (currentWeapon === 'missile') {
  buildMissileGun();
}

if (currentWeapon === 'blast') {
  buildBlastGun();
}

if (currentWeapon === 'plasma') {
  buildPlasmaGun();
}

if (currentWeapon === 'rapid') {
  buildRapidGun();
}

if (currentWeapon === 'heavy') {
  buildHeavyGun();
}
  gunBasePos = new THREE.Vector3(0.32, -0.28, -0.55);
  group.position.copy(gunBasePos);
  group.rotation.y = -0.05;

  camera.add(group);
  gunGroup = group;

  gunMuzzle = new THREE.Object3D();
  gunMuzzle.position.set(0, 0.01, -1.0);
  group.add(gunMuzzle);
}
  function updateGunViewmodel(dt) {
    if (!gunGroup) return;
    const now = performance.now() / 1000;
    const moving = (keys['w']||keys['a']||keys['s']||keys['d']||keys['arrowup']||keys['arrowdown']||keys['arrowleft']||keys['arrowright']) && onGround;
    const bobX = moving ? Math.sin(now * 9) * 0.012 : Math.sin(now * 1.6) * 0.003;
    const bobY = moving ? Math.abs(Math.sin(now * 9)) * 0.012 : Math.sin(now * 1.4) * 0.0025;
    if (gunKick > 0) {
      gunKick = Math.max(0, gunKick - dt * 6);
    }
    gunGroup.position.set(
      gunBasePos.x + bobX,
      gunBasePos.y + bobY,
      gunBasePos.z + gunKick * 0.18
    );
    gunGroup.visible = started && !scoping;
  }

  function updateScope(dt) {
    const targetFov = (started && scoping) ? SCOPE_FOV : BASE_FOV;
    camera.fov += (targetFov - camera.fov) * Math.min(1, dt * 12);
    camera.updateProjectionMatrix();
  }

  function toggleScope() {
    scoping = !scoping;
    scopeEl.style.display = scoping ? 'block' : 'none';
  }

  function buildBosses() {
    for (let i = 0; i < 3; i++) {
      const type = bossTypeOf(i);
      const group = new THREE.Group();
      const bodyMat = new THREE.MeshStandardMaterial({ color: type.color, emissive: type.emissive, emissiveIntensity: 0.35, roughness: 0.5 });
      const body = new THREE.Mesh(new THREE.SphereGeometry(3, 20, 20), bodyMat);
      group.add(body);
      for (let j = 0; j < 6; j++) {
        const spike = new THREE.Mesh(new THREE.ConeGeometry(0.5, 2, 6), bodyMat);
        const a = (j / 6) * Math.PI * 2;
        spike.position.set(Math.cos(a) * 2.6, Math.sin(a * 2) * 0.6, Math.sin(a) * 2.6);
        spike.lookAt(spike.position.clone().multiplyScalar(2));
        spike.rotateX(Math.PI / 2);
        group.add(spike);
      }
      const eyeMat = new THREE.MeshStandardMaterial({ color: 0xffe066, emissive: 0xffe066, emissiveIntensity: 1 });
      const eye = new THREE.Mesh(new THREE.SphereGeometry(0.5, 10, 10), eyeMat);
      eye.position.set(0, 0.5, 2.6);
      group.add(eye);

      const anchor = bossAnchors[i];
      group.position.set(anchor.x, 22, anchor.z);
      scene.add(group);
      bossMeshes[i] = group;
    }

    const ringGeo = new THREE.TorusGeometry(4.2, 0.12, 8, 32);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xffe066, transparent: true, opacity: 0.9 });
    lockRing = new THREE.Mesh(ringGeo, ringMat);
    lockRing.rotation.x = Math.PI / 2;
    lockRing.visible = false;
    scene.add(lockRing);

    updateBossHud();
  }

  function updateBossMovement(dt) {
    const now = Date.now() / 1000; // real time so all clients roughly agree on boss position
    for (let i = 0; i < 3; i++) {
      const mesh = bossMeshes[i];
      if (!mesh) continue;
      if (!bossAlive[i]) { mesh.visible = false; continue; }
      mesh.visible = true;
      const anchor = bossAnchors[i];
      const orbitSpeed = 0.09 + i * 0.02;
      const orbitRadius = 46 + Math.sin(now * 0.15 + i) * 14;
      const heightBob = 22 + Math.sin(now * 0.3 + i * 2) * 8;
      const angle = now * orbitSpeed + i * (Math.PI * 2 / 3);
      mesh.position.set(
        anchor.x + Math.cos(angle) * orbitRadius,
        heightBob,
        anchor.z + Math.sin(angle) * orbitRadius
      );
      mesh.rotation.y += dt * (0.4 + i * 0.1);
      mesh.lookAt(player.position.x, mesh.position.y, player.position.z);

      // Boss occasionally fires at the player if they're in range.
      const distToPlayer = mesh.position.distanceTo(player.position);
      if (distToPlayer < 130 && now - bossLastShot[i] > (2.6 - i * 0.2)) {
        bossLastShot[i] = now;
        fireBossBolt(i, mesh);
      }
    }
  }

  function fireBossBolt(i, mesh) {
    const type = bossTypeOf(i);
    const mat = new THREE.MeshStandardMaterial({ color: type.boltColor, emissive: type.boltColor, emissiveIntensity: 1.5 });
    const bolt = new THREE.Mesh(new THREE.SphereGeometry(0.45, 10, 10), mat);
    bolt.position.copy(mesh.position);
    scene.add(bolt);
    const dir = new THREE.Vector3().subVectors(player.position, mesh.position).normalize();
    bossBolts.push({ mesh: bolt, dir, dmg: 14 + Math.floor(Math.random() * 10) });
  }

  function updateBossBolts(dt) {
    for (let i = bossBolts.length - 1; i >= 0; i--) {
      const b = bossBolts[i];
      b.mesh.position.addScaledVector(b.dir, 34 * dt);
      if (b.mesh.position.distanceTo(player.position) < 2) {
        damagePlayer(b.dmg);
        scene.remove(b.mesh);
        bossBolts.splice(i, 1);
        continue;
      }
      if (b.mesh.position.length() > 900) {
        scene.remove(b.mesh);
        bossBolts.splice(i, 1);
      }
    }
  }

  function updateBossHud() {
    for (let i = 0; i < 3; i++) {
      const type = bossTypeOf(i);
      const pct = bossAlive[i] ? Math.max(0, bossHp[i] / bossMaxHp[i]) * 100 : 0;
      bossBarEls[i].style.width = pct + '%';
      bossNameEls[i].textContent = bossAlive[i] ? (type.name + ' · T' + bossTier[i]) : (type.name + ' — reforming…');
    }
    if (lockedTarget && lockedTarget.kind === 'boss' && !bossAlive[lockedTarget.index]) {
      lockedTarget = null;
      if (lockRing) lockRing.visible = false;
    }
  }

  function tryLockTarget(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1
    );
    raycaster.setFromCamera(mouse, camera);

    const candidates = [];
    for (let i = 0; i < 3; i++) {
      if (bossMeshes[i] && bossAlive[i]) candidates.push({ mesh: bossMeshes[i], target: { kind: 'boss', index: i } });
    }
    enemies.forEach(e => { if (e.alive) candidates.push({ mesh: e.mesh, target: { kind: 'enemy', ref: e } }); });
    if (pvpEnabled) {
      Object.keys(ghosts).forEach(id => {
        const g = ghosts[id];
        if (g.pvp) candidates.push({ mesh: g.mesh, target: { kind: 'player', id: id } });
      });
    }

    let closest = null, closestDist = Infinity;
    candidates.forEach(c => {
      const hits = raycaster.intersectObject(c.mesh, true);
      if (hits.length > 0 && hits[0].distance < closestDist) {
        closestDist = hits[0].distance;
        closest = c.target;
      }
    });

    if (closest) {
      const wasLocked = lockedTarget && sameTarget(lockedTarget, closest);
      lockedTarget = closest;
      lockRing.visible = true;
      const label = closest.kind === 'boss' ? bossTypeOf(closest.index).name :
        (closest.kind === 'player' ? (ghosts[closest.id] && ghosts[closest.id].name || 'a drifter') : closest.ref.def.label);
      msgEl.textContent = 'Target locked: ' + label + '. Click again or press E to fire.';
      if (wasLocked) fireBolt();
    } else {
      lockedTarget = null;
      lockRing.visible = false;
    }
  }

  function sameTarget(a, b) {
    if (a.kind !== b.kind) return false;
    if (a.kind === 'boss') return a.index === b.index;
    if (a.kind === 'player') return a.id === b.id;
    return a.ref === b.ref;
  }

  function targetMesh(t) {
    if (!t) return null;
    if (t.kind === 'boss') return bossAlive[t.index] ? bossMeshes[t.index] : null;
    if (t.kind === 'player') return (ghosts[t.id] && ghosts[t.id].pvp) ? ghosts[t.id].mesh : null;
    return t.ref.alive ? t.ref.mesh : null;
  }

  function makeMissile(color, isBlast) {
    const s = isBlast ? 1.5 : 1;
    const group = new THREE.Group();
    const bodyMat = new THREE.MeshStandardMaterial({ color: isBlast ? 0x3a2018 : 0xd8d8e0, metalness: 0.6, roughness: 0.3 });
    const noseMat = new THREE.MeshStandardMaterial({ color: color, emissive: color, emissiveIntensity: 0.9 });
    const finMat = new THREE.MeshStandardMaterial({ color: isBlast ? 0x7a3320 : 0x555566, metalness: 0.5, roughness: 0.4 });
    const flameMat = new THREE.MeshStandardMaterial({ color: 0xffaa33, emissive: 0xff6600, emissiveIntensity: 1.6, transparent: true, opacity: 0.9 });

    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.14 * s, 0.14 * s, 0.9 * s, 10), bodyMat);
    body.rotation.x = Math.PI / 2;
    group.add(body);

    const nose = new THREE.Mesh(new THREE.ConeGeometry(0.14 * s, 0.4 * s, 10), noseMat);
    nose.rotation.x = Math.PI / 2;
    nose.position.set(0, 0, -0.65 * s);
    group.add(nose);

    for (let i = 0; i < 4; i++) {
      const fin = new THREE.Mesh(new THREE.BoxGeometry(0.32 * s, 0.03 * s, 0.22 * s), finMat);
      const a = (i / 4) * Math.PI * 2;
      fin.position.set(Math.cos(a) * 0.12 * s, Math.sin(a) * 0.12 * s, 0.35 * s);
      fin.rotation.z = a;
      group.add(fin);
    }

    const flame = new THREE.Mesh(new THREE.ConeGeometry(0.13 * s, 0.5 * s, 8), flameMat);
    flame.rotation.x = -Math.PI / 2;
    flame.position.set(0, 0, 0.6 * s);
    group.add(flame);
    group.userData.flame = flame;

    return group;
  }

  function spawnExplosion(pos, radius) {
    const mat = new THREE.MeshStandardMaterial({ color: 0xffaa33, emissive: 0xff5522, emissiveIntensity: 1.8, transparent: true, opacity: 0.85 });
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.3, 14, 14), mat);
    mesh.position.copy(pos);
    scene.add(mesh);
    explosions.push({ mesh, born: performance.now() / 1000, maxR: radius });
  }

  function updateExplosions(dt) {
    const now = performance.now() / 1000;
    for (let i = explosions.length - 1; i >= 0; i--) {
      const ex = explosions[i];
      const age = now - ex.born;
      const dur = 0.4;
      if (age > dur) {
        scene.remove(ex.mesh);
        explosions.splice(i, 1);
        continue;
      }
      const t = age / dur;
      const scale = 0.3 + ex.maxR * t;
      ex.mesh.scale.set(scale / 0.3, scale / 0.3, scale / 0.3);
      ex.mesh.material.opacity = 0.85 * (1 - t);
    }
  }

  function explodeSplash(pos, dmg, excludeBossIndex, excludeEnemy) {
    spawnExplosion(pos, BLAST_RADIUS);
    for (let i = 0; i < 3; i++) {
      if (i === excludeBossIndex) continue;
      if (!bossAlive[i] || !bossMeshes[i]) continue;
      if (pos.distanceTo(bossMeshes[i].position) < BLAST_RADIUS) {
        bossHp[i] = Math.max(0, bossHp[i] - dmg);
        pendingBossDamage[i] = (pendingBossDamage[i] || 0) + dmg;
        flashMesh(bossMeshes[i]);
        updateBossHud();
        if (bossHp[i] <= 0) {
          bossAlive[i] = false;
          if (lockedTarget && lockedTarget.kind === 'boss' && lockedTarget.index === i) { lockedTarget = null; lockRing.visible = false; }
          updateBossHud();
          msgEl.textContent = 'The ' + bossTypeOf(i).name + ' shatters! It will reform shortly, stronger than before.';
        }
      }
    }
    enemies.forEach(e => {
      if (!e.alive || e === excludeEnemy) return;
      if (pos.distanceTo(e.mesh.position) < BLAST_RADIUS) {
        e.hp = Math.max(0, e.hp - dmg);
        flashMesh(e.mesh);
        if (e.hp <= 0) {
          e.alive = false;
          e.deadAt = performance.now() / 1000;
          e.mesh.visible = false;
          if (lockedTarget && lockedTarget.kind === 'enemy' && lockedTarget.ref === e) {
            lockedTarget = null; lockRing.visible = false;
          }
        }
      }
    });
  }

  function orientMissile(mesh, dir) {
    const lookTarget = mesh.position.clone().add(dir);
    mesh.up.set(0, 1, 0);
    mesh.lookAt(lookTarget);
  }

  function spawnTrailPuff(pos) {
    const mat = new THREE.MeshStandardMaterial({ color: 0xcfd6e6, transparent: true, opacity: 0.55 });
    const puff = new THREE.Mesh(new THREE.SphereGeometry(0.16, 6, 6), mat);
    puff.position.copy(pos);
    scene.add(puff);
    const born = performance.now() / 1000;
    trailPuffs.push({ mesh: puff, born });
  }

  function updateTrailPuffs(dt) {
    const now = performance.now() / 1000;
    for (let i = trailPuffs.length - 1; i >= 0; i--) {
      const p = trailPuffs[i];
      const age = now - p.born;
      if (age > 0.6) {
        scene.remove(p.mesh);
        trailPuffs.splice(i, 1);
        continue;
      }
      const scale = 1 + age * 2.5;
      p.mesh.scale.set(scale, scale, scale);
      p.mesh.material.opacity = 0.55 * (1 - age / 0.6);
    }
  }

  function autoAcquireTarget() {
    const camDir = new THREE.Vector3();
    camera.getWorldDirection(camDir);
    const camPos = new THREE.Vector3();
    camera.getWorldPosition(camPos);

    const candidates = [];
    for (let i = 0; i < 3; i++) {
      if (bossMeshes[i] && bossAlive[i]) candidates.push({ kind: 'boss', index: i });
    }
    enemies.forEach(e => { if (e.alive) candidates.push({ kind: 'enemy', ref: e }); });
    if (pvpEnabled) {
      Object.keys(ghosts).forEach(id => {
        if (ghosts[id].pvp) candidates.push({ kind: 'player', id: id });
      });
    }

    let best = null, bestScore = -Infinity;
    candidates.forEach(c => {
      const mesh = targetMesh(c);
      if (!mesh) return;
      const toTarget = new THREE.Vector3().subVectors(mesh.position, camPos);
      const dist = toTarget.length();
      toTarget.normalize();
      const alignment = toTarget.dot(camDir); // 1 = dead center, <0 = behind
      if (alignment < 0.3) return; // roughly outside a ~70° cone in front of the camera
      const score = alignment - dist * 0.002; // prefer well-aimed, then closer
      if (score > bestScore) {
        bestScore = score;
        best = c;
      }
    });
    return best;
  }

  function fireBolt() {
    if (!started) return;
    const now = performance.now() / 1000;
    const mult = rapidFire ? RAPID_MULT : 1;

    if (currentWeapon === 'bullet') {
      if (now - lastAttack < BULLET_COOLDOWN * mult) return;
      fireBulletShot(now);
      return;
    }

    const isBlast = currentWeapon === 'blast';
    const cooldown = isBlast ? BLAST_COOLDOWN : ATTACK_COOLDOWN;
    if (now - lastAttack < cooldown * mult) return;

    const target = lockedTarget || autoAcquireTarget();

    if (target) {
      const mesh = targetMesh(target);
      if (!mesh) {
        if (lockedTarget === target) { lockedTarget = null; lockRing.visible = false; }
      } else {
        lastAttack = now;
        recoil();
        const boltColor = isBlast ? 0xff8844 : (target.kind === 'boss' ? bossTypeOf(target.index).boltColor : 0x7cf7ff);
        const bolt = makeMissile(boltColor, isBlast);
        bolt.position.copy(player.position).add(new THREE.Vector3(0, 0.6, 0));
        scene.add(bolt);
        const dmg = Math.round((isBlast ? (26 + Math.floor(Math.random() * 14)) :
          (target.kind === 'boss' ? (15 + Math.floor(Math.random() * 16)) : (12 + Math.floor(Math.random() * 10)))) * dmgMultiplier());
        activeBolts.push({ mesh: bolt, dmg, target: target, lastPuff: now, blast: isBlast });
        return;
      }
    }

    // Nothing to auto-aim at — fires straight from the gun muzzle along the camera's look
    // direction instead, with no maximum range.
    lastAttack = now;
    recoil();
    const dir = new THREE.Vector3();
    camera.getWorldDirection(dir);
    const muzzlePos = new THREE.Vector3();
    gunMuzzle.getWorldPosition(muzzlePos);
    const bolt = makeMissile(isBlast ? 0xff8844 : 0x7cf7ff, isBlast);
    bolt.position.copy(muzzlePos);
    orientMissile(bolt, dir);
    scene.add(bolt);
    const dmg = Math.round((isBlast ? (26 + Math.floor(Math.random() * 14)) : (10 + Math.floor(Math.random() * 9))) * dmgMultiplier());
    freeBolts.push({ mesh: bolt, dir: dir.clone(), dmg, born: now, lastPuff: now, blast: isBlast });
  }

  function fireBulletShot(now) {
    lastAttack = now;
    recoil();
    const dir = new THREE.Vector3();
    camera.getWorldDirection(dir);
    const muzzlePos = new THREE.Vector3();
    gunMuzzle.getWorldPosition(muzzlePos);
    const mat = new THREE.MeshStandardMaterial({ color: 0xfff2b0, emissive: 0xffcc55, emissiveIntensity: 1.6 });
    const bullet = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.3, 6), mat);
    bullet.rotation.x = Math.PI / 2;
    bullet.position.copy(muzzlePos);
    orientMissile(bullet, dir);
    scene.add(bullet);
    const dmg = Math.round((5 + Math.floor(Math.random() * 5)) * dmgMultiplier());
    bullets.push({ mesh: bullet, dir: dir.clone(), dmg, born: now });
  }

  function recoil() {
    gunKick = 1;
  }

  const WEAPON_ICONS = { bullet: '🔫', missile: '🎯', blast: '💥' };
  const WEAPON_KEYS = { bullet: '1', missile: '2', blast: '3' };
  function weaponLabelText() {
    return WEAPON_ICONS[currentWeapon] + ' Weapon: ' + WEAPON_LABELS[currentWeapon] + ' (' + WEAPON_KEYS[currentWeapon] + ')' + (rapidFire ? ' ⚡ RAPID' : '');
  }
  const WEAPON_HAND_COLORS = { bullet: 0xfff2b0, missile: 0x7cf7ff, blast: 0xff8844 };
  function switchWeapon(w) {
  if (!unlockedWeapons[w]) {
    const price = WEAPON_PRICES[w];
    msgEl.textContent =
      '🔒 ' + WEAPON_LABELS[w] +
      ' costs ' + price + ' Orbs. Open the shop with B!';
    return;
  }

  currentWeapon = w;

  // Remove the old gun
  if (gunGroup) {
    camera.remove(gunGroup);
    gunGroup = null;
    gunMuzzle = null;
  }

  // Build the new gun
  buildGunViewmodel();

  weaponEl.textContent = weaponLabelText();
  msgEl.textContent = 'Switched to ' + WEAPON_LABELS[w] + '.';

  if (humanVisual && humanVisual.userData.handWeaponAccent) {
    const c = WEAPON_HAND_COLORS[w];
    humanVisual.userData.handWeaponAccent.color.setHex(c);
    humanVisual.userData.handWeaponAccent.emissive.setHex(c);
  }
}
  function toggleRapidFire() {
    rapidFire = !rapidFire;
    weaponEl.textContent = weaponLabelText();
    msgEl.textContent = rapidFire ? 'Rapid fire engaged — hold E to unload.' : 'Rapid fire disengaged.';
  }

  function togglePvp() {
    pvpEnabled = !pvpEnabled;
    pvpEl.textContent = '⚔ PvP: ' + (pvpEnabled ? 'ON' : 'OFF') + ' (P)';
    pvpEl.style.color = pvpEnabled ? '#fb7185' : '#94a3b8';
    pvpEl.style.borderColor = pvpEnabled ? 'rgba(251,113,133,0.5)' : 'rgba(148,163,184,0.3)';
    msgEl.textContent = pvpEnabled ? 'PvP enabled — you can now hit (and be hit by) other players who also have it on.' : 'PvP disabled.';
  }

  function tryDamageNearestBoss(pos, radius, dmg) {
    for (let i = 0; i < 3; i++) {
      if (!bossAlive[i] || !bossMeshes[i]) continue;
      if (pos.distanceTo(bossMeshes[i].position) < radius) {
        bossHp[i] = Math.max(0, bossHp[i] - dmg);
        pendingBossDamage[i] = (pendingBossDamage[i] || 0) + dmg;
        flashMesh(bossMeshes[i]);
        updateBossHud();
        if (bossHp[i] <= 0) {
          bossAlive[i] = false;
          if (lockedTarget && lockedTarget.kind === 'boss' && lockedTarget.index === i) { lockedTarget = null; lockRing.visible = false; }
          updateBossHud();
          msgEl.textContent = 'The ' + bossTypeOf(i).name + ' shatters! It will reform shortly, stronger than before.';
        }
        return i;
      }
    }
    return -1;
  }

  function tryDamageNearbyPlayer(pos, radius, dmg) {
    if (!pvpEnabled) return null;
    for (const id of Object.keys(ghosts)) {
      const g = ghosts[id];
      if (!g.pvp) continue;
      if (pos.distanceTo(g.mesh.position) < radius) {
        pendingPvpDamage[id] = (pendingPvpDamage[id] || 0) + dmg;
        flashMesh(g.mesh);
        msgEl.textContent = 'Hit ' + (g.name || 'a drifter') + ' for ' + dmg + '!';
        return id;
      }
    }
    return null;
  }

  function updateBullets(dt) {
    const now = performance.now() / 1000;
    for (let i = bullets.length - 1; i >= 0; i--) {
      const b = bullets[i];
      b.mesh.position.addScaledVector(b.dir, BULLET_SPEED * dt);

      let hit = tryDamageNearestBoss(b.mesh.position, BULLET_BOSS_RADIUS, b.dmg) >= 0;
      if (!hit) {
        for (const e of enemies) {
          if (!e.alive) continue;
          if (b.mesh.position.distanceTo(e.mesh.position) < BULLET_ENEMY_RADIUS) {
            e.hp = Math.max(0, e.hp - b.dmg);
            flashMesh(e.mesh);
            if (e.hp <= 0) {
              e.alive = false;
              e.deadAt = now;
              e.mesh.visible = false;
              if (lockedTarget && lockedTarget.kind === 'enemy' && lockedTarget.ref === e) {
                lockedTarget = null; lockRing.visible = false;
              }
            }
            hit = true;
            break;
          }
        }
      }
      if (!hit && pvpEnabled) {
        hit = tryDamageNearbyPlayer(b.mesh.position, BULLET_ENEMY_RADIUS, b.dmg) !== null;
      }

      if (hit || now - b.born > BULLET_LIFETIME) {
        scene.remove(b.mesh);
        bullets.splice(i, 1);
      }
    }
  }

  function updateFreeBolts(dt) {
    const now = performance.now() / 1000;
    for (let i = freeBolts.length - 1; i >= 0; i--) {
      const b = freeBolts[i];
      b.mesh.position.addScaledVector(b.dir, FREE_BOLT_SPEED * dt);

      if (now - b.lastPuff > 0.04) {
        spawnTrailPuff(b.mesh.position.clone().addScaledVector(b.dir, 0.4));
        b.lastPuff = now;
      }

      let hit = false;
      let impactPos = null;
      const nearestBossCheck = (radius) => {
        for (let bi = 0; bi < 3; bi++) {
          if (bossAlive[bi] && bossMeshes[bi] && b.mesh.position.distanceTo(bossMeshes[bi].position) < radius) return bi;
        }
        return -1;
      };
      const bIdx = nearestBossCheck(FREE_BOLT_BOSS_RADIUS);
      if (bIdx >= 0) {
        impactPos = b.mesh.position.clone();
        if (!b.blast) {
          bossHp[bIdx] = Math.max(0, bossHp[bIdx] - b.dmg);
          pendingBossDamage[bIdx] = (pendingBossDamage[bIdx] || 0) + b.dmg;
          flashMesh(bossMeshes[bIdx]);
          updateBossHud();
          if (bossHp[bIdx] <= 0) {
            bossAlive[bIdx] = false;
            if (lockedTarget && lockedTarget.kind === 'boss' && lockedTarget.index === bIdx) { lockedTarget = null; lockRing.visible = false; }
            updateBossHud();
            msgEl.textContent = 'The ' + bossTypeOf(bIdx).name + ' shatters! It will reform shortly, stronger than before.';
          }
        } else {
          explodeSplash(impactPos, b.dmg, bIdx, null);
        }
        hit = true;
      }
      if (!hit) {
        for (const e of enemies) {
          if (!e.alive) continue;
          if (b.mesh.position.distanceTo(e.mesh.position) < FREE_BOLT_ENEMY_RADIUS) {
            impactPos = b.mesh.position.clone();
            if (!b.blast) {
              e.hp = Math.max(0, e.hp - b.dmg);
              flashMesh(e.mesh);
              if (e.hp <= 0) {
                e.alive = false;
                e.deadAt = now;
                e.mesh.visible = false;
                if (lockedTarget && lockedTarget.kind === 'enemy' && lockedTarget.ref === e) {
                  lockedTarget = null; lockRing.visible = false;
                }
              }
            } else {
              e.hp = Math.max(0, e.hp - b.dmg);
              flashMesh(e.mesh);
              if (e.hp <= 0) {
                e.alive = false;
                e.deadAt = now;
                e.mesh.visible = false;
                if (lockedTarget && lockedTarget.kind === 'enemy' && lockedTarget.ref === e) {
                  lockedTarget = null; lockRing.visible = false;
                }
              }
              explodeSplash(impactPos, b.dmg, false, e);
            }
            hitEnemyRef = e;
            hit = true;
            break;
          }
        }
      }
      if (!hit && pvpEnabled) {
        const hitId = tryDamageNearbyPlayer(b.mesh.position, FREE_BOLT_ENEMY_RADIUS, b.dmg);
        if (hitId !== null) {
          if (b.blast) explodeSplash(b.mesh.position.clone(), b.dmg, false, null);
          hit = true;
        }
      }

      if (hit || now - b.born > FREE_BOLT_LIFETIME) {
        scene.remove(b.mesh);
        freeBolts.splice(i, 1);
      }
    }
  }


  function updateBolts(dt) {
    const now = performance.now() / 1000;
    for (let i = activeBolts.length - 1; i >= 0; i--) {
      const b = activeBolts[i];
      const mesh = targetMesh(b.target);
      if (!mesh) { scene.remove(b.mesh); activeBolts.splice(i, 1); continue; }
      const dir = new THREE.Vector3().subVectors(mesh.position, b.mesh.position);
      const dist = dir.length();
      dir.normalize();
      orientMissile(b.mesh, dir);
      if (now - b.lastPuff > 0.04) {
        spawnTrailPuff(b.mesh.position.clone());
        b.lastPuff = now;
      }
      if (dist < 1.6) {
        const impactPos = b.mesh.position.clone();
        if (b.target.kind === 'boss') {
          const bi = b.target.index;
          bossHp[bi] = Math.max(0, bossHp[bi] - b.dmg);
          pendingBossDamage[bi] = (pendingBossDamage[bi] || 0) + b.dmg;
          flashMesh(bossMeshes[bi]);
          updateBossHud();
          if (bossHp[bi] <= 0) {
            bossAlive[bi] = false;
            if (lockedTarget && lockedTarget.kind === 'boss' && lockedTarget.index === bi) { lockedTarget = null; lockRing.visible = false; }
            updateBossHud();
            msgEl.textContent = 'The ' + bossTypeOf(bi).name + ' shatters! It will reform shortly, stronger than before.';
          }
          if (b.blast) explodeSplash(impactPos, b.dmg, bi, null);
        } else if (b.target.kind === 'player') {
          const id = b.target.id;
          if (ghosts[id] && ghosts[id].pvp) {
            pendingPvpDamage[id] = (pendingPvpDamage[id] || 0) + b.dmg;
            flashMesh(ghosts[id].mesh);
            msgEl.textContent = 'Hit ' + (ghosts[id].name || 'a drifter') + ' for ' + b.dmg + '!';
          }
          if (b.blast) explodeSplash(impactPos, b.dmg, false, null);
        } else {
          const e = b.target.ref;
          e.hp = Math.max(0, e.hp - b.dmg);
          flashMesh(e.mesh);
          if (e.hp <= 0) {
            e.alive = false;
            e.deadAt = performance.now() / 1000;
            e.mesh.visible = false;
            if (lockedTarget && lockedTarget.kind === 'enemy' && lockedTarget.ref === e) {
              lockedTarget = null; lockRing.visible = false;
            }
          }
          if (b.blast) explodeSplash(impactPos, b.dmg, false, e);
        }
        scene.remove(b.mesh);
        activeBolts.splice(i, 1);
        continue;
      }
      b.mesh.position.addScaledVector(dir, 45 * dt);
    }
  }

  function flashMesh(mesh) {
    if (!mesh) return;
    mesh.scale.set(1.15, 1.15, 1.15);
    setTimeout(() => { if (mesh) mesh.scale.set(1,1,1); }, 120);
  }

  function makeGhost(pl) {
    const geo = typeof THREE.CapsuleGeometry === 'function' ? new THREE.CapsuleGeometry(0.5, 1, 4, 8) : new THREE.CylinderGeometry(0.5, 0.5, 2, 8);
    const mat = new THREE.MeshStandardMaterial({ color: pl.color || '#a78bfa', transparent: true, opacity: 0.85 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(pl.x, pl.y, pl.z);
    scene.add(mesh);
    return { mesh, target: { x: pl.x, y: pl.y, z: pl.z, yaw: pl.yaw || 0 } };
  }

  function syncGhosts(list) {
    const seen = {};
    list.forEach(pl => {
      seen[pl.id] = true;
      if (!ghosts[pl.id]) {
        ghosts[pl.id] = makeGhost(pl);
      }
      ghosts[pl.id].target = { x: pl.x, y: pl.y, z: pl.z, yaw: pl.yaw || 0 };
      ghosts[pl.id].name = pl.name;
      ghosts[pl.id].color = pl.color;
      ghosts[pl.id].pvp = !!pl.pvp;
      ghosts[pl.id].id = pl.id;
    });
    Object.keys(ghosts).forEach(id => {
      if (!seen[id]) {
        scene.remove(ghosts[id].mesh);
        delete ghosts[id];
      }
    });
    rosterEl.textContent = INIT.isSolo ? 'Solo flight' : ('Players online: ' + (list.length + 1));
  }

  function updateGhosts(dt) {
    Object.values(ghosts).forEach(g => {
      g.mesh.position.lerp(new THREE.Vector3(g.target.x, g.target.y, g.target.z), Math.min(1, dt * 3));
      g.mesh.rotation.y += (g.target.yaw - g.mesh.rotation.y) * Math.min(1, dt * 3);
    });
  }

  function updatePlayer(dt) {
    onIsland = false;
    islands.forEach(isl => {
      const dx = player.position.x - isl.x, dz = player.position.z - isl.z;
      const dist = Math.sqrt(dx * dx + dz * dz);
      if (dist < isl.r && Math.abs(player.position.y - (isl.y + 0.9)) < 4) onIsland = true;
    });

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
      if (move.lengthSq() > 0) move.normalize().multiplyScalar(MOVE_SPEED * FLY_SPEED_MULT * speedMultiplier());
      if (keys[' ']) move.y += MOVE_SPEED * 1.6;
      if (keys['shift']) move.y -= MOVE_SPEED * 1.6;

      player.position.addScaledVector(move, dt);

// Keep the player completely weightless while flying
playerVel.x = 0;
playerVel.y = 0;
playerVel.z = 0;
onGround = false;

      if (move.lengthSq() > 0.001) {
        const targetAngle = Math.atan2(move.x, move.z);
        player.rotation.y += (targetAngle - player.rotation.y) * Math.min(1, dt * 10);
      }
      if (player.position.y < -20) player.position.set(0, 8, 0);
      return;
    }

    if (keys['w'] || keys['arrowup']) move.add(flatForward);
    if (keys['s'] || keys['arrowdown']) move.sub(flatForward);
    if (keys['d'] || keys['arrowright']) move.add(flatRight);
    if (keys['a'] || keys['arrowleft']) move.sub(flatRight);
    if (move.lengthSq() > 0) {
      move.normalize().multiplyScalar(MOVE_SPEED * speedMultiplier());
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
      if (player.position.distanceTo(o.position) < 3.5) {
        scene.remove(o);
        orbs.splice(i, 1);
        collected++;
        currency++;
        saveShopData();
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
            msgEl.textContent = 'New best time: ' + elapsed.toFixed(2) + 's!';
          } else {
            msgEl.textContent = 'Finished in ' + elapsed.toFixed(2) + 's. Best stays ' + bestTime.toFixed(2) + 's.';
          }
        } else {
          msgEl.textContent = 'Checkpoint ' + raceCheckpoint + ' of ' + (raceGates.length - 1) + '!';
        }
      }
    }
  }

  function updateHudStatic() {
    hpEl.textContent = '❤ HP: ' + Math.round(myHp) + ' / ' + currentMaxHp();
  }

  function heartbeat() {
    try {
      const payload = {
        player: {
          x: player.position.x, y: player.position.y, z: player.position.z,
          yaw: player.rotation.y, hp: myHp, pvp: pvpEnabled
        },
        boss_damage: pendingBossDamage,
        pvp_damage: pendingPvpDamage
      };
      pendingBossDamage = {};
      pendingPvpDamage = {};
      const doc = window.parent.document;
      const inp = doc.querySelector('textarea[aria-label="od_sync_data"]');
      if (inp) {
        const setter = Object.getOwnPropertyDescriptor(window.parent.HTMLTextAreaElement.prototype, 'value').set;
        setter.call(inp, JSON.stringify(payload));
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        const buttons = Array.from(doc.querySelectorAll('button'));
        const btn = buttons.find(b => b.textContent.trim() === '⛭');
        if (btn) btn.click();
      }
    } catch (e) {}
  }

  function animate() {
    requestAnimationFrame(animate);
    onResize();
    if (!started) { renderer.render(scene, camera); return; }
    const dt = Math.min(clock.getDelta(), 0.05);
    updatePlayer(dt);
    safeZoneEl.style.display = onIsland ? 'block' : 'none';
    updateMinimap();
    updateCamera();
    updateGhosts(dt);
    updateBolts(dt);
    updateEnemies(dt);
    updateEnemyBolts(dt);
    updateBossMovement(dt);
    updateBossBolts(dt);
    updateFreeBolts(dt);
    updateBullets(dt);
    updateExplosions(dt);
    updateTrailPuffs(dt);
    updateHealthPacks(dt);
    updateShield(dt);
    updateGunViewmodel(dt);
    updateScope(dt);
    if (rapidFire && keys['e'] && started) fireBolt();
    if (lockRing && lockedTarget) {
      const tm = targetMesh(lockedTarget);
      if (tm) {
        lockRing.position.set(tm.position.x, tm.position.y, tm.position.z);
        lockRing.rotation.z += dt * 1.5;
        const pulse = 1 + Math.sin(performance.now() * 0.006) * 0.08;
        lockRing.scale.set(pulse, pulse, pulse);
      } else {
        lockRing.visible = false;
      }
    }
    checkOrbs();
    checkRace(dt);
    renderer.render(scene, camera);
  }

  startBtn.addEventListener('click', () => {
    startScreen.style.display = 'none';
    started = true;
    canvas.focus();
  });

  shopBtn.addEventListener('click', () => toggleShop());
  shopCloseBtn.addEventListener('click', () => toggleShop());

  init();
})();
</script>
"""

GAME_HTML = GAME_HTML.replace("__INIT_DATA__", INIT_DATA)

components.html(GAME_HTML, height=640, scrolling=False)

if not is_solo:
    st.markdown("#### Room chat")
    chat_box = st.container(height=220)
    with chat_box:
        if not chat_log:
            st.caption("No messages yet — say hi to your fellow drifters.")
        for msg in chat_log:
            st.markdown(
                f'<div style="margin-bottom:6px;"><span style="color:{msg["color"]}; font-weight:600;">{msg["name"]}:</span> '
                f'<span style="color:#e8e6ff;">{msg["text"]}</span></div>',
                unsafe_allow_html=True
            )

    chat_input = st.chat_input("Message the room…")
    if chat_input:
        chat = load_json(room_chat_path(room), [])
        chat.append({"name": st.session_state.od_name, "color": st.session_state.od_color,
                    "text": chat_input[:200], "ts": time.time()})
        save_json(room_chat_path(room), chat[-60:])
        st.rerun()

st.markdown("""
<div style="max-width:900px; margin:1rem auto 0 auto; color:#a9a4d0; font-family:'Outfit',sans-serif;
    font-size:0.85rem; text-align:center;">
    Position, boss damage, and HP sync with the room roughly every 1.5 seconds. Best race time is saved locally per browser.
</div>
""", unsafe_allow_html=True)
