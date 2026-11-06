# -*- coding: utf-8 -*-
"""
Script to apply Option 1: Ultra Premium Streaming Theme to index.html
Preserves all functionality, IDs, event handlers, and endpoints.
"""

new_css = r"""    /* ======================================================== */
    /* 🎬 ULTRA-PREMIUM STREAMING THEME (NETFLIX / APPLE TV / HBO) */
    /* ======================================================== */
    :root, body[data-service="netflix"] {
      --accent-color: #E50914;
      --accent-rgb: 229, 9, 20;
      --accent-glow: rgba(229, 9, 20, 0.45);
      --accent-glow-subtle: rgba(229, 9, 20, 0.14);
      --accent-gradient: linear-gradient(135deg, #FF1E27 0%, #B20710 100%);
      --accent-gradient-hover: linear-gradient(135deg, #FF3841 0%, #D40813 100%);
      
      --bg-base: #06080e;
      --panel-bg: rgba(14, 20, 34, 0.72);
      --panel-border: rgba(229, 9, 20, 0.28);
      --panel-border-hover: rgba(229, 9, 20, 0.65);
      --panel-border-glass: rgba(255, 255, 255, 0.08);
      
      --text-bright: #ffffff;
      --text-dim: #94a3b8;
      --text-dark: #475569;
      --matrix-color: #e50914;
      
      --font-display: 'Outfit', sans-serif;
      --font-body: 'Plus Jakarta Sans', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    body[data-service="hbo"] {
      --accent-color: #9D4EDD;
      --accent-rgb: 157, 78, 221;
      --accent-glow: rgba(157, 78, 221, 0.45);
      --accent-glow-subtle: rgba(157, 78, 221, 0.14);
      --accent-gradient: linear-gradient(135deg, #A855F7 0%, #6B21A8 100%);
      --accent-gradient-hover: linear-gradient(135deg, #C084FC 0%, #7E22CE 100%);
      
      --bg-base: #07060f;
      --panel-bg: rgba(18, 14, 34, 0.72);
      --panel-border: rgba(157, 78, 221, 0.28);
      --panel-border-hover: rgba(157, 78, 221, 0.65);
      --panel-border-glass: rgba(255, 255, 255, 0.08);
      
      --text-bright: #ffffff;
      --text-dim: #cbd5e1;
      --text-dark: #64748b;
      --matrix-color: #9d4edd;
    }

    body[data-service="crunchyroll"] {
      --accent-color: #FF7700;
      --accent-rgb: 255, 119, 0;
      --accent-glow: rgba(255, 119, 0, 0.45);
      --accent-glow-subtle: rgba(255, 119, 0, 0.14);
      --accent-gradient: linear-gradient(135deg, #FF8500 0%, #E85D04 100%);
      --accent-gradient-hover: linear-gradient(135deg, #FFA200 0%, #FF6F00 100%);
      
      --bg-base: #0a0705;
      --panel-bg: rgba(26, 17, 12, 0.72);
      --panel-border: rgba(255, 119, 0, 0.28);
      --panel-border-hover: rgba(255, 119, 0, 0.65);
      --panel-border-glass: rgba(255, 255, 255, 0.08);
      
      --text-bright: #ffffff;
      --text-dim: #fed7aa;
      --text-dark: #78350f;
      --matrix-color: #ff7700;
    }

    body[data-service="sky"] {
      --accent-color: #00A6FB;
      --accent-rgb: 0, 166, 251;
      --accent-glow: rgba(0, 166, 251, 0.45);
      --accent-glow-subtle: rgba(0, 166, 251, 0.14);
      --accent-gradient: linear-gradient(135deg, #00A6FB 0%, #006494 100%);
      --accent-gradient-hover: linear-gradient(135deg, #33B9FC 0%, #0582CA 100%);
      
      --bg-base: #040810;
      --panel-bg: rgba(10, 19, 36, 0.72);
      --panel-border: rgba(0, 166, 251, 0.28);
      --panel-border-hover: rgba(0, 166, 251, 0.65);
      --panel-border-glass: rgba(255, 255, 255, 0.08);
      
      --text-bright: #ffffff;
      --text-dim: #bae6fd;
      --text-dark: #0369a1;
      --matrix-color: #00a6fb;
    }

    body[data-service="disney"] {
      --accent-color: #00D4FF;
      --accent-rgb: 0, 212, 255;
      --accent-glow: rgba(0, 212, 255, 0.45);
      --accent-glow-subtle: rgba(0, 212, 255, 0.15);
      --accent-gradient: linear-gradient(135deg, #00D4FF 0%, #0077B6 100%);
      --accent-gradient-hover: linear-gradient(135deg, #38E1FF 0%, #023E8A 100%);
      
      --bg-base: #040714;
      --panel-bg: rgba(10, 18, 42, 0.75);
      --panel-border: rgba(0, 212, 255, 0.28);
      --panel-border-hover: rgba(0, 212, 255, 0.65);
      --panel-border-glass: rgba(255, 255, 255, 0.10);
      
      --text-bright: #ffffff;
      --text-dim: #bae6fd;
      --text-dark: #0284c7;
      --matrix-color: #00d4ff;
    }

    body[data-service="claro"] {
      --accent-color: #EF233C;
      --accent-rgb: 239, 35, 60;
      --accent-glow: rgba(239, 35, 60, 0.45);
      --accent-glow-subtle: rgba(239, 35, 60, 0.14);
      --accent-gradient: linear-gradient(135deg, #EF233C 0%, #B91C1C 100%);
      --accent-gradient-hover: linear-gradient(135deg, #FF4D6D 0%, #DC2626 100%);
      
      --bg-base: #090506;
      --panel-bg: rgba(26, 12, 14, 0.75);
      --panel-border: rgba(239, 35, 60, 0.28);
      --panel-border-hover: rgba(239, 35, 60, 0.65);
      --panel-border-glass: rgba(255, 255, 255, 0.08);
      
      --text-bright: #ffffff;
      --text-dim: #fecdd3;
      --text-dark: #be123c;
      --matrix-color: #ef233c;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
      user-select: none;
    }

    body {
      background: var(--bg-base);
      background-image: 
        radial-gradient(ellipse 90% 70% at 50% 0%, var(--accent-glow-subtle) 0%, transparent 75%),
        linear-gradient(rgba(255, 255, 255, 0.012) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.012) 1px, transparent 1px);
      background-size: 100% 100%, 48px 48px, 48px 48px;
      color: var(--text-bright);
      font-family: var(--font-body);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 16px 60px;
      overflow-x: hidden;
      position: relative;
      transition: background 0.6s ease;
    }

    /* Ambient Lighting Mesh */
    .ambient-glow {
      position: fixed;
      border-radius: 50%;
      pointer-events: none;
      filter: blur(140px);
      z-index: 0;
      opacity: 0.6;
      transition: background 0.7s ease, opacity 0.5s ease;
    }

    .orb-1 {
      width: 650px;
      height: 520px;
      top: -140px;
      left: 50%;
      transform: translateX(-50%);
      background: radial-gradient(circle, var(--accent-glow) 0%, rgba(var(--accent-rgb), 0.12) 50%, transparent 75%);
      animation: floatOrb 12s ease-in-out infinite alternate;
    }

    .orb-2 {
      width: 520px;
      height: 520px;
      bottom: -100px;
      right: -80px;
      background: radial-gradient(circle, var(--accent-glow-subtle) 0%, transparent 70%);
      animation: floatOrb2 16s ease-in-out infinite alternate;
    }

    @keyframes floatOrb {
      0% { transform: translateX(-50%) translateY(0) scale(1); }
      50% { transform: translateX(-47%) translateY(40px) scale(1.08); }
      100% { transform: translateX(-53%) translateY(20px) scale(0.96); }
    }

    @keyframes floatOrb2 {
      0% { transform: translateY(0) scale(1); }
      100% { transform: translateY(-45px) scale(1.12); }
    }

    /* Matrix canvas is disabled to give clean high-end streaming feel */
    #matrix-canvas {
      display: none !important;
    }

    #confetti-canvas {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      pointer-events: none;
      z-index: 9999;
    }

    .deck-container {
      width: 100%;
      max-width: 580px;
      display: flex;
      flex-direction: column;
      gap: 18px;
      position: relative;
      z-index: 2;
      margin: 0 auto;
    }

    /* ======================================================== */
    /* 👑 BRAND HEADER - SLEEK CINEMA CAPSULE                   */
    /* ======================================================== */
    .brand-header {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 8px 0 6px;
    }

    .brand-badge {
      display: inline-flex;
      align-items: center;
      gap: 16px;
      padding: 12px 26px;
      background: rgba(14, 20, 36, 0.72);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 50px;
      backdrop-filter: blur(28px) saturate(180%);
      -webkit-backdrop-filter: blur(28px) saturate(180%);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.15), 0 0 30px var(--accent-glow-subtle);
      transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .brand-badge:hover {
      border-color: rgba(255, 255, 255, 0.22);
      box-shadow: 0 20px 45px rgba(0, 0, 0, 0.7), 0 0 35px var(--accent-glow);
      transform: translateY(-2px);
    }

    .brand-icon-wrapper {
      position: relative;
      width: 44px;
      height: 44px;
      border-radius: 16px;
      background: var(--accent-gradient);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 8px 25px var(--accent-glow), inset 0 1px 0 rgba(255, 255, 255, 0.4);
      flex-shrink: 0;
    }

    .brand-icon-svg {
      width: 22px;
      height: 22px;
      stroke: #ffffff;
      fill: none;
      stroke-width: 2.2;
      stroke-linecap: round;
      stroke-linejoin: round;
      filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
    }

    .brand-live-dot {
      position: absolute;
      top: -2px;
      right: -2px;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #00ff88;
      border: 2px solid #06080e;
      box-shadow: 0 0 12px #00ff88;
      animation: livePulse 2s infinite ease-in-out;
    }

    @keyframes livePulse {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.15); opacity: 0.8; }
    }

    .brand-info {
      display: flex;
      flex-direction: column;
      text-align: left;
    }

    .brand-title {
      font-family: var(--font-display);
      font-size: 16.5px;
      font-weight: 900;
      letter-spacing: 0.8px;
      color: #ffffff;
      line-height: 1.25;
      display: flex;
      align-items: center;
      gap: 9px;
    }

    .brand-title-badge {
      font-size: 10px;
      font-weight: 900;
      background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
      color: #0b0f19;
      padding: 2px 8px;
      border-radius: 20px;
      letter-spacing: 0.6px;
      box-shadow: 0 2px 10px rgba(255, 215, 0, 0.4);
    }

    .brand-subtitle {
      font-size: 11.5px;
      color: var(--text-dim);
      font-weight: 600;
      letter-spacing: 0.4px;
      margin-top: 2px;
    }

    /* ======================================================== */
    /* 🛰️ TELEMETRY BAR - LUXURY GLASS CAPSULE                  */
    /* ======================================================== */
    .telemetry-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--panel-bg);
      border: 1px solid var(--panel-border-glass);
      border-radius: 50px;
      padding: 10px 20px;
      backdrop-filter: blur(28px) saturate(180%);
      -webkit-backdrop-filter: blur(28px) saturate(180%);
      box-shadow: 0 12px 35px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.1);
      font-size: 11.5px;
      font-weight: 600;
      letter-spacing: 0.4px;
      transition: all 0.3s ease;
      width: 100%;
      box-sizing: border-box;
      gap: 12px;
      flex-wrap: wrap;
    }

    .telemetry-left {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
      flex: 1;
      min-width: 220px;
    }

    .status-radar {
      position: relative;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #00ff88;
      box-shadow: 0 0 12px #00ff88;
    }

    .status-radar::after {
      content: '';
      position: absolute;
      top: -4px;
      left: -4px;
      right: -4px;
      bottom: -4px;
      border-radius: 50%;
      border: 1.5px solid #00ff88;
      animation: radarPing 2.2s infinite cubic-bezier(0, 0, 0.2, 1);
    }

    @keyframes radarPing {
      0% { transform: scale(0.6); opacity: 1; }
      100% { transform: scale(2.4); opacity: 0; }
    }

    .telemetry-right {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }

    .btn-icon {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text-bright);
      padding: 7px 14px;
      border-radius: 30px;
      cursor: pointer;
      font-family: var(--font-body);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.4px;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      backdrop-filter: blur(12px);
    }

    .btn-icon:hover {
      background: var(--accent-gradient);
      color: #fff;
      border-color: rgba(255, 255, 255, 0.3);
      box-shadow: 0 6px 20px var(--accent-glow);
      transform: translateY(-1px);
    }

    .btn-icon:active {
      transform: scale(0.96);
    }

    /* ======================================================== */
    /* 🎛️ SERVICE SWITCHER - CINEMA FLOATING PILL DOCK          */
    /* ======================================================== */
    .service-switcher {
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 6px;
      background: rgba(10, 15, 28, 0.72);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 50px;
      padding: 6px;
      backdrop-filter: blur(28px) saturate(180%);
      -webkit-backdrop-filter: blur(28px) saturate(180%);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), inset 0 2px 4px rgba(0, 0, 0, 0.4);
    }

    .service-tab {
      background: transparent;
      border: 1px solid transparent;
      padding: 12px 6px;
      border-radius: 40px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      font-family: var(--font-display);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.4px;
      color: var(--text-dim);
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      white-space: nowrap;
      user-select: none;
    }

    .service-tab:hover {
      color: var(--text-bright);
      background: rgba(255, 255, 255, 0.06);
      transform: translateY(-1px);
    }

    .service-tab.active-netflix,
    .service-tab.active-hbo,
    .service-tab.active-crunchyroll,
    .service-tab.active-sky,
    .service-tab.active-disney,
    .service-tab.active-claro {
      background: var(--accent-gradient);
      border-color: rgba(255, 255, 255, 0.3);
      color: #ffffff;
      box-shadow: 0 8px 28px var(--accent-glow), inset 0 1px 0 rgba(255, 255, 255, 0.45);
      transform: scale(1.03);
    }

    .service-tab.tab-locked {
      opacity: 0.45;
      cursor: not-allowed !important;
      border: 1px dashed rgba(255, 51, 68, 0.5) !important;
      background: rgba(15, 15, 25, 0.5) !important;
      box-shadow: none !important;
      filter: grayscale(0.3);
      position: relative;
    }

    .service-tab.tab-locked:hover {
      opacity: 0.75;
      border-color: #ff3344 !important;
      transform: none !important;
    }

    .tab-lock-indicator {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      margin-left: 4px;
      background: rgba(255, 51, 68, 0.25);
      border: 1px solid rgba(255, 51, 68, 0.6);
      border-radius: 6px;
      padding: 1px 5px;
      animation: lockPulse 2s infinite ease-in-out;
    }

    @keyframes lockPulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.12); }
    }

    /* ======================================================== */
    /* 💎 CYBER CARD - ULTRA FROSTED GLASS PANELS               */
    /* ======================================================== */
    .cyber-card {
      background: var(--panel-bg);
      border: 1px solid var(--panel-border-glass);
      border-radius: 28px;
      padding: 24px;
      backdrop-filter: blur(32px) saturate(200%);
      -webkit-backdrop-filter: blur(32px) saturate(200%);
      box-shadow: 
        0 24px 60px rgba(0, 0, 0, 0.65), 
        inset 0 1px 0 rgba(255, 255, 255, 0.12), 
        0 0 35px var(--accent-glow-subtle);
      position: relative;
      transition: border-color 0.4s ease, box-shadow 0.4s ease;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 18px;
      padding-bottom: 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }

    .card-title {
      font-family: var(--font-display);
      font-size: 13.5px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: 0.6px;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: color 0.3s ease;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .card-title span {
      display: inline-flex;
      align-items: center;
      gap: 7px;
    }

    .badge-signal {
      font-size: 10.5px;
      font-weight: 700;
      color: #00ff88;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      letter-spacing: 0.5px;
      background: rgba(0, 255, 136, 0.1);
      border: 1px solid rgba(0, 255, 136, 0.3);
      padding: 4px 12px;
      border-radius: 20px;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .payload-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-bottom: 18px;
      width: 100%;
    }

    .payload-box {
      background: linear-gradient(160deg, rgba(16, 24, 42, 0.65) 0%, rgba(8, 12, 24, 0.88) 100%);
      border: 1px solid rgba(255, 255, 255, 0.07);
      border-radius: 20px;
      padding: 15px 18px;
      transition: all 0.3s ease;
      box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.5), 0 4px 16px rgba(0, 0, 0, 0.25);
      min-width: 0;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-height: 80px;
    }

    .payload-box:hover {
      border-color: rgba(255, 255, 255, 0.18);
      background: linear-gradient(160deg, rgba(22, 32, 56, 0.75) 0%, rgba(10, 16, 30, 0.95) 100%);
      box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.5), 0 0 25px var(--accent-glow-subtle);
    }

    .payload-box-label {
      font-size: 10px;
      color: var(--text-dim);
      text-transform: uppercase;
      font-weight: 800;
      letter-spacing: 0.8px;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }

    .payload-box-val {
      font-family: var(--font-body);
      font-size: 13px;
      font-weight: 700;
      color: #fff;
      min-width: 0;
      overflow: hidden;
      display: flex;
      align-items: center;
      gap: 8px;
      line-height: 1.35;
    }

    #active-email-text {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      min-width: 0;
      flex: 1;
      font-family: var(--font-mono);
      font-size: 12.5px;
      letter-spacing: 0.2px;
      color: #f1f5f9;
    }

    #active-account-plan {
      white-space: normal !important;
      word-break: break-word !important;
      display: inline-flex !important;
      align-items: center !important;
      gap: 7px !important;
      padding: 5px 12px;
      background: linear-gradient(135deg, rgba(255, 215, 0, 0.15) 0%, rgba(218, 165, 32, 0.08) 100%);
      border: 1px solid rgba(255, 215, 0, 0.45);
      border-radius: 14px;
      color: #ffd700 !important;
      font-weight: 800;
      font-size: 12px;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      box-shadow: 0 0 16px rgba(255, 215, 0, 0.2);
    }

    .badge-country {
      background: var(--accent-gradient);
      border: none;
      color: #ffffff;
      font-size: 10px;
      font-weight: 900;
      padding: 3px 8px;
      border-radius: 10px;
      flex-shrink: 0;
      box-shadow: 0 2px 8px var(--accent-glow);
    }

    .payload-footer {
      display: flex;
      flex-direction: column;
      gap: 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 14px;
    }

    .payload-cookie-tag {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-dim);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      padding: 5px 10px;
      background: rgba(0, 0, 0, 0.35);
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.05);
      display: inline-block;
    }

    #live-stock-badge {
      font-family: var(--font-body);
      font-size: 11px;
      font-weight: 800;
      color: #34d399;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.35);
      padding: 4px 12px;
      border-radius: 20px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 0 14px rgba(16, 185, 129, 0.15);
    }

    /* ======================================================== */
    /* 📺 SMART TV PIN DISPLAY (SQUIRCLES & HIGH-END GLOW)       */
    /* ======================================================== */
    .pin-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 18px;
      margin: 4px 0;
    }

    .pin-label-row {
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .pin-title {
      font-family: var(--font-display);
      font-size: 14px;
      font-weight: 800;
      letter-spacing: 0.6px;
      color: var(--text-bright);
      display: flex;
      align-items: center;
      gap: 7px;
    }

    .pin-counter {
      background: var(--accent-glow-subtle);
      border: 1px solid var(--panel-border);
      color: var(--accent-color);
      padding: 5px 14px;
      border-radius: 30px;
      font-size: 11.5px;
      font-weight: 800;
      letter-spacing: 0.6px;
      box-shadow: 0 2px 10px var(--accent-glow-subtle);
    }

    .pin-grid-wrapper {
      position: relative;
      width: 100%;
      max-width: 530px;
      margin: 8px 0;
      cursor: text;
    }

    .pin-native-input {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      opacity: 0.001;
      z-index: 10;
      cursor: text;
      font-size: 20px;
      border: none;
      background: transparent;
      color: transparent;
      caret-color: transparent;
      -webkit-user-select: text;
      user-select: text;
      touch-action: manipulation;
    }

    .pin-grid {
      display: grid;
      grid-template-columns: repeat(8, 1fr);
      gap: 10px;
      width: 100%;
      position: relative;
      z-index: 1;
    }

    .pin-slot {
      aspect-ratio: 1 / 1.15;
      background: linear-gradient(180deg, rgba(20, 28, 48, 0.6) 0%, rgba(6, 10, 20, 0.85) 100%);
      border: 1.6px solid rgba(255, 255, 255, 0.1);
      border-radius: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-display);
      font-size: 26px;
      font-weight: 900;
      color: var(--accent-color);
      text-shadow: 0 0 14px var(--accent-glow);
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      cursor: text;
      box-shadow: 
        inset 0 2px 6px rgba(0, 0, 0, 0.6), 
        inset 0 1px 0 rgba(255, 255, 255, 0.08), 
        0 6px 18px rgba(0, 0, 0, 0.35);
    }

    .pin-slot:hover {
      border-color: rgba(255, 255, 255, 0.25);
      background: linear-gradient(180deg, rgba(26, 36, 62, 0.75) 0%, rgba(8, 14, 26, 0.95) 100%);
    }

    .pin-slot.active {
      border-color: var(--accent-color);
      box-shadow: 0 0 28px var(--accent-glow), inset 0 0 12px var(--accent-glow-subtle);
      animation: pulseSlotBorder 1.4s infinite alternate ease-in-out;
      background: linear-gradient(180deg, rgba(30, 42, 72, 0.8) 0%, rgba(10, 16, 32, 0.95) 100%);
    }

    .pin-slot.filled {
      border-color: rgba(255, 255, 255, 0.35);
      background: var(--accent-gradient);
      box-shadow: 0 8px 30px var(--accent-glow), inset 0 1px 0 rgba(255, 255, 255, 0.5);
      transform: scale(1.05);
      color: #ffffff;
      text-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
      animation: popSlot 0.22s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    @keyframes popSlot {
      0% { transform: scale(0.85); }
      70% { transform: scale(1.12); }
      100% { transform: scale(1.05); }
    }

    @keyframes pulseSlotBorder {
      from { border-color: var(--accent-color); box-shadow: 0 0 16px var(--accent-glow); }
      to { border-color: #ffffff; box-shadow: 0 0 28px var(--accent-glow); }
    }

    .pin-hint {
      font-size: 12px;
      color: var(--text-dim);
      letter-spacing: 0.3px;
      text-align: center;
      font-weight: 500;
    }

    .pin-actions {
      display: flex;
      justify-content: center;
      gap: 12px;
      width: 100%;
    }

    .mobile-keypad {
      display: none;
      flex-direction: column;
      gap: 8px;
      width: 100%;
      max-width: 330px;
      margin: 8px auto 0;
    }

    .keypad-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }

    .key-btn {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 18px;
      color: #fff;
      font-family: var(--font-display);
      font-size: 22px;
      font-weight: 800;
      padding: 14px;
      cursor: pointer;
      transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1);
      touch-action: manipulation;
      display: flex;
      align-items: center;
      justify-content: center;
      backdrop-filter: blur(12px);
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }

    .key-btn:active {
      background: var(--accent-gradient);
      border-color: rgba(255, 255, 255, 0.3);
      color: #fff;
      transform: scale(0.93);
      box-shadow: 0 0 20px var(--accent-glow);
    }

    .key-action {
      font-size: 14px;
      color: var(--accent-color);
      font-weight: 800;
    }

    @media (max-width: 768px) {
      .mobile-keypad {
        display: flex;
      }
    }

    /* ======================================================== */
    /* ⚡ MAIN CALL-TO-ACTION TRANSMIT BUTTON                    */
    /* ======================================================== */
    .btn-transmit {
      width: 100%;
      background: var(--accent-gradient);
      border: none;
      border-radius: 50px;
      padding: 19px 28px;
      font-family: var(--font-display);
      font-size: 16px;
      font-weight: 900;
      letter-spacing: 0.9px;
      color: #ffffff;
      cursor: pointer;
      box-shadow: 
        0 12px 35px var(--accent-glow), 
        inset 0 1px 0 rgba(255, 255, 255, 0.5),
        0 0 20px rgba(0, 0, 0, 0.4);
      transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      position: relative;
      overflow: hidden;
      margin-top: 8px;
    }

    .btn-transmit::after {
      content: '';
      position: absolute;
      top: -50%;
      left: -60%;
      width: 35%;
      height: 200%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.35), transparent);
      transform: rotate(30deg);
      animation: lightSweep 4s infinite ease-in-out;
    }

    @keyframes lightSweep {
      0% { left: -70%; }
      30%, 100% { left: 140%; }
    }

    .btn-transmit:hover:not(:disabled) {
      transform: translateY(-2px);
      background: var(--accent-gradient-hover);
      box-shadow: 0 16px 45px var(--accent-glow), inset 0 1px 0 rgba(255, 255, 255, 0.65);
    }

    .btn-transmit:disabled {
      opacity: 0.85;
      cursor: wait;
      box-shadow: 0 6px 20px var(--accent-glow-subtle);
    }

    .btn-transmit.loading {
      animation: transmit-pulse 1.2s infinite ease-in-out;
    }

    @keyframes transmit-pulse {
      0%, 100% { box-shadow: 0 6px 20px var(--accent-glow-subtle); }
      50% { box-shadow: 0 12px 50px var(--accent-glow); }
    }

    .alert-banner {
      display: none;
      padding: 14px 20px;
      border-radius: 18px;
      font-size: 12.5px;
      font-weight: 600;
      letter-spacing: 0.3px;
      animation: fadeIn 0.3s ease;
    }

    .alert-error {
      background: rgba(239, 35, 60, 0.15);
      border: 1px solid #ef233c;
      color: #fecdd3;
    }

    .alert-success {
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid #10b981;
      color: #a7f3d0;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* ======================================================== */
    /* 📋 LOWER DECK: TABS & QUEUE                              */
    /* ======================================================== */
    .deck-tabs-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }

    .window-dots {
      display: flex;
      gap: 6px;
    }

    .window-dot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
    }

    .dot-red { background: #ff5f56; }
    .dot-yellow { background: #ffbd2e; }
    .dot-green { background: #27c93f; }

    .deck-nav {
      display: flex;
      gap: 8px;
    }

    .deck-nav-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-dim);
      padding: 6px 14px;
      border-radius: 20px;
      font-family: var(--font-body);
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
      letter-spacing: 0.3px;
      transition: all 0.2s ease;
    }

    .deck-nav-btn.active {
      background: var(--accent-glow-subtle);
      border-color: var(--accent-color);
      color: var(--accent-color);
    }

    .cookie-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 310px;
      overflow-y: auto;
      padding-right: 4px;
    }

    .cookie-list::-webkit-scrollbar {
      width: 5px;
    }
    .cookie-list::-webkit-scrollbar-thumb {
      background: var(--panel-border);
      border-radius: 10px;
    }

    .cookie-row {
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid var(--panel-border-glass);
      border-radius: 16px;
      padding: 11px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11.5px;
      transition: all 0.2s ease;
      cursor: pointer;
    }

    .cookie-row:hover {
      border-color: var(--accent-color);
      background: var(--accent-glow-subtle);
      transform: translateX(2px);
    }

    .cookie-row.selected {
      border-color: var(--accent-color);
      background: var(--accent-glow-subtle);
      box-shadow: 0 0 14px var(--accent-glow-subtle);
    }

    .cookie-row-left {
      display: flex;
      align-items: center;
      gap: 10px;
      overflow: hidden;
    }

    .cookie-email {
      color: #fff;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .cookie-row-right {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }

    .kernel-logs-box {
      background: rgba(0, 0, 0, 0.78);
      border: 1px solid var(--panel-border-glass);
      border-radius: 16px;
      padding: 14px;
      font-family: var(--font-mono);
      font-size: 11.5px;
      color: #e2e8f0;
      height: 220px;
      overflow-y: auto;
      line-height: 1.65;
      display: none;
      box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.7);
    }

    .kernel-logs-box::-webkit-scrollbar {
      width: 5px;
    }
    .kernel-logs-box::-webkit-scrollbar-thumb {
      background: var(--panel-border);
      border-radius: 10px;
    }

    .kernel-log-line {
      margin-bottom: 5px;
      word-break: break-word;
    }

    .kernel-log-time {
      color: var(--text-dim);
      margin-right: 6px;
      font-weight: 600;
    }

    .kernel-log-line.error .kernel-log-msg {
      color: #ff4d6d;
      font-weight: 700;
      text-shadow: 0 0 10px rgba(255, 77, 109, 0.4);
    }

    .kernel-log-line.success .kernel-log-msg {
      color: #00ff88;
      font-weight: 700;
      text-shadow: 0 0 10px rgba(0, 255, 136, 0.4);
    }

    .kernel-log-line.warn .kernel-log-msg {
      color: #ffd700;
      font-weight: 600;
      text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
    }

    /* ======================================================== */
    /* 🔐 LOGIN OVERLAY - CINEMATIC GATEWAY                     */
    /* ======================================================== */
    #login-overlay {
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      background: radial-gradient(ellipse at 50% 15%, rgba(15, 23, 42, 0.96) 0%, rgba(8, 12, 22, 0.98) 60%, #03060d 100%);
      backdrop-filter: blur(40px);
      -webkit-backdrop-filter: blur(40px);
      z-index: 10000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
      overflow-y: auto;
    }

    #login-overlay::before, #login-overlay::after {
      content: '';
      position: absolute;
      border-radius: 50%;
      filter: blur(140px);
      pointer-events: none;
      opacity: 0.28;
      animation: floatAuraSmooth 14s ease-in-out infinite alternate;
    }

    #login-overlay::before {
      width: 520px;
      height: 520px;
      background: radial-gradient(circle, rgba(14, 165, 233, 0.3) 0%, rgba(99, 102, 241, 0.2) 50%, transparent 75%);
      top: 5%;
      left: 15%;
    }

    #login-overlay::after {
      width: 480px;
      height: 480px;
      background: radial-gradient(circle, rgba(229, 9, 20, 0.25) 0%, rgba(249, 115, 22, 0.18) 50%, transparent 75%);
      bottom: 5%;
      right: 15%;
      animation-delay: -7s;
    }

    @keyframes floatAuraSmooth {
      0% { transform: translate(0px, 0px) scale(1); }
      50% { transform: translate(30px, -25px) scale(1.08); }
      100% { transform: translate(-25px, 25px) scale(0.96); }
    }

    .login-card {
      width: 100%;
      max-width: 450px;
      background: linear-gradient(180deg, rgba(20, 27, 45, 0.88) 0%, rgba(10, 14, 25, 0.96) 100%);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 28px;
      padding: 36px 30px 28px;
      box-shadow: 
        0 30px 80px -15px rgba(0, 0, 0, 0.95), 
        0 0 50px rgba(56, 189, 248, 0.06), 
        inset 0 1px 0 rgba(255, 255, 255, 0.18);
      text-align: center;
      position: relative;
      animation: modalPremiumSlide 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      overflow: hidden;
      z-index: 1;
      backdrop-filter: blur(32px) saturate(180%);
      -webkit-backdrop-filter: blur(32px) saturate(180%);
    }

    @keyframes modalPremiumSlide {
      from { opacity: 0; transform: translateY(22px) scale(0.97); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    .login-card-topline {
      position: absolute;
      top: 0;
      left: 15%;
      width: 70%;
      height: 2px;
      background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.9) 30%, rgba(168, 85, 247, 0.9) 70%, transparent);
      box-shadow: 0 0 14px rgba(56, 189, 248, 0.5);
    }

    .login-brand-chips {
      display: flex;
      justify-content: center;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 22px;
      position: relative;
      z-index: 2;
    }

    .login-chip {
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      letter-spacing: 0.3px;
      background: rgba(255, 255, 255, 0.035);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: #94a3b8;
      user-select: none;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .login-chip-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      display: inline-block;
    }

    .login-chip:hover {
      transform: translateY(-1px);
      color: #ffffff;
      background: rgba(255, 255, 255, 0.07);
    }

    .login-chip.nf { border-color: rgba(229, 9, 20, 0.3); }
    .login-chip.nf .login-chip-dot { background: #E50914; box-shadow: 0 0 7px #E50914; }
    .login-chip.nf:hover { border-color: #E50914; box-shadow: 0 0 14px rgba(229, 9, 20, 0.25); color: #fff; }

    .login-chip.hbo { border-color: rgba(168, 85, 247, 0.3); }
    .login-chip.hbo .login-chip-dot { background: #A855F7; box-shadow: 0 0 7px #A855F7; }
    .login-chip.hbo:hover { border-color: #A855F7; box-shadow: 0 0 14px rgba(168, 85, 247, 0.25); color: #fff; }

    .login-chip.cr { border-color: rgba(244, 117, 33, 0.3); }
    .login-chip.cr .login-chip-dot { background: #F47521; box-shadow: 0 0 7px #F47521; }
    .login-chip.cr:hover { border-color: #F47521; box-shadow: 0 0 14px rgba(244, 117, 33, 0.25); color: #fff; }

    .login-chip.sky { border-color: rgba(0, 160, 227, 0.3); }
    .login-chip.sky .login-chip-dot { background: #00A0E3; box-shadow: 0 0 7px #00A0E3; }
    .login-chip.sky:hover { border-color: #00A0E3; box-shadow: 0 0 14px rgba(0, 160, 227, 0.25); color: #fff; }

    .login-chip.disney { border-color: rgba(0, 210, 255, 0.3); }
    .login-chip.disney .login-chip-dot { background: #00d2ff; box-shadow: 0 0 7px #00d2ff; }
    .login-chip.disney:hover { border-color: #00d2ff; box-shadow: 0 0 14px rgba(0, 210, 255, 0.25); color: #fff; }

    .login-chip.claro { border-color: rgba(229, 29, 37, 0.3); }
    .login-chip.claro .login-chip-dot { background: #e51d25; box-shadow: 0 0 7px #e51d25; }
    .login-chip.claro:hover { border-color: #e51d25; box-shadow: 0 0 14px rgba(229, 29, 37, 0.25); color: #fff; }

    /* Hero Emblem */
    .login-orbital-wrap {
      position: relative;
      width: 70px;
      height: 70px;
      margin: 0 auto 14px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .login-orbital-ring {
      position: absolute;
      inset: -5px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(56, 189, 248, 0.16) 0%, rgba(168, 85, 247, 0.08) 50%, transparent 70%);
      pointer-events: none;
    }

    .login-icon-box {
      width: 60px;
      height: 60px;
      border-radius: 20px;
      background: linear-gradient(145deg, rgba(30, 41, 59, 0.85) 0%, rgba(15, 23, 42, 0.98) 100%);
      border: 1.5px solid rgba(255, 255, 255, 0.15);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 
        0 10px 25px rgba(0, 0, 0, 0.5), 
        inset 0 1px 0 rgba(255, 255, 255, 0.25),
        0 0 22px rgba(56, 189, 248, 0.2);
      position: relative;
      z-index: 2;
    }

    .login-icon-svg {
      width: 32px;
      height: 32px;
      fill: none;
      stroke: url(#loginIconGrad);
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
      filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.5));
    }

    .login-title {
      font-family: 'Outfit', sans-serif;
      font-size: 24px;
      font-weight: 800;
      letter-spacing: 0.3px;
      margin-bottom: 4px;
      position: relative;
      z-index: 2;
      background: linear-gradient(135deg, #ffffff 40%, #e2e8f0 75%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      filter: drop-shadow(0 2px 10px rgba(56, 189, 248, 0.2));
    }

    .login-sub {
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 12px;
      color: #94a3b8;
      font-weight: 600;
      letter-spacing: 0.8px;
      margin-bottom: 12px;
      position: relative;
      z-index: 2;
    }

    .login-status-badge {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.25);
      border-radius: 20px;
      padding: 4px 13px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 10.5px;
      font-weight: 700;
      color: #34d399;
      letter-spacing: 0.3px;
      margin-bottom: 20px;
      position: relative;
      z-index: 2;
    }

    .login-pulse-dot {
      width: 6.5px;
      height: 6.5px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
      position: relative;
    }

    .login-input-wrap {
      position: relative;
      display: flex;
      align-items: center;
      background: rgba(15, 23, 42, 0.85);
      border: 1.5px solid rgba(255, 255, 255, 0.12);
      border-radius: 16px;
      padding: 4px 12px;
      margin-bottom: 16px;
      box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.4);
      transition: all 0.25s ease;
      z-index: 2;
    }

    .login-input-wrap:focus-within {
      border-color: #38bdf8;
      box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.4), 0 0 20px rgba(56, 189, 248, 0.25);
      background: rgba(10, 16, 30, 0.95);
    }

    .login-input-icon {
      color: #38bdf8;
      pointer-events: none;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      margin-right: 8px;
    }

    .login-input {
      flex: 1;
      min-width: 0;
      background: transparent;
      border: none;
      padding: 12px 6px;
      color: #ffffff;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13.5px;
      letter-spacing: 1px;
      outline: none;
    }

    .login-input::placeholder {
      color: rgba(148, 163, 184, 0.55);
      letter-spacing: 0.2px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 12.5px;
      font-weight: 500;
    }

    .login-input-actions {
      display: flex;
      align-items: center;
      gap: 5px;
      flex-shrink: 0;
    }

    .btn-paste-login {
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: #38bdf8;
      border-radius: 8px;
      padding: 6px 10px;
      font-size: 11px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: all 0.2s ease;
    }

    .btn-paste-login:hover {
      background: rgba(56, 189, 248, 0.22);
      border-color: #38bdf8;
      color: #ffffff;
    }

    .btn-eye {
      background: transparent;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      padding: 6px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
    }

    .btn-eye:hover {
      color: #38bdf8;
      background: rgba(255, 255, 255, 0.05);
    }

    .login-options {
      display: flex;
      justify-content: flex-start;
      align-items: center;
      margin-bottom: 18px;
      z-index: 2;
      position: relative;
    }

    .login-checkbox-label {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      color: #94a3b8;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 12px;
      font-weight: 600;
      transition: color 0.2s;
    }

    .login-checkbox-label:hover {
      color: #f1f5f9;
    }

    .login-checkbox {
      accent-color: #0284c7;
      width: 15px;
      height: 15px;
      cursor: pointer;
      border-radius: 4px;
    }

    .btn-unlock {
      width: 100%;
      background: linear-gradient(135deg, #0284c7 0%, #2563eb 50%, #4f46e5 100%);
      color: #ffffff;
      border: none;
      border-radius: 16px;
      padding: 16px;
      font-family: 'Outfit', sans-serif;
      font-size: 15px;
      font-weight: 800;
      letter-spacing: 0.6px;
      cursor: pointer;
      box-shadow: 
        0 10px 25px -4px rgba(37, 99, 235, 0.5), 
        inset 0 1px 0 rgba(255, 255, 255, 0.25);
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      position: relative;
      overflow: hidden;
      z-index: 2;
    }

    .btn-unlock:hover {
      transform: translateY(-2px);
      box-shadow: 
        0 14px 35px -4px rgba(37, 99, 235, 0.65), 
        0 0 25px rgba(79, 70, 229, 0.35);
      filter: brightness(1.05);
    }

    .btn-unlock:active {
      transform: translateY(1px);
    }

    .login-badges-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-top: 18px;
      position: relative;
      z-index: 2;
    }

    .login-mini-badge {
      background: rgba(255, 255, 255, 0.025);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 12px;
      padding: 10px 4px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 10px;
      font-weight: 700;
      color: #94a3b8;
      letter-spacing: 0.2px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      transition: all 0.2s ease;
    }

    .login-mini-badge .lmb-label {
      font-size: 9.5px;
      font-weight: 700;
      color: #94a3b8;
      letter-spacing: 0.3px;
    }

    .login-mini-badge .lmb-val {
      font-size: 8.5px;
      font-weight: 800;
    }

    .login-mini-badge:hover {
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(56, 189, 248, 0.3);
      color: #ffffff;
      transform: translateY(-1px);
    }

    .login-error {
      display: none;
      color: #ff4d5a;
      font-size: 12.5px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-weight: 700;
      margin-top: 14px;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(255, 51, 68, 0.12);
      border: 1px solid rgba(255, 51, 68, 0.4);
      box-shadow: 0 0 20px rgba(255, 51, 68, 0.15);
      z-index: 2;
      position: relative;
      animation: shakeLogin 0.4s ease-in-out;
    }

    @keyframes shakeLogin {
      0%, 100% { transform: translateX(0); }
      20%, 60% { transform: translateX(-6px); }
      40%, 80% { transform: translateX(6px); }
    }

    /* 🏆 SUCCESS MODAL - VIP CELEBRATION */
    #success-modal {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(3, 7, 18, 0.92);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      z-index: 10001;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .success-card {
      width: 100%;
      max-width: 480px;
      background: var(--panel-bg);
      border: 2px solid var(--accent-color);
      border-radius: 32px;
      padding: 38px 32px;
      text-align: center;
      box-shadow: 0 15px 70px var(--accent-glow), inset 0 0 30px var(--accent-glow-subtle);
      position: relative;
      animation: modalSlide 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    @keyframes modalSlide {
      from { transform: scale(0.85); opacity: 0; }
      to { transform: scale(1); opacity: 1; }
    }

    .success-badge-icon {
      width: 84px;
      height: 84px;
      border-radius: 50%;
      background: var(--accent-glow-subtle);
      border: 3px solid var(--accent-color);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 40px;
      margin: 0 auto 20px;
      box-shadow: 0 0 35px var(--accent-glow);
    }

    .success-title {
      font-family: var(--font-display);
      font-size: 20px;
      font-weight: 900;
      color: var(--accent-color);
      letter-spacing: 1px;
      margin-bottom: 8px;
    }

    .success-subtitle {
      font-size: 13px;
      color: var(--text-dim);
      margin-bottom: 24px;
      font-weight: 600;
    }

    .success-data-box {
      background: rgba(0, 0, 0, 0.55);
      border: 1px solid var(--panel-border-glass);
      border-radius: 20px;
      padding: 20px;
      margin-bottom: 24px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      text-align: left;
    }

    .success-data-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12.5px;
    }

    .success-data-key {
      color: var(--text-dim);
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.6px;
    }

    .success-data-val {
      color: #fff;
      font-weight: 700;
    }

    .btn-finish {
      width: 100%;
      background: var(--accent-gradient);
      color: #fff;
      border: none;
      border-radius: 50px;
      padding: 17px;
      font-family: var(--font-display);
      font-size: 15.5px;
      font-weight: 900;
      letter-spacing: 1px;
      cursor: pointer;
      box-shadow: 0 8px 30px var(--accent-glow);
      transition: all 0.25s ease;
    }

    .btn-finish:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 40px var(--accent-glow);
    }

    /* ======================================================== */
    /* 📱 RESPONSIVE MOBILE TWEAKS                              */
    /* ======================================================== */
    @media (max-width: 600px) {
      body {
        padding: 16px 12px 60px;
      }
      .deck-container {
        gap: 14px;
        width: 100%;
        max-width: 100%;
      }
      .brand-title {
        font-size: 14.5px;
      }
      .telemetry-bar {
        padding: 8px 12px;
        border-radius: 30px;
        gap: 6px;
      }
      .telemetry-left {
        gap: 8px;
        font-size: 10.5px;
      }
      #telemetry-ip {
        display: none !important;
      }
      .telemetry-right {
        gap: 5px;
      }
      .btn-icon {
        padding: 6px 10px;
        font-size: 10.5px;
        border-radius: 20px;
        gap: 4px;
        white-space: nowrap;
      }
      .service-switcher {
        grid-template-columns: repeat(3, 1fr);
        gap: 6px;
        border-radius: 24px;
        padding: 6px;
      }
      .service-tab {
        padding: 10px 8px;
        font-size: 12px;
        border-radius: 18px;
      }
      .cyber-card {
        padding: 18px 16px;
        border-radius: 22px;
      }
      .payload-grid {
        grid-template-columns: 1fr;
        gap: 10px;
      }
      .pin-grid {
        gap: 6px;
      }
      .pin-slot {
        font-size: 20px;
        border-radius: 14px;
      }
      .btn-transmit {
        padding: 17px 20px;
        font-size: 15px;
        border-radius: 40px;
      }
      .login-card {
        padding: 28px 20px;
        border-radius: 24px;
      }
    }
"""

with open("index.html", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Replace <style> ... </style>
start_idx = content.find("<style>")
end_idx = content.find("</style>")

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx + len("<style>\n")] + new_css + content[end_idx:]
    print("CSS replaced successfully!")
else:
    print("Could not find style tags!")

# Also polish the Title and Header in HTML
content = content.replace(
    "<title>CYBER DECK // Smart TV Kernel Activator</title>",
    "<title>VIP STREAM // Ativador Smart TV 4K</title>"
)

content = content.replace(
    '<h1 class="brand-title">STREAM ACTIVATOR <span class="brand-title-badge">PRO</span></h1>',
    '<h1 class="brand-title">STREAM ACTIVATOR <span class="brand-title-badge">👑 4K ULTRA HD</span></h1>'
)

content = content.replace(
    '<p class="brand-subtitle">Smart TV Pairing Hub &bull; Netflix &bull; HBO Max &bull; Crunchyroll &bull; Sky+ &bull; Disney+ &bull; Claro TV+</p>',
    '<p class="brand-subtitle">Central Oficial de Ativação Instantânea para Smart TVs</p>'
)

content = content.replace(
    '// CONTA CONECTADA',
    'CONTA AUTORIZADA'
)

content = content.replace(
    '// PLANO DA CONTA',
    'PLANO EXCLUSIVO'
)

content = content.replace(
    '💡 Digite o código de 8 dígitos da sua TV no teclado ou clique em Colar',
    '💡 Digite o código exibido na tela da sua Smart TV ou clique em Colar'
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html successfully updated with Option 1 Ultra Premium Streaming Theme!")

