/**
 * Smart Attendance System - Administrator Dashboard Interactions (admin_dashboard.js)
 */

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

document.addEventListener('DOMContentLoaded', function () {
  // Initialize Chart.js Doughnut Chart
  const ctx = document.getElementById('attendanceDoughnut');
  if (ctx && typeof Chart !== 'undefined') {
    const present = parseInt(ctx.getAttribute('data-present') || '0', 10);
    const absent = parseInt(ctx.getAttribute('data-absent') || '0', 10);
    const pending = parseInt(ctx.getAttribute('data-pending') || '0', 10);

    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Present', 'Absent', 'Pending'],
        datasets: [{
          data: [present, absent, pending],
          backgroundColor: ['#16a34a', '#dc2626', '#d97706'],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        cutout: '72%'
      }
    });
  }
});

function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const ol = document.getElementById('mobileOverlay');
  if (sb) sb.classList.toggle('-translate-x-full');
  if (ol) ol.classList.toggle('hidden');
}

function openSubjectModal() {
  const modal = document.getElementById('subjectModal');
  if (modal) modal.classList.remove('hidden');
}

function closeSubjectModal() {
  const modal = document.getElementById('subjectModal');
  if (modal) modal.classList.add('hidden');
}

function filterRoster() {
  const searchInput = document.getElementById('rosterSearch');
  if (!searchInput) return;
  const q = searchInput.value.toLowerCase();
  const rows = document.querySelectorAll('#rosterTable tbody tr');
  rows.forEach(r => {
    const text = r.innerText.toLowerCase();
    r.style.display = text.includes(q) ? '' : 'none';
  });
}

async function startRecognition(subjectId) {
  try {
    const res = await fetch('/admin/start-recognition', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ subject_id: subjectId })
    });
    const data = await res.json();
    if (data.redirect) {
      window.location.href = data.redirect;
    } else {
      window.location.href = `/admin/camera?subject_id=${subjectId}`;
    }
  } catch (e) {
    window.location.href = `/admin/camera?subject_id=${subjectId}`;
  }
}

function openCloseAttendanceModal() {
  const modal = document.getElementById('closeAttendanceModal');
  if (modal) modal.classList.remove('hidden');
}

function closeCloseAttendanceModal() {
  const modal = document.getElementById('closeAttendanceModal');
  if (modal) modal.classList.add('hidden');
}

function closeAttendance(subjectId) {
  openCloseAttendanceModal();
}

async function submitCloseAttendance(subjectId) {
  const checkbox = document.getElementById('sendEmailsCheckbox');
  const sendEmailsFlag = checkbox ? checkbox.checked : true;
  const btn = document.getElementById('confirmCloseBtn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-xs"></i> Processing...';
  }

  try {
    const res = await fetch('/admin/close-attendance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({
        subject_id: subjectId,
        send_emails: sendEmailsFlag
      })
    });
    const data = await res.json();
    closeCloseAttendanceModal();
    alert(data.message || 'Attendance finalized.');
    window.location.reload();
  } catch (e) {
    alert('Error closing attendance: ' + e);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-check text-xs"></i> Finalize &amp; Dispatch';
    }
  }
}

async function sendEmails(subjectId, forceResend = false) {
  const promptMsg = forceResend
    ? 'Force resend absence alert emails to all absent students (even if already sent today)?'
    : 'Dispatch automated absence alert emails to absent students in this subject?';
  if (!confirm(promptMsg)) return;

  try {
    const res = await fetch('/admin/send-emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({
        subject_id: subjectId,
        force_resend: forceResend
      })
    });
    const data = await res.json();
    alert(data.message || 'Email dispatch initiated.');
    const logsModal = document.getElementById('emailLogsModal');
    if (logsModal && !logsModal.classList.contains('hidden')) {
      openEmailLogsModal(subjectId);
    }
  } catch (e) {
    alert('Error sending emails: ' + e);
  }
}

async function openEmailLogsModal(subjectId) {
  const modal = document.getElementById('emailLogsModal');
  if (modal) modal.classList.remove('hidden');

  const container = document.getElementById('emailLogsContainer');
  if (container) {
    container.innerHTML = '<div class="text-center py-8 text-slate-400 text-xs"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Fetching email delivery logs...</div>';
  }

  try {
    const res = await fetch(`/admin/email-logs?subject_id=${subjectId}`);
    const data = await res.json();
    const logs = data.logs || [];

    if (!container) return;

    if (logs.length === 0) {
      container.innerHTML = `
        <div class="text-center py-10 text-slate-400 text-xs">
          <i class="fa-solid fa-envelope-open text-2xl text-slate-300 mb-2 block"></i>
          No automated absence emails have been dispatched for this subject today.<br>
          <span class="text-slate-500 mt-1 inline-block">Emails are automatically sent when you close attendance or click "Email Absent Alerts".</span>
        </div>
      `;
      return;
    }

    let html = `
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider border-b border-slate-200">
            <tr>
              <th class="py-2.5 px-3">Student</th>
              <th class="py-2.5 px-3">Recipient Email</th>
              <th class="py-2.5 px-3 text-center">Delivery Status</th>
              <th class="py-2.5 px-3 text-right">Dispatched At</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-slate-700">
    `;

    logs.forEach(l => {
      let badge = '';
      if (l.status === 'Sent') {
        badge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">Delivered</span>';
      } else if (l.status === 'Simulated') {
        badge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800" title="Recorded in local log">Queued / Simulated</span>';
      } else {
        badge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800" title="${l.error_message || 'Delivery error'}">Failed</span>`;
      }

      html += `
        <tr class="hover:bg-slate-50">
          <td class="py-2.5 px-3">
            <span class="font-bold text-slate-900">${l.student_name}</span>
            <span class="block text-[10px] text-slate-400 font-mono">${l.roll || ''}</span>
          </td>
          <td class="py-2.5 px-3 font-mono text-slate-600 text-[11px]">${l.recipient_email}</td>
          <td class="py-2.5 px-3 text-center">${badge}</td>
          <td class="py-2.5 px-3 text-right text-slate-400 text-[11px]">${l.sent_at}</td>
        </tr>
      `;
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;
  } catch (e) {
    if (container) {
      container.innerHTML = `<div class="p-4 text-center text-xs text-rose-600">Failed to load email logs: ${e}</div>`;
    }
  }
}

function closeEmailLogsModal() {
  const modal = document.getElementById('emailLogsModal');
  if (modal) modal.classList.add('hidden');
}

async function resetTodayAttendance(subjectId) {
  if (!confirm('Are you sure you want to reset attendance for today? All attendance rows for today will be deleted.')) return;
  try {
    const res = await fetch('/admin/reset-attendance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ subject_id: subjectId })
    });
    const data = await res.json();
    alert(data.message || 'Today attendance reset.');
    window.location.reload();
  } catch (e) {
    alert('Error resetting: ' + e);
  }
}

