(() => {
  const steps = [1, 2, 3, 4, 5, 6];
  let current = 0; // index into steps
  let qrTimerInterval = null;
  let qrLoaded = false;

  const state = {
    category: null, label: null, suggested: null,
  };

  const $ = (sel) => document.querySelector(sel);
  const stepEls = {};
  document.querySelectorAll('.step[data-step]').forEach(el => stepEls[el.dataset.step] = el);

  const backBtn = $('#back-btn');
  const nextBtn = $('#next-btn');
  const errorLine = $('#error-line');
  const ticketNo = $('#ticket-no');
  const ticketSteps = $('#ticket-steps');

  function showStep(n) {
    Object.values(stepEls).forEach(el => el.classList.remove('active'));
    stepEls[String(n)].classList.add('active');
    errorLine.textContent = '';
    backBtn.style.visibility = n === steps[0] ? 'hidden' : 'visible';
    ticketSteps.textContent = `step ${steps.indexOf(n) + 1} / ${steps.length}`;
    ticketNo.textContent = state.category ? `TICKET · ${state.label.toUpperCase()}` : 'TICKET · DRAFT';

    if (n === 5) startPaymentStep();
  }

  function setError(msg) { errorLine.textContent = msg; }

  // ---- step 1: category ----
  document.querySelectorAll('.cat-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.cat-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      state.category = card.dataset.code;
      state.label = card.dataset.label;
      state.suggested = Number(card.dataset.amount);
      $('#f-amount').value = state.suggested;
      toggleExplainField();
    });
  });

  function toggleExplainField() {
    const amount = Number($('#f-amount').value || 0);
    const wrap = $('#f-explain-wrap');
    wrap.hidden = !(state.suggested !== null && amount !== state.suggested);
  }
  $('#f-amount').addEventListener('input', toggleExplainField);

  // ---- validation per step ----
  function validateStep(n) {
    if (n === 1) {
      if (!state.category) return 'Please pick a meal to donate.';
    }
    if (n === 2) {
      const amount = Number($('#f-amount').value);
      if (!amount || amount <= 0) return 'Please enter a valid amount.';
      if (amount !== state.suggested && !$('#f-explain').value.trim()) {
        return "Since that's different from the suggested amount, please tell us why.";
      }
    }
    if (n === 3) {
      if (!$('#f-name').value.trim()) return 'Please tell us your name.';
      const email = $('#f-email').value.trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return 'Please enter a valid email.';
    }
    if (n === 6) {
      if (!$('#f-screenshot').files.length) return 'Please attach your payment screenshot.';
      if (!$('#f-utr').value.trim()) return 'Please enter your UTR / transaction ID.';
    }
    return null;
  }

  // ---- QR + timer (step 5) ----
  function startPaymentStep() {
    if (!qrLoaded) {
      const img = $('#qr-img');
      img.onerror = () => {
        img.style.display = 'none';
        setError('QR image failed to load. Please tell the admin, or try again shortly.');
      };
      img.onload = () => { img.style.display = 'block'; };
      img.src = '/api/qr?_=' + Date.now();
      qrLoaded = true;
    }
    if (qrTimerInterval) return;
    const totalSeconds = window.QR_MINUTES * 60;
    let remaining = totalSeconds;
    const timerEl = $('#qr-timer');
    qrTimerInterval = setInterval(() => {
      remaining -= 1;
      const m = Math.max(0, Math.floor(remaining / 60));
      const s = Math.max(0, remaining % 60);
      timerEl.textContent = `${m}:${String(s).padStart(2, '0')}`;
      if (remaining <= 0) {
        clearInterval(qrTimerInterval);
        timerEl.textContent = 'expired';
      }
    }, 1000);
  }

  // ---- submit (end of step 6) ----
  async function submitDonation() {
    nextBtn.disabled = true;
    nextBtn.textContent = 'Sending…';

    const fd = new FormData();
    fd.append('category', state.category);
    fd.append('amount', $('#f-amount').value);
    fd.append('explanation', $('#f-explain').value.trim() || '-');
    fd.append('name', $('#f-name').value.trim());
    fd.append('instagram', $('#f-insta').value.trim() || '-');
    fd.append('email', $('#f-email').value.trim());
    fd.append('message', $('#f-message').value.trim() || '-');
    fd.append('utr', $('#f-utr').value.trim());
    fd.append('screenshot', $('#f-screenshot').files[0]);

    try {
      const res = await fetch('/api/submit', { method: 'POST', body: fd });
      const data = await res.json();
      if (!data.ok) {
        setError(data.error || 'Something went wrong, please try again.');
        nextBtn.disabled = false;
        nextBtn.textContent = 'Next';
        return;
      }
      $('#ref-id').textContent = data.donation_id;
      window.DONATION_ID = data.donation_id;
      showStep('done');
      $('#back-btn').style.visibility = 'hidden';
      nextBtn.style.display = 'none';
    } catch (e) {
      setError('Network error, please try again.');
      nextBtn.disabled = false;
      nextBtn.textContent = 'Next';
    }
  }

  // ---- nav buttons ----
  nextBtn.addEventListener('click', () => {
    const n = steps[current];
    const err = validateStep(n);
    if (err) { setError(err); return; }

    if (n === 6) { submitDonation(); return; }

    current += 1;
    showStep(steps[current]);
  });

  backBtn.addEventListener('click', () => {
    if (current === 0) return;
    current -= 1;
    showStep(steps[current]);
  });

  $('#check-status-btn').addEventListener('click', async () => {
    if (!window.DONATION_ID) return;
    const line = $('#status-line');
    line.textContent = 'Checking…';
    try {
      const res = await fetch(`/api/status/${window.DONATION_ID}`);
      const data = await res.json();
      if (!data.ok) { line.textContent = 'Not found.'; return; }
      line.textContent = `Status: ${data.status}`;
    } catch (e) {
      line.textContent = 'Could not check status right now.';
    }
  });

  showStep(steps[0]);
})();
