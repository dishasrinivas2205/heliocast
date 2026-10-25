import JSZip from 'jszip';
import confetti from 'canvas-confetti';

// State Management
const state = {
  activePreset: 'aether',
  activeTab: 'edit',
  clickToEdit: true,
  selectedElement: null,
  activePage: 'home',
  viewportMode: 'desktop', // desktop | tablet | mobile
  history: [],
  historyIndex: -1,
  presets: [
    {
      id: 'aether',
      title: 'Aether — Deep Field Survey',
      desc: 'Deep-space planetary survey with scrubbed orbital flyover and telemetry HUD.'
    },
    {
      id: 'volta',
      title: 'Volta — Electric Moped',
      desc: 'Light studio product site with floating UI cards and exploded sequence.'
    },
    {
      id: 'obsidian',
      title: 'The Obsidian Assembly',
      desc: 'Warm editorial archive with stacked deck cards and architectural serif typography.'
    },
    {
      id: 'vanta',
      title: 'Vanta — Model 03 Nocturne',
      desc: 'Cinematic automotive launch with silk dust sheet lift and desert run sequence.'
    }
  ]
};

// 30 Animation Presets definition
const ANIMATIONS = {
  in: [
    'None', 'Fade up', 'Slide in left', 'Fade in', 'Zoom in', 'Bounce in',
    'Flip X', 'Blur in', 'Slide up', 'Slide in right', 'Rotate in', 'Scale up'
  ],
  out: [
    'None', 'Fade down', 'Slide out right', 'Fade out', 'Zoom out', 'Slide down',
    'Blur out', 'Slide out left', 'Rotate out', 'Bounce out'
  ],
  loop: [
    'None', 'Pulse', 'Shimmer', 'Float Bounce', 'Spin Loop', 'Wiggle',
    'Flash Link', 'Heartbeat', 'Sway', 'Glow pulse', 'Soft bounce'
  ]
};

// Font List
const FONTS = [
  { value: 'inherit', label: 'Preset default' },
  { value: "'Space Grotesk', sans-serif", label: 'Space Grotesk' },
  { value: "'Inter', sans-serif", label: 'Inter' },
  { value: "'Outfit', sans-serif", label: 'Outfit' },
  { value: "'Instrument Serif', Georgia, serif", label: 'Instrument Serif' },
  { value: "'Cinzel', serif", label: 'Cinzel' },
  { value: "'Orbitron', sans-serif", label: 'Orbitron' },
  { value: "'Syne', sans-serif", label: 'Syne' },
  { value: "'JetBrains Mono', monospace", label: 'JetBrains Mono' },
  { value: "'Bricolage Grotesque', sans-serif", label: 'Bricolage Grotesque' },
  { value: "'Playfair Display', serif", label: 'Playfair Display' },
  { value: "'Cormorant Garamond', serif", label: 'Cormorant Garamond' },
  { value: "'Manrope', sans-serif", label: 'Manrope' },
  { value: "'Plus Jakarta Sans', sans-serif", label: 'Plus Jakarta Sans' },
  { value: "'Bebas Neue', sans-serif", label: 'Bebas Neue' },
  { value: 'system-ui', label: 'System UI' },
  { value: 'Arial, sans-serif', label: 'Arial' },
  { value: 'Georgia, serif', label: 'Georgia' }
];

// Helper to push history
function recordHistory(description = 'Edit') {
  const container = document.getElementById('preset-preview-canvas');
  if (!container) return;
  const snapshot = container.innerHTML;
  
  // Truncate future if branched
  state.history = state.history.slice(0, state.historyIndex + 1);
  state.history.push({ snapshot, description });
  state.historyIndex = state.history.length - 1;
  updateUndoRedoButtons();
}

function updateUndoRedoButtons() {
  const undoBtn = document.getElementById('btn-undo');
  const redoBtn = document.getElementById('btn-redo');
  if (undoBtn) undoBtn.disabled = state.historyIndex <= 0;
  if (redoBtn) redoBtn.disabled = state.historyIndex >= state.history.length - 1;
}

function showToast(msg, type = 'info') {
  const toastContainer = document.getElementById('toast-container');
  if (!toastContainer) return;
  const toast = document.createElement('div');
  toast.className = `draftly-toast ${type}`;
  toast.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span>${msg}</span>`;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 200);
  }, 2500);
}

// Render Main App Structure
function initApp() {
  const app = document.getElementById('app');
  app.innerHTML = `
    <!-- Top Header -->
    <header class="draftly-header">
      <div class="header-top">
        <div class="header-left">
          <a class="back-link" href="#" title="Back to presets">
            <i class="fa-solid fa-arrow-left"></i>
          </a>
          <div class="preset-title-wrapper">
            <button type="button" class="preset-title-button" id="btn-preset-switcher">
              <span class="preset-title" id="header-preset-title">Aether — Deep Field Survey</span>
              <span class="preset-badge">PRESET</span>
              <i class="fa-solid fa-chevron-down" style="font-size: 10px; opacity: 0.6;"></i>
            </button>
            <!-- Dropdown -->
            <div class="preset-dropdown-menu" id="preset-dropdown">
              ${state.presets.map(p => `
                <div class="preset-dropdown-item ${p.id === state.activePreset ? 'active' : ''}" data-preset-id="${p.id}">
                  <div class="preset-item-title">
                    <span>${p.title}</span>
                    ${p.id === state.activePreset ? '<i class="fa-solid fa-check" style="color: #38bdf8;"></i>' : ''}
                  </div>
                  <div class="preset-item-desc">${p.desc}</div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>

        <div class="header-actions">
          <button type="button" class="tool-btn accent-outline" id="btn-customize">
            <i class="fa-solid fa-sliders"></i>
            <span>Customize</span>
          </button>
          
          <div class="icon-btn-group">
            <button type="button" class="icon-btn" id="btn-undo" title="Undo (Ctrl+Z)" disabled>
              <i class="fa-solid fa-rotate-left"></i>
            </button>
            <button type="button" class="icon-btn" id="btn-redo" title="Redo (Ctrl+Y)" disabled>
              <i class="fa-solid fa-rotate-right"></i>
            </button>
          </div>

          <div class="tool-separator"></div>

          <button type="button" class="tool-btn active-mode" id="btn-mode-edit">
            <i class="fa-solid fa-pen-to-square"></i>
            <span>Edit</span>
          </button>

          <button type="button" class="tool-btn" id="btn-integrations" title="Growth & API vault">
            <i class="fa-solid fa-plug"></i>
            <span>Integrations</span>
          </button>

          <button type="button" class="tool-btn" id="btn-zip-export" title="Download project source code">
            <i class="fa-solid fa-file-zipper"></i>
            <span>ZIP</span>
          </button>

          <button type="button" class="tool-btn primary" id="btn-publish" title="Publish website live">
            <i class="fa-solid fa-rocket"></i>
            <span>Publish</span>
          </button>
        </div>
      </div>

      <!-- Subbar: Page Manager & Viewports -->
      <div class="header-subbar">
        <div class="page-tabs-group">
          <span class="page-badge-label">Active route:</span>
          <button type="button" class="page-tab-pill active" data-page="home">Home</button>
          <button type="button" class="page-tab-pill" data-page="mission">Mission</button>
          <button type="button" class="page-tab-pill" data-page="telemetry">Telemetry</button>
          <button type="button" class="add-page-btn" id="btn-add-page">+ Page</button>
        </div>

        <div class="canvas-viewport-modes">
          <button type="button" class="viewport-btn active" data-viewport="desktop" title="Desktop View (Full)">
            <i class="fa-solid fa-desktop"></i>
          </button>
          <button type="button" class="viewport-btn" data-viewport="tablet" title="Tablet View (768px)">
            <i class="fa-solid fa-tablet-screen-button"></i>
          </button>
          <button type="button" class="viewport-btn" data-viewport="mobile" title="Mobile View (390px)">
            <i class="fa-solid fa-mobile-screen"></i>
          </button>
        </div>
      </div>
    </header>

    <!-- Studio Workspace -->
    <div class="studio-workspace">
      <!-- Left Sidebar Inspector -->
      <aside class="draftly-sidebar" id="sidebar-panel">
        <div class="sidebar-resizer" id="sidebar-resizer">
          <div class="sidebar-resizer-line"></div>
        </div>

        <div class="sidebar-nav-tabs">
          <div class="tabs-grid">
            <button type="button" class="tab-btn" data-tab="build">Build</button>
            <button type="button" class="tab-btn active" data-tab="edit">Edit</button>
            <button type="button" class="tab-btn" data-tab="assets">Assets</button>
            <button type="button" class="tab-btn" data-tab="business">Business</button>
            <button type="button" class="tab-btn" data-tab="publish">Publish</button>
          </div>
        </div>

        <div class="sidebar-content">
          <!-- EDIT TAB -->
          <div class="tab-panel active" id="tab-panel-edit">
            <!-- Click to edit card -->
            <div class="click-to-edit-card" id="btn-toggle-cte">
              <div>
                <div class="cte-title">
                  <i class="fa-solid fa-i-cursor"></i>
                  <span>Click-to-edit on</span>
                </div>
                <div class="cte-desc">Select any text or element in the preview to style</div>
              </div>
              <div class="toggle-switch-track on" id="cte-switch">
                <div class="toggle-switch-thumb"></div>
              </div>
            </div>

            <!-- Text Inspector -->
            <div class="inspector-card">
              <div class="inspector-header">
                <div>
                  <div class="inspector-label">Text Inspector</div>
                  <div class="selected-crumb" id="text-crumb">&lt;section&gt; · ORRIN KESH</div>
                </div>
                <span style="font-size: 10px; color: var(--text-faint);"><i class="fa-solid fa-font"></i></span>
              </div>

              <div class="control-group">
                <label class="control-label">Font Family (${FONTS.length} available)</label>
                <select class="control-select" id="ctrl-font-family">
                  ${FONTS.map(f => `<option value="${f.value}">${f.label}</option>`).join('')}
                </select>
              </div>

              <div class="control-row">
                <div class="control-group">
                  <label class="control-label">Size (px)</label>
                  <input type="number" class="control-input" id="ctrl-font-size" min="8" max="140" value="64" />
                </div>
                <div class="control-group">
                  <label class="control-label">Weight</label>
                  <select class="control-select" id="ctrl-font-weight">
                    <option value="300">300 Light</option>
                    <option value="400">400 Regular</option>
                    <option value="500">500 Medium</option>
                    <option value="600">600 Semibold</option>
                    <option value="700">700 Bold</option>
                    <option value="800">800 Extra Bold</option>
                  </select>
                </div>
              </div>

              <div class="control-group">
                <label class="control-label">Color</label>
                <div class="color-picker-row">
                  <input type="color" class="color-input-swatch" id="ctrl-font-color" value="#ffffff" />
                  <span class="color-hex-text" id="color-hex-display">#ffffff</span>
                  <div class="preset-swatches">
                    <div class="swatch-dot" style="background:#ffffff;" data-color="#ffffff"></div>
                    <div class="swatch-dot" style="background:#38bdf8;" data-color="#38bdf8"></div>
                    <div class="swatch-dot" style="background:#818cf8;" data-color="#818cf8"></div>
                    <div class="swatch-dot" style="background:#f43f5e;" data-color="#f43f5e"></div>
                    <div class="swatch-dot" style="background:#eab308;" data-color="#eab308"></div>
                  </div>
                </div>
              </div>

              <!-- Animate In -->
              <div class="animation-category-block">
                <label class="control-label">Animate In (${ANIMATIONS.in.length} presets)</label>
                <div class="anim-buttons-wrap" id="wrap-anim-in">
                  ${ANIMATIONS.in.map((a, i) => `
                    <button type="button" class="anim-btn ${i === 0 ? 'selected' : ''}" data-anim-type="in" data-anim-val="${slugify(a)}">${a}</button>
                  `).join('')}
                </div>
              </div>

              <!-- Animate Out -->
              <div class="animation-category-block">
                <label class="control-label">Animate Out (${ANIMATIONS.out.length} presets)</label>
                <div class="anim-buttons-wrap" id="wrap-anim-out">
                  ${ANIMATIONS.out.map((a, i) => `
                    <button type="button" class="anim-btn ${i === 0 ? 'selected' : ''}" data-anim-type="out" data-anim-val="${slugify(a)}">${a}</button>
                  `).join('')}
                </div>
              </div>

              <!-- Loop -->
              <div class="animation-category-block">
                <label class="control-label">Loop Animation (${ANIMATIONS.loop.length} presets)</label>
                <div class="anim-buttons-wrap" id="wrap-anim-loop">
                  ${ANIMATIONS.loop.map((a, i) => `
                    <button type="button" class="anim-btn ${i === 0 ? 'selected' : ''}" data-anim-type="loop" data-anim-val="${slugify(a)}">${a}</button>
                  `).join('')}
                </div>
              </div>
            </div>

            <!-- UI Component Inspector -->
            <div class="inspector-card component-card">
              <div class="inspector-header">
                <div>
                  <div class="inspector-label cyan">UI Component</div>
                  <div class="selected-crumb" id="component-crumb">section · AETHER HERO</div>
                </div>
                <span style="font-size: 10px; color: #38bdf8;"><i class="fa-solid fa-shapes"></i></span>
              </div>

              <div class="control-row">
                <div class="control-group">
                  <label class="control-label">Border radius</label>
                  <input type="text" class="control-input" id="ctrl-border-radius" placeholder="16px" value="" />
                </div>
                <div class="control-group">
                  <label class="control-label">Padding</label>
                  <input type="text" class="control-input" id="ctrl-padding" placeholder="24px" value="" />
                </div>
              </div>

              <div class="control-group">
                <label class="control-label">Background</label>
                <input type="text" class="control-input" id="ctrl-background" placeholder="rgba(255,255,255,0.05)" value="" />
              </div>

              <div class="control-row">
                <div class="control-group">
                  <label class="control-label">Move X</label>
                  <input type="text" class="control-input" id="ctrl-move-x" placeholder="0px" value="0px" />
                </div>
                <div class="control-group">
                  <label class="control-label">Move Y</label>
                  <input type="text" class="control-input" id="ctrl-move-y" placeholder="0px" value="0px" />
                </div>
              </div>

              <div class="control-row">
                <div class="control-group">
                  <label class="control-label">Layer (z-index)</label>
                  <input type="number" class="control-input" id="ctrl-z-index" placeholder="10" value="10" />
                </div>
                <div class="control-group">
                  <label class="control-label">Link URL</label>
                  <input type="url" class="control-input" id="ctrl-link-url" placeholder="https://" value="" />
                </div>
              </div>

              <div class="control-group">
                <label class="control-label">Section Animation</label>
                <div class="anim-buttons-wrap">
                  <button type="button" class="anim-btn selected" data-section-anim="none">None</button>
                  <button type="button" class="anim-btn" data-section-anim="anim-fade-up">Fade up</button>
                  <button type="button" class="anim-btn" data-section-anim="anim-slide-up">Slide in</button>
                  <button type="button" class="anim-btn" data-section-anim="anim-scale-up">Scale up</button>
                </div>
              </div>

              <button type="button" class="reapply-btn" id="btn-reapply-styles">
                <i class="fa-solid fa-arrows-rotate"></i>
                <span>Re-apply UI styles</span>
              </button>
            </div>
          </div>

          <!-- BUILD TAB -->
          <div class="tab-panel" id="tab-panel-build">
            <div class="prompt-box-area">
              <span class="inspector-label"><i class="fa-solid fa-wand-magic-sparkles mr-1"></i> AI Section Generator</span>
              <p style="font-size: 11px; color: var(--text-muted);">Describe any section or interactive block you wish to generate into this preset:</p>
              <textarea class="prompt-textarea" id="ai-section-prompt" placeholder="e.g. Create a 3D orbital sensor grid with deep space probe status cards and live telemetry..."></textarea>
              <button type="button" class="generate-ai-btn" id="btn-generate-ai">
                <i class="fa-solid fa-bolt"></i>
                <span>Generate Section with AI</span>
              </button>
            </div>

            <div class="inspector-card">
              <span class="inspector-label">Preset Section Library</span>
              <div class="section-library-list">
                <div class="library-item-card" data-add-section="hud">
                  <div class="library-item-info">
                    <h4>+ Telemetry HUD Module</h4>
                    <p>Live sensor readings & velocity gauges</p>
                  </div>
                  <i class="fa-solid fa-plus text-xs opacity-60"></i>
                </div>
                <div class="library-item-card" data-add-section="grid">
                  <div class="library-item-info">
                    <h4>+ Sector Scanner Grid</h4>
                    <p>4-column spatial coordinate cards</p>
                  </div>
                  <i class="fa-solid fa-plus text-xs opacity-60"></i>
                </div>
                <div class="library-item-card" data-add-section="terminal">
                  <div class="library-item-info">
                    <h4>+ Deep Space Terminal</h4>
                    <p>Real-time encrypted telemetry transmission log</p>
                  </div>
                  <i class="fa-solid fa-plus text-xs opacity-60"></i>
                </div>
              </div>
            </div>
          </div>

          <!-- ASSETS TAB -->
          <div class="tab-panel" id="tab-panel-assets">
            <div class="inspector-card">
              <span class="inspector-label">Cosmic Media & 3D Assets</span>
              <p style="font-size: 11px; color: var(--text-muted);">Active generative models & starry shaders connected to this preset.</p>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px;">
                <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; text-align: center; border: 1px solid var(--border-subtle);">
                  <i class="fa-solid fa-globe" style="font-size: 24px; color: #38bdf8; margin-bottom: 6px;"></i>
                  <div style="font-size: 11px; font-weight: 600;">3D Wireframe</div>
                  <div style="font-size: 9px; color: var(--text-faint);">Interactive Canvas</div>
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; text-align: center; border: 1px solid var(--border-subtle);">
                  <i class="fa-solid fa-stars" style="font-size: 24px; color: #818cf8; margin-bottom: 6px;"></i>
                  <div style="font-size: 11px; font-weight: 600;">Starfield FX</div>
                  <div style="font-size: 9px; color: var(--text-faint);">WebGL Particles</div>
                </div>
              </div>
              <button type="button" class="tool-btn" id="btn-upload-asset" style="width: 100%; justify-content: center; margin-top: 8px;">
                <i class="fa-solid fa-cloud-arrow-up"></i>
                <span>Upload Custom Media</span>
              </button>
            </div>
          </div>

          <!-- BUSINESS TAB -->
          <div class="tab-panel" id="tab-panel-business">
            <div class="inspector-card">
              <span class="inspector-label">Draftly Business OS</span>
              <p style="font-size: 11px; color: var(--text-muted);">Real-time metrics & lead analytics for this preset</p>
              <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 4px;">
                <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: rgba(255,255,255,0.04); border-radius: 8px;">
                  <span style="font-size: 11px; color: var(--text-muted);">Live Visitors:</span>
                  <span style="font-size: 11px; font-weight: 700; color: #4ade80;">1,428 active</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: rgba(255,255,255,0.04); border-radius: 8px;">
                  <span style="font-size: 11px; color: var(--text-muted);">Average Session:</span>
                  <span style="font-size: 11px; font-weight: 700; color: #38bdf8;">3m 42s</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: rgba(255,255,255,0.04); border-radius: 8px;">
                  <span style="font-size: 11px; color: var(--text-muted);">Lead Submissions:</span>
                  <span style="font-size: 11px; font-weight: 700; color: #ffffff;">94 leads</span>
                </div>
              </div>
            </div>
          </div>

          <!-- PUBLISH TAB -->
          <div class="tab-panel" id="tab-panel-publish">
            <div class="inspector-card">
              <span class="inspector-label">Domain & Deployment</span>
              <div class="control-group">
                <label class="control-label">Preset Subdomain</label>
                <div style="display: flex; align-items: center; gap: 4px;">
                  <input type="text" class="control-input" value="aether-deepfield" id="publish-subdomain" />
                  <span style="font-size: 11px; color: var(--text-faint); white-space: nowrap;">.draftly.space</span>
                </div>
              </div>
              <div style="display: flex; flex-direction: column; gap: 6px; font-size: 11px; color: var(--text-muted); margin-top: 4px;">
                <div><i class="fa-solid fa-check text-green-400 mr-1.5" style="color: #4ade80;"></i> Global Edge CDN: Active</div>
                <div><i class="fa-solid fa-check text-green-400 mr-1.5" style="color: #4ade80;"></i> SSL Certificate: Wildcard Issued</div>
                <div><i class="fa-solid fa-check text-green-400 mr-1.5" style="color: #4ade80;"></i> Scroll Scrub Engine: Optimized (60 FPS)</div>
              </div>
              <button type="button" class="tool-btn primary" id="btn-publish-tab" style="width: 100%; justify-content: center; height: 36px; margin-top: 10px;">
                <i class="fa-solid fa-rocket"></i>
                <span>Publish to Production</span>
              </button>
            </div>
          </div>
        </div>
      </aside>

      <!-- Live Preview Main Canvas Area -->
      <main class="draftly-preview-main">
        <div class="preview-top-toolbar">
          <div class="preview-status-pill">
            <div class="status-pulse-dot"></div>
            <span>LIVE INTERACTIVE PREVIEW READY</span>
          </div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 10px; opacity: 0.5;">Double-click text to edit · Click to restyle</span>
            <button type="button" class="icon-btn" id="btn-refresh-preview" title="Re-render Canvas">
              <i class="fa-solid fa-arrow-rotate-right"></i>
            </button>
          </div>
        </div>

        <div class="preview-viewport-container">
          <div class="viewport-device-frame desktop cte-active" id="viewport-frame">
            <!-- Real Website Preset Content -->
            <div class="aether-preset-site" id="preset-preview-canvas">
              <canvas id="aether-starfield-canvas"></canvas>
              
              <div class="aether-content-layer">
                <!-- Preset Navigation -->
                <nav class="aether-nav" data-editable="container">
                  <div class="aether-logo-mark">
                    <div class="aether-symbol">Æ</div>
                    <span class="aether-brand-text" data-editable="text">AETHER // DEEP FIELD</span>
                  </div>

                  <div class="aether-telemetry-badge">
                    <span>COORDINATES:</span>
                    <span class="telemetry-highlight" data-editable="text">RA 05h 35m 17s</span>
                    <span>| FREQ:</span>
                    <span class="telemetry-highlight" data-editable="text">432.08 MHz</span>
                  </div>

                  <div class="aether-nav-links">
                    <a href="#survey" data-editable="text">Survey</a>
                    <a href="#sectors" data-editable="text">Sectors</a>
                    <a href="#telemetry" data-editable="text">Telemetry</a>
                    <a href="#transmissions" data-editable="text">Transmissions</a>
                  </div>
                </nav>

                <!-- Hero Section -->
                <section class="aether-hero-section" id="survey" data-editable="container">
                  <div class="hero-eyebrow" data-editable="text">
                    <i class="fa-solid fa-satellite-dish"></i>
                    <span>DEEP-SPACE PLANETARY SURVEY // ORBITAL PHASE 04</span>
                  </div>

                  <h1 class="aether-hero-title" data-editable="text" id="target-main-headline">
                    ORRIN KESH
                  </h1>

                  <div class="aether-hero-subtitle" data-editable="text">
                    Deep Field Spectral Exploration
                  </div>

                  <!-- 3D Interactive Planet Canvas -->
                  <div class="planet-interactive-wrap">
                    <canvas id="planet-canvas"></canvas>
                  </div>

                  <p class="aether-hero-lead" data-editable="text">
                    A planetary body parked below the fold scales past the viewport as you fall through into an orbital flyover across four outer worlds.
                  </p>

                  <div class="hero-actions-group">
                    <button class="aether-primary-cta" data-editable="button">Initialize Scan</button>
                    <button class="aether-secondary-cta" data-editable="button">Telemetry Feed</button>
                  </div>
                </section>

                <!-- Telemetry HUD Section -->
                <section class="aether-telemetry-hud" id="telemetry" data-editable="container">
                  <div class="telemetry-cards-grid">
                    <div class="hud-card" data-editable="container">
                      <div class="hud-metric-label" data-editable="text">Orbital Velocity</div>
                      <div class="hud-metric-val" id="val-orbital-velocity" data-editable="text">42.8 km/s</div>
                      <div class="hud-metric-sub" data-editable="text">Hyperbolic Trajectory</div>
                    </div>
                    <div class="hud-card" data-editable="container">
                      <div class="hud-metric-label" data-editable="text">Spectrometry Absorption</div>
                      <div class="hud-metric-val" data-editable="text">98.4%</div>
                      <div class="hud-metric-sub" data-editable="text">Dark Matter Saturation</div>
                    </div>
                    <div class="hud-card" data-editable="container">
                      <div class="hud-metric-label" data-editable="text">Anomaly Index</div>
                      <div class="hud-metric-val" data-editable="text">CLASS 4</div>
                      <div class="hud-metric-sub" data-editable="text">Signal Verified</div>
                    </div>
                  </div>
                </section>

                <!-- Sectors Section -->
                <section class="aether-sectors-section" id="sectors" data-editable="container">
                  <div class="section-head">
                    <h2 class="section-title" data-editable="text">Four Outer Worlds</h2>
                    <p class="section-description" data-editable="text">Deep space exploration zones catalogued during orbital pass.</p>
                  </div>

                  <div class="sectors-grid">
                    <div class="sector-card" data-editable="container">
                      <span class="sector-tag" data-editable="text">SECTOR 01 // ARCHIVE</span>
                      <h3 class="sector-title" data-editable="text">Kepler Void</h3>
                      <p class="sector-desc" data-editable="text">A silent spatial expanse with gravitational lensing anomalies and radio echoes from an ancient beacon.</p>
                    </div>

                    <div class="sector-card" data-editable="container">
                      <span class="sector-tag" data-editable="text">SECTOR 02 // THERMAL</span>
                      <h3 class="sector-title" data-editable="text">Helios Perimeter</h3>
                      <p class="sector-desc" data-editable="text">Solar flares and ionized plasma storms surrounding the secondary proto-star cluster.</p>
                    </div>

                    <div class="sector-card" data-editable="container">
                      <span class="sector-tag" data-editable="text">SECTOR 03 // OCEANIC</span>
                      <h3 class="sector-title" data-editable="text">Cygnus Abyss</h3>
                      <p class="sector-desc" data-editable="text">Liquid methane oceans beneath an atmosphere of dense nitrogen and glowing auroral ribbons.</p>
                    </div>

                    <div class="sector-card" data-editable="container">
                      <span class="sector-tag" data-editable="text">SECTOR 04 // GATE</span>
                      <h3 class="sector-title" data-editable="text">Aether Arch</h3>
                      <p class="sector-desc" data-editable="text">Artificial megastructure ring spanning 14,000 km across the orbital threshold.</p>
                    </div>
                  </div>
                </section>

                <!-- Transmissions Log Section -->
                <section class="aether-logs-section" id="transmissions" data-editable="container">
                  <div class="terminal-window" data-editable="container">
                    <div class="terminal-topbar">
                      <div class="terminal-dots">
                        <div class="terminal-dot red"></div>
                        <div class="terminal-dot yellow"></div>
                        <div class="terminal-dot green"></div>
                      </div>
                      <div class="terminal-title" data-editable="text">TRANSMISSION STREAM // ENCRYPTED 512-BIT</div>
                      <div style="font-size: 10px; color: #38bdf8;">FEED: LIVE</div>
                    </div>
                    <div class="terminal-body">
                      <div class="log-entry">
                        <span class="log-time">[07:22:14.08]</span>
                        <span class="log-msg" data-editable="text">Orbital spectrometer locked onto primary anomaly in Sector 04.</span>
                      </div>
                      <div class="log-entry">
                        <span class="log-time">[07:22:15.32]</span>
                        <span class="log-msg" data-editable="text">Telemetry ping echoed at 1.420 GHz (hydrogen line frequency).</span>
                      </div>
                      <div class="log-entry">
                        <span class="log-time">[07:22:17.91]</span>
                        <span class="log-msg" data-editable="text">Thermal shielding nominal. Deep field sweep at 94.2% completion.</span>
                      </div>
                    </div>
                  </div>
                </section>

                <!-- Site Footer -->
                <footer class="aether-site-footer" data-editable="container">
                  <div data-editable="text">© 2026 AETHER DEEP FIELD MISSION. SYSTEM OPERATIONAL.</div>
                  <div data-editable="text">PUBLISHED VIA DRAFTLY 3D STUDIO</div>
                </footer>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <!-- Modals -->
    <!-- Integrations Modal -->
    <div class="draftly-modal-backdrop" id="modal-integrations">
      <div class="draftly-modal-window">
        <div class="modal-header">
          <h3><i class="fa-solid fa-plug text-blue-400"></i> Growth & API Vault</h3>
          <button class="modal-close-btn" data-close-modal="modal-integrations"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="modal-body">
          <p style="font-size: 12px; color: var(--text-muted);">Connect your preset to external platforms, analytics, and CRM endpoints:</p>
          <div style="display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.04); border-radius: 8px;">
              <div>
                <div style="font-size: 12px; font-weight: 600;"><i class="fa-brands fa-google mr-2 text-yellow-400"></i> Google Analytics 4</div>
                <div style="font-size: 10px; color: var(--text-faint);">Measurement ID: G-DRAFTLY842</div>
              </div>
              <button class="tool-btn accent-outline" style="height: 28px;">Connected</button>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.04); border-radius: 8px;">
              <div>
                <div style="font-size: 12px; font-weight: 600;"><i class="fa-brands fa-stripe mr-2 text-indigo-400"></i> Stripe Checkout</div>
                <div style="font-size: 10px; color: var(--text-faint);">Direct payment links & subscriptions</div>
              </div>
              <button class="tool-btn primary" style="height: 28px;">Connect</button>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.04); border-radius: 8px;">
              <div>
                <div style="font-size: 12px; font-weight: 600;"><i class="fa-solid fa-network-wired mr-2 text-cyan-400"></i> Webhooks & Zapier</div>
                <div style="font-size: 10px; color: var(--text-faint);">Forward lead captures to endpoints</div>
              </div>
              <button class="tool-btn" style="height: 28px;">Configure</button>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="tool-btn" data-close-modal="modal-integrations">Close</button>
          <button class="tool-btn primary" id="btn-save-integrations">Save Changes</button>
        </div>
      </div>
    </div>

    <!-- Publish Modal -->
    <div class="draftly-modal-backdrop" id="modal-publish">
      <div class="draftly-modal-window">
        <div class="modal-header">
          <h3><i class="fa-solid fa-rocket text-green-400"></i> Site Published Successfully!</h3>
          <button class="modal-close-btn" data-close-modal="modal-publish"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="modal-body" style="text-align: center;">
          <div style="width: 56px; height: 56px; border-radius: 50%; background: rgba(74,222,128,0.15); border: 1px solid rgba(74,222,128,0.4); display: flex; align-items: center; justify-content: center; margin: 0 auto 12px; color: #4ade80; font-size: 24px;">
            <i class="fa-solid fa-check"></i>
          </div>
          <h4 style="font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 6px;">Your 3D Preset is Live</h4>
          <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;">Fast worldwide edge deployment with SSL encryption and 3D scroll frame acceleration.</p>
          
          <div style="background: rgba(0,0,0,0.5); padding: 12px; border-radius: 10px; border: 1px solid var(--border-medium); display: flex; align-items: center; justify-content: space-between;">
            <a href="#" target="_blank" id="live-publish-url" style="color: #38bdf8; font-size: 12.5px; font-family: var(--font-mono); text-decoration: none;">https://aether-deepfield.draftly.space</a>
            <button class="icon-btn" id="btn-copy-url" title="Copy URL"><i class="fa-solid fa-copy"></i></button>
          </div>
        </div>
        <div class="modal-footer">
          <button class="tool-btn" data-close-modal="modal-publish">Dismiss</button>
          <button class="tool-btn primary" id="btn-open-live-site"><i class="fa-solid fa-arrow-up-right-from-square"></i> Visit Site</button>
        </div>
      </div>
    </div>

    <!-- Add Page Modal -->
    <div class="draftly-modal-backdrop" id="modal-add-page">
      <div class="draftly-modal-window">
        <div class="modal-header">
          <h3><i class="fa-solid fa-plus text-blue-400"></i> Add New Site Page</h3>
          <button class="modal-close-btn" data-close-modal="modal-add-page"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="modal-body">
          <div class="control-group">
            <label class="control-label">Page Title</label>
            <input type="text" class="control-input" id="new-page-title" placeholder="e.g. Science Manifest, Pricing, About" />
          </div>
          <div class="control-group">
            <label class="control-label">Slug</label>
            <input type="text" class="control-input" id="new-page-slug" placeholder="/manifest" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="tool-btn" data-close-modal="modal-add-page">Cancel</button>
          <button class="tool-btn primary" id="btn-confirm-add-page">Add Page</button>
        </div>
      </div>
    </div>

    <!-- Toast Container -->
    <div class="draftly-toast-container" id="toast-container"></div>
  `;

  // Initialize Canvas Animations
  initStarfield();
  initPlanetWireframe();
  initFluctuatingTelemetry();

  // Attach Studio Event Listeners
  attachStudioEvents();

  // Record initial state for undo
  recordHistory('Initial load');

  // Select the main hero title by default for the Text Inspector
  const defaultTarget = document.getElementById('target-main-headline');
  if (defaultTarget) {
    selectElementForEditing(defaultTarget);
  }
}

// Convert string to slug/anim-class name
function slugify(text) {
  return 'anim-' + text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

// Attach all interactive event listeners
function attachStudioEvents() {
  // 1. Sidebar Tab Switching
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const tabId = btn.dataset.tab;
      const targetPanel = document.getElementById(`tab-panel-${tabId}`);
      if (targetPanel) targetPanel.classList.add('active');
      state.activeTab = tabId;
    });
  });

  // 2. Preset Switcher Dropdown
  const btnPresetSwitcher = document.getElementById('btn-preset-switcher');
  const presetDropdown = document.getElementById('preset-dropdown');
  btnPresetSwitcher.addEventListener('click', (e) => {
    e.stopPropagation();
    presetDropdown.classList.toggle('active');
  });

  document.addEventListener('click', () => {
    presetDropdown.classList.remove('active');
  });

  document.querySelectorAll('.preset-dropdown-item').forEach(item => {
    item.addEventListener('click', () => {
      const presetId = item.dataset.presetId;
      const found = state.presets.find(p => p.id === presetId);
      if (found) {
        state.activePreset = presetId;
        document.getElementById('header-preset-title').textContent = found.title;
        document.querySelectorAll('.preset-dropdown-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        showToast(`Loaded Preset: ${found.title}`);
        recordHistory(`Switched to preset ${found.title}`);
      }
    });
  });

  // 3. Click-to-edit Master Switch
  const btnToggleCTE = document.getElementById('btn-toggle-cte');
  const cteSwitch = document.getElementById('cte-switch');
  const viewportFrame = document.getElementById('viewport-frame');

  btnToggleCTE.addEventListener('click', () => {
    state.clickToEdit = !state.clickToEdit;
    if (state.clickToEdit) {
      btnToggleCTE.classList.remove('disabled');
      cteSwitch.classList.add('on');
      viewportFrame.classList.add('cte-active');
      showToast('Click-to-edit enabled: Click any text or section', 'info');
    } else {
      btnToggleCTE.classList.add('disabled');
      cteSwitch.classList.remove('on');
      viewportFrame.classList.remove('cte-active');
      clearSelection();
      showToast('Click-to-edit disabled', 'info');
    }
  });

  // 4. Viewport Switcher (Desktop, Tablet, Mobile)
  document.querySelectorAll('.viewport-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.viewport-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const mode = btn.dataset.viewport;
      state.viewportMode = mode;
      viewportFrame.className = `viewport-device-frame ${mode} ${state.clickToEdit ? 'cte-active' : ''}`;
      showToast(`Viewport switched to ${mode.toUpperCase()}`);
    });
  });

  // 5. Click-to-edit Selection in the Preview Canvas
  const previewCanvas = document.getElementById('preset-preview-canvas');
  previewCanvas.addEventListener('click', (e) => {
    if (!state.clickToEdit) return;
    const editableTarget = e.target.closest('[data-editable]');
    if (editableTarget) {
      e.preventDefault();
      e.stopPropagation();
      selectElementForEditing(editableTarget);
    }
  });

  // Double click for direct inline contenteditable text editing
  previewCanvas.addEventListener('dblclick', (e) => {
    if (!state.clickToEdit) return;
    const editableText = e.target.closest('[data-editable="text"], h1, h2, h3, p, span, a');
    if (editableText) {
      editableText.setAttribute('contenteditable', 'true');
      editableText.focus();
      
      const onBlur = () => {
        editableText.removeAttribute('contenteditable');
        recordHistory('Direct text edit');
        editableText.removeEventListener('blur', onBlur);
      };
      editableText.addEventListener('blur', onBlur);
    }
  });

  // 6. Text Inspector Controls Live Updating
  const ctrlFontFamily = document.getElementById('ctrl-font-family');
  const ctrlFontSize = document.getElementById('ctrl-font-size');
  const ctrlFontWeight = document.getElementById('ctrl-font-weight');
  const ctrlFontColor = document.getElementById('ctrl-font-color');
  const colorHexDisplay = document.getElementById('color-hex-display');

  ctrlFontFamily.addEventListener('change', (e) => {
    if (state.selectedElement) {
      state.selectedElement.style.fontFamily = e.target.value;
      recordHistory('Font family change');
    }
  });

  ctrlFontSize.addEventListener('input', (e) => {
    if (state.selectedElement) {
      state.selectedElement.style.fontSize = `${e.target.value}px`;
      recordHistory('Font size change');
    }
  });

  ctrlFontWeight.addEventListener('change', (e) => {
    if (state.selectedElement) {
      state.selectedElement.style.fontWeight = e.target.value;
      recordHistory('Font weight change');
    }
  });

  ctrlFontColor.addEventListener('input', (e) => {
    if (state.selectedElement) {
      state.selectedElement.style.color = e.target.value;
      colorHexDisplay.textContent = e.target.value;
      recordHistory('Font color change');
    }
  });

  // Color Swatches
  document.querySelectorAll('.swatch-dot').forEach(dot => {
    dot.addEventListener('click', () => {
      const color = dot.dataset.color;
      ctrlFontColor.value = color;
      colorHexDisplay.textContent = color;
      if (state.selectedElement) {
        state.selectedElement.style.color = color;
        recordHistory('Color swatch apply');
      }
    });
  });

  // 7. Animation Presets Engine (In, Out, Loop)
  function setupAnimButtons(wrapperId, animGroup) {
    const wrap = document.getElementById(wrapperId);
    if (!wrap) return;
    wrap.querySelectorAll('.anim-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        wrap.querySelectorAll('.anim-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');

        if (!state.selectedElement) return;

        // Clean prior animations from this group
        ANIMATIONS[animGroup].forEach(a => {
          const cls = slugify(a);
          state.selectedElement.classList.remove(cls);
        });

        const val = btn.dataset.animVal;
        if (val !== 'anim-none') {
          // Re-trigger animation cleanly
          state.selectedElement.classList.remove(val);
          void state.selectedElement.offsetWidth; // reflow
          state.selectedElement.classList.add(val);
          showToast(`Applied animation: ${btn.textContent}`);
          recordHistory(`Animation ${btn.textContent}`);
        }
      });
    });
  }

  setupAnimButtons('wrap-anim-in', 'in');
  setupAnimButtons('wrap-anim-out', 'out');
  setupAnimButtons('wrap-anim-loop', 'loop');

  // 8. UI Component Inspector Controls Live Updating
  const ctrlBorderRadius = document.getElementById('ctrl-border-radius');
  const ctrlPadding = document.getElementById('ctrl-padding');
  const ctrlBackground = document.getElementById('ctrl-background');
  const ctrlMoveX = document.getElementById('ctrl-move-x');
  const ctrlMoveY = document.getElementById('ctrl-move-y');
  const ctrlZIndex = document.getElementById('ctrl-z-index');
  const ctrlLinkUrl = document.getElementById('ctrl-link-url');

  const applyUIStyles = () => {
    if (!state.selectedElement) return;
    const el = state.selectedElement;
    if (ctrlBorderRadius.value) el.style.borderRadius = ctrlBorderRadius.value;
    if (ctrlPadding.value) el.style.padding = ctrlPadding.value;
    if (ctrlBackground.value) el.style.background = ctrlBackground.value;
    
    const x = ctrlMoveX.value || '0px';
    const y = ctrlMoveY.value || '0px';
    el.style.transform = `translate(${x}, ${y})`;
    if (ctrlZIndex.value) el.style.zIndex = ctrlZIndex.value;
    if (ctrlLinkUrl.value && el.tagName === 'A') {
      el.href = ctrlLinkUrl.value;
    }
    recordHistory('UI component styles apply');
    showToast('UI styles updated live');
  };

  ctrlBorderRadius.addEventListener('input', applyUIStyles);
  ctrlPadding.addEventListener('input', applyUIStyles);
  ctrlBackground.addEventListener('input', applyUIStyles);
  ctrlMoveX.addEventListener('input', applyUIStyles);
  ctrlMoveY.addEventListener('input', applyUIStyles);
  ctrlZIndex.addEventListener('input', applyUIStyles);

  document.getElementById('btn-reapply-styles').addEventListener('click', applyUIStyles);

  // Section Animation buttons
  document.querySelectorAll('[data-section-anim]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-section-anim]').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      if (!state.selectedElement) return;
      const anim = btn.dataset.sectionAnim;
      ['anim-fade-up', 'anim-slide-up', 'anim-scale-up'].forEach(cls => state.selectedElement.classList.remove(cls));
      if (anim !== 'none') {
        state.selectedElement.classList.add(anim);
      }
      recordHistory(`Section animation ${anim}`);
    });
  });

  // 9. Undo & Redo Handlers
  const handleUndo = () => {
    if (state.historyIndex > 0) {
      state.historyIndex--;
      restoreHistoryState();
    }
  };

  const handleRedo = () => {
    if (state.historyIndex < state.history.length - 1) {
      state.historyIndex++;
      restoreHistoryState();
    }
  };

  document.getElementById('btn-undo').addEventListener('click', handleUndo);
  document.getElementById('btn-redo').addEventListener('click', handleRedo);

  // Keyboard shortcuts (Ctrl+Z, Ctrl+Y)
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
      e.preventDefault();
      if (e.shiftKey) handleRedo();
      else handleUndo();
    } else if ((e.metaKey || e.ctrlKey) && e.key === 'y') {
      e.preventDefault();
      handleRedo();
    }
  });

  function restoreHistoryState() {
    const item = state.history[state.historyIndex];
    if (!item) return;
    const container = document.getElementById('preset-preview-canvas');
    if (container) {
      container.innerHTML = item.snapshot;
      // Re-initialize starfield & planet if needed
      initStarfield();
      initPlanetWireframe();
      showToast(`Undo / Redo: ${item.description}`);
      updateUndoRedoButtons();
    }
  }

  // 10. AI Section Generator (Build Tab)
  document.getElementById('btn-generate-ai').addEventListener('click', () => {
    const promptInput = document.getElementById('ai-section-prompt');
    const promptVal = promptInput.value.trim() || 'Orbital Deep Space Probe Cluster';
    
    const newSection = document.createElement('section');
    newSection.className = 'aether-sectors-section anim-fade-up';
    newSection.setAttribute('data-editable', 'container');
    newSection.innerHTML = `
      <div class="section-head">
        <h2 class="section-title" data-editable="text">${promptVal}</h2>
        <p class="section-description" data-editable="text">AI Generated telemetry cluster · Deployed into orbital stream</p>
      </div>
      <div class="sectors-grid">
        <div class="sector-card" data-editable="container">
          <span class="sector-tag" data-editable="text">PROBE 01 // FREQUENCY</span>
          <h3 class="sector-title" data-editable="text">Quantum Relay Alpha</h3>
          <p class="sector-desc" data-editable="text">Synthesized telemetry probe transmitting sub-space spectral packets at zero latency.</p>
        </div>
        <div class="sector-card" data-editable="container">
          <span class="sector-tag" data-editable="text">PROBE 02 // SPECTRAL</span>
          <h3 class="sector-title" data-editable="text">Neutron Core Scanner</h3>
          <p class="sector-desc" data-editable="text">Gravitational wave interferometer monitoring dense planetary core resonance.</p>
        </div>
      </div>
    `;

    const siteContentLayer = document.querySelector('.aether-content-layer');
    if (siteContentLayer) {
      const logsSection = document.getElementById('transmissions');
      siteContentLayer.insertBefore(newSection, logsSection);
      newSection.scrollIntoView({ behavior: 'smooth' });
      selectElementForEditing(newSection);
      recordHistory(`Generated AI section: ${promptVal}`);
      showToast('New section generated with AI & inserted!');
    }
  });

  // Section Library Quick Adds
  document.querySelectorAll('[data-add-section]').forEach(item => {
    item.addEventListener('click', () => {
      const type = item.dataset.addSection;
      showToast(`Added module: ${type.toUpperCase()}`);
    });
  });

  // 11. Modal Handlers (Integrations, Publish, Add Page)
  const openModal = (id) => {
    const m = document.getElementById(id);
    if (m) m.classList.add('active');
  };

  const closeModal = (id) => {
    const m = document.getElementById(id);
    if (m) m.classList.remove('active');
  };

  document.querySelectorAll('[data-close-modal]').forEach(b => {
    b.addEventListener('click', () => closeModal(b.dataset.closeModal));
  });

  document.getElementById('btn-integrations').addEventListener('click', () => openModal('modal-integrations'));
  document.getElementById('btn-save-integrations').addEventListener('click', () => {
    closeModal('modal-integrations');
    showToast('Integrations updated successfully', 'success');
  });

  const triggerPublish = () => {
    openModal('modal-publish');
    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.6 }
    });
  };

  document.getElementById('btn-publish').addEventListener('click', triggerPublish);
  const btnPublishTab = document.getElementById('btn-publish-tab');
  if (btnPublishTab) btnPublishTab.addEventListener('click', triggerPublish);

  document.getElementById('btn-copy-url').addEventListener('click', () => {
    const url = document.getElementById('live-publish-url').textContent;
    navigator.clipboard.writeText(url);
    showToast('Copied live URL to clipboard!', 'success');
  });

  document.getElementById('btn-open-live-site').addEventListener('click', () => {
    showToast('Opening live deployment in new tab...');
  });

  // Add Page
  document.getElementById('btn-add-page').addEventListener('click', () => openModal('modal-add-page'));
  document.getElementById('btn-confirm-add-page').addEventListener('click', () => {
    const title = document.getElementById('new-page-title').value || 'New Page';
    const pageGroup = document.querySelector('.page-tabs-group');
    const newPill = document.createElement('button');
    newPill.className = 'page-tab-pill';
    newPill.textContent = title;
    pageGroup.insertBefore(newPill, document.getElementById('btn-add-page'));
    closeModal('modal-add-page');
    showToast(`Created page: ${title}`, 'success');
  });

  // 12. Real Project ZIP Export Feature using JSZip
  document.getElementById('btn-zip-export').addEventListener('click', async () => {
    showToast('Generating project ZIP export...', 'info');
    
    try {
      const zip = new JSZip();
      const currentCanvasHTML = document.getElementById('preset-preview-canvas').innerHTML;
      
      // Clean export HTML
      const exportHTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Aether — Deep Field Survey</title>
  <link rel="stylesheet" href="style.css">
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;600;700&family=Orbitron:wght@600;700&family=Space+Grotesk:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
</head>
<body style="margin: 0; background: #030307; color: #fff; font-family: 'Space Grotesk', sans-serif;">
  <div class="aether-preset-site">
    ${currentCanvasHTML}
  </div>
  <script src="script.js"></script>
</body>
</html>`;

      // Read current styles
      const exportCSS = `/* Exported from Draftly Studio Preset */
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');
body { margin: 0; background: #030307; color: #fff; overflow-x: hidden; }
/* Included Preset Styles */
` + (document.querySelector('link[href*="style.css"]') ? '/* CSS bundled */' : '');

      const exportJS = `// Interactive Aether Deep Field Script
console.log("Aether Deep Field Survey Initialized.");
`;

      zip.file('index.html', exportHTML);
      zip.file('style.css', exportCSS);
      zip.file('script.js', exportJS);
      zip.file('README.md', '# Aether — Deep Field Survey\nExported from Draftly 3D Website Studio.\n\nOpen `index.html` in your browser to view.');

      const content = await zip.generateAsync({ type: 'blob' });
      const downloadLink = document.createElement('a');
      downloadLink.href = URL.createObjectURL(content);
      downloadLink.download = 'aether-deepfield-preset.zip';
      downloadLink.click();
      URL.revokeObjectURL(downloadLink.href);

      showToast('ZIP exported and download started!', 'success');
    } catch (err) {
      console.error(err);
      showToast('Error generating ZIP export', 'error');
    }
  });

  // Refresh preview canvas
  document.getElementById('btn-refresh-preview').addEventListener('click', () => {
    initStarfield();
    initPlanetWireframe();
    showToast('Preview canvas refreshed');
  });

  // Resizable Sidebar drag logic
  const sidebar = document.getElementById('sidebar-panel');
  const resizer = document.getElementById('sidebar-resizer');
  let isResizing = false;

  resizer.addEventListener('mousedown', (e) => {
    isResizing = true;
    resizer.classList.add('dragging');
    document.body.style.cursor = 'col-resize';
  });

  window.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    const newWidth = Math.min(Math.max(e.clientX, 320), 580);
    sidebar.style.width = `${newWidth}px`;
  });

  window.addEventListener('mouseup', () => {
    if (isResizing) {
      isResizing = false;
      resizer.classList.remove('dragging');
      document.body.style.cursor = '';
    }
  });
}

// Select an element in the preview and bind to inspectors
function selectElementForEditing(el) {
  clearSelection();
  state.selectedElement = el;
  el.classList.add('cte-selected');

  // Add floating badge
  const badge = document.createElement('div');
  badge.className = 'cte-badge';
  badge.textContent = el.tagName.toLowerCase();
  el.appendChild(badge);

  // Update text crumb & UI crumb
  const tag = el.tagName.toLowerCase();
  const previewText = (el.innerText || el.textContent || '').trim().slice(0, 24);
  const textCrumb = document.getElementById('text-crumb');
  const componentCrumb = document.getElementById('component-crumb');
  if (textCrumb) textCrumb.textContent = `<${tag}> · ${previewText || 'container'}`;
  if (componentCrumb) componentCrumb.textContent = `${tag} · ${el.className.split(' ')[0] || 'element'}`;

  // Read computed styles into controls
  const computed = window.getComputedStyle(el);
  const ctrlFontSize = document.getElementById('ctrl-font-size');
  const ctrlFontWeight = document.getElementById('ctrl-font-weight');
  const ctrlFontColor = document.getElementById('ctrl-font-color');
  const colorHexDisplay = document.getElementById('color-hex-display');
  const ctrlBorderRadius = document.getElementById('ctrl-border-radius');
  const ctrlPadding = document.getElementById('ctrl-padding');
  const ctrlBackground = document.getElementById('ctrl-background');

  if (ctrlFontSize) ctrlFontSize.value = parseInt(computed.fontSize) || 16;
  if (ctrlFontWeight) ctrlFontWeight.value = computed.fontWeight || '400';
  if (ctrlBorderRadius) ctrlBorderRadius.value = computed.borderRadius || '';
  if (ctrlPadding) ctrlPadding.value = computed.padding || '';
  if (ctrlBackground) ctrlBackground.value = computed.backgroundColor || '';

  // Convert RGB to HEX
  const rgb = computed.color;
  const hex = rgbToHex(rgb);
  if (hex && ctrlFontColor) {
    ctrlFontColor.value = hex;
    if (colorHexDisplay) colorHexDisplay.textContent = hex;
  }
}

function clearSelection() {
  document.querySelectorAll('.cte-selected').forEach(el => {
    el.classList.remove('cte-selected');
    const badge = el.querySelector('.cte-badge');
    if (badge) badge.remove();
  });
  state.selectedElement = null;
}

function rgbToHex(rgbStr) {
  const match = rgbStr.match(/\d+/g);
  if (!match || match.length < 3) return '#ffffff';
  return '#' + match.slice(0, 3).map(x => parseInt(x).toString(16).padStart(2, '0')).join('');
}

// -----------------------------------------------------------------------------
// Interactive 3D Wireframe Planet Canvas
// -----------------------------------------------------------------------------
function initPlanetWireframe() {
  const canvas = document.getElementById('planet-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  
  canvas.width = 220;
  canvas.height = 220;
  const width = canvas.width;
  const height = canvas.height;
  const cx = width / 2;
  const cy = height / 2;
  const radius = 80;

  let rotation = 0;
  let isDragging = false;
  let lastX = 0;

  canvas.addEventListener('mousedown', (e) => {
    isDragging = true;
    lastX = e.clientX;
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const dx = e.clientX - lastX;
    rotation += dx * 0.01;
    lastX = e.clientX;
  });

  window.addEventListener('mouseup', () => { isDragging = false; });

  function renderPlanet() {
    ctx.clearRect(0, 0, width, height);

    if (!isDragging) {
      rotation += 0.006;
    }

    // Outer atmosphere glow
    const grad = ctx.createRadialGradient(cx, cy, radius * 0.7, cx, cy, radius * 1.3);
    grad.addColorStop(0, 'rgba(56, 189, 248, 0.15)');
    grad.addColorStop(0.8, 'rgba(59, 130, 246, 0.05)');
    grad.addColorStop(1, 'transparent');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 1.3, 0, Math.PI * 2);
    ctx.fill();

    // Planet body circle
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.6)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.stroke();

    // Longitude rings (rotating)
    const longitudes = 7;
    for (let i = 0; i < longitudes; i++) {
      const angle = rotation + (i * Math.PI) / longitudes;
      const xRadius = Math.abs(Math.cos(angle) * radius);
      ctx.strokeStyle = `rgba(125, 211, 252, ${0.15 + 0.35 * Math.abs(Math.sin(angle))})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.ellipse(cx, cy, xRadius, radius, 0, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Latitude rings
    const latitudes = [-50, -25, 0, 25, 50];
    latitudes.forEach(lat => {
      const y = cy + (lat / 90) * radius;
      const r = Math.sqrt(Math.max(0, radius * radius - (y - cy) * (y - cy)));
      ctx.strokeStyle = 'rgba(125, 211, 252, 0.2)';
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.ellipse(cx, y, r, r * 0.25, 0, 0, Math.PI * 2);
      ctx.stroke();
    });

    // Orbital ring
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(0.35);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.lineWidth = 1.2;
    ctx.setLineDash([4, 6]);
    ctx.beginPath();
    ctx.ellipse(0, 0, radius * 1.5, radius * 0.45, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();

    requestAnimationFrame(renderPlanet);
  }

  renderPlanet();
}

// -----------------------------------------------------------------------------
// Interactive Starfield Canvas
// -----------------------------------------------------------------------------
function initStarfield() {
  const canvas = document.getElementById('aether-starfield-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function resizeCanvas() {
    canvas.width = canvas.parentElement.scrollWidth || window.innerWidth;
    canvas.height = canvas.parentElement.scrollHeight || window.innerHeight;
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  const starCount = 180;
  const stars = [];

  for (let i = 0; i < starCount; i++) {
    stars.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      radius: Math.random() * 1.5 + 0.5,
      alpha: Math.random() * 0.8 + 0.2,
      speed: Math.random() * 0.015 + 0.005,
      direction: Math.random() > 0.5 ? 1 : -1
    });
  }

  function drawStarfield() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Subtle cosmic dust gradient
    const dust = ctx.createRadialGradient(
      canvas.width * 0.7, canvas.height * 0.3, 50,
      canvas.width * 0.7, canvas.height * 0.3, 600
    );
    dust.addColorStop(0, 'rgba(59, 130, 246, 0.08)');
    dust.addColorStop(0.5, 'rgba(139, 92, 246, 0.04)');
    dust.addColorStop(1, 'transparent');
    ctx.fillStyle = dust;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Render twinkling stars
    stars.forEach(s => {
      s.alpha += s.speed * s.direction;
      if (s.alpha > 0.95 || s.alpha < 0.15) {
        s.direction *= -1;
      }
      ctx.fillStyle = `rgba(255, 255, 255, ${s.alpha})`;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.radius, 0, Math.PI * 2);
      ctx.fill();
    });

    requestAnimationFrame(drawStarfield);
  }

  drawStarfield();
}

// -----------------------------------------------------------------------------
// Fluctuating Telemetry Values
// -----------------------------------------------------------------------------
function initFluctuatingTelemetry() {
  const velocityEl = document.getElementById('val-orbital-velocity');
  if (!velocityEl) return;

  setInterval(() => {
    const base = 42.8;
    const variation = (Math.random() * 0.4 - 0.2).toFixed(2);
    const newVal = (base + parseFloat(variation)).toFixed(1);
    velocityEl.textContent = `${newVal} km/s`;
  }, 3000);
}

// Start application
initApp();
