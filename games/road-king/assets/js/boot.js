var __defProp = Object.defineProperty;
var __defProps = Object.defineProperties;
var __getOwnPropDescs = Object.getOwnPropertyDescriptors;
var __getOwnPropSymbols = Object.getOwnPropertySymbols;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __propIsEnum = Object.prototype.propertyIsEnumerable;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __spreadValues = (a, b) => {
  for (var prop in b || (b = {}))
    if (__hasOwnProp.call(b, prop))
      __defNormalProp(a, prop, b[prop]);
  if (__getOwnPropSymbols)
    for (var prop of __getOwnPropSymbols(b)) {
      if (__propIsEnum.call(b, prop))
        __defNormalProp(a, prop, b[prop]);
    }
  return a;
};
var __spreadProps = (a, b) => __defProps(a, __getOwnPropDescs(b));
(function installPlayerSettings() {
  if (window.RoadKingSettings) return;
  var KEY = "drive-player-settings-v1";
  var FEATURES = ["invincible", "cruise", "speed", "density", "motorcycles", "ramps", "rampInterval", "storm", "fog", "snow"];
  var WEATHER = ["storm", "fog", "snow"];
  var DEFAULTS = {
    "display.orientation": "portrait",
    "display.camera": "first",
    "display.controls": "wheel",
    "vehicle": "sedan",
    "audio.bgmVolume": 50,
    "mods.target": 300,
    "mods.density": "normal",
    "mods.rampInterval": 1e3,
    "controlLayout.portrait": {},
    "controlLayout.landscape": {},
    "assistant.positions.portrait": null,
    "assistant.positions.landscape": null
  };
  FEATURES.forEach(function(k) {
    DEFAULTS["mods.on." + k] = false;
    DEFAULTS["unlocks." + k] = false;
  });
  var fields = {}, listeners = [], clock = 1;
  var writer = Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
  var storageState = { persistent: false, session: false, mode: "memory" };
  function own(o, k) {
    return Object.prototype.hasOwnProperty.call(o, k);
  }
  function object(v) {
    return v !== null && typeof v === "object" && !Array.isArray(v);
  }
  function copy(v) {
    return JSON.parse(JSON.stringify(v));
  }
  function equal(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
  }
  function numeric(v, min, max) {
    if (typeof v !== "number" && !(typeof v === "string" && v.trim() !== "")) return void 0;
    var n = Number(v);
    return isFinite(n) ? Math.max(min, Math.min(max, n)) : void 0;
  }
  function normalize(k, v) {
    if (!own(DEFAULTS, k)) return void 0;
    var allowed = {
      "display.orientation": ["portrait", "landscape"],
      "display.camera": ["first", "third"],
      "display.controls": ["wheel", "buttons"],
      vehicle: ["sedan", "motorcycle", "truck"],
      "mods.density": ["empty", "sparse", "normal", "dense"]
    };
    if (allowed[k]) return allowed[k].indexOf(v) >= 0 ? v : void 0;
    if (k === "audio.bgmVolume") return numeric(v, 0, 100);
    if (k === "mods.target") return numeric(v, 0, 300);
    if (k === "mods.rampInterval") return numeric(v, 200, 2e3);
    if (k.indexOf("mods.on.") === 0 || k.indexOf("unlocks.") === 0) return typeof v === "boolean" ? v : void 0;
    if (k.indexOf("controlLayout.") === 0) {
      if (!object(v)) return void 0;
      var layout = {};
      Object.keys(v).forEach(function(id) {
        var p = v[id];
        if (!/^[a-z-]+$/.test(id) || !object(p) || typeof p.x !== "number" || typeof p.y !== "number" || typeof p.scale !== "number" || !isFinite(p.x) || !isFinite(p.y) || !isFinite(p.scale)) return;
        layout[id] = { x: Math.max(0, Math.min(1, p.x)), y: Math.max(0, Math.min(1, p.y)), scale: Math.max(0.5, Math.min(1.8, p.scale)) };
      });
      return layout;
    }
    if (k.indexOf("assistant.positions.") === 0) {
      if (v === null) return null;
      if (!object(v) || typeof v.x !== "number" || typeof v.y !== "number" || !isFinite(v.x) || !isFinite(v.y)) return void 0;
      return { x: Math.max(0, Math.min(1, v.x)), y: Math.max(0, Math.min(1, v.y)) };
    }
  }
  function read(name, key) {
    try {
      return window[name].getItem(key);
    } catch (_) {
      return null;
    }
  }
  function parse(raw) {
    try {
      return JSON.parse(raw);
    } catch (_) {
      return null;
    }
  }
  function put(name, key, value2) {
    try {
      var s = window[name];
      s.setItem(key, value2);
      return s.getItem(key) === value2;
    } catch (_) {
      return false;
    }
  }
  function sectionOf(k) {
    return k.split(".")[0];
  }
  function merge(raw) {
    var doc = parse(raw), changed = [];
    if (!object(doc) || doc.version !== 1 || !object(doc.fields)) return changed;
    Object.keys(doc.fields).forEach(function(k) {
      var r = doc.fields[k];
      if (!object(r) || !own(DEFAULTS, k)) return;
      var v = normalize(k, r.v);
      if (v === void 0 || typeof r.t !== "number" || !isFinite(r.t) || r.t < 1 || r.t > Number.MAX_SAFE_INTEGER - 1e3 || Math.floor(r.t) !== r.t || typeof r.s !== "string" || r.s.length > 120) return;
      var old = fields[k];
      if (k.indexOf("unlocks.") === 0 && old && old.v === true && v !== true) return;
      if (!old || k.indexOf("unlocks.") === 0 && v === true && old.v !== true || r.t > old.t || r.t === old.t && r.s > old.s) {
        fields[k] = { v, t: r.t, s: r.s };
        clock = Math.max(clock, r.t);
        if (!old || !equal(old.v, v)) changed.push(sectionOf(k));
      }
    });
    return changed;
  }
  function value(k) {
    return own(fields, k) ? copy(fields[k].v) : copy(DEFAULTS[k]);
  }
  function snapshot() {
    var out = {
      display: { orientation: value("display.orientation"), camera: value("display.camera"), controls: value("display.controls") },
      controlLayout: { portrait: value("controlLayout.portrait"), landscape: value("controlLayout.landscape") },
      vehicle: value("vehicle"),
      audio: { bgmVolume: value("audio.bgmVolume") },
      mods: { on: {}, target: value("mods.target"), density: value("mods.density"), rampInterval: value("mods.rampInterval") },
      unlocks: {},
      assistant: { positions: {}, weather: [] }
    };
    FEATURES.forEach(function(k) {
      out.mods.on[k] = value("mods.on." + k);
      if (value("unlocks." + k) === true) out.unlocks[k] = true;
    });
    ["portrait", "landscape"].forEach(function(k) {
      var p = value("assistant.positions." + k);
      if (p) out.assistant.positions[k] = p;
    });
    out.assistant.weather = WEATHER.filter(function(k) {
      return out.mods.on[k] === true && out.unlocks[k] === true;
    });
    return out;
  }
  function emit(sections, reason) {
    if (!sections.length) return;
    var unique = sections.filter(function(k, i, a) {
      return a.indexOf(k) === i;
    });
    listeners.slice().forEach(function(fn) {
      try {
        fn({ sections: unique, reason });
      } catch (e) {
        if (window.console) window.console.error(e);
      }
    });
  }
  function mergeAvailable() {
    return merge(read("localStorage", KEY)).concat(merge(read("sessionStorage", KEY)));
  }
  function persist() {
    if (!Object.keys(fields).length) return;
    var json = JSON.stringify({ version: 1, fields });
    storageState.persistent = put("localStorage", KEY, json);
    storageState.session = put("sessionStorage", KEY, json);
    storageState.mode = storageState.persistent ? "persistent" : storageState.session ? "session" : "memory";
  }
  function mirror(sections) {
    var s = snapshot(), map = {
      display: ["drive-display-settings", JSON.stringify(s.display)],
      vehicle: ["drive-vehicle", s.vehicle],
      audio: ["drive-bgm-volume", String(s.audio.bgmVolume)],
      mods: ["drive-233-mod-runtime", JSON.stringify({ on: s.mods.on, target: s.mods.target, density: s.mods.density, rampInterval: s.mods.rampInterval })],
      unlocks: ["drive-233-ad-unlocked-v1", JSON.stringify(s.unlocks)],
      assistant: ["drive-233-assistant-position", JSON.stringify(s.assistant.positions)]
    };
    sections.filter(function(k, i, a) {
      return a.indexOf(k) === i;
    }).forEach(function(k) {
      if (!map[k]) return;
      ["localStorage", "sessionStorage"].forEach(function(n) {
        put(n, map[k][0], map[k][1]);
      });
    });
    if (sections.indexOf("mods") >= 0 || sections.indexOf("unlocks") >= 0) {
      ["localStorage", "sessionStorage"].forEach(function(n) {
        put(n, "drive-233-assistant-settings", JSON.stringify({ weather: s.assistant.weather }));
      });
    }
  }
  function flush() {
    var changed = mergeAvailable();
    persist();
    emit(changed, "external");
    return copy(storageState);
  }
  function commit(patch, reason) {
    var changed = mergeAvailable(), t = Math.max(Date.now(), clock + 1), touched = [];
    Object.keys(patch).forEach(function(k) {
      var v = normalize(k, patch[k]);
      if (v === void 0) return;
      if (fields[k] && equal(fields[k].v, v)) return;
      fields[k] = { v: copy(v), t, s: writer };
      clock = t;
      touched.push(sectionOf(k));
    });
    if (touched.length) {
      persist();
      mirror(touched);
    }
    emit(changed.concat(touched), reason || "selection");
    return snapshot();
  }
  function set(section, patch) {
    var p = {};
    if (section === "vehicle") p.vehicle = patch;
    else if (section === "display" && object(patch)) ["orientation", "camera", "controls"].forEach(function(k) {
      if (own(patch, k)) p["display." + k] = patch[k];
    });
    else if (section === "audio" && object(patch) && own(patch, "bgmVolume")) p["audio.bgmVolume"] = patch.bgmVolume;
    else if (section === "controlLayout" && object(patch)) ["portrait", "landscape"].forEach(function(k) {
      if (own(patch, k)) p["controlLayout." + k] = patch[k];
    });
    else if (section === "mods" && object(patch)) {
      ["target", "density", "rampInterval"].forEach(function(k) {
        if (own(patch, k)) p["mods." + k] = patch[k];
      });
      if (object(patch.on)) FEATURES.forEach(function(k) {
        if (own(patch.on, k)) p["mods.on." + k] = patch.on[k];
      });
    } else if (section === "assistant" && object(patch) && object(patch.positions)) {
      ["portrait", "landscape"].forEach(function(k) {
        if (own(patch.positions, k)) p["assistant.positions." + k] = patch.positions[k];
      });
    }
    return commit(p, "selection");
  }
  function grantReward(feature, result) {
    if (FEATURES.indexOf(feature) < 0 || !result || result.success !== true || result.status !== 4 || result.mocked) return false;
    var p = {};
    p["unlocks." + feature] = true;
    p["mods.on." + feature] = true;
    commit(p, "reward");
    return true;
  }
  mergeAvailable();
  var legacy = {};
  function legacyField(k, v) {
    var n = normalize(k, v);
    if (n !== void 0) legacy[k] = n;
  }
  ["localStorage", "sessionStorage"].forEach(function(n) {
    var display = parse(read(n, "drive-display-settings"));
    if (object(display)) ["orientation", "camera", "controls"].forEach(function(k) {
      legacyField("display." + k, display[k]);
    });
    legacyField("vehicle", read(n, "drive-vehicle"));
    legacyField("audio.bgmVolume", read(n, "drive-bgm-volume"));
    var u = parse(read(n, "drive-233-ad-unlocked-v1"));
    if (object(u)) FEATURES.forEach(function(k) {
      if (u[k] === true) legacyField("unlocks." + k, true);
    });
    var m = parse(read(n, "drive-233-mod-runtime"));
    if (object(m)) {
      ["target", "density", "rampInterval"].forEach(function(k) {
        legacyField("mods." + k, m[k]);
      });
      if (object(m.on)) FEATURES.forEach(function(k) {
        legacyField("mods.on." + k, m.on[k]);
      });
    }
    var pos = parse(read(n, "drive-233-assistant-position"));
    if (object(pos)) ["portrait", "landscape"].forEach(function(k) {
      legacyField("assistant.positions." + k, pos[k]);
    });
  });
  ["localStorage", "sessionStorage"].forEach(function(n) {
    var w = parse(read(n, "drive-233-assistant-settings"));
    if (object(w) && Array.isArray(w.weather)) WEATHER.forEach(function(k) {
      if (!own(legacy, "mods.on." + k) && w.weather.indexOf(k) >= 0) legacyField("mods.on." + k, true);
    });
  });
  Object.keys(legacy).forEach(function(k) {
    if (!own(fields, k)) fields[k] = { v: legacy[k], t: 1, s: "legacy" };
  });
  if (Object.keys(fields).length) persist();
  window.RoadKingSettings = {
    version: 1,
    key: KEY,
    get: function(section) {
      var s = snapshot();
      return section ? copy(s[section]) : s;
    },
    set,
    grantReward,
    flush,
    status: function() {
      return copy(storageState);
    },
    subscribe: function(fn) {
      if (typeof fn !== "function") return function() {
      };
      listeners.push(fn);
      return function() {
        var i = listeners.indexOf(fn);
        if (i >= 0) listeners.splice(i, 1);
      };
    }
  };
  window.addEventListener("storage", function(e) {
    if (e.key === KEY) {
      var changed = merge(e.newValue).concat(mergeAvailable());
      persist();
      emit(changed, "external");
    }
  });
  window.addEventListener("pagehide", flush);
  window.addEventListener("pageshow", flush);
  window.addEventListener("game-home-restored", flush);
  document.addEventListener("visibilitychange", flush);
})();
(function install() {
  var root = document.documentElement;
  var gapProbe = document.createElement("div");
  gapProbe.style.cssText = "position:absolute;visibility:hidden;display:flex;flex-direction:column;row-gap:1px;";
  gapProbe.appendChild(document.createElement("div"));
  gapProbe.appendChild(document.createElement("div"));
  document.body.appendChild(gapProbe);
  root.setAttribute("data-flex-gap", gapProbe.scrollHeight === 1 ? "true" : "false");
  gapProbe.remove();
  var settings = window.RoadKingSettings;
  var displayOptions = { orientation: ["portrait", "landscape"], camera: ["first", "third"], controls: ["wheel", "buttons"] };
  var displayValues = settings.get("display");
  var autoOrientation = window.RoadKingToyAutoOrientation && window.RoadKingToyAutoOrientation();
  if (autoOrientation) displayValues.orientation = autoOrientation;
  function syncDisplaySettings() {
    displayValues = settings.get("display");
    var autoOrientation2 = window.RoadKingToyAutoOrientation && window.RoadKingToyAutoOrientation();
    if (autoOrientation2) displayValues.orientation = autoOrientation2;
    Object.keys(displayValues).forEach(function(key) {
      root.setAttribute("data-" + key, displayValues[key]);
    });
    if (root.getAttribute("data-story-mode") === "story-3") root.setAttribute("data-camera", "third");
    var summary = document.getElementById("settings-summary");
    if (summary) summary.textContent = (displayValues.orientation === "landscape" ? "\u6A2A\u5C4F" : "\u7AD6\u5C4F") + " \xB7 " + (displayValues.camera === "third" ? "\u7B2C\u4E09\u4EBA\u79F0" : "\u7B2C\u4E00\u4EBA\u79F0") + " \xB7 " + (displayValues.controls === "buttons" ? "\u6309\u952E" : "\u65B9\u5411\u76D8");
    document.querySelectorAll(".drive-preferences button").forEach(function(button) {
      Object.keys(displayOptions).forEach(function(key) {
        if (button.hasAttribute("data-" + key)) button.setAttribute("aria-pressed", String(button.getAttribute("data-" + key) === displayValues[key]));
      });
    });
  }
  function saveDisplaySettings() {
    var value = Object.assign({}, displayValues);
    if (window.RoadKingToyAutoOrientation && window.RoadKingToyAutoOrientation()) value.orientation = settings.get("display").orientation;
    settings.set("display", value);
  }
  syncDisplaySettings();
  function setMusic(value) {
    root.setAttribute("data-bgm-volume", String(value));
    var slider = document.getElementById("bgm-volume"), output = document.getElementById("bgm-volume-value");
    if (slider) slider.value = String(value);
    if (output) output.textContent = String(value);
  }
  setMusic(settings.get("audio").bgmVolume);
  document.addEventListener("input", function(e) {
    if (e.target.id !== "bgm-volume") return;
    var value = Math.max(0, Math.min(100, Number(e.target.value)));
    settings.set("audio", { bgmVolume: value });
  });
  var settingsReturn, settingsKeyboard = false;
  function closeSettings() {
    var overlay = document.querySelector(".game-settings-overlay");
    if (!overlay) return;
    overlay.hidden = true;
    var menu = document.getElementById("mode-screen");
    if (menu) {
      menu.removeAttribute("aria-hidden");
      menu.inert = false;
    }
    if (settingsKeyboard && settingsReturn) settingsReturn.focus({ preventScroll: true });
  }
  document.addEventListener("click", function(e) {
    if (e.target.closest && e.target.closest(".game-settings-open")) {
      var overlay = document.querySelector(".game-settings-overlay");
      if (!overlay) return;
      settingsReturn = e.target.closest(".game-settings-open");
      settingsKeyboard = e.detail === 0;
      document.body.appendChild(overlay);
      overlay.hidden = false;
      var menu = document.getElementById("mode-screen");
      if (menu) {
        menu.setAttribute("aria-hidden", "true");
        menu.inert = true;
      }
      if (settingsKeyboard) overlay.querySelector("[data-settings-close]").focus({ preventScroll: true });
    } else if (e.target.closest && e.target.closest("[data-settings-close]") || e.target.classList.contains("game-settings-overlay")) closeSettings();
  });
  document.addEventListener("keydown", function(e) {
    var overlay = document.querySelector(".game-settings-overlay");
    if (!overlay || overlay.hidden) return;
    if (e.key === "Escape") {
      e.preventDefault();
      closeSettings();
    } else if (e.key === "Tab") {
      var items = overlay.querySelectorAll("button,input");
      var first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus({ preventScroll: true });
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus({ preventScroll: true });
      }
    }
  });
  function fitHome(width, height, land) {
    var menu = document.getElementById("mode-screen"), content = menu && menu.querySelector(".mode-content");
    if (!content || getComputedStyle(menu).display === "none") return;
    var frame = menu.querySelector(".home-fit-frame");
    if (!frame) {
      frame = document.createElement("div");
      frame.className = "home-fit-frame";
      menu.insertBefore(frame, content);
      frame.appendChild(content);
    }
    var style = getComputedStyle(menu);
    var availableWidth = width - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    var availableHeight = height - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
    var designWidth = land ? Math.max(640, Math.min(980, availableWidth)) : Math.max(320, Math.min(420, availableWidth));
    content.style.width = designWidth + "px";
    content.style.transform = "none";
    var scale = Math.max(0.1, Math.min(1, availableWidth / designWidth, availableHeight / content.offsetHeight));
    frame.style.width = designWidth * scale + "px";
    frame.style.height = content.offsetHeight * scale + "px";
    content.style.transform = "scale(" + scale + ")";
  }
  var timer;
  function apply() {
    var viewport = window.RoadKingToyViewport;
    var w = viewport ? viewport.width : root.clientWidth || window.innerWidth, h = viewport ? viewport.height : root.clientHeight || window.innerHeight;
    if (!(w > 0 && h > 0)) return;
    syncDisplaySettings();
    var land = root.getAttribute("data-orientation") === "landscape";
    var rotate = land ? w < h : w > h;
    var width = rotate ? h : w, height = rotate ? w : h;
    root.style.setProperty("--aux-portrait-top", Math.max(146, height * 0.25) + "px");
    root.setAttribute("data-rotated", rotate ? "true" : "false");
    root.setAttribute("data-menu-compact", height < 650 ? "true" : "false");
    root.setAttribute("data-menu-tight", height < (land ? 340 : 460) ? "true" : "false");
    root.style.setProperty("--screen-width", width + "px");
    root.style.setProperty("--screen-height", height + "px");
    document.body.style.width = width + "px";
    document.body.style.height = height + "px";
    document.body.style.setProperty("--app-height", height + "px");
    document.body.style.setProperty("--app-width", width + "px");
    document.body.style.transform = rotate ? "translateX(" + w + "px) rotate(90deg)" : "rotate(0deg)";
    fitHome(width, height, land);
    window.dispatchEvent(new Event("game-layout-change"));
  }
  document.addEventListener("click", function(e) {
    var b = e.target.closest && e.target.closest(".drive-preferences button");
    if (!b) return;
    var changed = false;
    Object.keys(displayOptions).forEach(function(key) {
      var value = b.getAttribute("data-" + key);
      if (displayOptions[key].indexOf(value) !== -1) {
        displayValues[key] = value;
        changed = true;
      }
    });
    if (!changed) return;
    saveDisplaySettings();
    syncDisplaySettings();
    var orientation = b.getAttribute("data-orientation");
    if (displayOptions.orientation.indexOf(orientation) !== -1) {
      apply();
      try {
        var o = window.screen.orientation;
        if (o && o.lock) {
          var p = o.lock(orientation);
          if (p && p.catch) p.catch(function() {
          });
        }
      } catch (_) {
      }
    }
  });
  window.addEventListener("resize", function() {
    clearTimeout(timer);
    timer = setTimeout(apply, 50);
  });
  if (window.visualViewport) window.visualViewport.addEventListener("resize", function() {
    clearTimeout(timer);
    timer = setTimeout(apply, 50);
  });
  window.addEventListener("orientationchange", function() {
    apply();
    setTimeout(apply, 300);
  });
  function restoreHomeLayout() {
    closeSettings();
    syncDisplaySettings();
    setMusic(settings.get("audio").bgmVolume);
    settings.flush();
    apply();
  }
  settings.subscribe(function(change) {
    if (change.sections.indexOf("display") >= 0) {
      syncDisplaySettings();
      apply();
    }
    if (change.sections.indexOf("audio") >= 0) {
      setMusic(settings.get("audio").bgmVolume);
      window.dispatchEvent(new Event("bgm-volume-change"));
    }
  });
  window.addEventListener("game-home-restored", restoreHomeLayout);
  window.addEventListener("pageshow", function() {
    syncDisplaySettings();
    setMusic(settings.get("audio").bgmVolume);
    apply();
  });
  document.addEventListener("visibilitychange", function() {
    if (!document.hidden) apply();
  });
  if (window.ResizeObserver) {
    var sizeObserver = new ResizeObserver(function() {
      clearTimeout(timer);
      timer = setTimeout(apply, 50);
    });
    sizeObserver.observe(root);
  }
  apply();
})();
(function install2() {
  var root = document.documentElement, names = { sedan: "\u8F7F\u8F66", motorcycle: "\u6469\u6258\u8F66", truck: "\u5927\u8FD0\u91CD\u5361" }, selected = "sedan", draft = "sedan", returnTo, keyboardOpen = false;
  var settings = window.RoadKingSettings;
  selected = settings.get("vehicle");
  root.setAttribute("data-vehicle", selected);
  function updateHome() {
    selected = settings.get("vehicle");
    root.setAttribute("data-vehicle", root.getAttribute("data-story-mode") === "story-3" ? "motorcycle" : root.getAttribute("data-story-mode") === "story-1" ? "sedan" : selected);
    var name = document.querySelector(".home-vehicle strong");
    if (name) name.textContent = names[selected];
  }
  settings.subscribe(function(change) {
    if (change.sections.indexOf("vehicle") >= 0) updateHome();
  });
  window.addEventListener("game-home-restored", function() {
    close();
    updateHome();
    draft = selected;
    paint();
  });
  window.addEventListener("pageshow", updateHome);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", updateHome);
  else updateHome();
  function paint() {
    var host = document.getElementById("garage-render");
    if (host) host.setAttribute("data-vehicle", draft);
    window.dispatchEvent(new Event("garage-vehicle-changed"));
    document.querySelectorAll("[data-garage-car]").forEach(function(e) {
      e.hidden = e.getAttribute("data-garage-car") !== draft;
    });
    document.querySelectorAll("[data-choose-vehicle]").forEach(function(e) {
      e.setAttribute("aria-pressed", String(e.getAttribute("data-choose-vehicle") === draft));
    });
  }
  function close() {
    window.dispatchEvent(new Event("garage-closed"));
    var overlay = document.querySelector(".garage-overlay");
    if (overlay) overlay.hidden = true;
    var menu = document.getElementById("mode-screen");
    if (menu) {
      menu.inert = false;
      menu.removeAttribute("aria-hidden");
    }
    if (keyboardOpen && returnTo) returnTo.focus({ preventScroll: true });
  }
  document.addEventListener("click", function(e) {
    var t = e.target.closest && e.target.closest("button");
    if (t && t.classList.contains("garage-preview")) {
      var overlay = document.querySelector(".garage-overlay");
      document.body.appendChild(overlay);
      draft = selected;
      paint();
      returnTo = t;
      keyboardOpen = e.detail === 0;
      overlay.hidden = false;
      window.dispatchEvent(new Event("garage-opened"));
      var menu = document.getElementById("mode-screen");
      menu.inert = true;
      menu.setAttribute("aria-hidden", "true");
      if (keyboardOpen) overlay.querySelector("[data-garage-close]").focus({ preventScroll: true });
    } else if (t && t.hasAttribute("data-choose-vehicle")) {
      draft = t.getAttribute("data-choose-vehicle");
      paint();
    } else if (t && t.classList.contains("garage-confirm")) {
      settings.set("vehicle", draft);
      selected = settings.get("vehicle");
      root.setAttribute("data-vehicle", selected);
      updateHome();
      close();
    } else if (t && t.hasAttribute("data-garage-close") || e.target.classList.contains("garage-overlay")) close();
  });
  document.addEventListener("keydown", function(e) {
    var overlay = document.querySelector(".garage-overlay");
    if (!overlay || overlay.hidden) return;
    if (e.key === "Escape") {
      e.preventDefault();
      close();
    }
    if (e.key === "Tab") {
      var items = overlay.querySelectorAll("button"), first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus({ preventScroll: true });
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus({ preventScroll: true });
      }
    }
  });
})();
(function install3(catalog) {
  if (window.RoadKingStory) return;
  var root = document.documentElement;
  var phase = "home", current = null, lastSelected = null;
  function node(id) {
    return document.getElementById(id);
  }
  function findStory(id) {
    for (var i = 0; i < catalog.length; i++) if (catalog[i].id === id) return catalog[i];
    return null;
  }
  function focus(element) {
    if (!element || !element.focus) return;
    try {
      element.focus({ preventScroll: true });
    } catch (_) {
      element.focus();
    }
  }
  function emit(name, detail) {
    var event;
    if (typeof window.CustomEvent === "function") event = new CustomEvent(name, { detail });
    else {
      event = document.createEvent("CustomEvent");
      event.initCustomEvent(name, false, false, detail);
    }
    window.dispatchEvent(event);
  }
  function lockHome(locked) {
    var home = node("mode-screen"), button = document.querySelector("[data-story-open]");
    if (home) {
      home.inert = locked;
      if (locked) home.setAttribute("aria-hidden", "true");
      else home.removeAttribute("aria-hidden");
    }
    if (button) button.setAttribute("aria-expanded", String(phase === "selection"));
  }
  function exitCurrent() {
    if (!current) return;
    var previous = current;
    current = null;
    emit("game-story-exited", { id: previous.id, title: previous.title });
  }
  function otherDialogOpen() {
    var settings = document.querySelector(".game-settings-overlay"), garage = document.querySelector(".garage-overlay");
    return settings && !settings.hidden || garage && !garage.hidden;
  }
  function openSelection() {
    if (root.hasAttribute("data-game-mode") || otherDialogOpen()) return false;
    var overlay = node("story-selection"), scene = node("story-scene");
    if (!overlay || !scene) return false;
    exitCurrent();
    phase = "selection";
    root.removeAttribute("data-story-mode");
    scene.hidden = true;
    overlay.hidden = false;
    focus(lastSelected ? overlay.querySelector('[data-story-selection="' + lastSelected + '"]') : overlay.querySelector("[data-story-close]"));
    lockHome(true);
    return true;
  }
  function enter(id) {
    var story = findStory(id), overlay = node("story-selection"), scene = node("story-scene");
    if (!story || phase !== "selection" || root.hasAttribute("data-game-mode") || !overlay || !scene) return false;
    current = story;
    lastSelected = story.id;
    phase = "story";
    node("story-scene-title").textContent = story.title;
    node("story-scene-number").textContent = story.number;
    root.setAttribute("data-story-mode", story.id);
    overlay.hidden = true;
    scene.hidden = false;
    focus(node("story-scene-title"));
    lockHome(true);
    emit("game-story-selected", { id: story.id, title: story.title, containerId: "story-scene-content" });
    return true;
  }
  function reset(restoreFocus) {
    if (phase === "home") return false;
    exitCurrent();
    phase = "home";
    var overlay = node("story-selection"), scene = node("story-scene");
    if (overlay) overlay.hidden = true;
    if (scene) scene.hidden = true;
    root.removeAttribute("data-story-mode");
    lockHome(false);
    if (restoreFocus) focus(document.querySelector("[data-story-open]"));
    return true;
  }
  function returnHome() {
    if (reset(true)) window.dispatchEvent(new Event("game-home-restored"));
  }
  document.addEventListener("click", function(e) {
    var target = e.target, button = target && target.closest && target.closest("button");
    if (button && button.hasAttribute("data-story-open")) openSelection();
    else if (button && button.hasAttribute("data-story-selection") && phase === "selection") enter(button.getAttribute("data-story-selection"));
    else if (button && button.hasAttribute("data-story-back") && phase === "story") openSelection();
    else if (button && (button.hasAttribute("data-story-close") || button.hasAttribute("data-story-home")) || target === node("story-selection") && phase === "selection") returnHome();
  });
  document.addEventListener("click", function(e) {
    if (phase === "home") return;
    var home = node("mode-screen");
    if (home && home.contains(e.target)) {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  }, true);
  document.addEventListener("keydown", function(e) {
    if (phase === "home" || root.hasAttribute("data-game-mode")) return;
    if (e.key === "Escape") {
      e.preventDefault();
      if (phase === "story") openSelection();
      else returnHome();
      return;
    }
    if (e.key !== "Tab") return;
    var host = phase === "story" ? node("story-scene") : node("story-selection");
    var buttons = host.querySelectorAll("button:not([disabled])");
    if (!buttons.length) return;
    var first = buttons[0], last = buttons[buttons.length - 1], active = document.activeElement;
    if (e.shiftKey && (active === first || !host.contains(active) || active.tagName !== "BUTTON")) {
      e.preventDefault();
      focus(last);
    } else if (!e.shiftKey && (active === last || !host.contains(active))) {
      e.preventDefault();
      focus(first);
    }
  });
  window.addEventListener("game-home-restored", function() {
    reset(false);
  });
  window.addEventListener("game-return-home", function() {
    reset(false);
  });
  window.addEventListener("game-mode-selected", function() {
    reset(false);
  });
  window.RoadKingStory = {
    openSelection,
    enter,
    returnHome,
    getState: function() {
      return { phase, storyId: current ? current.id : null };
    },
    list: function() {
      return catalog.map(function(story) {
        return { id: story.id, title: story.title };
      });
    }
  };
})([{ "id": "story-1", "title": "\u8F7F\u8F66\u7BC7", "number": "01" }, { "id": "story-2", "title": "\u5361\u8F66\u7BC7", "number": "02" }, { "id": "story-3", "title": "\u6469\u6258\u8F66\u7BC7", "number": "03" }]);
(function install5() {
  var overlay = document.getElementById("update-notice");
  var confirm = document.getElementById("update-notice-confirm");
  var menu = document.getElementById("mode-screen");
  var content = overlay && overlay.querySelector(".update-notice-content");
  var closed = false, failures = 0, timer;
  function unlock() {
    if (menu) {
      menu.inert = false;
      menu.removeAttribute("aria-hidden");
    }
  }
  function close() {
    if (closed) return;
    closed = true;
    if (overlay) overlay.hidden = true;
    unlock();
    clearInterval(timer);
    document.removeEventListener("focusin", focusInside, true);
    document.removeEventListener("click", blockBackground, true);
    document.removeEventListener("keydown", keyboard, true);
  }
  if (!overlay || !confirm || !content) {
    close();
    return;
  }
  function usable() {
    if (overlay.hidden || !overlay.isConnected) return false;
    var node = confirm;
    while (node && node !== document.documentElement) {
      var style = window.getComputedStyle(node);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return false;
      node = node.parentElement;
    }
    var r = confirm.getBoundingClientRect(), w = document.documentElement.clientWidth || window.innerWidth, h = document.documentElement.clientHeight || window.innerHeight;
    if (r.width < 16 || r.height < 16 || r.left < 0 || r.top < 0 || r.right > w || r.bottom > h) return false;
    var target = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return !!target && (target === confirm || confirm.contains(target));
  }
  function focusInside(e) {
    if (!usable()) {
      close();
      return;
    }
    if (!overlay.contains(e.target)) confirm.focus({ preventScroll: true });
  }
  function blockBackground(e) {
    if (!usable()) {
      close();
      return;
    }
    if (!overlay.contains(e.target)) {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  }
  function keyboard(e) {
    if (!usable()) {
      close();
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      close();
      return;
    }
    if (e.key === "Tab") {
      e.preventDefault();
      (document.activeElement === confirm ? content : confirm).focus({ preventScroll: true });
    }
    e.stopImmediatePropagation();
  }
  if (menu) {
    menu.inert = true;
    menu.setAttribute("aria-hidden", "true");
  }
  document.addEventListener("focusin", focusInside, true);
  document.addEventListener("click", blockBackground, true);
  document.addEventListener("keydown", keyboard, true);
  confirm.addEventListener("click", close);
  timer = setInterval(function() {
    if (document.hidden || document.readyState !== "complete") return;
    try {
      failures = usable() ? 0 : failures + 1;
    } catch (_) {
      failures++;
    }
    if (failures >= 2) close();
  }, 500);
})();
window.addEventListener("error", function(e) {
  if (e.target && e.target.tagName !== "SCRIPT" && e.target !== window) return;
  var p = document.getElementById("boot-message"), b = document.getElementById("boot-screen");
  if (p) p.textContent = "\u52A0\u8F7D\u672A\u5B8C\u6210\uFF0C\u8BF7\u91CD\u65B0\u6253\u5F00\u6E38\u620F\u3002";
  if (b) b.setAttribute("data-failed", "true");
}, true);
document.addEventListener("click", function(e) {
  var t = e.target;
  while (t && t !== document) {
    if (t.getAttribute && t.getAttribute("data-mode-selection")) break;
    t = t.parentNode;
  }
  if (!t || t === document || document.documentElement.getAttribute("data-game-mode") || document.documentElement.hasAttribute("data-story-mode")) return;
  var m = t.getAttribute("data-mode-selection");
  if (m !== "normal" && m !== "simulation") return;
  document.documentElement.setAttribute("data-game-mode", m);
  var p = document.getElementById("boot-message");
  if (p) p.textContent = "\u6B63\u5728\u51C6\u5907" + (m === "simulation" ? "\u72C2\u66B4" : "\u6B63\u5E38") + "\u6A21\u5F0F\u2026";
  window.dispatchEvent(new Event("game-mode-selected"));
});
