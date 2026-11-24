// Shoi Frontend PWA Application Logic
const API_BASE = window.location.origin;

// State
let token = localStorage.getItem('shoi_token') || null;
let userId = localStorage.getItem('shoi_user_id') || null;
let sessionId = localStorage.getItem('shoi_session_id') || ('shoi_sess_' + Math.random().toString(36).substring(2, 12));
localStorage.setItem('shoi_session_id', sessionId);
let lastAudioBase64 = null;
let lastReplyText = null;
let recognition = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let toastTimeout = null;

// DOM Elements
const micBtn = document.getElementById('micBtn');
const micWave = document.getElementById('micWave');
const voiceStatus = document.getElementById('voiceStatus');
const voiceStatusText = document.getElementById('voiceStatusText');
const micInstruction = document.getElementById('micInstruction');
const voiceResponseCard = document.getElementById('voiceResponseCard');
const userQueryBubble = document.getElementById('userQueryBubble');
const userQueryText = document.getElementById('userQueryText');
const responseText = document.getElementById('responseText');
const citationsContainer = document.getElementById('citationsContainer');
const audioPlayer = document.getElementById('audioPlayer');
const replayVoiceBtn = document.getElementById('replayVoiceBtn');
const emergencyModal = document.getElementById('emergencyModal');
const audioEqualizer = document.getElementById('audioEqualizer');
const micIcon = document.getElementById('micIcon');
const voiceSpeedBtn = document.getElementById('voiceSpeedBtn');
let isSlowSpeed = localStorage.getItem('shoi_slow_voice') === 'true';

// Non-blocking UI Toast
function showToast(message, isError = false) {
  let toast = document.getElementById('shoiToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'shoiToast';
    toast.className = 'shoi-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = 'shoi-toast' + (isError ? ' error' : '');
  void toast.offsetWidth; // Trigger reflow for smooth animation
  toast.classList.add('show');

  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.classList.remove('show');
  }, 3200);
}

// Unlock audio context on user gesture to avoid browser autoplay blocks
function primeAudioPlayback() {
  if (audioPlayer && audioPlayer.paused && !audioPlayer.src) {
    audioPlayer.src = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';
    audioPlayer.play().then(() => {
      audioPlayer.pause();
      audioPlayer.currentTime = 0;
    }).catch(() => {});
  }
}

// Initialize App
document.addEventListener('DOMContentLoaded', async () => {
  // Register Service Worker for PWA offline caching
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {
      navigator.serviceWorker.register('/pwa/service-worker.js').catch((err) => {
        console.log('SW registration note:', err);
      });
    });
  }

  setupNavigation();
  setupSpeechAndAudioPipeline();
  await ensureAnonymousAuth();
  setupPeriodTracker();
  setupMoodTracker();
  setupPCOSChecker();
  setupPregnancyTracker();
  setupSettings();
  setupQuickQuestions();
  setupVoiceSpeedToggle();
  setupSharedPhonePrivacyFeatures();
});

// Helper for auth headers
function getAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// 1. Authentication State & UI Sync
function updateAuthUIState() {
  const loggedInBox = document.getElementById('loggedInSettingsBox');
  const loggedOutBox = document.getElementById('loggedOutSettingsBox');
  const idDisplay = document.getElementById('anonymousUserIdDisplay');
  const modalVal = document.getElementById('uniqueIdModalValue');
  const logoutIdVal = document.getElementById('logoutModalUserId');

  if (userId && token) {
    if (loggedInBox) loggedInBox.style.display = 'block';
    if (loggedOutBox) loggedOutBox.style.display = 'none';
    if (idDisplay) idDisplay.value = userId;
    if (modalVal) modalVal.textContent = userId;
    if (logoutIdVal) logoutIdVal.textContent = userId;
  } else {
    if (loggedInBox) loggedInBox.style.display = 'none';
    if (loggedOutBox) loggedOutBox.style.display = 'block';
    if (idDisplay) idDisplay.value = '';
    if (modalVal) modalVal.textContent = '';
    if (logoutIdVal) logoutIdVal.textContent = '';
  }
}

function showUniqueIdAlert(customTitle = null) {
  const modal = document.getElementById('uniqueIdAlertModal');
  const modalTitle = document.getElementById('uniqueIdModalTitle');
  const modalVal = document.getElementById('uniqueIdModalValue');
  if (!modal) return;
  if (customTitle && modalTitle) modalTitle.textContent = customTitle;
  if (modalVal && userId) modalVal.textContent = userId;
  modal.style.display = 'flex';
}

async function ensureAnonymousAuth() {
  let isBrandNew = false;
  if (!token || !userId) {
    try {
      const res = await fetch(`${API_BASE}/auth/anonymous`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ age_group: '20-29', language: 'bn' })
      });
      if (res.ok) {
        const data = await res.json();
        token = data.access_token;
        userId = data.user_id;
        localStorage.setItem('shoi_token', token);
        localStorage.setItem('shoi_user_id', userId);
        isBrandNew = true;
      }
    } catch (e) {
      console.warn('Anonymous auth offline/error:', e);
    }
  }

  updateAuthUIState();

  // Alert user of their new Unique ID if newly created or alert hasn't been acknowledged
  if (userId && (isBrandNew || localStorage.getItem('shoi_id_alert_shown') !== userId)) {
    setTimeout(() => {
      showUniqueIdAlert('🌸 স্বাগতম! আপনার গোপন ইউনিক আইডি');
    }, 700);
  }
}

// 2. Navigation Tabs
function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const screens = document.querySelectorAll('.screen');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      primeAudioPlayback();
      const targetId = item.getAttribute('data-target');

      navItems.forEach(n => n.classList.remove('active'));
      screens.forEach(s => s.classList.remove('active'));

      item.classList.add('active');
      const targetScreen = document.getElementById(targetId);
      if (targetScreen) targetScreen.classList.add('active');

      // Trigger refreshes for active tab
      if (targetId === 'screen-period') loadPeriodData();
      if (targetId === 'screen-mood') loadMoodData();
      if (targetId === 'screen-pregnancy') loadPregnancyData();
    });
  });

  // Emergency quick button
  document.getElementById('emergencyTriggerBtn').addEventListener('click', () => {
    emergencyModal.style.display = 'flex';
  });
  document.getElementById('dismissEmergencyBtn').addEventListener('click', () => {
    emergencyModal.style.display = 'none';
  });
}

// 3. Voice & Speech Recognition Pipeline (Dual: Web Speech API + MediaRecorder Fallback)
function setupSpeechAndAudioPipeline() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'bn-BD'; // Standard Bangla
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {
      isRecording = true;
      if (navigator.vibrate) try { navigator.vibrate(35); } catch (e) {}
      setVoiceState('listening');
    };

    recognition.onresult = async (event) => {
      let interim = '';
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      if (interim && isRecording) {
        voiceStatusText.textContent = `🎙️ "${interim}"`;
      }

      if (finalTranscript) {
        console.log('Recognized speech:', finalTranscript);
        if (navigator.vibrate) try { navigator.vibrate(40); } catch (e) {}
        setVoiceState('thinking');
        await sendVoiceQuery(finalTranscript);
      }
    };

    recognition.onerror = (event) => {
      console.warn('Speech recognition status:', event.error);
      isRecording = false;
      setVoiceState('idle');
      if (event.error === 'not-allowed') {
        showToast('মাইক্রোফোন ব্যবহারের অনুমতি দিন।', true);
      } else if (event.error === 'no-speech') {
        voiceStatusText.textContent = 'কোনো কথা শোনা যায়নি। আবার বোতাম চেপে বলুন।';
      }
    };

    recognition.onend = () => {
      isRecording = false;
      if (voiceStatus.className.includes('listening')) {
        setVoiceState('idle');
      }
    };
  }

  micBtn.addEventListener('click', async () => {
    primeAudioPlayback();
    if (navigator.vibrate) try { navigator.vibrate(30); } catch (e) {}

    // If currently speaking, interrupt and stop audio immediately
    if (voiceStatus.className.includes('speaking')) {
      if (audioPlayer) {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      setVoiceState('idle');
      return;
    }

    // If currently recording, stop
    if (isRecording) {
      if (recognition) {
        try { recognition.stop(); } catch (e) {}
      }
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      }
      isRecording = false;
      setVoiceState('thinking');
      return;
    }

    // Start recording
    if (recognition) {
      try {
        recognition.start();
        return;
      } catch (e) {
        console.warn('Recognition start failed, trying MediaRecorder:', e);
      }
    }

    // MediaRecorder fallback (Firefox, Safari, WebViews)
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          stream.getTracks().forEach(track => track.stop());
          const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
          if (audioBlob.size > 0) {
            setVoiceState('thinking');
            await sendVoiceAudio(audioBlob);
          } else {
            setVoiceState('idle');
          }
        };

        mediaRecorder.start();
        isRecording = true;
        setVoiceState('listening');
      } catch (err) {
        console.error('Microphone access denied or unavailable:', err);
        showToast('মাইক্রোফোন চালু করা সম্ভব হয়নি। অনুগ্রহ করে অনুমতি দিন বা লিখে জানান।', true);
        setVoiceState('idle');
      }
    } else {
      // Manual input toggle if audio capture is completely unsupported
      const chatDrawer = document.getElementById('textChatDrawer');
      if (chatDrawer) chatDrawer.style.display = 'block';
      showToast('আপনার ব্রাউজারে ভয়েস সমর্থিত নয়। নিচে লিখে প্রশ্ন করুন।');
    }
  });

  // Replay / Stop audio toggle
  replayVoiceBtn.addEventListener('click', () => {
    primeAudioPlayback();
    if (voiceStatus.className.includes('speaking')) {
      if (audioPlayer) {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      setVoiceState('idle');
      return;
    }
    if (lastAudioBase64) {
      audioPlayer.src = `data:audio/mp3;base64,${lastAudioBase64}`;
      setVoiceState('speaking');
      audioPlayer.play().catch(() => setVoiceState('idle'));
      audioPlayer.onended = () => setVoiceState('idle');
    } else if (lastReplyText && 'speechSynthesis' in window) {
      speakNativeText(lastReplyText);
    }
  });

  // Context-Aware Text Chat & Memory Manager Integration
  const toggleBtn = document.getElementById('toggleTextChatBtn');
  const chatDrawer = document.getElementById('textChatDrawer');
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendChatBtn');
  const chatMessagesList = document.getElementById('chatMessagesList');
  const chatSessionTitle = document.getElementById('chatSessionTitle');
  const newChatSessionBtn = document.getElementById('newChatSessionBtn');
  const openMemoriesBtn = document.getElementById('openMemoriesBtn');
  const patientMemoriesModal = document.getElementById('patientMemoriesModal');
  const closeMemoriesModalBtn = document.getElementById('closeMemoriesModalBtn');
  const memoriesListContainer = document.getElementById('memoriesListContainer');

  let currentConvId = localStorage.getItem('shoi_conv_id') || null;

  function renderWelcomeStarters() {
    if (!chatMessagesList) return;
    chatMessagesList.innerHTML = `
      <div class="chat-welcome-card" id="chatWelcomeCard">
        <div class="welcome-badge">🌸 আপুর সাথে কথা বলুন</div>
        <div class="welcome-text">
          <strong>আপু, আমি তোমার ব্যক্তিগত স্বাস্থ্য সই।</strong>
          <p>মাসিক, সাদা স্রাব, স্তন, পিসিওএস কিংবা গোপন শারীরিক অস্বস্তি—যেকোনো বিষয়ে নিঃসংকোচে কথা বলো। তোমার সব তথ্য সম্পূর্ণ সুরক্ষিত ও গোপন থাকবে।</p>
        </div>
        <div class="starter-chips-container">
          <span class="starter-label">কী নিয়ে কথা বলতে চাও? বেছে নাও:</span>
          <div class="starter-chips">
            <button class="starter-chip" data-prompt="আপু, আমার মাসিক নিয়মিত হয় না। এটা নিয়ে কথা বলতে চাই।">🩸 মাসিক নিয়মিত হচ্ছে না</button>
            <button class="starter-chip" data-prompt="আমার সাদা স্রাব নিয়ে কিছু প্রশ্ন আছে।">🤍 সাদা স্রাব নিয়ে প্রশ্ন</button>
            <button class="starter-chip" data-prompt="আমার PCOS হয়েছে কি না, সেটা নিয়ে চিন্তিত।">🩺 PCOS হয়েছে কি না?</button>
            <button class="starter-chip" data-prompt="মাসিকের সময় তীব্র পেটব্যথা কমানোর ঘরোয়া উপায় কি?">⚡ পিরিয়ডে পেটে ব্যথা</button>
            <button class="starter-chip" data-prompt="আমার স্তনে কিছু পরিবর্তন লক্ষ্য করছি। এ বিষয়ে জানতে চাই।">🎀 স্তনে ব্যথা বা পরিবর্তন</button>
            <button class="starter-chip" data-prompt="প্রস্রাবের সময় জ্বালাপোড়া ও অস্বস্তি হচ্ছে।">💧 প্রস্রাবে জ্বালাপোড়া</button>
            <button class="starter-chip" data-prompt="আমার মানসিক অবস্থা ও হরমোনের পরিবর্তন নিয়ে সাহায্য দরকার।">💭 মেজাজ খিটখিটে ও মানসিক অস্বস্তি</button>
            <button class="starter-chip" data-prompt="ব্যক্তিগত স্বাস্থ্য নিয়ে কিছু কথা জানতে চাই, যা কাউকে বলতে পারি না।">🔒 ব্যক্তিগত গোপন স্বাস্থ্যকথা</button>
          </div>
        </div>
      </div>
    `;

    chatMessagesList.querySelectorAll('.starter-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        primeAudioPlayback();
        const prompt = btn.getAttribute('data-prompt');
        if (prompt) {
          sendContextChatMessage(prompt);
        }
      });
    });
  }

  async function loadConversationHistory() {
    if (!chatMessagesList) return;
    if (!currentConvId) {
      renderWelcomeStarters();
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/v1/conversations/${currentConvId}/messages`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const msgs = await res.json();
        chatMessagesList.innerHTML = '';
        if (!msgs || msgs.length === 0) {
          renderWelcomeStarters();
        } else {
          msgs.forEach(m => renderChatBubble(m.role, m.content, m.citations));
          chatMessagesList.scrollTop = chatMessagesList.scrollHeight;
        }
      } else {
        renderWelcomeStarters();
      }
    } catch (err) {
      console.warn('Could not load chat history:', err);
      renderWelcomeStarters();
    }
  }

  function renderChatBubble(role, content, citations, contextUsed) {
    if (!chatMessagesList) return;
    const welcomeCard = document.getElementById('chatWelcomeCard');
    if (welcomeCard) {
      welcomeCard.remove();
    }
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    bubble.textContent = content;

    if (role === 'assistant') {
      const badgesDiv = document.createElement('div');
      badgesDiv.className = 'chat-bubble-badges';

      if (contextUsed && contextUsed.patient_memory) {
        const memBadge = document.createElement('span');
        memBadge.className = 'chat-badge memory';
        memBadge.textContent = '🧠 মেমোরি সংযুক্ত';
        badgesDiv.appendChild(memBadge);
      }

      // 1-tap Listen button to hear the full answer aloud
      const speakBtn = document.createElement('button');
      speakBtn.className = 'chat-badge listen-btn';
      speakBtn.innerHTML = '🔊 শুনুন';
      speakBtn.title = 'পুরো উত্তরটি শুনুন';
      speakBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        primeAudioPlayback();
        speakNativeText(content);
      });
      badgesDiv.appendChild(speakBtn);

      if (badgesDiv.children.length > 0) {
        bubble.appendChild(badgesDiv);
      }
    }

    chatMessagesList.appendChild(bubble);
    chatMessagesList.scrollTop = chatMessagesList.scrollHeight;
  }

  async function sendContextChatMessage(text) {
    renderChatBubble('user', text);
    chatInput.value = '';
    sendBtn.disabled = true;
    sendBtn.textContent = '...';

    try {
      const res = await fetch(`${API_BASE}/api/v1/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          conversation_id: currentConvId,
          message: text
        })
      });

      if (res.ok) {
        const data = await res.json();
        currentConvId = data.conversation_id;
        localStorage.setItem('shoi_conv_id', currentConvId);
        renderChatBubble('assistant', data.response, data.sources, data.context_used);

        // Also update voice card and speak if needed
        lastReplyText = data.response;
        responseText.textContent = data.response;
        voiceResponseCard.style.display = 'block';

        if (data.safety_flags && data.safety_flags.includes('crisis_detected')) {
          if (emergencyModal) emergencyModal.style.display = 'flex';
        }
      } else {
        renderChatBubble('assistant', 'দুঃখিত আপু, উত্তর প্রক্রিয়াকরণে সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।');
      }
    } catch (err) {
      console.error('Chat error:', err);
      renderChatBubble('assistant', 'নেটওয়ার্ক সংযোগ নেই বা ত্রুটি দেখা দিয়েছে।');
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = 'পাঠান';
    }
  }

  toggleBtn.addEventListener('click', () => {
    primeAudioPlayback();
    const isHidden = chatDrawer.style.display === 'none';
    chatDrawer.style.display = isHidden ? 'block' : 'none';
    toggleBtn.textContent = isHidden ? '❌ চ্যাট বন্ধ করুন' : '⌨️ লিখে জিজ্ঞাসা করুন';
    if (isHidden) {
      chatInput.focus();
      loadConversationHistory();
    }
  });

  sendBtn.addEventListener('click', () => {
    primeAudioPlayback();
    const text = chatInput.value.trim();
    if (text) {
      sendContextChatMessage(text);
    }
  });

  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      sendBtn.click();
    }
  });

  if (newChatSessionBtn) {
    newChatSessionBtn.addEventListener('click', async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/conversations`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders()
          },
          body: JSON.stringify({ title: 'নতুন আলোচনা' })
        });
        if (res.ok) {
          const data = await res.json();
          currentConvId = data.id;
          localStorage.setItem('shoi_conv_id', currentConvId);
          if (chatMessagesList) renderWelcomeStarters();
          if (chatSessionTitle) chatSessionTitle.textContent = '💬 নতুন আলোচনা';
          showToast('নতুন কথোপকথন তৈরি হয়েছে।');
        }
      } catch (e) {
        currentConvId = null;
        localStorage.removeItem('shoi_conv_id');
        if (chatMessagesList) renderWelcomeStarters();
        showToast('নতুন সেশন শুরু হয়েছে।');
      }
    });
  }

  async function loadPatientMemoriesUI() {
    if (!memoriesListContainer) return;
    memoriesListContainer.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">তথ্য লোড হচ্ছে...</p>';
    try {
      const res = await fetch(`${API_BASE}/api/v1/patient/memories`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const mems = await res.json();
        if (mems.length === 0) {
          memoriesListContainer.innerHTML = '<p style="color:var(--text-muted);font-size:13px;padding:12px 0;">এখনও কোনো স্বাস্থ্য তথ্য সংরক্ষিত নেই। কথোপকথনে মাসিকের দৈর্ঘ্য বা লক্ষণ শেয়ার করলে সই তা স্বয়ংক্রিয়ভাবে মনে রাখবে।</p>';
          return;
        }
        memoriesListContainer.innerHTML = '';
        mems.forEach(m => {
          const card = document.createElement('div');
          card.className = 'memory-item-card';
          card.innerHTML = `
            <div class="memory-item-content">
              <h4>${m.category} • ${m.key}</h4>
              <p>${m.value}</p>
            </div>
            <button class="memory-del-btn" data-id="${m.id}" title="মুছুন">🗑️</button>
          `;
          card.querySelector('.memory-del-btn').addEventListener('click', async (e) => {
            const memId = e.target.getAttribute('data-id');
            const delRes = await fetch(`${API_BASE}/api/v1/patient/memories/${memId}`, {
              method: 'DELETE',
              headers: getAuthHeaders()
            });
            if (delRes.ok) {
              showToast('তথ্যটি সফলভাবে মুছে ফেলা হয়েছে।');
              loadPatientMemoriesUI();
            }
          });
          memoriesListContainer.appendChild(card);
        });
      }
    } catch (e) {
      memoriesListContainer.innerHTML = '<p style="color:red;font-size:13px;">মেমোরি লোড করা যায়নি।</p>';
    }
  }

  if (openMemoriesBtn) {
    openMemoriesBtn.addEventListener('click', () => {
      if (patientMemoriesModal) {
        patientMemoriesModal.style.display = 'flex';
        loadPatientMemoriesUI();
      }
    });
  }

  if (closeMemoriesModalBtn) {
    closeMemoriesModalBtn.addEventListener('click', () => {
      if (patientMemoriesModal) patientMemoriesModal.style.display = 'none';
    });
  }

  loadConversationHistory();
}

function setupVoiceSpeedToggle() {
  if (voiceSpeedBtn) {
    updateVoiceSpeedUI();
    voiceSpeedBtn.addEventListener('click', () => {
      isSlowSpeed = !isSlowSpeed;
      localStorage.setItem('shoi_slow_voice', isSlowSpeed);
      updateVoiceSpeedUI();
      if (audioPlayer) {
        audioPlayer.playbackRate = isSlowSpeed ? 0.85 : 1.0;
      }
      showToast(isSlowSpeed ? '🐢 ধীরগতির কণ্ঠস্বর চালু করা হয়েছে' : '🔊 স্বাভাবিক কণ্ঠস্বর চালু করা হয়েছে');
    });
  }
}

function updateVoiceSpeedUI() {
  if (!voiceSpeedBtn) return;
  voiceSpeedBtn.textContent = isSlowSpeed ? '🐢 ধীরগতি' : '🔊 স্বাভাবিক';
}

function setVoiceState(state) {
  voiceStatus.className = 'voice-status-pill ' + state;
  micWave.className = 'mic-wave' + (state === 'listening' ? ' active' : (state === 'speaking' ? ' speaking' : ''));

  if (state === 'listening' || state === 'speaking') {
    if (audioEqualizer) audioEqualizer.style.display = 'flex';
    if (micIcon) micIcon.style.opacity = '0.25';
  } else {
    if (audioEqualizer) audioEqualizer.style.display = 'none';
    if (micIcon) micIcon.style.opacity = '1';
  }

  if (replayVoiceBtn) {
    if (state === 'speaking') {
      replayVoiceBtn.textContent = '⏹️ থামান';
      replayVoiceBtn.title = 'কণ্ঠস্বর থামান';
    } else {
      replayVoiceBtn.textContent = '🔊 শুনুন';
      replayVoiceBtn.title = 'পুনরায় শুনুন';
    }
  }

  if (state === 'listening') {
    voiceStatusText.textContent = 'শুনছি... আপনার প্রশ্ন বলুন';
    micInstruction.textContent = 'কথা শেষ হলে বোতামে আবার চাপ দিন';
  } else if (state === 'thinking') {
    voiceStatusText.textContent = 'ভাবছি... একটু অপেক্ষা করুন';
    micInstruction.textContent = 'তথ্য যাচাই করা হচ্ছে...';
  } else if (state === 'speaking') {
    voiceStatusText.textContent = 'বলছি... শুনুন';
    micInstruction.textContent = 'থামাতে বোতামে আবার চাপ দিন';
  } else {
    voiceStatusText.textContent = 'কথা বলতে বোতামে চাপ দিন';
    micInstruction.textContent = 'মাঝের বোতামটি চেপে আপনার প্রশ্ন বলুন';
  }
}

async function sendVoiceQuery(textQuery) {
  try {
    const headers = {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId,
      ...getAuthHeaders()
    };
    const res = await fetch(`${API_BASE}/voice`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        direct_transcript: textQuery,
        session_id: sessionId
      })
    });

    if (res.ok) {
      const data = await res.json();
      if (data.session_id) {
        sessionId = data.session_id;
        localStorage.setItem('shoi_session_id', sessionId);
      }
      displayVoiceResponse(data);
    } else {
      setVoiceState('idle');
      showToast('উত্তর পেতে সমস্যা হয়েছে। আবার চেষ্টা করুন।', true);
    }
  } catch (err) {
    console.error('Voice query error:', err);
    setVoiceState('idle');
    showToast('নেটওয়ার্ক সংযোগ নেই বা ত্রুটি দেখা দিয়েছে।', true);
  }
}

async function sendVoiceAudio(audioBlob) {
  try {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'voice_query.webm');
    formData.append('session_id', sessionId);

    const headers = {
      'X-Session-ID': sessionId,
      ...getAuthHeaders()
    };
    const res = await fetch(`${API_BASE}/voice`, {
      method: 'POST',
      headers: headers,
      body: formData
    });

    if (res.ok) {
      const data = await res.json();
      if (data.session_id) {
        sessionId = data.session_id;
        localStorage.setItem('shoi_session_id', sessionId);
      }
      displayVoiceResponse(data);
    } else {
      setVoiceState('idle');
      showToast('ভয়েস প্রক্রিয়াকরণে সমস্যা হয়েছে। আবার চেষ্টা করুন।', true);
    }
  } catch (err) {
    console.error('Voice audio upload error:', err);
    setVoiceState('idle');
    showToast('ভয়েস পাঠাতে সমস্যা হয়েছে।', true);
  }
}

function cleanBanglaPhonetics(text) {
  if (!text) return '';
  // Remove citations & system notes
  let t = text.replace(/\([^\)]*সূত্র[^\)]*\)/g, '').replace(/\[[^\]]*সূত্র[^\]]*\]/g, '');
  t = t.replace(/\(সূত্র:[^\)]*\)/g, '');
  
  // Strip question repeating prefixes and source citations
  t = t.replace(/^প্রশ্ন:[^\n]+\n*/gi, '');
  t = t.replace(/^উত্তর:\s*/gi, '');
  t = t.replace(/\bউত্তর:\s*/gi, '');
  t = t.replace(/^Regarding\s+['"][^'"]+['"]:\s*/gi, '');
  t = t.replace(/\(সূত্র:[^)]*\)/gi, '');
  t = t.replace(/\(Source:[^)]*\)/gi, '');

  // Naturalize bullet items for speech
  t = t.replace(/(?:^|\n|\s)১[\.\)]\s*/g, '\nপ্রথমত, ');
  t = t.replace(/(?:^|\n|\s)২[\.\)]\s*/g, '\nদ্বিতীয়ত, ');
  t = t.replace(/(?:^|\n|\s)৩[\.\)]\s*/g, '\nতৃতীয়ত, ');
  t = t.replace(/(?:^|\n|\s)৪[\.\)]\s*/g, '\nচতুর্থত, ');
  t = t.replace(/(?:^|\n|\s)৫[\.\)]\s*/g, '\nপঞ্চমত, ');
  t = t.replace(/(?:^|\n|\s)[•\-\*]\s*/g, ', ');

  // English acronyms to Bangla phonetics
  t = t.replace(/\bPCOS\b|\bpcos\b/gi, 'পিসিওএস');
  t = t.replace(/\bBMI\b|\bbmi\b/gi, 'বিএমআই');
  t = t.replace(/\bEDD\b|\bedd\b/gi, 'ইডিডি');
  t = t.replace(/\bLMP\b|\blmp\b/gi, 'এলএমপি');
  t = t.replace(/\bAI\b|\bai\b/gi, 'এআই');
  t = t.replace(/\bSMS\b|\bsms\b/gi, 'এসএমএস');
  t = t.replace(/\bWHO\b|\bwho\b/gi, 'হু');
  t = t.replace(/\bDGHS\b|\bdghs\b/gi, 'ডিজিএইচএস');
  t = t.replace(/\bDr\.?|\bdr\.?/gi, 'ডাক্তার');
  t = t.replace(/\bapp\b/gi, 'অ্যাপ');
  t = t.replace(/\b999\b/g, 'নয় নয় নয়');
  t = t.replace(/\b109\b/g, 'এক শূন্য নয়');

  // Convert English digits to Bengali digits
  const enToBn = {'0':'০','1':'১','2':'২','3':'৩','4':'৪','5':'৫','6':'৬','7':'৭','8':'৮','9':'৯'};
  t = t.replace(/[0-9]/g, digit => enToBn[digit] || digit);
  t = t.replace(/([০-৯]+)\s*[-–—]\s*([০-৯]+)/g, '$1 থেকে $2');

  // Remove markdown symbols
  t = t.replace(/[*#`~>\[\]]/g, '');
  t = t.replace(/[-–—]/g, ', ');
  return t.trim();
}

function speakNativeText(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const cleanText = cleanBanglaPhonetics(text);
  if (!cleanText) return;

  // Split into natural sentences so long answers are read in full without browser 15s timeout
  const rawSentences = cleanText.split(/([।?!]+|\n+)/);
  const sentences = [];
  for (let i = 0; i < rawSentences.length; i += 2) {
    const s = (rawSentences[i] || '') + (rawSentences[i + 1] || '');
    const trimmed = s.trim();
    if (trimmed) sentences.push(trimmed);
  }

  if (sentences.length === 0) return;

  setVoiceState('speaking');

  const voices = window.speechSynthesis.getVoices();
  const bnVoice = voices.find(v => 
    v.lang === 'bn-BD' || 
    v.lang.startsWith('bn') || 
    v.name.includes('Bangla') || 
    v.name.includes('Bengali') || 
    v.name.includes('Nabanita')
  );

  let currentIndex = 0;
  function speakNext() {
    if (currentIndex >= sentences.length) {
      setVoiceState('idle');
      return;
    }
    const currentText = sentences[currentIndex++];
    const utterance = new SpeechSynthesisUtterance(currentText);
    utterance.lang = 'bn-BD';
    if (bnVoice) utterance.voice = bnVoice;
    utterance.rate = isSlowSpeed ? 0.78 : 0.92;
    utterance.pitch = 1.0;
    if (isEarpieceMode) {
      utterance.volume = 0.35;
    }

    utterance.onend = () => {
      speakNext();
    };
    utterance.onerror = () => {
      setVoiceState('idle');
    };
    window.speechSynthesis.speak(utterance);
  }

  speakNext();
}

function displayVoiceResponse(data) {
  lastReplyText = data.reply_text;
  responseText.textContent = data.reply_text;
  voiceResponseCard.style.display = 'block';
  setTimeout(() => {
    voiceResponseCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 100);

  // User query bubble hidden per UI requirements
  if (userQueryBubble) {
    userQueryBubble.style.display = 'none';
  }

  // Citations (hidden per UI requirements)
  if (citationsContainer) {
    citationsContainer.innerHTML = '';
    citationsContainer.style.display = 'none';
  }

  // Safety trigger
  const emergencyInlineBox = document.getElementById('emergencyInlineBox');
  if (data.risk_level === 'high' || (data.emergency_payload && data.emergency_payload.is_emergency)) {
    if (emergencyInlineBox) emergencyInlineBox.style.display = 'block';
    if (emergencyModal) emergencyModal.style.display = 'flex';
  } else {
    if (emergencyInlineBox) emergencyInlineBox.style.display = 'none';
  }

  // Audio Playback
  if (data.audio_base64) {
    lastAudioBase64 = data.audio_base64;
    audioPlayer.src = `data:audio/mp3;base64,${data.audio_base64}`;
    audioPlayer.playbackRate = isSlowSpeed ? 0.85 : 1.0;
    setVoiceState('speaking');
    audioPlayer.play().catch(() => {
      // If browser blocks autoplay, user can tap replay button
      setVoiceState('idle');
    });
    audioPlayer.onended = () => setVoiceState('idle');
  } else {
    speakNativeText(data.reply_text);
  }

  // Handle Voice Q&A Cycle Tracking Actions
  const cycleActionBox = document.getElementById('voiceCycleActionBox');
  const cycleSummaryText = document.getElementById('voiceCycleSummaryText');
  const cycleBtnRow = document.getElementById('voiceCycleBtnRow');
  const cycleSavedBadge = document.getElementById('voiceCycleSavedBadge');
  const cycleYesBtn = document.getElementById('voiceCycleYesBtn');
  const cycleNoBtn = document.getElementById('voiceCycleNoBtn');

  if (cycleActionBox) {
    if (data.cycle_action) {
      cycleActionBox.style.display = 'block';
      if (data.cycle_action.status === 'pending_confirmation') {
        const summary = data.cycle_action.summary || 'তারিখ নিশ্চিতকরণ';
        if (cycleSummaryText) cycleSummaryText.textContent = summary;
        if (cycleBtnRow) cycleBtnRow.style.display = 'flex';
        if (cycleSavedBadge) cycleSavedBadge.style.display = 'none';

        if (cycleYesBtn) {
          cycleYesBtn.onclick = () => {
            primeAudioPlayback();
            setVoiceState('thinking');
            sendVoiceQuery('হ্যাঁ, সংরক্ষণ করো');
          };
        }
        if (cycleNoBtn) {
          cycleNoBtn.onclick = () => {
            primeAudioPlayback();
            setVoiceState('thinking');
            sendVoiceQuery('না, বাতিল');
          };
        }
      } else if (data.cycle_action.status === 'saved') {
        if (cycleBtnRow) cycleBtnRow.style.display = 'none';
        if (cycleSavedBadge) cycleSavedBadge.style.display = 'flex';
        if (typeof fetchPeriods === 'function') {
          fetchPeriods();
        }
        showToast('🩸 পিরিয়ডের তথ্য সংরক্ষিত হয়েছে!');
      } else {
        cycleActionBox.style.display = 'none';
      }
    } else {
      cycleActionBox.style.display = 'none';
    }
  }
}

function setupQuickQuestions() {
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      primeAudioPlayback();
      const q = chip.getAttribute('data-q');
      setVoiceState('thinking');
      sendVoiceQuery(q);
    });
  });
}

// 4. Period Tracker Logic
function setupPeriodTracker() {
  const form = document.getElementById('periodForm');
  const startDateInput = document.getElementById('periodStartDate');
  const endDateInput = document.getElementById('periodEndDate');

  const startVoiceBtn = document.getElementById('startPeriodVoiceTrackingBtn');
  if (startVoiceBtn) {
    startVoiceBtn.addEventListener('click', () => {
      primeAudioPlayback();
      showScreen('voice');
      setVoiceState('thinking');
      sendVoiceQuery('আমার পিরিয়ডের তথ্য রেকর্ড করতে চাই');
    });
  }

  // Pre-fill today's date and enforce boundary
  const today = new Date().toISOString().split('T')[0];
  if (startDateInput) {
    startDateInput.value = today;
    startDateInput.max = today;
  }
  if (endDateInput) {
    endDateInput.max = today;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const startDate = startDateInput.value;
    const endDate = endDateInput.value || null;

    if (startDate > today) {
      showToast('ভবিষ্যতের তারিখ নির্বাচন করা যাবে না।', true);
      return;
    }

    if (endDate && endDate < startDate) {
      showToast('শেষের তারিখ শুরুর তারিখের আগের হতে পারে না।', true);
      return;
    }

    const flowInput = form.querySelector('input[name="flow"]:checked');
    const flow = flowInput ? flowInput.value : 'medium';

    // Scoped symptom selection
    const symptoms = [];
    form.querySelectorAll('.symptom-tags input:checked').forEach(cb => symptoms.push(cb.value));

    try {
      const res = await fetch(`${API_BASE}/track/period`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ start_date: startDate, end_date: endDate, flow, symptoms })
      });
      if (res.ok) {
        showToast('পিরিয়ড সফলভাবে সংরক্ষণ করা হয়েছে!');
        // Reset inputs to clean defaults
        startDateInput.value = today;
        endDateInput.value = '';
        form.querySelectorAll('.symptom-tags input').forEach(cb => cb.checked = false);
        loadPeriodData();
      } else {
        const err = await res.json();
        showToast(err.detail || 'পিরিয়ড সংরক্ষণ ব্যর্থ হয়েছে', true);
      }
    } catch (e) {
      console.error(e);
      showToast('সার্ভারের সাথে যোগাযোগ করা যায়নি।', true);
    }
  });
}

async function loadPeriodData() {
  if (!token) return;
  try {
    const resAnalysis = await fetch(`${API_BASE}/track/period/analysis`, {
      headers: getAuthHeaders()
    });
    if (resAnalysis.ok) {
      const a = await resAnalysis.json();
      const infoBox = document.getElementById('predictionInfo');
      infoBox.innerHTML = `
        <p style="white-space: pre-line;">${a.explanation_bn}</p>
        ${a.predicted_next_period_start ? `<p style="margin-top: 8px;"><strong>পরবর্তী পিরিয়ড:</strong> ${a.predicted_next_period_start}</p>` : ''}
        ${a.ovulation_window_start ? `<p><strong>ডিম্বস্ফোটন সময়:</strong> ${a.ovulation_window_start} হতে ${a.ovulation_window_end}</p>` : ''}
      `;
    }

    const resList = await fetch(`${API_BASE}/track/period`, {
      headers: getAuthHeaders()
    });
    if (resList.ok) {
      const list = await resList.json();
      const ul = document.getElementById('periodList');
      if (list.length === 0) {
        ul.innerHTML = '<li>কোনো পূর্ববর্তী পিরিয়ড লগ নেই।</li>';
      } else {
        ul.innerHTML = list.map(item => `
          <li>
            <strong>শুরু:</strong> ${item.start_date} ${item.end_date ? `| <strong>শেষ:</strong> ${item.end_date}` : ''}
            <br><small>মাত্রা: ${item.flow === 'heavy' ? 'ভারী' : (item.flow === 'light' ? 'হালকা' : 'স্বাভাবিক')}, লক্ষণ: ${item.symptoms.join(', ') || 'নেই'}</small>
          </li>
        `).join('');
      }
    }
  } catch (e) {
    console.error(e);
  }
}

// 5. Mood Tracker Logic
let selectedMoodScore = 3;

function setupMoodTracker() {
  const emojiBtns = document.querySelectorAll('.emoji-btn');
  
  // Ensure default score 3 has selected class on load
  emojiBtns.forEach(btn => {
    if (parseInt(btn.getAttribute('data-score')) === selectedMoodScore) {
      btn.classList.add('selected');
    }
    btn.addEventListener('click', () => {
      emojiBtns.forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      selectedMoodScore = parseInt(btn.getAttribute('data-score'));
    });
  });

  document.getElementById('saveMoodBtn').addEventListener('click', async () => {
    const tags = [];
    document.querySelectorAll('#moodTags input:checked').forEach(cb => tags.push(cb.value));

    try {
      const res = await fetch(`${API_BASE}/track/mood`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ mood_score: selectedMoodScore, tags })
      });
      if (res.ok) {
        showToast('আপনার অনুভূতি সংরক্ষণ করা হয়েছে!');
        loadMoodData();
      } else {
        showToast('অনুভূতি সংরক্ষণ করা সম্ভব হয়নি।', true);
      }
    } catch (e) {
      console.error(e);
      showToast('সার্ভারের সাথে যোগাযোগ করা যায়নি।', true);
    }
  });
}

async function loadMoodData() {
  if (!token) return;
  try {
    const res = await fetch(`${API_BASE}/track/mood/analysis`, {
      headers: getAuthHeaders()
    });
    if (res.ok) {
      const a = await res.json();
      const p = document.getElementById('moodSuggestionText');
      p.innerHTML = `
        ${a.seven_day_avg ? `<p>৭ দিনের গড় মেজাজ: <strong>${a.seven_day_avg} / ৫</strong></p>` : ''}
        ${a.phase_correlation_bn ? `<p style="color: #9E3E5B; margin: 6px 0;"><strong>${a.phase_correlation_bn}</strong></p>` : ''}
        <p style="margin-top: 8px;">${a.gentle_suggestion_bn}</p>
      `;
    }
  } catch (e) {
    console.error(e);
  }
}

// 6. PCOS Risk Checker Logic
function setupPCOSChecker() {
  const form = document.getElementById('pcosForm');
  const quizCard = document.getElementById('pcosQuizCard');
  const resultCard = document.getElementById('pcosResultCard');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      age: parseInt(document.getElementById('pcosAge').value),
      height_cm: parseFloat(document.getElementById('pcosHeight').value),
      weight_kg: parseFloat(document.getElementById('pcosWeight').value),
      cycle_regularity: document.querySelector('input[name="cycle_regularity"]:checked').value,
      cycle_length_days: parseInt(document.getElementById('pcosCycleLength').value),
      weight_gain: document.getElementById('pcosWeightGain').checked,
      excess_hair_growth: document.getElementById('pcosHairGrowth').checked,
      skin_darkening: document.getElementById('pcosSkinDark').checked,
      hair_loss: document.getElementById('pcosHairLoss').checked,
      pimples_acne: document.getElementById('pcosAcne').checked,
      regular_exercise: document.querySelector('input[name="pcosExercise"]:checked').value === 'yes'
    };

    try {
      const res = await fetch(`${API_BASE}/pcos/predict`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const result = await res.json();
        displayPCOSResult(result);
      } else {
        showToast('পিসিওএস ফলাফল পাওয়া যায়নি। আবার চেষ্টা করুন।', true);
      }
    } catch (e) {
      console.error(e);
      showToast('সার্ভারের সাথে যোগাযোগ করা যায়নি।', true);
    }
  });

  document.getElementById('pcosRetakeBtn').addEventListener('click', () => {
    resultCard.style.display = 'none';
    quizCard.style.display = 'block';
  });
}

function displayPCOSResult(res) {
  document.getElementById('pcosQuizCard').style.display = 'none';
  const resultCard = document.getElementById('pcosResultCard');
  resultCard.style.display = 'block';

  const badge = document.getElementById('pcosRiskBadge');
  badge.textContent = res.risk_band_bn;
  badge.className = `result-badge ${res.risk_band}`;

  document.getElementById('pcosExplanation').textContent = res.explanation_bn;

  const factorsUl = document.getElementById('pcosFactorsList');
  factorsUl.innerHTML = res.contributing_factors.map(f => `<li>${f}</li>`).join('');

  const adviceUl = document.getElementById('pcosAdviceList');
  adviceUl.innerHTML = res.actionable_advice_bn.map(a => `<li>${a}</li>`).join('');

  document.getElementById('pcosDisclaimer').textContent = res.disclaimer_bn;
}

// 7. Pregnancy Tracker Logic
function setupPregnancyTracker() {
  const saveBtn = document.getElementById('savePregBtn');
  const lmpInput = document.getElementById('pregLmpDate');

  // Enforce boundary
  const today = new Date().toISOString().split('T')[0];
  if (lmpInput) {
    lmpInput.max = today;
  }

  saveBtn.addEventListener('click', async () => {
    const lmp = lmpInput.value;
    if (!lmp) {
      showToast('অনুগ্রহ করে শেষ মাসিকের প্রথম দিন নির্বাচন করুন', true);
      return;
    }
    if (lmp > today) {
      showToast('ভবিষ্যতের তারিখ নির্বাচন করা যাবে না।', true);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/preg/start`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ lmp_date: lmp })
      });
      if (res.ok) {
        const data = await res.json();
        renderPregnancyStatus(data);
        showToast('গর্ভকালীন তথ্য সফলভাবে আপডেট হয়েছে!');
      } else {
        const err = await res.json();
        showToast(err.detail || 'তথ্য প্রক্রিয়াকরণে সমস্যা হয়েছে', true);
      }
    } catch (e) {
      console.error(e);
      showToast('সার্ভারের সাথে যোগাযোগ করা যায়নি।', true);
    }
  });
}

async function loadPregnancyData() {
  if (!token) return;
  try {
    const res = await fetch(`${API_BASE}/preg/timeline`, {
      headers: getAuthHeaders()
    });
    if (res.ok) {
      const data = await res.json();
      renderPregnancyStatus(data);
      // Pre-fill LMP date input
      const lmpInput = document.getElementById('pregLmpDate');
      if (lmpInput && data.lmp_date) {
        lmpInput.value = data.lmp_date;
      }
    }
  } catch (e) {
    console.warn('No active pregnancy found');
  }
}

function renderPregnancyStatus(data) {
  const card = document.getElementById('pregStatusCard');
  card.style.display = 'block';

  document.getElementById('pregWeeks').textContent = data.gestational_weeks;
  document.getElementById('pregTrimester').textContent = data.current_trimester + (data.current_trimester === 1 ? 'ম' : (data.current_trimester === 2 ? 'য়' : 'য়'));
  document.getElementById('pregEdd').textContent = data.edd;

  const m = data.current_milestone;
  document.getElementById('pregBabySize').textContent = `শিশুর আকার: ${m.baby_size_bn}`;
  document.getElementById('pregDevelopment').textContent = m.development_summary_bn;
  document.getElementById('pregMotherChanges').textContent = m.maternal_changes_bn;

  const ancBox = document.getElementById('pregAncNotice');
  if (m.anc_recommended && m.anc_visit_title_bn) {
    ancBox.innerHTML = `<strong>🩺 চেকআপ সময়:</strong> ${m.anc_visit_title_bn}`;
    ancBox.style.display = 'block';
  } else {
    ancBox.style.display = 'none';
  }

  const dangerUl = document.getElementById('pregDangerSigns');
  dangerUl.innerHTML = m.urgent_warning_signs_bn.map(s => `<li>${s}</li>`).join('');
}

// 8. Settings & Authentication Logic (Login, Logout, Unique ID Alert)
function setupSettings() {
  // Copy ID handlers
  const copyId = (idValue) => {
    if (!idValue) return;
    navigator.clipboard.writeText(idValue).then(() => {
      showToast('গোপন ইউনিক আইডি কপি করা হয়েছে!');
    }).catch(() => {
      showToast('আইডি কপি করা হয়েছে!');
    });
  };

  const copyBtn = document.getElementById('copyIdBtn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const idField = document.getElementById('anonymousUserIdDisplay');
      if (idField) copyId(idField.value);
    });
  }

  const modalCopyBtn = document.getElementById('uniqueIdModalCopyBtn');
  if (modalCopyBtn) {
    modalCopyBtn.addEventListener('click', () => {
      copyId(userId);
    });
  }

  const logoutModalCopyBtn = document.getElementById('logoutModalCopyBtn');
  if (logoutModalCopyBtn) {
    logoutModalCopyBtn.addEventListener('click', () => {
      copyId(userId);
    });
  }

  // Show / Close Unique ID Alert Modal
  const showIdAlertModalBtn = document.getElementById('showIdAlertModalBtn');
  if (showIdAlertModalBtn) {
    showIdAlertModalBtn.addEventListener('click', () => {
      showUniqueIdAlert('🌸 আপনার গোপন ইউনিক আইডি ও জরুরি সতর্কতা');
    });
  }

  const closeUniqueIdModalBtn = document.getElementById('closeUniqueIdModalBtn');
  const uniqueIdAlertModal = document.getElementById('uniqueIdAlertModal');
  if (closeUniqueIdModalBtn && uniqueIdAlertModal) {
    closeUniqueIdModalBtn.addEventListener('click', () => {
      if (userId) {
        localStorage.setItem('shoi_id_alert_shown', userId);
      }
      uniqueIdAlertModal.style.display = 'none';
      showToast('আইডি সংরক্ষণ সম্পন্ন হয়েছে');
    });
  }

  // --- LOGOUT SYSTEM WITH SAFE ID ALERT MODAL ---
  const logoutTriggerBtn = document.getElementById('logoutTriggerBtn');
  const logoutConfirmModal = document.getElementById('logoutConfirmModal');
  const cancelLogoutBtn = document.getElementById('cancelLogoutBtn');
  const confirmLogoutBtn = document.getElementById('confirmLogoutBtn');
  const logoutModalUserId = document.getElementById('logoutModalUserId');

  if (logoutTriggerBtn && logoutConfirmModal) {
    logoutTriggerBtn.addEventListener('click', () => {
      if (logoutModalUserId && userId) {
        logoutModalUserId.textContent = userId;
      }
      logoutConfirmModal.style.display = 'flex';
    });
  }

  if (cancelLogoutBtn && logoutConfirmModal) {
    cancelLogoutBtn.addEventListener('click', () => {
      logoutConfirmModal.style.display = 'none';
    });
  }

  if (confirmLogoutBtn && logoutConfirmModal) {
    confirmLogoutBtn.addEventListener('click', () => {
      // Clear authenticated session tokens
      token = null;
      userId = null;
      localStorage.removeItem('shoi_token');
      localStorage.removeItem('shoi_user_id');
      localStorage.removeItem('shoi_id_alert_shown');

      logoutConfirmModal.style.display = 'none';
      updateAuthUIState();

      // Clear cached period logs on screen
      const periodListEl = document.getElementById('periodList');
      if (periodListEl) periodListEl.innerHTML = '<li class="empty-text">কোনো তথ্য নেই</li>';
      const moodSuggestion = document.getElementById('moodSuggestionText');
      if (moodSuggestion) moodSuggestion.textContent = 'আপনার মেজাজের বিশ্লেষণ দেখতে লগ করুন।';

      showToast('সফলভাবে লগআউট করা হয়েছে। ইউনিক আইডি দিয়ে পুনরায় লগইন করতে পারবেন।');
    });
  }

  // --- LOGIN SYSTEM WITH UNIQUE ID & OPTIONAL PIN ---
  const loginSubmitBtn = document.getElementById('loginSubmitBtn');
  const loginUserIdInput = document.getElementById('loginUserIdInput');
  const loginPinInput = document.getElementById('loginPinInput');

  if (loginSubmitBtn && loginUserIdInput) {
    loginSubmitBtn.addEventListener('click', async () => {
      const inputId = loginUserIdInput.value.trim();
      const inputPin = loginPinInput ? loginPinInput.value.trim() : '';

      if (!inputId) {
        showToast('দয়া করে আপনার গোপন ইউনিক আইডি লিখুন বা পেস্ট করুন', true);
        loginUserIdInput.focus();
        return;
      }

      setVoiceState('thinking');
      try {
        const payload = { user_id: inputId };
        if (inputPin) {
          payload.pin = inputPin;
        }

        const res = await fetch(`${API_BASE}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          const data = await res.json();
          token = data.access_token;
          userId = data.user_id;
          localStorage.setItem('shoi_token', token);
          localStorage.setItem('shoi_user_id', userId);
          localStorage.setItem('shoi_id_alert_shown', userId);

          updateAuthUIState();
          loginUserIdInput.value = '';
          if (loginPinInput) loginPinInput.value = '';

          // Reload user's existing health history
          if (typeof fetchPeriods === 'function') fetchPeriods();
          if (typeof fetchMoods === 'function') fetchMoods();
          if (typeof loadPrivacyPreferences === 'function') loadPrivacyPreferences();

          setVoiceState('idle');
          showToast('স্বাগতম! সফলভাবে আপনার অ্যাকাউন্টে লগইন হয়েছে।');
        } else if (res.status === 404) {
          setVoiceState('idle');
          showToast('এই আইডি দিয়ে কোনো অ্যাকাউন্ট পাওয়া যায়নি। সঠিক আইডি দিন।', true);
        } else if (res.status === 401) {
          setVoiceState('idle');
          showToast('ভুল পিন কোড! দয়া করে সঠিক পিন দিন।', true);
        } else {
          setVoiceState('idle');
          showToast('লগইন করতে সমস্যা হয়েছে। দয়া করে আবার চেষ্টা করুন।', true);
        }
      } catch (err) {
        setVoiceState('idle');
        console.error('Login error:', err);
        showToast('সার্ভারের সাথে সংযোগ করা যায়নি। ইন্টারনেট পরীক্ষা করুন।', true);
      }
    });
  }

  // --- CREATE NEW ANONYMOUS ACCOUNT BUTTON ---
  const createNewAccountBtn = document.getElementById('createNewAccountBtn');
  if (createNewAccountBtn) {
    createNewAccountBtn.addEventListener('click', async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/anonymous`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ age_group: '20-29', language: 'bn' })
        });
        if (res.ok) {
          const data = await res.json();
          token = data.access_token;
          userId = data.user_id;
          localStorage.setItem('shoi_token', token);
          localStorage.setItem('shoi_user_id', userId);
          updateAuthUIState();
          showUniqueIdAlert('🌸 আপনার নতুন গোপন ইউনিক আইডি');
          showToast('নতুন গোপন আইডি সফলভাবে তৈরি হয়েছে!');
        } else {
          showToast('নতুন আইডি তৈরিতে সমস্যা হয়েছে।', true);
        }
      } catch (e) {
        console.error(e);
        showToast('সার্ভারের সাথে যোগাযোগ করা যায়নি।', true);
      }
    });
  }

  // Save PIN button
  const savePinBtn = document.getElementById('savePinBtn');
  const pinInput = document.getElementById('userPinInput');
  if (savePinBtn && pinInput) {
    savePinBtn.addEventListener('click', async () => {
      const pin = pinInput.value.trim();
      if (!/^\d{4,6}$/.test(pin)) {
        showToast('পিন অবশ্যই ৪ থেকে ৬ সংখ্যার (শুধু সংখ্যা) হতে হবে', true);
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/auth/pin`, {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify({ pin })
        });
        if (res.ok) {
          showToast('পিন কোড সফলভাবে সংরক্ষিত হয়েছে!');
          pinInput.value = '';
        } else {
          showToast('পিন সংরক্ষণ করতে সমস্যা হয়েছে।', true);
        }
      } catch (e) {
        console.error(e);
        showToast('সার্ভারের সাথে যোগাযোগ করা যায়নি।', true);
      }
    });
  }

  const deleteBtn = document.getElementById('deleteAllDataBtn');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      if (confirm('আপনি কি নিশ্চিত যে আপনার সমস্ত তথ্য চিরতরে মুছে ফেলতে চান? এটি আর ফিরিয়ে আনা যাবে না।')) {
        try {
          const res = await fetch(`${API_BASE}/auth/me`, {
            method: 'DELETE',
            headers: getAuthHeaders()
          });
          if (res.ok) {
            showToast('আপনার সমস্ত তথ্য সফলভাবে মুছে ফেলা হয়েছে।');
            localStorage.clear();
            setTimeout(() => {
              window.location.reload();
            }, 1200);
          } else {
            showToast('তথ্য মুছতে সমস্যা হয়েছে।', true);
          }
        } catch (e) {
          console.error(e);
          showToast('সার্ভারের সাথে যোগাযোগ করা যায়নি।', true);
        }
      }
    });
  }
}

// 9. Shared-Phone Privacy & Decoy Camouflage Features
let isEarpieceMode = localStorage.getItem('shoi_earpiece_mode') === 'true';
let earpieceDeviceId = null;
let decoyTapCount = 0;
let decoyLastTapTime = 0;

function setupSharedPhonePrivacyFeatures() {
  const panicCamouflageBtn = document.getElementById('panicCamouflageBtn');
  const earpieceModeBtn = document.getElementById('earpieceModeBtn');
  const decoyCamouflageOverlay = document.getElementById('decoyCamouflageOverlay');
  const decoyHeader = document.getElementById('decoyHeader');

  // Find earpiece device if supported
  if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
    navigator.mediaDevices.enumerateDevices().then(devices => {
      const earpiece = devices.find(d => d.kind === 'audiooutput' && (d.label.toLowerCase().includes('earpiece') || d.label.toLowerCase().includes('receiver')));
      if (earpiece) earpieceDeviceId = earpiece.deviceId;
    }).catch(() => {});
  }

  function updateEarpieceUI() {
    if (!earpieceModeBtn) return;
    if (isEarpieceMode) {
      earpieceModeBtn.textContent = '👂 ইয়ারপিস মোড';
      earpieceModeBtn.classList.add('earpiece-active');
    } else {
      earpieceModeBtn.textContent = '👂 স্পিকার';
      earpieceModeBtn.classList.remove('earpiece-active');
    }
  }

  if (earpieceModeBtn) {
    updateEarpieceUI();
    earpieceModeBtn.addEventListener('click', () => {
      isEarpieceMode = !isEarpieceMode;
      localStorage.setItem('shoi_earpiece_mode', isEarpieceMode);
      updateEarpieceUI();
      showToast(isEarpieceMode ? 'ইয়ারপিস মোড চালু: ফোনটি কানের কাছে নিয়ে শুনুন' : 'স্পিকার মোড চালু');
    });
  }

  // Panic Camouflage Overlay Handlers
  function activateCamouflage() {
    if (!decoyCamouflageOverlay) return;
    decoyCamouflageOverlay.style.display = 'block';
    // Immediate acoustic silence
    if (audioPlayer) audioPlayer.pause();
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    if (isRecording && recognition) {
      try { recognition.abort(); } catch (e) {}
      isRecording = false;
      setVoiceState('idle');
    }
  }

  function restoreFromCamouflage() {
    if (!decoyCamouflageOverlay) return;
    decoyCamouflageOverlay.style.display = 'none';
    showToast('স্বাভাবিক স্ক্রিনে ফেরা হয়েছে');
  }

  if (panicCamouflageBtn) {
    panicCamouflageBtn.addEventListener('click', () => {
      activateCamouflage();
    });
  }

  // Triple-Tap restoration gesture on decoy overlay header
  function handleTripleTapRestore() {
    const now = Date.now();
    if (now - decoyLastTapTime < 1400) {
      decoyTapCount++;
      if (decoyTapCount >= 3) {
        decoyTapCount = 0;
        restoreFromCamouflage();
      }
    } else {
      decoyTapCount = 1;
    }
    decoyLastTapTime = now;
  }

  if (decoyHeader) {
    decoyHeader.addEventListener('click', handleTripleTapRestore);
  }
  if (decoyCamouflageOverlay) {
    decoyCamouflageOverlay.addEventListener('click', (e) => {
      if (e.target && e.target.id === 'decoyRestoreHint') {
        handleTripleTapRestore();
      }
    });
  }

  // Accelerometer flip gesture (face-down triggers camouflage)
  if (window.DeviceOrientationEvent) {
    window.addEventListener('deviceorientation', (event) => {
      if (event.gamma !== null && (Math.abs(event.gamma) > 150 || (event.beta !== null && event.beta < -40))) {
        activateCamouflage();
      }
    }, { passive: true });
  }

  // RAM-only Hygiene: Auto-silence when app goes to background
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      if (audioPlayer) audioPlayer.pause();
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      if (isRecording && recognition) {
        try { recognition.abort(); } catch (e) {}
        isRecording = false;
        setVoiceState('idle');
      }
      if (isEarpieceMode) {
        activateCamouflage();
      }
    }
  });
}
