'use strict';
const byId = id => document.getElementById(id);
let cards = [];
let assets = new Map();
let elapsed = 0;
let playing = true;
let previous = performance.now();
let selected = null;
let generation = 0;
let scene = null;

function relativeUrl(path, base) {
  if (typeof path !== 'string' || path.includes('..') || !/^[A-Za-z0-9_./-]+$/.test(path) || path.startsWith('/')) {
    throw new Error(`不安全的相对路径：${path}`);
  }
  return new URL(path, base);
}
async function json(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `${url.pathname}: HTTP ${response.status}`);
  return data;
}
async function loadImage(url, expectedHash) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`图片读取失败：${url.pathname} HTTP ${response.status}`);
  const bytes = await response.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const hash = [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2,'0')).join('');
  if (hash !== expectedHash) throw new Error(`图片在校验后发生变化：${url.pathname}`);
  const objectUrl = URL.createObjectURL(new Blob([bytes], {type:'image/png'}));
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => { URL.revokeObjectURL(objectUrl); resolve(image); };
    image.onerror = () => { URL.revokeObjectURL(objectUrl); reject(new Error(`无法解码图片：${url.pathname}`)); };
    image.src = objectUrl;
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
    const validationUrl = new URL('api/validate', root);
    validationUrl.searchParams.set('manifest', byId('manifest').value);
    const validated = await json(validationUrl);
    const manifest = validated.manifest;
    const theme = validated.theme;
    const previewScene = validated.preview;
    const loaded = await Promise.all(manifest.assets.map(async asset => {
      const image = await loadImage(relativeUrl(asset.file, url), asset.sha256);
      if (image.width !== asset.size[0] || image.height !== asset.size[1]) throw new Error(`${asset.id} 尺寸与清单不同`);
      return {...asset, image};
    }));
    if (current !== generation) return;
    assets = new Map(loaded.map(asset => [asset.id, asset]));
    const durations = loaded.flatMap(asset => Object.values(asset.clips).map(clip => clip.frames.length * 1000 / clip.fps));
    byId('time').max = Math.ceil(Math.max(...durations));
    scene = previewScene;
    if (scene) {
      for (const item of [...scene.tiles, ...scene.items]) {
        if (!assets.has(item.asset)) throw new Error(`场景引用缺失资源：${item.asset}`);
        if (!assets.get(item.asset).clips[item.clip]) throw new Error(`场景引用缺失动作：${item.asset}/${item.clip}`);
      }
      byId('map').width = scene.canvas_size[0];
      byId('map').height = scene.canvas_size[1];
    }
    selected = null;
    byId('selection').textContent = scene ? '尚未选择地块' : '本批未提供可选场景；所有资产仍可在下方独立预览。';
    byId('gallery').replaceChildren(); cards = loaded.map(card); elapsed = 0;
    byId('status').textContent = `${theme.title} · ${loaded.length} 项资源已校验并载入 · ${validated.report.decoded_bytes.toLocaleString()} 解码字节`;
    const global = theme.global_visual;
    byId('global').textContent = global ? `${global.id} / ${global.start_year}\n${global.entities.map(entity => `${entity.label}\n特色外观：${entity.specialty_units.join(', ')}`).join('\n')}` : '本批未包含全球视觉描述。';
  } catch (error) {
    if (current !== generation) return;
    assets = new Map(); cards = []; scene = null; selected = null;
    byId('gallery').replaceChildren(); byId('global').textContent = '';
    byId('status').className = 'error';
    byId('status').textContent = `载入失败：${error.message}\n请使用 python tools/preview.py 启动工作台，按错误定位修正数据。`;
  }
}
function centers() {
  if (!scene) return [];
  const scale = Number(byId('zoom').value);
  return scene.tiles.map(tile => ({...tile, scale,
    x: scene.origin[0] + (tile.column * scene.hex.step[0] + (tile.row % 2) * scene.hex.odd_row_offset) * scale,
    y: scene.origin[1] + tile.row * scene.hex.step[1] * scale
  }));
}
function renderMap() {
  const canvas = byId('map'), ctx = canvas.getContext('2d'); ctx.clearRect(0,0,canvas.width,canvas.height);
  for (const center of centers()) {
    const tile = assets.get(center.asset);
    draw(ctx,tile,center.clip,elapsed,center.x,center.y,center.scale,false,false);
    if (selected && center.row === selected.row && center.column === selected.column) {
      ctx.strokeStyle='#e33967'; ctx.lineWidth=3; ctx.strokeRect(center.x-17,center.y-17,34,34);
    }
  }
  if (scene) {
    const zoom = Number(byId('zoom').value);
    for (const item of scene.items) {
      draw(ctx,assets.get(item.asset),item.clip,elapsed,
        scene.origin[0]+item.position[0]*zoom, scene.origin[1]+item.position[1]*zoom,
        item.scale*zoom,byId('mirror').checked,byId('anchors').checked);
    }
  }
}
byId('map').addEventListener('click', event => {
  const rect = event.currentTarget.getBoundingClientRect();
  const x = (event.clientX-rect.left)*event.currentTarget.width/rect.width;
  const y = (event.clientY-rect.top)*event.currentTarget.height/rect.height;
  selected = centers().sort((a,b)=>(a.x-x)**2+(a.y-y)**2-(b.x-x)**2-(b.y-y)**2)[0];
  if (!selected) return;
  const tile = assets.get(selected.asset);
  const dx = Math.abs(x-selected.x)/(tile.display_size[0]*selected.scale/2);
  const dy = Math.abs(y-selected.y)/(tile.display_size[1]*selected.scale/2);
  if (dx>1 || dy>1 || dy>1-dx/2) {
    selected = null;
    byId('selection').textContent = '点击位于格网之外';
    return;
  }
  byId('selection').textContent = `选择：row=${selected.row}, column=${selected.column}；屏幕中心 ${selected.x.toFixed(1)}, ${selected.y.toFixed(1)}`;
});
byId('loader').addEventListener('submit', event => { event.preventDefault(); load(); });
byId('play').onclick = () => { playing = !playing; byId('play').textContent = playing ? '暂停动画' : '播放动画'; };
byId('restart').onclick = () => { elapsed = 0; };
byId('time').oninput = event => { playing = false; byId('play').textContent = '播放动画'; elapsed = Number(event.target.value); };
function tick(now) {
  if (playing) elapsed += Math.min(100, now-previous);
  if (playing) byId('time').value = Math.min(Number(byId('time').max), elapsed);
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
