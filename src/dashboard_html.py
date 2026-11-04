"""
Responsive Korean Web Dashboard HTML for AI Model Radar (v1.1 with Password Auth & Full-List Copy).
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ko" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI Model Radar — 실시간 AI 모델 통합 조회·검증 센터</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    body {
      font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
      background-color: #0b0f19;
      color: #e2e8f0;
    }
    .glass {
      background: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .copy-chip:hover {
      border-color: #38bdf8;
      background: rgba(56, 189, 248, 0.14);
    }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
  </style>
</head>
<body class="min-h-screen pb-16">
  <!-- 🔒 Password Lock Screen Overlay -->
  <div id="auth-overlay" class="fixed inset-0 z-50 bg-slate-950/95 backdrop-blur-xl flex items-center justify-center p-4">
    <div class="glass rounded-3xl max-w-md w-full p-8 border border-slate-800 shadow-2xl space-y-6 text-center">
      <div class="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-3xl shadow-lg shadow-sky-500/25">
        🔒
      </div>
      <div>
        <h2 class="text-xl font-bold text-white">AI Model Radar 보안 접속</h2>
        <p class="text-xs text-slate-400 mt-1.5 leading-relaxed">
          허가된 사용자만 조회 및 API 설정을 변경할 수 있습니다.<br/>접속 비밀번호를 입력해 주세요.
        </p>
      </div>

      <form onsubmit="submitLogin(event)" class="space-y-3 text-left">
        <div>
          <label class="block text-xs text-slate-300 font-medium mb-1.5">접속 비밀번호 (Password)</label>
          <input
            id="login-password"
            type="password"
            autofocus
            placeholder="비밀번호 입력..."
            class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>
        <div id="login-error" class="hidden text-xs text-rose-400 font-medium">
          ⚠️ 비밀번호가 일치하지 않습니다. 다시 확인해 주세요.
        </div>
        <button
          type="submit"
          class="w-full bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold py-3 rounded-xl text-sm transition shadow-lg shadow-sky-500/20"
        >
          🔓 잠금 해제 및 대시보드 접속
        </button>
      </form>
    </div>
  </div>

  <!-- Toast Notification -->
  <div id="toast" class="fixed bottom-6 right-6 z-50 hidden transform transition-all duration-300 bg-sky-500 text-slate-950 font-semibold px-5 py-3 rounded-xl shadow-2xl flex items-center gap-2 max-w-md">
    <span id="toast-msg" class="truncate">복사되었습니다!</span>
  </div>

  <!-- Header -->
  <header class="sticky top-0 z-30 glass border-b border-slate-800/80 px-6 py-4">
    <div class="max-w-7xl mx-auto flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="w-11 h-11 rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-2xl shadow-lg shadow-sky-500/20">
          📡
        </div>
        <div>
          <div class="flex items-center gap-2.5">
            <h1 class="text-xl font-bold text-white tracking-tight">AI Model Radar</h1>
            <span class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-medium">
              무인증 통합 허브 가동 중
            </span>
          </div>
          <p class="text-xs text-slate-400 mt-0.5">
            OpenRouter + LiteLLM 실시간 통합 레지스트리 · 개별 API 키 없이 전 세계 최신 사용 가능 AI 모델 즉시 조회
          </p>
        </div>
      </div>

      <!-- Status & Actions -->
      <div class="flex flex-wrap items-center gap-2">
        <div id="sync-badge" class="text-xs bg-slate-900/90 border border-slate-800 px-3 py-2 rounded-xl text-slate-300">
          동기화 확인 중...
        </div>
        <button onclick="triggerSync()" id="btn-sync" class="text-xs font-semibold bg-sky-500 hover:bg-sky-400 text-slate-950 px-3.5 py-2 rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-sky-500/15">
          <span>🔄</span> 지금 즉시 동기화
        </button>
        <button onclick="openKeyModal()" class="text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3.5 py-2 rounded-xl transition flex items-center gap-1.5">
          <span>🔑</span> API 키/비밀번호 설정
        </button>
        <button onclick="sendTelegramReport()" class="text-xs font-medium bg-indigo-600/80 hover:bg-indigo-500 text-white px-3.5 py-2 rounded-xl transition flex items-center gap-1.5">
          <span>✈️</span> 텔레그램 요약 발송
        </button>
        <button onclick="lockDashboard()" class="text-xs font-medium bg-rose-500/15 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 px-3 py-2 rounded-xl transition flex items-center gap-1">
          <span>🔒</span> 잠금
        </button>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-6 mt-6 space-y-6">
    <!-- Top Summary Cards -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="glass rounded-2xl p-4">
        <div class="text-xs text-slate-400 flex items-center justify-between">
          <span>현재 즉시 사용 가능한 모델</span>
          <span class="text-sky-400">OpenRouter Live</span>
        </div>
        <div class="text-2xl font-bold text-white mt-1" id="stat-total">-</div>
        <div class="text-xs text-slate-400 mt-1" id="stat-or-lat">응답 속도 측정 중...</div>
      </div>

      <div class="glass rounded-2xl p-4">
        <div class="text-xs text-slate-400 flex items-center justify-between">
          <span>LiteLLM 공식 스펙 매핑</span>
          <span class="text-indigo-400">Native ID 검증</span>
        </div>
        <div class="text-2xl font-bold text-white mt-1" id="stat-litellm">-</div>
        <div class="text-xs text-slate-400 mt-1" id="stat-ll-lat">공식 입출력 한도·기능 매핑 완료</div>
      </div>

      <div class="glass rounded-2xl p-4">
        <div class="text-xs text-slate-400 flex items-center justify-between">
          <span>무료 호출 가능 모델 (:free)</span>
          <span class="text-emerald-400">Free Tier</span>
        </div>
        <div class="text-2xl font-bold text-emerald-400 mt-1" id="stat-free">-</div>
        <div class="text-xs text-slate-400 mt-1">비용 $0 테스트/경량 봇용 모델</div>
      </div>

      <div class="glass rounded-2xl p-4">
        <div class="text-xs text-slate-400 flex items-center justify-between">
          <span>연동된 선택형 API 키</span>
          <span class="text-amber-400">Optional Keys</span>
        </div>
        <div class="text-lg font-bold text-white mt-1 truncate" id="stat-keys">무인증 모드 (0개 키로도 완동)</div>
        <div class="text-xs text-slate-400 mt-1">OpenRouter 키 1개면 전 모델 Ping 가능</div>
      </div>
    </section>

    <!-- Navigation Tabs -->
    <div class="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
      <button onclick="switchTab('rec')" id="tab-btn-rec" class="tab-btn px-4 py-2 rounded-xl text-sm font-semibold bg-sky-500 text-slate-950 transition">
        🏆 제조사별 최신 주력·가성비 & 전체 모델 복사
      </button>
      <button onclick="switchTab('all')" id="tab-btn-all" class="tab-btn px-4 py-2 rounded-xl text-sm font-medium bg-slate-900 text-slate-300 hover:bg-slate-800 transition">
        🔍 전체 모델 실시간 검색·비교표
      </button>
      <button onclick="switchTab('changes')" id="tab-btn-changes" class="tab-btn px-4 py-2 rounded-xl text-sm font-medium bg-slate-900 text-slate-300 hover:bg-slate-800 transition">
        🔔 신규 출시 & 단종(Deprecated) 감지 이력
      </button>
      <button onclick="switchTab('api')" id="tab-btn-api" class="tab-btn px-4 py-2 rounded-xl text-sm font-medium bg-slate-900 text-slate-300 hover:bg-slate-800 transition">
        🔌 다른 도커 봇 자동 연동 API 가이드
      </button>
    </div>

    <!-- TAB 1: Smart Recommendations per Provider -->
    <section id="tab-rec" class="space-y-4">
      <div class="glass rounded-2xl p-4 border-l-4 border-sky-500 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div>
          <h2 class="text-sm font-bold text-white">💡 제조사별 개별 모델 복사 및 제조사 전체 모델 일괄 복사</h2>
          <p class="text-xs text-slate-400 mt-0.5">
            각 제조사 카드 우측 상단의 <b>[📋 이 제조사 전체 모델 ID 복사]</b> 또는 <b>[📦 전체 모델 상세표 복사]</b>를 누르면 해당 제조사의 모든 사용 가능 모델을 한 번에 복사합니다.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button onclick="copyAllProvidersEnv()" class="text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 px-3 py-2 rounded-xl transition">
            ⚙️ 8대 제조사 추천 .env 한 번에 복사
          </button>
          <button onclick="copyAllProvidersModels()" class="text-xs font-semibold bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/30 px-3 py-2 rounded-xl transition">
            📋 8대 제조사 전체 모델 목록 일괄 복사
          </button>
        </div>
      </div>

      <div id="rec-grid" class="grid grid-cols-1 md:grid-cols-2 gap-5">
        <!-- Populated by JS -->
      </div>
    </section>

    <!-- TAB 2: Full Searchable Model Explorer -->
    <section id="tab-all" class="hidden space-y-4">
      <div class="glass rounded-2xl p-4 flex flex-col xl:flex-row gap-3 items-stretch xl:items-center justify-between">
        <div class="flex flex-wrap gap-2">
          <select id="filter-provider" onchange="loadModels()" class="bg-slate-900 border border-slate-700 text-xs rounded-xl px-3 py-2 text-slate-200">
            <option value="all">🌐 전체 제조사</option>
            <option value="google">💎 Google Gemini</option>
            <option value="openai">🟢 OpenAI (GPT / o시리즈)</option>
            <option value="anthropic">🟠 Anthropic Claude</option>
            <option value="deepseek">🐋 DeepSeek</option>
            <option value="x-ai">✖️ xAI Grok</option>
            <option value="meta-llama">🦙 Meta Llama</option>
            <option value="qwen">🟣 Alibaba Qwen</option>
            <option value="mistralai">🌪️ Mistral AI</option>
          </select>

          <select id="filter-tier" onchange="loadModels()" class="bg-slate-900 border border-slate-700 text-xs rounded-xl px-3 py-2 text-slate-200">
            <option value="all">✨ 전체 등급</option>
            <option value="flagship">🏆 최고성능 주력 (Flagship)</option>
            <option value="fast">⚡ 가성비·속도 (Flash / Mini)</option>
            <option value="reasoning">🧠 추론 특화 (Reasoning)</option>
            <option value="free">🎁 무료 제공 (:free)</option>
          </select>

          <select id="filter-modality" onchange="loadModels()" class="bg-slate-900 border border-slate-700 text-xs rounded-xl px-3 py-2 text-slate-200">
            <option value="all">📄 전체 입력 방식</option>
            <option value="image">🖼️ 이미지/비전 지원</option>
            <option value="audio">🎙️ 오디오 입력 지원</option>
          </select>
        </div>

        <div class="flex flex-wrap items-center gap-2 flex-1 justify-end">
          <input
            id="filter-search"
            type="text"
            oninput="loadModels()"
            placeholder="모델명 검색 (예: gemini-3.8, gpt-6, sonnet, flash, grok...)"
            class="flex-1 min-w-[220px] bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
          <span id="model-count-label" class="text-xs text-slate-400 whitespace-nowrap">0개</span>
          <button onclick="copyFilteredIds()" class="text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-300 px-3 py-2 rounded-xl transition whitespace-nowrap">
            📋 현재 목록 전체 ID 복사
          </button>
          <button onclick="copyFilteredDetails()" class="text-xs font-semibold bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/30 text-sky-300 px-3 py-2 rounded-xl transition whitespace-nowrap">
            📦 현재 목록 전체 상세 복사
          </button>
        </div>
      </div>

      <div class="glass rounded-2xl overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-slate-800 text-[11px] uppercase text-slate-400 bg-slate-900/60">
                <th class="py-3 px-4">제조사 / 모델명</th>
                <th class="py-3 px-4">공식 Native ID (클릭 복사)</th>
                <th class="py-3 px-4">OpenRouter 통합 ID</th>
                <th class="py-3 px-4">컨텍스트 / 출력</th>
                <th class="py-3 px-4">지원 기능</th>
                <th class="py-3 px-4">가격 (1M 토큰당)</th>
                <th class="py-3 px-4">출시 / 상태</th>
                <th class="py-3 px-4 text-right">복사 / 실시간 진단</th>
              </tr>
            </thead>
            <tbody id="models-tbody" class="divide-y divide-slate-800/60 text-xs">
              <!-- Populated by JS -->
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 3: Change Radar -->
    <section id="tab-changes" class="hidden space-y-4">
      <div class="glass rounded-2xl p-5">
        <h3 class="text-base font-bold text-white mb-1">🔔 신규 모델 출시 & 단종(Deprecated) 감지 로그</h3>
        <p class="text-xs text-slate-400 mb-4">
          주기적 스캔 시 이전 버전과 비교하여 새로 추가되거나 만료 예정인 모델을 자동으로 기록합니다.
        </p>
        <div id="changes-container" class="space-y-3">
          <!-- Populated by JS -->
        </div>
      </div>
    </section>

    <!-- TAB 4: Internal Docker API Guide -->
    <section id="tab-api" class="hidden space-y-4">
      <div class="glass rounded-2xl p-6 space-y-4">
        <h3 class="text-base font-bold text-white">🔌 다른 도커 봇에서 최신 모델명을 자동으로 받아오는 방법</h3>
        <p class="text-xs text-slate-300 leading-relaxed">
          시놀로지 NAS에서 실행 중인 다른 봇(예: <code>rehab-ai-bot</code>, <code>journal-club-bot</code>, <code>bot-cal-card</code>)에서 모델명이 업그레이드될 때마다 코드를 수정할 필요 없이, 본 컨테이너의 REST API를 호출하면 <b>현재 시점 가장 최신 가성비/주력 모델명</b>을 0.01초 만에 반환합니다.
        </p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2">
            <div class="text-xs font-semibold text-sky-400">1️⃣ 제조사별 최적 모델 자동 조회 API</div>
            <code class="block text-xs text-emerald-300 bg-slate-900 p-2.5 rounded-lg">
              GET /api/resolve/google?tier=fast<br/>
              GET /api/resolve/openai?tier=flagship<br/>
              GET /api/resolve/anthropic?tier=fast
            </code>
            <p class="text-[11px] text-slate-400">
              <code>tier=fast</code> (가성비 Flash/Mini), <code>tier=flagship</code> (최고성능 Pro/Opus), <code>tier=reasoning</code> (추론), <code>tier=free</code> (무료) 지원
            </p>
          </div>
          <div class="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2">
            <div class="text-xs font-semibold text-indigo-400">2️⃣ 파이썬 봇 코드 3줄 연동 예시</div>
            <pre class="text-[11px] text-slate-200 bg-slate-900 p-2.5 rounded-lg overflow-x-auto">import requests
res = requests.get("http://ai-model-radar:8500/api/resolve/google?tier=fast").json()
GEMINI_MODEL = res["native_id"]  # 예: 'gemini-3.8-flash'</pre>
          </div>
        </div>
      </div>
    </section>
  </main>

  <!-- Live Endpoint / Ping Inspection Modal -->
  <div id="ping-modal" class="fixed inset-0 z-50 hidden bg-black/75 flex items-center justify-center p-4">
    <div class="glass rounded-2xl max-w-2xl w-full p-6 border border-slate-700 space-y-4 max-h-[88vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 class="text-base font-bold text-white" id="ping-modal-title">🩺 모델 실시간 가동률 & 엔드포인트 진단</h3>
          <p class="text-xs text-slate-400" id="ping-modal-sub">-</p>
        </div>
        <button onclick="closePingModal()" class="text-slate-400 hover:text-white text-lg px-2">✕</button>
      </div>
      <div id="ping-modal-body" class="space-y-4 text-xs">
        <!-- Populated dynamically -->
      </div>
    </div>
  </div>

  <!-- Optional API Keys, Password & Telegram Settings Modal -->
  <div id="key-modal" class="fixed inset-0 z-50 hidden bg-black/75 flex items-center justify-center p-4">
    <div class="glass rounded-2xl max-w-xl w-full p-6 border border-slate-700 space-y-4 max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 class="text-base font-bold text-white">🔑 소수 API 키 · 비밀번호 · 텔레그램 설정</h3>
          <p class="text-xs text-slate-400">
            API 키가 없어도 모든 모델 조회 및 글로벌 가동률 확인이 가능합니다. 원하는 항목만 입력 후 저장하세요.
          </p>
        </div>
        <button onclick="closeKeyModal()" class="text-slate-400 hover:text-white text-lg px-2">✕</button>
      </div>

      <div class="space-y-3 text-xs">
        <div>
          <label class="block text-amber-300 font-semibold mb-1">🔒 웹 대시보드 접속 비밀번호 변경 (선택 — 비워두면 기존 비밀번호 유지)</label>
          <input id="input-dashboard-pw" type="password" placeholder="새 비밀번호 입력 (쉼표로 복수 비밀번호 등록 가능)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white" />
        </div>
        <hr class="border-slate-800 my-2" />
        <div>
          <label class="block text-slate-300 font-semibold mb-1">🌐 OpenRouter API Key (가장 추천 — 키 1개로 전 세계 450+ 모델 실호출 테스트)</label>
          <input id="input-or-key" type="password" placeholder="sk-or-v1-... (비워두면 기존 값 유지)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white" />
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-slate-300 font-medium mb-1">💎 Google Gemini API Key (선택)</label>
            <input id="input-gemini-key" type="password" placeholder="AIza..." class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white" />
          </div>
          <div>
            <label class="block text-slate-300 font-medium mb-1">🟢 OpenAI API Key (선택)</label>
            <input id="input-openai-key" type="password" placeholder="sk-..." class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white" />
          </div>
          <div>
            <label class="block text-slate-300 font-medium mb-1">🟠 Anthropic API Key (선택)</label>
            <input id="input-anthropic-key" type="password" placeholder="sk-ant-..." class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white" />
          </div>
          <div>
            <label class="block text-slate-300 font-medium mb-1">🐋 DeepSeek API Key (선택)</label>
            <input id="input-deepseek-key" type="password" placeholder="sk-..." class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white" />
          </div>
        </div>
        <hr class="border-slate-800 my-2" />
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-slate-300 font-medium mb-1">✈️ 텔레그램 봇 토큰 (선택)</label>
            <input id="input-tg-token" type="password" placeholder="123456:ABC-DEF..." class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white" />
          </div>
          <div>
            <label class="block text-slate-300 font-medium mb-1">💬 텔레그램 채팅방 ID (선택)</label>
            <input id="input-tg-chat" type="text" placeholder="예: 123456789" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white" />
          </div>
        </div>
      </div>

      <div class="flex justify-end gap-2 pt-3 border-t border-slate-800">
        <button onclick="closeKeyModal()" class="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs">취소</button>
        <button onclick="saveSettings()" class="px-4 py-2 rounded-xl bg-sky-500 text-slate-950 font-semibold text-xs">💾 저장 및 즉시 반영</button>
      </div>
    </div>
  </div>

  <script>
    let cachedRecommendations = [];
    let cachedFilteredModels = [];

    function getAuthToken() {
      return localStorage.getItem('radar_auth_token') || '';
    }

    async function apiFetch(url, options = {}) {
      const headers = Object.assign({}, options.headers || {}, {
        'X-Radar-Token': getAuthToken(),
      });
      const res = await fetch(url, Object.assign({}, options, { headers }));
      if (res.status === 401) {
        document.getElementById('auth-overlay').classList.remove('hidden');
        throw new Error('Unauthorized');
      }
      return res;
    }

    async function checkInitialAuth() {
      try {
        const res = await fetch('api/auth/check', {
          headers: { 'X-Radar-Token': getAuthToken() }
        }).then(r => r.json());
        if (res.authenticated) {
          document.getElementById('auth-overlay').classList.add('hidden');
          loadDashboard();
        } else {
          document.getElementById('auth-overlay').classList.remove('hidden');
        }
      } catch (e) {
        document.getElementById('auth-overlay').classList.remove('hidden');
      }
    }

    async function submitLogin(e) {
      e.preventDefault();
      const pw = document.getElementById('login-password').value;
      const errEl = document.getElementById('login-error');
      errEl.classList.add('hidden');

      const res = await fetch('api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pw })
      });
      if (res.status === 200) {
        const data = await res.json();
        localStorage.setItem('radar_auth_token', data.token);
        document.getElementById('login-password').value = '';
        document.getElementById('auth-overlay').classList.add('hidden');
        showToast('🔓 인증 완료! 대시보드에 접속되었습니다.');
        loadDashboard();
      } else {
        errEl.classList.remove('hidden');
      }
    }

    function lockDashboard() {
      localStorage.removeItem('radar_auth_token');
      document.cookie = 'radar_auth=; Max-Age=0; path=/';
      document.getElementById('auth-overlay').classList.remove('hidden');
      document.getElementById('login-password').focus();
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      document.getElementById('toast-msg').innerText = msg;
      t.classList.remove('hidden');
      setTimeout(() => t.classList.add('hidden'), 2600);
    }

    function copyText(txt, customToast = '') {
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(txt).catch(() => fallbackCopy(txt));
      } else {
        fallbackCopy(txt);
      }
      showToast(customToast || `📋 복사 완료: ${txt.length > 45 ? txt.slice(0, 45) + '...' : txt}`);
    }

    function fallbackCopy(txt) {
      const ta = document.createElement('textarea');
      ta.value = txt;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try { document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
    }

    function formatModelFullLine(m) {
      const price = m.is_free ? '무료($0)' : `$${m.input_cost_1m}/$${m.output_cost_1m}`;
      const ctx = m.context_length ? `${Math.round(m.context_length / 1024)}K` : '-';
      return `[${m.provider_name}] ${m.name} | 공식ID: ${m.native_id} | OpenRouter: ${m.openrouter_id} | LiteLLM: ${m.litellm_id} | .env: ${m.env_var}=${m.native_id} | 컨텍스트: ${ctx} | 가격(1M): ${price} | 출시: ${m.created_date}`;
    }

    function copySingleModelFull(encodedJson) {
      const m = JSON.parse(decodeURIComponent(encodedJson));
      const text = [
        `모델명: ${m.name} (${m.provider_name})`,
        `공식 Native ID: ${m.native_id}`,
        `OpenRouter ID: ${m.openrouter_id}`,
        `LiteLLM ID: ${m.litellm_id}`,
        `.env 설정: ${m.env_var}=${m.native_id}`,
        `컨텍스트/출력: ${m.context_length} / ${m.max_output_tokens} tokens`,
        `가격(1M 토큰): 입력 $${m.input_cost_1m} / 출력 $${m.output_cost_1m}`,
        `출시일: ${m.created_date}`
      ].join('\\n');
      copyText(text, `📦 [${m.native_id}] 전체 스펙 정보가 복사되었습니다!`);
    }

    function copyProviderAllIds(providerSlug) {
      const rec = cachedRecommendations.find(r => r.provider === providerSlug);
      if (!rec) return;
      const models = rec.all_models || rec.top_models || [];
      const text = models.map(m => m.native_id).join('\\n');
      copyText(text, `📋 ${rec.provider_name} 전체 모델 ID (${models.length}개) 복사 완료!`);
    }

    function copyProviderAllDetails(providerSlug) {
      const rec = cachedRecommendations.find(r => r.provider === providerSlug);
      if (!rec) return;
      const models = rec.all_models || rec.top_models || [];
      const header = `# ${rec.icon} ${rec.provider_name} 사용 가능 전체 모델 목록 (총 ${models.length}종)`;
      const lines = models.map(m => `- ${m.native_id} (OpenRouter: ${m.openrouter_id} | 가격: $${m.input_cost_1m}/$${m.output_cost_1m} | 출시: ${m.created_date})`);
      copyText([header, ...lines].join('\\n'), `📦 ${rec.provider_name} 전체 모델 상세표 (${models.length}개) 복사 완료!`);
    }

    function copyAllProvidersEnv() {
      if (!cachedRecommendations.length) return;
      const lines = cachedRecommendations.map(r => [
        `# ${r.icon} ${r.provider_name} (가성비: ${r.fast?.native_id} / 주력: ${r.flagship?.native_id})`,
        `${r.env_var}=${r.fast?.native_id || ''}`
      ].join('\\n'));
      copyText(lines.join('\\n\\n'), `⚙️ 8대 제조사 추천 .env 설정이 일괄 복사되었습니다!`);
    }

    function copyAllProvidersModels() {
      if (!cachedRecommendations.length) return;
      const blocks = cachedRecommendations.map(r => {
        const models = r.all_models || r.top_models || [];
        return `[${r.provider_name} (${models.length}종)]\\n` + models.map(m => m.native_id).join(', ');
      });
      copyText(blocks.join('\\n\\n'), `📋 8대 제조사 전체 모델 ID 목록이 일괄 복사되었습니다!`);
    }

    function copyFilteredIds() {
      if (!cachedFilteredModels.length) return;
      const text = cachedFilteredModels.map(m => m.native_id).join('\\n');
      copyText(text, `📋 현재 조회된 전체 모델 ID (${cachedFilteredModels.length}개) 복사 완료!`);
    }

    function copyFilteredDetails() {
      if (!cachedFilteredModels.length) return;
      const text = cachedFilteredModels.map(m => formatModelFullLine(m)).join('\\n');
      copyText(text, `📦 현재 조회된 전체 모델 상세 정보 (${cachedFilteredModels.length}개) 복사 완료!`);
    }

    function toggleProviderExpand(providerSlug) {
      const el = document.getElementById(`all-chips-${providerSlug}`);
      const btn = document.getElementById(`expand-btn-${providerSlug}`);
      if (!el) return;
      const isHidden = el.classList.contains('hidden');
      el.classList.toggle('hidden', !isHidden);
      btn.innerText = isHidden ? '▲ 전체 모델 목록 접기' : '▼ 이 제조사 전체 모델 모두 펼치기';
    }

    function switchTab(tab) {
      ['rec', 'all', 'changes', 'api'].forEach(t => {
        document.getElementById(`tab-${t}`).classList.toggle('hidden', t !== tab);
        const btn = document.getElementById(`tab-btn-${t}`);
        if (t === tab) {
          btn.className = 'tab-btn px-4 py-2 rounded-xl text-sm font-semibold bg-sky-500 text-slate-950 transition';
        } else {
          btn.className = 'tab-btn px-4 py-2 rounded-xl text-sm font-medium bg-slate-900 text-slate-300 hover:bg-slate-800 transition';
        }
      });
      if (tab === 'all') loadModels();
      if (tab === 'changes') loadChanges();
    }

    async function loadDashboard() {
      const statusRes = await apiFetch('api/status').then(r => r.json());
      document.getElementById('sync-badge').innerText = `🕒 최근 동기화: ${statusRes.last_sync_iso}`;
      document.getElementById('stat-total').innerText = `${statusRes.total_active_models}개 모델`;
      const orHub = statusRes.hub_status?.openrouter || {};
      const llHub = statusRes.hub_status?.litellm || {};
      document.getElementById('stat-or-lat').innerText = `OpenRouter 수신 완료 (${orHub.latency_ms || 0}ms)`;
      document.getElementById('stat-litellm').innerText = `${(llHub.count || 0).toLocaleString()}개 스펙`;
      document.getElementById('stat-free').innerText = `${statusRes.free_models_count}개 무료`;

      const configuredKeys = statusRes.hub_status?.direct_keys?.configured || [];
      document.getElementById('stat-keys').innerText = configuredKeys.length > 0
        ? configuredKeys.join(', ')
        : '무인증 허브 모드 (키 없이 100% 작동)';

      const recs = await apiFetch('api/recommendations').then(r => r.json());
      cachedRecommendations = recs.recommendations || [];
      renderRecommendations(cachedRecommendations);
    }

    function renderModelCardRow(label, badgeColor, m, envVar) {
      if (!m) return '';
      const price = m.is_free ? '무료 ($0)' : `$${m.input_cost_1m} / $${m.output_cost_1m}`;
      const ctx = m.context_length ? `${Math.round(m.context_length / 1024)}K` : '-';
      const encoded = encodeURIComponent(JSON.stringify(m));
      return `
        <div class="bg-slate-900/90 border border-slate-800/90 rounded-xl p-3 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-semibold px-2 py-0.5 rounded-md ${badgeColor}">${label}</span>
            <div class="flex items-center gap-2 text-[11px] text-slate-400">
              <span>컨텍스트 ${ctx}</span>
              <span>·</span>
              <span class="text-sky-300 font-medium">${price}</span>
              <span>·</span>
              <span>출시 ${m.created_date}</span>
            </div>
          </div>
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div class="text-xs font-bold text-white">${m.name}</div>
              <div class="text-[11px] text-slate-400 mt-0.5">
                공식 ID: <code class="text-emerald-400 font-semibold">${m.native_id}</code>
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-1.5">
              <button onclick="copyText('${m.native_id}')" class="copy-chip text-[11px] bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-lg text-emerald-300 font-medium transition">
                📋 공식 ID
              </button>
              <button onclick="copyText('${envVar}=${m.native_id}')" class="copy-chip text-[11px] bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-lg text-sky-300 font-medium transition">
                ⚙️ .env 복사
              </button>
              <button onclick="copySingleModelFull('${encoded}')" class="copy-chip text-[11px] bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-lg text-amber-300 font-medium transition">
                📦 전체 정보 복사
              </button>
              <button onclick="inspectModel('${m.openrouter_id}', '${m.native_id}', '${m.provider}')" class="text-[11px] bg-sky-500/15 hover:bg-sky-500/30 border border-sky-500/30 text-sky-300 px-2.5 py-1 rounded-lg font-semibold transition">
                🩺 실시간 가동률
              </button>
            </div>
          </div>
        </div>
      `;
    }

    function renderRecommendations(recs) {
      const grid = document.getElementById('rec-grid');
      grid.innerHTML = recs.map(r => {
        const allModels = r.all_models || r.top_models || [];
        const topChips = (r.top_models || []).map(m => `
          <button onclick="copyText('${m.native_id}')" class="copy-chip text-[11px] bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg text-slate-300 transition flex items-center gap-1">
            <span>${m.native_id}</span>
            <span class="text-[10px] text-slate-500">(${m.created_date.slice(5)})</span>
          </button>
        `).join('');

        const fullChips = allModels.map(m => `
          <button onclick="copyText('${m.native_id}')" class="copy-chip text-[11px] bg-slate-950 border border-slate-800 px-2.5 py-1 rounded-lg text-emerald-300 transition flex items-center gap-1">
            <span>${m.native_id}</span>
            <span class="text-[10px] text-slate-500">(${m.created_date.slice(5)})</span>
          </button>
        `).join('');

        return `
          <div class="glass rounded-2xl p-5 space-y-3.5 flex flex-col justify-between">
            <div class="space-y-3">
              <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                <div class="flex items-center gap-2">
                  <span class="text-xl">${r.icon}</span>
                  <div>
                    <h3 class="text-sm font-bold text-white">${r.provider_name}</h3>
                    <span class="text-[11px] text-slate-400">현재 즉시 사용 가능: <b>${r.total_active}개</b> 모델</span>
                  </div>
                </div>
                <div class="flex flex-wrap items-center gap-1.5">
                  <button onclick="copyProviderAllIds('${r.provider}')" class="text-[11px] font-semibold bg-emerald-500/15 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-300 px-2.5 py-1.5 rounded-lg transition">
                    📋 전체 모델 ID 복사 (${r.total_active}개)
                  </button>
                  <button onclick="copyProviderAllDetails('${r.provider}')" class="text-[11px] font-medium bg-indigo-500/15 hover:bg-indigo-500/30 border border-indigo-500/30 text-indigo-300 px-2.5 py-1.5 rounded-lg transition">
                    📦 전체 상세표 복사
                  </button>
                </div>
              </div>

              ${renderModelCardRow('⚡ 가성비·속도 주력 (봇 .env 추천 1순위)', 'bg-emerald-500/20 text-emerald-300', r.fast, r.env_var)}
              ${renderModelCardRow('🏆 최고 성능 플래그십 주력', 'bg-amber-500/20 text-amber-300', r.flagship, r.env_var)}
            </div>

            <div class="pt-2 border-t border-slate-800/60 space-y-2">
              <div class="flex items-center justify-between text-[11px]">
                <span class="text-slate-400">최근 출시 모델 (클릭 시 복사):</span>
                <div class="flex items-center gap-2">
                  <button id="expand-btn-${r.provider}" onclick="toggleProviderExpand('${r.provider}')" class="text-sky-400 hover:underline font-medium">
                    ▼ 이 제조사 전체 모델(${r.total_active}개) 모두 펼치기
                  </button>
                  <span class="text-slate-600">|</span>
                  <button onclick="filterByProvider('${r.provider}')" class="text-slate-400 hover:text-white">
                    비교표로 보기 →
                  </button>
                </div>
              </div>
              <div class="flex flex-wrap gap-1.5">${topChips}</div>

              <div id="all-chips-${r.provider}" class="hidden pt-2 mt-2 border-t border-slate-800/50 space-y-2">
                <div class="flex items-center justify-between text-[11px] text-emerald-400 font-semibold">
                  <span>✨ ${r.provider_name} 전체 사용 가능 모델 (${r.total_active}종 전수 목록)</span>
                  <button onclick="copyProviderAllIds('${r.provider}')" class="underline">전체 복사하기</button>
                </div>
                <div class="flex flex-wrap gap-1.5">${fullChips}</div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function filterByProvider(prov) {
      document.getElementById('filter-provider').value = prov;
      switchTab('all');
    }

    async function loadModels() {
      const provider = document.getElementById('filter-provider').value;
      const tier = document.getElementById('filter-tier').value;
      const modality = document.getElementById('filter-modality').value;
      const search = document.getElementById('filter-search').value;

      const params = new URLSearchParams({ provider, tier, modality, search });
      const data = await apiFetch(`api/models?${params.toString()}`).then(r => r.json());
      const models = data.models || [];
      cachedFilteredModels = models;
      document.getElementById('model-count-label').innerText = `총 ${models.length}개 모델`;

      const tbody = document.getElementById('models-tbody');
      tbody.innerHTML = models.slice(0, 250).map(m => {
        const ctx = m.context_length ? `${Math.round(m.context_length / 1024)}K` : '-';
        const maxOut = m.max_output_tokens ? `${Math.round(m.max_output_tokens / 1024)}K` : '-';
        const price = m.is_free
          ? '<span class="text-emerald-400 font-semibold">무료 ($0)</span>'
          : `$${m.input_cost_1m} / $${m.output_cost_1m}`;

        const badges = [];
        if (m.supports_vision) badges.push('<span class="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[10px]">비전</span>');
        if (m.supports_tools) badges.push('<span class="px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 text-[10px]">도구</span>');
        if (m.supports_reasoning) badges.push('<span class="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px]">추론</span>');
        if (m.in_litellm) badges.push('<span class="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px]">LiteLLM</span>');

        const statusBadge = m.status === 'active'
          ? '<span class="text-emerald-400 font-medium">● 정상 가동</span>'
          : `<span class="text-amber-400 font-medium">⚠️ 만료예정 (${m.expiration_date})</span>`;

        const encoded = encodeURIComponent(JSON.stringify(m));

        return `
          <tr class="hover:bg-slate-900/50 transition">
            <td class="py-3 px-4">
              <div class="font-semibold text-white">${m.provider_icon} ${m.name}</div>
              <div class="text-[11px] text-slate-400">${m.provider_name} · 컷오프: ${m.knowledge_cutoff}</div>
            </td>
            <td class="py-3 px-4">
              <button onclick="copyText('${m.native_id}')" class="copy-chip bg-slate-900 border border-slate-700 px-2.5 py-1 rounded-lg text-emerald-300 font-mono text-xs">
                ${m.native_id} 📋
              </button>
            </td>
            <td class="py-3 px-4">
              <button onclick="copyText('${m.openrouter_id}')" class="copy-chip bg-slate-900 border border-slate-800 px-2 py-1 rounded-lg text-slate-300 font-mono text-[11px]">
                ${m.openrouter_id}
              </button>
            </td>
            <td class="py-3 px-4 text-slate-300">${ctx} / ${maxOut}</td>
            <td class="py-3 px-4"><div class="flex flex-wrap gap-1">${badges.join('')}</div></td>
            <td class="py-3 px-4 text-slate-200">${price}</td>
            <td class="py-3 px-4">
              <div>${statusBadge}</div>
              <div class="text-[10px] text-slate-400">${m.created_date}</div>
            </td>
            <td class="py-3 px-4 text-right">
              <div class="flex items-center justify-end gap-1.5">
                <button onclick="copySingleModelFull('${encoded}')" class="bg-amber-500/15 hover:bg-amber-500/30 border border-amber-500/30 text-amber-300 px-2 py-1.5 rounded-lg text-[11px] font-medium">
                  📦 전체복사
                </button>
                <button onclick="inspectModel('${m.openrouter_id}', '${m.native_id}', '${m.provider}')" class="bg-sky-500/15 hover:bg-sky-500/30 border border-sky-500/30 text-sky-300 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold">
                  🩺 진단
                </button>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }

    async function inspectModel(openrouterId, nativeId, provider) {
      const modal = document.getElementById('ping-modal');
      const body = document.getElementById('ping-modal-body');
      document.getElementById('ping-modal-title').innerText = `🩺 ${nativeId} 실시간 가동률 & 스냅샷 진단`;
      document.getElementById('ping-modal-sub').innerText = `OpenRouter ID: ${openrouterId} · 실시간 클라우드 엔드포인트 조회 중...`;
      body.innerHTML = `<div class="py-8 text-center text-slate-400">⏳ 실시간 글로벌 엔드포인트 상태 및 응답 속도를 측정하고 있습니다...</div>`;
      modal.classList.remove('hidden');

      const res = await apiFetch('api/ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: openrouterId, native_id: nativeId, provider })
      }).then(r => r.json());

      const epInfo = res.endpoint_info || {};
      const keyTest = res.key_test || {};
      const snaps = (epInfo.snapshots || []).map(s => `
        <button onclick="copyText('${s}')" class="copy-chip bg-slate-900 border border-slate-700 px-2.5 py-1 rounded-lg text-emerald-300 font-mono text-xs">
          ${s} 📋
        </button>
      `).join(' ');

      const epRows = (epInfo.endpoints || []).map(e => `
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div class="font-bold text-white">${e.provider_name} <span class="text-[11px] font-normal text-slate-400">(${e.tag})</span></div>
            <div class="text-[11px] text-slate-400 font-mono mt-0.5">${e.name}</div>
          </div>
          <div class="flex items-center gap-3 text-xs">
            <span class="px-2.5 py-1 rounded-lg bg-emerald-500/15 text-emerald-300 font-semibold">
              5분 가동률: ${e.uptime_5m}%
            </span>
            <span class="px-2.5 py-1 rounded-lg bg-sky-500/15 text-sky-300">
              24시간: ${e.uptime_1d}%
            </span>
          </div>
        </div>
      `).join('');

      body.innerHTML = `
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-3.5 space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-semibold text-slate-300">🔑 API 호출 검증 상태 (${keyTest.via || '-'})</span>
            <span class="${keyTest.ok ? 'text-emerald-400' : 'text-amber-400'} font-bold">
              ${keyTest.ok ? '✅ 정상 확인' : '⚠️ 확인 필요'} (${keyTest.latency_ms || 0}ms)
            </span>
          </div>
          <div class="text-slate-400">${keyTest.message || ''}</div>
        </div>

        ${snaps ? `
        <div class="space-y-1.5">
          <div class="text-slate-300 font-semibold">📌 감지된 실제 날짜별 스냅샷 모델명 (클릭 시 복사):</div>
          <div class="flex flex-wrap gap-2">${snaps}</div>
        </div>` : ''}

        <div class="space-y-2">
          <div class="text-slate-300 font-semibold">☁️ 현재 이 모델을 서비스 중인 글로벌 클라우드 백엔드 (${epInfo.endpoint_count || 0}개):</div>
          ${epRows || '<div class="text-slate-400">엔드포인트 상세 정보가 없습니다.</div>'}
        </div>
      `;
    }

    function closePingModal() {
      document.getElementById('ping-modal').classList.add('hidden');
    }

    async function loadChanges() {
      const data = await apiFetch('api/changes').then(r => r.json());
      const list = data.changelog || [];
      const container = document.getElementById('changes-container');
      if (!list.length) {
        container.innerHTML = `<div class="text-xs text-slate-400 py-6 text-center">아직 감지된 모델 추가/단종 변경 이력이 없습니다. (초기 베이스라인 스냅샷 저장 완료)</div>`;
        return;
      }
      container.innerHTML = list.map(item => `
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 text-xs">
          <div class="font-bold text-sky-400">🕒 ${item.timestamp}</div>
          ${item.added?.length ? `<div>✨ <b>신규 출시 (${item.added.length}종):</b> ${item.added.map(x => `<code>${x.native_id}</code>`).join(', ')}</div>` : ''}
          ${item.expiring?.length ? `<div>⚠️ <b>단종 예정 (${item.expiring.length}종):</b> ${item.expiring.map(x => `<code>${x.native_id}</code>`).join(', ')}</div>` : ''}
          ${item.removed?.length ? `<div>🚨 <b>제거됨 (${item.removed.length}종):</b> ${item.removed.map(x => `<code>${x.native_id}</code>`).join(', ')}</div>` : ''}
        </div>
      `).join('');
    }

    async function triggerSync() {
      const btn = document.getElementById('btn-sync');
      btn.innerText = '⏳ 동기화 중...';
      await apiFetch('api/sync', { method: 'POST' });
      await loadDashboard();
      btn.innerHTML = '<span>🔄</span> 지금 즉시 동기화';
      showToast('✅ 최신 AI 모델 목록 동기화가 완료되었습니다!');
    }

    async function sendTelegramReport() {
      const res = await apiFetch('api/telegram/test', { method: 'POST' }).then(r => r.json());
      if (res.ok) {
        showToast('✈️ 텔레그램으로 최신 AI 모델 요약 리포트를 발송했습니다!');
      } else {
        showToast('⚠️ 텔레그램 토큰/채팅방 ID를 먼저 설정해 주세요.');
        openKeyModal();
      }
    }

    function openKeyModal() {
      document.getElementById('key-modal').classList.remove('hidden');
    }

    function closeKeyModal() {
      document.getElementById('key-modal').classList.add('hidden');
    }

    async function saveSettings() {
      const payload = {};
      const fields = [
        ['DASHBOARD_PASSWORD', 'input-dashboard-pw'],
        ['OPENROUTER_API_KEY', 'input-or-key'],
        ['GEMINI_API_KEY', 'input-gemini-key'],
        ['OPENAI_API_KEY', 'input-openai-key'],
        ['ANTHROPIC_API_KEY', 'input-anthropic-key'],
        ['DEEPSEEK_API_KEY', 'input-deepseek-key'],
        ['TELEGRAM_BOT_TOKEN', 'input-tg-token'],
        ['TELEGRAM_CHAT_ID', 'input-tg-chat'],
      ];
      fields.forEach(([k, id]) => {
        const val = document.getElementById(id).value.trim();
        if (val) payload[k] = val;
      });
      const res = await apiFetch('api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).then(r => r.json());
      if (res.token) {
        localStorage.setItem('radar_auth_token', res.token);
      }
      closeKeyModal();
      await triggerSync();
      showToast('💾 설정이 저장되고 즉시 반영되었습니다!');
    }

    checkInitialAuth();
  </script>
</body>
</html>
"""
