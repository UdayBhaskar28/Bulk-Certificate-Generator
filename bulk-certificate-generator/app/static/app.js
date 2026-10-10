/**
 * CertifyBulk — Institutional Credential & Certificate Issuance Engine
 * Interactive Client Controller & Live Canvas Synchronizer
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- Global State ---
  let recipientsState = [];
  let activePreviewIndex = 0;
  let trackingPollInterval = null;
  let currentJobCache = null;
  let activeFilter = 'all';

  // --- DOM Elements ---
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabPanels = document.querySelectorAll('.tab-panel');
  const toastContainer = document.getElementById('toast-container');

  // Form inputs
  const formCreateJob = document.getElementById('form-create-job');
  const btnSubmitJob = document.getElementById('btn-submit-job');
  const inputTitle = document.getElementById('input-title');
  const inputIssuer = document.getElementById('input-issuer');
  const inputDate = document.getElementById('input-date');
  const inputDescription = document.getElementById('input-description');
  const inputRecipientsJson = document.getElementById('input-recipients-json');
  const badgeRecipientCount = document.getElementById('badge-recipient-count');

  // Mode switcher elements
  const modeTabs = document.querySelectorAll('.mode-tab');
  const modeViews = {
    table: document.getElementById('view-mode-table'),
    csv: document.getElementById('view-mode-csv'),
    json: document.getElementById('view-mode-json')
  };
  const recipientTableBody = document.getElementById('recipient-table-body');
  const btnAddRecipientRow = document.getElementById('btn-add-recipient-row');
  const btnClearRecipients = document.getElementById('btn-clear-recipients');
  const csvDropzone = document.getElementById('csv-dropzone');
  const inputCsvFile = document.getElementById('input-csv-file');

  // Live Preview elements
  const livePreviewTitle = document.getElementById('live-preview-title');
  const livePreviewRecipient = document.getElementById('live-preview-recipient');
  const livePreviewIssuer = document.getElementById('live-preview-issuer');
  const livePreviewDate = document.getElementById('live-preview-date');
  const previewCandidateChips = document.getElementById('preview-candidate-chips');

  // Tracker elements
  const inputTrackerJobId = document.getElementById('input-tracker-job-id');
  const btnTrackJob = document.getElementById('btn-track-job');
  const btnRefreshTracker = document.getElementById('btn-refresh-tracker');
  const trackerEmptyState = document.getElementById('tracker-empty-state');
  const trackerContent = document.getElementById('tracker-content');
  const trackerStatusPill = document.getElementById('tracker-status-pill');
  const trackerJobTitle = document.getElementById('tracker-job-title');
  const trackerJobIssuer = document.getElementById('tracker-job-issuer');
  const trackerJobIdChip = document.getElementById('tracker-job-id-chip');
  const trackerJobDateChip = document.getElementById('tracker-job-date-chip');
  const btnDownloadAllZip = document.getElementById('btn-download-all-zip');
  const metricTotal = document.getElementById('metric-total');
  const metricProcessed = document.getElementById('metric-processed');
  const metricSuccess = document.getElementById('metric-success');
  const metricFailed = document.getElementById('metric-failed');
  const progressLabel = document.getElementById('progress-label');
  const progressFill = document.getElementById('progress-fill');
  const trackerItemsBody = document.getElementById('tracker-items-body');

  // History & Verification elements
  const historyItemsBody = document.getElementById('history-items-body');
  const btnRefreshHistory = document.getElementById('btn-refresh-history');
  const inputVerifyId = document.getElementById('input-verify-id');
  const btnRunVerify = document.getElementById('btn-run-verify');
  const btnSampleVerify = document.getElementById('btn-sample-verify');
  const verifyResultContainer = document.getElementById('verify-result-container');

  // Modal elements
  const previewModal = document.getElementById('preview-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const pdfPreviewFrame = document.getElementById('pdf-preview-frame');
  const modalTitle = document.getElementById('modal-title');

  // --- Professional Sample Cohorts ---
  const sampleAcademyCohort = [
    { name: "Eleanor Vance", email: "eleanor.vance@oxford.edu", grade: "First Class Honors" },
    { name: "Dr. Julian Thorne", email: "j.thorne@cambridge-inst.org", grade: "Distinction" },
    { name: "Amina Al-Mansoor", email: "amina.mansoor@qatar-health.org", grade: "High Honors" },
    { name: "Kenji Takahashi", email: "kenji.takahashi@tokyo-univ.ac.jp", grade: "Merit Award" },
    { name: "Sofia Hernandez", email: "sofia.hernandez@madrid-biomed.es", grade: "Dean's List" }
  ];

  const sampleValidationCohort = [
    { name: "Dr. Arthur Pendelton", email: "arthur.pendelton@oxford.ac.uk", grade: "Distinction" },
    { name: "", email: "unnamed.scholar@harvard.edu", grade: "Incomplete" }, // Invalid: missing name
    { name: "Beatrice Montgomery", email: "beatrice.m@stanford.edu", grade: "Honors" },
    { name: "Damian Sterling", email: "not-a-valid-email-format", grade: "Review Needed" }, // Invalid: email format
    { name: "Elena Rostova", email: "elena.rostova@sorbonne-univ.fr", grade: "Excellence" }
  ];

  // --- Toast System ---
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✓';
    if (type === 'error') icon = '⚠️';

    toast.innerHTML = `<span style="font-weight:700;">${icon}</span> <span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('toast-leave');
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // --- Tab Navigation ---
  function switchTab(tabId) {
    tabButtons.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
    });
    tabPanels.forEach(panel => {
      panel.classList.toggle('active', panel.id === tabId);
    });

    if (tabId === 'tab-history') {
      loadJobHistory();
    }
  }

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn.getAttribute('data-tab'));
    });
  });

  // --- Mode Switcher (Table / CSV / JSON) ---
  modeTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      modeTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const mode = tab.getAttribute('data-mode');

      Object.keys(modeViews).forEach(m => {
        modeViews[m].classList.toggle('active', m === mode);
      });
    });
  });

  // --- Synchronize Recipients State ---
  function setRecipientsState(newList) {
    recipientsState = Array.isArray(newList) ? newList : [];
    updateBadge();
    renderInteractiveTable();
    updateJsonTextarea();
    renderPreviewCandidateChips();
    updateLiveCertificate();
  }

  function updateBadge() {
    const count = recipientsState.length;
    badgeRecipientCount.textContent = `${count} Candidate${count === 1 ? '' : 's'} Listed`;
    badgeRecipientCount.className = count > 0 ? 'badge badge-info' : 'badge';
  }

  function updateJsonTextarea() {
    inputRecipientsJson.value = JSON.stringify(recipientsState, null, 2);
  }

  function renderInteractiveTable() {
    recipientTableBody.innerHTML = '';
    if (recipientsState.length === 0) {
      recipientTableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">
            No recipients listed yet. Click <strong>Add Recipient Row</strong> or drop a CSV file.
          </td>
        </tr>
      `;
      return;
    }

    recipientsState.forEach((item, index) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>
          <input type="text" class="table-input input-row-name" data-index="${index}" value="${escapeHtml(item.name || '')}" placeholder="Full Name">
        </td>
        <td>
          <input type="email" class="table-input input-row-email" data-index="${index}" value="${escapeHtml(item.email || '')}" placeholder="official.email@domain.com">
        </td>
        <td>
          <input type="text" class="table-input input-row-grade" data-index="${index}" value="${escapeHtml(item.grade || '')}" placeholder="e.g. Honors">
        </td>
        <td style="text-align: right;">
          <button type="button" class="btn-row-delete" data-index="${index}" title="Remove entry">✕</button>
        </td>
      `;
      recipientTableBody.appendChild(tr);
    });

    // Row input listeners
    recipientTableBody.querySelectorAll('.input-row-name').forEach(input => {
      input.addEventListener('input', (e) => {
        const idx = parseInt(e.target.getAttribute('data-index'), 10);
        recipientsState[idx].name = e.target.value;
        updateJsonTextarea();
        updateLiveCertificate();
      });
    });

    recipientTableBody.querySelectorAll('.input-row-email').forEach(input => {
      input.addEventListener('input', (e) => {
        const idx = parseInt(e.target.getAttribute('data-index'), 10);
        recipientsState[idx].email = e.target.value;
        updateJsonTextarea();
      });
    });

    recipientTableBody.querySelectorAll('.input-row-grade').forEach(input => {
      input.addEventListener('input', (e) => {
        const idx = parseInt(e.target.getAttribute('data-index'), 10);
        recipientsState[idx].grade = e.target.value;
        updateJsonTextarea();
      });
    });

    recipientTableBody.querySelectorAll('.btn-row-delete').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.target.getAttribute('data-index'), 10);
        recipientsState.splice(idx, 1);
        if (activePreviewIndex >= recipientsState.length) {
          activePreviewIndex = Math.max(0, recipientsState.length - 1);
        }
        setRecipientsState(recipientsState);
      });
    });
  }

  // Add row
  btnAddRecipientRow.addEventListener('click', () => {
    recipientsState.push({ name: '', email: '', grade: '' });
    setRecipientsState(recipientsState);
    const lastRow = recipientTableBody.querySelector('tr:last-child .input-row-name');
    if (lastRow) lastRow.focus();
  });

  // Clear rows
  btnClearRecipients.addEventListener('click', () => {
    if (recipientsState.length > 0 && confirm('Clear all recipient rows from the registry?')) {
      setRecipientsState([]);
      showToast('Recipient registry cleared', 'info');
    }
  });

  // Direct JSON input sync
  inputRecipientsJson.addEventListener('input', () => {
    try {
      const val = inputRecipientsJson.value.trim();
      if (!val) {
        recipientsState = [];
        updateBadge();
        renderInteractiveTable();
        renderPreviewCandidateChips();
        updateLiveCertificate();
        return;
      }
      const parsed = JSON.parse(val);
      if (Array.isArray(parsed)) {
        recipientsState = parsed;
        updateBadge();
        renderInteractiveTable();
        renderPreviewCandidateChips();
        updateLiveCertificate();
      }
    } catch {
      badgeRecipientCount.textContent = 'JSON Syntax Error';
      badgeRecipientCount.className = 'badge table-badge FAILED';
    }
  });

  // --- CSV Drag & Drop Upload Handler ---
  function parseCsvContent(text) {
    const lines = text.split(/\r?\n/).filter(line => line.trim().length > 0);
    if (lines.length < 2) return [];

    const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/^["']|["']$/g, ''));
    const nameIdx = headers.findIndex(h => ['name', 'recipient_name', 'full_name', 'candidate'].includes(h));
    const emailIdx = headers.findIndex(h => ['email', 'recipient_email', 'mail'].includes(h));
    const gradeIdx = headers.findIndex(h => ['grade', 'honors', 'score', 'award'].includes(h));

    const result = [];
    for (let i = 1; i < lines.length; i++) {
      const row = lines[i].split(',').map(cell => cell.trim().replace(/^["']|["']$/g, ''));
      if (row.length === 0 || (row.length === 1 && !row[0])) continue;

      const name = nameIdx !== -1 && row[nameIdx] ? row[nameIdx] : (row[0] || '');
      const email = emailIdx !== -1 && row[emailIdx] ? row[emailIdx] : (row[1] || '');
      const grade = gradeIdx !== -1 && row[gradeIdx] ? row[gradeIdx] : (row[2] || '');

      result.push({ name, email, grade });
    }
    return result;
  }

  function handleCsvFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.csv')) {
      showToast('Please upload a valid .csv file', 'error');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const parsed = parseCsvContent(e.target.result);
        if (parsed.length === 0) {
          showToast('No candidate rows detected in CSV file', 'error');
          return;
        }
        setRecipientsState(parsed);
        // Switch to table mode so user can see parsed rows
        document.getElementById('btn-mode-table').click();
        showToast(`Successfully imported ${parsed.length} candidate rows from CSV!`, 'success');
      } catch (err) {
        showToast('Error reading CSV: ' + err.message, 'error');
      }
    };
    reader.readAsText(file);
  }

  csvDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    csvDropzone.classList.add('dragover');
  });

  csvDropzone.addEventListener('dragleave', () => {
    csvDropzone.classList.remove('dragover');
  });

  csvDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    csvDropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleCsvFile(e.dataTransfer.files[0]);
    }
  });

  inputCsvFile.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleCsvFile(e.target.files[0]);
    }
  });

  // --- Real-time Live Certificate Canvas Synchronization ---
  function updateLiveCertificate() {
    const titleVal = inputTitle.value.trim() || 'Master Program in Global Health Policy';
    const issuerVal = inputIssuer.value.trim() || 'Cambridge Academic Credentialing Council';
    const dateVal = inputDate.value.trim() || 'October 10, 2026';

    let activeRecipient = 'Eleanor Vance';
    if (recipientsState.length > 0 && recipientsState[activePreviewIndex]) {
      activeRecipient = recipientsState[activePreviewIndex].name || 'Candidate Name';
    }

    livePreviewTitle.textContent = titleVal;
    livePreviewIssuer.textContent = issuerVal;
    livePreviewDate.textContent = dateVal;
    livePreviewRecipient.textContent = activeRecipient;
  }

  function renderPreviewCandidateChips() {
    previewCandidateChips.innerHTML = '';
    if (recipientsState.length === 0) {
      previewCandidateChips.innerHTML = `<span style="font-size:0.72rem; color:var(--text-muted);">None listed</span>`;
      return;
    }

    recipientsState.slice(0, 6).forEach((item, index) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = `candidate-chip ${index === activePreviewIndex ? 'active' : ''}`;
      chip.textContent = item.name ? item.name.split(' ')[0] : `Candidate ${index + 1}`;
      chip.title = item.name || `Candidate ${index + 1}`;
      chip.addEventListener('click', () => {
        activePreviewIndex = index;
        renderPreviewCandidateChips();
        updateLiveCertificate();
      });
      previewCandidateChips.appendChild(chip);
    });
  }

  inputTitle.addEventListener('input', updateLiveCertificate);
  inputIssuer.addEventListener('input', updateLiveCertificate);
  inputDate.addEventListener('input', updateLiveCertificate);

  // --- Sample Loader Triggers ---
  document.getElementById('btn-load-sample').addEventListener('click', () => {
    inputTitle.value = "Executive Master of Public Health & Global Health Policy";
    inputIssuer.value = "Johns Hopkins & Global Health Council";
    inputDate.value = "October 10, 2026";
    inputDescription.value = "Conferred upon successful defense of advanced epidemiological capstone practicum.";
    setRecipientsState(sampleAcademyCohort);
    showToast('Loaded John Hopkins Cohort Sample', 'info');
  });

  document.getElementById('btn-load-mixed-sample').addEventListener('click', () => {
    inputTitle.value = "Distinguished Fellowship in Sustainable Finance";
    inputIssuer.value = "Oxford Institute for Institutional Economics";
    inputDate.value = "October 10, 2026";
    inputDescription.value = "Professional cohort issuance with intentional validation error tests.";
    setRecipientsState(sampleValidationCohort);
    showToast('Loaded Validation Test Cohort', 'info');
  });

  // Pre-load clean sample initially
  document.getElementById('btn-load-sample').click();

  // --- Confetti Celebration Function ---
  function launchConfetti() {
    const canvas = document.getElementById('confetti-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const pieces = [];
    const colors = ['#d4af37', '#f3d982', '#10b981', '#38bdf8', '#ffffff', '#e5c05b'];

    for (let i = 0; i < 90; i++) {
      pieces.push({
        x: Math.random() * canvas.width,
        y: Math.random() * -canvas.height,
        size: Math.random() * 8 + 5,
        color: colors[Math.floor(Math.random() * colors.length)],
        velX: (Math.random() - 0.5) * 4,
        velY: Math.random() * 3 + 3,
        rotation: Math.random() * 360,
        rotSpeed: (Math.random() - 0.5) * 8
      });
    }

    let frames = 0;
    function render() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      let alive = false;
      pieces.forEach(p => {
        p.x += p.velX;
        p.y += p.velY;
        p.rotation += p.rotSpeed;

        if (p.y < canvas.height) alive = true;

        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rotation * Math.PI) / 180);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
        ctx.restore();
      });

      frames++;
      if (alive && frames < 240) {
        requestAnimationFrame(render);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    }
    requestAnimationFrame(render);
  }

  // --- Submit Generation Job ---
  formCreateJob.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!recipientsState || recipientsState.length === 0) {
      showToast('Please add at least one candidate before submitting', 'error');
      return;
    }

    const payload = {
      title: inputTitle.value.trim(),
      issuer_name: inputIssuer.value.trim(),
      issue_date: inputDate.value.trim() || undefined,
      description: inputDescription.value.trim() || undefined,
      recipients: recipientsState
    };

    btnSubmitJob.disabled = true;
    btnSubmitJob.innerHTML = `<span>⏳ Authorizing & Compiling...</span>`;

    try {
      const res = await fetch('/api/v1/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        let errorMsg = `Server error (${res.status})`;
        try {
          const errorData = await res.json();
          errorMsg = errorData.detail || errorData.message || errorMsg;
        } catch {
          const text = await res.text();
          if (text) errorMsg = text;
        }
        throw new Error(errorMsg);
      }

      const jobData = await res.json();
      showToast('Batch successfully authorized and submitted!', 'success');

      // Switch to tracker tab and render immediately
      switchTab('tab-nav-tracker');
      inputTrackerJobId.value = jobData.id;
      renderJobDetails(jobData);

      if (jobData.status === 'COMPLETED') {
        launchConfetti();
        showToast('All cohort certificates generated successfully!', 'success');
      } else if (!['COMPLETED', 'PARTIALLY_COMPLETED', 'FAILED'].includes(jobData.status)) {
        startTrackingJob(jobData.id);
      }

    } catch (err) {
      showToast('Issuance error: ' + err.message, 'error');
    } finally {
      btnSubmitJob.disabled = false;
      btnSubmitJob.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path>
        </svg>
        Authorize & Issue Certificates
      `;
    }
  });

  // --- Job Tracking & Polling ---
  async function fetchJobData(jobId) {
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}`);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  function renderJobDetails(job) {
    if (!job) return;
    currentJobCache = job;

    trackerEmptyState.classList.add('hidden');
    trackerContent.classList.remove('hidden');

    trackerStatusPill.textContent = job.status;
    trackerStatusPill.className = `status-pill ${job.status}`;

    trackerJobTitle.textContent = job.title;
    trackerJobIssuer.textContent = `Issued by ${job.issuer_name}`;
    trackerJobIdChip.textContent = `ID: ${job.id}`;
    trackerJobDateChip.textContent = `Date: ${job.issue_date}`;

    metricTotal.textContent = job.total_count;
    metricProcessed.textContent = job.processed_count;
    metricSuccess.textContent = job.success_count;
    metricFailed.textContent = job.failed_count;

    const pct = job.progress_percentage || 0;
    progressLabel.textContent = `${pct}%`;
    progressFill.style.width = `${pct}%`;

    if (job.download_all_url && job.success_count > 0) {
      btnDownloadAllZip.href = job.download_all_url;
      btnDownloadAllZip.classList.remove('disabled');
    } else {
      btnDownloadAllZip.classList.add('disabled');
      btnDownloadAllZip.removeAttribute('href');
    }

    renderItemsTable(job.certificates || []);
  }

  function renderItemsTable(items) {
    trackerItemsBody.innerHTML = '';

    const filtered = items.filter(item => {
      if (activeFilter === 'all') return true;
      return item.status === activeFilter;
    });

    if (filtered.length === 0) {
      trackerItemsBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-muted); padding: 2.5rem;">No certificate records match this filter.</td></tr>`;
      return;
    }

    filtered.forEach(item => {
      const tr = document.createElement('tr');
      const isCompleted = item.status === 'COMPLETED';

      let detailsHtml = '<span style="color:var(--text-muted);">-</span>';
      if (item.error_message) {
        detailsHtml = `<span style="color:var(--danger); font-size:0.78rem;">⚠️ ${escapeHtml(item.error_message)}</span>`;
      } else if (item.file_size) {
        detailsHtml = `<span style="color:var(--text-muted); font-size: 0.78rem;">Vector PDF • ${(item.file_size / 1024).toFixed(1)} KB</span>`;
      }

      tr.innerHTML = `
        <td class="recipient-col">
          <div style="font-weight:700;">${escapeHtml(item.recipient_name || '(Unnamed)')}</div>
          <div style="font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:var(--text-muted); margin-top:0.25rem;">
            ID: <span class="clickable-id" onclick="copyCertId('${item.id}')" title="Click to copy Certificate UUID">${item.id.slice(0, 8)}...${item.id.slice(-4)} 📋</span>
          </div>
        </td>
        <td class="email-col">${escapeHtml(item.recipient_email || '-')}</td>
        <td><span class="table-badge ${item.status}">${item.status}</span></td>
        <td>${detailsHtml}</td>
        <td style="text-align: right;">
          ${isCompleted ? `
            <a href="${item.download_url}" class="btn-table-action btn-table-download" download>
              ⬇️ Download
            </a>
            <button type="button" class="btn-table-action btn-table-preview" onclick="openPreviewModal('${item.preview_url}', '${escapeHtml(item.recipient_name)}')">
              👁️ Preview
            </button>
            <button type="button" class="btn-table-action btn-table-verify" onclick="quickVerifyCert('${item.id}')" title="Audit authenticity in Verifier tab">
              🔍 Verify
            </button>
          ` : `<span style="color:var(--text-muted); font-size:0.75rem;">Unavailable</span>`}
        </td>
      `;
      trackerItemsBody.appendChild(tr);
    });
  }

  function startTrackingJob(jobId) {
    if (trackingPollInterval) {
      clearInterval(trackingPollInterval);
    }

    const poll = async () => {
      const job = await fetchJobData(jobId);
      if (job) {
        renderJobDetails(job);
        if (['COMPLETED', 'PARTIALLY_COMPLETED', 'FAILED'].includes(job.status)) {
          clearInterval(trackingPollInterval);
          trackingPollInterval = null;
          if (job.status === 'COMPLETED') {
            launchConfetti();
            showToast('All certificates generated successfully!', 'success');
          }
        }
      } else {
        clearInterval(trackingPollInterval);
      }
    };

    poll();
    trackingPollInterval = setInterval(poll, 1500);
  }

  btnTrackJob.addEventListener('click', () => {
    const id = inputTrackerJobId.value.trim();
    if (id) startTrackingJob(id);
  });

  btnRefreshTracker.addEventListener('click', () => {
    const id = inputTrackerJobId.value.trim();
    if (id) startTrackingJob(id);
  });

  document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeFilter = chip.getAttribute('data-filter');
      if (currentJobCache && currentJobCache.certificates) {
        renderItemsTable(currentJobCache.certificates);
      }
    });
  });

  // --- Job History ---
  async function loadJobHistory() {
    historyItemsBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2.5rem; color:var(--text-muted);">Retrieving issuance archives...</td></tr>`;
    try {
      const res = await fetch('/api/v1/jobs?limit=50');
      if (!res.ok) throw new Error("Failed to load jobs");
      const jobs = await res.json();

      if (jobs.length === 0) {
        historyItemsBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2.5rem; color:var(--text-muted);">No certification archives recorded yet.</td></tr>`;
        return;
      }

      historyItemsBody.innerHTML = '';
      jobs.forEach(job => {
        const tr = document.createElement('tr');
        const dateStr = new Date(job.created_at).toLocaleString();
        tr.innerHTML = `
          <td>
            <div style="font-weight: 600; color: #fff;">${escapeHtml(job.title)}</div>
            <div style="color: var(--text-muted); font-size: 0.78rem;">${escapeHtml(job.issuer_name)}</div>
          </td>
          <td><span class="table-badge ${job.status}">${job.status}</span></td>
          <td style="font-family:'JetBrains Mono', monospace; font-size:0.8rem;">${job.progress_percentage}%</td>
          <td style="font-family:'JetBrains Mono', monospace; font-size:0.8rem;">${job.success_count} / ${job.total_count}</td>
          <td style="color: var(--text-muted); font-size: 0.78rem;">${dateStr}</td>
          <td style="text-align: right;">
            <button type="button" class="btn-table-action btn-table-preview" onclick="inspectHistoricalJob('${job.id}')">
              Inspect Batch
            </button>
          </td>
        `;
        historyItemsBody.appendChild(tr);
      });
    } catch {
      historyItemsBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2.5rem; color:var(--danger);">Error loading archives.</td></tr>`;
    }
  }

  btnRefreshHistory.addEventListener('click', loadJobHistory);

  window.inspectHistoricalJob = (jobId) => {
    switchTab('tab-nav-tracker');
    inputTrackerJobId.value = jobId;
    startTrackingJob(jobId);
  };

  // --- Public Credential Verifier ---
  btnRunVerify.addEventListener('click', async () => {
    const certId = inputVerifyId.value.trim();
    if (!certId) {
      showToast('Please enter a certificate identifier (UUID)', 'error');
      return;
    }

    verifyResultContainer.classList.remove('hidden');
    verifyResultContainer.innerHTML = `<div style="text-align:center; padding: 1.5rem; color:var(--text-muted);">Auditing certificate cryptographic signature...</div>`;

    try {
      const res = await fetch(`/api/v1/certificates/${certId}/verify`);
      const data = await res.json();

      if (data.valid) {
        verifyResultContainer.className = 'verify-result-card verified';
        verifyResultContainer.innerHTML = `
          <div class="verify-badge-header">
            <div class="verify-seal-icon">✓</div>
            <div>
              <h3 style="color: var(--success); font-size: 1.2rem; margin-bottom: 0.2rem;">Authentic Institutional Credential</h3>
              <p style="color: var(--text-secondary); font-size: 0.82rem;">Confirmed signature issued by certified authority</p>
            </div>
          </div>
          <div class="verify-details-grid">
            <div class="verify-detail-item">
              <span class="verify-detail-label">Conferred Candidate</span>
              <span class="verify-detail-val">${escapeHtml(data.recipient_name || '-')}</span>
            </div>
            <div class="verify-detail-item">
              <span class="verify-detail-label">Recipient Email</span>
              <span class="verify-detail-val" style="font-family:'JetBrains Mono', monospace; font-size:0.8rem;">${escapeHtml(data.recipient_email || '-')}</span>
            </div>
            <div class="verify-detail-item">
              <span class="verify-detail-label">Program of Study</span>
              <span class="verify-detail-val">${escapeHtml(data.title || '-')}</span>
            </div>
            <div class="verify-detail-item">
              <span class="verify-detail-label">Issuing Authority</span>
              <span class="verify-detail-val">${escapeHtml(data.issuer_name || '-')}</span>
            </div>
            <div class="verify-detail-item">
              <span class="verify-detail-label">Conferral Date</span>
              <span class="verify-detail-val">${escapeHtml(data.issue_date || '-')}</span>
            </div>
            <div class="verify-detail-item">
              <span class="verify-detail-label">Certificate ID</span>
              <span class="verify-detail-val" style="font-family:'JetBrains Mono', monospace; font-size:0.75rem;">${escapeHtml(data.certificate_id)}</span>
            </div>
          </div>
          ${data.download_url ? `
            <a href="${data.download_url}" class="btn-zip-download" style="display:inline-flex;" download>
              ⬇️ Download Official Vector PDF
            </a>
          ` : ''}
        `;
        showToast('Certificate successfully verified!', 'success');
      } else {
        verifyResultContainer.className = 'verify-result-card';
        verifyResultContainer.innerHTML = `
          <div class="verify-badge-header">
            <div class="verify-seal-icon" style="background:var(--danger-bg); border-color:var(--danger); color:var(--danger);">✕</div>
            <div>
              <h3 style="color: var(--danger); font-size: 1.2rem; margin-bottom: 0.2rem;">Verification Failed</h3>
              <p style="color: var(--text-secondary); font-size: 0.82rem;">No authentic issuance found matching this identifier</p>
            </div>
          </div>
          <p style="color: var(--text-muted); font-size: 0.85rem;">Status: <code>${escapeHtml(data.verification_status)}</code></p>
        `;
      }
    } catch (err) {
      verifyResultContainer.innerHTML = `<p style="color: var(--danger);">Network error verifying credential: ${escapeHtml(err.message)}</p>`;
    }
  });

  // Sample ID verify loader
  btnSampleVerify.addEventListener('click', async () => {
    try {
      const res = await fetch('/api/v1/jobs?limit=5');
      if (res.ok) {
        const jobs = await res.json();
        if (jobs.length > 0) {
          const detailRes = await fetch(`/api/v1/jobs/${jobs[0].id}`);
          if (detailRes.ok) {
            const detail = await detailRes.json();
            if (detail.certificates && detail.certificates.length > 0) {
              const completed = detail.certificates.find(c => c.status === 'COMPLETED');
              if (completed) {
                inputVerifyId.value = completed.id;
                btnRunVerify.click();
                return;
              }
            }
          }
        }
      }
      showToast('No issued certificates found to load. Please issue a batch first!', 'info');
    } catch {
      showToast('Could not fetch sample certificate ID', 'error');
    }
  });

  // --- ID Utilities & Verification Shortcuts ---
  window.copyCertId = (id) => {
    navigator.clipboard.writeText(id).then(() => {
      showToast('Certificate UUID copied to clipboard!', 'success');
    }).catch(() => {
      prompt('Copy Certificate ID:', id);
    });
  };

  window.quickVerifyCert = (id) => {
    switchTab('tab-nav-verify');
    inputVerifyId.value = id;
    btnRunVerify.click();
  };

  // --- PDF Preview Modal ---
  window.openPreviewModal = (previewUrl, recipientName) => {
    modalTitle.textContent = `Certificate Document — ${recipientName}`;
    pdfPreviewFrame.src = previewUrl;
    previewModal.classList.remove('hidden');
  };

  btnCloseModal.addEventListener('click', () => {
    previewModal.classList.add('hidden');
    pdfPreviewFrame.src = 'about:blank';
  });

  previewModal.querySelector('.modal-backdrop').addEventListener('click', () => {
    previewModal.classList.add('hidden');
    pdfPreviewFrame.src = 'about:blank';
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !previewModal.classList.contains('hidden')) {
      previewModal.classList.add('hidden');
      pdfPreviewFrame.src = 'about:blank';
    }
  });

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
});
