/**
 * Smart Attendance System - Live Biometric Recognition Controller (camera.js)
 */

let pollInterval = null;
let seenStudents = new Set();
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

document.addEventListener('DOMContentLoaded', function () {
  // Start recognition status polling every 1 second
  pollInterval = setInterval(pollRecognitionStatus, 1000);
});

function handleFeedError() {
  const overlay = document.getElementById('offlineOverlay');
  if (overlay) overlay.classList.remove('hidden');

  const badge = document.getElementById('statusBadge');
  if (badge) {
    badge.className = 'flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800 border border-slate-700 text-slate-400 text-xs font-semibold';
  }
  const statusText = document.getElementById('statusText');
  if (statusText) statusText.innerText = 'Offline';
}

async function pollRecognitionStatus() {
  try {
    const res = await fetch('/admin/recognition-status');
    const data = await res.json();

    if (data.marked) {
      const attendeeCountEl = document.getElementById('attendeeCount');
      if (attendeeCountEl) {
        attendeeCountEl.innerText = data.count || data.marked.length;
      }

      const list = document.getElementById('attendeesList');
      const empty = document.getElementById('emptyLog');

      if (data.marked.length > 0 && empty) {
        empty.remove();
      }

      data.marked.forEach(name => {
        if (!seenStudents.has(name)) {
          seenStudents.add(name);

          const item = document.createElement('div');
          item.className = 'p-2.5 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-between text-xs transition';
          item.innerHTML = `
            <div class="flex items-center gap-2 truncate">
              <div class="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-[10px] font-bold">
                <i class="fa-solid fa-check"></i>
              </div>
              <span class="font-semibold text-white truncate">${name}</span>
            </div>
            <span class="text-[10px] text-emerald-400 font-mono font-medium">Verified</span>
          `;
          if (list) list.prepend(item);
        }
      });
    }

    if (!data.running) {
      handleFeedError();
    }
  } catch (err) {
    console.error('Recognition polling error:', err);
  }
}

async function stopRecognition() {
  try {
    const res = await fetch('/admin/stop-recognition', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken
      }
    });
    const data = await res.json();
    handleFeedError();
    if (pollInterval) clearInterval(pollInterval);
  } catch (err) {
    alert('Error stopping scanner: ' + err);
  }
}

async function restartRecognition() {
  const subSelect = document.getElementById('subjectSelector');
  const subjectId = subSelect ? subSelect.value : 1;
  try {
    await fetch('/admin/start-recognition', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ subject_id: subjectId })
    });
    window.location.reload();
  } catch (err) {
    alert('Error restarting scanner: ' + err);
  }
}

function changeSubject(subId) {
  window.location.href = `/admin/camera?subject_id=${subId}`;
}

async function finalizeAndNotifyFromCamera() {
  const subSelect = document.getElementById('subjectSelector');
  const subjectId = subSelect ? subSelect.value : document.body.getAttribute('data-subject-id') || 1;
  if (!confirm('Finalize attendance session for this subject? All remaining unverified students will be marked Absent and automated alert emails will be dispatched.')) return;

  try {
    await stopRecognition();
    const res = await fetch('/admin/close-attendance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ subject_id: subjectId, send_emails: true })
    });
    const data = await res.json();
    alert(data.message || 'Attendance finalized and emails dispatched.');
    window.location.href = '/admin';
  } catch (e) {
    alert('Error: ' + e);
  }
}

