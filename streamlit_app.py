import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="충북 교육 미션 게임", page_icon="🚀", layout="wide")

st.title("🚀 김성근 교육감 후보 - 충북 교육 미션")
st.caption("Star Fox 느낌의 레일 슈팅 미니게임: 교육 문제를 해결하고 새로운 충북 교육을 완성하세요!")

st.markdown(
    """
**조작 방법**
- 이동: `← → ↑ ↓` 또는 `W A S D`
- 발사: `Space`
- 목표: 교육 문제(장애물)를 제거하고 정책 아이템을 수집해 60초 안에 최고 점수를 달성!
"""
)

components.html(
    """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <style>
    body { margin:0; background:#0b1020; color:#fff; font-family:system-ui, sans-serif; }
    .wrap { display:flex; flex-direction:column; align-items:center; gap:8px; padding:8px; }
    canvas { border:2px solid #5da8ff; border-radius:10px; box-shadow:0 0 20px rgba(93,168,255,.45); background:linear-gradient(#0c1838,#081026); }
    .hud { width:900px; max-width:100%; display:flex; justify-content:space-between; font-weight:700; }
    .small { opacity:.85; font-size:13px; }
  </style>
</head>
<body>
<div class=\"wrap\">
  <div class=\"hud\">
    <div id=\"score\">점수: 0</div>
    <div id=\"life\">생명: 5</div>
    <div id=\"time\">남은 시간: 60</div>
  </div>
  <canvas id=\"game\" width=\"900\" height=\"500\"></canvas>
  <div class=\"small\">정책 아이템(초록)을 먹으면 +20점, 문제 장애물(빨강)은 맞추면 +10점 / 충돌 시 생명 -1</div>
</div>
<script>
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const W = canvas.width, H = canvas.height;

let keys = {};
let score = 0, life = 5, timeLeft = 60;
let gameOver = false;

const player = { x:120, y:H/2, w:34, h:22, speed:5, cooldown:0 };
const bullets = [];
const enemies = [];
const items = [];
const stars = Array.from({length:140}, () => ({x:Math.random()*W, y:Math.random()*H, z:1+Math.random()*3}));

const enemyLabels = ["학력격차", "교실과밀", "돌봄부담", "진로혼선", "디지털격차"];
const itemLabels = ["기초학력지원", "AI교육", "돌봄강화", "교사행정경감", "진로체험확대"];

addEventListener('keydown', e => { keys[e.key.toLowerCase()] = true; if (e.code === 'Space') e.preventDefault(); });
addEventListener('keyup', e => { keys[e.key.toLowerCase()] = false; });

function spawnEnemy(){
  const h = 26 + Math.random()*18;
  enemies.push({x:W+20, y:20+Math.random()*(H-40), w:h*1.1, h, speed:3+Math.random()*3, label: enemyLabels[Math.floor(Math.random()*enemyLabels.length)]});
}
function spawnItem(){
  const r = 12 + Math.random()*8;
  items.push({x:W+20, y:20+Math.random()*(H-40), r, speed:2.4+Math.random()*2, label:itemLabels[Math.floor(Math.random()*itemLabels.length)]});
}

setInterval(() => { if(!gameOver) spawnEnemy(); }, 700);
setInterval(() => { if(!gameOver) spawnItem(); }, 1800);
setInterval(() => {
  if(gameOver) return;
  timeLeft--;
  if(timeLeft <= 0) gameOver = true;
}, 1000);

function collide(a,b){
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

function update(){
  if(gameOver) return;

  if(keys['arrowup']||keys['w']) player.y -= player.speed;
  if(keys['arrowdown']||keys['s']) player.y += player.speed;
  if(keys['arrowleft']||keys['a']) player.x -= player.speed;
  if(keys['arrowright']||keys['d']) player.x += player.speed;

  player.x = Math.max(20, Math.min(W-120, player.x));
  player.y = Math.max(20, Math.min(H-20-player.h, player.y));

  if(player.cooldown>0) player.cooldown--;
  if(keys[' '] && player.cooldown===0){
    bullets.push({x:player.x+player.w, y:player.y+player.h/2-2, w:14, h:4, speed:10});
    player.cooldown=9;
  }

  for(const s of stars){ s.x -= s.z; if(s.x<0){ s.x=W; s.y=Math.random()*H; } }

  bullets.forEach(b=> b.x += b.speed);
  for(let i=bullets.length-1;i>=0;i--) if(bullets[i].x>W) bullets.splice(i,1);

  enemies.forEach(e=> e.x -= e.speed);
  items.forEach(it=> it.x -= it.speed);

  for(let i=enemies.length-1;i>=0;i--){
    const e = enemies[i];
    if(e.x + e.w < 0) { enemies.splice(i,1); continue; }

    const pbox = {x:player.x, y:player.y, w:player.w, h:player.h};
    if(collide(pbox,e)){
      life--; enemies.splice(i,1);
      if(life<=0) gameOver = true;
      continue;
    }

    for(let j=bullets.length-1;j>=0;j--){
      if(collide(bullets[j],e)){
        bullets.splice(j,1);
        enemies.splice(i,1);
        score += 10;
        break;
      }
    }
  }

  for(let i=items.length-1;i>=0;i--){
    const it = items[i];
    if(it.x + it.r < 0) { items.splice(i,1); continue; }
    const cx = player.x + player.w/2, cy = player.y + player.h/2;
    const d = Math.hypot(cx-it.x, cy-it.y);
    if(d < it.r + Math.max(player.w,player.h)/2){
      score += 20;
      items.splice(i,1);
    }
  }

  document.getElementById('score').textContent = `점수: ${score}`;
  document.getElementById('life').textContent = `생명: ${life}`;
  document.getElementById('time').textContent = `남은 시간: ${timeLeft}`;
}

function drawShip(){
  const x=player.x, y=player.y;
  ctx.fillStyle='#84c8ff';
  ctx.beginPath();
  ctx.moveTo(x, y+player.h/2);
  ctx.lineTo(x+player.w, y);
  ctx.lineTo(x+player.w-4, y+player.h/2);
  ctx.lineTo(x+player.w, y+player.h);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle='#2c5ea8';
  ctx.fillRect(x+8,y+8,12,6);

  ctx.fillStyle='#ff8a30';
  ctx.fillRect(x-8,y+9,8,4);
}

function draw(){
  ctx.clearRect(0,0,W,H);

  for(const s of stars){
    ctx.fillStyle = `rgba(255,255,255,${0.3 + s.z/5})`;
    ctx.fillRect(s.x, s.y, s.z, s.z);
  }

  drawShip();

  ctx.fillStyle='#8fe3ff';
  bullets.forEach(b=>ctx.fillRect(b.x,b.y,b.w,b.h));

  enemies.forEach(e=>{
    ctx.fillStyle='#ff4f4f';
    ctx.fillRect(e.x,e.y,e.w,e.h);
    ctx.fillStyle='white';
    ctx.font='12px sans-serif';
    ctx.fillText(e.label, e.x+2, e.y-4);
  });

  items.forEach(it=>{
    ctx.fillStyle='#41d17a';
    ctx.beginPath(); ctx.arc(it.x,it.y,it.r,0,Math.PI*2); ctx.fill();
    ctx.fillStyle='white';
    ctx.font='11px sans-serif';
    ctx.fillText(it.label, it.x-it.r, it.y-it.r-4);
  });

  if(gameOver){
    ctx.fillStyle='rgba(0,0,0,.55)';
    ctx.fillRect(0,0,W,H);
    ctx.fillStyle='white';
    ctx.font='bold 42px sans-serif';
    ctx.fillText('미션 종료!', W/2-110, H/2-20);
    ctx.font='24px sans-serif';
    ctx.fillText(`최종 점수: ${score}`, W/2-85, H/2+20);
    ctx.font='16px sans-serif';
    ctx.fillText('새로고침하면 다시 시작됩니다.', W/2-110, H/2+55);
  }
}

function loop(){ update(); draw(); requestAnimationFrame(loop); }
loop();
</script>
</body>
</html>
""",
    height=620,
)

st.info("원하시면 다음 단계로 후보 이미지(제공하신 PNG)를 우주선 스프라이트로 적용하도록 확장해드릴게요.")
