// 首頁右邊的像素擂台：一位漫威英雄對一位 DC 英雄，打到 K.O. 換下一組。
// 只用配色、道具與招式致敬角色，不畫官方標誌、不寫角色名字。
// 畫布是 128×80 的邏輯像素（CSS 放大、image-rendering: pixelated）。
(() => {
  const cv = document.getElementById('arena')
  if (!cv || !cv.getContext) return
  const ctx = cv.getContext('2d')
  const W = 128, H = 80, G = 70             // G：地面的 y
  const BASE = [42, 86]                      // 左右兩人站定的位置
  const box = cv.parentElement
  const hpBars = box.querySelectorAll('.hp i')
  const call = box.querySelector('.call')
  const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches

  // ---------------------------------------------------------------- 角色
  // 座標以腳底中心為原點、面向右；y 往上是負。R(x, y, w, h, 顏色)
  const SKIN = '#f1c27d', GOLD = '#f2b01e', WHITE = '#ffffff'
  const HEROES = {
    iron: { side: 'M', sp: 'beam', beam: '#8ff7ff',
      head: '#c8102e', torso: '#c8102e', arms: '#c8102e', hands: GOLD, legs: '#c8102e', boots: GOLD, eyes: '#8ff7ff',
      headFx: (R, b, l) => { R(0 + l, -21 + b, 3, 4, GOLD) },
      chestFx: (R, b, l) => { R(-2 + l, -12 + b, 4, 3, GOLD); R(-1 + l, -15 + b, 2, 2, '#8ff7ff') } },
    cap: { side: 'M', sp: 'shield',
      head: '#1f4fa8', torso: '#1f4fa8', arms: '#1f4fa8', hands: '#c8102e', legs: '#1f4fa8', boots: '#8a1020', eyes: WHITE,
      headFx: (R, b, l) => { R(0 + l, -18 + b, 3, 2, SKIN) },
      chestFx: (R, b, l) => { R(-4 + l, -12 + b, 8, 1, '#c8102e'); R(-4 + l, -11 + b, 8, 1, WHITE); R(-4 + l, -10 + b, 8, 1, '#c8102e'); R(-1 + l, -15 + b, 2, 2, WHITE) },
      backFx: (R, b, l, F) => { if (!F.noShield) { R(-9 + l, -16 + b, 4, 7, '#c8102e'); R(-8 + l, -15 + b, 2, 5, WHITE); R(-8 + l, -13 + b, 2, 1, '#1f4fa8') } } },
    thor: { side: 'M', sp: 'lightning', up: true,
      head: SKIN, torso: '#5a616c', arms: SKIN, legs: '#2a2d33', boots: '#80868f', cape: '#b3121e', eyes: '#3a6fd8',
      headFx: (R, b, l) => { R(-3 + l, -23 + b, 6, 2, '#f3d36b'); R(-4 + l, -22 + b, 2, 7, '#f3d36b') },
      chestFx: (R, b, l) => { R(-3 + l, -15 + b, 2, 2, '#b8c0cc'); R(1 + l, -15 + b, 2, 2, '#b8c0cc') },
      weapon: (R, hx, hy) => { R(hx, hy - 1, 1, 4, '#7a4a24'); R(hx - 1, hy - 4, 4, 3, '#a7adb6') } },
    hulk: { side: 'M', sp: 'smash', s: 1.3,
      head: '#4f9a32', torso: '#4f9a32', arms: '#4f9a32', legs: '#4f9a32', shorts: '#5b2a86', eyes: '#1b3d10',
      headFx: (R, b, l) => { R(-3 + l, -23 + b, 6, 2, '#16161a') },
      chestFx: (R, b, l) => { R(-3 + l, -14 + b, 2, 3, '#3e7d27'); R(1 + l, -14 + b, 2, 3, '#3e7d27') } },
    spidey: { side: 'M', sp: 'web',
      head: '#d0161e', torso: '#d0161e', arms: '#d0161e', legs: '#1c3fa0', boots: '#d0161e', eyes: WHITE,
      headFx: (R, b, l) => { R(0 + l, -21 + b, 3, 2, WHITE) },
      chestFx: (R, b, l) => { R(-4 + l, -16 + b, 2, 8, '#1c3fa0') } },
    superman: { side: 'D', sp: 'heat', beam: '#ff3b2f',
      head: SKIN, torso: '#1f4fbf', arms: '#1f4fbf', legs: '#1f4fbf', boots: '#c8102e', cape: '#c8102e', belt: GOLD, eyes: '#3a6fd8',
      headFx: (R, b, l) => { R(-3 + l, -23 + b, 6, 2, '#16161a'); R(2 + l, -22 + b, 1, 2, '#16161a') },
      chestFx: (R, b, l) => { R(-2 + l, -15 + b, 4, 3, '#c8102e'); R(-1 + l, -14 + b, 2, 1, GOLD) } },
    batman: { side: 'D', sp: 'batarang',
      head: '#2b2b33', torso: '#6b6f78', arms: '#6b6f78', hands: '#16161a', legs: '#6b6f78', boots: '#16161a', cape: '#15151a', belt: GOLD, eyes: WHITE,
      headFx: (R, b, l) => { R(-3 + l, -24 + b, 1, 2, '#2b2b33'); R(2 + l, -24 + b, 1, 2, '#2b2b33'); R(0 + l, -18 + b, 3, 2, SKIN) },
      chestFx: (R, b, l) => { R(-3 + l, -15 + b, 6, 2, '#16161a') } },
    flash: { side: 'D', sp: 'dash',
      head: '#d0161e', torso: '#d0161e', arms: '#d0161e', legs: '#d0161e', boots: GOLD, belt: GOLD, eyes: WHITE,
      headFx: (R, b, l) => { R(-3 + l, -21 + b, 1, 3, GOLD); R(0 + l, -18 + b, 3, 2, SKIN) },
      chestFx: (R, b, l) => { R(-1 + l, -15 + b, 2, 2, GOLD) } },
    ww: { side: 'D', sp: 'lasso',
      head: SKIN, torso: '#c1121f', arms: SKIN, hands: GOLD, legs: SKIN, boots: '#c1121f', eyes: '#16161a',
      headFx: (R, b, l) => { R(-3 + l, -23 + b, 7, 2, '#16161a'); R(-4 + l, -22 + b, 2, 9, '#16161a'); R(-2 + l, -22 + b, 4, 1, GOLD) },
      chestFx: (R, b, l) => { R(-4 + l, -16 + b, 8, 1, GOLD); R(-4 + l, -10 + b, 8, 3, '#1f3fa8'); R(-2 + l, -9 + b, 1, 1, WHITE); R(1 + l, -9 + b, 1, 1, WHITE) } },
    aqua: { side: 'D', sp: 'wave',
      head: SKIN, torso: '#e07b1a', arms: '#e07b1a', hands: SKIN, legs: '#1f7a4a', boots: '#1f7a4a', belt: GOLD, eyes: '#1f7a4a',
      headFx: (R, b, l) => { R(-3 + l, -23 + b, 6, 2, '#b9873a'); R(-4 + l, -22 + b, 2, 8, '#b9873a'); R(0 + l, -17 + b, 3, 1, '#8a6128') },
      chestFx: (R, b, l) => { R(-3 + l, -14 + b, 2, 1, '#f3a64a'); R(1 + l, -12 + b, 2, 1, '#f3a64a') },
      weapon: (R, hx, hy) => { R(hx, hy - 12, 1, 16, GOLD); R(hx - 2, hy - 12, 1, 3, GOLD); R(hx + 2, hy - 12, 1, 3, GOLD); R(hx - 2, hy - 10, 5, 1, GOLD) } },
  }
  const MARVEL = ['iron', 'cap', 'thor', 'hulk', 'spidey']
  const DCU = ['superman', 'batman', 'flash', 'ww', 'aqua']

  const fighter = (key, i) => ({ h: HEROES[key], key, x: i ? W + 14 : -14, y: 0, base: BASE[i], facing: i ? -1 : 1,
    pose: 'walk', hp: 100, flash: 0, alpha: 1, noShield: false })

  function handPos(F) {
    const l = F.pose === 'hit' ? -1 : 0
    if (F.pose === 'punch') return [11, -15]
    if (F.pose === 'win' || (F.pose === 'special' && F.h.up)) return [4, -26]
    if (F.pose === 'special') return [10, -16]
    return [4 + l, -10]
  }

  function drawFighter(F, t) {
    const h = F.h, S = h.s || 1, d = F.facing
    const X = Math.round(F.x), Y = Math.round(G + F.y)
    const blink = F.flash > 0 && Math.floor(t * 30) % 2 === 0
    ctx.globalAlpha = F.alpha
    const R = (x, y, w, hh, c) => {
      x *= S; y *= S; w *= S; hh *= S
      ctx.fillStyle = blink ? WHITE : c
      ctx.fillRect(Math.round(d > 0 ? X + x : X - x - w), Math.round(Y + y), Math.ceil(w), Math.ceil(hh))
    }
    if (F.pose === 'ko') {                       // 倒地
      if (h.cape) R(-12, -2, 11, 2, h.cape)
      R(-12, -3, 8, 3, h.legs); R(-12, -3, 2, 3, h.boots || h.legs)
      R(-4, -4, 8, 4, h.torso); R(4, -5, 6, 5, h.head)
      ctx.globalAlpha = 1
      return
    }
    const b = F.pose === 'idle' ? (Math.sin(t * 5 + F.base) > 0 ? 0 : 1) : 0
    const l = F.pose === 'hit' ? -1 : 0
    if (h.cape) R(-6 + l, -16 + b, 3, 14, h.cape)
    let lb = -4, lf = 1
    if (F.pose === 'walk') { const ph = Math.floor(t * 10) % 2; lb = ph ? -5 : -3; lf = ph ? 2 : 0 }
    if (F.pose === 'punch' || F.pose === 'special') { lb = -5; lf = 2 }
    R(lb, -8, 3, 8, h.legs); R(lf, -8, 3, 8, h.legs)
    if (h.boots) { R(lb, -2, 3, 2, h.boots); R(lf, -2, 3, 2, h.boots) }
    if (h.shorts) R(-4, -8, 8, 3, h.shorts)
    R(-6 + l, -16 + b, 2, 7, h.arms); R(-6 + l, -10 + b, 2, 1, h.hands || h.arms)
    if (h.backFx) h.backFx(R, b, l, F)
    R(-4 + l, -16 + b, 8, 8, h.torso)
    if (h.chestFx) h.chestFx(R, b, l)
    if (h.belt) R(-4 + l, -9 + b, 8, 1, h.belt)
    R(-3 + l, -22 + b, 6, 6, h.head)
    if (h.headFx) h.headFx(R, b, l)
    R(1 + l, -20 + b, 2, 1, h.eyes || '#16161a')
    const fa = h.arms, fh = h.hands || h.arms
    if (F.pose === 'punch') { R(4, -15, 7, 2, fa); R(11, -15, 2, 2, fh) }
    else if (F.pose === 'win' || (F.pose === 'special' && h.up)) { R(4, -25, 2, 9, fa); R(4, -26, 2, 1, fh) }
    else if (F.pose === 'special') { R(4, -16, 6, 2, fa); R(10, -16, 2, 2, fh) }
    else { R(4 + l, -16 + b, 2, 7, fa); R(4 + l, -10 + b, 2, 1, fh) }
    if (h.weapon) { const [hx, hy] = handPos(F); h.weapon(R, hx, hy + (F.pose === 'idle' ? b : 0)) }
    ctx.globalAlpha = 1
  }

  // ---------------------------------------------------------------- 背景（只畫一次）
  const bg = document.createElement('canvas'); bg.width = W; bg.height = H
  ;(() => {
    const g = bg.getContext('2d')
    const sky = ['#140a24', '#1c0d2e', '#261036', '#35123c', '#4a1440', '#651740']
    sky.forEach((c, i) => { g.fillStyle = c; g.fillRect(0, i * 12, W, 12) })
    g.fillStyle = '#651740'; g.fillRect(0, 72, W, H - 72)
    let seed = 7; const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280
    g.fillStyle = '#ffffff'
    for (let i = 0; i < 26; i++) g.fillRect(Math.floor(rnd() * W), Math.floor(rnd() * 36) + 14, 1, 1)
    g.fillStyle = '#ffe9b0'                       // 圓月（7×7 的像素圓）
    ;[[2, 0, 3], [1, 1, 5], [0, 2, 7], [0, 3, 7], [0, 4, 7], [1, 5, 5], [2, 6, 3]].forEach(([x, y, w]) => g.fillRect(100 + x, 14 + y, w, 1))
    g.fillStyle = '#f3d68a'; g.fillRect(102, 17, 2, 1); g.fillRect(104, 19, 1, 1)
    for (let x = 0; x < W;) {                       // 城市剪影與窗戶
      const w = 6 + Math.floor(rnd() * 10), h = 10 + Math.floor(rnd() * 22)
      g.fillStyle = '#0d0716'; g.fillRect(x, G - h, w, h)
      g.fillStyle = '#8a6a2e'
      for (let wy = G - h + 3; wy < G - 4; wy += 4) for (let wx = x + 2; wx < x + w - 2; wx += 3) if (rnd() < 0.14) g.fillRect(wx, wy, 1, 1)
      x += w + 1
    }
    g.fillStyle = '#2a2233'; g.fillRect(0, G, W, H - G)
    g.fillStyle = '#E4000F'; g.fillRect(0, G, W, 1)
    g.fillStyle = '#3a3046'; for (let x = 0; x < W; x += 8) g.fillRect(x, G + 5, 4, 1)
  })()

  // ---------------------------------------------------------------- 特效
  let fx = [], shake = 0
  const sparks = (x, y, n = 8, c = [WHITE, '#ffe24a', '#ff7a1a']) => {
    for (let i = 0; i < n; i++) { const a = Math.random() * Math.PI * 2, v = 30 + Math.random() * 50
      fx.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 20, life: 0.35, c: c[i % c.length] }) }
  }
  function stepFx(dt) {
    fx = fx.filter((p) => (p.life -= dt) > 0)
    for (const p of fx) { p.x += p.vx * dt; p.y += p.vy * dt; p.vy += 120 * dt }
  }
  function drawFx() {
    for (const p of fx) { ctx.fillStyle = p.c; ctx.fillRect(Math.round(p.x), Math.round(p.y), 2, 2) }
  }

  // 大招畫面：p 是 0～1 的進度
  function drawSpecial(A, D, p) {
    const S = A.h.s || 1, d = A.facing
    const hx = A.x + d * 11 * S, hy = G - 16 * S
    const dx = D.x, dy = G - 14
    const line = (x1, y1, x2, y2, c, w = 2) => {
      ctx.fillStyle = c
      const n = Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1)) | 0
      for (let i = 0; i <= n; i++) ctx.fillRect(Math.round(x1 + (x2 - x1) * i / n), Math.round(y1 + (y2 - y1) * i / n), w, w)
    }
    switch (A.h.sp) {
      case 'beam': case 'heat': {
        if (p < 0.25 || p > 0.8) break
        const y = A.h.sp === 'heat' ? G - 20 : hy
        const x0 = A.h.sp === 'heat' ? A.x + d * 3 : hx
        ctx.fillStyle = A.h.beam; ctx.fillRect(Math.min(x0, dx), y - 1, Math.abs(dx - x0), 3)
        ctx.fillStyle = WHITE; ctx.fillRect(Math.min(x0, dx), y, Math.abs(dx - x0), 1)
        if (Math.random() < 0.5) sparks(dx, y, 2, [A.h.beam, WHITE])
        break }
      case 'shield': case 'batarang': {
        const q = p < 0.5 ? p / 0.5 : 1 - (p - 0.5) / 0.5
        const x = hx + (dx - hx) * q, spin = Math.floor(p * 24) % 2
        if (A.h.sp === 'shield') {
          ctx.fillStyle = '#c8102e'; ctx.fillRect(x - 3, dy - 3, 6, 6)
          ctx.fillStyle = WHITE; ctx.fillRect(x - 2, dy - 2, 4, 4)
          ctx.fillStyle = '#1f4fa8'; ctx.fillRect(x - 1, dy - 1, 2, 2)
        } else {
          ctx.fillStyle = '#16161a'
          if (spin) ctx.fillRect(x - 4, dy, 8, 2); else ctx.fillRect(x - 1, dy - 3, 2, 8)
        }
        break }
      case 'lightning': {
        if (p < 0.28 || p > 0.62) break
        ctx.fillStyle = 'rgba(255,255,255,0.25)'; ctx.fillRect(0, 0, W, H)
        let x = dx, y = 0
        while (y < G - 12) { const nx = x + (Math.random() * 8 - 4) | 0, ny = y + 6; line(x, y, nx, ny, Math.random() < 0.5 ? WHITE : '#9fe8ff'); x = nx; y = ny }
        break }
      case 'smash': {
        if (p < 0.5) break
        const r = (p - 0.5) * 120
        ctx.fillStyle = '#c9b48a'
        for (const s of [-1, 1]) { const x = A.x + d * 10 + s * r; ctx.fillRect(Math.round(x), G - 4, 4, 4); ctx.fillRect(Math.round(x) + s * 5, G - 2, 2, 2) }
        break }
      case 'web': {
        if (p < 0.15) break
        const reach = Math.min(1, (p - 0.15) / 0.2)
        line(hx, hy, hx + (dx - hx) * reach, dy, WHITE, 1)
        if (p > 0.35) { ctx.fillStyle = WHITE; ctx.fillRect(dx - 3, dy - 6, 6, 10); ctx.fillStyle = '#d9d9d9'; ctx.fillRect(dx - 2, dy - 4, 4, 1); ctx.fillRect(dx - 2, dy, 4, 1) }
        break }
      case 'dash': {
        ctx.globalAlpha = 0.35
        for (let k = 1; k <= 3; k++) drawFighter({ ...A, x: A.x - d * k * 7, flash: 0, alpha: 0.35 }, 0)
        ctx.globalAlpha = 1
        ctx.fillStyle = '#ffe24a'
        for (let k = 0; k < 4; k++) ctx.fillRect(Math.round(A.x - d * (10 + k * 6)), G - 8 - k * 4, 5, 1)
        break }
      case 'lasso': {
        if (p < 0.18) break
        const reach = Math.min(1, (p - 0.18) / 0.2)
        line(hx, hy, hx + (dx - hx) * reach, dy, GOLD, 1)
        if (p > 0.38) { ctx.fillStyle = GOLD; ctx.fillRect(dx - 5, dy - 4, 10, 1); ctx.fillRect(dx - 5, dy + 3, 10, 1); ctx.fillRect(dx - 5, dy - 4, 1, 8); ctx.fillRect(dx + 4, dy - 4, 1, 8) }
        break }
      case 'wave': {
        if (p < 0.2) break
        const q = Math.min(1, (p - 0.2) / 0.35), x = hx + (dx - hx) * q, w = 14
        ctx.fillStyle = '#1c6fd1'; ctx.fillRect(Math.round(Math.min(x, x - d * w)), G - 12, w, 12)
        ctx.fillStyle = '#6fc3ff'; ctx.fillRect(Math.round(Math.min(x, x - d * w)), G - 13, w, 2)
        ctx.fillStyle = WHITE; for (let i = 0; i < w; i += 3) ctx.fillRect(Math.round(Math.min(x, x - d * w)) + i, G - 14, 1, 1)
        break }
    }
  }

  // ---------------------------------------------------------------- 比賽流程
  let round = 0, P = [], state = 'enter', st = 0, act = null, rest = 0, specials = [0, 0], T = 0
  const say = (text) => { call.textContent = text; call.classList.toggle('on', !!text) }
  const hpUI = () => P.forEach((F, i) => { hpBars[i].style.width = Math.max(0, F.hp) + '%' })

  // 每次重新整理都洗牌：出場順序、對手、左右邊都隨機；第一組也不會跟上次看到的一樣
  const shuffle = (a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]] } return a }
  const mOrder = shuffle(MARVEL), dOrder = shuffle(DCU)
  let lastPair = ''
  try { lastPair = localStorage.getItem('dc-arena-last') || '' } catch (e) { /* 無痕模式 */ }
  if (lastPair === mOrder[0] + ',' + dOrder[0]) dOrder.push(dOrder.shift())
  try { localStorage.setItem('dc-arena-last', mOrder[0] + ',' + dOrder[0]) } catch (e) { /* 無痕模式 */ }
  const leftFirst = Math.random() < 0.5

  function newMatch() {
    const m = mOrder[round % 5], d = dOrder[(round + Math.floor(round / 5)) % 5]
    const left = (round % 2 === 0) === leftFirst
    P = left ? [fighter(m, 0), fighter(d, 1)] : [fighter(d, 0), fighter(m, 1)]
    round++; state = 'enter'; st = 0; act = null; rest = 0; specials = [0, 0]; fx = []
    say(''); hpUI()
  }

  function hit(A, D, dmg, big) {
    D.hp -= dmg; D.flash = 0.28; D.pose = 'hit'
    sparks(D.x, G - 14 * (D.h.s || 1), big ? 14 : 8)
    if (big) shake = 0.35
    hpUI()
  }

  function startAction() {
    const i = Math.random() < 0.5 ? 0 : 1
    const A = P[i], D = P[1 - i]
    const special = specials[i] < 2 && (Math.random() < 0.38 || (A.hp < 45 && specials[i] === 0))
    if (special) specials[i]++
    act = special
      ? { A, D, kind: 'special', t: 0, dur: A.h.sp === 'smash' ? 1.2 : 1.1, hitAt: { beam: 0.5, heat: 0.5, shield: 0.45, batarang: 0.45, lightning: 0.4, smash: 0.5, web: 0.4, dash: 0.3, lasso: 0.42, wave: 0.55 }[A.h.sp], hit: false }
      : { A, D, kind: 'melee', t: 0, dur: 0.75, hitAt: 0.32, hit: false }
  }

  function stepAction(dt) {
    const { A, D } = act
    act.t += dt
    const p = Math.min(1, act.t / act.dur), d = A.facing, S = A.h.s || 1
    if (act.kind === 'melee') {
      const near = D.x - d * 13 * S
      if (p < 0.3) { A.pose = 'walk'; A.x = A.base + (near - A.base) * (p / 0.3) }
      else if (p < 0.5) { A.pose = 'punch'; A.x = near }
      else { A.pose = 'idle'; A.x = near + (A.base - near) * ((p - 0.5) / 0.5) }
    } else {
      A.pose = 'special'
      if (A.h.sp === 'shield') A.noShield = p > 0.05 && p < 0.95
      if (A.h.sp === 'smash') {
        const near = D.x - d * 14 * S
        if (p < 0.5) { const q = p / 0.5; A.x = A.base + (near - A.base) * q; A.y = -Math.sin(Math.PI * q) * 18 }
        else { A.y = 0; A.x = p < 0.8 ? near : near + (A.base - near) * ((p - 0.8) / 0.2) }
      }
      if (A.h.sp === 'dash') {
        const near = D.x - d * 11
        const q = p < 0.6 ? Math.abs(Math.sin(p / 0.6 * Math.PI * 2)) : 0
        A.x = A.base + (near - A.base) * q
      }
      if (A.h.sp === 'web' && p > 0.4 && p < 0.7) D.x = D.base - d * (p - 0.4) * 20
      if (A.h.sp === 'lasso' && p > 0.45 && p < 0.75) D.x = D.base - d * (p - 0.45) * 16
    }
    if (!act.hit && p >= act.hitAt) {
      act.hit = true
      hit(A, D, act.kind === 'special' ? 24 + Math.floor(Math.random() * 9) : 9 + Math.floor(Math.random() * 9), act.kind === 'special')
      if (A.h.sp === 'dash' && act.kind === 'special') act.hit2 = false
    }
    if (act.kind === 'special' && A.h.sp === 'dash' && act.hit && act.hit2 === false && p > 0.5) { act.hit2 = true; hit(A, D, 8, false) }
    // 被打的人往後退一點、再站回原位
    if (D.pose === 'hit' && !(act.kind === 'special' && (A.h.sp === 'web' || A.h.sp === 'lasso'))) {
      const q = Math.max(0, Math.min(1, (p - act.hitAt) / 0.35))
      D.x = D.base + A.facing * 7 * Math.sin(Math.PI * q)
    }
    if (p >= 1) {
      A.pose = 'idle'; A.x = A.base; A.y = 0; A.noShield = false
      D.x = D.base
      if (D.hp <= 0) { D.pose = 'ko'; A.pose = 'win'; state = 'ko'; st = 0; say('K.O.') }
      else { D.pose = 'idle'; rest = 0.25 + Math.random() * 0.25 }
      act = null
    }
  }

  function update(dt) {
    st += dt
    stepFx(dt)
    for (const F of P) F.flash = Math.max(0, F.flash - dt)
    shake = Math.max(0, shake - dt)
    if (state === 'enter') {
      const q = Math.min(1, st / 1.1)
      P[0].x = -14 + (P[0].base + 14) * q; P[1].x = W + 14 + (P[1].base - W - 14) * q
      if (st > 0.1 && st < 0.9) say('ROUND ' + round)
      if (q >= 1) { P.forEach((F) => (F.pose = 'idle')); state = 'ready'; st = 0; say('FIGHT!') }
    } else if (state === 'ready') {
      if (st > 0.7) { state = 'fight'; st = 0; say('') }
    } else if (state === 'fight') {
      if (act) stepAction(dt)
      else if ((rest -= dt) <= 0) startAction()
    } else if (state === 'ko') {
      if (st > 1.8) { state = 'exit'; st = 0; say('') }
    } else if (state === 'exit') {
      P.forEach((F) => (F.alpha = Math.max(0, 1 - st / 0.5)))
      if (st > 0.6) newMatch()
    }
  }

  function render(dt) {
    ctx.save()
    if (shake > 0) ctx.translate(Math.round(Math.random() * 4 - 2), Math.round(Math.random() * 3 - 1))
    ctx.drawImage(bg, 0, 0)
    for (const F of P) drawFighter(F, T)
    if (act && act.kind === 'special') drawSpecial(act.A, act.D, Math.min(1, act.t / act.dur))
    drawFx()
    ctx.restore()
  }

  // ---------------------------------------------------------------- 迴圈（畫面外、分頁在背景時暫停）
  newMatch()
  // 測試用：?arena_ff=秒數 直接快轉到那個時間點再畫一張（截圖檢查用）
  const ff = parseFloat(new URLSearchParams(location.search).get('arena_ff'))
  if (ff > 0) {
    for (let t = 0; t < ff; t += 1 / 60) { T += 1 / 60; update(1 / 60); if (t > ff - 0.2) render(1 / 60) }
    render(0)
    return
  }
  if (reduce) {                       // 減少動態：停在兩人對峙的畫面
    P[0].x = P[0].base; P[1].x = P[1].base; P.forEach((F) => (F.pose = 'idle'))
    render(0)
    return
  }
  let last = 0, visible = true, raf = 0
  const loop = (now) => {
    const dt = Math.min(0.05, (now - (last || now)) / 1000); last = now; T += dt
    update(dt); render(dt)
    raf = requestAnimationFrame(loop)
  }
  const start = () => { if (!raf && visible && !document.hidden) { last = 0; raf = requestAnimationFrame(loop) } }
  const stop = () => { cancelAnimationFrame(raf); raf = 0 }
  if ('IntersectionObserver' in window) new IntersectionObserver((es) => { visible = es[0].isIntersecting; visible ? start() : stop() }).observe(cv)
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()))
  render(0)
  start()
})()
