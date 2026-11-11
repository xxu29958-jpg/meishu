'use strict';
/* Screen viewer: composes a batch's UI assets into working screens from a flow file.

   Three inputs, kept apart: the batch manifest (art facts, validated by the same
   /api/validate the workbench uses), a flow (page compositions) and display data
   (representative names, prices, counts). Interaction state lives only here:
   current screen, selection, pressed control, open dialog, scroll, clock.
   Nothing in this file names an asset, a screen or a nation. */

const $ = id => document.getElementById(id);
const SCROLLBAR = 14;                        // room kept clear at the right of a list for its scroll indicator
const state = { screen: null, dialog: null, selection: {}, tab: {}, assets: new Map(), flow: null, data: null,
                viewport: null, started: performance.now(), sprites: [] };

async function getJson(url) {
  const response = await fetch(url);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `${url}: HTTP ${response.status}`);
  return body;
}

function lookup(path, scope) {
  let value = scope;
  for (const key of path.split('.')) {
    if (value == null) return undefined;
    value = value[key];
  }
  return value;
}
/* "{item.name}" -> display text. Unknown paths stay visible so a broken binding is noticed. */
const fill = (template, scope) => String(template).replace(/\{([^}]+)\}/g, (whole, path) => {
  const value = lookup(path.trim(), scope);
  return value === undefined ? `⟨${path}⟩` : value;
});

function asset(id, node) {
  const found = state.assets.get(id);
  if (!found) throw new Error(`Screen "${state.screen}" uses asset ${id}, which this batch does not contain (${node.type})`);
  return found;
}
function stateFrame(item, name) {
  const clip = item.clips[name];
  if (!clip) throw new Error(`${item.id} has no "${name}" state`);
  return clip.frames[0];
}
/* A window onto part of one frame, stretched to fill `box`. Pure CSS on the sheet: no pixel read-back,
   so it behaves the same in every browser and the way an engine samples a sprite. */
function region(box, item, frame, sx, sy, sw, sh) {
  const [fw, fh] = item.frame_size, columns = item.size[0] / fw;
  const x = (frame % columns) * fw + sx, y = Math.floor(frame / columns) * fh + sy;
  const sheet = document.createElement('img');
  sheet.alt = ''; sheet.src = item.url; sheet.className = 'sheet';
  Object.assign(sheet.style, { left: `${-x / sw * 100}%`, top: `${-y / sh * 100}%`,
                               width: `${item.size[0] / sw * 100}%`, height: `${item.size[1] / sh * 100}%` });
  box.classList.add('window');
  box.append(sheet);
  return box;
}
function piece(css, item, frame, sx, sy, sw, sh) {
  const box = document.createElement('div');
  box.className = 'piece';
  Object.assign(box.style, css);
  return sw > 0 && sh > 0 ? region(box, item, frame, sx, sy, sw, sh) : box;
}
/* Nine-slice from the manifest's stretch insets [left, top, right, bottom]: corners keep their size,
   edges stretch one way, the centre both. */
function skin(element, item, name) {
  const [l, t, r, b] = item.stretch, [fw, fh] = item.frame_size, frame = stateFrame(item, name);
  const cw = fw - l - r, ch = fh - t - b;
  const inner = `calc(100% - ${l + r}px)`, tall = `calc(100% - ${t + b}px)`;
  const layer = document.createElement('div');
  layer.className = 'skin';
  layer.append(
    piece({ left: 0, top: 0, width: `${l}px`, height: `${t}px` }, item, frame, 0, 0, l, t),
    piece({ left: `${l}px`, top: 0, width: inner, height: `${t}px` }, item, frame, l, 0, cw, t),
    piece({ right: 0, top: 0, width: `${r}px`, height: `${t}px` }, item, frame, fw - r, 0, r, t),
    piece({ left: 0, top: `${t}px`, width: `${l}px`, height: tall }, item, frame, 0, t, l, ch),
    piece({ left: `${l}px`, top: `${t}px`, width: inner, height: tall }, item, frame, l, t, cw, ch),
    piece({ right: 0, top: `${t}px`, width: `${r}px`, height: tall }, item, frame, fw - r, t, r, ch),
    piece({ left: 0, bottom: 0, width: `${l}px`, height: `${b}px` }, item, frame, 0, fh - b, l, b),
    piece({ left: `${l}px`, bottom: 0, width: inner, height: `${b}px` }, item, frame, l, fh - b, cw, b),
    piece({ right: 0, bottom: 0, width: `${r}px`, height: `${b}px` }, item, frame, fw - r, fh - b, r, b));
  element.querySelector(':scope > .skin')?.remove();
  element.prepend(layer);
}

/* Placement: design coordinates on the flow's canvas; ax/ay say which edge a node keeps when the
   viewport is wider or taller than the design canvas. */
function place(element, node, parent) {
  const extraX = parent.width - parent.designWidth, extraY = parent.height - parent.designHeight;
  const shiftX = { left: 0, center: extraX / 2, right: extraX, stretch: 0 }[node.ax || 'left'];
  const shiftY = { top: 0, center: extraY / 2, bottom: extraY, stretch: 0 }[node.ay || 'top'];
  element.style.left = `${node.x + shiftX}px`;
  element.style.top = `${node.y + shiftY}px`;
  if (node.w !== undefined) element.style.width = `${node.w + (node.ax === 'stretch' ? extraX : 0)}px`;
  if (node.h !== undefined) element.style.height = `${node.h + (node.ay === 'stretch' ? extraY : 0)}px`;
}

function textNode(node, scope) {
  const element = document.createElement('div');
  element.className = `text style-${node.style || 'body'}`;
  element.textContent = fill(node.text, scope);
  if (node.align) element.style.textAlign = node.align;
  if (node.lines) { element.style.webkitLineClamp = node.lines; element.classList.add('clamp'); }
  if (node.nowrap) element.classList.add('nowrap');
  return element;
}

function run(action, scope) {
  if (!action) return;
  if (action.select) state.selection[action.select] = scope.index;
  if (action.tab) state.tab[action.tab] = action.value;
  if (action.open) state.dialog = { name: action.open, scope };
  if (action.close) state.dialog = null;
  if (action.goto) { state.screen = action.goto; state.dialog = null; }
  render(Boolean(action.goto));
}

function control(element, node, item, scope, base) {
  const enabled = node.enabled === undefined ? true : Boolean(lookup(node.enabled, scope));
  const resting = !enabled ? 'disabled' : base;
  skin(element, item, resting);
  element.classList.add('control');
  if (!enabled) { element.classList.add('disabled'); element.setAttribute('aria-disabled', 'true'); return; }
  element.tabIndex = 0;
  element.setAttribute('role', 'button');
  const press = () => skin(element, item, 'pressed'), release = () => skin(element, item, resting);
  element.addEventListener('pointerdown', press);
  element.addEventListener('pointerup', release);
  element.addEventListener('pointerleave', release);
  element.addEventListener('focus', () => element.classList.add('focus'));
  element.addEventListener('blur', () => element.classList.remove('focus'));
  element.addEventListener('click', () => run(node.action, scope));
  element.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); run(node.action, scope); } });
}

const builders = {
  slice(node, scope) {
    const element = document.createElement('div');
    skin(element, asset(node.asset, node), node.state || 'normal');
    return element;
  },
  image(node, scope) {
    const item = asset(fill(node.asset, scope), node);
    const frame = item.clips[node.clip || Object.keys(item.clips)[0]].frames[0];
    return region(document.createElement('div'), item, frame, 0, 0, item.frame_size[0], item.frame_size[1]);
  },
  sprite(node, scope) {                       // plays a manifest clip with the contract's frame formula
    const item = asset(fill(node.asset, scope), node);
    const element = document.createElement('canvas');
    element.width = item.frame_size[0]; element.height = item.frame_size[1];
    state.sprites.push({ element, item, clips: node.clips || [fill(node.clip, scope)], facing: node.facing || 1 });
    return element;
  },
  text: textNode,
  button(node, scope) {
    const element = document.createElement('div');
    control(element, node, asset(node.asset, node), scope, 'normal');
    const label = document.createElement('span');
    label.className = `text style-${node.style || 'button'} nowrap`;
    label.textContent = fill(node.label, scope);
    element.append(label);
    return element;
  },
  tabs(node, scope) {
    const element = document.createElement('div');
    element.className = 'tabs';
    const current = state.tab[node.key] ?? node.items[0].value;
    for (const entry of node.items) {
      const tab = document.createElement('div');
      tab.style.width = `${node.tab_w}px`; tab.style.height = `${node.h}px`;
      control(tab, { action: { tab: node.key, value: entry.value }, enabled: entry.enabled }, asset(node.asset, node), scope,
              entry.value === current ? 'selected' : 'normal');
      const label = document.createElement('span');
      label.className = 'text style-tab nowrap';
      label.textContent = fill(entry.label, scope);
      tab.append(label);
      element.append(tab);
    }
    return element;
  },
  list(node, scope, parent) {
    const element = document.createElement('div');
    element.className = 'list';
    const rows = visibleRows(node, scope);
    if (!rows.length) {                        // empty state is designed, not accidental
      element.append(textNode({ text: node.empty || '—', style: 'empty', align: 'center' }, scope));
      return element;
    }
    selectedRow(node, scope);
    const width = node.w + (node.ax === 'stretch' ? parent.width - parent.designWidth : 0);
    for (const { item, index } of rows) {
      const rowScope = { ...scope, item, index };
      const row = document.createElement('div');
      row.className = 'row';
      row.style.height = `${node.row_h}px`;
      control(row, { action: { select: node.key }, enabled: node.row_enabled }, asset(node.asset, node), rowScope,
              state.selection[node.key] === index ? 'selected' : 'normal');
      if (state.selection[node.key] === index) row.classList.add('selected');
      // Row children are laid out against the row's outer box, so undo the nine-slice border offset.
      const [left, top] = asset(node.asset, node).stretch;
      const inner = document.createElement('div');
      inner.className = 'row-content';
      inner.style.left = `${-left}px`; inner.style.top = `${-top}px`;
      inner.style.width = `${width - SCROLLBAR}px`; inner.style.height = `${node.row_h}px`;
      const box = { width: width - SCROLLBAR, height: node.row_h, designWidth: node.w - SCROLLBAR, designHeight: node.row_h };
      for (const child of node.row) inner.append(build(child, rowScope, box));
      row.append(inner);
      element.append(row);
    }
    return element;
  },
};

/* Rows a list shows: its items, narrowed by the current tab when it declares a filter. */
function visibleRows(source, scope) {
  const filter = source.filter ? state.tab[source.filter.tab] ?? source.filter.default : null;
  return (lookup(source.items, scope) || []).map((item, index) => ({ item, index }))
    .filter(row => !source.filter || row.item[source.filter.field] === filter);
}
/* Keep a list's selection on a visible row; returns the selected record or null when the list is empty. */
function selectedRow(source, scope) {
  const rows = visibleRows(source, scope);
  if (!rows.length) return null;
  if (!rows.some(row => row.index === state.selection[source.key])) state.selection[source.key] = rows[0].index;
  return rows.find(row => row.index === state.selection[source.key]);
}

function build(node, scope, parent) {
  if (!builders[node.type]) throw new Error(`Unknown node type "${node.type}" in screen "${state.screen}"`);
  if (node.when !== undefined) {                 // "path" shows when truthy, "!path" when falsy
    const negate = node.when.startsWith('!');
    if (Boolean(lookup(node.when.replace(/^!/, ''), scope)) === negate) return document.createComment('hidden');
  }
  const element = builders[node.type](node, scope, parent);
  element.classList.add('node');
  place(element, node, parent);
  return element;
}

function scopeFor(screen) {
  const scope = { ...state.data };
  for (const [name, source] of Object.entries(screen.selected || {})) {       // expose each list's selected record
    scope[name] = selectedRow(source, scope)?.item ?? null;
  }
  return scope;
}

function compose(name, layer, parent, extraScope) {
  const screen = state.flow.screens[name];
  if (!screen) throw new Error(`Flow has no screen "${name}"`);
  const scope = { ...scopeFor(screen), ...(extraScope || {}) };
  if (screen.backdrop) {
    const backdrop = builders.image({ asset: screen.backdrop, type: 'image' }, scope);
    backdrop.classList.add('backdrop');
    layer.append(backdrop);
  }
  for (const node of screen.nodes) layer.append(build(node, scope, parent));
}

function render(transition) {
  const stage = $('stage'), [width, height] = state.viewport.size, [designWidth, designHeight] = state.flow.canvas;
  const parent = { width, height, designWidth, designHeight };
  stage.style.width = `${width}px`; stage.style.height = `${height}px`;
  const scroll = [...stage.querySelectorAll('.list')].map(list => list.scrollTop);
  state.sprites = [];
  const layer = document.createElement('div');
  layer.className = 'layer' + (transition ? ' enter' : '');
  try {
    compose(state.screen, layer, parent);
    if (state.dialog) {
      const veil = document.createElement('div');
      veil.className = 'veil';
      veil.addEventListener('click', event => { if (event.target === veil) run({ close: true }); });
      const modal = document.createElement('div');
      modal.className = 'layer dialog';
      compose(state.dialog.name, modal, parent, state.dialog.scope);
      veil.append(modal);
      layer.append(veil);
    }
    $('status').className = ''; $('status').textContent = `${state.flow.title} · ${state.screen}${state.dialog ? ' › ' + state.dialog.name : ''} · ${width}×${height}`;
  } catch (error) {
    $('status').className = 'error'; $('status').textContent = `Cannot compose screen: ${error.message}`;
  }
  stage.replaceChildren(layer);
  [...stage.querySelectorAll('.list')].forEach((list, index) => { if (!transition && scroll[index]) list.scrollTop = scroll[index]; });
  fit();
}

function fit() {                               // show the device frame whole, at integer-free scale
  const [width, height] = state.viewport.size;
  const room = $('frame').parentElement.clientWidth - 2;
  const scale = Math.min(1, room / width);
  $('stage').style.transform = `scale(${scale})`;
  $('frame').style.width = `${width * scale}px`; $('frame').style.height = `${height * scale}px`;
}

function tick(now) {
  const elapsed = now - state.started;
  for (const sprite of state.sprites) {
    const durations = sprite.clips.map(name => { const clip = sprite.item.clips[name]; return clip.frames.length * 1000 / clip.fps * (clip.loop ? 3 : 1); });
    let time = elapsed % durations.reduce((a, b) => a + b, 0), index = 0;
    while (time >= durations[index]) time -= durations[index++];
    const clip = sprite.item.clips[sprite.clips[index]];
    const step = Math.floor(time * clip.fps / 1000);
    const frame = clip.frames[clip.loop ? step % clip.frames.length : Math.min(step, clip.frames.length - 1)];
    const [fw, fh] = sprite.item.frame_size, columns = sprite.item.size[0] / fw;
    const ctx = sprite.element.getContext('2d');
    ctx.clearRect(0, 0, fw, fh);
    ctx.drawImage(sprite.item.image, (frame % columns) * fw, Math.floor(frame / columns) * fh, fw, fh, 0, 0, fw, fh);
  }
  requestAnimationFrame(tick);
}

async function load() {
  $('status').className = ''; $('status').textContent = 'Checking batch and loading flow…';
  try {
    const root = new URL('../', location.href);
    const check = new URL('api/validate', root);
    check.searchParams.set('manifest', $('manifest').value);
    const validated = await getJson(check);
    const base = new URL($('manifest').value, root);
    const loaded = await Promise.all(validated.manifest.assets.map(item => new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve({ ...item, image, url: image.src });
      image.onerror = () => reject(new Error(`Cannot load ${item.file}`));
      image.src = new URL(item.file, base);
    })));
    state.assets = new Map(loaded.map(item => [item.id, item]));
    const flowUrl = new URL($('flow').value, root);
    state.flow = await getJson(flowUrl);
    state.data = await getJson(new URL(state.flow.data, flowUrl));
    state.screen = state.flow.start; state.dialog = null; state.selection = {}; state.tab = {};
    $('viewport').replaceChildren(...state.flow.viewports.map((viewport, index) => new Option(`${viewport.label} · ${viewport.size.join('×')}`, index)));
    state.viewport = state.flow.viewports[0];
    $('screens').replaceChildren(...Object.entries(state.flow.screens).filter(([, screen]) => !screen.modal)
      .map(([name, screen]) => { const button = document.createElement('button'); button.textContent = screen.title || name;
        button.onclick = () => run({ goto: name }); return button; }));
    render(true);
  } catch (error) {
    $('stage').replaceChildren();
    $('status').className = 'error'; $('status').textContent = `Load failed: ${error.message}`;
  }
}

$('loader').addEventListener('submit', event => { event.preventDefault(); load(); });
$('viewport').addEventListener('change', event => { state.viewport = state.flow.viewports[event.target.value]; render(false); });
window.addEventListener('resize', () => state.viewport && fit());
const query = new URLSearchParams(location.search);
if (query.get('manifest')) $('manifest').value = query.get('manifest');
if (query.get('flow')) $('flow').value = query.get('flow');
load().then(() => {
  if (query.get('viewport') && state.flow) {
    state.viewport = state.flow.viewports[Number(query.get('viewport'))] || state.viewport;
    $('viewport').value = query.get('viewport');
    render(false);
  }
  if (query.get('screen') && state.flow) run({ goto: query.get('screen') });
  if (query.get('tab') && state.flow) { const [key, value] = query.get('tab').split(':'); run({ tab: key, value }); }
  if (query.get('dialog') && state.flow) run({ open: query.get('dialog') });
});
requestAnimationFrame(tick);
