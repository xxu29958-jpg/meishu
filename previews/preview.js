'use strict';
const byId = id => document.getElementById(id);
let cards = [];
let assets = new Map();
let elapsed = 0;
let playing = true;
let previous = performance.now();
let selected = null;
let generation = 0;

function relativeUrl(path, base) {
  if (typeof path !== 'string' || path.includes('..') || !/^[A-Za-z0-9_./-]+$/.test(path) || path.startsWith('/')) {
    throw new Error(`不安全的相对路径：${path}`);
  }
  return new URL(path, base);
}
async function json(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url.pathname}: HTTP ${response.status}`);
  return response.json();
}
function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`无法解码图片：${url.pathname}`));
    image.src = url;
  });
}
function draw(ctx, asset, clipName, time, x, y, scale, mirror, anchors) {
  const clip = asset.clips[clipName];
  if (!clip) throw new Error(`${asset.id} 缺少动作 ${clipName}`);
  const index = Math.floor(time * clip.fps / 1000);
  const frame = clip.frames[clip.loop ? index % clip.frames.length : Math.min(index, clip.frames.length - 1)];
  const [fw, fh] = asset.frame_size;
  const columns = asset.size[0] / fw;
  const [dw, dh] = asset.display_size;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale * (mirror && asset.directions === 'mirror-x' ? -1 : 1), scale);
  ctx.globalCompositeOperation = asset.blend === 'add' ? 'lighter' : 'source-over';
  ctx.drawImage(asset.image, (frame % columns) * fw, Math.floor(frame / columns) * fh, fw, fh,
    -asset.anchor[0] * dw, -asset.anchor[1] * dh, dw, dh);
  ctx.restore();
  if (anchors) {
    ctx.strokeStyle = '#d42859'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x-7,y); ctx.lineTo(x+7,y); ctx.moveTo(x,y-7); ctx.lineTo(x,y+7); ctx.stroke();
  }
}
function card(asset) {
  const article = document.createElement('article');
  const canvas = document.createElement('canvas'); canvas.width = 400; canvas.height = 260;
  canvas.setAttribute('aria-label', asset.id);
  const info = document.createElement('div'); info.className = 'info';
  const title = document.createElement('h3'); title.textContent = asset.id;
  const details = document.createElement('p');
  details.textContent = `${asset.frame_size.join(' × ')} px · 锚点 ${asset.anchor.join(', ')} · ${asset.directions}`;
  const select = document.createElement('select'); select.setAttribute('aria-label', `${asset.id} 动作`);
  for (const name of Object.keys(asset.clips)) {
    const option = document.createElement('option'); option.value = name; option.textContent = name; select.append(option);
  }
  select.addEventListener('change', () => { elapsed = 0; });
  info.append(title, details, select); article.append(canvas, info); byId('gallery').append(article);
  return {asset, canvas, select};
}
async function load() {
  const current = ++generation;
  byId('status').className = '';
  byId('status').textContent = '正在检查并加载批次…';
  try {
    const root = new URL('../', location.href);
    const url = relativeUrl(byId('manifest').value, root);
    const manifest = await json(url);
    if (manifest.contract_version !== 1) throw new Error('不支持的合同版本');
    const theme = await json(relativeUrl(manifest.theme, url));
    const loaded = await Promise.all(manifest.assets.map(async asset => {
      const image = await loadImage(relativeUrl(asset.file, url));
      if (image.width !== asset.size[0] || image.height !== asset.size[1]) throw new Error(`${asset.id} 尺寸与清单不同`);
      return {...asset, image};
    }));
    if (current !== generation) return;
    assets = new Map(loaded.map(asset => [asset.id, asset]));
    byId('gallery').replaceChildren(); cards = loaded.map(card); elapsed = 0;
    byId('status').textContent = `${theme.title} · ${loaded.length} 项资源已载入。此预览不替代完整格式校验。`;
    const global = theme.global_visual;
    byId('global').textContent = global ? `${global.id} / ${global.start_year}\n${global.entities.map(entity => `${entity.label}\n特色外观：${entity.specialty_units.join(', ')}`).join('\n')}` : '本批未包含全球视觉描述。';
  } catch (error) {
    byId('status').className = 'error';
    byId('status').textContent = `载入失败：${error.message}\n请使用 README 中的本地 HTTP 服务，确认清单路径，并运行 tools/validate.py。`;
  }
}
function centers() {
  const scale = Number(byId('zoom').value) * 1.35;
  const result = [];
  for (let row=0; row<3; row++) for (let column=0; column<4; column++) {
    result.push({row,column,x:100+(column+(row%2)/2)*64*scale,y:65+row*54*scale,scale});
  }
  return result;
}
function renderMap() {
  const canvas = byId('map'), ctx = canvas.getContext('2d'); ctx.clearRect(0,0,canvas.width,canvas.height);
  const tiles = ['plain','forest','mountain','water'];
  for (const center of centers()) {
    const tile = assets.get(`maps.terrain.${tiles[(center.row+center.column)%tiles.length]}`);
    if (tile) draw(ctx,tile,'still',0,center.x,center.y,center.scale,false,false);
    if (selected && center.row === selected.row && center.column === selected.column) {
      ctx.strokeStyle='#e33967'; ctx.lineWidth=3; ctx.strokeRect(center.x-17,center.y-17,34,34);
    }
  }
  const unit = assets.get('units.infantry.line');
  if (unit) draw(ctx,unit,'move',elapsed,280,140,1.6,byId('mirror').checked,byId('anchors').checked);
}
byId('map').addEventListener('click', event => {
  const rect = event.currentTarget.getBoundingClientRect();
  const x = (event.clientX-rect.left)*640/rect.width, y = (event.clientY-rect.top)*340/rect.height;
  selected = centers().sort((a,b)=>(a.x-x)**2+(a.y-y)**2-(b.x-x)**2-(b.y-y)**2)[0];
  byId('selection').textContent = `选择：row=${selected.row}, column=${selected.column}；屏幕中心 ${selected.x.toFixed(1)}, ${selected.y.toFixed(1)}`;
});
byId('loader').addEventListener('submit', event => { event.preventDefault(); load(); });
byId('play').onclick = () => { playing = !playing; byId('play').textContent = playing ? '暂停动画' : '播放动画'; };
byId('restart').onclick = () => { elapsed = 0; };
byId('time').oninput = event => { playing = false; byId('play').textContent = '播放动画'; elapsed = Number(event.target.value); };
function tick(now) {
  if (playing) elapsed += Math.min(100, now-previous);
  previous = now;
  byId('milliseconds').textContent = `${Math.round(elapsed)} ms`;
  for (const {asset,canvas,select} of cards) {
    const ctx = canvas.getContext('2d'); ctx.clearRect(0,0,canvas.width,canvas.height);
    const [dw,dh] = asset.display_size;
    const scale = Math.min(340/dw,210/dh,2.4);
    const x = 200+(asset.anchor[0]-.5)*dw*scale;
    const y = 130+(asset.anchor[1]-.5)*dh*scale;
    draw(ctx,asset,select.value,elapsed,x,y,scale,byId('mirror').checked,byId('anchors').checked);
  }
  renderMap(); requestAnimationFrame(tick);
}
load(); requestAnimationFrame(tick);
